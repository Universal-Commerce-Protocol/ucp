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
goods fulfillment (shipping, pickup, etc). Each parent capability opts in
independently, with a parent-specific projection:

* **Checkout** (`dev.ucp.shopping.checkout`) — location-aware context plus
    selection and cost: which items go where, by which method, at what price
    and ETA.
* **Cart** (`dev.ucp.shopping.cart`) — location-aware context only; it does not
    add methods, destinations, groups, options, or selection IDs.
* **Catalog** (`dev.ucp.shopping.catalog.search` and
    `dev.ucp.shopping.catalog.lookup`) — location-aware request context and
    discovery: a variant advertises the fulfillment options available for it.
    See [Catalog Discovery](#catalog-discovery).

On Checkout, the `fulfillment` field contains:

* `methods[]` — fulfillment methods applicable to line items (shipping, pickup, etc.)
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

### Location Context

Fulfillment adds an optional `location` to the parent `context`. `location` is
accepted on Catalog requests and on Cart and Checkout Create and Update
requests.

These fields have distinct semantic roles; they are not precision levels of the
same location:

| Field | Role |
| --- | --- |
| `context.location` | Provisional, non-binding Business-location anchor for location-scoped pricing, availability, estimates, or initial options—roughly, “evaluate this experience at this Business location.” |
| Catalog `filters.fulfills_to` | Explicit fulfillment destination and filter: “can this be fulfilled to here?” |
| Catalog response `variants[].fulfillment.methods[].location` | Business location for which the availability of a place-based method was resolved. |
| Checkout `selected_destination_id` or authoritative fulfillment address | Explicit destination for the affected fulfillment scope; it supersedes `context.location` there. |

**Continuity example.** The same Business-scoped Location Identifier can appear
in different fields without collapsing their roles. Catalog may report a
place-based method at `loc_123`. A Platform continuing that location-scoped
experience can carry `loc_123` as Cart `context.location`. Cart-to-Checkout
conversion carries `context.location` into Checkout, allowing the Business to
surface that location as the initial fulfillment choice. Once the Platform
selects it through `selected_destination_id`, it becomes the explicit
destination for the affected fulfillment scope.

#### Platform

* A Platform **MUST NOT** send a location ID established by one Business to a
    different Business. It **MAY** provide an ID learned from a Fulfillment
    response or another mechanism operated by the same Business.
* A Platform **MUST NOT** treat `context.location` as a binding fulfillment
    destination.

#### Business

* A Business **MUST** ignore an unknown or inapplicable `context.location` and
    return a successful response for an otherwise valid request. It **MAY**
    report the ignored value through a warning in `messages[]`.
* Catalog confirms resolution through the applicable
    `variants[].fulfillment.methods[].location`; top-level response context is
    not part of this extension's Catalog response contract.
* For Catalog fulfillment destination and availability resolution, a Business
    **MUST** use explicit `filters.fulfills_to` instead of
    `context.address_country`, `context.address_region`, `context.postal_code`,
    or `context.location`. For the Checkout scope governed by an
    explicit `selected_destination_id` or authoritative fulfillment address,
    the Business **MUST** use that destination or address instead of
    `context.location`.

## Schema

Fulfillment applies only to items requiring physical delivery. Items not
requiring fulfillment (e.g., digital goods) do not need to be assigned to a
method.

### Properties

{{ extension_fields('fulfillment', 'fulfillment') }}

### Entities

#### Fulfillment

{{ schema_fields('types/fulfillment_resp', 'fulfillment') }}

#### Fulfillment Context

{{ extension_schema_fields('fulfillment.json#/$defs/fulfillment_context', 'fulfillment') }}

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
                "description": { "plain": "Arrives Dec 12-15 via USPS" },
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
                "description": { "plain": "Arrives Dec 10-11 via FedEx" },
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
| `groups[].options[]`  | `totals`      | Yes      | Cost breakdown: an array of `total` objects             |
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
* Platforms **SHOULD** preserve that order, but **MAY** re-order it
    (e.g. to match known buyer preferences or surface-specific ranking);
    they **MUST** preserve the method/option grouping

### Platform Responsibilities

Platforms **SHOULD** treat fulfillment as a generic, renderable structure:

* Render each option as a card using `title`, `description`, and `total`
* Present all methods returned—method selection is a buyer decision
* Preserve the method and option structure—do not merge or de-duplicate;
    the platform chooses ordering
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
methods available for that variant and their availability — so a buyer
browsing the catalog can see how an item can be fulfilled.

### Methods

`fulfillment.methods[]` lists the methods available for a variant. Each
method has:

* `type` — the fulfillment method (e.g. `shipping`, `pickup`); see
    [Method Types](#method-types).
* `description` — short, buyer-facing summary of how the variant is
    fulfilled via this method (e.g. "Ships in 2–4 business days"). Directly
    renderable; see [Rendering](#rendering).
* `availability` — whether the variant is available via this method at the
    specified or inferred location.
* `location` — for place-based methods (e.g. `pickup`), the resolved
    [Location Identifier](glossary.md#commerce) for that method. Across UCP
    surfaces exposed by the same Business, the same value identifies the same
    location; the containing field defines that location's role. A Business
    that advertises pickup at a `location` **MUST** accept that same ID as
    `selected_destination_id` for that method in Checkout.
* `options` — concrete fulfillment choices within this method (e.g.
    Standard, Express); see [Options](#options). Optional.

Catalog reports availability for a single location per method — the one
specified via `fulfills_to` or inferred from `context`; discovering and
comparing other locations is handled separately.

The variant-level `availability` indicates whether the variant is
obtainable via *any* method; a method's own `availability` is authoritative
for that method. Where a method states `availability`, consumers MUST use
it for that method and MUST NOT infer per-method availability from the
variant-level value.

### Options

A method MAY carry `options[]`, a representative subset of its fulfillment
options — not an exhaustive list. Without a destination or full cart,
catalog SHOULD preview meaningful boundary options for the buyer (e.g.
cheapest, fastest); the full, high-resolution set is negotiated in checkout
once the line items and destination are known.

Each option carries an `id` and a `title` (a short label distinguishing it
from siblings), plus an optional renderable `description` for context. These
are a shared base: at checkout the same option is composed with cost and
timing (`totals`, carrier, fulfillment times). The option is open, so a
business MAY annotate it with additional fields. A method MAY also carry
none, surfacing only `type`, `description`, and `availability`; options are
nested directly under the method, with no group layer (unlike checkout
`methods[].groups[].options[]`).

A discovered option `id` lets a buyer's choice carry forward to Checkout: a
Business **SHOULD** accept the same ID as `selected_option_id` unless other
products, quantities, or combined fulfillment change the available options.
The ID is a best-effort handle, not a guaranteed match. Cart does not carry
option IDs or other full Fulfillment structures.

### Shapes

#### Catalog Fulfillment

{{ extension_schema_fields('fulfillment.json#/$defs/catalog_fulfillment', 'fulfillment') }}

#### Catalog Fulfillment Method

{{ extension_schema_fields('fulfillment.json#/$defs/catalog_fulfillment_method', 'fulfillment') }}

#### Fulfillment Option Base

{{ schema_fields('types/fulfillment_option_base', 'fulfillment') }}

#### Availability

{{ schema_fields('types/availability', 'fulfillment') }}

#### Fulfillment Destination Filter

{{ schema_fields('types/fulfillment_destination_filter', 'fulfillment') }}

### Location and method: `context` and `filters`

* **`context`** provides non-binding hints that a Business uses to report
    `availability`. Its coarse locality fields (`address_country` /
    `address_region` / `postal_code`) describe the Buyer's locality. Its
    `location` is a provisional Business-location anchor for store-scoped
    pricing, availability, or initial fulfillment options; it need not be the
    Buyer's physical location. On a market-scoped Catalog, the Business
    **MAY** use context to narrow results; otherwise, context annotates rather
    than removes them.
* **`filters.fulfills_to`** is where the order is *fulfilled to* — a single
    destination, named by value (a coarse address: `address_country` /
    `address_region` / `postal_code`) or by reference (a `location` id — a
    store, pickup point, or saved address). Platforms **SHOULD** provide one
    or the other, not both; if both are present, a business **SHOULD** use
    the more specific — typically `location`. It restricts results to what
    can be fulfilled there and seeds method `availability`, and may differ
    from `context` (e.g. a gift).
* **`filters.methods`** restricts results to specific method types (e.g.
    `["pickup"]`).

`context` carries non-binding Buyer locality or a provisional
Business-location anchor; `fulfills_to` names an explicit destination. When
both are present, `fulfills_to` supersedes `context.address_country`,
`context.address_region`, `context.postal_code`, or `context.location` for
fulfillment destination and availability resolution.

### Example

A variant exposes two fulfillment methods: shipping to the buyer's ship-to
and pickup today at a named store. Each method carries its own availability,
and `pickup` references the resolved location by id.

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
                "description": { "plain": "Ships to your address in 1–4 business days" },
                "availability": { "available": true, "status": "in_stock" },
                "options": [
                  {
                    "id": "std",
                    "title": "Standard",
                    "description": { "plain": "Arrives in 4 business days" }
                  },
                  {
                    "id": "exp",
                    "title": "Express",
                    "description": { "plain": "Next business day" }
                  }
                ]
              },
              {
                "type": "pickup",
                "description": { "plain": "Pickup today at Downtown Store" },
                "location": "loc_downtown",
                "availability": { "available": true, "status": "in_stock" }
              }
            ]
          }
        }
      ]
    }
  ]
}
```

Each method is a way the variant can be fulfilled, with its own
`availability`. Each method's `description` is directly renderable, so a
platform can present it without recognizing the `type` (see
[Rendering](#rendering)). The shipping method's `description` previews the
delivery range, and its `options[]` refine it (Standard, Express); pickup
carries none — `options` is optional.

## Configuration

Businesses and platforms declare fulfillment constraints in their profiles.
Businesses fetch platform profiles to adapt responses accordingly.

The `extends` array lists the parent capabilities to which this extension
applies. Checkout is the authoritative, transactional surface; catalog is for
discovery; Cart receives only location-aware context. Each parent is an
independent opt-in, so advertising fulfillment for one parent does not activate
it for another.

A Platform or Business that advertises Cart and extends either Catalog
capability with Fulfillment **SHOULD** also extend Cart with Fulfillment to
preserve `context.location` across the Catalog → Cart → Checkout journey.
Omitting the Cart projection means location-scoped Cart continuity is not
provided.

### Platform Profile

Platforms declare their rendering capabilities using `platform_schema`:

{{ schema_fields('types/platform_fulfillment_config', 'fulfillment') }}

Platforms that omit config or set `supports_multi_group: false` receive
single-group responses. The response shape is always
`methods[].groups[]`—the difference is whether `groups.length` can exceed 1
within each method.

Default declaration (single group per Checkout method; fulfillment surfaced on
Checkout and Catalog, with location context on Cart):

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
        "dev.ucp.shopping.cart",
        "dev.ucp.shopping.catalog.search",
        "dev.ucp.shopping.catalog.lookup"
      ]
    }
  ]
}
```

