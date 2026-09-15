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

"""Stage 3: attaching the metadata a requirement needs to be actionable.

An obligation is only useful to an implementer if it says who is bound, what
it operates on, and when it applies. This stage derives those three from the
clause and its surroundings.

Actor
  Resolved by a fixed ladder of strategies, strongest first, each carrying a
  confidence so that consumers can tell a stated actor from an inferred one.
  The ladder stops at the first strategy that answers, and the confidence is
  that strategy's, never an average.

  Only text before the keyword is considered. This is the stage's least
  obvious rule and the one most likely to be "fixed" by a later reader, so:
  a lexicon match after the keyword is usually the direct object rather than
  the party under obligation. "**MUST** present the content to the buyer"
  obliges the host. Across this corpus the signal is wrong far more often
  than it is right, so it is rejected and reported instead of used.

Referenced fields
  The inline-code identifiers the obligation operates on, recognized by
  shape rather than by exclusion. A span that pins a field to a value keeps
  the field and drops the value.

Condition
  The trigger clause that bounds when the obligation applies, kept as the
  spec's own words. Reducing "When the pricing basis is the sale basis" to a
  formal predicate would be a semantic claim this stage cannot honestly
  make, so the text is recorded verbatim and normalization is left to a
  consumer that knows the schema.
"""

from __future__ import annotations

import dataclasses
import re

from tools.requirements_extractor import classifier, config, parser
from tools.requirements_extractor.models import Clause, ExtractionReport

# An author's explicit override, e.g. <!-- ucp:actor=business -->. None appear
# in the corpus today; the hook exists because it is the remedy an author
# reaches for when the report flags a clause as unresolved or low confidence.
ACTOR_ANNOTATION_RE = re.compile(
  r"<!--\s*ucp:actor\s*=\s*([a-z_]+)\s*-->", re.IGNORECASE
)

# Surface form -> canonical actor, longest surface first so that "payment
# handler" is not shadowed by "handler" and "embedded checkout" is not
# shadowed by a bare party name.
_SURFACE_TO_ACTOR: dict[str, str] = {
  form: actor for actor, forms in config.ACTOR_LEXICON.items() for form in forms
}
_SURFACES: tuple[str, ...] = tuple(
  sorted(_SURFACE_TO_ACTOR, key=len, reverse=True)
)
_SURFACE_RE = {
  surface: re.compile(r"\b" + re.escape(surface) + r"\b", re.IGNORECASE)
  for surface in _SURFACES
}

_CODE_SPAN_RE = re.compile(r"`([^`]*)`")

# Markdown that should not survive into a recorded condition.
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_EMPHASIS_RE = re.compile(r"\*\*|\*|__")

_OPENERS = "([{"
_CLOSERS = ")]}"


def keyword_position(clause: Clause) -> int:
  """Return the offset where this clause's obligation keyword begins.

  Args:
    clause: A classified obligation.

  Returns:
    The offset of the governing keyword, or the length of the text when no
    keyword can be located, which makes "before the keyword" mean "anywhere".

  """
  masked = parser.mask_code_spans(clause.text)
  hits = classifier.find_keywords(masked, config.OBLIGATION_KEYWORDS)
  if not hits:
    return len(clause.text)
  bolded = [hit for hit in hits if hit.bolded]
  return (bolded[0] if bolded else hits[0]).outer_start


def _last_match_before(text: str, cutoff: int) -> str | None:
  """Return the canonical actor of the last lexicon match before `cutoff`."""
  best_actor: str | None = None
  best_start = -1
  for surface in _SURFACES:
    for match in _SURFACE_RE[surface].finditer(text, 0, cutoff):
      if match.start() > best_start:
        best_start = match.start()
        best_actor = _SURFACE_TO_ACTOR[surface]
  return best_actor


def _first_match_within(text: str, limit: int) -> str | None:
  """Return the canonical actor of the earliest match within `limit`."""
  best_actor: str | None = None
  best_start = len(text) + 1
  for surface in _SURFACES:
    match = _SURFACE_RE[surface].search(text)
    if match and match.start() < min(best_start, limit):
      best_start = match.start()
      best_actor = _SURFACE_TO_ACTOR[surface]
  return best_actor


def _mentions_actor_after(text: str, cutoff: int) -> str | None:
  """Return an actor mentioned only after the keyword, for reporting."""
  for surface in _SURFACES:
    match = _SURFACE_RE[surface].search(text, cutoff)
    if match:
      return _SURFACE_TO_ACTOR[surface]
  return None


