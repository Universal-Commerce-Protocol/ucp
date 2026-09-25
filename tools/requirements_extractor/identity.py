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

"""Stage 4: giving each requirement a stable, content-addressed identity.

An identifier is only useful if it survives edits that do not change the
requirement and changes when one does. Deriving it from position -- a file
and a line -- fails the first test, because inserting a paragraph renumbers
everything below it. So the identifier is derived from content.

What goes into the digest
  Text alone is not enough. The obligation matrix in the checkout index
  reduces eight cells to the single words "must" or "may", and on text alone
  they collide four ways. Their meaning lives in the row and column that
  head them, which the parser recorded as the compound parent, so the digest
  covers that too. Capability is included so the same sentence appearing
  under two capabilities is two requirements, which it is.

  Every component is published in the catalog record -- `capability`,
  `compound_parent` and `normalized` -- so an identifier can be recomputed
  and checked without access to the spec or to this code.

What stays out of the digest
  The file, the line and the section heading. All three are positional: a
  file can move, a heading can be reworded, and neither event changes what
  is required of whom. Including them would trade churn for a property the
  digest does not need, because context from the compound parent already
  separates every clause in this corpus but two.

Genuine duplicates
  Those two are the same sentence stated in both the REST and the MCP
  binding. They are distinct requirements with identical content and
  context, so content-addressing cannot separate them and an ordinal is
  appended. They are reported as well, because the same normative sentence
  maintained in two documents is a spec-authoring hazard.
"""

from __future__ import annotations

import dataclasses
import hashlib
import re

from tools.requirements_extractor import config
from tools.requirements_extractor.models import (
  Clause,
  ExtractionReport,
  Requirement,
)

# Separates the digest components. A control character cannot occur in the
# prose it joins, so no combination of contents can be made to collide by
# shifting a boundary.
DIGEST_SEPARATOR = "\x1f"

# `[label](target)` -> `label`. Retargeting a link, or the tree being
# rearranged beneath it, must not change what the requirement says.
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")

# Bold markers. The corpus contains no italics, and underscores are left
# alone because they occur inside field names such as `continue_url`.
_BOLD_RE = re.compile(r"\*\*")

# Dashes an author may swap for one another without changing meaning.
_DASH_RE = re.compile(r"[\u2012\u2013\u2014\u2015]")

_WHITESPACE_RE = re.compile(r"\s+")

# Punctuation carrying no meaning at the end of a clause.
_TRAILING_PUNCTUATION = ".,;: "


def normalize(text: str) -> str:
  """Reduce clause text to the canonical form used for hashing.

  Each step erases a difference that authors introduce without changing the
  obligation: retargeting a link, adding emphasis, fencing an identifier in
  backticks, swapping a hyphen for an em dash, reflowing a paragraph, or
  changing capitalization.

  Args:
    text: Clause text as it appears in the spec.

  Returns:
    The canonical form: lower case, single-spaced, free of Markdown markup
    and of trailing punctuation.

  """
  out = _LINK_RE.sub(r"\1", text)
  out = _BOLD_RE.sub("", out)
  out = out.replace("`", "")
  out = _DASH_RE.sub("-", out)
  out = _WHITESPACE_RE.sub(" ", out)
  return out.strip().strip(_TRAILING_PUNCTUATION).strip().lower()


def digest_input(
  capability: str | None, compound_parent: str | None, normalized: str
) -> str:
  """Assemble the exact string the identifier digests.

  Kept separate from hashing so a verifier can reproduce the hash input from
  the published catalog fields alone.

  Args:
    capability: Reverse-DNS capability identifier.
    compound_parent: Stem or matrix context, if the clause has one.
    normalized: Canonical clause text from `normalize`.

  Returns:
    The exact string that is hashed.

  """
  return DIGEST_SEPARATOR.join(
    (
      capability or "",
      normalize(compound_parent) if compound_parent else "",
      normalized,
    )
  )


def requirement_digest(
  capability: str | None, compound_parent: str | None, normalized: str
) -> str:
  """Return the content digest for a requirement.

  This is the stable half of a requirement's identity. It depends only on
  what the clause says, never on where it sits, so reformatting the document
  or moving a section leaves it untouched. The readable identifier carries
  location; this carries content.

  Args:
    capability: Reverse-DNS capability identifier.
    compound_parent: Stem or matrix context, if the clause has one.
    normalized: Canonical clause text from `normalize`.

  Returns:
    The leading `config.ID_DIGEST_LENGTH` hex characters of the SHA-256 of
    `digest_input`.

  """
  hash_input = digest_input(capability, compound_parent, normalized)
  digest = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
  return digest[: config.ID_DIGEST_LENGTH]


