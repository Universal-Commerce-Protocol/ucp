# Fulfillment Extension

## Overview

The fulfillment extension enables businesses to advertise support for physical goods fulfillment (shipping, pickup, etc).

This extension adds a `fulfillment` field to Checkout and/or Catalog:

- **Checkout** (`dev.ucp.shopping.checkout`) — selection and cost: which items go where, by which method, at what price and ETA.
- **Catalog** (`dev.ucp.shopping.catalog.search` and `dev.ucp.shopping.catalog.lookup`) — discovery: a variant advertises the fulfillment options available for it, based on the provided buyer context. See [Catalog Discovery](#catalog-discovery).

On Checkout, the `fulfillment` field contains:

- `methods[]` — fulfillment methods applicable to cart items (shipping, pickup, etc.)
  - `line_item_ids` — which items this method fulfills
  - `destinations[]` — where to fulfill (address, store location)
  - `groups[]` — business-generated packages, each with selectable `options[]`
- `available_methods[]` — inventory availability per item (optional)

**Mental model:**

- `methods[0]` Shipping
  - `line_item_ids` 👕👖
  - `selected_destination_id` = `destinations[0].id` 🔘✅ 123 Fake St
  - `groups[0]` 📦👕👖
    - `selected_option_id` = `options[0].id` 🔘✅ Standard $5
    - `options[1]` 🔘 Express $10
- `methods[1]` Pick Up in Store
  - `line_item_ids` 👞
  - `selected_destination_id` = `destinations[0].id` 🔘✅ Uptown Store
  - `groups[0]` 📦👞
    - `selected_option_id` = `options[0].id` 🔘✅ In-Store Pickup
    - `options[1]` 🔘 Curbside Pickup

## Schema

Fulfillment applies only to items requiring physical delivery. Items not requiring fulfillment (e.g., digital goods) do not need to be assigned to a method.

### Properties

| Name        | Type                                                         | Requirement                   | Description          |
| ----------- | ------------------------------------------------------------ | ----------------------------- | -------------------- |
| fulfillment | [Fulfillment](/draft/specification/fulfillment/#fulfillment) | Optional; omitted on complete | Fulfillment details. |

### Entities

#### Fulfillment

| Name              | Type                                                                                                  | Requirement | Description                         |
| ----------------- | ----------------------------------------------------------------------------------------------------- | ----------- | ----------------------------------- |
| methods           | Array\[[Fulfillment Method](/draft/specification/reference/#fulfillment-method)\]                     | Optional    | Fulfillment methods for cart items. |
| available_methods | Array\[[Fulfillment Available Method](/draft/specification/reference/#fulfillment-available-method)\] | Optional    | Inventory availability hints.       |

#### Fulfillment Method

| Name                    | Type                                                                                        | Requirement  | Description                                                                                                  |
| ----------------------- | ------------------------------------------------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------ |
| id                      | string                                                                                      | **Required** | Unique fulfillment method identifier.                                                                        |
| type                    | string                                                                                      | **Required** | Fulfillment method type. Well-known values: `shipping`, `pickup`. Businesses MAY use additional values.      |
| line_item_ids           | Array[string]                                                                               | **Required** | Line item IDs fulfilled via this method.                                                                     |
| destinations            | Array\[[Fulfillment Destination](/draft/specification/reference/#fulfillment-destination)\] | Optional     | Available destinations. For shipping: addresses. For pickup: retail locations.                               |
| selected_destination_id | ['string', 'null']                                                                          | Optional     | ID of the selected destination.                                                                              |
| groups                  | Array\[[Fulfillment Group](/draft/specification/reference/#fulfillment-group)\]             | Optional     | Fulfillment groups for selecting options. Agent sets selected_option_id on groups to choose shipping method. |

#### Fulfillment Destination

This object MUST be one of the following types: [Shipping Destination](/draft/specification/reference/#shipping-destination), [Retail Location](/draft/specification/reference/#retail-location).

#### Shipping Destination

| Name             | Type   | Requirement  | Description                                                                                                                                                                                                                               |
| ---------------- | ------ | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| extended_address | string | Optional     | An address extension such as an apartment number, C/O or alternative name.                                                                                                                                                                |
| street_address   | string | Optional     | The street address.                                                                                                                                                                                                                       |
| address_locality | string | Optional     | The locality in which the street address is, and which is in the region. For example, Mountain View.                                                                                                                                      |
| address_region   | string | Optional     | The region in which the locality is, and which is in the country. Required for applicable countries (i.e. state in US, province in CA). For example, California or another appropriate first-level Administrative division.               |
| address_country  | string | Optional     | The country. Recommended to be in 2-letter ISO 3166-1 alpha-2 format, for example "US". For backward compatibility, a 3-letter ISO 3166-1 alpha-3 country code such as "SGP" or a full country name such as "Singapore" can also be used. |
| postal_code      | string | Optional     | The postal code. For example, 94043.                                                                                                                                                                                                      |
| first_name       | string | Optional     | Optional. First name of the contact associated with the address.                                                                                                                                                                          |
| last_name        | string | Optional     | Optional. Last name of the contact associated with the address.                                                                                                                                                                           |
| phone_number     | string | Optional     | Optional. Phone number of the contact associated with the address.                                                                                                                                                                        |
| id               | string | **Required** | ID specific to this shipping destination.                                                                                                                                                                                                 |

#### Retail Location

| Name    | Type                                                             | Requirement  | Description                       |
| ------- | ---------------------------------------------------------------- | ------------ | --------------------------------- |
| id      | string                                                           | **Required** | Unique location identifier.       |
| name    | string                                                           | **Required** | Location name (e.g., store name). |
| address | [Postal Address](/draft/specification/reference/#postal-address) | Optional     | Physical address of the location. |

#### Fulfillment Group

| Name               | Type                                                                              | Requirement  | Description                                                            |
| ------------------ | --------------------------------------------------------------------------------- | ------------ | ---------------------------------------------------------------------- |
| id                 | string                                                                            | **Required** | Group identifier for referencing merchant-generated groups in updates. |
| line_item_ids      | Array[string]                                                                     | **Required** | Line item IDs included in this group/package.                          |
| options            | Array\[[Fulfillment Option](/draft/specification/reference/#fulfillment-option)\] | Optional     | Available fulfillment options for this group.                          |
| selected_option_id | ['string', 'null']                                                                | Optional     | ID of the selected fulfillment option for this group.                  |

#### Fulfillment Option

| Name                      | Type                                                       | Requirement  | Description                                                                                                                                             |
| ------------------------- | ---------------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id                        | string                                                     | **Required** | Unique identifier for this fulfillment option.                                                                                                          |
| title                     | string                                                     | **Required** | Short label that distinguishes this option from its siblings (e.g. 'Standard', 'Express Shipping', 'Curbside Pickup').                                  |
| description               | [Description](/draft/specification/reference/#description) | Optional     | Supplementary context for the title (e.g. 'Arrives in 4 business days', 'Arrives Dec 12-15 via FedEx'). Directly renderable; MUST NOT repeat the title. |
| carrier                   | string                                                     | Optional     | Carrier name (for shipping).                                                                                                                            |
| earliest_fulfillment_time | string                                                     | Optional     | Earliest fulfillment date.                                                                                                                              |
| latest_fulfillment_time   | string                                                     | Optional     | Latest fulfillment date.                                                                                                                                |
| totals                    | Array\[[Total](/draft/specification/reference/#total)\]    | **Required** | Fulfillment option totals breakdown.                                                                                                                    |

#### Fulfillment Available Method

| Name           | Type               | Requirement  | Description                                                                                                                          |
| -------------- | ------------------ | ------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| type           | string             | **Required** | Fulfillment method type this availability applies to. Well-known values: `shipping`, `pickup`; businesses MAY use additional values. |
| line_item_ids  | Array[string]      | **Required** | Line items available for this fulfillment method.                                                                                    |
| fulfillable_on | ['string', 'null'] | Optional     | 'now' for immediate availability, or ISO 8601 date for future (preorders, transfers).                                                |
| description    | string             | Optional     | Human-readable availability info (e.g., 'Available for pickup at Downtown Store today').                                             |

#### Total

| Name         | Type                                                           | Requirement  | Description                                                                                                                                                                                                                                                                                 |
| ------------ | -------------------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string                                                         | **Required** | Cost category. Well-known values: subtotal, items_discount, discount, fulfillment, tax, fee, total. Businesses MAY use additional values.                                                                                                                                                   |
| display_text | string                                                         | Optional     | Text to display against the amount. Should reflect appropriate method (e.g., 'Shipping', 'Delivery').                                                                                                                                                                                       |
| amount       | [Signed Amount](/draft/specification/reference/#signed-amount) | **Required** | Monetary amount in the currency's minor unit as defined by ISO 4217. Refer to the currency's exponent to determine minor-to-major ratio (e.g., 2 for USD, 0 for JPY, 3 for KWD). May be negative — the sign is intrinsic to the value (e.g., discounts are negative, charges are positive). |

#### Postal Address

See [Postal Address](/draft/specification/reference/#postal-address) in the [Schema Reference](/draft/specification/reference/) for the canonical field definition.

### Example

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

Fulfillment options are designed for **method-agnostic rendering**. Platforms do not need to understand specific method types (shipping, pickup, etc.) to present options meaningfully. The business provides precomputed, human-readable fields that platforms render directly.

### Human-Readable Fields

| Location              | Field         | Required | Purpose                                            |
| --------------------- | ------------- | -------- | -------------------------------------------------- |
| `groups[].options[]`  | `title`       | Yes      | Primary label that distinguishes from siblings     |
| `groups[].options[]`  | `description` | No       | Supplementary context for the title                |
| `groups[].options[]`  | `totals`      | Yes      | Cost breakdown: an array of `total` objects        |
| `available_methods[]` | `description` | No       | Standalone explanation of alternative availability |

### Business Responsibilities

**For `options[].title`:**

- **MUST** distinguish this option from its siblings
- **SHOULD** include method and speed (e.g., "Express Shipping", "Curbside Pickup")
- **MUST** be sufficient for buyer decision if `description` is absent

**For `options[].description`:**

- **MUST NOT** repeat `title` or `total`—provides supplementary context only
- **SHOULD** include timing, carrier, or other decision-relevant details
- **SHOULD** be a complete phrase (e.g., "Arrives Dec 12-15 via FedEx")
- **MAY** be omitted if title is self-explanatory

**For `available_methods[].description`:**

- **MUST** be a standalone sentence explaining what, when, and where
- **SHOULD** be usable verbatim in platform dialogue (e.g., "Pants available for pickup at Downtown Store today at 2pm")

**For ordering:**

- Businesses **SHOULD** return `options[]` in a meaningful order (e.g., cheapest first, fastest first)
- Platforms **SHOULD** preserve that order, but **MAY** re-order it (e.g. to match known buyer preferences or surface-specific ranking); they **MUST** preserve the method/option grouping

### Platform Responsibilities

Platforms **SHOULD** treat fulfillment as a generic, renderable structure:

- Render each option as a card using `title`, `description`, and `total`
- Present all methods returned—method selection is a buyer decision
- Preserve the method and option structure—do not merge or de-duplicate; the platform chooses ordering
- Use `available_methods[].description` to surface alternatives to the buyer

Platforms **MAY** provide enhanced UX for recognized method types (store selectors for pickup, carrier logos for shipping), but this is optional. The baseline contract is: **`title` + `description` + `total` is sufficient to render any option.**

When a buyer selects an option the platform cannot fully process, the platform **SHOULD** use `continue_url` to hand off to the business's checkout.

## Available Methods

Available methods indicate whether an item can be fulfilled with a given method, and when. Use cases:

- **Alternative methods**: "These pants are also available for pickup at Downtown Store"
- **Fulfill later**: Preorders, items shipping from a distant warehouse, pickup when store gets inventory

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

> 🤖 The shirt and pants ship for $5, arriving in 5-8 days. Or the pants can be picked up at Downtown Store in 4 hours.

If the buyer chooses pickup but the platform doesn't support split fulfillment, the platform **SHOULD** use `continue_url` to hand off to the business's checkout.

## Catalog Discovery

When the fulfillment extension extends the Catalog capability, each variant in a catalog response carries a `fulfillment` object listing the fulfillment methods available for that variant and their availability — so a buyer browsing the catalog can see how an item can be fulfilled.

### Methods

`fulfillment.methods[]` lists the methods available for a variant. Each method has:

- `type` — the fulfillment method (e.g. `shipping`, `pickup`); see [Method Types](#method-types).
- `description` — short, buyer-facing summary of how the variant is fulfilled via this method (e.g. "Ships in 2–4 business days"). Directly renderable; see [Rendering](#rendering).
- `availability` — whether the variant is available via this method at the specified or inferred location.
- `location` — for place-based methods (e.g. `pickup`), the resolved location id, and the business's stable identifier for that location. A business that advertises pickup at a `location` MUST accept the same id as `selected_destination_id` for that method, so a discovered location can be used in cart and checkout.
- `options` — concrete fulfillment choices within this method (e.g. Standard, Express); see [Options](#options). Optional.

Catalog reports availability for a single location per method — the one specified via `fulfills_to` or inferred from `context`; discovering and comparing other locations is handled separately.

The variant-level `availability` indicates whether the variant is obtainable via *any* method; a method's own `availability` is authoritative for that method. Where a method states `availability`, consumers MUST use it for that method and MUST NOT infer per-method availability from the variant-level value.

### Options

A method MAY carry `options[]`, a representative subset of its fulfillment options — not an exhaustive list. Without a destination or full cart, catalog SHOULD preview meaningful boundary options for the buyer (e.g. cheapest, fastest); the full, high-resolution set is negotiated in cart and checkout once those are known.

Each option carries an `id` and a `title` (a short label distinguishing it from siblings), plus an optional renderable `description` for context. These are a shared base: at checkout the same option is composed with cost and timing (`totals`, carrier, fulfillment times). The option is open, so a business MAY annotate it with additional fields. A method MAY also carry none, surfacing only `type`, `description`, and `availability`; options are nested directly under the method, with no group layer (unlike checkout `methods[].groups[].options[]`).

A discovered option `id` lets a buyer's choice carry forward: a business SHOULD accept the same id as `selected_option_id` in cart and checkout. The id is a best-effort handle, not a guaranteed match — an option discovered for a single product may differ in a cart, where other products, quantities, and combined fulfillment modify the options.

### Shapes

#### Catalog Fulfillment

How a catalog variant can be fulfilled. Mirrors checkout `fulfillment`.

| Name    | Type          | Requirement | Description                           |
| ------- | ------------- | ----------- | ------------------------------------- |
| methods | Array[object] | Optional    | Fulfillment methods for this variant. |

#### Catalog Fulfillment Method

A fulfillment method on a catalog variant: how the variant can be fulfilled, and its availability.

| Name         | Type          | Requirement  | Description                                                                                                                                                                                                                                                                                                                                  |
| ------------ | ------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| type         | string        | **Required** | Fulfillment method type. Well-known values: `shipping`, `pickup`. Businesses MAY use additional values.                                                                                                                                                                                                                                      |
| description  | object        | Optional     | Short buyer-facing summary (e.g. 'Ships in 2–4 business days').                                                                                                                                                                                                                                                                              |
| availability | object        | Optional     | Availability of this variant via this method at the specified or inferred location.                                                                                                                                                                                                                                                          |
| location     | string        | Optional     | The location resolved for this method, where appropriate (e.g. the pickup store or location), as a location id.                                                                                                                                                                                                                              |
| options      | Array[object] | Optional     | Fulfillment options for this method (e.g. Standard, Express) to describe per-choice details such as cost, time estimates, etc. Optional and selective: without a destination or full cart, a business SHOULD preview meaningful boundary options (e.g. cheapest, fastest); the full, high-resolution set is negotiated in cart and checkout. |

#### Fulfillment Option Base

| Name        | Type                                                       | Requirement  | Description                                                                                                                                             |
| ----------- | ---------------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id          | string                                                     | **Required** | Unique identifier for this fulfillment option.                                                                                                          |
| title       | string                                                     | **Required** | Short label that distinguishes this option from its siblings (e.g. 'Standard', 'Express Shipping', 'Curbside Pickup').                                  |
| description | [Description](/draft/specification/reference/#description) | Optional     | Supplementary context for the title (e.g. 'Arrives in 4 business days', 'Arrives Dec 12-15 via FedEx'). Directly renderable; MUST NOT repeat the title. |

#### Availability

| Name      | Type    | Requirement | Description                                                                                                                         |
| --------- | ------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| available | boolean | Optional    | Whether this can be obtained. See status for fulfillment details.                                                                   |
| status    | string  | Optional    | Qualifies available with fulfillment state. Well-known values: `in_stock`, `backorder`, `preorder`, `out_of_stock`, `discontinued`. |

#### Fulfillment Destination Filter

| Name            | Type   | Requirement | Description                                                                                                                    |
| --------------- | ------ | ----------- | ------------------------------------------------------------------------------------------------------------------------------ |
| address_country | string | Optional    | The country, as a 2-letter ISO 3166-1 alpha-2 code (e.g. "US"). A 3-letter alpha-3 code or full country name MAY also be used. |
| address_region  | string | Optional    | The first-level administrative region within the country (e.g. a state or province such as California).                        |
| postal_code     | string | Optional    | The postal code (e.g. "94043").                                                                                                |
| location        | string | Optional    | A reference to the destination (e.g. store, pickup location, saved address).                                                   |

### Location and method: `context` and `filters`

- **`context`** (`address_country` / `address_region` / `postal_code`) is where the *buyer* is — a non-binding hint the business uses to report `availability`. On a market-scoped catalog it MAY narrow results; otherwise it annotates rather than removes them.
- **`filters.fulfills_to`** is where the order is *fulfilled to* — a single destination, named by value (a coarse address: `address_country` / `address_region` / `postal_code`) or by reference (a `location` id — a store, pickup point, or saved address). Platforms **SHOULD** provide one or the other, not both; if both are present, a business **SHOULD** use the more specific — typically `location`. It restricts results to what can be fulfilled there and seeds method `availability`, and may differ from `context` (e.g. a gift).
- **`filters.methods`** restricts results to specific method types (e.g. `["pickup"]`).

Provide location once: `context` for where the buyer is, `fulfills_to` for an explicit destination. When both are present, `fulfills_to` supersedes `context`.

### Example

A variant exposes two fulfillment methods: shipping to the buyer's ship-to and pickup today at a named store. Each method carries its own availability, and `pickup` references the resolved location by id.

```json
{
  "ucp": { "version": "draft" },
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

Each method is a way the variant can be fulfilled, with its own `availability`. Each method's `description` is directly renderable, so a platform can present it without recognizing the `type` (see [Rendering](#rendering)). The shipping method's `description` previews the delivery range, and its `options[]` refine it (Standard, Express); pickup carries none — `options` is optional.

## Configuration

Businesses and platforms declare fulfillment constraints in their profiles. Businesses fetch platform profiles to adapt responses accordingly.

The `extends` array lists the capabilities this extension adds fulfillment to. Checkout is the authoritative, transactional surface; catalog is for discovery. A business lists the catalog capabilities in `extends` to expose fulfillment on catalog, or omits them to scope itself to checkout only.

### Platform Profile

Platforms declare their rendering capabilities using `platform_schema`:

| Name                 | Type    | Requirement | Description                         |
| -------------------- | ------- | ----------- | ----------------------------------- |
| supports_multi_group | boolean | Optional    | Enables multiple groups per method. |

Platforms that omit config or set `supports_multi_group: false` receive single-group responses. The response shape is always `methods[].groups[]`—the difference is whether `groups.length` can exceed 1 within each method.

Default declaration (single group per method; fulfillment surfaced on checkout and on catalog discovery):

```json
{
  "dev.ucp.shopping.fulfillment": [
    {
      "version": "draft",
      "spec": "https://ucp.dev/draft/specification/fulfillment",
      "schema": "https://ucp.dev/draft/schemas/shopping/fulfillment.json",
      "extends": [
        "dev.ucp.shopping.checkout",
        "dev.ucp.shopping.catalog.search",
        "dev.ucp.shopping.catalog.lookup"
      ]
    }
  ]
}
```

A party that does not expose catalog discovery MAY narrow `extends` to `"dev.ucp.shopping.checkout"` (string form) or to a single-element array.

Opt-in declaration (business MAY return multiple groups per method):

```json
{
  "dev.ucp.shopping.fulfillment": [
    {
      "version": "draft",
      "spec": "https://ucp.dev/draft/specification/fulfillment",
      "schema": "https://ucp.dev/draft/schemas/shopping/fulfillment.json",
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

Businesses declare what fulfillment configurations they support using `business_config`:

| Name                | Type          | Requirement | Description                                                                                                                                                                                                 |
| ------------------- | ------------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| multi_destination   | Array[object] | Optional    | Method types that permit multiple destinations within one cart (e.g. split shipping across addresses). Listing a method permits it; an omitted method does not. Open — businesses MAY list any method type. |
| method_combinations | Array[array]  | Optional    | Method-type combinations the business permits within one cart. Each inner array is a permitted set of method `type` values (e.g. shipping + pickup).                                                        |

```json
{
  "dev.ucp.shopping.fulfillment": [
    {
      "version": "draft",
      "spec": "https://ucp.dev/draft/specification/fulfillment",
      "schema": "https://ucp.dev/draft/schemas/shopping/fulfillment.json",
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

This example says: shipping can go to multiple addresses, and carts can mix shipping+pickup.

### Business Response Behavior

**When `supports_multi_group: false` (default):**

- Business **MUST** consolidate all items into a **single group per method**
- Response still uses array structure: `methods[].groups[]` with `groups.length === 1`
- Business **MAY** still return multiple methods (e.g., shipping + pickup) if cart items require it

**When `supports_multi_group: true`:**

- Business **MAY** return multiple groups per method based on inventory, packaging, or warehouse logic
- Platform is responsible for rendering group selection UI (e.g., choose shipping speed per package)

### Method Types

`fulfillment_method.type` (checkout) and `catalog_fulfillment_method.type` (catalog) share one open-string vocabulary. Presentation is method-agnostic: platforms **SHOULD** present every method, rendering `description` and `availability` regardless of its `type` (see [Rendering](#rendering)), and **SHOULD NOT** omit a method solely because they do not recognize its `type`. Recognizing a `type` only enables optional type-specific UX.

A method is identified by its `type` and its fulfillment scope (what it fulfills and where). A business **SHOULD** model same-scope variation (e.g. Standard vs Express) as `options`, and **SHOULD NOT** emit multiple methods that differ only in option-level detail. Same-`type` methods are valid when their scope differs — e.g. checkout may carry two `shipping` methods to different destinations. In catalog a method covers a single variant at one resolved location, so this collapses to at most one method per `type`.

**Well-known values:**

| Value      | Meaning                                                                |
| ---------- | ---------------------------------------------------------------------- |
| `shipping` | Carrier ships to the buyer's address.                                  |
| `pickup`   | Buyer picks up at a named location.                                    |
| `curbside` | Buyer picks up at a location without leaving their vehicle (drive-up). |

**Adding method types.** Because `type` is an open string, a business MAY introduce a new value at any time with no consumer change: it advertises the value (and filters on it via `filters.methods`), and consumers present it like any other method.

**Example — adding `home_installation`.** No schema change or registration is needed. Emit the value directly as the `type` on catalog and checkout, and filter with `filters.methods: ["home_installation"]`. For cart and checkout negotiation, declare its behavior in the business profile `config` — e.g. include `["shipping", "home_installation"]` in `method_combinations` so a cart can mix shipped and installed items (see [Business Profile](#business-profile)). On a catalog variant's method:

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

Business splits items into multiple packages; buyer selects shipping rate per package.

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

Shirt ships to mom (US), pants ship to grandma (Hong Kong). Two methods of the same type, each with its own destination.

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
