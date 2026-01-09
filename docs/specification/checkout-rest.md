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
[Checkout Capability](checkout.md).

## Protocol Fundamentals

### Base URL
All UCP REST endpoints are relative to the merchant's base URL, which is
discovered through the UCP profile at `/.well-known/ucp`. The endpoint for the
checkout capability is defined in the `transports.rest.endpoint` field of the
merchant profile.

### Content Types

*   **Request**: `application/json`
*   **Response**: `application/json`

All request and response bodies **MUST** be valid JSON as specified in
[RFC 8259](https://tools.ietf.org/html/rfc8259){ target="_blank" }.

### Transport Security
All REST endpoints **MUST** be served over HTTPS with minimum TLS version
1.3.

## Operations

| Operation | Method | Endpoint | Description |
| :---- | :---- | :---- | :---- |
| [Create Checkout](checkout.md#create-checkout) | `POST` | `/checkout-sessions` | Create a checkout session. |
| [Get Checkout](checkout.md#get-checkout) | `GET` | `/checkout-sessions/{id}` | Get a checkout session. |
| [Update Checkout](checkout.md#update-checkout) | `PUT` | `/checkout-sessions/{id}` | Update a checkout session. |
| [Complete Checkout](checkout.md#complete-checkout) | `POST` | `/checkout-sessions/{id}/complete` | Place the order. |
| [Cancel Checkout](checkout.md#cancel-checkout) | `POST` | `/checkout-sessions/{id}/cancel` | Cancel a checkout session. |
| [Checkout Permalink](#checkout-permalink) | `GET` | `/checkout-sessions/new/{items}` | Initialize checkout via URL (browser navigation). |

## Examples

### Create Checkout

**Request**

```json
POST /checkout-sessions HTTP/1.1
Content-Type: application/json
UCP-Agent: profile="https://agent.example/profile"

{
  "line_items": [
    {
      "item": {
        "id": "item_123",
        "title": "Red T-Shirt",
        "price": 2500
      },
      "id": "li_1",
      "quantity": 2,
    }
  ]
}
```

**Response**

```json
HTTP/1.1 201 Created
Content-Type: application/json

{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": [
      {
        "name": "dev.ucp.shopping.checkout",
        "version": "2026-01-11"
      }
    ]
  },
  "id": "chk_1234567890",
  "status": "incomplete",
  "messages": [
    {
      "type": "error",
      "code": "missing",
      "path": "$.buyer.email",
      "content": "Buyer email is required",
      "severity": "recoverable"
    }
  ],
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": {
        "id": "item_123",
        "title": "Red T-Shirt",
        "price": 2500
      },
      "quantity": 2,
      "totals": [
        {"type": "subtotal", "amount": 5000},
        {"type": "total", "amount": 5000}
      ]
    }
  ],
  "totals": [
    {
      "type": "subtotal",
      "amount": 5000
    },
    {
      "type": "tax",
      "amount": 400
    },
    {
      "type": "total",
      "amount": 5400
    }
  ],
  "links": [
    {
      "type": "terms_of_service",
      "url": "https://merchant.com/terms"
    }
  ],
  "payment": {
    "handlers": [
      {
        "id": "com.google.pay",
        "name": "gpay",
        "version": "2024-12-03",
        "spec": "https://developers.google.com/merchant/ucp/guides/gpay-payment-handler",
        "config_schema": "https://pay.google.com/gp/p/ucp/2026-01-11/schemas/gpay_config.json",
        "instrument_schemas": [
          "https://pay.google.com/gp/p/ucp/2026-01-11/schemas/gpay_card_payment_instrument.json"
        ],
        "config": {
          "allowed_payment_methods": [
            {
              "type": "CARD",
              "parameters": {
                "allowed_card_networks": [
                  "VISA",
                  "MASTERCARD",
                  "AMEX"
                ]
              }
            }
          ]
        }
      }
    ],
    "selected_instrument_id": "pi_gpay_5678",
    "instruments": [
      {
        "id": "pi_gpay_5678",
        "handler_id": "com.google.pay",
        "type": "card",
        "brand": "mastercard",
        "last_digits": "5678",
        "rich_text_description": "Google Pay •••• 5678"
      }
    ]
  }
}
```

### Update Checkout

#### Update Buyer Info

All fields in `buyer` are optional, allowing clients to progressively build
the checkout state across multiple calls. Each PUT replaces the entire session,
so clients must include all previously set fields they wish to retain.

**Request**

```json
PUT /checkout-sessions/{id} HTTP/1.1
Content-Type: application/json
UCP-Agent: profile="https://agent.example/profile"

{
  "id": "chk_123456789",
  "buyer": {
    "email": "jane@example.com",
    "first_name": "Jane",
    "last_name": "Doe"
  },
  "line_items": [
    {
      "item": {
        "id": "item_123",
        "title": "Red T-Shirt",
        "price": 2500
      },
      "id": "li_1",
      "quantity": 2,
    }
  ]
}
```

**Response**

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": [
      {
        "name": "dev.ucp.shopping.checkout",
        "version": "2026-01-11"
      }
    ],
  },
  "id": "chk_1234567890",
  "status": "incomplete",
  "messages": [
    {
      "type": "error",
      "code": "missing",
      "path": "$.buyer.shipping_address",
      "content": "Shipping address is required",
      "severity": "recoverable"
    }
  ],
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": {
        "id": "item_123",
        "title": "Red T-Shirt",
        "price": 2500
      },
      "quantity": 2,
      "totals": [
        {"type": "subtotal", "amount": 5000},
        {"type": "total", "amount": 5000}
      ]
    }
  ],
  "buyer": {
    "email": "jane@example.com",
    "first_name": "Jane",
    "last_name": "Doe"
  },
  "totals": [
    {
      "type": "subtotal",
      "amount": 5000
    },
    {
      "type": "tax",
      "amount": 400
    },
    {
      "type": "total",
      "amount": 5400
    }
  ],
  "links": [
    {
      "type": "terms_of_service",
      "url": "https://merchant.com/terms"
    }
  ],
  "payment": {
    "handlers": [
      {
        "id": "com.google.pay",
        "name": "gpay",
        "version": "2024-12-03",
        "spec": "https://ucp.dev/handlers/google_pay",
        "config_schema": "https://pay.google.com/gp/p/ucp/2026-01-11/schemas/gpay_config.json",
        "instrument_schemas": [
          "https://pay.google.com/gp/p/ucp/2026-01-11/schemas/gpay_card_payment_instrument.json"
        ],
        "config": {
          "allowed_payment_methods": [
            {
              "type": "CARD",
              "parameters": {
                "allowed_card_networks": [
                  "VISA",
                  "MASTERCARD",
                  "AMEX"
                ]
              }
            }
          ]
        }
      }
    ],
    "selected_instrument_id": "pi_gpay_5678",
    "instruments": [
      {
        "id": "pi_gpay_5678",
        "handler_id": "com.google.pay",
        "type": "card",
        "brand": "mastercard",
        "last_digits": "5678",
        "rich_text_description": "Google Pay •••• 5678"
      }
    ]
  }
}
```

#### Update Fulfillment Address

Fulfillment is an extension to the checkout capability and contains a
`fulfillment_address`. All fields are optional, enabling progressive data
collection. Each PUT replaces the entire session, so include all fields to
retain.

**Request**

```json
PUT /checkout-sessions/{id} HTTP/1.1
Content-Type: application/json
UCP-Agent: profile="https://agent.example/profile"

{
  "id": "chk_123456789",
  "buyer": {
    "email": "jane@example.com",
    "first_name": "Jane",
    "last_name": "Doe"
  },
  "line_items": [
    {
      "item": {
        "id": "item_123",
        "title": "Red T-Shirt",
        "price": 2500
      },
      "id": "li_1",
      "quantity": 2,
    }
  ],
  "fulfillment_address": {
    "full_name": "John Doe", // Can differ from buyer name.
    "street_address": "123 Urban St",
    "address_locality": "San Francisco",
    "address_region": "CA",
    "postal_code": "94103",
    "address_country": "US"
  }
}
```

**Response**

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": [
      {
        "name": "dev.ucp.shopping.checkout",
        "version": "2026-01-11"
      }
    ],
  },
  "id": "chk_1234567890",
  "status": "incomplete",
  "messages": [
    {
      "type": "error",
      "code": "missing",
      "path": "$.selected_fulfillment_option",
      "content": "Please select a fulfillment option",
      "severity": "recoverable"
    }
  ],
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": {
        "id": "item_123",
        "title": "Red T-Shirt",
        "price": 2500
      },
      "quantity": 2,
      "totals": [
        {"type": "subtotal", "amount": 5000},
        {"type": "total", "amount": 5000}
      ]
    }
  ],
  "buyer": {
    "email": "jane@example.com",
    "first_name": "Jane",
    "last_name": "Doe"
  },
  "totals": [
    {
      "type": "subtotal",
      "amount": 5000
    },
    {
      "type": "tax",
      "amount": 400
    },
    {
      "type": "total",
      "amount": 5400
    }
  ],
  "links": [
    {
      "type": "terms_of_service",
      "url": "https://merchant.com/terms"
    }
  ],
  "fulfillment_address": {
    "full_name": "John Doe", // Can differ from buyer name.
    "street_address": "123 Urban St",
    "address_locality": "San Francisco",
    "address_region": "CA",
    "postal_code": "94103",
    "address_country": "US"
  },
  "fulfillment_options": [
    {
      "id": "ship-1",
      "type": "shipping",
      "title": "Standard Shipping",
      "sub_title": "Arrives in 4-5 days",
      "subtotal": 500
    },
    {
      "id": "ship-2",
      "type": "shipping",
      "title": "Express Shipping",
      "sub_title": "Arrives in 1-2 days",
      "subtotal": 1500
    }
  ],
  "payment": {
    "handlers": [
      {
        "id": "com.google.pay",
        "name": "gpay",
        "version": "2024-12-03",
        "spec": "https://ucp.dev/handlers/google_pay",
        "config_schema": "https://ucp.dev/handlers/google_pay/config.json",
        "instrument_schemas": [
          "https://ucp.dev/handlers/google_pay/card_payment_instrument.json"
        ],
        "config": {
          "allowed_payment_methods": [
            {
              "type": "CARD",
              "parameters": {
                "allowed_card_networks": [
                  "VISA",
                  "MASTERCARD",
                  "AMEX"
                ]
              }
            }
          ]
        }
      }
    ],
    "selected_instrument_id": "pi_gpay_5678",
    "instruments": [
      {
        "id": "pi_gpay_5678",
        "handler_id": "com.google.pay",
        "type": "card",
        "brand": "mastercard",
        "last_digits": "5678",
        "rich_text_description": "Google Pay •••• 5678"
      }
    ]
  }
}
```

#### Update Fulfillment Selection

Follow-up call after `fulfillment_options` are returned based on the provided
`fulfillment_address`.

**Request**

```json
PUT /checkout-sessions/{id} HTTP/1.1
Content-Type: application/json
UCP-Agent: profile="https://agent.example/profile"

{
  "id": "chk_123456789",
  "buyer": {
    "email": "jane@example.com",
    "first_name": "Jane",
    "last_name": "Doe"
  },
  "line_items": [
    {
      "item": {
        "id": "item_123",
        "title": "Red T-Shirt",
        "price": 2500
      },
      "id": "li_1",
      "quantity": 2,
    }
  ],
  "fulfillment_address": {
    "full_name": "John Doe", // Can differ from buyer name.
    "street_address": "123 Urban St",
    "address_locality": "San Francisco",
    "address_region": "CA",
    "postal_code": "94103",
    "address_country": "US"
  },
  "fulfillment_option_id": "ship-2"
}
```

**Response**

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": [
      {
        "name": "dev.ucp.shopping.checkout",
        "version": "2026-01-11"
      }
    ],
  },
  "id": "chk_1234567890",
  "status": "ready_for_complete",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": {
        "id": "item_123",
        "title": "Red T-Shirt",
        "price": 2500
      },
      "quantity": 2,
      "totals": [
        {"type": "subtotal", "amount": 5000},
        {"type": "total", "amount": 5000}
      ]
    }
  ],
  "buyer": {
    "email": "jane@example.com",
    "first_name": "Jane",
    "last_name": "Doe"
  },
  "totals": [
    {
      "type": "subtotal",
      "amount": 5000
    },
    {
      "type": "tax",
      "amount": 400
    },
    {
      "type": "total",
      "amount": 5400
    }
  ],
  "links": [
    {
      "type": "terms_of_service",
      "url": "https://merchant.com/terms"
    }
  ],
  "fulfillment_address": {
    "full_name": "John Doe", // Can differ from buyer name.
    "street_address": "123 Urban St",
    "address_locality": "San Francisco",
    "address_region": "CA",
    "postal_code": "94103",
    "address_country": "US"
  },
  "fulfillment_options": [
    {
      "id": "ship-1",
      "type": "shipping",
      "title": "Standard Shipping",
      "sub_title": "Arrives in 4-5 days",
      "subtotal": 500
    },
    {
      "id": "ship-2",
      "type": "shipping",
      "title": "Express Shipping",
      "sub_title": "Arrives in 1-2 days",
      "subtotal": 1500
    }
  ],
  "fulfillment_option_id": "ship-2",
  "payment": {
    "handlers": [
      {
        "id": "com.google.pay",
        "name": "gpay",
        "version": "2024-12-03",
        "spec": "https://ucp.dev/handlers/google_pay",
        "config_schema": "https://ucp.dev/handlers/google_pay/config.json",
        "instrument_schemas": [
          "https://ucp.dev/handlers/google_pay/card_payment_instrument.json"
        ],
        "config": {
          "allowed_payment_methods": [
            {
              "type": "CARD",
              "parameters": {
                "allowed_card_networks": [
                  "VISA",
                  "MASTERCARD",
                  "AMEX"
                ]
              }
            }
          ]
        }
      }
    ],
    "selected_instrument_id": "pi_gpay_5678",
    "instruments": [
      {
        "id": "pi_gpay_5678",
        "handler_id": "com.google.pay",
        "type": "card",
        "brand": "mastercard",
        "last_digits": "5678",
        "rich_text_description": "Google Pay •••• 5678"
      }
    ]
  }
}
```

### Complete Checkout

If merchants have specific logic to enforce field existence in `buyer` and
addresses (i.e. `fulfillment_address`, `billing_address`), this is the right
place to set these expectations via `messages`.

**Request**

```json
POST /checkout-sessions/{id}/complete
Content-Type: application/json

