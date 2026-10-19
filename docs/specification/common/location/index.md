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

The Location capability allows Platforms to discover, search, and retrieve
physical Locations (such as retail stores, restaurants, and brand lockers) from
Businesses.

This is vertical-agnostic and enables key commerce flows such as:

* **Local Pickup Discovery**: Finding nearby Locations such as retail stores or
    restaurant branches that support Buyer pickup, checking their operating
    hours, and discovering where selected items are currently available before
    selection.
* **Fulfillment Area Verification**: Checking if a specific location (e.g., utility depot, restaurant,
    or local service provider) can serve a Buyer's address (the `serves` relation).

## Capabilities

| Capability | Description |
| :--- | :--- |
| [`dev.ucp.common.location.search`](search.md) | Search for Locations using free-text queries, explicit spatial relations (`distance`, `serves`), and filters (`hours`, `amenities`, and `items`). |
| [`dev.ucp.common.location.lookup`](lookup.md) | Retrieve full details for one or more Locations by identifier, optionally refined by the same relations and filters. |

## Key Concepts

* **Location**: A physical entity that can be found on a map. Defined by a display name,
    address, operating hours, and **geographic context** (geographic coordinates).
* **Amenities**: Static features, services, or capabilities of the Location.
    Responses use a map with reverse-DNS amenity identifiers as keys, combining
    collision-resistant names, one entry per identifier, and buyer-facing
    descriptions that keep custom amenities renderable. See
    [Amenity Vocabulary](search.md#amenity-vocabulary).
* **Item Availability**: The `items` filter asks whether the Business can
    currently provide every referenced item at a candidate Location. Returning
    the Location is a coarse, provisional assertion, not item-level detail or a
    reservation. See [Item Availability Filter](search.md#item-availability-filter).
* **Proximity & Serviceability**: Two distinct, explicit spatial relations:
    * **`distance`**: Compares a Location's coordinates against a Platform-supplied center point and inclusive radius.
    * **`serves`**: Asks whether the Location can provisionally serve one explicit
      Platform-supplied target; the Business is authoritative for that answer, and UCP does not
      model or expose the underlying coverage geometry — a Location does not implicitly carry a
      geometric boundary around its coordinates. See [Spatial Relations](search.md#spatial-relations).
* **Operating Hours**: Regular weekly schedules (`hours`) and date-specific
    exceptions (`exception_hours`), interpreted in the Location's `timezone`.
    See [Operating Hours](#operating-hours).

### Relationship to Other Capabilities

The Location capability provides the foundation for localized commerce by
integrating tightly with other capabilities (like Catalog, Cart, and Checkout
in Shopping):

1. **Stable Identifiers**: Location Search and Lookup return stable,
    Business-scoped `Location.id` values representing physical entities. A
    Location ID selects only the physical entity; it does not determine the
    interaction mode, guarantee availability, or bind operational terms.
    Downstream capabilities authoritatively negotiate and revalidate all terms
    during transaction processing (for example, a returned ID submitted as
    `selected_destination_id`; see
    [Selection and Location Identity](../../shopping/extensions/fulfillment.md#selection-and-location-identity)).
2. **Separation of Discovery Concerns**: Each capability answers one narrow
    question, and later stages revalidate earlier signals. Location answers
    which places can currently provide a set of referenced items (the
    [`items` filter](search.md#item-availability-filter)).
3. **Provisional vs. Authoritative Boundaries**:
    * *Discovery Phase (Provisional)*: Location responses based on operating
        hours, current item availability, and amenities represent the
        Business's *current terms* at the time of query. They are **provisional
        signals** and are not binding commitments.
    * *Checkout Phase (Authoritative)*: Final transaction terms that depend on a location (e.g., pickup)
        **MUST** be negotiated and finalized authoritatively. Discovery signals **SHOULD NOT** be cached
        or reused across sessions without re-validation.

## Operating Hours

### Representation

The hours filter's [`open_at`](search.md#hours-based-filter) value is an exact
instant. Operating hours use the Location's local date and clock time,
interpreted using its IANA timezone.

* `hours` is a list of regular weekly intervals. Each item contains `day`,
    `opens`, and `closes`. `day` is a stable UCP day-of-week identifier for the
    day on which the interval begins, not localized display text. A Platform
    **MAY** localize it for presentation. Times use 24-hour `HH:MM` form.
* `exception_hours` is a list of date-specific timed intervals or full
    closures. Each item contains inclusive local-date bounds `valid_from` and
    `valid_through` in `YYYY-MM-DD` form; equal bounds select one date. Both
    `opens` and `closes` define a timed interval, while omitting both defines a
    full closure. The optional `title` is a short, human-readable heading. It is
    presentation metadata and does not affect schedule evaluation.
* `timezone` identifies the Business-owned canonical local civil-time frame for
    both schedules.

### Evaluation

Timed intervals are open at `opens` and closed at `closes`. For example,
`10:00`–`17:00` is open immediately before `17:00` and closed at `17:00`. If
`closes` is earlier than `opens`, the interval continues into the next local
date. As a reserved exception to this closing-boundary rule, the exact
`00:00`–`23:59` pair represents the entire local civil date, including daylight
saving time transitions. Every pair with equal `opens` and `closes` is invalid,
including `00:00`–`00:00`.

Schedule evaluation is deterministic for each instant: convert the instant to
the Location's local date, day of week, and time using `timezone`, then apply the
effective schedule to those local values. During a forward daylight saving time
(DST) transition, local clock labels in the gap correspond to no instants and
are not shifted. During a backward DST transition, both instants in the fold
that map to the same repeated local time receive the same schedule result. The
current schedule shape cannot distinguish the two fold occurrences.

Multiple `hours` items for the same `day` combine as split shifts. An omitted
day means no regular interval begins that day, but an interval from the
preceding day can carry into it. Absent `hours` means the regular schedule is
unknown, not closed. To represent a temporary full closure, a Business retains
its regular `hours` and adds an `exception_hours` entry for the affected dates
without `opens` or `closes`.

An exception schedule replaces the regular schedule on every covered local
date. If an interval carries into a local date governed by an exception, that
exception takes authority at local midnight. Intersecting non-identical
exception ranges are invalid, including when one contains another. Timed
entries with identical bounds can coexist as split shifts, but a full closure
stands alone for its bounds. Array order establishes no precedence.

#### Exception hours example

<!-- ucp:example schema=common/types/location op=read direction=response -->
```json
{
  "id": "loc_downtown",
  "name": "Downtown Store",
  "timezone": "America/New_York",
  "exception_hours": [
    {
      "title": "Holiday hours",
      "valid_from": "2026-12-24",
      "valid_through": "2026-12-26",
      "opens": "10:00",
      "closes": "14:00"
    },
    {
      "title": "Holiday hours",
      "valid_from": "2026-12-24",
      "valid_through": "2026-12-26",
      "opens": "16:00",
      "closes": "18:00"
    }
  ]
}
```

The two entries share date bounds, so they define split shifts that apply
independently on each date in the inclusive range. A full closure instead uses
one item that omits both `opens` and `closes`.

### Guidelines

#### Business

A Business owns each Location's canonical schedule frame. When a Business
emits `hours` or `exception_hours`, it **MUST** express every `day`, `opens`,
`closes`, `valid_from`, and `valid_through` value in that frame and **MUST**
include `timezone` as a valid
[Internet Assigned Numbers Authority (IANA) Time Zone Database](https://www.iana.org/time-zones)
identifier. A Business **MUST NOT** vary the canonical schedule frame according
to the requesting Platform's or Buyer's timezone. Because JSON Schema does not
enforce every semantic constraint, a Business **MUST** emit only schedules that
follow the rules above, including unequal `opens` and `closes`, a `valid_from`
value no later than `valid_through`, and valid exception-range intersections.
A Business **SHOULD** omit an `exception_hours` entry once it can no longer
affect the schedule at any current or future instant. It **SHOULD** publish
known future exceptions through the planning horizon for which its schedule is
authoritative.

#### Platform

When evaluating a returned schedule, a Platform **MUST** use the returned
Location's `timezone`. A Platform **MAY** convert concrete dated occurrences to
another timezone for presentation, but it **MUST NOT** reinterpret the canonical
schedule values in another timezone. A Platform **MUST NOT** infer that a
Location with absent, invalid, or otherwise unusable schedule data is open. A
Platform **MAY** present `title` according to its presentation policy and
**MUST NOT** use it to determine whether a Location is open or closed.

## Shared Entities

### Amenity {: #amenity }

Location responses represent amenities as a map keyed by amenity identifier.
The Business **MUST** provide a nonempty, plain-text, buyer-facing
`description` for every entry. The Business **SHOULD** make it a short,
self-contained label or phrase suitable for direct use in a compact list and
**SHOULD** localize it for the request when possible. It does not participate
in amenity identity or filtering. An entry without that description is
schema-invalid; a Platform **MUST** reject the invalid response rather than
infer presentation text from the key.

Amenity presentation is identifier-agnostic: the Business-provided
`description` alone is sufficient to present any amenity. A Platform governs
its own presentation policy and **MAY** decide whether and where amenities
appear (for example, omitting them on a compact summary card). When it
presents amenities, it **SHOULD** use the provided `description` for every
entry it presents and **MUST NOT** suppress an entry solely because its
identifier is unrecognized. A Platform **MAY** enhance recognized amenities
with icons, grouping, or other structured presentation, but **MUST NOT** infer
semantics from an unrecognized identifier or treat it as equivalent to another
amenity.

{{ extension_schema_fields('types/location.json#/$defs/amenity', 'common/location') }}

### Context

Buyer location and market context for the operations. All fields are optional
hints for relevance and localization. Platforms **MAY** geo-detect context from
request headers.

Context signals are provisional—not authoritative data. A Business **MAY** use
them to influence ranking, localization, or selection of a bounded default
browse page, and **MAY** ignore or down-rank them if inconsistent with
higher-confidence signals (authenticated account, risk detection). A Business
**MUST NOT** substitute them for explicit `distance` or `serves` operands or
for `filters.items` item identifiers; they prove neither proximity,
serviceability, nor item availability (see
[Request Grammar](search.md#request-grammar)).

{{ schema_fields('types/context', 'common/location') }}

### Signals

Environment data provided by the Platform to support authorization and abuse
prevention. Signal values **MUST NOT** be buyer-asserted claims. See
[Signals](../../overview/index.md#signals) for details and privacy requirements.

{{ schema_fields('types/signals', 'common/location') }}

## Messages and Error Handling

All Location responses include an optional `messages` array that allows
Businesses to provide context about errors, warnings, or informational notices.

### Message Types

Messages communicate business outcomes and provide context:

| Type | When to Use | Example Codes |
| :--- | :--- | :--- |
| `error` | Business-level errors | Business-defined codes (freeform codes permitted) |
| `warning` | Important conditions affecting purchase | `permanently_closed`, `temporary_closure` |
| `info` | Diagnostics or additional context that do not fail the operation | `not_found`, `holiday_hours_active` |

#### Message (Error)

{{ schema_fields('types/message_error', 'common/location') }}

#### Message (Warning)

{{ schema_fields('types/message_warning', 'common/location') }}

#### Message (Info)

{{ schema_fields('types/message_info', 'common/location') }}

### Common Scenarios

#### Empty Search

When a valid Search finds no matches, the Business **MUST** return an empty
`locations` array. No message is required for an ordinary non-match, including
when a `filters.items` identifier is unknown, is unavailable, or cannot be
evaluated.

<!-- ucp:example schema=common/location_search op=search -->
```json
{
  "ucp": {...},
  "locations": []
}
```

An ordinary empty result is not an error: the query was valid but returned no
matching Locations.

## Transport Bindings

The capabilities above are bound to specific transport protocols:

* [REST Binding](rest.md): RESTful API mapping.
* [MCP Binding](mcp.md): Model Context Protocol mapping via JSON-RPC.

## Security & Privacy Considerations

1. **Coarse-by-default**: Platforms **SHOULD** default to sending coarse location hints (e.g., postal code or rounded coordinates) during the discovery phase.
  Precise locations/coordinates **SHOULD** only be shared when the Buyer explicitly consents or selects a specific Location.
2. **Availability Probing Mitigation**: Businesses **SHOULD** rate-limit
  requests carrying `filters.items` to reduce item-availability probing
  and aggressive enumeration of the directory.
3. **Private/Dark Locations**: Businesses **MUST** filter out internal-only or non-Buyer-accessible locations (e.g., dark kitchens, fulfillment-only hubs)
  from search results.
4. **Physical Address Spoofing (Integrity)**: While location discovery is read-only, tampering with physical addresses in responses (e.g., through MITM attacks)
  poses a physical safety/fraud risk. Platforms **SHOULD** verify signatures on location payloads before rendering them to Buyers.
5. **Data Retention & Logging Sanitization**: Businesses **MUST NOT** persist precise location inputs beyond the lifecycle of the request, unless explicit Buyer
  consent is collected. Server logs should sanitize coordinate inputs by truncating decimal places (e.g., to 2 decimal places, ~1km accuracy) to prevent
  accidental storage of precise Buyer history.
