#!/bin/bash
# Regenerates spec outputs and SDK models in one command.

set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$ROOT_DIR"

python generate_schemas.py

SDK_SCRIPT="$ROOT_DIR/sdk/python/generate_models.sh"
if [ -f "$SDK_SCRIPT" ]; then
  bash "$SDK_SCRIPT"
else
  echo "SDK generator not found at $SDK_SCRIPT. Skipping SDK regeneration."
fi
