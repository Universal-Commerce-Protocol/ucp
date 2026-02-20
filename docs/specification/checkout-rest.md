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

All UCP REST endpoints are relative to the business's base URL, which is
discovered through the UCP profile at `/.well-known/ucp`. The endpoint for the
checkout capability is defined in the `rest.endpoint` field of the
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

| Operation                                          | Method | Endpoint                           | Description                |
| :------------------------------------------------- | :----- | :--------------------------------- | :------------------------- |
| [Create Checkout](checkout.md#create-checkout)     | `POST` | `/checkout-sessions`               | Create a checkout session. |
| [Get Checkout](checkout.md#get-checkout)           | `GET`  | `/checkout-sessions/{id}`          | Get a checkout session.    |
| [Update Checkout](checkout.md#update-checkout)     | `PUT`  | `/checkout-sessions/{id}`          | Update a checkout session. |
| [Complete Checkout](checkout.md#complete-checkout) | `POST` | `/checkout-sessions/{id}/complete` | Place the order.           |
| [Cancel Checkout](checkout.md#cancel-checkout)     | `POST` | `/checkout-sessions/{id}/cancel`   | Cancel a checkout session. |

## Examples

### Create Checkout

=== "Request"

    ```json
    POST /checkout-sessions HTTP/1.1
    UCP-Agent: profile="https://platform.example/profile"
    Content-Type: application/json

    {
      "line_items": [
        {
          "item": {
            "id": "item_123",
            "title": "Red T-Shirt",
            "price": 2500
          },
          "id": "li_1",
          "quantity": 2
        }
      ]
    }
    ```

=== "Response"

    ```json
    HTTP/1.1 201 Created
    Content-Type: application/json

    {
      "ucp": {
        "version": "2026-01-11",
        "capabilities": {
          "dev.ucp.shopping.checkout": [
            {"version": "2026-01-11"}
          ]
        },
        "payment_handlers": {
          "com.shopify.shop_pay": [
            {
              "id": "shop_pay_1234",
              "version": "2026-01-11",
              "config": {
                "merchant_id": "shop_merchant_123"
              }
            }
          ]
        }
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
          "url": "https://business.example.com/terms"
        }
      ],
      "payment": {
        "instruments": [
          {
            "id": "instr_shop_pay_1",
            "handler_id": "shop_pay_1234",
            "type": "shop_pay",
            "selected": true,
            "display": {
              "email": "buyer@example.com"
            }
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

=== "Request"

    ```json
    PUT /checkout-sessions/{id} HTTP/1.1
    UCP-Agent: profile="https://platform.example/profile"
    Content-Type: application/json

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
          "quantity": 2
        }
      ]
    }
    ```

=== "Response"

    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "ucp": {
        "version": "2026-01-11",
        "capabilities": {
          "dev.ucp.shopping.checkout": [
            {"version": "2026-01-11"}
          ]
        },
        "payment_handlers": {
          "com.shopify.shop_pay": [
            {
              "id": "shop_pay_1234",
              "version": "2026-01-11",
              "config": {
                "merchant_id": "shop_merchant_123"
              }
            }
          ]
        }
      },
      "id": "chk_1234567890",
      "status": "incomplete",
      "messages": [
        {
          "type": "error",
          "code": "missing",
          "path": "$.fulfillment.method[0].selected_destination_id",
          "content": "Fulfillment address is required",
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
          "url": "https://business.example.com/terms"
        }
      ],
      "payment": {
        "instruments": [
          {
            "id": "instr_shop_pay_1",
            "handler_id": "shop_pay_1234",
            "type": "shop_pay",
            "selected": true,
            "display": {
              "email": "buyer@example.com"
            }
          }
        ]
      }
    }
    ```

#### Update Fulfillment

Fulfillment is an extension to the checkout capability. Most fields are provided
by the business based on buyer inputs, which includes desired fulfillment
type & addresses.

=== "Request"

    ```json
    PUT /checkout-sessions/{id} HTTP/1.1
    UCP-Agent: profile="https://platform.example/profile"
    Content-Type: application/json

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
          "quantity": 2
        }
      ],
      "fulfillment": {
        "methods": [
          {
            "type": "shipping",
            "destinations": [
              {
                "street_address": "123 Main St",
                "address_locality": "Springfield",
                "address_region": "IL",
                "postal_code": "62701",
                "address_country": "US"
              }
            ]
          }
        ]
      }
    }
    ```

=== "Response"

    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "ucp": {
        "version": "2026-01-11",
        "capabilities": {
          "dev.ucp.shopping.checkout": [
            {"version": "2026-01-11"}
          ]
        },
        "payment_handlers": {
          "com.google.pay": [
            {
              "id": "gpay_1234",
              "version": "2026-01-11",
              "config": {
                "allowed_payment_methods": [
                  {
                    "type": "CARD",
                    "parameters": {
                      "allowed_card_networks": ["VISA", "MASTERCARD", "AMEX"]
                    }
                  }
                ]
              }
            }
          ]
        }
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
      "fulfillment": {
        "methods": [
          {
            "id": "shipping_1",
            "type": "shipping",
            "line_item_ids": ["item_123"],
            "selected_destination_id": "dest_home",
            "destinations": [
              {
                "id": "dest_home",
                "street_address": "123 Main St",
                "address_locality": "Springfield",
                "address_region": "IL",
                "postal_code": "62701",
                "address_country": "US"
              }
            ],
            "groups": [
              {
                "id": "package_1",
                "line_item_ids": ["item_123"],
                "selected_option_id": "standard",
                "options": [
                  {
                    "id": "standard",
                    "title": "Standard Shipping",
                    "description": "Arrives in 5-7 business days",
                    "totals": [
                      {
                        "type": "total",
                        "amount": 500
                      }
                    ]
                  },
                  {
                    "id": "express",
                    "title": "Express Shipping",
                    "description": "Arrives in 2-3 business days",
                    "totals": [
                      {
                        "type": "total",
                        "amount": 1000
                      }
                    ]
                  }
                ]
              }
            ]
          }
        ]
      },
      "payment": {
        "instruments": [
          {
            "id": "pi_gpay_5678",
            "handler_id": "gpay_1234",
            "type": "card",
            "selected": true,
            "display": {
              "brand": "mastercard",
              "last_digits": "5678",
              "rich_text_description": "Google Pay •••• 5678"
            }
          }
        ]
      }
    }
    ```

#### Update Fulfillment Selection

Follow-up calls after initial `fulfillment` data to update selection.

=== "Request"

    ```json
    PUT /checkout-sessions/{id} HTTP/1.1
    UCP-Agent: profile="https://platform.example/profile"
    Content-Type: application/json

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
      "fulfillment": {
        "methods": [
          {
            "id": "shipping_1",
            "type": "shipping",
            "line_item_ids": ["item_123"],
            "selected_destination_id": "dest_home",
            "destinations": [
              {
                "id": "dest_home",
                "street_address": "123 Main St",
                "address_locality": "Springfield",
                "address_region": "IL",
                "postal_code": "62701",
                "address_country": "US"
              }
            ],
            "groups": [
              {
                "id": "package_1",
                "selected_option_id": "express"
              }
            ]
          }
        ]
      }
    }
    ```

=== "Response"

    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "ucp": {
        "version": "2026-01-11",
        "capabilities": {
          "dev.ucp.shopping.checkout": [
            {"version": "2026-01-11"}
          ]
        },
        "payment_handlers": {
          "com.shopify.shop_pay": [
            {
              "id": "shop_pay_1234",
              "version": "2026-01-11",
              "config": {
                "merchant_id": "shop_merchant_123"
              }
            }
          ]
        }
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
      "fulfillment": {
        "methods": [
          {
            "id": "shipping_1",
            "type": "shipping",
            "line_item_ids": ["item_123"],
            "selected_destination_id": "dest_home",
            "destinations": [
              {
                "id": "dest_home",
                "street_address": "123 Main St",
                "address_locality": "Springfield",
                "address_region": "IL",
                "postal_code": "62701",
                "address_country": "US"
              }
            ],
            "groups": [
              {
                "id": "package_1",
                "line_item_ids": ["item_123"],
                "selected_option_id": "express",
                "options": [
                  {
                    "id": "standard",
                    "title": "Standard Shipping",
                    "description": "Arrives in 5-7 business days",
                    "totals": [
                      {
                        "type": "total",
                        "amount": 500
                      }
                    ]
                  },
                  {
                    "id": "express",
                    "title": "Express Shipping",
                    "description": "Arrives in 2-3 business days",
                    "totals": [
                      {
                        "type": "total",
                        "amount": 1000
                      }
                    ]
                  }
                ]
              }
            ]
          }
        ]
      },
      "payment": {
        "instruments": [
          {
            "id": "instr_shop_pay_1",
            "handler_id": "shop_pay_1234",
            "type": "shop_pay",
            "selected": true,
            "display": {
              "email": "buyer@example.com"
            }
          }
        ]
      }
    }
    ```

### Complete Checkout

If businesses have specific logic to enforce field existence in `buyer` and
addresses (i.e. `fulfillment_address`, `billing_address`), this is the right
place to set these expectations via `messages`.

=== "Request"

    ```json
    POST /checkout-sessions/{id}/complete
    UCP-Agent: profile="https://platform.example/profile"
    Content-Type: application/json

    {
      "payment": {
        "instruments": [
          {
            "id": "pi_gpay_5678",
            "handler_id": "gpay_1234",
            "type": "card",
            "selected": true,
            "display": {
              "brand": "mastercard",
              "last_digits": "5678",
              "card_art": "https://cart-art-1.html",
              "description": "Google Pay •••• 5678"
            },
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
          }
        ]
      },
      "risk_signals": {
        //... risk signal related data (device fingerprint / risk token)
      }
    }
    ```

=== "Response"

    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "ucp": {
        "version": "2026-01-11",
        "capabilities": {
          "dev.ucp.shopping.checkout": [
            {"version": "2026-01-11"}
          ]
        },
        "payment_handlers": {
          "com.google.pay": [
            {
              "id": "gpay_1234",
              "version": "2026-01-11",
              "config": {
                "allowed_payment_methods": [
                  {
                    "type": "CARD",
                    "parameters": {
                      "allowed_card_networks": ["VISA", "MASTERCARD", "AMEX"]
                    }
                  }
                ]
              }
            }
          ]
        }
      },
      "id": "chk_123456789",
      "status": "completed",
      "currency": "USD",
      "order": {
        "id": "ord_99887766",
        "permalink_url": "https://merchant.com/orders/ord_99887766"
      },
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
      "fulfillment": {
        "methods": [
          {
            "id": "shipping_1",
            "type": "shipping",
            "line_item_ids": ["item_123"],
            "selected_destination_id": "dest_home",
            "destinations": [
              {
                "id": "dest_home",
                "street_address": "123 Main St",
                "address_locality": "Springfield",
                "address_region": "IL",
                "postal_code": "62701",
                "address_country": "US"
              }
            ],
            "groups": [
              {
                "id": "package_1",
                "line_item_ids": ["item_123"],
                "selected_option_id": "express",
                "options": [
                  {
                    "id": "standard",
                    "title": "Standard Shipping",
                    "description": "Arrives in 5-7 business days",
                    "totals": [
                      {
                        "type": "total",
                        "amount": 500
                      }
                    ]
                  },
                  {
                    "id": "express",
                    "title": "Express Shipping",
                    "description": "Arrives in 2-3 business days",
                    "totals": [
                      {
                        "type": "total",
                        "amount": 1000
                      }
                    ]
                  }
                ]
              }
            ]
          }
        ]
      },
      "payment": {
        "instruments": [
          {
            "id": "pi_gpay_5678",
            "handler_id": "gpay_1234",
            "type": "card",
            "selected": true,
            "display": {
              "brand": "mastercard",
              "last_digits": "5678",
              "rich_text_description": "Google Pay •••• 5678"
            }
          }
        ]
      }
    }
    ```

### Get Checkout

=== "Request"

    ```json
    GET /checkout-sessions/{id}
    UCP-Agent: profile="https://platform.example/profile"
    Content-Type: application/json

    {}
    ```

=== "Response"

    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "ucp": {
        "version": "2026-01-11",
        "capabilities": {
          "dev.ucp.shopping.checkout": [
            {"version": "2026-01-11"}
          ]
        },
        "payment_handlers": {
          "com.shopify.shop_pay": [
            {
              "id": "shop_pay_1234",
              "version": "2026-01-11",
              "config": {
                "merchant_id": "shop_merchant_123"
              }
            }
          ]
        }
      },
      "id": "chk_123456789",
      "status": "completed",
      "currency": "USD",
      "order": {
        "id": "ord_99887766",
        "permalink_url": "https://merchant.com/orders/ord_99887766"
      },
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
      "fulfillment": {
        "methods": [
          {
            "id": "shipping_1",
            "type": "shipping",
            "line_item_ids": ["item_123"],
            "selected_destination_id": "dest_home",
            "destinations": [
              {
                "id": "dest_home",
                "street_address": "123 Main St",
                "address_locality": "Springfield",
                "address_region": "IL",
                "postal_code": "62701",
                "address_country": "US"
              }
            ],
            "groups": [
              {
                "id": "package_1",
                "line_item_ids": ["item_123"],
                "selected_option_id": "express",
                "options": [
                  {
                    "id": "standard",
                    "title": "Standard Shipping",
                    "description": "Arrives in 5-7 business days",
                    "totals": [
                      {
                        "type": "total",
                        "amount": 500
                      }
                    ]
                  },
                  {
                    "id": "express",
                    "title": "Express Shipping",
                    "description": "Arrives in 2-3 business days",
                    "totals": [
                      {
                        "type": "total",
                        "amount": 1000
                      }
                    ]
                  }
                ]
              }
            ]
          }
        ]
      },
      "payment": {
        "instruments": [
          {
            "id": "instr_shop_pay_1",
            "handler_id": "shop_pay_1234",
            "type": "shop_pay",
            "selected": true,
            "display": {
              "email": "buyer@example.com"
            }
          }
        ]
      }
    }
    ```

