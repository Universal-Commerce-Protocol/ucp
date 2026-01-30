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

Retrieves a specific product or variant by its Global ID (GID). Use this when
you already have an ID (e.g., from a saved list, deep link, or cart validation).

## Operation

| Operation | Description |
| :--- | :--- |
| **Lookup Catalog** | Retrieve a specific product or variant by ID. |

### ID Resolution Behavior

The `id` parameter accepts either a product ID or variant ID. The response MUST
return the parent product with full context (title, description, media, options):

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

* [REST Binding](rest.md#get-catalogitemid): `GET /catalog/item/{id}`
* [MCP Binding](mcp.md#lookup_catalog): `lookup_catalog` tool