{
  "payment_data": {
    "id": "pi_gpay_5678",
    "handler_id": "com.google.pay",
    "type": "card",
    "brand": "mastercard",
    "last_digits": "5678",
    "rich_card_art": "https://cart-art-1.html",
    "rich_text_description": "Google Pay •••• 5678",
    "billing_address": {
      "street_address": "123 Main St",
      "address_locality": "Anytown",
      "address_region": "CA",
      "address_country": "US",
      "postal_code": "12345"
    },
    "credential": {
      "type": "PAYMENT_GATEWAY",
      "token": "examplePaymentMethodToken"
    }
  },
  "risk_signals": {
    //... risk signal related data (device fingerprint / risk token)
  }
}
```

**Response**

Returns the full checkout object indicating the order is complete.

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": [
      {
        "name": "dev.ucp.shopping.checkout",
        "version": "2026-01-11"
      }
    ],
  },
  "id": "chk_123456789",
  "status": "completed",
  "currency": "USD",
  "order_id": "ord_99887766",
  "order_permalink_url": "https://merchant.com/orders/ord_99887766",
  "line_items": [
    {
      "id": "li_1",
      "item": {
        "id": "item_123",
        "title": "Red T-Shirt",
        "price": 2500
      },
      "quantity": 2,
      "totals": [
        {"type": "subtotal", "amount": 5000},
        {"type": "total", "amount": 5000}
      ]
    }
  ],
  "buyer": {
    "email": "jane@example.com",
    "first_name": "Jane",
    "last_name": "Doe"
  },
  "totals": [
    {
      "type": "subtotal",
      "amount": 5000
    },
    {
      "type": "tax",
      "amount": 400
    },
    {
      "type": "total",
      "amount": 5400
    }
  ],
  "links": [
    {
      "type": "terms_of_service",
      "url": "https://merchant.com/terms"
    }
  ],
  "fulfillment_address": {
    "full_name": "John Doe", // Can differ from buyer name.
    "street_address": "123 Urban St",
    "address_locality": "San Francisco",
    "address_region": "CA",
    "postal_code": "94103",
    "address_country": "US"
  },
  "fulfillment_options": [
    {
      "id": "ship-1",
      "type": "shipping",
      "title": "Standard Shipping",
      "sub_title": "Arrives in 4-5 days",
      "subtotal": 500
    },
    {
      "id": "ship-2",
      "type": "shipping",
      "title": "Express Shipping",
      "sub_title": "Arrives in 1-2 days",
      "subtotal": 1500
    }
  ],
  "fulfillment_option_id": "ship-2",
  "payment": {
    "handlers": [
      {
        "id": "com.google.pay",
        "name": "gpay",
        "version": "2024-12-03",
        "spec": "https://ucp.dev/handlers/google_pay",
        "config_schema": "https://ucp.dev/handlers/google_pay/config.json",
        "instrument_schemas": [
          "https://ucp.dev/handlers/google_pay/card_payment_instrument.json"
        ],
        "config": {
          "allowed_payment_methods": [
            {
              "type": "CARD",
              "parameters": {
                "allowed_card_networks": [
                  "VISA",
                  "MASTERCARD",
                  "AMEX"
                ]
              }
            }
          ]
        }
      }
    ],
    "selected_instrument_id": "pi_gpay_5678",
    "instruments": [
      {
        "id": "pi_gpay_5678",
        "handler_id": "com.google.pay",
        "type": "card",
        "brand": "mastercard",
        "last_digits": "5678",
        "rich_text_description": "Google Pay •••• 5678"
      }
    ]
  }
}
```

