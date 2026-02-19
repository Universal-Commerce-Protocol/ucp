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
queries, filtering by category and price, and pagination.

## Operation

| Operation | Description |
| :--- | :--- |
| **Search Catalog** | Search for products using query text and filters. |

### Request

{{ extension_schema_fields('catalog_search.json#/$defs/search_request', 'catalog') }}

### Response

{{ extension_schema_fields('catalog_search.json#/$defs/search_response', 'catalog') }}

## Search Filters

Filter criteria for narrowing search results. Standard filters are defined below;
merchants MAY support additional custom filters via `additionalProperties`.

{{ schema_fields('types/search_filters', 'catalog') }}

### Price Filter

{{ schema_fields('types/price_filter', 'catalog') }}

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

## Transport Bindings

* [REST Binding](rest.md#post-catalogsearch): `POST /catalog/search`
* [MCP Binding](mcp.md#search_catalog): `search_catalog` tool
