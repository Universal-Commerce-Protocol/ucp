# Checkout Capability - REST Binding

This document specifies the REST binding for the [Food Checkout Capability](http://ucp.dev/draft/specification/food/checkout/index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise REST transport availability through their UCP profile at `/.well-known/ucp`.

```json
{
  "ucp": {
    "version": "draft",
    "services": {
      "dev.ucp.food": [
        {
          "version": "draft",
          "spec": "https://ucp.dev/draft/specification/overview",
          "transport": "rest",
          "schema": "https://ucp.dev/draft/services/food/rest.openapi.json",
          "endpoint": "https://food.example.com/ucp"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.food.checkout": [
        {
          "version": "draft",
          "spec": "https://ucp.dev/draft/specification/food/checkout",
          "schema": "https://ucp.dev/draft/schemas/food/checkout.json"
        }
      ],
      "dev.ucp.food.fulfillment": [
        {
          "version": "draft",
          "extends": "dev.ucp.food.checkout",
          "spec": "https://ucp.dev/draft/specification/food/extensions/fulfillment",
          "schema": "https://ucp.dev/draft/schemas/food/fulfillment.json"
        }
      ],
      "dev.ucp.food.tip": [
        {
          "version": "draft",
          "extends": "dev.ucp.food.checkout",
          "spec": "https://ucp.dev/draft/specification/food/extensions/tip",
          "schema": "https://ucp.dev/draft/schemas/food/tip.json"
        }
      ]
    },
    "payment_handlers": {
      "com.example.processor_tokenizer": [
        {
          "id": "processor_tokenizer_1",
          "version": "draft",
          "spec": "https://example.com/specs/processor-tokenizer",
          "schema": "https://example.com/schemas/processor-tokenizer-config.json",
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

All UCP REST endpoints are relative to the Business's base URL, which is discovered through the UCP profile at `/.well-known/ucp`. The endpoint for the food checkout capability is defined in the `rest.endpoint` field of the business profile.

### Content Types

- **Request**: `application/json`
- **Response**: `application/json`

All request and response bodies **MUST** be valid JSON as specified in [RFC 8259](https://tools.ietf.org/html/rfc8259).

### Transport Security

All REST endpoints **MUST** be served over HTTPS with minimum TLS version 1.3.

## Operations

| Operation                                                                                | Method | Endpoint                           | Description                |
| ---------------------------------------------------------------------------------------- | ------ | ---------------------------------- | -------------------------- |
| [Create Checkout](http://ucp.dev/draft/specification/food/checkout/#create-checkout)     | `POST` | `/checkout-sessions`               | Create a checkout session. |
| [Get Checkout](http://ucp.dev/draft/specification/food/checkout/#get-checkout)           | `GET`  | `/checkout-sessions/{id}`          | Get a checkout session.    |
| [Update Checkout](http://ucp.dev/draft/specification/food/checkout/#update-checkout)     | `PUT`  | `/checkout-sessions/{id}`          | Update a checkout session. |
| [Complete Checkout](http://ucp.dev/draft/specification/food/checkout/#complete-checkout) | `POST` | `/checkout-sessions/{id}/complete` | Place the order.           |
| [Cancel Checkout](http://ucp.dev/draft/specification/food/checkout/#cancel-checkout)     | `POST` | `/checkout-sessions/{id}/cancel`   | Cancel a checkout session. |

## Examples

The examples below follow one order from start to finish: two customized pizzas and a salad from Luigi's, delivered ASAP with an 18% tip.

### Create Checkout

The Platform sends the establishment and the configured dishes. The Business prices them and asks for a fulfillment method.

```json
POST /checkout-sessions HTTP/1.1
UCP-Agent: profile="https://platform.example/profile"
Content-Type: application/json
...other required headers...

{
  "food_establishment": {
    "id": "est_luigis_01"
  },
  "line_items": [
    {
      "quantity": 2,
      "dish": {
        "id": "dish_margherita_12"
      },
      "modifications": [
        {"id": "mod_extra_mozzarella"},
        {"id": "mod_fresh_basil"}
      ],
      "note": "Well done crust, please"
    },
    {
      "quantity": 1,
      "dish": {
        "id": "dish_caesar"
      },
      "note": "Dressing on the side"
    }
  ],
  "buyer": {
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane.doe@example.com",
    "phone_number": "+14155550199"
  }
}
```

```json
HTTP/1.1 201 Created
Content-Type: application/json

{
  "ucp": {
    "version": "draft",
    "capabilities": {
      "dev.ucp.food.checkout": [
        {"version": "draft"}
      ],
      "dev.ucp.food.fulfillment": [
        {"version": "draft", "extends": "dev.ucp.food.checkout"}
      ],
      "dev.ucp.food.tip": [
        {"version": "draft", "extends": "dev.ucp.food.checkout"}
      ]
    },
    "payment_handlers": {
      "com.example.processor_tokenizer": [
        {"id": "processor_tokenizer_1", "version": "draft", "available_instruments": [{"type": "card"}], "config": {}}
      ]
    }
  },
  "id": "chk_food_7187",
  "status": "incomplete",
  "currency": "USD",
  "food_establishment": {
    "id": "est_luigis_01",
    "name": "Luigi's Artisan Pizzeria",
    "address": {
      "street_address": "210 University Ave",
      "address_locality": "Palo Alto",
      "address_region": "CA",
      "postal_code": "94301",
      "address_country": "US"
    },
    "media": [
      {"type": "image", "url": "https://food.example.com/img/luigis.jpg", "alt_text": "Luigi's storefront"}
    ]
  },
  "buyer": {
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane.doe@example.com",
    "phone_number": "+14155550199"
  },
  "line_items": [
    {
      "id": "li_1",
      "quantity": 2,
      "dish": {
        "id": "dish_margherita_12",
        "title": "Margherita Pizza (12\")",
        "price": 1600,
        "media": [
          {"type": "image", "url": "https://food.example.com/img/margherita.jpg"}
        ]
      },
      "modifications": [
        {"id": "mod_extra_mozzarella", "title": "Extra Mozzarella", "price": 200},
        {"id": "mod_fresh_basil", "title": "Fresh Basil", "price": 150}
      ],
      "note": "Well done crust, please",
      "totals": [
        {"type": "subtotal", "amount": 3900},
        {"type": "total", "amount": 3900}
      ]
    },
    {
      "id": "li_2",
      "quantity": 1,
      "dish": {
        "id": "dish_caesar",
        "title": "Caesar Salad",
        "price": 1100
      },
      "note": "Dressing on the side",
      "totals": [
        {"type": "subtotal", "amount": 1100},
        {"type": "total", "amount": 1100}
      ]
    }
  ],
  "fulfillment": {
    "available_methods": [
      {
        "type": "delivery",
        "fulfillable_on": "2026-04-10T18:25:00-07:00",
        "scheduling": "asap_and_scheduled"
      },
      {
        "type": "pickup",
        "fulfillable_on": "2026-04-10T18:15:00-07:00",
        "scheduling": "asap_and_scheduled"
      }
    ]
  },
  "tip": {
    "options": [
      {"id": "tip_15", "unit": "percentage", "amount": 15},
      {"id": "tip_18", "unit": "percentage", "amount": 18},
      {"id": "tip_20", "unit": "percentage", "amount": 20}
    ]
  },
  "totals": [
    {"type": "subtotal", "display_text": "Subtotal", "amount": 5000},
    {"type": "tax", "display_text": "Estimated Tax", "amount": 438},
    {"type": "total", "display_text": "Estimated Total", "amount": 5438}
  ],
  "messages": [
    {
      "type": "error",
      "code": "missing",
      "path": "$.fulfillment.methods",
      "content": "Choose delivery or pickup.",
      "severity": "recoverable"
    }
  ],
  "links": [
    {"type": "privacy_policy", "url": "https://food.example.com/privacy"},
    {"type": "terms_of_service", "url": "https://food.example.com/terms"}
  ],
  "continue_url": "https://food.example.com/checkout/chk_food_7187",
  "expires_at": "2026-04-11T00:00:00Z"
}
```

### Update Checkout

The Platform sends the full writable state plus a delivery address and a tip. The Business adds delivery options, drop-off preferences, fees, and the resolved tip.

```json
PUT /checkout-sessions/chk_food_7187 HTTP/1.1
UCP-Agent: profile="https://platform.example/profile"
Content-Type: application/json
...other required headers...

{
  "food_establishment": {
    "id": "est_luigis_01"
  },
  "line_items": [
    {
      "id": "li_1",
      "quantity": 2,
      "dish": {
        "id": "dish_margherita_12"
      },
      "modifications": [
        {"id": "mod_extra_mozzarella"},
        {"id": "mod_fresh_basil"}
      ],
      "note": "Well done crust, please"
    },
    {
      "id": "li_2",
      "quantity": 1,
      "dish": {
        "id": "dish_caesar"
      },
      "note": "Dressing on the side"
    }
  ],
  "buyer": {
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane.doe@example.com",
    "phone_number": "+14155550199"
  },
  "fulfillment": {
    "methods": [
      {
        "type": "delivery",
        "destination": {
          "type": "delivery_address",
          "address": {
            "street_address": "450 Serra Mall",
            "extended_address": "Apt 3B",
            "address_locality": "Stanford",
            "address_region": "CA",
            "postal_code": "94305",
            "address_country": "US"
          }
        },
        "notes": "Gate code #4210, second floor"
      }
    ]
  },
  "tip": {
    "selected_option_id": "tip_18"
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
      "dev.ucp.food.checkout": [
        {"version": "draft"}
      ],
      "dev.ucp.food.fulfillment": [
        {"version": "draft", "extends": "dev.ucp.food.checkout"}
      ],
      "dev.ucp.food.tip": [
        {"version": "draft", "extends": "dev.ucp.food.checkout"}
      ]
    },
    "payment_handlers": {
      "com.example.processor_tokenizer": [
        {"id": "processor_tokenizer_1", "version": "draft", "available_instruments": [{"type": "card"}], "config": {}}
      ]
    }
  },
  "id": "chk_food_7187",
  "status": "ready_for_complete",
  "currency": "USD",
  "food_establishment": {...},
  "buyer": {...},
  "line_items": [...],
  "fulfillment": {
    "available_methods": [
      {
        "type": "delivery",
        "fulfillable_on": "2026-04-10T18:25:00-07:00",
        "scheduling": "asap_and_scheduled"
      },
      {
        "type": "pickup",
        "fulfillable_on": "2026-04-10T18:15:00-07:00",
        "scheduling": "asap_and_scheduled"
      }
    ],
    "methods": [
      {
        "id": "method_delivery",
        "type": "delivery",
        "destination": {
          "id": "dest_home",
          "type": "delivery_address",
          "address": {
            "street_address": "450 Serra Mall",
            "extended_address": "Apt 3B",
            "address_locality": "Stanford",
            "address_region": "CA",
            "postal_code": "94305",
            "address_country": "US"
          }
        },
        "preference_options": [
          {"id": "pref_leave_at_door", "label": "Leave at my door"},
          {"id": "pref_hand_to_me", "label": "Hand it to me"}
        ],
        "selected_preference_option_ids": ["pref_leave_at_door"],
        "notes": "Gate code #4210, second floor",
        "selected_option_id": "opt_standard",
        "options": [
          {
            "id": "opt_priority",
            "title": "Priority Delivery",
            "description": "Sent directly to you with no other stops",
            "earliest_fulfillment_time": "2026-04-10T18:25:00-07:00",
            "latest_fulfillment_time": "2026-04-10T18:35:00-07:00",
            "totals": [{"type": "total", "amount": 599}]
          },
          {
            "id": "opt_standard",
            "title": "Standard Delivery",
            "earliest_fulfillment_time": "2026-04-10T18:35:00-07:00",
            "latest_fulfillment_time": "2026-04-10T18:50:00-07:00",
            "totals": [{"type": "total", "amount": 299}]
          }
        ]
      }
    ]
  },
  "tip": {
    "selected_option_id": "tip_18",
    "options": [
      {"id": "tip_15", "unit": "percentage", "amount": 15},
      {"id": "tip_18", "unit": "percentage", "amount": 18},
      {"id": "tip_20", "unit": "percentage", "amount": 20}
    ]
  },
  "totals": [
    {"type": "subtotal", "display_text": "Subtotal", "amount": 5000},
    {"type": "fulfillment", "display_text": "Standard Delivery", "amount": 299},
    {
      "type": "fee",
      "display_text": "Service & Regulatory Fees",
      "amount": 550,
      "lines": [
        {"display_text": "Service Fee", "amount": 350},
        {"display_text": "City Courier Regulatory Fee", "amount": 200}
      ]
    },
    {"type": "tax", "display_text": "Tax (8.75%)", "amount": 438},
    {"type": "tip", "display_text": "Courier Tip (18%)", "amount": 900},
    {"type": "total", "display_text": "Total", "amount": 7187}
  ],
  "links": [...],
  "continue_url": "https://food.example.com/checkout/chk_food_7187",
  "expires_at": "2026-04-11T00:00:00Z"
}
```

### Complete Checkout

The Platform submits payment. The Business places the order with the kitchen and returns the order confirmation.

```json
POST /checkout-sessions/chk_food_7187/complete HTTP/1.1
UCP-Agent: profile="https://platform.example/profile"
Content-Type: application/json
...other required headers...

