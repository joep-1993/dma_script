# TASKS
_Active task tracking. Update when: starting work, completing tasks, finding blockers._

## Current Sprint
_Active tasks for immediate work_

- [ ] Customize VISION.md with product goals #priority:high #estimate:15m
- [ ] Test Docker setup with docker-compose up #priority:medium #estimate:10m
- [ ] Verify AI integration works #priority:medium #estimate:15m

## In Progress
_Tasks currently being worked on (max 1-2 items)_

## Completed
_Recently finished tasks_

- [x] Fix tuple index out of range error when writing to column G #claude-session:2025-11-21 #priority:critical
  - Changed from row tuple indexing to sheet.cell() method for writing status/errors
  - Root cause: iter_rows() returns tuples of existing cells only, accessing non-existent columns failed
  - Solution: sheet.cell(row=row_num, column=col_num) creates cell if it doesn't exist
  - Applied to all status and error message writes
  - Error messages now always appear in column G regardless of existing columns
- [x] Improve error messages in column G with brief, user-friendly text #claude-session:2025-11-21 #priority:medium
  - Shortened "Campaign not found" message (campaign name visible in other columns)
  - Categorized API errors: "Tree structure error", "Concurrent modification", "Resource not found", etc.
  - Truncated generic errors to 80 chars max (was 100)
  - All error messages now brief and easy to understand at a glance in Excel
- [x] Add CL0 targeting validation from Excel diepste_cat_id column #claude-session:2025-11-21 #priority:high
  - Extract diepste_cat_id (column D) from exclusion sheet
  - Pass required_cl0_value to rebuild_tree_with_shop_exclusions
  - Override existing CL0 if it doesn't match Excel value
  - Validation order: CL0 (Excel) → CL1 (ad group name) → CL3 (shops) → Item IDs
  - Ensures correct category targeting before adding shop exclusions
- [x] Implement working copy feature to protect original Excel file #claude-session:2025-11-21 #priority:high
  - Create timestamped working copy before processing (format: *_working_copy_YYYYMMDD_HHMMSS.xlsx)
  - All processing happens on copy, not original file
  - Original file never modified or opened for writing
  - Safe from corruption if script crashes
  - Multiple runs create separate timestamped copies for debugging
- [x] Add item ID exclusion preservation to shop exclusion logic #claude-session:2025-11-21 #priority:high
  - Modified rebuild_tree_with_shop_exclusions() to read and preserve existing item ID exclusions
  - Creates CL3 OTHERS as subdivision (if item IDs exist) to hold item IDs underneath
  - Tree structure: ROOT → CL0 → CL1 → CL3 shops + CL3 OTHERS (subdivision) → Item IDs
  - Tested on ad group 189081353036 with 2 item ID exclusions - both preserved successfully
  - Script now preserves ALL existing targeting dimensions (CL0, item IDs, etc.) when adding shop exclusions
  - Maintains backward compatibility: CL3 OTHERS remains a unit if no item IDs present
- [x] Add CL1 targeting validation based on ad group name suffix #claude-session:2025-11-21 #priority:medium
  - Script detects if ad group name ends with _a, _b, or _c
  - Extracts letter without underscore as required CL1 value (e.g., "_b" → "b")
  - Overrides existing CL1 value with required value to ensure correct targeting
  - Prevents cross-contamination between a/b/c variants
  - Example: Ad group "PLA/Zwemvesten_b" will always have CL1="b" targeting
- [x] Fix LISTING_GROUP_SUBDIVISION_REQUIRES_OTHERS_CASE error in shop exclusions #claude-session:2025-11-21 #priority:critical
  - Restructured mutate operations to provide OTHERS cases with subdivisions in same operation
  - MUTATE 1: ROOT + CL0 subdivision + CL1 OTHERS (under CL0) + CL0 OTHERS (under ROOT)
  - MUTATE 2: CL1 subdivision + CL3 OTHERS (under CL1)
  - MUTATE 3: Individual shop exclusions only (no duplicate CL3 OTHERS)
  - Tested on ad group 161157611033 - verified correct hierarchical tree structure
  - Key fix: Each subdivision must have its OTHERS case in the SAME mutate operation

- [x] Optimize safe_remove_entire_listing_tree() to reduce API calls #claude-session:2025-11-20 #priority:high
  - Rewrote function to query only for root node instead of all listing groups
  - Changed from querying all nodes to filtered query: WHERE parent_ad_group_criterion IS NULL
  - Reduced API calls from 4 to 3 per campaign (25-30% improvement)
  - Updated google_ads_helpers.py lines 81-123
  - Restarted campaign rebuild script with optimized code
  - Performance improvement reduces estimated processing time from 7-8 hours to 5-6 hours
