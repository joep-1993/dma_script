# LEARNINGS
_Capture mistakes, solutions, and patterns. Update when: errors occur, bugs are fixed, patterns emerge._

## Docker Commands
```bash
# Development
docker-compose up              # Run with logs
docker-compose up -d           # Run in background
docker-compose logs -f app     # View app logs
docker-compose down            # Stop everything
docker-compose down -v         # Stop and remove volumes

# Debugging
docker-compose ps              # Check status
docker exec -it <container> bash  # Enter container
```

## Common Issues & Solutions

### GAQL Query Fails with Apostrophes in Names
**Problem**: GAQL queries fail with `INVALID_ARGUMENT` / `UNEXPECTED_INPUT` errors when campaign or ad group names contain apostrophes
**Symptoms**: Error message shows "unexpected input" at the apostrophe position (e.g., "Error in query: unexpected input \'s store_b\'")
**Example**: Campaign name "PLA/Auto's store_b" breaks the query
**Root Cause**: Single quotes in GAQL string literals must be escaped, but the wrong escaping method was used
**Broken Code**:
```python
# WRONG: Using double single quotes (SQL-style escaping)
escaped_name = campaign_name.replace("'", "''")
query = f"WHERE campaign.name = '{escaped_name}'"
# Results in: WHERE campaign.name = 'PLA/Auto''s store_b'
# GAQL doesn't recognize '' as escaped quote
```
**Fixed Code**:
```python
# CORRECT: Using backslash escaping (GAQL-style escaping)
escaped_name = campaign_name.replace("'", "\\'")
query = f"WHERE campaign.name = '{escaped_name}'"
# Results in: WHERE campaign.name = 'PLA/Auto\'s store_b'
# GAQL correctly interprets \' as literal single quote
```
**Locations Fixed**:
- google_ads_helpers.py line 181: Campaign name in exact match query
- google_ads_helpers.py line 373: Ad group name in lookup query
- campaign_processor.py line 196: Bid strategy name query
- campaign_processor.py line 246: Campaign name pattern in LIKE query
**Impact**: Script now handles any campaign/ad group names with apostrophes (Auto's, Men's, Children's, etc.)
_#claude-session:2025-11-19_

### Migration Data Loss Due to No Incremental Saves
**Problem**: Large-scale migration lost all progress (3 hours of work) when script crashed with 500 Internal Server Error
**Symptoms**: Script processed 1,100+ campaigns successfully, marked them as TRUE in memory, but crashed before saving Excel file
**Root Cause**: `process_exclusion_sheet()` only saved workbook at very end (line 1374). When crash occurred, all in-memory status updates were lost.
**Impact**: 866,351 campaigns remained to process with 0 successful completions saved
**Solution**: Implement incremental saving every N campaigns:
```python
def process_exclusion_sheet(
    client, workbook, customer_id,
    save_interval: int = 50,  # Save every 50 campaigns
    rate_limit_seconds: float = 0.5  # Delay between campaigns
):
    processed_since_save = 0

    for idx, row in enumerate(sheet.iter_rows(min_row=2), start=2):
        # Process campaign...
        processed_since_save += 1

        # Incremental save
        if processed_since_save >= save_interval:
            print(f"\n   💾 Saving progress...")
            try:
                workbook.save(EXCEL_FILE_PATH)
                print(f"   ✅ Progress saved successfully")
                processed_since_save = 0
            except Exception as save_error:
                print(f"   ⚠️  Error saving: {save_error}")

        # Rate limiting
        if rate_limit_seconds > 0:
            time.sleep(rate_limit_seconds)

    # Final save
    workbook.save(EXCEL_FILE_PATH)
```
**Benefits**: Maximum 50 campaigns lost on crash instead of hours of work, progress persists through failures
**Additional Fix**: Add rate limiting to prevent API overload that causes 500 errors
_#claude-session:2025-11-19_

### CONCURRENT_MODIFICATION Error Marked as SUCCESS
**Problem**: When CONCURRENT_MODIFICATION errors occurred, campaigns were incorrectly marked as TRUE (success) in Excel
**Symptoms**: Excel shows TRUE status but shop exclusion was never applied due to API error
**Root Cause**: `rebuild_tree_with_custom_label_3_exclusion()` caught exceptions and printed error but returned normally instead of raising
**Broken Code**:
```python
try:
    agc_service.mutate_ad_group_criteria(operations=ops2)
except Exception as e:
    print(f"   ❌ Error adding shop exclusion: {e}")
    return  # Silent failure - calling code thinks it succeeded!
```
**Fixed Code**:
```python
try:
    agc_service.mutate_ad_group_criteria(operations=ops2)
except Exception as e:
    print(f"   ❌ Error adding shop exclusion: {e}")
    raise  # Re-raise so calling code marks as FALSE
```
**Locations Fixed**:
- Line 463: Error reading existing tree
- Line 699: Error rebuilding tree (first mutate)
- Line 765: Error adding shop exclusion (second mutate)
**Impact**: Now only campaigns that fully succeed are marked TRUE, failed campaigns marked FALSE with error message
_#claude-session:2025-11-19_

### Google Ads CONCURRENT_MODIFICATION Error
**Problem**: Multiple shops trying to modify the same ad group simultaneously causes CONCURRENT_MODIFICATION error
**Symptoms**: When processing multiple shops in same campaign, both shops get assigned the same ad group ID, leading to concurrent modification conflicts
**Root Cause**: `add_shopping_ad_group()` function was checking if ANY ad group exists in campaign (old single-ad-group design) and returning it without checking the ad_group_name parameter
**Solution**: Update query to check for SPECIFIC ad group name:
```python
# BROKEN: Old query checking ANY ad group
query = f"""
    SELECT ad_group.id, ad_group.resource_name
    FROM ad_group
    WHERE ad_group.campaign = '{campaign_resource_name}'
    AND ad_group.status != 'REMOVED'
    LIMIT 1
"""

# FIXED: New query checking specific ad group name
query = f"""
    SELECT ad_group.id, ad_group.resource_name, ad_group.name
    FROM ad_group
    WHERE ad_group.campaign = '{campaign_resource_name}'
    AND ad_group.name = '{ad_group_name}'
    AND ad_group.status != 'REMOVED'
    LIMIT 1
"""
```
**Additional Fix**: Add delay after listing tree creation to avoid race conditions:
```python
time.sleep(1)  # Small delay to avoid concurrent modification issues
```
**File**: `google_ads_helpers.py` lines 371-384
_#claude-session:2025-11-12_

### Google Ads LISTING_GROUP_REQUIRES_SAME_DIMENSION_TYPE_AS_SIBLINGS Error
**Problem**: When trying to preserve existing tree structures while adding shop exclusions, get error "Dimension type of listing group must be the same as that of its siblings"
**Symptoms**: Cannot add CL4 (Custom Label 4) and CL3 (Custom Label 3) as siblings under same parent
**Root Cause**: Google Ads requires all sibling nodes in listing tree to have the SAME dimension type. Cannot mix CL4, CL1, CL3 as siblings.
**Solution**: Build hierarchical tree where each level has ONE dimension type:
```
ROOT (level 0)
└─ CL1 = 'a' (level 1 - only CL1 nodes)
   └─ CL4 = '9005157' (level 2 - only CL4 nodes)
      ├─ CL3 = 'shop.nl' (level 3 - only CL3 nodes)
      └─ CL3 = OTHERS (level 3 - only CL3 nodes)
```
**Pattern**: When adding deeper nesting, convert positive UNIT nodes to SUBDIVISIONS:
```python
# If CL4 was a positive UNIT node, convert to SUBDIVISION
cl4_subdivision_op = create_listing_group_subdivision(
    parent=deepest_parent,
    dimension=dim_cl4  # CL4 = '9005157'
)

# Then nest CL3 under it
ops.append(create_listing_group_unit(
    parent=cl4_subdivision_tmp,
    dimension=dim_cl3_shop,  # CL3 = 'shop.nl'
    negative=True
))
```
**Reference**: Study `rebuild_tree_with_label_and_item_ids` in example_functions.txt for working pattern
_#claude-session:2025-11-12_

### Google Ads SUBDIVISION_REQUIRES_OTHERS_CASE Error
**Problem**: Campaign listing tree creation fails with `criterion_error: LISTING_GROUP_SUBDIVISION_REQUIRES_OTHERS_CASE`
**Solution**: When creating a SUBDIVISION node in Google Ads listing tree, you MUST provide its OTHERS case in the SAME mutate operation using temporary resource names
**Correct Implementation**:
```python
# MUTATE 1: Create subdivision + its OTHERS case together
ops1 = []

# Create subdivision with temporary resource name
subdivision_op = create_listing_group_subdivision(
    parent=root_tmp,  # Using temp name
    dimension=dim_maincat
)
subdivision_tmp = subdivision_op.create.resource_name
ops1.append(subdivision_op)

# Add OTHERS case as child of subdivision (using temp name)
ops1.append(create_listing_group_unit(
    parent=subdivision_tmp,  # Reference temp subdivision
    dimension=dim_others,
    negative=True
))

# Execute together
response = service.mutate_ad_group_criteria(operations=ops1)
subdivision_actual = response.results[0].resource_name  # Get actual name

# MUTATE 2: Now add other children using actual resource name
ops2 = []
ops2.append(create_listing_group_unit(
    parent=subdivision_actual,  # Use actual name from response
    dimension=dim_specific_value,
    negative=False
))
service.mutate_ad_group_criteria(operations=ops2)
```
**Root Cause**: Google Ads API requires subdivisions to have complete structure (including OTHERS) to prevent undefined states
**Reference**: See example_functions.txt line 405-441 for working pattern
_#claude-session:2025-11-12_

### ModuleNotFoundError: No module named 'dotenv'
**Problem**: Script fails with missing dotenv module
**Solution**: Install dependencies with `pip install -r requirements.txt` or `pip3 install python-dotenv google-ads openpyxl`
**Root Cause**: Dependencies not installed before running script
_#claude-session:2025-11-11_

### Google Ads .env Variable Naming
**Problem**: Script can't find Google Ads credentials even though they're in .env
**Solution**: Variables must be prefixed with `GOOGLE_ADS_*` not just `GOOGLE_*`
**Correct names**: `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_CLIENT_ID`, `GOOGLE_ADS_CLIENT_SECRET`, `GOOGLE_ADS_REFRESH_TOKEN`, `GOOGLE_ADS_LOGIN_CUSTOMER_ID`
**Wrong names**: `GOOGLE_DEVELOPER_TOKEN`, `GOOGLE_CLIENT_ID`, etc.
_#claude-session:2025-11-11_

### Google Ads tracking_url_template "Too short" Error
**Problem**: Campaign creation fails with `string_length_error: TOO_SHORT` on tracking_url_template field
**Solution**: Only set `tracking_url_template` field if it has a non-empty value
```python
# Don't do this:
campaign.tracking_url_template = ""  # Causes TOO_SHORT error

# Do this instead:
if tracking_template:
    campaign.tracking_url_template = tracking_template
```
**Root Cause**: Google Ads API rejects empty string for tracking_url_template, requires either valid URL or field not set
_#claude-session:2025-11-11_

### Column Index Mismatch Between Excel Sheets
**Problem**: Script fails with `name 'COL_CATEGORY' is not defined` when processing exclusion sheet
**Solution**: Use separate column index constants for different sheet structures
- Inclusion sheet (toevoegen): 8 columns (A-H), status in column H
- Exclusion sheet (uitsluiten): 6 columns (A-F), status in column F
```python
# Inclusion sheet columns
COL_SHOP_NAME = 0
COL_MAINCAT = 2
COL_STATUS = 7  # Column H

# Exclusion sheet columns
COL_EX_SHOP_NAME = 0
COL_EX_CAT_UITSLUITEN = 2
COL_EX_STATUS = 5  # Column F
```
**Root Cause**: Different Excel sheets have different column structures
_#claude-session:2025-11-11_

### Port Conflicts
- FastAPI on 8001 (not 8000) to avoid conflicts
- PostgreSQL on 5433 (not 5432) for same reason

### CORS Errors
- Check `allow_origins` in main.py
- For dev: use `["*"]`
- For production: specify exact frontend URL

### Database Connection
- Wait for PostgreSQL to fully start
- Check DATABASE_URL in .env
- Run `docker-compose logs db` to debug

## Project Patterns

### Cross-Platform Excel Path Handling with OS Detection
**Pattern**: Use `platform.system()` to automatically detect operating system and select appropriate file paths
**Implementation**:
```python
import platform
import os

def get_excel_path():
    windows_path = "c:/Users/Name/Downloads/file.xlsx"
    wsl_path = "/mnt/c/Users/Name/Downloads/file.xlsx"

    system = platform.system().lower()
    if system == "windows":
        return windows_path
    elif system == "linux":
        # Check for WSL
        if os.path.exists("/proc/version"):
            with open("/proc/version", "r") as f:
                if "microsoft" in f.read().lower():
                    return wsl_path
        return wsl_path if os.path.exists(wsl_path) else windows_path
    return windows_path
```
**Benefits**: Script works on both Windows and WSL without manual path changes
_#claude-session:2025-11-11_

### Google Ads Client Initialization from .env
**Pattern**: Load Google Ads credentials from environment variables instead of google-ads.yaml
**Implementation**:
```python
from google.ads.googleads.client import GoogleAdsClient
from dotenv import load_dotenv
import os

load_dotenv()

credentials = {
    "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
    "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
    "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
    "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
    "use_proto_plus": True
}

client = GoogleAdsClient.load_from_dict(credentials)
```
**Benefits**: Credentials managed with other environment variables, easier deployment
_#claude-session:2025-11-11_

### Testing Scripts for Setup Verification
**Pattern**: Create separate test scripts to verify setup before running main script
**Examples**:
- `test_google_ads_init.py` - Tests Google Ads client initialization and credentials
- `test_campaign_processor.py` - Tests all components (client, Excel file, helper functions)
**Benefits**: Catch configuration issues early, provide clear error messages
_#claude-session:2025-11-11_

### Row Grouping for Batch Campaign Creation
**Pattern**: Group Excel rows by key fields before processing to create one campaign per unique group
**Implementation**:
```python
from collections import defaultdict

groups = defaultdict(list)
for row in sheet.iter_rows(min_row=2):
    # Group by combination of fields
    group_key = (shop_name, maincat, custom_label_1)
    groups[group_key].append(row_data)

# Process each group
for group_key, rows_in_group in groups.items():
    # Create campaign once for entire group
    campaign = create_campaign(group_key)
    # Collect all category IDs from rows in this group
    cat_ids = [r['cat_id'] for r in rows_in_group]
    # Build listing tree with all categories
    build_tree(campaign, cat_ids)
```
**Benefits**: Reduces API calls, creates logical campaign structure, handles multiple rows per campaign
**Use Case**: When Excel has multiple rows that belong to same campaign (different categories for same shop/label combo)
_#claude-session:2025-11-11_

### Hierarchical Listing Tree Structure
**Pattern**: Build multi-level listing tree subdivisions in Google Ads Shopping campaigns
**Structure**:
```
Root SUBDIVISION
├─ Shop Name (Custom Label 3) = "Shop A" [SUBDIVISION]
│  ├─ Category (Custom Label 4) = "Cat1" [UNIT, POSITIVE, biddable]
│  ├─ Category (Custom Label 4) = "Cat2" [UNIT, POSITIVE, biddable]
│  └─ OTHERS (Custom Label 4) [UNIT, NEGATIVE]
└─ OTHERS (Custom Label 3) [UNIT, NEGATIVE]
```
**Implementation**:
- First mutate: Create root + first level subdivisions + OTHERS units
- Second mutate: Create child units under subdivisions
- Use temporary IDs for parent references before actual resource names returned
**Benefits**: Precise targeting control, excludes unwanted combinations, maintains clean tree hierarchy
_#claude-session:2025-11-11_

### Portfolio Bid Strategy from MCC Account
**Pattern**: Search for and apply portfolio bid strategies from MCC account to campaigns in client accounts
**Implementation**:
```python
# Configuration
MCC_ACCOUNT_ID = "3011145605"  # MCC account where bid strategies are stored
BID_STRATEGY_MAPPING = {
    'a': 'DMA: Elektronica shops A - 0,25',
    'b': 'DMA: Elektronica shops B - 0,21',
    'c': 'DMA: Elektronica shops C - 0,17'
}

# Search in MCC account
def get_bid_strategy_by_name(client, customer_id, strategy_name):
    query = f"""
        SELECT bidding_strategy.resource_name
        FROM bidding_strategy
        WHERE bidding_strategy.name = '{strategy_name}'
    """
    response = ga_service.search(customer_id=customer_id, query=query)
    for row in response:
        return row.bidding_strategy.resource_name
    return None

# Apply to campaign
bid_strategy_name = BID_STRATEGY_MAPPING[custom_label_1]  # e.g., 'a' → strategy name
bid_strategy_resource = get_bid_strategy_by_name(client, MCC_ACCOUNT_ID, bid_strategy_name)

# When creating campaign
campaign.bidding_strategy = bid_strategy_resource  # Portfolio strategy from MCC
```
**Benefits**: Centralized bid strategy management in MCC, applies to all client accounts
**Use Case**: Multiple client accounts sharing same bid strategies defined at MCC level
_#claude-session:2025-11-12_

### Incremental Saving for Long-Running Excel Processing
**Pattern**: Save workbook periodically during long-running operations to prevent data loss on crashes
**Implementation**:
```python
def process_large_dataset(workbook, save_interval=50):
    processed_count = 0

    for idx, row in enumerate(sheet.iter_rows(min_row=2), start=2):
        # Process row...
        try:
            # Do work
            row[STATUS_COL].value = True
            processed_count += 1
        except Exception as e:
            row[STATUS_COL].value = False

        # Incremental save
        if processed_count >= save_interval:
            print(f"💾 Saving progress ({processed_count} processed)...")
            try:
                workbook.save(EXCEL_FILE_PATH)
                processed_count = 0  # Reset counter
            except Exception as save_error:
                print(f"⚠️  Save failed: {save_error}")
                # Continue processing even if save fails

    # Final save
    workbook.save(EXCEL_FILE_PATH)
```
**Benefits**:
- Limits data loss to `save_interval` rows on crash (vs entire run)
- Enables recovery from long-running processes
- Provides progress checkpoints for debugging
**Trade-offs**: More disk I/O, but negligible compared to API operations
**Use Case**: Processing 866,351 campaigns where entire run takes days
_#claude-session:2025-11-19_

### Rate Limiting for Google Ads API Operations
**Pattern**: Add configurable delays between API operations to prevent overwhelming the API
**Implementation**:
```python
def process_campaigns(client, campaigns, rate_limit_seconds=0.5):
    for campaign in campaigns:
        # Process campaign...
        try:
            process_single_campaign(client, campaign)
        except Exception as e:
            handle_error(e)

        # Rate limiting - prevent API overload
        if rate_limit_seconds > 0:
            time.sleep(rate_limit_seconds)
```
**Benefits**:
- Reduces CONCURRENT_MODIFICATION errors
- Prevents 500 Internal Server Errors from API overload
- More reliable for large-scale operations
**Recommended Values**:
- Conservative: 0.5-1.0 seconds (safer, slower)
- Moderate: 0.3-0.5 seconds (balanced)
- Aggressive: 0.1-0.3 seconds (faster, riskier)
**Use Case**: Processing thousands of campaigns where API rate limits could be exceeded
_#claude-session:2025-11-19_

### Optimal Rate Limiting and Smart Delay Strategy
**Finding**: Tested 0.2s rate limiting on 872,571 campaign migration and discovered optimal strategy
**Results**:
- 1,766 campaigns successfully processed (26.1% success rate on existing campaigns)
- 5,008 campaigns failed with CONCURRENT_MODIFICATION (0.2s still too fast for some operations)
- 865,797 campaigns "not found" (quickly skipped)
- Total processing time: ~8-9 hours (down from estimated 5-10 days)
**Key Optimization**: Only apply rate limiting AFTER successful operations, not after errors or "not found":
```python
try:
    # Process campaign
    rebuild_tree_with_custom_label_3_exclusion(...)
    row[COL_EX_STATUS].value = True

    # Rate limiting ONLY after success (moved inside try block)
    if rate_limit_seconds > 0:
        time.sleep(rate_limit_seconds)

except Exception as e:
    row[COL_EX_STATUS].value = False
    # NO rate limiting after errors - fail fast
```
**Impact**: This optimization provided ~10x speedup overall because:
- 99.2% of rows (865,797) were "campaign not found" and skipped instantly with no delay
- Only 0.8% of rows (6,774 existing campaigns) needed rate limiting
- Eliminated unnecessary delays for 99%+ of rows
**Trade-offs**:
- 0.2s still causes 74% failure rate on existing campaigns (5,008/6,774)
- Failed campaigns marked FALSE and can be retried later with slower rate
- Acceptable trade-off for massive speed improvement on large datasets
**Recommendation**: Use smart rate limiting (delays only after success) + 0.2s for fast bulk operations where retry is acceptable
_#claude-session:2025-11-19_

### Resumable Excel Processing
**Pattern**: Skip rows that have already been processed to enable resuming from failures
**Implementation**:
```python
for idx, row in enumerate(sheet.iter_rows(min_row=2), start=2):
    # Check status column - skip if already processed
    status_value = row[COL_STATUS].value
    if status_value is not None and status_value != '':
        continue  # Skip this row, already has TRUE or FALSE

    # Process row...
    try:
        # Do work
        row[COL_STATUS].value = True  # Mark as successful
    except Exception as e:
        row[COL_STATUS].value = False  # Mark as failed

# Save workbook after processing
workbook.save(excel_path)
```
**Benefits**:
- Script can be re-run without duplicating work
- Failed rows can be fixed and re-processed individually
- Partial progress is saved even if script crashes
**Use Case**: Large Excel files where processing may fail partway through
_#claude-session:2025-11-12_

### Helper Functions for Campaign Management
**Functions added to google_ads_helpers.py**:
- `ensure_campaign_label_exists(client, customer_id, label_name)` - Creates or retrieves campaign label
- `script_label = "DMA_SCRIPT_JVS"` - Global constant for auto-labeling campaigns
- `add_shopping_ad_group(client, customer_id, campaign_resource_name, ad_group_name, campaign_name)` - Creates ad group with 2 cent (20,000 micros) default bid
- `labelCampaign(client, customer_id, campaign_name, campaign_resource_name)` - Adds label to campaign
**Pattern**: Keep campaign management logic in helper file, import into main script
_#claude-session:2025-11-11_

### Custom Label Mapping: maincat_id → Custom Label 4
**Change**: Modified inclusion function to target maincat_id using Custom Label 4 instead of Custom Label 0
**Reason**: Align with updated product feed structure where maincat_id is mapped to Custom Label 4
**Implementation**:
```python
# Old: Using INDEX0 (Custom Label 0)
dim_maincat.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX0

# New: Using INDEX4 (Custom Label 4)
dim_maincat.product_custom_attribute.index = client.enums.ProductCustomAttributeIndexEnum.INDEX4
```
**Updated Tree Structure**:
```
ROOT (subdivision)
├─ Custom Label 1 = custom_label_1 (subdivision) [a/b/c]
│  ├─ Custom Label 1 OTHERS (unit, negative)
│  └─ Custom Label 4 = maincat_id (subdivision)
│     ├─ Custom Label 4 OTHERS (unit, negative)
│     ├─ Custom Label 3 = shop_name (unit, biddable, positive)
│     └─ Custom Label 3 OTHERS (unit, negative)
└─ Custom Label 1 OTHERS (unit, negative)
```
**Files Updated**: `campaign_processor.py` (lines 867, 883, 787-788, 804, 976)
_#claude-session:2025-11-17_

### Preserving Hierarchical Listing Tree Structures
**Pattern**: When modifying listing trees, preserve existing custom label subdivisions and units by collecting BOTH types and rebuilding hierarchy
**Problem**: Exclusion logic was destroying existing CL4 and CL1 targeting when adding CL3 shop exclusions
**Solution**:
```python
# Step 1: Collect BOTH subdivisions (hierarchy) and units (targeting)
custom_label_subdivisions = []  # CL4/CL1 subdivision nodes
custom_label_structures = []     # CL4/CL1 unit nodes

for row in results:
    if is_subdivision:
        custom_label_subdivisions.append({
            'index': index_name,  # e.g., 'INDEX4' or 'INDEX1'
            'value': value,       # e.g., '9005157' or 'a'
            'parent': parent_resource
        })
    elif is_unit:
        custom_label_structures.append({
            'index': index_name,
            'value': value,
            'negative': is_negative,
            'bid_micros': bid
        })

# Step 2: Rebuild subdivisions hierarchically (ROOT → CL1 → CL4)
# Step 3: Convert positive CL4 units to subdivisions
# Step 4: Nest CL3 exclusions under CL4 subdivisions
```
**Key Insight**: Must differentiate between SUBDIVISION nodes (define hierarchy) and UNIT nodes (targeting/exclusions). When adding deeper nesting, convert units to subdivisions.
**Reference**: Follow pattern from `rebuild_tree_with_label_and_item_ids` in example_functions.txt
_#claude-session:2025-11-12_

### Converting Units to Subdivisions for Deeper Nesting
**Pattern**: When adding deeper custom label levels to existing tree, convert positive UNIT nodes to SUBDIVISION nodes
**Use Case**: Have CL4='9005157' as positive UNIT with bid. Need to add CL3 shop exclusions under it.
**Implementation**:
```python
# Original structure:
# ROOT → CL1='a' [SUBDIVISION] → CL4='9005157' [UNIT, positive, bid=1.00€]

# Convert CL4 unit to subdivision
cl4_subdivision_op = create_listing_group_subdivision(
    parent=cl1_actual,
    dimension=dim_cl4  # CL4 = '9005157'
)
ops.append(cl4_subdivision_op)

# Add CL4 OTHERS (negative)
ops.append(create_listing_group_unit(
    parent=cl4_subdivision_tmp,
    dimension=dim_cl4_others,
    negative=True
))

# Add CL3 OTHERS (positive, inherits bid)
ops.append(create_listing_group_unit(
    parent=cl4_subdivision_tmp,
    dimension=dim_cl3_others,
    negative=False,
    bid=original_bid  # Preserve the bid from CL4 unit
))

# Add CL3 shop exclusion (negative)
ops.append(create_listing_group_unit(
    parent=cl4_subdivision_actual,  # From mutate response
    dimension=dim_cl3_shop,
    negative=True
))

# New structure:
# ROOT → CL1='a' [SUBDIVISION] → CL4='9005157' [SUBDIVISION]
#                                  ├─ CL4 OTHERS [UNIT, negative]
#                                  ├─ CL3 OTHERS [UNIT, positive, bid=1.00€]
#                                  └─ CL3='shop.nl' [UNIT, negative]
```
**Benefits**: Preserves original bid, maintains tree validity, enables deeper nesting
**Reference**: Study `rebuild_tree_with_label_and_item_ids` in example_functions.txt lines 200-250
_#claude-session:2025-11-12_

### Optimizing Google Ads API Queries with Filtered GAQL
**Pattern**: Use WHERE clauses in GAQL queries to fetch only necessary data instead of querying all records and filtering in code
**Use Case**: Finding the root node of a listing tree was querying all nodes then filtering in Python
**Problem**: Original `safe_remove_entire_listing_tree()` called `list_listing_groups_with_depth()` which fetched ALL listing groups just to find the one root node
**Implementation**:
```python
# INEFFICIENT: Query all nodes, then filter in Python
def safe_remove_entire_listing_tree_OLD(client, customer_id, ad_group_id):
    # Queries ALL listing groups (could be 100+ nodes)
    rows, depth = list_listing_groups_with_depth(client, customer_id, ad_group_id)

    # Find root node by filtering all results in Python
    root = None
    for r in rows:
        if not r.ad_group_criterion.listing_group.parent_ad_group_criterion:
            root = r
            break

    # Remove root (API cascades to children)
    op = client.get_type("AdGroupCriterionOperation")
    op.remove = root.ad_group_criterion.resource_name
    agc.mutate_ad_group_criteria(operations=[op])

# OPTIMIZED: Query only the root node with filtered GAQL
def safe_remove_entire_listing_tree(client, customer_id, ad_group_id):
    ag_path = ag_service.ad_group_path(customer_id, ad_group_id)

    # Query ONLY for root node using WHERE clause
    query = f"""
        SELECT ad_group_criterion.resource_name
        FROM ad_group_criterion
        WHERE ad_group_criterion.ad_group = '{ag_path}'
            AND ad_group_criterion.type = 'LISTING_GROUP'
            AND ad_group_criterion.listing_group.parent_ad_group_criterion IS NULL
        LIMIT 1
    """

    results = list(ga_service.search(customer_id=customer_id, query=query))
    if not results:
        return  # No tree to remove

    # Remove root (API cascades to children)
    op = client.get_type("AdGroupCriterionOperation")
    op.remove = results[0].ad_group_criterion.resource_name
    agc.mutate_ad_group_criteria(operations=[op])
```
**Benefits**:
- Reduced API calls from 4 to 3 per campaign (25-30% improvement)
- Less data transferred over network
- Faster processing for large listing trees
- More efficient for bulk operations on thousands of campaigns
**Performance**: On 1,612 campaign batch, reduced estimated processing time from 7-8 hours to 5-6 hours
**Key Principle**: Push filtering to the API layer with GAQL WHERE clauses instead of fetching all data and filtering in application code
**File**: google_ads_helpers.py lines 81-123
_#claude-session:2025-11-20_

### Managing Long-Running Campaign Processing Scripts
**Pattern**: Monitor and manage long-running scripts processing thousands of campaigns with progress tracking
**Use Case**: Processing 4,212 campaigns to remove CL2/CL3 exclusions over 5-6 hours
**Implementation**:
```python
# Script structure for long-running operations
def process_large_campaign_batch():
    processed_count = 0
    save_interval = 100  # Auto-save every 100 campaigns

    for idx, row in enumerate(sheet.iter_rows(min_row=2), start=2):
        # Skip already processed
        if row[STATUS_COL].value is not None:
            continue

        # Process campaign
        print(f"[{processed_count + 1}/{total_remaining}] Row {idx}: {campaign_name}")

        try:
            # Do work...
            row[STATUS_COL].value = True
            processed_count += 1

            # Auto-save at intervals
            if processed_count % save_interval == 0:
                print(f"\n💾 Progress saved at {processed_count} campaigns")
                workbook.save(EXCEL_FILE_PATH)

        except Exception as e:
            row[STATUS_COL].value = False
            print(f"   ❌ Error: {e}")

    # Final save
    workbook.save(EXCEL_FILE_PATH)
```
**Monitoring Running Script**:
```bash
# Check progress in background process
python3 -u script.py &  # Run in background with unbuffered output

# Monitor output with filtering
tail -f output.log | grep "Row"  # Watch progress
ps aux | grep python3  # Check process status
```
**Benefits**:
- Progress tracking with row numbers and campaign names
- Auto-save prevents data loss on crashes
- Can resume from last save point
- Clear error reporting per campaign
- Background execution for multi-hour runs
**Optimization Tips**:
- Use optimized API queries to reduce processing time
- Implement smart rate limiting (delay only after success)
- Skip rows with existing status values for resumability
- Save more frequently (every 50-100) for long runs
**Use Case**: 4,212 campaign batch processed over 5-6 hours with auto-saves every 100 campaigns
_#claude-session:2025-11-20_

### Preserving Item ID Exclusions in Listing Tree Modifications
**Pattern**: Read existing tree structure, extract item ID exclusions, and rebuild tree with preserved exclusions
**Use Case**: Adding shop exclusions (CL3) to campaigns that already have item ID exclusions
**Problem**: Simply rebuilding the tree with shop exclusions would destroy existing item ID targeting
**Solution**:
```python
def rebuild_tree_with_shop_exclusions(client, customer_id, ad_group_id, shop_names):
    # Step 1: Read existing tree including item IDs
    query = f"""
        SELECT
            ad_group_criterion.listing_group.case_value.product_item_id.value,
            ad_group_criterion.listing_group.case_value.product_custom_attribute.index,
            ad_group_criterion.listing_group.case_value.product_custom_attribute.value,
            ad_group_criterion.negative
        FROM ad_group_criterion
        WHERE ad_group_criterion.ad_group = '{ag_path}'
            AND ad_group_criterion.type = 'LISTING_GROUP'
    """

    # Extract item ID exclusions
    item_id_exclusions = []
    for row in results:
        if row.listing_group.case_value.product_item_id.value:
            if row.negative:  # Only preserve negative (exclusions)
                item_id_exclusions.append(row.listing_group.case_value.product_item_id.value)

    # Step 2: Remove old tree
    safe_remove_entire_listing_tree(client, customer_id, ad_group_id)

    # Step 3: Rebuild with conditional structure
    has_item_ids = len(item_id_exclusions) > 0

    # MUTATE 2: Create CL3 OTHERS as subdivision if item IDs exist
    if has_item_ids:
        # CL3 OTHERS as SUBDIVISION to hold item IDs
        cl3_others_op = create_listing_group_subdivision(
            parent=cl1_subdivision_tmp,
            dimension=dim_cl3_others
        )
        ops2.append(cl3_others_op)

        # ITEM_ID OTHERS under CL3 OTHERS (satisfies subdivision requirement)
        dim_item_others = client.get_type("ListingDimensionInfo")
        dim_item_others.product_item_id = client.get_type("ProductItemIdInfo")
        ops2.append(create_listing_group_unit_biddable(
            parent=cl3_others_tmp,
            dimension=dim_item_others,
            negative=False,
            bid=existing_bid
        ))
    else:
        # CL3 OTHERS as UNIT (simpler structure, no item IDs)
        ops2.append(create_listing_group_unit_biddable(
            parent=cl1_subdivision_tmp,
            dimension=dim_cl3_others,
            negative=False,
            bid=existing_bid
        ))

    # MUTATE 3: Add shop exclusions
    for shop_name in shop_names:
        ops3.append(create_listing_group_unit_biddable(
            parent=cl1_actual,
            dimension=dim_cl3_shop,
            negative=True
        ))

    # MUTATE 4: Add item ID exclusions (if any)
    if has_item_ids:
        for item_id in item_id_exclusions:
            dim_item_id = client.get_type("ListingDimensionInfo")
            dim_item_id.product_item_id.value = item_id
            ops4.append(create_listing_group_unit_biddable(
                parent=cl3_others_actual,
                dimension=dim_item_id,
                negative=True
            ))
```
**Tree Structure**:
```
ROOT → CL0 → CL1 →
  ├─ CL3=shop1 (unit, negative) - exclude shop 1
  ├─ CL3=shop2 (unit, negative) - exclude shop 2
  └─ CL3 OTHERS (subdivision) - for all other shops:
     ├─ ITEM_ID=xxx (unit, negative) - preserved exclusion
     ├─ ITEM_ID=yyy (unit, negative) - preserved exclusion
     └─ ITEM_ID OTHERS (unit, positive with bid)
```
**Benefits**:
- Preserves existing item ID exclusions when adding shop targeting
- Maintains backward compatibility (simpler structure when no item IDs)
- Allows combining multiple targeting dimensions without conflicts
**Tested**: Ad group 189081353036 with 2 item ID exclusions - both preserved successfully
_#claude-session:2025-11-21_

### CL1 Targeting Validation from Ad Group Name Suffix
**Pattern**: Enforce CL1 (Custom Label 1) targeting based on ad group name suffix to prevent targeting errors
**Use Case**: Ad groups ending with _a, _b, or _c must target the corresponding custom_label_1 value
**Problem**: Manual Excel entry could result in ad group name "campaign_b" but CL1="a" in tree, causing wrong products to be targeted
**Solution**:
```python
def rebuild_tree_with_shop_exclusions(client, customer_id, ad_group_id, shop_names):
    # Step 1: Get ad group name
    ag_name_query = f"""
        SELECT ad_group.name
        FROM ad_group
        WHERE ad_group.id = {ad_group_id}
    """
    ad_group_name = list(ga_service.search(query=ag_name_query))[0].ad_group.name

    # Step 2: Check for suffix requirement
    required_cl1 = None
    for suffix in ['_a', '_b', '_c']:
        if ad_group_name.endswith(suffix):
            required_cl1 = suffix[1:]  # "_b" → "b"
            print(f"Ad group name ends with '{suffix}' → CL1 must be '{required_cl1}'")
            break

    # Step 3: Read existing tree
    # ... extract cl1_value from existing tree ...

    # Step 4: Override CL1 if required
    if required_cl1:
        if cl1_value and cl1_value != required_cl1:
            print(f"Overriding existing CL1='{cl1_value}' with required CL1='{required_cl1}'")
        cl1_value = required_cl1

    # Step 5: Rebuild tree with validated CL1
    # ... use cl1_value in tree building ...
```
**Benefits**:
- Enforces naming convention automatically
- Prevents targeting wrong custom_label_1 segments
- Self-corrects manual errors in tree structure
- Ensures ad group suffix matches product targeting
**Example**: Ad group "PLA/Zwemvesten_b" will always have CL1="b" targeting, regardless of what was in the existing tree
_#claude-session:2025-11-21_

### Fixing SUBDIVISION_REQUIRES_OTHERS_CASE with Correct Mutate Grouping
**Pattern**: When creating listing tree subdivisions, provide each subdivision's OTHERS case in the SAME mutate operation
**Problem**: Creating CL0 as subdivision in MUTATE 1, then adding CL1 OTHERS under it in MUTATE 2 causes `LISTING_GROUP_SUBDIVISION_REQUIRES_OTHERS_CASE` error
**Root Cause**: Google Ads API validates subdivisions immediately and requires OTHERS case to exist in same operation
**Broken Code**:
```python
# MUTATE 1: ROOT + CL0 subdivision + CL0 OTHERS
ops1 = []
ops1.append(root_op)  # ROOT
ops1.append(cl0_subdivision_op)  # CL0 subdivision
ops1.append(create_unit(parent=root_tmp, dim=cl0_others))  # CL0 OTHERS under ROOT
# ERROR: CL0 subdivision has no OTHERS case!

# MUTATE 2: CL1 subdivision + CL1 OTHERS
ops2 = []
ops2.append(cl1_subdivision_op)  # CL1 subdivision under CL0
ops2.append(create_unit(parent=cl0_actual, dim=cl1_others))  # Too late!
```
**Fixed Code**:
```python
# MUTATE 1: ROOT + CL0 subdivision + BOTH required OTHERS cases
ops1 = []
ops1.append(root_op)  # ROOT subdivision
ops1.append(cl0_subdivision_op)  # CL0 subdivision under ROOT
# Add CL1 OTHERS under CL0 - satisfies CL0 subdivision requirement!
ops1.append(create_unit(parent=cl0_subdivision_tmp, dim=cl1_others, negative=True))
# Add CL0 OTHERS under ROOT - satisfies ROOT subdivision requirement!
ops1.append(create_unit(parent=root_tmp, dim=cl0_others, negative=True))

# MUTATE 2: CL1 subdivision + its OTHERS case
ops2 = []
ops2.append(cl1_subdivision_op)  # CL1 subdivision under CL0
# Add CL3 OTHERS under CL1 - satisfies CL1 subdivision requirement!
ops2.append(create_unit(parent=cl1_subdivision_tmp, dim=cl3_others, negative=False))

# MUTATE 3: Individual shop exclusions (OTHERS already exists)
ops3 = []
for shop_name in shop_names:
    ops3.append(create_unit(parent=cl1_actual, dim=cl3_shop, negative=True))
```
**Key Principle**: Each subdivision must have its OTHERS case sibling added in the SAME mutate operation using temporary resource names
**Testing**: Verified on ad group 161157611033 - tree builds successfully with correct hierarchy
**File**: campaign_processor.py lines 946-1154 (rebuild_tree_with_shop_exclusions function)
_#claude-session:2025-11-21_

### Working Copy Pattern for Excel File Safety
**Pattern**: Create timestamped working copy before processing to protect original file from corruption
**Use Case**: Long-running scripts that modify Excel files and may crash mid-execution
**Problem**: Script crashes can corrupt Excel files, losing all original data and progress
**Solution**:
```python
from datetime import datetime
import shutil

# Create timestamped working copy
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
working_copy_path = original_path.replace(".xlsx", f"_working_copy_{timestamp}.xlsx")

# Copy original to working copy
shutil.copy2(original_path, working_copy_path)

# Load and process working copy
workbook = load_workbook(working_copy_path)
# ... process workbook ...
workbook.save(working_copy_path)  # Save to copy, not original

# Original file remains untouched
```
**Benefits**:
- Original file never modified or opened for writing
- Safe from corruption if script crashes or API errors occur
- Multiple runs create separate timestamped copies for debugging
- Can compare working copies to understand what changed
- Easy rollback: just delete working copy and run again
**File Naming**: `dma_script_ivor_working_copy_20251121_174649.xlsx`
_#claude-session:2025-11-21_

### Openpyxl: Writing to Non-Existent Columns
**Problem**: Using `row[column_index]` fails with "tuple index out of range" when column doesn't exist
**Root Cause**: `sheet.iter_rows()` returns tuples of cells that already exist. If row has columns A-F, tuple has 6 cells (indices 0-5). Accessing index 6 (column G) fails.
**Broken Code**:
```python
for idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=False), start=2):
    # row is tuple of existing cells only
    if len(row) == 6:  # Only has columns A-F
        row[6].value = "error"  # FAILS: tuple index out of range
```
**Fixed Code**:
```python
for idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=False), start=2):
    # Use sheet.cell() to write to any column (creates if doesn't exist)
    sheet.cell(row=idx, column=7).value = "error"  # Works! (column G)
```
**Key Insight**: `sheet.cell(row=row_num, column=col_num)` creates cell if it doesn't exist, while `row[index]` only accesses existing cells in the tuple.
**Application**: When writing status/error messages, always use `sheet.cell()` method instead of row tuple indexing.
_#claude-session:2025-11-21_

### CL0 Validation from Excel Data
**Pattern**: Enforce Custom Label 0 targeting based on Excel data column before applying other modifications
**Use Case**: Exclusion sheet has "diepste_cat_id" column that must match CL0 in listing tree
**Problem**: Tree might have wrong CL0 value from previous operations or manual changes
**Solution**:
```python
def rebuild_tree_with_shop_exclusions(
    client, customer_id, ad_group_id,
    shop_names,
    required_cl0_value: str = None  # From Excel
):
    # Step 1: Read existing tree
    # ... extract cl0_value from tree ...

    # Step 2: Override CL0 if Excel specifies different value
    if required_cl0_value:
        if cl0_value and cl0_value != required_cl0_value:
            print(f"Overriding CL0='{cl0_value}' with required '{required_cl0_value}'")
        cl0_value = required_cl0_value

    # Step 3: Rebuild tree with validated CL0
    # ... build tree with cl0_value ...
```
**Validation Order**:
1. CL0 = diepste_cat_id (from Excel column D) - category targeting
2. CL1 = a/b/c (from ad group name suffix) - variant targeting
3. CL3 = shop exclusions (from Excel) - shop filtering
4. Item IDs = preserved from existing tree - product exclusions
**Benefits**: Self-correcting tree structure ensures targeting matches Excel data source
_#claude-session:2025-11-21_

### User-Friendly Error Messages in Excel
**Pattern**: Categorize and shorten error messages for better readability in Excel cells
**Use Case**: Writing error messages to Excel column that users will read and act on
**Implementation**:
```python
error_str = str(e)

# Categorize common errors with brief messages
if "SUBDIVISION_REQUIRES_OTHERS_CASE" in error_str:
    error_msg = "Tree structure error: missing OTHERS case"
elif "CONCURRENT_MODIFICATION" in error_str:
    error_msg = "Concurrent modification (retry needed)"
elif "NOT_FOUND" in error_str or "not found" in error_str.lower():
    error_msg = "Resource not found"
elif "INVALID_ARGUMENT" in error_str:
    error_msg = "Invalid argument in API call"
elif "PERMISSION_DENIED" in error_str:
    error_msg = "Permission denied"
elif "Could not find CL0" in error_str or "Could not find CL1" in error_str:
    error_msg = error_str[:80]  # Keep informative validation errors
else:
    # Generic error - truncate but keep key info
    error_msg = error_str[:80] if len(error_str) > 80 else error_str

# Write to Excel column
sheet.cell(row=row_num, column=ERROR_COLUMN).value = error_msg
```
**Benefits**:
- Users understand errors at a glance without reading full API traces
- Consistent error categories help identify patterns
- Shortened messages fit well in Excel cells
- Actionable messages (e.g., "retry needed") guide next steps
**Example Messages**:
- "Campaign not found" (not "Campaign not found: PLA/Category_a")
- "Tree structure error: missing OTHERS case" (not full API error text)
- "Concurrent modification (retry needed)" (with action hint)
_#claude-session:2025-11-21_

### Idempotent Campaign and Ad Group Creation
**Pattern**: Check for existing resources before creation to enable safe re-runs without duplicates
**Use Case**: Inclusion script needs to be re-runnable when adding new shops to existing campaigns
**Implementation**:
```python
def add_standard_shopping_campaign(client, customer_id, campaign_name, ...):
    google_ads_service = client.get_service("GoogleAdsService")

    # Check if campaign already exists by exact name match
    escaped_campaign_name = campaign_name.replace("'", "\\'")
    query = f"""
        SELECT campaign.id, campaign.resource_name, campaign.status
        FROM campaign
        WHERE campaign.name = '{escaped_campaign_name}'
    """
    response = google_ads_service.search(customer_id=customer_id, query=query)

    for row in response:
        if row.campaign.status != client.enums.CampaignStatusEnum.REMOVED:
            print(f"Campaign '{campaign_name}' already exists. Using existing.")
            return row.campaign.resource_name  # Reuse existing

    # Only create if not found
    campaign_operation = client.get_type("CampaignOperation")
    # ... create campaign ...
    return campaign_resource_name

def add_shopping_ad_group(client, customer_id, campaign_resource_name, ad_group_name, ...):
    google_ads_service = client.get_service("GoogleAdsService")

    # Check if ad group exists in this campaign
    escaped_ad_group_name = ad_group_name.replace("'", "\\'")
    query = f"""
        SELECT ad_group.id, ad_group.resource_name
        FROM ad_group
        WHERE ad_group.campaign = '{campaign_resource_name}'
        AND ad_group.name = '{escaped_ad_group_name}'
        AND ad_group.status != 'REMOVED'
    """
    response = google_ads_service.search(customer_id=customer_id, query=query)

    for row in response:
        print(f"Ad group '{ad_group_name}' already exists. Using existing.")
        return row.ad_group.resource_name, False  # Reuse existing

    # Only create if not found
    ad_group_operation = client.get_type("AdGroupOperation")
    # ... create ad group ...
    return ad_group_resource_name, True
```
**Benefits**:
- Script can be run multiple times on same data without errors
- Enables adding new shops to existing campaigns
- Safe recovery from partial failures
- Reduces API calls by reusing existing resources
**Key Points**:
- Always escape single quotes in names with backslash (\')
- Check for NOT REMOVED status to avoid reusing deleted resources
- Query by exact name match for campaigns
- Query by campaign + name for ad groups (multiple campaigns may have same ad group name)
**Use Case Example**: Re-running inclusion sheet after adding new shops to existing campaigns will:
1. Find and reuse existing campaign
2. Create only the new ad groups for new shops
3. Build listing trees for new ad groups only
_#claude-session:2025-11-19_

### Case-Insensitive Shop Name Comparison for Exclusions
**Problem**: When merging existing shop exclusions with new ones, duplicates were created due to case differences
**Symptoms**: Google Ads API rejected the rebuild with `LISTING_GROUP_ALREADY_EXISTS` error when trying to add shops that already existed with different case
**Root Cause**: Set comparison `shop not in existing_set` is case-sensitive. Existing exclusions stored as lowercase (e.g., `bobplaza.com`) but Excel had mixed case (`Bobplaza.com`)
**Broken Code**:
```python
# Case-sensitive comparison - treats "Bobplaza.com" and "bobplaza.com" as different
all_shop_exclusions = set(existing_shop_exclusions)
for shop in shop_names:
    if shop not in all_shop_exclusions:  # WRONG: case-sensitive
        all_shop_exclusions.add(shop)
# Result: both "bobplaza.com" and "Bobplaza.com" in set → API error
```
**Fixed Code**:
```python
# Case-insensitive comparison using lowercase mapping
existing_lower = {shop.lower(): shop for shop in existing_shop_exclusions}
all_shop_exclusions = set(existing_shop_exclusions)

for shop in shop_names:
    shop_lower = shop.lower()
    if shop_lower not in existing_lower:  # CORRECT: case-insensitive
        all_shop_exclusions.add(shop)
        existing_lower[shop_lower] = shop

# Sort case-insensitively for consistent ordering
shop_names = sorted(all_shop_exclusions, key=str.lower)
```
**Benefits**: Prevents duplicate entries regardless of case, preserves original casing in Google Ads
**File**: campaign_processor.py lines 1020-1039
_#claude-session:2025-12-11_

### Preserving Existing Shop Exclusions When Adding New Ones
**Problem**: Script was removing existing CL3 shop exclusions when processing exclusion sheet
**Symptoms**: Ad group with 8 shop exclusions ended up with only 4 after running script
**Root Cause**: `rebuild_tree_with_shop_exclusions` function was only preserving item ID exclusions, not existing CL3 shop exclusions
**Solution**: Read existing shop exclusions before rebuilding and merge with new ones:
```python
def rebuild_tree_with_shop_exclusions(client, customer_id, ad_group_id, shop_names, ...):
    # Step 1: Read existing tree
    existing_shop_exclusions = []
    for row in results:
        if case_value.product_custom_attribute:
            index = case_value.product_custom_attribute.index.name
            value = case_value.product_custom_attribute.value
            # Capture existing CL3 shop exclusions (NEGATIVE units with value)
            if index == 'INDEX3' and value:
                if row.listing_group.type.name == 'UNIT' and row.negative:
                    existing_shop_exclusions.append(value)

    # Step 2: Merge with new exclusions (case-insensitive)
    existing_lower = {shop.lower(): shop for shop in existing_shop_exclusions}
    all_shop_exclusions = set(existing_shop_exclusions)
    for shop in shop_names:
        if shop.lower() not in existing_lower:
            all_shop_exclusions.add(shop)
    shop_names = sorted(all_shop_exclusions, key=str.lower)

    # Step 3: Rebuild tree with merged exclusions
    # ... rebuild using shop_names which now includes all exclusions ...
```
**Benefits**: Script is now additive - existing exclusions preserved while new ones are added
**File**: campaign_processor.py lines 959-984, 1020-1039
_#claude-session:2025-12-11_

### Uitbreiding Script - Adding Shops to Category Campaigns
**Pattern**: Create campaigns per category/CL1 and add shop-specific ad groups with targeting
**Campaign Naming**: `PLA/{maincat} store_{cl1}` (e.g., "PLA/Klussen store_a")
**Ad Group Naming**: `PLA/{shop_name}_{cl1}` (e.g., "PLA/Coolblue.nl_a")
**Listing Tree Structure**:
```
ROOT (subdivision)
└─ CL1 = 'a' (subdivision)
   ├─ CL3 = shop_name (subdivision)
   │  ├─ CL4 = maincat_id (unit, positive, biddable)
   │  └─ CL4 OTHERS (unit, negative)
   └─ CL3 OTHERS (unit, negative)
└─ CL1 OTHERS (unit, negative)
```
**Excel Columns**: Shop name, Shop ID, maincat, maincat_id, cl1, budget, result
**Features**:
- Creates campaign if not found (with bid strategy from MCC + negative keyword list)
- Creates ad group if not found
- Builds listing tree targeting CL1, CL3 (shop), CL4 (maincat)
- Idempotent: skips rows already processed (checks result column)
**File**: campaign_processor.py process_uitbreiding_sheet() and build_listing_tree_for_uitbreiding()
_#claude-session:2025-12-16_

### Exclusion Script V2 - Using cat_ids Mapping Sheet
**Pattern**: Map maincat_id to deepest_cat values, then add shop exclusions to matching campaigns
**Use Case**: Exclude a shop from all campaigns under a specific maincat_id
**Excel Columns (uitsluiten)**: Shop name, Shop ID, maincat, maincat_id, cl1, result
**Excel Columns (cat_ids)**: maincat, maincat_id, deepest_cat, cat_id
**Campaign Naming**: `PLA/{deepest_cat}_{cl1}` (e.g., "PLA/Elektronica_a")
**Process Flow**:
1. Load cat_ids sheet into mapping: {maincat_id: [deepest_cat1, deepest_cat2, ...]}
2. For each row in uitsluiten, get shop_name, maincat_id, cl1
3. Look up all deepest_cats for that maincat_id
4. For each deepest_cat, find campaign PLA/{deepest_cat}_{cl1}
5. Find ad group(s) in that campaign
6. Add shop_name as CL3 exclusion (negative unit) to the ad group's listing tree
**Implementation**:
```python
def add_shop_exclusion_to_ad_group(client, customer_id, ad_group_id, shop_name):
    # 1. Read existing tree to find CL1 subdivision (parent for CL3)
    # 2. Check if shop already excluded (case-insensitive)
    # 3. Add new CL3 negative unit under CL1 subdivision
```
**File**: campaign_processor.py process_exclusion_sheet_v2(), add_shop_exclusion_to_ad_group(), load_cat_ids_mapping()
_#claude-session:2025-12-16_

### Rate Limiting for CONCURRENT_MODIFICATION Prevention
**Problem**: CONCURRENT_MODIFICATION errors when multiple mutate operations happen too quickly
**Solution**: Add time.sleep() between operations
**Recommended Delays**:
- Between mutate operations in tree building: 2 seconds
- After tree creation, before ad creation: 2 seconds
- Between rows: 2 seconds
- Between ad groups in exclusion processing: 1 second
- Between campaigns in exclusion processing: 1 second
**Trade-off**: Slower processing but much higher success rate
**File**: campaign_processor.py build_listing_tree_for_uitbreiding(), process_uitbreiding_sheet(), process_exclusion_sheet_v2()
_#claude-session:2025-12-16_

### No Build Tools Benefits
- Edit HTML/CSS/JS → Save → Refresh browser
- No npm install delays
- No webpack configuration
- No node_modules folder (saves 500MB+)
- Works identically on any machine with Docker

## Script Commands

### Google Ads Campaign Processor
```bash
# Main script execution
python3 campaign_processor.py

# Test Google Ads credentials
python3 test_google_ads_init.py

# Test full setup
python3 test_campaign_processor.py

# Install dependencies
pip3 install -r requirements.txt
```
_#claude-session:2025-11-11_

---
_Created from template: 2025-11-10_
_Updated: 2025-11-19_
