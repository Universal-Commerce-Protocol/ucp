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

"""Shared data structures for the requirements extractor.

These types are the contract between pipeline stages. The parser emits
`Clause` candidates, the classifier and metadata stages populate them in place,
and the identity stage promotes each survivor to a `Requirement` by assigning
an `id`.

Nothing here performs I/O or parsing; keeping the models inert lets every other
module import them without risking a circular dependency.
"""

from __future__ import annotations

import dataclasses
import enum


class Level(enum.Enum):
  """RFC 2119 obligation levels.

  These are the only values that appear as a requirement's `level` in the
  emitted catalog. `SHALL`/`SHALL_NOT` are retained because the corpus contains
  one instance of each, even though `MUST` is the house style.
  """

  MUST = "MUST"
  MUST_NOT = "MUST NOT"
  SHALL = "SHALL"
  SHALL_NOT = "SHALL NOT"
  SHOULD = "SHOULD"
  SHOULD_NOT = "SHOULD NOT"
  MAY = "MAY"

  def __str__(self) -> str:
    """Return the spec-facing spelling, e.g. ``MUST NOT``."""
    return self.value


class Annotation(enum.Enum):
  """RFC 2119 keywords used in this corpus mainly as schema annotations.

  In UCP prose these overwhelmingly mark schema field optionality, as in
  ``payload: - checkout (object, REQUIRED)``, rather than stating an obligation
  on a party. They are tracked separately and excluded from the catalog unless
  `--include-annotations` is passed, because treating them as obligations was
  measured to be the largest single source of spurious requirements.
  """

  REQUIRED = "REQUIRED"
  OPTIONAL = "OPTIONAL"
  RECOMMENDED = "RECOMMENDED"

  def __str__(self) -> str:
    """Return the spec-facing spelling, e.g. ``REQUIRED``."""
    return self.value


class BlockType(enum.Enum):
  """The kind of Markdown construct a clause was extracted from.

  Recorded for traceability and to let downstream consumers weigh, for example,
  a table cell differently from a body paragraph.
  """

  PARAGRAPH = "paragraph"
  LIST_ITEM = "list_item"
  TABLE_CELL = "table_cell"

  def __str__(self) -> str:
    """Return the serialized spelling, e.g. ``list_item``."""
    return self.value


@dataclasses.dataclass(frozen=True)
class SourceRef:
  """Where a clause came from.

  This is provenance only: none of these fields feed the requirement's
  identifier. Section paths and file paths are both volatile (headings get
  reorganized, files get moved), and including them would re-mint IDs on
  changes that do not alter the obligation itself.

  Attributes:
    file: Repository-relative path, POSIX separators.
    line_start: 1-based first line of the enclosing block.
    line_end: 1-based last line of the enclosing block, inclusive.
    section: Heading breadcrumb, e.g. ``Checkout Capability > Continue URL``.
    block_type: Markdown construct the clause was found in.

  """

  file: str
  line_start: int
  line_end: int
  section: str
  block_type: BlockType

  def as_dict(self) -> dict[str, object]:
    """Return a JSON-serializable form with enums reduced to strings."""
    return {
      "file": self.file,
      "line_start": self.line_start,
      "line_end": self.line_end,
      "section": self.section,
      "block_type": str(self.block_type),
    }


@dataclasses.dataclass
class Clause:
  """A candidate normative sentence, prior to identity assignment.

  Instances start life from the parser with only `text`, `source`,
  `document_order` and possibly `compound_parent` populated. Later stages fill
  in the rest. A clause that never receives a `level` is not normative and is
  dropped before the catalog is written.

  Attributes:
    text: Raw Markdown of the sentence, emphasis and links intact.
    normalized: Canonical form used for hashing. Set by the identity stage.
    level: Obligation level, or None if the clause is not an obligation.
    annotation: Annotation keyword, when the clause is a schema annotation.
    bolded: Whether the governing keyword was wrapped in ``**``.
    capability: Reverse-DNS capability identifier.
    actor: Party the obligation falls on, or None when genuinely absent.
    actor_confidence: 0.0-1.0. See metadata.extract_actor for the scale.
    referenced_fields: Sorted, deduplicated inline-code identifiers.
    condition: Normalized trigger clause, e.g. ``when status == failed``.
    compound_parent: Stem text when this clause is a colon-list child.
    source: Provenance record.
    document_order: Monotonic per-document counter. Display only; carries no
      identity and may change freely between runs of different inputs.
    split_from_compound: True when produced by splitting a multi-obligation
      sentence, recorded so the diagnostics report can surface it.

  """

  text: str
  source: SourceRef
  document_order: int
  normalized: str = ""
  level: Level | None = None
  annotation: Annotation | None = None
  bolded: bool = False
  capability: str | None = None
  actor: str | None = None
  actor_confidence: float = 0.0
  referenced_fields: list[str] = dataclasses.field(default_factory=list)
  condition: str | None = None
  compound_parent: str | None = None
  split_from_compound: bool = False

  @property
  def is_obligation(self) -> bool:
    """Whether this clause carries an RFC 2119 obligation level."""
    return self.level is not None


