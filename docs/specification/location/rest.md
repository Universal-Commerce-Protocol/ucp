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

## Endpoints

| Endpoint | Method | Capability | Description |
| :--- | :--- | :--- | :--- |
| `/locations/search` | POST | [Search](search.md) | Search for physical locations. |
| `/locations/lookup` | POST | [Lookup](lookup.md) | Lookup single or multiple location(s) by known ID. |

### `POST /locations/search`

Maps to the [Location Search](search.md) capability.

{{ method_fields('search_locations', 'rest.openapi.json', 'location/rest') }}

#### Example: Search for Grocery Stores with Local Delivery Coverage (Geofencing)

=== "Request"

    <!-- ucp:example schema=common/location_search op=search direction=request -->
    ```json
    POST /locations/search HTTP/1.1
    Host: business.example.com
    Content-Type: application/json
    Request-Id: 8ef9b0c2-78d1-4e4b-91c2-3e2ef0d3ab9f
    UCP-Agent: profile="https://platform.example/profiles/v2026-01/agent.json"

    {
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
    ```

#### Example: Search for Electronics Stores with iPhone in stock (Store Finder)

=== "Request"

    <!-- ucp:example schema=common/location_search op=search direction=request -->
    ```json
    POST /locations/search HTTP/1.1
    Host: business.example.com
    Content-Type: application/json
    Request-Id: 9ef9b0c2-78d1-4e4b-91c2-3e2ef0d3ab9f
    UCP-Agent: profile="https://platform.example/profiles/v2026-01/agent.json"

    {
      "context": {
        "address_country": "US"
      },
      "filters": {
        "hours": {
          "open_now": true
        },
        "offerings": {
          "inventory": [
            {
              "id": "item_id_iphone_15_pro",
              "type": "product",
              "quantity": 1
            }
          ]
        },
        "geo": {
          "distance": {
            "center": {
              "latitude": 40.707,
              "longitude": -74.011
            },
            "max_distance": 10000
          }
        }
      }
    }
    ```

