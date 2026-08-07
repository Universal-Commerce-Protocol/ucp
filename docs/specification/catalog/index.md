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

# Catalog Capability

## Overview

The Catalog capability allows platforms to search, browse, and enumerate business
product catalogs. This enables product discovery before checkout, supporting use
cases like:

* Free-text product search
* Category and filter-based browsing
* Batch product/variant retrieval by identifier
* Price comparison across variants
* Full catalog enumeration for platform indexing and incremental sync

## Capabilities

| Capability | Description |
| :--- | :--- |
| [`dev.ucp.shopping.catalog.search`](search.md) | Search for products using query text and filters. |
| [`dev.ucp.shopping.catalog.lookup`](lookup.md) | Retrieve products or variants by identifier. |
| [`dev.ucp.shopping.catalog.list`](list.md) | Paginate through the full product catalog. |

## Key Concepts

* **Product**: A catalog item with title, description, media, and one or more
  variants.
* **Variant**: A purchasable item with specific option selections (e.g., "Blue /
  Large"), price, and availability.
* **Price**: Price values include both amount (in minor currency units) and
  currency code, enabling multi-currency catalogs.

### Relationship to Checkout

Catalog operations return product and variant IDs that can be used directly in
checkout `line_items[].item.id`. The variant ID from catalog retrieval should match
the item ID expected by checkout.

Catalog responses (pricing, availability, etc.) reflect the Business's current
terms for the given request but are not transactional commitments — checkout
is authoritative. Responses can be session-specific and **SHOULD NOT** be
reused across sessions without re-validation.

## Shared Entities

### Context

Location and market context for catalog operations. All fields are optional
hints for relevance and localization. Platforms MAY geo-detect context from
request headers.

Context signals are provisional—not authoritative data. Businesses SHOULD use
these values when verified inputs (e.g., shipping address) are absent, and MAY
ignore or down-rank them if inconsistent with higher-confidence signals
(authenticated account, risk detection) or regulatory constraints (export
controls). Eligibility and policy enforcement MUST occur at checkout time using
binding transaction data.

Businesses determine market assignment—including currency—based on context
signals. Price filter values are denominated in `context.currency`; when
the presentment currency differs, businesses SHOULD convert before applying
(see [Price Filter](search.md#price-filter)). Response prices include
explicit currency codes confirming the resolution.

When `context.eligibility` claims are present, Businesses that accept them
**MAY** adjust `price` / `list_price` directly for strikethrough display and
**MAY** use `messages` with `code: "eligibility_benefit"` to attribute the
adjustment to a specific claim.

{{ schema_fields('types/context', 'catalog') }}

### Signals

Environment data provided by the platform to support authorization
and abuse prevention. Signal values MUST NOT be buyer-asserted claims. See
[Signals](../overview.md#signals) for details and privacy requirements.

{{ schema_fields('types/signals', 'catalog') }}

### Attribution

Platform-provided referral and conversion-event context — campaign IDs,
click identifiers, and source/medium markers communicated by the platform.
See [Attribution](../overview.md#attribution) for details and consent
requirements.

{{ schema_fields('types/attribution', 'catalog') }}

### Product

A catalog item representing a sellable item with one or more purchasable variants.

`media` and `variants` are ordered arrays. Businesses SHOULD return the most
relevant variant and image first—default for lookups, best match based on query
and context for search. Platforms SHOULD treat the first element as featured.

{{ schema_fields('types/product', 'catalog') }}

### Variant

A purchasable item with specific option selections, price, and availability.

In lookup responses, each variant carries an `inputs` array for correlation:
which request identifiers resolved to this variant, and whether the match
was `exact` or `featured` (server-selected). See
[Client Correlation](lookup.md#client-correlation) for details.

`media` is an ordered array. Businesses SHOULD return the featured variant image
as the first element. Platforms SHOULD treat the first element as featured.

{{ schema_fields('types/variant', 'catalog') }}

### Price

{{ schema_fields('types/price', 'catalog') }}

### Price Range

{{ schema_fields('types/price_range', 'catalog') }}

### Media

{{ schema_fields('types/media', 'catalog') }}

### Product Option

{{ schema_fields('types/product_option', 'catalog') }}

### Option Value

{{ schema_fields('types/option_value', 'catalog') }}

### Selected Option

{{ schema_fields('types/selected_option', 'catalog') }}

### Rating

{{ schema_fields('types/rating', 'catalog') }}

### Policy

Policies (return/refund terms, warranty, and the like) that apply to the
products in a catalog response. JSONPath targets in `applies_to` are
relative to the response root — `$.products[N]` for search and batch lookup,
`$.product` for get_product. See [Policies](../overview.md#policies) for the full model.

{{ schema_fields('types/policy', 'catalog') }}

## Actions

Catalog Search, batch Lookup, and successful Get Product responses can include
extension-defined Actions. In Catalog, an Action is outstanding work that gates
the effect its type defines, which may affect which products the Business
returns or how the Platform handles them.

Search, batch Lookup, and successful Get Product are independent Catalog
operations; their responses do not share a containing-resource lifetime. The
Business **MAY** use the same Action `id` in separate responses; that equality
does not identify the same work. A concrete Action-type contract **MAY** define
stronger correlation for its instances.

For Search and batch Lookup, the Business decides whether to return zero, some,
or all otherwise relevant products under the Action-type contract and its own
policy. A Message can point to the Action to explain the response. Successful
Get Product still includes `product`; its existing error response is unchanged.

After processing an Action, the Platform performs a fresh Catalog operation and
the later Business response is authoritative. Catalog defines no Action
lifecycle, polling, or resume behavior; a concrete Action-type contract **MAY**
define those behaviors for processing its instances. The common shape and rules
are defined in [Overview — Actions](../overview.md#actions).

For example, this Search response returns no products and explains that age
verification may affect the results:

<!-- ucp:example schema=shopping/catalog_search op=search -->
```json
{
  "ucp": {...},
  "products": [],
  "actions": {
    "com.example.identity.age_verification": [
      {
        "id": "age-check-1"
      }
    ]
  },
  "messages": [
    {
      "type": "info",
      "code": "age_verification_required",
      "content": "Complete age verification to see age-restricted products matching your search.",
      "path": "$.actions['com.example.identity.age_verification'][0]"
    }
  ]
}
```

Returning zero products is one Business choice; returning a subset or the full
result set is also conformant. The Action type and Message code are illustrative;
Catalog defines neither.

## Messages and Error Handling

All catalog responses include an optional `messages` array that allows businesses
to provide context about errors, warnings, or informational notices.

### Message Types

Messages communicate business outcomes and provide context:

| Type | When to Use | Example Codes |
| :--- | :--- | :--- |
| `error` | Business-level errors | `NOT_FOUND`, `OUT_OF_STOCK`, `REGION_RESTRICTED` |
| `warning` | Important conditions affecting purchase | `DELAYED_FULFILLMENT`, `FINAL_SALE` |
| `info` | Additional context without issues | `PROMOTIONAL_PRICING`, `LIMITED_AVAILABILITY` |

Warnings with `presentation: "disclosure"` carry notices (e.g., allergen
declarations, safety warnings) that platforms must not hide or dismiss. See
[Warning Presentation](../checkout.md#warning-presentation) for the full
rendering contract.

**Note**: Most catalog errors use `severity: "recoverable"` - agents
handle them programmatically (retry, inform user, show alternatives).
`get_product` returns `severity: "unrecoverable"` when an identifier
doesn't resolve; agents MUST NOT retry the same `id` (see the
[REST](rest.md#product-not-found) and [MCP](mcp.md#product-not-found)
examples).

#### Message (Error)

{{ schema_fields('types/message_error', 'catalog') }}

#### Message (Warning)

{{ schema_fields('types/message_warning', 'catalog') }}

#### Message (Info)

{{ schema_fields('types/message_info', 'catalog') }}

### Common Scenarios

#### Empty Search

When search finds no matches, return an empty array without messages.

<!-- ucp:example schema=shopping/catalog_search op=search -->
```json
{
  "ucp": {...},
  "products": []
}
```

This is not an error - the query was valid but returned no results.

#### Backorder Warning

When a product is available but has delayed fulfillment, return the product with
a warning message. Use the `path` field to target specific variants.

<!-- ucp:example schema=shopping/catalog_search op=search -->
```json
{
  "ucp": {...},
  "products": [
    {
      "id": "prod_xyz789",
      "title": "Professional Chef Knife Set",
      "description": { "plain": "Complete professional knife collection." },
      "price_range": {
        "min": { "amount": 29900, "currency": "USD" },
        "max": { "amount": 29900, "currency": "USD" }
      },
      "variants": [
        {
          "id": "var_abc",
          "title": "12-piece Set",
          "description": { "plain": "Complete professional knife collection." },
          "price": { "amount": 29900, "currency": "USD" },
          "availability": { "available": true }
        }
      ]
    }
  ],
  "messages": [
    {
      "type": "warning",
      "code": "delayed_fulfillment",
      "path": "$.products[0].variants[0]",
      "content": "12-piece set on backorder, ships in 2-3 weeks"
    }
  ]
}
```

Agents can present the option and inform the user about the delay. The `path`
field uses RFC 9535 JSONPath to target specific components.

#### Identifiers Not Found

When requested identifiers don't exist, return success with the found products
(if any). The response MAY include informational messages indicating which
identifiers were not found.

<!-- ucp:example schema=shopping/catalog_lookup op=lookup -->
```json
{
  "ucp": {...},
  "products": [],
  "messages": [
    {
      "type": "info",
      "code": "not_found",
      "content": "prod_invalid"
    }
  ]
}
```

Agents correlate results using the `inputs` array on each variant. See
[Client Correlation](lookup.md#client-correlation).

#### Product Disclosure

When a product requires a disclosure (e.g., allergen notice, safety warning),
return it as a warning with `presentation: "disclosure"`. The `path` field targets the
relevant component in the response — when it targets a product, the
disclosure applies to all of its variants.

<!-- ucp:example schema=shopping/catalog_search op=search -->
```json
{
  "ucp": {...},
  "products": [
    {
      "id": "prod_nut_butter",
      "title": "Artisan Nut Butter Collection",
      "description": { "plain": "Assorted artisan nut butters." },
      "price_range": {
        "min": { "amount": 1299, "currency": "USD" },
        "max": { "amount": 1499, "currency": "USD" }
      },
      "variants": [
        {
          "id": "var_almond",
          "title": "Almond Butter",
          "description": { "plain": "Smooth almond butter." },
          "price": { "amount": 1299, "currency": "USD" },
          "availability": { "available": true }
        },
        {
          "id": "var_cashew",
          "title": "Cashew Butter",
          "description": { "plain": "Creamy cashew butter." },
          "price": { "amount": 1499, "currency": "USD" },
          "availability": { "available": true }
        }
      ]
    }
  ],
  "messages": [
    {
      "type": "warning",
      "code": "allergens",
      "path": "$.products[0]",
      "content": "**Contains: tree nuts.** Produced in a facility that also processes peanuts, milk, and soy.",
      "content_type": "markdown",
      "presentation": "disclosure",
      "image_url": "https://merchant.com/allergen-tree-nuts.svg",
      "url": "https://merchant.com/allergen-info"
    }
  ]
}
```

See [Warning Presentation](../checkout.md#warning-presentation) for the
full rendering contract.

## Scopes

The Catalog Search and Catalog Lookup capabilities define the following
well-known scopes for user-authenticated access:

| Scope | Description |
| :--- | :--- |
| `dev.ucp.shopping.catalog.search:read` | Search on behalf of the authenticated user — personalized results, member pricing, gated inventory. |
| `dev.ucp.shopping.catalog.lookup:read` | Lookup on behalf of the authenticated user — personalized pricing or availability for specific products. |

Scope declaration, derivation, and rules for extending this set with
custom scopes are defined in [Identity Linking — Scopes](../identity-linking.md#scopes).

## Transport Bindings

The capabilities above are bound to specific transport protocols:

* [REST Binding](rest.md): RESTful API mapping.
* [MCP Binding](mcp.md): Model Context Protocol mapping via JSON-RPC.
