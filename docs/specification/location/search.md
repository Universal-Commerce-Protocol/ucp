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

# Location Search Capability

* **Capability Name:** `dev.ucp.common.location.search`

Performs a search for physical locations (e.g., retail stores, restaurants,
warehouses). Supports natural language queries, geographic proximity (distance)
searches, and structured filtering by operating hours and offerings such as
amenities and inventory availability.

## Operation

| Operation | Description |
| :--- | :--- |
| **Search Locations** | Search for locations using query text, context, and filters. |

### Request

{{ extension_schema_fields('location_search.json#/$defs/search_request', 'location') }}

### Response

{{ extension_schema_fields('location_search.json#/$defs/search_response', 'location') }}

## Search Inputs

A valid search request **MUST** include at least one of: a `query` string, one or more
`filters`, platform-provided user `context` hints, or an extension-defined input.
When `query` is omitted, the request represents a browse operation — the business
returns locations matching the provided filters without text-relevance ranking.

Implementations **MUST** validate that incoming requests contain at least one
recognized input and **SHOULD** reject empty or invalid requests with an
appropriate error. Implementations define and enforce their own rules for
input presence and content — for example, requiring `query`, rejecting
empty `query` strings, or accepting filter-only requests.

> **Implementation guidance:** For processing search requests containing only `context`,
> the following rules **MAY** be followed by businesses:
>
> If the provided `context` is insufficient to determine a location boundary
> (e.g., only country is provided, or context is empty), business **MAY** return a default
> set of locations (e.g., featured locations, or all locations up to a default server-side
> limit) or an empty list.
>
> If the server cannot resolve the location, it **SHOULD** return an error message.

## Search Filters

Location filters allow narrowing results based on specific criteria.
Standard filters are defined as below; businesses **MAY** support additional
custom filters via `additionalProperties`.

{{ schema_fields('types/location_filter', 'location') }}

### Hours-Based Filter

The standard `filters.hours` object requires `open_at`, an exact RFC 3339
instant expressed with `Z` or a numeric offset, and can include
extension-defined fields. Before sending a Buyer-local wall time, a Platform
**MUST** resolve it to an exact instant for `open_at`. When asking which
Locations are open now, a Platform **MUST** supply the current instant. No
timezone field is needed in the standard `context` object because `open_at`
already identifies the instant.

The `Z` or numeric offset identifies only that instant. Platforms and
Businesses **MUST NOT** treat the offset as the Internet Assigned Numbers
Authority (IANA) Time Zone Database identifier of a Platform, Business, Buyer,
or Location. For each candidate Location, a Business **MUST** use that
Location's authoritative `timezone` to convert `open_at` to the local date,
day of week, and time, then evaluate the effective schedule under
[Operating Hours](index.md#operating-hours). A Business **MUST** treat absent,
invalid, or otherwise unusable schedule data as not matching the supplied
instant.

### Offerings-Based Filter

Separates static location characteristics from dynamic availability:

* **`amenities`** (Array of Strings): Static features or services of the
    location. All specified amenities **MUST** be supported by the location (AND semantic).
    See [Amenity Vocabulary](#amenity-vocabulary) for well-known values.
* **`inventory`** (Array of Objects): Real-time availability of items/goods at
    the location. Some industry specific use cases include:
    * *Shopping*: Checking stock availability for specific products or variants.
    * *Food Ordering*: Checking offering availability of specific dishes or menu items.
    Each inventory filter requires an `id` (e.g., product/dish ID) and can optionally specify
    a coarse `availability_status` value.

#### Amenity Vocabulary

UCP defines an open string vocabulary for amenities via `amenity_type.json` to ensure cross-business
interoperability. Implementations **SHOULD** map their internal features to the well-known types where applicable.

### Geographic & Geofencing Filter

Supports two distinct, industry-agnostic spatial search models:

* **`distance` (Proximity Search)**: Filters for locations within a `max_distance`
    (in RFC 7035 distance units = meters) of a `center` point.

> **Privacy Integration**: If `center` is omitted, business **MUST** use the
> user's address hint provided in the request `context` (which may be coarse/sanitized)
> to derive the center. If `context` is omitted or business is unable to resolve the
> provided address hint, then business **MUST** return an error message with
> `code: "location_geo_filter_resolution_failed"`.

* **`serves` (Service Area Coverage)**: Filters for locations that can serve
    a target destination. The business evaluates coverage using their internal service area rules
    (e.g., internal geometry, ZIP code lists) and returns qualifying locations only.

> **Contextual Fallback**: If the `serves` filter is not explicitly specified in
> the request, the business **MAY** use the user's contextual location hints passed in the
> request `context` object to implicitly apply a `serves` filter, returning only locations
> that can service the user. Similarly to the callout above, if `context` is omitted or
> business is unable to resolve the provided address hint, then business **MUST** return
> an error message with `code: "location_geo_filter_resolution_failed"`.

## Pagination

Cursor-based pagination for list operations. Cursors are opaque strings
that implementations **MAY** encode as stateless keyset tokens.

### Page Size

The `limit` parameter is a requested page size, not a guaranteed count.
Implementations **SHOULD** accept a page size of at least 10. When the
requested limit exceeds the implementation's maximum, implementations
**MAY** clamp to their maximum silently — returning fewer results without
error. Clients MUST NOT assume the response size equals the requested limit.

### Pagination Request

{{ extension_schema_fields('types/pagination.json#/$defs/request', 'location') }}

### Pagination Response

{{ extension_schema_fields('types/pagination.json#/$defs/response', 'location') }}

## Examples {: #examples }

The following requests and responses are transport-neutral UCP payloads.

### Grocery stores serving a point and open at an instant

=== "Request"

    <!-- ucp:example schema=common/location_search op=search direction=request -->
    ```json
    {
      "query": "grocery store near me",
      "context": {
        "address_country": "US",
        "address_region": "CA",
        "postal_code": "94043"
      },
      "filters": {
        "hours": {
          "open_at": "2026-05-18T17:00:00Z"
        },
        "amenities": ["curbside_pickup"],
        "geo": {
          "serves": {
            "point": {
              "latitude": 37.422,
              "longitude": -122.084
            }
          }
        }
      }
    }
    ```

=== "Response"

    <!-- ucp:example schema=common/location_search op=search direction=response -->
    ```json
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
            "longitude": -122.080
          },
          "amenities": ["curbside_pickup", "in_store_pickup", "parking"],
          "timezone": "America/Los_Angeles",
          "hours": [
            {"day": "monday", "opens": "08:00", "closes": "21:00"}
          ]
        }
      ]
    }
    ```

At the supplied instant, it is Monday at `10:00` in
`America/Los_Angeles`, within the returned interval. See
[Operating Hours](index.md#operating-hours) for complete schedule evaluation
rules.

### Locations with an inventory item within a distance

=== "Request"

    <!-- ucp:example schema=common/location_search op=search direction=request -->
    ```json
    {
      "filters": {
        "inventory": [
          {
            "id": "item_id_phone_15_pro",
            "availability_status": "in_stock"
          }
        ],
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
            "longitude": -74.008
          },
          "amenities": ["curbside_pickup", "in_store_pickup"]
        }
      ]
    }
    ```

## Transport Bindings

* [REST Binding](rest.md#post-locationssearch): `POST /locations/search`
* [MCP Binding](mcp.md#search_locations): `search_locations` tool
