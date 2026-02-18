#!/bin/bash
# Automated code review using Claude Code headless mode
#
# Usage:
#   ./scripts/claude-review.sh                  # Review last commit (default)
#   ./scripts/claude-review.sh last-commit      # Review last commit
#   ./scripts/claude-review.sh staged           # Review staged changes
#   ./scripts/claude-review.sh branch           # Review all changes on current branch vs main
#   ./scripts/claude-review.sh full             # Full project audit (spawns parallel agents)
#
# Output: Creates a timestamped markdown report in the project root

set -e

SCOPE="${1:-last-commit}"
REPORT_FILE="review-report-$(date +%Y%m%d-%H%M%S).md"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$PROJECT_ROOT"

echo "Running Claude Code review (scope: $SCOPE)..."

case "$SCOPE" in
    last-commit)
        FILES=$(git diff --name-only HEAD~1 2>/dev/null || echo "")
        if [ -z "$FILES" ]; then
            echo "No changes found in last commit."
            exit 0
        fi
        PROMPT="Review the files changed in the last commit of this project. Check for:
1. Missing dependency imports (not in backend/requirements.txt or frontend/package.json)
2. Float usage in financial calculations (should use Decimal)
3. N+1 query patterns (missing select_related/prefetch_related)
4. Missing error handling or bare except clauses
5. 'any' type usage in TypeScript (strict mode violation)
6. English user-facing messages (should be Russian per CLAUDE.md rules)
7. Business logic in views instead of services (violates service layer pattern)
8. Security issues (SQL injection, XSS, exposed secrets)

Files changed:
$FILES

Read each file and output a markdown report with findings grouped by severity:
- **Critical**: Security issues, data loss risks, production crashes
- **Warning**: Code quality issues, pattern violations
- **Info**: Style suggestions, minor improvements

If no issues found, say so clearly."
        ;;

    staged)
        FILES=$(git diff --cached --name-only 2>/dev/null || echo "")
        if [ -z "$FILES" ]; then
            echo "No staged changes found."
            exit 0
        fi
        PROMPT="Review the staged changes in this project before commit. Check for:
1. Missing dependencies (imports without corresponding requirements.txt/package.json entries)
2. Security issues (SQL injection, XSS, exposed secrets, hardcoded credentials)
3. Financial calculation errors (float instead of Decimal)
4. TypeScript strict mode violations ('any' type)
5. Response format violations (must use {success, data/error} format)

Staged files:
$FILES

Read each file and output a concise markdown checklist of issues found. Be brief and actionable."
        ;;

    branch)
        BASE=$(git merge-base main HEAD 2>/dev/null || echo "HEAD~10")
        FILES=$(git diff --name-only "$BASE"..HEAD 2>/dev/null || echo "")
        COMMITS=$(git log --oneline "$BASE"..HEAD 2>/dev/null || echo "")
        if [ -z "$FILES" ]; then
            echo "No changes found on current branch vs main."
            exit 0
        fi
        PROMPT="Review all changes on this branch compared to main. This is a comprehensive code review.

Commits on this branch:
$COMMITS

Files changed:
$FILES

Read ALL changed files and provide a structured review covering:
1. **Architecture**: Service layer pattern compliance, separation of concerns
2. **Security**: Injection risks, auth gaps, exposed secrets
3. **Performance**: N+1 queries, missing indexes, unnecessary DB calls
4. **Code Quality**: TypeScript strict mode, response format consistency, language rules
5. **Edge Cases**: Financial precision, state transitions, race conditions
6. **Missing Tests**: Logic that should have test coverage

Output a markdown report with a summary table and detailed findings."
        ;;

    full)
        PROMPT="Perform a full project audit of this MTT container terminal management system. Read the CLAUDE.md for project context.

Use parallel sub-agents to check different areas simultaneously:

Agent 1 - Financial Logic: Scan all files in backend/apps/billing/ for float usage (should be Decimal), rounding issues, race conditions (missing select_for_update), and immutability violations on historical records.

Agent 2 - API Quality: Check all files in backend/apps/*/views.py for missing error handling, N+1 queries (missing select_related/prefetch_related), business logic that should be in services, and response format violations.

Agent 3 - Frontend Quality: Check all .vue and .ts files in frontend/src/ for TypeScript 'any' usage, missing type annotations, Options API usage (should be Composition API), and hardcoded English user-facing strings.

Agent 4 - Security: Check for hardcoded secrets, SQL injection risks, missing permission checks, and exposed debug endpoints across the entire project.

Compile all agent findings into a single prioritized markdown report with:
- Executive summary (1-2 paragraphs)
- Critical issues (must fix)
- Warnings (should fix)
- Suggestions (nice to have)
- Statistics (files scanned, issues found per category)"
        ;;

    *)
        echo "Usage: $0 [last-commit|staged|branch|full]"
        echo ""
        echo "Scopes:"
        echo "  last-commit  Review changes in the most recent commit (default)"
        echo "  staged       Review currently staged changes"
        echo "  branch       Review all changes on current branch vs main"
        echo "  full         Full project audit using parallel agents"
        exit 1
        ;;
esac

echo "Output will be saved to: $REPORT_FILE"
echo ""

claude -p "$PROMPT" \
    --allowedTools "Read,Grep,Glob,Bash(read-only commands: git diff, git log, git status, ls, python -c),Task" \
    > "$REPORT_FILE"

echo ""
echo "Review complete! Report saved to: $REPORT_FILE"
echo "View with: cat $REPORT_FILE"
