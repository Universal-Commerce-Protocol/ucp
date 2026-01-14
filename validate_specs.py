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

This script provides comprehensive validation including:
- JSON/YAML syntax validation
- $ref reference resolution and validation
- OpenAPI 3.1 compliance checks
- JSON Schema structure validation
- UCP-specific convention checks

Usage:
  python validate_specs.py                    # Validate all specs
  python validate_specs.py --verbose          # Show all files, not just errors
  python validate_specs.py --continue         # Don't stop on first error
  python validate_specs.py --openapi-only     # Only validate OpenAPI files
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import schema_utils
import yaml

# Configuration
SPEC_DIR = "spec"
OPENAPI_DIR = os.path.join(SPEC_DIR, "services")
SCHEMAS_DIR = os.path.join(SPEC_DIR, "schemas")


class Severity(Enum):
  """Validation issue severity levels."""

  ERROR = "error"
  WARNING = "warning"
  INFO = "info"


@dataclass
class ValidationIssue:
  """Represents a single validation issue."""

  file_path: str
  message: str
  severity: Severity = Severity.ERROR
  line: Optional[int] = None
  column: Optional[int] = None
  rule: str = ""

  def __str__(self) -> str:
    loc = ""
    if self.line:
      loc = f" (line {self.line}"
      if self.column:
        loc += f", col {self.column}"
      loc += ")"
    rule_tag = f"[{self.rule}] " if self.rule else ""
    return f"{rule_tag}{self.message}{loc}"


@dataclass
class ValidationResult:
  """Aggregates validation results for a file or entire spec."""

  issues: list[ValidationIssue] = field(default_factory=list)
  files_checked: int = 0
  files_passed: int = 0

  @property
  def has_errors(self) -> bool:
    return any(i.severity == Severity.ERROR for i in self.issues)

  @property
  def error_count(self) -> int:
    return sum(1 for i in self.issues if i.severity == Severity.ERROR)

  @property
  def warning_count(self) -> int:
    return sum(1 for i in self.issues if i.severity == Severity.WARNING)

  def add(self, issue: ValidationIssue) -> None:
    self.issues.append(issue)

  def merge(self, other: "ValidationResult") -> None:
    self.issues.extend(other.issues)
    self.files_checked += other.files_checked
    self.files_passed += other.files_passed


# ANSI Colors for nicer output
class Colors:
  GREEN = "\033[92m"
  RED = "\033[91m"
  YELLOW = "\033[93m"
  CYAN = "\033[96m"
  RESET = "\033[0m"
  BOLD = "\033[1m"


def check_ref(
    ref: str, current_file: str, root_data: Optional[Any] = None
) -> Optional[ValidationIssue]:
  """Checks if a reference exists and is valid.

  Args:
    ref: The $ref value to validate.
    current_file: Path to the file containing the reference.
    root_data: The root data structure for internal reference resolution.

  Returns:
    A ValidationIssue if the reference is invalid, None otherwise.
  """
  if ref.startswith("#"):
    if ref != "#" and not ref.startswith("#/"):
      return ValidationIssue(
          file_path=current_file,
          message=f"Invalid internal reference format: {ref} (Must start with '#/')",
          rule="ref-format",
      )
    if root_data is not None:
      if schema_utils.resolve_internal_ref(ref, root_data) is None:
        return ValidationIssue(
            file_path=current_file,
            message=f"Broken internal reference: {ref}",
            rule="ref-resolve",
        )
    return None

  if ref.startswith("http"):
    return None  # External URL - can't validate without network

  # Split ref from internal path (e.g. file.json#/definition)
  parts = ref.split("#")
  file_part = parts[0]
  anchor_part = parts[1] if len(parts) > 1 else None

  current_dir = os.path.dirname(current_file)
  referenced_path = os.path.join(current_dir, file_part)

  if not os.path.exists(referenced_path):
    return ValidationIssue(
        file_path=current_file,
        message=f"Missing referenced file: {ref}",
        rule="ref-file-exists",
    )

  # If there is an anchor, we need to load the referenced file and check it
  if anchor_part:
    if not anchor_part.startswith("/"):
      return ValidationIssue(
          file_path=current_file,
          message=f"Invalid anchor format: {ref} (Anchor must start with '/')",
          rule="ref-anchor-format",
      )
    try:
      with open(referenced_path, "r", encoding="utf-8") as f:
        if referenced_path.endswith(".json"):
          referenced_data = json.load(f)
        elif referenced_path.endswith((".yaml", ".yml")):
          referenced_data = yaml.safe_load(f)
        else:
          return None  # Unknown file type, can't validate anchor

      if (
          schema_utils.resolve_internal_ref("#" + anchor_part, referenced_data)
          is None
      ):
        return ValidationIssue(
            file_path=current_file,
            message=f"Broken anchor in external reference: {ref}",
            rule="ref-anchor-resolve",
        )

    except (json.JSONDecodeError, yaml.YAMLError, OSError) as e:
      return ValidationIssue(
          file_path=current_file,
          message=f"Could not parse referenced file {referenced_path}: {e}",
          severity=Severity.WARNING,
          rule="ref-parse",
      )

  return None


