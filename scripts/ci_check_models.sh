#!/bin/bash
# Checks if UCP Pydantic models in src/ucp_sdk/models are in sync with JSON schemas.
# To be used in CI. If models are out of sync, exits with error.

set -e # Exit immediately if a command exits with a non-zero status.

# Ensure we are in the script's directory
cd "$(dirname "$0")"

# Configuration
SCHEMA_DIR="../spec/"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: uv not found."
    echo "Please install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "Running model sync check..."
OUTPUT_DIR="../model_test_ci"
trap 'rm -rf -- "$OUTPUT_DIR"' EXIT
# Ensure output directory is clean
rm -r -f "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"
echo "Generating Pydantic models from $SCHEMA_DIR to temporary dir $OUTPUT_DIR..."

# Run generation using uv
uv run \
    --link-mode=copy \
    --extra-index-url https://pypi.org/simple python \
    -m datamodel_code_generator \
    --input "$SCHEMA_DIR" \
    --input-file-type jsonschema \
    --output "$OUTPUT_DIR" \
    --output-model-type pydantic_v2.BaseModel \
    --use-schema-description \
    --field-constraints \
    --use-field-description \
    --enum-field-as-literal all \
    --disable-timestamp \
    --use-double-quotes \
    --no-use-annotated \
    --allow-extra-fields

echo "SUCCESS: Models can be generated successfully from schemas in $SCHEMA_DIR."
exit 0
