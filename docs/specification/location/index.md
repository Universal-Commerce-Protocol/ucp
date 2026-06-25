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

# Location Capability

The Location capability allows platforms to discover, search, and retrieve physical locations
(such as retail stores, restaurants, brand lockers) from businesses.

This is vertical-agnostic and enables key commerce flows such as:

* **Local Pickup Discovery**: Finding locations like retail stores or restaurant branches
    nearby that support customer pickup and checking their operating hours & inventory availability
    before selection.
* **Fulfillment Area Verification**: Checking if a specific location (e.g., utility depot, restaurant,
    or local service provider) has delivery coverage for a buyer's address.

## Capabilities

| Capability | Description |
| :--- | :--- |
| [`dev.ucp.common.location.search`](search.md) | Search for locations using natural language queries and filters (hours, offerings, geofencing). |
| [`dev.ucp.common.location.lookup`](lookup.md) | Retrieve full details for one or more locations by identifier. |

## Key Concepts

* **Location**: A physical entity that can be found on a map. Defined by a display name,
    address, operating hours, and **geographic context** (geographic coordinates and an
    optional circular **geofence service radius** for delivery/service area checks).
* **Offerings**: Features, capabilities, and inventory provided by the location.
    This is split into two distinct concepts to ensure tooling compatibility and semantic clarity:
    * **Amenities**: Static features, services, or capabilities of the location
        (e.g., `free_wifi`, `parking`, `outdoor_seating`, `curbside_pickup`).
    * **Inventory**: Dynamic availability of goods (e.g., retail products or restaurant dishes).
* **Geofencing**: Locations can define a `geofence_radius` around their coordinates.
    This is used to determine if a location can serve a specific user (e.g., delivery area check).
    Clients can perform proximity searches (`distance` filter) or coverage checks (`geofence` filter) using the filter.
* **Operating Hours**: Weekly schedules (`hours`) and date-specific overrides
    (`exception_hours` - e.g., holidays, temporary closures) associated with a timezone.

### Relationship to Other Capabilities

The Location capability provides the foundation for localized commerce by integrating tightly
other capabilities (like Catalog, Cart, and Checkout in Shopping):

1. **Stable Identifiers**: Location search/lookup operations return stable,
    business-scoped `location.id` values. These IDs are referenced further in other requests & responses
    (e.g., associating product variants to specific locations in Catalog filters, passed directly
    in `selected_destination_id` to indicate pickup fulfillment mode).
2. **Inventory-Based Store Finder**: Platforms can use Location Search with the `offerings.inventory` filter
    to locate nearby stores that have a specific item available, bridging the gap between online catalog
    browsing and physical store visits.
3. **Provisional vs. Authoritative Boundaries**:
    * *Discovery Phase (Provisional)*: Location responses based on operating hours, real-time inventory
        availability, and amenities offerings represent the business's *current terms* at the
        time of query. They are **provisional signals** (despite most, like hours & amenities, remain stable
        overtime) and are not binding commitments.
    * *Checkout Phase (Authoritative)*: Final transaction terms that depend on a location (e.g., pickup)
        **MUST** be negotiated and finalized authoritatively. Discovery signals **SHOULD NOT** be cached
        or reused across sessions without re-validation.

## Shared Entities

### Context

User location and market context for the operations. All fields are optional
hints for relevance and localization. Platforms **MAY** geo-detect context from
request headers.

Context signals are provisional—not authoritative data. Businesses **SHOULD** use
these values when verified inputs (e.g., coordinates as part of the request filter)
are absent, and **MAY** ignore or down-rank them if inconsistent with
higher-confidence signals (authenticated account, risk detection).

{{ schema_fields('types/context', 'location') }}

### Signals

Environment data provided by the platform to support authorization
and abuse prevention. Signal values **MUST NOT** be buyer-asserted claims. See
[Signals](../overview.md#signals) for details and privacy requirements.

{{ schema_fields('types/signals', 'location') }}

## Messages and Error Handling

All location responses include an optional `messages` array that allows businesses
to provide context about errors, warnings, or informational notices.

### Message Types

Messages communicate business outcomes and provide context:

| Type | When to Use | Example Codes |
| :--- | :--- | :--- |
| `error` | Business-level errors | `no_service_coverage` (geographic coordinates based filter) |
| `warning` | Important conditions affecting purchase | `permanently_closed`, `temporary_closure` |
| `info` | Additional context without issues | `not_found`, `holiday_hours_active` |

**Note**: Most catalog errors use `severity: "recoverable"` - agents
handle them programmatically (retry, inform user, show alternatives).

#### Message (Error)

{{ schema_fields('types/message_error', 'catalog') }}

#### Message (Warning)

{{ schema_fields('types/message_warning', 'catalog') }}

#### Message (Info)

{{ schema_fields('types/message_info', 'catalog') }}

### Common Scenarios

#### Empty Search

When search finds no matches, return an empty array without messages.

<!-- ucp:example schema=common/location_search op=search -->
```json
{
  "ucp": {...},
  "locations": []
}
```

This is not an error - the query was valid but returned no results.

## Transport Bindings

The capabilities above are bound to specific transport protocols:

* [REST Binding](rest.md): RESTful API mapping.
* [MCP Binding](mcp.md): Model Context Protocol mapping via JSON-RPC.
