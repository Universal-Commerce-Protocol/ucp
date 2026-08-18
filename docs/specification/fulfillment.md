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

## Location Context

Base [Context](catalog/index.md#context) defines an optional `location`: a
stable, opaque [Location](glossary.md#commerce) identifier in the Business's
namespace. The field appears on Catalog requests and on Cart and Checkout
create and update requests (see [Checkout Context](checkout.md#context)).
Fulfillment does not add or redefine the field; when the Fulfillment
extension is active, it defines the field's effects.

When Fulfillment extends Catalog or Checkout, `context.location` on a request
to that capability names the provisional Business Location that the Business
evaluates fulfillment availability against, and generates initial fulfillment
choices for. It does not select a fulfillment destination.

These fields carry distinct roles, not precision levels of one value:

| Field | Role |
| --- | --- |
| `context.location` | Provisional Business Location to evaluate fulfillment against. |
| Catalog `filters.fulfills_to` | Explicit destination items are fulfilled to, and a filter on results. |
| Catalog `methods[].location` | The Business Location resolved for a place-based method (e.g. `pickup`) on a variant. |
| Checkout `methods[].selected_destination_id` | The destination selected from that method's `destinations[]`. |

Precedence is scoped to what each field governs:

* When Catalog `filters.fulfills_to` is present, a Business **MUST** resolve
    the fulfillment destination and method `availability` from it rather than
    from `context`. Other `context` fields are unaffected.
* Once a Platform sets `selected_destination_id` on a Checkout method, a
    Business **MUST** use the referenced destination rather than
    `context.location` for that method's fulfillment scope. Other methods are
    unaffected.

**Carrying a Location forward.** The same identifier can appear in several of
these fields without collapsing their roles. A Catalog response can report a
place-based method at `loc_123`. Because base Cart Context already includes
`location`, `loc_123` can travel forward as `context.location` on a Cart
request. [Cart-to-Checkout conversion](cart.md#cart-to-checkout-conversion)
initializes the Checkout from the Cart's `context`, so the Business **MAY**
use `loc_123` to generate an initial Checkout fulfillment destination. Once
the Platform sets `selected_destination_id`, that explicit selection governs.

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

#### Business Location Destination

{{ schema_fields('types/location_destination_resp', 'fulfillment') }}

#### Location Summary

{{ schema_fields('location_summary', 'fulfillment') }}

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
            "type": "shipping_address",
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

## Destinations

A fulfillment method's `type` describes how items are fulfilled, for example
by shipping or pickup. A destination's `type` describes where fulfillment
occurs, for example at a shipping address or Business Location. The two
discriminators play different roles by direction: in Business responses,
every destination carries a required `type`, so responses are
self-describing; in Platform requests, the method's contract determines who
authors `destinations[]` and MAY define a default destination shape when
`type` is omitted.

By default, the Platform does not write a method's `destinations[]`; a contract
keyed on the method's `type` **MAY** opt into a Platform-writable request
shape:

| Method `type` | Request `destinations[]` |
| --- | --- |
| `shipping` | Platform-writable. The Platform writes the Buyer's shipping-address facts. |
| `pickup` | Not Platform-writable. The Business enumerates locations in its response; the Platform selects a location by its Business-scoped ID (see [Selection and Location Identity](#selection-and-location-identity)). |
| any other method `type` | Not Platform-writable (the base default). The Business enumerates destinations in its response; the Platform selects one via `selected_destination_id`. |

Destination `type` is **required in responses and optional in requests**. In
responses, every destination carries `type`, so destinations remain
self-describing wherever they appear. In requests, `destinations[]` is omitted
unless a method-specific contract opts into a Platform-writable shape:

* Under a well-known `shipping` method, every destination is a Shipping
    Destination: a destination that omits `type` defaults to
    `shipping_address`.
* Under a well-known `pickup` method, destinations are response-only; the
    Platform selects a location via `selected_destination_id` (see
    [Selection and Location Identity](#selection-and-location-identity)).
* Under any other method type, the base default applies: `destinations[]` is
    response-only, each response destination self-describes through its
    required `type` and `id`, and the Platform selects one via
    `selected_destination_id`. That method's defining contract — a future
    revision of this specification or a negotiated extension — **MAY** narrow
    the response destination shape or opt into a Platform-writable request
    shape.

A request that includes `destinations[]` MUST also include the method's
`type`. The well-known values are:

| Value | Meaning |
| --- | --- |
| `shipping_address` | A Shipping Destination with flat Postal Address fields. |
| `business_location` | A Business Location Destination identified by a Business-scoped `id`. |

Additional values are defined by negotiated extensions. Destination fields
specific to such a value are validated by the negotiated extension's schema.

### Shipping Destination

A Shipping Destination can contain the address itself or an `id` that
references a saved address. The Business can resolve that `id` from its own
records or through a trusted Credential Provider, such as a digital wallet or
identity provider.

#### Platform Request

<!-- ucp:example schema=shopping/types/shipping_destination op=update direction=request -->
```json
{
  "street_address": "123 Main St",
  "address_locality": "Springfield",
  "address_region": "IL",
  "postal_code": "62701",
  "address_country": "US"
}
```

#### Business Response

<!-- ucp:example schema=shopping/types/shipping_destination op=read direction=response -->
```json
{
  "type": "shipping_address",
  "id": "dest_1",
  "street_address": "123 Main St",
  "address_locality": "Springfield",
  "address_region": "IL",
  "postal_code": "62701",
  "address_country": "US"
}
```

### Business Location Destination

Business Location Destinations appear only in responses; `destinations[]` on a
`pickup` method is not a request field. The Platform **MUST NOT** write
Business Location Destinations into `destinations[]`; it selects a location by
submitting its stable, opaque, Business-scoped ID as
`selected_destination_id`. The Business **MUST** return
`type: "business_location"`, `id`, and its Buyer-facing `name`, and **MAY**
return its Postal Address in `address`.

#### Platform Request

<!-- ucp:example schema=shopping/types/fulfillment_method op=update direction=request -->
```json
{
  "type": "pickup",
  "line_item_ids": ["shirt", "pants"],
  "selected_destination_id": "loc_downtown"
}
```

#### Business Response

<!-- ucp:example schema=shopping/types/location_destination op=read direction=response -->
```json
{
  "type": "business_location",
  "id": "loc_downtown",
  "name": "Downtown Store",
  "address": {
    "street_address": "123 Main St",
    "address_locality": "Springfield",
    "address_region": "IL",
    "postal_code": "62701",
    "address_country": "US"
  }
}
```

### Selection and Location Identity

`selected_destination_id` identifies the selected destination in a method by
its `id`, and is the sole channel for selecting a Business Location. It accepts
any stable, Business-scoped ID the Business recognizes for that method,
including an ID the Business has not (yet) enumerated in that method's
`destinations[]`.

Selection is source-agnostic. A non-null `selected_destination_id` **MAY**
carry an ID the Platform obtained from a Catalog response, a Location search
or lookup, an earlier Checkout, or any other source the Business recognizes
for that method. Where the ID came from does not change the contract below.

When the Business accepts a non-null `selected_destination_id`, its response:

* **MUST** carry that same `selected_destination_id` value on the method; and
* **MUST** include exactly one destination in that same method's
    `destinations[]` whose `id` equals it, typed as specified in
    [Destinations](#destinations) — so the response is self-describing whatever
    the ID's source.

The Business **MUST** revalidate the selected destination's current
availability and terms; recognizing an ID neither reserves inventory nor
guarantees eligibility. The Business **MUST NOT** silently substitute another
destination: it **MUST NOT** return a different `selected_destination_id`, and
**MUST NOT** keep the submitted ID while returning a destination that
describes another location. A Business that cannot honor the submitted
selection rejects it rather than replacing it.

When the Business cannot accept a `selected_destination_id` submitted on
[Update Checkout](checkout.md#update-checkout) — the ID is not recognized for
that method, or revalidation fails — it follows the general behavior for a
rejected Update: it **MUST** leave the current Checkout unchanged and
**MUST** return that Checkout with an error Message with
`severity: "recoverable"` whose `path` selects the attempted method's
`selected_destination_id` (for example
`$.fulfillment.methods[0].selected_destination_id`). See
[Error Handling](checkout.md#error-handling) and
[The `path` Field](checkout.md#the-path-field).

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
* `location` — for place-based methods such as `pickup`, the
    [Location](glossary.md#commerce) resolved for that method and the
    Business's stable identifier for that place. A Business that advertises
    pickup at a `location` **MUST** accept that same ID as
    `selected_destination_id` for that method in Checkout. The Business
    revalidates current availability and terms; discovery neither reserves
    inventory nor guarantees eligibility. The selection contract is
    source-agnostic; see
    [Selection and Location Identity](#selection-and-location-identity).
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
options — not an exhaustive list. Without a destination or full cart, a
Business **SHOULD** preview meaningful boundary options for the Buyer (e.g.
cheapest, fastest); more specific options are negotiated in Checkout once the
line items and destination are known.

Each option carries an `id` and a `title` (a short label distinguishing it
from siblings), plus an optional renderable `description` for context. These
are a shared base: at checkout the same option is composed with cost and
timing (`totals`, carrier, fulfillment times). The option is open, so a
business MAY annotate it with additional fields. A method MAY also carry
none, surfacing only `type`, `description`, and `availability`; options are
nested directly under the method, with no group layer (unlike checkout
`methods[].groups[].options[]`).

A discovered option `id` lets a Buyer's choice carry forward: a Business
**SHOULD** accept the same ID as `methods[].groups[].selected_option_id` in
Checkout. The ID is a best-effort handle, not a guaranteed match — an option
discovered for a single product may differ at Checkout, where other products,
quantities, and combined fulfillment modify the options.

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

* **`context`** carries non-binding hints the Business uses to report
    `availability`: coarse locality fields for where the *Buyer* is, and
    `location` for a provisional Business Location (see
    [Location Context](#location-context)). On a market-scoped Catalog a
    Business **MAY** narrow results with these hints; otherwise they annotate
    results rather than remove them.
* **`filters.fulfills_to`** is where items are *fulfilled to* — a single
    destination
    ([Fulfillment Destination Filter](#fulfillment-destination-filter)),
    named by value (a coarse locality) or by reference (a `location` id — a
    store, pickup point, or saved address). Platforms **SHOULD** provide one
    or the other, not both; if both are present, a business **SHOULD** use
    the more specific — typically `location`. It restricts results to what
    can be fulfilled there and seeds method `availability`, and may differ
    from `context` (e.g. a gift).
* **`filters.methods`** restricts results to specific method types (e.g.
    `["pickup"]`).

`context` only hints; `fulfills_to` names the destination. See
[Location Context](#location-context) for the precedence rule.

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
so a cart can mix shipped and installed items (see
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
            "type": "shipping_address",
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
            "type": "shipping_address",
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
            "type": "shipping_address",
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
            "type": "shipping_address",
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