=== "Response"

    <!-- ucp:example schema=common/location_search op=search direction=response -->
    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

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
          "id": "loc_downtown_electronics",
          "name": "Downtown Electronics",
          "address": {
            "street_address": "100 Broadway",
            "address_locality": "New York",
            "address_region": "NY",
            "address_country": "US",
            "postal_code": "10005"
          },
          "geo": {
            "latitude": 40.709,
            "longitude": -74.008,
            "geofence_radius": 2000
          },
          "timezone": "America/New_York"
        }
      ]
    }
    ```

### `POST /locations/lookup`

Maps to the [Location Lookup](lookup.md) capability.

{{ method_fields('lookup_locations', 'rest.openapi.json', 'location/rest') }}

#### Example: Simple Lookup

=== "Request"

    <!-- ucp:example schema=common/location_lookup op=lookup direction=request -->
    ```json
    POST /locations/lookup HTTP/1.1
    Host: business.example.com
    Content-Type: application/json
    Request-Id: 2c9b0c2a-18d1-4e4b-91c2-3e2ef0d3ab9f
    UCP-Agent: profile="https://platform.example/profiles/v2026-01/agent.json"

    {
      "ids": ["loc_downtown", "loc_uptown"]
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
          "timezone": "America/New_York",
          "hours": [
            {
              "day": "monday",
              "intervals": [{"open": "09:00", "close": "21:00"}]
            },
            {
              "day": "tuesday",
              "intervals": [{"open": "09:00", "close": "21:00"}]
            },
            {
              "day": "wednesday",
              "intervals": [{"open": "09:00", "close": "21:00"}]
            },
            {
              "day": "thursday",
              "intervals": [{"open": "09:00", "close": "21:00"}]
            },
            {
              "day": "friday",
              "intervals": [{"open": "09:00", "close": "22:00"}]
            },
            {
              "day": "saturday",
              "intervals": [{"open": "10:00", "close": "20:00"}]
            },
            {
              "day": "sunday",
              "is_closed": true
            }
          ],
          "exception_hours": [
            {
              "date": "2026-11-26",
              "label": "Thanksgiving",
              "is_closed": true
            }
          ]
        },
        {
          "id": "loc_uptown",
          "name": "Uptown Boutique",
          "address": {
            "street_address": "2000 Madison Ave",
            "address_locality": "New York",
            "address_region": "NY",
            "address_country": "US",
            "postal_code": "10035"
          },
          "geo": {
            "latitude": 40.790,
            "longitude": -73.950,
            "geofence_radius": 1000
          },
          "timezone": "America/New_York",
          "hours": [
            {
              "day": "monday",
              "intervals": [{"open": "09:00", "close": "21:00"}]
            },
            {
              "day": "tuesday",
              "intervals": [{"open": "09:00", "close": "21:00"}]
            },
            {
              "day": "wednesday",
              "intervals": [{"open": "09:00", "close": "21:00"}]
            },
            {
              "day": "thursday",
              "intervals": [{"open": "09:00", "close": "21:00"}]
            },
            {
              "day": "friday",
              "intervals": [{"open": "09:00", "close": "22:00"}]
            },
            {
              "day": "saturday",
              "is_closed": true
            },
            {
              "day": "sunday",
              "is_closed": true
            }
          ],
          "exception_hours": [
            {
              "date": "2026-11-26",
              "label": "Thanksgiving",
              "is_closed": true
            }
          ]
        }
      ]
    }
    ```

#### Example: Partial Success (Some Locations Not Found)

=== "Request"

    <!-- ucp:example schema=common/location_lookup op=lookup direction=request -->
    ```json
    POST /locations/lookup HTTP/1.1
    Host: business.example.com
    Content-Type: application/json
    Request-Id: 2c9b0c2a-18d1-4e4b-91c2-3e2ef0d3ab9f
    UCP-Agent: profile="https://platform.example/profiles/v2026-01/agent.json"

    {
      "ids": ["loc_downtown", "loc_invalid_id"]
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
          "timezone": "America/New_York",
          "hours": [
            {
              "day": "monday",
              "intervals": [{"open": "09:00", "close": "21:00"}]
            },
            {
              "day": "tuesday",
              "intervals": [{"open": "09:00", "close": "21:00"}]
            },
            {
              "day": "wednesday",
              "intervals": [{"open": "09:00", "close": "21:00"}]
            },
            {
              "day": "thursday",
              "intervals": [{"open": "09:00", "close": "21:00"}]
            },
            {
              "day": "friday",
              "intervals": [{"open": "09:00", "close": "22:00"}]
            },
            {
              "day": "saturday",
              "intervals": [{"open": "10:00", "close": "20:00"}]
            },
            {
              "day": "sunday",
              "is_closed": true
            }
          ],
          "exception_hours": [
            {
              "date": "2026-11-26",
              "label": "Thanksgiving",
              "is_closed": true
            }
          ]
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

### UCP Response Catalog (Envelope) {: #ucp-response-catalog-schema }

{{ extension_schema_fields('ucp.json#/$defs/response_catalog_schema', 'location/rest') }}

### Location {: #location-entity }

{{ schema_fields('types/location', 'location/rest') }}

### Location Filter {: #location-filter-schema }

{{ schema_fields('types/location_filter', 'location/rest') }}

### Location Offering Filter {: #location-offering-filter-schema }

{{ schema_fields('types/location_offering_filter', 'location/rest') }}

### Error Response {: #error-response }

{{ schema_fields('types/error_response', 'location/rest') }}

## Conformance

A conforming REST transport implementation **MUST**:

1. Implement endpoints for each location capability advertised in the business's UCP profile,
    per their respective capability requirements ([Search](search.md), [Lookup](lookup.md)).
    Each capability **MAY** be adopted independently.
2. Default to business-derived coordinates based on user location hint provided in `context.json`
    for proximity (`distance`) filters when explicit coordinates are omitted by the platform in the request.
3. Support cursor-based pagination with a default limit of 10 for search results.
4. Return HTTP 200 for lookup requests; unknown identifiers result in fewer or no locations
    returned (**MAY** include informational `not_found` messages).
5. Return HTTP 400 with `request_too_large` error for requests exceeding batch size limits.
