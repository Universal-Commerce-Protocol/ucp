# Booking Capability - MCP Binding

This document specifies the Model Context Protocol (MCP) binding for the [Booking Capability](http://ucp.dev/draft/specification/lodging/booking/index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise MCP transport availability through their UCP profile at `/.well-known/ucp`.

```json
{
  "ucp": {
    "version": "draft",
    "services": {
      "dev.ucp.lodging": [
        {
          "version": "draft",
          "spec": "https://ucp.dev/draft/specification/overview",
          "transport": "mcp",
          "schema": "https://ucp.dev/draft/services/lodging/mcp.openrpc.json",
          "endpoint": "https://business.example.com/ucp/mcp"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.lodging.booking": [
        {
          "version": "draft",
          "spec": "https://ucp.dev/draft/specification/lodging/booking",
          "schema": "https://ucp.dev/draft/schemas/lodging/booking.json"
        }
      ]
    },
    "payment_handlers": {
      "com.example.vendor.delegate_payment": [
        {
          "id": "handler_1",
          "version": "draft",
          "spec": "https://example.vendor.com/specs/delegate-payment",
          "schema": "https://example.vendor.com/schemas/delegate-payment-config.json",
          "available_instruments": [
            {"type": "card", "constraints": {"properties": {"brand": {"enum": ["visa", "mastercard"]}}}}
          ],
          "config": {...}
        }
      ]
    }
  }
}
```

### Request Metadata

MCP clients **MUST** include a `meta` object in every request containing protocol metadata:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "create_booking_session",
    "arguments": {
      "meta": {
        "ucp-agent": {
          "profile": "https://platform.example/profiles/lodging-agent.json"
        },
        "idempotency-key": "550e8400-e29b-41d4-a716-446655440000"
      },
      "booking": {
        "property": {...},
        "stays": [...]
      }
    }
  }
}
```

The `meta["ucp-agent"]` field is **required** on all requests to enable [capability negotiation](http://ucp.dev/draft/specification/overview/#negotiation-protocol). The `complete_booking_session` and `cancel_booking_session` operations also require `meta["idempotency-key"]` for retry safety. Platforms **MAY** include additional metadata fields.

## Tools

UCP Capabilities map 1:1 to MCP Tools.

### Identifier Pattern

MCP tools separate resource identification from payload data:

- **Requests:** For operations on existing booking sessions (`get`, `update`, `complete`, `cancel`), a top-level `id` parameter identifies the target resource. The `booking` object in the request payload **MUST NOT** contain an `id` field.
- **Responses:** All responses **MUST** include `booking.id` as part of the full resource state.
- **Create:** The `create_booking_session` operation does not require an `id` in the request, and the response includes the newly assigned `booking.id`.

| Tool                       | Operation                                                                                                | Description               |
| -------------------------- | -------------------------------------------------------------------------------------------------------- | ------------------------- |
| `create_booking_session`   | [Create Booking Session](http://ucp.dev/draft/specification/lodging/booking/#create-booking-session)     | Create a booking session. |
| `get_booking_session`      | [Get Booking Session](http://ucp.dev/draft/specification/lodging/booking/#get-booking-session)           | Get a booking session.    |
| `update_booking_session`   | [Update Booking Session](http://ucp.dev/draft/specification/lodging/booking/#update-booking-session)     | Update a booking session. |
| `complete_booking_session` | [Complete Booking Session](http://ucp.dev/draft/specification/lodging/booking/#complete-booking-session) | Complete booking.         |
| `cancel_booking_session`   | [Cancel Booking Session](http://ucp.dev/draft/specification/lodging/booking/#cancel-booking-session)     | Cancel a booking session. |

### `create_booking_session`

Maps to the [Create Booking Session](http://ucp.dev/draft/specification/lodging/booking/#create-booking-session) operation.

#### Input Schema

| Name           | Type                                                    | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| -------------- | ------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| property       | [Property](/draft/specification/reference/#property)    | **Required** | The physical establishment or geographic location where the lodging is situated (e.g., hotel, resort, villa estate, cabin park).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| stays          | Array\[[Stay](/draft/specification/reference/#stay)\]   | **Required** | List of stay line-items for the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| booker         | [Booker](/draft/specification/reference/#booker)        | Optional     | Representation of the legal contracting party making the reservation.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| guests         | Array\[[Guest](/draft/specification/reference/#guest)\] | Optional     | List of guest profiles associated with the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| travel_purpose | string                                                  | Optional     | Purpose of the trip or reservation, supplied by the Platform. Well-known values: `business`, `leisure`. Platforms MAY send additional values; a Business MUST ignore values it does not recognize and treat the purpose as unspecified.                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| context        | [Context](/draft/specification/reference/#context)      | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals        | [Signals](/draft/specification/reference/#signals)      | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| payment        | [Payment](/draft/specification/reference/#payment)      | Optional     | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |

#### Output Schema

| Name           | Type                                                                         | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| -------------- | ---------------------------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp            | any                                                                          | **Required** | UCP metadata for booking responses.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| id             | string                                                                       | **Required** | Unique identifier of the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| status         | string                                                                       | **Required** | Booking state indicating the current phase and required action. See Booking Status lifecycle documentation for state transition details. **Enum:** `incomplete`, `requires_escalation`, `ready_for_complete`, `complete_in_progress`, `completed`, `canceled`                                                                                                                                                                                                                                                                                                                                                                                                           |
| property       | [Property](/draft/specification/reference/#property)                         | **Required** | The physical establishment or geographic location where the lodging is situated (e.g., hotel, resort, villa estate, cabin park).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| stays          | Array\[[Stay Response](/draft/specification/reference/#stay)\]               | **Required** | List of stay line-items for the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| booker         | [Booker](/draft/specification/reference/#booker)                             | Optional     | Representation of the legal contracting party making the reservation.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| guests         | Array\[[Guest](/draft/specification/reference/#guest)\]                      | Optional     | List of guest profiles associated with the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| travel_purpose | string                                                                       | Optional     | Purpose of the trip or reservation, supplied by the Platform. Well-known values: `business`, `leisure`. Platforms MAY send additional values; a Business MUST ignore values it does not recognize and treat the purpose as unspecified.                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| context        | [Context](/draft/specification/reference/#context)                           | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals        | [Signals](/draft/specification/reference/#signals)                           | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| currency       | string                                                                       | **Required** | ISO 4217 currency code reflecting the business's market determination. Derived from address, context, and geo IP—buyers provide signals, businesses determine currency.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| totals         | [Totals](/draft/specification/reference/#totals)                             | **Required** | Authoritative pricing breakdown for the booking. The `total` entry represents the authoritative all-in stay liability across all requested units. All non-total entries are price addends that sum to `total`. When payment timing is split across schedules or property-collected charges apply, timing breakdowns are conveyed via payment terms (`payment.terms[]`) schedules rather than within `totals`.                                                                                                                                                                                                                                                           |
| actions        | [Actions](/draft/specification/reference/#actions)                           | Optional     | Outstanding extension-defined Actions for this booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| messages       | Array\[[Message](/draft/specification/reference/#message)\]                  | Optional     | List of messages with error and info about the booking session state.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| links          | Array\[[Link](/draft/specification/reference/#link)\]                        | **Required** | Links to be displayed by the platform (Privacy Policy, TOS). Mandatory for legal compliance.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| policies       | Array\[[Policy](/draft/specification/reference/#policy)\]                    | Optional     | Policies (e.g., cancellation terms) that apply to the booking session. `applies_to` targets are relative to the response root; when absent or empty, refer to the URLs in `links[]`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| expires_at     | string                                                                       | Optional     | RFC 3339 timestamp after which the booking session is no longer valid. Indicates how long session state, quoted pricing, and any temporary inventory holds remain valid. Businesses MUST NOT complete a booking at a modified price without first returning updated totals to the platform.                                                                                                                                                                                                                                                                                                                                                                             |
| continue_url   | string                                                                       | Optional     | URL for booking handoff and session recovery. MUST be provided when status is requires_escalation. See specification for format and availability requirements.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| payment        | [Payment](/draft/specification/reference/#payment)                           | Optional     | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| confirmation   | [Booking Confirmation](/draft/specification/reference/#booking-confirmation) | Optional     | Details about the booking created from this specific session.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |

#### Example

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "create_booking_session",
    "arguments": {
      "meta": {
        "ucp-agent": {
          "profile": "https://platform.example/profiles/v2026-07/lodging-agent.json"
        }
      },
      "booking": {
        "property": {
          "id": "hotel_123"
        },
        "stays": [
          {
            "id": "stay_luxury_queen__rp_avg_base_rate",
            "accommodation_type": {
              "id": "rt_luxury_queen"
            },
            "rate_plan": {
              "id": "rp_avg_base_rate"
            },
            "occupancy": {
              "adults": 2,
              "total": 2
            },
            "stay_dates": {
              "start_date": "2026-07-15",
              "end_date": "2026-07-21"
            }
          }
        ]
      }
    }
  }
}
```

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "structuredContent": {
      "ucp": {
        "version": "draft",
        "capabilities": {
          "dev.ucp.lodging.booking": [
            {"version": "draft"}
          ]
        },
        "payment_handlers": {
          "com.example.vendor.delegate_payment": [
            {"id": "handler_1", "version": "draft", "available_instruments": [{"type": "card"}], "config": {}}
          ]
        }
      },
      "id": "booking_123",
      "status": "incomplete",
      "property": {
        "id": "hotel_123",
        "name": "Beautiful Scenery Hotel",
        "address": {
          "street_address": "123 Scene St",
          "address_locality": "Phoenix",
          "address_region": "AZ",
          "address_country": "US",
          "postal_code": "85004"
        }
      },
      "stays": [
        {
          "id": "stay_luxury_queen__rp_avg_base_rate",
          "accommodation_type": {
            "id": "rt_luxury_queen",
            "title": "Luxury Queen Room with Two Queen Beds",
            "capacity": {
              "adults": 2,
              "children": 2,
              "child_age_ranges": [
                {
                  "ages": {
                    "min": 0,
                    "max": 5
                  },
                  "limit": 1
                },
                {
                  "ages": {
                    "min": 6,
                    "max": 17
                  },
                  "limit": 1
                }
              ],
              "total": 4
            }
          },
          "rate_plan": {
            "id": "rp_avg_base_rate",
            "title": "Best Available Rate"
          },
          "occupancy": {
            "adults": 2,
            "total": 2
          },
          "stay_dates": {
            "start_date": "2026-07-15",
            "end_date": "2026-07-21"
          },
          "totals": [
            {
              "type": "subtotal",
              "amount": 330000
            },
            {
              "type": "tax",
              "amount": 33000
            },
            {
              "type": "total",
              "amount": 363000
            }
          ]
        }
      ],
      "currency": "USD",
      "totals": [
        {
          "type": "subtotal",
          "amount": 330000
        },
        {
          "type": "tax",
          "amount": 33000
        },
        {
          "type": "fee",
          "display_text": "Booking fee",
          "amount": 1000
        },
        {
          "type": "total",
          "amount": 364000
        }
      ],
      "links": [
        {
          "type": "privacy_policy",
          "url": "https://business.example.com/privacy"
        },
        {
          "type": "terms_of_service",
          "url": "https://business.example.com/terms"
        },
        {
          "type": "cancellation_policy",
          "url": "https://business.example.com/cancellation"
        }
      ],
      "continue_url": "https://business.example.com/booking-sessions/booking_123",
      "expires_at": "2026-06-01T18:30:00Z"
    },
    "content": [
      {
        "type": "text",
        "text": "{\"ucp\":{…},…}"
      }
    ]
  }
}
```

Selected room is no longer available — no booking session resource is created:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "structuredContent": {
      "ucp": {
        "version": "draft",
        "status": "error"
      },
      "messages": [
        {
          "type": "error",
          "code": "inventory_exhausted",
          "content": "Selected room is no longer available.",
          "severity": "unrecoverable"
        }
      ],
      "continue_url": "https://business.com/"
    },
    "content": [
      {"type": "text", "text": "..."}
    ]
  }
}
```