def extract_actor(clause: Clause) -> tuple[str | None, float]:
  """Resolve the party an obligation binds, with a confidence.

  Strategies are tried strongest first and the first answer wins:

    1.0  an explicit ``<!-- ucp:actor=... -->`` annotation
    0.9  the last lexicon match before the keyword, which is the subject
    0.8  a colon-list stem that names the party, e.g. "**Host
         responsibilities**:", where the obligation itself is a bare
         fragment such as "**MUST** validate that ..."
    0.5  a party named in the heading breadcrumb
    0.0  unresolved

  Args:
    clause: A classified obligation.

  Returns:
    The canonical actor and the confidence of the strategy that found it,
    or (None, 0.0).

  """
  annotation = ACTOR_ANNOTATION_RE.search(clause.text)
  if annotation:
    return annotation.group(1).lower(), config.ACTOR_CONFIDENCE_ANNOTATION

  masked = parser.mask_code_spans(clause.text)

  inline = _last_match_before(masked, keyword_position(clause))
  if inline:
    return inline, config.ACTOR_CONFIDENCE_INLINE

  if clause.compound_parent and config.STEM_OBLIGATION_LABEL_RE.search(
    clause.compound_parent
  ):
    stem = _first_match_within(
      parser.mask_code_spans(clause.compound_parent),
      config.STEM_ACTOR_MAX_OFFSET,
    )
    if stem:
      return stem, config.ACTOR_CONFIDENCE_COMPOUND_PARENT

  if clause.source.section:
    section = _first_match_within(
      clause.source.section, len(clause.source.section)
    )
    if section:
      return section, config.ACTOR_CONFIDENCE_SECTION

  return None, config.ACTOR_CONFIDENCE_NONE


def extract_referenced_fields(text: str) -> list[str]:
  """Return the schema fields an obligation names, sorted and deduplicated.

  Args:
    text: Clause text, with code spans intact.

  Returns:
    Canonical field names. A span pinning a field to a value contributes the
    field alone, so ``severity: "recoverable"`` yields ``severity``.

  """
  fields: set[str] = set()

  for raw in _CODE_SPAN_RE.findall(text):
    value = raw.strip()
    if not value or len(value) > config.FIELD_MAX_LENGTH:
      continue
    if config.FIELD_URL_RE.match(value):
      continue

    pair = config.FIELD_KEY_VALUE_RE.match(value)
    if pair:
      value = pair.group(1)

    if value in config.FIELD_STOP_WORDS:
      continue
    if config.FIELD_NAME_RE.match(value):
      fields.add(value)

  return sorted(fields)


def _clean(text: str) -> str:
  """Strip link syntax and emphasis from a recorded condition."""
  without_links = _LINK_RE.sub(r"\1", text)
  return " ".join(_EMPHASIS_RE.sub("", without_links).split())


def _subordinate_end(text: str, start: int) -> int:
  """Find the comma closing a leading subordinate clause.

  Commas inside brackets belong to a parenthetical rather than to the
  sentence structure -- "(e.g., origin validation failure)" contains one --
  so only depth-zero commas end the clause.

  Args:
    text: Clause text with code spans masked.
    start: Offset of the trigger word.

  Returns:
    Offset of the closing comma, or -1 if there is none.

  """
  depth = 0
  for index in range(start, len(text)):
    char = text[index]
    if char in _OPENERS:
      depth += 1
    elif char in _CLOSERS:
      depth = max(0, depth - 1)
    elif char == "," and depth == 0:
      return index
  return -1


def extract_condition(clause: Clause) -> str | None:
  """Return the trigger clause bounding when an obligation applies.

  A condition may lead the sentence ("When `x` is provided, the host
  **MUST** ...") or trail it ("**MUST** fire the message when that action is
  triggered"). A leading condition is cut at the comma that closes it; a
  trailing one runs to the end of the sentence.

  Args:
    clause: A classified obligation.

  Returns:
    The condition in the spec's own words, or None when the clause states no
    trigger.

  """
  text = clause.text
  masked = parser.mask_code_spans(text)

  trigger = config.CONDITION_TRIGGER_RE.search(masked)
  if not trigger:
    return None

  start = trigger.start()
  if start < keyword_position(clause):
    end = _subordinate_end(masked, start)
    if end == -1:
      return None
  else:
    end = len(text)

  condition = _clean(text[start:end]).rstrip(".,;: ")
  if not condition or len(condition) > config.CONDITION_MAX_LENGTH:
    return None
  return condition


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


def annotate(clause: Clause, report: ExtractionReport) -> Clause:
  """Return a copy of `clause` with actor, fields and condition filled in.

  Args:
    clause: A classified obligation.
    report: Diagnostics collector.

  Returns:
    A new clause; the input is not modified.

  """
  actor, confidence = extract_actor(clause)

  if actor is None:
    report.actor_unresolved.append(_record(clause))
    after = _mentions_actor_after(
      parser.mask_code_spans(clause.text), keyword_position(clause)
    )
    if after:
      report.actor_after_keyword_only.append(_record(clause, candidate=after))
  elif confidence < config.ACTOR_LOW_CONFIDENCE_THRESHOLD:
    report.actor_low_confidence.append(
      _record(clause, actor=actor, confidence=confidence)
    )

  return dataclasses.replace(
    clause,
    capability=config.resolve_capability(
      clause.source.file, config.REPO_ROOT / clause.source.file
    ),
    actor=actor,
    actor_confidence=confidence,
    referenced_fields=extract_referenced_fields(clause.text),
    condition=extract_condition(clause),
  )


def annotate_all(
  clauses: list[Clause], report: ExtractionReport | None = None
) -> tuple[list[Clause], ExtractionReport]:
  """Attach metadata to every obligation.

  Args:
    clauses: Classified obligations.
    report: Existing diagnostics collector, or None to create one.

  Returns:
    The annotated clauses, and the diagnostics collected.

  """
  collected = report or ExtractionReport()
  return [annotate(clause, collected) for clause in clauses], collected
