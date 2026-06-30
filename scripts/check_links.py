"""Script to check for broken internal links and anchors in the built site."""

import argparse
import os
import sys
import json
import re
from html.parser import HTMLParser
import requests
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
from urllib.parse import urlparse, unquote
from pathlib import Path
from collections import defaultdict

# Configuration
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
    # Handle bare URLs surrounded by angle brackets (e.g., <https://ucp.dev/b>)
    # HTMLParser mistakenly treats these as HTML tags instead of text data.
    if not self.is_ignoring_links and tag in ("http:", "https:"):
      raw_tag = self.get_starttag_text()
      if raw_tag:
        # This regex is for URLs that HTMLParser mistakes as tags, like
        # <https://ucp.dev/b>. It finds all such URLs in the raw tag text.
        urls = re.findall(r"https://ucp\.dev[^\s>]+", raw_tag)
        for url in urls:
          if (
            not url.endswith("...")
            and not url.endswith("*")
            and url not in self.links
          ):
            self.links.append(url)

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

    # Find URLs inside quotes, angle brackets, or just in plain text.
    # This pattern handles URLs that might be surrounded by various delimiters.
    # It correctly extracts URLs without including trailing punctuation.
    urls = re.findall(r'https://ucp\.dev[^\s"\'<>]+', data)

    for url in urls:
      if url.endswith("...") or url.endswith("*"):
        continue
      if url not in self.links:
        self.links.append(url)


def check_links():
  """Scan the built documentation site for broken links and anchors."""
  parser = argparse.ArgumentParser(
    description="Check for broken internal links and anchors in the built site."
  )
  parser.add_argument(
    "root_dir",
    nargs="?",
    type=Path,
    default=Path("local_preview"),
    help="Directory containing the built site (default: local_preview)",
  )
  parser.add_argument(
    "--check-external",
    action="store_true",
    help="Check external links for reachability (can be slow).",
  )
  parser.add_argument(
    "--format",
    choices=["text", "json"],
    default="text",
    help="Output format (default: text)",
  )
  args = parser.parse_args()
  root_dir = args.root_dir

  if not root_dir.exists():
    print(
      f"Error: {root_dir} does not exist. "
      "Ensure you've run `mkdocs build` or `mkdocs serve` and specified "
      "the correct output directory, or mkdocs build (CI) first."
    )
    sys.exit(1)

  ignore_patterns = []
  try:
    with Path(".linkignore").open("r", encoding="utf-8") as f:
      for line in f:
        line = line.strip()
        if line and not line.startswith("#"):
          try:
            ignore_patterns.append(re.compile(line))
          except re.error as e:
            print(f"Warning: Invalid regex in .linkignore '{line}': {e}")
  except FileNotFoundError:
    pass  # .linkignore is optional and it is safe to skip
  except Exception as e:
    print(f"Warning: Could not read .linkignore: {e}")

  if args.format != "json":
    print(f"Scanning {root_dir} for broken links (Site URL: {SITE_URL})...")

  html_files = list(root_dir.rglob("*.html"))
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

  def check_external_link(link):
    try:
      # Use a timeout to prevent hanging and a user-agent to avoid some blocks
      headers = {
        "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/91.0.4472.124 Safari/537.36"
        )
      }
      response = requests.head(
        link, timeout=10, allow_redirects=True, headers=headers
      )

      # Some sites block HEAD requests (403, 404, 405) or rate limit like
      # GitHub (429). In this case, we retry with a GET request.
      if response.status_code in (403, 404, 405, 429):
        response = requests.get(
          link, timeout=10, allow_redirects=True, headers=headers
        )

      if 200 <= response.status_code < 400 or response.status_code == 429:
        return True, None
      else:
        return (
          False,
          f"External link returned status code {response.status_code}",
        )
    except requests.exceptions.RequestException as e:
      return False, f"Failed to connect: {e}"

  # Parallelize HTML file parsing
  with ThreadPoolExecutor() as executor:
    futures = {
      executor.submit(get_file_ids, html_file): html_file
      for html_file in html_files
    }
    for future in futures:
      _ = future.result()  # Ensure all files are parsed and cached

  # For parallel external link checking
  external_links_to_check = set()
  file_external_links = defaultdict(list)

  for file_path in html_files:
    try:
      rel_path = file_path.relative_to(root_dir)
      first_part = rel_path.parts[0]

      # Heuristic for version detection
      is_version = False
      if first_part in ["draft", "latest"] or re.match(
        r"^\d{4}-\d{2}-\d{2}$", first_part
      ):
        is_version = True

      version = first_part if is_version else "root"
    except (ValueError, IndexError):
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

      # Check if any ignore pattern matches. The any() function provides a
      # short-circuiting and more Pythonic way to do this.
      if any(pattern.search(original_link) for pattern in ignore_patterns):
        continue

      # Ignore external links
      if link.startswith(("mailto:", "tel:", "javascript:", "data:")):
        continue

      # Check external links if --check-external is set
      parsed = urlparse(link)
      if parsed.scheme and parsed.scheme in ("http", "https"):
        if not link.startswith(SITE_URL):
          if args.check_external:
            external_links_to_check.add(link)
            file_external_links[file_path].append((version, link))
          continue  # External links are handled or ignored beyond this point

        # Internal absolute URL
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
          and not (root_dir / parts[0]).exists()
        ):
          rel_path = parts[1]

        target_file = root_dir / rel_path
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

  # Process external links in parallel
  if args.check_external and external_links_to_check:
    if args.format != "json":
      print(
        f"Checking {len(external_links_to_check)} external links in parallel..."
      )
    external_results = {}
    with ThreadPoolExecutor(max_workers=20) as executor:
      future_to_link = {
        executor.submit(check_external_link, link_url): link_url
        for link_url in external_links_to_check
      }
      for future in concurrent.futures.as_completed(future_to_link):
        link_url = future_to_link[future]
        external_results[link_url] = future.result()

    for file_path, links in file_external_links.items():
      for version, link in links:
        is_valid, error_msg = external_results[link]
        if not is_valid:
          errors_by_version[version][str(file_path)].append(
            f"  External Link: {link}\n  Reason: {error_msg}"
          )

  if errors_by_version:
    if args.format == "json":
      out = []
      for v, files in errors_by_version.items():
        for fp, errs in files.items():
          for e in errs:
            out.append({"version": v, "file": fp, "error": e.strip()})
      print(json.dumps(out, indent=2))
      sys.exit(1)

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
    if args.format != "json":
      print("All links validated successfully.")


if __name__ == "__main__":
  check_links()
