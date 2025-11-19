"""
Process ONLY the exclusion sheet with Custom Label 3 (INDEX3) exclusions.
Includes incremental saving and rate limiting.
"""

import sys
from openpyxl import load_workbook
from campaign_processor import (
    initialize_google_ads_client,
    process_exclusion_sheet,
    EXCEL_FILE_PATH,
    SHEET_EXCLUSION,
    CUSTOMER_ID
)


def main():
    print("="*70)
    print("PROCESSING EXCLUSION SHEET ONLY")
    print("Custom Label 3 (INDEX3) Shop Exclusions")
    print("="*70)

    # Initialize Google Ads client
    print("\nInitializing Google Ads client...")
    client = initialize_google_ads_client()
    print("✅ Client initialized")

    # Load Excel file
    print(f"\nLoading Excel file: {EXCEL_FILE_PATH}")
    try:
        workbook = load_workbook(filename=EXCEL_FILE_PATH)
        print("✅ Excel file loaded")
    except Exception as e:
        print(f"❌ Error loading Excel file: {e}")
        return

    # Process exclusion sheet with incremental saving and rate limiting
    print("\n" + "="*70)
    print("PROCESSING EXCLUSION SHEET")
    print("="*70)

    try:
        process_exclusion_sheet(
            client=client,
            workbook=workbook,
            customer_id=CUSTOMER_ID,
            save_interval=25,      # Save every 25 campaigns (more frequent)
            rate_limit_seconds=0.2 # 0.2s delay between campaigns (faster)
        )
        print("\n✅ Exclusion sheet processing completed")
    except Exception as e:
        print(f"\n❌ Error processing exclusion sheet: {e}")
        import traceback
        traceback.print_exc()

    # Final save
    print("\n" + "="*70)
    print("SAVING FINAL RESULTS")
    print("="*70)
    try:
        workbook.save(EXCEL_FILE_PATH)
        print(f"✅ Excel file saved: {EXCEL_FILE_PATH}")
    except Exception as e:
        print(f"❌ Error saving Excel file: {e}")

    print("\n" + "="*70)
    print("COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
