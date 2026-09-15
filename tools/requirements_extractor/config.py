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

"""Tunable configuration for the requirements extractor.

Everything the pipeline treats as policy rather than mechanism lives here:
which documents are in scope, which keywords count, which words name an actor,
and how a document maps to a capability.

Capability resolution is deliberately minimal at present. The full design is a
four-tier fallback chain, because only 11 of the 46 specification documents
declare their own capability:

  Tier 1  Explicit ``* **Capability Name:**`` bullet in the document.
  Tier 2  mkdocs.yml nav grouping - inherit from the group's Overview page.
  Tier 3  Intra-document link - binding docs open by linking to their parent.
  Tier 4  Explicit override map for documents none of the above resolve.

Every document currently in scope sits under a single capability directory, so
Tier 1 plus a directory prefix settles all of them and tiers 2-4 are not yet
implemented. `resolve_capability` is the seam they will be added behind; no
caller needs to change when they are.
"""

from __future__ import annotations

from pathlib import Path
import re

# Repository root, resolved from this file so the extractor can be invoked
# from any working directory.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

MKDOCS_PATH = REPO_ROOT / "mkdocs.yml"
SCHEMA_ROOT = REPO_ROOT / "source" / "schemas"

# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------

# Directories scanned for normative prose. Scoped to the checkout capability.
SPEC_DIRS = [Path("docs/specification/shopping/checkout")]

# Documents excluded even when they fall inside SPEC_DIRS.
#
# `payment/template.md` is a scaffold whose body is placeholder text, including
# the corpus's only `**Version:**` line, which reads `{YYYY-MM-DD}`. Extracting
# it would mint requirements from a form letter. Listed here rather than in the
# scope filter so it stays excluded if SPEC_DIRS ever widens.
EXCLUDED_FILES = frozenset(
  {
    "docs/specification/payment/template.md",
    "docs/specification/shopping/playground.md",
  }
)

# ---------------------------------------------------------------------------
# Capability resolution
# ---------------------------------------------------------------------------

# Directory prefix -> capability. Consulted after an explicit in-document
# declaration and before the (not yet implemented) nav and link tiers.
CAPABILITY_BY_PREFIX = {
  "docs/specification/shopping/checkout": "dev.ucp.shopping.checkout",
}

# Matches the declaration bullet, anchored on the list marker and bold label so
# it cannot match the "Capability Name" column header of the registry table in
# overview/index.md.
CAPABILITY_DECLARATION_RE = re.compile(
  r"^\s*[*\-+]\s+\*\*Capability Name:\*\*\s*`([a-z0-9_.]+)`\s*$",
  re.MULTILINE,
)

# Only the first N lines of a document are searched for the declaration. The
# bullet is part of the document preamble; a match further down is prose about
# some other capability, not a declaration of this one.
CAPABILITY_DECLARATION_MAX_LINE = 40

# Fallback when mkdocs.yml cannot be read. Release branches bake a date into
# `extra.ucp_version`; main carries "draft".
DEFAULT_SPEC_VERSION = "draft"

# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------

# Ordered longest-first. Callers MUST match in this order so that "MUST NOT" is
# never truncated to "MUST" - a truncation bug here silently inverts the
# meaning of every prohibition in the corpus.
OBLIGATION_KEYWORDS = (
  "MUST NOT",
  "SHALL NOT",
  "SHOULD NOT",
  "MUST",
  "SHALL",
  "SHOULD",
  "MAY",
)

ANNOTATION_KEYWORDS = ("REQUIRED", "RECOMMENDED", "OPTIONAL")

ALL_KEYWORDS = OBLIGATION_KEYWORDS + ANNOTATION_KEYWORDS

# A clause citing at least this many distinct keywords is the RFC 2119
# boilerplate paragraph ("The key words MUST, MUST NOT, REQUIRED, ...") rather
# than an obligation. Dropped and logged.
RFC2119_BOILERPLATE_KEYWORD_THRESHOLD = 4

# ---------------------------------------------------------------------------
# Actor resolution
# ---------------------------------------------------------------------------

# Canonical actor -> surface forms. Matching is case-insensitive and takes the
# LAST match preceding the keyword, not the first: in "When a buyer selects an
# option the platform cannot fully process, the platform **SHOULD** ...", the
# first match yields `buyer` and the last correctly yields `platform`.
ACTOR_LEXICON = {
  "business": ("business", "businesses", "merchant", "merchants"),
  "platform": ("platform", "platforms"),
  "agent": ("agent", "agents"),
  "handler": ("payment handler", "payment handlers", "handler", "handlers"),
  "buyer": ("buyer", "buyers", "user", "users"),
  "host": ("host", "hosts"),
  "auth_server": ("authorization server", "auth server"),
}

# Confidence assigned by each resolution strategy.
ACTOR_CONFIDENCE_ANNOTATION = 1.0  # explicit <!-- ucp:actor=... --> override
ACTOR_CONFIDENCE_INLINE = 0.9  # lexicon match within the clause
ACTOR_CONFIDENCE_COMPOUND_PARENT = 0.8  # inherited from a colon-list stem
ACTOR_CONFIDENCE_SECTION = 0.5  # inferred from the heading breadcrumb
ACTOR_CONFIDENCE_NONE = 0.0  # unresolved

# Clauses below this are surfaced in the report for author review.
ACTOR_LOW_CONFIDENCE_THRESHOLD = 0.6

# ---------------------------------------------------------------------------
# Referenced fields
# ---------------------------------------------------------------------------

