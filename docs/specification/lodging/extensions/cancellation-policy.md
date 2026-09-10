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
[`policies[]`](../../overview/index.md#policies) primitive for the lodging service. It
adds pre-purchase, machine-readable cancellation terms to policies that
carry this type, so platforms can answer questions like "Can I cancel this booking?",
"Is it free cancellation or is there a fee?", and "Is this rate completely
non-refundable?" without leaving to parse external policy pages.

**Key features:**

- Tri-state refundability classification (`refundability`) to signal whether
  cancellation is currently free (`refundable`), incurs a penalty
  (`partially_refundable`), or is disallowed (`non_refundable`)
- Human-readable summary in `description` carrying detailed property cutoff
  times, timezone deadlines, and penalty schedules
- Optional direct link to the property's complete legal terms (`url`)

**Dependencies:**

- The core `policies[]` primitive (see [Policies](../../overview/index.md#policies)).
- Any parent capabilities this type extends: Booking
  (`dev.ucp.lodging.booking`).

## Discovery

Businesses advertise cancellation policy support in their profile. The type
extends any surface that carries `policies[]`:

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
`dev.ucp.lodging.policy.cancellation` carries additional attributes
(e.g., `refundability`) in addition to the base `type`,
`description`, `applies_to`, and `url`.

{{ extension_schema_fields('policy_cancellation.json#/$defs/cancellation_item', 'lodging/extensions/cancellation-policy') }}

## Cancellation terms

### Refundability classifications

The `refundability` field provides a standardized high-level classification:

- **`refundable`**: Free cancellation is currently available. The booker can
  cancel without penalty before the deadline stated in `description`.
- **`partially_refundable`**: The booking can be cancelled, but a cancellation
  fee applies (e.g., a one-night room charge or fixed administrative fee), or
  the booking is currently inside a partial penalty window. Specific cancellation
  fees, penalty schedules, and refund effects are outlined in the policy's
  `description` field.
- **`non_refundable`**: The reservation cannot be refunded upon cancellation
  (the full booking price is retained by the business, subject to local regulation).

### Non-refundable bookings

To signal that a booking or rate is non-refundable, a business **MUST** set
`refundability` to `"non_refundable"`.

When a business requires the booker to be shown that a booking is non-refundable
prior to confirmation, it emits a `messages[]` warning with
`presentation: "disclosure"` and `code` equal to
`dev.ucp.lodging.policy.cancellation`, targeting the item. The disclosure pairs
with the governing cancellation policy at that node, as defined in
[Presenting policies](../../overview/index.md#presenting-policies).

### Human-readable descriptions

Because lodging cancellation rules frequently incorporate specific property
local cutoff times (e.g., "by 3:00 PM property time 2 days before check-in")
and seasonal rules, businesses **MUST** articulate the full timeline and terms in
`description`. The `description` and `refundability` field **MUST NOT** contradict
each other.

## Targeting and precedence

Targeting and precedence are provided by the `policies[]` primitive and are not
redefined here. In short: a policy with no `applies_to` is the response-wide
default; a policy that targets specific room overrides will result in the
narrowest same-type target winning. See
[Targeting](../../overview/index.md#targeting) and
[Precedence](../../overview/index.md#precedence).

For lodging bookings, a common example is when a business states a single default cancellation
policy once, then adds targeted overrides only for specific exceptions (such as
a non-refundable room rate or promotional upgrade).

## Responsibilities

Cancellation policies are business-stated facts. They are response-only data
that a platform never submits. They carry no user-asserted claims and no PII.

A business **SHOULD** accurately summarize cancellation timelines, applicable
penalties and cutoff deadlines in `description` and link to full policy terms
via `url`. A platform **SHOULD** surface `url` alongside the policy description
so the booker can review full dynamic property policies.

## Examples

<!-- ucp:example schema=lodging/booking target=$.policies -->
```json
[
  {
    "type": "dev.ucp.lodging.policy.cancellation",
    "description": {
      "plain": "Free cancellation until Dec 20, 2026, 3:00 PM EDT (48 hours before check-in). 1 night penalty thereafter."
    },
    "refundability": "refundable",
    "url": "https://example.com/cancellation-terms"
  },
  {
    "type": "dev.ucp.lodging.policy.cancellation",
    "description": {
      "plain": "Non-refundable promotional rate. This room reservation cannot be cancelled or modified for a refund."
    },
    "applies_to": ["$.room_rates[0]"],
    "refundability": "non_refundable",
    "url": "https://example.com/cancellation-terms#non-refundable"
  }
]
```