def check_refs(
    data: Any, current_file: str, root_data: Optional[Any] = None
) -> list[ValidationIssue]:
  """Recursively checks for broken references in a JSON/YAML object.

  Args:
    data: The data structure to validate.
    current_file: Path to the file being validated.
    root_data: The root data structure for internal reference resolution.

  Returns:
    List of ValidationIssue objects for any broken references.
  """
  issues: list[ValidationIssue] = []
  if root_data is None:
    root_data = data

  if isinstance(data, dict):
    for key, value in data.items():
      if key == "$ref":
        issue = check_ref(value, current_file, root_data)
        if issue:
          issues.append(issue)
      else:
        issues.extend(check_refs(value, current_file, root_data))
  elif isinstance(data, list):
    for item in data:
      issues.extend(check_refs(item, current_file, root_data))
  return issues


def validate_openapi_structure(
    data: dict[str, Any], file_path: str
) -> list[ValidationIssue]:
  """Validates OpenAPI 3.1 structure and compliance.

  Args:
    data: Parsed OpenAPI document.
    file_path: Path to the file being validated.

  Returns:
    List of validation issues found.
  """
  issues: list[ValidationIssue] = []

  # Check OpenAPI version
  openapi_version = data.get("openapi", "")
  if not openapi_version:
    issues.append(
        ValidationIssue(
            file_path=file_path,
            message="Missing 'openapi' version field",
            rule="openapi-version",
        )
    )
  elif not openapi_version.startswith("3.1"):
    issues.append(
        ValidationIssue(
            file_path=file_path,
            message=f"Expected OpenAPI 3.1.x, found: {openapi_version}",
            severity=Severity.WARNING,
            rule="openapi-version",
        )
    )

  # Check required info object
  info = data.get("info", {})
  if not info:
    issues.append(
        ValidationIssue(
            file_path=file_path,
            message="Missing required 'info' object",
            rule="openapi-info",
        )
    )
  else:
    if not info.get("title"):
      issues.append(
          ValidationIssue(
              file_path=file_path,
              message="Missing required 'info.title' field",
              rule="openapi-info-title",
          )
      )
    if not info.get("version"):
      issues.append(
          ValidationIssue(
              file_path=file_path,
              message="Missing required 'info.version' field",
              rule="openapi-info-version",
          )
      )

  # Check paths structure
  paths = data.get("paths", {})
  for path, path_item in paths.items():
    if not path.startswith("/"):
      issues.append(
          ValidationIssue(
              file_path=file_path,
              message=f"Path must start with '/': {path}",
              rule="openapi-path-format",
          )
      )

    if isinstance(path_item, dict):
      for method, operation in path_item.items():
        if method in ("get", "post", "put", "patch", "delete", "options", "head"):
          if isinstance(operation, dict):
            # Check for operationId
            if not operation.get("operationId"):
              issues.append(
                  ValidationIssue(
                      file_path=file_path,
                      message=f"Missing operationId for {method.upper()} {path}",
                      severity=Severity.WARNING,
                      rule="openapi-operation-id",
                  )
              )
            # Check for responses
            if not operation.get("responses"):
              issues.append(
                  ValidationIssue(
                      file_path=file_path,
                      message=f"Missing responses for {method.upper()} {path}",
                      rule="openapi-responses",
                  )
              )

  # Check webhooks (OpenAPI 3.1 feature)
  webhooks = data.get("webhooks", {})
  for webhook_name, webhook_item in webhooks.items():
    if isinstance(webhook_item, dict):
      for method, operation in webhook_item.items():
        if isinstance(operation, dict) and not operation.get("operationId"):
          issues.append(
              ValidationIssue(
                  file_path=file_path,
                  message=f"Missing operationId for webhook '{webhook_name}'",
                  severity=Severity.WARNING,
                  rule="openapi-webhook-operation-id",
              )
          )

  return issues


