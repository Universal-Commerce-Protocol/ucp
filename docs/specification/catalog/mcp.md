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
    "version": "{{ ucp_version }}",
    "services": {
      "dev.ucp.shopping": {
        "version": "{{ ucp_version }}",
        "spec": "https://ucp.dev/{{ ucp_version }}/specification/overview",
        "mcp": {
          "schema": "https://ucp.dev/{{ ucp_version }}/services/shopping/mcp.openrpc.json",
          "endpoint": "https://business.example.com/ucp/mcp"
        }
      }
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
          "address_country": "US",
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
| `lookup_catalog` | [Lookup](lookup.md) | Lookup one or more products or variants by identifier. |

### `search_catalog`

Maps to the [Catalog Search](search.md) capability.

#### Search Request

{{ extension_schema_fields(
  'catalog_search.json#/$defs/search_request', 'catalog/mcp'
) }}

### Search Response

{{ extension_schema_fields(
  'catalog_search.json#/$defs/search_response', 'catalog/mcp'
) }}

#### Search Example

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
                  "selected_options": [
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
      }
    }
    ```

### `lookup_catalog`

Maps to the [Catalog Lookup](lookup.md) capability. See capability documentation
for supported identifiers, resolution behavior, and client correlation requirements.

The `catalog.ids` parameter accepts an array of identifiers and optional context.

#### Lookup Request

{{ extension_schema_fields(
  'catalog_lookup.json#/$defs/lookup_request', 'catalog/mcp'
) }}

### Lookup Response

{{ extension_schema_fields(
  'catalog_lookup.json#/$defs/lookup_response', 'catalog/mcp'
) }}

#### Lookup Example

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
              "address_country": "US"
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
                  "inputs": [
                    { "id": "prod_abc123", "match": "featured" }
                  ],
                  "tags": ["running", "road", "neutral"],
                  "seller": {
                    "name": "Example Store",
                    "links": [
                      {
                        "type": "refund_policy",
                        "url": "https://business.example.com/policies/refunds"
                      }
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
                  "inputs": [
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
2. Implement tools for each catalog capability advertised in the business's UCP profile, per their respective capability requirements ([Search](search.md), [Lookup](lookup.md)). Each capability may be adopted independently.
3. Use JSON-RPC errors for transport issues; use `messages` array for business outcomes.
4. Return successful result for lookup requests; unknown identifiers result in fewer products returned (MAY include informational `not_found` messages).
5. Validate tool inputs against UCP schemas.
6. Return products with valid `Price` objects (amount + currency).
7. Support cursor-based pagination with default limit of 10.
8. Return `-32602` (Invalid params) for requests exceeding batch size limits.
