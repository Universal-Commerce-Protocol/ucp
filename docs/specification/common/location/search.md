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
warehouses). Supports free-text queries, explicit `distance` and `serves`
relations, and structured filtering by operating hours, amenities, and
current item availability.

## Operation

| Operation | Description |
| :--- | :--- |
| **Search Locations** | Search for Locations using query text, explicit spatial relations, context, and filters. |

### Request

{{ extension_schema_fields('location_search.json#/$defs/search_request', 'common/location') }}

### Response

{{ extension_schema_fields('location_search.json#/$defs/search_response', 'common/location') }}

## Request Grammar

Each request input has a distinct role:

| Input | Meaning |
| :--- | :--- |
| `query` | Free-text retrieval (e.g., "restaurants near me that deliver"). |
| `distance` | A relation between a candidate Location and an explicit Platform-supplied center point and inclusive radius. |
| `serves` | A relation between a candidate Location and one explicit Platform-supplied service target. |
| `filters` | Predicates over inherent or current Location facts: `hours`, `amenities`, and `items`, plus extension-defined filters. |
| `context` / `signals` | Provisional hints for relevance, localization, and bounded default selection; never spatial proof. |
| `pagination` | A request for the shape of a bounded result page. |

`distance` and `serves` sit at the request root because they compare a
candidate Location against external facts the Platform supplies, while
`filters` predicates ask whether the Location itself has or currently
satisfies a fact. The two relations are independent: either can anchor a
request by itself, they can use different points, and neither inherits an
operand from the other.

For any candidate Location, every explicit structured constraint is
conjunctive:

```text
matches = distance (when present)
      AND serves (when present)
      AND every supplied filters.* predicate
```

This rule defines observable results, not backend evaluation order.

