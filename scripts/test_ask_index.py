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

"""Unit tests for scripts/ask_index.py.

Run with: uv run python scripts/test_ask_index.py
"""

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from ask_index import MAX_CHUNK_WORDS, chunk_html, write_index  # noqa: E402

PAGE = """
<h1 id="checkout-capability">Checkout Capability<a class="headerlink"
 href="#checkout-capability">¶</a></h1>
<ul><li><strong>Capability Name:</strong>
<code>dev.ucp.shopping.checkout</code></li></ul>
<h2 id="overview">Overview<a class="headerlink" href="#overview">¶</a></h2>
<p>Allows platforms to facilitate checkout sessions. The checkout has to be
finalized manually by the user through a trusted UI unless the AP2 Mandates
extension is supported. The business remains the Merchant of Record and does
not need to become PCI DSS compliant to accept card payments through this
capability. This paragraph is padded so the section is long enough to stand
on its own as a retrieval chunk rather than being merged into the previous
section of the page.</p>
<script>window.x = 1;</script>
<h3 id="payments">Payments<a class="headerlink" href="#payments">¶</a></h3>
<table><thead><tr><th>Field</th><th>Type</th></tr></thead>
<tbody><tr><td><code>id</code></td><td>string</td></tr></tbody>
</table>
<pre><code>{"status": "ready_for_complete"}</code></pre>
"""


class ChunkHtmlTest(unittest.TestCase):
  """Behavioral checks for the HTML chunker."""

  def test_sections_carry_anchors_and_skip_noise(self):
    """Headings become anchored URLs; scripts and permalinks are dropped."""
    chunks = chunk_html(PAGE, "shopping/checkout/", "Checkout Capability")
    urls = [c.url for c in chunks]
    self.assertIn("shopping/checkout/#overview", urls)
    joined = "\n".join(c.text for c in chunks)
    self.assertNotIn("¶", joined)
    self.assertNotIn("window.x", joined)
    self.assertIn("dev.ucp.shopping.checkout", joined)
    # Table rows are flattened to pipe-separated text.
    self.assertIn("id | string |", joined)
    # Code blocks keep their content.
    self.assertIn('"status": "ready_for_complete"', joined)

  def test_small_trailing_sections_merge_into_predecessor(self):
    """Short sections fold into the previous chunk."""
    chunks = chunk_html(PAGE, "shopping/checkout/", "Checkout Capability")
    # "Payments" is short, so it should be folded into the Overview chunk.
    headings = [c.heading for c in chunks]
    self.assertNotIn("Payments", headings)
    overview = next(c for c in chunks if c.url.endswith("#overview"))
    self.assertIn("Payments", overview.text)

  def test_long_sections_are_split_at_paragraphs(self):
    """Oversized sections split at paragraph boundaries."""
    para = "<p>" + " ".join(["word"] * 150) + "</p>"
    html = '<h2 id="big">Big</h2>' + para * 5
    chunks = chunk_html(html, "big/", "Big")
    self.assertGreater(len(chunks), 1)
    for chunk in chunks:
      self.assertLessEqual(chunk.words, MAX_CHUNK_WORDS)
    self.assertEqual(chunks[1].heading, "Big (part 2)")

  def test_table_rows_stay_on_one_line(self):
    """Whitespace between cells does not split a row across lines."""
    html = (
      '<h2 id="f">Fields</h2><table><tbody>\n<tr>\n<td>line_items</td>\n'
      "<td>Array</td>\n<td>Required</td>\n</tr>\n</tbody></table>"
    )
    chunks = chunk_html(html, "x/", "X")
    self.assertIn("line_items | Array | Required |", chunks[0].text)

  def test_ids_are_stable(self):
    """Chunk ids are deterministic for identical input."""
    a = chunk_html(PAGE, "shopping/checkout/", "Checkout Capability")
    b = chunk_html(PAGE, "shopping/checkout/", "Checkout Capability")
    self.assertEqual([c.id for c in a], [c.id for c in b])

  def test_write_index_round_trips_with_version(self):
    """The index file carries a version hash and all chunks."""
    chunks = chunk_html(PAGE, "shopping/checkout/", "Checkout Capability")
    with tempfile.TemporaryDirectory() as tmp:
      out = write_index(
        chunks,
        [{"url": "shopping/checkout/", "title": "Checkout", "summary": "x"}],
        tmp,
        "https://ucp.dev/latest/",
      )
      data = json.loads(out.read_text(encoding="utf-8"))
    self.assertEqual(data["format"], 1)
    self.assertEqual(data["base_url"], "https://ucp.dev/latest/")
    self.assertEqual(len(data["chunks"]), len(chunks))
    self.assertEqual(len(data["version"]), 16)


if __name__ == "__main__":
  unittest.main()
