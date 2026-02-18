#!/bin/bash
# PostToolUse Hook: Auto-format files after Edit/Write operations

# Read JSON from stdin
INPUT=$(cat)

# Extract file path from JSON
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Skip if no file path provided
if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Only format code files
case "$FILE_PATH" in
    *.ts|*.tsx|*.js|*.jsx|*.vue)
        if [[ "$FILE_PATH" == *"frontend/"* ]]; then
            cd "$(dirname "$0")/../../frontend" 2>/dev/null || exit 0
            npx prettier --write "$FILE_PATH" 2>/dev/null
        fi
        ;;
    *.py)
        if [[ "$FILE_PATH" == *"backend/"* ]]; then
            cd "$(dirname "$0")/../../backend" 2>/dev/null || exit 0
            ruff format "$FILE_PATH" 2>/dev/null
        fi
        ;;
esac

exit 0
