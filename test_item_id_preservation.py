"""
Test the item ID preservation logic on ad group 189081353036.
This ad group has 2 item ID exclusions that should be preserved.
"""
from campaign_processor import (
    initialize_google_ads_client,
    rebuild_tree_with_shop_exclusions,
    CUSTOMER_ID
)

def main():
    ad_group_id = 189081353036
    shops_to_exclude = ["TestShop1.nl", "TestShop2.nl"]

    print("="*80)
    print(f"TESTING ITEM ID PRESERVATION ON AD GROUP {ad_group_id}")
    print("="*80)
    print(f"Shops to exclude: {shops_to_exclude}")
    print()

    client = initialize_google_ads_client()

    # Test the function
    try:
        rebuild_tree_with_shop_exclusions(
            client=client,
            customer_id=CUSTOMER_ID,
            ad_group_id=ad_group_id,
            shop_names=shops_to_exclude
        )
        print("\n✅ Function completed successfully!")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Verify tree structure
    print("\n" + "="*80)
    print("VERIFYING TREE STRUCTURE")
    print("="*80)

    ga_service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT
            ad_group_criterion.listing_group.type,
            ad_group_criterion.listing_group.case_value.product_item_id.value,
            ad_group_criterion.listing_group.case_value.product_custom_attribute.index,
            ad_group_criterion.listing_group.case_value.product_custom_attribute.value,
            ad_group_criterion.negative,
            ad_group_criterion.cpc_bid_micros
        FROM ad_group_criterion
        WHERE ad_group_criterion.ad_group = 'customers/{CUSTOMER_ID}/adGroups/{ad_group_id}'
            AND ad_group_criterion.type = 'LISTING_GROUP'
            AND ad_group_criterion.status != 'REMOVED'
    """

    try:
        response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
        nodes = []

        for row in response:
            lg = row.ad_group_criterion.listing_group

            # Determine dimension
            dim_str = "ROOT"
            if lg.case_value.product_item_id.value:
                dim_str = f"ITEM_ID={lg.case_value.product_item_id.value}"
            elif lg.case_value.product_custom_attribute.index:
                index = lg.case_value.product_custom_attribute.index.name
                value = lg.case_value.product_custom_attribute.value if lg.case_value.product_custom_attribute.value else "OTHERS"
                dim_str = f"{index}={value}"

            neg_str = "NEG" if row.ad_group_criterion.negative else "POS"
            bid_str = f"${row.ad_group_criterion.cpc_bid_micros/1_000_000:.2f}" if row.ad_group_criterion.cpc_bid_micros else "no bid"

            nodes.append({
                'type': lg.type_.name,
                'dim': dim_str,
                'neg': neg_str,
                'bid': bid_str
            })

        print(f"\nFound {len(nodes)} nodes:\n")
        for i, node in enumerate(nodes, 1):
            print(f"{i:2}. {node['type']:<12} {node['dim']:<50} {node['neg']:<4} {node['bid']}")

        # Count item IDs
        item_id_count = sum(1 for n in nodes if 'ITEM_ID=' in n['dim'] and n['dim'] != 'ITEM_ID=OTHERS')
        shop_count = sum(1 for n in nodes if 'INDEX3=' in n['dim'] and n['dim'] != 'INDEX3=OTHERS' and n['neg'] == 'NEG')

        print("\n" + "="*80)
        print(f"✅ {shop_count} shop exclusions")
        print(f"✅ {item_id_count} item ID exclusions preserved")
        print("="*80)

        # Verify expected structure
        expected_shops = len(shops_to_exclude)
        expected_items = 2  # We know there are 2 item IDs in this ad group

        if shop_count == expected_shops and item_id_count == expected_items:
            print("\n✅ SUCCESS - All shop and item ID exclusions are present!")
            return True
        else:
            print(f"\n⚠️  WARNING:")
            print(f"   Expected {expected_shops} shops, found {shop_count}")
            print(f"   Expected {expected_items} item IDs, found {item_id_count}")
            return False

    except Exception as e:
        print(f"\n❌ Error verifying tree: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    main()
