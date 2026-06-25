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

A valid search request **MUST** include at least one of: a `query` string
or one or more `filters`. When `query` is omitted, the request represents
a browse operation — the business returns locations matching the provided
filters without text-relevance ranking.

Implementations **MUST** validate that incoming requests contain at least one
recognized input and **SHOULD** reject empty or invalid requests with an
appropriate error. Implementations define and enforce their own rules for
input presence and content — for example, requiring `query`, rejecting
empty `query` strings, or accepting filter-only requests.

## Search Filters

Location filters allow narrowing results based on specific criteria.
Standard filters are defined as below; businesses **MAY** support additional
custom filters via `additionalProperties`.

{{ schema_fields('types/location_filter', 'location') }}

### Hours-Based Filter

Filters locations based on their operating hours:

* `open_now`: A quick boolean filter to find locations currently open.
* `open_at`: An RFC 3339 date-time string to find locations open at a
    specific future time (e.g., planning a visit or ordering ahead).
    The business resolves this against the location's local time and timezone.

### Offerings-Based Filter

Separates static location characteristics from dynamic availability:

* **`amenities`** (Array of Strings): Static features or services of the
    location (e.g., `free_wifi`, `parking`, `outdoor_seating`, `curbside_pickup`, `vegetarian`).
    All specified amenities **MUST** be supported by the location (AND semantic).
* **`inventory`** (Array of Objects): Real-time availability of items/goods at
    the location. Some industry specific use cases include:
    * *Shopping*: Checking stock levels for specific products or variants.
    * *Food Ordering*: Checking availability of specific dishes or menu items.
    Each inventory filter requires an `id` (product/dish ID) and can optionally specify
    a `type` to help multi-industry business with backend routing and a
    minimum `quantity`.

### Geographic & Geofencing Filter

Supports two distinct, industry-agnostic spatial search models:

* **`distance` (Proximity Search)**: Filters for locations within a `max_distance`
    (in RFC 7035 distance units = meters) of a `center` point.

> **Privacy Integration**: If `center` is omitted, the server **MUST** use the
> user's address hint provided in the request `context` (which may be coarse/sanitized)
> to derive the center.

* **`geofence_point` (Service Area Coverage)**: Filters for locations whose circular
    service area (defined by `geofence_radius`) contains the specified point.

## Pagination

Cursor-based pagination for list operations. Cursors are opaque strings
that implementations MAY encode as stateless keyset tokens.

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

## Transport Bindings

* [REST Binding](rest.md#search): `POST /location/search`
* [MCP Binding](mcp.md#search_location): `search_location` tool