### Get Checkout

**Request**

```json
GET /checkout-sessions/{id}
Content-Type: application/json

{}
```

**Response**

Returns the full checkout object snapshot.

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": [
      {
        "name": "dev.ucp.shopping.checkout",
        "version": "2026-01-11"
      }
    ],
  },
  "id": "chk_123456789",
  "status": "completed",
  "currency": "USD",
  "order_id": "ord_99887766",
  "order_permalink_url": "https://merchant.com/orders/ord_99887766",
  "line_items": [
    {
      "id": "li_1",
      "item": {
        "id": "item_123",
        "title": "Red T-Shirt",
        "price": 2500
      },
      "quantity": 2,
      "totals": [
        {"type": "subtotal", "amount": 5000},
        {"type": "total", "amount": 5000}
      ]
    }
  ],
  "buyer": {
    "email": "jane@example.com",
    "first_name": "Jane",
    "last_name": "Doe"
  },
  "totals": [
    {
      "type": "subtotal",
      "amount": 5000
    },
    {
      "type": "tax",
      "amount": 400
    },
    {
      "type": "total",
      "amount": 5400
    }
  ],
  "links": [
    {
      "type": "terms_of_service",
      "url": "https://merchant.com/terms"
    }
  ],
  "fulfillment_address": {
    "full_name": "John Doe", // Can differ from buyer name.
    "street_address": "123 Urban St",
    "address_locality": "San Francisco",
    "address_region": "CA",
    "postal_code": "94103",
    "address_country": "US"
  },
  "fulfillment_options": [
    {
      "id": "ship-1",
      "type": "shipping",
      "title": "Standard Shipping",
      "sub_title": "Arrives in 4-5 days",
      "subtotal": 500
    },
    {
      "id": "ship-2",
      "type": "shipping",
      "title": "Express Shipping",
      "sub_title": "Arrives in 1-2 days",
      "subtotal": 1500
    }
  ],
  "fulfillment_option_id": "ship-2",
  "payment": {
    "handlers": [
      {
        "id": "com.google.pay",
        "name": "gpay",
        "version": "2024-12-03",
        "spec": "https://ucp.dev/handlers/google_pay",
        "config_schema": "https://ucp.dev/handlers/google_pay/config.json",
        "instrument_schemas": [
          "https://ucp.dev/handlers/google_pay/card_payment_instrument.json"
        ],
        "config": {
          "allowed_payment_methods": [
            {
              "type": "CARD",
              "parameters": {
                "allowed_card_networks": [
                  "VISA",
                  "MASTERCARD",
                  "AMEX"
                ]
              }
            }
          ]
        }
      }
    ],
    "selected_instrument_id": "pi_gpay_5678",
    "instruments": [
      {
        "id": "pi_gpay_5678",
        "handler_id": "com.google.pay",
        "type": "card",
        "brand": "mastercard",
        "last_digits": "5678",
        "rich_text_description": "Google Pay •••• 5678"
      }
    ]
  }
}
```

### Cancel Checkout

**Request**

```json
POST /checkout-sessions/{id}/cancel
Content-Type: application/json

