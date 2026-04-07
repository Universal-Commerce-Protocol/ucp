# Catalog Search Capability

- **Capability Name:** `dev.ucp.shopping.catalog.search`

Performs a search against the business's product catalog. Supports free-text queries, filtering by category and price, and pagination.

## Operation

| Operation          | Description                                            |
| ------------------ | ------------------------------------------------------ |
| **Search Catalog** | Search for products using provided inputs and filters. |

### Request

| Name       | Type   | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ---------- | ------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| query      | string | No       | Free-text search query.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| context    | object | No       | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals    | object | No       | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| filters    | object | No       | Filter criteria to narrow search results. All specified filters combine with AND logic.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| pagination | object | No       | Pagination parameters for requests.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |

### Response

| Name       | Type          | Required | Description                                                           |
| ---------- | ------------- | -------- | --------------------------------------------------------------------- |
| ucp        | any           | **Yes**  | UCP metadata for catalog responses.                                   |
| products   | Array[object] | **Yes**  | Products matching the search criteria.                                |
| pagination | object        | No       | Pagination information in responses.                                  |
| messages   | Array[object] | No       | Errors, warnings, or informational messages about the search results. |

## Search Inputs

A valid search request MUST include at least one of: a `query` string, one or more `filters`, or an extension-defined input. When `query` is omitted, the request represents a browse operation — the business returns products matching the provided filters without text-relevance ranking. Extensions MAY define additional inputs (e.g., visual similarity, product references).

Implementations MUST validate that incoming requests contain at least one recognized input and SHOULD reject empty or invalid requests with an appropriate error. Implementations define and enforce their own rules for input presence and content — for example, requiring `query`, rejecting empty `query` strings, or accepting filter-only requests for category browsing.

## Search Filters

Filter criteria for narrowing search results. Standard filters are defined below; merchants MAY support additional custom filters via `additionalProperties`.

| Name       | Type                                                         | Required | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ---------- | ------------------------------------------------------------ | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| categories | Array[string]                                                | No       | Filter by product categories (OR logic — matches products in any listed categories). Values match against the value field in product category entries. Valid values can be discovered from the categories field in search results, merchant documentation, or standard taxonomies that businesses may align with.                                                                                                                                                |
| price      | [Price Filter](/draft/specification/reference/#price-filter) | No       | Price range filter denominated in context.currency. When context.currency matches the presentment currency, businesses apply the filter directly. When it differs, businesses SHOULD convert filter values to the presentment currency before applying; if conversion is not supported, businesses MAY ignore the filter and SHOULD indicate this via a message. When context.currency is absent, filter denomination is ambiguous and businesses MAY ignore it. |

### Price Filter

| Name | Type                                             | Required | Description                            |
| ---- | ------------------------------------------------ | -------- | -------------------------------------- |
| min  | [Amount](/draft/specification/reference/#amount) | No       | Minimum price in ISO 4217 minor units. |
| max  | [Amount](/draft/specification/reference/#amount) | No       | Maximum price in ISO 4217 minor units. |

## Pagination

Cursor-based pagination for list operations. Cursors are opaque strings that implementations MAY encode as stateless keyset tokens.

### Page Size

The `limit` parameter is a requested page size, not a guaranteed count. Implementations SHOULD accept a page size of at least 10. When the requested limit exceeds the implementation's maximum, implementations MAY clamp to their maximum silently — returning fewer results without error. Clients MUST NOT assume the response size equals the requested limit.

### Pagination Request

Pagination parameters for requests.

| Name   | Type    | Required | Description                                                        |
| ------ | ------- | -------- | ------------------------------------------------------------------ |
| cursor | string  | No       | Opaque cursor from previous response.                              |
| limit  | integer | No       | Requested page size. Implementations MAY clamp to a lower maximum. |

### Pagination Response

Pagination information in responses.

| Name          | Type    | Required | Description                                                                           |
| ------------- | ------- | -------- | ------------------------------------------------------------------------------------- |
| cursor        | string  | No       | Cursor to fetch the next page of results. MUST be present when has_next_page is true. |
| has_next_page | boolean | **Yes**  | Whether more results are available.                                                   |
| total_count   | integer | No       | Total number of matching items, if available.                                         |

## Transport Bindings

- [REST Binding](http://ucp.dev/draft/specification/catalog/rest/#post-catalogsearch): `POST /catalog/search`
- [MCP Binding](http://ucp.dev/draft/specification/catalog/mcp/#search_catalog): `search_catalog` tool
