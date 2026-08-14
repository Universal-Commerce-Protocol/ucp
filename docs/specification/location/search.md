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

The standard `filters.hours` object requires `open_at`, an RFC 3339 instant
expressed with `Z` or a numeric offset.

A Platform selects `open_at` to represent the time relevant to the Buyer's
intent. It can use its current time or choose another time, such as an expected
arrival, pickup, or order-acceptance time. A Platform **MAY** round or adjust
its selected time to the granularity appropriate to the interaction, but the
value it sends identifies one specific instant.

For each candidate Location, a Business **MUST** evaluate `open_at` exactly as
supplied. It converts the instant to the local date, day of week, and time using
the Location's authoritative `timezone`, then evaluates the effective schedule
under [Operating Hours](index.md#operating-hours). The `Z` or numeric offset in
`open_at` identifies the instant; it does not identify the Location's timezone.

A Business **MUST** return a Location only when it can establish that the
Location is open at `open_at`. If its schedule data is absent, invalid, outside
the range for which it can evaluate authoritatively, or otherwise unusable, the
Location does not match the filter. A Business **MUST NOT** round, shift, or
otherwise reinterpret the supplied instant.

### Offerings-Based Filter

Separates static location characteristics from dynamic availability:

* **`amenities`** (Array of Strings): Static features or services of the
    location. All specified amenities **MUST** be supported by the location (AND semantic).
    See [Amenity Vocabulary](#amenity-vocabulary) for well-known values.
* **`inventory`** (Array of Objects): Real-time availability of items/goods at
    the location. Some industry specific use cases include:
    * *Shopping*: Checking stock availability for specific products or variants.
    * *Food Ordering*: Checking offering availability of specific dishes or menu items.
    Each inventory filter requires an stable, opaque `id` (e.g., product/dish ID) and
    can optionally specify a coarse `availability_status` value.

#### Amenity Vocabulary

UCP defines an open reverse-DNS vocabulary for amenities via `amenity_type.json` to ensure cross-business
interoperability. Implementations **SHOULD** map their internal features to the well-known types where applicable.

#### Inventory Filter Evaluation Rules

* **Omission Semantics**: When `availability_status` is omitted for an item `id`,
  the business **MUST** treat the predicate as requiring that the item is currently orderable/fulfillable
  at that location (equivalent to `in_stock`, or active `preorder`/`backorder` with available capacity).
* **Conjunctive Matching**: Multiple entries in `filters.inventory` combine with logical **AND**.
  A location matches only if all item predicates are simultaneously satisfied.
* **Contradictory / Impossible Predicates**: If contradictory predicates are supplied
  for the same item `id` (e.g., requesting both `in_stock` and `backorder` availability status), the
  business **MUST** evaluate the conjunction strictly, returning an empty result set rather than throwing an error.
  Business **MAY** include an info message with `code: "contradictory_filters"` to indicate the reason behind the
  empty result.
* **Nonexistent Item IDs**: If an item `id` does not exist in the business's domain, that item's
  availability predicate is always evaluated as `false`. Business **MUST** return an empty result set and **MAY** append
  an info message with `code: "item_not_found"`.

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
> that can service the user. If `context` is omitted or business is unable to resolve the
> provided address hint, unlike the treatment above for `distance`, business **SHOULD**
> interpret this unqualified filter predicate as "serves any location target".

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
        "amenities": ["dev.ucp.amenity.shopping.curbside_pickup"],
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
          "amenities": ["dev.ucp.amenity.shopping.curbside_pickup", "dev.ucp.amenity.shopping.in_store_pickup", "dev.ucp.amenity.parking"],
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
          "amenities": ["dev.ucp.amenity.shopping.curbside_pickup", "dev.ucp.amenity.shopping.in_store_pickup"]
        }
      ]
    }
    ```

## Transport Bindings

* [REST Binding](rest.md#post-locationssearch): `POST /locations/search`
* [MCP Binding](mcp.md#search_locations): `search_locations` tool