{}
```

**Response**

Returns the full checkout object snapshot with status updated to `canceled`.

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": [
      {
        "name": "dev.ucp.shopping.checkout",
        "version": "2026-01-11"
      }
    ],
  },
  "id": "chk_123456789",
  "status": "canceled", // Status is updated to canceled.
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": {
        "id": "item_123",
        "title": "Red T-Shirt",
        "price": 2500
      },
      "quantity": 2,
      "totals": [
        {"type": "subtotal", "amount": 5000},
        {"type": "total", "amount": 5000}
      ]
    }
  ],
  "buyer": {
    "email": "jane@example.com",
    "first_name": "Jane",
    "last_name": "Doe"
  },
  "totals": [
    {
      "type": "subtotal",
      "amount": 5000
    },
    {
      "type": "tax",
      "amount": 400
    },
    {
      "type": "total",
      "amount": 5400
    }
  ],
  "links": [
    {
      "type": "terms_of_service",
      "url": "https://merchant.com/terms"
    }
  ],
  "fulfillment_address": {
    "full_name": "John Doe", // Can differ from buyer name.
    "street_address": "123 Urban St",
    "address_locality": "San Francisco",
    "address_region": "CA",
    "postal_code": "94103",
    "address_country": "US"
  },
  "fulfillment_options": [
    {
      "id": "ship-1",
      "type": "shipping",
      "title": "Standard Shipping",
      "sub_title": "Arrives in 4-5 days",
      "subtotal": 500
    },
    {
      "id": "ship-2",
      "type": "shipping",
      "title": "Express Shipping",
      "sub_title": "Arrives in 1-2 days",
      "subtotal": 1500
    }
  ],
  "fulfillment_option_id": "ship-2",
  "payment": {
    "handlers": [
      {
        "id": "com.google.pay",
        "name": "gpay",
        "version": "2024-12-03",
        "spec": "https://ucp.dev/handlers/google_pay",
        "config_schema": "https://ucp.dev/handlers/google_pay/config.json",
        "instrument_schemas": [
          "https://ucp.dev/handlers/google_pay/card_payment_instrument.json"
        ],
        "config": {
          "allowed_payment_methods": [
            {
              "type": "CARD",
              "parameters": {
                "allowed_card_networks": [
                  "VISA",
                  "MASTERCARD",
                  "AMEX"
                ]
              }
            }
          ]
        }
      }
    ],
    "selected_instrument_id": "pi_gpay_5678",
    "instruments": [
      {
        "id": "pi_gpay_5678",
        "handler_id": "com.google.pay",
        "type": "card",
        "brand": "mastercard",
        "last_digits": "5678",
        "rich_text_description": "Google Pay •••• 5678"
      }
    ]
  }
}
```

