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

# Intent Trace Extension

**Version:** `2026-01-11`

## Overview

The Intent Trace extension enables agents to transmit structured data about why
a checkout session was abandoned when calling the cancel endpoint.

In the base specification, cancellation is a terminal action with no structured
context. Merchants receive a `status: canceled` session but no signal about the
user's objection. This forces reliance on probabilistic retargeting—buying ad
impressions without knowing why the user left.

**Key features:**

- Structured reason codes based on cart abandonment research
- Optional human-readable summary
- Extensible metadata for additional context
- Write-only semantics (not returned in responses)
- Backward compatible (fully optional)

**Dependencies:**

- Checkout Capability

## Discovery

Businesses advertise intent trace support in their profile:

```json
{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": [
      {
        "name": "dev.ucp.shopping.intent_trace",
        "version": "2026-01-11",
        "extends": "dev.ucp.shopping.checkout",
        "spec": "https://ucp.dev/specification/intent-trace",
        "schema": "https://ucp.dev/schemas/shopping/intent_trace.json"
      }
    ]
  }
}
```

## Schema

When this capability is active, the cancel endpoint accepts an optional
`intent_trace` object in the request body.

### Intent Trace Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reason_code` | string | Yes | Structured reason for cancellation (see below) |
| `trace_summary` | string | No | Human-readable summary (max 500 chars) |
| `metadata` | object | No | Flat key-value pairs for additional context |

### Reason Codes

Reason codes are based on [Baymard Institute cart abandonment research](https://baymard.com/lists/cart-abandonment-rate):

| Code | Description |
|------|-------------|
| `price_sensitivity` | Total price was too high or exceeded budget |
| `shipping_cost` | Shipping fees were unacceptable |
| `shipping_speed` | Delivery timeframe did not meet requirements |
| `product_fit` | Product specs, size, or features did not match needs |
| `trust_security` | Concerns about merchant trustworthiness or payment security |
| `returns_policy` | Return/refund policy was unsatisfactory |
| `payment_options` | Preferred payment method was not available |
| `comparison` | User chose to purchase from a different merchant |
| `timing_deferred` | User intends to complete purchase later |
| `other` | Reason does not fit other categories |

**Forward compatibility:** Servers SHOULD accept unrecognized `reason_code`
values and treat them as `other`. This allows the enum to expand without
breaking existing implementations.

### Metadata Object

The `metadata` field accepts a flat key-value object for additional context:

- Keys must be strings
- Values must be strings, numbers, or booleans
- Arrays and nested objects are NOT permitted
- Monetary values SHOULD be integers in minor currency units

## Semantics

### Write-Only

The `intent_trace` field is **write-only**:

- Accepted on the cancel endpoint
- **Never returned** in GET responses or webhooks
- Treated as operational data for merchant use

### Optional and Backward Compatible

The `intent_trace` is optional to maintain backward compatibility:

- Agents that do not support this extension omit the request body
- Servers that do not implement it ignore the body
- Cancellation proceeds normally in both cases

### Cancellation Always Succeeds

Cancellation **MUST succeed** regardless of whether the server:

- Supports the intent trace capability
- Successfully processes or validates the trace
- Encounters validation errors in the trace data

Servers SHOULD return `400 Bad Request` only for structurally malformed data
(wrong types, nested objects in metadata). Unknown `reason_code` values are
NOT errors.

### Idempotency

Requests with `intent_trace` MUST be idempotent:

- Repeated calls with the same `Idempotency-Key` MUST NOT duplicate the trace
- Standard UCP idempotency semantics apply

## Privacy Considerations

Unlike cookie-based retargeting, Intent Traces are:

- **Explicit:** Transmitted only when the user chooses to cancel
- **Scoped:** Sent only to the merchant involved in the session
- **Minimal:** Structured codes over free-text to reduce PII leakage

Agents SHOULD NOT transmit PII in the `trace_summary` field unless explicitly
authorized by the user. Examples of what to avoid:

- Email addresses or phone numbers
- Full names or addresses
- Account identifiers from other services

## Operations

Intent traces are submitted when canceling a checkout session.

**Supported endpoint:**

- `POST /checkout-sessions/{id}/cancel` — Cancel with optional intent trace

**Request behavior:**

- **Optional body**: Request body can be omitted entirely
- **Write-only**: Trace is not returned in the response
- **Idempotent**: Safe to retry with same `Idempotency-Key`

## Use Cases

### Merchant Response to Objections

A merchant receiving structured cancellation data can respond programmatically:

| Reason Code | Potential Response |
|-------------|-------------------|
| `shipping_cost` | Offer free shipping promotion |
| `shipping_speed` | Highlight express shipping options |
| `price_sensitivity` | Send discount code via email |
| `payment_options` | Expand payment method support |
| `returns_policy` | Clarify or improve returns policy |

### Analytics and Optimization

Aggregate intent traces reveal patterns:

- Which objections are most common for specific products?
- Do certain price points trigger `price_sensitivity` more often?
- Are `trust_security` concerns higher for new merchants?

## Examples

### Basic cancellation with reason

**Cancel Request:**

```json
POST /checkout-sessions/cs_abc123/cancel

{
  "intent_trace": {
    "reason_code": "shipping_cost"
  }
}
```

**Response:**

```json
{
  "id": "cs_abc123",
  "status": "canceled"
}
```

Note: `intent_trace` is not echoed in the response.

### Detailed trace with summary

**Cancel Request:**

```json
{
  "intent_trace": {
    "reason_code": "price_sensitivity",
    "trace_summary": "Total exceeded $100 budget for office supplies"
  }
}
```

### Trace with metadata

**Cancel Request:**

```json
{
  "intent_trace": {
    "reason_code": "comparison",
    "trace_summary": "Found same product cheaper elsewhere",
    "metadata": {
      "price_difference_cents": 1500,
      "competitor_category": "marketplace"
    }
  }
}
```

### Deferred purchase

**Cancel Request:**

```json
{
  "intent_trace": {
    "reason_code": "timing_deferred",
    "trace_summary": "Waiting for payday",
    "metadata": {
      "intent_to_return": true,
      "estimated_days": 14
    }
  }
}
```

### Cancellation without trace (backward compatible)

Agents that don't support intent traces simply omit the body:

**Cancel Request:**

```
POST /checkout-sessions/cs_abc123/cancel
```

No request body. The cancel succeeds as before.
