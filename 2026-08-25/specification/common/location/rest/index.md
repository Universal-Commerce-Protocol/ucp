# Location - REST Binding

This document specifies the HTTP/REST binding for the [Location Capability](http://ucp.dev/2026-08-25/specification/common/location/index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise REST transport availability for the Common service and Location capabilities through their UCP profile at `/.well-known/ucp`.

```json
{
  "ucp": {
    "version": "2026-08-25",
    "services": {
      "dev.ucp.common": [
        {
          "version": "2026-08-25",
          "spec": "https://ucp.dev/2026-08-25/specification/overview",
          "transport": "rest",
          "schema": "https://ucp.dev/2026-08-25/services/common/rest.openapi.json",
          "endpoint": "https://business.example.com/ucp"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.common.location.search": [{
        "version": "2026-08-25",
        "spec": "https://ucp.dev/2026-08-25/specification/common/location/search",
        "schema": "https://ucp.dev/2026-08-25/schemas/common/location_search.json"
      }],
      "dev.ucp.common.location.lookup": [{
        "version": "2026-08-25",
        "spec": "https://ucp.dev/2026-08-25/specification/common/location/lookup",
        "schema": "https://ucp.dev/2026-08-25/schemas/common/location_lookup.json"
      }]
    },
    "payment_handlers": {}
  }
}
```

## Endpoints

| Endpoint            | Method | Capability                                                                        | Description                                                                                   |
| ------------------- | ------ | --------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `/locations/search` | POST   | [Search](http://ucp.dev/2026-08-25/specification/common/location/search/index.md) | Search for physical locations.                                                                |
| `/locations/lookup` | POST   | [Lookup](http://ucp.dev/2026-08-25/specification/common/location/lookup/index.md) | Lookup Locations by identifier, optionally refined by explicit spatial relations and filters. |

### `POST /locations/search`

Maps to the [Location Search](http://ucp.dev/2026-08-25/specification/common/location/search/index.md) capability. See the [complete transport-neutral Search example](http://ucp.dev/2026-08-25/specification/common/location/search/#examples).

**Inputs**

| Name       | Type                                                                          | Requirement | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ---------- | ----------------------------------------------------------------------------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| query      | string                                                                        | Optional    | Free-text search query for natural language location search (e.g., 'restaurants near me that deliver', 'hotels with pool').                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| context    | [Context](/2026-08-25/specification/reference/#context)                       | Optional    | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals    | [Signals](/2026-08-25/specification/reference/#signals)                       | Optional    | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| distance   | [Location Distance](/2026-08-25/specification/reference/#location-distance)   | Optional    | Optional explicit-center radius predicate. When present, it combines with `serves` and every supplied `filters` predicate using AND.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| serves     | [Location Serves](/2026-08-25/specification/reference/#location-serves)       | Optional    | Optional authoritative service-target predicate. When present, it combines with `distance` and every supplied `filters` predicate using AND.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| filters    | [Location Filter](/2026-08-25/specification/reference/#location-filter)       | Optional    | Filter criteria to narrow Location Search and Lookup results. All supplied filters combine with AND.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| pagination | [Pagination Request](/2026-08-25/specification/reference/#pagination-request) | Optional    | Cursor-based pagination for list operations.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |

**Output**

| Name       | Type                                                                            | Requirement  | Description                                                           |
| ---------- | ------------------------------------------------------------------------------- | ------------ | --------------------------------------------------------------------- |
| ucp        | any                                                                             | **Required** | UCP metadata for location responses.                                  |
| locations  | Array\[[Location](/2026-08-25/specification/reference/#location)\]              | **Required** | Locations matching the search criteria.                               |
| pagination | [Pagination Response](/2026-08-25/specification/reference/#pagination-response) | Optional     | Cursor-based pagination for list operations.                          |
| messages   | Array\[[Message](/2026-08-25/specification/reference/#message)\]                | Optional     | Errors, warnings, or informational messages about the search results. |

#### Binding envelope example

```json
POST /locations/search HTTP/1.1
Host: business.example.com
Content-Type: application/json
Request-Id: 8ef9b0c2-78d1-4e4b-91c2-3e2ef0d3ab9f
UCP-Agent: profile="https://platform.example/profiles/v2026-01/agent.json"

{
  "query": "grocery store"
}
```

```json
HTTP/1.1 200 OK
Content-Type: application/json
Content-Digest: sha-256=:yG9a8bC7...:

{
  "ucp": {
    "version": "2026-08-25",
    "capabilities": {
      "dev.ucp.common.location.search": [
        {"version": "2026-08-25"}
      ]
    }
  },
  "locations": [
    {
      "id": "loc_valley_grocers",
      "name": "Valley Grocers"
    }
  ]
}
```

### `POST /locations/lookup`

Maps to the [Location Lookup](http://ucp.dev/2026-08-25/specification/common/location/lookup/index.md) capability. See the [complete transport-neutral Lookup example](http://ucp.dev/2026-08-25/specification/common/location/lookup/#examples).

**Inputs**

| Name     | Type                                                                        | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| -------- | --------------------------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ids      | Array[string]                                                               | **Required** | Identifiers of the Locations to look up. The Business MUST support canonical `Location.id` values and MAY support secondary or alias identifiers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| distance | [Location Distance](/2026-08-25/specification/reference/#location-distance) | Optional     | Optional explicit-center radius predicate applied after ID resolution. It combines with `serves` and every supplied `filters` predicate using AND.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| serves   | [Location Serves](/2026-08-25/specification/reference/#location-serves)     | Optional     | Optional authoritative service-target predicate applied after ID resolution. It combines with `distance` and every supplied `filters` predicate using AND.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| filters  | [Location Filter](/2026-08-25/specification/reference/#location-filter)     | Optional     | Filter criteria to narrow Location Search and Lookup results. All supplied filters combine with AND.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| context  | [Context](/2026-08-25/specification/reference/#context)                     | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals  | [Signals](/2026-08-25/specification/reference/#signals)                     | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |

**Output**

| Name      | Type                                                                                         | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                    |
| --------- | -------------------------------------------------------------------------------------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp       | any                                                                                          | **Required** | UCP metadata for location responses.                                                                                                                                                                                                                                                                                                                           |
| locations | Array\[ [Lookup Location](/2026-08-25/specification/common/location/rest/#lookup-location)\] | **Required** | Locations matching the requested identifiers and refinements. May contain fewer Locations if some identifiers do not resolve or their resolved Locations are filtered out, or more if one identifier resolves to multiple Locations. When multiple identifiers resolve to the same Location, one returned Location carries all corresponding `inputs` entries. |
| messages  | Array\[[Message](/2026-08-25/specification/reference/#message)\]                             | Optional     | Errors, warnings, or informational messages about the requested Locations, including `batch_limit_applied` when the Business processes only its configured maximum number of identifiers.                                                                                                                                                                      |

#### Binding envelope example

```json
POST /locations/lookup HTTP/1.1
Host: business.example.com
Content-Type: application/json
Request-Id: 2c9b0c2a-18d1-4e4b-91c2-3e2ef0d3ab9f
UCP-Agent: profile="https://platform.example/profiles/v2026-01/agent.json"

{
  "ids": ["loc_downtown"]
}
```

```json
HTTP/1.1 200 OK
Content-Type: application/json

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

## Error Handling

UCP uses a two-layer error model separating transport-level errors from business outcomes.

### Transport Errors

Use HTTP status codes for protocol-level issues that prevent request processing:

| Status | Meaning                                                     |
| ------ | ----------------------------------------------------------- |
| 400    | Bad Request - Malformed JSON or missing required parameters |
| 401    | Unauthorized - Missing or invalid authentication            |
| 429    | Too Many Requests - Rate limited                            |
| 500    | Internal Server Error                                       |

### Business Outcomes

All application-level outcomes return HTTP 200 with the UCP envelope and optional `messages` array. See [Location Overview](http://ucp.dev/2026-08-25/specification/common/location/#messages-and-error-handling) for message semantics.

## Entities

### UCP Response Location (Envelope)

UCP metadata for location responses.

| Name             | Type   | Requirement  | Description                                                                                                                                    |
| ---------------- | ------ | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| version          | string | **Required** | Version identifier in YYYY-MM-DD format.                                                                                                       |
| map_order        | object | Optional     | Preferred key-traversal order for sibling registry fields inside the root `ucp` envelope (`services`, `capabilities`, and `payment_handlers`). |
| status           | string | Optional     | Application-level status of the UCP operation. **Enum:** `success`, `error`                                                                    |
| services         | object | Optional     | Service registry keyed by reverse-domain name.                                                                                                 |
| capabilities     | object | Optional     | Capability registry keyed by reverse-domain name.                                                                                              |
| payment_handlers | object | Optional     | Payment handler registry keyed by reverse-domain name.                                                                                         |
| capabilities     | any    | Optional     |                                                                                                                                                |

### Amenity Type

| Name                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Type | Requirement | Description |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ----------- | ----------- |
| Reverse-domain identifier used for collision-safe namespacing of capabilities, services, handlers, eligibility claims, and extension-contributed keys. Must contain at least two dot-separated segments (e.g., 'dev.ucp.shopping.checkout', 'com.example.loyalty_gold'). Segments after the first are domain- or identifier-derived: they may contain interior hyphens, may start with a digit, and may contain underscores (e.g., 'com.example-shop.checkout', 'com.2example.cart', 'dev.ucp.common.identity_linking'), but must not start or end with a hyphen. The first segment (the reversed top-level domain) is letters and digits, and may contain interior hyphens to support internationalized (punycode) top-level domains such as 'xn--p1ai'. |      |             |             |

**Pattern:** `^[a-z](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9_-]*[a-z0-9_])?)+$`

### Amenity

Buyer-facing presentation metadata for one amenity identifier. The containing map key, not this metadata, defines amenity identity and filter matching.

| Name        | Type   | Requirement  | Description                                                                                                                                                                                                                                                                    |
| ----------- | ------ | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| description | string | **Required** | Short, plain-text, buyer-facing label or phrase for the amenity, suitable for direct use in a compact list (e.g., 'Curbside pickup'). The Business SHOULD localize it for the request when possible. This content does not participate in amenity identity or filter matching. |

### Location

| Name            | Type                                                                           | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                    |
| --------------- | ------------------------------------------------------------------------------ | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| id              | string                                                                         | **Required** | Stable, opaque, Business-scoped Location identifier.                                                                                                                                                                                                                                                                                                                           |
| name            | string                                                                         | **Required** | Buyer-facing, Business-owned display name.                                                                                                                                                                                                                                                                                                                                     |
| address         | [Postal Address](/2026-08-25/specification/reference/#postal-address)          | Optional     | Physical address of the location.                                                                                                                                                                                                                                                                                                                                              |
| geo             | [Geo](/2026-08-25/specification/reference/#geo)                                | Optional     | Geographic coordinates for the location.                                                                                                                                                                                                                                                                                                                                       |
| amenities       | object                                                                         | Optional     | Static features, services, or capabilities of the Location, keyed by reverse-domain amenity identifier. Each value provides a buyer-facing description; the key alone defines amenity identity and filter matching.                                                                                                                                                            |
| hours           | Array\[[Daily Hour](/2026-08-25/specification/reference/#daily-hour)\]         | Optional     | Regular weekly operating hours whose day and time values use this Location's canonical local civil-time frame. Multiple entries for the same day support split shifts. An omitted day has no regular interval beginning that day; an interval beginning on the preceding day can carry into it. Omission of the entire `hours` property means the regular schedule is unknown. |
| exception_hours | Array\[[Exception Hour](/2026-08-25/specification/reference/#exception-hour)\] | Optional     | Date-specific operating-hour exceptions, including full closures, whose date and time values use this Location's canonical local civil-time frame.                                                                                                                                                                                                                             |
| timezone        | string                                                                         | Optional     | The Business-owned IANA Time Zone Database identifier (e.g., 'America/New_York') defining this Location's canonical local civil-time frame for all returned schedule day, time, and date fields. The Business does not vary this canonical framing by the requesting Platform's or Buyer's timezone. Required when hours or exception_hours is present.                        |

### Lookup Location

Location with required correlation metadata for lookup responses.

| Name            | Type          | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                    |
| --------------- | ------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| id              | string        | **Required** | Stable, opaque, Business-scoped Location identifier.                                                                                                                                                                                                                                                                                                                           |
| name            | string        | **Required** | Buyer-facing, Business-owned display name.                                                                                                                                                                                                                                                                                                                                     |
| address         | object        | Optional     | Physical address of the location.                                                                                                                                                                                                                                                                                                                                              |
| geo             | object        | Optional     | Geographic coordinates for the location.                                                                                                                                                                                                                                                                                                                                       |
| amenities       | object        | Optional     | Static features, services, or capabilities of the Location, keyed by reverse-domain amenity identifier. Each value provides a buyer-facing description; the key alone defines amenity identity and filter matching.                                                                                                                                                            |
| hours           | Array[object] | Optional     | Regular weekly operating hours whose day and time values use this Location's canonical local civil-time frame. Multiple entries for the same day support split shifts. An omitted day has no regular interval beginning that day; an interval beginning on the preceding day can carry into it. Omission of the entire `hours` property means the regular schedule is unknown. |
| exception_hours | Array[object] | Optional     | Date-specific operating-hour exceptions, including full closures, whose date and time values use this Location's canonical local civil-time frame.                                                                                                                                                                                                                             |
| timezone        | string        | Optional     | The Business-owned IANA Time Zone Database identifier (e.g., 'America/New_York') defining this Location's canonical local civil-time frame for all returned schedule day, time, and date fields. The Business does not vary this canonical framing by the requesting Platform's or Buyer's timezone. Required when hours or exception_hours is present.                        |
| inputs          | Array[object] | **Required** | Which request identifiers resolved to this Location. Each entry preserves one identifier exactly as supplied in the request.                                                                                                                                                                                                                                                   |

### Location Filter

| Name      | Type                                                                       | Requirement | Description                                                                                                                                                                                            |
| --------- | -------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| hours     | object                                                                     | Optional    | Filter by operating hours, evaluated at the one supplied instant.                                                                                                                                      |
| amenities | Array\[[Amenity Type](/2026-08-25/specification/reference/#amenity-type)\] | Optional    | Filter by amenity identifier. A Location matches only when its `amenities` map contains every supplied identifier as an exact key; descriptions and namespace prefixes do not participate in matching. |
| items     | Array[string]                                                              | Optional    | Current item-availability filter. A candidate Location matches only when the Business can currently provide every referenced item at that Location; all references combine with AND.                   |

### Location Distance

| Name   | Type                                            | Requirement  | Description                                                                                                                                                                             |
| ------ | ----------------------------------------------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| center | [Geo](/2026-08-25/specification/reference/#geo) | **Required** | Explicit center of the radius. The Platform MUST supply it; the Business MUST NOT derive it from context, signals, an IP address, or `serves`.                                          |
| max    | number                                          | **Required** | Inclusive maximum distance in RFC 7035 distance unit (meters). A Business unable to honor the supplied value MUST reject the request rather than clamp it or substitute another radius. |

### Location Serves

| Name    | Type                                            | Requirement | Description                               |
| ------- | ----------------------------------------------- | ----------- | ----------------------------------------- |
| point   | [Geo](/2026-08-25/specification/reference/#geo) | Optional    | WGS 84 coordinates of the service target. |
| address | any                                             | Optional    | Coarse locality of the service target.    |

### Error Response

| Name         | Type                                                             | Requirement  | Description                                                       |
| ------------ | ---------------------------------------------------------------- | ------------ | ----------------------------------------------------------------- |
| ucp          | any                                                              | **Required** | UCP protocol metadata. Status MUST be 'error' for error response. |
| messages     | Array\[[Message](/2026-08-25/specification/reference/#message)\] | **Required** | Array of messages describing why the operation failed.            |
| continue_url | string                                                           | Optional     | URL for buyer handoff or session recovery.                        |

## Conformance

A conforming REST transport implementation **MUST**:

1. Implement endpoints for each Location capability advertised in the Business's UCP profile, per their respective capability requirements ([Search](http://ucp.dev/2026-08-25/specification/common/location/search/index.md), [Lookup](http://ucp.dev/2026-08-25/specification/common/location/lookup/index.md)). Each capability **MAY** be adopted independently.
1. Evaluate the `distance` and `serves` relations and the `filters.items` availability predicate only against their explicit Platform-supplied operands. Never derive an operand from `context`, `signals`, or an IP address, and never apply an implicit serviceability or item-availability check when its input is absent.
1. Apply `distance`, `serves`, and every supplied `filters` predicate conjunctively (AND).
1. Support cursor-based pagination for Search according to the shared pagination contract (see [Pagination](http://ucp.dev/2026-08-25/specification/common/location/search/#pagination)).
1. Return HTTP 200 for Lookup requests; unknown identifiers result in fewer or no Locations returned (**MAY** include informational `not_found` messages).
1. Return HTTP 200 when a Lookup request exceeds the Business's batch maximum, process the first maximum number of distinct identifiers in request order, and include an informational `batch_limit_applied` message.