## Checkout Permalink

A stateless URL that encodes checkout state directly, allowing reconstruction
without server-side persistence. Merchants **SHOULD** implement support for this
format to facilitate checkout handoff and accelerated entry—for example, a
platform can prefill checkout state when initiating a buy-now flow.

### Path Format

The permalink path is `/checkout-sessions/new/{items}`, where items are encoded
as `{item_id}:{quantity}`, comma-separated for multiple items:

```
https://{shop_domain}/checkout-sessions/new/{item_id}:{quantity},{item_id}:{quantity}
```

The `/new` segment distinguishes permalinks from existing session access
(`/checkout-sessions/{id}`). Unlike the JSON API operations above, accessing a
checkout permalink is a **browser navigation** endpoint: it returns a redirect
to the checkout UI or renders the checkout page directly. This endpoint is not
included in the OpenAPI specification as it does not return JSON.

### Checkout Fields (Query Parameters)

Additional checkout state is encoded as query parameters using JSONPath syntax
(RFC 9535) without the `$` root prefix. Parameter names and values **MUST** be
percent-encoded per RFC 3986.

| Schema Path | Query Parameter | Example |
|:------------|:----------------|:--------|
| `$.currency` | `currency` | `?currency=USD` |
| `$.buyer.email` | `buyer.email` | `?buyer.email=user%40example.com` |
| `$.fulfillment.methods[0].destinations[0].postal_code` | `fulfillment.methods[0].destinations[0].postal_code` | `?fulfillment.methods%5B0%5D...` |
| `$.discount_codes` (array) | `discount_codes` | `?discount_codes=SAVE10,WELCOME` |

