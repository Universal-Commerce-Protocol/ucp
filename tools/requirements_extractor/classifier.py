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

"""Stage 2: deciding which clauses are normative.

Given the parser's candidates, this stage answers two questions: does the
clause state an obligation, and at what level. Four rules do the work.

Emphasis gates obligations
  UCP house style bolds the keyword of a real obligation. Treating emphasis
  as the signal keeps prose that merely mentions a keyword out of the
  catalog. An obligation whose keyword is not bolded is reported rather than
  emitted, because each is either intentionally non-normative or a spec bug.

Annotations are not obligations
  ``REQUIRED``, ``OPTIONAL`` and ``RECOMMENDED`` are used predominantly to
  mark schema field optionality, as in ``ec_version (string, REQUIRED):``.
  Those are excluded. The same keywords in running prose ("Response
  signatures are RECOMMENDED for ...") do state an obligation and are
  promoted to the RFC 2119 equivalent level.

Boilerplate is not an obligation
  The paragraph defining the keywords cites most of them at once. Any clause
  naming four or more distinct keywords is that paragraph.

One sentence can hold two obligations
  "The host MUST tear down the context and MAY redirect the buyer" is two
  requirements at different levels. Such sentences are split at the
  conjunction, with each fragment inheriting the shared subject.
"""

from __future__ import annotations

import dataclasses
import re

from tools.requirements_extractor import config, parser
from tools.requirements_extractor.models import (
  Annotation,
  Clause,
  ExtractionReport,
  Level,
)

# RFC 2119 defines the annotation keywords as synonyms of obligation levels.
# Used when an annotation keyword appears in prose rather than as a schema
# field marker.
_ANNOTATION_TO_LEVEL = {
  Annotation.REQUIRED: Level.MUST,
  Annotation.RECOMMENDED: Level.SHOULD,
  Annotation.OPTIONAL: Level.MAY,
}

# Strongest first, for choosing a level when a compound cannot be split.
_LEVEL_STRENGTH = {
  Level.MUST_NOT: 6,
  Level.SHALL_NOT: 6,
  Level.MUST: 5,
  Level.SHALL: 5,
  Level.SHOULD_NOT: 4,
  Level.SHOULD: 3,
  Level.MAY: 1,
}

_LEVEL_BY_KEYWORD = {level.value: level for level in Level}
_ANNOTATION_BY_KEYWORD = {ann.value: ann for ann in Annotation}


def _keyword_pattern(keyword: str) -> str:
  """Return a regex body matching a keyword with flexible inner whitespace."""
  return keyword.replace(" ", r"\s+")


_PLAIN_RE = {
  kw: re.compile(r"\b" + _keyword_pattern(kw) + r"\b")
  for kw in config.ALL_KEYWORDS
}
_BOLD_RE = {
  kw: re.compile(r"\*\*\s*" + _keyword_pattern(kw) + r"\s*\*\*")
  for kw in config.ALL_KEYWORDS
}

# A schema field annotation: a field name in backticks, a parenthesised type
# carrying the keyword, and nothing else. Matching the shape directly is more
# precise than trying to detect the absence of a finite verb, and it keeps
# genuinely normative prose such as "Response signatures are RECOMMENDED
# for:" out of the exclusion.
_SCHEMA_ANNOTATION_RE = re.compile(
  r"^\s*[`*]*`[^`]+`[`*]*\s*"
  r"\([^)]*\*\*(?:REQUIRED|OPTIONAL|RECOMMENDED)\*\*[^)]*\)"
  r"\s*[:.]?\s*$"
)

# Conjunctions that can separate two obligations in one sentence.
_CONJUNCTION_RE = re.compile(r"\b(?:and|but|or)\b|;")

# Leading residue left behind after cutting at a conjunction.
_FRAGMENT_TRIM_RE = re.compile(r"^[\s,;:)\-]+|[\s,;:(\-]+$")


@dataclasses.dataclass(frozen=True)
class KeywordHit:
  """One keyword occurrence within a clause.

  Two spans are recorded. The inner one locates the keyword itself; the outer
  one additionally covers the ``**`` markers when the keyword is bolded.
  Splitting a compound sentence must cut on the outer span, otherwise the
  emphasis markers are severed and each fragment is left with half a pair.

  Attributes:
    start: Character offset of the keyword, into the masked text.
    end: Character offset just past the keyword.
    keyword: The keyword as spelled in RFC 2119.
    bolded: Whether the occurrence was wrapped in ``**``.
    outer_start: Offset of the opening ``**``, or `start` when not bolded.
    outer_end: Offset just past the closing ``**``, or `end` when not bolded.

  """

  start: int
  end: int
  keyword: str
  bolded: bool
  outer_start: int
  outer_end: int


