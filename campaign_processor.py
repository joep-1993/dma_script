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

# Column indices (0-based) - EXCLUSION SHEET (uitsluiten) - OLD STRUCTURE
COL_EX_SHOP_NAME = 0      # Column A: Shop name
COL_EX_SHOP_ID = 1        # Column B: Shop ID
COL_EX_CAT_UITSLUITEN = 2 # Column C: cat_uitsluiten
COL_EX_DIEPSTE_CAT_ID = 3 # Column D: Diepste cat ID
COL_EX_CUSTOM_LABEL_1 = 4 # Column E: custom label 1
COL_EX_STATUS = 5         # Column F: Status (TRUE/FALSE)


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

    query = f"""
        SELECT
            bidding_strategy.id,
            bidding_strategy.name,
            bidding_strategy.resource_name
        FROM bidding_strategy
        WHERE bidding_strategy.name = '{strategy_name}'
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

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.resource_name,
            campaign.status
        FROM campaign
        WHERE campaign.name LIKE '%{name_pattern}%'
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
    dim_cl3_others.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX2  # INDEX2 = Custom Label 3
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
    dim_shop.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX2  # INDEX2 = Custom Label 3
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

    Structure:
    Root SUBDIVISION
    ├─ Custom Label 3 OTHERS [POSITIVE, biddable] → Show all shops
    └─ Custom Label 3 = shop_name [NEGATIVE] → Block this specific shop

    Args:
        client: Google Ads client
        customer_id: Customer ID
        ad_group_id: Ad group ID
        shop_name: Shop name to exclude (custom label 3 value)
        default_bid_micros: Bid amount in micros
    """
    print(f"   Rebuilding tree to EXCLUDE shop '{shop_name}' (custom label 3)")

    # Remove existing tree
    safe_remove_entire_listing_tree(client, customer_id, str(ad_group_id))
    time.sleep(0.5)

    agc_service = client.get_service("AdGroupCriterionService")

    # MUTATE 1: Create root SUBDIVISION + Custom Label 3 OTHERS (positive)
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

    # 2. Custom Label 3 OTHERS (positive - shows all shops)
    dim_cl3_others = client.get_type("ListingDimensionInfo")
    dim_cl3_others.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX2  # INDEX2 = Custom Label 3
    # Don't set value - OTHERS case

    ops1.append(
        create_listing_group_unit_biddable(
            client=client,
            customer_id=customer_id,
            ad_group_id=str(ad_group_id),
            parent_ad_group_criterion_resource_name=root_tmp,
            listing_dimension_info=dim_cl3_others,
            targeting_negative=False,  # POSITIVE - shows everything else
            cpc_bid_micros=default_bid_micros
        )
    )

    # Execute first mutate
    resp1 = agc_service.mutate_ad_group_criteria(customer_id=customer_id, operations=ops1)
    root_actual = resp1.results[0].resource_name
    time.sleep(0.5)

    # MUTATE 2: Add specific shop name as NEGATIVE unit (exclusion)
    ops2 = []

    dim_shop = client.get_type("ListingDimensionInfo")
    dim_shop.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX2  # INDEX2 = Custom Label 3
    dim_shop.product_custom_attribute.value = shop_name

    ops2.append(
        create_listing_group_unit_biddable(
            client=client,
            customer_id=customer_id,
            ad_group_id=str(ad_group_id),
            parent_ad_group_criterion_resource_name=root_actual,
            listing_dimension_info=dim_shop,
            targeting_negative=True,  # NEGATIVE targeting (exclusion)
            cpc_bid_micros=None
        )
    )

    agc_service.mutate_ad_group_criteria(customer_id=customer_id, operations=ops2)
    print(f"   ✅ Tree rebuilt: EXCLUDING shop '{shop_name}'")


# ============================================================================
# LISTING TREE BUILDING
# ============================================================================