A Business **MAY** use the `query` text to narrow and rank results as
ordinary free-text retrieval, including letting spatial phrases in it (for
example, "near me") influence text relevance and ranking. The `query` never
carries structured authority in either direction. A Business **MUST NOT**
treat `query` text as creating a `distance` or `serves` relation or a
`filters` predicate. Only explicit constraints establish structured
matching; spatial proof comes only from the operands in
[Spatial Relations](#spatial-relations). A Business **MUST NOT** relax an
explicit structured constraint because of the `query` text: a Location
that fails `distance`, `serves`, or a `filters` predicate is excluded no
matter how well it matches the query.

### Bounded Browse

A request without a spatial relation is valid. An empty body `{}`, a request
carrying only `context` or `signals`, a request carrying only `pagination`, and
a filters-only request are each a bounded browse over the Business's default,
policy-controlled selection — never a spatial assertion and never an export.
A request carrying only `filters.items` remains non-spatial: it
constrains the candidate set through its explicit item identifiers without
asserting any spatial relation. Page size follows the shared
[Pagination](#pagination) contract.

A Business **MAY** use `context`, `signals`, and IP-derived locality to
influence ranking, localization, or selection of a bounded default browse
page. A Business using those hints **MUST NOT** treat that choice as proof
that a Location serves a target or falls within an unstated radius; only
explicit `distance` and `serves` operands establish spatial matching.

### Rejection and Empty Results

Requests that fail the Search request schema use the binding's
invalid-request mechanism. The same mechanism carries the defined semantic
errors for `distance`, `serves`, and unsupported filters; see
[Spatial Relations](#spatial-relations) and [Search Filters](#search-filters).
A well-formed relation or supported predicate that simply matches no Locations
remains a successful empty business outcome (see
[Empty Search](index.md#common-scenarios)).

## Spatial Relations

### Distance

The `distance` relation matches Locations within an inclusive radius of an
explicit center point. Both members are required: `distance.center` is a
`geo.json` point in World Geodetic System 1984 (WGS 84) decimal degrees, and
`distance.max` is the inclusive maximum distance in meters.

{{ schema_fields('types/location_distance', 'common/location') }}

The Platform **MUST** supply `distance.center` whenever it supplies
`distance`. The Business **MUST NOT** derive a missing center from `context`,
`signals`, an Internet Protocol (IP) address, or `serves`; a request missing
a required operand is invalid rather than broader than intended.

Matching semantics are closed:

* The computed distance is the shortest geodesic distance over the WGS 84
    ellipsoid between `distance.center` and the Location's authoritative
    `geo`, in meters. When the two points lie on opposite sides of the
    180-degree meridian the same rule applies — the shortest geodesic — with
    no special casing.
* The Business **MUST** compare the unrounded computed value to
    `distance.max`; a Location matches when that value is less than or equal
    to `distance.max`, and exact equality matches.
* The Business **MUST NOT** apply a tolerance band, substitute an operand,
    clamp the radius, or evaluate route, travel, or planar distance in place
    of the geodesic comparison.
* The Business **MAY** compute the value with any algorithm that produces
    the WGS 84 inverse-geodesic result at sufficient precision that the
    match outcome agrees with the unrounded comparison defined above.
* A Business that cannot honor a supplied `distance.max` (for example, a
    radius cap below the requested value) **MUST** reject the request with an
    actionable error; it **MUST NOT** silently clamp the radius or substitute
    its own. The permission to return fewer results under
    [Pagination](#pagination) never permits reducing `distance.max`.
* A Location without a usable authoritative `geo` does not match; exclusion
    is a non-match, not an error.

The relation is a hard restriction; it neither requests nor implies distance
ordering. Ranking remains separate Business behavior unless another
negotiated input specifies it.

### Serves

The `serves` relation matches Locations that can provisionally serve one
explicit target. It is a one-entry map: the Platform **MUST** supply exactly
one target representation — `point`, `address`, or a negotiated
reverse-domain extension target.

{{ schema_fields('types/location_serves', 'common/location') }}

* `point` is a WGS 84 latitude and longitude coordinate pair and uses the
    same coordinate representation as `distance.center`.
* `address` is a coarse locality. When supplying it, the Platform **MUST**
    include at least one non-empty `address_country`, `address_region`, or
    `postal_code`. An `address` is invalid if it is empty, contains only
    unrecognized fields, or all of its recognized fields are empty. A `serves`
    map is invalid if it is empty or contains more than one target.

The explicit target is authoritative. Omitting `serves` never creates an
implicit serviceability check, and the Business **MUST NOT** derive a target
from `context`, `signals`, or an IP address.

A Location matches when at least one currently available service or
fulfillment method at that Location can provisionally serve the target. The
match does not disclose the Business's coverage geometry, identify the
qualifying method, reserve capacity, or guarantee that checkout or
fulfillment will succeed; the Business revalidates serviceability against
binding transaction data later in the commerce flow.

A Business unable to evaluate an otherwise well-formed target — for example,
a postal code system it does not model — **MUST** return an actionable
request error; it **MUST NOT** fall back to a coarser interpretation or
return broadened results. If a namespaced target's extension was not
negotiated, the Business **MUST** return an actionable request error rather
than silently omit the target.

The relation also has a deliberate correlation limit: a Location matching both
`serves` and [`filters.items`](#item-availability-filter) satisfies each
constraint independently. The match establishes that at least one method can
provisionally serve the target and that the Business can currently provide
every referenced item at that Location — not that the same method can fulfill
those items to that target.

## Search Filters

Standard Location filters are `hours`, `amenities`, and `items`. A
Business **MAY** support additional custom filters through
`additionalProperties`. All supplied filters combine with AND. A Business
that receives a filter it does not support **MUST** reject the request with
an actionable error; it **MUST NOT** ignore the filter and return broadened
results.

{{ schema_fields('types/location_filter', 'common/location') }}

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

### Amenity Filter

The `amenities` filter identifies static features, services, or capabilities.
A Location matches only when its response `amenities` map contains every
supplied identifier as an exact key. See
[Amenity Vocabulary](#amenity-vocabulary) for well-known values.

#### Amenity Vocabulary

UCP defines an open reverse-DNS vocabulary for amenity identifiers. A Business
**SHOULD** use a well-known UCP identifier when its definition accurately
describes the amenity and **MAY** define additional identifiers under a
namespace it controls. The following table is a non-exhaustive list of
well-known values:

| Amenity Name                               | Domain             | Semantic Definition                                                    |
| :----------------------------------------- | :----------------  | :--------------------------------------------------------------------- |
| `dev.ucp.amenity.wi_fi`                    | Common / Universal | Complimentary or Buyer-accessible wireless internet on premises.       |
| `dev.ucp.amenity.parking`                  | Common / Universal | Dedicated parking lot or garage available on site.                     |
| `dev.ucp.amenity.shopping.curbside_pickup` | Retail Shopping    | Dedicated vehicle bays for order pickup without entering the building. |
| `dev.ucp.amenity.shopping.in_store_pickup` | Retail Shopping    | Dedicated counter or area inside store for order pickup.               |

Location responses use the shared
[Amenity representation](index.md#amenity), which keeps custom identifiers
presentable without assigning them standardized semantics.

A Platform supplies amenity filters as an array of identifiers. Matching uses
exact whole-key equality; namespace prefixes carry no wildcard or inheritance
semantics. A Business **MUST NOT** ignore a supplied identifier: a Location
whose authoritative amenity set lacks any supplied key does not match. This
includes identifiers the Business does not use; no diagnostic is required for
an ordinary non-match. When `filters.amenities` is present, the Business
**MUST** include every supplied identifier in each returned Location's
`amenities` map. A Platform **MUST** reject a returned Location as
non-conforming if it omits the map or any requested key, rather than accept a
broadened or unverifiable result.

### Item Availability Filter

The standard `filters.items` value is a nonempty array of distinct item
identifiers. Each identifier is a stable, opaque, Business-scoped reference to
an orderable item in the applicable domain, such as a shopping variant or a
food menu item. The filter asks one coarse discovery question: at which
Locations can the Business currently provide every referenced item?

A Location matches only when the Business can currently provide every
referenced item at that Location. The Business evaluates each identifier
independently against its current data when processing the request, and the
per-item outcomes combine with AND. Evaluation is independent of the
Location's operating hours and of any fulfillment method: `filters.hours` is a
separate conjunctive predicate, and `filters.hours.open_at` does not change
the availability evaluation instant, even when it represents a future arrival
or pickup time.

An identifier that is unknown, is currently unavailable, or cannot be evaluated
at a candidate Location fails the filter for that Location. The Business
**MUST NOT** ignore such an identifier to return broadened results; the
candidate does not match. This is an ordinary non-match and requires no
diagnostic (see [Empty Search](index.md#common-scenarios)).

A match is a coarse, provisional assertion, and the response intentionally
remains Location-shaped without echoing per-item facts. The result does not
evaluate Platform-selected quantities, prove that the referenced items can be
transacted together as one basket, select or identify a fulfillment method,
reserve any item, or predict availability at a future instant. The Business
**MUST** revalidate transaction-specific availability, quantities, methods,
and terms later in the commerce flow. See
[Relationship to Other Capabilities](index.md#relationship-to-other-capabilities).

Combining `filters.items` with a pickup amenity (for example,
`dev.ucp.amenity.shopping.in_store_pickup`) matches Locations where every
referenced item is currently available and pickup is generally supported. The
two predicates remain independent: the combination does not establish that
the referenced items are available through pickup. Exact one-shot,
method-qualified store finding is outside the base Location capability and
requires an applicable domain capability that can correlate item availability
with a fulfillment method.

## Pagination

Cursor-based pagination for list operations. Cursors are opaque strings. A
Business **MAY** encode them as stateless keyset tokens.

### Page Size

The `limit` parameter is a requested page size, not a guaranteed result
count. When `limit` is omitted, the Business **MUST** apply a default page
size. A default of 10 is **RECOMMENDED**, but the Business **MAY** choose
another value.

The Business **MAY** return fewer results than the requested or default page
size, including when enforcing its maximum page size. A Platform **MUST NOT**
assume that the response count equals either value. This permission applies
only to page size; it does not permit reducing `distance.max` (see
[Distance](#distance)).

### Pagination Request

{{ extension_schema_fields('types/pagination.json#/$defs/request', 'common/location') }}

### Pagination Response

{{ extension_schema_fields('types/pagination.json#/$defs/response', 'common/location') }}

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
      "serves": {
        "point": {
          "latitude": 37.422,
          "longitude": -122.084
        }
      },
      "filters": {
        "hours": {
          "open_at": "2026-05-18T17:00:00Z"
        },
        "amenities": ["dev.ucp.amenity.shopping.curbside_pickup"]
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
          "amenities": {
            "dev.ucp.amenity.shopping.curbside_pickup": {
              "description": "Curbside pickup"
            },
            "dev.ucp.amenity.shopping.in_store_pickup": {
              "description": "In-store pickup"
            },
            "dev.ucp.amenity.parking": {
              "description": "On-site parking"
            },
            "com.example.amenity.in_person_installation": {
              "description": "In-person installation by appointment"
            }
          },
          "timezone": "America/Los_Angeles",
          "hours": [
            {"day": "monday", "opens": "08:00", "closes": "21:00"}
          ]
        }
      ]
    }
    ```

The explicit `serves.point` is the authoritative service target; the coarse
`context` hints only shape ranking and localization. At the supplied instant,
it is Monday at `10:00` in `America/Los_Angeles`, within the returned
interval. See [Operating Hours](index.md#operating-hours) for complete
schedule evaluation rules. The custom amenity remains presentable through its
description without assigning the identifier any standardized UCP meaning.

### Locations where every requested item is available within a distance

=== "Request"

    <!-- ucp:example schema=common/location_search op=search direction=request -->
    ```json
    {
      "distance": {
        "center": {
          "latitude": 40.707,
          "longitude": -74.011
        },
        "max": 10000
      },
      "filters": {
        "items": [
          "item_id_phone_15_pro",
          "item_id_phone_15_pro_case_black"
        ]
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
          "amenities": {
            "dev.ucp.amenity.shopping.curbside_pickup": {
              "description": "Curbside pickup"
            },
            "dev.ucp.amenity.shopping.in_store_pickup": {
              "description": "In-store pickup"
            }
          }
        }
      ]
    }
    ```

Each returned Location satisfies the `distance` relation and the `items`
availability predicate for every supplied identifier. The response does not
echo per-item facts. The `distance` relation does not require the Business to disclose the
Location coordinate used in the evaluation.

## Transport Bindings

* [REST Binding](rest.md#post-locationssearch): `POST /locations/search`
* [MCP Binding](mcp.md#search_locations): `search_locations` tool
