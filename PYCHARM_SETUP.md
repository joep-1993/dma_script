# Running from PyCharm - Quick Guide

## 1. Install Dependencies

### Option A: PyCharm Terminal (Recommended)
1. Open PyCharm
2. Click on **Terminal** tab at the bottom of the window
3. Run:
   ```bash
   pip install -r requirements.txt
   ```

### Option B: Command Prompt/PowerShell
1. Navigate to the project folder
2. Run:
   ```bash
   cd /home/jschagen/dma-shop-campaigns
   pip install -r requirements.txt
   ```

## 2. Configure Google Ads Credentials

Add your Google Ads API credentials to the `.env` file:

```env
# Google Ads API Credentials
GOOGLE_ADS_DEVELOPER_TOKEN=your_actual_developer_token
GOOGLE_ADS_CLIENT_ID=your_actual_client_id.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=your_actual_client_secret
GOOGLE_ADS_REFRESH_TOKEN=your_actual_refresh_token
GOOGLE_ADS_LOGIN_CUSTOMER_ID=1234567890  # Optional
```

## 3. Add Your Helper Functions

Open `google_ads_helpers.py` and paste your existing helper functions:
- `safe_remove_entire_listing_tree()`
- `create_listing_group_subdivision()`
- `create_listing_group_unit_biddable()`

## 4. Configure the Script

Edit `campaign_processor.py` line 45-47 if needed:

```python
CUSTOMER_ID = "3800751597"  # Your customer ID
EXCEL_FILE_PATH = "c:/Users/JoepvanSchagen/Downloads/dma_script_ivor.xlsx"  # Your Excel file path
DEFAULT_BID_MICROS = 200_000  # €0.20
```

## 5. Run from PyCharm

### Method 1: Right-click Run (Easiest)
1. Open `campaign_processor.py` in PyCharm
2. Right-click anywhere in the editor
3. Select **"Run 'campaign_processor'"**

### Method 2: Run Configuration
1. Click the **Run** menu → **Run...**
2. Select **campaign_processor**
3. Press Enter

### Method 3: Play Button
1. Open `campaign_processor.py`
2. Click the green **▶ Play button** in the top-right corner

### Method 4: Terminal
1. Open Terminal in PyCharm
2. Run:
   ```bash
   python campaign_processor.py
   ```

## Expected Output

You should see:

```
======================================================================
DMA SHOP CAMPAIGNS PROCESSOR
======================================================================
Customer ID: 3800751597
Excel File: c:/Users/JoepvanSchagen/Downloads/dma_script_ivor.xlsx
======================================================================

Loading Google Ads credentials from .env file...
✅ Google Ads client initialized successfully from .env
Loading Excel file: c:/Users/JoepvanSchagen/Downloads/dma_script_ivor.xlsx
✅ Excel file loaded successfully
   Available sheets: ['toevoegen', 'uitsluiten']

======================================================================
PROCESSING INCLUSION SHEET: 'toevoegen'
======================================================================
...
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'google'"
- **Solution**: Install dependencies with `pip install -r requirements.txt`

### "Error initializing Google Ads client"
- **Solution**: Check your `.env` file has correct Google Ads credentials
- Make sure there are no spaces around the `=` sign
- Example: `GOOGLE_ADS_DEVELOPER_TOKEN=abc123` ✅
- Not: `GOOGLE_ADS_DEVELOPER_TOKEN = abc123` ❌

### "Could not import helper functions"
- **Solution**: Add your existing helper functions to `google_ads_helpers.py`

### "FileNotFoundError: [Errno 2] No such file or directory: 'c:/Users/JoepvanSchagen/Downloads/dma_script_ivor.xlsx'"
- **Solution**: Update `EXCEL_FILE_PATH` in `campaign_processor.py` with the correct path
- On Windows, use forward slashes `/` or double backslashes `\\`
- Example: `"c:/Users/YourName/Downloads/file.xlsx"` or `"c:\\Users\\YourName\\Downloads\\file.xlsx"`

### "Permission denied" when saving Excel
- **Solution**: Close the Excel file if it's open in Microsoft Excel
- The script needs to write to the file

## What the Script Does

1. **Loads credentials** from your `.env` file
2. **Reads Excel file** with two sheets:
   - `toevoegen` (inclusion) - Targets specific shops
   - `uitsluiten` (exclusion) - Excludes specific shops
3. **For each row**:
   - Finds the campaign by pattern
   - Retrieves the ad group
   - Rebuilds the listing tree with Custom Label 3 targeting
   - Updates column F with TRUE (success) or FALSE (failed)
4. **Saves results** back to the Excel file

## File Structure

```
campaign_processor.py          ← Main script (RUN THIS!)
google_ads_helpers.py          ← Add your helper functions here
requirements.txt               ← Dependencies
.env                          ← Your credentials (keep secret!)
.env.example                  ← Template for .env
CAMPAIGN_PROCESSOR_README.md  ← Full documentation
PYCHARM_SETUP.md              ← This file
```

## Next Steps

1. ✅ Install dependencies: `pip install -r requirements.txt`
2. ✅ Add Google Ads credentials to `.env`
3. ✅ Add helper functions to `google_ads_helpers.py`
4. ✅ Update `EXCEL_FILE_PATH` if needed
5. ✅ Right-click `campaign_processor.py` → **Run**
