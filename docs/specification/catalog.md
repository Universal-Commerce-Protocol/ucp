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

* **Capability Name:** `dev.ucp.shopping.catalog`
* **Version:** `DRAFT`

## Overview

Allows platforms to search and browse business product catalogs. This capability
enables product discovery before checkout, supporting use cases like:

* Free-text product search
* Category and filter-based browsing
* Direct product/variant retrieval by ID
* Price comparison across variants

**Key Concepts**

* **Product**: A catalog entry with title, description, media, and one or more
  variants.
* **Variant**: A purchasable SKU with specific option selections (e.g., "Blue /
  Large"), price, and availability.
* **Price**: Price values include both amount (in minor currency units) and
  currency code, enabling multi-currency catalogs.

**Relationship to Checkout**

Catalog operations return product and variant IDs that can be used directly in
checkout `line_items[].item.id`. The variant ID from catalog retrieval should match
the item ID expected by checkout.

## Operations

The Catalog capability defines the following logical operations.

| Operation | Description |
| :--- | :--- |
| **Search Catalog** | Search for products using query text and filters. |
| **Get Catalog Item** | Retrieve a specific product or variant by ID. |

### Search Catalog

Performs a search against the business's product catalog. Supports free-text
queries, filtering by category and price, and pagination.

**Use Cases:**

* User searches for "blue running shoes"
* Agent browses products in a category
* Platform fetches featured or trending products

{{ method_fields('search_catalog', 'rest.openapi.json', 'catalog') }}

### Get Catalog Item

Retrieves a specific product or variant by its Global ID (GID). Use this when
you already have an ID (e.g., from a saved list, deep link, or cart validation).

**Use Cases:**

* Validating cart items before checkout
* Fetching full product details from a product ID
* Resolving variant details for display

**ID Resolution Behavior:**

The `id` parameter accepts either a product ID or variant ID. The response MUST
return the parent product with full context (title, description, media, options):

* **Product ID lookup**: `variants` MAY contain a representative set.
* **Variant ID lookup**: `variants` MUST contain only the requested variant.

When the full variant set is large, a representative set MAY be returned based on
buyer context or other criteria. This ensures agents always have product context
for display while getting exactly what they requested.

{{ method_fields('get_catalog_item', 'rest.openapi.json', 'catalog') }}

## Entities

### Context

Location and market context for catalog operations. All fields are optional. Platforms MAY geo-detect context from request IP/headers. When context fields are provided, they MUST override any auto-detected values.

{{ extension_schema_fields('catalog.json#/$defs/context', 'catalog') }}

### Product

A catalog entry representing a sellable item with one or more purchasable variants.

`media` and `variants` are ordered arrays. Businesses SHOULD return the featured
image and default variant as the first element. Platforms SHOULD treat the first
element as the featured item for display.

{{ schema_fields('types/product', 'catalog') }}

### Variant

A purchasable SKU with specific option selections, price, and availability.

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

### Pagination

Cursor-based pagination for list operations.

#### Pagination Request

{{ extension_schema_fields('types/pagination.json#/$defs/request', 'catalog') }}

#### Pagination Response

{{ extension_schema_fields('types/pagination.json#/$defs/response', 'catalog') }}

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

**Empty Search**

When search finds no matches, return an empty array without messages.

```json
{
  "ucp": {...},
  "products": []
}
```

This is not an error—the query was valid but returned no results.

**Backorder Warning**

When a product is available but has delayed fulfillment, return the product with a warning message. Use the `path` field to target specific variants.

```json
{
  "ucp": {...},
  "product": {
    "id": "prod_xyz789",
    "title": "Professional Chef Knife Set",
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
      "code": "DELAYED_FULFILLMENT",
      "path": "$.product.variants[0]",
      "content": "12-piece set on backorder, ships in 2-3 weeks"
    }
  ]
}
```

Agents can present the option and inform the user about the delay. The `path` field uses RFC 9535 JSONPath to target specific components.

**Product Not Found**

When a requested product/variant ID doesn't exist, return success with an error message and omit the `product` field.

```json
{
  "ucp": {...},
  "messages": [
    {
      "type": "error",
      "code": "NOT_FOUND",
      "content": "The requested product ID does not exist",
      "severity": "recoverable"
    }
  ]
}
```

Agents should handle this gracefully (e.g., ask user for a different product).

## Transport Bindings

The abstract operations above are bound to specific transport protocols as
defined below:

* [REST Binding](catalog-rest.md): RESTful API mapping.
* [MCP Binding](catalog-mcp.md): Model Context Protocol mapping via JSONRPC.
