# CC1 Documentation System

**CC1** is a structured documentation system designed for **AI-assisted development**. It maintains institutional knowledge across Claude Code sessions, enabling effective collaboration between humans and AI.

---

## Philosophy

Traditional documentation fails because it's either:
- Too heavy (comprehensive docs that nobody maintains)
- Too light (scattered notes that provide no context)

**CC1 solves this by being:**
- **Lightweight** - Only document what matters for decisions
- **AI-optimized** - Structured for context injection into LLMs
- **Action-oriented** - Tied directly to active work
- **Evidence-based** - Grounded in metrics and user feedback

---

## File Structure

```
cc1/
├── README.md           # This file - system guide
├── VISION.md          # Product vision + Opportunity Solution Tree (OST)
├── TASKS.md           # Active task tracking (what's being worked on)
├── LEARNINGS.md       # Knowledge capture (errors, patterns, solutions)
├── PROJECT_INDEX.md   # Technical reference (architecture, decisions)
├── BACKLOG.md         # Future planning (deferred features, ideas)
└── specs/             # Feature specifications (solutions to opportunities)
    ├── _template.md   # Template for new specs
    └── feature-name.md # Individual feature specs
```

---

## Core Workflow

### 1. Discovery Phase (Define Problems)

**Start with opportunities, not solutions:**

```
User Research/Feedback
    ↓
Add to VISION.md as Opportunity
    ↓
Validate with evidence (metrics, user quotes)
    ↓
Brainstorm multiple solutions
```

**When to create a spec:**
- Multi-day features
- Security-sensitive work
- Solutions needing context injection (reference existing patterns)

### 2. Planning Phase (Design Solutions)

**For features requiring specs:**

```
Copy specs/_template.md → specs/solution-name.md
    ↓
Fill out (10-20 minutes):
  - Link to opportunity in VISION.md
  - Hypothesis (what will this achieve?)
  - Constraints (what NOT to do)
  - Context injection (existing code to reference)
    ↓
Add to TASKS.md with #spec:solution-name tag
    ↓
Mark spec status: draft → approved
```

### 3. Implementation Phase (Build)

**Active development:**

```
Work from TASKS.md
    ↓
Reference spec for constraints/context
    ↓
Update spec status: approved → implementing
    ↓
Capture blockers/learnings in LEARNINGS.md
    ↓
Mark tasks complete in TASKS.md
```

### 4. Validation Phase (Measure Results)

**After shipping:**

```
Measure against success metrics
    ↓
Update VISION.md with results (✅ validated or ❌ invalidated)
    ↓
Update spec status: implementing → done
    ↓
Move task to "Completed" in TASKS.md
```

---

## Decision Flowchart

**"Where should I document X?"**

```
Is it about WHAT to build or WHY?
├─ Yes → VISION.md (opportunities, evidence, outcomes)
│
└─ No → Is it about ACTIVE work?
    ├─ Yes → TASKS.md (current sprint, in-progress, blockers)
    │
    └─ No → Is it about HOW to build something?
        ├─ Yes → Need a spec?
        │   ├─ Multi-day feature → specs/feature-name.md
        │   ├─ Security-sensitive → specs/feature-name.md
        │   ├─ Needs context injection → specs/feature-name.md
        │   └─ Simple task → Just TASKS.md
        │
        └─ No → Is it about something we LEARNED?
            ├─ Yes → LEARNINGS.md (errors, patterns, gotchas)
            │
            └─ No → Is it technical reference?
                ├─ Yes → PROJECT_INDEX.md (architecture, decisions)
                │
                └─ Is it for LATER?
                    └─ Yes → BACKLOG.md (future ideas, deferred work)
```

---

## File-Specific Guides

### VISION.md (Opportunity Solution Tree)
**Purpose:** Define WHAT problems exist and WHY they matter

**Structure:**
- Product vision (target outcome)
- Current focus opportunities (active problems being solved)
- Solutions being explored (hypotheses, specs, status)
- Results (validated/invalidated learnings)
- Backlog opportunities (future problems to tackle)

**Update when:**
- Discovering new user problems
- Starting work on an opportunity
- Completing experiments (add results)

**Example entry:**
```markdown
### 🎯 Opportunity: api-response-time-degradation
**Problem:** API endpoints taking >2s to respond under load
**Evidence:** P95 latency increased from 300ms to 2.1s (last week)
**Impact:** 20% increase in user complaints, 15% drop in API usage

#### Solutions:
- 💡 Query Caching Layer 🔄
  - Hypothesis: Redis cache reduces DB hits by 70%, latency <500ms
  - Spec: cc1/specs/query-caching.md
  - Status: Implementing
```

---

### TASKS.md (Active Work Tracking)
**Purpose:** Track what's being worked on RIGHT NOW

**Structure:**
- Current Sprint (immediate work)
- In Progress (actively being done)
- Completed (recently finished)
- Blocked (waiting on dependencies)

**Update when:**
- Starting work (move to "In Progress")
- Completing tasks (move to "Completed")
- Getting blocked (move to "Blocked" with reason)

**Task format:**
```markdown
- [ ] Task description #priority:high #estimate:2h #spec:feature-name
```

---

### specs/feature-name.md (Solution Specs)
**Purpose:** Guardrails and context for AI-assisted development

