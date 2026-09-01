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

# Booking Capability - MCP Binding

This document specifies the Model Context Protocol (MCP) binding for the
[Booking Capability](index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise MCP transport availability through their UCP profile at
`/.well-known/ucp`.

<!-- ucp:example schema=profile def=business_schema op=read direction=response -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": {
      "dev.ucp.lodging": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/overview",
          "transport": "mcp",
          "schema": "https://ucp.dev/{{ ucp_version }}/services/lodging/mcp.openrpc.json",
          "endpoint": "https://business.example.com/ucp/mcp"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.lodging.booking": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/lodging/booking",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/lodging/booking.json"
        }
      ]
    },
    "payment_handlers": {
      "com.example.vendor.delegate_payment": [
        {
          "id": "handler_1",
          "version": "{{ ucp_version }}",
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

MCP clients **MUST** include a `meta` object in every request containing
protocol metadata:

<!-- ucp:example schema=lodging/booking op=start direction=request extract=$.params.arguments.booking -->
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
        "accommodation": {...},
        "room_rates": [...],
        "itinerary": {...}
      }
    }
  }
}
```

The `meta["ucp-agent"]` field is **required** on all requests to enable
[capability negotiation](../../overview/index.md#negotiation-protocol). The
`complete_booking_session` operation also requires
`meta["idempotency-key"]` for retry safety. Platforms **MAY** include
additional metadata fields.

## Tools

UCP Capabilities map 1:1 to MCP Tools.

### Identifier Pattern

MCP tools separate resource identification from payload data:

* **Requests:** For operations on existing booking sessions (`get`, `update`,
    `complete`, `cancel`), a top-level `id` parameter identifies the target
    resource. The `booking` object in the request payload **MUST NOT** contain
    an `id` field.
* **Responses:** All responses **MUST** include `booking.id` as part of the full resource state.
* **Create:** The `create_booking_session` operation does not require an `id` in the request, and the response includes the newly assigned `booking.id`.

| Tool                       | Operation                                                           | Description                |
| :------------------------- | :------------------------------------------------------------------ | :------------------------- |
| `create_booking_session`   | [Create Booking Session](index.md#create-booking-session)           | Create a booking session.  |
| `get_booking_session`      | [Get Booking Session](index.md#get-booking-session)                 | Get a booking session.     |
| `update_booking_session`   | [Update Booking Session](index.md#update-booking-session)           | Update a booking session.  |
| `complete_booking_session` | [Complete Booking Session](index.md#complete-booking-session)       | Complete booking.          |
| `cancel_booking_session`   | [Cancel Booking Session](index.md#cancel-booking-session)           | Cancel a booking session.  |

### `create_booking_session`

Maps to the [Create Booking Session](index.md#create-booking-session) operation.

#### Input Schema

{{ schema_fields('booking_create_req', 'lodging/booking/mcp') }}

#### Output Schema

{{ schema_fields('booking_resp', 'lodging/booking/mcp') }}

#### Example

=== "Request"

    <!-- ucp:example schema=lodging/booking op=create direction=request extract=$.params.arguments.booking -->
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
            "accommodation": {
              "id": "hotel_123"
            },
            "room_rates": [
              {
                "id": "rt_luxury_queen__rp_avg_base_rate",
                "room_type": {
                  "id": "rt_luxury_queen"
                },
                "rate_plan": {
                  "id": "rp_avg_base_rate"
                },
                "occupancy": {
                  "adults": 2,
                  "total": 2
                }
              }
            ],
            "itinerary": {
              "start_date": "2026-07-15",
              "end_date": "2026-07-21"
            }
          }
        }
      }
    }
    ```

