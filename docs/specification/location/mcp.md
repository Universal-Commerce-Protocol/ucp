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
        "spec": "https://ucp.dev/{{ ucp_version }}/specification/location/search",
        "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/location_search.json"
      }],
      "dev.ucp.common.location.lookup": [{
        "version": "{{ ucp_version }}",
        "spec": "https://ucp.dev/{{ ucp_version }}/specification/location/lookup",
        "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/location_lookup.json"
      }]
    },
    "payment_handlers": {}
  }
}
```

### Request Metadata

MCP clients **MUST** include a `meta` object in every request containing
protocol metadata:

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
        "query": "grocery store open now",
        "filters": {
          "hours": {
            "open_now": true
          }
        }
      }
    }
  }
}
```

The `meta["ucp-agent"]` field is **required** on all requests to enable
version compatibility checking and capability negotiation.

## Tools

| Tool | Capability | Description |
| :--- | :--- | :--- |
| `search_locations` | [Search](search.md) | Search for locations using text, coordinates, and filters. |
| `lookup_locations` | [Lookup](lookup.md) | Batch lookup one or multiple location(s) by ID. |

### `search_locations`

Maps to the [Location Search](search.md) capability.

#### Request Arguments

{{ extension_schema_fields('location_search.json#/$defs/search_request', 'location/mcp') }}

#### Response Schema

{{ extension_schema_fields('location_search.json#/$defs/search_response', 'location/mcp') }}

#### Example

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
            "query": "grocery store near me",
            "context": {
              "address_country": "US",
              "address_region": "CA",
              "postal_code": "94043"
            },
            "filters": {
              "hours": {
                "open_now": true
              },
              "offerings": {
                "amenities": ["curbside_pickup"]
              },
              "geo": {
                "geofence_point": {
                  "latitude": 37.422,
                  "longitude": -122.084
                }
              }
            }
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
              "name": "Valley Grocers",
              "address": {
                "street_address": "789 Maple Ave",
                "address_locality": "Mountain View",
                "address_region": "CA",
                "address_country": "US",
                "postal_code": "94043"
              },
              "geo": {
                "latitude": 37.420,
                "longitude": -122.080,
                "geofence_radius": 10000
              },
              "timezone": "America/Los_Angeles"
            }
          ]
        }
      }
    }
    ```

### `lookup_locations`

Maps to the [Location Lookup](lookup.md) capability.

#### Request Arguments

{{ extension_schema_fields('location_lookup.json#/$defs/lookup_request', 'location/mcp') }}

#### Response Schema

{{ extension_schema_fields('location_lookup.json#/$defs/lookup_response', 'location/mcp') }}

#### Example

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
            "ids": ["loc_downtown", "loc_uptown"]
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
                "longitude": -74.011,
                "geofence_radius": 2000
              },
              "timezone": "America/New_York"
            }
          ],
          "messages": [
            {
              "type": "info",
              "code": "not_found",
              "content": "Unable to find the location associated with loc_uptown"
            }
          ]
        }
      }
    }
    ```

## Error Handling

UCP uses a two-layer error model separating transport-level errors from business outcomes.

### Transport Errors

Transport-level failures (authentication, rate limiting, invalid parameters) that prevent request processing are returned as JSON-RPC `error`. See the [Core Specification](../overview.md#error-codes) for details.

### Business Outcomes

All application-level outcomes return a successful JSON-RPC result with the UCP envelope and optional `messages` array. See [Location Overview](index.md#messages-and-error-handling) for message semantics.

## Entities

### Location {: #location-entity }

{{ schema_fields('types/location', 'location/mcp') }}

### Location Filter {: #location-filter-schema }

{{ schema_fields('types/location_filter', 'location/mcp') }}

### Location Offering Filter {: #location-offering-filter-schema }

{{ schema_fields('types/location_offering_filter', 'location/mcp') }}

### Error Response {: #error-response }

{{ schema_fields('types/error_response', 'location/mcp') }}

## Conformance

A conforming MCP transport implementation **MUST**:

1. Implement JSON-RPC 2.0 protocol correctly.
2. Implement tools for each location capability advertised in the business's UCP profile, per their respective
    capability requirements ([Search](search.md), [Lookup](lookup.md)).
    Each capability may be adopted independently.
3. Default to business-derived coordinates based on user location hint provided in `context.json`
    for proximity (`distance`) filters when explicit coordinates are omitted by the platform in the request.
4. Return a successful JSON-RPC result for lookup requests; unknown identifiers result in fewer or no locations
    returned (**MAY** include informational `not_found` messages in the `messages` array).
5. Validate tool inputs against UCP schemas.
6. Return `-32602` (Invalid params) for requests exceeding batch size limits.
