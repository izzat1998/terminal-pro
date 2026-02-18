#!/bin/bash
# PreToolUse Hook: Validate file access before Read/Edit/Write operations
# Prevents accidental access to sensitive or critical files

# Read JSON from stdin
INPUT=$(cat)

# Extract values from JSON
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')

# Skip if no file path provided
if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Get just the filename and directory name
FILENAME=$(basename "$FILE_PATH")
DIRNAME=$(dirname "$FILE_PATH")

# ====================
# BLOCKED FILES (Exit 2 = block with message)
# ====================

# Block access to .env files
if [[ "$FILENAME" == ".env"* && "$FILENAME" != ".env.example" ]]; then
    echo "⛔ BLOCKED: .env files contain secrets and should not be read or edited by Claude."
    echo "💡 Tip: Check .env.example for the template, or ask the user about specific variables."
    exit 2
fi

# Block credentials files
if [[ "$FILENAME" == *"credentials"* ]] || [[ "$FILENAME" == *"secrets"* ]]; then
    echo "⛔ BLOCKED: Credential/secret files should not be accessed."
    exit 2
fi

# Block SSH keys and certificates
if [[ "$FILENAME" == "id_rsa"* ]] || [[ "$FILENAME" == *.pem ]] || [[ "$FILENAME" == *.key ]]; then
    echo "⛔ BLOCKED: Private keys and certificates should not be accessed."
    exit 2
fi

# ====================
# WARNED FILES (Exit 0 but print warning)
# ====================

# Warn for migration files (only on Edit/Write)
if [[ "$DIRNAME" == *"/migrations/"* ]] && [[ "$TOOL_NAME" != "Read" ]]; then
    echo "⚠️ WARNING: Editing existing migrations is dangerous!"
    echo "   Create a new migration instead: python manage.py makemigrations"
fi

# All checks passed
exit 0