def find_keywords(text: str, keywords: tuple[str, ...]) -> list[KeywordHit]:
  """Locate non-overlapping keyword occurrences, longest match winning.

  Keywords are tried in the order given, which `config` guarantees is
  longest first. Without that ordering "MUST NOT" would be recorded as
  "MUST", inverting the obligation.

  Args:
    text: Clause text with code spans already masked.
    keywords: Keywords to search for, longest first.

  Returns:
    Hits sorted by position.

  """
  hits: list[KeywordHit] = []
  claimed: list[tuple[int, int]] = []

  for keyword in keywords:
    for match in _PLAIN_RE[keyword].finditer(text):
      if any(
        match.start() >= start and match.end() <= end for start, end in claimed
      ):
        continue
      claimed.append((match.start(), match.end()))
      outer = next(
        (
          (bold.start(), bold.end())
          for bold in _BOLD_RE[keyword].finditer(text)
          if bold.start() <= match.start() and bold.end() >= match.end()
        ),
        None,
      )
      hits.append(
        KeywordHit(
          start=match.start(),
          end=match.end(),
          keyword=keyword,
          bolded=outer is not None,
          outer_start=outer[0] if outer else match.start(),
          outer_end=outer[1] if outer else match.end(),
        )
      )

  return sorted(hits, key=lambda hit: hit.start)


def is_boilerplate(hits: list[KeywordHit]) -> bool:
  """Whether the keyword spread marks this as the RFC 2119 definition text.

  Args:
    hits: Keyword occurrences found in the clause.

  Returns:
    True when the clause names at least the configured number of distinct
    keywords, which no ordinary obligation does.

  """
  distinct = {hit.keyword for hit in hits}
  return len(distinct) >= config.RFC2119_BOILERPLATE_KEYWORD_THRESHOLD


def is_schema_annotation(text: str) -> bool:
  """Whether the clause is a schema field annotation rather than prose.

  Args:
    text: Clause text.

  Returns:
    True for forms like ``ec_version (string, REQUIRED):``.

  """
  return bool(_SCHEMA_ANNOTATION_RE.match(text.strip()))


def _strongest(levels: list[Level]) -> Level:
  """Return the most demanding level in the list."""
  return max(levels, key=lambda level: _LEVEL_STRENGTH[level])


def _trim(fragment: str) -> str:
  """Strip separator residue from a split fragment."""
  return _FRAGMENT_TRIM_RE.sub("", fragment).strip()


def split_compound(
  clause: Clause, hits: list[KeywordHit]
) -> list[Clause] | None:
  """Split a sentence carrying several obligations into one clause each.

  Cuts are made at the conjunction nearest the following keyword, so that an
  earlier "and" joining a list of nouns is not mistaken for the boundary, and
  on the outer span of each hit so that ``**`` pairs stay intact.

  A sentence may state its subject once and let it govern every obligation
  ("The host **MUST** tear down the context and **MAY** redirect the buyer"),
  or it may give each obligation its own ("A revision **MUST** be returned
  ...; the Business **MUST NOT** silently reinterpret ..."). The shared
  subject is therefore prepended only to fragments that begin at their
  keyword; anything already sitting in front of the keyword is that
  fragment's own subject, and prepending would produce a doubled one.

  Args:
    clause: The clause to split.
    hits: Bolded obligation hits, in order, at least two of them.

  Returns:
    One clause per obligation, or None when any boundary has no conjunction,
    leaving the caller to fall back to a single strongest-level clause.

  """
  text = clause.text
  subject = _trim(text[: hits[0].outer_start])

  cut_points: list[tuple[int, int]] = []
  for current, following in zip(hits, hits[1:], strict=False):
    segment = text[current.outer_end : following.outer_start]
    matches = list(_CONJUNCTION_RE.finditer(segment))
    if not matches:
      return None
    last = matches[-1]
    cut_points.append(
      (current.outer_end + last.start(), current.outer_end + last.end())
    )

  fragments: list[Clause] = []
  start = hits[0].outer_start
  for index, hit in enumerate(hits):
    end = cut_points[index][0] if index < len(cut_points) else len(text)
    body = _trim(text[start:end])
    own_subject = _trim(text[start : hit.outer_start])
    if index < len(cut_points):
      start = cut_points[index][1]
    if not body:
      continue
    combined = (
      f"{subject} {body}".strip() if subject and not own_subject else body
    )
    fragments.append(
      dataclasses.replace(
        clause,
        text=combined,
        level=_LEVEL_BY_KEYWORD[hit.keyword],
        bolded=True,
        split_from_compound=True,
      )
    )

  return fragments or None


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


