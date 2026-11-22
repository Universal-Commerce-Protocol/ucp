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

<!-- cspell:ignore inpost orlenpaczka packeta Paczka Orlen Paczkomat Prosta Warszawa -->

# Carrier Pickup Extension

## Overview

The Carrier Pickup Extension defines the `carrier_pickup` fulfillment method.
The Business ships the parcel to a parcel locker or a staffed pickup point that
a carrier network operates, and the Buyer collects it there. The point belongs
to the network, not to the Business, which is what separates this method from
`pickup` at a Business Location.

A carrier point differs from a Business Location in four ways that matter to an
agent:

- **The network owns the point identifier.** Point IDs are issued by the
  network, are unique only within a network and country, and are usually chosen
  by the Buyer in the network's own point selector.
- **Several networks serve one market and one site.** A Buyer may choose among
  several networks in one checkout, and one shop counter can be a point of
  several networks, each with its own ID, holding period and limits.
- **The method needs Buyer contact data.** Networks deliver the collection code
  or the deposit notice to the Buyer's phone or email, so the shipment cannot be
  created without them. A street address of the Buyer is not needed for the
  delivery itself.
- **Delivery has two steps.** The carrier deposits the parcel at the point, and
  the Buyer later collects it, or does not collect it before the holding period
  ends.

**Key features:**

- A Carrier Point Destination keyed by (`network`, `country`, `point_id`),
  with an optional broker identifier, point type, host site, holding period and
  parcel limits
- Platform-writable point selection, with Business re-validation on every
  update
- Machine-readable reasons why a point cannot be used
- Per-method Buyer field requirements with a stated purpose
- Order events that separate deposit at the point from collection by the Buyer

**Dependencies:**

- [Fulfillment Extension](fulfillment.md): this extension defines one more
  method `type` and one more destination `type` on top of it.
- Checkout, and Order for the post-purchase events.

## Discovery

