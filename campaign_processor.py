"""
DMA Shop Campaigns Processor

This script processes Excel files with shop campaign data and updates Google Ads
listing trees with custom label 3 targeting (shop name).

Usage:
    python campaign_processor.py

Configuration:
    - Excel file path: EXCEL_FILE_PATH constant below
    - Customer ID: CUSTOMER_ID constant below
    - Google Ads credentials: google-ads.yaml in the same directory or set via environment
"""

import sys
import os
import time
import platform
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
import openpyxl
from openpyxl import load_workbook
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import helper functions (add your existing helper functions to google_ads_helpers.py)
try:
    from google_ads_helpers import (
        safe_remove_entire_listing_tree,
        create_listing_group_subdivision,
        create_listing_group_unit_biddable,
        add_standard_shopping_campaign,
        add_shopping_ad_group,
        add_shopping_product_ad,
    )
except ImportError:
    print("⚠️  Warning: Could not import helper functions from google_ads_helpers.py")
    print("   Please add your existing helper functions to google_ads_helpers.py")

# ============================================================================
# CONFIGURATION
# ============================================================================

CUSTOMER_ID = "3800751597"
MCC_ACCOUNT_ID = "3011145605"  # MCC account where bid strategies are stored
DEFAULT_BID_MICROS = 200_000  # €0.20

# Bid strategy mapping based on custom label 1
BID_STRATEGY_MAPPING = {
    'a': 'DMA: Elektronica shops A - 0,25',
    'b': 'DMA: Elektronica shops B - 0,21',
    'c': 'DMA: Elektronica shops C - 0,17'
}

# Auto-detect Excel file path based on operating system
def get_excel_path():
    """
    Automatically detect the correct Excel file path based on OS.

    Returns:
        str: Path to Excel file (WSL format for Linux, Windows format for Windows)
    """
    # Base Windows path
    windows_path = "c:/Users/JoepvanSchagen/Downloads/dma_script_ivor.xlsx"
    wsl_path = "/mnt/c/Users/JoepvanSchagen/Downloads/dma_script_ivor.xlsx"

    system = platform.system().lower()

    if system == "windows":
        # Running on native Windows (PyCharm on Windows)
        return windows_path
    elif system == "linux":
        # Check if running on WSL
        if os.path.exists("/proc/version"):
            with open("/proc/version", "r") as f:
                if "microsoft" in f.read().lower():
                    # Running on WSL
                    return wsl_path
        # Running on native Linux - try WSL path first, fall back to Windows path
        if os.path.exists(wsl_path):
            return wsl_path
        return windows_path
    else:
        # Default to Windows path for other systems (macOS, etc.)
        return windows_path

EXCEL_FILE_PATH = get_excel_path()

# Sheet names
SHEET_INCLUSION = "toevoegen"  # Inclusion sheet
SHEET_EXCLUSION = "uitsluiten"  # Exclusion sheet

# Column indices (0-based) - INCLUSION SHEET (toevoegen)
COL_SHOP_NAME = 0      # Column A: Shop name
COL_SHOP_ID = 1        # Column B: Shop ID
COL_MAINCAT = 2        # Column C: maincat
COL_MAINCAT_ID = 3     # Column D: maincat_id
COL_CUSTOM_LABEL_1 = 4 # Column E: custom label 1
COL_BUDGET = 5         # Column F: budget
COL_STATUS = 6         # Column G: Status (TRUE/FALSE)
COL_ERROR = 7          # Column H: Error message (when status is FALSE)

# Column indices (0-based) - EXCLUSION SHEET (uitsluiten) - OLD STRUCTURE
COL_EX_SHOP_NAME = 0      # Column A: Shop name
COL_EX_SHOP_ID = 1        # Column B: Shop ID
COL_EX_CAT_UITSLUITEN = 2 # Column C: cat_uitsluiten
COL_EX_DIEPSTE_CAT_ID = 3 # Column D: Diepste cat ID
COL_EX_CUSTOM_LABEL_1 = 4 # Column E: custom label 1
COL_EX_STATUS = 5         # Column F: Status (TRUE/FALSE)
COL_EX_ERROR = 6          # Column G: Error message (when status is FALSE)


# ============================================================================
# GOOGLE ADS CLIENT INITIALIZATION
# ============================================================================

def initialize_google_ads_client():
    """
    Initialize Google Ads API client.

    Loads credentials from .env file with the following variables:
    - GOOGLE_ADS_DEVELOPER_TOKEN
    - GOOGLE_ADS_CLIENT_ID
    - GOOGLE_ADS_CLIENT_SECRET
    - GOOGLE_ADS_REFRESH_TOKEN
    - GOOGLE_ADS_LOGIN_CUSTOMER_ID (optional)

    Alternatively, can use google-ads.yaml if .env variables are not set.

    Returns:
        GoogleAdsClient: Initialized client
    """
    try:
        # Try loading from environment variables first
        if os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"):
            print("Loading Google Ads credentials from .env file...")
            credentials = {
                "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
                "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
                "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
                "use_proto_plus": True
            }

            # Add login_customer_id if provided
            login_customer_id = os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
            if login_customer_id:
                credentials["login_customer_id"] = login_customer_id

            client = GoogleAdsClient.load_from_dict(credentials)
            print("✅ Google Ads client initialized successfully from .env")
        else:
            # Fall back to google-ads.yaml
            print("Loading Google Ads credentials from google-ads.yaml...")
            client = GoogleAdsClient.load_from_storage()
            print("✅ Google Ads client initialized successfully from google-ads.yaml")

        return client
    except Exception as e:
        print(f"❌ Error initializing Google Ads client: {e}")
        print("   Make sure your .env file contains:")
        print("   - GOOGLE_ADS_DEVELOPER_TOKEN")
        print("   - GOOGLE_ADS_CLIENT_ID")
        print("   - GOOGLE_ADS_CLIENT_SECRET")
        print("   - GOOGLE_ADS_REFRESH_TOKEN")
        print("   - GOOGLE_ADS_LOGIN_CUSTOMER_ID (optional)")
        sys.exit(1)


# ============================================================================
# BID STRATEGY RETRIEVAL
# ============================================================================

def get_bid_strategy_by_name(
    client: GoogleAdsClient,
    customer_id: str,
    strategy_name: str
) -> Optional[str]:
    """
    Retrieve portfolio bid strategy by name.

    Args:
        client: Google Ads client
        customer_id: Customer ID
        strategy_name: Bid strategy name to search for

    Returns:
        Bid strategy resource name or None if not found
    """
    ga_service = client.get_service("GoogleAdsService")

    # Escape single quotes in strategy name for GAQL (replace ' with \')
    escaped_strategy_name = strategy_name.replace("'", "\\'")

    query = f"""
        SELECT
            bidding_strategy.id,
            bidding_strategy.name,
            bidding_strategy.resource_name
        FROM bidding_strategy
        WHERE bidding_strategy.name = '{escaped_strategy_name}'
        LIMIT 1
    """

    try:
        response = ga_service.search(customer_id=customer_id, query=query)

        for row in response:
            print(f"   📊 Found bid strategy: {row.bidding_strategy.name} (ID: {row.bidding_strategy.id})")
            return row.bidding_strategy.resource_name

        print(f"   ⚠️  Bid strategy '{strategy_name}' not found")
        return None

    except Exception as e:
        print(f"   ❌ Error searching for bid strategy '{strategy_name}': {e}")
        return None


