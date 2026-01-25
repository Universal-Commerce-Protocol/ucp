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

**Version:** `2026-01-11`

## Overview

The Buyer Consent extension enables platforms to transmit buyer consent choices
to businesses regarding data usage and communication preferences. It allows
buyers to communicate their consent status for various categories, such as
analytics, marketing, and data sales, helping businesses comply with privacy
regulations like CCPA and GDPR.

When this extension is supported, the `buyer` object in checkout is extended
with a `consent` field containing boolean consent states.

This extension can be included in `create_checkout` and `update_checkout`
operations.

## Discovery

Businesses advertise consent support in their profile:

```json
{
  "capabilities": {
    "dev.ucp.shopping.buyer_consent": [
      {
        "version": "2026-01-11",
        "extends": "dev.ucp.shopping.checkout"
      }
    ]
  }
}
```

## Schema Composition

The consent extension extends the **buyer object** within checkout:

- **Base schema extended**: `checkout` via `buyer` object
- **Path**: `checkout.buyer.consent`
- **Schema reference**: `buyer_consent.json`

## Schema Definition

### Consent Object

{{ extension_schema_fields('buyer_consent_resp.json#/$defs/consent', 'buyer-consent') }}

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
      "marketing": false,
      "sale_of_data": false
    }
  }
}
```

### Example: Checkout Response with Consent

```json
{
  "id": "checkout_456",
  "status": "ready_for_payment",
  "currency": "USD",
  "buyer": {
    "email": "jane.doe@example.com",
    "first_name": "Jane",
    "last_name": "Doe",
    "consent": {
      "analytics": true,
      "preferences": true,
      "marketing": false,
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

## Security & Privacy Considerations

1. **Consent is declarative** - The protocol communicates consent, it does not enforce it
2. **Legal compliance** remains the business's responsibility
3. **Platforms should not** assume consent without explicit user action
4. **Default behavior** when consent is not provided is business-specific
5. **Consent states** should align with actual user choices, not platform defaults
