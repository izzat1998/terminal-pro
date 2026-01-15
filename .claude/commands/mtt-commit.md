---
description: Create a conventional commit with MTT project conventions. Use when committing changes to ensure consistent commit history.
---

# MTT Commit Command

Create a commit following MTT project conventions.

## Arguments

- `$1` - Optional: Commit type override (feat, fix, docs, refactor, test, chore)

## Workflow

When this command is invoked, follow these steps:

### 1. Check Current State

Run these commands to understand the changes:
```bash
git status
git diff --staged
git diff
git log -3 --oneline
```

### 2. Stage Changes (if needed)

If there are unstaged changes, ask the user:
- "Should I stage all changes (`git add .`) or specific files?"
- Wait for user confirmation before staging

### 3. Determine Commit Type

Based on the changes, determine the appropriate prefix:

| Prefix | When to Use |
|--------|------------|
| `feat:` | New functionality, new endpoints, new components |
| `fix:` | Bug fixes, error corrections |
| `docs:` | README, CLAUDE.md, comments only |
| `refactor:` | Code restructuring without behavior change |
| `test:` | Test files only |
| `chore:` | Dependencies, configs, build files |

If unsure, ask the user which prefix to use.

### 4. Draft Commit Message

Create a message following this format:
```
<type>: <short description in imperative mood>

<optional body explaining what and why>

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Guidelines:**
- Use imperative mood ("add" not "added", "fix" not "fixed")
- Keep first line under 72 characters
- Focus on WHAT changed and WHY, not HOW
- Reference issue numbers if mentioned by user

### 5. Show Preview and Confirm

Show the user:
```
📝 Proposed commit:
---
<commit message>
---

Files to commit:
- file1.py
- file2.ts

Proceed with commit? (yes/no)
```

### 6. Execute Commit

Only after user confirmation:
```bash
git commit -m "$(cat <<'EOF'
<type>: <description>

<body if needed>

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### 7. Post-Commit

After successful commit:
- Show the commit hash
- Remind user to push if ready: "Push with `git push` when ready"

## Examples

**Example 1: New feature**
```
feat: add relative time formatting to dateFormat utility

Adds formatRelativeTime() function that displays time as "2 hours ago"
or "3 days ago" for recent dates, falling back to absolute date format
for dates older than 7 days.

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Example 2: Bug fix**
```
fix: correct vehicle exit status validation

Vehicle exit was allowed even when entry_time was null, causing
downstream errors in statistics calculation.

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Example 3: Refactor**
```
refactor: extract file upload logic to shared utility

Moves duplicate file upload code from VehicleEntry and ContainerEntry
views into apps/core/utils/file_upload.py.

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Important Notes

- NEVER commit without showing preview and getting confirmation
- NEVER include secrets or .env changes in commits
- If tests are failing, warn the user before committing
- If there are no changes to commit, inform the user instead of failing
