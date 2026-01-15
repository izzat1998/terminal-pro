#!/bin/bash
# PostToolUse Hook: Auto-format files after Edit/Write operations
# This hook runs prettier/eslint on modified files to ensure consistent formatting

# Get the file path from the hook context (passed as argument)
FILE_PATH="$1"

# Skip if no file path provided
if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Only format code files
case "$FILE_PATH" in
    *.ts|*.tsx|*.js|*.jsx|*.vue)
        # Check if we're in the frontend directory
        if [[ "$FILE_PATH" == *"frontend/"* ]]; then
            cd "$(dirname "$0")/../../frontend" 2>/dev/null || exit 0
            # Run prettier on the specific file
            npx prettier --write "$FILE_PATH" 2>/dev/null
        fi
        ;;
    *.py)
        # Check if we're in the backend directory
        if [[ "$FILE_PATH" == *"backend/"* ]]; then
            cd "$(dirname "$0")/../../backend" 2>/dev/null || exit 0
            # Run ruff format on the specific file
            ruff format "$FILE_PATH" 2>/dev/null
        fi
        ;;
esac

exit 0
