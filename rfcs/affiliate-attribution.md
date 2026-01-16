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

# Enhancement Proposal: Affiliate Attribution Extension

| Status | Provisional |
|--------|-------------|
| Author | @0xtotaylor |
| Created | 2026-01-11 |
| Last Updated | 2026-01-12 |

## Summary

This proposal extends the `POST /checkout-sessions/{id}/complete` endpoint to
accept an optional `affiliate_attribution` object, enabling agents to transmit
fraud-resistant attribution claims for crediting third-party publishers
(affiliates) without relying on cookies, redirects, or client-side tracking.

## Motivation

Affiliate marketing is a core distribution channel for e-commerce. In
traditional web flows, attribution is inferred via links, cookies, redirects,
and pixels. In **agentic commerce**, the agent often performs discovery and
comparison and may complete the purchase without a conventional "click trail,"
breaking classic attribution primitives.

### Why structured attribution?

Without a standardized attribution signal:

- Merchants cannot reliably credit publishers who influenced the purchase.
- Affiliates are disincentivized to create high-quality commerce content.
- The ecosystem devolves into opaque, platform-controlled deals rather than
  open, interoperable referral economics.

A structured `affiliate_attribution` object enables deterministic,
fraud-resistant attribution transport from agent to merchant at checkout time.

### Why token-first?

A **provider-issued, opaque token** is the simplest way to support fraud
resistance without baking any single network's API into UCP. Merchants can
validate tokens out-of-band with the provider they trust, similar to how
payment tokens are validated via PSPs.

### Why write-only?

Attribution often contains commercially sensitive data (publisher IDs, campaign
identifiers, token secrets). The safest default is that it is **write-only**:
accepted and stored by the merchant but not echoed back in responses or exposed
in any read endpoint.

### Why complete-only?

Submitting attribution at completion (rather than create/update) provides two
benefits:

1. **Simplicity**: Servers don't need to track attribution state across session
   updates.
2. **Last-touch semantics**: Aligns with how most affiliate networks operate
   today, where the final action before purchase determines attribution.

## Detailed Design

### Endpoint Updated

The following endpoint accepts an optional `affiliate_attribution` object in
its request body:

- `POST /checkout-sessions/{id}/complete` — Complete Session

### New Schemas

#### AffiliateAttributionSource

```yaml
AffiliateAttributionSource:
  type: string
  enum:
    - click
    - impression
    - api
    - agent_recommendation
    - comparison_result
  description: Indicates how the attribution was captured.
```

#### AffiliateAttributionMetadata

```yaml
AffiliateAttributionMetadata:
  type: object
  additionalProperties: true
  description: Provider-specific metadata. Extensible for network-specific fields.
```

#### AffiliateAttribution

```yaml
AffiliateAttribution:
  type: object
  required: [provider]
  anyOf:
    - required: [token]
    - required: [publisher_id]
  properties:
    provider:
      type: string
      description: Attribution provider namespace (e.g., 'impact.com').
    token:
      type: string
      description: Opaque provider-issued token for fraud-resistant validation.
    publisher_id:
      type: string
      description: Provider-scoped affiliate identifier. Required if token is omitted.
    campaign_id:
      type: string
    creative_id:
      type: string
    sub_id:
      type: string
    source:
      $ref: "#/components/schemas/AffiliateAttributionSource"
    issued_at:
      type: string
      format: date-time
    expires_at:
      type: string
      format: date-time
    metadata:
      $ref: "#/components/schemas/AffiliateAttributionMetadata"
```

### Semantics (Normative)

1. **Write-only**: The `affiliate_attribution` field MUST NOT be returned in
   `GET /checkout-sessions/{id}` responses, list endpoints, or webhook payloads.

2. **Checkout success independent of attribution**: Checkout MUST succeed
   regardless of whether the server supports or successfully processes the
   attribution.

3. **Idempotency**: Standard UCP idempotency semantics apply:
   - Same `Idempotency-Key` + identical payload → success (idempotent replay)
   - Same `Idempotency-Key` + different payload → `409 Conflict`

4. **Forward compatibility**: Servers SHOULD accept unknown `provider` values
   to support future networks without protocol changes.

5. **PII rejection**: Servers SHOULD return `400 Bad Request` with code
   `pii_not_allowed` for payloads containing obvious PII.

