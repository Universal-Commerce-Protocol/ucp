# Location Lookup Capability

- **Capability Name:** `dev.ucp.common.location.lookup`

Resolves identifiers to physical Locations. Supports full-detail batch retrieval of multiple Locations or retrieval of a single Location (useful for a dedicated Location detail page), optionally refined by the same explicit spatial relations and filters as Search (see [Refinement](#refinement)).

## Operation

| Operation              | Description                                          |
| ---------------------- | ---------------------------------------------------- |
| **Lookup Location(s)** | Retrieve single or multiple Locations by identifier. |

## Supported Identifiers

The `ids` parameter accepts an array of identifiers. A Business **MUST** support lookup by a Location's stable canonical `Location.id` and **MAY** additionally support secondary or alias identifiers.

A Business **MUST** dedupe duplicate identifiers in the request. When an identifier matches multiple Locations, the Business returns the matching Locations and **MAY** limit the result set. When multiple identifiers resolve to the same Location, the Business **MUST** return it only once.

### Platform Correlation

The response does not guarantee order. Each Location carries an `inputs` array identifying which requested identifiers resolved to it. Every entry contains a required `id`, copied exactly from the Lookup request.

Multiple request identifiers may resolve to the same Location. When this occurs, the Location's `inputs` array contains one entry per resolved identifier. A Business **MUST NOT** include a Location without an `inputs` entry in a Lookup response.

### Batch Size

A Business **SHOULD** accept at least 10 identifiers per request and **MAY** enforce a maximum batch size. The maximum applies after duplicate identifiers are deduplicated.

When a request exceeds that maximum, the Business **MUST** process the first maximum number of distinct identifiers in request order and return a successful response for that prefix. It **MUST** include an informational message with `code: "batch_limit_applied"`; the message content **MUST** state the applied maximum and how many identifiers were not processed. The Business **MUST NOT** evaluate the omitted suffix or report its identifiers as unresolved. A Platform **MUST NOT** interpret the omitted suffix as unresolved and **MAY** submit it in a subsequent request.

### Refinement

The Business first resolves the identifiers and deduplicates repeated values. Optional root `distance` and `serves` relations and `filters` predicates then refine the resolved set. All supplied criteria combine with AND: a resolved Location is returned only when it satisfies every supplied relation and filter. The relations and predicates use the same schemas and semantics as Search — see [Spatial Relations](http://ucp.dev/2026-08-25/specification/common/location/search/#spatial-relations), [Search Filters](http://ucp.dev/2026-08-25/specification/common/location/search/#search-filters), and [Item Availability Filter](http://ucp.dev/2026-08-25/specification/common/location/search/#item-availability-filter).

For example, if a Platform requests `["loc_downtown", "loc_uptown"]` with an hours filter of `{"open_at": "2026-05-18T17:00:00Z"}`:

1. The Business first resolves both identifiers to their respective Locations.
1. The Business evaluates the supplied instant against each resolved Location.
1. If `loc_uptown` is closed at that instant, the Business excludes it and returns only `loc_downtown`.

An identifier that does not resolve has no corresponding returned Location or `inputs` entry. If an identifier resolves to a Location that fails any supplied criterion, including because a `filters.items` identifier is unknown, is unavailable, or cannot be evaluated there, that Location and its corresponding `inputs` entry are omitted. The request still succeeds. The Business **MAY** attach an informational `not_found` message for an unresolved Location identifier, but no per-identifier explanation is guaranteed for a refinement non-match.

### Request

Request body for batch location lookup. The Business resolves and deduplicates `ids` before applying `distance`, `serves`, and every supplied `filters` predicate; all structured predicates combine with AND.

| Name     | Type          | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| -------- | ------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ids      | Array[string] | **Required** | Identifiers of the Locations to look up. The Business MUST support canonical `Location.id` values and MAY support secondary or alias identifiers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| distance | object        | Optional     | Optional explicit-center radius predicate applied after ID resolution. It combines with `serves` and every supplied `filters` predicate using AND.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| serves   | object        | Optional     | Optional authoritative service-target predicate applied after ID resolution. It combines with `distance` and every supplied `filters` predicate using AND.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| filters  | object        | Optional     | Filter criteria to narrow Location Search and Lookup results. All supplied filters combine with AND.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| context  | object        | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals  | object        | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |

### Response

| Name      | Type            | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                    |
| --------- | --------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp       | any             | **Required** | UCP metadata for location responses.                                                                                                                                                                                                                                                                                                                           |
| locations | Array[Location] | **Required** | Locations matching the requested identifiers and refinements. May contain fewer Locations if some identifiers do not resolve or their resolved Locations are filtered out, or more if one identifier resolves to multiple Locations. When multiple identifiers resolve to the same Location, one returned Location carries all corresponding `inputs` entries. |
| messages  | Array[object]   | Optional     | Errors, warnings, or informational messages about the requested Locations, including `batch_limit_applied` when the Business processes only its configured maximum number of identifiers.                                                                                                                                                                      |

## Examples

The following request and response are transport-neutral UCP payloads.

### Downtown Store schedule

```json
{
  "ids": ["loc_downtown", "downtown-store"]
}
```

```json
{
  "ucp": {
    "version": "2026-08-25",
    "capabilities": {
      "dev.ucp.common.location.lookup": [
        {"version": "2026-08-25"}
      ]
    }
  },
  "locations": [
    {
      "id": "loc_downtown",
      "inputs": [
        {"id": "loc_downtown"},
        {"id": "downtown-store"}
      ],
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
        "longitude": -74.011
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
        }
      },
      "timezone": "America/New_York",
      "hours": [
        {"day": "monday", "opens": "09:00", "closes": "21:00"},
        {"day": "tuesday", "opens": "09:00", "closes": "12:00"},
        {"day": "tuesday", "opens": "13:00", "closes": "21:00"},
        {"day": "wednesday", "opens": "09:00", "closes": "21:00"},
        {"day": "thursday", "opens": "09:00", "closes": "21:00"},
        {"day": "friday", "opens": "09:00", "closes": "22:00"},
        {"day": "saturday", "opens": "10:00", "closes": "20:00"}
      ],
      "exception_hours": [
        {
          "title": "Thanksgiving",
          "valid_from": "2026-11-26",
          "valid_through": "2026-11-26"
        }
      ]
    }
  ]
}
```

The response correlates the canonical identifier and the Business-supported alias to one Location. Tuesday's two `hours` entries form a split shift. Sunday has no `hours` entry, meaning no regular interval begins that day. The `exception_hours` entry omits `opens` and `closes`, making it a full closure. See [Operating Hours](http://ucp.dev/2026-08-25/specification/common/location/#operating-hours) for schedule representation and evaluation rules.

### Item availability refinement

```json
{
  "ids": ["loc_downtown", "loc_uptown"],
  "filters": {
    "items": ["item_id_phone_15_pro"]
  }
}
```

```json
{
  "ucp": {
    "version": "2026-08-25",
    "capabilities": {
      "dev.ucp.common.location.lookup": [
        {"version": "2026-08-25"}
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
```

Both identifiers resolve, but the Business cannot currently provide the referenced item at `loc_uptown`, so that Location and its `inputs` entry are omitted. The request still succeeds, and this ordinary refinement non-match requires no message (see [Item Availability Filter](http://ucp.dev/2026-08-25/specification/common/location/search/#item-availability-filter)).

### Partial success

```json
{
  "ids": ["loc_downtown", "loc_invalid_id"]
}
```

```json
{
  "ucp": {
    "version": "2026-08-25",
    "capabilities": {
      "dev.ucp.common.location.lookup": [
        {"version": "2026-08-25"}
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

The request succeeds with the Locations that resolve. A Business can use an informational `not_found` message to identify an unresolved identifier.

### Batch limit applied

The following Business accepts at most two distinct identifiers per Lookup request.

```json
{
  "ids": ["loc_downtown", "loc_uptown", "loc_airport"]
}
```

```json
{
  "ucp": {
    "version": "2026-08-25",
    "capabilities": {
      "dev.ucp.common.location.lookup": [
        {"version": "2026-08-25"}
      ]
    }
  },
  "locations": [
    {
      "id": "loc_downtown",
      "inputs": [{"id": "loc_downtown"}],
      "name": "Downtown Store"
    },
    {
      "id": "loc_uptown",
      "inputs": [{"id": "loc_uptown"}],
      "name": "Uptown Store"
    }
  ],
  "messages": [
    {
      "type": "info",
      "code": "batch_limit_applied",
      "content": "Processed the first 2 of 3 distinct identifiers; 1 identifier was not processed."
    }
  ]
}
```

The Business evaluates `loc_downtown` and `loc_uptown` in request order. `loc_airport` was not evaluated and is not unresolved; the Platform can submit it in a subsequent request.

## Transport Bindings

- [REST Binding](http://ucp.dev/2026-08-25/specification/common/location/rest/#post-locationslookup): `POST /locations/lookup`
- [MCP Binding](http://ucp.dev/2026-08-25/specification/common/location/mcp/#lookup_locations): `lookup_locations` tool
