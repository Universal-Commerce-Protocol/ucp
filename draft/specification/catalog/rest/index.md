# Catalog - REST Binding

This document specifies the HTTP/REST binding for the [Catalog Capability](http://ucp.dev/draft/specification/catalog/index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise REST transport availability through their UCP profile at `/.well-known/ucp`.

```json
{
  "ucp": {
    "version": "draft",
    "services": {
      "dev.ucp.shopping": [
        {
          "version": "draft",
          "spec": "https://ucp.dev/draft/specification/overview",
          "transport": "rest",
          "schema": "https://ucp.dev/draft/services/shopping/rest.openapi.json",
          "endpoint": "https://business.example.com/ucp"
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
    },
    "payment_handlers": {}
  }
}
```

## Endpoints

| Endpoint           | Method | Capability                                                                           | Description                            |
| ------------------ | ------ | ------------------------------------------------------------------------------------ | -------------------------------------- |
| `/catalog/search`  | POST   | [Search](http://ucp.dev/draft/specification/catalog/search/index.md)                 | Search for products.                   |
| `/catalog/lookup`  | POST   | [Lookup](http://ucp.dev/draft/specification/catalog/lookup/index.md)                 | Lookup one or more products by ID.     |
| `/catalog/product` | POST   | [Lookup](http://ucp.dev/draft/specification/catalog/lookup/#get-product-get_product) | Get full product detail by identifier. |

### `POST /catalog/search`

Maps to the [Catalog Search](http://ucp.dev/draft/specification/catalog/search/index.md) capability.

**Inputs**

| Name        | Type                                                                     | Requirement | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ----------- | ------------------------------------------------------------------------ | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| query       | string                                                                   | Optional    | Free-text search query.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| context     | [Context](/draft/specification/reference/#context)                       | Optional    | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals     | [Signals](/draft/specification/reference/#signals)                       | Optional    | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| attribution | [Attribution](/draft/specification/reference/#attribution)               | Optional    | Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| filters     | [Search Filters](/draft/specification/reference/#search-filters)         | Optional    | Filter criteria to narrow search results. All specified filters combine with AND logic.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| pagination  | [Pagination Request](/draft/specification/reference/#pagination-request) | Optional    | Cursor-based pagination for list operations.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |

**Output**

| Name       | Type                                                                       | Requirement  | Description                                                             |
| ---------- | -------------------------------------------------------------------------- | ------------ | ----------------------------------------------------------------------- |
| ucp        | any                                                                        | **Required** | UCP metadata for catalog responses.                                     |
| products   | Array\[[Product](/draft/specification/reference/#product)\]                | **Required** | Products matching the search criteria.                                  |
| pagination | [Pagination Response](/draft/specification/reference/#pagination-response) | Optional     | Cursor-based pagination for list operations.                            |
| actions    | [Actions](/draft/specification/reference/#actions)                         | Optional     | Outstanding extension-defined Actions for this catalog search response. |
| messages   | Array\[[Message](/draft/specification/reference/#message)\]                | Optional     | Errors, warnings, or informational messages about the search results.   |

#### Example

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

```json
{
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
```

### `POST /catalog/lookup`

Maps to the [Catalog Lookup](http://ucp.dev/draft/specification/catalog/lookup/index.md) capability. See capability documentation for supported identifiers, resolution behavior, and client correlation requirements.

The request body contains an array of identifiers and optional context that applies to all lookups in the batch.

**Inputs**

| Name        | Type                                                             | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ----------- | ---------------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ids         | Array[string]                                                    | **Required** | Identifiers to lookup. Implementations MUST support product ID and variant ID; MAY support secondary identifiers (SKU, handle, etc.).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| filters     | [Search Filters](/draft/specification/reference/#search-filters) | Optional     | Filter criteria to narrow returned products and variants. All specified filters combine with AND logic.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| context     | [Context](/draft/specification/reference/#context)               | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals     | [Signals](/draft/specification/reference/#signals)               | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| attribution | [Attribution](/draft/specification/reference/#attribution)       | Optional     | Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.                                                                                                                                                                                                                                                                                                                                                                                                                                                        |

**Output**

| Name     | Type                                                        | Requirement  | Description                                                                                                                                         |
| -------- | ----------------------------------------------------------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp      | any                                                         | **Required** | UCP metadata for catalog responses.                                                                                                                 |
| products | Array\[[Product](/draft/specification/reference/#product)\] | **Required** | Products matching the requested identifiers. May contain fewer items if some identifiers not found, or more if identifiers match multiple products. |
| actions  | [Actions](/draft/specification/reference/#actions)          | Optional     | Outstanding extension-defined Actions for this catalog lookup response.                                                                             |
| messages | Array\[[Message](/draft/specification/reference/#message)\] | Optional     | Errors, warnings, or informational messages about the requested items.                                                                              |

#### Example: Batch Lookup with Context

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

```json
{
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
          "description": { "plain": "Variante talla 10" },
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

When some identifiers in the batch are not found, the response includes the found products in the `products` array. The response MAY include informational messages indicating which identifiers were not found.

```json
{
  "ids": ["prod_abc123", "prod_invalid", "prod_def456"]
}
```

```json
{
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
      "description": { "plain": "Lightweight running shoes." },
      "variants": [ ... ],
      "price_range": {
        "min": { "amount": 12000, "currency": "USD" },
        "max": { "amount": 12000, "currency": "USD" }
      }
    },
    {
      "id": "prod_def456",
      "title": "Trail Blazer X",
      "description": { "plain": "Trail shoes with superior traction." },
      "variants": [ ... ],
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

Maps to the [Catalog Lookup](http://ucp.dev/draft/specification/catalog/lookup/#get-product-get_product) capability. Returns a singular `product` object (not an array) for full product detail page rendering.

**Inputs**

| Name        | Type                                                                        | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ----------- | --------------------------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| id          | string                                                                      | **Required** | Product or variant identifier. Implementations MUST support product ID and variant ID.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| selected    | Array\[[Selected Option](/draft/specification/reference/#selected-option)\] | Optional     | Partial or full option selections for interactive variant narrowing. When provided, response option values include availability signals (available, exists) relative to these selections.                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| preferences | Array[string]                                                               | Optional     | Option names in relaxation priority order. When no exact variant matches all selections, the server drops options from the end of this list first. E.g., ['Color', 'Size'] keeps Color and relaxes Size.                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| filters     | [Search Filters](/draft/specification/reference/#search-filters)            | Optional     | Filter criteria to narrow returned variants. All specified filters combine with AND logic.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| context     | [Context](/draft/specification/reference/#context)                          | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals     | [Signals](/draft/specification/reference/#signals)                          | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| attribution | [Attribution](/draft/specification/reference/#attribution)                  | Optional     | Platform-emitted referral and conversion-event context — campaign identifiers, click IDs, source/medium markers, etc. The same parameters platforms communicate via URL query parameters in browser-based flows.                                                                                                                                                                                                                                                                                                                                                                                                                                                        |

**Output**

This object MUST be one of the following types: [Catalog Lookup Get Product Response](/draft/specification/catalog/rest/#catalog-lookup-get-product-response), [Error Response](/draft/specification/reference/#error-response).

#### Example: With Option Selection

The user selected Color=Blue. The response includes availability signals on option values and returns variants matching the selection.

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

```json
{
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
```

Green is out of stock (`available: false, exists: true`). Size 11 doesn't exist in Blue (`exists: false`). Variants returned match the Color=Blue selection.

#### Product Not Found

When the identifier does not resolve to a product, the server returns HTTP 200 with `ucp.status: "error"` and a descriptive message. This is an application outcome, not a transport error — the handler executed and reports its result via the UCP envelope.

```json
{
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
```

Unlike `/catalog/lookup` (which returns partial results for batch requests), `/catalog/product` is a single-resource operation. A missing product is an application error with `unrecoverable` severity — the agent should not retry with the same identifier.

## HTTP Headers

The following headers are defined for the HTTP binding and apply to all operations unless otherwise noted.

**Request Headers**

| Header            | Required | Description                                                                                                                                                                                                                                                   |
| ----------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Authorization`   | No       | Should contain oauth token representing the following 2 schemes: 1. Platform self authenticating (client_credentials). 2. Platform authenticating on behalf of end user (authorization_code).                                                                 |
| `X-API-Key`       | No       | Authenticates the platform with a reusable api key allocated to the platform by the business.                                                                                                                                                                 |
| `Signature`       | No       | RFC 9421 HTTP Message Signature. Required when using HTTP Message Signatures for authentication. Format: `sig1=:<base64-signature>:`.                                                                                                                         |
| `Signature-Input` | No       | RFC 9421 Signature-Input header. Required when using HTTP Message Signatures for authentication. Format: `sig1=("@method" "@path" ...);created=<timestamp>;keyid="<key-id>"`.                                                                                 |
| `Content-Digest`  | No       | Body digest per RFC 9530. Required for requests/responses with a body. Format: `sha-256=:<base64-digest>:`.                                                                                                                                                   |
| `Request-Id`      | **Yes**  | For tracing the requests across network layers and components.                                                                                                                                                                                                |
| `User-Agent`      | No       | Identifies the user agent string making the call.                                                                                                                                                                                                             |
| `UCP-Agent`       | **Yes**  | Identifies the UCP agent making the call. All requests MUST include the UCP-Agent header containing the signer's profile URI using RFC 8941 Dictionary syntax. The URL MUST point to /.well-known/ucp. Format: profile="https://example.com/.well-known/ucp". |
| `Content-Type`    | No       | Representation Metadata. Tells the receiver what the data in the message body actually is.                                                                                                                                                                    |
| `Accept`          | No       | Content Negotiation. The client tells the server what data formats it is capable of understanding.                                                                                                                                                            |
| `Accept-Language` | No       | Localization. Tells the receiver the user's preferred natural languages, often with "weights" or priorities.                                                                                                                                                  |
| `Accept-Encoding` | No       | Compression. The client tells the server which content-codings it supports, usually for compression.                                                                                                                                                          |

**Response Headers**

| Header            | Required | Description                                                                                                           |
| ----------------- | -------- | --------------------------------------------------------------------------------------------------------------------- |
| `Signature`       | No       | RFC 9421 HTTP Message Signature for response. Contains the signature value in the format `sig1=:<base64-signature>:`. |
| `Signature-Input` | No       | RFC 9421 Signature-Input header for response. Describes signed components, timestamp, and key ID.                     |
| `Content-Digest`  | No       | JCS-canonicalized body digest per RFC 8785. Format: `sha-256=:<base64-digest>:`.                                      |

### Specific Header Requirements

- **UCP-Agent**: All requests **MUST** include the `UCP-Agent` header containing the platform profile URI using Dictionary Structured Field syntax ([RFC 8941](https://datatracker.ietf.org/doc/html/rfc8941)). Format: `profile="https://platform.example/profile"`.

## Error Handling

UCP uses a two-layer error model separating transport errors from business outcomes.

### Transport Errors

Use HTTP status codes for protocol-level issues that prevent request processing:

| Status | Meaning                                                     |
| ------ | ----------------------------------------------------------- |
| 400    | Bad Request - Malformed JSON or missing required parameters |
| 401    | Unauthorized - Missing or invalid authentication            |
| 429    | Too Many Requests - Rate limited                            |
| 500    | Internal Server Error                                       |

### Business Outcomes

All application-level outcomes return HTTP 200 with the UCP envelope and optional `messages` array. See [Catalog Overview](http://ucp.dev/draft/specification/catalog/#messages-and-error-handling) for message semantics and common scenarios.

#### Example: All Products Not Found

When all requested identifiers fail lookup, the `products` array is empty. The response MAY include informational messages indicating which identifiers were not found.

```json
{
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

### UCP Response Catalog

UCP metadata for catalog responses.

| Name             | Type   | Requirement  | Description                                                                 |
| ---------------- | ------ | ------------ | --------------------------------------------------------------------------- |
| version          | string | **Required** | UCP version in YYYY-MM-DD format.                                           |
| status           | string | Optional     | Application-level status of the UCP operation. **Enum:** `success`, `error` |
| services         | object | Optional     | Service registry keyed by reverse-domain name.                              |
| capabilities     | object | Optional     | Capability registry keyed by reverse-domain name.                           |
| payment_handlers | object | Optional     | Payment handler registry keyed by reverse-domain name.                      |
| capabilities     | any    | Optional     |                                                                             |

### Detail Product

A product in a get_product response, extended with effective selections and availability signals on option values.

| Name     | Type          | Requirement | Description                                                                                                                                                                                          |
| -------- | ------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| selected | Array[object] | Optional    | Effective option selections that anchor the featured variant and availability signals. Required when the product has configurable options; may be empty or omitted for products with no option axes. |
| options  | Array[object] | Optional    | Product options with availability signals relative to the effective selections.                                                                                                                      |

### Get Product Response

| Name     | Type          | Requirement  | Description                                                                                                |
| -------- | ------------- | ------------ | ---------------------------------------------------------------------------------------------------------- |
| ucp      | any           | **Required** | UCP metadata for catalog responses.                                                                        |
| product  | object        | **Required** | The requested product with full detail. Singular — this is a single-resource operation.                    |
| actions  | object        | Optional     | Outstanding extension-defined Actions for this product response.                                           |
| messages | Array[object] | Optional     | Warnings or informational messages about the product (e.g., price recently changed, limited availability). |

### Error Response

See [Error Response](/draft/specification/reference/#error-response) in the [Schema Reference](/draft/specification/reference/) for the canonical field definition.

## Conformance

A conforming REST transport implementation **MUST**:

1. Implement endpoints for each catalog capability advertised in the business's UCP profile, per their respective capability requirements ([Search](http://ucp.dev/draft/specification/catalog/search/index.md), [Lookup](http://ucp.dev/draft/specification/catalog/lookup/index.md)). Each capability may be adopted independently. When the Lookup capability is advertised, both `/catalog/lookup` and `/catalog/product` MUST be available.
1. Return products with valid `Price` objects (amount + currency).
1. Support cursor-based pagination with default limit of 10.
1. Return HTTP 200 for lookup requests; unknown identifiers result in fewer products returned (MAY include informational `not_found` messages).
1. Return HTTP 400 with `request_too_large` error for requests exceeding batch size limits.
