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

# Saved Payment Instruments Extension

## Overview

The Saved Payment Instruments extension surfaces the set of payment
instruments the authenticated user has previously saved with a business
on cart and checkout responses. It lets platforms — especially AI
agents — recognize and present "your saved methods" without requiring
the user to re-enter payment information for every transaction.

Without this extension, the only way for a platform to know what is
saved is to inspect what the business pre-populates in
`payment.instruments[]` on a cart or checkout. That conflates "available
for this transaction" with "saved for this user" and offers no way to
mark which instrument is the user's default.

Core use cases:

* **Recognition:** "Use your saved Visa ending in 4242?" surfaced as the
    default suggestion when the user opens a cart.
* **Selection:** Render the full saved set ("Visa ****4242 (default),
    Mastercard ****5454") so the user picks rather than re-enters.
* **Expiration awareness:** Surface "your saved card expires next month"
    inline with cart/checkout.

A standalone capability that allows enumeration and management of saved
instruments **outside any cart/checkout context** (pre-cart enumeration,
set-default, delete) is intentionally deferred — see
[Open Questions](#open-questions).

## Key Concepts

**Identity-gated.** The extension activates only with a user-identity
bearer token obtained via the
[Identity Linking Capability](identity-linking.md). Businesses MUST list
the scope `dev.ucp.shopping.saved_instruments:read` under
`dev.ucp.common.identity_linking.config.scopes`. Without that scope the
extension MUST be omitted from responses.

**Response-only.** The extension is decorated with `ucp_request: omit`
on every extended capability — `saved_instruments` flows merchant →
platform only. Platforms MUST NOT send the field in cart/checkout
requests; doing so has no defined effect.

**Display-only on the wire.** Saved instruments carry **no credential
material**. The schema explicitly forbids a `credential` field
(`"credential": { "not": {} }`). To use a saved instrument at checkout
time, the platform sets `payment.instruments[].id` to the saved
instrument's `id`; the business resolves it against its internal vault
and mints a checkout-bound `TokenCredential` per its declared payment
handler. See the [Tokenization Guide](tokenization-guide.md).

**Business-scoped IDs.** A `saved_instrument.id` is meaningful only to
the issuing business; cross-merchant portability is out of scope.

**Why not identity linking?** Identity linking authenticates *who the
user is*; it does not enumerate per-business state. Saved instruments
have their own lifecycle (additions, expirations, deletions) and their
own consent dimension, so they belong in a payments-domain surface gated
by an identity-linking-declared scope. This mirrors the pattern
established by [`dev.ucp.common.loyalty`](loyalty.md).

## Discovery

Businesses advertise the extension by adding it to their UCP profile and
listing the read scope under identity linking:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp target=$.ucp -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.identity_linking": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/identity-linking",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/identity_linking.json",
          "config": {
            "scopes": {
              "dev.ucp.shopping.saved_instruments:read": {
                "description": "View payment instruments you've saved with this business."
              }
            }
          }
        }
      ],
      "dev.ucp.shopping.cart": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/cart",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/cart.json"
        }
      ],
      "dev.ucp.shopping.checkout": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/checkout",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/checkout.json"
        }
      ],
      "dev.ucp.shopping.saved_instruments": [
        {
          "version": "{{ ucp_version }}",
          "extends": [
            "dev.ucp.shopping.cart",
            "dev.ucp.shopping.checkout"
          ],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/saved-instruments",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/saved_instruments.json"
        }
      ]
    }
  }
}
```

**Dependencies:**

* [Identity Linking Capability](identity-linking.md) — required for user
    authentication and scope declaration.
* [Cart Capability](cart.md) and/or [Checkout Capability](checkout.md) —
    at least one MUST be advertised; the extension decorates these.

## Schema

### Entities

#### Saved Instrument

{{ extension_schema_fields('saved_instruments.json#/$defs/saved_instrument', 'saved_instruments') }}

#### Saved Instruments

{{ extension_schema_fields('saved_instruments.json#/$defs/saved_instruments', 'saved_instruments') }}

## Behavior

### Activation

The extension activates only when the cart or checkout request carries a
valid user-identity bearer token that includes the
`dev.ucp.shopping.saved_instruments:read` scope. When activated, the
business MUST populate `payment.saved_instruments` with the set of
instruments owned by the authenticated user.

When the scope is absent or the bearer is missing, the business MUST
omit the `payment.saved_instruments` field. An empty array (`[]`) is
reserved for "scope granted, user has no saved instruments" — distinct
from "extension not active."

### Default instrument

At most one entry in `payment.saved_instruments` MAY have `default: true`.
If no entry is marked default, the business has no recorded default
preference for this user; platforms SHOULD prompt the user to pick
rather than infer a default from list ordering.

The default flag is informational on this surface — it is not a
selection. To use the default instrument at checkout, the platform
copies its `id` into `payment.instruments[]` like any other selection.

### Relationship with `payment.instruments[]`

`payment.instruments[]` and `payment.saved_instruments` answer different
questions:

| Field                         | Question answered                                                       |
| :---------------------------- | :---------------------------------------------------------------------- |
| `payment.instruments[]`       | What instruments are eligible (or selected) for *this* cart/checkout?   |
| `payment.saved_instruments`   | What instruments has *this user* saved with this business overall?      |

The two sets MAY overlap (a saved instrument is eligible for this
checkout) or diverge (a saved card is below the cart total minimum, or a
business pre-fills a guest instrument the user has not saved). Platforms
SHOULD reconcile by `id` — the same identifier appears in both when an
instrument is both saved and eligible.

### Credential is forbidden on this surface

The schema sets `"credential": { "not": {} }` on saved instruments to
make the contract explicit: this extension never carries credential
material. Businesses MUST resolve a selected `saved_instrument.id` to a
usable credential at checkout time, through their declared payment
handler — typically by minting a checkout-bound `TokenCredential` per
the [Tokenization Guide](tokenization-guide.md).

## Use Cases and Examples

### Listing saved instruments on cart creation

The platform creates a cart with a user-identity bearer token that
carries the `:read` scope. The business returns the cart plus the
user's saved set under `payment.saved_instruments`.

=== "Request"

    <!-- ucp:example schema=shopping/cart op=create direction=request -->
    ```json
    {
      "line_items": [
        { "item": { "id": "prod_1" }, "quantity": 1 }
      ]
    }
    ```

=== "Response"

    ```json
    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.shopping.cart": [{"version": "{{ ucp_version }}"}],
          "dev.ucp.shopping.saved_instruments": [{"version": "{{ ucp_version }}"}]
        }
      },
      "id": "cart_abc",
      "currency": "USD",
      "line_items": [
        {
          "id": "li_1",
          "item": { "id": "prod_1", "title": "T-Shirt", "price": 2000 },
          "quantity": 1,
          "totals": [
            {"type": "subtotal", "amount": 2000},
            {"type": "total", "amount": 2000}
          ]
        }
      ],
      "totals": [
        {"type": "subtotal", "amount": 2000},
        {"type": "total", "amount": 2000}
      ],
      "payment": {
        "saved_instruments": [
          {
            "id": "msi_01H8YN...",
            "handler_id": "merchant_vault",
            "type": "card",
            "default": true,
            "display": {
              "brand": "visa",
              "last_digits": "4242",
              "expiry_month": 11,
              "expiry_year": 2027
            }
          },
          {
            "id": "msi_01H8YP...",
            "handler_id": "merchant_vault",
            "type": "card",
            "display": {
              "brand": "mastercard",
              "last_digits": "5454",
              "expiry_month": 4,
              "expiry_year": 2026
            }
          }
        ]
      }
    }
    ```

### Using a saved instrument at checkout

To use the default Visa, the platform sets
`payment.instruments[0].id` to the saved instrument's `id`. The business
resolves it against its vault and continues the standard checkout flow.

```json
{
  "payment": {
    "instruments": [
      {
        "id": "msi_01H8YN...",
        "handler_id": "merchant_vault",
        "type": "card",
        "selected": true
      }
    ]
  }
}
```

## Implementation Guidelines

* `saved_instrument.id` values MUST be opaque (not derived from
    credential data), stable across sessions, and meaningful only to the
    issuing business.
* Businesses MUST scope the returned set to instruments owned by the
    authenticated user. The set MUST NOT include other users'
    instruments under any circumstance.
* Platforms SHOULD NOT cache the saved set across sessions without
    re-fetching on each cart/checkout that surfaces it — the saved set
    is mutable (expirations, deletions, additions).
* Saved-instrument responses MUST NOT carry a `credential` field. The
    schema enforces this with `"credential": { "not": {} }`;
    implementations should additionally reject any in-flight credential
    on this surface as a defense-in-depth measure.

## Out of Scope

* **Adding a new saved instrument.** Saving occurs via the business's
    existing UX (typically opt-in at checkout completion) or via the
    business's site. This extension does not define a write path.
* **Updating a saved instrument** (e.g., billing address). Out of scope
    for v1.
* **Cross-merchant credential portability.** Using a card saved at
    Merchant A on Merchant B requires a platform-vault model that is
    distinct from merchant-side enumeration.
* **Raw PAN handling.** Saved instruments never carry raw credentials;
    PCI scope stays inside the business's vault.