# ============================================================================
# CAMPAIGN AND AD GROUP RETRIEVAL
# ============================================================================

def get_campaign_by_name_pattern(
    client: GoogleAdsClient,
    customer_id: str,
    name_pattern: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieve campaign by name pattern.

    Args:
        client: Google Ads client
        customer_id: Customer ID
        name_pattern: Campaign name pattern (e.g., "PLA/Electronics_A")

    Returns:
        Dict with campaign info (id, name, resource_name) or None if not found
    """
    ga_service = client.get_service("GoogleAdsService")

    # Escape single quotes in name pattern for GAQL (replace ' with \')
    escaped_name_pattern = name_pattern.replace("'", "\\'")

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.resource_name,
            campaign.status
        FROM campaign
        WHERE campaign.name LIKE '%{escaped_name_pattern}%'
            AND campaign.status != 'REMOVED'
        LIMIT 1
    """

    try:
        response = ga_service.search(customer_id=customer_id, query=query)

        for row in response:
            campaign = row.campaign
            return {
                'id': campaign.id,
                'name': campaign.name,
                'resource_name': campaign.resource_name,
                'status': campaign.status.name
            }

        return None

    except GoogleAdsException as e:
        print(f"❌ Error searching for campaign '{name_pattern}': {e}")
        return None


def get_ad_group_from_campaign(
    client: GoogleAdsClient,
    customer_id: str,
    campaign_id: int
) -> Optional[Dict[str, Any]]:
    """
    Retrieve the first active ad group from a campaign.

    Args:
        client: Google Ads client
        customer_id: Customer ID
        campaign_id: Campaign ID

    Returns:
        Dict with ad group info (id, name, resource_name) or None if not found
    """
    ga_service = client.get_service("GoogleAdsService")

    query = f"""
        SELECT
            ad_group.id,
            ad_group.name,
            ad_group.resource_name,
            ad_group.status
        FROM ad_group
        WHERE ad_group.campaign = 'customers/{customer_id}/campaigns/{campaign_id}'
            AND ad_group.status != 'REMOVED'
        LIMIT 1
    """

    try:
        response = ga_service.search(customer_id=customer_id, query=query)

        for row in response:
            ad_group = row.ad_group
            return {
                'id': ad_group.id,
                'name': ad_group.name,
                'resource_name': ad_group.resource_name,
                'status': ad_group.status.name
            }

        return None

    except GoogleAdsException as e:
        print(f"❌ Error retrieving ad group for campaign {campaign_id}: {e}")
        return None


def get_campaign_and_ad_group_by_pattern(
    client: GoogleAdsClient,
    customer_id: str,
    name_pattern: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieve campaign AND ad group by campaign name pattern in a single query.
    This is more efficient than making two separate API calls.

    Args:
        client: Google Ads client
        customer_id: Customer ID
        name_pattern: Campaign name pattern (e.g., "PLA/Electronics_A")

    Returns:
        Dict with campaign and ad_group info:
        {
            'campaign': {'id': ..., 'name': ..., 'resource_name': ..., 'status': ...},
            'ad_group': {'id': ..., 'name': ..., 'resource_name': ..., 'status': ...}
        }
        or None if not found
    """
    ga_service = client.get_service("GoogleAdsService")

    # Escape single quotes in name pattern for GAQL (replace ' with \')
    escaped_name_pattern = name_pattern.replace("'", "\\'")

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.resource_name,
            campaign.status,
            ad_group.id,
            ad_group.name,
            ad_group.resource_name,
            ad_group.status
        FROM ad_group
        WHERE campaign.name LIKE '%{escaped_name_pattern}%'
            AND campaign.status != 'REMOVED'
            AND ad_group.status != 'REMOVED'
        LIMIT 1
    """

    try:
        response = ga_service.search(customer_id=customer_id, query=query)

        for row in response:
            return {
                'campaign': {
                    'id': row.campaign.id,
                    'name': row.campaign.name,
                    'resource_name': row.campaign.resource_name,
                    'status': row.campaign.status.name
                },
                'ad_group': {
                    'id': row.ad_group.id,
                    'name': row.ad_group.name,
                    'resource_name': row.ad_group.resource_name,
                    'status': row.ad_group.status.name
                }
            }

        return None

    except GoogleAdsException as e:
        print(f"❌ Error searching for campaign+ad group '{name_pattern}': {e}")
        return None


# ============================================================================
# LISTING TREE REBUILD FUNCTIONS (Custom Label 3 Targeting)
# ============================================================================

def rebuild_tree_with_custom_label_3_inclusion(
    client: GoogleAdsClient,
    customer_id: str,
    ad_group_id: int,
    shop_name: str,
    default_bid_micros: int = DEFAULT_BID_MICROS
):
    """
    Rebuild listing tree to TARGET (include) a specific shop name via custom label 3.

    Structure:
    Root SUBDIVISION
    ├─ Custom Label 3 = shop_name [POSITIVE, biddable] → Target this shop
    └─ Custom Label 3 OTHERS [NEGATIVE] → Exclude all other shops

    Args:
        client: Google Ads client
        customer_id: Customer ID
        ad_group_id: Ad group ID
        shop_name: Shop name to target (custom label 3 value)
        default_bid_micros: Bid amount in micros
    """
    print(f"   Rebuilding tree to TARGET shop '{shop_name}' (custom label 3)")

    # Remove existing tree
    safe_remove_entire_listing_tree(client, customer_id, str(ad_group_id))
    time.sleep(0.5)

    agc_service = client.get_service("AdGroupCriterionService")

    # MUTATE 1: Create root SUBDIVISION + Custom Label 3 OTHERS (negative)
    ops1 = []

    # 1. ROOT SUBDIVISION
    root_op = create_listing_group_subdivision(
        client=client,
        customer_id=customer_id,
        ad_group_id=str(ad_group_id),
        parent_ad_group_criterion_resource_name=None,
        listing_dimension_info=None
    )
    root_tmp = root_op.create.resource_name
    ops1.append(root_op)

    # 2. Custom Label 3 OTHERS (negative - blocks all other shops)
    dim_cl3_others = client.get_type("ListingDimensionInfo")
    dim_cl3_others.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX3  # INDEX3 = Custom Label 3
    # Don't set value - OTHERS case

    ops1.append(
        create_listing_group_unit_biddable(
            client=client,
            customer_id=customer_id,
            ad_group_id=str(ad_group_id),
            parent_ad_group_criterion_resource_name=root_tmp,
            listing_dimension_info=dim_cl3_others,
            targeting_negative=True,  # NEGATIVE - blocks everything else
            cpc_bid_micros=None
        )
    )

    # Execute first mutate
    resp1 = agc_service.mutate_ad_group_criteria(customer_id=customer_id, operations=ops1)
    root_actual = resp1.results[0].resource_name
    time.sleep(0.5)

    # MUTATE 2: Add specific shop name as POSITIVE unit
    ops2 = []

    dim_shop = client.get_type("ListingDimensionInfo")
    dim_shop.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX3  # INDEX3 = Custom Label 3
    dim_shop.product_custom_attribute.value = shop_name

    ops2.append(
        create_listing_group_unit_biddable(
            client=client,
            customer_id=customer_id,
            ad_group_id=str(ad_group_id),
            parent_ad_group_criterion_resource_name=root_actual,
            listing_dimension_info=dim_shop,
            targeting_negative=False,  # POSITIVE targeting
            cpc_bid_micros=default_bid_micros
        )
    )

    agc_service.mutate_ad_group_criteria(customer_id=customer_id, operations=ops2)
    print(f"   ✅ Tree rebuilt: ONLY targeting shop '{shop_name}'")


def rebuild_tree_with_custom_label_3_exclusion(
    client: GoogleAdsClient,
    customer_id: str,
    ad_group_id: int,
    shop_name: str,
    default_bid_micros: int = DEFAULT_BID_MICROS
):
    """
    Rebuild listing tree to EXCLUDE a specific shop name via custom label 3.

    Following the pattern from rebuild_tree_with_label_and_item_ids in example_functions.txt:
    1. Read existing tree structure
    2. Collect ALL custom label structures (CL0, CL1, etc.) EXCEPT CL3
    3. Rebuild tree preserving those structures
    4. Add CL3 exclusion

    Args:
        client: Google Ads client
        customer_id: Customer ID
        ad_group_id: Ad group ID
        shop_name: Shop name to exclude (custom label 3 value)
        default_bid_micros: Bid amount in micros
    """
    print(f"   Rebuilding tree to EXCLUDE shop '{shop_name}' (custom label 3)")

    # Step 1: Read existing tree structure
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
    except Exception as e:
        print(f"   ❌ Error reading existing tree: {e}")
        raise  # Re-raise exception so calling code can handle it properly

    # Step 2: Collect ALL custom label structures to preserve (EXCEPT CL2/INDEX2 and CL3/INDEX3)
    custom_label_structures = []
    custom_label_subdivisions = []

    if results:
        for row in results:
            criterion = row.ad_group_criterion
            lg = criterion.listing_group
            case_val = lg.case_value

            if (case_val and
                case_val._pb.WhichOneof("dimension") == "product_custom_attribute"):
                index_name = case_val.product_custom_attribute.index.name
                value = case_val.product_custom_attribute.value

                # Skip Custom Label 2 (INDEX2) and Custom Label 3 (INDEX3) - we're replacing them
                # INDEX2 is the old (incorrect) shop name targeting, INDEX3 is the new (correct) one
                if index_name == 'INDEX2' or index_name == 'INDEX3':
                    continue

                # Skip OTHERS cases (empty value)
                if not value or value == '':
                    continue

                # Collect SUBDIVISION nodes separately
                if lg.type_.name == 'SUBDIVISION':
                    custom_label_subdivisions.append({
                        'index': index_name,
                        'value': value,
                        'parent': lg.parent_ad_group_criterion if lg.parent_ad_group_criterion else None
                    })

                # Preserve all other custom label UNIT nodes (both negative and positive)
                if lg.type_.name == 'UNIT':
                    custom_label_structures.append({
                        'index': index_name,
                        'value': value,
                        'negative': criterion.negative,
                        'bid_micros': criterion.cpc_bid_micros
                    })

    if custom_label_subdivisions:
        print(f"      ℹ️ Found {len(custom_label_subdivisions)} existing subdivision(s):")
        for struct in custom_label_subdivisions:
            print(f"         - {struct['index']}: '{struct['value']}' (SUBDIVISION)")

    if custom_label_structures:
        print(f"      ℹ️ Preserving {len(custom_label_structures)} existing UNIT structure(s):")
        for struct in custom_label_structures:
            neg_str = "[NEGATIVE]" if struct['negative'] else "[POSITIVE]"
            print(f"         - {struct['index']}: '{struct['value']}' {neg_str}")

    # Step 3: Remove old tree
    safe_remove_entire_listing_tree(client, customer_id, str(ad_group_id))
    # No sleep needed - API operations are synchronous

    agc_service = client.get_service("AdGroupCriterionService")

    # Step 4: Rebuild tree hierarchically with preserved structures + CL3 exclusion
    # Use SUBDIVISIONS to determine hierarchy, not UNIT nodes

    # Group subdivisions by INDEX (dimension type)
    cl0_subdivisions = [s for s in custom_label_subdivisions if s['index'] == 'INDEX0']
    cl1_subdivisions = [s for s in custom_label_subdivisions if s['index'] == 'INDEX1']

    # Group UNIT structures by INDEX
    cl0_units = [s for s in custom_label_structures if s['index'] == 'INDEX0']
    cl1_units = [s for s in custom_label_structures if s['index'] == 'INDEX1']

    ops1 = []

    # 1. ROOT SUBDIVISION
    root_op = create_listing_group_subdivision(
        client=client,
        customer_id=customer_id,
        ad_group_id=str(ad_group_id),
        parent_ad_group_criterion_resource_name=None,
        listing_dimension_info=None
    )
    root_tmp = root_op.create.resource_name
    ops1.append(root_op)

    # Determine hierarchy based on SUBDIVISIONS (not units)
    current_parent_tmp = root_tmp
    deepest_subdivision_tmp = root_tmp
    result_index_map = [0]  # Track which result index is which subdivision

    # If CL0 or CL1 subdivisions exist, rebuild them
    if cl0_subdivisions:
        # Build CL0 level
        cl0_subdiv = cl0_subdivisions[0]

        # Create CL0 subdivision
        dim_cl0 = client.get_type("ListingDimensionInfo")
        dim_cl0.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX0
        dim_cl0.product_custom_attribute.value = cl0_subdiv['value']

        cl0_subdivision_op = create_listing_group_subdivision(
            client=client,
            customer_id=customer_id,
            ad_group_id=str(ad_group_id),
            parent_ad_group_criterion_resource_name=current_parent_tmp,
            listing_dimension_info=dim_cl0
        )
        cl0_subdivision_tmp = cl0_subdivision_op.create.resource_name
        ops1.append(cl0_subdivision_op)
        result_index_map.append(len(ops1) - 1)  # Track CL0 subdivision index

        # Add CL0 OTHERS (negative)
        dim_cl0_others = client.get_type("ListingDimensionInfo")
        dim_cl0_others.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX0
        ops1.append(
            create_listing_group_unit_biddable(
                client=client,
                customer_id=customer_id,
                ad_group_id=str(ad_group_id),
                parent_ad_group_criterion_resource_name=current_parent_tmp,
                listing_dimension_info=dim_cl0_others,
                targeting_negative=True,
                cpc_bid_micros=None
            )
        )

        current_parent_tmp = cl0_subdivision_tmp
        deepest_subdivision_tmp = cl0_subdivision_tmp

    if cl1_subdivisions:
        # Build CL1 level under current parent
        cl1_subdiv = cl1_subdivisions[0]

        # Create CL1 subdivision
        dim_cl1 = client.get_type("ListingDimensionInfo")
        dim_cl1.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX1
        dim_cl1.product_custom_attribute.value = cl1_subdiv['value']

        cl1_subdivision_op = create_listing_group_subdivision(
            client=client,
            customer_id=customer_id,
            ad_group_id=str(ad_group_id),
            parent_ad_group_criterion_resource_name=current_parent_tmp,
            listing_dimension_info=dim_cl1
        )
        cl1_subdivision_tmp = cl1_subdivision_op.create.resource_name
        ops1.append(cl1_subdivision_op)
        result_index_map.append(len(ops1) - 1)  # Track CL1 subdivision index

        # Add CL1 OTHERS (negative)
        dim_cl1_others = client.get_type("ListingDimensionInfo")
        dim_cl1_others.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX1
        ops1.append(
            create_listing_group_unit_biddable(
                client=client,
                customer_id=customer_id,
                ad_group_id=str(ad_group_id),
                parent_ad_group_criterion_resource_name=current_parent_tmp,
                listing_dimension_info=dim_cl1_others,
                targeting_negative=True,
                cpc_bid_micros=None
            )
        )

        current_parent_tmp = cl1_subdivision_tmp
        deepest_subdivision_tmp = cl1_subdivision_tmp

    # If there are CL0 units under the deepest subdivision, we need to convert them to subdivisions
    # and nest CL3 under them (following pattern from rebuild_tree_with_label_and_item_ids)
    if cl0_units:
        # For each CL0 unit, create as subdivision and add CL3 under it
        for unit in cl0_units:
            # Create CL0 subdivision (instead of unit)
            dim_cl0_subdiv = client.get_type("ListingDimensionInfo")
            dim_cl0_subdiv.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX0
            dim_cl0_subdiv.product_custom_attribute.value = unit['value']

            cl0_unit_subdivision_op = create_listing_group_subdivision(
                client=client,
                customer_id=customer_id,
                ad_group_id=str(ad_group_id),
                parent_ad_group_criterion_resource_name=deepest_subdivision_tmp,
                listing_dimension_info=dim_cl0_subdiv
            )
            cl0_unit_subdivision_tmp = cl0_unit_subdivision_op.create.resource_name
            ops1.append(cl0_unit_subdivision_op)

            # Add CL3 OTHERS under this CL0 subdivision
            dim_cl3_others = client.get_type("ListingDimensionInfo")
            dim_cl3_others.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX3
            ops1.append(
                create_listing_group_unit_biddable(
                    client=client,
                    customer_id=customer_id,
                    ad_group_id=str(ad_group_id),
                    parent_ad_group_criterion_resource_name=cl0_unit_subdivision_tmp,
                    listing_dimension_info=dim_cl3_others,
                    targeting_negative=False,
                    cpc_bid_micros=unit['bid_micros']  # Use the original bid from CL0 unit
                )
            )

        # Add CL0 OTHERS (negative) under deepest subdivision
        dim_cl0_others = client.get_type("ListingDimensionInfo")
        dim_cl0_others.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX0
        ops1.append(
            create_listing_group_unit_biddable(
                client=client,
                customer_id=customer_id,
                ad_group_id=str(ad_group_id),
                parent_ad_group_criterion_resource_name=deepest_subdivision_tmp,
                listing_dimension_info=dim_cl0_others,
                targeting_negative=True,
                cpc_bid_micros=None
            )
        )
    else:
        # No CL0 units - just add CL3 directly under deepest subdivision
        dim_cl3_others = client.get_type("ListingDimensionInfo")
        dim_cl3_others.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX3
        ops1.append(
            create_listing_group_unit_biddable(
                client=client,
                customer_id=customer_id,
                ad_group_id=str(ad_group_id),
                parent_ad_group_criterion_resource_name=deepest_subdivision_tmp,
                listing_dimension_info=dim_cl3_others,
                targeting_negative=False,
                cpc_bid_micros=default_bid_micros
            )
        )

    # Execute first mutate
    try:
        resp1 = agc_service.mutate_ad_group_criteria(customer_id=customer_id, operations=ops1)
    except Exception as e:
        print(f"   ❌ Error rebuilding tree: {e}")
        raise  # Re-raise exception so calling code can handle it properly

    # No sleep needed - API operations are synchronous

    # MUTATE 2: Add shop exclusion under each CL0 subdivision (if they exist)
    ops2 = []

    if cl0_units:
        # We created CL0 subdivisions - need to find their actual resource names and add exclusion to each
        # Calculate the index of the first CL0 subdivision in results
        base_index = 1  # Start after ROOT
        if cl0_subdivisions:
            base_index += 2  # CL0 subdivision + CL0 OTHERS
        if cl1_subdivisions:
            base_index += 2  # CL1 subdivision + CL1 OTHERS

        # Each CL0 unit became: CL0 subdivision + CL3 OTHERS
        # So CL0 subdivisions are at: base_index, base_index+2, base_index+4, ...
        for i, unit in enumerate(cl0_units):
            cl0_subdivision_actual = resp1.results[base_index + (i * 2)].resource_name

            dim_shop = client.get_type("ListingDimensionInfo")
            dim_shop.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX3
            dim_shop.product_custom_attribute.value = shop_name
            ops2.append(
                create_listing_group_unit_biddable(
                    client=client,
                    customer_id=customer_id,
                    ad_group_id=str(ad_group_id),
                    parent_ad_group_criterion_resource_name=cl0_subdivision_actual,
                    listing_dimension_info=dim_shop,
                    targeting_negative=True,
                    cpc_bid_micros=None
                )
            )
    else:
        # No CL0 units - add exclusion under the deepest subdivision (CL1 or ROOT)
        if cl1_subdivisions:
            if cl0_subdivisions:
                deepest_subdivision_actual = resp1.results[3].resource_name  # ROOT, CL0 subdivision, CL0 OTHERS, CL1 subdivision
            else:
                deepest_subdivision_actual = resp1.results[1].resource_name  # ROOT, CL1 subdivision
        elif cl0_subdivisions:
            deepest_subdivision_actual = resp1.results[1].resource_name  # ROOT, CL0 subdivision
        else:
            deepest_subdivision_actual = resp1.results[0].resource_name  # ROOT

        dim_shop = client.get_type("ListingDimensionInfo")
        dim_shop.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX3
        dim_shop.product_custom_attribute.value = shop_name
        ops2.append(
            create_listing_group_unit_biddable(
                client=client,
                customer_id=customer_id,
                ad_group_id=str(ad_group_id),
                parent_ad_group_criterion_resource_name=deepest_subdivision_actual,
                listing_dimension_info=dim_shop,
                targeting_negative=True,
                cpc_bid_micros=None
            )
        )

    try:
        agc_service.mutate_ad_group_criteria(customer_id=customer_id, operations=ops2)
    except Exception as e:
        print(f"   ❌ Error adding shop exclusion: {e}")
        raise  # Re-raise exception so calling code can handle it properly

    preserved_count = len(custom_label_structures)
    if preserved_count > 0:
        print(f"   ✅ Tree rebuilt: EXCLUDING shop '{shop_name}', preserved {preserved_count} existing structure(s)")
    else:
        print(f"   ✅ Tree rebuilt: EXCLUDING shop '{shop_name}', showing all others.")


def build_listing_tree_for_inclusion(
    client: GoogleAdsClient,
    customer_id: str,
    ad_group_id: str,
    custom_label_1: str,
    maincat_id: str,
    shop_name: str,
    default_bid_micros: int = DEFAULT_BID_MICROS
):
    """
    Build listing tree for inclusion logic (NEW STRUCTURE):

    Tree structure:
    ROOT (subdivision)
    ├─ Custom Label 3 = shop_name (subdivision)
    │  ├─ Custom Label 3 OTHERS (unit, negative)
    │  └─ Custom Label 4 = maincat_id (subdivision)
    │     ├─ Custom Label 4 OTHERS (unit, negative)
    │     ├─ Custom Label 1 = custom_label_1 (unit, biddable, positive) ← Added in MUTATE 2
    │     └─ Custom Label 1 OTHERS (unit, negative) ← Created in MUTATE 1 with temp name
    └─ Custom Label 3 OTHERS (unit, negative)

    CRITICAL: Google Ads requires that when you create a SUBDIVISION, you must
    provide its OTHERS case in the SAME mutate operation using temporary resource names.

    MUTATE 1: Create root + CL3 subdivision + CL4 subdivision + all OTHERS cases
    MUTATE 2: Add positive custom_label_1 target under maincat subdivision

    Args:
        client: Google Ads client
        customer_id: Customer ID
        ad_group_id: Ad group ID
        custom_label_1: Custom label 1 value (a/b/c)
        maincat_id: Main category ID to target (custom label 4)
        shop_name: Shop name to target (custom label 3)
        default_bid_micros: Default bid in micros
    """
    print(f"      Building tree: Shop={shop_name}, Maincat ID={maincat_id}, CL1={custom_label_1}")

    # Remove existing tree if any
    safe_remove_entire_listing_tree(client, customer_id, ad_group_id)
    # No sleep needed - API operations are synchronous

    agc_service = client.get_service("AdGroupCriterionService")

    # MUTATE 1: Create root + CL3 subdivision + CL4 subdivision + all OTHERS cases
    # CRITICAL: When creating a subdivision, you MUST provide its OTHERS case in the SAME mutate
    ops1 = []

    # 1. ROOT SUBDIVISION
    root_op = create_listing_group_subdivision(
        client=client,
        customer_id=customer_id,
        ad_group_id=ad_group_id,
        parent_ad_group_criterion_resource_name=None,
        listing_dimension_info=None
    )
    root_tmp = root_op.create.resource_name
    ops1.append(root_op)

    # 2. Custom Label 3 subdivision (Custom Label 3 = shop_name)
    dim_cl3 = client.get_type("ListingDimensionInfo")
    dim_cl3.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX3  # INDEX3 = Custom Label 3
    dim_cl3.product_custom_attribute.value = str(shop_name)

    cl3_subdivision_op = create_listing_group_subdivision(
        client=client,
        customer_id=customer_id,
        ad_group_id=ad_group_id,
        parent_ad_group_criterion_resource_name=root_tmp,
        listing_dimension_info=dim_cl3
    )
    cl3_subdivision_tmp = cl3_subdivision_op.create.resource_name
    ops1.append(cl3_subdivision_op)

    # 3. Custom Label 3 OTHERS (negative - blocks other shops)
    # This is a child of ROOT and satisfies the OTHERS requirement for root
    dim_cl3_others = client.get_type("ListingDimensionInfo")
    dim_cl3_others.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX3
    # Don't set value - OTHERS case

    ops1.append(
        create_listing_group_unit_biddable(
            client=client,
            customer_id=customer_id,
            ad_group_id=ad_group_id,
            parent_ad_group_criterion_resource_name=root_tmp,
            listing_dimension_info=dim_cl3_others,
            targeting_negative=True,  # NEGATIVE
            cpc_bid_micros=None
        )
    )

    # 4. Maincat ID subdivision (Custom Label 4 = maincat_id)
    # This is a child of CL3 subdivision (using TEMP name)
    dim_maincat = client.get_type("ListingDimensionInfo")
    dim_maincat.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX4  # INDEX4 = Custom Label 4
    dim_maincat.product_custom_attribute.value = str(maincat_id)

    maincat_subdivision_op = create_listing_group_subdivision(
        client=client,
        customer_id=customer_id,
        ad_group_id=ad_group_id,
        parent_ad_group_criterion_resource_name=cl3_subdivision_tmp,  # Under CL3, not ROOT!
        listing_dimension_info=dim_maincat
    )
    maincat_subdivision_tmp = maincat_subdivision_op.create.resource_name
    ops1.append(maincat_subdivision_op)

    # 5. Custom Label 4 OTHERS (negative - blocks other categories)
    # This is a child of CL3 subdivision and satisfies the OTHERS requirement for CL3
    dim_cl4_others = client.get_type("ListingDimensionInfo")
    dim_cl4_others.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX4
    # Don't set value - OTHERS case

    ops1.append(
        create_listing_group_unit_biddable(
            client=client,
            customer_id=customer_id,
            ad_group_id=ad_group_id,
            parent_ad_group_criterion_resource_name=cl3_subdivision_tmp,  # Child of CL3
            listing_dimension_info=dim_cl4_others,
            targeting_negative=True,  # NEGATIVE
            cpc_bid_micros=None
        )
    )

    # 6. Custom Label 1 OTHERS (negative - blocks other CL1 values)
    # This is a child of maincat_id subdivision (using TEMP name) and satisfies its OTHERS requirement
    dim_cl1_others = client.get_type("ListingDimensionInfo")
    dim_cl1_others.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX1
    # Don't set value - OTHERS case

    ops1.append(
        create_listing_group_unit_biddable(
            client=client,
            customer_id=customer_id,
            ad_group_id=ad_group_id,
            parent_ad_group_criterion_resource_name=maincat_subdivision_tmp,  # Using TEMP name!
            listing_dimension_info=dim_cl1_others,
            targeting_negative=True,  # NEGATIVE - block other CL1 values
            cpc_bid_micros=None
        )
    )

    # Execute first mutate
    resp1 = agc_service.mutate_ad_group_criteria(customer_id=customer_id, operations=ops1)
    maincat_subdivision_actual = resp1.results[3].resource_name  # Fourth result is maincat subdivision (0=root, 1=cl3, 2=cl3_others, 3=cl4)
    # No sleep needed - API operations are synchronous

    # MUTATE 2: Under maincat_id, add the positive custom_label_1 target
    # Note: CL1 OTHERS was already created in MUTATE 1
    ops2 = []

    # Custom Label 1 (Custom Label 1 = custom_label_1) - POSITIVE target
    dim_cl1 = client.get_type("ListingDimensionInfo")
    dim_cl1.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX1  # INDEX1 = Custom Label 1
    dim_cl1.product_custom_attribute.value = str(custom_label_1)

    ops2.append(
        create_listing_group_unit_biddable(
            client=client,
            customer_id=customer_id,
            ad_group_id=ad_group_id,
            parent_ad_group_criterion_resource_name=maincat_subdivision_actual,
            listing_dimension_info=dim_cl1,
            targeting_negative=False,  # POSITIVE - target this CL1 value
            cpc_bid_micros=10_000  # 1 cent = €0.01 = 10,000 micros
        )
    )

    # Execute second mutate
    agc_service.mutate_ad_group_criteria(customer_id=customer_id, operations=ops2)
    print(f"      ✅ Tree created: Shop '{shop_name}' → Maincat '{maincat_id}' → CL1 '{custom_label_1}'")


# ============================================================================
# EXCEL PROCESSING
# ============================================================================

def process_inclusion_sheet(
    client: GoogleAdsClient,
    workbook: openpyxl.Workbook,
    customer_id: str
):
    """
    Process the 'toevoegen' (inclusion) sheet.

    Excel columns:
    A. Shop name
    B. Shop ID
    C. maincat
    D. maincat_id
    E. custom label 1
    F. budget (daily budget in EUR)
    G. Status (TRUE/FALSE) - updated by script

    Groups rows by unique combination of (maincat, custom_label_1) ONLY.
    For each group:
    1. Create ONE campaign with name: PLA/{maincat} store_{custom_label_1}
       - Uses budget from column F (converted to micros)
       - Applies bid strategy from MCC based on custom_label_1
    2. Create MULTIPLE ad groups (one per unique shop_name in group)
       - Ad group names: PLA/{shop_name}_{custom_label_1}
    3. Build listing tree for EACH ad group:
       - Target maincat_id as custom label 4
       - Subdivide and target shop_name as custom label 3
       - Exclude everything else at both levels
       - Bid: 1 cent (10,000 micros)
    4. Update column G (status) with TRUE/FALSE per row based on shop success

    Args:
        client: Google Ads client
        workbook: Excel workbook
        customer_id: Customer ID
    """
    print(f"\n{'='*70}")
    print(f"PROCESSING INCLUSION SHEET: '{SHEET_INCLUSION}'")
    print(f"{'='*70}\n")

    try:
        sheet = workbook[SHEET_INCLUSION]
    except KeyError:
        print(f"❌ Sheet '{SHEET_INCLUSION}' not found in workbook")
        return

    # Step 1: Read all rows and group by (maincat, custom_label_1) only
    from collections import defaultdict
    groups = defaultdict(list)  # key: (maincat, custom_label_1), value: list of row data

    print("Step 1: Reading and grouping rows...")
    for idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=False), start=2):
        # Check if status column (G) is empty - if so, this is where we start processing
        status_value = row[COL_STATUS].value

        # Skip rows that already have a status (TRUE/FALSE)
        if status_value is not None and status_value != '':
            continue

        shop_name = row[COL_SHOP_NAME].value
        shop_id = row[COL_SHOP_ID].value
        maincat = row[COL_MAINCAT].value
        maincat_id = row[COL_MAINCAT_ID].value
        custom_label_1 = row[COL_CUSTOM_LABEL_1].value
        budget = row[COL_BUDGET].value

        # Validate required fields
        if not shop_name or not maincat or not maincat_id or not custom_label_1:
            print(f"   ⚠️  [Row {idx}] Missing required fields (shop_name/maincat/maincat_id/custom_label_1), skipping")
            row[COL_STATUS].value = False
            # Only write to error column if it exists
            if len(row) > COL_ERROR:
                row[COL_ERROR].value = "Missing required fields (shop_name/maincat/maincat_id/custom_label_1)"
            continue

        # NEW: Group by (maincat, custom_label_1) only - multiple shops per campaign
        group_key = (maincat, custom_label_1)

        # Store row data
        groups[group_key].append({
            'row_idx': idx,
            'row_obj': row,
            'shop_name': shop_name,
            'shop_id': shop_id,
            'maincat': maincat,
            'maincat_id': maincat_id,
            'custom_label_1': custom_label_1,
            'budget': budget
        })

    print(f"   Found {len(groups)} unique group(s) to process\n")

    # Step 2: Process each group
    total_groups = len(groups)
    successful_groups = 0

    for group_idx, (group_key, rows_in_group) in enumerate(groups.items(), start=1):
        maincat, custom_label_1 = group_key

        print(f"\n{'─'*70}")
        print(f"GROUP {group_idx}/{total_groups}: {maincat} | {custom_label_1}")
        print(f"   Rows in group: {len(rows_in_group)}")
        print(f"{'─'*70}")

        # Get metadata from first row (all rows in group share same maincat, maincat_id, budget)
        first_row = rows_in_group[0]
        maincat_id = first_row['maincat_id']
        budget_value = first_row['budget']

        # Get unique shops in this group
        unique_shops = {}  # shop_name -> shop_id mapping
        for row_data in rows_in_group:
            unique_shops[row_data['shop_name']] = row_data['shop_id']

        print(f"   Maincat ID: {maincat_id}")
        print(f"   Budget: {budget_value} EUR")
        print(f"   Unique shops in group: {len(unique_shops)}")

        try:
            # NEW: Build campaign name: PLA/{maincat} store_{custom_label_1}
            campaign_name = f"PLA/{maincat} store_{custom_label_1}"
            print(f"\n   Step 1: Checking for existing campaign or creating new: {campaign_name}")

            # Campaign configuration
            merchant_center_account_id = 140784594  # Merchant Center ID
            budget_name = f"Budget_{campaign_name}"
            tracking_template = ""  # Not needed
            country = "NL"  # Always Netherlands

            # Convert budget from EUR to micros (EUR * 1,000,000)
            # Default to 10 EUR if budget is missing or invalid
            try:
                budget_micros = int(float(budget_value) * 1_000_000) if budget_value else 10_000_000
            except (ValueError, TypeError):
                print(f"   ⚠️  Invalid budget value '{budget_value}', using default 10 EUR")
                budget_micros = 10_000_000

            # Get bid strategy based on custom label 1 (from MCC account)
            bid_strategy_resource_name = None
            if custom_label_1 in BID_STRATEGY_MAPPING:
                bid_strategy_name = BID_STRATEGY_MAPPING[custom_label_1]
                print(f"   Looking up bid strategy: {bid_strategy_name} (in MCC account)")
                bid_strategy_resource_name = get_bid_strategy_by_name(
                    client=client,
                    customer_id=MCC_ACCOUNT_ID,  # Search in MCC account
                    strategy_name=bid_strategy_name
                )

            # Use first shop's ID for campaign metadata
            first_shop_id = list(unique_shops.values())[0]
            first_shop_name = list(unique_shops.keys())[0]

            campaign_resource_name = add_standard_shopping_campaign(
                client=client,
                customer_id=customer_id,
                merchant_center_account_id=merchant_center_account_id,
                campaign_name=campaign_name,
                budget_name=budget_name,
                tracking_template=tracking_template,
                country=country,
                shopid=first_shop_id,
                shopname=first_shop_name,
                label=custom_label_1,
                budget=budget_micros,
                bidding_strategy_resource_name=bid_strategy_resource_name
            )

            if not campaign_resource_name:
                raise Exception("Failed to create/find campaign")

            print(f"   Campaign resource: {campaign_resource_name}")

            # NEW: Check/create multiple ad groups - one for each unique shop
            print(f"\n   Step 2: Processing ad groups for {len(unique_shops)} shop(s)...")
            shops_processed_successfully = []
            shop_errors = {}  # Track errors per shop

            for shop_idx, (shop_name, shop_id) in enumerate(unique_shops.items(), start=1):
                print(f"\n   ──── Shop {shop_idx}/{len(unique_shops)}: {shop_name} ────")

                try:
                    # Build ad group name: PLA/{shop_name}_{custom_label_1}
                    ad_group_name = f"PLA/{shop_name}_{custom_label_1}"
                    print(f"      Checking/creating ad group: {ad_group_name}")

                    ad_group_resource_name, was_created = add_shopping_ad_group(
                        client=client,
                        customer_id=customer_id,
                        campaign_resource_name=campaign_resource_name,
                        ad_group_name=ad_group_name,
                        campaign_name=campaign_name
                    )

                    if not ad_group_resource_name:
                        raise Exception(f"Failed to create/find ad group for {shop_name}")

                    print(f"      ✅ Ad group ready: {ad_group_resource_name}")

                    # Extract ad group ID from resource name
                    ad_group_id = ad_group_resource_name.split('/')[-1]

                    # Build listing tree for this shop
                    print(f"      Building listing tree...")
                    build_listing_tree_for_inclusion(
                        client=client,
                        customer_id=customer_id,
                        ad_group_id=ad_group_id,
                        custom_label_1=custom_label_1,
                        maincat_id=maincat_id,
                        shop_name=shop_name,
                        default_bid_micros=DEFAULT_BID_MICROS
                    )

                    print(f"      ✅ Listing tree created for {shop_name}")

                    # Create shopping product ad in the ad group
                    print(f"      Creating shopping product ad...")
                    ad_resource_name = add_shopping_product_ad(
                        client=client,
                        customer_id=customer_id,
                        ad_group_resource_name=ad_group_resource_name
                    )

                    if not ad_resource_name:
                        print(f"      ⚠️  Warning: Failed to create shopping ad for {shop_name}")

                    shops_processed_successfully.append(shop_name)

                    # Small delay to avoid concurrent modification issues
                    time.sleep(1)

                except Exception as e:
                    error_msg = str(e)
                    print(f"      ❌ Failed to process shop {shop_name}: {error_msg}")
                    shop_errors[shop_name] = error_msg
                    # Continue with next shop instead of failing entire group

            # Mark rows as successful/failed based on their shop
            for row_data in rows_in_group:
                if row_data['shop_name'] in shops_processed_successfully:
                    row_data['row_obj'][COL_STATUS].value = True
                    # Clear error message on success (only if column exists)
                    if len(row_data['row_obj']) > COL_ERROR:
                        row_data['row_obj'][COL_ERROR].value = ""
                else:
                    row_data['row_obj'][COL_STATUS].value = False
                    # Add error message if available (only if column exists)
                    if len(row_data['row_obj']) > COL_ERROR:
                        if row_data['shop_name'] in shop_errors:
                            row_data['row_obj'][COL_ERROR].value = shop_errors[row_data['shop_name']]
                        else:
                            row_data['row_obj'][COL_ERROR].value = "Failed to process shop"

            if len(shops_processed_successfully) > 0:
                successful_groups += 1
                print(f"\n   ✅ GROUP {group_idx} COMPLETED: {len(shops_processed_successfully)}/{len(unique_shops)} shops processed")

        except Exception as e:
            error_msg = str(e)
            print(f"\n   ❌ GROUP {group_idx} FAILED: {error_msg}")
            # Mark all rows in this group as failed
            for row_data in rows_in_group:
                row_data['row_obj'][COL_STATUS].value = False
                # Only write error message if column exists
                if len(row_data['row_obj']) > COL_ERROR:
                    row_data['row_obj'][COL_ERROR].value = f"Group failed: {error_msg}"

    print(f"\n{'='*70}")
    print(f"INCLUSION SHEET SUMMARY: {successful_groups}/{total_groups} groups processed successfully")
    print(f"{'='*70}\n")


