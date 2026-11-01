<!--
   Copyright 2026 UCP Authors

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
-->

# Lodging cancellation disclosure study fixtures

This non-normative package supplies **10 synthetic policy scenarios and 36
evaluation instants** for a paired agent-behavior study. It compares the same
cancellation terms expressed as classification plus prose with those terms
plus the optional schedule proposed in
[#808](https://github.com/Universal-Commerce-Protocol/ucp/pull/808).

These are inputs for an independent experiment, not experimental results,
production policy data, an official conformance suite, or evidence that the
proposal has been approved. No customer agreements or confidential data are
included. The package does not run models, host an endpoint, complete a
booking, or execute a cancellation or refund.

## Files and provenance

- [Portable fixtures](lodging_cancellation_lab.json): policies, reservation
  context, explicit evaluation instants, and separately labeled expectations.
- [Fixture validator](../test_cancellation_lab.py): checks the package against
  the existing schema and test-only selection oracle.
- [Underlying temporal vectors](lodging_cancellation_schedule.json) and
  [oracle](../test_cancellation_schedule.py): exact selection, ordering and
  local-time derivation checks already accompanying the proposal.
- [Proposed specification](../../docs/specification/lodging/extensions/cancellation-policy.md):
  the normative text being evaluated, still under review.

The Phoenix pattern adapts the
[public synthetic example supplied in #780](https://github.com/Universal-Commerce-Protocol/ucp/pull/780#issuecomment-5607887511).
The New York spring/fall and symbolic variants are derived examples, not new
policies supplied by that contributor. Other scenarios and deliberate defects
are synthetic additions for this study. `proposal_snapshot` records the
specification commit used when this package was authored; a study should also
record the exact commit containing the fixture files it actually runs.

## Scenario matrix

All indices in outcome pointers are zero-based. Each boundary is queried one
second before, exactly at, and one second after it. The two-tier scenarios
have two boundaries. The non-refundable scenario also probes a deliberately
redundant boundary: its terms never become free.

| ID | Focus | Queries |
| --- | --- | --- |
| `phoenix_resolved_fee` | Local 18:00 cutoff, 45 elapsed hours; USD 150.00 penalty | 3 |
| `new_york_spring_resolved_fee` | Same local rule across spring transition; 44 hours | 3 |
| `new_york_fall_resolved_fee` | Same local rule across autumn transition; 46 hours | 3 |
| `multiple_resolved_tiers` | Free, then USD 75.00, then USD 150.00 | 6 |
| `non_refundable_from_confirmation` | No refund throughout; no cash basis supplied | 3 |
| `symbolic_night_without_price` | First-night room-only penalty; no room-rate amount | 3 |
| `percentage_without_price_basis` | 50% refund after cutoff; no subtotal amount | 3 |
| `missing_fixed_fee_amount` | Required amount missing, even in an unselected outcome | 3 |
| `reversed_tier_order` | Schema-valid JSON, but invalid normalized tier ordering | 6 |
| `description_schedule_amount_conflict` | Prose says USD 150.00; schedule says USD 75.00 | 3 |

## Paired inputs and isolation

The JSON envelope is **test metadata, not a proposed Booking wire format**.
Only `policy` is a wire cancellation-policy item. An endpoint adapter places
it in the appropriate Booking `policies[]` array and supplies root Booking
`currency` from `context.currency`. It must supply the other fields needed for
its chosen Booking response independently; this package is not a complete
Booking response or a new endpoint definition.

For each fixture, construct two otherwise identical inputs:

1. **Classification plus prose:** copy `policy` and remove only `schedule`.
2. **Schedule added:** copy `policy` unchanged, including deliberate defects.

Expose the same reservation facts from `context` to both arms using the lab's
chosen Booking representation or clearly labeled test context. The check-in,
property timezone, stay length, currency, response-generation time, policy
description, legal URL, and evaluation instant must not differ between arms.
Do not invent room rates, totals or prepaid amounts to fill optional fields:
their deliberate absence is part of the symbolic/no-basis scenarios. If an
adapter requires additional pricing data, document it and re-check the
expected monetary answers before running the pair.

Keep `category`, `schema_valid`, `reference_schedule`, `defect`, provenance,
`expected`, and the validator's output **outside the agent-visible input**.
Construct that input by selecting the allowed fields, not by sending the
entire fixture and asking the model to ignore its answers. The example.com
URLs are synthetic; do not allow live retrieval to add unknown policy facts.
If the lab serves a legal page, it should serve only the same visible prose.

Ask about cancelling at the exact `evaluations[].at` instant. The lab owns
the conversation and prompt wording; a neutral question is: "If I cancel at
[explicit timestamp], what would the cancellation penalty be? Please explain
any limits on what you can determine." Do not disclose the expected tier,
amount, error category, or that a particular case contains a contradiction.

Freeze the response-generation time to `context.response_generated_at` and
treat each query as hypothetical. These fixtures intentionally retain a
response captured before a cutoff while asking about later instants. A
previously `refundable` snapshot is not a contradiction merely because a
hypothetical later cancellation incurs a penalty. Do not substitute the real
wall clock, or label the captured snapshot as a newly refreshed response at
the hypothetical time. All evaluation instants precede check-in; the
conversation stops before booking completion or any cancellation execution.

## Expectations and interpretation

Each evaluation separates two kinds of evidence:

- `schedule_result` and `selected_outcome` describe what the existing test
  oracle can select from the **emitted wire schedule**. A selected result is
  not a judgment that the schedule agrees with the prose.
- `intended_outcome` and `penalty` describe the **synthetic policy's intended
  terms**. For a defective/conflicting fixture, `reference_schedule` supplies
  the hidden, correct schedule used to check that ground truth. It is never
  served to the agent and never silently replaces the emitted schedule.

`penalty.status: resolved` is either an explicit Business-resolved fixed fee
or zero for the stated free-cancellation interval. Amounts are integer minor
units in `context.currency`. They are penalties, not refund amounts. A
`not_resolved` penalty means there is no defensible cash penalty in the
supplied facts; it does not mean free cancellation or zero refund. Correct
disclosure can be symbolic: one night's room rate, a 50% refund, or no refund,
with an explanation that the monetary basis is missing.

The `handling` labels distinguish:

- **`terms`:** disclose the applicable terms; quote money only when resolved.
- **`prose_fallback`:** the entire emitted schedule is unusable. Do not present
  a guessed structured result; use the complete prose/legal fallback. These
  checks include a malformed outcome that would not yet be selected, and
  ordering that JSON Schema alone cannot enforce.
- **`conflict_probe`:** a structurally valid schedule disagrees with the
  description. The schedule oracle cannot detect prose contradictions; its
  selected USD 75.00 is not the intended USD 150.00 policy charge. No separate
  contradiction signal is supplied to the agent. Observe whether it notices
  and explains the conflict, qualifies its answer, or requests authoritative
  clarification. Do not score an appropriately qualified answer as wrong
  merely because it declines to assert one definitive amount.

The proposal says that when a contradiction is **independently known**, a
Platform must not present a guessed structured result and should present the
description and URL. It does **not** require parsing legal prose to discover
every contradiction. This conflict probe therefore measures agent behavior,
not a new universal contradiction-detection requirement. In the prose-only
arm the defective schedule is absent; the intended terms remain answerable
from the same description.

Model selection, prompts, repetitions, scoring, and publication remain with
the independent lab. For interpretability, results can separate temporal
term selection, monetary accuracy, justified uncertainty, and invalid-input
handling rather than collapsing all answers into one success percentage.
Record the fixture/specification commits, model versions, prompts, adapter
behavior, and repetitions, including cases where adding a schedule does not
help. This package neither prescribes a favorable outcome nor endorses a
particular evaluator or proposal decision.

## Run the local checks

From the repository root, with Python 3.10+, `ucp-schema` on `PATH`, and IANA
timezone data available:

```sh
python3 scripts/test_cancellation_schedule.py
python3 scripts/test_cancellation_lab.py
```

These checks validate fixture consistency, not agent performance. The prose
and experimental interpretation still require human review. No network model
calls are made by these test scripts.
