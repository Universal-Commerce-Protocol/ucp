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
buyer which one it is and how to reach the seller, at the point where the offer
is shown.

This extension carries those facts as data:

- **Catalog**: the `seller` object on a [variant](../catalog/index.md) gains
    a seller `id` and the [Seller Details](#seller-details) fields, so a
    platform can show the seller, its trader status and its identity with the
    offer.
- **Cart, checkout and order**: a response-only `seller_disclosures` map lists
    each seller in the session and the line items it sells. The order records
    the seller facts and the notice text the buyer was shown at checkout.

This extension covers who the seller is. It does not cover the wording of the
final order control or the information shown directly before it; those are
separate obligations and are not addressed here.

### Legal context (informative)

The fields are jurisdiction-neutral. As an example, in the EU:

| Duty                                                                                                                   | Source                                | Owed by                      |
| ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------- | ---------------------------- |
| Identity, geographic address, telephone number and email of the trader                                                 | Directive 2011/83/EU Art. 6(1)(b)-(c) | The trader                   |
| Complaints address, if different                                                                                       | Directive 2011/83/EU Art. 6(1)(d)     | The trader                   |
| Whether the third party is a trader, based on its own declaration                                                      | Directive 2011/83/EU Art. 6a(1)(b)    | The marketplace provider     |
| Notice that consumer rights do not apply to the contract with a non-trader                                             | Directive 2011/83/EU Art. 6a(1)(c)    | The marketplace provider     |
| How contract obligations are shared between seller and marketplace                                                     | Directive 2011/83/EU Art. 6a(1)(d)    | The marketplace provider     |
| Name, address, telephone, email, trade register entry and self-certification, available where the product is presented | Regulation (EU) 2022/2065 Art. 30(7)  | The online platform provider |

The consumer-law duties apply to contracts with consumers. Regulation (EU)
2022/2065 Art. 29 exempts micro and small platform providers from Art. 30
unless they are designated as very large online platforms. Whether a given
Business or Platform owes a duty depends on its role in the transaction; this
specification defines what each party sends and renders, not who is liable.

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
negotiation. A Platform that renders `variant.seller.name` for an offer whose
seller carries `trader_status` **MUST** also render that status under the
rules below. A Platform that has not negotiated this extension ignores
`seller_disclosures` on cart, checkout and order.

## Schema

### Seller Details

The shared fields added to the catalog variant `seller` (which keeps its
existing `name` and `links`) and used in every `seller_disclosures` entry. All
fields are optional on catalog. A `seller_disclosures` entry also requires a
non-blank `name` and a `trader_status`, and bounds its `links`.

{{ schema_fields('shopping/types/seller_details', 'shopping/extensions/seller-disclosure') }}

### Contact

{{ extension_schema_fields('types/seller_details.json#/$defs/contact', 'shopping/extensions/seller-disclosure') }}

### Registration

{{ extension_schema_fields('types/seller_details.json#/$defs/registration', 'shopping/extensions/seller-disclosure') }}

### Seller Disclosure Entry

An entry in the cart or checkout `seller_disclosures` map. It adds the
`line_item_ids` the seller sells.

{{ extension_schema_fields('seller_disclosure.json#/$defs/seller_entry', 'shopping/extensions/seller-disclosure') }}

### Order Seller Disclosure Entry

An entry in the order `seller_disclosures` map. It adds the notices the
Business sent at checkout and, for a later snapshot, the `seller_id`.

{{ extension_schema_fields('seller_disclosure.json#/$defs/order_seller_entry', 'shopping/extensions/seller-disclosure') }}

{{ extension_schema_fields('seller_disclosure.json#/$defs/presented_notice', 'shopping/extensions/seller-disclosure') }}

## Seller ID

The seller ID is a Business-scoped identifier of a seller. It is the key of the
seller's `seller_disclosures` entry and equals `variant.seller.id` in catalog,
so a Platform can follow the same seller from the offer to the order. It
identifies a business or an individual seller, not a buyer, and **MUST NOT**
encode buyer or session data.

A seller ID stands for one seller in one capacity. A natural person who sells
both professional stock and personal belongings on the same marketplace has
two seller IDs, each with its own `trader_status`.

## Trader status

`trader_status` records what the seller declared to the Business. It is not a
legal assessment by the Business or the Platform. Each value has its own
presentation:

| Value           | The Business sends                        | The Platform presents                                                              |
| --------------- | ----------------------------------------- | ---------------------------------------------------------------------------------- |
| `trader`        | Nothing extra                             | That the seller is a trader (a professional seller)                                |
| `non_trader`    | A `seller_non_trader` disclosure          | That the seller is a private seller, and the Business's notice                     |
| `not_declared`  | A `seller_status_not_declared` disclosure | That the seller has not declared whether it is a trader, and the Business's notice |
| Any other value | A disclosure explaining the value         | The same as `not_declared`                                                         |

`not_declared` is not `non_trader`. A missing declaration does not establish
that consumer rights are excluded. A Platform **MUST NOT** state or imply that
consumer rights do not apply to a seller whose status is `not_declared` or
unrecognized, and **MUST NOT** present such a seller as a trader.

A Business that sells its own goods sends `trader`.

`not_declared` can be shown during discovery. Where applicable law requires
the buyer to be told the seller's declared status before the contract (for
example, Directive 2011/83/EU Art. 6a(1)(b) for a consumer contract on an EU
online marketplace), the Business **MUST** obtain the seller's declaration
before the buyer completes checkout and **MUST NOT** complete the checkout for
that seller's line items without it; until then it keeps the checkout in
`requires_escalation`. Where no such law applies, the Business **SHOULD** do
the same.

