# TASKS
_Active task tracking. Update when: starting work, completing tasks, finding blockers._

## Current Sprint
_Active tasks for immediate work_

- [ ] Review project setup and configuration #priority:high #estimate:10m
- [ ] Customize VISION.md with product goals #priority:high #estimate:15m
- [ ] Update .env with required API keys #priority:high #estimate:5m
- [ ] Test Docker setup with docker-compose up #priority:medium #estimate:10m
- [ ] Verify AI integration works #priority:medium #estimate:15m

## In Progress
_Tasks currently being worked on (max 1-2 items)_

## Completed
_Recently finished tasks_

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
