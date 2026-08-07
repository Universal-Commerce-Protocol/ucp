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

# Catalog List Capability

* **Capability Name:** `dev.ucp.shopping.catalog.list`

Enumerates a business's product catalog via cursor-based pagination. Unlike
search (query-driven, relevance-ranked), list returns all products in a stable,
deterministic order without requiring a query or filter.

## Operation

| Operation | Description |
| :--- | :--- |
| **List Catalog** | Paginate through the business's product catalog. |

### Request

{{ extension_schema_fields('catalog_list.json#/$defs/list_request', 'catalog') }}

### Response

{{ extension_schema_fields('catalog_list.json#/$defs/list_response', 'catalog') }}

## List Filters

Filter criteria for narrowing the enumerated set. When no filters are provided,
the operation returns all products in the catalog. Businesses MAY support
additional custom filters via `additionalProperties`.

{{ schema_fields('types/list_filters', 'catalog') }}

### Modified Since

The `modified_since` filter enables incremental sync. When provided, only
products created or updated at or after the given timestamp are returned.
"Modified" includes any change to the product or its variants (price,
availability, title, media, options, etc.).

Businesses that do not track modification timestamps MAY ignore this filter
and return the full catalog. When ignored, businesses SHOULD notify the
platform via a message with `code: "filter_ignored"`.

## Ordering

Products are returned in a stable, deterministic order. The ordering is
implementation-defined (typically by internal ID or creation time) and MUST
be consistent across pages within a single pagination sequence.

## Pagination

Uses the same cursor-based pagination as catalog search. Cursors are opaque
strings that implementations MAY encode as stateless keyset tokens.

### Page Size

Implementations SHOULD accept a page size of at least 100 for list operations.
When the requested limit exceeds the implementation's maximum, implementations
MAY clamp to their maximum silently. Clients MUST NOT assume the response size
equals the requested limit.

### Pagination Request

{{ extension_schema_fields('types/pagination.json#/$defs/request', 'catalog') }}

### Pagination Response

{{ extension_schema_fields('types/pagination.json#/$defs/response', 'catalog') }}

## Deleted Products

Businesses MAY signal deletions via a message with `code: "deleted"` and the
product ID in `content`. Platforms that need deletion detection SHOULD maintain
a local manifest and diff against list results.

## Transport Bindings

* [REST Binding](rest.md#post-cataloglist): `POST /catalog/list`
* [MCP Binding](mcp.md#list_catalog): `list_catalog` tool
