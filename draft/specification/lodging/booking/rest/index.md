# Booking Capability - REST Binding

This document specifies the REST binding for the [Booking Capability](http://ucp.dev/draft/specification/lodging/booking/index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise REST transport availability through their UCP profile at `/.well-known/ucp`.

```json
{
  "ucp": {
    "version": "draft",
    "services": {
      "dev.ucp.lodging": [
        {
          "version": "draft",
          "spec": "https://ucp.dev/draft/specification/overview",
          "transport": "rest",
          "schema": "https://ucp.dev/draft/services/lodging/rest.openapi.json",
          "endpoint": "https://business.example.com/ucp/v1"
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

### Base URL

All UCP REST endpoints are relative to the business's base URL, which is discovered through the UCP profile at `/.well-known/ucp`. The endpoint for the booking capability is defined in the `rest.endpoint` field of the business profile.

### Content Types

- **Request**: `application/json`
- **Response**: `application/json`

All request and response bodies **MUST** be valid JSON as specified in [RFC 8259](https://tools.ietf.org/html/rfc8259).

### Transport Security

All REST endpoints **MUST** be served over HTTPS with minimum TLS version 1.3.

## Operations

| Operation                                                                                                | Method | Endpoint                          | Description               |
| -------------------------------------------------------------------------------------------------------- | ------ | --------------------------------- | ------------------------- |
| [Create Booking Session](http://ucp.dev/draft/specification/lodging/booking/#create-booking-session)     | `POST` | `/booking-sessions`               | Create a booking session. |
| [Get Booking Session](http://ucp.dev/draft/specification/lodging/booking/#get-booking-session)           | `GET`  | `/booking-sessions/{id}`          | Get a booking session.    |
| [Update Booking Session](http://ucp.dev/draft/specification/lodging/booking/#update-booking-session)     | `PUT`  | `/booking-sessions/{id}`          | Update a booking session. |
| [Complete Booking Session](http://ucp.dev/draft/specification/lodging/booking/#complete-booking-session) | `POST` | `/booking-sessions/{id}/complete` | Complete booking.         |
| [Cancel Booking Session](http://ucp.dev/draft/specification/lodging/booking/#cancel-booking-session)     | `POST` | `/booking-sessions/{id}/cancel`   | Cancel a booking session. |

## Examples

### Create Booking Session

#### Single-stay Booking

```json
POST /booking-sessions HTTP/1.1
UCP-Agent: profile="https://platform.example/profile"
Content-Type: application/json
...other required headers...

{
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
```

```json
HTTP/1.1 201 Created
Content-Type: application/json

{
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
}
```

Selected room is no longer available — no booking session resource is created:

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
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
}
```

#### Multi-stay Booking

```json
POST /booking-sessions HTTP/1.1
UCP-Agent: profile="https://platform.example/profile"
Content-Type: application/json
...other required headers...

{
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
    },
    {
      "id": "stay_standard_king__rp_avg_base_rate",
      "accommodation_type": {
        "id": "rt_standard_king"
      },
      "rate_plan": {
        "id": "rp_avg_base_rate"
      },
      "occupancy": {
        "adults": 1,
        "total": 1
      },
      "stay_dates": {
        "start_date": "2026-07-15",
        "end_date": "2026-07-21"
      }
    }
  ]
}
```

```json
HTTP/1.1 201 Created
Content-Type: application/json

{
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
  "id": "booking_124",
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
    },
    {
      "id": "stay_standard_king__rp_avg_base_rate",
      "accommodation_type": {
        "id": "rt_standard_king",
        "title": "Standard King Room",
        "capacity": {
          "adults": 2,
          "total": 2
        }
      },
      "rate_plan": {
        "id": "rp_avg_base_rate",
        "title": "Best Available Rate"
      },
      "occupancy": {
        "adults": 1,
        "total": 1
      },
      "stay_dates": {
        "start_date": "2026-07-15",
        "end_date": "2026-07-21"
      },
      "totals": [
        {
          "type": "subtotal",
          "amount": 270000
        },
        {
          "type": "tax",
          "amount": 27000
        },
        {
          "type": "total",
          "amount": 297000
        }
      ]
    }
  ],
  "currency": "USD",
  "totals": [
    {
      "type": "subtotal",
      "amount": 600000
    },
    {
      "type": "tax",
      "amount": 60000
    },
    {
      "type": "fee",
      "display_text": "Booking fee",
      "amount": 1000
    },
    {
      "type": "total",
      "amount": 661000
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
  "continue_url": "https://business.example.com/booking-sessions/booking_124",
  "expires_at": "2026-06-01T18:30:00Z"
}
```

### Update Booking Session

This is a full replacement operation. The Platform **MUST** send the entire booking session resource, including any data updates to write-only fields; the supplied resource replaces the existing booking session state. The Platform **MUST NOT** start a new Update operation while the booking session is `complete_in_progress`. Duplicate requests remain subject to [Replay Protection](http://ucp.dev/draft/specification/signatures/#replay-protection). If the Business receives a new Update request in that state, it **MUST** leave the booking session unchanged and return the current booking session with a recoverable error message.

All fields in `guests`, `booker`, `travel_purpose`, and `stays[].guest_assignments` are optional, allowing the Platform to progressively build the booking session across multiple calls. Outside `complete_in_progress`, each Update replaces the entire booking session, so the Platform **MUST** include all previously set fields it intends to retain.

If businesses have specific logic to enforce field existence in `guests`, `booker`, `guest_assignments`, or addresses (i.e. `billing_address`), this is the right place to set these expectations via `messages`.

```json
PUT /booking-sessions/{id} HTTP/1.1
UCP-Agent: profile="https://platform.example/profile"
Content-Type: application/json
...other required headers...

{
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
  // New data introduced in the update call.
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
  "booker": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone_number": "+14155559876",
    "birthdate": "1980-08-26",
    "address": {
      "street_address": "1600 Amphitheatre Pkwy",
      "address_locality": "Mountain View",
      "address_region": "CA",
      "address_country": "US",
      "postal_code": "94043"
    }
  },
  "travel_purpose": "leisure"
}
```

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
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
  "booker": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone_number": "+14155559876",
    "birthdate": "1980-08-26",
    "address": {
      "street_address": "1600 Amphitheatre Pkwy",
      "address_locality": "Mountain View",
      "address_region": "CA",
      "address_country": "US",
      "postal_code": "94043"
    }
  },
  "travel_purpose": "leisure",
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
}
```

### Complete Booking Session

```json
POST /booking-sessions/{id}/complete
UCP-Agent: profile="https://platform.example/profile"
Content-Type: application/json
...other required headers...

{
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
```

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
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
  "booker": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone_number": "+14155559876",
    "birthdate": "1980-08-26",
    "address": {
      "street_address": "1600 Amphitheatre Pkwy",
      "address_locality": "Mountain View",
      "address_region": "CA",
      "address_country": "US",
      "postal_code": "94043"
    }
  },
  "travel_purpose": "leisure",
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
  // Booking confirmation that MUST be set in the response.
  "confirmation": {
    "id": "confirmation_123",
    "label": "CON123AZ",
    "pincode": "1234"
  },
  "payment": {...},
  "signals": {...}
}
```

### Get Booking Session

```json
GET /booking-sessions/{id}
UCP-Agent: profile="https://platform.example/profile"
Content-Type: application/json
...other required headers...

{}
```

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
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
  "booker": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone_number": "+14155559876",
    "birthdate": "1980-08-26",
    "address": {
      "street_address": "1600 Amphitheatre Pkwy",
      "address_locality": "Mountain View",
      "address_region": "CA",
      "address_country": "US",
      "postal_code": "94043"
    }
  },
  "travel_purpose": "leisure",
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
}
```

### Cancel Booking Session

```json
POST /booking-sessions/{id}/cancel
UCP-Agent: profile="https://platform.example/profile"
Content-Type: application/json
...other required headers...