def build_listing_tree_for_inclusion(
    client: GoogleAdsClient,
    customer_id: str,
    ad_group_id: str,
    maincat_id: str,
    shop_name: str,
    default_bid_micros: int = DEFAULT_BID_MICROS
):
    """
    Build listing tree for inclusion logic (NEW STRUCTURE):

    Tree structure (matches example_functions.txt pattern):
    ROOT (subdivision)
    ├─ Custom Label 0 = maincat_id (subdivision)
    │  ├─ Custom Label 3 = shop_name (unit, biddable, positive) ← Added in MUTATE 2
    │  └─ Custom Label 3 OTHERS (unit, negative) ← Created in MUTATE 1 with temp name
    └─ Custom Label 0 OTHERS (unit, negative)

    CRITICAL: Google Ads requires that when you create a SUBDIVISION, you must
    provide its OTHERS case in the SAME mutate operation using temporary resource names.

    MUTATE 1: Create root + maincat subdivision + both OTHERS cases
    MUTATE 2: Add positive shop_name target under maincat subdivision

    Args:
        client: Google Ads client
        customer_id: Customer ID
        ad_group_id: Ad group ID
        maincat_id: Main category ID to target (custom label 0)
        shop_name: Shop name to target (custom label 3)
        default_bid_micros: Default bid in micros
    """
    print(f"      Building tree: Maincat ID={maincat_id}, Shop={shop_name}")

    # Remove existing tree if any
    safe_remove_entire_listing_tree(client, customer_id, ad_group_id)
    time.sleep(0.5)

    agc_service = client.get_service("AdGroupCriterionService")

    # MUTATE 1: Create root + maincat_id subdivision + both OTHERS cases
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

    # 2. Maincat ID subdivision (Custom Label 0 = maincat_id)
    dim_maincat = client.get_type("ListingDimensionInfo")
    dim_maincat.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX0  # INDEX0 = Custom Label 0
    dim_maincat.product_custom_attribute.value = str(maincat_id)

    maincat_subdivision_op = create_listing_group_subdivision(
        client=client,
        customer_id=customer_id,
        ad_group_id=ad_group_id,
        parent_ad_group_criterion_resource_name=root_tmp,
        listing_dimension_info=dim_maincat
    )
    maincat_subdivision_tmp = maincat_subdivision_op.create.resource_name
    ops1.append(maincat_subdivision_op)

    # 3. Custom Label 0 OTHERS (negative - blocks other categories)
    # This is a child of ROOT and satisfies the OTHERS requirement for root
    dim_cl0_others = client.get_type("ListingDimensionInfo")
    dim_cl0_others.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX0
    # Don't set value - OTHERS case

    ops1.append(
        create_listing_group_unit_biddable(
            client=client,
            customer_id=customer_id,
            ad_group_id=ad_group_id,
            parent_ad_group_criterion_resource_name=root_tmp,
            listing_dimension_info=dim_cl0_others,
            targeting_negative=True,  # NEGATIVE
            cpc_bid_micros=None
        )
    )

    # 4. Custom Label 3 OTHERS (negative - blocks other shops)
    # This is a child of maincat_id subdivision (using TEMP name) and satisfies its OTHERS requirement
    dim_cl3_others = client.get_type("ListingDimensionInfo")
    dim_cl3_others.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX2
    # Don't set value - OTHERS case

    ops1.append(
        create_listing_group_unit_biddable(
            client=client,
            customer_id=customer_id,
            ad_group_id=ad_group_id,
            parent_ad_group_criterion_resource_name=maincat_subdivision_tmp,  # Using TEMP name!
            listing_dimension_info=dim_cl3_others,
            targeting_negative=True,  # NEGATIVE - block other shops
            cpc_bid_micros=None
        )
    )

    # Execute first mutate
    resp1 = agc_service.mutate_ad_group_criteria(customer_id=customer_id, operations=ops1)
    maincat_subdivision_actual = resp1.results[1].resource_name  # Second result is maincat subdivision
    time.sleep(0.5)

    # MUTATE 2: Under maincat_id, add the positive shop_name target
    # Note: CL3 OTHERS was already created in MUTATE 1
    ops2 = []

    # Shop name (Custom Label 3 = shop_name) - POSITIVE target
    dim_shop = client.get_type("ListingDimensionInfo")
    dim_shop.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX2  # INDEX2 = Custom Label 3
    dim_shop.product_custom_attribute.value = shop_name

    ops2.append(
        create_listing_group_unit_biddable(
            client=client,
            customer_id=customer_id,
            ad_group_id=ad_group_id,
            parent_ad_group_criterion_resource_name=maincat_subdivision_actual,
            listing_dimension_info=dim_shop,
            targeting_negative=False,  # POSITIVE - target this shop
            cpc_bid_micros=10_000  # 1 cent = €0.01 = 10,000 micros
        )
    )

    # Execute second mutate
    agc_service.mutate_ad_group_criteria(customer_id=customer_id, operations=ops2)
    print(f"      ✅ Tree created: Maincat '{maincat_id}' → Shop '{shop_name}'")


