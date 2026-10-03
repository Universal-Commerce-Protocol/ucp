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

# Checkout Capability - REST Binding

This document specifies the REST binding for the
[Food Checkout Capability](index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise REST transport availability through their UCP profile at
`/.well-known/ucp`.

<!-- ucp:example schema=profile def=business_schema -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": {
      "dev.ucp.food": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/overview",
          "transport": "rest",
          "schema": "https://ucp.dev/{{ ucp_version }}/services/food/rest.openapi.json",
          "endpoint": "https://food.example.com/ucp"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.food.checkout": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/food/checkout",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/food/checkout.json"
        }
      ],
      "dev.ucp.food.fulfillment": [
        {
          "version": "{{ ucp_version }}",
          "extends": "dev.ucp.food.checkout",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/food/extensions/fulfillment",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/food/fulfillment.json"
        }
      ]
    },
    "payment_handlers": {
      "com.example.processor_tokenizer": [
        {
          "id": "processor_tokenizer_1",
          "version": "{{ ucp_version }}",
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

All UCP REST endpoints are relative to the Business's base URL, which is
discovered through the UCP profile at `/.well-known/ucp`. The endpoint for the
food checkout capability is defined in the `rest.endpoint` field of the
business profile.

### Content Types

* **Request**: `application/json`
* **Response**: `application/json`

All request and response bodies **MUST** be valid JSON as specified in
[RFC 8259](https://tools.ietf.org/html/rfc8259){ target="_blank" }.

### Transport Security

All REST endpoints **MUST** be served over HTTPS with minimum TLS version
1.3.

## Operations

| Operation | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| [Create Checkout](index.md#create-checkout) | `POST` | `/checkout-sessions` | Create a checkout session. |
| [Get Checkout](index.md#get-checkout) | `GET` | `/checkout-sessions/{id}` | Get a checkout session. |
| [Update Checkout](index.md#update-checkout) | `PUT` | `/checkout-sessions/{id}` | Update a checkout session. |
| [Complete Checkout](index.md#complete-checkout) | `POST` | `/checkout-sessions/{id}/complete` | Place the order. |
| [Cancel Checkout](index.md#cancel-checkout) | `POST` | `/checkout-sessions/{id}/cancel` | Cancel a checkout session. |

## Examples

The examples below follow one order from start to finish: two customized
pizzas and a salad from Luigi's, delivered ASAP with an 18% tip.

### Create Checkout

The Platform sends the establishment and the configured dishes. The Business
prices them and asks for a fulfillment method.

=== "Request"

    <!-- ucp:example schema=food/checkout op=create direction=request -->
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
            "id": "dish_margherita_12",
            "modifications": [
              {"id": "mod_extra_mozzarella"},
              {"id": "mod_fresh_basil"}
            ],
            "note": "Well done crust, please"
          }
        },
        {
          "quantity": 1,
          "dish": {
            "id": "dish_caesar",
            "note": "Dressing on the side"
          }
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

=== "Response"

    <!-- ucp:example schema=food/fulfillment def=dev.ucp.food.checkout op=read -->
    ```json
    HTTP/1.1 201 Created
    Content-Type: application/json

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.food.checkout": [
            {"version": "{{ ucp_version }}"}
          ],
          "dev.ucp.food.fulfillment": [
            {"version": "{{ ucp_version }}", "extends": "dev.ucp.food.checkout"}
          ]
        },
        "payment_handlers": {
          "com.example.processor_tokenizer": [
            {"id": "processor_tokenizer_1", "version": "{{ ucp_version }}", "available_instruments": [{"type": "card"}], "config": {}}
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
            ],
            "modifications": [
              {"id": "mod_extra_mozzarella", "title": "Extra Mozzarella", "price": 200},
              {"id": "mod_fresh_basil", "title": "Fresh Basil", "price": 150}
            ],
            "note": "Well done crust, please"
          },
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
            "price": 1100,
            "note": "Dressing on the side"
          },
          "totals": [
            {"type": "subtotal", "amount": 1100},
            {"type": "total", "amount": 1100}
          ]
        }
      ],
      "fulfillment": {
        "available_methods": [
          {"type": "delivery", "fulfillable_on": "now"},
          {"type": "pickup", "fulfillable_on": "now"}
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

The Platform sends the full writable state plus a delivery address and a tip.
The Business adds delivery options, drop-off preferences, fees, and the
resolved tip.

=== "Request"

    <!-- ucp:example schema=food/fulfillment def=dev.ucp.food.checkout op=update direction=request -->
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
            "id": "dish_margherita_12",
            "modifications": [
              {"id": "mod_extra_mozzarella"},
              {"id": "mod_fresh_basil"}
            ],
            "note": "Well done crust, please"
          }
        },
        {
          "id": "li_2",
          "quantity": 1,
          "dish": {
            "id": "dish_caesar",
            "note": "Dressing on the side"
          }
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
              "postal_address": {
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

=== "Response"

    <!-- ucp:example schema=food/fulfillment def=dev.ucp.food.checkout op=read -->
    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.food.checkout": [
            {"version": "{{ ucp_version }}"}
          ],
          "dev.ucp.food.fulfillment": [
            {"version": "{{ ucp_version }}", "extends": "dev.ucp.food.checkout"}
          ]
        },
        "payment_handlers": {
          "com.example.processor_tokenizer": [
            {"id": "processor_tokenizer_1", "version": "{{ ucp_version }}", "available_instruments": [{"type": "card"}], "config": {}}
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
          {"type": "delivery", "fulfillable_on": "now"},
          {"type": "pickup", "fulfillable_on": "now"}
        ],
        "methods": [
          {
            "id": "method_delivery",
            "type": "delivery",
            "destination": {
              "id": "dest_home",
              "type": "delivery_address",
              "postal_address": {
                "street_address": "450 Serra Mall",
                "extended_address": "Apt 3B",
                "address_locality": "Stanford",
                "address_region": "CA",
                "postal_code": "94305",
                "address_country": "US"
              },
              "preference_options": [
                {"id": "pref_leave_at_door", "label": "Leave at my door"},
                {"id": "pref_hand_to_me", "label": "Hand it to me"}
              ],
              "selected_preference_option_ids": ["pref_leave_at_door"]
            },
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

The Platform submits payment. The Business places the order with the kitchen
and returns the order confirmation.

=== "Request"

    <!-- ucp:example schema=food/checkout op=complete direction=request -->
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

=== "Response"

    <!-- ucp:example schema=food/fulfillment def=dev.ucp.food.checkout op=complete direction=response -->
    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.food.checkout": [
            {"version": "{{ ucp_version }}"}
          ],
          "dev.ucp.food.fulfillment": [
            {"version": "{{ ucp_version }}", "extends": "dev.ucp.food.checkout"}
          ]
        },
        "payment_handlers": {
          "com.example.processor_tokenizer": [
            {"id": "processor_tokenizer_1", "version": "{{ ucp_version }}", "available_instruments": [{"type": "card"}], "config": {}}
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
        "tracking_url": "https://food.example.com/orders/ord_food_9876543210"
      },
      "links": [...]
    }
    ```

### Get Checkout

=== "Request"

    <!-- ucp:example skip reason="GET request has no body" -->
    ```json
    GET /checkout-sessions/chk_food_7187 HTTP/1.1
    UCP-Agent: profile="https://platform.example/profile"
    ...other required headers...
    ```

=== "Response"

    <!-- ucp:example schema=food/fulfillment def=dev.ucp.food.checkout op=read -->
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

=== "Request"

    <!-- ucp:example skip reason="cancel request has no body" -->
    ```json
    POST /checkout-sessions/chk_food_7187/cancel HTTP/1.1
    UCP-Agent: profile="https://platform.example/profile"
    Idempotency-Key: 883e1733-a52e-44f7-9049-779988773333
    ...other required headers...
    ```

=== "Response"

    <!-- ucp:example schema=food/checkout op=read -->
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

The following headers are defined for the HTTP binding and apply to all
operations unless otherwise noted.

{{ header_fields('create_checkout', 'food/rest.openapi.json') }}

### Specific Header Requirements

* **UCP-Agent**: All requests **MUST** include the `UCP-Agent` header
    containing the platform profile URI using Dictionary Structured Field syntax
    ([RFC 8941](https://datatracker.ietf.org/doc/html/rfc8941){target="_blank"}).
    Format: `profile="https://platform.example/profile"`.
* **Idempotency-Key**: Operations that modify state **SHOULD** support
    idempotency. Retrying Complete Checkout without the same key risks placing
    the same food order twice. When provided, the server **MUST**:
    1. Store the key with the operation result for at least 24 hours.
    2. Return the cached result for duplicate keys whose request body matches the original.
    3. Return `409 Conflict` if the key is reused with a mismatched body.
    See [Message Signatures — Idempotency Key Requirements](../../signatures.md#replay-protection)
    for the full payload-matching contract.

## Protocol Mechanics

### Status Codes

| Status Code | Description |
| :--- | :--- |
| `200 OK` | The request was successful. |
| `201 Created` | The resource was successfully created. |
| `400 Bad Request` | The request was invalid or cannot be served. |
| `401 Unauthorized` | Authentication is required and has failed or has not been provided. |
| `403 Forbidden` | The request is authenticated but the user does not have the necessary permissions. |
| `409 Conflict` | The request could not be completed due to a conflict (e.g., idempotent key reuse). |
| `422 Unprocessable Entity` | The profile content is malformed (discovery failure). |
| `424 Failed Dependency` | The profile URL is valid but fetch failed (discovery failure). |
| `429 Too Many Requests` | Rate limit exceeded. |
| `503 Service Unavailable` | Temporary unavailability. |
| `500 Internal Server Error` | An unexpected condition was encountered on the server. |

### Error Responses

See the [Core Specification](../../overview/index.md#error-handling) for the complete error
code registry and transport binding examples.

* **Protocol errors**: Return appropriate HTTP status code (401, 403, 409, 429,
    503) with JSON body containing `code` and `content`.
* **Business outcomes**: Return HTTP 200 with UCP envelope and `messages` array.

#### Business Outcomes

Business outcomes — a sold-out dish, a closed kitchen, an address outside the
delivery zone — are returned with HTTP 200 and the UCP envelope containing
`messages` (see [Error Handling](index.md#error-handling)):

<!-- ucp:example schema=food/checkout op=read -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.food.checkout": [
        {"version": "{{ ucp_version }}"}
      ]
    },
    "payment_handlers": {
      "com.example.processor_tokenizer": [
        {"id": "processor_tokenizer_1", "version": "{{ ucp_version }}", "available_instruments": [{"type": "card"}], "config": {}}
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

For `create_checkout`, when no checkout session can be created (for example,
the establishment is permanently closed), the Business **MUST** return HTTP 200
and the UCP envelope containing `messages`:

<!-- ucp:example schema=common/types/error_response op=read -->
```json
{
  "ucp": { "version": "{{ ucp_version }}", "status": "error" },
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

Platforms **MAY** choose among authentication mechanisms (API keys, OAuth,
mTLS, HTTP Message Signatures). When using HTTP Message Signatures, checkout
operations follow the [Message Signatures](../../signatures.md) specification.

### Request Signing

When HTTP Message Signatures are used, requests **MUST** include valid
`Signature-Input` and `Signature` headers (and `Content-Digest` when a body
is present) per RFC 9421:

| Header | Required | Description |
| :--- | :--- | :--- |
| `Signature-Input` | Yes | Describes signed components |
| `Signature` | Yes | Contains the signature value |
| `Content-Digest` | Cond.* | SHA-256 hash of request body |
| `UCP-Agent` | Yes | Signer identity (profile URL) |
| `Idempotency-Key` | Yes | Unique key for replay protection |

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

See [Message Signatures - REST Request Signing](../../signatures.md#rest-request-signing)
for the complete signing algorithm.

### Response Signing

Response signatures are **RECOMMENDED** for:

* `complete_checkout` responses (order confirmation)

Response signatures are **OPTIONAL** for:

* `create_checkout`, `get_checkout`, `update_checkout`, `cancel_checkout`

**Example Signed Response:**

```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Digest: sha-256=:Y5fK8nLmPqRsT3vWxYzAbCdEfGhIjKlMnO...:
Signature-Input: sig1=("@status" "content-digest" "content-type");keyid="business-2026"
Signature: sig1=:MFQCIH7kL9nM2oP5qR8sT1uV4wX6yZaB3cD...:

{"id":"chk_food_7187","status":"completed","order":{"id":"ord_food_9876543210","label":"#42",...}}
```

See [Message Signatures - REST Response Signing](../../signatures.md#rest-response-signing)
for the complete signing algorithm.

## Security Considerations

### Authentication

Authentication is optional and depends on business requirements. When
authentication is required, the REST transport **MAY** use:

1. **Open API**: No authentication required for public operations.
2. **API Keys**: Via `X-API-Key` header.
3. **OAuth 2.0**: Via `Authorization: Bearer {token}` header. Identifies the
   platform for agent-authenticated access, or both platform and user for
   user-authenticated access (see [Identity Linking](../../common/identity-linking/index.md)).
4. **Mutual TLS**: For high-security environments.
5. **HTTP Message Signatures**: Per [RFC 9421](https://www.rfc-editor.org/rfc/rfc9421)
    (see [Message Signing](#message-signing) above).

Businesses **MAY** require authentication for some operations while leaving
others open (e.g., guest checkout without authentication).
