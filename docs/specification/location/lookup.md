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

Filters apply **after** identifier resolution. For example, if a Platform
requests `["loc_downtown", "loc_uptown"]` with an hours filter of
`{"open_at": "2026-05-18T17:00:00Z"}`:

1. The Business first resolves both identifiers to their respective Locations.
2. The Business evaluates the supplied instant against each resolved Location.
3. If `loc_uptown` is closed at that instant, the Business excludes it and
    returns only `loc_downtown`.

### Request

{{ extension_schema_fields('location_lookup.json#/$defs/lookup_request', 'location') }}

### Response

{{ extension_schema_fields('location_lookup.json#/$defs/lookup_response', 'location') }}

## Examples {: #examples }

The following request and response are transport-neutral UCP payloads.

### Downtown Store schedule

=== "Request"

    <!-- ucp:example schema=common/location_lookup op=lookup direction=request -->
    ```json
    {
      "ids": ["loc_downtown"]
    }
    ```

=== "Response"

    <!-- ucp:example schema=common/location_lookup op=lookup direction=response -->
    ```json
    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.common.location.lookup": [
            {"version": "{{ ucp_version }}"}
          ]
        }
      },
      "locations": [
        {
          "id": "loc_downtown",
          "name": "Downtown Store",
          "address": {
            "street_address": "100 Broadway",
            "address_locality": "New York",
            "address_region": "NY",
            "address_country": "US",
            "postal_code": "10005"
          },
          "geo": {
            "latitude": 40.707,
            "longitude": -74.011
          },
          "amenities": [
            "dev.ucp.amenity.shopping.curbside_pickup",
            "dev.ucp.amenity.shopping.in_store_pickup",
            "dev.ucp.amenity.parking"
          ],
          "timezone": "America/New_York",
          "hours": [
            {"day": "monday", "opens": "09:00", "closes": "21:00"},
            {"day": "tuesday", "opens": "09:00", "closes": "12:00"},
            {"day": "tuesday", "opens": "13:00", "closes": "21:00"},
            {"day": "wednesday", "opens": "09:00", "closes": "21:00"},
            {"day": "thursday", "opens": "09:00", "closes": "21:00"},
            {"day": "friday", "opens": "09:00", "closes": "22:00"},
            {"day": "saturday", "opens": "10:00", "closes": "20:00"}
          ],
          "exception_hours": [
            {
              "title": "Thanksgiving",
              "valid_from": "2026-11-26",
              "valid_through": "2026-11-26"
            }
          ]
        }
      ]
    }
    ```

Tuesday's two `hours` entries form a split shift. Sunday has no `hours` entry,
meaning no regular interval begins that day. The `exception_hours` entry omits
`opens` and `closes`, making it a full closure.
See [Operating Hours](index.md#operating-hours) for schedule representation and
evaluation rules.

### Partial success

=== "Request"

    <!-- ucp:example schema=common/location_lookup op=lookup direction=request -->
    ```json
    {
      "ids": ["loc_downtown", "loc_invalid_id"]
    }
    ```

=== "Response"

    <!-- ucp:example schema=common/location_lookup op=lookup direction=response -->
    ```json
    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.common.location.lookup": [
            {"version": "{{ ucp_version }}"}
          ]
        }
      },
      "locations": [
        {
          "id": "loc_downtown",
          "name": "Downtown Store"
        }
      ],
      "messages": [
        {
          "type": "info",
          "code": "not_found",
          "content": "Unable to find the location associated with loc_invalid_id."
        }
      ]
    }
    ```

The request succeeds with the Locations that resolve. A Business can use an
informational `not_found` message to identify an unresolved ID.

## Transport Bindings

* [REST Binding](rest.md#post-locationslookup): `POST /locations/lookup`
* [MCP Binding](mcp.md#lookup_locations): `lookup_locations` tool
