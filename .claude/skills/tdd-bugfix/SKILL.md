---
name: tdd-bugfix
description: Fix bugs using test-driven development. Write a failing test first, then iterate the fix autonomously. Use when the user reports a bug or says "fix this bug with TDD".
---

# Test-Driven Bug Fix Pipeline

This is a **RIGID** skill. Follow every phase exactly. Do NOT skip ahead to writing a fix.

## Phase 1: Understand the Bug (READ ONLY)

1. Read the source files where the bug occurs
2. Identify the EXACT function/module with the issue
3. State clearly:
   - **Expected behavior:** what should happen
   - **Actual behavior:** what happens instead
   - **Root cause hypothesis:** your best guess at why

Do NOT write any code in this phase.

## Phase 2: Write a Failing Test

1. Create a test that reproduces the bug exactly
2. Place it in the appropriate test file (follow existing test structure)
3. Run the test to CONFIRM it fails:

**Backend (Python):**
```bash
cd backend && .venv/bin/pytest apps/<app>/tests/test_<module>.py::<TestClass>::<test_method> -v
```

**Frontend (TypeScript):**
```bash
cd frontend && npx vitest run src/<path>/<test_file>.test.ts
```

4. **If the test PASSES:** Your test doesn't capture the bug. Revise it.
5. **If the test FAILS with the expected error:** Proceed to Phase 3.

## Phase 3: Fix Loop (max 5 iterations)

```
┌─────────────────────────┐
│ Implement MINIMAL fix   │
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│ Run the failing test    │
└───────────┬─────────────┘
            ▼
       ┌────────┐
       │ Pass?  │──── Yes ──→ Phase 4
       └────┬───┘
            │ No
            ▼
┌─────────────────────────┐
│ Analyze failure output  │
│ Adjust fix accordingly  │
└───────────┬─────────────┘
            │
            └──→ (back to top, max 5 iterations)
```

**Rules during the loop:**
- Do NOT ask the user for guidance — work autonomously
- Do NOT refactor unrelated code
- Do NOT add features beyond the fix
- Do NOT change the test to make it pass (unless the test itself was wrong)
- Each iteration: implement fix → run test → analyze → adjust

**If 5 iterations pass without success:**
- Stop and report to the user
- Show what you tried and why it didn't work
- Ask for guidance

## Phase 4: Regression Check

1. Run the FULL test suite for the affected app:

```bash
cd backend && .venv/bin/pytest apps/<app>/ -v
```

2. If any OTHER test broke:
   - Fix it WITHOUT breaking the original bug-fix test
   - Run again until ALL tests pass

3. If fixing regressions would change the approach:
   - Report to the user with the trade-off
   - Let them decide

## Phase 5: Report

Present a clean summary:

```
## Bug Fix Report

**Root Cause:** [1-2 sentences explaining WHY the bug existed]

**Fix:** [1-2 sentences explaining what was changed]

**Test:** [name of the test that now passes]

**Regression Check:** All N tests passing ✅

**Files Changed:**
- path/to/file1.py (fix)
- path/to/test_file.py (new test)
```

Do NOT commit. Let the user decide when to commit (they may want to review first).
