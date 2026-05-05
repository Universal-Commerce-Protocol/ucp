# Catalog - MCP Binding

This document specifies the Model Context Protocol (MCP) binding for the [Catalog Capability](http://ucp.dev/draft/specification/catalog/index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise MCP transport availability through their UCP profile at `/.well-known/ucp`.

```json
{
  "ucp": {
    "version": "draft",
    "services": {
      "dev.ucp.shopping": [
        {
          "version": "draft",
          "spec": "https://ucp.dev/draft/specification/overview",
          "transport": "mcp",
          "schema": "https://ucp.dev/draft/services/shopping/mcp.openrpc.json",
          "endpoint": "https://business.example.com/ucp/mcp"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.shopping.catalog.search": [{
        "version": "draft",
        "spec": "https://ucp.dev/draft/specification/catalog/search",
        "schema": "https://ucp.dev/draft/schemas/shopping/catalog_search.json"
      }],
      "dev.ucp.shopping.catalog.lookup": [{
        "version": "draft",
        "spec": "https://ucp.dev/draft/specification/catalog/lookup",
        "schema": "https://ucp.dev/draft/schemas/shopping/catalog_lookup.json"
      }]
    }
  }
}
```

### Request Metadata

MCP clients **MUST** include a `meta` object in every request containing protocol metadata:

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

The `meta["ucp-agent"]` field is **required** on all requests to enable version compatibility checking and capability negotiation.

## Tools

| Tool             | Capability                                                                           | Description                                            |
| ---------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------ |
| `search_catalog` | [Search](http://ucp.dev/draft/specification/catalog/search/index.md)                 | Search for products.                                   |
| `lookup_catalog` | [Lookup](http://ucp.dev/draft/specification/catalog/lookup/index.md)                 | Lookup one or more products or variants by identifier. |
| `get_product`    | [Lookup](http://ucp.dev/draft/specification/catalog/lookup/#get-product-get_product) | Get full product detail by identifier.                 |

### `search_catalog`

Maps to the [Catalog Search](http://ucp.dev/draft/specification/catalog/search/index.md) capability.

#### Search Request

| Name        | Type   | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ----------- | ------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| query       | string | No       | Free-text search query.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| context     | object | No       | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals     | object | No       | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| attribution | object | No       | Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| filters     | object | No       | Filter criteria to narrow search results. All specified filters combine with AND logic.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| pagination  | object | No       | Pagination parameters for requests.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |

### Search Response

| Name       | Type          | Required | Description                                                           |
| ---------- | ------------- | -------- | --------------------------------------------------------------------- |
| ucp        | any           | **Yes**  | UCP metadata for catalog responses.                                   |
| products   | Array[object] | **Yes**  | Products matching the search criteria.                                |
| pagination | object        | No       | Pagination information in responses.                                  |
| messages   | Array[object] | No       | Errors, warnings, or informational messages about the search results. |

#### Search Example

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

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "structuredContent": {
      "ucp": {
        "version": "draft",
        "capabilities": {
          "dev.ucp.shopping.catalog.search": [
            {"version": "draft"}
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
  }
}
```

### `lookup_catalog`

Maps to the [Catalog Lookup](http://ucp.dev/draft/specification/catalog/lookup/index.md) capability. See capability documentation for supported identifiers, resolution behavior, and client correlation requirements.

The `catalog.ids` parameter accepts an array of identifiers and optional context.

#### Lookup Request

Request body for catalog lookup.

| Name        | Type          | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ----------- | ------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ids         | Array[string] | **Yes**  | Identifiers to lookup. Implementations MUST support product ID and variant ID; MAY support secondary identifiers (SKU, handle, etc.).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| filters     | object        | No       | Filter criteria to narrow returned products and variants. All specified filters combine with AND logic.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| context     | object        | No       | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals     | object        | No       | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| attribution | object        | No       | Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.                                                                                                                                                                                                                                                                                                                                                                                                                                                        |

### Lookup Response

| Name     | Type          | Required | Description                                                                                                                                         |
| -------- | ------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp      | any           | **Yes**  | UCP metadata for catalog responses.                                                                                                                 |
| products | Array[any]    | **Yes**  | Products matching the requested identifiers. May contain fewer items if some identifiers not found, or more if identifiers match multiple products. |
| messages | Array[object] | No       | Errors, warnings, or informational messages about the requested items.                                                                              |

#### Lookup Example

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

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "structuredContent": {
      "ucp": {
        "version": "draft",
        "capabilities": {
          "dev.ucp.shopping.catalog.lookup": [
            {"version": "draft"}
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

When some identifiers are not found, the response includes the found products. The response MAY include informational messages indicating which identifiers were not found.

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "structuredContent": {
      "ucp": {
        "version": "draft",
        "capabilities": {
          "dev.ucp.shopping.catalog.lookup": [
            {"version": "draft"}
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

Maps to the [Catalog Lookup](http://ucp.dev/draft/specification/catalog/lookup/#get-product-get_product) capability. Returns a singular `product` object for full product detail with interactive option selection.

#### Get Product Request

Request body for single-product retrieval. Supports interactive variant narrowing via selected and preferences.

| Name        | Type          | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ----------- | ------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id          | string        | **Yes**  | Product or variant identifier. Implementations MUST support product ID and variant ID.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| selected    | Array[object] | No       | Partial or full option selections for interactive variant narrowing. When provided, response option values include availability signals (available, exists) relative to these selections.                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| preferences | Array[string] | No       | Option names in relaxation priority order. When no exact variant matches all selections, the server drops options from the end of this list first. E.g., ['Color', 'Size'] keeps Color and relaxes Size.                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| filters     | object        | No       | Filter criteria to narrow returned variants. All specified filters combine with AND logic.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| context     | object        | No       | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals     | object        | No       | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| attribution | object        | No       | Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.                                                                                                                                                                                                                                                                                                                                                                                                                                                        |

#### Get Product Response

| Name     | Type          | Required | Description                                                                                                |
| -------- | ------------- | -------- | ---------------------------------------------------------------------------------------------------------- |
| ucp      | any           | **Yes**  | UCP metadata for catalog responses.                                                                        |
| product  | object        | **Yes**  | The requested product with full detail. Singular — this is a single-resource operation.                    |
| messages | Array[object] | No       | Warnings or informational messages about the product (e.g., price recently changed, limited availability). |

#### Get Product Example

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
          "address_country": "US"
        }
      }
    }
  }
}
```

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "structuredContent": {
      "ucp": {
        "version": "draft",
        "capabilities": {
          "dev.ucp.shopping.catalog.lookup": [
            {"version": "draft"}
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
  }
}
```

#### Product Not Found

When the identifier does not resolve to a product, the server returns a successful JSON-RPC result with `ucp.status: "error"` and a descriptive message. This is an application outcome, not a transport error.

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "structuredContent": {
      "ucp": {
        "version": "draft",
        "status": "error",
        "capabilities": {
          "dev.ucp.shopping.catalog.lookup": [
            {"version": "draft"}
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
  }
}
```

## Error Handling

UCP uses a two-layer error model separating transport errors from business outcomes.

### Transport Errors

Transport-level failures (authentication, rate limiting, unavailability) that prevent request processing are returned as JSON-RPC `error`. See the [Core Specification](http://ucp.dev/draft/specification/overview/#error-codes) for the complete error code registry and JSON-RPC error code mappings.

### Business Outcomes

All application-level outcomes return a successful JSON-RPC result with the UCP envelope and optional `messages` array. See [Catalog Overview](http://ucp.dev/draft/specification/catalog/#messages-and-error-handling) for message semantics and common scenarios.

#### Example: All Products Not Found

When all requested identifiers fail to resolve, the response contains an empty `products` array. The response MAY include informational messages indicating which identifiers were not found.

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "structuredContent": {
      "ucp": {
        "version": "draft",
        "capabilities": {
          "dev.ucp.shopping.catalog.lookup": [
            {"version": "draft"}
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

Business outcomes use the JSON-RPC `result` field with messages in the response payload. See the [Partial Success](#partial-success) section for handling mixed results.

## Entities

### Detail Product

A product in a get_product response, extended with effective selections and availability signals on option values.

| Name     | Type          | Required | Description                                                                                                                                                                                          |
| -------- | ------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| selected | Array[object] | No       | Effective option selections that anchor the featured variant and availability signals. Required when the product has configurable options; may be empty or omitted for products with no option axes. |
| options  | Array[object] | No       | Product options with availability signals relative to the effective selections.                                                                                                                      |

### Get Product Response

| Name     | Type          | Required | Description                                                                                                |
| -------- | ------------- | -------- | ---------------------------------------------------------------------------------------------------------- |
| ucp      | any           | **Yes**  | UCP metadata for catalog responses.                                                                        |
| product  | object        | **Yes**  | The requested product with full detail. Singular — this is a single-resource operation.                    |
| messages | Array[object] | No       | Warnings or informational messages about the product (e.g., price recently changed, limited availability). |

### Error Response

| Name         | Type                                                        | Required | Description                                                       |
| ------------ | ----------------------------------------------------------- | -------- | ----------------------------------------------------------------- |
| ucp          | any                                                         | **Yes**  | UCP protocol metadata. Status MUST be 'error' for error response. |
| messages     | Array\[[Message](/draft/specification/reference/#message)\] | **Yes**  | Array of messages describing why the operation failed.            |
| continue_url | string                                                      | No       | URL for buyer handoff or session recovery.                        |

## Conformance

A conforming MCP transport implementation **MUST**:

1. Implement JSON-RPC 2.0 protocol correctly.
1. Implement tools for each catalog capability advertised in the business's UCP profile, per their respective capability requirements ([Search](http://ucp.dev/draft/specification/catalog/search/index.md), [Lookup](http://ucp.dev/draft/specification/catalog/lookup/index.md)). Each capability may be adopted independently. When the Lookup capability is advertised, both `lookup_catalog` and `get_product` tools MUST be available.
1. Use JSON-RPC errors for transport issues; use `messages` array for business outcomes.
1. Return successful result for lookup requests; unknown identifiers result in fewer products returned (MAY include informational `not_found` messages).
1. Validate tool inputs against UCP schemas.
1. Return products with valid `Price` objects (amount + currency).
1. Support cursor-based pagination with default limit of 10.
1. Return `-32602` (Invalid params) for requests exceeding batch size limits.
