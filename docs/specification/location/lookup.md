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

# Location Lookup Capability

* **Capability Name:** `dev.ucp.common.location.lookup`

Retrieves physical locations by their unique identifiers.
Supports full-detail batch retrieval of multiple locations to provide optionalities
or retrieval of a single location (useful for a dedicated location detail page).

## Operation

| Operation              | Description                                   |
| :--------------------- | :-------------------------------------------- |
| **Lookup Location(s)** | Retrieve single or multiple locations by ID.  |

## Supported Identifiers

The `ids` parameter accepts an array of identifiers. Implementations **MUST**
support lookup by the business's stable location ID.

Duplicate identifiers in the request **MUST** be deduplicated by the server.
When multiple identifiers resolve to the same physical location,
it **MUST** be returned only once in the response.

### Client Correlation

The response does not guarantee order. Clients correlate returned locations
simply by matching the returned `id` field against their requested `ids`.

### Batch Size

Implementations **SHOULD** accept at least 10 identifiers per request.
Implementations **MAY** enforce a maximum batch size and **MUST** reject
requests exceeding their limit with an appropriate error (HTTP 400
`request_too_large` for REST, JSON-RPC `-32602` for MCP).

### Filters

Optional `filters` (hours, offerings/inventory, geo) are accepted
to narrow down the returned locations.
Filters use the same schema and AND semantics as [Search Filters](search.md#search-filters).

Filters apply **after** identifier resolution. For example, if a client requests
`["loc_downtown", "loc_uptown"]` with a filter of `hours.open_now: true`:

1. The server first resolves both identifiers to their respective locations.
2. The server then evaluates the `open_now` filter against each resolved location.
3. If `loc_uptown` is currently closed, it is excluded, and only `loc_downtown` is returned.

### Request

{{ extension_schema_fields('location_lookup.json#/$defs/lookup_request', 'location') }}

### Response

{{ extension_schema_fields('location_lookup.json#/$defs/lookup_response', 'location') }}

## Transport Bindings

* [REST Binding](rest.md#post-locationslookup): `POST /locations/lookup`
* [MCP Binding](mcp.md#lookup_locations): `lookup_locations` tool
