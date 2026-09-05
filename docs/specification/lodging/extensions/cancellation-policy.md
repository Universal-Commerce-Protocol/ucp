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

## Cancellation terms

### Refundability classification

`refundability` provides a standardized current high-level classification:

- **`refundable`**: cancellation without penalty is currently available.
- **`partially_refundable`**: cancellation is available but a penalty currently
  applies.
- **`non_refundable`**: no refund is currently available upon cancellation,
  subject to applicable law.

Platforms **MUST** tolerate unknown classification values and use `description`
when they cannot interpret the value.

`schedule` does not replace this classification. When both are present, the
Business **MUST** set `refundability` to the outcome applicable when it creates
the response: a full refund is `refundable`, a partial, fixed-fee, or unit
deduction outcome is `partially_refundable`, and no refund is
`non_refundable`.

### Deterministic schedule

`schedule` is optional. Its absence means that structured timeline evaluation
is unavailable; it does not mean that the booking is non-refundable. When
present, `anchor`, a non-empty `tiers` array, and `after_last_tier` form one
atomic value.

#### Representation

`anchor` is an RFC 3339 instant and **MUST** include `Z` or a numeric UTC
offset. The offset identifies the instant; it does not declare a recurring
property timezone. For lodging, the anchor normally represents the stated
arrival or check-in cutoff.

Each tier's `until` is an ISO 8601 elapsed duration before `anchor`. This version
supports days, hours, minutes, and seconds only. A day is exactly 24 elapsed
hours. Calendar months, calendar years, local-calendar days, and business days
are not supported.

A Business **MUST** order `tiers` from the farthest cutoff before `anchor` to
the nearest cutoff. Durations **MUST** be strictly decreasing and **MUST NOT**
repeat. An invalid order makes structured evaluation unavailable.

#### Evaluation

For a tier, its cutoff is the `anchor` instant minus its `until` elapsed
duration. Given an evaluation instant `at`, a Platform evaluates tiers in array
order and selects the first tier for which `at` is strictly earlier than the
cutoff. If no tier matches, `after_last_tier` applies.

The cutoff belongs to the following interval. At exactly `anchor - until`, that
tier no longer applies. Neither party rounds, shifts, or reinterprets `at`, the
anchor, or a computed cutoff.

For example, with an anchor of `2026-12-22T15:00:00-05:00` and `until` of
`PT48H`, the cutoff is `2026-12-20T20:00:00Z`. An evaluation at
`2026-12-20T19:59:59Z` selects the tier; an evaluation at
`2026-12-20T20:00:00Z` advances to the following interval.

#### Outcome vocabulary

`kind` is an open string discriminator. This specification defines these
well-known values:

- **`percentage`** requires `buyer_bps`, an integer from 0 through 10000. It is
  the share of the policy-scoped amount returned to the Buyer, in basis points.
- **`fixed_fee`** requires `seller_keeps.amount`, expressed as an integer in the
  Booking currency's minor unit. Currency is inherited from the Booking and is
  not repeated in the outcome.
- **`unit_deduction`** requires a positive integer `seller_keeps.quantity` and
  an open `seller_keeps.unit` value. `night` is the well-known lodging unit.

A unit deduction is a deterministic symbolic outcome, but it does not imply a
cash amount. A Platform **MUST NOT** calculate money unless the targeted Booking
data supplies an unambiguous price basis.

A Platform that encounters an unsupported `kind` **MUST** preserve it, **MUST
NOT** claim a deterministic outcome it cannot interpret, and **SHOULD** present
`description`.

### Non-refundable bookings

To signal that a booking or rate is currently non-refundable, a Business
**MUST** set `refundability` to `"non_refundable"`.

When the Booker must acknowledge this condition before confirmation, the
Business emits a `messages[]` warning with `presentation: "disclosure"` and a
`code` of `dev.ucp.lodging.policy.cancellation`, targeting the affected item.
See [Presenting policies](../../overview/index.md#presenting-policies).

### Human-readable terms and fallback

`description` remains the universal human-readable and legal fallback. A
Business **MUST NOT** emit a structured schedule that contradicts
`description`. Detecting contradictions does not require a Platform to parse
legal prose. If a contradiction is independently known, the schedule is
invalid, ordered-tier constraints are violated, or a selected outcome is
unsupported, the Platform **MUST NOT** present a guessed structured result and
**SHOULD** present `description` and `url`.

## Targeting and precedence

Targeting and precedence are supplied by `policies[]` and are not redefined
here. A policy without `applies_to` is the response-wide default. A policy that
targets a room rate overrides a less-specific policy of the same type. See
[Targeting](../../overview/index.md#targeting) and
[Precedence](../../overview/index.md#precedence).

## Responsibilities

### Business

Cancellation policies are Business-stated response-only facts. A Business
**MUST** emit a valid ordered schedule, keep `refundability`, `schedule`, and
`description` consistent, and preserve the complete legal summary in
`description`. It **SHOULD** link the full terms with `url`.

### Platform

A Platform supplies the evaluation instant, applies the exact elapsed-time and
boundary rules above, and respects policy targeting before evaluation. It
**MUST NOT** turn a symbolic unit deduction into money without an unambiguous
basis, infer a result from an unsupported outcome, or execute cancellation or
refund behavior solely from this pre-purchase policy.

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
      "seller_keeps": {
        "quantity": 1,
        "unit": "night"
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

## Normative evaluation vectors

The following compact vectors define selection behavior. `tier[n]` uses
zero-based array indexing. An expected outcome is the selected wire outcome,
not a cancellation or refund instruction.

| ID | Schedule and evaluation instant | Expected result |
| --- | --- | --- |
| `before_cutoff` | Example schedule above; `at = 2026-12-20T19:59:59Z` | `tier[0]`; `percentage`, `buyer_bps = 10000` |
| `exact_cutoff` | Example schedule above; `at = 2026-12-20T20:00:00Z` | `after_last_tier`; `unit_deduction`, one `night` |
| `after_cutoff` | Example schedule above; `at = 2026-12-20T20:00:01Z` | `after_last_tier`; `unit_deduction`, one `night` |
| `middle_tier` | `anchor = 2026-12-31T12:00:00Z`; tiers `P7D -> buyer_bps 10000`, `PT48H -> buyer_bps 5000`; `at = 2026-12-24T12:00:00Z` | `tier[1]`; `percentage`, `buyer_bps = 5000` |
| `last_cutoff` | Same two-tier schedule; `at = 2026-12-29T12:00:00Z`; after-last `buyer_bps = 0` | `after_last_tier`; `percentage`, `buyer_bps = 0` |
| `fixed_fee` | `anchor = 2027-01-10T12:00:00Z`; tier `PT24H -> buyer_bps 10000`; `at = 2027-01-09T12:00:00Z`; after-last fixed fee amount `7500` | `after_last_tier`; `fixed_fee`, seller keeps `7500` minor units |
| `elapsed_day_dst` | `anchor = 2026-03-09T02:30:00-04:00`; tier `P1D -> buyer_bps 10000`; `at = 2026-03-08T06:29:59Z` | Computed cutoff is `2026-03-08T06:30:00Z`; select `tier[0]` |
| `unsupported_kind` | Selected outcome has `kind = com.example.voucher`; otherwise valid schedule | Preserve the value; structured outcome unavailable; fall back to `description` |
| `schedule_absent` | Policy has no `schedule` | Timeline evaluation unavailable; use `refundability` and `description` |