# ============================================================================
# EXCEL PROCESSING
# ============================================================================

def process_inclusion_sheet(
    client: GoogleAdsClient,
    workbook: openpyxl.Workbook,
    customer_id: str
):
    """
    Process the 'toevoegen' (inclusion) sheet with NEW LOGIC.

    Excel columns:
    A. Shop name
    B. Shop ID
    C. maincat
    D. maincat_id
    E. custom label 1
    F. budget (daily budget in EUR)
    G. Status (TRUE/FALSE) - updated by script

    Groups rows by unique combination of (shop_name, maincat, custom_label_1).
    For each group:
    1. Create campaign with name: PLA/{maincat} {shop_name}_{custom_label_1}
       - Uses budget from column F (converted to micros)
    2. Create ad group with name: PLA/{shop_name}_{custom_label_1}
    3. Build listing tree:
       - Target maincat_id as custom label 0
       - Subdivide and target shop_name as custom label 3
       - Exclude everything else at both levels
    4. Update column G (status) with TRUE/FALSE for all rows in group

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

    # Step 1: Read all rows and group by (shop_name, maincat, custom_label_1)
    from collections import defaultdict
    groups = defaultdict(list)  # key: (shop_name, maincat, custom_label_1), value: list of row data

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
            continue

        # Group key
        group_key = (shop_name, maincat, custom_label_1)

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
        shop_name, maincat, custom_label_1 = group_key

        print(f"\n{'─'*70}")
        print(f"GROUP {group_idx}/{total_groups}: {shop_name} | {maincat} | {custom_label_1}")
        print(f"   Rows in group: {len(rows_in_group)}")
        print(f"{'─'*70}")

        # Get metadata from first row (all rows in group share same maincat, maincat_id, shop, budget)
        first_row = rows_in_group[0]
        shop_id = first_row['shop_id']
        maincat_id = first_row['maincat_id']
        budget_value = first_row['budget']

        print(f"   Maincat ID: {maincat_id}")
        print(f"   Budget: {budget_value} EUR")

        try:
            # Build campaign name: PLA/{maincat} {shop_name}_{custom_label_1}
            campaign_name = f"PLA/{maincat} {shop_name}_{custom_label_1}"
            print(f"\n   Step 1: Creating/finding campaign: {campaign_name}")

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

            campaign_resource_name = add_standard_shopping_campaign(
                client=client,
                customer_id=customer_id,
                merchant_center_account_id=merchant_center_account_id,
                campaign_name=campaign_name,
                budget_name=budget_name,
                tracking_template=tracking_template,
                country=country,
                shopid=shop_id,
                shopname=shop_name,
                label=custom_label_1,
                budget=budget_micros,
                bidding_strategy_resource_name=bid_strategy_resource_name
            )

            if not campaign_resource_name:
                raise Exception("Failed to create/find campaign")

            print(f"   ✅ Campaign ready: {campaign_resource_name}")

            # Build ad group name: PLA/{shop_name}_{custom_label_1}
            ad_group_name = f"PLA/{shop_name}_{custom_label_1}"
            print(f"\n   Step 2: Creating/finding ad group: {ad_group_name}")

            ad_group_resource_name, was_created = add_shopping_ad_group(
                client=client,
                customer_id=customer_id,
                campaign_resource_name=campaign_resource_name,
                ad_group_name=ad_group_name,
                campaign_name=campaign_name
            )

            if not ad_group_resource_name:
                raise Exception("Failed to create/find ad group")

            print(f"   ✅ Ad group ready: {ad_group_resource_name}")

            # Extract ad group ID from resource name
            ad_group_id = ad_group_resource_name.split('/')[-1]

            # Build listing tree
            print(f"\n   Step 3: Building listing tree...")
            build_listing_tree_for_inclusion(
                client=client,
                customer_id=customer_id,
                ad_group_id=ad_group_id,
                maincat_id=maincat_id,
                shop_name=shop_name,
                default_bid_micros=DEFAULT_BID_MICROS
            )

            print(f"   ✅ Listing tree created successfully")

            # Mark all rows in this group as successful
            for row_data in rows_in_group:
                row_data['row_obj'][COL_STATUS].value = True

            successful_groups += 1
            print(f"\n   ✅ GROUP {group_idx} COMPLETED SUCCESSFULLY")

        except Exception as e:
            print(f"\n   ❌ GROUP {group_idx} FAILED: {e}")
            # Mark all rows in this group as failed
            for row_data in rows_in_group:
                row_data['row_obj'][COL_STATUS].value = False

    print(f"\n{'='*70}")
    print(f"INCLUSION SHEET SUMMARY: {successful_groups}/{total_groups} groups processed successfully")
    print(f"{'='*70}\n")


def process_exclusion_sheet(
    client: GoogleAdsClient,
    workbook: openpyxl.Workbook,
    customer_id: str
):
    """
    Process the 'uitsluiten' (exclusion) sheet.

    For each row:
    1. Retrieve campaign by pattern: PLA/*cat_uitsluiten*_*custom_label_1*
    2. Get ad group from campaign
    3. Rebuild tree to EXCLUDE shop name (custom label 3)
    4. Update column F with TRUE/FALSE

    Args:
        client: Google Ads client
        workbook: Excel workbook
        customer_id: Customer ID
    """
    print(f"\n{'='*70}")
    print(f"PROCESSING EXCLUSION SHEET: '{SHEET_EXCLUSION}'")
    print(f"{'='*70}\n")

    try:
        sheet = workbook[SHEET_EXCLUSION]
    except KeyError:
        print(f"❌ Sheet '{SHEET_EXCLUSION}' not found in workbook")
        return

    # Skip header row (row 1)
    total_rows = 0
    success_count = 0

    for idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=False), start=2):
        # Check if status column (F) is empty - if so, this is where we start processing
        status_value = row[COL_EX_STATUS].value

        # Skip rows that already have a status (TRUE/FALSE)
        if status_value is not None and status_value != '':
            continue

        total_rows += 1

        # Extract values (using exclusion sheet column indices)
        shop_name = row[COL_EX_SHOP_NAME].value
        _shop_id = row[COL_EX_SHOP_ID].value  # Available if needed
        cat_uitsluiten = row[COL_EX_CAT_UITSLUITEN].value
        _diepste_cat_id = row[COL_EX_DIEPSTE_CAT_ID].value  # Available if needed
        custom_label_1 = row[COL_EX_CUSTOM_LABEL_1].value

        print(f"\n[Row {idx}] Processing exclusion for shop: {shop_name}")
        print(f"         Category: {cat_uitsluiten}, Custom Label 1: {custom_label_1}")

        # Validate required fields
        if not shop_name or not cat_uitsluiten or not custom_label_1:
            print(f"   ⚠️  Missing required fields, skipping row")
            row[COL_EX_STATUS].value = False
            continue

        # Build campaign name pattern
        campaign_pattern = f"PLA/{cat_uitsluiten}_{custom_label_1}"
        print(f"   Searching for campaign: {campaign_pattern}")

        # Retrieve campaign
        campaign = get_campaign_by_name_pattern(client, customer_id, campaign_pattern)
        if not campaign:
            print(f"   ❌ Campaign not found")
            row[COL_EX_STATUS].value = False
            continue

        print(f"   ✅ Found campaign: {campaign['name']} (ID: {campaign['id']})")

        # Retrieve ad group
        ad_group = get_ad_group_from_campaign(client, customer_id, campaign['id'])
        if not ad_group:
            print(f"   ❌ No ad group found in campaign")
            row[COL_EX_STATUS].value = False
            continue

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
            row[COL_EX_STATUS].value = True
            success_count += 1
            print(f"   ✅ SUCCESS - Row {idx} completed")

        except Exception as e:
            print(f"   ❌ Error rebuilding tree: {e}")
            row[COL_EX_STATUS].value = False

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

    # Process exclusion sheet
    try:
        process_exclusion_sheet(client, workbook, CUSTOMER_ID)
    except Exception as e:
        print(f"❌ Error processing exclusion sheet: {e}")

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
