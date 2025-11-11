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
