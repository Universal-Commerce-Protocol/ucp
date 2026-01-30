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

The Catalog capability allows platforms to search and browse business product catalogs.
This enables product discovery before checkout, supporting use cases like:

* Free-text product search
* Category and filter-based browsing
* Direct product/variant retrieval by ID
* Price comparison across variants

## Capabilities

| Capability | Description |
| :--- | :--- |
| [`dev.ucp.shopping.catalog.search`](search.md) | Search for products using query text and filters. |
| [`dev.ucp.shopping.catalog.lookup`](lookup.md) | Retrieve a specific product or variant by ID. |

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

## Shared Entities

### Context

Location and market context for catalog operations. All fields are optional
hints for relevance and localization. Platforms MAY geo-detect context from
request headers.

Context signals are provisional—not authorization. Businesses SHOULD use these
values when authoritative data (e.g., shipping address) is absent, and MAY
ignore or down-rank them if inconsistent with stronger signals (authenticated
account, fraud rules, export controls). Eligibility and policy enforcement
MUST occur at checkout/order time with authoritative data.

Businesses determine market assignment—including currency—based on context
signals. Price filter values are interpreted in the business's assigned
currency; response prices include explicit currency codes.

{{ schema_fields('types/context', 'catalog') }}

### Product

A catalog item representing a sellable item with one or more purchasable variants.

`media` and `variants` are ordered arrays. Businesses SHOULD return the most relevant variant and image first—default for lookups, best match based on query and context for search. Platforms SHOULD treat the first element as featured.

{{ schema_fields('types/product', 'catalog') }}

### Variant

A purchasable item with specific option selections, price, and availability.

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

## Messages and Error Handling

All catalog responses include an optional `messages` array that allows businesses
to provide context about errors, warnings, or informational notices.

### Message Types

Messages communicate business outcomes and provide context:

| Type | When to Use | Example Codes |
| :--- | :--- | :--- |
| `error` | Business-level errors | `NOT_FOUND`, `OUT_OF_STOCK`, `REGION_RESTRICTED` |
| `warning` | Important conditions affecting purchase | `DELAYED_FULFILLMENT`, `FINAL_SALE`, `AGE_RESTRICTED` |
| `info` | Additional context without issues | `PROMOTIONAL_PRICING`, `LIMITED_AVAILABILITY` |

**Note**: All catalog errors use `severity: "recoverable"` - agents handle them programmatically (retry, inform user, show alternatives).

#### Message (Error)

{{ schema_fields('types/message_error', 'catalog') }}

#### Message (Warning)

{{ schema_fields('types/message_warning', 'catalog') }}

#### Message (Info)

{{ schema_fields('types/message_info', 'catalog') }}

### Common Scenarios

#### Empty Search

When search finds no matches, return an empty array without messages.

```json
{
  "ucp": {...},
  "products": []
}
```

This is not an error - the query was valid but returned no results.

#### Backorder Warning

When a product is available but has delayed fulfillment, return the product with a warning message. Use the `path` field to target specific variants.

```json
{
  "ucp": {...},
  "product": {
    "id": "prod_xyz789",
    "title": "Professional Chef Knife Set",
    "description": { "plain": "Complete professional knife collection." },
    "price": {
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
  },
  "messages": [
    {
      "type": "warning",
      "code": "delayed_fulfillment",
      "path": "$.product.variants[0]",
      "content": "12-piece set on backorder, ships in 2-3 weeks"
    }
  ]
}
```

Agents can present the option and inform the user about the delay. The `path` field uses RFC 9535 JSONPath to target specific components.

#### Product Not Found

When a requested product/variant ID doesn't exist, return success with an error message and omit the `product` field.

```json
{
  "ucp": {...},
  "messages": [
    {
      "type": "error",
      "code": "not_found",
      "content": "The requested product ID does not exist",
      "severity": "recoverable"
    }
  ]
}
```

Agents should handle this gracefully (e.g., ask user for a different product).

## Transport Bindings

The capabilities above are bound to specific transport protocols:

* [REST Binding](rest.md): RESTful API mapping.
* [MCP Binding](mcp.md): Model Context Protocol mapping via JSON-RPC.
