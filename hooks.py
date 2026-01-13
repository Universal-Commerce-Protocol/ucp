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
import os
import shutil

log = logging.getLogger("mkdocs")


def _process_refs(data, file_rel_path):
    """Recursively processes $ref fields in a JSON object."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "$ref" and isinstance(value, str):
                # 1. Replace _resp.json with .json
                new_ref = value.replace("_resp.json", ".json")

                # 2. Replace relative paths with absolute paths
                if new_ref.startswith("#"):
                    data[key] = f"https://ucp.dev/{file_rel_path}{new_ref}"
                elif not new_ref.startswith("https://"):
                    base_path = os.path.dirname(file_rel_path)
                    # normpath will resolve ../ and ./
                    resolved_path = os.path.normpath(os.path.join(base_path, new_ref))
                    data[key] = f"https://ucp.dev/{resolved_path}"
                else:
                    data[key] = new_ref
            else:
                _process_refs(value, file_rel_path)
    elif isinstance(data, list):
        for item in data:
            _process_refs(item, file_rel_path)


def on_post_build(config):
    """
    Copies and processes spec files into the site directory.

    For JSON files, it resolves $ref paths to absolute URLs and standardizes
    response file names. Non-JSON files are copied as-is.
    """
    base_src_path = os.path.join(os.getcwd(), "spec")
    if not os.path.exists(base_src_path):
        log.warning("Spec source directory not found: %s", base_src_path)
        return

    for root, _, files in os.walk(base_src_path):
        for filename in files:
            src_file = os.path.join(root, filename)
            rel_path = os.path.relpath(src_file, base_src_path)

            if not filename.endswith(".json"):
                dest_file = os.path.join(config["site_dir"], rel_path)
                dest_dir = os.path.dirname(dest_file)
                os.makedirs(dest_dir, exist_ok=True)
                shutil.copy2(src_file, dest_file)
                log.info("Copied %s to %s", src_file, dest_file)
                continue

            # Process JSON files
            try:
                with open(src_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Determine the final relative path for the destination
                file_id = data.get("$id")
                prefix = "https://ucp.dev"
                if file_id and file_id.startswith(prefix):
                    file_rel_path = file_id[len(prefix) :].lstrip("/")
                else:
                    file_rel_path = rel_path.replace("_resp.json", ".json")

                # Process refs using the final path
                _process_refs(data, file_rel_path)

                dest_file = os.path.join(config["site_dir"], file_rel_path)
                dest_dir = os.path.dirname(dest_file)

                os.makedirs(dest_dir, exist_ok=True)
                with open(dest_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                log.info("Processed and copied %s to %s", src_file, dest_file)

            except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
                log.error(
                    "Failed to process JSON file %s, copying as-is: %s", src_file, e
                )
                # Fallback to copying if processing fails
                dest_file = os.path.join(config["site_dir"], rel_path)
                dest_dir = os.path.dirname(dest_file)
                os.makedirs(dest_dir, exist_ok=True)
                shutil.copy2(src_file, dest_file)
