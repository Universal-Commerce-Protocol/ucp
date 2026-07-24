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

# Catalog Search Capability

* **Capability Name:** `dev.ucp.shopping.catalog.search`

Performs a search against the business's product catalog. Supports free-text
queries, filtering by category, price, availability, and brand, and pagination.

## Operation

| Operation | Description |
| :--- | :--- |
| **Search Catalog** | Search for products using provided inputs and filters. |

### Request

{{ extension_schema_fields('catalog_search.json#/$defs/search_request', 'catalog') }}

### Response

{{ extension_schema_fields('catalog_search.json#/$defs/search_response', 'catalog') }}

## Search Inputs

A valid search request MUST include at least one of: a `query` string,
one or more `filters`, or an extension-defined input. When `query` is
omitted, the request represents a browse operation — the business returns
products matching the provided filters without text-relevance ranking.
Extensions MAY define additional inputs (e.g., visual similarity,
product references).

Implementations MUST validate that incoming requests contain at least one
recognized input and SHOULD reject empty or invalid requests with an
appropriate error. Implementations define and enforce their own rules for
input presence and content — for example, requiring `query`, rejecting
empty `query` strings, or accepting filter-only requests for category browsing.

## Search Filters

Filter criteria for narrowing search results. Standard filters are defined below;
merchants MAY support additional custom filters via `additionalProperties`.

{{ schema_fields('types/search_filters', 'catalog') }}

### Price Filter

{{ schema_fields('types/price_filter', 'catalog') }}

### Availability Filter

The `availability` filter narrows results to products with at least one variant
matching a listed status. Values use the same vocabulary defined in the variant
`availability.status` field.

When omitted, the business returns products regardless of availability status.
Businesses that do not track availability status MAY ignore this filter and
SHOULD notify the platform via a message.

### Brand Filter

The `brand` filter narrows results to products whose `brand` field matches any
listed value (OR logic). Matching SHOULD be case-insensitive. Businesses that
do not index brand data MAY ignore this filter.

## Pagination

Cursor-based pagination for list operations. Cursors are opaque strings
that implementations MAY encode as stateless keyset tokens.

### Page Size

The `limit` parameter is a requested page size, not a guaranteed count.
Implementations SHOULD accept a page size of at least 10. When the
requested limit exceeds the implementation's maximum, implementations
MAY clamp to their maximum silently — returning fewer results without
error. Clients MUST NOT assume the response size equals the requested limit.

### Pagination Request

{{ extension_schema_fields('types/pagination.json#/$defs/request', 'catalog') }}

### Pagination Response

{{ extension_schema_fields('types/pagination.json#/$defs/response', 'catalog') }}

## Actions

Search responses adopt the response-only `actions` map. The required `products`
array can be empty; the Business decides whether it contains zero, some, or all
otherwise relevant products under the Action-type contract. See
[Catalog — Actions](index.md#actions) for the parent contract and example, and
[Overview — Actions](../overview.md#actions) for the common rules.

## Transport Bindings

* [REST Binding](rest.md#post-catalogsearch): `POST /catalog/search`
* [MCP Binding](mcp.md#search_catalog): `search_catalog` tool
