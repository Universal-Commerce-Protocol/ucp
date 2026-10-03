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

# Fulfillment Extension

## Overview

The Food Fulfillment Extension (`dev.ucp.food.fulfillment`) adds a
`fulfillment` field describing how a prepared order gets from the kitchen
to the buyer: courier **delivery** to the buyer's address, or buyer **pickup**
at the establishment.

**Key features:**

- Order-wide fulfillment: one method covers every dish in the order
- Type-discriminated destinations: a buyer `delivery_address` or the
  establishment's `business_location`
- ASAP or scheduled ordering via `requested_fulfillment_time`
- Structured drop-off preferences (e.g., "Leave at my door") plus free-form
  courier `notes`
- Time-window options (`earliest_fulfillment_time` / `latest_fulfillment_time`)
  priced through `totals`

`fulfillment` contains:

- `methods[]` — the fulfillment method for the order (`delivery` or `pickup`)
    - `destination` — where the order goes (buyer address or establishment)
    - `requested_fulfillment_time` — omitted for ASAP; a timestamp for scheduled orders
    - `options[]` — Business-generated time windows, each with `totals`
    - `notes` — courier or pickup instructions
- `available_methods[]` — whether delivery and pickup are offered, and when

**Mental model:**

- `methods[0]` 🛵 Delivery
    - `destination` 🏠 `delivery_address` 450 Serra Mall, Apt 3B
        - `selected_preference_option_ids` 🔘✅ Leave at my door · 🔘 Hand it to me
    - `requested_fulfillment_time` ⏱️ *(omitted → ASAP)*
    - `notes` 📝 "Gate code #4210, second floor"
    - `selected_option_id` = `options[1].id`
        - `options[0]` 🔘 Priority Delivery · 6:25–6:35 PM · $5.99
        - `options[1]` 🔘✅ Standard Delivery · 6:35–6:50 PM · $2.99
- `available_methods[]` 🛵 delivery: now · 🛍️ pickup: now

### Design Compared to Shopping Fulfillment

Fulfillment shares its vocabulary with
[Shopping Fulfillment](../../shopping/extensions/fulfillment.md) but is
deliberately flatter, because a food order is cooked, bagged, and handed off
together from a single kitchen:

| Dimension | Shopping Fulfillment | Food Fulfillment | Why |
| :--- | :--- | :--- | :--- |
| **Scope** | Per line item (`line_item_ids[]`) | Whole order | Dishes from one kitchen travel together; there are no split shipments. |
| **Hierarchy** | `methods[]` → `groups[]` → `options[]` | `methods[]` → `options[]` | No packaging layer; speed and time tiers attach to the method. |
| **Destination** | `destinations[]` + `selected_destination_id` | One `destination`, discriminated by `type` | An order goes to one address or is collected at one counter. |
| **Timing** | Chosen only from Business options | Platform may request a time (`requested_fulfillment_time`) | Buyers order "now" or for a specific dinner time. |
| **Handoff** | — | `preference_options[]` + `selected_preference_option_ids[]` + `notes` | Contactless drop-off and building access are core to delivery. |

## Discovery