@dataclasses.dataclass
class Requirement(Clause):
  """A clause that has been assigned a stable, content-addressed identity.

  The `id` is derived solely from `normalized`; see identity.requirement_id.

  Attributes:
    id: Identifier of the form ``UCP-<CAPABILITY-SLUG>-<10 hex>``, with an
      optional ``-2``/``-3`` suffix disambiguating genuine duplicate prose.

  """

  id: str = ""

  def as_dict(self, spec_version: str) -> dict[str, object]:
    """Return the JSON-serializable catalog record.

    Args:
      spec_version: Release the catalog was generated from. Carried on the
        catalog rather than per clause, because UCP documents do not declare
        individual versions.

    Returns:
      A dict whose keys match the published requirement schema.

    """
    return {
      "id": self.id,
      "capability": self.capability,
      "version": spec_version,
      "level": str(self.level) if self.level else None,
      "actor": self.actor,
      "actor_confidence": round(self.actor_confidence, 2),
      "text": self.text,
      "normalized": self.normalized,
      "condition": self.condition,
      "referenced_fields": list(self.referenced_fields),
      "compound_parent": self.compound_parent,
      "document_order": self.document_order,
      "source": self.source.as_dict(),
    }


@dataclasses.dataclass
class ExtractionReport:
  """Diagnostics accumulated while building the catalog.

  This is the spec-linter half of the output and is as valuable as the
  catalog itself. Its governing rule is that nothing disappears quietly: a
  clause that cites an RFC 2119 keyword but does not reach the catalog must
  appear in exactly one of these lists, so the totals reconcile.

  Attributes:
    candidates_without_emphasis: Obligations whose keyword was not
      emphasized. Under house style these read as normative but are
      excluded, so each is either a deliberate non-obligation or a spec bug
      worth fixing.
    annotations_excluded: Schema field annotations, which mark optionality
      rather than stating an obligation on a party.
    annotation_as_obligation: Annotation keywords used in prose and therefore
      promoted to the equivalent obligation level. Logged for review because
      the distinction is a judgement call.
    rfc2119_boilerplate: Clauses dropped for citing so many keywords that
      they must be the RFC 2119 definition paragraph.
    multi_obligation_sentences: Sentences carrying more than one obligation,
      recorded with the levels they were split into.
    compounds_not_split: Multi-obligation sentences with no conjunction
      boundary, emitted as a single clause at the strongest level present.
    empty_after_split: Fragments that reduced to nothing during splitting.
    actor_unresolved: Obligations no strategy could attribute to a party.
    actor_low_confidence: Obligations attributed only by a weak signal, such
      as the section heading. Worth an author's eye before the catalog is
      relied on.
    actor_after_keyword_only: Obligations whose sole lexicon match follows
      the keyword. Recorded rather than used: the match is usually the
      direct object, not the party under obligation.

  """

  candidates_without_emphasis: list[dict[str, object]] = dataclasses.field(
    default_factory=list
  )
  annotations_excluded: list[dict[str, object]] = dataclasses.field(
    default_factory=list
  )
  annotation_as_obligation: list[dict[str, object]] = dataclasses.field(
    default_factory=list
  )
  rfc2119_boilerplate: list[dict[str, object]] = dataclasses.field(
    default_factory=list
  )
  multi_obligation_sentences: list[dict[str, object]] = dataclasses.field(
    default_factory=list
  )
  compounds_not_split: list[dict[str, object]] = dataclasses.field(
    default_factory=list
  )
  empty_after_split: list[dict[str, object]] = dataclasses.field(
    default_factory=list
  )
  actor_unresolved: list[dict[str, object]] = dataclasses.field(
    default_factory=list
  )
  actor_low_confidence: list[dict[str, object]] = dataclasses.field(
    default_factory=list
  )
  actor_after_keyword_only: list[dict[str, object]] = dataclasses.field(
    default_factory=list
  )

  def as_dict(self) -> dict[str, object]:
    """Return a JSON-serializable form."""
    return {
      field.name: getattr(self, field.name)
      for field in dataclasses.fields(self)
    }