{}
```

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
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
  // Status is updated upon a successful cancellation.
  "status": "canceled",
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
  "booker": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone_number": "+14155559876",
    "birthdate": "1980-08-26",
    "address": {
      "street_address": "1600 Amphitheatre Pkwy",
      "address_locality": "Mountain View",
      "address_region": "CA",
      "address_country": "US",
      "postal_code": "94043"
    }
  },
  "travel_purpose": "leisure",
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
  "continue_url": "https://business.example.com/booking-sessions/booking_123"
}
```

## HTTP Headers

The following headers are defined for the HTTP binding and apply to all operations unless otherwise noted.

**Request Headers**

| Header            | Required | Description                                                                                                                                                                                                                                                   |
| ----------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Authorization`   | No       | Should contain oauth token representing the following 2 schemes: 1. Platform self authenticating (client_credentials). 2. Platform authenticating on behalf of end user (authorization_code).                                                                 |
| `X-API-Key`       | No       | Authenticates the platform with a reusable api key allocated to the platform by the business.                                                                                                                                                                 |
| `Signature`       | No       | RFC 9421 HTTP Message Signature. Required when using HTTP Message Signatures for authentication. Format: `sig1=:<base64-signature>:`.                                                                                                                         |
| `Signature-Input` | No       | RFC 9421 Signature-Input header. Required when using HTTP Message Signatures for authentication. Format: `sig1=("@method" "@path" ...);created=<timestamp>;keyid="<key-id>"`.                                                                                 |
| `Content-Digest`  | No       | Body digest per RFC 9530. Format: `sha-256=:<base64-digest>:`.                                                                                                                                                                                                |
| `Idempotency-Key` | **Yes**  | Ensures duplicate operations don't happen during retries.                                                                                                                                                                                                     |
| `Request-Id`      | **Yes**  | For tracing the requests across network layers and components.                                                                                                                                                                                                |
| `User-Agent`      | No       | Identifies the user agent string making the call.                                                                                                                                                                                                             |
| `UCP-Agent`       | **Yes**  | Identifies the UCP agent making the call. All requests MUST include the UCP-Agent header containing the signer's profile URI using RFC 8941 Dictionary syntax. The URL MUST point to /.well-known/ucp. Format: profile="https://example.com/.well-known/ucp". |
| `Content-Type`    | No       | Representation Metadata. Tells the receiver what the data in the message body actually is.                                                                                                                                                                    |
| `Accept`          | No       | Content Negotiation. The client tells the server what data formats it is capable of understanding.                                                                                                                                                            |
| `Accept-Language` | No       | Localization. Tells the receiver the user's preferred natural languages, often with "weights" or priorities.                                                                                                                                                  |
| `Accept-Encoding` | No       | Compression. The client tells the server which content-codings it supports, usually for compression.                                                                                                                                                          |

### Specific Header Requirements

- **UCP-Agent**: All requests **MUST** include the `UCP-Agent` header containing the platform profile URI using Dictionary Structured Field syntax ([RFC 8941](https://datatracker.ietf.org/doc/html/rfc8941)). Format: `profile="https://platform.example/profile"`.
- **Idempotency-Key**: Operations that modify state **SHOULD** support idempotency. When provided, the server **MUST**:
  1. Store the key with the operation result for at least 24 hours.
  1. Return the cached result for duplicate keys whose request body matches the original.
  1. Return `409 Conflict` if the key is reused with a mismatched body. See [Message Signatures — Idempotency Key Requirements](http://ucp.dev/draft/specification/signatures/#replay-protection) for the full payload-matching contract.

## Protocol Mechanics

### Status Codes

UCP uses standard HTTP status codes to indicate the success or failure of an API request.

| Status Code                 | Description                                                                        |
| --------------------------- | ---------------------------------------------------------------------------------- |
| `200 OK`                    | The request was successful.                                                        |
| `201 Created`               | The resource was successfully created.                                             |
| `400 Bad Request`           | The request was invalid or cannot be served.                                       |
| `401 Unauthorized`          | Authentication is required and has failed or has not been provided.                |
| `403 Forbidden`             | The request is authenticated but the user does not have the necessary permissions. |
| `409 Conflict`              | The request could not be completed due to a conflict (e.g., idempotent key reuse). |
| `422 Unprocessable Entity`  | The profile content is malformed (discovery failure).                              |
| `424 Failed Dependency`     | The profile URL is valid but fetch failed (discovery failure).                     |
| `429 Too Many Requests`     | Rate limit exceeded.                                                               |
| `503 Service Unavailable`   | Temporary unavailability.                                                          |
| `500 Internal Server Error` | An unexpected condition was encountered on the server.                             |

### Error Responses

See the [Core Specification](http://ucp.dev/draft/specification/overview/#error-handling) for the complete error code registry and transport binding examples.

- **Protocol errors**: Return appropriate HTTP status code (401, 403, 409, 429, 503) with JSON body containing `code` and `content`.
- **Business outcomes**: Return HTTP 200 with UCP envelope and `messages` array.

#### Business Outcomes

Business outcomes (including errors like invalid guest info) are returned with HTTP 200 and the UCP envelope containing `messages`:

```json
{
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
}
```

For `create_booking_session`, when no booking session can be created, business **MUST** return HTTP 200 and the UCP envelope containing `messages`

```json
{
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
}
```

## Message Signing

Platforms **MAY** choose among authentication mechanisms (API keys, OAuth, mTLS, HTTP Message Signatures). When using HTTP Message Signatures, booking operations follow the [Message Signatures](http://ucp.dev/draft/specification/signatures/index.md) specification.

### Request Signing

When HTTP Message Signatures are used, requests **MUST** include valid `Signature-Input` and `Signature` headers (and `Content-Digest` when a body is present) per RFC 9421:

| Header            | Required | Description                      |
| ----------------- | -------- | -------------------------------- |
| `Signature-Input` | Yes      | Describes signed components      |
| `Signature`       | Yes      | Contains the signature value     |
| `Content-Digest`  | Cond.\*  | SHA-256 hash of request body     |
| `UCP-Agent`       | Yes      | Signer identity (profile URL)    |
| `Idempotency-Key` | Yes      | Unique key for replay protection |

\* Required for requests with a body (POST, PUT)

**Example Signed Request:**

```http
POST /booking-sessions HTTP/1.1
Host: business.example.com
Content-Type: application/json
UCP-Agent: profile="https://platform.example/.well-known/ucp"
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Digest: sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:
Signature-Input: sig1=("@method" "@authority" "@path" "idempotency-key" "content-digest" "content-type");keyid="platform-2025"
Signature: sig1=:MEUCIQDTxNq8h7LGHpvVZQp1iHkFp9+3N8Mxk2zH1wK4YuVN8w...:

{"payment":{...}, ...}
```

See [Message Signatures - REST Request Signing](http://ucp.dev/draft/specification/signatures/#rest-request-signing) for the complete signing algorithm.

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

{"id":"booking_123","status":"completed","confirmation":{...}}
```

See [Message Signatures - REST Response Signing](http://ucp.dev/draft/specification/signatures/#rest-response-signing) for the complete signing algorithm.

## Security Considerations

### Authentication

Authentication is optional and depends on business requirements. When authentication is required, the REST transport **MAY** use:

1. **Open API**: No authentication required for public operations.
1. **API Keys**: Via `X-API-Key` header.
1. **OAuth 2.0**: Via `Authorization: Bearer {token}` header. Identifies the platform for agent-authenticated access, or both platform and user for user-authenticated access (see [Identity Linking](http://ucp.dev/draft/specification/common/identity-linking/index.md)).
1. **Mutual TLS**: For high-security environments.
1. **HTTP Message Signatures**: Per [RFC 9421](https://www.rfc-editor.org/rfc/rfc9421) (see [Message Signing](#message-signing) above).

Businesses **MAY** require authentication for some operations while leaving others open (e.g., public booking without authentication).
