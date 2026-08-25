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

# Location - REST Binding

This document specifies the HTTP/REST binding for the [Location Capability](index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise REST transport availability for the Common service and
Location capabilities through their UCP profile at `/.well-known/ucp`.

<!-- ucp:example schema=profile def=business_schema -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": {
      "dev.ucp.common": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/overview",
          "transport": "rest",
          "schema": "https://ucp.dev/{{ ucp_version }}/services/common/rest.openapi.json",
          "endpoint": "https://business.example.com/ucp"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.common.location.search": [{
        "version": "{{ ucp_version }}",
        "spec": "https://ucp.dev/{{ ucp_version }}/specification/common/location/search",
        "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/location_search.json"
      }],
      "dev.ucp.common.location.lookup": [{
        "version": "{{ ucp_version }}",
        "spec": "https://ucp.dev/{{ ucp_version }}/specification/common/location/lookup",
        "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/location_lookup.json"
      }]
    },
    "payment_handlers": {}
  }
}
```

## Endpoints

| Endpoint | Method | Capability | Description |
| :--- | :--- | :--- | :--- |
| `/locations/search` | POST | [Search](search.md) | Search for physical locations. |
| `/locations/lookup` | POST | [Lookup](lookup.md) | Lookup Locations by identifier, optionally refined by explicit spatial relations and filters. |

### `POST /locations/search`

Maps to the [Location Search](search.md) capability. See the
[complete transport-neutral Search example](search.md#examples).

{{ method_fields('search_locations', 'common/rest.openapi.json', 'common/location/rest') }}

#### Binding envelope example

=== "Request"

    <!-- ucp:example schema=common/location_search op=search direction=request -->
    ```json
    POST /locations/search HTTP/1.1
    Host: business.example.com
    Content-Type: application/json
    Request-Id: 8ef9b0c2-78d1-4e4b-91c2-3e2ef0d3ab9f
    UCP-Agent: profile="https://platform.example/profiles/v2026-01/agent.json"

    {
      "query": "grocery store"
    }
    ```

=== "Response"

    <!-- ucp:example schema=common/location_search op=search direction=response -->
    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json
    Content-Digest: sha-256=:yG9a8bC7...:

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.common.location.search": [
            {"version": "{{ ucp_version }}"}
          ]
        }
      },
      "locations": [
        {
          "id": "loc_valley_grocers",
          "name": "Valley Grocers"
        }
      ]
    }
    ```

### `POST /locations/lookup`

Maps to the [Location Lookup](lookup.md) capability. See the
[complete transport-neutral Lookup example](lookup.md#examples).

{{ method_fields('lookup_locations', 'common/rest.openapi.json', 'common/location/rest') }}

#### Binding envelope example

=== "Request"

    <!-- ucp:example schema=common/location_lookup op=lookup direction=request -->
    ```json
    POST /locations/lookup HTTP/1.1
    Host: business.example.com
    Content-Type: application/json
    Request-Id: 2c9b0c2a-18d1-4e4b-91c2-3e2ef0d3ab9f
    UCP-Agent: profile="https://platform.example/profiles/v2026-01/agent.json"

    {
      "ids": ["loc_downtown"]
    }
    ```

=== "Response"

    <!-- ucp:example schema=common/location_lookup op=lookup direction=response -->
    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

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

## Error Handling

UCP uses a two-layer error model separating transport-level errors from business outcomes.

### Transport Errors

Use HTTP status codes for protocol-level issues that prevent request processing:

| Status | Meaning |
| :--- | :--- |
| 400 | Bad Request - Malformed JSON or missing required parameters |
| 401 | Unauthorized - Missing or invalid authentication |
| 429 | Too Many Requests - Rate limited |
| 500 | Internal Server Error |

### Business Outcomes

All application-level outcomes return HTTP 200 with the UCP envelope and optional `messages` array. See [Location Overview](index.md#messages-and-error-handling) for message semantics.

## Entities

### UCP Response Location (Envelope) {: #ucp-response-location-schema }

{{ extension_schema_fields('ucp.json#/$defs/response_location_schema', 'common/location/rest') }}

### Amenity Type

{{ schema_fields('types/amenity_type', 'common/location/rest') }}

### Amenity {: #amenity }

{{ extension_schema_fields('types/location.json#/$defs/amenity', 'common/location/rest') }}

### Location {: #location-entity }

{{ schema_fields('types/location', 'common/location/rest') }}

### Lookup Location {: #lookup-location }

{{ extension_schema_fields('location_lookup.json#/$defs/lookup_location', 'common/location/rest') }}

### Location Filter {: #location-filter-schema }

{{ schema_fields('types/location_filter', 'common/location/rest') }}

### Location Distance {: #location-distance-schema }

{{ schema_fields('types/location_distance', 'common/location/rest') }}

### Location Serves {: #location-serves-schema }

{{ schema_fields('types/location_serves', 'common/location/rest') }}

### Error Response {: #error-response }

{{ schema_fields('types/error_response', 'common/location/rest') }}

## Conformance

A conforming REST transport implementation **MUST**:

1. Implement endpoints for each Location capability advertised in the Business's UCP profile,
    per their respective capability requirements ([Search](search.md), [Lookup](lookup.md)).
    Each capability **MAY** be adopted independently.
2. Evaluate the `distance` and `serves` relations and the `filters.items`
    availability predicate only against their explicit Platform-supplied
    operands. Never derive an operand from `context`, `signals`, or an IP address, and never
    apply an implicit serviceability or item-availability check when its
    input is absent.
3. Apply `distance`, `serves`, and every supplied `filters` predicate
    conjunctively (AND).
4. Support cursor-based pagination for Search according to the shared
    pagination contract (see [Pagination](search.md#pagination)).
5. Return HTTP 200 for Lookup requests; unknown identifiers result in fewer or no Locations
    returned (**MAY** include informational `not_found` messages).
6. Return HTTP 200 when a Lookup request exceeds the Business's batch maximum,
    process the first maximum number of distinct identifiers in request order,
    and include an informational `batch_limit_applied` message.
