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

**Version:** `2026-01-11`

## Overview

The fulfillment extension enables businesses to advertise support for physical
goods fulfillment (shipping, pickup, etc).

This extension adds a `fulfillment` field to Checkout containing:

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

{{ extension_fields('fulfillment_resp', 'fulfillment') }}

### Entities

#### Fulfillment

{{ schema_fields('types/fulfillment_resp', 'fulfillment') }}

#### Fulfillment Method Response

{{ schema_fields('types/fulfillment_method_resp', 'fulfillment') }}

#### Fulfillment Destination Response

{{ schema_fields('types/fulfillment_destination_resp', 'fulfillment') }}

#### Shipping Destination Response

{{ schema_fields('types/shipping_destination_resp', 'fulfillment') }}

#### Retail Location Response

{{ schema_fields('types/retail_location_resp', 'fulfillment') }}

#### Fulfillment Group Response

{{ schema_fields('types/fulfillment_group_resp', 'fulfillment') }}

#### Fulfillment Option Response

{{ schema_fields('types/fulfillment_option_resp', 'fulfillment') }}

#### Fulfillment Available Method Response

{{ schema_fields('types/fulfillment_available_method_resp', 'fulfillment') }}

#### Total Response

{{ schema_fields('types/total_resp', 'fulfillment') }}

#### Postal Address

{{ schema_fields('postal_address', 'fulfillment') }}

### Example

```json
{
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

```json
{
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

## Configuration

Businesses and platforms declare fulfillment constraints in their profiles.
Businesses fetch platform profiles to adapt responses accordingly.

### Platform Profile

Platforms declare their rendering capabilities using `platform_schema`:

{{ schema_fields('types/platform_fulfillment_config', 'fulfillment') }}

Platforms that omit config or set `supports_multi_group: false` receive
single-group responses. The response shape is always
`methods[].groups[]`—the difference is whether `groups.length` can exceed 1
within each method.

```json
// Default: single group per method
{ "dev.ucp.shopping.fulfillment": [{"version": "2026-01-11"}] }

// Opt-in: business MAY return multiple groups per method
{ "dev.ucp.shopping.fulfillment": [{"version": "2026-01-11", "config": { "supports_multi_group": true }}] }
```

### Business Profile

Businesses declare what fulfillment configurations they support using
`merchant_config`:

{{ schema_fields('types/merchant_fulfillment_config', 'fulfillment') }}

```json
{
  "capabilities": {
    "dev.ucp.shopping.fulfillment": [
      {
        "version": "2026-01-11",
        "config": {
          "allows_multi_destination": {
            "shipping": true
          },
          "allows_method_combinations": [["shipping", "pickup"]]
        }
      }
    ]
  }
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

### Adding New Methods

Extensions that extend fulfillment with new method types (e.g.,
`local_delivery`) **MUST** add an extension schema that:

1. Adds the method to the `type` enum in `fulfillment_method`
2. Adds corresponding business config options:
    * `allows_multi_destination.local_delivery: boolean`
    * `allows_method_combinations` items enum (includes `"local_delivery"`)

Note: Platform's `supports_multi_group` is method-agnostic (single boolean),
so no extension needed.

## Examples

### Basic

**Config:** None required (default behavior)

```json
{
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

```json
{
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

```json
{
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