- [x] Fix and test shopping product ad creation #claude-session:2025-11-20 #priority:high
  - Created add_shopping_product_ad() function in google_ads_helpers.py
  - Fixed protobuf union field issue using CopyFrom on _pb objects
  - Key fix: ad_group_ad.ad._pb.shopping_product_ad.CopyFrom(shopping_product_ad_info._pb)
  - Function creates shopping product ads with ENABLED status
  - Checks for existing ads before creation to prevent duplicates
  - Integrated into process_inclusion_sheet() - ads created after listing tree
  - Shopping ads automatically pull product data from Merchant Center feed
  - Tested and verified working on campaign 23273663505
  - Created 3 ads successfully across all ad groups
- [x] Make inclusion script idempotent with existing resource checks #claude-session:2025-11-19 #priority:medium
  - Modified campaign lookup to search by exact campaign name instead of embedded metadata
  - Added check for existing campaigns before creation (reuses if found)
  - Added check for existing ad groups by name within campaign before creation
  - Fixed GAQL single quote escaping issue (apostrophes in names like "Auto's")
  - Changed from double single quotes ('') to backslash escaping (\') for GAQL
  - Script now safe to re-run without creating duplicate campaigns/ad groups
- [x] Complete 872K campaign migration with optimized rate limiting #claude-session:2025-11-19 #priority:high
  - Tested 0.2s rate limiting on full 872,571 campaign dataset
  - Implemented smart delay strategy: only delay after successful operations (not after errors/"not found")
  - Achieved ~10x speedup: 8-9 hours vs 5-10 days estimate
  - Successfully migrated 1,766 campaigns to Custom Label 3 (INDEX3)
  - 5,008 campaigns failed (CONCURRENT_MODIFICATION) - marked for potential retry
  - 865,797 campaigns "not found" (quickly skipped with no delays)
  - Updated LEARNINGS.md with optimal rate limiting findings
  - Updated BACKLOG.md technical debt item with results
- [x] Fix exclusion migration data loss and API rate limiting #claude-session:2025-11-19 #priority:critical
  - Discovered migration lost 3 hours of work after crash (no incremental saves)
  - Added incremental saving every 50 campaigns to process_exclusion_sheet()
  - Added rate limiting (0.5s delay) between campaigns to prevent API overload
  - Fixed CONCURRENT_MODIFICATION error handling to properly raise exceptions
  - Changed rebuild_tree functions to raise instead of return on errors
  - Created test_improved_migration.py to validate improvements on small batches
  - Prevents data loss and reduces CONCURRENT_MODIFICATION errors significantly
- [x] Fix concurrent modification in ad group creation #claude-session:2025-11-12 #priority:critical
  - Fixed add_shopping_ad_group() to check for SPECIFIC ad group name instead of ANY ad group
  - Changed query from checking campaign existence to checking (campaign + ad_group_name)
  - Prevents multiple shops from getting same ad group ID when processing same campaign
  - Added 1 second delay after listing tree creation to avoid race conditions
- [x] Fix exclusion logic to preserve hierarchical tree structures #claude-session:2025-11-12 #priority:critical
  - Rewrote rebuild_tree_with_custom_label_3_exclusion() to preserve CL0 and CL1 structures
  - Collects BOTH subdivision nodes (hierarchy) and unit nodes (targeting)
  - Rebuilds hierarchy level by level following pattern from example_functions.txt
  - Converts positive CL0 units to subdivisions when adding CL3 exclusions
  - Final structure: ROOT → CL1 → CL0 → CL3 (preserves all existing targeting)
- [x] Implement multiple ad groups per campaign structure #claude-session:2025-11-12 #priority:high
  - Campaigns now contain multiple ad groups (one per shop)
  - Campaign pattern: PLA/{maincat} {shop_name}_{custom_label_1}
  - Ad group pattern: PLA/{shop_name}_{custom_label_1}
  - Each ad group has separate listing tree for its shop
  - Enables proper concurrent processing of multiple shops in same campaign
- [x] Implement resumable processing logic #claude-session:2025-11-12 #priority:medium
  - Script now skips rows with existing status values (TRUE/FALSE)
  - Enables continuing from where script left off after failures
  - Inclusion sheet checks column G, exclusion sheet checks column F
- [x] Update Excel column structure with budget support #claude-session:2025-11-12 #priority:medium
  - Inclusion sheet now 7 columns: A-G (added budget in column F)
  - Status column moved from F to G
  - Budget read from Excel and converted to micros for campaign creation
- [x] Integrate MCC account bid strategies #claude-session:2025-11-12 #priority:high
  - Searches bid strategies in MCC account (3011145605) instead of client account
  - Maps custom label 1 (a/b/c) to specific bid strategies: "DMA: Elektronica shops A/B/C"
  - Applies portfolio bid strategy from MCC to campaigns in client account
- [x] Fix listing tree SUBDIVISION_REQUIRES_OTHERS_CASE error #claude-session:2025-11-12 #priority:high
  - Resolved critical Google Ads API error when creating listing tree subdivisions
  - Solution: Provide OTHERS case in same mutate operation using temporary resource name
  - Updated build_listing_tree_for_inclusion to follow correct pattern from example_functions.txt
- [x] Refactor inclusion logic with campaign/ad group creation #claude-session:2025-11-11 #priority:critical
  - Groups rows by (shop_name, maincat, custom_label_1) before processing
  - Creates campaigns with pattern: PLA/{maincat} {shop_name}_{custom_label_1}
  - Creates ad groups with pattern: PLA/{shop_name}_{custom_label_1}
  - Builds hierarchical listing tree: Shop (CL3) → Categories (CL0)
  - Updated column structure: 8 columns for inclusion, 6 for exclusion
- [x] Fix multiple critical errors in campaign processor #claude-session:2025-11-11 #priority:high
  - Fixed tracking_url_template "Too short" error (only set when non-empty)
  - Fixed column index mismatch between inclusion/exclusion sheets
  - Fixed undefined client parameter in labelCampaign function
  - Added merchant_center_account_id (140784594), budget (10 EUR), country (NL)
- [x] Implement Google Ads campaign processor script #claude-session:2025-11-11 #priority:critical
  - Full Python script with Excel processing, OS detection, and Google Ads API integration
  - Processes inclusion (toevoegen) and exclusion (uitsluiten) sheets
  - Auto-rebuilds listing trees with Custom Label 3 targeting
- [x] Configure Google Ads API credentials in .env #claude-session:2025-11-11 #priority:high
  - Set up GOOGLE_ADS_DEVELOPER_TOKEN, GOOGLE_ADS_CLIENT_ID, GOOGLE_ADS_CLIENT_SECRET, GOOGLE_ADS_REFRESH_TOKEN
  - Configured automatic credential loading from environment
- [x] Implement helper functions for listing tree operations #claude-session:2025-11-11 #priority:high
  - safe_remove_entire_listing_tree, create_listing_group_subdivision, create_listing_group_unit_biddable
  - list_listing_groups_with_depth, next_id for temporary resource names
  - ensure_campaign_label_exists, script_label = "DMA_SCRIPT_JVS"
  - add_shopping_ad_group with 2 cent standard bids
- [x] Review project setup and configuration #claude-session:2025-11-11 #priority:high
- [x] Update .env with required API keys #claude-session:2025-11-11 #priority:high
- [x] Initialize project with CC1 Boilerplate V2 #claude-session:2025-11-10

## Blocked
_Tasks waiting on dependencies_

---

## Task Tags Guide

**Priority:**
- `#priority:high` - Urgent, blocking other work
- `#priority:medium` - Important, should be done soon
- `#priority:low` - Nice to have, can defer

**Estimates:**
- `#estimate:5m` `#estimate:1h` `#estimate:2d` - Time estimates

**Organization:**
- `#spec:feature-name` - Links to cc1/specs/feature-name.md
- `#blocked-by:dependency` - What's blocking this task
- `#claude-session:YYYY-MM-DD` - Claude Code session date

**Example task with spec:**
```markdown
- [ ] Implement user authentication #priority:high #estimate:2d #spec:jwt-auth-system
```

---

## Usage Notes

**Starting work:**
1. Move task from "Current Sprint" to "In Progress"
2. Update status to `in_progress` in linked spec (if applicable)
3. Start working, referencing spec for constraints/context

**Completing work:**
1. Move task from "In Progress" to "Completed"
2. Update spec status to `done` (if applicable)
3. Add completion date with `#completed:YYYY-MM-DD`

**Getting blocked:**
1. Move task to "Blocked" section
2. Add `#blocked-by:reason` tag
3. Create unblocking task if needed

**Weekly cleanup:**
- Archive completed tasks older than 1 week
- Review "Current Sprint" and reprioritize
- Remove stale tasks no longer relevant