### `get_booking_session`

Maps to the [Get Booking Session](http://ucp.dev/draft/specification/lodging/booking/#get-booking-session) operation.

#### Input Schema

- `id` (String): **Required**. The ID of the booking session to retrieve.

#### Output Schema

| Name           | Type                                                                         | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| -------------- | ---------------------------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp            | any                                                                          | **Required** | UCP metadata for booking responses.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| id             | string                                                                       | **Required** | Unique identifier of the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| status         | string                                                                       | **Required** | Booking state indicating the current phase and required action. See Booking Status lifecycle documentation for state transition details. **Enum:** `incomplete`, `requires_escalation`, `ready_for_complete`, `complete_in_progress`, `completed`, `canceled`                                                                                                                                                                                                                                                                                                                                                                                                           |
| property       | [Property](/draft/specification/reference/#property)                         | **Required** | The physical establishment or geographic location where the lodging is situated (e.g., hotel, resort, villa estate, cabin park).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| stays          | Array\[[Stay Response](/draft/specification/reference/#stay)\]               | **Required** | List of stay line-items for the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| booker         | [Booker](/draft/specification/reference/#booker)                             | Optional     | Representation of the legal contracting party making the reservation.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| guests         | Array\[[Guest](/draft/specification/reference/#guest)\]                      | Optional     | List of guest profiles associated with the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| travel_purpose | string                                                                       | Optional     | Purpose of the trip or reservation, supplied by the Platform. Well-known values: `business`, `leisure`. Platforms MAY send additional values; a Business MUST ignore values it does not recognize and treat the purpose as unspecified.                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| context        | [Context](/draft/specification/reference/#context)                           | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals        | [Signals](/draft/specification/reference/#signals)                           | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| currency       | string                                                                       | **Required** | ISO 4217 currency code reflecting the business's market determination. Derived from address, context, and geo IP—buyers provide signals, businesses determine currency.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| totals         | [Totals](/draft/specification/reference/#totals)                             | **Required** | Authoritative pricing breakdown for the booking. The `total` entry represents the authoritative all-in stay liability across all requested units. All non-total entries are price addends that sum to `total`. When payment timing is split across schedules or property-collected charges apply, timing breakdowns are conveyed via payment terms (`payment.terms[]`) schedules rather than within `totals`.                                                                                                                                                                                                                                                           |
| actions        | [Actions](/draft/specification/reference/#actions)                           | Optional     | Outstanding extension-defined Actions for this booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| messages       | Array\[[Message](/draft/specification/reference/#message)\]                  | Optional     | List of messages with error and info about the booking session state.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| links          | Array\[[Link](/draft/specification/reference/#link)\]                        | **Required** | Links to be displayed by the platform (Privacy Policy, TOS). Mandatory for legal compliance.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| policies       | Array\[[Policy](/draft/specification/reference/#policy)\]                    | Optional     | Policies (e.g., cancellation terms) that apply to the booking session. `applies_to` targets are relative to the response root; when absent or empty, refer to the URLs in `links[]`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| expires_at     | string                                                                       | Optional     | RFC 3339 timestamp after which the booking session is no longer valid. Indicates how long session state, quoted pricing, and any temporary inventory holds remain valid. Businesses MUST NOT complete a booking at a modified price without first returning updated totals to the platform.                                                                                                                                                                                                                                                                                                                                                                             |
| continue_url   | string                                                                       | Optional     | URL for booking handoff and session recovery. MUST be provided when status is requires_escalation. See specification for format and availability requirements.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| payment        | [Payment](/draft/specification/reference/#payment)                           | Optional     | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| confirmation   | [Booking Confirmation](/draft/specification/reference/#booking-confirmation) | Optional     | Details about the booking created from this specific session.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |

### `update_booking_session`

Maps to the [Update Booking Session](http://ucp.dev/draft/specification/lodging/booking/#update-booking-session) operation.

#### Input Schema

- `id` (String): **Required**. The ID of the booking session to update.

| Name           | Type                                                    | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| -------------- | ------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| property       | [Property](/draft/specification/reference/#property)    | **Required** | The physical establishment or geographic location where the lodging is situated (e.g., hotel, resort, villa estate, cabin park).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| stays          | Array\[[Stay](/draft/specification/reference/#stay)\]   | **Required** | List of stay line-items for the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| booker         | [Booker](/draft/specification/reference/#booker)        | Optional     | Representation of the legal contracting party making the reservation.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| guests         | Array\[[Guest](/draft/specification/reference/#guest)\] | Optional     | List of guest profiles associated with the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| travel_purpose | string                                                  | Optional     | Purpose of the trip or reservation, supplied by the Platform. Well-known values: `business`, `leisure`. Platforms MAY send additional values; a Business MUST ignore values it does not recognize and treat the purpose as unspecified.                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| context        | [Context](/draft/specification/reference/#context)      | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals        | [Signals](/draft/specification/reference/#signals)      | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| payment        | [Payment](/draft/specification/reference/#payment)      | Optional     | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |

#### Output Schema

| Name           | Type                                                                         | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| -------------- | ---------------------------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp            | any                                                                          | **Required** | UCP metadata for booking responses.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| id             | string                                                                       | **Required** | Unique identifier of the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| status         | string                                                                       | **Required** | Booking state indicating the current phase and required action. See Booking Status lifecycle documentation for state transition details. **Enum:** `incomplete`, `requires_escalation`, `ready_for_complete`, `complete_in_progress`, `completed`, `canceled`                                                                                                                                                                                                                                                                                                                                                                                                           |
| property       | [Property](/draft/specification/reference/#property)                         | **Required** | The physical establishment or geographic location where the lodging is situated (e.g., hotel, resort, villa estate, cabin park).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| stays          | Array\[[Stay Response](/draft/specification/reference/#stay)\]               | **Required** | List of stay line-items for the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| booker         | [Booker](/draft/specification/reference/#booker)                             | Optional     | Representation of the legal contracting party making the reservation.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| guests         | Array\[[Guest](/draft/specification/reference/#guest)\]                      | Optional     | List of guest profiles associated with the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| travel_purpose | string                                                                       | Optional     | Purpose of the trip or reservation, supplied by the Platform. Well-known values: `business`, `leisure`. Platforms MAY send additional values; a Business MUST ignore values it does not recognize and treat the purpose as unspecified.                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| context        | [Context](/draft/specification/reference/#context)                           | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals        | [Signals](/draft/specification/reference/#signals)                           | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| currency       | string                                                                       | **Required** | ISO 4217 currency code reflecting the business's market determination. Derived from address, context, and geo IP—buyers provide signals, businesses determine currency.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| totals         | [Totals](/draft/specification/reference/#totals)                             | **Required** | Authoritative pricing breakdown for the booking. The `total` entry represents the authoritative all-in stay liability across all requested units. All non-total entries are price addends that sum to `total`. When payment timing is split across schedules or property-collected charges apply, timing breakdowns are conveyed via payment terms (`payment.terms[]`) schedules rather than within `totals`.                                                                                                                                                                                                                                                           |
| actions        | [Actions](/draft/specification/reference/#actions)                           | Optional     | Outstanding extension-defined Actions for this booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| messages       | Array\[[Message](/draft/specification/reference/#message)\]                  | Optional     | List of messages with error and info about the booking session state.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| links          | Array\[[Link](/draft/specification/reference/#link)\]                        | **Required** | Links to be displayed by the platform (Privacy Policy, TOS). Mandatory for legal compliance.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| policies       | Array\[[Policy](/draft/specification/reference/#policy)\]                    | Optional     | Policies (e.g., cancellation terms) that apply to the booking session. `applies_to` targets are relative to the response root; when absent or empty, refer to the URLs in `links[]`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| expires_at     | string                                                                       | Optional     | RFC 3339 timestamp after which the booking session is no longer valid. Indicates how long session state, quoted pricing, and any temporary inventory holds remain valid. Businesses MUST NOT complete a booking at a modified price without first returning updated totals to the platform.                                                                                                                                                                                                                                                                                                                                                                             |
| continue_url   | string                                                                       | Optional     | URL for booking handoff and session recovery. MUST be provided when status is requires_escalation. See specification for format and availability requirements.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| payment        | [Payment](/draft/specification/reference/#payment)                           | Optional     | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| confirmation   | [Booking Confirmation](/draft/specification/reference/#booking-confirmation) | Optional     | Details about the booking created from this specific session.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |

#### Example

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "update_booking_session",
    "arguments": {
      "meta": {
        "ucp-agent": {
          "profile": "https://platform.example/profiles/v2026-07/lodging-agent.json"
        }
      },
      "id": "booking_123",
      "booking": {
        "property": {
          "id": "hotel_123"
        },
        "stays": [
          {
            "id": "stay_luxury_queen__rp_avg_base_rate",
            "accommodation_type": {
              "id": "rt_luxury_queen"
            },
            "rate_plan": {
              "id": "rp_avg_base_rate"
            },
            "occupancy": {
              "adults": 2,
              "total": 2
            },
            "stay_dates": {
              "start_date": "2026-07-15",
              "end_date": "2026-07-21"
            },
            "guest_assignments": [
              {
                "guest_id": "gst_01",
                "role": "primary"
              },
              {
                "guest_id": "gst_02",
                "role": "accompanying"
              }
            ]
          }
        ],
        "guests": [
          {
            "id": "gst_01",
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane.doe@example.com",
            "phone_number": "+14155551234"
          },
          {
            "id": "gst_02",
            "first_name": "Mary",
            "last_name": "Doe"
          }
        ]
      }
    }
  }
}
```

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "structuredContent": {
      "ucp": {
        "version": "draft",
        "capabilities": {
          "dev.ucp.lodging.booking": [
            {"version": "draft"}
          ]
        },
        "payment_handlers": {
          "com.example.vendor.delegate_payment": [
            {"id": "handler_1", "version": "draft", "available_instruments": [{"type": "card"}], "config": {}}
          ]
        }
      },
      "id": "booking_123",
      "status": "ready_for_complete",
      "property": {
        "id": "hotel_123",
        "name": "Beautiful Scenery Hotel",
        "address": {
          "street_address": "123 Scene St",
          "address_locality": "Phoenix",
          "address_region": "AZ",
          "address_country": "US",
          "postal_code": "85004"
        }
      },
      "stays": [
        {
          "id": "stay_luxury_queen__rp_avg_base_rate",
          "accommodation_type": {
            "id": "rt_luxury_queen",
            "title": "Luxury Queen Room with Two Queen Beds",
            "capacity": {
              "adults": 2,
              "children": 2,
              "child_age_ranges": [
                {
                  "ages": {
                    "min": 0,
                    "max": 5
                  },
                  "limit": 1
                },
                {
                  "ages": {
                    "min": 6,
                    "max": 17
                  },
                  "limit": 1
                }
              ],
              "total": 4
            }
          },
          "rate_plan": {
            "id": "rp_avg_base_rate",
            "title": "Best Available Rate"
          },
          "occupancy": {
            "adults": 2,
            "total": 2
          },
          "stay_dates": {
            "start_date": "2026-07-15",
            "end_date": "2026-07-21"
          },
          "guest_assignments": [
            {
              "guest_id": "gst_01",
              "role": "primary"
            },
            {
              "guest_id": "gst_02",
              "role": "accompanying"
            }
          ],
          "totals": [
            {
              "type": "subtotal",
              "amount": 330000
            },
            {
              "type": "tax",
              "amount": 33000
            },
            {
              "type": "total",
              "amount": 363000
            }
          ]
        }
      ],
      "guests": [
        {
          "id": "gst_01",
          "first_name": "Jane",
          "last_name": "Doe",
          "email": "jane.doe@example.com",
          "phone_number": "+14155551234"
        },
        {
          "id": "gst_02",
          "first_name": "Mary",
          "last_name": "Doe"
        }
      ],
      "currency": "USD",
      "totals": [
        {
          "type": "subtotal",
          "amount": 330000
        },
        {
          "type": "tax",
          "amount": 33000
        },
        {
          "type": "fee",
          "display_text": "Booking fee",
          "amount": 1000
        },
        {
          "type": "total",
          "amount": 364000
        }
      ],
      "links": [
        {
          "type": "privacy_policy",
          "url": "https://business.example.com/privacy"
        },
        {
          "type": "terms_of_service",
          "url": "https://business.example.com/terms"
        },
        {
          "type": "cancellation_policy",
          "url": "https://business.example.com/cancellation"
        }
      ],
      "continue_url": "https://business.example.com/booking-sessions/booking_123",
      "expires_at": "2026-06-01T18:30:00Z"
    },
    "content": [
      {
        "type": "text",
        "text": "{\"ucp\":{…},…}"
      }
    ]
  }
}
```

### `complete_booking_session`

Maps to the [Complete Booking Session](http://ucp.dev/draft/specification/lodging/booking/#complete-booking-session) operation.

#### Input Schema

- `id` (String): **Required**. The ID of the booking session.

| Name    | Type                                               | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                             |
| ------- | -------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| signals | [Signals](/draft/specification/reference/#signals) | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace. |
| payment | [Payment](/draft/specification/reference/#payment) | **Required** | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                              |

#### Output Schema

| Name           | Type                                                                         | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| -------------- | ---------------------------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp            | any                                                                          | **Required** | UCP metadata for booking responses.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| id             | string                                                                       | **Required** | Unique identifier of the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| status         | string                                                                       | **Required** | Booking state indicating the current phase and required action. See Booking Status lifecycle documentation for state transition details. **Enum:** `incomplete`, `requires_escalation`, `ready_for_complete`, `complete_in_progress`, `completed`, `canceled`                                                                                                                                                                                                                                                                                                                                                                                                           |
| property       | [Property](/draft/specification/reference/#property)                         | **Required** | The physical establishment or geographic location where the lodging is situated (e.g., hotel, resort, villa estate, cabin park).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| stays          | Array\[[Stay Response](/draft/specification/reference/#stay)\]               | **Required** | List of stay line-items for the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| booker         | [Booker](/draft/specification/reference/#booker)                             | Optional     | Representation of the legal contracting party making the reservation.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| guests         | Array\[[Guest](/draft/specification/reference/#guest)\]                      | Optional     | List of guest profiles associated with the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| travel_purpose | string                                                                       | Optional     | Purpose of the trip or reservation, supplied by the Platform. Well-known values: `business`, `leisure`. Platforms MAY send additional values; a Business MUST ignore values it does not recognize and treat the purpose as unspecified.                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| context        | [Context](/draft/specification/reference/#context)                           | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals        | [Signals](/draft/specification/reference/#signals)                           | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| currency       | string                                                                       | **Required** | ISO 4217 currency code reflecting the business's market determination. Derived from address, context, and geo IP—buyers provide signals, businesses determine currency.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| totals         | [Totals](/draft/specification/reference/#totals)                             | **Required** | Authoritative pricing breakdown for the booking. The `total` entry represents the authoritative all-in stay liability across all requested units. All non-total entries are price addends that sum to `total`. When payment timing is split across schedules or property-collected charges apply, timing breakdowns are conveyed via payment terms (`payment.terms[]`) schedules rather than within `totals`.                                                                                                                                                                                                                                                           |
| actions        | [Actions](/draft/specification/reference/#actions)                           | Optional     | Outstanding extension-defined Actions for this booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| messages       | Array\[[Message](/draft/specification/reference/#message)\]                  | Optional     | List of messages with error and info about the booking session state.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| links          | Array\[[Link](/draft/specification/reference/#link)\]                        | **Required** | Links to be displayed by the platform (Privacy Policy, TOS). Mandatory for legal compliance.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| policies       | Array\[[Policy](/draft/specification/reference/#policy)\]                    | Optional     | Policies (e.g., cancellation terms) that apply to the booking session. `applies_to` targets are relative to the response root; when absent or empty, refer to the URLs in `links[]`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| expires_at     | string                                                                       | Optional     | RFC 3339 timestamp after which the booking session is no longer valid. Indicates how long session state, quoted pricing, and any temporary inventory holds remain valid. Businesses MUST NOT complete a booking at a modified price without first returning updated totals to the platform.                                                                                                                                                                                                                                                                                                                                                                             |
| continue_url   | string                                                                       | Optional     | URL for booking handoff and session recovery. MUST be provided when status is requires_escalation. See specification for format and availability requirements.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| payment        | [Payment](/draft/specification/reference/#payment)                           | Optional     | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| confirmation   | [Booking Confirmation](/draft/specification/reference/#booking-confirmation) | Optional     | Details about the booking created from this specific session.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |

**Note:** Response **MUST** include a `confirmation` object if completion succeeds.

#### Example

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "complete_booking_session",
    "arguments": {
      "meta": {
        "ucp-agent": {
          "profile": "https://platform.example/profiles/v2026-07/lodging-agent.json"
        },
        "idempotency-key": "550e8400-e29b-41d4-a716-446655440000"
      },
      "id": "booking_123",
      "booking": {
        "payment": {
          "instruments": [
            {
              "id": "pi_handler_1",
              "handler_id": "handler_1",
              "type": "card",
              "selected": true,
              "display": {
                "brand": "mastercard",
                "last_digits": "5678",
                "card_art": "https://cart-art-1.html",
                "description": "Vendor Pay •••• 5678"
              },
              "billing_address": {
                "street_address": "123 Main St",
                "address_locality": "Mountain View",
                "address_region": "CA",
                "address_country": "US",
                "postal_code": "94040"
              },
              "credential": {
                "type": "PAYMENT_GATEWAY",
                "token": "examplePaymentMethodToken"
              }
            }
          ]
        },
        "signals": {
          "dev.ucp.user_agent": "Mozilla/5.0 ..."
        }
      }
    }
  }
}
```

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "structuredContent": {
     "ucp": {
        "version": "draft",
        "capabilities": {
          "dev.ucp.lodging.booking": [
            {"version": "draft"}
          ]
        },
        "payment_handlers": {
          "com.example.vendor.delegate_payment": [
            {"id": "handler_1", "version": "draft", "available_instruments": [{"type": "card"}], "config": {}}
          ]
        }
      },
      "id": "booking_123",
      "status": "completed",
      "property": {
        "id": "hotel_123",
        "name": "Beautiful Scenery Hotel",
        "address": {
          "street_address": "123 Scene St",
          "address_locality": "Phoenix",
          "address_region": "AZ",
          "address_country": "US",
          "postal_code": "85004"
        }
      },
      "stays": [
        {
          "id": "stay_luxury_queen__rp_avg_base_rate",
          "accommodation_type": {
            "id": "rt_luxury_queen",
            "title": "Luxury Queen Room with Two Queen Beds",
            "capacity": {
              "adults": 2,
              "children": 2,
              "child_age_ranges": [
                {
                  "ages": {
                    "min": 0,
                    "max": 5
                  },
                  "limit": 1
                },
                {
                  "ages": {
                    "min": 6,
                    "max": 17
                  },
                  "limit": 1
                }
              ],
              "total": 4
            }
          },
          "rate_plan": {
            "id": "rp_avg_base_rate",
            "title": "Best Available Rate"
          },
          "occupancy": {
            "adults": 2,
            "total": 2
          },
          "stay_dates": {
            "start_date": "2026-07-15",
            "end_date": "2026-07-21"
          },
          "guest_assignments": [
            {
              "guest_id": "gst_01",
              "role": "primary"
            },
            {
              "guest_id": "gst_02",
              "role": "accompanying"
            }
          ],
          "totals": [
            {
              "type": "subtotal",
              "amount": 330000
            },
            {
              "type": "tax",
              "amount": 33000
            },
            {
              "type": "total",
              "amount": 363000
            }
          ]
        }
      ],
      "guests": [
        {
          "id": "gst_01",
          "first_name": "Jane",
          "last_name": "Doe",
          "email": "jane.doe@example.com",
          "phone_number": "+14155551234"
        },
        {
          "id": "gst_02",
          "first_name": "Mary",
          "last_name": "Doe"
        }
      ],
      "currency": "USD",
      "totals": [
        {
          "type": "subtotal",
          "amount": 330000
        },
        {
          "type": "tax",
          "amount": 33000
        },
        {
          "type": "fee",
          "display_text": "Booking fee",
          "amount": 1000
        },
        {
          "type": "total",
          "amount": 364000
        }
      ],
      "links": [
        {
          "type": "privacy_policy",
          "url": "https://business.example.com/privacy"
        },
        {
          "type": "terms_of_service",
          "url": "https://business.example.com/terms"
        },
        {
          "type": "cancellation_policy",
          "url": "https://business.example.com/cancellation"
        }
      ],
      "confirmation": {
        "id": "confirmation_123",
        "label": "CON123AZ",
        "pincode": "1234"
      },
      "payment": {...},
      "signals": {...}
    },
    "content": [
      {
        "type": "text",
        "text": "{\"ucp\":{…},…}"
      }
    ]
  }
}
```

### `cancel_booking_session`

Maps to the [Cancel Booking Session](http://ucp.dev/draft/specification/lodging/booking/#cancel-booking-session) operation.

#### Input Schema

- `id` (String): **Required**. The ID of the booking session.

#### Output Schema

| Name           | Type                                                                         | Requirement  | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| -------------- | ---------------------------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ucp            | any                                                                          | **Required** | UCP metadata for booking responses.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| id             | string                                                                       | **Required** | Unique identifier of the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| status         | string                                                                       | **Required** | Booking state indicating the current phase and required action. See Booking Status lifecycle documentation for state transition details. **Enum:** `incomplete`, `requires_escalation`, `ready_for_complete`, `complete_in_progress`, `completed`, `canceled`                                                                                                                                                                                                                                                                                                                                                                                                           |
| property       | [Property](/draft/specification/reference/#property)                         | **Required** | The physical establishment or geographic location where the lodging is situated (e.g., hotel, resort, villa estate, cabin park).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| stays          | Array\[[Stay Response](/draft/specification/reference/#stay)\]               | **Required** | List of stay line-items for the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| booker         | [Booker](/draft/specification/reference/#booker)                             | Optional     | Representation of the legal contracting party making the reservation.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| guests         | Array\[[Guest](/draft/specification/reference/#guest)\]                      | Optional     | List of guest profiles associated with the booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| travel_purpose | string                                                                       | Optional     | Purpose of the trip or reservation, supplied by the Platform. Well-known values: `business`, `leisure`. Platforms MAY send additional values; a Business MUST ignore values it does not recognize and treat the purpose as unspecified.                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| context        | [Context](/draft/specification/reference/#context)                           | Optional     | Provisional buyer signals for relevance and localization—not authoritative data. Businesses SHOULD use these values when verified inputs (e.g., shipping address) are absent, and MAY ignore or down-rank them if inconsistent with higher-confidence signals (authenticated account, risk detection) or regulatory constraints (export controls). Eligibility and policy enforcement MUST occur at checkout time using binding transaction data. Context SHOULD be non-identifying and can be disclosed progressively—coarse signals early, finer resolution as the session progresses. Higher-resolution data (shipping address, billing address) supersedes context. |
| signals        | [Signals](/draft/specification/reference/#signals)                           | Optional     | Environment data provided by the platform to support authorization and abuse prevention. Values MUST NOT be buyer-asserted claims — platforms provide signals based on direct observation or independently verifiable third-party attestations. All signal keys MUST use reverse-domain naming to ensure provenance and prevent collisions when multiple extensions contribute to the shared namespace.                                                                                                                                                                                                                                                                 |
| currency       | string                                                                       | **Required** | ISO 4217 currency code reflecting the business's market determination. Derived from address, context, and geo IP—buyers provide signals, businesses determine currency.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| totals         | [Totals](/draft/specification/reference/#totals)                             | **Required** | Authoritative pricing breakdown for the booking. The `total` entry represents the authoritative all-in stay liability across all requested units. All non-total entries are price addends that sum to `total`. When payment timing is split across schedules or property-collected charges apply, timing breakdowns are conveyed via payment terms (`payment.terms[]`) schedules rather than within `totals`.                                                                                                                                                                                                                                                           |
| actions        | [Actions](/draft/specification/reference/#actions)                           | Optional     | Outstanding extension-defined Actions for this booking.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| messages       | Array\[[Message](/draft/specification/reference/#message)\]                  | Optional     | List of messages with error and info about the booking session state.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| links          | Array\[[Link](/draft/specification/reference/#link)\]                        | **Required** | Links to be displayed by the platform (Privacy Policy, TOS). Mandatory for legal compliance.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| policies       | Array\[[Policy](/draft/specification/reference/#policy)\]                    | Optional     | Policies (e.g., cancellation terms) that apply to the booking session. `applies_to` targets are relative to the response root; when absent or empty, refer to the URLs in `links[]`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| expires_at     | string                                                                       | Optional     | RFC 3339 timestamp after which the booking session is no longer valid. Indicates how long session state, quoted pricing, and any temporary inventory holds remain valid. Businesses MUST NOT complete a booking at a modified price without first returning updated totals to the platform.                                                                                                                                                                                                                                                                                                                                                                             |
| continue_url   | string                                                                       | Optional     | URL for booking handoff and session recovery. MUST be provided when status is requires_escalation. See specification for format and availability requirements.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| payment        | [Payment](/draft/specification/reference/#payment)                           | Optional     | Payment configuration containing handlers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| confirmation   | [Booking Confirmation](/draft/specification/reference/#booking-confirmation) | Optional     | Details about the booking created from this specific session.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |

**Note:** Response **MUST** include `"status": "canceled"` if cancellation succeeds.

## Error Handling

UCP distinguishes between protocol errors and business outcomes. See the [Core Specification](http://ucp.dev/draft/specification/overview/#error-handling) for the complete error code registry and transport binding examples.

- **Protocol errors**: Transport-level failures (authentication, rate limiting, unavailability) that prevent request processing. Returned as JSON-RPC `error` with code `-32000` (or `-32001` for discovery errors).
- **Business outcomes**: Application-level results from successful request processing, returned as JSON-RPC `result` with UCP envelope and `messages`.

### Business Outcomes

Business outcomes (including errors like unavailable merchandise) are returned as JSON-RPC `result` with `structuredContent` containing the UCP envelope and `messages`:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "structuredContent": {
      "ucp": {
        "version": "draft",
        "capabilities": {
          "dev.ucp.lodging.booking": [
            {"version": "draft"}
          ]
        },
        "payment_handlers": {
          "com.example.vendor.delegate_payment": [
            {"id": "handler_1", "version": "draft", "available_instruments": [{"type": "card"}], "config": {}}
          ]
        }
      },
      "id": "booking_123",
      "status": "incomplete",
      "property": {
        "id": "hotel_123",
        "name": "Beautiful Scenery Hotel"
      },
      "stays": [
        {
          "id": "stay_luxury_queen__rp_avg_base_rate",
          "accommodation_type": {
            "id": "rt_luxury_queen",
            "title": "Luxury Queen Room with Two Queen Beds",
            "capacity": {
              "adults": 2,
              "children": 2,
              "child_age_ranges": [
                {
                  "ages": {
                    "min": 0,
                    "max": 5
                  },
                  "limit": 1
                },
                {
                  "ages": {
                    "min": 6,
                    "max": 17
                  },
                  "limit": 1
                }
              ],
              "total": 4
            }
          },
          "rate_plan": {
            "id": "rp_avg_base_rate",
            "title": "Best Available Rate"
          },
          "occupancy": {
            "adults": 6,
            "total": 6
          },
          "stay_dates": {
            "start_date": "2026-07-15",
            "end_date": "2026-07-21"
          },
          "totals": [
            {
              "type": "subtotal",
              "amount": 350000
            },
            {
              "type": "tax",
              "amount": 42000
            },
            {
              "type": "total",
              "amount": 392000
            }
          ]
        }
      ],
      "currency": "USD",
      "totals": [
        {
          "type": "subtotal",
          "amount": 350000
        },
        {
          "type": "tax",
          "amount": 42000
        },
        {
          "type": "fee",
          "display_text": "Resort fee",
          "amount": 32500
        },
        {
          "type": "total",
          "amount": 424500
        }
      ],
      "links": [],
      "continue_url": "https://business.example.com/booking-sessions/booking_123",
      "expires_at": "2026-06-01T18:30:00Z",
      "messages": [
        {
          "type": "error",
          "code": "occupancy_exceeded_capacity",
          "content": "Number of additional guests requested surpassed room capacity.",
          "path": "$.stays[0]",
          "severity": "recoverable"
        }
      ]
    },
    "content": [
      {"type": "text", "text": "{\"ucp\":{…},…}"}
    ]
  }
}
```

For `create_booking_session`, when no booking session can be created, JSON-RPC `result` with `structuredContent` containing the UCP envelope and `messages`:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "structuredContent": {
      "ucp": { "version": "draft", "status": "error" },
      "messages": [
        {
          "type": "error",
          "code": "inventory_exhausted",
          "content": "Selected room is no longer available.",
          "severity": "unrecoverable"
        }
      ],
      "continue_url": "https://business.com/"
    },
    "content": [
      {"type": "text", "text": "{\"ucp\":{…},…}"}
    ]
  }
}
```

## Message Signing

Platforms **SHOULD** authenticate agents when using MCP transport. When using HTTP Message Signatures, all booking operations follow the [Message Signatures](http://ucp.dev/draft/specification/signatures/index.md) specification.

### Request Signing

UCP's MCP transport uses **streamable HTTP**, allowing the same RFC 9421 signature mechanism as REST. The signature is applied at the HTTP layer:

| Header            | Required | Description                      |
| ----------------- | -------- | -------------------------------- |
| `Signature-Input` | Yes      | Describes signed components      |
| `Signature`       | Yes      | Contains the signature value     |
| `Content-Digest`  | Yes      | SHA-256 hash of request body     |
| `UCP-Agent`       | Yes      | Signer identity (profile URL)    |
| `Idempotency-Key` | Cond.\*  | Unique key for replay protection |

\* Required for `complete_booking_session` and `cancel_booking_session`

**Example Signed Request:**

```http
POST /mcp HTTP/1.1
Host: business.example.com
Content-Type: application/json
UCP-Agent: profile="https://platform.example/.well-known/ucp"
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Digest: sha-256=:RK/0qy18MlBSVnWgjwz6lZEWjP/lF5HF9bvEF8FabDg=:
Signature-Input: sig1=("@method" "@authority" "@path" "content-digest" "content-type" "ucp-agent" "idempotency-key");keyid="platform-2026"
Signature: sig1=:MEUCIQDXyK9N3p5Rt...:

{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"complete_booking_session","arguments":{"id":"booking_123","booking":{"payment":{...}, ...}}}}
```

The `Content-Digest` binds the JSON-RPC body to the signature. No JSON canonicalization is required.

See [Message Signatures - MCP Transport](http://ucp.dev/draft/specification/signatures/#mcp-transport) for details.

### Response Signing

Response signatures are **RECOMMENDED** for:

- `complete_booking_session` responses (booking confirmation)

Response signatures are **OPTIONAL** for:

- `create_booking_session`, `get_booking_session`, `update_booking_session`, `cancel_booking_session`

**Example Signed Response:**

```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Digest: sha-256=:Y5fK8nLmPqRsT3vWxYzAbCdEfGhIjKlMnO...:
Signature-Input: sig1=("@status" "content-digest" "content-type");keyid="business-2026"
Signature: sig1=:MFQCIH7kL9nM2oP5qR8sT1uV4wX6yZaB3cD...:

{"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"..."}],"structuredContent":{"id":"booking_123","status":"completed", ...}}}
```

See [Message Signatures - REST Response Signing](http://ucp.dev/draft/specification/signatures/#rest-response-signing) for the signing algorithm (identical for MCP over HTTP).

## Conformance

A conforming MCP transport implementation **MUST**:

1. Implement JSON-RPC 2.0 protocol correctly.
1. Provide all core booking tools defined in this specification.
1. Return errors per the [Core Specification](http://ucp.dev/draft/specification/overview/#error-handling).
1. Return business outcomes as JSON-RPC `result` with UCP envelope and `messages` array.
1. Validate tool inputs against UCP schemas.
1. Support HTTP transport with streaming.

A conforming implementation **SHOULD**:

1. Authenticate agents using one of the supported mechanisms (API keys, OAuth, mTLS, or HTTP Message Signatures per [Message Signatures](http://ucp.dev/draft/specification/signatures/index.md)).
1. Verify authentication on incoming requests before processing.

## Implementation

UCP operations are defined using [OpenRPC](https://open-rpc.org/) (JSON-RPC schema format). The [MCP specification](https://modelcontextprotocol.io/) requires all tool invocations to use a `tools/call` method with the operation name and arguments wrapped in `params`. Implementers **MUST** apply this transformation:

| OpenRPC  | MCP                |
| -------- | ------------------ |
| `method` | `params.name`      |
| `params` | `params.arguments` |

**Param conventions:**

- `meta` contains request metadata
- `id` identifies the target resource (path parameter equivalent)
- `booking` contains the domain payload (body equivalent)
