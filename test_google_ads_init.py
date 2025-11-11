"""
Quick test to verify Google Ads client initialization
"""
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 70)
print("TESTING GOOGLE ADS CLIENT INITIALIZATION")
print("=" * 70)

# Check if credentials are loaded
print("\n1. Checking .env variables...")
required_vars = [
    "GOOGLE_ADS_DEVELOPER_TOKEN",
    "GOOGLE_ADS_CLIENT_ID",
    "GOOGLE_ADS_CLIENT_SECRET",
    "GOOGLE_ADS_REFRESH_TOKEN"
]

all_present = True
for var in required_vars:
    value = os.getenv(var)
    if value:
        print(f"   ✅ {var}: Found ({value[:10]}...)")
    else:
        print(f"   ❌ {var}: Missing")
        all_present = False

if not all_present:
    print("\n❌ Some credentials are missing!")
    sys.exit(1)

# Try to import Google Ads
print("\n2. Importing Google Ads library...")
try:
    from google.ads.googleads.client import GoogleAdsClient
    print("   ✅ Google Ads library imported successfully")
except ImportError as e:
    print(f"   ❌ Error importing: {e}")
    sys.exit(1)

# Try to initialize client
print("\n3. Initializing Google Ads client...")
try:
    credentials = {
        "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
        "use_proto_plus": True
    }

    login_customer_id = os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
    if login_customer_id:
        credentials["login_customer_id"] = login_customer_id

    client = GoogleAdsClient.load_from_dict(credentials)
    print("   ✅ Google Ads client initialized successfully!")

    # Try to get a service (doesn't make API call, just initializes)
    ga_service = client.get_service("GoogleAdsService")
    print("   ✅ GoogleAdsService retrieved successfully")

    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED - Your setup is ready!")
    print("=" * 70)
    print("\nYou can now run: python3 campaign_processor.py")

except Exception as e:
    print(f"   ❌ Error: {e}")
    print("\n" + "=" * 70)
    print("❌ INITIALIZATION FAILED")
    print("=" * 70)
    print("\nPossible issues:")
    print("1. Check if your refresh token is still valid")
    print("2. Verify your client ID and client secret are correct")
    print("3. Make sure your developer token is approved")
    sys.exit(1)
