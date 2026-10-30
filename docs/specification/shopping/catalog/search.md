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
queries, relational discovery (recommendations and swaps), filtering by
category and price, and pagination.

## Operation

| Operation | Description |
| :--- | :--- |
| **Search Catalog** | Search for products using provided inputs and filters. |

### Request

{{ extension_schema_fields('catalog_search.json#/$defs/search_request', 'shopping/catalog') }}

### Response

{{ extension_schema_fields('catalog_search.json#/$defs/search_response', 'shopping/catalog') }}

## Search Inputs

A valid search request **MUST** include at least one of: a `query` string,
one or more `filters`, a non-`search` `purpose` (with or without
`reference_ids`), or an extension-defined input. When `purpose` is `search`
(or omitted) and `query` is omitted, a filter-based request represents a browse
operation where the Business returns products matching the provided filters
without text-relevance ranking. Extensions **MAY** define additional inputs
(e.g., visual similarity).

A Business **MUST** validate that incoming requests contain at least one
recognized input and **SHOULD** reject empty or invalid requests with an
appropriate error. A Business defines and enforces its own rules for input
presence and content (for example, requiring `query`, rejecting empty `query`
strings, or accepting filter-only requests for category browsing).

### Purpose and Reference Identifiers

The `purpose` and `reference_ids` fields support relational and intent-specific
catalog discovery:

* **`search`** (default when `purpose` is omitted): Standard free-text search
    or filter-based browse.
* **`recommendation`**: Returns complementary, related, or personalized items
    anchored to `reference_ids` and/or `context`.
* **`swap`**: Returns functional substitute items for the anchor product or
    variant in `reference_ids`.

#### Supported Purposes

Support for `recommendation` and `swap` varies by Business, so a Business
advertises the non-default `purpose` values it supports in its catalog search
capability `config.purposes`. Each key is a supported value; an empty object
means the value is supported with no additional policy. `search` is always
supported and need not be listed. When `config` or `purposes` is absent or
empty, only `search` is supported.

{{ extension_schema_fields('catalog_search.json#/$defs/business_config', 'shopping/catalog') }}

A Business that supports recommendations but not swaps declares:

<!-- ucp:example schema=profile def=business_schema target=$.ucp.capabilities -->
```json
{
  "dev.ucp.shopping.catalog.search": [
    {
      "version": "{{ ucp_version }}",
      "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/catalog/search",
      "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/catalog_search.json",
      "config": {
        "purposes": {
          "recommendation": {}
        }
      }
    }
  ]
}
```

A Platform **MUST NOT** send a `purpose` value that the Business does not
advertise. A Platform reads `config.purposes` from the Business profile it
already fetches for capability negotiation, so it can decide before calling
whether to offer recommendations or swaps.

The following rules apply:

1. **Pairing**: When `purpose` is `search` (or omitted), the request **MUST**
    include at least one of `query`, `filters`, or an extension-defined input;
    `reference_ids` does not apply, and the Business **MUST** ignore it if
    present. When `purpose` is `swap`, `reference_ids` **MUST** contain exactly
    one identifier; a Platform that needs substitutes for several items sends
    one request per item. A Business **MUST** reject requests that violate
    these pairing rules. For `recommendation`, multiple `reference_ids` jointly
    describe one anchor set: the Business returns candidates related to that
    set as a whole, results need not relate to every anchor, and the response
    does not correlate results to individual anchors.