Array field values are comma-separated. Servers **MUST** gracefully ignore
unrecognized query parameters.

### Example

```
https://shop.example.com/checkout-sessions/new/sku123:2,sku456:1?currency=USD&buyer.email=user%40example.com&discount_codes=SAVE10
```

This permalink creates a checkout with two units of `sku123` and one unit of
`sku456`, sets the currency to USD, prefills the buyer's email, and applies the
`SAVE10` discount code. The server responds with a redirect to the checkout UI
or renders the checkout page directly.

### Platform-Constructed Permalinks

Because checkout permalinks follow a standard format, platforms MAY construct
permalinks directly to initiate handoff—for example, to start a buy-now flow
without a prior API call. However, when a merchant-provided `continue_url` is
available, platforms **SHOULD** prefer it over constructing their own permalink.

### Privacy Considerations

When constructing or transmitting checkout permalinks, attention **MUST** be
paid to what data is included in URL parameters. PII, payment data, and other
sensitive information are subject to privacy regulations and PCI-DSS
requirements. Implementers should evaluate what fields are appropriate to encode
based on their compliance obligations.

## HTTP Headers

The following headers are defined for the HTTP binding and apply to all
operations unless otherwise noted.

{{ header_fields('create_checkout', 'rest.openapi.json') }}

