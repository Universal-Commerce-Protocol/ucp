"""Unit tests for check_links.py."""

import sys
import unittest
from pathlib import Path

# Import the module under test
sys.path.insert(0, str(Path(__file__).parent))
from check_links import LinkParser


class TestLinkParser(unittest.TestCase):
  """Test cases for the LinkParser class."""

  def test_extract_href(self):
    """Test extraction of standard href attributes from anchor tags."""
    parser = LinkParser()
    parser.feed(
      '<a href="/test/path">Test</a><a href="https://ucp.dev/external">Ext</a>'
    )
    self.assertIn("/test/path", parser.links)
    self.assertIn("https://ucp.dev/external", parser.links)

  def test_extract_ids_and_names(self):
    """Test extraction of id and name attributes."""
    parser = LinkParser()
    parser.feed('<h1 id="header1">H1</h1><a name="old-anchor"></a>')
    self.assertIn("header1", parser.ids)
    self.assertIn("old-anchor", parser.ids)

  def test_extract_bare_urls_from_text(self):
    """Test extraction of bare URLs directly from text."""
    parser = LinkParser()
    parser.feed(
      "Here is a bare URL: https://ucp.dev/specification/overview "
      "and some text."
    )
    self.assertIn("https://ucp.dev/specification/overview", parser.links)

  def test_ignore_links_comments(self):
    """Test that links inside ignore comments are correctly skipped."""
    parser = LinkParser()
    html = """
        <a href="/keep1">Keep 1</a>
        <!-- ignore-link-begin -->
        <a href="/ignore1">Ignore 1</a>
        https://ucp.dev/ignore2
        <!-- ignore-link-end -->
        <a href="/keep2">Keep 2</a>
        """
    parser.feed(html)
    self.assertIn("/keep1", parser.links)
    self.assertIn("/keep2", parser.links)
    self.assertNotIn("/ignore1", parser.links)
    self.assertNotIn("https://ucp.dev/ignore2", parser.links)

  def test_ignore_ellipsis_and_wildcards(self):
    """Test that wildcard or ellipsis paths are ignored."""
    parser = LinkParser()
    parser.feed('<a href="/path/...">Dots</a><a href="/path/*">Star</a>')
    self.assertNotIn("/path/...", parser.links)
    self.assertNotIn("/path/*", parser.links)

  def test_ignore_non_anchor_tags(self):
    """Test that href is only extracted from <a> tags, but IDs from any tag."""
    parser = LinkParser()
    parser.feed('<link href="/ignore-this-link"><div id="content-div"></div>')
    self.assertNotIn("/ignore-this-link", parser.links)
    self.assertIn("content-div", parser.ids)

  def test_multiple_bare_urls_with_quotes(self):
    """Test extraction of bare URLs surrounded by quotes or brackets."""
    parser = LinkParser()
    parser.feed('See "https://ucp.dev/a" or <https://ucp.dev/b>.')
    self.assertIn("https://ucp.dev/a", parser.links)
    self.assertIn("https://ucp.dev/b", parser.links)

  def test_bare_url_in_anchor_text(self):
    """Test extraction of bare URLs from within an anchor tag's text."""
    parser = LinkParser()
    parser.feed('<a href="/some-link">See this spec: https://ucp.dev/spec</a>')
    self.assertIn("/some-link", parser.links)
    self.assertIn("https://ucp.dev/spec", parser.links)


if __name__ == "__main__":
  unittest.main()
