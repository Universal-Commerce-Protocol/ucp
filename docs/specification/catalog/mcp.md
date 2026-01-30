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
        "version": "2026-01-11",
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
| `lookup_catalog` | [Lookup](lookup.md) | Get a product or variant by ID. |

### `search_catalog`

Maps to the [Catalog Search](search.md) capability.

{{ method_fields('search_catalog', 'mcp.openrpc.json', 'catalog-mcp') }}

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
              "category": "Footwear",
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
      }
    }
    ```

### `lookup_catalog`

Maps to the [Catalog Lookup](lookup.md) capability.

The `id` parameter accepts either a product ID or variant ID. The response
MUST return the parent product with full context. For product ID lookups,
`variants` MAY contain a representative set (when the full set is large, based on
buyer context or other criteria). For variant ID lookups, `variants` MUST contain
only the requested variant.

{{ method_fields('lookup_catalog', 'mcp.openrpc.json', 'catalog-mcp') }}

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
          "id": "prod_abc123",
          "catalog": {
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
                {"version": "2026-01-11"}
              ]
            }
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
      }
    }
    ```

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

#### Example: Product Not Found

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "structuredContent": {
      "ucp": {
        "version": "2026-01-11",
        "capabilities": {
          "dev.ucp.shopping.catalog.lookup": [
            {"version": "2026-01-11"}
          ]
        }
      },
      "messages": [
        {
          "type": "error",
          "code": "not_found",
          "content": "The requested product ID does not exist",
          "severity": "recoverable"
        }
      ]
    }
  }
}
```

The `product` field is omitted when the ID doesn't exist. Business outcomes use the
JSON-RPC `result` field with messages in the response payload.

## Conformance

A conforming MCP transport implementation **MUST**:

1. Implement JSON-RPC 2.0 protocol correctly.
2. Provide both `search_catalog` and `lookup_catalog` tools.
3. Require `catalog.query` parameter for `search_catalog`.
4. Require `id` parameter for `lookup_catalog`.
5. Use JSON-RPC errors for transport issues; use `messages` array for business outcomes.
6. Return successful result with `NOT_FOUND` message for unknown product/variant IDs.
7. Validate tool inputs against UCP schemas.
8. Return products with valid `Price` objects (amount + currency).
9. Support cursor-based pagination with default limit of 10.