{
  "payment": {
    "instruments": [
      {
        "id": "instr_1",
        "handler_id": "processor_tokenizer_1",
        "type": "card",
        "selected": true,
        "brand": "visa",
        "last_digits": "4242",
        "credential": {
          "type": "token",
          "token": "tok_visa_4242"
        }
      }
    ]
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
      "dev.ucp.food.checkout": [
        {"version": "draft"}
      ],
      "dev.ucp.food.fulfillment": [
        {"version": "draft", "extends": "dev.ucp.food.checkout"}
      ],
      "dev.ucp.food.tip": [
        {"version": "draft", "extends": "dev.ucp.food.checkout"}
      ]
    },
    "payment_handlers": {
      "com.example.processor_tokenizer": [
        {"id": "processor_tokenizer_1", "version": "draft", "available_instruments": [{"type": "card"}], "config": {}}
      ]
    }
  },
  "id": "chk_food_7187",
  "status": "completed",
  "currency": "USD",
  "food_establishment": {...},
  "buyer": {...},
  "line_items": [...],
  "fulfillment": {...},
  "tip": {...},
  "totals": [...],
  "payment": {
    "instruments": [
      {
        "id": "instr_1",
        "handler_id": "processor_tokenizer_1",
        "type": "card",
        "selected": true,
        "brand": "visa",
        "last_digits": "4242"
      }
    ]
  },
  "order": {
    "id": "ord_food_9876543210",
    "label": "#42",
    "tracking_url": "https://food.example.com/orders/ord_food_9876543210",
    "earliest_fulfillment_time": "2026-04-10T18:35:00-07:00",
    "latest_fulfillment_time": "2026-04-10T18:50:00-07:00"
  },
  "links": [...]
}
```

### Get Checkout

```json
GET /checkout-sessions/chk_food_7187 HTTP/1.1
UCP-Agent: profile="https://platform.example/profile"
...other required headers...
```

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "ucp": {...},
  "id": "chk_food_7187",
  "status": "ready_for_complete",
  "currency": "USD",
  "food_establishment": {...},
  "line_items": [...],
  "fulfillment": {...},
  "tip": {...},
  "totals": [...],
  "links": [...],
  "continue_url": "https://food.example.com/checkout/chk_food_7187",
  "expires_at": "2026-04-11T00:00:00Z"
}
```

