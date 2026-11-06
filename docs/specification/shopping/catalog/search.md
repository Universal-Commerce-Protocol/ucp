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

Performs a search against the Business's product catalog. Supports free-text
queries, search by similarity to a product or variant, filtering by category
and price, and pagination.

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
one or more `filters`, one or more `like` anchors, or an extension-defined
input. When both `query` and `like` are omitted, the request represents a
browse operation — the Business returns products matching the provided
filters; with no ranking input, their order is Business-determined.

The Business **MUST** validate that incoming requests contain at least one
recognized input and **SHOULD** reject empty or invalid requests with an
appropriate error. The Business defines and enforces its own rules for
input presence and content — for example, requiring `query`, rejecting
empty `query` strings, or accepting filter-only requests for category browsing.

### Similarity Anchors

`like` lists similarity anchors: products or variants the results should
resemble — "more like this" from an item the Buyer is viewing. Combined
with `query`, an anchor and the text rank together — for example, items
resembling a given shoe that also match "waterproof". Functional
replacements for an unavailable item are `substitutes` in
[Catalog Lookup](lookup.md#includes), not an anchored search. Each anchor
carries one key naming its kind; core defines `id`.

{{ extension_schema_fields('catalog_search.json#/$defs/like_item', 'shopping/catalog') }}

#### Resolution

The Business resolves `id` as in Catalog Lookup's
[Supported Identifiers](lookup.md#supported-identifiers): it **MUST**
support product ID and variant ID anchors and **MAY** support secondary
identifiers such as SKU or handle. An identifier that resolves to several
items (for example a SKU shared across variants) makes each of them an
anchor.

#### Ranking

Results are ranked by resemblance to the request's inputs, as the Business
determines it. `query` and `like` both rank; `filters` narrow and never
rank. How `query` and multiple anchors combine, and whether weakly
resembling items are omitted or merely ranked low, is Business-determined —
as it is for text relevance. This specification does not define the
resemblance function, and the response does not indicate which anchor a
result resembles. A Platform **MUST NOT** infer that an item is dissimilar
from its absence.

#### Exclusion

An anchor is never returned as a result. A product anchor excludes the
whole product. A variant anchor excludes that variant only; its product
**MAY** appear with its other variants. The Platform chooses accordingly:
anchor on the product ID to exclude the model, on the variant ID to allow
other colors and sizes of it. The Business **MUST** treat anchors that
resolve to the same product or variant as one anchor (so a SKU and the
variant ID it resolves to are one); a product anchor subsumes anchors on
its variants. The Business **MUST NOT** return an anchored product or
variant on any page of the result set.

#### Unresolved Anchors

The Business drops an anchor that does not resolve and **SHOULD** add an
informational `not_found` message naming it, as Catalog Lookup does for an
unresolved identifier. Omitting the message is conformant but leaves the
Platform unable to tell a dropped anchor from a weak match. When no anchor
resolves, the Business **MUST** return an empty result regardless of
`query` or `filters` — the request's subject is gone, and the Business
**MUST NOT** substitute a text search or filter browse for it.

#### Unrecognized Anchor Kinds

The Business **MUST** ignore an item whose anchor key it does not recognize,
such as an extension-defined kind it does not implement. If no recognized
input remains, the [Search Inputs](#search-inputs) rule applies.

#### Anchor Limit

A Business **MAY** enforce a maximum number of anchors. When a request
exceeds it, the Business **MUST** process the first maximum number of
distinct anchors in request order and include an informational
`batch_limit_applied` message stating the maximum and how many anchors were
not processed, as [Location Lookup](../../common/location/lookup.md#batch-size)
does for identifiers. The Business **MUST NOT** report the omitted anchors as
unresolved.

#### Examples

Products resembling a variant, within a budget. The anchored variant is
excluded; other variants of its product can appear:

<!-- ucp:example schema=shopping/catalog_search op=search direction=request -->
```json
{
  "like": [
    { "id": "prod_abc123_size10" }
  ],
  "context": { "currency": "USD" },
  "filters": {
    "price": { "max": 15000 }
  },
  "pagination": { "limit": 10 }
}
```

A text query refined by an anchor. Results are ranked by resemblance to
both the query and the product; the anchored product is excluded:

<!-- ucp:example schema=shopping/catalog_search op=search direction=request -->
```json
{
  "query": "waterproof trail shoes",
  "like": [
    { "id": "prod_abc123" }
  ],
  "context": { "currency": "USD" },
  "filters": {
    "categories": ["Footwear"],
    "price": { "max": 15000 }
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
