"""
Inspect ad group 189081353036 to see tree structure with item ID exclusions.
"""
from campaign_processor import initialize_google_ads_client, CUSTOMER_ID

def inspect_tree_structure(client, customer_id, ad_group_id):
    """Inspect and display the complete tree structure"""
    ga_service = client.get_service("GoogleAdsService")

    query = f"""
        SELECT
            ad_group_criterion.resource_name,
            ad_group_criterion.criterion_id,
            ad_group_criterion.listing_group.type,
            ad_group_criterion.listing_group.parent_ad_group_criterion,
            ad_group_criterion.listing_group.case_value.product_item_id.value,
            ad_group_criterion.listing_group.case_value.product_custom_attribute.index,
            ad_group_criterion.listing_group.case_value.product_custom_attribute.value,
            ad_group_criterion.negative,
            ad_group_criterion.cpc_bid_micros
        FROM ad_group_criterion
        WHERE ad_group_criterion.ad_group = 'customers/{customer_id}/adGroups/{ad_group_id}'
            AND ad_group_criterion.type = 'LISTING_GROUP'
            AND ad_group_criterion.status != 'REMOVED'
    """

    try:
        response = ga_service.search(customer_id=customer_id, query=query)
        nodes = []

        for row in response:
            lg = row.ad_group_criterion.listing_group
            criterion_id = row.ad_group_criterion.criterion_id

            # Extract dimension info
            dimension_type = None
            dimension_value = None

            # Check for Item ID
            if lg.case_value.product_item_id.value:
                dimension_type = "ITEM_ID"
                dimension_value = lg.case_value.product_item_id.value
            # Check for Custom Attribute (CL0-CL4)
            elif lg.case_value.product_custom_attribute.index:
                index = lg.case_value.product_custom_attribute.index.name
                dimension_type = index
                dimension_value = lg.case_value.product_custom_attribute.value if lg.case_value.product_custom_attribute.value else "OTHERS"

            nodes.append({
                'criterion_id': criterion_id,
                'resource_name': row.ad_group_criterion.resource_name,
                'type': lg.type_.name,
                'parent': lg.parent_ad_group_criterion if lg.parent_ad_group_criterion else None,
                'dimension_type': dimension_type,
                'dimension_value': dimension_value,
                'negative': row.ad_group_criterion.negative,
                'bid': row.ad_group_criterion.cpc_bid_micros
            })

        return nodes
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return []

def print_tree_hierarchy(nodes):
    """Print tree in hierarchical format"""
    # Create lookup by resource name
    node_map = {node['resource_name']: node for node in nodes}

    # Find root
    root = None
    for node in nodes:
        if node['parent'] is None:
            root = node
            break

    if not root:
        print("No root node found!")
        return

    def print_node(node, indent=0):
        prefix = "  " * indent
        neg_str = "NEG" if node['negative'] else "POS"
        bid_str = f"${node['bid']/1_000_000:.2f}" if node['bid'] else "no bid"

        if node['dimension_type']:
            print(f"{prefix}├─ {node['type']:<12} {node['dimension_type']}={node['dimension_value']:<30} {neg_str:<4} {bid_str}")
        else:
            print(f"{prefix}├─ {node['type']:<12} ROOT{' '*36} {neg_str:<4} {bid_str}")

        # Find children
        children = [n for n in nodes if n['parent'] == node['resource_name']]
        for child in children:
            print_node(child, indent + 1)

    print("\n" + "="*80)
    print("TREE STRUCTURE (HIERARCHICAL)")
    print("="*80)
    print_node(root)


def main():
    ad_group_id = 189081353036
    campaign_id = 21078840897

    print("="*80)
    print(f"INSPECTING AD GROUP {ad_group_id} IN CAMPAIGN {campaign_id}")
    print("="*80)

    client = initialize_google_ads_client()

    # Get ad group name
    ga_service = client.get_service("GoogleAdsService")
    ag_query = f"""
        SELECT
            ad_group.name,
            campaign.name
        FROM ad_group
        WHERE ad_group.id = {ad_group_id}
    """

    result = list(ga_service.search(customer_id=CUSTOMER_ID, query=ag_query))
    if result:
        print(f"\nCampaign: {result[0].campaign.name}")
        print(f"Ad Group: {result[0].ad_group.name}")

    # Inspect tree
    nodes = inspect_tree_structure(client, CUSTOMER_ID, ad_group_id)

    if not nodes:
        print("\nNo listing groups found!")
        return

    print(f"\nFound {len(nodes)} nodes in tree\n")

    # Print as list
    print("="*80)
    print("ALL NODES (LIST VIEW)")
    print("="*80)
    for i, node in enumerate(nodes, 1):
        neg_str = "NEG" if node['negative'] else "POS"
        bid_str = f"${node['bid']/1_000_000:.2f}" if node['bid'] else "no bid"
        dim_str = f"{node['dimension_type']}={node['dimension_value']}" if node['dimension_type'] else "ROOT"
        print(f"{i:2}. {node['type']:<12} {dim_str:<40} {neg_str:<4} {bid_str}")

    # Print as hierarchy
    print_tree_hierarchy(nodes)

    # Count item IDs
    item_id_count = sum(1 for n in nodes if n['dimension_type'] == 'ITEM_ID')
    print("\n" + "="*80)
    print(f"SUMMARY: {item_id_count} item ID exclusions found")
    print("="*80)

if __name__ == "__main__":
    main()