Businesses advertise food fulfillment support in their profile:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.food.fulfillment": [
        {
          "version": "{{ ucp_version }}",
          "extends": "dev.ucp.food.checkout",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/food/extensions/fulfillment",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/food/fulfillment.json"
        }
      ]
    }
  }
}
```

## Schema

### Entities

#### Fulfillment

{{ schema_fields('food/types/fulfillment_resp', 'food/extensions/fulfillment') }}

#### Fulfillment Method

{{ schema_fields('food/types/fulfillment_method_resp', 'food/extensions/fulfillment') }}

#### Fulfillment Destination

{{ schema_fields('food/types/fulfillment_destination_resp', 'food/extensions/fulfillment') }}

#### Delivery Destination

{{ schema_fields('food/types/delivery_destination_resp', 'food/extensions/fulfillment') }}

#### Physical Address

{{ schema_fields('types/physical_address', 'food/extensions/fulfillment') }}

#### Geo

{{ schema_fields('types/geo', 'food/extensions/fulfillment') }}

#### Business Location Destination

{{ schema_fields('food/types/location_destination_resp', 'food/extensions/fulfillment') }}

#### Preference Option

{{ schema_fields('food/types/preference_option_resp', 'food/extensions/fulfillment') }}

#### Fulfillment Option

{{ schema_fields('food/types/fulfillment_option_resp', 'food/extensions/fulfillment') }}

#### Fulfillment Available Method

{{ schema_fields('food/types/fulfillment_available_method_resp', 'food/extensions/fulfillment') }}

## Destinations

Each method has a single `destination`. As in
[Shopping Fulfillment — Destinations](../../shopping/extensions/fulfillment.md#destinations),
`destination.type` is required in Business responses and optional in Platform
requests; the method `type` determines which destination contract applies:

| Method `type` | Destination `type` | Authored by | Contents |
| :--- | :--- | :--- | :--- |
| `delivery` | `delivery_address` | Platform (address, coordinates, selections) + Business (`preference_options[]`) | [Physical Address](../../reference.md#physical-address) (`postal_address` and/or `geo`), drop-off preferences |
| `pickup` | `business_location` | Business only (response-only) | [Location Summary](../../reference.md#location-summary) of the establishment |

### Delivery Address

The Platform writes the buyer's address; the Business adds the drop-off
choices it supports.

#### Platform Request

<!-- ucp:example schema=food/types/fulfillment_method op=update direction=request -->
```json
{
  "id": "method_delivery",
  "type": "delivery",
  "destination": {
    "id": "dest_home",
    "type": "delivery_address",
    "postal_address": {
      "street_address": "450 Serra Mall",
      "extended_address": "Apt 3B",
      "address_locality": "Stanford",
      "address_region": "CA",
      "postal_code": "94305",
      "address_country": "US"
    }
  },
  "notes": "Gate code #4210, second floor"
}
```

#### Business Response

<!-- ucp:example schema=food/types/fulfillment_method op=read -->
```json
{
  "id": "method_delivery",
  "type": "delivery",
  "destination": {
    "id": "dest_home",
    "type": "delivery_address",
    "postal_address": {
      "street_address": "450 Serra Mall",
      "extended_address": "Apt 3B",
      "address_locality": "Stanford",
      "address_region": "CA",
      "postal_code": "94305",
      "address_country": "US"
    },
    "preference_options": [
      { "id": "pref_leave_at_door", "label": "Leave at my door" },
      { "id": "pref_hand_to_me", "label": "Hand it to me" },
      { "id": "pref_meet_outside", "label": "Meet outside" }
    ],
    "selected_preference_option_ids": ["pref_leave_at_door"]
  },
  "notes": "Gate code #4210, second floor",
  "selected_option_id": "opt_standard",
  "options": [
    {
      "id": "opt_priority",
      "title": "Priority Delivery",
      "description": "Sent directly to you with no other stops",
      "earliest_fulfillment_time": "2026-04-10T18:25:00-07:00",
      "latest_fulfillment_time": "2026-04-10T18:35:00-07:00",
      "totals": [{ "type": "total", "amount": 599 }]
    },
    {
      "id": "opt_standard",
      "title": "Standard Delivery",
      "earliest_fulfillment_time": "2026-04-10T18:35:00-07:00",
      "latest_fulfillment_time": "2026-04-10T18:50:00-07:00",
      "totals": [{ "type": "total", "amount": 299 }]
    }
  ]
}
```

### Delivery to Coordinates

In markets where formal postal addressing is unreliable, the destination **MAY** be expressed as WGS 84 coordinates instead of,
or in addition to, a postal address. At least one of `postal_address` or `geo` **MUST** be provided.

<!-- ucp:example schema=food/types/fulfillment_method op=read -->
```json
{
  "id": "method_delivery_coord",
  "type": "delivery",
  "destination": {
    "id": "dest_pin",
    "type": "delivery_address",
    "geo": {
      "latitude": 12.9716,
      "longitude": 77.5946
    }
  },
  "options": [
    {
      "id": "standard",
      "title": "Standard Delivery",
      "description": "Estimated arrival in 30-45 minutes",
      "totals": [
        { "type": "total", "amount": 499 }
      ]
    }
  ],
  "selected_option_id": "standard",
  "notes": "Blue gate opposite the bakery."
}
```

### Business Location

For pickup, the destination is the establishment itself. It is Business-authored
and response-only: the Platform sends just the method `type`, and the Business
fills in the location.

#### Platform Request

<!-- ucp:example schema=food/types/fulfillment_method op=update direction=request -->
```json
{
  "type": "pickup"
}
```

#### Business Response

<!-- ucp:example schema=food/types/fulfillment_method op=read -->
```json
{
  "id": "method_pickup",
  "type": "pickup",
  "destination": {
    "id": "est_luigis_01",
    "type": "business_location",
    "name": "Luigi's Artisan Pizzeria",
    "address": {
      "street_address": "210 University Ave",
      "address_locality": "Palo Alto",
      "address_region": "CA",
      "postal_code": "94301",
      "address_country": "US"
    }
  },
  "selected_option_id": "opt_pickup_asap",
  "options": [
    {
      "id": "opt_pickup_asap",
      "title": "Counter Pickup",
      "description": "Ask for your order number at the pickup shelf",
      "earliest_fulfillment_time": "2026-04-10T18:15:00-07:00",
      "latest_fulfillment_time": "2026-04-10T18:25:00-07:00",
      "totals": [{ "type": "total", "amount": 0 }]
    }
  ]
}
```

### Drop-Off Preferences & Notes

Delivery handoff is split into two channels so couriers get both a structured
instruction and the details only the buyer knows:

- **Preferences (`preference_options[]` → `selected_preference_option_ids[]`)**:
  The Business lists the handoff modes it supports, each with an `id` and a
  display `label`. The Platform selects by `id`. The Business **MAY** pre-select
  a default (commonly contactless).
- **Notes (`methods[].notes`)**: Free-form courier instructions — gate codes,
  building entrances, "call on arrival". Kitchen requests belong in
  `line_items[].dish.note`, not here.

```text
Drop-off
 (•) Leave at my door    ( ) Hand it to me    ( ) Meet outside
