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

# Catalog - MCP Binding

This document specifies the Model Context Protocol (MCP) binding for the
[Catalog Capability](index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise MCP transport availability through their UCP profile at
`/.well-known/ucp`.

```json
{
  "ucp": {
    "version": "2026-01-11",
    "services": {
      "dev.ucp.shopping": {
        "version": "2026-01-11",
        "spec": "https://ucp.dev/specification/overview",
        "mcp": {
          "schema": "https://ucp.dev/services/shopping/mcp.openrpc.json",
          "endpoint": "https://business.example.com/ucp/mcp"
        }
      }
    },
    "capabilities": [
      {
        "name": "dev.ucp.shopping.catalog.search",
        "version": "2026-01-11",
        "spec": "https://ucp.dev/specification/catalog/search",
        "schema": "https://ucp.dev/schemas/shopping/catalog_search.json"
      },
      {
        "name": "dev.ucp.shopping.catalog.lookup",
        "version": "2026-02-01",
        "spec": "https://ucp.dev/specification/catalog/lookup",
        "schema": "https://ucp.dev/schemas/shopping/catalog_lookup.json"
      }
    ]
  }
}
```

### Request Metadata

MCP clients **MUST** include a `meta` object in every request containing
protocol metadata:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search_catalog",
    "arguments": {
      "meta": {
        "ucp-agent": {
          "profile": "https://platform.example/profiles/v2026-01/shopping-agent.json"
        }
      },
      "catalog": {
        "query": "blue running shoes",
        "context": {
          "country": "US",
          "intent": "looking for comfortable everyday shoes"
        }
      }
    }
  }
}
```

The `meta["ucp-agent"]` field is **required** on all requests to enable
version compatibility checking and capability negotiation.

## Tools

| Tool | Capability | Description |
| :--- | :--- | :--- |
| `search_catalog` | [Search](search.md) | Search for products. |
| `lookup_catalog` | [Lookup](lookup.md) | Batch lookup products or variants by identifier. |
| `get_product` | [Lookup](lookup.md#get-product-get_product) | Get full details for a single product. |

### `search_catalog`

Maps to the [Catalog Search](search.md) capability.

#### Request

{{ extension_schema_fields('catalog_search.json#/$defs/search_request', 'catalog-mcp') }}

#### Response

{{ extension_schema_fields('catalog_search.json#/$defs/search_response', 'catalog-mcp') }}

#### Example

=== "Request"

    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "method": "tools/call",
      "params": {
        "name": "search_catalog",
        "arguments": {
          "meta": {
            "ucp-agent": {
              "profile": "https://platform.example/profiles/v2026-01/shopping-agent.json"
            }
          },
          "catalog": {
            "query": "blue running shoes",
            "context": {
              "country": "US",
              "region": "CA",
              "intent": "looking for comfortable everyday shoes"
            },
            "filters": {
              "category": ["Footwear"],
              "price": {
                "max": 15000
              }
            },
            "pagination": {
              "limit": 20
            }
          }
        }
      }
    }
    ```

