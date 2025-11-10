# VISION
_Product vision and Opportunity Solution Tree (OST). Update when: discovering user problems, validating solutions, analyzing results._

## Product Vision

**Target Outcome:** [What ultimate user/business outcome are we driving toward?]

**Example:** "Enable developers to build AI-powered FastAPI applications in minutes, not days, with production-ready patterns and best practices built-in."

---

## Opportunity Solution Tree (OST)

The OST connects **desired outcomes** → **opportunities** (user problems) → **solutions** (features/experiments) → **evidence** (what we learned).

### Legend
- 🎯 **Opportunity** - A user problem or friction point (NOT a solution)
- 💡 **Solution** - A specific feature/experiment to address an opportunity
- 📊 **Evidence** - Data, feedback, or metrics that validate/invalidate hypothesis
- ✅ **Validated** - Solution worked, hypothesis confirmed
- ❌ **Invalidated** - Solution didn't work, pivot needed
- 🔄 **In Progress** - Currently testing/building

---

## Current Focus

### 🎯 Opportunity: [opportunity-slug]
**Problem:** [What user friction/pain exists? Be specific.]
**Impact:** [How many users? How severe? Business/UX cost?]
**Evidence:** [User feedback, metrics, observations that surface this problem]

#### Solutions Being Explored:
- 💡 **[Solution Name]** 🔄
  - **Hypothesis:** If we build X, then Y outcome will improve by Z
  - **Spec:** `cc1/specs/solution-slug.md`
  - **Status:** Draft | Implementing | Testing

- 💡 **[Alternative Solution]**
  - **Hypothesis:** [Different approach to same opportunity]
  - **Status:** Idea | Deprioritized

#### Results:
- 📊 **[Date]** - ✅ Solution worked: [Metric improved by X%, user feedback positive]
- 📊 **[Date]** - ❌ Solution failed: [Hypothesis was wrong because Y, pivot to Z]

---

## Backlog Opportunities

### 🎯 Opportunity: [another-opportunity-slug]
**Problem:** [User problem description]
**Evidence:** [Why we think this matters]
**Priority:** High | Medium | Low
**Status:** Researching | Validating | Deprioritized

---

## Template Usage

### Adding a New Opportunity
1. **Surface the problem** (user research, feedback, metrics)
2. **Frame as opportunity** (what's the user friction, not the solution)
3. **Create OST entry** with evidence
4. **Brainstorm solutions** (list 3-5 possible approaches)
5. **Select best solution** for first experiment
6. **Create spec** (`cc1/specs/solution-slug.md`)
7. **Build & test** (update with results)

### OST → Spec Workflow
```
VISION.md (problem space)
    ↓
  Define Opportunity + Evidence
    ↓
  Hypothesize Solutions
    ↓
cc1/specs/solution-slug.md (solution space)
    ↓
  Build & Test
    ↓
VISION.md (update with results)
```

### Naming Conventions
- **Opportunities:** `user-onboarding-friction`, `deployment-reliability`, `api-performance-issues`
- **Solutions:** `interactive-setup-wizard`, `health-check-system`, `query-caching-layer`
- **Spec files:** Match solution name (`interactive-setup-wizard.md`)

---

## Example OST Entry

### 🎯 Opportunity: developer-environment-setup-friction
**Problem:** New developers spend 30+ minutes configuring environment variables, database connections, and Docker settings before seeing the app run
**Impact:** Affects 100% of new users, causes 40% to abandon in first session
**Evidence:**
- Support tickets: 15 issues in last month about "Docker won't start"
- User interviews: 4/5 developers said setup was confusing
- Analytics: Avg. time-to-first-successful-run is 47 minutes

#### Solutions:
- 💡 **Automated Environment Setup Script** ✅
  - **Hypothesis:** If we create a `./setup.sh` script that validates dependencies and generates .env, then time-to-first-run drops to <10 minutes
  - **Spec:** `cc1/specs/automated-setup-script.md`
  - **Status:** Done
  - **Result:** ✅ Time-to-first-run dropped to 8 minutes avg. User feedback: "This saved me so much time!"

- 💡 **Interactive Setup CLI** 🔄
  - **Hypothesis:** If we prompt users for configuration instead of editing .env manually, then setup success rate increases to 95%
  - **Spec:** `cc1/specs/interactive-setup-cli.md`
  - **Status:** Implementing

#### Results:
- 📊 **2025-01-15** - ✅ Setup script reduced support tickets by 60%
- 📊 **2025-01-20** - 🔄 Testing interactive CLI with 10 beta users

---

## Vision Evolution

_Track how your product vision changes over time as you learn_

**2025-11-10** - Initial vision: [Starting hypothesis about what users need]

---

**Notes:**
- This file drives feature prioritization - if it's not in the OST, it's not being worked on
- Update with results after each experiment to inform future decisions
- Use evidence-based language: metrics, user quotes, concrete observations
- Frame opportunities as problems, not solutions ("users can't find X" not "we need a search bar")
