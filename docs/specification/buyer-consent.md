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

# Buyer Consent Extension

## Overview

The Buyer Consent extension enables platforms to transmit buyer consent choices
to businesses regarding data usage and communication preferences. It allows
buyers to communicate their consent status for various categories, such as
analytics, marketing, and data sales, helping businesses comply with privacy
regulations like CCPA and GDPR.

When this extension is supported, the `buyer` object in checkout is extended
with a `consent` field containing boolean consent states. Additionally,
businesses can declare available marketing channels via
`marketing_consent_options` on the checkout response, enabling per-channel
marketing consent capture at checkout completion.

This extension can be included in `create_checkout`, `update_checkout`, and
`complete_checkout` operations.

## Discovery

Businesses advertise consent support in their profile:

```json
{
  "capabilities": {
    "dev.ucp.shopping.buyer_consent": [
      {
        "version": "{{ ucp_version }}",
        "extends": "dev.ucp.shopping.checkout"
      }
    ]
  }
}
```

## Schema Composition

The consent extension extends checkout in two ways:

- **Buyer object**: `checkout.buyer.consent` — boolean consent states and
  per-channel marketing consent
- **Checkout level**: `checkout.marketing_consent_options` — business-declared
  marketing channels available for opt-in
- **Schema reference**: `buyer_consent.json`

## Schema Definition

### Consent Object

{{ extension_schema_fields('buyer_consent.json#/$defs/consent', 'buyer-consent') }}

### Marketing Consent Option

{{ extension_schema_fields('buyer_consent.json#/$defs/marketing_consent_option', 'buyer-consent') }}

### Marketing Channel Consent

{{ extension_schema_fields('buyer_consent.json#/$defs/marketing_channel_consent', 'buyer-consent') }}

## Usage

The platform includes consent within the `buyer` object in checkout operations:

### Example: Create Checkout with Consent

```json
POST /checkouts

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
    "consent": {
      "analytics": true,
      "preferences": true,
      "sale_of_data": false
    }
  }
}
```

### Example: Checkout Response with Consent

```json
{
  "id": "checkout_456",
  "status": "ready_for_complete",
  "currency": "USD",
  "buyer": {
    "email": "jane.doe@example.com",
    "first_name": "Jane",
    "last_name": "Doe",
    "consent": {
      "analytics": true,
      "preferences": true,
      "sale_of_data": false
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

## Marketing Consent

### Overview

The marketing consent flow enables per-channel marketing consent capture
during checkout. Email and SMS consent are legally distinct — CAN-SPAM treats
email as opt-out while the TCPA requires prior express written consent for
SMS. Per-channel consent addresses this regulatory divergence.

The flow has three phases:

| Phase | Actor | Action |
| ------- | ------- | -------- |
| **Declare** | Business | Includes `marketing_consent_options` on the checkout response. |
| **Render** | Platform | Displays consent UI based on the options. |
| **Capture** | Platform | Includes `buyer.consent.marketing_channels` on the complete request. |

### Marketing Consent Options

Businesses declare available marketing channels by including
`marketing_consent_options` in the checkout response. This is a top-level
checkout field, not part of the buyer object — it describes what the business
offers, not buyer state.

Businesses SHOULD include `marketing_consent_options` in `create` and `update`
checkout responses only. Options included in `complete` responses are ignored
by the platform, as consent has already been collected.

Businesses SHOULD NOT include options for channels where the buyer is already
subscribed. This keeps the protocol stateless and eliminates ambiguity about
whether declining a pre-existing subscription constitutes revocation.

### Marketing Channels

The buyer's consent decisions are submitted via
`buyer.consent.marketing_channels` on the `complete_checkout` request. This
array contains one entry per channel the platform surfaced to the buyer.

Platforms MUST NOT send entries for channels that were not displayed to the
buyer. Omission of `marketing_channels` preserves current subscription state.

### Channel Semantics

The `channel` field is a closed enum. Supported values are `email`, `sms`,
and `whatsapp`. New channels may be added in future spec versions as
additive, non-breaking changes.

**Contact resolution:**

| Channel | Contact Source |
| --------- | --------------- |
| `email` | `buyer.email` |
| `sms` | `buyer.phone_number` |
| `whatsapp` | `buyer.phone_number` |

If no contact can be resolved for a channel, the business MUST ignore consent
for that channel.

### Example: Marketing Consent Flow

=== "Create Response"

    The business declares available marketing channels in the checkout
    response:

    ```json
    {
      "id": "checkout_789",
      "status": "ready_for_complete",
      "currency": "USD",
      "buyer": {
        "email": "jane.doe@example.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "consent": {
          "analytics": true,
          "preferences": true,
          "sale_of_data": false
        }
      },
      "marketing_consent_options": [
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
      ],
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

=== "Complete Request"

    The platform submits the buyer's consent decisions at checkout completion:

    ```json
    POST /checkout-sessions/checkout_789/complete

    {
      "buyer": {
        "consent": {
          "marketing_channels": [
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

### Deprecation: `marketing` Boolean

The `marketing` boolean on the consent object is deprecated. Use
`marketing_channels` for per-channel consent. When `marketing_channels` is
present, `marketing` SHOULD be ignored.

When the business includes `marketing_consent_options` in the checkout
response, the platform MUST NOT use `marketing` and MUST use
`marketing_channels` to submit the buyer's consent decisions.

Existing implementations that only send the `marketing` boolean continue to
work. New implementations should adopt `marketing_channels`.

## Security & Privacy Considerations

1. **Consent is declarative** - The protocol communicates consent, it does not
   enforce it
2. **Legal compliance** remains the business's responsibility
3. **Platforms should not** assume consent without explicit user action
4. **Default behavior** when consent is not provided is business-specific
5. **Omission preserves state** — businesses MUST NOT treat omission of
   `marketing_channels` as new consent
6. **Businesses MUST ignore** consent entries for channels not offered in
   `marketing_consent_options`
7. **Platforms MUST NOT** send `opted_in` values for consent options that were
   not displayed to the buyer