### Cancel Checkout

=== "Request"

    ```json
    POST /checkout-sessions/{id}/cancel
    UCP-Agent: profile="https://platform.example/profile"
    Content-Type: application/json

    {}
    ```

=== "Response"

    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "ucp": {
        "version": "2026-01-11",
        "capabilities": {
          "dev.ucp.shopping.checkout": [
            {"version": "2026-01-11"}
          ]
        },
        "payment_handlers": {
          "com.google.pay": [
            {
              "id": "gpay_1234",
              "version": "2026-01-11",
              "config": {
                "allowed_payment_methods": [
                  {
                    "type": "CARD",
                    "parameters": {
                      "allowed_card_networks": ["VISA", "MASTERCARD", "AMEX"]
                    }
                  }
                ]
              }
            }
          ]
        }
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
      "fulfillment": {
        "methods": [
          {
            "id": "shipping_1",
            "type": "shipping",
            "line_item_ids": ["item_123"],
            "selected_destination_id": "dest_home",
            "destinations": [
              {
                "id": "dest_home",
                "street_address": "123 Main St",
                "address_locality": "Springfield",
                "address_region": "IL",
                "postal_code": "62701",
                "address_country": "US"
              }
            ],
            "groups": [
              {
                "id": "package_1",
                "line_item_ids": ["item_123"],
                "selected_option_id": "express",
                "options": [
                  {
                    "id": "standard",
                    "title": "Standard Shipping",
                    "description": "Arrives in 5-7 business days",
                    "totals": [
                      {
                        "type": "total",
                        "amount": 500
                      }
                    ]
                  },
                  {
                    "id": "express",
                    "title": "Express Shipping",
                    "description": "Arrives in 2-3 business days",
                    "totals": [
                      {
                        "type": "total",
                        "amount": 1000
                      }
                    ]
                  }
                ]
              }
            ]
          }
        ]
      },
      "payment": {
        "instruments": [
          {
            "id": "pi_gpay_5678",
            "handler_id": "gpay_1234",
            "type": "card",
            "selected": true,
            "display": {
              "brand": "mastercard",
              "last_digits": "5678",
              "rich_text_description": "Google Pay •••• 5678"
            }
          }
        ]
      }
    }
    ```

## HTTP Headers

The following headers are defined for the HTTP binding and apply to all
operations unless otherwise noted.

{{ header_fields('create_checkout', 'rest.openapi.json') }}

### Specific Header Requirements

* **UCP-Agent**: All requests **MUST** include the `UCP-Agent` header
    containing the platform profile URI using Dictionary Structured Field syntax
    ([RFC 8941](https://datatracker.ietf.org/doc/html/rfc8941){target="_blank"}).
    Format: `profile="https://platform.example/profile"`.
* **Idempotency-Key**: Operations that modify state **SHOULD** support
    idempotency. When provided, the server **MUST**:
    1. Store the key with the operation result for at least 24 hours.
    2. Return the cached result for duplicate keys.
    3. Return `409 Conflict` if the key is reused with different parameters.

## Protocol Mechanics

### Status Codes

UCP uses standard HTTP status codes to indicate the success or failure of an API
request.

| Status Code                 | Description                                                                        |
| :-------------------------- | :--------------------------------------------------------------------------------- |
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

See the [Core Specification](overview.md#error-handling) for the complete error
code registry and transport binding examples.

* **Protocol errors**: Return appropriate HTTP status code (401, 403, 409, 429,
    503) with JSON body containing `code` and `content`.
* **Business outcomes**: Return HTTP 200 with UCP envelope and `messages` array.

#### Business Outcomes

Business outcomes (including errors like unavailable merchandise) are returned
with HTTP 200 and the UCP envelope containing `messages`:

```json
{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": {
      "dev.ucp.shopping.checkout": [{"version": "2026-01-11"}]
    }
  },
  "id": "checkout_abc123",
  "status": "incomplete",
  "line_items": [
    {
      "id": "item_456",
      "quantity": 100,
      "available_quantity": 12
    }
  ],
  "messages": [
    {
      "type": "warning",
      "code": "quantity_adjusted",
      "content": "Quantity adjusted, requested 100 units but only 12 available",
      "path": "$.line_items[0].quantity"
    }
  ],
  "continue_url": "https://merchant.com/checkout/checkout_abc123"
}
```

## Message Signing

Platforms **MAY** choose among authentication mechanisms (API keys, OAuth,
mTLS, HTTP Message Signatures). When using
HTTP Message Signatures, checkout operations follow the
[Message Signatures](signatures.md) specification.

### Request Signing

When HTTP Message Signatures are used, requests **MUST** include valid
`Signature-Input` and `Signature` headers (and `Content-Digest` when a body
is present) per RFC 9421:

| Header                   | Required | Description                              |
| :----------------------- | :------- | :--------------------------------------- |
| `Signature-Input`        | Yes      | Describes signed components              |
| `Signature`              | Yes      | Contains the signature value             |
| `Content-Digest`         | Cond.*   | SHA-256 hash of request body             |

\* Required for requests with a body (POST, PUT)

**Example Signed Request:**

```http
POST /checkout-sessions HTTP/1.1
Host: merchant.example.com
Content-Type: application/json
UCP-Agent: profile="https://platform.example/.well-known/ucp"
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Digest: sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:
Signature-Input: sig1=("@method" "@authority" "@path" "idempotency-key" "content-digest" "content-type");keyid="platform-2025"
Signature: sig1=:MEUCIQDTxNq8h7LGHpvVZQp1iHkFp9+3N8Mxk2zH1wK4YuVN8w...:

