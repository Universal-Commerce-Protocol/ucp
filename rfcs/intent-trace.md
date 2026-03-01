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

# Enhancement Proposal: Intent Trace Extension

| Status | Provisional |
|--------|-------------|
| Author | @0xtotaylor |
| Created | 2026-01-11 |
| Last Updated | 2026-01-21 |

## Summary

This proposal extends the `POST /checkout-sessions/{id}/cancel` endpoint to
accept an optional `intent_trace` object, enabling agents to transmit structured
data about why a checkout session was abandoned.

## Motivation

In the current specification, cancellation is a terminal action with no
structured context. Merchants receive a `status: canceled` session, but no
signal about the user's objection. This forces reliance on probabilistic
retargeting—buying ad impressions without knowing why the user left.

### Why structured cancellation context?

When an agent manages checkout, abandonment is often a reasoned decision based
on specific constraints (price, shipping speed, trust concerns). Capturing this
decision as an **Intent Trace** converts abandonment from a dead end into an
actionable signal.

A merchant receiving `reason_code: shipping_cost` can programmatically respond
with a free shipping offer rather than guessing. This creates value for:

- **Merchants**: Actionable insights for conversion optimization
- **Users**: More relevant follow-up offers
- **Ecosystem**: Structured data instead of opaque retargeting

### Why optional?

The `intent_trace` is optional to maintain backward compatibility:

- Agents that do not support this extension omit the request body
- Servers that do not implement it ignore the body
- Cancellation proceeds as before in both cases

### Why write-only?

Intent traces may contain commercially sensitive signals about user objections.
The safest default is **write-only**: accepted and stored by the merchant but
not echoed back in responses or exposed in any read endpoint.

## Detailed Design

### Endpoint Updated

The following endpoint accepts an optional request body with `intent_trace`:

- `POST /checkout-sessions/{id}/cancel` — Cancel Session

### New Schemas

#### ReasonCode

```yaml
ReasonCode:
  type: string
  enum:
    - price_sensitivity
    - shipping_cost
    - shipping_speed
    - product_fit
    - trust_security
    - returns_policy
    - payment_options
    - comparison
    - timing_deferred
    - other
  description: >
    Structured reason for cancellation. Servers SHOULD accept unrecognized
    values and treat them as "other" for forward compatibility.
```

