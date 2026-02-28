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
import os
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from mkdocs.structure.files import Files

log = logging.getLogger("mkdocs")

# URL prefix for UCP schemas that need version injection
UCP_SCHEMA_PREFIX = "https://ucp.dev/schemas/"
# Pattern for valid date-based versions
DATE_VERSION_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _process_refs(data, current_file_dir, url_version=None):
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
            ref_id = ref_data["$id"]
            if url_version and ref_id.startswith(UCP_SCHEMA_PREFIX):
              versioned_prefix = f"https://ucp.dev/{url_version}/schemas/"
              ref_id = ref_id.replace(UCP_SCHEMA_PREFIX, versioned_prefix, 1)
            data[key] = ref_id + fragment
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
        _process_refs(value, current_file_dir, url_version)
  elif isinstance(data, list):
    for item in data:
      _process_refs(item, current_file_dir, url_version)


def _rewrite_version_urls(data, url_version):
  """Recursively rewrite ucp.dev/schemas/ URLs to include version.

  Transforms: https://ucp.dev/schemas/X
  -> https://ucp.dev/{url_version}/schemas/X

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


def on_config(config):
  """Adjust configuration based on DOCS_MODE."""
  mode = os.environ.get("DOCS_MODE", "root")

  # Update site_url from environment if set (e.g. for forks/CI)
  # This ensures plugins like mkdocs-site-urls use the correct base URL.
  site_url_env = os.environ.get("SITE_URL")
  if site_url_env:
    current_site_url = config.get("site_url", "/")
    # Replace default domain with the env var, preserving version suffix
    if "https://ucp.dev/" in current_site_url:
      config["site_url"] = current_site_url.replace(
        "https://ucp.dev/", site_url_env
      )
      log.info(
        f"Updated site_url to {config['site_url']} based on SITE_URL env var"
      )

  # Calculate base path for links (e.g. / or /ucp/)
  # Do not use config.get("site_url") as mike appends the version directory
  site_url = os.environ.get("SITE_URL", "https://ucp.dev/")
  base_path = urlparse(site_url).path
  if not base_path.endswith("/"):
    base_path += "/"

  # --- Adjust Nav (Config Phase) ---
  # Modifying config['nav'] prevents validation errors for missing files.
  if "nav" in config:
    new_nav = []
    for item in config["nav"]:
      # Nav items are usually dicts {Title: path/content} or strings
      if isinstance(item, dict):
        title = list(item.keys())[0]

        if mode == "root":
          if title == "Specification":
            # Replace Specification section with a Link to the latest spec
            new_nav.append(
              {"Specification": f"{base_path}latest/specification/overview/"}
            )
          else:
            new_nav.append(item)
        elif mode == "spec":
          if title in ("Overview", "Home"):
            # Replace Overview/Home with a Link to the root site
            new_nav.append({"Overview": base_path})
          elif title == "Specification":
            new_nav.append(item)
          # Skip other sections in spec mode
      else:
        # String item (e.g. "index.md")
        if mode == "root":
          new_nav.append(item)
        # In spec mode, we skip root-level string items unless we want them

    config["nav"] = new_nav

  # --- Adjust llmstxt Plugin Config ---
  if "plugins" in config and "llmstxt" in config["plugins"]:
    # config['plugins'] is a PluginCollection (dict-like)
    llms_plugin = config["plugins"]["llmstxt"]
    llms_conf = llms_plugin.config
    if "sections" in llms_conf:
      if mode == "root":
        # Remove any section containing specification/ files
        sections_to_remove = []
        for section_name, pages in llms_conf["sections"].items():
          # pages is a list of strings (file paths)
          if any(p.startswith("specification/") for p in pages):
            sections_to_remove.append(section_name)

        for section_name in sections_to_remove:
          if section_name in llms_conf["sections"]:
            del llms_conf["sections"][section_name]

      elif mode == "spec" and "Overview" in llms_conf["sections"]:
        # Remove Overview section from llmstxt
        del llms_conf["sections"]["Overview"]

  # Always force logo to link to root site
  if "extra" not in config:
    config["extra"] = {}
  config["extra"]["homepage"] = base_path

  if mode == "root" and "version" in config.get("extra", {}):
    # Disable mike version selector for the root site
    del config["extra"]["version"]
  return config


def on_files(files, config):
  """Filter files based on DOCS_MODE (spec or root)."""
  mode = os.environ.get("DOCS_MODE", "root")
  new_files = []
  for f in files:
    if mode == "spec":
      # Include only specification/, assets/, stylesheets/, and index.md
      if (
        f.src_path.startswith("specification/")
        or f.src_path.startswith("assets/")
        or f.src_path.startswith("stylesheets/")
        or f.src_path == "index.md"
      ):
        new_files.append(f)
    elif mode == "root" and not f.src_path.startswith("specification/"):
      # Exclude specification/
      new_files.append(f)
  return Files(new_files)


def on_page_markdown(markdown, page, config, files):
  """Rewrite links to excluded pages (e.g. spec in root mode)."""
  mode = os.environ.get("DOCS_MODE", "root")

  if mode == "root":
    # Rewrite relative links to specification/ to absolute URLs
    # pointing to latest spec.
    site_url = os.environ.get("SITE_URL", "https://ucp.dev/")
    base_path = urlparse(site_url).path
    if not base_path.endswith("/"):
      base_path += "/"

    target_base = f"{base_path}latest/specification/"

    def replace_link(match):
      path = match.group(1)
      if path.endswith("index.md"):
        path = path[:-8]
      elif path.endswith(".md"):
        path = path[:-3] + "/"
      return f"({target_base}{path})"

    # Pattern matches: (  prefix  specification/  path  )
    # We capture the path AFTER specification/
    # Matches: (../specification/foo.md) or (specification/foo.md)
    pattern = r"\((?:(?:\.\./)+|\./)?specification/([^)]+)\)"

    markdown = re.sub(pattern, replace_link, markdown)

    # Rewrite relative links to assets/ to absolute URLs
    # pointing to served assets folder.
    target_base = f"{base_path}assets/"

    def replace_asset_link(match):
      path = match.group(1)
      output = f"{target_base}{path}"
      log.info(f"on_page_markdown::replace_asset_link: {path} -> {output}")
      return output

    # Pattern matches: (  prefix  assets/  path  )
    # We capture the path AFTER assets/
    # Matches: (../assets/foo.img) or (assets/foo.img)
    pattern = r"\"(?:(?:\.\./)+|\./)?assets/([^)\"]+)\""

    markdown = re.sub(pattern, replace_asset_link, markdown)

  return markdown


def on_post_build(config):
  """Copy and process source files into the site directory."""
  # --- Redirects for excluded pages (Spec Mode) ---
  mode = os.environ.get("DOCS_MODE", "root")
  if mode == "spec":
    site_url = os.environ.get("SITE_URL", "https://ucp.dev/")
    base_path = urlparse(site_url).path
    if not base_path.endswith("/"):
      base_path += "/"

    docs_dir = Path(config["docs_dir"])
    site_dir = Path(config["site_dir"])

    # Redirect documentation/* to root site
    doc_folder = docs_dir / "documentation"
    if doc_folder.exists():
      for md_file in doc_folder.rglob("*.md"):
        rel_path = md_file.relative_to(docs_dir).with_suffix(".html")
        dest_file = site_dir / rel_path

        # Target URL: base_path + relative_path
        # (e.g. /ucp/documentation/foo.html)
        target = f"{base_path}{rel_path.as_posix()}"

        dest_file.parent.mkdir(parents=True, exist_ok=True)
        with Path.open(dest_file, "w") as f:
          f.write(
            "<!doctype html>"
            f'<meta http-equiv="refresh" content="0; url={target}">'
          )

    # Redirect index.html to specification/overview/
    index_file = site_dir / "index.html"
    index_target = "specification/overview/"
    index_file.parent.mkdir(parents=True, exist_ok=True)
    with Path.open(index_file, "w") as f:
      f.write(
        "<!doctype html>"
        f'<meta http-equiv="refresh" content="0; url={index_target}">'
      )

  # --- Existing Logic ---
  # --- Existing Logic ---
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

  # Skip copying source schemas for the root site.
  # Root site pages should link to versioned schemas (e.g. /draft/schemas/...)
  if mode == "root":
    return

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