{"line_items":[{"item":{"id":"item_123"},"quantity":2}]}
```

See [Message Signatures - REST Request Signing](signatures.md#rest-request-signing)
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
Signature-Input: sig1=("@status" "content-digest" "content-type");keyid="merchant-2025"
Signature: sig1=:MFQCIH7kL9nM2oP5qR8sT1uV4wX6yZaB3cD...:

{"id":"chk_123","status":"completed","order":{"id":"ord_456"}}
```

See [Message Signatures - REST Response Signing](signatures.md#rest-response-signing)
for the complete signing algorithm.

## Security Considerations

### Authentication

Authentication is optional and depends on business requirements. When
authentication is required, the REST transport **MAY** use:

1. **Open API**: No authentication required for public operations.
2. **API Keys**: Via `X-API-Key` header.
3. **OAuth 2.0**: Via `Authorization: Bearer {token}` header, following
    [RFC 6749](https://tools.ietf.org/html/rfc6749){ target="_blank" }.
4. **Mutual TLS**: For high-security environments.
5. **HTTP Message Signatures**: Per [RFC 9421](https://www.rfc-editor.org/rfc/rfc9421)
    (see [Message Signing](#message-signing) above).

Businesses **MAY** require authentication for some operations while leaving
others open (e.g., public checkout without authentication).
