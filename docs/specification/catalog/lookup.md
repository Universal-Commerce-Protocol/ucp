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

# Catalog Lookup Capability

* **Capability Name:** `dev.ucp.shopping.catalog.lookup`

Retrieves products or variants by identifier. Use this when you already have
identifiers (e.g., from a saved list, deep links, cart validation, or a selected
product for detail rendering).

## Operations

| Operation | Tool / Endpoint | Description |
| :--- | :--- | :--- |
| **Batch Lookup** | `lookup_catalog` / `POST /catalog/lookup` | Retrieve multiple products by identifier. |
| **Get Product** | `get_product` / `POST /catalog/product` | Retrieve full detail for a single product. |

`lookup_catalog` resolves identifiers to products; `get_product` fetches
full detail for a known product or variant ID:

| Concern | `lookup_catalog` | `get_product` |
| :--- | :--- | :--- |
| **Input** | `ids[]` — product/variant ID; MAY support SKU, handle, URL, etc. | `id` — product or variant ID |
| **Purpose** | Resolve identifiers to products | Full product detail for purchase decisions with interactive option selection |
| **Variants** | One featured variant per product | Featured variant and relevant subset, filtered by option selections |

Use `lookup_catalog` when you have identifiers to resolve or display in a list.
Use `get_product` when a product has been identified and the agent needs full
detail, including interactive variant selection, for a purchase decision.

---

## Batch Lookup (`lookup_catalog`)

### Supported Identifiers

The `ids` parameter accepts an array of identifiers. Implementations MUST support
lookup by product ID and variant ID. Implementations MAY additionally support
secondary identifiers such as SKU or handle, provided these are also fields on
the returned product object.

Duplicate identifiers in the request MUST be deduplicated. When an identifier
matches multiple products (e.g., a SKU shared across variants), implementations
return matching products and MAY limit the result set. When multiple identifiers
resolve to the same product, it MUST be returned once.

### Client Correlation

The response does not guarantee order. Each variant carries an `inputs`
array identifying which request identifiers resolved to it, and how.

{{ schema_fields('types/input_correlation', 'catalog') }}

Multiple request identifiers may resolve to the same variant (e.g., a
product ID and one of its variant IDs). When this occurs, the variant's
`inputs` array contains one entry per resolved identifier, each with its
own match type. Variants without an `inputs` entry MUST NOT appear in
lookup responses.

### Batch Size

Implementations SHOULD accept at least 10 identifiers per request. Implementations
MAY enforce a maximum batch size and MUST reject requests exceeding their limit
with an appropriate error (HTTP 400 `request_too_large` for REST, JSON-RPC
`-32602` for MCP).

### Resolution Behavior

`match` reflects the resolution level of the identifier, not its type:

* **`exact`**: Identifier resolved directly to this variant
  (e.g., variant ID, SKU, barcode).
* **`featured`**: Identifier resolved to the parent product; server
  selected this variant as representative (e.g., product ID, handle).

### Filters

Both `lookup_catalog` and `get_product` accept optional `filters` to
narrow the returned products and variants. Filters use the same schema
and AND semantics as [Search Filters](search.md#search-filters) — for
example, a price filter excludes variants outside the specified range.

Filters apply *after* identifier resolution (lookup) or option selection
(get_product). An identifier that resolves to a product whose variants
all fall outside the price filter results in that product being excluded
from the response.

### Request

{{ extension_schema_fields('catalog_lookup.json#/$defs/lookup_request', 'catalog') }}

### Response

{{ extension_schema_fields('catalog_lookup.json#/$defs/lookup_response', 'catalog') }}

---

## Get Product (`get_product`)

Retrieves current product state for a single identifier, with support for
interactive variant selection and real-time availability signals. This is the
authoritative source for purchase decisions.

### Supported Identifiers

The `id` parameter accepts a single product ID or variant ID.

### Resolution Behavior

The response returns the product with complete context (title, description,
media, options) and a **subset of variants matching
[`product.selected`](#option-selection)**:

* **Product ID**: `variants` SHOULD contain the featured variant and other
  variants matching `product.selected`. When the request includes `selected`
  options, this narrows the subset to variants matching the client's choices.
* **Variant ID**: The requested variant MUST be the first element (featured).
  `product.selected` reflects that variant's options. Remaining variants
  match the same effective selections. When the request includes `selected`
  options that conflict with the variant's own options, the variant's
  options take precedence — the variant ID fully determines the selection
  state and `selected` is ignored.

### Response Shape

The response contains a singular `product` object (not an array). This reflects
the single-resource semantics of the operation. When the identifier is not found,
the server returns `ucp.status: "error"` with a `messages` array containing
the error detail. This is an application outcome — the handler ran and reports
its result via the UCP envelope, not a transport error.

### Option Selection

The `selected` and `preferences` parameters enable interactive variant
narrowing: the core product detail page interaction where a user progressively selects options
(Color, Size, etc.) and the UI updates availability in real time.

#### Input

* **`selected`**: Array of option selections (e.g., `[{"name": "Color", "label": "Red"}]`).
  Partial selections are valid; the client sends whatever the user has chosen so far.
  Each option name MUST appear at most once.
* **`preferences`**: Option names in relaxation priority order (e.g.,
  `["Color", "Size"]`). When no variant matches all selections, the server drops
  options from the **end** of this list first, keeping higher-priority selections
  intact. Optional; if omitted, the server uses its own relaxation heuristic.

#### Output: Effective Selections

The response MUST include `product.selected` when the product has
configurable options — reflecting the effective selections after any
relaxation when the request includes `selected`, or the featured
variant's default selections otherwise. When the product has no
configurable options, `selected` MAY be empty or omitted.

Clients that send `selected` detect relaxation by diffing their request
against `product.selected`:

* **No relaxation**: Response `selected` matches the request — all
  selections resolved to at least one variant.
* **Relaxation occurred**: Response `selected` is a subset of the
  request — the server dropped unresolvable options per `preferences`
  priority.

#### Output: Availability Signals

Option values in the response SHOULD include availability signals
relative to `product.selected`:

| `available` | `exists` | Meaning | UI Treatment |
| :--- | :--- | :--- | :--- |
| `true` | `true` | In stock — purchasable | Selectable |
| `false` | `true` | Out of stock — variant exists but unavailable | Disabled / strikethrough |
| `false` | `false` | No variant for this combination | Hidden or visually distinct |

These fields appear on each option value in `product.options[].values[]`. They
reflect availability **relative to the effective selections**. Changing a
selection changes the availability map.

### Request

{{ extension_schema_fields('catalog_lookup.json#/$defs/get_product_request', 'catalog') }}

### Response

{{ extension_schema_fields('catalog_lookup.json#/$defs/get_product_response', 'catalog') }}

---

## Transport Bindings

* [REST Binding](rest.md#post-cataloglookup): `POST /catalog/lookup` (batch)
* [REST Binding](rest.md#post-catalogproduct): `POST /catalog/product` (single)
* [MCP Binding](mcp.md#lookup_catalog): `lookup_catalog` tool (batch)
* [MCP Binding](mcp.md#get_product): `get_product` tool (single)