def validate_json_schema_structure(
    data: dict[str, Any], file_path: str
) -> list[ValidationIssue]:
  """Validates JSON Schema structure and UCP conventions.

  Args:
    data: Parsed JSON Schema document.
    file_path: Path to the file being validated.

  Returns:
    List of validation issues found.
  """
  issues: list[ValidationIssue] = []

  # Check for $schema declaration
  schema_uri = data.get("$schema", "")
  if not schema_uri:
    issues.append(
        ValidationIssue(
            file_path=file_path,
            message="Missing '$schema' declaration",
            severity=Severity.WARNING,
            rule="schema-declaration",
        )
    )
  elif "draft-2020-12" not in schema_uri and "draft/2020-12" not in schema_uri:
    issues.append(
        ValidationIssue(
            file_path=file_path,
            message=f"Expected JSON Schema 2020-12, found: {schema_uri}",
            severity=Severity.INFO,
            rule="schema-version",
        )
    )

  # Check for recommended fields
  if not data.get("title") and not data.get("$ref"):
    issues.append(
        ValidationIssue(
            file_path=file_path,
            message="Missing 'title' field (recommended for documentation)",
            severity=Severity.INFO,
            rule="schema-title",
        )
    )

  # Validate $defs structure
  defs = data.get("$defs", {})
  for def_name, def_schema in defs.items():
    if not isinstance(def_schema, dict):
      issues.append(
          ValidationIssue(
              file_path=file_path,
              message=f"Invalid $defs/{def_name}: expected object, got {type(def_schema).__name__}",
              rule="schema-defs-type",
          )
      )
    elif not def_schema.get("type") and not def_schema.get("$ref") and not any(
        k in def_schema for k in ("oneOf", "anyOf", "allOf", "enum", "const")
    ):
      issues.append(
          ValidationIssue(
              file_path=file_path,
              message=f"$defs/{def_name} has no type or composition keyword",
              severity=Severity.WARNING,
              rule="schema-defs-structure",
          )
      )

  # Check UCP naming conventions
  basename = os.path.basename(file_path)
  if basename.endswith(".json"):
    name = basename[:-5]
    # Check for snake_case naming
    if not re.match(r"^[a-z][a-z0-9_.]*$", name):
      issues.append(
          ValidationIssue(
              file_path=file_path,
              message=f"Schema filename should use snake_case: {basename}",
              severity=Severity.INFO,
              rule="ucp-naming",
          )
      )

  return issues


def validate_file(filepath: str) -> ValidationResult:
  """Validates a single file for syntax, references, and structure.

  Args:
    filepath: Path to the file to validate.

  Returns:
    ValidationResult containing any issues found.
  """
  result = ValidationResult()
  result.files_checked = 1

  # 1. Validate JSON
  if filepath.endswith(".json"):
    try:
      with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

      # Check references
      ref_issues = check_refs(data, filepath, root_data=data)
      for issue in ref_issues:
        result.add(issue)

      # Determine file type and run appropriate structural validation
      if "openapi" in data:
        openapi_issues = validate_openapi_structure(data, filepath)
        for issue in openapi_issues:
          result.add(issue)
      elif "$schema" in data or "properties" in data or "$defs" in data:
        schema_issues = validate_json_schema_structure(data, filepath)
        for issue in schema_issues:
          result.add(issue)

      if not result.has_errors:
        result.files_passed = 1

    except json.JSONDecodeError as e:
      result.add(
          ValidationIssue(
              file_path=filepath,
              message=f"JSON syntax error: {e.msg}",
              line=e.lineno,
              column=e.colno,
              rule="json-syntax",
          )
      )
    except OSError as e:
      result.add(
          ValidationIssue(
              file_path=filepath,
              message=f"File read error: {e}",
              rule="file-read",
          )
      )

  # 2. Validate YAML
  elif filepath.endswith((".yaml", ".yml")):
    try:
      with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

      # Check references
      ref_issues = check_refs(data, filepath, root_data=data)
      for issue in ref_issues:
        result.add(issue)

      # Check OpenAPI structure if applicable
      if isinstance(data, dict) and "openapi" in data:
        openapi_issues = validate_openapi_structure(data, filepath)
        for issue in openapi_issues:
          result.add(issue)

      if not result.has_errors:
        result.files_passed = 1

    except yaml.YAMLError as e:
      result.add(
          ValidationIssue(
              file_path=filepath,
              message=f"YAML syntax error: {e}",
              rule="yaml-syntax",
          )
      )
    except OSError as e:
      result.add(
          ValidationIssue(
              file_path=filepath,
              message=f"File read error: {e}",
              rule="file-read",
          )
      )

  else:
    # Non-JSON/YAML files are ignored
    result.files_checked = 0

  return result


