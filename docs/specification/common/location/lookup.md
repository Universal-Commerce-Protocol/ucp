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

Resolves identifiers to physical Locations.
Supports full-detail batch retrieval of multiple Locations or retrieval of a
single Location (useful for a dedicated Location detail page), optionally
refined by the same explicit spatial relations and filters as Search (see
[Refinement](#refinement)).

## Operation

| Operation              | Description                                          |
| :--------------------- | :--------------------------------------------------- |
| **Lookup Location(s)** | Retrieve single or multiple Locations by identifier. |

## Supported Identifiers

The `ids` parameter accepts an array of identifiers. A Business **MUST**
support lookup by a Location's stable canonical `Location.id` and **MAY**
additionally support secondary or alias identifiers.

A Business **MUST** dedupe duplicate identifiers in the request. When an
identifier matches multiple Locations, the Business returns the matching
Locations and **MAY** limit the result set. When multiple identifiers resolve
to the same Location, the Business **MUST** return it only once.

### Platform Correlation

The response does not guarantee order. Each Location carries an `inputs`
array identifying which requested identifiers resolved to it. Every entry
contains a required `id`, copied exactly from the Lookup request.

Multiple request identifiers may resolve to the same Location. When this
occurs, the Location's `inputs` array contains one entry per resolved
identifier. A Business **MUST NOT** include a Location without an `inputs`
entry in a Lookup response.

### Batch Size

A Business **SHOULD** accept at least 10 identifiers per request and **MAY**
enforce a maximum batch size. The maximum applies after duplicate identifiers
are deduplicated.

When a request exceeds that maximum, the Business **MUST** process the first
maximum number of distinct identifiers in request order and return a successful
response for that prefix. It **MUST** include an informational message with
`code: "batch_limit_applied"`; the message content **MUST** state the applied
maximum and how many identifiers were not processed. The Business **MUST NOT**
evaluate the omitted suffix or report its identifiers as unresolved. A Platform
**MUST NOT** interpret the omitted suffix as unresolved and **MAY** submit it in
a subsequent request.

### Refinement

The Business first resolves the identifiers and deduplicates repeated values.
Optional root `distance` and `serves` relations and `filters` predicates then
refine the resolved set. All supplied criteria combine with AND: a resolved
Location is returned only when it satisfies every supplied relation and
filter. The relations and predicates use the same schemas and semantics as
Search — see [Spatial Relations](search.md#spatial-relations),
[Search Filters](search.md#search-filters), and
[Item Availability Filter](search.md#item-availability-filter).

For example, if a Platform requests `["loc_downtown", "loc_uptown"]` with an
hours filter of `{"open_at": "2026-05-18T17:00:00Z"}`:

1. The Business first resolves both identifiers to their respective Locations.
2. The Business evaluates the supplied instant against each resolved Location.
3. If `loc_uptown` is closed at that instant, the Business excludes it and
    returns only `loc_downtown`.

An identifier that does not resolve has no corresponding returned Location or
`inputs` entry. If an identifier resolves to a Location that fails any supplied
criterion, including because a `filters.items` identifier is unknown,
is unavailable, or cannot be evaluated there, that Location and its
corresponding `inputs` entry are omitted. The request
still succeeds. The Business **MAY** attach an informational `not_found`
message for an unresolved Location identifier, but no per-identifier
explanation is guaranteed for a refinement non-match.

### Request

{{ extension_schema_fields('location_lookup.json#/$defs/lookup_request', 'common/location') }}

### Response

{{ extension_schema_fields('location_lookup.json#/$defs/lookup_response', 'common/location') }}

## Examples {: #examples }

The following request and response are transport-neutral UCP payloads.

### Downtown Store schedule

=== "Request"

    <!-- ucp:example schema=common/location_lookup op=lookup direction=request -->
    ```json
    {
      "ids": ["loc_downtown", "downtown-store"]
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
          "inputs": [
            {"id": "loc_downtown"},
            {"id": "downtown-store"}
          ],
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
          "amenities": {
            "dev.ucp.amenity.shopping.curbside_pickup": {
              "description": "Curbside pickup"
            },
            "dev.ucp.amenity.shopping.in_store_pickup": {
              "description": "In-store pickup"
            },
            "dev.ucp.amenity.parking": {
              "description": "On-site parking"
            }
          },
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

The response correlates the canonical identifier and the Business-supported
alias to one Location. Tuesday's two `hours` entries form a split shift.
Sunday has no `hours` entry, meaning no regular interval begins that day. The
`exception_hours` entry omits `opens` and `closes`, making it a full closure.
See [Operating Hours](index.md#operating-hours) for schedule representation and
evaluation rules.

### Item availability refinement

=== "Request"

    <!-- ucp:example schema=common/location_lookup op=lookup direction=request -->
    ```json
    {
      "ids": ["loc_downtown", "loc_uptown"],
      "filters": {
        "items": ["item_id_phone_15_pro"]
      }
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
          "inputs": [
            {"id": "loc_downtown"}
          ],
          "name": "Downtown Store"
        }
      ]
    }
    ```

Both identifiers resolve, but the Business cannot currently provide the
referenced item at `loc_uptown`, so that Location and its `inputs` entry are
omitted. The request still succeeds, and this ordinary refinement non-match
requires no message (see
[Item Availability Filter](search.md#item-availability-filter)).

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
          "inputs": [
            {"id": "loc_downtown"}
          ],
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
informational `not_found` message to identify an unresolved identifier.

### Batch limit applied

The following Business accepts at most two distinct identifiers per Lookup
request.

=== "Request"

    <!-- ucp:example schema=common/location_lookup op=lookup direction=request -->
    ```json
    {
      "ids": ["loc_downtown", "loc_uptown", "loc_airport"]
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
          "inputs": [{"id": "loc_downtown"}],
          "name": "Downtown Store"
        },
        {
          "id": "loc_uptown",
          "inputs": [{"id": "loc_uptown"}],
          "name": "Uptown Store"
        }
      ],
      "messages": [
        {
          "type": "info",
          "code": "batch_limit_applied",
          "content": "Processed the first 2 of 3 distinct identifiers; 1 identifier was not processed."
        }
      ]
    }
    ```

The Business evaluates `loc_downtown` and `loc_uptown` in request order.
`loc_airport` was not evaluated and is not unresolved; the Platform can submit
it in a subsequent request.

## Transport Bindings

* [REST Binding](rest.md#post-locationslookup): `POST /locations/lookup`
* [MCP Binding](mcp.md#lookup_locations): `lookup_locations` tool
