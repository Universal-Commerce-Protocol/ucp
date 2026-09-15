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

"""Stage 1: Markdown to candidate clauses.

Walks the markdown-it token stream and emits one `Clause` per sentence of
normative-eligible prose. This stage makes no judgement about whether a
sentence is normative; that is the classifier's job. It is responsible for
three things the downstream stages cannot recover on their own:

Excluding non-prose
  Fenced and indented code blocks, raw HTML, and inline code spans are not
  prose. The checkout specification contains pseudocode fences using tokens
  like ``IF`` and ``MUST``-shaped words that would otherwise be extracted as
  requirements.

Reflowing hard wraps
  The corpus is wrapped at 80 columns, so a single sentence routinely spans
  several source lines. Sentence boundaries cannot be found until the line
  breaks are collapsed.

Recovering list ancestry
  Where a stem paragraph ends in a colon and is followed by a list, the
  grammatical subject lives in the stem and not in the bullet. The stem is
  attached to each child as `compound_parent` so the metadata stage can
  resolve an actor for bullets that name none.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import re

from markdown_it import MarkdownIt
from markdown_it.token import Token

from tools.requirements_extractor import config
from tools.requirements_extractor.models import BlockType, Clause, SourceRef

# Inline children that contribute no prose and are dropped during rendering.
_DROPPED_INLINE_TYPES = frozenset({"html_inline", "image"})

# Block tokens that are skipped wholesale.
_SKIPPED_BLOCK_TYPES = frozenset({"fence", "code_block", "html_block"})

_LIST_OPEN_TYPES = frozenset({"bullet_list_open", "ordered_list_open"})
_LIST_CLOSE_TYPES = frozenset({"bullet_list_close", "ordered_list_close"})

# Sentence boundary: punctuation, whitespace, then something that looks like
# the start of a new sentence. The negative lookbehinds keep common
# abbreviations intact; without them "e.g. The business ..." splits in two.
#
# Reverse-DNS names (dev.ucp.shopping.checkout), version strings (2026-01-11)
# and RFC references (RFC 8785) need no guard, because the pattern requires
# whitespace after the punctuation and those contain none.
_SENTENCE_SPLIT_RE = re.compile(
  r"(?<=[.:;])"
  r"(?<!e\.g\.)"
  r"(?<!i\.e\.)"
  r"(?<!etc\.)"
  r"(?<!cf\.)"
  r"(?<!vs\.)"
  r"(?<!Fig\.)"
  r"(?<!No\.)"
  r"\s+"
  r"(?=[A-Z`*\[\-])"
)

# Ordered-list numerals that survive sentence splitting, e.g. a fragment
# ending "... unless already cached. 2." where the trailing numeral is the
# marker of the following list item rather than part of the sentence.
_TRAILING_NUMERAL_RE = re.compile(r"\s*\b\d+\.\s*$")
_LEADING_NUMERAL_RE = re.compile(r"^\s*\d+\.\s+")

# Inline code spans. Matched here so keyword scanning can ignore their
# contents while preserving offsets, and so sentence splitting cannot break
# on punctuation that belongs to a code sample.
_CODE_SPAN_RE = re.compile(r"`[^`]*`")

# A sentence must contain at least one letter to be worth considering; this
# drops table cells holding only punctuation, dashes or numbers.
_HAS_LETTER_RE = re.compile(r"[A-Za-z]")


def mask_code_spans(text: str) -> str:
  """Blank out inline code spans while preserving character offsets.

  Inline code carries schema field names, not prose, and must never be
  scanned for RFC 2119 keywords: a literal ``MUST`` inside backticks is a
  value being named, not an obligation being stated. Replacing each span with
  spaces of equal width keeps offsets stable so a caller can map a match back
  onto the unmasked text.

  Args:
    text: Rendered Markdown of a clause.

  Returns:
    The same string with the interior of every code span replaced by spaces.

  """
  return _CODE_SPAN_RE.sub(lambda m: " " * len(m.group(0)), text)


def _render_inline(token: Token) -> str:
  """Reconstruct Markdown source text from an inline token's children.

  Emphasis markers are preserved because the classifier treats bolding as the
  signal that a keyword is a deliberate obligation. Code spans keep their
  backticks so the metadata stage can recover referenced field names. Soft
  breaks become spaces, which is what reflows the hard-wrapped source.

  Args:
    token: An ``inline`` token.

  Returns:
    Markdown text for the token, on a single line.

  """
  parts: list[str] = []
  link_targets: list[str] = []

  for child in token.children or []:
    kind = child.type
    if kind in _DROPPED_INLINE_TYPES:
      continue
    if kind == "text":
      parts.append(child.content)
    elif kind == "code_inline":
      parts.append(f"`{child.content}`")
    elif kind in ("softbreak", "hardbreak"):
      parts.append(" ")
    elif kind in ("strong_open", "strong_close"):
      parts.append("**")
    elif kind in ("em_open", "em_close"):
      parts.append("*")
    elif kind == "link_open":
      link_targets.append(child.attrGet("href") or "")
      parts.append("[")
    elif kind == "link_close":
      href = link_targets.pop() if link_targets else ""
      parts.append(f"]({href})")
    else:
      parts.append(child.content or "")

  return " ".join("".join(parts).split())


def _mask_code_interiors(text: str) -> str:
  """Blank the inside of every code span, keeping the backticks.

  Used for locating sentence boundaries. `mask_code_spans` cannot serve here
  because it blanks the backticks too, and a sentence is allowed to begin
  with a code span -- erasing the opening backtick would hide that boundary.

  Args:
    text: Rendered Markdown of a clause.

  Returns:
    The same string, same length, with code span interiors replaced by
    spaces.

  """
  return _CODE_SPAN_RE.sub(
    lambda m: "`" + " " * (len(m.group(0)) - 2) + "`", text
  )


def split_sentences(text: str) -> list[str]:
  """Split reflowed prose into candidate sentences.

  Boundaries are located against a copy whose code span interiors have been
  blanked, then sliced out of the original. Inline code routinely contains
  sentence-ending punctuation -- `{transfer: [port2]}` has a colon followed
  by a bracket, which is exactly the boundary shape -- and splitting there
  would cut an obligation in half and strand its tail in a clause that no
  longer cites a keyword.

  Args:
    text: Single-line Markdown text for one block.

  Returns:
    Sentences with list-marker residue stripped. Fragments containing no
    letters are discarded.

  """
  masked = _mask_code_interiors(text)

  raw_parts: list[str] = []
  start = 0
  for match in _SENTENCE_SPLIT_RE.finditer(masked):
    raw_parts.append(text[start : match.start()])
    start = match.end()
  raw_parts.append(text[start:])

  sentences = []
  for raw in raw_parts:
    cleaned = _LEADING_NUMERAL_RE.sub("", raw)
    cleaned = _TRAILING_NUMERAL_RE.sub("", cleaned).strip()
    if cleaned and _HAS_LETTER_RE.search(cleaned):
      sentences.append(cleaned)
  return sentences


class _DocumentWalker:
  """Traverses one document's token stream, accumulating clauses.

  Kept as a class because the walk is stateful in four independent ways: the
  heading breadcrumb, the enclosing block type, the colon-stem stack, and the
  per-document ordering counter.
  """

  def __init__(self, rel_path: str) -> None:
    """Initialize the walker for a single document.

    Args:
      rel_path: Repository-relative path, used in emitted source references.

    """
    self.rel_path = rel_path
    self.clauses: list[Clause] = []
    self._headings: list[tuple[int, str]] = []
    self._context: list[str] = []
    self._stem_stack: list[str | None] = []
    self._pending_stem: str | None = None
    self._order = 0
    self._in_heading = False
    self._heading_level = 0
    # Table matrix state. Specifications express some obligations as a grid
    # whose cells hold only a keyword, with the subject in the row header and
    # the qualifying case in the column header. Tracking both lets such a
    # cell carry its context instead of reducing to a bare "MAY".
    self._in_thead = False
    self._table_headers: list[str] = []
    self._cell_text = ""
    self._cell_index = 0
    self._row_label: str | None = None

  @property
  def _section(self) -> str:
    """Return the current heading breadcrumb."""
    return " > ".join(text for _, text in self._headings)

  @property
  def _block_type(self) -> BlockType:
    """Return the block type of the innermost enclosing construct."""
    for frame in reversed(self._context):
      if frame == "cell":
        return BlockType.TABLE_CELL
      if frame == "item":
        return BlockType.LIST_ITEM
    return BlockType.PARAGRAPH

  def _push_heading(self, level: int, text: str) -> None:
    """Replace the breadcrumb tail with a heading at the given level."""
    while self._headings and self._headings[-1][0] >= level:
      self._headings.pop()
    self._headings.append((level, text))

  def walk(self, tokens: list[Token]) -> list[Clause]:
    """Traverse the token stream and return the clauses found.

    Args:
      tokens: Flat token list from `MarkdownIt.parse`.

    Returns:
      Clause candidates in document order.

    """
    for token in tokens:
      self._handle(token)
    return self.clauses

  def _handle(self, token: Token) -> None:
    """Dispatch a single token."""
    kind = token.type

    if kind in _SKIPPED_BLOCK_TYPES:
      return

    if kind == "heading_open":
      self._in_heading = True
      self._heading_level = int(token.tag[1:]) if token.tag[1:].isdigit() else 1
      return
    if kind == "heading_close":
      self._in_heading = False
      return

    if kind in _LIST_OPEN_TYPES:
      # A stem is only meaningful for the list that directly follows it.
      self._stem_stack.append(self._pending_stem)
      self._pending_stem = None
      return
    if kind in _LIST_CLOSE_TYPES:
      if self._stem_stack:
        self._stem_stack.pop()
      return

    if kind == "list_item_open":
      self._context.append("item")
      return
    if kind == "list_item_close":
      self._pop_context("item")
      return

    if kind == "table_open":
      self._table_headers = []
      return
    if kind == "thead_open":
      self._in_thead = True
      return
    if kind == "thead_close":
      self._in_thead = False
      return
    if kind == "tr_open":
      self._cell_index = 0
      self._row_label = None
      return

    if kind in ("td_open", "th_open"):
      self._context.append("cell")
      self._cell_text = ""
      return
    if kind in ("td_close", "th_close"):
      self._pop_context("cell")
      self._close_cell()
      return

    if kind == "inline":
      self._handle_inline(token)

  def _pop_context(self, expected: str) -> None:
    """Pop the innermost context frame if it matches."""
    if self._context and self._context[-1] == expected:
      self._context.pop()

  def _close_cell(self) -> None:
    """Record a finished table cell and advance the column counter.

    Header cells are accumulated as column labels, including empty ones, so
    that a later cell's index still lines up with the correct header. The
    first cell of a body row is retained as that row's label.
    """
    if self._in_thead:
      self._table_headers.append(self._cell_text)
    elif self._cell_index == 0:
      self._row_label = self._cell_text
    self._cell_index += 1
    self._cell_text = ""

  def _cell_context(self) -> str | None:
    """Return "row | column" context for the cell being processed.

    Returns None for header cells and for the leading label cell of a row,
    neither of which is an obligation in its own right.
    """
    if self._in_thead or self._cell_index == 0:
      return None
    header = (
      self._table_headers[self._cell_index]
      if self._cell_index < len(self._table_headers)
      else ""
    )
    parts = [p for p in (self._row_label, header) if p]
    return " | ".join(parts) if parts else None

  def _handle_inline(self, token: Token) -> None:
    """Emit clauses for an inline token, or record it as a heading or stem."""
    text = _render_inline(token)

    if self._context and self._context[-1] == "cell":
      self._cell_text = text

    if not text:
      return

    if self._in_heading:
      # Headings are structure, not obligations. Strip emphasis so the
      # breadcrumb reads cleanly.
      self._push_heading(self._heading_level, text.replace("**", "").strip())
      return

    block_type = self._block_type
    source_map = token.map or [0, 0]
    line_start = source_map[0] + 1
    line_end = max(source_map[1], source_map[0] + 1)

    if block_type is BlockType.TABLE_CELL:
      # Column headers label the grid; they state no obligation.
      if self._in_thead:
        return
      compound_parent = self._cell_context()
    elif block_type is BlockType.LIST_ITEM and self._stem_stack:
      compound_parent = self._stem_stack[-1]
    else:
      compound_parent = None

    for sentence in split_sentences(text):
      self._order += 1
      self.clauses.append(
        Clause(
          text=sentence,
          source=SourceRef(
            file=self.rel_path,
            line_start=line_start,
            line_end=line_end,
            section=self._section,
            block_type=block_type,
          ),
          document_order=self._order,
          compound_parent=compound_parent,
        )
      )

    # Remember a colon-terminated paragraph in case a list follows it.
    if block_type is not BlockType.TABLE_CELL and text.rstrip().endswith(":"):
      self._pending_stem = text
    else:
      self._pending_stem = None


def _markdown() -> MarkdownIt:
  """Return a CommonMark parser with table support enabled."""
  return MarkdownIt("commonmark").enable("table")


def parse_text(source: str, rel_path: str) -> list[Clause]:
  """Parse Markdown source into clause candidates.

  Args:
    source: Markdown document text.
    rel_path: Repository-relative path recorded on each clause.

  Returns:
    Clause candidates in document order.

  """
  tokens = _markdown().parse(source)
  return _DocumentWalker(rel_path).walk(tokens)


def parse_file(path: Path, repo_root: Path | None = None) -> list[Clause]:
  """Parse a Markdown file into clause candidates.

  Args:
    path: Absolute path to the document.
    repo_root: Root the recorded path is made relative to. Defaults to the
      repository root.

  Returns:
    Clause candidates in document order.

  """
  root = repo_root or config.REPO_ROOT
  rel_path = path.resolve().relative_to(root).as_posix()
  return parse_text(path.read_text(encoding="utf-8"), rel_path)


def iter_spec_files(
  spec_dirs: list[Path] | None = None, repo_root: Path | None = None
) -> Iterator[Path]:
  """Yield in-scope specification documents in a stable order.

  Args:
    spec_dirs: Directories to scan, relative to the repository root.
      Defaults to `config.SPEC_DIRS`.
    repo_root: Repository root. Defaults to `config.REPO_ROOT`.

  Yields:
    Absolute paths to Markdown documents that are not excluded.

  """
  root = repo_root or config.REPO_ROOT
  for spec_dir in spec_dirs or config.SPEC_DIRS:
    base = spec_dir if spec_dir.is_absolute() else root / spec_dir
    for path in sorted(base.rglob("*.md")):
      rel = path.resolve().relative_to(root).as_posix()
      if not config.is_excluded(rel):
        yield path


def parse_all(
  spec_dirs: list[Path] | None = None, repo_root: Path | None = None
) -> list[Clause]:
  """Parse every in-scope document.

  Args:
    spec_dirs: Directories to scan. Defaults to `config.SPEC_DIRS`.
    repo_root: Repository root. Defaults to `config.REPO_ROOT`.

  Returns:
    Clause candidates across all documents, grouped by document in path order.

  """
  clauses: list[Clause] = []
  for path in iter_spec_files(spec_dirs, repo_root):
    clauses.extend(parse_file(path, repo_root))
  return clauses
