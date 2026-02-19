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


"""MkDocs hooks for UCP documentation.

Processes source files during build:
1. Resolve relative $ref to absolute URLs (using $id from referenced files)
2. Rewrite all ucp.dev/schemas/ URLs to include version for proper resolution
3. Copy to site directory based on $id path

Mike handles deployment to /{version}/ paths, so output paths exclude version
but $id/$ref URLs include it for correct resolution after deployment.
"""

import json
import logging
import re
import shutil
from datetime import date
from pathlib import Path

log = logging.getLogger("mkdocs")

# URL prefix for UCP schemas that need version injection
UCP_SCHEMA_PREFIX = "https://ucp.dev/schemas/"
# Pattern for valid date-based versions
DATE_VERSION_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _process_refs(data, current_file_dir):
  """Recursively resolve relative $ref paths to absolute URLs.

  Reads referenced file's $id to construct the absolute URL.
  Only processes relative refs (not # fragments or http URLs).
  """
  if isinstance(data, dict):
    for key, value in data.items():
      if (
        key == "$ref"
        and isinstance(value, str)
        and not value.startswith(("#", "http"))
      ):
        ref_parts = value.split("#", 1)
        relative_path = ref_parts[0]
        fragment = f"#{ref_parts[1]}" if len(ref_parts) > 1 else ""

        if not relative_path:
          continue

        ref_file_path = (current_file_dir / relative_path).resolve()

        try:
          with ref_file_path.open("r", encoding="utf-8") as f:
            ref_data = json.load(f)

          if "$id" in ref_data:
            data[key] = ref_data["$id"] + fragment
          else:
            log.warning(
              f"No '$id' found in {ref_file_path}. "
              f"Keeping original '$ref': {value}"
            )
        except FileNotFoundError:
          log.error(
            f"Referenced file not found: {ref_file_path}. "
            f"Keeping original '$ref': {value}"
          )
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
          log.error(
            f"Failed to read referenced file {ref_file_path}: {e}. "
            f"Keeping original '$ref': {value}"
          )
      else:
        _process_refs(value, current_file_dir)
  elif isinstance(data, list):
    for item in data:
      _process_refs(item, current_file_dir)


def _rewrite_version_urls(data, url_version):
  """Recursively rewrite ucp.dev/schemas/ URLs to include version.

  Transforms: https://ucp.dev/schemas/X -> https://ucp.dev/{url_version}/schemas/X

  This ensures $id matches the deployed URL and $ref resolves correctly.
  Applied to both $id and $ref fields.
  """
  versioned_prefix = f"https://ucp.dev/{url_version}/schemas/"

  if isinstance(data, dict):
    for key, value in data.items():
      if (
        key in ("$id", "$ref")
        and isinstance(value, str)
        and value.startswith(UCP_SCHEMA_PREFIX)
      ):
        data[key] = value.replace(UCP_SCHEMA_PREFIX, versioned_prefix, 1)
      else:
        _rewrite_version_urls(value, url_version)
  elif isinstance(data, list):
    for item in data:
      _rewrite_version_urls(item, url_version)


def _set_schema_version(data, version):
  """Set version field for named entities (capabilities, services, handlers).

  Named entities (schemas with top-level 'name' field) require version per
  ucp.json#/$defs/entity. Build injects version so source files don't need it.

  Additionally, for OpenAPI and OpenRPC transport specifications, set the
  required info.version field.
  """
  if "name" in data:
    data["version"] = version

  if ("openapi" in data or "openrpc" in data) and isinstance(
    data["info"], dict
  ):
    data["info"]["version"] = version


def on_post_build(config):
  """Copy and process source files into the site directory.

  For JSON files:
  1. Resolve relative $ref to absolute URLs
  2. Set schema version field
  3. Rewrite URLs to include version (for proper resolution after deployment)
  4. Output to path derived from original $id (mike adds version prefix)

  Non-JSON files are copied as-is.

  Version handling:
  - YYYY-MM-DD: use for both URL path and version field
  - Non-date (e.g., 'draft'): URL uses literal, version = today's date
  """
  ucp_version = config.get("extra", {}).get("ucp_version")
  if not ucp_version:
    log.warning("No ucp_version in mkdocs.yml extra config")
    url_version = None
    schema_version = None
  else:
    # URL always uses configured version string (date or label like 'draft')
    url_version = ucp_version
    if DATE_VERSION_PATTERN.match(ucp_version):
      schema_version = ucp_version
    else:
      # Non-date: $id matches deployed URL, version = publish date
      schema_version = date.today().isoformat()
      log.info(
        f"Non-date version '{ucp_version}': schema version set to "
        f"'{schema_version}'"
      )

  base_src_path = Path.cwd() / "source"
  if not base_src_path.exists():
    log.warning("Source directory not found: %s", base_src_path)
    return

  for src_file in base_src_path.rglob("*"):
    if not src_file.is_file():
      continue
    rel_path = src_file.relative_to(base_src_path).as_posix()

    if not src_file.name.endswith(".json"):
      dest_file = Path(config["site_dir"]) / rel_path
      dest_dir = dest_file.parent
      dest_dir.mkdir(exist_ok=True, parents=True)
      shutil.copy2(src_file, dest_file)
      log.info("Copied %s to %s", src_file, dest_file)
      continue

    # Process JSON files
    try:
      with src_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

      # Determine output path from ORIGINAL $id (before version rewrite).
      # Mike deploys site/ to /{version}/, so we exclude version from path.
      file_id = data.get("$id")
      if file_id and file_id.startswith("https://ucp.dev"):
        file_rel_path = file_id.removeprefix("https://ucp.dev").lstrip("/")
      else:
        file_rel_path = rel_path

      # Step 1: Resolve relative $ref to absolute URLs
      _process_refs(data, src_file.parent)

      # Step 2: Inject version field for named entities
      if schema_version:
        _set_schema_version(data, schema_version)

      # Step 3: Rewrite URLs to include version
      if url_version:
        _rewrite_version_urls(data, url_version)

      dest_file = Path(config["site_dir"]) / file_rel_path
      dest_dir = dest_file.parent

      dest_dir.mkdir(exist_ok=True, parents=True)
      with dest_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
      log.info("Processed and copied %s to %s", src_file, dest_file)

    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
      log.error(
        "Failed to process JSON file %s, copying as-is: %s", src_file, e
      )
      # Fallback to copying if processing fails
      dest_file = Path(config["site_dir"]) / rel_path
      dest_dir = dest_file.parent
      dest_dir.mkdir(exist_ok=True, parents=True)
      shutil.copy2(src_file, dest_file)
