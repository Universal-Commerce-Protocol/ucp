# Buyer Consent Extension

## Overview

The Buyer Consent extension enables platforms to transmit buyer consent choices to businesses regarding data usage and communication preferences. It allows buyers to communicate their consent status for various categories, such as analytics, marketing, and data sales, helping businesses comply with privacy regulations like CCPA and GDPR.

When this extension is supported, the `buyer` object in checkout is extended with a `consent` field containing boolean consent states.

This extension can be included in `create_checkout` and `update_checkout` operations.

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

| Name         | Type    | Required | Description                                       |
| ------------ | ------- | -------- | ------------------------------------------------- |
| analytics    | boolean | No       | Consent for analytics and performance tracking.   |
| preferences  | boolean | No       | Consent for storing user preferences.             |
| marketing    | boolean | No       | Consent for marketing communications.             |
| sale_of_data | boolean | No       | Consent for selling data to third parties (CCPA). |

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
1. **Legal compliance** remains the business's responsibility
1. **Platforms should not** assume consent without explicit user action
1. **Default behavior** when consent is not provided is business-specific