### Privacy Considerations

- Attribution MUST NOT contain user PII (emails, phone numbers, addresses,
  stable user identifiers, device fingerprints).
- Tokens SHOULD be treated as secrets and not logged in plaintext.
- Agents MUST NOT treat `affiliate_attribution` as a ranking boost mechanism—it
  is strictly for post-selection attribution/settlement.

### Discovery

Merchants advertise support via their discovery profile:

```json
{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": [
      {
        "name": "dev.ucp.shopping.affiliate_attribution",
        "version": "2026-01-11",
        "extends": "dev.ucp.shopping.checkout",
        "spec": "https://ucp.dev/specification/affiliate-attribution",
        "schema": "https://ucp.dev/schemas/shopping/affiliate_attribution.json"
      }
    ]
  }
}
```

### Example Request

```json
POST /checkout-sessions/cs_abc123/complete

{
  "payment_data": {
    "instrument_id": "pi_xyz",
    "credential": {...}
  },
  "affiliate_attribution": {
    "provider": "impact.com",
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "source": "agent_recommendation",
    "issued_at": "2026-01-11T10:30:00Z",
    "expires_at": "2026-01-11T11:30:00Z"
  }
}
```

## Risks

### Adoption Risk

Merchants may not implement the extension if affiliate networks don't adopt
UCP-compatible token issuance. Mitigation: The `publisher_id` fallback allows
attribution without network integration.

### Fraud Risk

Without token validation, attribution claims could be forged. Mitigation:
Token-first design encourages cryptographic validation; merchants control their
risk tolerance.

### Privacy Risk

Metadata fields could leak sensitive information. Mitigation: Schema explicitly
prohibits PII; servers SHOULD reject obvious violations.

### Complexity Risk

Adding attribution to checkout increases implementation burden. Mitigation:
Extension is fully optional; checkout succeeds regardless of attribution
support.

## Test Plan

### Schema Validation

- [ ] `affiliate_attribution.json` passes JSON Schema validation
- [ ] Generated schemas compile without errors
- [ ] OpenAPI spec validates successfully

### Conformance Tests

- [ ] Complete request with valid token succeeds
- [ ] Complete request with valid publisher_id (no token) succeeds
- [ ] Complete request missing both token and publisher_id returns 400
- [ ] Complete request missing provider returns 400
- [ ] Attribution is not echoed in response
- [ ] Attribution is not returned in GET /checkout-sessions/{id}
- [ ] Unknown provider values are accepted (forward compatibility)
- [ ] Checkout succeeds even if server doesn't support extension

### Integration Tests

- [ ] End-to-end flow with mock affiliate provider
- [ ] Token validation callback (out-of-band)
- [ ] Idempotency behavior with attribution

## Graduation Criteria

### Alpha (Current)

- Schema defined and documented
- Reference implementation in at least one platform
- Basic conformance tests passing

**Exit Criteria**: TC approval of design, 1+ platform implementing

### Beta

- At least 2 platforms implementing the extension
- At least 1 affiliate network issuing UCP-compatible tokens
- Conformance test suite complete
- Documentation reviewed by TC

**Exit Criteria**: 90-day stability period with no breaking changes

### General Availability (GA)

- At least 3 platforms in production
- At least 2 affiliate networks supporting UCP tokens
- Full test coverage
- Performance benchmarks documented

**Exit Criteria**: TC vote for GA status, no outstanding blocking issues

## Files Changed

| File | Description |
|------|-------------|
| `rfcs/affiliate-attribution.md` | This enhancement proposal |
| `source/schemas/shopping/affiliate_attribution.json` | Extension schema |
| `docs/specification/affiliate-attribution.md` | Specification documentation |
| `mkdocs.yml` | Navigation updates |

## References

- [Baymard Institute: Cart Abandonment Statistics](https://baymard.com/lists/cart-abandonment-rate)
- [Impact.com API Documentation](https://developer.impact.com/)
- [UCP Governance: Enhancement Proposals](https://github.com/Universal-Commerce-Protocol/ucp/blob/main/GOVERNANCE.md#enhancement-proposals)

## Changelog

| Date | Change |
|------|--------|
| 2026-01-11 | Initial proposal |
| 2026-01-12 | Simplified to complete-only per reviewer feedback |