def _order_key(clause: Clause) -> tuple[str, int, int]:
  """Sort key deciding which of two identical requirements is first.

  Source order, so that the ordinal appended to a duplicate is a property of
  the documents rather than of the order the parser happened to visit them.
  """
  return (
    clause.source.file,
    clause.source.line_start,
    clause.document_order,
  )


def _record(clause: Clause, **extra: object) -> dict[str, object]:
  """Build a report entry locating a clause in the source."""
  entry: dict[str, object] = {
    "file": clause.source.file,
    "line": clause.source.line_start,
    "section": clause.source.section,
    "text": clause.text,
  }
  entry.update(extra)
  return entry


def readable_id(clause: Clause, ordinal: int) -> str:
  """Return the readable identifier for a clause at a given ordinal.

  Args:
    clause: The clause being identified.
    ordinal: 1-based position within its capability/document/section group.

  Returns:
    An identifier such as ``REQ-CHECKOUT-WARNING-PRESENTATION-03``.

  """
  capability = clause.capability or ""
  parts = [
    config.READABLE_ID_PREFIX,
    config.CAPABILITY_SHORT_NAME.get(
      capability, config.capability_slug(capability)
    ),
  ]
  document = config.document_token(clause.source.file)
  if document:
    parts.append(document)
  parts.append(config.section_token(clause.source.section))
  parts.append(f"{ordinal:0{config.ORDINAL_WIDTH}d}")
  return "-".join(parts)


def _group_key(clause: Clause) -> str:
  """Return the identifier prefix a clause's ordinal is counted within."""
  capability = clause.capability or ""
  parts = [
    config.READABLE_ID_PREFIX,
    config.CAPABILITY_SHORT_NAME.get(
      capability, config.capability_slug(capability)
    ),
  ]
  document = config.document_token(clause.source.file)
  if document:
    parts.append(document)
  parts.append(config.section_token(clause.source.section))
  return "-".join(parts)


def assign_identities(
  clauses: list[Clause], report: ExtractionReport | None = None
) -> tuple[list[Requirement], ExtractionReport]:
  """Turn annotated clauses into identified requirements.

  Each requirement receives two identifiers. `id` is readable and counts an
  ordinal within its section, allocated in source order so the catalog reads
  in document sequence. `content_digest` is derived from the clause's content
  alone and moves only when the obligation's wording does.

  Clauses whose content and context are identical share a digest; that is
  reported, but they still receive distinct identifiers, because the
  identifier is positional and two copies occupy two positions.

  Args:
    clauses: Clauses that have been through classification and metadata.
    report: Existing diagnostics collector, or None to create one.

  Returns:
    The requirements, in the order given, and the diagnostics collected.

  """
  collected = report or ExtractionReport()

  normalized_by_clause = [normalize(clause.text) for clause in clauses]
  digests = [
    requirement_digest(clause.capability, clause.compound_parent, normalized)
    for clause, normalized in zip(clauses, normalized_by_clause, strict=True)
  ]

  # Ordinals run in source order within each group, so an identifier's number
  # reflects where the requirement sits in the document rather than the order
  # the parser happened to visit blocks.
  order = sorted(range(len(clauses)), key=lambda i: _order_key(clauses[i]))
  counters: dict[str, int] = {}
  ids: list[str] = [""] * len(clauses)
  for index in order:
    key = _group_key(clauses[index])
    counters[key] = counters.get(key, 0) + 1
    ids[index] = readable_id(clauses[index], counters[key])

  grouped: dict[str, list[int]] = {}
  for index, digest in enumerate(digests):
    grouped.setdefault(digest, []).append(index)

  for digest, indices in grouped.items():
    if len(indices) == 1:
      continue
    ordered = sorted(indices, key=lambda i: _order_key(clauses[i]))
    collected.duplicate_requirements.append(
      _record(
        clauses[ordered[0]],
        content_digest=digest,
        copies=len(indices),
        ids=[ids[i] for i in ordered],
        locations=[
          f"{clauses[i].source.file}:{clauses[i].source.line_start}"
          for i in ordered
        ],
      )
    )

  # A shallow copy of the fields: `dataclasses.asdict` would recurse and
  # replace the nested SourceRef with a plain dict.
  requirements = [
    Requirement(
      **(
        {
          field.name: getattr(clause, field.name)
          for field in dataclasses.fields(clause)
        }
        | {
          "normalized": normalized,
          "id": identifier,
          "content_digest": digest,
        }
      )
    )
    for clause, normalized, identifier, digest in zip(
      clauses, normalized_by_clause, ids, digests, strict=True
    )
  ]
  return requirements, collected
