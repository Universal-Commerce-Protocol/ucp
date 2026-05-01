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

# Marketing Consent Extension

## Overview

The Marketing Consent extension enables per-channel marketing consent capture
during checkout. It supports two flows:

1. **Platform collected consent**: The platform has already collected the
   buyer's marketing preferences and sends them to the business during
   checkout creation or update.
2. **Business-requested consent**: The business declares available marketing
   channels in the checkout response. The platform collects the buyer's
   consent and submits it at checkout completion.

**Key features:**

- Per-channel consent (`email`, `sms`)
- Business-declared consent options with display text and privacy policy URLs
- Omission of consent preserves current subscription state

**Dependencies:**

- Checkout Capability

## Discovery

Businesses advertise marketing consent support in their profile:

```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.marketing_consent": [
        {
          "version": "{{ ucp_version }}",
          "extends": "dev.ucp.shopping.checkout",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/marketing-consent",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/marketing_consent.json"
        }
      ]
    }
  }
}
```

## Schema Composition

The marketing consent extension extends the **buyer object** within checkout:

- **Base schema extended**: `checkout` via `buyer` object
- **Path**: `checkout.buyer.marketing_consent`
- **Schema reference**: `marketing_consent.json`

## Schema Definition

### Marketing Consent

{{ extension_schema_fields('marketing_consent.json#/$defs/marketing_consent', 'marketing-consent') }}

### Marketing Consent Option

{{ extension_schema_fields('marketing_consent.json#/$defs/marketing_consent_option', 'marketing-consent') }}

### Marketing Consent Entry

{{ extension_schema_fields('marketing_consent.json#/$defs/marketing_consent_entry', 'marketing-consent') }}

## Flows

### Flow 1: Platform Collected Consent

The platform has already collected the buyer's marketing preferences (e.g.,
through its own consent UI). It includes `marketing_consent.consents` in the
checkout create or update request.

=== "Request"

    ```json
    POST /checkout-sessions

    {
      "line_items": [
        {
          "item": {
            "id": "prod_123",
            "title": "Blue T-Shirt",
            "price": 1999
          },
          "id": "li_1",
          "quantity": 1
        }
      ],
      "buyer": {
        "email": "jane.doe@example.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "marketing_consent": {
          "consents": [
            { "channel": "email", "opted_in": true },
            { "channel": "sms", "opted_in": false }
          ]
        }
      }
    }
    ```

=== "Response"

    ```json
    {
      "id": "checkout_456",
      "status": "ready_for_complete",
      "currency": "USD",
      "buyer": {
        "email": "jane.doe@example.com",
        "first_name": "Jane",
        "last_name": "Doe"
      },
      "line_items": [...],
      "totals": [...]
    }
    ```

### Flow 2: Business-Requested Consent

The business declares available marketing channels in the checkout response.
The platform collects the buyer's consent and submits it at checkout
completion.

**Phase 1 — Declare:** Business includes `marketing_consent.options` in the
checkout response.

**Phase 2 — Render:** Platform displays consent UI based on the options.

**Phase 3 — Capture:** Platform includes `marketing_consent.consents` in
the complete request.

=== "Create Response"

    ```json
    {
      "id": "checkout_789",
      "status": "ready_for_complete",
      "currency": "USD",
      "buyer": {
        "email": "jane.doe@example.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "marketing_consent": {
          "options": [
            {
              "channel": "email",
              "display_text": "Promotional emails and exclusive offers",
              "privacy_policy_url": "https://example.com/privacy"
            },
            {
              "channel": "sms",
              "display_text": "Order updates and deals via text",
              "privacy_policy_url": "https://example.com/privacy"
            }
          ]
        }
      },
      "line_items": [...],
      "totals": [...],
      "links": [
        {
          "type": "privacy_policy",
          "url": "https://example.com/privacy"
        }
      ]
    }
    ```

=== "Update Response"

    The business MAY also include `marketing_consent.options` in update
    responses:

    ```json
    {
      "id": "checkout_789",
      "status": "ready_for_complete",
      "currency": "USD",
      "buyer": {
        "email": "jane.doe@example.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "marketing_consent": {
          "options": [
            {
              "channel": "email",
              "display_text": "Promotional emails and exclusive offers",
              "privacy_policy_url": "https://example.com/privacy"
            },
            {
              "channel": "sms",
              "display_text": "Order updates and deals via text",
              "privacy_policy_url": "https://example.com/privacy"
            }
          ]
        }
      },
      "line_items": [...],
      "totals": [...]
    }
    ```

=== "Complete Request"

    ```json
    POST /checkout-sessions/checkout_789/complete

    {
      "buyer": {
        "marketing_consent": {
          "consents": [
            { "channel": "email", "opted_in": true },
            { "channel": "sms", "opted_in": false }
          ]
        }
      },
      "payment": {
        "handler": "dev.ucp.payments.example",
        "details": {
          "token": "tok_abc123"
        }
      }
    }
    ```

## Channel Semantics

The `channel` field is a closed enum. Supported values are `email` and `sms`.
New channels may be added in future spec versions as additive, non-breaking
changes.

**Contact resolution:**

| Channel | Contact Source |
| ------- | ------------- |
| `email` | `buyer.email` |
| `sms` | `buyer.phone_number` |

If no contact can be resolved for a channel, the business MUST ignore consent
for that channel.

## Relationship to Buyer Consent Extension

The [Buyer Consent Extension](buyer-consent.md) includes a `marketing`
boolean on `buyer.consent`. The Marketing Consent Extension provides a richer,
per-channel model:

- `buyer.consent.marketing` — simple boolean for general marketing consent
- `buyer.marketing_consent` — per-channel consent with display text and
  privacy policy URLs

Both extensions are independent. A business MAY advertise either or both in
their capability profile. When a business advertises
`dev.ucp.shopping.marketing_consent`, platforms MUST use
`buyer.marketing_consent.consents` for marketing consent and MUST ignore
`buyer.consent.marketing`. The Marketing Consent Extension supersedes the
`marketing` boolean in the Buyer Consent Extension.

## Security & Privacy Considerations

1. **Consent is declarative** — the protocol communicates consent, it does not
   enforce it
2. **Omission preserves state** — businesses MUST NOT treat omission of
   `marketing_consent.consents` as new consent
3. **Legal compliance** remains the business's responsibility
4. **Businesses MUST ignore** consent entries for channels not offered in
   `marketing_consent.options`
5. **Platforms MUST NOT** send `opted_in` values for consent options that were
   not displayed to the buyer
6. **Privacy policy URLs** SHOULD be displayed to buyers before consent
   collection
7. **Regulatory support** — provides a clear audit trail for GDPR, CAN-SPAM,
   and CCPA compliance
