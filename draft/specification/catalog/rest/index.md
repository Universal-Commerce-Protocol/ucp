# Catalog - REST Binding

This document specifies the HTTP/REST binding for the [Catalog Capability](https://ucp.dev/draft/specification/catalog/index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise REST transport availability through their UCP profile at `/.well-known/ucp`.

```json
{
  "ucp": {
    "version": "draft",
    "services": {
      "dev.ucp.shopping": {
        "version": "draft",
        "spec": "https://ucp.dev/draft/specification/overview",
        "rest": {
          "schema": "https://ucp.dev/draft/services/shopping/rest.openapi.json",
          "endpoint": "https://business.example.com/ucp"
        }
      }
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

## Endpoints

| Endpoint          | Method | Capability                                                            | Description                        |
| ----------------- | ------ | --------------------------------------------------------------------- | ---------------------------------- |
| `/catalog/search` | POST   | [Search](https://ucp.dev/draft/specification/catalog/search/index.md) | Search for products.               |
| `/catalog/lookup` | POST   | [Lookup](https://ucp.dev/draft/specification/catalog/lookup/index.md) | Lookup one or more products by ID. |

### `POST /catalog/search`

Maps to the [Catalog Search](https://ucp.dev/draft/specification/catalog/search/index.md) capability.

**Inputs**

| Name       | Type                                                                     | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ---------- | ------------------------------------------------------------------------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| query      | string                                                                   | No       | Free-text search query.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| context    | [Context](/draft/specification/reference/#context)                       | No       | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| filters    | [Search Filters](/draft/specification/reference/#search-filters)         | No       | Filter criteria to narrow search results. All specified filters combine with AND logic.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| pagination | [Pagination Request](/draft/specification/reference/#pagination-request) | No       | Cursor-based pagination for list operations.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |

**Output**

| Name       | Type                                                                                          | Required | Description                                                                                                             |
| ---------- | --------------------------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------- |
| ucp        | [Ucp Response Catalog Schema](/draft/specification/catalog/rest/#ucp-response-catalog-schema) | **Yes**  | Protocol metadata for discovery profiles and responses. Uses slim schema pattern with context-specific required fields. |
| products   | Array\[[Product](/draft/specification/reference/#product)\]                                   | **Yes**  | Products matching the search criteria.                                                                                  |
| pagination | [Pagination Response](/draft/specification/reference/#pagination-response)                    | No       | Cursor-based pagination for list operations.                                                                            |
| messages   | Array\[[Message](/draft/specification/reference/#message)\]                                   | No       | Errors, warnings, or informational messages about the search results.                                                   |

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
```

### `POST /catalog/lookup`

Maps to the [Catalog Lookup](https://ucp.dev/draft/specification/catalog/lookup/index.md) capability. See capability documentation for supported identifiers, resolution behavior, and client correlation requirements.

The request body contains an array of identifiers and optional context that applies to all lookups in the batch.

**Inputs**

| Name    | Type                                               | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ------- | -------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ids     | Array[string]                                      | **Yes**  | Identifiers to lookup. Implementations MUST support product ID and variant ID; MAY support secondary identifiers (SKU, handle, etc.).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| context | [Context](/draft/specification/reference/#context) | No       | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |

**Output**

| Name     | Type                                                                                          | Required | Description                                                                                                                                         |
| -------- | --------------------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp      | [Ucp Response Catalog Schema](/draft/specification/catalog/rest/#ucp-response-catalog-schema) | **Yes**  | Protocol metadata for discovery profiles and responses. Uses slim schema pattern with context-specific required fields.                             |
| products | Array[any]                                                                                    | **Yes**  | Products matching the requested identifiers. May contain fewer items if some identifiers not found, or more if identifiers match multiple products. |
| messages | Array\[[Message](/draft/specification/reference/#message)\]                                   | No       | Errors, warnings, or informational messages about the requested items.                                                                              |

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

All application-level outcomes return HTTP 200 with the UCP envelope and optional `messages` array. See [Catalog Overview](https://ucp.dev/draft/specification/catalog/#messages-and-error-handling) for message semantics and common scenarios.

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

| Name             | Type   | Required | Description                                                                 |
| ---------------- | ------ | -------- | --------------------------------------------------------------------------- |
| version          | string | **Yes**  | UCP version in YYYY-MM-DD format.                                           |
| status           | string | No       | Application-level status of the UCP operation. **Enum:** `success`, `error` |
| services         | object | No       | Service registry keyed by reverse-domain name.                              |
| capabilities     | object | No       | Capability registry keyed by reverse-domain name.                           |
| payment_handlers | object | No       | Payment handler registry keyed by reverse-domain name.                      |
| capabilities     | any    | No       |                                                                             |

## Conformance

A conforming REST transport implementation **MUST**:

1. Implement endpoints for each catalog capability advertised in the business's UCP profile, per their respective capability requirements ([Search](https://ucp.dev/draft/specification/catalog/search/index.md), [Lookup](https://ucp.dev/draft/specification/catalog/lookup/index.md)). Each capability may be adopted independently.
1. Return products with valid `Price` objects (amount + currency).
1. Support cursor-based pagination with default limit of 10.
1. Return HTTP 200 for lookup requests; unknown identifiers result in fewer products returned (MAY include informational `not_found` messages).
1. Return HTTP 400 with `request_too_large` error for requests exceeding batch size limits.
