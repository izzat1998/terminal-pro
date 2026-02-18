---
name: smart-commit
description: Review, verify dependencies, group, and commit changes with conventional commit format. Use when the user says "commit", "smart commit", or wants a clean commit workflow.
---

# Smart Commit Workflow

Follow these steps exactly. Never skip dependency verification.

## Step 1: Survey Changes

Run in parallel:
```bash
git status
git diff
git diff --cached
git log --oneline -5
```

Understand the full scope of what changed.

## Step 2: Verify Dependencies

For EVERY changed file, check for new imports:

**Python files:** Extract imports and verify each is either:
- A stdlib module
- Already in `backend/requirements.txt`
- A project-internal module (`apps.*`, `terminal_app.*`)

If a third-party import is missing from requirements.txt:
1. Add it to `backend/requirements.txt`
2. Stage that change too

**TypeScript/Vue files:** Extract `from 'package'` imports and verify each is in:
- `frontend/package.json` (dependencies or devDependencies)
- Or `telegram-miniapp/package.json`

If missing, warn the user and suggest `npm install <package>`.

## Step 3: Group into Logical Commits

Separate changes into independent commits when possible:

| Group | Prefix | Example |
|-------|--------|---------|
| New feature code | `feat:` | Backend + frontend for one feature = 1 commit |
| Bug fixes | `fix:` | Each independent fix = separate commit |
| Refactoring | `refactor:` | Structural changes without behavior change |
| Dependencies | `chore:` | requirements.txt, package.json changes |
| Tests | `test:` | Test additions/modifications |
| Docs | `docs:` | Documentation only |

**Rule:** If backend and frontend changes are for the SAME feature, they go in ONE commit. If they're independent, separate commits.

## Step 4: Draft Messages

For each commit, draft a message that:
- Uses conventional commit prefix
- Is concise (1 line, under 72 chars)
- Explains WHY, not WHAT
- Is in English

Show the user the plan:
```
Commit 1: feat: add container export to Excel
  Files: backend/apps/billing/services/export_service.py, frontend/src/components/billing/ExportButton.vue

Commit 2: fix: correct decimal rounding in storage cost calculation
  Files: backend/apps/billing/services/billing_service.py
```

Wait for user approval before executing.

## Step 5: Execute Commits

For each approved commit:
1. Stage SPECIFIC files only: `git add <file1> <file2>`
2. Commit with HEREDOC format:
   ```bash
   git commit -m "$(cat <<'EOF'
   feat: description here

   Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
   EOF
   )"
   ```
3. Report the commit hash

## Step 6: Final Report

```bash
git log --oneline -N  # N = number of commits just made
```

Report all commit hashes. Do NOT push unless the user explicitly asks.

## Rules

- **NEVER** use `git add -A` or `git add .`
- **NEVER** push without explicit user request
- **NEVER** amend previous commits unless asked
- **NEVER** skip dependency verification
- **NEVER** commit .env files, credentials, or secrets
- If pre-commit hook shows warnings, address them before retrying
