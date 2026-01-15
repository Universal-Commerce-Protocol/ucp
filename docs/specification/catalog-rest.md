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

# Catalog Capability - REST Binding

This document specifies the HTTP/REST binding for the
[Catalog Capability](catalog.md).

## Protocol Fundamentals

### Discovery

Businesses advertise REST transport availability through their UCP profile at
`/.well-known/ucp`.

```json
{
  "ucp": {
    "version": "2026-01-11",
    "services": {
      "dev.ucp.shopping": {
        "version": "2026-01-11",
        "spec": "https://ucp.dev/specification/overview",
        "rest": {
          "schema": "https://ucp.dev/services/shopping/rest.openapi.json",
          "endpoint": "https://business.example.com/ucp"
        }
      }
    },
    "capabilities": [
      {
        "name": "dev.ucp.shopping.catalog",
        "version": "2026-01-11",
        "spec": "https://ucp.dev/specification/catalog",
        "schema": "https://ucp.dev/schemas/shopping/catalog.json"
      }
    ]
  }
}
```

## Endpoints

| Endpoint | Method | Operation | Description |
| :--- | :--- | :--- | :--- |
| `/catalog/search` | POST | [Search Catalog](catalog.md#search-catalog) | Search for products. |
| `/catalog/item/{id}` | GET | [Get Catalog Item](catalog.md#get-catalog-item) | Get a product or variant by ID. |

### `POST /catalog/search`

Maps to the [Search Catalog](catalog.md#search-catalog) operation.

{{ method_fields('search_catalog', 'rest.openapi.json', 'catalog-rest') }}

#### Example

=== "Request"

    ```json
    {
      "query": "blue running shoes",
      "context": {
        "country": "US",
        "region": "CA",
        "intent": "looking for comfortable everyday shoes"
      },
      "filters": {
        "category": "Footwear",
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
        "version": "2026-01-11",
        "capabilities": [
          {
            "name": "dev.ucp.shopping.catalog",
            "version": "2026-01-11"
          }
        ]
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
          "category": "Footwear > Running",
          "price": {
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
              "values": [{"label": "8"}, {"label": "9"}, {"label": "10"}, {"label": "11"}, {"label": "12"}]
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
              "selected_options": [
                { "name": "Size", "label": "10" }
              ],
              "tags": ["running", "road", "neutral"],
              "seller": {
                "name": "Example Store",
                "links": [
                  { "type": "refund_policy", "url": "https://business.example.com/policies/refunds" }
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

### `GET /catalog/item/{id}`

Maps to the [Get Catalog Item](catalog.md#get-catalog-item) operation.

The `id` path parameter accepts either a product ID or variant ID. The response
MUST return the parent product with full context. For product ID lookups,
`variants` MAY contain a representative set (when the full set is large, based on
buyer context or other criteria). For variant ID lookups, `variants` MUST contain
only the requested variant.

{{ method_fields('get_catalog_item', 'rest.openapi.json', 'catalog-rest') }}

#### Example

=== "Request"

    ```http
    GET /catalog/item/prod_abc123 HTTP/1.1
    Host: business.example.com
    ```

    Or get by variant ID (returns parent product with only this variant):

    ```http
    GET /catalog/item/prod_abc123_size10 HTTP/1.1
    Host: business.example.com
    ```

=== "Response"

    ```json
    {
      "ucp": {
        "version": "2026-01-11",
        "capabilities": [
          {
            "name": "dev.ucp.shopping.catalog",
            "version": "2026-01-11"
          }
        ]
      },
      "product": {
        "id": "prod_abc123",
        "title": "Blue Runner Pro",
        "description": {
          "plain": "Lightweight running shoes with responsive cushioning."
        },
        "price": {
          "min": { "amount": 12000, "currency": "USD" },
          "max": { "amount": 12000, "currency": "USD" }
        },
        "variants": [
          {
            "id": "prod_abc123_size10",
            "sku": "BRP-BLU-10",
            "title": "Size 10",
            "description": { "plain": "Size 10 variant" },
            "price": { "amount": 12000, "currency": "USD" },
            "availability": { "available": true },
            "tags": ["running", "road", "neutral"],
            "seller": {
              "name": "Example Store",
              "links": [
                { "type": "refund_policy", "url": "https://business.example.com/policies/refunds" }
              ]
            }
          }
        ],
        "metadata": {
          "collection": "Winter 2026",
          "technology": {
            "midsole": "React foam",
            "outsole": "Continental rubber"
          }
        }
      }
    }
    ```

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
`messages` array. See [Catalog Capability](catalog.md#messages-and-error-handling)
for message semantics and common scenarios.

**Example: Product Not Found**

```json
{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": [
      {
        "name": "dev.ucp.shopping.catalog",
        "version": "2026-01-11"
      }
    ]
  },
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

The `product` field is omitted when the ID doesn't exist. Business outcomes use the
standard HTTP 200 status with messages in the response body.

## Conformance

A conforming REST transport implementation **MUST**:

1. Implement the `POST /catalog/search` endpoint with required `query` parameter.
2. Implement the `GET /catalog/item/{id}` endpoint with required `id` path parameter.
3. Return products with valid `Price` objects (amount + currency).
4. Support cursor-based pagination with default limit of 10.
5. Return HTTP 200 with `NOT_FOUND` message for item requests with unknown IDs.