Instructions for courier
 ┌──────────────────────────────────────────────────────────────┐
 │ Gate code #4210, second floor                                │
 └──────────────────────────────────────────────────────────────┘
```

## Fulfillment Timing

Food establishments sell both "as soon as possible" and "for a specific time". The
method's `requested_fulfillment_time` expresses which one the buyer wants, and
the Business answers with concrete windows in `options[]`:

| `requested_fulfillment_time` | Meaning | Business response |
| :--- | :--- | :--- |
| Omitted | **ASAP** — prepare as soon as the order is placed. | Windows based on live kitchen load and courier supply. |
| RFC 3339 timestamp | **Scheduled** — ready or delivered at that time (e.g., dinner at 7:30 PM, a catering drop). | The nearest matching windows, see [Business Validation](#business-validation); if unavailable, a recoverable error plus alternative windows. |

```text
                 now                          7:30 PM
  ───────────────┼──────────────────────────────┼──────────────────▶
  ASAP           [■■■ 6:35–6:50 Standard ■■■]
                 [■ 6:25–6:35 Priority ■]
  Scheduled                               [■■ 7:25–7:40 ■■]
```

### Business Validation

When `requested_fulfillment_time` is provided, the business validates the time and responds accordingly:

- **Available:** Business returns fulfillment options with
  `earliest_fulfillment_time` / `latest_fulfillment_time` windows that contain the requested time
  (i.e., `earliest_fulfillment_time` <= `requested_fulfillment_time` <= `latest_fulfillment_time`).
  Session proceeds normally.
- **Unavailable:** Business returns a `recoverable` error. The fulfillment options array **SHOULD** contain the
  nearest available alternatives so the platform can propose an adjusted time to the buyer.

### Scheduled Fulfillment Examples

Scheduled requests are where food differs most from retail: establishments
have opening hours, pre-order horizons, and per-slot kitchen capacity. When a
requested time cannot be honored, the Business keeps the session recoverable
and offers alternatives instead of failing.

=== "Scheduled Request"

    <!-- ucp:example schema=food/types/fulfillment_method op=update direction=request -->
    ```json
    {
      "id": "method_delivery",
      "type": "delivery",
      "destination": {
        "id": "dest_home",
        "type": "delivery_address",
        "postal_address": {
          "street_address": "450 Serra Mall",
          "address_locality": "Stanford",
          "address_region": "CA",
          "postal_code": "94305",
          "address_country": "US"
        }
      },
      "requested_fulfillment_time": "2026-04-10T22:30:00-07:00"
    }
    ```

=== "Slot Unavailable — Alternatives (`messages`)"

    <!-- ucp:example schema=food/checkout target=$.messages op=read -->
    ```json
    [
      {
        "type": "error",
        "code": "location_closed",
        "path": "$.fulfillment.methods[0].requested_fulfillment_time",
        "content": "Luigi's closes at 10:00 PM. Choose one of the latest available delivery times.",
        "severity": "recoverable"
      }
    ]
    ```

=== "Slot Unavailable — Alternatives (`options`)"

    <!-- ucp:example schema=food/types/fulfillment_method op=read -->
    ```json
    {
      "id": "method_delivery",
      "type": "delivery",
      "destination": {
        "id": "dest_home",
        "type": "delivery_address",
        "postal_address": {
          "street_address": "450 Serra Mall",
          "address_locality": "Stanford",
          "address_region": "CA",
          "postal_code": "94305",
          "address_country": "US"
        }
      },
      "requested_fulfillment_time": "2026-04-10T22:30:00-07:00",
      "options": [
        {
          "id": "opt_2130",
          "title": "Scheduled Delivery, 9:30 PM",
          "earliest_fulfillment_time": "2026-04-10T21:25:00-07:00",
          "latest_fulfillment_time": "2026-04-10T21:40:00-07:00",
          "totals": [{ "type": "total", "amount": 299 }]
        },
        {
          "id": "opt_2145",
          "title": "Scheduled Delivery, 9:45 PM",
          "earliest_fulfillment_time": "2026-04-10T21:40:00-07:00",
          "latest_fulfillment_time": "2026-04-10T21:55:00-07:00",
          "totals": [{ "type": "total", "amount": 299 }]
        }
      ]
    }
    ```

## Rendering

Food options follow the method-agnostic rendering contract in
[Shopping Fulfillment — Rendering](../../shopping/extensions/fulfillment.md#rendering):
`title` + `description` + `totals` is sufficient to render any option. For
food, Businesses **SHOULD** put speed or slot in `title` (e.g., "Priority
Delivery", "Scheduled Delivery, 9:30 PM") and provide
`earliest_fulfillment_time` / `latest_fulfillment_time` so Platforms can show
an arrival or ready window. Pickup options **MAY** have empty `totals`; Platforms
**SHOULD** render a `0` or missing amount as "Free".

```text
Delivery to 450 Serra Mall, Apt 3B                      [ Change ]
 ( ) Priority Delivery            6:25–6:35 PM               $5.99
     Sent directly to you with no other stops
 (•) Standard Delivery            6:35–6:50 PM               $2.99
