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

# Affiliate Attribution Extension

**Version:** `2026-01-11`

## Overview

The Affiliate Attribution extension enables agents to transmit fraud-resistant
attribution claims for crediting third-party publishers (affiliates) without
relying on cookies, redirects, or client-side tracking.

In traditional web commerce, attribution is inferred via links, cookies,
redirects, and pixels. In **agentic commerce**, the agent often performs
discovery and comparison and may complete the purchase without a conventional
"click trail," breaking classic attribution primitives.

**Key features:**

- Token-first design for fraud-resistant validation
- Provider-agnostic (supports any affiliate network)
- Write-only semantics (not returned in responses)
- Complete-only (submitted at final checkout step)
- "Last touch wins" attribution model

**Dependencies:**

- Checkout Capability

## Discovery

Businesses advertise affiliate attribution support in their profile:

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

## Schema

When this capability is active, checkout is extended with an
`affiliate_attribution` object.

### Affiliate Attribution Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `provider` | string | Yes | Attribution provider namespace (e.g., `impact.com`) |
| `token` | string | Conditional | Opaque provider-issued token. Required if `publisher_id` omitted |
| `publisher_id` | string | Conditional | Provider-scoped affiliate ID. Required if `token` omitted |
| `campaign_id` | string | No | Provider-scoped campaign identifier |
| `creative_id` | string | No | Provider-scoped creative/ad unit identifier |
| `sub_id` | string | No | Publisher-defined sub-tracking identifier |
| `source` | string | No | How attribution was captured (see below) |
| `issued_at` | date-time | No | When the token/claim was issued |
| `expires_at` | date-time | No | When the claim expires |
| `metadata` | object | No | Provider-specific metadata (no PII allowed) |

### Attribution Source

The `source` field indicates how the attribution was captured:

| Value | Description |
|-------|-------------|
| `click` | User clicked an affiliate link |
| `impression` | Attribution based on ad/content impression |
| `api` | Attribution passed programmatically via API |
| `agent_recommendation` | Agent recommended the merchant/product |
| `comparison_result` | Attribution from a comparison or discovery flow |

## Semantics

### Write-Only

The `affiliate_attribution` field is **write-only**:

- Accepted on checkout create and update operations
- **Never returned** in GET responses, list endpoints, or webhook payloads
- Treated as sensitive commercial data

### Token-First Design

A provider-issued opaque token is the preferred attribution method:

- Merchants validate tokens **out-of-band** with the attribution provider
- Similar to how payment tokens are validated via PSPs
- No single network's API is baked into UCP

When tokens aren't available, `publisher_id` provides a fallback identifier.

### Idempotency

Attribution follows standard complete request idempotency:

| Scenario | Behavior |
|----------|----------|
| Same `Idempotency-Key` + identical payload | Success (idempotent replay) |
| Same `Idempotency-Key` + different payload | `409 Conflict` |

Since attribution is submitted only at completion, there's no risk of
conflicting attributions across multiple requests—the complete operation
is inherently single-shot.

### Checkout Success Independent of Attribution

Checkout operations **MUST succeed** regardless of whether the server:

- Supports the affiliate attribution capability
- Successfully processes or validates the attribution
- Encounters validation errors in the attribution data

Attribution is supplementary—it should never block a purchase.

## Privacy Requirements

Attribution data has strict privacy constraints:

**MUST NOT contain:**

- User PII (emails, phone numbers, addresses)
- Stable user identifiers
- Device fingerprints

**SHOULD:**

- Treat tokens as secrets (do not log in plaintext)
- Validate `metadata` does not contain obvious PII

Servers **SHOULD** return `400 Bad Request` with code `pii_not_allowed` if
the payload contains obvious PII.

## Ranking Independence

Agents **MUST NOT** use `affiliate_attribution` as a ranking boost mechanism.
Attribution is strictly for post-selection crediting and settlement—it must not
influence which merchants or products are recommended to users.

## Operations

Attribution is submitted at checkout completion—the final step when the order
is placed. This aligns with "last touch wins" attribution semantics used by
most affiliate networks.

**Request behavior:**

- **Optional field**: Attribution can be omitted entirely
- **Complete-only**: Submitted with the complete checkout request
- **No echo**: Not returned in responses

**Supported endpoint:**

- `POST /checkout-sessions/{id}/complete` — Submit attribution at order placement

> **Rationale:** Submitting attribution at completion (rather than create/update)
> simplifies the implementation—servers don't need to track attribution state
> across session updates. It also ensures attribution reflects the final
> purchase decision.

## Provider Validation

UCP does not specify how merchants validate attribution with providers. Common
patterns include:

1. **Token validation API**: Merchant calls provider's API to verify token
2. **Webhook confirmation**: Provider confirms attribution via callback
3. **Batch reconciliation**: Periodic bulk validation of recorded attributions

Commission rates, payout schedules, and settlement rails are explicitly
out-of-scope—these are handled between merchant and provider.

## Examples

### Token-based attribution

The recommended approach using a provider-issued token at checkout completion:

**Complete Request:**

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

**Response:**

```json
{
  "id": "cs_abc123",
  "status": "complete",
  "order": {...}
}
```

Note: `affiliate_attribution` is not echoed in the response.

### Publisher ID fallback

When tokens aren't available, use explicit identifiers:

**Complete Request:**

```json
{
  "payment_data": {...},
  "affiliate_attribution": {
    "provider": "cj.com",
    "publisher_id": "pub_12345",
    "campaign_id": "summer_2026",
    "creative_id": "banner_300x250",
    "sub_id": "homepage_slot_1",
    "source": "click"
  }
}
```

### Attribution with metadata

Provider-specific fields via the metadata object:

**Complete Request:**

```json
{
  "payment_data": {...},
  "affiliate_attribution": {
    "provider": "rakuten.com",
    "token": "rak_token_xyz",
    "source": "comparison_result",
    "metadata": {
      "comparison_category": "electronics",
      "position": 3,
      "total_compared": 10
    }
  }
}
```

### Unsupported provider (graceful handling)

Servers should accept unknown providers for forward compatibility:

**Complete Request:**

```json
{
  "payment_data": {...},
  "affiliate_attribution": {
    "provider": "new-network.io",
    "publisher_id": "aff_999"
  }
}
```

The server accepts this even if it doesn't have an integration with
`new-network.io`. The merchant can decide later whether to honor the attribution.
