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

# Location - MCP Binding

This document specifies the Model Context Protocol (MCP) binding for the [Location Capability](index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise MCP transport availability for the Common service and Location capabilities through their UCP profile at `/.well-known/ucp`.

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
          "transport": "mcp",
          "schema": "https://ucp.dev/{{ ucp_version }}/services/common/mcp.openrpc.json",
          "endpoint": "https://business.example.com/ucp/mcp"
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

### Request Metadata

A Platform using MCP **MUST** include a `meta` object with
`meta["ucp-agent"].profile` in every request. The field identifies the
Platform's UCP profile for version compatibility checks and capability
negotiation. Protocol metadata remains in `meta`, separate from the domain
request in `location`.

## Tools

| Tool | Capability | Description |
| :--- | :--- | :--- |
| `search_locations` | [Search](search.md) | Search for Locations using text, explicit spatial relations, and filters. |
| `lookup_locations` | [Lookup](lookup.md) | Batch lookup Locations by identifier, optionally refined by explicit spatial relations and filters. |

### `search_locations`

Maps to the [Location Search](search.md) capability. See the
[complete transport-neutral Search example](search.md#examples).

#### Request Arguments

{{ extension_schema_fields('location_search.json#/$defs/search_request', 'common/location/mcp') }}

#### Response Schema

{{ extension_schema_fields('location_search.json#/$defs/search_response', 'common/location/mcp') }}

#### Binding envelope example

=== "Request"

    <!-- ucp:example schema=common/location_search op=search direction=request extract=$.params.arguments.location -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "method": "tools/call",
      "params": {
        "name": "search_locations",
        "arguments": {
          "meta": {
            "ucp-agent": {
              "profile": "https://platform.example/profiles/v2026-01/agent.json"
            }
          },
          "location": {
            "query": "grocery store"
          }
        }
      }
    }
    ```

=== "Response"

    <!-- ucp:example schema=common/location_search op=search direction=response extract=$.result.structuredContent -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "result": {
        "structuredContent": {
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
      }
    }
    ```

### `lookup_locations`

Maps to the [Location Lookup](lookup.md) capability. See the
[complete transport-neutral Lookup example](lookup.md#examples).

#### Request Arguments

{{ extension_schema_fields('location_lookup.json#/$defs/lookup_request', 'common/location/mcp') }}

#### Response Schema

{{ extension_schema_fields('location_lookup.json#/$defs/lookup_response', 'common/location/mcp') }}

#### Binding envelope example

=== "Request"

    <!-- ucp:example schema=common/location_lookup op=lookup direction=request extract=$.params.arguments.location -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 2,
      "method": "tools/call",
      "params": {
        "name": "lookup_locations",
        "arguments": {
          "meta": {
            "ucp-agent": {
              "profile": "https://platform.example/profiles/v2026-01/agent.json"
            }
          },
          "location": {
            "ids": ["loc_downtown"]
          }
        }
      }
    }
    ```

=== "Response"

    <!-- ucp:example schema=common/location_lookup op=lookup direction=response extract=$.result.structuredContent -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 2,
      "result": {
        "structuredContent": {
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
      }
    }
    ```

## Error Handling

UCP uses a two-layer error model separating transport-level errors from business outcomes.

### Transport Errors

Transport-level failures (authentication, rate limiting, invalid parameters) that prevent request processing are returned as JSON-RPC `error`. See the [Core Specification](../../overview/index.md#error-codes) for details.

### Business Outcomes

All application-level outcomes return a successful JSON-RPC result with the UCP envelope and optional `messages` array. See [Location Overview](index.md#messages-and-error-handling) for message semantics.

## Entities

### Amenity Type

{{ schema_fields('types/amenity_type', 'common/location/mcp') }}

### Amenity {: #amenity }

{{ extension_schema_fields('types/location.json#/$defs/amenity', 'common/location/mcp') }}

### Lookup Location

{{ extension_schema_fields('location_lookup.json#/$defs/lookup_location', 'common/location/mcp') }}

### Location {: #location-entity }

{{ schema_fields('types/location', 'common/location/mcp') }}

### Location Filter {: #location-filter-schema }

{{ schema_fields('types/location_filter', 'common/location/mcp') }}

### Location Distance {: #location-distance-schema }

{{ schema_fields('types/location_distance', 'common/location/mcp') }}

### Location Serves {: #location-serves-schema }

{{ schema_fields('types/location_serves', 'common/location/mcp') }}

### Error Response {: #error-response }

{{ schema_fields('types/error_response', 'common/location/mcp') }}

## Conformance

A conforming MCP transport implementation **MUST**:

1. Implement JSON-RPC 2.0 protocol correctly.
2. Implement tools for each Location capability advertised in the Business's UCP profile, per their respective
    capability requirements ([Search](search.md), [Lookup](lookup.md)).
    Each capability **MAY** be adopted independently.
3. Evaluate the `distance` and `serves` relations and the `filters.items`
    availability predicate only against their explicit Platform-supplied
    operands. Never derive an operand from `context`, `signals`, or an IP address, and never
    apply an implicit serviceability or item-availability check when its
    input is absent.
4. Apply `distance`, `serves`, and every supplied `filters` predicate
    conjunctively (AND).
5. Support cursor-based pagination for Search according to the shared
    pagination contract (see [Pagination](search.md#pagination)).
6. Return a successful JSON-RPC result for Lookup requests; unknown identifiers result in fewer or no Locations
    returned (**MAY** include informational `not_found` messages in the `messages` array).
7. Return a successful JSON-RPC result when a Lookup request exceeds the
    Business's batch maximum, process the first maximum number of distinct
    identifiers in request order, and include an informational
    `batch_limit_applied` message.
8. Validate tool inputs against UCP schemas.
