#!/usr/bin/env python3
"""Contract conformance tests for check_links.py.

Each test asserts one claim about how a link shape is classified. Tests
are deliberately one-claim-each so a failure points at exactly which rule
broke.

Two layers of testing exist for the link checker:

  - **The built site is the integration test.** Every internal link in
    the rendered documentation is resolved on each CI run, which proves
    real links point at real pages.

  - **This file is the unit test layer.** It proves each classification
    rule is *enforced*: that off-site links are skipped rather than
    resolved against the local build, and that on-site links which
    cannot resolve are reported. Without it, the site corpus only proves
    "the links we happen to write today pass".

check_links.py resolves paths against a real directory tree and reads
configuration from the environment, so tests drive it as a subprocess
against a synthetic site rather than importing it. This exercises the
same entry point CI uses.

Run: python3 scripts/test_check_links.py
Exit: 0 on all pass, 1 on any failure.

No external dependencies.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).parent / "check_links.py"

# -----------------------------------------------------------
# Test harness (minimal, no deps)
# -----------------------------------------------------------

_RESULTS: list[tuple[str, bool, str]] = []


def _check(name: str, condition: bool, detail: str = "") -> None:
  """Record a test result."""
  _RESULTS.append((name, condition, detail))


def _report() -> int:
  """Print results and return exit code."""
  passed = sum(1 for _, ok, _ in _RESULTS if ok)
  failed = [(n, d) for n, ok, d in _RESULTS if not ok]
  for name, ok, detail in _RESULTS:
    status = "PASS" if ok else "FAIL"
    suffix = f" — {detail}" if detail and not ok else ""
    print(f"  {status}  {name}{suffix}")
  print(f"\n{passed} passed, {len(failed)} failed")
  return 0 if not failed else 1


# -----------------------------------------------------------
# Synthetic site
# -----------------------------------------------------------


def _build_site(root: Path, cases: dict[str, str]) -> None:
  """Create a small site: one page per case, plus a shared link target.

  The target directory holds a rendered index.html carrying id="real",
  and a raw page.md that exists on disk. A raw Markdown target has to
  exist for the raw-Markdown guard to be the only thing that can reject
  a link to it.
  """
  (root / "target").mkdir(parents=True, exist_ok=True)
  (root / "target/index.html").write_text(
    "<html><body><h2 id='real'>Real</h2></body></html>", encoding="utf-8"
  )
  (root / "target/page.md").write_text("# page\n", encoding="utf-8")
  (root / "target/page.MD").write_text("# page\n", encoding="utf-8")

  for name, href in cases.items():
    (root / f"{name}.html").write_text(
      f'<html><body><a href="{href}">link</a></body></html>', encoding="utf-8"
    )


def _run(root: Path, cwd: Path, env_extra: dict | None = None) -> str:
  """Run the real checker over `root`, from `cwd`. Return its stdout."""
  env = {"PATH": "/usr/bin:/bin", "SITE_URL": "https://ucp.dev/"}
  if env_extra:
    env.update(env_extra)
  proc = subprocess.run(
    [sys.executable, str(SCRIPT), str(root)],
    cwd=str(cwd),
    capture_output=True,
    text=True,
    env=env,
  )
  return proc.stdout


def _flagged(output: str, case: str) -> bool:
  """Report whether the checker flagged a problem on `case`'s page."""
  return f"{case}.html" in output


# -----------------------------------------------------------
# Tests
# -----------------------------------------------------------

# An off-site link must be skipped. Resolving one against the local build
# reports a spurious "Not Found" and fails the docs job on a link that is
# not ours to fix.
OFF_SITE = {
  "ext_https": "https://example.com/x",
  "ext_https_md": "https://example.com/x.md",
  "ext_mailto": "mailto:a@b.c",
  "ext_tel": "tel:+15550100",
  "ext_protocol_relative": "//example.com/x",
  "ext_protocol_relative_md": "//example.com/x.md",
  "ext_unhandled_scheme": "ftp://example.com/x",
  "ext_ws_scheme": "ws://example.com/socket",
  # A scheme with no host at all. Only a scheme check catches this one; a
  # host check alone lets it through to be resolved as a local path.
  "ext_scheme_without_host": "vscode:extension/ms-python.python",
}

# An on-site link must be resolved, and reported when it cannot be.
ON_SITE_OK = {
  "ok_dir": "target/",
  "ok_dir_query": "target/?v=1",
  "ok_anchor": "target/#real",
  "ok_anchor_encoded": "target/#re%61l",
  "ok_dot_slash": "./target/",
  "ok_site_absolute": "https://ucp.dev/target/",
}

ON_SITE_BAD = {
  "bad_missing": "nope/",
  "bad_anchor": "target/#ghost",
  "bad_raw_md": "target/page.md",
  "bad_raw_md_query": "target/page.md?v=1",
  "bad_raw_md_upper": "target/page.MD",
  # A relative path may contain a colon without carrying a scheme. Treating
  # one as off-site would silently stop resolving real internal links, so
  # this must still be reported as missing.
  "bad_colon_in_relative_path": "target/some:file.html",
}