Reason codes are grounded in [Baymard Institute cart abandonment research](https://baymard.com/lists/cart-abandonment-rate).

#### IntentTraceMetadata

```yaml
IntentTraceMetadata:
  type: object
  additionalProperties:
    oneOf:
      - type: string
      - type: number
      - type: boolean
  description: >
    Flat key-value object for additional context. Arrays and nested objects
    are NOT permitted. Monetary values SHOULD be integers in minor currency
    units.
```

#### IntentTrace

```yaml
IntentTrace:
  type: object
  required: [reason_code]
  properties:
    reason_code:
      $ref: "#/components/schemas/ReasonCode"
    trace_summary:
      type: string
      maxLength: 500
      description: Human-readable summary of the objection.
    metadata:
      $ref: "#/components/schemas/IntentTraceMetadata"
```

### Semantics (Normative)

1. **Write-only**: The `intent_trace` field MUST NOT be returned in
   `GET /checkout-sessions/{id}` responses or webhook payloads.

2. **Cancellation success independent of trace**: Cancellation MUST succeed
   regardless of whether the server supports or successfully processes the
   `intent_trace`.

3. **Forward compatibility**: Servers SHOULD accept unrecognized `reason_code`
   values and treat them as `other`. Unknown codes are NOT errors.

4. **Structural validation only**: Servers SHOULD return `400 Bad Request` only
   for structurally malformed data (wrong types, nested objects in `metadata`).

5. **Idempotency**: Requests with `intent_trace` MUST be idempotent. Repeated
   calls with the same `Idempotency-Key` MUST NOT duplicate the trace record.

### Privacy Considerations

Unlike cookie-based retargeting, Intent Traces are:

- **Explicit**: Transmitted only when the user chooses to cancel
- **Scoped**: Sent only to the merchant involved in the session
- **Minimal**: Structured codes over free-text to reduce PII leakage

Agents SHOULD NOT transmit PII in the `trace_summary` field unless explicitly
authorized by the user.

### Discovery

Merchants advertise support via their discovery profile:

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

### Example Requests

**Basic cancellation with reason:**

```json
POST /checkout-sessions/cs_abc123/cancel

{
  "intent_trace": {
    "reason_code": "shipping_cost"
  }
}
```

**Detailed trace with metadata:**

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

**Backward compatible (no body):**

```
POST /checkout-sessions/cs_abc123/cancel
```

No request body. Cancellation succeeds as before.

## Risks

### Adoption Risk

Merchants may not implement the extension if the ROI of structured abandonment
data is unclear. Mitigation: Document use cases (retargeting optimization,
A/B testing checkout flows) to demonstrate value.

### Privacy Risk

`trace_summary` free-text could leak PII. Mitigation: Documentation explicitly
discourages PII; schema limits to 500 characters; structured `reason_code` is
preferred.

### Gaming Risk

Agents could submit false reason codes to manipulate merchant behavior.
Mitigation: Merchants control how they act on traces; bad actors gain little
from false signals.

### Complexity Risk

Adding optional request body to cancel increases implementation burden.
Mitigation: Extension is fully optional; cancel succeeds regardless of support.

## Test Plan

### Schema Validation

- [ ] `intent_trace.json` passes JSON Schema validation
- [ ] Generated schemas compile without errors
- [ ] OpenAPI spec validates successfully

### Conformance Tests

- [ ] Cancel request with valid intent_trace succeeds
- [ ] Cancel request with empty body succeeds (backward compatibility)
- [ ] Cancel request missing reason_code returns 400
- [ ] Intent trace is not echoed in response
- [ ] Intent trace is not returned in GET /checkout-sessions/{id}
- [ ] Unknown reason_code values are accepted (forward compatibility)
- [ ] Nested objects in metadata return 400
- [ ] Cancel succeeds even if server doesn't support extension

### Integration Tests

- [ ] End-to-end cancel flow with intent trace
- [ ] Idempotency behavior with intent trace
- [ ] Merchant analytics pipeline receives trace data

## Graduation Criteria

### Alpha (Current)

- Schema defined and documented
- Reference implementation in at least one platform
- Basic conformance tests passing

**Exit Criteria**: TC approval of design, 1+ platform implementing

### Beta

- At least 2 platforms implementing the extension
- Merchant feedback on reason code taxonomy
- Conformance test suite complete
- Documentation reviewed by TC

**Exit Criteria**: 90-day stability period with no breaking changes

### General Availability (GA)

- At least 3 platforms in production
- Demonstrated merchant value (case studies)
- Full test coverage
- Reason code taxonomy validated against real abandonment data

**Exit Criteria**: TC vote for GA status, no outstanding blocking issues

## Implementation Plan

Per governance, this proposal does not include implementation changes. If advanced to Implementable, a follow-up PR will add schemas, transport bindings, and documentation.

## Files Changed

| File | Description |
|------|-------------|
| `rfcs/intent-trace.md` | This enhancement proposal |

## References

- [Baymard Institute: Cart Abandonment Statistics](https://baymard.com/lists/cart-abandonment-rate)
- [UCP Governance: Enhancement Proposals](https://github.com/Universal-Commerce-Protocol/ucp/blob/main/GOVERNANCE.md#enhancement-proposals)

## Changelog

| Date | Change |
|------|--------|
| 2026-01-11 | Initial proposal |
| 2026-01-12 | Added Enhancement Proposal format per governance requirements |
| 2026-01-21 | Proposal-only update pending TC approval |