def print_result(result: ValidationResult, verbose: bool = False) -> None:
  """Prints validation results in a formatted manner.

  Args:
    result: The validation result to print.
    verbose: If True, print info-level issues too.
  """
  for issue in result.issues:
    if issue.severity == Severity.INFO and not verbose:
      continue

    if issue.severity == Severity.ERROR:
      color = Colors.RED
      prefix = "❌"
    elif issue.severity == Severity.WARNING:
      color = Colors.YELLOW
      prefix = "⚠️ "
    else:
      color = Colors.CYAN
      prefix = "ℹ️ "

    print(f"{color}{prefix} {issue.file_path}{Colors.RESET}")
    print(f"   └── {issue}")


def main() -> None:
  """Main entry point for the validation script."""
  parser = argparse.ArgumentParser(
      description="Validate UCP specification files"
  )
  parser.add_argument(
      "--verbose", "-v", action="store_true", help="Show all issues including info"
  )
  parser.add_argument(
      "--continue", "-c", dest="continue_on_error", action="store_true",
      help="Continue validation after errors (don't stop on first error)"
  )
  parser.add_argument(
      "--openapi-only", action="store_true",
      help="Only validate OpenAPI specification files"
  )
  parser.add_argument(
      "--schemas-only", action="store_true",
      help="Only validate JSON Schema files"
  )
  args = parser.parse_args()

  if not os.path.exists(SPEC_DIR):
    print(
        f"{Colors.YELLOW}Warning: Directory '{SPEC_DIR}' not"
        f" found.{Colors.RESET}"
    )
    sys.exit(0)

  print(f"{Colors.BOLD}🔍 UCP Specification Validator{Colors.RESET}")
  print(f"   Scanning '{SPEC_DIR}/' for syntax, reference, and structure issues...\n")

  total_result = ValidationResult()

  # Determine which directories to scan
  scan_dirs = []
  if args.openapi_only:
    scan_dirs = [OPENAPI_DIR]
  elif args.schemas_only:
    scan_dirs = [SCHEMAS_DIR]
  else:
    scan_dirs = [SPEC_DIR]

  for scan_dir in scan_dirs:
    if not os.path.exists(scan_dir):
      continue

    for root, _, files in os.walk(scan_dir):
      for filename in files:
        full_path = os.path.join(root, filename)

        # Skip hidden files or unrelated types
        if filename.startswith(".") or not filename.endswith(
            (".json", ".yaml", ".yml")
        ):
          continue

        file_result = validate_file(full_path)
        total_result.merge(file_result)

        if file_result.has_errors:
          print_result(file_result, args.verbose)
          if not args.continue_on_error:
            print(f"\n{Colors.RED}Stopped on first error.{Colors.RESET}")
            sys.exit(1)
        elif file_result.warning_count > 0 and args.verbose:
          print_result(file_result, args.verbose)
        else:
          # Progress indicator
          print(f"{Colors.GREEN}.{Colors.RESET}", end="", flush=True)

  print("\n")

  # Summary
  print(f"{Colors.BOLD}Summary:{Colors.RESET}")
  print(f"  Files checked: {total_result.files_checked}")
  print(f"  Files passed:  {total_result.files_passed}")
  print(f"  Errors:        {total_result.error_count}")
  print(f"  Warnings:      {total_result.warning_count}")

  if total_result.error_count == 0:
    print(
        f"\n{Colors.GREEN}✅ Success! All {total_result.files_checked} files"
        f" passed validation.{Colors.RESET}"
    )
    sys.exit(0)
  else:
    print(
        f"\n{Colors.RED}🚨 Failed. Found {total_result.error_count} errors"
        f" in {total_result.files_checked - total_result.files_passed}"
        f" files.{Colors.RESET}"
    )
    sys.exit(1)


if __name__ == "__main__":
  main()