def _process_single_exclusion_row(
    row_data: dict,
    client: GoogleAdsClient,
    customer_id: str,
    rate_limit_seconds: float
) -> dict:
    """
    Process a single exclusion row (worker function for parallel processing).

    Args:
        row_data: Dict containing row information
        client: Google Ads client
        customer_id: Customer ID
        rate_limit_seconds: Rate limit delay

    Returns:
        Dict with results: {'success': bool, 'error': str or None}
    """
    idx = row_data['idx']
    shop_name = row_data['shop_name']
    cat_uitsluiten = row_data['cat_uitsluiten']
    custom_label_1 = row_data['custom_label_1']

    print(f"\n[Row {idx}] Processing exclusion for shop: {shop_name}")
    print(f"         Category: {cat_uitsluiten}, Custom Label 1: {custom_label_1}")

    # Build campaign name pattern
    campaign_pattern = f"PLA/{cat_uitsluiten}_{custom_label_1}"
    print(f"   Searching for campaign+ad group: {campaign_pattern}")

    # Use combined lookup (saves 1 API call)
    result = get_campaign_and_ad_group_by_pattern(client, customer_id, campaign_pattern)
    if not result:
        print(f"   ❌ Campaign or ad group not found")
        return {
            'success': False,
            'error': f"Campaign not found: {campaign_pattern}"
        }

    campaign = result['campaign']
    ad_group = result['ad_group']

    print(f"   ✅ Found campaign: {campaign['name']} (ID: {campaign['id']})")
    print(f"   ✅ Found ad group: {ad_group['name']} (ID: {ad_group['id']})")

    # Rebuild tree with shop name exclusion
    try:
        rebuild_tree_with_custom_label_3_exclusion(
            client=client,
            customer_id=customer_id,
            ad_group_id=ad_group['id'],
            shop_name=shop_name,
            default_bid_micros=DEFAULT_BID_MICROS
        )
        print(f"   ✅ SUCCESS - Row {idx} completed")

        # Rate limiting ONLY after successful processing
        if rate_limit_seconds > 0:
            time.sleep(rate_limit_seconds)

        return {'success': True, 'error': None}

    except Exception as e:
        error_msg = str(e)
        print(f"   ❌ Error rebuilding tree: {error_msg}")
        return {
            'success': False,
            'error': f"Error rebuilding tree: {error_msg[:500]}"
        }


