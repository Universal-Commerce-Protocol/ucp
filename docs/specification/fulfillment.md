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

The fulfillment extension enables businesses to advertise support for physical
goods fulfillment (shipping, pickup, etc).

This extension adds a `fulfillment` field to Checkout and/or Catalog:

* **Checkout** (`dev.ucp.shopping.checkout`) — selection and cost: which
    items go where, by which method, at what price and ETA.
* **Catalog** (`dev.ucp.shopping.catalog.search` and
    `dev.ucp.shopping.catalog.lookup`) — discovery: a variant advertises the
    fulfillment options available for it, based on the provided buyer
    context. See [Catalog Discovery](#catalog-discovery).

On Checkout, the `fulfillment` field contains:

* `methods[]` — fulfillment methods applicable to cart items (shipping, pickup, etc.)
    * `line_item_ids` — which items this method fulfills
    * `destinations[]` — where to fulfill (address, store location)
    * `groups[]` — business-generated packages, each with selectable `options[]`
* `available_methods[]` — inventory availability per item (optional)

**Mental model:**

* `methods[0]` Shipping
    * `line_item_ids` 👕👖
    * `selected_destination_id` = `destinations[0].id` 🔘✅ 123 Fake St
    * `groups[0]` 📦👕👖
        * `selected_option_id` = `options[0].id` 🔘✅ Standard $5
        * `options[1]` 🔘 Express $10
* `methods[1]` Pick Up in Store
    * `line_item_ids` 👞
    * `selected_destination_id` = `destinations[0].id` 🔘✅ Uptown Store
    * `groups[0]` 📦👞
        * `selected_option_id` = `options[0].id` 🔘✅ In-Store Pickup
        * `options[1]` 🔘 Curbside Pickup

## Schema

Fulfillment applies only to items requiring physical delivery. Items not
requiring fulfillment (e.g., digital goods) do not need to be assigned to a
method.

### Properties

{{ extension_fields('fulfillment', 'fulfillment') }}

### Entities

#### Fulfillment

{{ schema_fields('types/fulfillment_resp', 'fulfillment') }}

#### Fulfillment Method

{{ schema_fields('types/fulfillment_method_resp', 'fulfillment') }}

#### Fulfillment Destination

{{ schema_fields('types/fulfillment_destination_resp', 'fulfillment') }}

#### Shipping Destination

{{ schema_fields('types/shipping_destination_resp', 'fulfillment') }}

#### Retail Location

{{ schema_fields('types/retail_location_resp', 'fulfillment') }}

#### Fulfillment Group

{{ schema_fields('types/fulfillment_group_resp', 'fulfillment') }}

#### Fulfillment Option

{{ schema_fields('types/fulfillment_option_resp', 'fulfillment') }}

#### Fulfillment Available Method

{{ schema_fields('types/fulfillment_available_method_resp', 'fulfillment') }}

#### Total

{{ schema_fields('types/total_resp', 'fulfillment') }}

#### Postal Address

{{ schema_fields('postal_address', 'fulfillment') }}

### Example

<!-- ucp:example schema=shopping/checkout op=read -->
```json
{
  "ucp": { ... },
  "id": "...",
  "status": "...",
  "currency": "...",
  "line_items": [ ... ],
  "totals": [ ... ],
  "links": [ ... ],
  "fulfillment": {
    "methods": [
      {
        "id": "method_1",
        "type": "shipping",
        "line_item_ids": ["shirt", "pants"],
        "selected_destination_id": "dest_1",
        "destinations": [
          {
            "id": "dest_1",
            "street_address": "123 Main St",
            "address_locality": "Springfield",
            "address_region": "IL",
            "postal_code": "62701",
            "address_country": "US"
          }
        ],
        "groups": [
          {
            "id": "package_1",
            "line_item_ids": ["shirt", "pants"],
            "selected_option_id": "standard",
            "options": [
              {
                "id": "standard",
                "title": "Standard Shipping",
                "description": "Arrives Dec 12-15 via USPS",
                "totals": [
                  {
                    "type": "total",
                    "amount": 500
                  }
                ]
              },
              {
                "id": "express",
                "title": "Express Shipping",
                "description": "Arrives Dec 10-11 via FedEx",
                "totals": [
                  {
                    "type": "total",
                    "amount": 1000
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  }
}
```

## Rendering

Fulfillment options are designed for **method-agnostic rendering**. Platforms
do not need to understand specific method types (shipping, pickup, etc.) to
present options meaningfully. The business provides precomputed,
human-readable fields that platforms render directly.

### Human-Readable Fields

| Location              | Field         | Required | Purpose                                                 |
| --------------------- | ------------- | -------- | ------------------------------------------------------- |
| `groups[].options[]`  | `title`       | Yes      | Primary label that distinguishes from siblings          |
| `groups[].options[]`  | `description` | No       | Supplementary context for the title                     |
| `groups[].options[]`  | `total`       | Yes      | Price in minor units (may be null if not yet available) |
| `available_methods[]` | `description` | No       | Standalone explanation of alternative availability      |

### Business Responsibilities

**For `options[].title`:**

* **MUST** distinguish this option from its siblings
* **SHOULD** include method and speed (e.g., "Express Shipping", "Curbside Pickup")
* **MUST** be sufficient for buyer decision if `description` is absent

**For `options[].description`:**

* **MUST NOT** repeat `title` or `total`—provides supplementary context only
* **SHOULD** include timing, carrier, or other decision-relevant details
* **SHOULD** be a complete phrase (e.g., "Arrives Dec 12-15 via FedEx")
* **MAY** be omitted if title is self-explanatory

**For `available_methods[].description`:**

* **MUST** be a standalone sentence explaining what, when, and where
* **SHOULD** be usable verbatim in platform dialogue (e.g., "Pants available
    for pickup at Downtown Store today at 2pm")

**For ordering:**

* Businesses **SHOULD** return `options[]` in a meaningful order (e.g., cheapest
    first, fastest first)
* Platforms **SHOULD** render options in the provided order

### Platform Responsibilities

Platforms **SHOULD** treat fulfillment as a generic, renderable structure:

* Render each option as a card using `title`, `description`, and `total`
* Present options in the order provided by the business
* Present all methods returned—method selection is a buyer decision
* Use `available_methods[].description` to surface alternatives to the buyer

Platforms **MAY** provide enhanced UX for recognized method types (store
selectors
for pickup, carrier logos for shipping), but this is optional. The baseline
contract is: **`title` + `description` + `total` is sufficient to render any
option.**

When a buyer selects an option the platform cannot fully process, the
platform **SHOULD** use `continue_url` to hand off to the business's checkout.

## Available Methods

Available methods indicate whether an item can be fulfilled with a given
method, and when. Use cases:

* **Alternative methods**: "These pants are also available for pickup at Downtown Store"
* **Fulfill later**: Preorders, items shipping from a distant warehouse, pickup when store gets inventory

<!-- ucp:example schema=shopping/checkout op=read -->
```json
{
  "ucp": { ... },
  "id": "...",
  "status": "...",
  "currency": "...",
  "line_items": [ ... ],
  "totals": [ ... ],
  "links": [ ... ],
  "fulfillment": {
    "methods": [
      {
        "id": "shipping",
        "type": "shipping",
        "line_item_ids": ["shirt", "pants"]
      },
      {
        "id": "pickup",
        "type": "pickup",
        "line_item_ids": []
      }
    ],
    "available_methods": [
      {
        "type": "shipping",
        "line_item_ids": ["shirt", "pants"],
        "fulfillable_on": "now"
      },
      {
        "type": "pickup",
        "line_item_ids": ["pants"],
        "fulfillable_on": "2026-12-01T10:00:00Z",
        "description": "Available for pickup at Downtown Store today at 2pm"
      }
    ]
  }
}
```

The `description` field enables platforms to surface alternatives to buyers:

> 🤖 The shirt and pants ship for $5, arriving in 5-8 days. Or the pants can
> be picked up at Downtown Store in 4 hours.

If the buyer chooses pickup but the platform doesn't support split
fulfillment, the platform **SHOULD** use `continue_url` to hand off to the
business's checkout.

## Catalog Discovery

When the fulfillment extension extends the Catalog capability, each variant
in a catalog response carries a `fulfillment` object listing the fulfillment
methods available for that variant and where each can be received — so a
buyer browsing the catalog can see how an item can be received before
reaching checkout.

### Methods and destinations

`fulfillment.methods[]` lists the methods available for a variant. Each
method has:

* `type` — the fulfillment method (e.g. `shipping`, `pickup`); see
    [Method Types](#method-types).
* `destinations[]` — where the item is received via this method, each with
    its own `availability`.

Each destination has:

* `id` — the destination identifier. For `shipping` it is `address` (the
    buyer's address, supplied on the request); otherwise it is the store or
    location id.
* `name` and `address` — the location's name and address, when it has one.
* `availability` — whether the variant is available via this method at this
    destination.

A method's `type` tells you what kind of destination it carries. Catalog
only advertises these options; the buyer commits at checkout. A destination
`id` found here can be passed to cart or checkout as
`selected_destination_id`, though checkout can also present its own
destinations to choose from.

### Shapes

#### Catalog Fulfillment Method

{{ extension_schema_fields('fulfillment.json#/$defs/catalog_fulfillment_method', 'fulfillment') }}

#### Catalog Destination

{{ schema_fields('types/catalog_destination', 'fulfillment') }}

#### Availability

{{ schema_fields('types/availability', 'fulfillment') }}

### Location: `context` and `filters.fulfills_to`

The buyer's location can reach a catalog request two ways. They are distinct
use cases:

* **`context`** (the buyer's coarse address — `address_country` /
    `address_region` / `postal_code`) is a non-binding hint. The business
    uses it to report `availability` on the methods it returns: *"given
    roughly where I am, where is this available?"* It does not remove
    results — you still see the variant, annotated with availability.
* **`filters.fulfills_to`** (a postal address) is a filter. It *restricts*
    results to variants the business can fulfill to that destination:
    *"only show me what I can actually get here."* Like any filter, it
    narrows the result set.

When both are present, `fulfills_to` is authoritative and wins; `context`
is the fallback.

`fulfills_to` takes an address, not a store id; filtering by a specific
store or locker is not part of this capability.

### Example

A variant exposes two fulfillment methods: shipping to the buyer's ship-to
and pickup today at a named store. Each method carries its own destinations,
each with its own availability.

<!-- ucp:example schema=shopping/fulfillment def=fulfillment_search_response op=read -->
```json
{
  "ucp": { "version": "{{ ucp_version }}" },
  "products": [
    {
      "id": "prod_kettle",
      "title": "Electric Kettle",
      "description": { "plain": "1.7L electric kettle." },
      "price_range": {
        "min": { "amount": 4999, "currency": "USD" },
        "max": { "amount": 4999, "currency": "USD" }
      },
      "variants": [
        {
          "id": "var_ss",
          "title": "Stainless Steel",
          "description": { "plain": "Stainless steel finish." },
          "price": { "amount": 4999, "currency": "USD" },
          "availability": { "available": true, "status": "in_stock" },
          "fulfillment": {
            "methods": [
              {
                "type": "shipping",
                "description": { "plain": "Ships to your address" },
                "destinations": [
                  {
                    "id": "address",
                    "availability": { "available": true, "status": "in_stock" }
                  }
                ]
              },
              {
                "type": "pickup",
                "description": { "plain": "Pickup today at Downtown Store" },
                "destinations": [
                  {
                    "id": "loc_downtown",
                    "name": "Downtown Store",
                    "address": {
                      "address_locality": "Toronto",
                      "address_region": "ON",
                      "address_country": "CA",
                      "postal_code": "M5B 2H1"
                    },
                    "availability": { "available": true, "status": "in_stock" }
                  }
                ]
              }
            ]
          }
        }
      ]
    }
  ]
}
```

Each method gives the buyer a way to receive the item, with its own
`availability`. Each method's `description` is directly renderable, so a
platform can present it without recognizing the `type` (see
[Rendering](#rendering)).

## Configuration

Businesses and platforms declare fulfillment constraints in their profiles.
Businesses fetch platform profiles to adapt responses accordingly.

The `extends` array lists the capabilities this extension adds fulfillment
to. Checkout is the authoritative, transactional surface; catalog is for
discovery. A business lists the catalog capabilities in `extends` to expose
fulfillment on catalog, or omits them to scope itself to checkout only.

### Platform Profile

Platforms declare their rendering capabilities using `platform_schema`:

{{ schema_fields('types/platform_fulfillment_config', 'fulfillment') }}

Platforms that omit config or set `supports_multi_group: false` receive
single-group responses. The response shape is always
`methods[].groups[]`—the difference is whether `groups.length` can exceed 1
within each method.

Default declaration (single group per method; fulfillment surfaced on
checkout and on catalog discovery):

<!-- ucp:example schema=profile def=platform_schema target=$.ucp.capabilities -->
```json
{
  "dev.ucp.shopping.fulfillment": [
    {
      "version": "{{ ucp_version }}",
      "spec": "https://ucp.dev/{{ ucp_version }}/specification/fulfillment",
      "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/fulfillment.json",
      "extends": [
        "dev.ucp.shopping.checkout",
        "dev.ucp.shopping.catalog.search",
        "dev.ucp.shopping.catalog.lookup"
      ]
    }
  ]
}
```

A party that does not expose catalog discovery MAY narrow `extends` to
`"dev.ucp.shopping.checkout"` (string form) or to a single-element array.

Opt-in declaration (business MAY return multiple groups per method):

<!-- ucp:example schema=profile def=platform_schema target=$.ucp.capabilities -->
```json
{
  "dev.ucp.shopping.fulfillment": [
    {
      "version": "{{ ucp_version }}",
      "spec": "https://ucp.dev/{{ ucp_version }}/specification/fulfillment",
      "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/fulfillment.json",
      "extends": [
        "dev.ucp.shopping.checkout",
        "dev.ucp.shopping.catalog.search",
        "dev.ucp.shopping.catalog.lookup"
      ],
      "config": { "supports_multi_group": true }
    }
  ]
}
```

### Business Profile

Businesses declare what fulfillment configurations they support using
`merchant_config`:

{{ schema_fields('types/merchant_fulfillment_config', 'fulfillment') }}

<!-- ucp:example schema=profile def=business_schema target=$.ucp.capabilities -->
```json
{
  "dev.ucp.shopping.fulfillment": [
    {
      "version": "{{ ucp_version }}",
      "spec": "https://ucp.dev/{{ ucp_version }}/specification/fulfillment",
      "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/fulfillment.json",
      "extends": [
        "dev.ucp.shopping.checkout",
        "dev.ucp.shopping.catalog.search",
        "dev.ucp.shopping.catalog.lookup"
      ],
      "config": {
        "allows_multi_destination": {
          "shipping": true
        },
        "allows_method_combinations": [["shipping", "pickup"]]
      }
    }
  ]
}
```

This example says: shipping can go to multiple addresses, and carts can mix
shipping+pickup.

### Business Response Behavior

**When `supports_multi_group: false` (default):**

* Business **MUST** consolidate all items into a **single group per method**
* Response still uses array structure: `methods[].groups[]` with `groups.length === 1`
* Business **MAY** still return multiple methods (e.g., shipping + pickup) if
    cart items require it

**When `supports_multi_group: true`:**

* Business **MAY** return multiple groups per method based on inventory,
    packaging, or warehouse logic
* Platform is responsible for rendering group selection UI (e.g., choose
    shipping speed per package)

### Method Types

`fulfillment_method.type` (checkout) and `catalog_fulfillment_method.type`
(catalog) share one vocabulary of fulfillment method types. The field is an
open string: consumers ignore values they do not recognize.

**Well-known values:**

| Value | Meaning |
| --- | --- |
| `shipping` | Carrier ships to the buyer's address. |
| `pickup` | Buyer picks up at a named location. |

**Adding method types.** `type` is an open string: businesses MAY use
additional values, and consumers ignore values they do not recognize. New
well-known values are added via a UCP RFC and a `dev.ucp.shopping.fulfillment`
version bump.

## Examples

### Basic

**Config:** None required (default behavior)

<!-- ucp:example schema=shopping/checkout op=read -->
```json
{
  "ucp": { ... },
  "id": "...",
  "status": "...",
  "currency": "...",
  "line_items": [ ... ],
  "totals": [ ... ],
  "links": [ ... ],
  "fulfillment": {
    "methods": [
      {
        "id": "method_1",
        "type": "shipping",
        "line_item_ids": ["shirt", "pants"],
        "selected_destination_id": "dest_1",
        "destinations": [
          {
            "id": "dest_1",
            "street_address": "123 Main St",
            "address_locality": "Springfield",
            "address_region": "IL",
            "postal_code": "62701",
            "address_country": "US"
          }
        ],
        "groups": [
          {
            "id": "package_1",
            "line_item_ids": ["shirt", "pants"],
            "selected_option_id": "standard",
            "options": [
              {
                "id": "standard",
                "title": "Standard Shipping",
                "description": "Arrives Dec 12-15 via USPS",
                "totals": [
                  {
                    "type": "total",
                    "amount": 500
                  }
                ]
              },
              {
                "id": "express",
                "title": "Express Shipping",
                "description": "Arrives Dec 10-11 via FedEx",
                "totals": [
                  {
                    "type": "total",
                    "amount": 1000
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  }
}
```

### Split Groups

**Config:** Platform profile requires `config.supports_multi_group: true`

Business splits items into multiple packages; buyer selects shipping rate per
package.

<!-- ucp:example schema=shopping/checkout op=read -->
```json
{
  "ucp": { ... },
  "id": "...",
  "status": "...",
  "currency": "...",
  "line_items": [ ... ],
  "totals": [ ... ],
  "links": [ ... ],
  "fulfillment": {
    "methods": [
      {
        "id": "method_1",
        "type": "shipping",
        "line_item_ids": ["shirt", "pants"],
        "selected_destination_id": "dest_1",
        "destinations": [
          {
            "id": "dest_1",
            "street_address": "123 Main St",
            "address_locality": "Springfield",
            "address_region": "IL",
            "postal_code": "62701",
            "address_country": "US"
          }
        ],
        "groups": [
          {
            "id": "package_1",
            "line_item_ids": ["shirt"],
            "selected_option_id": "standard",
            "options": [
              {
                "id": "standard",
                "title": "Standard",
                "totals": [ {"type": "total", "amount": 500} ]
              },
              {
                "id": "express",
                "title": "Express",
                "totals": [ {"type": "total", "amount": 1000} ]
              }
            ]
          },
          {
            "id": "package_2",
            "line_item_ids": ["pants"],
            "selected_option_id": "express",
            "options": [
              {
                "id": "standard",
                "title": "Standard",
                "totals": [ {"type": "total", "amount": 500} ]
              },
              {
                "id": "express",
                "title": "Express",
                "totals": [ {"type": "total", "amount": 1000} ]
              }
            ]
          }
        ]
      }
    ]
  }
}
```

### Split Destinations

**Config:** Business profile requires
`config.allows_multi_destination.shipping: true`

Shirt ships to mom (US), pants ship to grandma (Hong Kong). Two methods of the
same type, each with its own destination.

<!-- ucp:example schema=shopping/checkout op=read -->
```json
{
  "ucp": { ... },
  "id": "...",
  "status": "...",
  "currency": "...",
  "line_items": [ ... ],
  "totals": [ ... ],
  "links": [ ... ],
  "fulfillment": {
    "methods": [
      {
        "id": "method_1",
        "type": "shipping",
        "line_item_ids": ["shirt"],
        "selected_destination_id": "dest_mom",
        "destinations": [
          {
            "id": "dest_mom",
            "street_address": "123 Mom St",
            "address_locality": "Springfield",
            "address_region": "IL",
            "postal_code": "62701",
            "address_country": "US"
          }
        ],
        "groups": [
          {
            "id": "package_1",
            "line_item_ids": ["shirt"],
            "selected_option_id": "standard",
            "options": [
              {
                "id": "standard",
                "title": "Standard",
                "totals": [
                  {
                    "type": "total",
                    "amount": 500
                  }
                ]
              },
              {
                "id": "express",
                "title": "Express",
                "totals": [
                  {
                    "type": "total",
                    "amount": 1000
                  }
                ]
              }
            ]
          }
        ]
      },
      {
        "id": "method_2",
        "type": "shipping",
        "line_item_ids": ["pants"],
        "selected_destination_id": "dest_grandma",
        "destinations": [
          {
            "id": "dest_grandma",
            "street_address": "88 Queensway",
            "address_locality": "Hong Kong",
            "address_country": "HK"
          }
        ],
        "groups": [
          {
            "id": "package_2",
            "line_item_ids": ["pants"],
            "selected_option_id": "standard",
            "options": [
              {
                "id": "standard",
                "title": "Standard",
                "totals": [
                  {
                    "type": "total",
                    "amount": 500
                  }
                ]
              },
              {
                "id": "express",
                "title": "Express",
                "totals": [
                  {
                    "type": "total",
                    "amount": 1000
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  }
}
```
