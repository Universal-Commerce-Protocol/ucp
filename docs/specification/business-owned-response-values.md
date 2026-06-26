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

# Business-Owned Response Values

## Overview

UCP response objects may include values supplied by the business from its own
user state, not only values previously supplied by the platform. When a request
is associated with an authenticated user through
[Identity Linking](identity-linking.md), a business can populate existing
checkout, cart, buyer, payment, and fulfillment fields with display-safe values
that it already knows for that user.

This pattern avoids creating a separate extension for every kind of saved user
state. For example, a business can return a user's saved payment methods in the
existing `payment.instruments[]` array on cart or checkout responses. The
platform can render those instruments for selection using the same payment
instrument shape it already understands.

## Common Cases

Business-owned response values are useful for:

* **Saved payment instruments:** A business returns display-safe saved cards or
    wallet accounts in `payment.instruments[]`.
* **Buyer profile data:** A business pre-populates `buyer` fields from the
    authenticated user's account.
* **Saved fulfillment information:** A business returns transaction-eligible
    fulfillment options or addresses where the capability allows it.

The business remains responsible for authorization, ownership checks, data
minimization, and only returning values appropriate for the current user and
transaction.

## Saved Payment Instruments

Saved payment instruments should use the existing `payment.instruments[]`
surface. A saved instrument is represented as a normal payment instrument with
an opaque business-scoped `id`, a `handler_id`, a `type`, and display-safe
metadata under `display`.

The response should not include raw payment credentials unless the active
payment handler explicitly requires credential material on that surface. For
business-vaulted saved instruments, the `id` is the reference the business can
resolve server-side when the buyer selects that instrument for checkout.

The base UCP schema does not currently standardize a generic "saved" or
"default" flag. A business can indicate the recommended choice by setting
`selected: true` when the instrument is selected for the current transaction,
and can use handler-specific display fields for richer UI labels. A broader
generic reference/tokenized-node abstraction may standardize more metadata in
the future.

## Sample Checkout Response

In this example, the platform created a checkout with a user-identity bearer
token. The business recognizes the user and returns a saved Shop Pay instrument
in the existing `payment.instruments[]` array. The instrument carries no raw
credential; it is a display-safe business-owned reference.

```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.checkout": [
        {
          "version": "{{ ucp_version }}"
        }
      ],
      "dev.ucp.common.identity_linking": [
        {
          "version": "{{ ucp_version }}"
        }
      ]
    },
    "payment_handlers": {
      "com.shopify.shop_pay": [
        {
          "id": "shop_pay_1234",
          "version": "{{ ucp_version }}",
          "available_instruments": [
            {
              "type": "shop_pay"
            }
          ]
        }
      ]
    }
  },
  "id": "checkout_123",
  "status": "ready_for_complete",
  "currency": "USD",
  "line_items": [
    {
      "id": "line_item_1",
      "item": {
        "id": "prod_1",
        "title": "T-Shirt",
        "price": 2000
      },
      "quantity": 1,
      "totals": [
        {
          "type": "subtotal",
          "amount": 2000
        }
      ]
    }
  ],
  "totals": [
    {
      "type": "subtotal",
      "amount": 2000
    },
    {
      "type": "tax",
      "amount": 160
    },
    {
      "type": "total",
      "amount": 2160
    }
  ],
  "payment": {
    "instruments": [
      {
        "id": "saved_shop_pay_4242",
        "handler_id": "shop_pay_1234",
        "type": "shop_pay",
        "selected": true,
        "display": {
          "description": "Saved Shop Pay account",
          "email": "buyer@example.com",
          "last_digits": "4242"
        }
      }
    ]
  }
}
```

If the buyer chooses this instrument, the platform can submit the selected
instrument by `id` in the next checkout update or completion request. The
business verifies ownership against the authenticated user and resolves the
reference through its own vault or payment handler integration.

## Guidance

* Businesses MUST only return business-owned values that belong to the
    authenticated user and are appropriate for the current transaction.
* Platforms MUST treat returned business-owned identifiers as opaque and scoped
    to that business.
* Platforms SHOULD render only display-safe fields and MUST NOT infer raw
    credentials from a display value.
* Businesses SHOULD omit business-owned user state when the request lacks the
    required user authorization.
* Empty arrays are meaningful: they indicate the business checked the relevant
    state and found no transaction-eligible values. Omitted fields indicate the
    business did not expose that state on the response.