=== "Response"

    <!-- ucp:example schema=lodging/booking op=read direction=response extract=$.result.structuredContent -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "result": {
        "structuredContent": {
          "ucp": {
            "version": "{{ ucp_version }}",
            "capabilities": {
              "dev.ucp.lodging.booking": [
                {"version": "{{ ucp_version }}"}
              ]
            },
            "payment_handlers": {
              "com.example.vendor.delegate_payment": [
                {"id": "handler_1", "version": "{{ ucp_version }}", "available_instruments": [{"type": "card"}], "config": {}}
              ]
            }
          },
          "id": "booking_123",
          "status": "ready_for_complete",
          "accommodation": {
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
          "room_rates": [
            {
              "id": "rt_luxury_queen__rp_avg_base_rate",
              "room_type": {
                "id": "rt_luxury_queen",
                "title": "Luxury Queen Room with Two Queen Beds",
                "capacity": {
                  "adults": 2,
                  "children": [
                    {
                      "from_age": 0,
                      "to_age": 5,
                      "total": 1
                    },
                    {
                      "from_age": 6,
                      "to_age": 16,
                      "total": 1
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
              "totals": [
                {
                  "type": "subtotal",
                  "amount": 55000
                },
                {
                  "type": "tax",
                  "amount": 5500
                },
                {
                  "type": "total",
                  "amount": 60500
                }
              ]
            }
          ],
          "itinerary": {
            "start_date": "2026-07-15",
            "end_date": "2026-07-21"
          },
          "currency": "USD",
          "totals": [
            {
              "type": "subtotal",
              "amount": 385000
            },
            {
              "type": "tax",
              "amount": 38500
            },
            {
              "type": "fee",
              "display_text": "Booking fee",
              "amount": 1000
            },
            {
              "type": "total",
              "amount": 424500
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

=== "Error Response"

    Selected room is no longer available — no booking session resource is created:

    <!-- ucp:example schema=common/types/error_response op=read direction=response extract=$.result.structuredContent -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "result": {
        "structuredContent": {
          "ucp": {
            "version": "{{ ucp_version }}",
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

Maps to the [Get Booking Session](index.md#get-booking-session) operation.

#### Input Schema

* `id` (String): **Required**. The ID of the booking session to retrieve.

#### Output Schema

{{ schema_fields('booking_resp', 'lodging/booking/mcp') }}

### `update_booking_session`

Maps to the [Update Booking](index.md#update-booking-session) operation.

#### Input Schema

* `id` (String): **Required**. The ID of the booking session to update.

{{ schema_fields('booking_update_req', 'lodging/booking/mcp') }}

#### Output Schema

{{ schema_fields('booking_resp', 'lodging/booking/mcp') }}

#### Example

=== "Request"

    <!-- ucp:example schema=lodging/booking op=update direction=request extract=$.params.arguments.booking -->
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
            "accommodation": {
              "id": "hotel_123"
            },
            "room_rates": [
              {
                "id": "rt_luxury_queen__rp_avg_base_rate",
                "room_type": {
                  "id": "rt_luxury_queen"
                },
                "rate_plan": {
                  "id": "rp_avg_base_rate"
                },
                "occupancy": {
                  "adults": 2,
                  "total": 2
                },
                "guest_assignments": [
                  {
                    "guest_id": "gst_01",
                    "role": "primary_guest"
                  },
                  {
                    "guest_id": "gst_02",
                    "role": "additional_guest"
                  }
                ]
              }
            ],
            "itinerary": {
              "start_date": "2026-07-15",
              "end_date": "2026-07-21"
            },
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

=== "Response"

    <!-- ucp:example schema=lodging/booking op=read direction=response extract=$.result.structuredContent -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 3,
      "result": {
        "structuredContent": {
          "ucp": {
            "version": "{{ ucp_version }}",
            "capabilities": {
              "dev.ucp.lodging.booking": [
                {"version": "{{ ucp_version }}"}
              ]
            },
            "payment_handlers": {
              "com.example.vendor.delegate_payment": [
                {"id": "handler_1", "version": "{{ ucp_version }}", "available_instruments": [{"type": "card"}], "config": {}}
              ]
            }
          },
          "id": "booking_123",
          "status": "ready_for_complete",
          "accommodation": {
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
          "room_rates": [
            {
              "id": "rt_luxury_queen__rp_avg_base_rate",
              "room_type": {
                "id": "rt_luxury_queen",
                "title": "Luxury Queen Room with Two Queen Beds",
                "capacity": {
                  "adults": 2,
                  "children": [
                    {
                      "from_age": 0,
                      "to_age": 5,
                      "total": 1
                    },
                    {
                      "from_age": 6,
                      "to_age": 16,
                      "total": 1
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
              "guest_assignments": [
                {
                  "guest_id": "gst_01",
                  "role": "primary_guest"
                },
                {
                  "guest_id": "gst_02",
                  "role": "additional_guest"
                }
              ],
              "totals": [
                {
                  "type": "subtotal",
                  "amount": 55000
                },
                {
                  "type": "tax",
                  "amount": 5500
                },
                {
                  "type": "total",
                  "amount": 60500
                }
              ]
            }
          ],
          "itinerary": {
            "start_date": "2026-07-15",
            "end_date": "2026-07-21"
          },
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
              "amount": 385000
            },
            {
              "type": "tax",
              "amount": 38500
            },
            {
              "type": "fee",
              "display_text": "Booking fee",
              "amount": 1000
            },
            {
              "type": "total",
              "amount": 424500
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

Maps to the [Complete Booking Session](index.md#complete-booking-session) operation.

#### Input Schema

* `id` (String): **Required**. The ID of the booking session.

{{ schema_fields('booking_complete_req', 'lodging/booking/mcp') }}

#### Output Schema

{{ schema_fields('booking_resp', 'lodging/booking/mcp') }}

**Note:** Response **MUST** include a `confirmation` object if completion succeeds.

#### Example

=== "Request"

    <!-- ucp:example schema=lodging/booking op=complete direction=request extract=$.params.arguments.booking -->
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

=== "Response"

    <!-- ucp:example schema=lodging/booking op=read direction=response extract=$.result.structuredContent -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 2,
      "result": {
        "structuredContent": {
         "ucp": {
            "version": "{{ ucp_version }}",
            "capabilities": {
              "dev.ucp.lodging.booking": [
                {"version": "{{ ucp_version }}"}
              ]
            },
            "payment_handlers": {
              "com.example.vendor.delegate_payment": [
                {"id": "handler_1", "version": "{{ ucp_version }}", "available_instruments": [{"type": "card"}], "config": {}}
              ]
            }
          },
          "id": "booking_123",
          "status": "completed",
          "accommodation": {
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
          "room_rates": [
            {
              "id": "rt_luxury_queen__rp_avg_base_rate",
              "room_type": {
                "id": "rt_luxury_queen",
                "title": "Luxury Queen Room with Two Queen Beds",
                "capacity": {
                  "adults": 2,
                  "children": [
                    {
                      "from_age": 0,
                      "to_age": 5,
                      "total": 1
                    },
                    {
                      "from_age": 6,
                      "to_age": 16,
                      "total": 1
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
              "guest_assignments": [
                {
                  "guest_id": "gst_01",
                  "role": "primary_guest"
                },
                {
                  "guest_id": "gst_02",
                  "role": "additional_guest"
                }
              ],
              "totals": [
                {
                  "type": "subtotal",
                  "amount": 55000
                },
                {
                  "type": "tax",
                  "amount": 5500
                },
                {
                  "type": "total",
                  "amount": 60500
                }
              ]
            }
          ],
          "itinerary": {
            "start_date": "2026-07-15",
            "end_date": "2026-07-21"
          },
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
              "amount": 385000
            },
            {
              "type": "tax",
              "amount": 38500
            },
            {
              "type": "fee",
              "display_text": "Booking fee",
              "amount": 1000
            },
            {
              "type": "total",
              "amount": 424500
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

Maps to the [Cancel Booking Session](index.md#cancel-booking-session) operation.

#### Input Schema

* `id` (String): **Required**. The ID of the booking session.

#### Output Schema

{{ schema_fields('booking_resp', 'lodging/booking/mcp') }}

**Note:** Response **MUST** include `"status": "canceled"` if cancellation succeeds.

## Error Handling

UCP distinguishes between protocol errors and business outcomes. See the
[Core Specification](../../overview/index.md#error-handling) for the complete error code
registry and transport binding examples.

* **Protocol errors**: Transport-level failures (authentication, rate limiting,
    unavailability) that prevent request processing. Returned as JSON-RPC
    `error` with code `-32000` (or `-32001` for discovery errors).
* **Business outcomes**: Application-level results from successful request
    processing, returned as JSON-RPC `result` with UCP envelope and `messages`.

### Business Outcomes

Business outcomes (including errors like unavailable merchandise) are returned
as JSON-RPC `result` with `structuredContent` containing the UCP envelope and
`messages`:

<!-- ucp:example schema=lodging/booking op=read direction=response extract=$.result.structuredContent -->
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "structuredContent": {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.lodging.booking": [
            {"version": "{{ ucp_version }}"}
          ]
        },
        "payment_handlers": {
          "com.example.vendor.delegate_payment": [
            {"id": "handler_1", "version": "{{ ucp_version }}", "available_instruments": [{"type": "card"}], "config": {}}
          ]
        }
      },
      "id": "booking_123",
      "status": "incomplete",
      "accommodation": {
        "id": "hotel_123",
        "name": "Beautiful Scenery Hotel"
      },
      "room_rates": [
        {
          "id": "rt_luxury_queen__rp_avg_base_rate",
          "room_type": {
            "id": "rt_luxury_queen",
            "title": "Luxury Queen Room with Two Queen Beds",
            "capacity": {
              "adults": 2,
              "children": [
                {
                  "from_age": 0,
                  "to_age": 5,
                  "total": 1
                },
                {
                  "from_age": 6,
                  "to_age": 16,
                  "total": 1
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
          }
        }
      ],
      "itinerary": {
        "start_date": "2026-07-15",
        "end_date": "2026-07-21"
      },
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
          "path": "$.room_rates[0]",
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

For `create_booking_session`, when no booking session can be created,
JSON-RPC `result` with `structuredContent` containing the UCP envelope and `messages`:

<!-- ucp:example schema=common/types/error_response op=read direction=response extract=$.result.structuredContent -->
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "structuredContent": {
      "ucp": { "version": "{{ ucp_version }}", "status": "error" },
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

Platforms **SHOULD** authenticate agents when using MCP transport. When using
HTTP Message Signatures, all booking operations follow the
[Message Signatures](../../signatures.md) specification.

### Request Signing

UCP's MCP transport uses **streamable HTTP**, allowing the same RFC 9421
signature mechanism as REST. The signature is applied at the HTTP layer:

| Header                   | Required | Description                              |
| :----------------------- | :------- | :--------------------------------------- |
| `Signature-Input`        | Yes      | Describes signed components              |
| `Signature`              | Yes      | Contains the signature value             |
| `Content-Digest`         | Yes      | SHA-256 hash of request body             |
| `UCP-Agent`              | Yes      | Signer identity (profile URL)            |
| `Idempotency-Key`        | Yes      | Unique key for replay protection         |

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

The `Content-Digest` binds the JSON-RPC body to the signature. No JSON
canonicalization is required.

See [Message Signatures - MCP Transport](../../signatures.md#mcp-transport)
for details.

### Response Signing

Response signatures are **RECOMMENDED** for:

* `complete_booking_session` responses (booking confirmation)

Response signatures are **OPTIONAL** for:

* `create_booking_session`, `get_booking_session`, `update_booking_session`, `cancel_booking_session`

**Example Signed Response:**

```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Digest: sha-256=:Y5fK8nLmPqRsT3vWxYzAbCdEfGhIjKlMnO...:
Signature-Input: sig1=("@status" "content-digest" "content-type");keyid="business-2026"
Signature: sig1=:MFQCIH7kL9nM2oP5qR8sT1uV4wX6yZaB3cD...:

{"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"..."}],"structuredContent":{"id":"booking_123","status":"completed", ...}}}
```

See [Message Signatures - REST Response Signing](../../signatures.md#rest-response-signing)
for the signing algorithm (identical for MCP over HTTP).

## Conformance

A conforming MCP transport implementation **MUST**:

1. Implement JSON-RPC 2.0 protocol correctly.
2. Provide all core booking tools defined in this specification.
3. Return errors per the [Core Specification](../../overview/index.md#error-handling).
4. Return business outcomes as JSON-RPC `result` with UCP envelope and
    `messages` array.
5. Validate tool inputs against UCP schemas.
6. Support HTTP transport with streaming.

A conforming implementation **SHOULD**:

1. Authenticate agents using one of the supported mechanisms (API keys, OAuth,
    mTLS, or HTTP Message Signatures per [Message Signatures](../../signatures.md)).
2. Verify authentication on incoming requests before processing.

## Implementation

UCP operations are defined using [OpenRPC](https://open-rpc.org/) (JSON-RPC
schema format). The [MCP specification](https://modelcontextprotocol.io/)
requires all tool invocations to use a `tools/call` method with the operation
name and arguments wrapped in `params`. Implementers **MUST** apply this
transformation:

| OpenRPC  | MCP                |
|:---------|:-------------------|
| `method` | `params.name`      |
| `params` | `params.arguments` |

**Param conventions:**

* `meta` contains request metadata
* `id` identifies the target resource (path parameter equivalent)
* `booking` contains the domain payload (body equivalent)
