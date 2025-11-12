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