Businesses advertise carrier pickup in their profile, and **MAY** list the
networks they ship to so a Platform can offer the right point selector before
Checkout:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.fulfillment.carrier_pickup": [
        {
          "version": "{{ ucp_version }}",
          "extends": [
            "dev.ucp.shopping.checkout",
            "dev.ucp.shopping.order"
          ],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/extensions/carrier-pickup",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/fulfillment_carrier_pickup.json",
          "config": {
            "networks": [
              {
                "network": "pl.inpost",
                "name": "InPost Paczkomat",
                "countries": ["PL"],
                "point_types": ["locker", "staffed"]
              },
              {
                "network": "pl.orlenpaczka",
                "name": "Orlen Paczka",
                "countries": ["PL"]
              },
              {
                "network": "com.packeta",
                "name": "Packeta",
                "countries": ["CZ", "SK", "HU"]
              }
            ]
          }
        }
      ]
    }
  }
}
```

The network identifiers in these examples are illustrative; see
[Network identifier](#network-identifier).

The Fulfillment extension **MUST** also be negotiated. A Platform that has not
negotiated this extension does not create `carrier_pickup` methods; a Business
**MUST NOT** return a `carrier_pickup` method to such a Platform.

## Schema

### Carrier Point Destination

{{ schema_fields('types/carrier_point_destination_resp', 'shopping/extensions/carrier-pickup') }}

### Unavailable Reason

{{ extension_schema_fields('types/carrier_point_destination.json#/$defs/unavailable_reason', 'shopping/extensions/carrier-pickup') }}

### Network Offer

{{ extension_schema_fields('fulfillment_carrier_pickup.json#/$defs/network_offer', 'shopping/extensions/carrier-pickup') }}

### Buyer Field Requirement

{{ extension_schema_fields('fulfillment_carrier_pickup.json#/$defs/buyer_field_requirement', 'shopping/extensions/carrier-pickup') }}

### Carrier Pickup Event Fields

{{ schema_fields('types/carrier_pickup_event', 'shopping/extensions/carrier-pickup') }}

## Method contract

A Fulfillment Method whose `type` is `carrier_pickup` follows the base
[Fulfillment](fulfillment.md) contract, with these additions:

| Field | Direction | Meaning |
| :-- | :-- | :-- |
| `destinations[]` | Request and response | Carrier Point Destinations. The Platform **MAY** write the point the Buyer chose; the Business returns the resolved point. |
| `networks[]` | Response | Networks the Business accepts for this method's line items. It **MAY** be narrower than the profile list, for example when a line item is too large for lockers. |
| `required_buyer_fields[]` | Response | Buyer fields the method needs. See [Buyer fields](#buyer-fields). |

The method opts into a Platform-writable request shape, as the
[Destinations](fulfillment.md#destinations) contract permits: under a
`carrier_pickup` method, a request destination that omits `type` is a
`carrier_point`, and only `network`, `country`, `point_id`, `broker` and `id`
are request fields. Everything else about a point is Business-authored.

Groups and options work as for `shipping`: the Business computes options and
their totals for the selected point, because the price depends on the network
and the service the Business buys from it.

### Point identity

A carrier point is identified by the tuple (`network`, `country`, `point_id`).

- The Business and Platform **MUST** compare `point_id` as an exact,
  case-sensitive string. They **MUST NOT** trim leading zeros, change case or
  parse structure out of it.
- The Platform **MUST NOT** infer `country` from `point_id` or from the
  Buyer's address. A network that operates in several countries can reuse the
  same `point_id` in each.
- `id` is the destination identifier used by `selected_destination_id`, as for
  every destination. It is not the point identifier.

#### Network identifier

`network` is a reverse-domain name derived from a domain the network operator
controls, such as `pl.inpost` for a network reached at `inpost.pl`. Domain
control prevents collisions without a central registry. The value names the
operating network, whose point directory and rules apply:

- A buyer-facing brand that sells several networks' points under one name, or a
  marketplace delivery program, is not a network. The point keeps the network
  that operates it.
- A host site, such as a convenience store chain, is not a network. See
  [Host sites](#host-sites).
- An operator that runs separate point namespaces under different brands uses a
  distinct value for each namespace.

The values in this page's examples are illustrative and are not registered or
endorsed by the named operators.

#### Brokers

A Platform or Business can reach a network through a broker that runs its own
point selector or directory. When the broker's identifier for the point differs
from the network's own, the destination carries both: `point_id` is always the
network's identifier, and `broker.point_id` is the broker's. A Platform that
knows only the broker's identifier **MUST NOT** put it in `point_id`; it
resolves the network identifier first, or the Business resolves it through the
same broker.

#### Host sites

One physical site can be a point of several networks. Each is a separate
destination with its own `network`, `point_id`, `pickup_period` and `limits`.
The Business **MAY** set the same `host.id` on those destinations so the
Platform can group them on a map, and **MUST NOT** merge them into one
destination.

### Selection and re-validation

The Platform selects a point in one of two ways:

1. It writes the point the Buyer chose as a destination with a Platform-chosen
   `id`, and sets `selected_destination_id` to that `id`.
2. It sets `selected_destination_id` to the `id` of a point the Business
   returned in `destinations[]`.

The Business resolves the written point against the network directory and
returns it with its Business-authored fields. The rules of
[Selection and Location Identity](fulfillment.md#selection-and-location-identity)
apply unchanged: the response echoes the selection and contains exactly one
matching destination, and the Business **MUST NOT** substitute another point.

Points go full, close for maintenance or leave the network between selection
and order placement. The Business **MUST** re-validate the selected point on
every Update Checkout and before Complete Checkout. When the point cannot be
used, the Business rejects the selection with an error Message with
`severity: "recoverable"`, a `path` that selects the method's
`selected_destination_id`, and a `code` from the
[unavailable reason](#unavailable-reason) codes. The Platform asks the Buyer
to choose another point, or offers another method.

A Business **MAY** list points it cannot use in a response, with
`available: false` and `unavailable_reasons[]`, so the Platform can explain why
a point the Buyer knows is not offered. The Platform **MUST NOT** select a point
marked `available: false`.

### Eligibility

Lockers have fixed compartment sizes and networks have weight limits, so a cart
can be valid for courier delivery and invalid for some or all points. The
Business decides eligibility, because it knows the parcel it will build.
`limits` is informational. The well-known reason codes are:

| Code | Meaning |
| :-- | :-- |
| `exceeds_size_limit` | The parcel does not fit the largest compartment or the point's size limit. |
| `exceeds_weight_limit` | The parcel is heavier than the point accepts. |
| `item_not_eligible` | A line item cannot be sent to points of this network, for a reason other than size or weight. |
| `point_full` | The point has no free capacity. |
| `point_closed` | The point is temporarily out of service. |
| `point_not_found` | The network directory does not know the point, or it has been removed. |
| `network_not_supported` | The Business does not ship to this network for this cart. |
| `country_not_supported` | The Business does not ship to this network in this country. |

A reason that comes from particular line items **SHOULD** list them in
`line_item_ids`, so a Platform can propose splitting the cart across methods.
When no point of any network can take the cart, the Business **SHOULD** omit
the `carrier_pickup` method and **MAY** explain it in `available_methods[]`.

### Buyer fields

`required_buyer_fields[]` lists the Checkout `buyer` fields the method needs to
create the shipment, each with a `purpose`. The Business:

- **MUST** list only fields the selected network needs for this method. A
  Business **MUST NOT** list a Buyer postal address as needed for a carrier
  point; a billing address, where required, has its own basis and its own
  field.
- **MUST** return a recoverable error with a `path` that selects the missing
  `buyer` field when a listed field is missing at Complete Checkout, so the
  Platform can collect it in band.

The Platform:

- **SHOULD** collect the listed fields before Complete Checkout and tell the
  Buyer what each one is for, using `purpose`.
- **SHOULD NOT** send Buyer fields for this method beyond those listed and those
  required by other parts of the Checkout.
- **MUST NOT** fill a listed field from stored or identity-linked data without
  the Buyer seeing the value that will be shared.

A `phone_number` with purpose `pickup_notification` must receive text messages,
because the network sends the collection code or deposit notice to it.

## Order events

This extension adds `point` and `pickup_by` to Fulfillment Events on the Order
and gives four event types a defined meaning for carrier points:

| Event `type` | Meaning | Fields |
| :-- | :-- | :-- |
| `ready_for_pickup` | The carrier deposited the parcel at the point. The holding period runs. | `point`, and `pickup_by` (required with `point`) |
| `picked_up` | The Buyer collected the parcel. | `point` |
| `not_collected` | The holding period ended without collection. | `point` |
| `returned_to_sender` | The parcel is on its way back to, or back at, the Business. | |

- `ready_for_pickup` is not delivery to the Buyer. A Platform **MUST NOT**
  present it as "delivered".
- `picked_up` with its `occurred_at` is the moment the Buyer acquired physical
  possession. A Business that states deadlines counted from possession, such as
  a return or withdrawal window, counts them from this event.
- A later `ready_for_pickup` with a new `pickup_by` supersedes an earlier one,
  for example after an extension or a redirect to another point, and carries
  the point where the parcel now waits.
- `not_collected` and `returned_to_sender` describe the parcel. They **MUST
  NOT** be interpreted as a cancellation, a return or a withdrawal by the Buyer.
  If the Business cancels the order or refunds it as a result, it reports that
  through `adjustments[]`.

## Consumer law considerations

This section is informative. It explains why the contract separates deposit
from collection and limits Buyer fields, for Businesses selling to consumers in
the European Union.

- **Passing of risk.** Under Article 20 of Directive 2011/83/EU (Consumer
  Rights Directive), risk passes when the consumer, or a third party the
  consumer indicated other than the carrier, acquires physical possession. The
  European Consumer Centres Network treats a pickup point the Business offered
  as part of the carrier's delivery, so on that reading risk passes at
  `picked_up`, not at `ready_for_pickup`.
- **Withdrawal period.** Under Article 9(2)(b) of the same Directive, the
  14-day withdrawal period for goods starts on the day the consumer acquires
  physical possession. For a carrier point that is `picked_up`. A parcel that is
  never collected does not start the period.
- **Not collecting is not withdrawing.** Withdrawal requires an unequivocal
  statement (Article 11(1)). `not_collected` and `returned_to_sender` are
  therefore not withdrawals; what follows depends on the contract and national
  law.
- **Data minimization.** Under Article 5(1)(c) and Article 25 of Regulation
  (EU) 2016/679 (GDPR), personal data is limited to what is necessary for the
  purpose. The European Data Protection Board Guidelines 2/2019 on Article
  6(1)(b) state that a home address is no longer necessary for the contract
  when the customer chose a pickup point. This is why `required_buyer_fields[]` carries a purpose and why
  a carrier point needs no Buyer address.

## Examples

### Checkout response with several networks

The Business lists the networks it accepts and the phone number the method
needs. The Buyer selected a locker; the Business also suggests a staffed point
of another network at the same site, and lists a third point it cannot use.

<!-- ucp:example schema=shopping/fulfillment_carrier_pickup def=dev.ucp.shopping.checkout op=read -->
```json
{
  "ucp": { ... },
  "id": "chk_7f3a",
  "status": "incomplete",
  "currency": "PLN",
  "line_items": [ ... ],
  "totals": [ ... ],
  "links": [ ... ],
  "fulfillment": {
    "methods": [
      {
        "id": "method_1",
        "type": "carrier_pickup",
        "line_item_ids": ["li_kettle"],
        "networks": [
          { "network": "pl.inpost", "name": "InPost Paczkomat", "countries": ["PL"] },
          { "network": "pl.orlenpaczka", "name": "Orlen Paczka", "countries": ["PL"] }
        ],
        "required_buyer_fields": [
          { "field": "phone_number", "purpose": "pickup_notification" },
          { "field": "email", "purpose": "pickup_notification", "networks": ["pl.inpost"] }
        ],
        "selected_destination_id": "pt_1",
        "destinations": [
          {
            "type": "carrier_point",
            "id": "pt_1",
            "network": "pl.inpost",
            "country": "PL",
            "point_id": "WAW99X",
            "point_type": "locker",
            "name": "Paczkomat WAW99X",
            "address": {
              "street_address": "ul. Prosta 5",
              "address_locality": "Warszawa",
              "postal_code": "00-850",
              "address_country": "PL"
            },
            "host": { "id": "site_17", "name": "Corner shop, ul. Prosta 5" },
            "pickup_period": { "duration": "PT48H" },
            "limits": {
              "max_weight": { "value": 25, "unit": "KGM", "display_text": "kg" },
              "max_dimensions": [
                { "value": 64, "unit": "CMT", "display_text": "cm" },
                { "value": 41, "unit": "CMT", "display_text": "cm" },
                { "value": 38, "unit": "CMT", "display_text": "cm" }
              ]
            }
          },
          {
            "type": "carrier_point",
            "id": "pt_2",
            "network": "pl.orlenpaczka",
            "country": "PL",
            "point_id": "100417",
            "point_type": "staffed",
            "name": "Orlen Paczka, Corner shop",
            "host": { "id": "site_17", "name": "Corner shop, ul. Prosta 5" },
            "pickup_period": { "duration": "P3D", "counting": "business_days" }
          },
          {
            "type": "carrier_point",
            "id": "pt_3",
            "network": "pl.inpost",
            "country": "PL",
            "point_id": "WAW12M",
            "point_type": "locker",
            "name": "Paczkomat WAW12M",
            "available": false,
            "unavailable_reasons": [
              { "code": "point_full", "content": "This locker is full today." }
            ]
          }
        ],
        "groups": [
          {
            "id": "package_1",
            "line_item_ids": ["li_kettle"],
            "selected_option_id": "locker_standard",
            "options": [
              {
                "id": "locker_standard",
                "title": "Parcel locker",
                "description": { "plain": "Ready for pickup in 1-2 business days" },
                "totals": [{ "type": "total", "amount": 1299 }]
              }
            ]
          }
        ]
      }
    ]
  }
}
```

### Platform selects a point chosen in a broker's selector

The Buyer picked a point in a broker's map. The Platform writes the network's
identifier and the broker's identifier, and selects the point.

<!-- ucp:example schema=shopping/fulfillment_carrier_pickup def=dev.ucp.shopping.checkout op=update direction=request -->
```json
{
  "line_items": [ ... ],
  "fulfillment": {
    "methods": [
      {
        "id": "method_1",
        "type": "carrier_pickup",
        "line_item_ids": ["li_book"],
        "selected_destination_id": "buyer_choice",
        "destinations": [
          {
            "id": "buyer_choice",
            "network": "com.packeta",
            "country": "CZ",
            "point_id": "004211",
            "broker": { "id": "com.example-broker", "point_id": "PK-CZ-004211" }
          }
        ]
      }
    ]
  }
}
```

### Selected point no longer available

On a later update the locker is full. The Business leaves the Checkout
unchanged and returns a recoverable error on the selection.

<!-- ucp:example schema=shopping/fulfillment_carrier_pickup def=dev.ucp.shopping.checkout op=read -->
```json
{
  "ucp": { ... },
  "id": "chk_7f3a",
  "status": "incomplete",
  "currency": "PLN",
  "line_items": [ ... ],
  "totals": [ ... ],
  "links": [ ... ],
  "messages": [
    {
      "type": "error",
      "code": "point_full",
      "path": "$.fulfillment.methods[0].selected_destination_id",
      "content": "Parcel locker WAW99X is full. Please choose another point.",
      "severity": "recoverable"
    }
  ]
}
```

### Order events: deposit, extension, collection

<!-- ucp:example schema=shopping/fulfillment_carrier_pickup def=dev.ucp.shopping.order op=read -->
```json
{
  "ucp": { ... },
  "id": "ord_51c2",
  "checkout_id": "chk_7f3a",
  "permalink_url": "https://shop.example.com/orders/ord_51c2",
  "currency": "PLN",
  "line_items": [ ... ],
  "totals": [ ... ],
  "fulfillment": {
    "events": [
      {
        "id": "evt_1",
        "occurred_at": "2026-11-23T09:12:00Z",
        "type": "shipped",
        "line_items": [{ "id": "li_kettle", "quantity": 1 }],
        "tracking_number": "TRK123456789",
        "tracking_url": "https://tracking.example.com/TRK123456789"
      },
      {
        "id": "evt_2",
        "occurred_at": "2026-11-24T07:40:00Z",
        "type": "ready_for_pickup",
        "line_items": [{ "id": "li_kettle", "quantity": 1 }],
        "tracking_number": "TRK123456789",
        "tracking_url": "https://tracking.example.com/TRK123456789",
        "point": { "network": "pl.inpost", "country": "PL", "point_id": "WAW99X" },
        "pickup_by": "2026-11-26T07:40:00Z"
      },
      {
        "id": "evt_3",
        "occurred_at": "2026-11-26T08:05:00Z",
        "type": "ready_for_pickup",
        "line_items": [{ "id": "li_kettle", "quantity": 1 }],
        "tracking_number": "TRK123456789",
        "tracking_url": "https://tracking.example.com/TRK123456789",
        "point": { "network": "pl.inpost", "country": "PL", "point_id": "WAW01B" },
        "pickup_by": "2026-11-29T08:05:00Z",
        "description": "Not collected from the locker; moved to a staffed point."
      },
      {
        "id": "evt_4",
        "occurred_at": "2026-11-27T17:21:00Z",
        "type": "picked_up",
        "line_items": [{ "id": "li_kettle", "quantity": 1 }],
        "tracking_number": "TRK123456789",
        "tracking_url": "https://tracking.example.com/TRK123456789",
        "point": { "network": "pl.inpost", "country": "PL", "point_id": "WAW01B" }
      }
    ]
  }
}
```

### Order events: not collected

<!-- ucp:example schema=shopping/fulfillment_carrier_pickup def=dev.ucp.shopping.order op=read -->
```json
{
  "ucp": { ... },
  "id": "ord_51c2",
  "checkout_id": "chk_7f3a",
  "permalink_url": "https://shop.example.com/orders/ord_51c2",
  "currency": "CZK",
  "line_items": [ ... ],
  "totals": [ ... ],
  "fulfillment": {
    "events": [
      {
        "id": "evt_2",
        "occurred_at": "2026-11-24T10:00:00Z",
        "type": "ready_for_pickup",
        "line_items": [{ "id": "li_book", "quantity": 1 }],
        "tracking_number": "Z0042110001",
        "tracking_url": "https://tracking.example.com/Z0042110001",
        "point": { "network": "com.packeta", "country": "CZ", "point_id": "004211" },
        "pickup_by": "2026-12-01T10:00:00Z"
      },
      {
        "id": "evt_3",
        "occurred_at": "2026-12-01T10:00:00Z",
        "type": "not_collected",
        "line_items": [{ "id": "li_book", "quantity": 1 }],
        "tracking_number": "Z0042110001",
        "tracking_url": "https://tracking.example.com/Z0042110001",
        "point": { "network": "com.packeta", "country": "CZ", "point_id": "004211" }
      },
      {
        "id": "evt_4",
        "occurred_at": "2026-12-04T13:30:00Z",
        "type": "returned_to_sender",
        "line_items": [{ "id": "li_book", "quantity": 1 }],
        "tracking_number": "Z0042110001",
        "tracking_url": "https://tracking.example.com/Z0042110001"
      }
    ]
  }
}
```