=== "Response"

    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "result": {
        "structuredContent": {
          "ucp": {
            "version": "2026-01-11",
            "capabilities": {
              "dev.ucp.shopping.catalog.search": [
                {"version": "2026-01-11"}
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
              "category": [
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
                  "options": [
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
      }
    }
    ```

### `lookup_catalog`

Maps to the [Catalog Lookup](lookup.md) capability. See capability documentation
for supported identifiers, resolution behavior, and client correlation requirements.

The `catalog.ids` parameter accepts an array of identifiers and optional context.

#### Request

{{ extension_schema_fields('catalog_lookup.json#/$defs/lookup_request', 'catalog-mcp') }}

#### Response

{{ extension_schema_fields('catalog_lookup.json#/$defs/lookup_response', 'catalog-mcp') }}

#### Example

=== "Request"

    ```json
    {
      "jsonrpc": "2.0",
      "id": 2,
      "method": "tools/call",
      "params": {
        "name": "lookup_catalog",
        "arguments": {
          "meta": {
            "ucp-agent": {
              "profile": "https://platform.example/profiles/v2026-01/shopping-agent.json"
            }
          },
          "catalog": {
            "ids": ["prod_abc123", "var_xyz789"],
            "context": {
              "country": "US"
            }
          }
        }
      }
    }
    ```

=== "Response"

    ```json
    {
      "jsonrpc": "2.0",
      "id": 2,
      "result": {
        "structuredContent": {
          "ucp": {
            "version": "2026-01-11",
            "capabilities": {
              "dev.ucp.shopping.catalog.lookup": [
                {"version": "2026-02-01"}
              ]
            }
          },
          "products": [
            {
              "id": "prod_abc123",
              "title": "Blue Runner Pro",
              "description": {
                "plain": "Lightweight running shoes with responsive cushioning."
              },
              "price_range": {
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
                  "input": [
                    { "id": "prod_abc123", "match": "featured" }
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
              "metadata": {
                "collection": "Winter 2026",
                "technology": {
                  "midsole": "React foam",
                  "outsole": "Continental rubber"
                }
              }
            },
            {
              "id": "prod_def456",
              "title": "Trail Master X",
              "description": {
                "plain": "Rugged trail running shoes with aggressive tread."
              },
              "price_range": {
                "min": { "amount": 15000, "currency": "USD" },
                "max": { "amount": 15000, "currency": "USD" }
              },
              "variants": [
                {
                  "id": "var_xyz789",
                  "sku": "TMX-GRN-11",
                  "title": "Size 11 - Green",
                  "description": { "plain": "Size 11 Green variant" },
                  "price": { "amount": 15000, "currency": "USD" },
                  "availability": { "available": true },
                  "input": [
                    { "id": "var_xyz789", "match": "exact" }
                  ],
                  "tags": ["trail", "waterproof"],
                  "seller": {
                    "name": "Example Store"
                  }
                }
              ]
            }
          ]
        }
      }
    }
    ```

#### Partial Success

When some identifiers are not found, the response includes the found products. The
response MAY include informational messages indicating which identifiers were not found.

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "structuredContent": {
      "ucp": {
        "version": "2026-02-01",
        "capabilities": {
          "dev.ucp.shopping.catalog.lookup": [
            {"version": "2026-02-01"}
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
          },
          "variants": []
        }
      ],
      "messages": [
        {
          "type": "info",
          "code": "not_found",
          "content": "prod_notfound1"
        },
        {
          "type": "info",
          "code": "not_found",
          "content": "prod_notfound2"
        }
      ]
    }
  }
}
```

### `get_product`

Maps to the [Catalog Lookup](lookup.md#get-product-get_product) capability. Returns a singular
`product` object (not an array) for full product detail page rendering.

#### Request

{{ extension_schema_fields('catalog_lookup.json#/$defs/get_product_request', 'catalog-mcp') }}

#### Response

{{ extension_schema_fields('catalog_lookup.json#/$defs/get_product_response', 'catalog-mcp') }}

#### Example: With Option Selection

The user selected Color=Blue on a product with Color and Size options.
The response includes availability signals on option values showing what's
available given that selection.

=== "Request"

    ```json
    {
      "jsonrpc": "2.0",
      "id": 3,
      "method": "tools/call",
      "params": {
        "name": "get_product",
        "arguments": {
          "meta": {
            "ucp-agent": {
              "profile": "https://platform.example/profiles/v2026-01/shopping-agent.json"
            }
          },
          "catalog": {
            "id": "prod_abc123",
            "selected": [
              { "name": "Color", "label": "Blue" }
            ],
            "preferences": ["Color", "Size"],
            "context": {
              "country": "US"
            }
          }
        }
      }
    }
    ```

=== "Response"

    ```json
    {
      "jsonrpc": "2.0",
      "id": 3,
      "result": {
        "structuredContent": {
          "ucp": {
            "version": "2026-02-01",
            "capabilities": {
              "dev.ucp.shopping.catalog.lookup": [
                {"version": "2026-02-01"}
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
                "id": "var_abc123_blue_8",
                "sku": "RP-BLU-08",
                "title": "Blue / Size 8",
                "description": { "plain": "Blue, Size 8" },
                "price": { "amount": 12000, "currency": "USD" },
                "availability": { "available": true },
                "options": [
                  { "name": "Color", "label": "Blue" },
                  { "name": "Size", "label": "8" }
                ]
              },
              {
                "id": "var_abc123_blue_9",
                "sku": "RP-BLU-09",
                "title": "Blue / Size 9",
                "description": { "plain": "Blue, Size 9" },
                "price": { "amount": 12000, "currency": "USD" },
                "availability": { "available": true },
                "options": [
                  { "name": "Color", "label": "Blue" },
                  { "name": "Size", "label": "9" }
                ]
              },
              {
                "id": "var_abc123_blue_10",
                "sku": "RP-BLU-10",
                "title": "Blue / Size 10",
                "description": { "plain": "Blue, Size 10" },
                "price": { "amount": 12000, "currency": "USD" },
                "availability": { "available": true },
                "options": [
                  { "name": "Color", "label": "Blue" },
                  { "name": "Size", "label": "10" }
                ]
              },
              {
                "id": "var_abc123_blue_12",
                "sku": "RP-BLU-12",
                "title": "Blue / Size 12",
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
      }
    }
    ```

In this response: Green is out of stock (`available: false, exists: true`),
Size 11 doesn't exist in Blue (`exists: false`), and four Blue variants are
returned matching the selection.

#### Product Not Found

When the identifier does not resolve to a product, return a JSON-RPC error:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "error": {
    "code": -32602,
    "message": "Product not found",
    "data": {
      "id": "prod_invalid"
    }
  }
}
```

Unlike `lookup_catalog` (which returns partial results for batch requests),
`get_product` is a single-resource operation. A missing product is an error,
not a partial success.

## Error Handling

UCP uses a two-layer error model separating transport errors from business outcomes.

### Transport Errors

Use JSON-RPC 2.0 error codes for protocol-level issues that prevent request processing:

| Code | Meaning |
| :--- | :--- |
| -32600 | Invalid Request - Malformed JSON-RPC |
| -32601 | Method not found |
| -32602 | Invalid params - Missing required parameter |
| -32603 | Internal error |

### Business Outcomes

All application-level outcomes return a successful JSON-RPC result with the UCP
envelope and optional `messages` array. See [Catalog Overview](index.md#messages-and-error-handling)
for message semantics and common scenarios.

#### Example: All Products Not Found

When all requested identifiers fail to resolve, the response contains an empty `products`
array. The response MAY include informational messages indicating which identifiers were
not found.

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "structuredContent": {
      "ucp": {
        "version": "2026-02-01",
        "capabilities": {
          "dev.ucp.shopping.catalog.lookup": [
            {"version": "2026-02-01"}
          ]
        }
      },
      "products": [],
      "messages": [
        {
          "type": "info",
          "code": "not_found",
          "content": "prod_invalid"
        }
      ]
    }
  }
}
```

Business outcomes use the JSON-RPC `result` field with messages in the response
payload. See the [Partial Success](#partial-success) section for handling mixed
results.

## Conformance

A conforming MCP transport implementation **MUST**:

1. Implement JSON-RPC 2.0 protocol correctly.
2. Provide `search_catalog`, `lookup_catalog`, and `get_product` tools.
3. Require `catalog.query` parameter for `search_catalog`.
4. Implement `lookup_catalog` per [Catalog Lookup](lookup.md) capability requirements.
5. Implement `get_product` per [Catalog Lookup](lookup.md#get-product-get_product) capability requirements.
6. Use JSON-RPC errors for transport issues; use `messages` array for business outcomes.
7. Return successful result for lookup requests; unknown identifiers result in fewer products returned (MAY include informational `not_found` messages).
8. Return JSON-RPC `-32602` error for `get_product` when the identifier is not found.
9. Validate tool inputs against UCP schemas.
10. Return products with valid `Price` objects (amount + currency).
11. Support cursor-based pagination with default limit of 10.
12. Return `-32602` (Invalid params) for requests exceeding batch size limits.
13. Return one featured variant per product for `search_catalog` and `lookup_catalog` when looking up by product ID. When looking up by variant ID, return only the requested variant.
14. When `get_product` includes `selected` options, return `available` and `exists` signals on option values.