2. **Supported Identifiers**: A Business **MUST** support lookup of
    `reference_ids` by product ID and variant ID, and **MAY** additionally
    support the secondary identifiers permitted by
    [Catalog Lookup](lookup.md#supported-identifiers). When one identifier
    resolves to several products or variants (for example, a shared SKU), each
    is an anchor and each is excluded under Self-Exclusion. When a specific
    variant is known (e.g., swapping an unavailable cart item), a Platform
    **SHOULD** supply the variant ID so the Business can match variant-level
    attributes (such as options, price, and `quantity_unit`). When
    `reference_ids` is provided, the Business evaluates the request using the
    identifiers that resolve (and **MAY** include informational `not_found`
    messages for unresolved identifiers); if none resolve, the Business
    **MUST** return an empty `products` array rather than falling back to a
    general browse. This applies to `recommendation` even when `context` alone
    could drive results; a Platform that wants contextual recommendations
    omits `reference_ids`.
3. **Self-Exclusion**: The Business **MUST** exclude any product or variant
    listed in `reference_ids` from the response. When a variant ID is supplied,
    the Business **MUST** exclude its parent product for `recommendation`, and
    **SHOULD** exclude its parent product for `swap` unless returning a
    distinct substitute variant of that product. A distinct substitute variant
    is a different variant of the same product (for example, Size 10 Wide for
    Size 10). Excluding a variant means it **MUST NOT** appear in the product's
    `variants[]` (so it is never the featured `variants[0]`); a product left
    with no returnable variants is omitted. Product-level fields follow the
    same treatment as when `filters` exclude variants.
4. **Combination with Query and Filters**: A request **MAY** combine
    `reference_ids` with `query` (e.g., a guided swap where the buyer specifies
    a preference) and `filters`. Supplied `filters` narrow the returned
    candidates (with the `AND` semantics of [Search Filters](#search-filters));
    they do not constrain resolution of `reference_ids`.
5. **Unsupported Purpose**: A Business that receives a `purpose` value it
    does not support (for example, from a Platform acting on a stale profile)
    **MUST** reject the request using the binding's invalid-request mechanism
    (HTTP 400 `unsupported_purpose` for REST, JSON-RPC `-32602` for MCP). It
    **MUST NOT** ignore `purpose` and fall back to a general browse.

#### Example: Guided Product Swap

Supplying a variant ID (`prod_abc123_size10`) lets the Business find functional
substitutes that match the unavailable variant's options (such as Size 10),
while `query` guides the swap toward the buyer's stated preference:

<!-- ucp:example schema=shopping/catalog_search op=search direction=request -->
```json
{
  "purpose": "swap",
  "reference_ids": ["prod_abc123_size10"],
  "query": "waterproof",
  "context": {
    "location": "loc_downtown",
    "currency": "USD"
  },
  "filters": {
    "price": {
      "max": 15000
    }
  },
  "pagination": {
    "limit": 5
  }
}
```

#### Example: Product Recommendation

`reference_ids` accepts product IDs, variant IDs, or a mix of both (e.g.,
recommending complementary items for a product and variant in the session):

<!-- ucp:example schema=shopping/catalog_search op=search direction=request -->
```json
{
  "purpose": "recommendation",
  "reference_ids": ["prod_abc123", "var_xyz789"],
  "context": {
    "address_country": "US",
    "currency": "USD"
  },
  "pagination": {
    "limit": 10
  }
}
```

## Search Filters

Filter criteria for narrowing search results. Standard filters are defined below;
merchants MAY support additional custom filters via `additionalProperties`.

{{ schema_fields('types/search_filters', 'shopping/catalog') }}

### Price Filter

{{ schema_fields('types/price_filter', 'shopping/catalog') }}

## Pagination

Cursor-based pagination for list operations. Cursors are opaque strings. A
Business **MAY** encode them as stateless keyset tokens.

### Page Size

The `limit` parameter is a requested page size, not a guaranteed result
count. When `limit` is omitted, the Business **MUST** apply a default page
size. A default of 10 is **RECOMMENDED**, but the Business **MAY** choose
another value.

The Business **MAY** return fewer results than the requested or default page
size, including when enforcing its maximum page size. A Platform **MUST NOT**
assume that the response count equals either value.

### Pagination Request

{{ extension_schema_fields('types/pagination.json#/$defs/request', 'shopping/catalog') }}

### Pagination Response

{{ extension_schema_fields('types/pagination.json#/$defs/response', 'shopping/catalog') }}

## Actions

Search responses adopt the response-only `actions` map. The required `products`
array can be empty; the Business decides whether it contains zero, some, or all
otherwise relevant products under the Action-type contract. See
[Catalog — Actions](index.md#actions) for the parent contract and example, and
[Overview — Actions](../../overview/index.md#actions) for the common rules.

## Transport Bindings

* [REST Binding](rest.md#post-catalogsearch): `POST /catalog/search`
* [MCP Binding](mcp.md#search_catalog): `search_catalog` tool