**NOT a comprehensive checklist** - focus on:
- **Opportunity linkage** (which problem from VISION.md?)
- **Hypothesis** (what will this achieve?)
- **Constraints** (what NOT to do - security, performance)
- **Context injection** (existing code patterns to follow)
- **Interfaces** (API contracts, schemas)

**Update when:**
- Creating (draft → approved)
- Starting build (approved → implementing)
- Shipping (implementing → done)

**Spec statuses:**
- `draft` - Being written
- `approved` - Ready to implement
- `implementing` - Actively being built
- `done` - Shipped and validated
- `deprecated` - No longer relevant

---

### LEARNINGS.md (Knowledge Capture)
**Purpose:** Document solutions to problems so they're not forgotten

**Structure:**
- Errors & Solutions (debugging wins)
- Patterns & Best Practices (reusable approaches)
- Gotchas & Pitfalls (things to avoid)

**Update when:**
- Solving a non-obvious error
- Discovering a pattern worth reusing
- Finding a gotcha that cost significant time

**Entry format:**
```markdown
**[E-001] Error:** Database connection timeout in Docker
**Solution:** Add `POSTGRES_HOST=db` to .env (not localhost)
**Context:** Docker Compose networking requires service name
**Reference:** docker-compose.yml:15
```

---

### PROJECT_INDEX.md (Technical Reference)
**Purpose:** Architecture, tech stack, key decisions

**Structure:**
- Tech Stack (languages, frameworks, tools)
- Architecture Overview (system design)
- Key Decisions (ADRs - architectural decision records)
- Dependencies (critical external services)

**Update when:**
- Adding new technologies
- Making architectural changes
- Documenting key technical decisions

---

### BACKLOG.md (Future Planning)
**Purpose:** Capture ideas and deferred work

**Structure:**
- Next Up (validated but not scheduled)
- Ideas (unvalidated concepts)
- Deferred (intentionally postponed)

**Update when:**
- Deferring work from current sprint
- Capturing new feature ideas
- Validating opportunities (promote to VISION.md)

---

## CC1 with Claude Code

### Slash Commands
- `/cc1-init` - Initialize CC1 in a new project
- `/cc1-update` - Review session work and suggest documentation updates
- `/cc1-audit-improve` - Audit CC1 docs for accuracy and improvements

### Workflow with AI
1. **Session start:** Claude reads `TASKS.md` for context
2. **During work:** Claude references specs for constraints
3. **Session end:** Use `/cc1-update` to capture learnings
4. **Approval required:** Review suggested updates before applying

---

## Best Practices

### ✅ Do:
- Link specs to opportunities in VISION.md
- Update TASKS.md as work progresses
- Capture non-obvious learnings in LEARNINGS.md
- Keep specs lightweight (10-20 min to write)
- Use tags (#priority, #spec, #blocked-by) for organization

### ❌ Don't:
- Auto-update CC1 files without approval
- Document trivial changes
- Create specs for simple tasks
- Let TASKS.md become stale
- Skip evidence in VISION.md

---

## Example Workflow

**Scenario:** Adding user authentication

1. **Discovery** - Add to VISION.md:
   ```markdown
   🎯 Opportunity: unauthorized-api-access
   Problem: Anyone can call our API endpoints without authentication
   Evidence: Security audit flagged this as critical risk
   ```

2. **Planning** - Create spec:
   ```bash
   cp cc1/specs/_template.md cc1/specs/jwt-auth-system.md
   # Fill out: opportunity, hypothesis, constraints, context
   ```

3. **Implement** - Add to TASKS.md:
   ```markdown
   - [ ] Implement JWT authentication #priority:high #spec:jwt-auth-system
   ```

4. **Build** - Work from spec, update status:
   ```markdown
   status: implementing
   ```

5. **Ship** - Update VISION.md with results:
   ```markdown
   📊 2025-01-20 - ✅ JWT auth deployed, zero unauthorized access attempts
   ```

6. **Document** - Add to LEARNINGS.md if needed:
   ```markdown
   **[E-015] Error:** JWT token validation failing in production
   **Solution:** Secret key must be 32+ characters for HS256
   ```

---

## Integration with CLAUDE.md

**CLAUDE.md** (global or project) contains **instructions for Claude**:
- Coding standards
- Response style preferences
- Workflow rules

**CC1 files** contain **project knowledge**:
- What problems exist (VISION.md)
- What's being built (TASKS.md)
- What's been learned (LEARNINGS.md)

**Rule:** If it's phrased as "Claude, do X" → CLAUDE.md. If it's information Claude needs → CC1.

---

## Maintenance

### Weekly:
- Review TASKS.md (move completed items, clean up stale tasks)
- Update VISION.md with experiment results

### Monthly:
- Archive old completed tasks from TASKS.md
- Review BACKLOG.md (promote validated ideas to VISION.md)

### As-needed:
- Run `/cc1-audit-improve` to check for stale documentation

---

## Questions?

**"Do I need a spec for every feature?"**
No. Only for multi-day features, security work, or when you need to inject context about existing patterns.

**"What if I don't have user research?"**
Use proxy evidence: support tickets, analytics, your own pain points. Document assumptions and validate incrementally.

**"How detailed should specs be?"**
10-20 minutes to write. Focus on constraints and context, not exhaustive checklists.

**"When do I update VISION.md?"**
When you discover problems, start solutions, or finish experiments. It's the source of truth for "why are we building this?"

---

**Version:** CC1 v2.0
**Last Updated:** 2025-11-10
