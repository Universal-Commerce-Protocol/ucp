#   Copyright 2026 UCP Authors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""Standalone script to validate JSON and YAML syntax in the 'spec' folder.

Usage: uv run validate_specs.py
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

import schema_utils
import yaml

# Configuration
SPEC_DIR = "spec"
EXIT_ON_ERROR = True  # Set to False if you want to see all errors at once


# ANSI Colors for nicer output
class Colors:
  """ANSI color codes for nicer output."""

  GREEN = "\033[92m"
  RED = "\033[91m"
  YELLOW = "\033[93m"
  RESET = "\033[0m"


def check_ref(
  ref: str, current_file: str, root_data: Any | None = None
) -> str | None:
  """Check if a reference exists."""
  if ref.startswith("#"):
    if ref != "#" and not ref.startswith("#/"):
      return (
        f"Invalid internal reference format in {current_file}: {ref} (Must"
        " start with '#/')"
      )
    if (
      root_data is not None
      and schema_utils.resolve_internal_ref(ref, root_data) is None
    ):
      return f"Broken internal reference in {current_file}: {ref}"
    return None  # Skip if no root_data context (shouldn't happen in new flow)

  if ref.startswith("http"):
    return None  # External URL

  # Split ref from internal path (e.g. file.json#/definition)
  parts = ref.split("#")
  file_part = parts[0]
  anchor_part = parts[1] if len(parts) > 1 else None

  current_dir = Path(current_file).parent
  referenced_path = current_dir / file_part

  if not referenced_path.exists():
    return f"Missing reference in {current_file}: {ref}"

  # If there is an anchor, we need to load the referenced file and check it
  if anchor_part:
    if not anchor_part.startswith("/"):
      return (
        f"Invalid anchor format in {current_file}: {ref} (Anchor must start"
        " with '/')"
      )
    try:
      with referenced_path.open(encoding="utf-8") as f:
        if referenced_path.suffix == ".json":
          referenced_data = json.load(f)
        elif referenced_path.suffix in (".yaml", ".yml"):
          referenced_data = yaml.safe_load(f)
        else:
          # Unknown file type, can't validate anchor
          return None

      # Validate the anchor using resolve_internal_ref logic
      # We verify if '#/anchor' resolves in referenced_data
      if (
        schema_utils.resolve_internal_ref("#" + anchor_part, referenced_data)
        is None
      ):
        return f"Broken anchor in external reference in {current_file}: {ref}"

    except (json.JSONDecodeError, yaml.YAMLError, OSError):
      # If we can't parse the referenced file, we can't validate the anchor.
      # But basic file existence check already passed.
      # Ideally we should report a warning or error here, but for now
      # we'll assume it's fine or caught by other validation.
      return (
        f"Could not parse referenced file for reference validation:"
        f" {referenced_path}"
      )

  return None


def check_refs(
  data: Any, current_file: str, root_data: Any | None = None
) -> list[str]:
  """Recursively check for broken references in a JSON/YAML object."""
  errors = []
  # If root_data isn't passed initially, assume 'data' is the root
  if root_data is None:
    root_data = data

  if isinstance(data, dict):
    for key, value in data.items():
      if key == "$ref":
        error = check_ref(value, current_file, root_data)
        if error:
          errors.append(error)
      else:
        errors.extend(check_refs(value, current_file, root_data))
  elif isinstance(data, list):
    for item in data:
      errors.extend(check_refs(item, current_file, root_data))
  return errors


def validate_file(filepath: str) -> tuple[bool, str | None]:
  """Return (True, None) if valid, or (False, error_message) if invalid."""
  # 1. Validate JSON
  if filepath.endswith(".json"):
    try:
      with Path(filepath).open(encoding="utf-8") as f:
        data = json.load(f)

      # Validate references
      ref_errors = check_refs(data, filepath, root_data=data)
      if ref_errors:
        return False, "\n   └── ".join(ref_errors)

      return True, None
    except json.JSONDecodeError as e:
      return False, f"JSON Error: {e.msg} at line {e.lineno}, column {e.colno}"

  # 2. Validate YAML
  elif filepath.endswith((".yaml", ".yml")):
    try:
      with Path(filepath).open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

      # Validate references
      ref_errors = check_refs(data, filepath, root_data=data)
      if ref_errors:
        return False, "\n   └── ".join(ref_errors)

      return True, None
    except yaml.YAMLError as e:
      # YAML errors are usually multiline, so we grab the first meaningful part
      return False, f"YAML Error: {e}"

  # Ignore other files
  return True, None


def main() -> None:
  """Validate specs in the spec directory."""
  if not Path(SPEC_DIR).exists():
    print(
      f"{Colors.YELLOW}Warning: Directory '{SPEC_DIR}' not found.{Colors.RESET}"
    )
    sys.exit(0)

  print(f"🔍 Scanning '{SPEC_DIR}/' for syntax and reference errors...")

  error_count = 0
  file_count = 0

  for root, _, files in os.walk(SPEC_DIR):
    for filename in files:
      full_path = Path(root) / filename

      # Skip hidden files or unrelated types
      if filename.startswith(".") or not filename.endswith(
        (".json", ".yaml", ".yml")
      ):
        continue

      file_count += 1
      is_valid, error_msg = validate_file(str(full_path))

      if not is_valid:
        error_count += 1
        print(f"{Colors.RED}❌ FAIL: {full_path}{Colors.RESET}")
        print(f"   └── {error_msg}")

        if EXIT_ON_ERROR:
          print(f"\n{Colors.RED}Stopped on first error.{Colors.RESET}")
          sys.exit(1)
      else:
        # Optional: Print dots for progress
        print(f"{Colors.GREEN}.{Colors.RESET}", end="", flush=True)

  print("\n")
  if error_count == 0:
    print(
      f"{Colors.GREEN}✅ Success! Scanned {file_count} files. No errors"
      f" found.{Colors.RESET}"
    )
    sys.exit(0)
  else:
    print(f"{Colors.RED}🚨 Failed. Found {error_count} errors.{Colors.RESET}")
    sys.exit(1)


if __name__ == "__main__":
  main()
