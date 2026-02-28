"""Script to check for broken internal links and anchors in the built site."""

import os
import sys
import re
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote
from pathlib import Path
from collections import defaultdict

# Configuration
ROOT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("local_preview")
SITE_URL = os.environ.get("SITE_URL", "https://ucp.dev/")

# Ensure trailing slash for site url to match correctly
if not SITE_URL.endswith("/"):
  SITE_URL += "/"
SITE_BASE_PATH = urlparse(SITE_URL).path
if SITE_BASE_PATH == "":
  SITE_BASE_PATH = "/"


class LinkParser(HTMLParser):
  """Parses HTML to extract links and id attributes."""

  def __init__(self):
    """Initialize the LinkParser."""
    super().__init__()
    self.links = []
    self.ids = set()
    self.is_ignoring_links = False

  def handle_comment(self, data):
    """Detect comments instructing to ignore links."""
    if "ignore-link-begin" in data:
      self.is_ignoring_links = True
    elif "ignore-link-end" in data:
      self.is_ignoring_links = False

  def handle_starttag(self, tag, attrs):
    """Extract href from anchor tags and id/name attributes from all tags."""
    attrs_dict = dict(attrs)
    if tag == "a" and "href" in attrs_dict:
      href = attrs_dict["href"]
      if (
        not self.is_ignoring_links
        and not href.endswith("...")
        and not href.endswith("*")
      ):
        self.links.append(href)

    # Collect IDs for anchor validation
    if "id" in attrs_dict:
      self.ids.add(attrs_dict["id"])
    if "name" in attrs_dict:  # Old style anchors
      self.ids.add(attrs_dict["name"])

  def handle_data(self, data):
    """Extract bare ucp.dev URLs from text content."""
    if self.is_ignoring_links:
      return

    # Find anything that looks like https://ucp.dev/... in the text
    urls = re.findall(r"https://ucp\.dev[^\s\"\'<>]*", data)
    for url in urls:
      if url.endswith("...") or url.endswith("*"):
        continue
      if url not in self.links:
        self.links.append(url)


