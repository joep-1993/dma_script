# DMA Shop Campaigns Processor - Setup Guide

## Overview
This script processes Excel files with shop campaign data and updates Google Ads listing trees with custom label 3 targeting (shop name).

## Files Created
- `campaign_processor.py` - Main script
- `google_ads_helpers.py` - Helper functions (needs your existing functions)
- `requirements.txt` - Updated with new dependencies

## Setup Instructions

### 1. Add Your Helper Functions

Open `google_ads_helpers.py` and add your existing helper functions:

**Required functions:**
- `safe_remove_entire_listing_tree(client, customer_id, ad_group_id)`
- `create_listing_group_subdivision(client, customer_id, ad_group_id, parent_ad_group_criterion_resource_name, listing_dimension_info)`
- `create_listing_group_unit_biddable(client, customer_id, ad_group_id, parent_ad_group_criterion_resource_name, listing_dimension_info, targeting_negative, cpc_bid_micros)`

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

New dependencies added:
- `google-ads==24.1.0` - Google Ads API client
- `openpyxl==3.1.2` - Excel file processing

### 3. Configure Google Ads Credentials

Add these variables to your `.env` file:

```env
# Google Ads API Credentials
GOOGLE_ADS_DEVELOPER_TOKEN=your_developer_token_here
GOOGLE_ADS_CLIENT_ID=your_client_id_here
GOOGLE_ADS_CLIENT_SECRET=your_client_secret_here
GOOGLE_ADS_REFRESH_TOKEN=your_refresh_token_here
GOOGLE_ADS_LOGIN_CUSTOMER_ID=your_login_customer_id_here  # Optional
```

Alternatively, you can use a `google-ads.yaml` file if preferred.

### 4. Configure the Script

Edit `campaign_processor.py` to set:

```python
CUSTOMER_ID = "3800751597"  # Your customer ID
EXCEL_FILE_PATH = "c:/Users/JoepvanSchagen/Downloads/dma_script_ivor.xlsx"  # Your Excel file
DEFAULT_BID_MICROS = 200_000  # Default bid (€0.20)
```

## Excel File Requirements

The Excel file should have two sheets:

### Sheet 1: "toevoegen" (Inclusion)
Columns:
1. **Shop name** - Shop name to target
2. **Shop ID** - Shop ID
3. **cat_toevoegen** - Category to add
4. **Diepste cat ID** - Deepest category ID
5. **custom label 1** - Custom label 1 value
6. **Status** - Will be updated with TRUE/FALSE

### Sheet 2: "uitsluiten" (Exclusion)
Same column structure as above, but with:
3. **cat_uitsluiten** - Category to exclude

## How It Works

### Inclusion Logic (Sheet: "toevoegen")
For each row:
1. Searches for campaign: `PLA/{cat_toevoegen}_{custom_label_1}`
2. Retrieves ad group from campaign
3. Rebuilds listing tree to **TARGET** shop name via custom label 3:
   ```
   Root SUBDIVISION
   ├─ Custom Label 3 OTHERS [NEGATIVE] → Block all other shops
   └─ Custom Label 3 = shop_name [POSITIVE] → Only show this shop
   ```
4. Updates column F with TRUE (success) or FALSE (failed)

### Exclusion Logic (Sheet: "uitsluiten")
For each row:
1. Searches for campaign: `PLA/{cat_uitsluiten}_{custom_label_1}`
2. Retrieves ad group from campaign
3. Rebuilds listing tree to **EXCLUDE** shop name via custom label 3:
   ```
   Root SUBDIVISION
   ├─ Custom Label 3 OTHERS [POSITIVE] → Show all shops
   └─ Custom Label 3 = shop_name [NEGATIVE] → Block this shop
   ```
4. Updates column F with TRUE (success) or FALSE (failed)

## Running the Script

```bash
python campaign_processor.py
```

The script will:
1. Load the Excel file
2. Process the inclusion sheet ("toevoegen")
3. Process the exclusion sheet ("uitsluiten")
4. Save results back to the Excel file (column F)
5. Print detailed progress and summary

## Output Example

```
======================================================================
DMA SHOP CAMPAIGNS PROCESSOR
======================================================================
Customer ID: 3800751597
Excel File: c:/Users/JoepvanSchagen/Downloads/dma_script_ivor.xlsx
======================================================================

✅ Google Ads client initialized successfully
Loading Excel file: ...
✅ Excel file loaded successfully

======================================================================
PROCESSING INCLUSION SHEET: 'toevoegen'
======================================================================

[Row 2] Processing inclusion for shop: Shop A
         Category: Electronics, Custom Label 1: A
   Searching for campaign: PLA/Electronics_A
   ✅ Found campaign: PLA/Electronics_A (ID: 12345)
   ✅ Found ad group: Ad Group 1 (ID: 67890)
   Rebuilding tree to TARGET shop 'Shop A' (custom label 3)
   ✅ Tree rebuilt: ONLY targeting shop 'Shop A'
   ✅ SUCCESS - Row 2 completed

======================================================================
INCLUSION SHEET SUMMARY: 10/10 rows processed successfully
======================================================================
```

## Important Notes

1. **Custom Label 3**: The script uses Custom Label 3 (INDEX2) for shop name targeting
2. **Overwrites Trees**: Each operation completely rebuilds the listing tree
3. **Excel Updates**: Column F is updated with TRUE/FALSE results
4. **Error Handling**: Rows with errors are marked FALSE and processing continues
5. **Campaign Pattern**: Campaigns must match pattern `PLA/{category}_{custom_label_1}`

## Troubleshooting

### "Could not import helper functions"
- Add your helper functions to `google_ads_helpers.py`

### "Error initializing Google Ads client"
- Check `google-ads.yaml` configuration
- Verify credentials are valid

### "Campaign not found"
- Verify campaign naming pattern matches `PLA/{category}_{custom_label_1}`
- Check if campaign is active (not REMOVED)

### "Error saving Excel file"
- Close the Excel file if it's open in Excel
- Check file permissions

## Contact
For issues or questions, refer to your Google Ads API documentation or the example functions in `example_functions.txt`.