# Inline-code spans longer than this are URLs or code fragments, not fields.
FIELD_MAX_LENGTH = 40

# Protocol nouns that appear in backticks but are not schema fields.
FIELD_STOP_WORDS = frozenset(
  {
    "GET",
    "PUT",
    "POST",
    "PATCH",
    "DELETE",
    "HEAD",
    "OPTIONS",
    "application/json",
    "true",
    "false",
    "null",
  }
)

FIELD_URL_RE = re.compile(r"^https?://")

# ---------------------------------------------------------------------------
# Conditions
# ---------------------------------------------------------------------------

CONDITION_TRIGGER_RE = re.compile(
  r"\b(when|if|unless|whenever|while|in case)\b", re.IGNORECASE
)

# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

# Hex characters retained from the sha256 of the normalized clause. Ten gives
# roughly 1.1e12 of space, which is ample for a corpus of this size while
# keeping IDs readable in prose and commit messages.
ID_DIGEST_LENGTH = 10

ID_PREFIX = "UCP"

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

OUTPUT_DIR = REPO_ROOT / "generated" / "requirements"
DEFAULT_CATALOG_PATH = OUTPUT_DIR / "requirements.json"
DEFAULT_REPORT_PATH = OUTPUT_DIR / "extraction_report.json"

CATALOG_SCHEMA_VERSION = "1.0.0"
EXTRACTOR_VERSION = "0.1.0"


def spec_version() -> str:
  """Return the UCP release the specification tree represents.

  Read from ``extra.ucp_version`` in mkdocs.yml at runtime rather than being
  hardcoded, because the value differs by branch: release branches bake in a
  date such as ``2026-08-25`` while main carries ``draft``. Hardcoding it would
  silently stamp the wrong release onto a catalog built from another branch.

  Parsed with a narrow regex instead of a YAML load so the extractor does not
  depend on PyYAML and does not have to tolerate the custom mkdocs tags that a
  strict loader rejects.

  Returns:
    The declared version, or DEFAULT_SPEC_VERSION if it cannot be determined.

  """
  try:
    text = MKDOCS_PATH.read_text(encoding="utf-8")
  except OSError:
    return DEFAULT_SPEC_VERSION
  match = re.search(
    r"^\s*ucp_version:\s*[\"']?([^\"'\s]+)[\"']?\s*$", text, re.MULTILINE
  )
  return match.group(1) if match else DEFAULT_SPEC_VERSION


def capability_slug(capability: str | None) -> str:
  """Reduce a reverse-DNS capability to the slug used inside requirement IDs.

  Strips the ``dev.ucp.`` prefix and raises the remainder to upper case, so
  ``dev.ucp.shopping.checkout`` becomes ``SHOPPING-CHECKOUT``.

  Args:
    capability: Reverse-DNS capability identifier, or None.

  Returns:
    An uppercase, hyphen-separated slug. Unresolved capabilities yield
    ``UNRESOLVED`` so the resulting IDs are conspicuous rather than malformed.

  """
  if not capability:
    return "UNRESOLVED"
  trimmed = capability.removeprefix("dev.ucp.")
  return re.sub(r"[._]", "-", trimmed).upper()


def is_excluded(rel_path: str) -> bool:
  """Whether a repository-relative path is excluded from extraction.

  Args:
    rel_path: Repository-relative path with POSIX separators.

  Returns:
    True if the document should not be scanned.

  """
  return rel_path in EXCLUDED_FILES


def declared_capability(path: Path) -> str | None:
  """Return the capability a document declares about itself, if any.

  This is Tier 1 of the resolution chain. Only the document preamble is
  searched, since the declaration bullet is part of the header block and a
  later match would be prose discussing some other capability.

  Args:
    path: Absolute path to a Markdown document.

  Returns:
    The reverse-DNS capability identifier, or None if undeclared.

  """
  try:
    with path.open(encoding="utf-8") as handle:
      preamble = "".join(
        line
        for _, line in zip(
          range(CAPABILITY_DECLARATION_MAX_LINE), handle, strict=False
        )
      )
  except OSError:
    return None
  match = CAPABILITY_DECLARATION_RE.search(preamble)
  return match.group(1) if match else None


def resolve_capability(
  rel_path: str, abs_path: Path | None = None
) -> str | None:
  """Resolve the capability a document's requirements belong to.

  Resolution order, matching the chain described in the module docstring:

    1. An explicit declaration inside the document.
    2. The directory the document lives in.

  Tiers 3 and 4 of the full design - mkdocs nav grouping, intra-document
  parent links, and a hand-maintained override map - are not implemented,
  because every document currently in scope resolves at tier 1 or 2. They
  belong here, as additional branches, when scope widens beyond a single
  capability directory.

  Args:
    rel_path: Repository-relative path with POSIX separators.
    abs_path: Absolute path, when available, enabling the tier 1 lookup.

  Returns:
    The reverse-DNS capability identifier, or None when unresolved. Callers
    decide whether an unresolved document is fatal; see --fail-on-unresolved.

  """
  if abs_path is not None:
    declared = declared_capability(abs_path)
    if declared:
      return declared

  # Longest prefix wins, so a nested capability directory is preferred over a
  # broader one should the map ever contain both.
  for prefix in sorted(CAPABILITY_BY_PREFIX, key=len, reverse=True):
    if rel_path == prefix or rel_path.startswith(prefix + "/"):
      return CAPABILITY_BY_PREFIX[prefix]

  return None
