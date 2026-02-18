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
matches multiple products (e.g., a SKU shared across variants), implementations
return matching products and MAY limit the result set. When multiple identifiers
resolve to the same product, it MUST be returned once.

### Client Correlation

The response does not guarantee order. Each variant carries an `input`
array identifying which request identifiers resolved to it, and how.

{{ schema_fields('types/input_correlation', 'catalog') }}

Multiple request identifiers may resolve to the same variant (e.g., a
product ID and one of its variant IDs). When this occurs, the variant's
`input` array contains one entry per resolved identifier, each with its
own match type. Variants without an `input` entry MUST NOT appear in
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

### Request

{{ extension_schema_fields('catalog_lookup.json#/$defs/lookup_request', 'catalog') }}

### Response

{{ extension_schema_fields('catalog_lookup.json#/$defs/lookup_response', 'catalog') }}

## Transport Bindings

* [REST Binding](rest.md#post-cataloglookup): `POST /catalog/lookup`
* [MCP Binding](mcp.md#lookup_catalog): `lookup_catalog` tool