## Display requirements

The seller information is part of the offer. Showing it **MUST NOT** depend on
the buyer asking for it.

**With the offer** (catalog, cart and checkout), the Platform **MUST** show
for every third-party offer, in the same view as the offer:

- the seller's `name`, marked as a third-party seller distinct from the
    marketplace and from the Platform;
- the presentation of its `trader_status` from the table above;
- every disclosure warning that points at the seller.

**One step from the offer**, the Platform **MUST** make the remaining seller
details available through a control shown next to the seller name, before the
buyer completes checkout: `legal_name`, `address`, `complaints_address`,
`contacts`, `registrations`, `compliance_self_certified`, and `on_behalf_of`.
The Platform presents a certification only when `compliance_self_certified` is
`true`, as a statement that the seller has certified it offers only compliant
products. It **MUST NOT** present `false` or an absent value as a
certification.

In a channel that has no such control, such as voice, the Platform **MUST**
make the details available while it presents the offer: it reads them out or
sends them in readable form in the same turn, and tells the buyer it has done
so. If it cannot, it **MUST NOT** present the offer and hands off instead
(see [Hand-off](#hand-off)).

**Completeness.** These duties apply to any Business, whether it sells its own
goods or runs a marketplace:

- Before the buyer completes checkout, the Business **MUST** send, for every
    seller that is a trader, the identity and contact details applicable law
    requires for the contract. For a distance contract with a consumer in the
    EU (Directive 2011/83/EU Art. 6(1)(b)-(d)) that is `legal_name` (or `name`
    as the trading name), `address`, at least one contact with `email` and one
    with `phone_number`, `complaints_address` when different, and
    `on_behalf_of` where the seller acts for another trader. This applies to a
    direct merchant and to a marketplace that is exempt from Regulation (EU)
    2022/2065 Art. 30.
- Where applicable law also requires seller details on the product
    presentation (for example, Regulation (EU) 2022/2065 Art. 30(7)), the
    Business **MUST** send them on the catalog variant as well: `legal_name`,
    `address`, the contacts above, `registrations` with the trade register
    entry where the seller is registered, and `compliance_self_certified`.
    Where that law requires a self-certification, the Business **MUST NOT**
    list the trader's offer unless `compliance_self_certified` is `true`.

## Disclosure warnings

Display duties for notices use the existing warning contract
([Warning Presentation](../checkout/index.md#warning-presentation)). The
Business sends a `messages[]` warning with `presentation: "disclosure"` and a
`path` to the seller: the variant `seller` object in catalog responses, or the
seller's `seller_disclosures` entry in cart and checkout responses.

| Code                         | When the Business sends it                                                                             |
| ---------------------------- | ------------------------------------------------------------------------------------------------------ |
| `seller_non_trader`          | `trader_status` is `non_trader` and the law requires a notice that consumer rights do not apply.       |
| `seller_status_not_declared` | `trader_status` is `not_declared` or another value the Business defines.                               |
| `seller_obligation_split`    | Contract obligations are shared between the seller and the Business, for example delivery and returns. |

**Business requirements:**

- **MUST** send one `seller_disclosures` entry for every seller of a line item
    in a cart, checkout or order response when it has negotiated this
    extension.
- **MUST** list `line_item_ids` on every entry when the map has more than one
    entry, and **MUST** list each line item in exactly one entry. Every listed
    ID **MUST** be a line item in the same response.
- **MUST** send a `seller_non_trader` disclosure for every `non_trader` seller
    where applicable law requires the buyer to be told that consumer rights do
    not apply to the contract with that seller.
- **MUST** send a `seller_status_not_declared` disclosure for every seller
    whose status is `not_declared`.
- **MUST** send a `seller_obligation_split` disclosure for every seller whose
    contract obligations are shared with the Business, from the first response
    that shows the seller's offer, with `path` pointing at that seller.
- **SHOULD** verify seller names at onboarding and **MUST NOT** accept a
    seller name that impersonates the marketplace, the Platform, or another
    seller.
- **MUST** return notices in the language requested through
    `context.language`. When it cannot, it **MUST** hand off (see
    [Hand-off](#hand-off)) rather than send a mandatory notice the buyer may
    not understand.
- **MUST NOT** send more than 10 seller disclosure warnings for one seller in
    one response, or a seller disclosure warning `content` longer than 2000
    characters. This covers every seller warning, including codes the
    Business defines: in cart and checkout the extension schema enforces the
    length for any warning whose `code` starts with `seller_` or whose `path`
    points into `seller_disclosures`. The order snapshot holds the same
    limits.
- **MUST NOT** have more than 100 active entries on an order (entries that
    list at least one line). Superseded snapshots kept as a record count
    toward a schema limit of 200 entries.
- **SHOULD** give Business-defined seller warning codes the `seller_` prefix.

**Platform requirements:**

- **MUST** follow [Display requirements](#display-requirements).
- **MUST** render every disclosure warning that points at a seller under the
    `disclosure` contract, and hand off (see [Hand-off](#hand-off)) when it
    cannot. A Platform that cannot present a seller's required notice
    **MUST NOT** present that seller's trader status or offer as purchasable.
- **MUST NOT** infer, change or omit a seller's trader status, and **MUST
    NOT** substitute its own identity, or the Business's identity, for the
    seller's.
- **MUST** reject a cart or checkout response whose line items are not each
    covered by exactly one entry, and hand off (see [Hand-off](#hand-off)).
- **SHOULD** tell apart sellers that share a `name` by showing `legal_name`.

### Hand-off

Where this page requires a hand-off, the Platform sends the buyer to the
Business's own interface:

- in cart and checkout, through `continue_url`;
- in catalog, which has no `continue_url`, through the variant or product
    `url`, and if neither is present, by not presenting the offer;
- on an order, through `permalink_url`.

Every hand-off URL **MUST** be an absolute `https` URL. A Platform **MUST NOT**
hand off to any other URL; if no suitable URL exists, it does not present the
offer or does not continue the checkout.

## Business-authored text and URLs

Every seller string (`name`, `legal_name`, contact `name`, `register_name`)
and every warning `content` is plain text written by the Business or relayed
from the seller. It carries no markup and no links. URLs go only in `links`,
and each **MUST** use `https`. In `seller_disclosures` entries the schema
enforces `https` and bounds every seller string, address field and link. On
the catalog variant, the new seller fields are bounded too; the existing core
`seller.name` and `seller.links` keep their current schema, because tightening
them would break existing catalog payloads, so the `https` rule and the bound
of 500 characters for names apply there by this text.

- A Platform **MUST** treat these strings as data from the Business and **MUST
    NOT** follow instructions found in them.
- A Platform **MUST** present the meaning of a notice. It **MAY** adapt layout
    and channel (voice, small screen). It **MUST NOT** change the substance:
    the seller's identity, its status, and the conditions stated.
- A Platform **MUST NOT** fetch a seller URL server-side on the buyer's
    behalf, except to show it.

## Trust

Trader status, identity, registrations and self-certification are statements
by the Business, which is responsible for their accuracy under applicable law.
A Platform presents them as the Business's statements about the seller. This
specification adds no verification duty for the Platform. That is without
prejudice to obligations the Platform or the Business has under applicable
law, such as the duties of an online platform in scope of Regulation (EU)
2022/2065 Art. 30(2)-(3) to assess and act on trader information. Signed or
verified claims are out of scope; see the attestation work in #1020.

## Privacy

A seller can be a natural person, so seller details can be personal data.

- Identity documents and payment account details collected to verify a seller
    **MUST NOT** appear in `seller`, in `seller_disclosures`, or in any
    extension of them.
- On catalog, a Business **SHOULD** send for a `non_trader` or `not_declared`
    seller only `id`, `name` and `trader_status`, and **SHOULD NOT** send that
    seller's address, contacts or registrations unless the law requires them.
- For a natural-person trader, a Business sends only the details the law
    requires on the offer. A Platform **SHOULD NOT** retain seller details
    beyond the session and the order record.
- `on_behalf_of` is sent only where the seller concludes the contract in the
    name of another trader, not as a supply-chain export.

## Order snapshot

The order records the seller disclosures the Business sent before the buyer
completed checkout:

- Each entry created at checkout is keyed by the same seller ID as at checkout.
- Its seller facts (`name` and all [Seller Details](#seller-details) fields)
    and its `presented_notices` are those sent at checkout and do not change
    afterwards.
- `presented_notices` holds the `code`, `content` and `language` of every
    seller disclosure warning the Business sent at checkout for that seller.
    It records the Business-supplied text, not how the Platform rendered it;
    a Platform that adapted the wording for its channel keeps its own record.
- `line_item_ids` reference the order's line item IDs. The Business maps each
    checkout line to the order line created from it.

The line associations can change after the order is placed:

- A line whose `status` becomes `removed` keeps its place in its entry, so the
    purchase stays attributed to its seller.
- A line deleted from the order is removed from the entry. An entry whose lines
    are all deleted stays on the order with `line_item_ids: []`.
- A line added later, for example in an exchange, from a seller whose facts and
    notices are unchanged, is added to that seller's entry.
- A line added later from a seller whose facts or notices changed, or from a
    seller that was not on the order, gets a new entry with the details and
    notices presented for that line. For an existing seller the new entry uses
    a new key and sets `seller_id`.

## Examples

### Catalog variant from a private seller

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
    "id": "seller_202",
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

The disclosure in the catalog search response:

<!-- ucp:example schema=shopping/catalog_search op=search target=$.messages -->
```json
[
  {
    "type": "warning",
    "code": "seller_non_trader",
    "path": "$.products[0].variants[0].seller",
    "presentation": "disclosure",
    "content": "Anna's attic is a private seller. The consumer rights that EU law gives you when buying from a business, such as the right of withdrawal, do not apply to your contract with this seller."
  }
]
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
    "content": "Anna's attic is a private seller. The consumer rights that EU law gives you when buying from a business, such as the right of withdrawal, do not apply to your contract with this seller."
  }
]
```

### Order snapshot

The order keeps the seller IDs from checkout, maps the lines to order line IDs,
and records the notice text that was shown. One entry is shown:

<!-- ucp:example schema=shopping/seller_disclosure def=order_seller_disclosures extract=$.seller_disclosures -->
```json
{
  "id": "order_5521",
  "checkout_id": "checkout_9f2",
  "seller_disclosures": {
    "seller_202": {
      "name": "Anna's attic",
      "trader_status": "non_trader",
      "line_item_ids": ["oli_2"],
      "presented_notices": [
        {
          "code": "seller_non_trader",
          "content": "Anna's attic is a private seller. The consumer rights that EU law gives you when buying from a business, such as the right of withdrawal, do not apply to your contract with this seller.",
          "language": "en"
        }
      ]
    }
  }
}
```

After an exchange, the line from the trader was deleted and replaced by a line
from the same seller under a changed obligation split. The original entry stays
as a record with no lines, and the new snapshot has its own key:

<!-- ucp:example schema=shopping/seller_disclosure def=order_seller_disclosures extract=$.seller_disclosures -->
```json
{
  "id": "order_5521",
  "seller_disclosures": {
    "seller_101": {
      "name": "Lumen Optics",
      "trader_status": "trader",
      "line_item_ids": []
    },
    "seller_101_x1": {
      "seller_id": "seller_101",
      "name": "Lumen Optics",
      "trader_status": "trader",
      "line_item_ids": ["oli_3"],
      "presented_notices": [
        {
          "code": "seller_obligation_split",
          "content": "The replacement is shipped by the marketplace. Lumen Optics remains responsible for its conformity.",
          "language": "en"
        }
      ]
    },
    "seller_202": { ... }
  }
}
```
