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

This module contains functions that are executed during the MkDocs build
process.
Currently, it includes a hook to copy specs files into the site directory
after the build is complete.
This makes the specs JSON files available in the website and programmatically
accessible.
"""

import json
import logging
import shutil
from pathlib import Path

log = logging.getLogger("mkdocs")


def _process_refs(data, current_file_dir):
  """Recursively processes $ref fields in a JSON object."""
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


def on_post_build(config):
  """Copy and process spec files into the site directory.

  For JSON files, it resolves $ref paths to absolute URLs and standardizes
  response file names. Non-JSON files are copied as-is.
  """
  base_src_path = Path.cwd() / "spec"
  if not base_src_path.exists():
    log.warning("Spec source directory not found: %s", base_src_path)
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

      # Determine the final relative path for the destination
      file_id = data.get("$id")
      prefix = "https://ucp.dev"
      if file_id and file_id.startswith(prefix):
        file_rel_path = file_id[len(prefix) :].lstrip("/")
      else:
        file_rel_path = rel_path.replace("_resp.json", ".json").replace(
          "_schema.json", ".json"
        )

      # Process refs using the final path
      _process_refs(data, src_file.parent)

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
