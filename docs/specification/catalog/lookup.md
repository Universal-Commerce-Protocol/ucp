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
identifiers (e.g., from a saved list, deep links, or cart validation).

## Operation

| Operation | Description |
| :--- | :--- |
| **Lookup Catalog** | Retrieve products or variants by identifier. |

### Supported Identifiers

The `ids` parameter accepts an array of identifiers. Implementations MUST support
lookup by product ID and variant ID. Implementations MAY additionally support
secondary identifiers such as SKU or handle, provided these are also fields on
the returned product object.

Duplicate identifiers in the request MUST be deduplicated. When an identifier
matches multiple products (e.g., a SKU shared across variants), all matching
products MUST be returned. When multiple identifiers resolve to the same product,
it MUST be returned once. The `products` array may contain fewer or more items
than requested identifiers.

### Client Correlation

The response does not guarantee order or provide explicit identifier-to-product
mapping. Clients correlate results by matching fields in the returned products
(e.g., `id`, `sku`, `handle`) against the requested identifiers.

### Batch Size

Implementations SHOULD accept at least 10 identifiers per request. Implementations
MAY enforce a maximum batch size and MUST reject requests exceeding their limit
with an appropriate error (HTTP 400 `request_too_large` for REST, JSON-RPC
`-32602` for MCP).

### Resolution Behavior

For each identifier, the response returns the parent product with full context
(title, description, media, options):

* **Product ID lookup**: `variants` MAY contain a representative set.
* **Variant ID lookup**: `variants` MUST contain only the requested variant.

When the variant set is large, a representative set MAY be returned based on
buyer context or other criteria. This ensures agents always have product context
for display while getting exactly what they requested.

### Request

{{ extension_schema_fields('catalog_lookup.json#/$defs/lookup_request', 'catalog') }}

### Response

{{ extension_schema_fields('catalog_lookup.json#/$defs/lookup_response', 'catalog') }}

## Transport Bindings

* [REST Binding](rest.md#post-cataloglookup): `POST /catalog/lookup`
* [MCP Binding](mcp.md#lookup_catalog): `lookup_catalog` tool