def classify(
  clause: Clause, report: ExtractionReport, include_annotations: bool = False
) -> list[Clause]:
  """Classify one clause, returning the obligations it yields.

  Args:
    clause: Candidate from the parser.
    report: Diagnostics collector; every exclusion is recorded here.
    include_annotations: Emit schema annotations as clauses rather than
      excluding them.

  Returns:
    Zero or more clauses with `level` set. Zero means the clause is not an
    obligation, in which case the reason has been recorded in the report.

  """
  # Inline code carries field names and example values. A keyword inside
  # backticks is a value being named, not an obligation being stated.
  masked = parser.mask_code_spans(clause.text)
  hits = find_keywords(masked, config.ALL_KEYWORDS)
  if not hits:
    return []

  if is_boilerplate(hits):
    report.rfc2119_boilerplate.append(
      _record(clause, keywords=sorted({hit.keyword for hit in hits}))
    )
    return []

  obligations = [
    hit for hit in hits if hit.keyword in config.OBLIGATION_KEYWORDS
  ]
  bolded = [hit for hit in obligations if hit.bolded]

  if obligations and not bolded:
    report.candidates_without_emphasis.append(
      _record(clause, keywords=[hit.keyword for hit in obligations])
    )
    return []

  if not obligations:
    return _classify_annotation(clause, hits, report, include_annotations)

  if len(bolded) == 1:
    return [
      dataclasses.replace(
        clause, level=_LEVEL_BY_KEYWORD[bolded[0].keyword], bolded=True
      )
    ]

  return _split_or_collapse(clause, bolded, report)


def _split_or_collapse(
  clause: Clause, bolded: list[KeywordHit], report: ExtractionReport
) -> list[Clause]:
  """Split a multi-obligation sentence, or collapse it if it has no boundary."""
  levels = [_LEVEL_BY_KEYWORD[hit.keyword] for hit in bolded]
  fragments = split_compound(clause, bolded)

  if fragments is None:
    report.compounds_not_split.append(
      _record(clause, levels=[str(level) for level in levels])
    )
    return [dataclasses.replace(clause, level=_strongest(levels), bolded=True)]

  report.multi_obligation_sentences.append(
    _record(
      clause,
      levels=[str(fragment.level) for fragment in fragments],
      parts=len(fragments),
    )
  )
  if len(fragments) < len(bolded):
    report.empty_after_split.append(
      _record(clause, expected=len(bolded), produced=len(fragments))
    )
  return fragments


def _classify_annotation(
  clause: Clause,
  hits: list[KeywordHit],
  report: ExtractionReport,
  include_annotations: bool,
) -> list[Clause]:
  """Handle a clause whose only keywords are annotations."""
  annotation = _ANNOTATION_BY_KEYWORD[hits[0].keyword]

  if is_schema_annotation(clause.text):
    report.annotations_excluded.append(
      _record(clause, annotation=str(annotation))
    )
    if include_annotations:
      return [dataclasses.replace(clause, annotation=annotation)]
    return []

  # Used in running prose, so it states an obligation. RFC 2119 defines the
  # equivalence; the promotion is logged because the call is a judgement.
  level = _ANNOTATION_TO_LEVEL[annotation]
  report.annotation_as_obligation.append(
    _record(clause, annotation=str(annotation), level=str(level))
  )
  return [
    dataclasses.replace(
      clause,
      level=level,
      annotation=annotation,
      bolded=any(hit.bolded for hit in hits),
    )
  ]


def classify_all(
  clauses: list[Clause],
  report: ExtractionReport | None = None,
  include_annotations: bool = False,
) -> tuple[list[Clause], ExtractionReport]:
  """Classify every candidate clause.

  Args:
    clauses: Candidates from the parser.
    report: Existing diagnostics collector, or None to create one.
    include_annotations: Emit schema annotations as clauses.

  Returns:
    The obligations found, and the diagnostics collected.

  """
  collected = report or ExtractionReport()
  obligations: list[Clause] = []
  for clause in clauses:
    obligations.extend(classify(clause, collected, include_annotations))
  return obligations, collected
