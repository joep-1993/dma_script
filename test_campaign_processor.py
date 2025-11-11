"""
Test script to verify campaign_processor is ready to run
"""
import sys
import os
from campaign_processor import initialize_google_ads_client, CUSTOMER_ID, EXCEL_FILE_PATH

print("=" * 70)
print("TESTING CAMPAIGN PROCESSOR SETUP")
print("=" * 70)

# Test 1: Google Ads Client
print("\n1. Testing Google Ads client initialization...")
try:
    client = initialize_google_ads_client()
    print("   ✅ Google Ads client initialized successfully")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    sys.exit(1)

# Test 2: Check customer ID
print(f"\n2. Checking customer ID configuration...")
print(f"   Customer ID: {CUSTOMER_ID}")
if CUSTOMER_ID:
    print("   ✅ Customer ID is configured")
else:
    print("   ❌ Customer ID is not set")
    sys.exit(1)

# Test 3: Check Excel file path
print(f"\n3. Checking Excel file path...")
print(f"   Path: {EXCEL_FILE_PATH}")
if os.path.exists(EXCEL_FILE_PATH):
    print("   ✅ Excel file exists")
else:
    print("   ⚠️  Excel file not found at this path")
    print("   Note: Update EXCEL_FILE_PATH in campaign_processor.py")
    print("   Current path:", EXCEL_FILE_PATH)

# Test 4: Try to get a service (doesn't make API call)
print("\n4. Testing Google Ads services...")
try:
    ga_service = client.get_service("GoogleAdsService")
    ag_service = client.get_service("AdGroupService")
    agc_service = client.get_service("AdGroupCriterionService")
    print("   ✅ All required services are accessible")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    sys.exit(1)

# Test 5: Import helper functions
print("\n5. Testing helper functions...")
try:
    from google_ads_helpers import (
        safe_remove_entire_listing_tree,
        create_listing_group_subdivision,
        create_listing_group_unit_biddable,
    )
    print("   ✅ All helper functions imported successfully")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED!")
print("=" * 70)
print("\nYour setup is ready. To run the script:")
print("  python3 campaign_processor.py")
print("\nMake sure:")
print("  1. Excel file path is correct")
print("  2. Excel file has sheets: 'toevoegen' and 'uitsluiten'")
print("  3. Close the Excel file before running (so it can be saved)")