### Specific Header Requirements

*   **UCP-Agent**: All requests **MUST** include the `UCP-Agent` header
    containing the Agent profile URI using Dictionary Structured Field syntax
    ([RFC 8941](https://datatracker.ietf.org/doc/html/rfc8941){target="_blank"}).
    Format: `profile="https://agent.example/profile"`.
*   **Idempotency-Key**: Operations that modify state **SHOULD** support
    idempotency. When provided, the server **MUST**:
    1.  Store the key with the operation result for at least 24 hours.
    2.  Return the cached result for duplicate keys.
    3.  Return `409 Conflict` if the key is reused with different parameters.

## Protocol Mechanics

### Status Codes

UCP uses standard HTTP status codes to indicate the success or failure of an API
request.

| Status Code | Description |
| :--- | :--- |
| `200 OK` | The request was successful. |
| `201 Created` | The resource was successfully created. |
| `400 Bad Request` | The request was invalid or cannot be served. |
| `401 Unauthorized` | Authentication is required and has failed or has not been provided. |
| `403 Forbidden` | The request is authenticated but the user does not have the necessary permissions. |
| `404 Not Found` | The requested resource could not be found. |
| `409 Conflict` | The request could not be completed due to a conflict (e.g., idempotent key reuse). |
| `429 Too Many Requests` | Rate limit exceeded. |
| `503 Service Unavailable` | Temporary unavailability. |
| `500 Internal Server Error` | An unexpected condition was encountered on the server. |

### Error Responses

Error responses follow the standard UCP error structure:

```json
{
  "status": "error",
  "errors": [
    {
      "code": "INVALID_CART_ITEMS",
      "message": "One or more cart items are invalid",
      "severity": "error",
      "details": {
        "invalid_items": ["sku_999"]
      }
    }
  ],
  "request_id": "req_abc123"
}
```

## Security Considerations

### Authentication

Authentication is optional and depends on merchant requirements. When
authentication is required, the REST transport **MAY** use:

1.  **Open API**: No authentication required for public operations.
2.  **API Keys**: Via `X-API-Key` header.
3.  **OAuth 2.0**: Via `Authorization: Bearer {token}` header, following
    [RFC 6749](https://tools.ietf.org/html/rfc6749).
4.  **Mutual TLS**: For high-security environments.

Merchants **MAY** require authentication for some operations while leaving
others open (e.g., public checkout without authentication).