### Cancel Checkout

```json
POST /checkout-sessions/chk_food_7187/cancel HTTP/1.1
UCP-Agent: profile="https://platform.example/profile"
Idempotency-Key: 883e1733-a52e-44f7-9049-779988773333
...other required headers...
```

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "ucp": {...},
  "id": "chk_food_7187",
  "status": "canceled",
  "currency": "USD",
  "food_establishment": {...},
  "line_items": [...],
  "totals": [...],
  "links": [...]
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
| `Content-Digest`  | No       | Body digest per RFC 9530. Required for requests/responses with a body. Format: `sha-256=:<base64-digest>:`.                                                                                                                                                   |
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
- **Idempotency-Key**: Operations that modify state **SHOULD** support idempotency. Retrying Complete Checkout without the same key risks placing the same food order twice. When provided, the server **MUST**:
  1. Store the key with the operation result for at least 24 hours.
  1. Return the cached result for duplicate keys whose request body matches the original.
  1. Return `409 Conflict` if the key is reused with a mismatched body. See [Message Signatures — Idempotency Key Requirements](http://ucp.dev/draft/specification/signatures/#replay-protection) for the full payload-matching contract.

## Protocol Mechanics

### Status Codes

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

Business outcomes — a sold-out dish, a closed kitchen, an address outside the delivery zone — are returned with HTTP 200 and the UCP envelope containing `messages` (see [Error Handling](http://ucp.dev/draft/specification/food/checkout/#error-handling)):

```json
{
  "ucp": {
    "version": "draft",
    "capabilities": {
      "dev.ucp.food.checkout": [
        {"version": "draft"}
      ]
    },
    "payment_handlers": {
      "com.example.processor_tokenizer": [
        {"id": "processor_tokenizer_1", "version": "draft", "available_instruments": [{"type": "card"}], "config": {}}
      ]
    }
  },
  "id": "chk_food_7187",
  "status": "incomplete",
  "currency": "USD",
  "food_establishment": {
    "id": "est_luigis_01",
    "name": "Luigi's Artisan Pizzeria"
  },
  "line_items": [
    {
      "id": "li_1",
      "quantity": 1,
      "dish": {
        "id": "dish_truffle_arancini",
        "title": "Truffle Arancini",
        "price": 1200
      },
      "totals": [
        {"type": "subtotal", "amount": 1200},
        {"type": "total", "amount": 1200}
      ]
    }
  ],
  "totals": [
    {"type": "subtotal", "amount": 1200},
    {"type": "total", "amount": 1200}
  ],
  "links": [],
  "messages": [
    {
      "type": "error",
      "code": "out_of_stock",
      "path": "$.line_items[0].dish",
      "content": "Truffle Arancini is sold out for tonight's dinner service.",
      "severity": "recoverable"
    }
  ]
}
```

For `create_checkout`, when no checkout session can be created (for example, the establishment is permanently closed), the Business **MUST** return HTTP 200 and the UCP envelope containing `messages`:

```json
{
  "ucp": { "version": "draft", "status": "error" },
  "messages": [
    {
      "type": "error",
      "code": "location_closed",
      "content": "This location is no longer taking orders.",
      "severity": "unrecoverable"
    }
  ],
  "continue_url": "https://food.example.com/"
}
```

## Message Signing

Platforms **MAY** choose among authentication mechanisms (API keys, OAuth, mTLS, HTTP Message Signatures). When using HTTP Message Signatures, checkout operations follow the [Message Signatures](http://ucp.dev/draft/specification/signatures/index.md) specification.

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
POST /checkout-sessions HTTP/1.1
Host: food.example.com
Content-Type: application/json
UCP-Agent: profile="https://platform.example/.well-known/ucp"
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Digest: sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:
Signature-Input: sig1=("@method" "@authority" "@path" "idempotency-key" "content-digest" "content-type");keyid="platform-2026"
Signature: sig1=:MEUCIQDTxNq8h7LGHpvVZQp1iHkFp9+3N8Mxk2zH1wK4YuVN8w...:

{"food_establishment":{"id":"est_luigis_01"},"line_items":[...]}
```

See [Message Signatures - REST Request Signing](http://ucp.dev/draft/specification/signatures/#rest-request-signing) for the complete signing algorithm.

### Response Signing

Response signatures are **RECOMMENDED** for:

- `complete_checkout` responses (order confirmation)

Response signatures are **OPTIONAL** for:

- `create_checkout`, `get_checkout`, `update_checkout`, `cancel_checkout`

**Example Signed Response:**

```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Digest: sha-256=:Y5fK8nLmPqRsT3vWxYzAbCdEfGhIjKlMnO...:
Signature-Input: sig1=("@status" "content-digest" "content-type");keyid="business-2026"
Signature: sig1=:MFQCIH7kL9nM2oP5qR8sT1uV4wX6yZaB3cD...:

{"id":"chk_food_7187","status":"completed","order":{"id":"ord_food_9876543210","label":"#42",...}}
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

Businesses **MAY** require authentication for some operations while leaving others open (e.g., guest checkout without authentication).
