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
**Symptoms**: Cannot add CL0 (Custom Label 0) and CL3 (Custom Label 3) as siblings under same parent
**Root Cause**: Google Ads requires all sibling nodes in listing tree to have the SAME dimension type. Cannot mix CL0, CL1, CL3 as siblings.
**Solution**: Build hierarchical tree where each level has ONE dimension type:
```
ROOT (level 0)
└─ CL1 = 'a' (level 1 - only CL1 nodes)
   └─ CL0 = '9005157' (level 2 - only CL0 nodes)
      ├─ CL3 = 'shop.nl' (level 3 - only CL3 nodes)
      └─ CL3 = OTHERS (level 3 - only CL3 nodes)
```
**Pattern**: When adding deeper nesting, convert positive UNIT nodes to SUBDIVISIONS:
```python
# If CL0 was a positive UNIT node, convert to SUBDIVISION
cl0_subdivision_op = create_listing_group_subdivision(
    parent=deepest_parent,
    dimension=dim_cl0  # CL0 = '9005157'
)

# Then nest CL3 under it
ops.append(create_listing_group_unit(
    parent=cl0_subdivision_tmp,
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
│  ├─ Category (Custom Label 0) = "Cat1" [UNIT, POSITIVE, biddable]
│  ├─ Category (Custom Label 0) = "Cat2" [UNIT, POSITIVE, biddable]
│  └─ OTHERS (Custom Label 0) [UNIT, NEGATIVE]
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

### Preserving Hierarchical Listing Tree Structures
**Pattern**: When modifying listing trees, preserve existing custom label subdivisions and units by collecting BOTH types and rebuilding hierarchy
**Problem**: Exclusion logic was destroying existing CL0 and CL1 targeting when adding CL3 shop exclusions
**Solution**:
```python
# Step 1: Collect BOTH subdivisions (hierarchy) and units (targeting)
custom_label_subdivisions = []  # CL0/CL1 subdivision nodes
custom_label_structures = []     # CL0/CL1 unit nodes

for row in results:
    if is_subdivision:
        custom_label_subdivisions.append({
            'index': index_name,  # e.g., 'INDEX0' or 'INDEX1'
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

# Step 2: Rebuild subdivisions hierarchically (ROOT → CL1 → CL0)
# Step 3: Convert positive CL0 units to subdivisions
# Step 4: Nest CL3 exclusions under CL0 subdivisions
```
**Key Insight**: Must differentiate between SUBDIVISION nodes (define hierarchy) and UNIT nodes (targeting/exclusions). When adding deeper nesting, convert units to subdivisions.
**Reference**: Follow pattern from `rebuild_tree_with_label_and_item_ids` in example_functions.txt
_#claude-session:2025-11-12_

### Converting Units to Subdivisions for Deeper Nesting
**Pattern**: When adding deeper custom label levels to existing tree, convert positive UNIT nodes to SUBDIVISION nodes
**Use Case**: Have CL0='9005157' as positive UNIT with bid. Need to add CL3 shop exclusions under it.
**Implementation**:
```python
# Original structure:
# ROOT → CL1='a' [SUBDIVISION] → CL0='9005157' [UNIT, positive, bid=1.00€]

# Convert CL0 unit to subdivision
cl0_subdivision_op = create_listing_group_subdivision(
    parent=cl1_actual,
    dimension=dim_cl0  # CL0 = '9005157'
)
ops.append(cl0_subdivision_op)

# Add CL0 OTHERS (negative)
ops.append(create_listing_group_unit(
    parent=cl0_subdivision_tmp,
    dimension=dim_cl0_others,
    negative=True
))

# Add CL3 OTHERS (positive, inherits bid)
ops.append(create_listing_group_unit(
    parent=cl0_subdivision_tmp,
    dimension=dim_cl3_others,
    negative=False,
    bid=original_bid  # Preserve the bid from CL0 unit
))

# Add CL3 shop exclusion (negative)
ops.append(create_listing_group_unit(
    parent=cl0_subdivision_actual,  # From mutate response
    dimension=dim_cl3_shop,
    negative=True
))

# New structure:
# ROOT → CL1='a' [SUBDIVISION] → CL0='9005157' [SUBDIVISION]
#                                  ├─ CL0 OTHERS [UNIT, negative]
#                                  ├─ CL3 OTHERS [UNIT, positive, bid=1.00€]
#                                  └─ CL3='shop.nl' [UNIT, negative]
```
**Benefits**: Preserves original bid, maintains tree validity, enables deeper nesting
**Reference**: Study `rebuild_tree_with_label_and_item_ids` in example_functions.txt lines 200-250
_#claude-session:2025-11-12_

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
_Updated: 2025-11-12_