A Platform or Business **MAY** narrow `extends` to any parent or set of parents
it supports, using the string form for one parent or an array for several.

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
        "dev.ucp.shopping.cart",
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
`business_config`:

{{ schema_fields('types/business_fulfillment_config', 'fulfillment') }}

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
        "dev.ucp.shopping.cart",
        "dev.ucp.shopping.catalog.search",
        "dev.ucp.shopping.catalog.lookup"
      ],
      "config": {
        "multi_destination": [
          { "method": "shipping" }
        ],
        "method_combinations": [["shipping", "pickup"]]
      }
    }
  ]
}
```

This example says: shipping can go to multiple addresses, and checkout can mix
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
(catalog) share one open-string vocabulary. Presentation is method-agnostic:
platforms **SHOULD** present every method, rendering `description` and
`availability` regardless of its `type` (see [Rendering](#rendering)), and
**SHOULD NOT** omit a method solely because they do not recognize its `type`.
Recognizing a `type` only enables optional type-specific UX.

A method is identified by its `type` and its fulfillment scope (what it
fulfills and where). A business **SHOULD** model same-scope variation (e.g.
Standard vs Express) as `options`, and **SHOULD NOT** emit multiple methods
that differ only in option-level detail. Same-`type` methods are valid when
their scope differs — e.g. checkout may carry two `shipping` methods to
different destinations. In catalog a method covers a single variant at one
resolved location, so this collapses to at most one method per `type`.

**Well-known values:**

| Value | Meaning |
| --- | --- |
| `shipping` | Carrier ships to the buyer's address. |
| `pickup` | Buyer picks up at a named location. |
| `curbside` | Buyer picks up at a location without leaving their vehicle (drive-up). |

**Adding method types.** Because `type` is an open string, a business MAY
introduce a new value at any time with no consumer change: it advertises the
value (and filters on it via `filters.methods`), and consumers present it
like any other method.

**Example — adding `home_installation`.** No schema change or registration is
needed. Emit the value directly as the `type` on catalog and checkout, and
filter with `filters.methods: ["home_installation"]`. For checkout
negotiation, declare its behavior in the business profile `config` — e.g.
include `["shipping", "home_installation"]` in `method_combinations`
so a checkout can mix shipped and installed items (see
[Business Profile](#business-profile)). On a catalog variant's method:

<!-- ucp:example schema=shopping/fulfillment def=catalog_fulfillment_method op=read -->
```json
{
  "type": "home_installation",
  "description": { "plain": "Delivered and installed in your home" },
  "availability": {
    "available": true
  }
}
```

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
                "description": { "plain": "Arrives Dec 12-15 via USPS" },
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
                "description": { "plain": "Arrives Dec 10-11 via FedEx" },
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

**Config:** Business profile lists `shipping` in `config.multi_destination`

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
