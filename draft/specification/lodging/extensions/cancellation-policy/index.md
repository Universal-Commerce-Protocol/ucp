# Cancellation Policy Extension

## Overview

The Cancellation Policy Extension defines the `dev.ucp.lodging.policy.cancellation` policy type on the core [`policies[]`](http://ucp.dev/draft/specification/overview/#policies) primitive for the lodging service. It adds pre-purchase, machine-readable cancellation terms to policies that carry this type, so platforms can answer questions like "Can I cancel this booking?", "Is it free cancellation or is there a fee?", and "Is this rate completely non-refundable?" without leaving to parse external policy pages.

**Key features:**

- Tri-state refundability classification (`refundability`) to signal whether cancellation is currently free (`refundable`), incurs a penalty (`partially_refundable`), or is disallowed (`non_refundable`)
- Human-readable summary in `description` carrying detailed property cutoff times, timezone deadlines, and penalty schedules
- Optional direct link to the property's complete legal terms (`url`)

**Dependencies:**

- The core `policies[]` primitive (see [Policies](http://ucp.dev/draft/specification/overview/#policies)).
- Any parent capabilities this type extends: Booking (`dev.ucp.lodging.booking`).

## Discovery

Businesses advertise cancellation policy support in their profile. The type extends any surface that carries `policies[]`:

```json
{
  "ucp": {
    "version": "draft",
    "capabilities": {
      "dev.ucp.lodging.policy.cancellation": [
        {
          "version": "draft",
          "extends": [
            "dev.ucp.lodging.booking"
          ],
          "spec": "https://ucp.dev/draft/specification/lodging/extensions/cancellation-policy",
          "schema": "https://ucp.dev/draft/schemas/lodging/policy_cancellation.json"
        }
      ]
    }
  }
}
```

## Schema

When this type is active, a `policies[]` entry whose `type` is `dev.ucp.lodging.policy.cancellation` carries additional attributes (e.g., `refundability`) in addition to the base `type`, `description`, `applies_to`, and `url`.

| Name          | Type                                                                       | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------------- | -------------------------------------------------------------------------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type          | [Reverse Domain Name](/draft/specification/reference/#reverse-domain-name) | **Required** | **Constant = dev.ucp.lodging.policy.cancellation**. Policy discriminator for lodging cancellation terms. Policy type discriminator. Open reverse-DNS vocabulary. See specification documentation for the registry of well-known policy types. Businesses MAY define custom types in their own domain (e.g., `com.example.policy.price_match`). Platforms MUST tolerate unknown values.                                                                                                                                                                                                                                                                                             |
| description   | [Description](/draft/specification/reference/#description)                 | **Required** | Human-readable policy summary in one or more formats (plain, markdown, html). Required on every policy so a platform can present it without understanding any type-specific fields. This is not the buyer-facing disclosure — display is compelled by a `messages[]` warning (see the Policies section).                                                                                                                                                                                                                                                                                                                                                                           |
| applies_to    | Array[string]                                                              | Optional     | RFC 9535 JSONPath expressions identifying the nodes this policy applies to, relative to the embedding response root (e.g., `$.line_items[0]` in cart/checkout, `$.products[2]` in catalog). Each target covers the node it names and everything nested under it, so a target on a product also covers its variants. A singular query (RFC 9535 Section 2.3.5.1; name and index selectors only) names a single node; filters, wildcards, and slices match a set. When omitted, the policy applies to the entire response. When policies of the same `type` contest a node, the narrowest target wins and overrides the rest. See the Policies section for how specificity resolves. |
| url           | string                                                                     | Optional     | Optional link to the full policy document.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| refundability | string                                                                     | **Required** | High-level refundability classification. Well-known values: `refundable` (free cancellation currently available), `partially_refundable` (cancellable with penalty, or inside penalty window), `non_refundable` (no refund upon cancellation).                                                                                                                                                                                                                                                                                                                                                                                                                                     |

## Cancellation terms

### Refundability classifications

The `refundability` field provides a standardized high-level classification:

- **`refundable`**: Free cancellation is currently available. The booker can cancel without penalty before the deadline stated in `description`.
- **`partially_refundable`**: The booking can be cancelled, but a cancellation fee applies (e.g., a one-night room charge or fixed administrative fee), or the booking is currently inside a partial penalty window. Specific cancellation fees, penalty schedules, and refund effects are outlined in the policy's `description` field.
- **`non_refundable`**: The reservation cannot be refunded upon cancellation (the full booking price is retained by the business, subject to local regulation).

### Non-refundable bookings

To signal that a booking or rate is non-refundable, a business **MUST** set `refundability` to `"non_refundable"`.

When a business requires the booker to be shown that a booking is non-refundable prior to confirmation, it emits a `messages[]` warning with `presentation: "disclosure"` and `code` equal to `dev.ucp.lodging.policy.cancellation`, targeting the item. The disclosure pairs with the governing cancellation policy at that node, as defined in [Presenting policies](http://ucp.dev/draft/specification/overview/#presenting-policies).

### Human-readable descriptions

Because lodging cancellation rules frequently incorporate specific property local cutoff times (e.g., "by 3:00 PM property time 2 days before check-in") and seasonal rules, businesses **MUST** articulate the full timeline and terms in `description`. The `description` and `refundability` field **MUST NOT** contradict each other.

## Targeting and precedence

Targeting and precedence are provided by the `policies[]` primitive and are not redefined here. In short: a policy with no `applies_to` is the response-wide default; a policy that targets specific room overrides will result in the narrowest same-type target winning. See [Targeting](http://ucp.dev/draft/specification/overview/#targeting) and [Precedence](http://ucp.dev/draft/specification/overview/#precedence).

For lodging bookings, a common example is when a business states a single default cancellation policy once, then adds targeted overrides only for specific exceptions (such as a non-refundable room rate or promotional upgrade).

## Responsibilities

Cancellation policies are business-stated facts. They are response-only data that a platform never submits. They carry no user-asserted claims and no PII.

A business **SHOULD** accurately summarize cancellation timelines, applicable penalties and cutoff deadlines in `description` and link to full policy terms via `url`. A platform **SHOULD** surface `url` alongside the policy description so the booker can review full dynamic property policies.

## Examples

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
    "applies_to": ["$.stays[0]"],
    "refundability": "non_refundable",
    "url": "https://example.com/cancellation-terms#non-refundable"
  }
]
```
