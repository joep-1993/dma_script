"""
Google Ads Helper Functions

This file contains helper functions for Google Ads listing tree operations.
"""

import time
from google.ads.googleads.errors import GoogleAdsException

# Global counter for temporary resource names
_temp_id_counter = -1


def next_id():
    """Generate next temporary ID for criterion resource names"""
    global _temp_id_counter
    _temp_id_counter -= 1
    return _temp_id_counter


def list_listing_groups_with_depth(client, customer_id: str, ad_group_id: str):
    """
    List all listing groups in an ad group with their depth.

    Returns:
        tuple: (rows, max_depth)
    """
    ga_service = client.get_service("GoogleAdsService")
    ag_service = client.get_service("AdGroupService")
    ag_path = ag_service.ad_group_path(customer_id, ad_group_id)

    query = f"""
        SELECT
            ad_group_criterion.resource_name,
            ad_group_criterion.listing_group.type,
            ad_group_criterion.listing_group.parent_ad_group_criterion,
            ad_group_criterion.listing_group.case_value.product_custom_attribute.index,
            ad_group_criterion.listing_group.case_value.product_custom_attribute.value,
            ad_group_criterion.negative,
            ad_group_criterion.cpc_bid_micros
        FROM ad_group_criterion
        WHERE ad_group_criterion.ad_group = '{ag_path}'
            AND ad_group_criterion.type = 'LISTING_GROUP'
    """

    try:
        results = list(ga_service.search(customer_id=customer_id, query=query))

        # Calculate depth
        depth_map = {}

        def calculate_depth(row):
            res_name = row.ad_group_criterion.resource_name
            if res_name in depth_map:
                return depth_map[res_name]

            parent = row.ad_group_criterion.listing_group.parent_ad_group_criterion
            if not parent:
                depth = 0
            else:
                # Find parent row
                parent_row = next((r for r in results if r.ad_group_criterion.resource_name == parent), None)
                if parent_row:
                    depth = 1 + calculate_depth(parent_row)
                else:
                    depth = 1

            depth_map[res_name] = depth
            return depth

        for row in results:
            calculate_depth(row)

        max_depth = max(depth_map.values()) if depth_map else 0
        return results, max_depth

    except Exception:
        return [], 0


def safe_remove_entire_listing_tree(client, customer_id: str, ad_group_id: str):
    agc = client.get_service("AdGroupCriterionService")
    rows, depth = list_listing_groups_with_depth(client, customer_id, ad_group_id)
    if not rows:
        return

    # Find the root SUBDIVISION (the one with no parent)
    root = None
    for r in rows:
        if not r.ad_group_criterion.listing_group.parent_ad_group_criterion:
            root = r
            break

    if not root:
        return

    # Remove only the root - the API will cascade-delete all children
    op = client.get_type("AdGroupCriterionOperation")
    op.remove = root.ad_group_criterion.resource_name

    try:
        agc.mutate_ad_group_criteria(customer_id=customer_id, operations=[op])
    except GoogleAdsException as ex:
        # Ignore if the tree is already gone or resource not found
        if not any(
            (getattr(e.error_code, "criterion_error", None) and
             e.error_code.criterion_error.name == "LISTING_GROUP_DOES_NOT_EXIST") or
            (getattr(e.error_code, "mutate_error", None) and
             e.error_code.mutate_error.name == "RESOURCE_NOT_FOUND")
            for e in ex.failure.errors
        ):
            raise


def create_listing_group_subdivision(
    client,
    customer_id,
    ad_group_id,
    parent_ad_group_criterion_resource_name=None,
    listing_dimension_info=None,
):
    operation = client.get_type("AdGroupCriterionOperation")
    ad_group_criterion = operation.create
    ad_group_criterion.resource_name = client.get_service(
        "AdGroupCriterionService"
    ).ad_group_criterion_path(customer_id, ad_group_id, next_id())
    ad_group_criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED

    listing_group_info = ad_group_criterion.listing_group
    listing_group_info.type_ = client.enums.ListingGroupTypeEnum.SUBDIVISION
    if parent_ad_group_criterion_resource_name is not None:
        listing_group_info.parent_ad_group_criterion = parent_ad_group_criterion_resource_name
    if listing_dimension_info is not None:
        client.copy_from(listing_group_info.case_value, listing_dimension_info)
    return operation


def create_listing_group_unit_biddable(
        client,
        customer_id,
        ad_group_id,
        parent_ad_group_criterion_resource_name,
        listing_dimension_info,
        targeting_negative,
        cpc_bid_micros=None
):
    operation = client.get_type("AdGroupCriterionOperation")
    criterion = operation.create
    criterion.resource_name = client.get_service(
        "AdGroupCriterionService"
    ).ad_group_criterion_path(customer_id, ad_group_id, next_id())
    criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
    if cpc_bid_micros and targeting_negative == False:
        criterion.cpc_bid_micros = cpc_bid_micros

    listing_group = criterion.listing_group
    listing_group.type_ = client.enums.ListingGroupTypeEnum.UNIT
    listing_group.parent_ad_group_criterion = parent_ad_group_criterion_resource_name

    # Case values contain the listing dimension used for the node.
    # For OTHERS units, pass a ListingDimensionInfo with index but no value
    if listing_dimension_info is not None:
        client.copy_from(listing_group.case_value, listing_dimension_info)

    if targeting_negative:
        criterion.negative = True
    return operation