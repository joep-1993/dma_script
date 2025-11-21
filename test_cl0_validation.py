"""
Test CL0 validation from Excel diepste_cat_id column.
"""
from campaign_processor import (
    initialize_google_ads_client,
    rebuild_tree_with_shop_exclusions,
    CUSTOMER_ID
)

def main():
    ad_group_id = 161157611033  # PLA/Zwemvesten_b
    campaign_id = 21089623885

    # This ad group has CL0=9003541 in the existing tree
    # We'll test with different CL0 values

    print("="*80)
    print("TESTING CL0 VALIDATION")
    print("="*80)
    print(f"Campaign: PLA/Zwemvesten_b ({campaign_id})")
    print(f"Ad Group: {ad_group_id}")
    print()

    client = initialize_google_ads_client()

    # Test 1: Override CL0 with different value
    print("\n" + "="*80)
    print("TEST: Override CL0 with required value from Excel")
    print("="*80)
    print("Current CL0 in tree: 9003541")
    print("Required CL0 from Excel: 9999999 (test value)")
    print()

    try:
        rebuild_tree_with_shop_exclusions(
            client=client,
            customer_id=CUSTOMER_ID,
            ad_group_id=ad_group_id,
            shop_names=["TestShop.nl"],
            required_cl0_value="9999999"  # Different from existing
        )
        print("\n✅ SUCCESS - CL0 was overridden with required value")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

    # Verify the tree
    print("\n" + "="*80)
    print("VERIFYING TREE STRUCTURE")
    print("="*80)

    ga_service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT
            ad_group_criterion.listing_group.type,
            ad_group_criterion.listing_group.case_value.product_custom_attribute.index,
            ad_group_criterion.listing_group.case_value.product_custom_attribute.value,
            ad_group_criterion.negative
        FROM ad_group_criterion
        WHERE ad_group_criterion.ad_group = 'customers/{CUSTOMER_ID}/adGroups/{ad_group_id}'
            AND ad_group_criterion.type = 'LISTING_GROUP'
            AND ad_group_criterion.status != 'REMOVED'
    """

    try:
        response = ga_service.search(customer_id=CUSTOMER_ID, query=query)

        cl0_found = None
        cl1_found = None

        for row in response:
            lg = row.ad_group_criterion.listing_group
            if lg.case_value.product_custom_attribute.index:
                index = lg.case_value.product_custom_attribute.index.name
                value = lg.case_value.product_custom_attribute.value

                if index == 'INDEX0' and value:
                    cl0_found = value
                elif index == 'INDEX1' and value:
                    cl1_found = value

        print(f"\nCL0 in tree: {cl0_found}")
        print(f"CL1 in tree: {cl1_found}")

        if cl0_found == "9999999":
            print("\n✅ SUCCESS - CL0 was correctly set to required value!")
        else:
            print(f"\n⚠️  WARNING - CL0 is '{cl0_found}', expected '9999999'")

    except Exception as e:
        print(f"\n❌ Error verifying tree: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