def check_links():
  """Scan the built documentation site for broken links and anchors."""
  if not ROOT_DIR.exists():
    print(
      f"Error: {ROOT_DIR} does not exist. Run build_local.sh (local) "
      "or mkdocs build (CI) first."
    )
    sys.exit(1)

  ignore_patterns = []
  if Path(".linkignore").exists():
    try:
      with Path.open(".linkignore", "r", encoding="utf-8") as f:
        for line in f:
          line = line.strip()
          if line and not line.startswith("#"):
            try:
              ignore_patterns.append(re.compile(line))
            except re.error as e:
              print(f"Warning: Invalid regex in .linkignore '{line}': {e}")
    except Exception as e:
      print(f"Warning: Could not read .linkignore: {e}")

  print(f"Scanning {ROOT_DIR} for broken links (Site URL: {SITE_URL})...")

  html_files = list(ROOT_DIR.rglob("*.html"))
  file_cache = {}  # Cache parsed IDs for each file to avoid re-parsing
  # Structure: errors_by_version[version][file_path] = [list of error details]
  errors_by_version = defaultdict(lambda: defaultdict(list))

  def get_file_ids(path):
    if path in file_cache:
      return file_cache[path]

    if not path.exists():
      return None

    try:
      content = path.read_text(encoding="utf-8")
      parser = LinkParser()
      parser.feed(content)
      file_cache[path] = parser.ids
      return parser.ids
    except Exception:
      # print(f"Failed to parse {path}: {e}") # Reduce noise
      return None

  for file_path in html_files:
    try:
      rel_path = file_path.relative_to(ROOT_DIR)
      first_part = rel_path.parts[0]

      # Heuristic for version detection
      is_version = False
      if first_part in ["draft", "latest"] or re.match(
        r"^\d{4}-\d{2}-\d{2}$", first_part
      ):
        is_version = True

      version = first_part if is_version else "root"
    except Exception:
      version = "unknown"

    try:
      content = file_path.read_text(encoding="utf-8")
    except Exception as e:
      errors_by_version[version][str(file_path)].append(
        f"  Could not read file: {e}"
      )
      continue

    parser = LinkParser()
    parser.feed(content)
    file_cache[file_path] = parser.ids

    for link in parser.links:
      original_link = link

      should_ignore = False
      for pattern in ignore_patterns:
        if pattern.search(original_link):
          should_ignore = True
          break
      if should_ignore:
        continue

      # Ignore external links
      if link.startswith(("mailto:", "tel:", "javascript:", "data:")):
        continue

      parsed = urlparse(link)
      if parsed.scheme and parsed.scheme in ("http", "https"):
        if not link.startswith(SITE_URL):
          continue  # External link
        # Internal absolute URL (e.g. https://ucp.dev/foo) -> /foo
        link = link[len(SITE_URL) - 1 :]  # Keep the leading slash

      path_part = parsed.path
      anchor_part = parsed.fragment
      path_part = unquote(path_part)

      # If the path starts with the SITE_BASE_PATH (e.g. /ucp/), strip it
      # so it resolves correctly against the local ROOT_DIR.
      if SITE_BASE_PATH != "/" and path_part.startswith(SITE_BASE_PATH):
        path_part = "/" + path_part[len(SITE_BASE_PATH) :]

      target_file = None

      # Resolve Target File
      if not path_part:
        target_file = file_path
      elif path_part.startswith("/"):
        # Absolute path from root
        rel_path = path_part[1:]
        parts = rel_path.split("/", 1)

        # If the path starts with a version identifier (latest, draft, or date)
        # and if that directory does NOT exist at the root, we are likely
        # scanning a single isolated build. In this case, strip the prefix to
        # test against the flat structure.
        if (
          len(parts) > 1
          and (
            parts[0] in ["latest", "draft"]
            or re.match(r"^\d{4}-\d{2}-\d{2}$", parts[0])
          )
          and not (ROOT_DIR / parts[0]).exists()
        ):
          rel_path = parts[1]

        target_file = ROOT_DIR / rel_path
      else:
        # Relative path
        target_file = file_path.parent / path_part

      # Handle directory targets
      if target_file.is_dir() or path_part.endswith("/"):
        target_file = target_file / "index.html"

      # Check Existence
      if not target_file.exists():
        # Allow for cases where /foo points to /foo.html
        if not path_part.endswith("/") and not target_file.name.endswith(
          ".html"
        ):
          candidate = target_file.with_name(target_file.name + ".html")
          if candidate.exists():
            target_file = candidate
          else:
            errors_by_version[version][str(file_path)].append(
              f"  Link: {original_link}\n  Target: {target_file} (Not Found)"
            )
            continue
        else:
          errors_by_version[version][str(file_path)].append(
            f"  Link: {original_link}\n  Target: {target_file} (Not Found)"
          )
          continue

      # Check Anchor
      if anchor_part and not target_file.name.endswith(".json"):
        ids = get_file_ids(target_file)
        if ids is None:
          continue

        if anchor_part not in ids:
          errors_by_version[version][str(file_path)].append(
            f"  Link: {original_link}\n"
            f"  Target: {target_file}#{anchor_part} (Anchor not found)"
          )

  if errors_by_version:
    total_errors = sum(
      sum(len(errs) for errs in files.values())
      for files in errors_by_version.values()
    )
    print(f"\nFound {total_errors} broken links:")

    for version in sorted(errors_by_version.keys()):
      print(f"\n=== Version: {version} ===")
      for file_path, errors in sorted(errors_by_version[version].items()):
        print(f"Issues in {file_path}:")
        for e in errors:
          print(e)
    sys.exit(1)
  else:
    print("All internal links validated successfully.")


if __name__ == "__main__":
  check_links()
