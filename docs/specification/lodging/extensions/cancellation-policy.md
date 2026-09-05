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

# Cancellation Policy Extension

## Overview

The Cancellation Policy Extension defines the
`dev.ucp.lodging.policy.cancellation` policy type on the core
[`policies[]`](../../overview/index.md#policies) primitive for the lodging
service. It adds pre-purchase machine-readable cancellation terms so Platforms
can answer whether cancellation is free, which cutoff applies, and what outcome
follows without parsing legal prose.

**Key features:**

- Tri-state `refundability` classification for the current high-level state
- Optional deterministic `schedule` with an exact anchor and relative cutoffs
- Structured percentage, fixed-fee, and lodging-unit outcomes
- Required human-readable `description` and optional legal-terms `url`

**Dependencies:**

- The core `policies[]` primitive (see
  [Policies](../../overview/index.md#policies)).
- Booking (`dev.ucp.lodging.booking`), which this policy type extends.

## Discovery

Businesses advertise cancellation policy support in their profile. The type
extends any Booking surface that carries `policies[]`:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.lodging.policy.cancellation": [
        {
          "version": "{{ ucp_version }}",
          "extends": [
            "dev.ucp.lodging.booking"
          ],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/lodging/extensions/cancellation-policy",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/lodging/policy_cancellation.json"
        }
      ]
    }
  }
}
```

## Schema

When this type is active, a `policies[]` entry whose `type` is
`dev.ucp.lodging.policy.cancellation` carries `refundability` and may carry a
`schedule`, in addition to the base `type`, `description`, `applies_to`, and
`url` fields.

{{ extension_schema_fields('policy_cancellation.json#/$defs/cancellation_item', 'lodging/extensions/cancellation-policy') }}

### Cancellation Schedule

{{ extension_schema_fields('policy_cancellation.json#/$defs/cancellation_schedule', 'lodging/extensions/cancellation-policy') }}

### Cancellation Tier

{{ extension_schema_fields('policy_cancellation.json#/$defs/cancellation_tier', 'lodging/extensions/cancellation-policy') }}

### Cancellation Outcome

{{ extension_schema_fields('policy_cancellation.json#/$defs/cancellation_outcome', 'lodging/extensions/cancellation-policy') }}

## Cancellation terms

### Refundability classification

`refundability` provides a standardized current high-level classification:

- **`refundable`**: cancellation without penalty is currently available.
- **`partially_refundable`**: the current cancellation result is strictly
  between a full refund and no refund; a penalty applies, but some refundable
  value remains.
- **`non_refundable`**: no refund is currently available upon cancellation,
  subject to applicable law.

Platforms **MUST** tolerate unknown classification values and use `description`
when they cannot interpret the value.

`schedule` does not replace this classification. When both are present, the
Business **MUST** ensure that `refundability` accurately summarizes the outcome
selected at the response-generation instant for the policy's governed scope. A
full refund is `refundable`, no refund is `non_refundable`, and a result strictly
between those endpoints is `partially_refundable`. The Business determines this
classification from its authoritative terms and pricing. A Platform **MUST**
treat `refundability` as authoritative for that snapshot and **MUST NOT**
replace it with a classification derived from an outcome kind or an inferred
monetary basis.

`refundability` is a point-in-time summary. For evaluation at an explicit `at`
instant, `schedule` governs: a Platform **MUST** select the applicable schedule
outcome and **MUST NOT** extrapolate `refundability` to that instant. Crossing a
cutoff later does not make the earlier response contradictory.

### Deterministic schedule

`schedule` is optional. Its absence means that structured timeline evaluation
is unavailable; it does not mean that the booking is non-refundable. When
present, `anchor`, a non-empty `tiers` array, and `after_last_tier` form one
atomic value.

#### Representation

`anchor` is an RFC 3339 instant and **MUST** include `Z` or a numeric UTC
offset. The timestamp identifies an instant; a numeric offset does not declare a
recurring property timezone. For lodging, the anchor normally represents the stated
arrival or check-in cutoff.

Each tier's `until` is an ISO 8601 elapsed duration before `anchor`. This version
supports nonnegative whole-number days, hours, minutes, and seconds only. A day
is exactly 24 elapsed hours. Calendar months, calendar years, local-calendar
days, and business days are not supported.

A Business **MUST** order `tiers` from the farthest cutoff before `anchor` to
the nearest cutoff. Businesses and Platforms compare durations after exact
normalization to elapsed seconds. The durations **MUST** be strictly decreasing
and **MUST NOT** repeat; for example, `P1D` and `PT24H` denote the same cutoff.
An invalid order makes structured evaluation unavailable.

#### Evaluation

For a tier, its cutoff is the `anchor` instant minus its `until` elapsed
duration. `at` is the exact hypothetical or current buyer-cancellation instant
the Platform is evaluating. A Platform evaluates tiers in array order and
selects the first tier for which `at` is strictly earlier than the cutoff. If no
tier matches, `after_last_tier` applies.

The cutoff belongs to the following interval. At exactly `anchor - until`, that
tier no longer applies. Neither party rounds, shifts, or reinterprets `at`, the
anchor, or a computed cutoff. Implementations use exact checked arithmetic. If
a duration or resulting cutoff cannot be represented exactly, structured
evaluation is unavailable.

For example, with an anchor of `2026-12-22T15:00:00-05:00` and `until` of
`PT48H`, the cutoff is `2026-12-20T20:00:00Z`. An evaluation at
`2026-12-20T19:59:59Z` selects the tier; an evaluation at
`2026-12-20T20:00:00Z` advances to the following interval.

#### Outcome vocabulary

`kind` is an open string discriminator. This specification defines these
well-known values:

- **`percentage`** requires `buyer_bps`, an integer from 0 through 10000. It is
  the Business-stated refund percentage under the policy. `0` means no refund
  and `10000` means a full refund. This version does not identify a monetary
  basis for the percentage.
- **`fixed_fee`** requires `penalty.amount`, expressed as an integer in the
  minor units of the root `currency` field of the Booking response. Currency is
  not repeated in the outcome.
- **`unit_deduction`** requires `penalty.measure` using the shared UCP measure
  representation, with a positive `value`, stable `unit`, and required
  `display_text`. `night` is the well-known lodging unit and has an effective
  `scale` of `0`.

Percentage and unit-deduction outcomes are deterministic symbolic terms, but
they do not necessarily imply a cash amount. A Platform **MUST NOT** calculate
money unless the targeted Booking data supplies an unambiguous basis.

For a well-known `kind`, a Business **MUST** emit only the fields defined for
that kind. A Platform evaluates only those fields and ignores unrelated outcome
members. Additional `kind` values **SHOULD** use reverse-domain identifiers.
Unit identifiers and display behavior follow the shared UCP unit rules.

A Platform that encounters an unsupported `kind` **MUST** tolerate the value,
**MUST NOT** infer its meaning or claim a deterministic outcome, and **MUST**
use `description` as the fallback.

### Non-refundable bookings

To signal that a booking or rate is currently non-refundable, a Business
**MUST** set `refundability` to `"non_refundable"`.

When a Business requires that the current non-refundable classification be
shown to the Booker before confirmation, it **MUST** emit a `messages[]` warning
with `presentation: "disclosure"` and a `code` of
`dev.ucp.lodging.policy.cancellation`. It sets `path` to the affected room-rate
node, or omits `path` for a response-wide policy. See [Presenting
policies](../../overview/index.md#presenting-policies).

### Human-readable terms and fallback

`description` remains the universal human-readable and legal fallback. Whether
or not `schedule` is present, a Business **MUST** articulate the full
cancellation timeline and terms in `description`. The point-in-time
`refundability` value **MUST NOT** contradict the outcome that `description`
states applies when the response is created. When present, `schedule`
**MUST NOT** contradict `description`.

Detecting contradictions does not require a Platform to parse legal prose. If a
contradiction is independently known, the schedule is invalid, ordered-tier
constraints are violated, or a selected outcome is unsupported, the Platform
**MUST NOT** present a guessed structured result and **SHOULD** present
`description` and `url`.

## Targeting and precedence

Targeting and precedence are supplied by `policies[]` and are not redefined
here. A policy without `applies_to` is the response-wide default. A policy that
targets a room rate overrides a less-specific policy of the same type. See
[Targeting](../../overview/index.md#targeting) and
[Precedence](../../overview/index.md#precedence).

## Responsibilities

### Business

Cancellation policies are Business-stated response-only facts. When a Business
emits `schedule`, it **MUST** emit a valid ordered schedule and keep it
consistent with `description`. Its outcome at response generation **MUST**
agree with the `refundability` snapshot. The Business preserves the complete
legal summary in `description` and **SHOULD** link the full terms with `url`.

### Platform

A Platform supplies the evaluation instant, applies the exact elapsed-time and
boundary rules above, and respects policy targeting before evaluation. It
**MUST NOT** turn a symbolic percentage or unit deduction into money without an
unambiguous basis, infer a result from an unsupported outcome, or execute
cancellation or refund behavior solely from this pre-purchase policy. It
**SHOULD** refresh the authoritative Booking response before presenting a stale
`refundability` snapshot as current.

## Examples

### Free cancellation followed by a one-night penalty

<!-- ucp:example schema=lodging/policy_cancellation def=cancellation_item -->
```json
{
  "type": "dev.ucp.lodging.policy.cancellation",
  "description": {
    "plain": "Free cancellation until Dec 20, 2026 at 3:00 PM UTC-05:00; one-night penalty thereafter."
  },
  "refundability": "refundable",
  "schedule": {
    "anchor": "2026-12-22T15:00:00-05:00",
    "tiers": [
      {
        "until": "PT48H",
        "outcome": {
          "kind": "percentage",
          "buyer_bps": 10000
        }
      }
    ],
    "after_last_tier": {
      "kind": "unit_deduction",
      "penalty": {
        "measure": {
          "value": 1,
          "unit": "night",
          "display_text": "night"
        }
      }
    }
  },
  "url": "https://example.com/cancellation-terms"
}
```

### Classification-only policy

<!-- ucp:example schema=lodging/policy_cancellation def=cancellation_item -->
```json
{
  "type": "dev.ucp.lodging.policy.cancellation",
  "description": {
    "plain": "Non-refundable promotional rate."
  },
  "applies_to": ["$.room_rates[0]"],
  "refundability": "non_refundable",
  "url": "https://example.com/cancellation-terms#non-refundable"
}
```

## Evaluation examples

The following human-readable cases define selection behavior. `tier[n]` uses
zero-based array indexing. An expected result summarizes the selected wire
outcome; it is not a cancellation or refund instruction. Executable vectors
remain a separate conformance artifact.

| ID | Schedule and evaluation instant | Expected result |
| --- | --- | --- |
| `before_cutoff` | Free-cancellation example; `at = 2026-12-20T19:59:59Z` | `tier[0]`; `percentage`, `buyer_bps = 10000` |
| `exact_cutoff` | Free-cancellation example; `at = 2026-12-20T20:00:00Z` | `after_last_tier`; `unit_deduction`, `penalty.measure.value = 1`, `penalty.measure.unit = night`, `penalty.measure.display_text = night` |
| `after_cutoff` | Free-cancellation example; `at = 2026-12-20T20:00:01Z` | `after_last_tier`; `unit_deduction`, `penalty.measure.value = 1`, `penalty.measure.unit = night`, `penalty.measure.display_text = night` |
| `middle_tier` | `anchor = 2026-12-31T12:00:00Z`; tiers `P7D -> buyer_bps 10000`, `PT48H -> buyer_bps 5000`; `at = 2026-12-24T12:00:00Z` | `tier[1]`; `percentage`, `buyer_bps = 5000` |
| `last_cutoff` | Same two-tier schedule; `at = 2026-12-29T12:00:00Z`; after-last `buyer_bps = 0` | `after_last_tier`; `percentage`, `buyer_bps = 0` |
| `fixed_fee` | `Booking.currency = USD`; `anchor = 2027-01-10T12:00:00Z`; tier `PT24H -> buyer_bps 10000`; `at = 2027-01-09T12:00:00Z`; after-last fixed fee amount `7500` | `after_last_tier`; `fixed_fee`, `penalty.amount = 7500` minor units in USD |
| `elapsed_day` | `anchor = 2026-03-09T02:30:00-04:00`; tier `P1D -> buyer_bps 10000`; `at = 2026-03-08T06:29:59Z` | Because `P1D` is 24 elapsed hours, the cutoff is `2026-03-08T06:30:00Z`; select `tier[0]` |
| `unsupported_kind` | Selected outcome has `kind = com.example.voucher`; otherwise valid schedule | Tolerate the value; structured outcome unavailable; fall back to `description` |
| `schedule_absent` | Policy has no `schedule` | Timeline evaluation unavailable; use `refundability` and `description` |