```

## Available Methods

`available_methods[]` tells the Platform whether delivery and pickup are
offered for this establishment right now, later, or not at all, following
[Shopping Fulfillment — Available Methods](../../shopping/extensions/fulfillment.md#available-methods):

- `fulfillable_on: "now"` — available immediately.
- An RFC 3339 timestamp — available from that time (e.g., delivery starts at
  5:00 PM for dinner service).
- Absent from the array — not offered (e.g., a pickup-only bakery).

<!-- ucp:example schema=food/types/fulfillment op=read -->
```json
{
  "available_methods": [
    {
      "type": "pickup",
      "fulfillable_on": "now"
    },
    {
      "type": "delivery",
      "fulfillable_on": "2026-04-10T17:00:00-07:00",
      "description": "Delivery starts at 5:00 PM when dinner service opens"
    }
  ]
}
```

The `description` lets Platforms surface the alternative in conversation:

> 🤖 Luigi's is open for pickup now — your order would be ready in about 15
> minutes. Delivery starts at 5:00 PM if you'd rather wait.

## Guidelines

### Platform

- **MUST** omit `requested_fulfillment_time` for ASAP orders and send an RFC 3339
  timestamp with a UTC offset for scheduled orders.
- **MUST** select only `id` values present in `preference_options[]`.
- **MUST** put courier instructions in `methods[].notes`, not in
  `line_items[].dish.note`.
- **SHOULD** offer every method in `available_methods[]`, and render each
  option's window and price.

### Business

- **MUST** return `destination.type` and `destination.id` whenever `destination`
  is present.
- **MUST** validate delivery addresses against the delivery zone and return
  `address_undeliverable` with `path` pointing to the destination when the
  address cannot be served.
- **MUST** treat an omitted `requested_fulfillment_time` as ASAP and **MUST**
  answer an unavailable requested time with a recoverable error; **SHOULD** provide
  alternative `options[]` as well when requested time is unavailable.
- **MUST** reflect the selected option's price in checkout `totals[]` as
  `type: "fulfillment"` and recompute tax, fees, and percentage tips when the
  method or option changes.
- **SHOULD** pre-select a default `selected_option_id` and default drop-off
  preference so the session can reach `ready_for_complete` without extra round
  trips.

## Examples

### Switching from Delivery to Pickup

A buyer who started with delivery switches to pickup. The Platform replaces
the method; the Business returns the establishment as the destination, a
$0 pickup window, and updated totals without the delivery fee.

=== "Request (`fulfillment`)"

    <!-- ucp:example schema=food/types/fulfillment op=update direction=request -->
    ```json
    {
      "methods": [
        {
          "type": "pickup"
        }
      ]
    }
    ```

=== "Response (`fulfillment`)"

    <!-- ucp:example schema=food/types/fulfillment op=read -->
    ```json
    {
      "available_methods": [
        { "type": "delivery", "fulfillable_on": "now" },
        { "type": "pickup", "fulfillable_on": "now" }
      ],
      "methods": [
        {
          "id": "method_pickup",
          "type": "pickup",
          "destination": {
            "id": "est_luigis_01",
            "type": "business_location",
            "name": "Luigi's Artisan Pizzeria",
            "address": {
              "street_address": "210 University Ave",
              "address_locality": "Palo Alto",
              "address_region": "CA",
              "postal_code": "94301",
              "address_country": "US"
            }
          },
          "selected_option_id": "opt_pickup_asap",
          "options": [
            {
              "id": "opt_pickup_asap",
              "title": "Counter Pickup",
              "earliest_fulfillment_time": "2026-04-10T18:15:00-07:00",
              "latest_fulfillment_time": "2026-04-10T18:25:00-07:00",
              "totals": [{ "type": "total", "amount": 0 }]
            }
          ]
        }
      ]
    }
    ```

=== "Response (`totals`)"

    <!-- ucp:example schema=food/checkout target=$.totals op=read -->
    ```json
    [
      { "type": "subtotal", "display_text": "Subtotal", "amount": 5000 },
      { "type": "fulfillment", "display_text": "Pickup", "amount": 0 },
      { "type": "tax", "display_text": "Tax (8.75%)", "amount": 438 },
      { "type": "tip", "display_text": "Staff Tip (10%)", "amount": 500 },
      { "type": "total", "display_text": "Total", "amount": 5938 }
    ]
    ```

## Security & Privacy Considerations

A `destination` with type `delivery_address` carries precise Buyer location data. The following considerations mirror the
[Location capability's Security & Privacy Considerations](../../common/location/index.md#security-privacy-considerations)
and apply to any `postal_address` or `geo` exchanged through this extension.

### Consistency

`postal_address` and `geo` **MAY** both be present on a `destination`. When they are, Businesses **SHOULD** treat `geo`
as authoritative for dispatch and routing, since it is unambiguous, and treat `postal_address` as authoritative for
display and manual verification. Platforms and Businesses **SHOULD** keep the two in sync when either is updated, and Businesses
**SHOULD** flag a destination for review rather than silently discarding one value if the two appear to resolve
to materially different physical locations.
