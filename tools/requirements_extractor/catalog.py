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

"""Stage 5: running the pipeline and writing the catalog.

Two documents come out of a run. The catalog is the requirements themselves.
The report is everything the extractor decided not to put in the catalog,
and why -- it is the half that makes the other half trustworthy, because a
clause citing an RFC 2119 keyword either reaches the catalog or appears in
the report with a reason, never neither.

Both are written deterministically. The same input produces byte-identical
output, which is what lets a consumer regenerate and diff to prove the
catalog matches the spec it claims to describe.

  No timestamp is recorded. A generation time would change every run and
  destroy that property, so provenance is carried by the spec version and
  the extractor version instead. This is deliberate and should not be
  "fixed" by adding a generated_at field.

Requirements are emitted in source order. The catalog's primary review path
is reading it beside the specification, and an identifier is stable under
insertion regardless of where it sits in the file, so nothing is gained by
ordering on the digest.
"""

from __future__ import annotations

import collections
import datetime
import json
from pathlib import Path
import subprocess

from tools.requirements_extractor import (
  classifier,
  config,
  identity,
  metadata,
  parser,
)
from tools.requirements_extractor.models import ExtractionReport, Requirement


def build() -> tuple[list[Requirement], ExtractionReport]:
  """Run every stage and return the requirements and the diagnostics.

  Returns:
    Requirements in source order, and the report accumulated across all
    stages.

  """
  clauses = parser.parse_all()
  obligations, report = classifier.classify_all(clauses)
  annotated, report = metadata.annotate_all(obligations, report)
  requirements, report = identity.assign_identities(annotated, report)

  requirements.sort(
    key=lambda r: (r.source.file, r.source.line_start, r.document_order)
  )
  return requirements, report


def _counter(values: list[str]) -> dict[str, int]:
  """Count values into a dict with deterministic key order."""
  counts = collections.Counter(values)
  return {key: counts[key] for key in sorted(counts)}


def summarize(
  requirements: list[Requirement], report: ExtractionReport
) -> dict[str, object]:
  """Describe a run in numbers.

  The reconciliation totals are included so the catalog carries its own
  evidence: every clause that cited a keyword is accounted for, either as a
  requirement or as a diagnostic.

  Args:
    requirements: The extracted requirements.
    report: Diagnostics from the run.

  Returns:
    A summary suitable for the head of either document.

  """
  diagnostics = {
    name: len(entries) for name, entries in sorted(report.as_dict().items())
  }
  by_level = _counter(
    [str(r.level) for r in requirements if r.level is not None]
  )
  return {
    "total": len(requirements),
    "must_count": by_level.get("MUST", 0),
    "must_not_count": by_level.get("MUST NOT", 0),
    "should_count": by_level.get("SHOULD", 0),
    "should_not_count": by_level.get("SHOULD NOT", 0),
    "may_count": by_level.get("MAY", 0),
    "by_level": by_level,
    "by_actor": _counter(
      [config.published_actor(r.actor) or "UNRESOLVED" for r in requirements]
    ),
    "by_file": _counter([r.source.file for r in requirements]),
    "with_condition": sum(1 for r in requirements if r.condition),
    "with_referenced_fields": sum(
      1 for r in requirements if r.referenced_fields
    ),
    "from_compound_split": sum(
      1 for r in requirements if r.split_from_compound
    ),
    "diagnostics": diagnostics,
  }


def _commit_sha() -> str | None:
  """Return the current commit, or None outside a git checkout.

  Provenance that survives the file being copied out of the repository. It
  is stable for a given tree, so unlike a timestamp it does not by itself
  make two runs differ.
  """
  try:
    completed = subprocess.run(
      ["git", "rev-parse", "HEAD"],
      cwd=config.REPO_ROOT,
      capture_output=True,
      text=True,
      check=False,
      timeout=10,
    )
  except (OSError, subprocess.SubprocessError):
    return None
  sha = completed.stdout.strip()
  return sha or None


def _envelope(spec_version: str) -> dict[str, object]:
  """Return the provenance header shared by both documents.

  `$schema` is deliberately not here. Both documents share provenance, but
  only the catalog has a published schema; claiming it on the report would
  assert a shape the report does not have.

  `generated_at` is the one field here that changes between runs of the same
  input. It is published because a consumer reading the catalog outside the
  repository has no other way to date it, but it is excluded from the
  comparison `--check` performs -- otherwise every run would report the
  committed catalog as stale and the CI gate would be worthless.
  """
  return {
    "schema_version": config.CATALOG_SCHEMA_VERSION,
    "extractor_version": config.EXTRACTOR_VERSION,
    "spec_version": spec_version,
    "generated_at": datetime.datetime.now(datetime.UTC).strftime(
      "%Y-%m-%dT%H:%M:%SZ"
    ),
    "commit_sha": _commit_sha(),
    # POSIX strings rather than Path objects, so the document is
    # serializable and identical regardless of the host platform.
    "source_spec": sorted(
      directory.as_posix() for directory in config.SPEC_DIRS
    ),
  }


def catalog_document(
  requirements: list[Requirement], report: ExtractionReport
) -> dict[str, object]:
  """Assemble the catalog document.

  Args:
    requirements: The extracted requirements, in source order.
    report: Diagnostics from the run, used for the summary only.

  Returns:
    A JSON-serializable catalog.

  """
  spec_version = config.spec_version()
  return {
    "$schema": config.CATALOG_SCHEMA_URL,
    **_envelope(spec_version),
    "summary": summarize(requirements, report),
    "requirements": [r.as_dict(spec_version) for r in requirements],
  }


def report_document(
  requirements: list[Requirement], report: ExtractionReport
) -> dict[str, object]:
  """Assemble the diagnostics document.

  Args:
    requirements: The extracted requirements, used for the summary.
    report: Diagnostics from the run.

  Returns:
    A JSON-serializable report.

  """
  return {
    **_envelope(config.spec_version()),
    "summary": summarize(requirements, report),
    "diagnostics": dict(sorted(report.as_dict().items())),
  }


def serialize(document: dict[str, object]) -> str:
  """Render a document as deterministic JSON.

  Args:
    document: The catalog or report.

  Returns:
    JSON text, newline-terminated. Key order is the order the document was
    assembled in, which is fixed by the code rather than by a dict's
    insertion history, so runs agree byte for byte.

  """
  return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def write(path: Path, document: dict[str, object]) -> None:
  """Write a document to disk, creating parent directories.

  Args:
    path: Destination file.
    document: The catalog or report.

  """
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(serialize(document), encoding="utf-8")


def unresolved_capabilities(requirements: list[Requirement]) -> list[str]:
  """Return the files whose capability could not be resolved.

  Args:
    requirements: The extracted requirements.

  Returns:
    Sorted, deduplicated file paths. Empty when every document resolved.

  """
  return sorted({r.source.file for r in requirements if not r.capability})
