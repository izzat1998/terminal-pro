#!/bin/bash
# PreToolUse Hook: Validate file access before Read/Edit/Write operations
# Prevents accidental access to sensitive or critical files

# Get the file path from the hook context
FILE_PATH="$1"
TOOL_NAME="$2"  # Read, Edit, or Write

# Skip if no file path provided
if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Get just the filename and directory name
FILENAME=$(basename "$FILE_PATH")
DIRNAME=$(dirname "$FILE_PATH")

# ====================
# BLOCKED FILES (Exit 1 = block)
# ====================

# Block access to .env files
if [[ "$FILENAME" == ".env"* ]]; then
    echo "⛔ BLOCKED: .env files contain secrets and should not be read or edited by Claude."
    echo "💡 Tip: Check .env.example for the template, or ask the user about specific variables."
    exit 1
fi

# Block credentials files
if [[ "$FILENAME" == *"credentials"* ]] || [[ "$FILENAME" == *"secrets"* ]]; then
    echo "⛔ BLOCKED: Credential/secret files should not be accessed."
    exit 1
fi

# Block SSH keys and certificates
if [[ "$FILENAME" == "id_rsa"* ]] || [[ "$FILENAME" == "*.pem" ]] || [[ "$FILENAME" == "*.key" ]]; then
    echo "⛔ BLOCKED: Private keys and certificates should not be accessed."
    exit 1
fi

# ====================
# WARNED FILES (Exit 0 but print warning)
# ====================

# Warn for infrastructure files (allow but warn)
if [[ "$FILENAME" == "docker-compose"* ]]; then
    echo "⚠️ WARNING: docker-compose files are critical infrastructure."
    echo "   Changes affect all developers. Please verify syntax before saving."
    # exit 0 - allow but warned
fi

# Warn for lock files
if [[ "$FILENAME" == "package-lock.json" ]] || [[ "$FILENAME" == "*.lock" ]]; then
    echo "⚠️ WARNING: Lock files are auto-generated and should not be manually edited."
    echo "   Changes can cause dependency issues. Use package manager commands instead."
fi

# Warn for migration files (only on Edit/Write)
if [[ "$DIRNAME" == *"/migrations/"* ]] && [[ "$TOOL_NAME" != "Read" ]]; then
    echo "⚠️ WARNING: Editing existing migrations is dangerous!"
    echo "   If migrations have been applied, create a new migration instead."
    echo "   Use: python manage.py makemigrations <app> --name <description>"
fi

# Warn for settings files
if [[ "$FILENAME" == "settings.py" ]] || [[ "$FILENAME" == "settings.json" ]]; then
    echo "⚠️ WARNING: Settings files affect application behavior."
    echo "   Please verify changes are intentional."
fi

# All checks passed
exit 0
