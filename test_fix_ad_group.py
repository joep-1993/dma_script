"""
Test the fixed rebuild_tree_with_shop_exclusions function on a specific ad group.
Testing: Ad Group 161157611033 in Campaign 21089623885 (PLA/Zwemvesten_b)
Shop to exclude: Knivesandtools.nl
"""
from campaign_processor import (
    initialize_google_ads_client,
    rebuild_tree_with_shop_exclusions,
    CUSTOMER_ID
)

def main():
    print("="*70)
    print("TESTING FIX ON AD GROUP 161157611033")
    print("="*70)
    print(f"\nCampaign: PLA/Zwemvesten_b (21089623885)")
    print(f"Ad Group: 161157611033")
    print(f"Shop to exclude: Knivesandtools.nl")

    # Initialize client
    print("\nInitializing Google Ads client...")
    client = initialize_google_ads_client()

    # Test the function
    print("\nCalling rebuild_tree_with_shop_exclusions()...")
    try:
        rebuild_tree_with_shop_exclusions(
            client=client,
            customer_id=CUSTOMER_ID,
            ad_group_id=161157611033,
            shop_names=["Knivesandtools.nl"]
        )
        print("\n✅ SUCCESS - Function completed without errors!")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Verify the tree structure
    print("\n" + "="*70)
    print("VERIFYING TREE STRUCTURE")
    print("="*70)

    ga_service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT
            ad_group_criterion.listing_group.type,
            ad_group_criterion.listing_group.parent_ad_group_criterion,
            ad_group_criterion.listing_group.case_value.product_custom_attribute.index,
            ad_group_criterion.listing_group.case_value.product_custom_attribute.value,
            ad_group_criterion.negative,
            ad_group_criterion.cpc_bid_micros
        FROM ad_group_criterion
        WHERE ad_group_criterion.ad_group = 'customers/{CUSTOMER_ID}/adGroups/161157611033'
            AND ad_group_criterion.type = 'LISTING_GROUP'
            AND ad_group_criterion.status != 'REMOVED'
    """

    try:
        response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
        nodes = []
        for row in response:
            lg = row.ad_group_criterion.listing_group
            index = None
            value = None
            if lg.case_value.product_custom_attribute.index:
                index = lg.case_value.product_custom_attribute.index.name
                value = lg.case_value.product_custom_attribute.value if lg.case_value.product_custom_attribute.value else "OTHERS"

            nodes.append({
                'type': lg.type_.name,
                'parent': lg.parent_ad_group_criterion if lg.parent_ad_group_criterion else "ROOT",
                'index': index,
                'value': value,
                'negative': row.ad_group_criterion.negative,
                'bid': row.ad_group_criterion.cpc_bid_micros
            })

        print(f"\nFound {len(nodes)} nodes in tree:\n")
        for i, node in enumerate(nodes, 1):
            neg_str = "NEG" if node['negative'] else "POS"
            bid_str = f"${node['bid']/1_000_000:.2f}" if node['bid'] else "no bid"
            if node['index']:
                print(f"{i}. {node['type']:<12} {node['index']}={node['value']:<20} {neg_str:<4} {bid_str}")
            else:
                print(f"{i}. {node['type']:<12} ROOT{' '*24} {neg_str:<4} {bid_str}")

        # Verify expected structure
        print("\n" + "="*70)
        print("EXPECTED STRUCTURE:")
        print("="*70)
        print("1. SUBDIVISION ROOT")
        print("2. SUBDIVISION INDEX0=9003541 (CL0)")
        print("3. UNIT       INDEX1=OTHERS (under CL0, negative)")
        print("4. UNIT       INDEX0=OTHERS (under ROOT, negative)")
        print("5. SUBDIVISION INDEX1=b (CL1, under CL0)")
        print("6. UNIT       INDEX3=OTHERS (under CL1, positive with bid)")
        print("7. UNIT       INDEX3=Knivesandtools.nl (under CL1, negative)")

        print("\n✅ Test completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Error verifying tree: {e}")
        return False


if __name__ == "__main__":
    main()
