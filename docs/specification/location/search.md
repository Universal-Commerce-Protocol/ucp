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
warehouses). Supports free-text queries, explicit spatial relations
(`distance` and `serves`), and structured filtering by operating hours and
offerings such as amenities and inventory availability.

## Operation

| Operation | Description |
| :--- | :--- |
| **Search Locations** | Search for locations using query text, spatial relations, context, and filters. |

### Request

{{ extension_schema_fields('location_search.json#/$defs/search_request', 'location') }}

### Response

{{ extension_schema_fields('location_search.json#/$defs/search_response', 'location') }}

## Request Grammar

Each request input has a distinct role:

| Input | Meaning |
| :--- | :--- |
| `query` | Free-text retrieval (e.g., "restaurants near me that deliver"). |
| `distance` | A relation between a candidate Location and an explicit Platform-supplied center point and inclusive radius. |
| `serves` | A relation between a candidate Location and one explicit Platform-supplied service target. |
| `filters` | Predicates over inherent or current Location facts: `hours`, `amenities`, and `inventory`. |
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
treat `query` text as creating a `distance` or `serves` relation or as
proof of spatial matching — only the explicit operands in
[Spatial Relations](#spatial-relations) establish those — and **MUST NOT**
relax an explicit structured constraint because of the `query` text: a
Location that fails `distance`, `serves`, or a `filters` predicate is
excluded no matter how well it matches the query.

### Bounded Browse

A request with no structured spatial constraint is valid. An empty body
`{}`, a request carrying only `context` or `signals`, a request carrying
only `pagination`, and a filters-only request are each a bounded browse over
the Business's default, policy-controlled selection — never a spatial
assertion and never an export. An omitted `pagination.limit` allows Business
to enforce their desired arbitrarily threshold and **MUST NOT** be
interpreted as "all records".

A Business **MAY** use `context`, `signals`, and IP-derived locality to
influence ranking, localization, or selection of a bounded default browse
page. A Business using those hints **MUST NOT** treat that choice as proof
that a Location serves a target or falls within an unstated radius; only
explicit `distance` and `serves` operands establish spatial matching.

### Rejection and Empty Results

Requests that fail the Search request schema use the binding's
invalid-request mechanism. The same mechanism carries the defined semantic
errors for `distance` and `serves`; see
[Spatial Relations](#spatial-relations). A supported predicate that simply
matches no Locations remains a successful empty business outcome (see
[Empty Search](index.md#common-scenarios)).

## Spatial Relations

### Distance

The `distance` relation matches Locations within an inclusive radius of an
explicit center point. Both members are required: `distance.center` is a
`geo.json` point in World Geodetic System 1984 (WGS 84) decimal degrees, and
`distance.max` is the inclusive maximum distance in meters.

{{ schema_fields('types/location_distance', 'location') }}

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
    its own. Requested-limit clamping in [Pagination](#pagination) never
    applies to `distance.max`.
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

{{ schema_fields('types/location_serves', 'location') }}

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

The relation also has a deliberate correlation limit: a Location matching
both `filters.inventory` and `serves` establishes that the inventory
predicate holds there and that at least one method can serve the target —
not that the same method can fulfill that item to that target.

## Search Filters

Location filters are predicates over inherent or current Location facts.
Standard Location filters are `hours`, `amenities`, and `inventory`. A
Business **MAY** support additional custom filters through
`additionalProperties`. All supplied filters combine with AND.

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

## Pagination

Cursor-based pagination for list operations. Cursors are opaque strings. A
Business **MAY** encode them as stateless keyset tokens.

### Page Size

The `limit` parameter is a requested page size, not a guaranteed count. A
Business **SHOULD** accept a page size of at least 10 unless resource or
policy constraints require a lower maximum. When the requested limit exceeds
the Business's maximum, the Business **MAY** clamp to that maximum silently —
returning fewer results without error. A Platform **MUST NOT** assume the
response size equals the requested limit. An omitted `limit` allows Business to
apply their desired threshold; it never means all records, and a cursor is not
an export guarantee. This clamping policy is specific to pagination; it never extends to
`distance.max` (see [Distance](#distance)).

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
          "amenities": ["dev.ucp.amenity.shopping.curbside_pickup", "dev.ucp.amenity.shopping.in_store_pickup", "dev.ucp.amenity.parking"],
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
schedule evaluation rules.

### Locations with an inventory item within a distance

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
        "inventory": [
          {
            "id": "item_id_phone_15_pro",
            "availability_status": "in_stock"
          }
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
          "amenities": ["dev.ucp.amenity.shopping.curbside_pickup", "dev.ucp.amenity.shopping.in_store_pickup"]
        }
      ]
    }
    ```

Each returned Location satisfies both the `distance` relation and the
inventory predicate. The `distance` relation does not require the Business to
disclose the Location coordinate used in the evaluation.

## Transport Bindings

* [REST Binding](rest.md#post-locationssearch): `POST /locations/search`
* [MCP Binding](mcp.md#search_locations): `search_locations` tool
