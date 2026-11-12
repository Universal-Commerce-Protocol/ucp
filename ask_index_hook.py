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

"""MkDocs hook that emits ``ask-index.json`` for the "Ask AI" assistant.

Every build (root site, ``draft``, ``latest`` and dated releases) writes its
own index next to its pages, so the assistant backend can load
``https://ucp.dev/ask-index.json`` plus ``https://ucp.dev/latest/ask-index.json``
and cover both the overview docs and the current specification without any
extra deploy step. See ``ask/README.md``.
"""

from __future__ import annotations

import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from ask_index import Chunk, chunk_html, write_index  # noqa: E402

log = logging.getLogger("mkdocs.hooks.ask_index")

_chunks: list[Chunk] = []
_pages: list[dict[str, str]] = []


def on_pre_build(config):
  """Reset state so ``mkdocs serve`` rebuilds do not accumulate chunks."""
  _chunks.clear()
  _pages.clear()


def on_page_content(html, page, config, files):
  """Chunk the rendered page body (after macros and snippets ran)."""
  if page.meta.get("ask_index") is False:
    return html
  title = page.title or page.file.name
  page_chunks = chunk_html(html, page.url, title)
  if page_chunks:
    _chunks.extend(page_chunks)
    summary = page.meta.get("description") or page_chunks[0].text[:200]
    _pages.append({"url": page.url, "title": title, "summary": summary})
  return html


def on_post_build(config):
  """Write the index to the site directory."""
  base_url = config.get("site_url") or "/"
  out = write_index(_chunks, _pages, config["site_dir"], base_url)
  log.info(
    f"Ask index: {len(_chunks)} chunks from {len(_pages)} pages -> {out}"
  )
