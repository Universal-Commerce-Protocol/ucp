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

## 1. Overview

The Buyer Consent extension enables Agents to transmit buyer consent choices to
Merchants regarding data usage and communication preferences. It allows buyers
to communicate their consent status for various categories, such as analytics,
marketing, and data sales, helping Merchants comply with privacy regulations
like CCPA and GDPR.

When this extension is supported, the `buyer` object in checkout is extended
with a `consent` field containing boolean consent states.

This extension can be included in `create_checkout` and `update_checkout`
operations.

## 2. Discovery

Merchants advertise consent support in their profile:

```json
{
  "capabilities": [
    {
      "name": "dev.ucp.shopping.buyer_consent",
      "version": "2026-01-11",
      "extends": "dev.ucp.shopping.checkout"
    }
  ]
}
```

## 3. Schema Composition

The consent extension extends the **buyer object** within checkout:

- **Base schema extended**: `checkout` via `buyer` object
- **Path**: `checkout.buyer.consent`
- **Schema reference**: `buyer_consent.json`

## 4. Schema Definition

### Consent Object

{{ extension_schema_fields('buyer_consent.json#/$defs/consent', 'buyer-consent') }}

## 5. Usage

The Agent includes consent within the `buyer` object in checkout operations:

### Example: Create Checkout with Consent

```json
POST /checkouts

{
  "line_items": [
    {
      "item": {
        "id": "prod_123",
        "quantity": 1,
        "title": "Blue T-Shirt",
        "price": 1999
      }
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
  "id": "gid://merchant.com/Checkout/checkout_456",
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

## 6. Security & Privacy Considerations

1. **Consent is declarative** - The protocol communicates consent, it does not enforce it
2. **Legal compliance** remains the merchant's responsibility
3. **Agents should not** assume consent without explicit user action
4. **Default behavior** when consent is not provided is merchant-specific
5. **Consent states** should align with actual user choices, not agent defaults
