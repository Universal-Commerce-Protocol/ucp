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

# Seller Disclosure Extension

## Overview

A buyer needs to know who sells an item before buying it. On a single-merchant
store the seller is the Business. On a marketplace each line item can come from
a different third-party seller, and that seller can be a professional trader or
a private individual. Many jurisdictions require the marketplace to tell the
buyer which one it is and how to reach the seller.

This extension carries those facts as data:

- **Catalog**: the `seller` object on a [variant](../catalog/index.md) gains
    the seller disclosure fields, so a platform can show the seller and its
    trader status next to an offer.
- **Cart, checkout and order**: a response-only `seller_disclosures` map lists
    each seller in the session and the line items it sells. The order carries
    the disclosures as they were presented at checkout.

The Business is the source of truth for every value. The Business collects the
data from its sellers and decides which disclosures apply to a session. The
platform renders the values as given and **MUST NOT** infer, change or omit a
seller's trader status.

For example, in the EU these fields serve the marketplace duties in Directive
2011/83/EU Art. 6a (trader status and the non-trader notice) and Art. 6(1)(b)-(d)
(trader identity and contact details), and the information that Regulation (EU)
2022/2065 Art. 30(7) requires a platform to show (name, address, telephone and
email, trade register entry, and the trader's self-certification). Other
jurisdictions can use the same fields.

## Discovery

Businesses advertise seller disclosure support in their profile. The extension
can extend cart, checkout and order:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.seller_disclosure": [
        {
          "version": "{{ ucp_version }}",
          "extends": [
            "dev.ucp.shopping.cart",
            "dev.ucp.shopping.checkout",
            "dev.ucp.shopping.order"
          ],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/extensions/seller-disclosure",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/seller_disclosure.json"
        }
      ]
    }
  }
}
```

The catalog fields live on the core variant `seller` object and need no
negotiation. A platform that has not negotiated this extension ignores
`seller_disclosures` on cart, checkout and order.

## Schema

### Seller Disclosure

The shared shape used on catalog variants and in every `seller_disclosures`
entry. All fields are optional.

{{ schema_fields('shopping/types/seller_disclosure', 'shopping/extensions/seller-disclosure') }}

### Contact

{{ extension_schema_fields('types/seller_disclosure.json#/$defs/contact', 'shopping/extensions/seller-disclosure') }}

### Registration

{{ extension_schema_fields('types/seller_disclosure.json#/$defs/registration', 'shopping/extensions/seller-disclosure') }}

### Seller Disclosure Entry

An entry in the cart, checkout or order `seller_disclosures` map. It adds a
display `name`, optional `links`, and the `line_item_ids` the seller sells.

{{ extension_schema_fields('seller_disclosure.json#/$defs/seller_entry', 'shopping/extensions/seller-disclosure') }}

## Trader status

`trader_status` records what the seller declared to the Business. It is not a
legal assessment by the Business or the platform.

| Value          | Meaning                                                       |
| -------------- | ------------------------------------------------------------- |
| `trader`       | The seller declared that it sells in a professional capacity. |
| `non_trader`   | The seller declared that it sells as a private individual.    |
| `not_declared` | The seller has not made a declaration.                        |

A Business that sells its own goods sends `trader`. `trader_status` is an open
string; a platform that receives a value it does not recognize **MUST** display
the value's accompanying disclosure warnings and **MUST NOT** treat the seller
as a trader.

## Data that must never be sent

A marketplace often collects more about a seller than it may publish, such as a
copy of an identity document or the seller's payment account, to verify the
seller. That data **MUST NOT** appear in `seller`, in `seller_disclosures`, or
in any extension of them. Every field this extension defines is meant to be
shown to buyers.

## Rendering

Display duties use the existing warning contract
([Warning Presentation](../checkout/index.md#warning-presentation)). The
Business sends a `messages[]` warning with `presentation: "disclosure"` and a
`path` to the seller entry. The warning `content` is the Business's own text in
the buyer's language, so the wording stays with the party responsible for it.

This extension defines two well-known warning codes:

| Code                      | When the Business sends it                                                                                                                |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `seller_non_trader`       | Seller `trader_status` is `non_trader` or `not_declared`, and the law requires telling the buyer that consumer rights do not apply.       |
| `seller_obligation_split` | Contract obligations are shared between the seller and the Business, for example the Business delivers and the seller handles conformity. |

**Business requirements:**

- **MUST** send one `seller_disclosures` entry for every seller of a line item
    in a cart, checkout or order response when it has negotiated this
    extension.
- **MUST NOT** cover a line item with more than one entry.
- **MUST** keep the seller ID key stable from cart through checkout to the
    resulting order.
- **MUST** send a `seller_non_trader` disclosure when applicable law requires
    the buyer to be told that consumer protection rules do not apply.
- **MUST** carry the disclosures presented at checkout unchanged on the order.

**Platform requirements:**

- **MUST** show, before the buyer completes checkout, each seller's `name` (or
    `legal_name` when `name` is absent) and `trader_status` for the line items
    that seller sells.
- **MUST** render the identity and contact fields when the buyer asks who the
    seller is, and **SHOULD** make them reachable from the line item.
- **MUST** render every disclosure warning that points at a seller entry
    according to the `disclosure` contract, including escalation through
    `continue_url` when it cannot.
- **MUST NOT** substitute its own identity, or the Business's identity, for the
    seller's.

## Examples

### Catalog variant from a third-party seller

<!-- ucp:example schema=shopping/types/variant -->
```json
{
  "id": "gid://shop.example/ProductVariant/88213",
  "title": "Vintage film camera, body only",
  "description": {
    "plain": "Used 35 mm film camera body, tested."
  },
  "price": {
    "amount": 14900,
    "currency": "EUR"
  },
  "seller": {
    "name": "Anna's attic",
    "trader_status": "non_trader",
    "links": [
      {
        "type": "seller_profile",
        "url": "https://shop.example/sellers/annas-attic",
        "title": "Seller profile"
      }
    ]
  }
}
```

### Checkout with two sellers

A marketplace checkout with one line from a trader and one from a private
seller. The `seller_disclosures` map:

<!-- ucp:example schema=shopping/seller_disclosure def=seller_disclosures extract=$.seller_disclosures -->
```json
{
  "id": "checkout_9f2",
  "status": "ready_for_complete",
  "line_items": [ ... ],
  "seller_disclosures": {
    "seller_101": {
      "name": "Lumen Optics",
      "trader_status": "trader",
      "legal_name": "Lumen Optics GmbH",
      "address": {
        "street_address": "Harbor Road 12",
        "address_locality": "Hamburg",
        "postal_code": "20457",
        "address_country": "DE"
      },
      "contacts": [
        {
          "type": "customer_support",
          "email": "support@lumen-optics.example",
          "phone_number": "+4940123456"
        }
      ],
      "registrations": [
        {
          "type": "trade_register",
          "number": "HRB 123456",
          "register_name": "Hamburg Local Court",
          "country": "DE"
        },
        {
          "type": "vat",
          "number": "DE123456789",
          "country": "DE"
        }
      ],
      "compliance_self_certified": true,
      "line_item_ids": ["li_1"]
    },
    "seller_202": {
      "name": "Anna's attic",
      "trader_status": "non_trader",
      "contacts": [
        {
          "url": "https://shop.example/sellers/annas-attic/contact"
        }
      ],
      "line_item_ids": ["li_2"]
    }
  }
}
```

The disclosure that tells the buyer the second line is bought from a private
seller:

<!-- ucp:example schema=shopping/checkout target=$.messages -->
```json
[
  {
    "type": "warning",
    "code": "seller_non_trader",
    "path": "$.seller_disclosures.seller_202",
    "presentation": "disclosure",
    "content": "Anna's attic is a private seller. EU consumer protection rules, such as the right of withdrawal, do not apply to this item."
  }
]
```

### Order snapshot

The order repeats the entries presented at checkout, keyed by the same seller
IDs, with line item IDs from the order. One entry is shown:

<!-- ucp:example schema=shopping/seller_disclosure def=seller_disclosures extract=$.seller_disclosures -->
```json
{
  "id": "order_5521",
  "checkout_id": "checkout_9f2",
  "seller_disclosures": {
    "seller_202": {
      "name": "Anna's attic",
      "trader_status": "non_trader",
      "contacts": [
        {
          "url": "https://shop.example/sellers/annas-attic/contact"
        }
      ],
      "line_item_ids": ["oli_2"]
    }
  }
}
```
