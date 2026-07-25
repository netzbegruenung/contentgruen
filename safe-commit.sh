#!/bin/bash
# Safe commit script that handles pre-commit hooks

if [ -z "$1" ]; then
    echo "Usage: ./safe-commit.sh \"commit message\""
    exit 1
fi

echo "Attempting commit..."
if git commit -m "$1"; then
    echo "✓ Commit successful on first try"
else
    echo "Pre-commit hook made changes. Reviewing..."

    # Show what changed
    echo "----------------------------------------"
    echo "Files modified by pre-commit hook:"
    git diff --name-only --cached
    echo "----------------------------------------"

    # Auto-stage formatting changes
    git add -u

    echo "Re-attempting commit with formatted files..."
    if git commit -m "$1"; then
        echo "✓ Commit successful after formatting"
    else
        echo "✗ Commit still failed. Manual intervention needed."
        echo "Run: git status"
        exit 1
    fi
fi
