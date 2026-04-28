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

# Catalog - REST Binding

This document specifies the HTTP/REST binding for the
[Catalog Capability](index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise REST transport availability through their UCP profile at
`/.well-known/ucp`.

```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": {
      "dev.ucp.shopping": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/overview",
          "transport": "rest",
          "schema": "https://ucp.dev/{{ ucp_version }}/services/shopping/rest.openapi.json",
          "endpoint": "https://business.example.com/ucp"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.shopping.catalog.search": [{
        "version": "{{ ucp_version }}",
        "spec": "https://ucp.dev/{{ ucp_version }}/specification/catalog/search",
        "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/catalog_search.json"
      }],
      "dev.ucp.shopping.catalog.lookup": [{
        "version": "{{ ucp_version }}",
        "spec": "https://ucp.dev/{{ ucp_version }}/specification/catalog/lookup",
        "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/catalog_lookup.json"
      }]
    }
  }
}
```

## Endpoints

| Endpoint | Method | Capability | Description |
| :--- | :--- | :--- | :--- |
| `/catalog/search` | POST | [Search](search.md) | Search for products. |
| `/catalog/lookup` | POST | [Lookup](lookup.md) | Lookup one or more products by ID. |
| `/catalog/product` | POST | [Lookup](lookup.md#get-product-get_product) | Get full product detail by identifier. |

### `POST /catalog/search`

Maps to the [Catalog Search](search.md) capability.

{{ method_fields('search_catalog', 'rest.openapi.json', 'catalog/rest') }}

#### Example

=== "Request"

    ```json
    {
      "query": "blue running shoes",
      "context": {
        "address_country": "US",
        "address_region": "CA",
        "intent": "looking for comfortable everyday shoes"
      },
      "filters": {
        "categories": ["Footwear"],
        "price": {
          "max": 15000
        }
      },
      "pagination": {
        "limit": 20
      }
    }
    ```

=== "Response"

    ```json
    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.shopping.catalog.search": [
            {"version": "{{ ucp_version }}"}
          ]
        }
      },
      "products": [
        {
          "id": "prod_abc123",
          "handle": "blue-runner-pro",
          "title": "Blue Runner Pro",
          "description": {
            "plain": "Lightweight running shoes with responsive cushioning."
          },
          "url": "https://business.example.com/products/blue-runner-pro",
          "categories": [
            { "value": "187", "taxonomy": "google_product_category" },
            { "value": "aa-8-1", "taxonomy": "shopify" },
            { "value": "Footwear > Running", "taxonomy": "merchant" }
          ],
          "price_range": {
            "min": { "amount": 12000, "currency": "USD" },
            "max": { "amount": 12000, "currency": "USD" }
          },
          "media": [
            {
              "type": "image",
              "url": "https://cdn.example.com/products/blue-runner-pro.jpg",
              "alt_text": "Blue Runner Pro running shoes"
            }
          ],
          "options": [
            {
              "name": "Size",
              "values": [
                {"label": "8"},
                {"label": "9"},
                {"label": "10"},
                {"label": "11"},
                {"label": "12"}
              ]
            }
          ],
          "variants": [
            {
              "id": "prod_abc123_size10",
              "sku": "BRP-BLU-10",
              "title": "Size 10",
              "description": { "plain": "Size 10 variant" },
              "price": { "amount": 12000, "currency": "USD" },
              "availability": { "available": true },
              "options": [
                { "name": "Size", "label": "10" }
              ],
              "tags": ["running", "road", "neutral"],
              "seller": {
                "name": "Example Store",
                "links": [
                  {
                    "type": "refund_policy",
                    "url": "https://business.example.com/refunds"
                  }
                ]
              }
            }
          ],
          "rating": {
            "value": 4.5,
            "scale_max": 5,
            "count": 128
          },
          "metadata": {
            "collection": "Winter 2026",
            "technology": {
              "midsole": "React foam",
              "outsole": "Continental rubber"
            }
          }
        }
      ],
      "pagination": {
        "cursor": "eyJwYWdlIjoxfQ==",
        "has_next_page": true,
        "total_count": 47
      }
    }
    ```

### `POST /catalog/lookup`

Maps to the [Catalog Lookup](lookup.md) capability. See capability documentation
for supported identifiers, resolution behavior, and client correlation requirements.

The request body contains an array of identifiers and optional context that
applies to all lookups in the batch.

{{ method_fields('lookup_catalog', 'rest.openapi.json', 'catalog/rest') }}

#### Example: Batch Lookup with Context

=== "Request"

    ```json
    POST /catalog/lookup HTTP/1.1
    Host: business.example.com
    Content-Type: application/json

    {
      "ids": ["prod_abc123", "prod_def456"],
      "context": {
        "address_country": "US",
        "language": "es"
      }
    }
    ```

=== "Response"

    ```json
    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.shopping.catalog.lookup": [
            {"version": "{{ ucp_version }}"}
          ]
        }
      },
      "products": [
        {
          "id": "prod_abc123",
          "title": "Blue Runner Pro",
          "description": {
            "plain": "Zapatillas ligeras con amortiguación reactiva."
          },
          "price_range": {
            "min": { "amount": 12000, "currency": "USD" },
            "max": { "amount": 12000, "currency": "USD" }
          },
          "variants": [
            {
              "id": "prod_abc123_size10",
              "sku": "BRP-BLU-10",
              "title": "Talla 10",
              "description": { "plain": "Variante talla 10" },
              "price": { "amount": 12000, "currency": "USD" },
              "availability": { "available": true },
              "inputs": [
                { "id": "prod_abc123", "match": "featured" }
              ]
            }
          ]
        },
        {
          "id": "prod_def456",
          "title": "Trail Blazer X",
          "description": {
            "plain": "Zapatillas de trail con tracción superior."
          },
          "price_range": {
            "min": { "amount": 15000, "currency": "USD" },
            "max": { "amount": 15000, "currency": "USD" }
          },
          "variants": [
            {
              "id": "prod_def456_size10",
              "sku": "TBX-GRN-10",
              "title": "Talla 10",
              "price": { "amount": 15000, "currency": "USD" },
              "availability": { "available": true },
              "inputs": [
                { "id": "prod_def456", "match": "featured" }
              ]
            }
          ]
        }
      ]
    }
    ```

#### Example: Partial Success (Some Identifiers Not Found)

When some identifiers in the batch are not found, the response includes the
found products in the `products` array. The response MAY include informational
messages indicating which identifiers were not found.

=== "Request"

    ```json
    {
      "ids": ["prod_abc123", "prod_invalid", "prod_def456"]
    }
    ```

=== "Response"

    ```json
    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.shopping.catalog.lookup": [
            {"version": "{{ ucp_version }}"}
          ]
        }
      },
      "products": [
        {
          "id": "prod_abc123",
          "title": "Blue Runner Pro",
          "price_range": {
            "min": { "amount": 12000, "currency": "USD" },
            "max": { "amount": 12000, "currency": "USD" }
          }
        },
        {
          "id": "prod_def456",
          "title": "Trail Blazer X",
          "price_range": {
            "min": { "amount": 15000, "currency": "USD" },
            "max": { "amount": 15000, "currency": "USD" }
          }
        }
      ],
      "messages": [
        {
          "type": "info",
          "code": "not_found",
          "content": "prod_invalid"
        }
      ]
    }
    ```

### `POST /catalog/product`

Maps to the [Catalog Lookup](lookup.md#get-product-get_product) capability. Returns a singular
`product` object (not an array) for full product detail page rendering.

{{ method_fields('get_product', 'rest.openapi.json', 'catalog/rest') }}

#### Example: With Option Selection

The user selected Color=Blue. The response includes availability signals
on option values and returns variants matching the selection.

=== "Request"

    ```json
    POST /catalog/product HTTP/1.1
    Host: business.example.com
    Content-Type: application/json

    {
      "id": "prod_abc123",
      "selected": [
        { "name": "Color", "label": "Blue" }
      ],
      "preferences": ["Color", "Size"],
      "context": {
        "address_country": "US"
      }
    }
    ```

=== "Response"

    ```json
    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.shopping.catalog.lookup": [
            {"version": "{{ ucp_version }}"}
          ]
        }
      },
      "product": {
        "id": "prod_abc123",
        "handle": "runner-pro",
        "title": "Runner Pro",
        "description": {
          "plain": "Lightweight running shoes with responsive cushioning."
        },
        "url": "https://business.example.com/products/runner-pro",
        "price_range": {
          "min": { "amount": 12000, "currency": "USD" },
          "max": { "amount": 15000, "currency": "USD" }
        },
        "media": [
          {
            "type": "image",
            "url": "https://cdn.example.com/products/runner-pro-blue.jpg",
            "alt_text": "Runner Pro in Blue"
          }
        ],
        "options": [
          {
            "name": "Color",
            "values": [
              {"label": "Blue", "available": true, "exists": true},
              {"label": "Red", "available": true, "exists": true},
              {"label": "Green", "available": false, "exists": true}
            ]
          },
          {
            "name": "Size",
            "values": [
              {"label": "8", "available": true, "exists": true},
              {"label": "9", "available": true, "exists": true},
              {"label": "10", "available": true, "exists": true},
              {"label": "11", "available": false, "exists": false},
              {"label": "12", "available": true, "exists": true}
            ]
          }
        ],
        "selected": [
          { "name": "Color", "label": "Blue" }
        ],
        "variants": [
          {
            "id": "prod_abc123_blu_10",
            "sku": "BRP-BLU-10",
            "title": "Blue, Size 10",
            "description": { "plain": "Blue, Size 10" },
            "price": { "amount": 12000, "currency": "USD" },
            "availability": { "available": true },
            "options": [
              { "name": "Color", "label": "Blue" },
              { "name": "Size", "label": "10" }
            ]
          },
          {
            "id": "prod_abc123_blu_12",
            "sku": "BRP-BLU-12",
            "title": "Blue, Size 12",
            "description": { "plain": "Blue, Size 12" },
            "price": { "amount": 15000, "currency": "USD" },
            "availability": { "available": true },
            "options": [
              { "name": "Color", "label": "Blue" },
              { "name": "Size", "label": "12" }
            ]
          }
        ],
        "rating": {
          "value": 4.5,
          "scale_max": 5,
          "count": 128
        }
      }
    }
    ```

Green is out of stock (`available: false, exists: true`). Size 11 doesn't
exist in Blue (`exists: false`). Variants returned match the Color=Blue
selection.

#### Product Not Found

When the identifier does not resolve to a product, the server returns HTTP 200
with `ucp.status: "error"` and a descriptive message. This is an application
outcome, not a transport error — the handler executed and reports its result
via the UCP envelope.

```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "status": "error",
    "capabilities": {
      "dev.ucp.shopping.catalog.lookup": [
        {"version": "{{ ucp_version }}"}
      ]
    }
  },
  "messages": [
    {
      "type": "error",
      "code": "not_found",
      "content": "Product not found: prod_invalid",
      "severity": "unrecoverable"
    }
  ]
}
```

Unlike `/catalog/lookup` (which returns partial results for batch requests),
`/catalog/product` is a single-resource operation. A missing product is an
application error with `unrecoverable` severity — the agent should not retry
with the same identifier.

## Error Handling

UCP uses a two-layer error model separating transport errors from business outcomes.

### Transport Errors

Use HTTP status codes for protocol-level issues that prevent request processing:

| Status | Meaning |
| :--- | :--- |
| 400 | Bad Request - Malformed JSON or missing required parameters |
| 401 | Unauthorized - Missing or invalid authentication |
| 429 | Too Many Requests - Rate limited |
| 500 | Internal Server Error |

### Business Outcomes

All application-level outcomes return HTTP 200 with the UCP envelope and optional
`messages` array. See [Catalog Overview](index.md#messages-and-error-handling)
for message semantics and common scenarios.

#### Example: All Products Not Found

When all requested identifiers fail lookup, the `products` array is empty. The response
MAY include informational messages indicating which identifiers were not found.

```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.catalog.lookup": [
        {"version": "{{ ucp_version }}"}
      ]
    }
  },
  "products": [],
  "messages": [
    {
      "type": "info",
      "code": "not_found",
      "content": "prod_invalid1"
    },
    {
      "type": "info",
      "code": "not_found",
      "content": "prod_invalid2"
    }
  ]
}
```

Business outcomes use the standard HTTP 200 status with messages in the response body.

## Entities

### UCP Response Catalog {: #ucp-response-catalog-schema }

{{ extension_schema_fields('ucp.json#/$defs/response_catalog_schema', 'catalog/rest') }}

### Detail Product {: #detail-product }

{{ extension_schema_fields('catalog_lookup.json#/$defs/detail_product', 'catalog/rest') }}

### Get Product Response {: #catalog-lookup-get-product-response }

{{ extension_schema_fields('catalog_lookup.json#/$defs/get_product_response', 'catalog/rest') }}

### Error Response {: #error-response }

{{ schema_fields('types/error_response', 'catalog/rest') }}

## Conformance

A conforming REST transport implementation **MUST**:

1. Implement endpoints for each catalog capability advertised in the business's UCP profile, per their respective capability requirements ([Search](search.md), [Lookup](lookup.md)). Each capability may be adopted independently. When the Lookup capability is advertised, both `/catalog/lookup` and `/catalog/product` MUST be available.
2. Return products with valid `Price` objects (amount + currency).
3. Support cursor-based pagination with default limit of 10.
4. Return HTTP 200 for lookup requests; unknown identifiers result in fewer products returned (MAY include informational `not_found` messages).
5. Return HTTP 400 with `request_too_large` error for requests exceeding batch size limits.