def process_exclusion_sheet(
    client: GoogleAdsClient,
    workbook: openpyxl.Workbook,
    customer_id: str,
    save_interval: int = 50,
    rate_limit_seconds: float = 0.05
):
    """
    Process the 'uitsluiten' (exclusion) sheet with PARALLEL PROCESSING.

    Uses ThreadPoolExecutor with 15 workers for ~8x speedup (Phase 3 optimized).

    For each row:
    1. Retrieve campaign AND ad group by pattern (single API call)
    2. Rebuild tree to EXCLUDE shop name (custom label 3)
    3. Update column F with TRUE/FALSE

    Args:
        client: Google Ads client
        workbook: Excel workbook
        customer_id: Customer ID
        save_interval: Save workbook every N campaigns (default: 50)
        rate_limit_seconds: Delay per worker after successful processing (default: 0.05)
    """
    print(f"\n{'='*70}")
    print(f"PROCESSING EXCLUSION SHEET: '{SHEET_EXCLUSION}' (PARALLEL MODE)")
    print(f"{'='*70}")
    print(f"  Workers: 15 parallel threads (Phase 3 optimized)")
    print(f"  Save interval: Every {save_interval} campaigns")
    print(f"  Rate limit: {rate_limit_seconds}s delay per worker")
    print(f"{'='*70}\n")

    try:
        sheet = workbook[SHEET_EXCLUSION]
    except KeyError:
        print(f"❌ Sheet '{SHEET_EXCLUSION}' not found in workbook")
        return

    # Step 1: Collect all rows to process
    rows_to_process = []

    for idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=False), start=2):
        # Skip rows that already have a status
        status_value = row[COL_EX_STATUS].value
        if status_value is not None and status_value != '':
            continue

        # Extract values
        shop_name = row[COL_EX_SHOP_NAME].value
        cat_uitsluiten = row[COL_EX_CAT_UITSLUITEN].value
        custom_label_1 = row[COL_EX_CUSTOM_LABEL_1].value

        # Validate required fields
        if not shop_name or not cat_uitsluiten or not custom_label_1:
            row[COL_EX_STATUS].value = False
            if len(row) > COL_EX_ERROR:
                row[COL_EX_ERROR].value = "Missing required fields (shop_name/cat_uitsluiten/custom_label_1)"
            continue

        rows_to_process.append({
            'idx': idx,
            'row_obj': row,
            'shop_name': shop_name,
            'cat_uitsluiten': cat_uitsluiten,
            'custom_label_1': custom_label_1
        })

    total_rows = len(rows_to_process)
    print(f"Found {total_rows} row(s) to process\n")

    if total_rows == 0:
        print("✅ No rows to process")
        return

    # Step 2: Process rows in parallel using ThreadPoolExecutor
    success_count = 0
    processed_count = 0
    lock = threading.Lock()  # Thread-safe counter and Excel writes

    def process_and_update(row_data):
        """Wrapper that processes and updates Excel (thread-safe)"""
        nonlocal success_count, processed_count

        result = _process_single_exclusion_row(
            row_data=row_data,
            client=client,
            customer_id=customer_id,
            rate_limit_seconds=rate_limit_seconds
        )

        # Update Excel row (thread-safe)
        with lock:
            row_obj = row_data['row_obj']

            if result['success']:
                row_obj[COL_EX_STATUS].value = True
                if len(row_obj) > COL_EX_ERROR:
                    row_obj[COL_EX_ERROR].value = ""
                success_count += 1
            else:
                row_obj[COL_EX_STATUS].value = False
                if len(row_obj) > COL_EX_ERROR:
                    row_obj[COL_EX_ERROR].value = result['error']

            processed_count += 1

            # Incremental save (thread-safe)
            if processed_count % save_interval == 0:
                print(f"\n   💾 Saving progress... ({success_count}/{processed_count} successful so far)")
                try:
                    workbook.save(EXCEL_FILE_PATH)
                    print(f"   ✅ Progress saved successfully")
                except Exception as save_error:
                    print(f"   ⚠️  Error saving file: {save_error}")

        return result

    # Execute with ThreadPoolExecutor (15 workers - Phase 3 optimized)
    with ThreadPoolExecutor(max_workers=15) as executor:
        # Submit all tasks
        futures = [executor.submit(process_and_update, row_data) for row_data in rows_to_process]

        # Wait for all to complete
        for future in as_completed(futures):
            try:
                future.result()  # Raise any exceptions that occurred
            except Exception as e:
                print(f"   ⚠️  Worker exception: {e}")

    # Final save
    print(f"\n   💾 Final save...")
    try:
        workbook.save(EXCEL_FILE_PATH)
        print(f"   ✅ Final save successful")
    except Exception as save_error:
        print(f"   ⚠️  Error on final save: {save_error}")

    print(f"\n{'='*70}")
    print(f"EXCLUSION SHEET SUMMARY: {success_count}/{total_rows} rows processed successfully")
    print(f"{'='*70}\n")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """
    Main execution function.
    """
    print(f"\n{'='*70}")
    print("DMA SHOP CAMPAIGNS PROCESSOR")
    print(f"{'='*70}")
    print(f"Operating System: {platform.system()}")
    print(f"Customer ID: {CUSTOMER_ID}")
    print(f"Excel File: {EXCEL_FILE_PATH}")
    print(f"{'='*70}\n")

    # Initialize Google Ads client
    client = initialize_google_ads_client()

    # Load Excel workbook
    print(f"Loading Excel file: {EXCEL_FILE_PATH}")
    try:
        workbook = load_workbook(EXCEL_FILE_PATH)
        print(f"✅ Excel file loaded successfully")
        print(f"   Available sheets: {workbook.sheetnames}")
    except Exception as e:
        print(f"❌ Error loading Excel file: {e}")
        sys.exit(1)

    # Process inclusion sheet
    try:
        process_inclusion_sheet(client, workbook, CUSTOMER_ID)
    except Exception as e:
        print(f"❌ Error processing inclusion sheet: {e}")

    '''
    # Process exclusion sheet
    try:
        process_exclusion_sheet(client, workbook, CUSTOMER_ID)
    except Exception as e:
        print(f"❌ Error processing exclusion sheet: {e}")
    '''

    # Save workbook with updates
    print(f"\n{'='*70}")
    print("SAVING RESULTS")
    print(f"{'='*70}")
    try:
        workbook.save(EXCEL_FILE_PATH)
        print(f"✅ Excel file saved successfully: {EXCEL_FILE_PATH}")
    except Exception as e:
        print(f"❌ Error saving Excel file: {e}")
        print(f"   You may need to close the file if it's open in Excel")

    print(f"\n{'='*70}")
    print("PROCESSING COMPLETE")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