def test_off_site_links_are_skipped() -> None:
  """Links that carry a host or a scheme we do not resolve are off-site."""
  with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp, "site")
    _build_site(root, OFF_SITE)
    out = _run(root, Path(tmp))
    for case, href in OFF_SITE.items():
      _check(
        f"off_site_skipped[{href}]",
        not _flagged(out, case),
        "reported as a broken internal link",
      )


def test_on_site_links_resolve() -> None:
  """Links to pages that exist must not be reported."""
  with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp, "site")
    _build_site(root, ON_SITE_OK)
    out = _run(root, Path(tmp))
    for case, href in ON_SITE_OK.items():
      _check(
        f"on_site_resolves[{href}]",
        not _flagged(out, case),
        "reported, but the target exists",
      )


def test_on_site_failures_are_reported() -> None:
  """Missing targets, missing anchors and raw Markdown must be reported."""
  with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp, "site")
    _build_site(root, ON_SITE_BAD)
    out = _run(root, Path(tmp))
    for case, href in ON_SITE_BAD.items():
      _check(
        f"on_site_failure_reported[{href}]",
        _flagged(out, case),
        "accepted, but the link is broken",
      )


def test_raw_markdown_names_its_own_reason() -> None:
  """A raw Markdown target is reported as such, not as a missing file.

  The file exists on disk, so a plain existence check would pass it. The
  message has to tell an author to link the rendered page instead.
  """
  with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp, "site")
    _build_site(root, {"md": "target/page.md"})
    out = _run(root, Path(tmp))
    _check(
      "raw_markdown_reason_reported",
      "raw Markdown" in out and "Not Found" not in out,
      f"got {out.strip()[-200:]!r}",
    )


def test_exit_code_signals_failure() -> None:
  """The checker exits non-zero on findings and zero on a clean site."""
  with tempfile.TemporaryDirectory() as tmp:
    clean = Path(tmp, "clean")
    _build_site(clean, {"ok": "target/"})
    broken = Path(tmp, "broken")
    _build_site(broken, {"bad": "nope/"})

    env = {"PATH": "/usr/bin:/bin", "SITE_URL": "https://ucp.dev/"}
    rc_clean = subprocess.run(
      [sys.executable, str(SCRIPT), str(clean)],
      cwd=tmp,
      capture_output=True,
      text=True,
      env=env,
    ).returncode
    rc_broken = subprocess.run(
      [sys.executable, str(SCRIPT), str(broken)],
      cwd=tmp,
      capture_output=True,
      text=True,
      env=env,
    ).returncode

    _check("exit_zero_when_clean", rc_clean == 0, f"got {rc_clean}")
    _check("exit_nonzero_when_broken", rc_broken == 1, f"got {rc_broken}")


def test_linkignore_suppresses_but_not_raw_markdown() -> None:
  """.linkignore suppresses resolution, never the raw-Markdown guard.

  An ignored link may legitimately point outside the current build, but
  it must still target a rendered page rather than source text.
  """
  with tempfile.TemporaryDirectory() as tmp:
    cwd = Path(tmp)
    (cwd / ".linkignore").write_text("^/latest/.*\n", encoding="utf-8")
    root = Path(tmp, "site")
    _build_site(
      root,
      {
        "ignored_missing": "/latest/specification/",
        "ignored_md": "/latest/specification/page.md",
      },
    )
    out = _run(root, cwd)
    _check(
      "linkignore_suppresses_missing_target",
      not _flagged(out, "ignored_missing"),
      "ignored link was still resolved",
    )
    _check(
      "linkignore_does_not_suppress_raw_markdown",
      _flagged(out, "ignored_md"),
      "raw Markdown slipped through an ignore rule",
    )


def test_docs_mode_spec_ignores_documentation_links() -> None:
  """DOCS_MODE=spec drops links into documentation/, which lives on root."""
  cases = {
    "doc_absolute": "/documentation/schema-authoring/",
    "doc_relative": "../documentation/schema-authoring/",
  }
  with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp, "site")
    _build_site(root, cases)

    root_mode = _run(root, Path(tmp), {"DOCS_MODE": "root"})
    spec_mode = _run(root, Path(tmp), {"DOCS_MODE": "spec"})

    for case, href in cases.items():
      _check(
        f"docs_mode_root_reports[{href}]",
        _flagged(root_mode, case),
        "root mode should resolve documentation links",
      )
      _check(
        f"docs_mode_spec_ignores[{href}]",
        not _flagged(spec_mode, case),
        "spec mode should ignore documentation links",
      )


# -----------------------------------------------------------
# Main
# -----------------------------------------------------------


def main() -> int:
  """Run all contract tests and report. Exit 0 on pass, 1 on failure."""
  print("Running check_links contract tests...\n")
  test_off_site_links_are_skipped()
  test_on_site_links_resolve()
  test_on_site_failures_are_reported()
  test_raw_markdown_names_its_own_reason()
  test_exit_code_signals_failure()
  test_linkignore_suppresses_but_not_raw_markdown()
  test_docs_mode_spec_ignores_documentation_links()
  return _report()


if __name__ == "__main__":
  sys.exit(main())
