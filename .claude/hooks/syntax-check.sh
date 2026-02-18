#!/bin/bash
# PostToolUse Hook: Quick syntax check after Edit/Write operations
# Catches syntax errors immediately before they become runtime bugs

# Read JSON from stdin
INPUT=$(cat)

# Extract file path from JSON
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Skip if no file path provided
if [ -z "$FILE_PATH" ]; then
    exit 0
fi

case "$FILE_PATH" in
    *.py)
        # Python: fast compile check (catches syntax errors instantly)
        if [[ "$FILE_PATH" == *"backend/"* ]]; then
            RESULT=$(python3 -c "
import py_compile, sys
try:
    py_compile.compile('$FILE_PATH', doraise=True)
except py_compile.PyCompileError as e:
    print(f'SYNTAX ERROR: {e}')
    sys.exit(1)
" 2>&1)
            if [ $? -ne 0 ]; then
                echo "⛔ Python syntax error detected in $FILE_PATH"
                echo "$RESULT"
                exit 2  # exit 2 = show error but don't block
            fi
        fi
        ;;
    *.ts|*.tsx|*.vue)
        # TypeScript: check for common issues (fast regex check, not full tsc)
        if [[ "$FILE_PATH" == *"frontend/"* ]] || [[ "$FILE_PATH" == *"telegram-miniapp/"* ]]; then
            ANY_COUNT=$(grep -c ': any\b\|as any\b\|<any>' "$FILE_PATH" 2>/dev/null || echo "0")
            if [ "$ANY_COUNT" -gt 0 ]; then
                echo "⚠️ Found $ANY_COUNT 'any' type usage(s) in $FILE_PATH - consider using proper types"
            fi
        fi
        ;;
esac

exit 0
