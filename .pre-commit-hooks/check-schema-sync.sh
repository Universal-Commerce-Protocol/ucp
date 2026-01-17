#!/bin/bash
# Pre-commit hook to check if spec/ is in sync with source/
# If source/ files changed, regenerate and check for differences

set -e

# Only check if schema inputs changed
if git diff --cached --name-only | grep -qE "(^source/|^generate_schemas\.py|^schema_utils\.py)"; then
  echo "Source schemas changed, checking if spec/ needs regeneration..."

  # Prefer python3, but fall back to python for systems without a python3 shim
  if command -v python3 &> /dev/null; then
    PYTHON=python3
  elif command -v python &> /dev/null; then
    PYTHON=python
  else
    echo "Error: python3 or python not found. Please install Python."
    exit 1
  fi

  # Generate schemas and keep output for debugging
  if ! "$PYTHON" generate_schemas.py; then
    echo ""
    echo "Error: Failed to generate schemas. Please fix errors above."
    exit 1
  fi

  # Check for differences (including untracked files)
  if git ls-files --others --exclude-standard spec/ | grep -q .; then
    echo ""
    echo "Error: spec/ contains untracked generated files"
    echo ""
    echo "Files that need adding:"
    git ls-files --others --exclude-standard spec/
    echo ""
    echo "Run: $PYTHON generate_schemas.py"
    echo "Then stage and commit the updated spec/ files"
    exit 1
  fi

  # Check for differences in tracked files
  if ! git diff --exit-code spec/ > /dev/null 2>&1; then
    echo ""
    echo "Error: spec/ is out of sync with source/"
    echo ""
    echo "Files that need updating:"
    git diff --name-only spec/
    echo ""
    echo "Run: $PYTHON generate_schemas.py"
    echo "Then stage and commit the updated spec/ files"
    exit 1
  fi
fi

exit 0
