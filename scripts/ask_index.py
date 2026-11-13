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

"""Build the retrieval index consumed by the "Ask AI" assistant.

The MkDocs hook in ``ask_index_hook.py`` feeds every rendered page's HTML
into :func:`chunk_html`. Each page is split into heading-delimited sections
("chunks") that carry the page URL plus the heading anchor, so the assistant
can cite the exact section it drew an answer from. The result is written to
``<site_dir>/ask-index.json`` by :func:`write_index`.

Chunks are sized for retrieval: large sections are split at paragraph
boundaries and tiny trailing sections are merged into their predecessor, so
the assistant can be given the top few hits without blowing the token budget.
Everything here is stdlib-only so it runs anywhere the docs build runs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from typing import Any

# Target chunk size in words. ~400 words is roughly 550 tokens, which keeps the
# top-k retrieval context small while still giving whole sections.
MAX_CHUNK_WORDS = 400
# Sections shorter than this are merged into the previous chunk of the same
# page so a bare heading never becomes its own hit.
MIN_CHUNK_WORDS = 40
# Headings that create chunk boundaries.
SECTION_TAGS = {"h1", "h2", "h3"}
# Content that should not be indexed.
SKIP_TAGS = {"script", "style", "svg", "nav", "button"}
# Elements that terminate a line of text.
BLOCK_TAGS = {
  "p",
  "div",
  "li",
  "tr",
  "pre",
  "blockquote",
  "section",
  "table",
  "ul",
  "ol",
  "dd",
  "dt",
  "details",
  "summary",
  "br",
  "hr",
  "h4",
  "h5",
  "h6",
} | SECTION_TAGS


@dataclass
class Chunk:
  """One retrievable unit of documentation."""

  id: str
  url: str
  page: str
  heading: str
  text: str
  words: int = 0


@dataclass
class _Section:
  heading: str
  anchor: str
  lines: list[str] = field(default_factory=list)


class _TextExtractor(HTMLParser):
  """Convert rendered page HTML into heading-delimited plain text."""

  def __init__(self) -> None:
    super().__init__(convert_charrefs=True)
    self.sections: list[_Section] = [_Section(heading="", anchor="")]
    self._skip_depth = 0
    self._heading: tuple[str, str] | None = None  # (tag, id)
    self._heading_text: list[str] = []
    self._cell_text: list[str] = []
    self._in_cell = False
    self._in_row = False
    self._in_pre = False
    self._buf: list[str] = []

  # -- helpers --------------------------------------------------------------
  def _flush(self) -> None:
    text = "".join(self._buf)
    self._buf = []
    if self._in_pre:
      stripped = text.strip("\n")
    else:
      stripped = re.sub(r"[ \t\r\f\v]+", " ", text).strip()
    if stripped:
      self.sections[-1].lines.append(stripped)

  # -- parser callbacks -----------------------------------------------------
  def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
    attr = dict(attrs)
    if self._skip_depth or tag in SKIP_TAGS:
      self._skip_depth += 1
      return
    # The ¶ permalink anchors Material adds to headings.
    if tag == "a" and "headerlink" in (attr.get("class") or ""):
      self._skip_depth += 1
      return
    if tag in SECTION_TAGS:
      self._flush()
      self._heading = (tag, attr.get("id") or "")
      self._heading_text = []
      return
    if tag == "tr":
      self._flush()
      self._in_row = True
      return
    if tag in ("td", "th"):
      self._in_cell = True
      self._cell_text = []
      return
    if tag == "pre":
      self._flush()
      self._in_pre = True
      return
    if tag in BLOCK_TAGS:
      self._flush()

  def handle_endtag(self, tag: str):
    if self._skip_depth:
      self._skip_depth -= 1
      return
    if tag in SECTION_TAGS and self._heading:
      heading = re.sub(r"\s+", " ", "".join(self._heading_text)).strip()
      self.sections.append(_Section(heading=heading, anchor=self._heading[1]))
      self._heading = None
      return
    if tag in ("td", "th"):
      cell = re.sub(r"\s+", " ", "".join(self._cell_text)).strip()
      self._in_cell = False
      if cell:
        self._buf.append(cell + " | ")
      return
    if tag == "tr":
      self._flush()
      self._in_row = False
      return
    if tag == "pre":
      self._flush()
      self._in_pre = False
      return
    if tag in BLOCK_TAGS:
      self._flush()

  def handle_data(self, data: str):
    if self._skip_depth:
      return
    if self._heading is not None:
      self._heading_text.append(data)
    elif self._in_cell:
      self._cell_text.append(data)
    elif self._in_row and not data.strip():
      # Whitespace between cells would break a row over several lines.
      return
    else:
      self._buf.append(data)

  def close(self) -> None:  # noqa: D102 - inherited docstring
    super().close()
    self._flush()


def page_h1(html: str) -> str | None:
  """Return the text of the first ``<h1>`` in ``html``, if any."""
  parser = _TextExtractor()
  parser.feed(html)
  parser.close()
  for section in parser.sections[1:]:
    if section.heading:
      return section.heading
  return None


def _word_count(text: str) -> int:
  return len(text.split())


def _split_long(text: str, limit: int) -> list[str]:
  """Split ``text`` at paragraph boundaries into pieces of <= ``limit`` words.

  Paragraphs longer than ``limit`` are kept whole.
  """
  if _word_count(text) <= limit:
    return [text]
  pieces: list[str] = []
  current: list[str] = []
  current_words = 0
  for para in text.split("\n"):
    words = _word_count(para)
    if current and current_words + words > limit:
      pieces.append("\n".join(current))
      current, current_words = [], 0
    current.append(para)
    current_words += words
  if current:
    pieces.append("\n".join(current))
  return pieces


def chunk_html(html: str, url: str, page_title: str) -> list[Chunk]:
  """Split one rendered page into retrievable chunks.

  Args:
    html: The page body HTML as produced by MkDocs (before theming).
    url: The page URL relative to the site root (e.g. ``shopping/cart/``).
    page_title: The page title used as the chunk's parent label.

  Returns:
    Chunks in document order. Empty pages produce an empty list.

  """
  parser = _TextExtractor()
  parser.feed(html)
  parser.close()

  chunks: list[Chunk] = []
  for section in parser.sections:
    text = "\n".join(section.lines).strip()
    if not text and not section.heading:
      continue
    heading = section.heading or page_title
    anchor = f"#{section.anchor}" if section.anchor else ""
    # Merge small sections into the previous chunk of the same page so a
    # heading with one sentence under it does not become a standalone hit.
    if (
      chunks
      and _word_count(text) < MIN_CHUNK_WORDS
      and chunks[-1].words + _word_count(text) <= MAX_CHUNK_WORDS
    ):
      prev = chunks[-1]
      prev.text = f"{prev.text}\n\n{heading}\n{text}".strip()
      prev.words = _word_count(prev.text)
      continue
    for i, piece in enumerate(_split_long(text, MAX_CHUNK_WORDS)):
      suffix = f" (part {i + 1})" if i else ""
      chunks.append(
        Chunk(
          id="",
          url=f"{url}{anchor}",
          page=page_title,
          heading=heading + suffix,
          text=piece,
          words=_word_count(piece),
        )
      )

  for chunk in chunks:
    digest = hashlib.sha1(  # noqa: S324 - identifier, not security
      f"{chunk.url}\n{chunk.heading}\n{chunk.text}".encode()
    ).hexdigest()
    chunk.id = digest[:12]
  return chunks


def write_index(
  chunks: list[Chunk],
  pages: list[dict[str, str]],
  site_dir: str | Path,
  base_url: str,
  filename: str = "ask-index.json",
) -> Path:
  """Write the index file and return its path.

  The ``version`` field is a content hash so the serving layer can detect a
  redeploy and drop any cached answers that were produced from older text.
  """
  payload: dict[str, Any] = {
    "format": 1,
    "base_url": base_url,
    "pages": pages,
    "chunks": [asdict(c) for c in chunks],
  }
  body = json.dumps(payload, ensure_ascii=False, sort_keys=True)
  payload["version"] = hashlib.sha256(body.encode()).hexdigest()[:16]
  out = Path(site_dir) / filename
  out.parent.mkdir(parents=True, exist_ok=True)
  out.write_text(
    json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    encoding="utf-8",
  )
  return out
