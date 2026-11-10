# Checkout Capability - MCP Binding

This document specifies the Model Context Protocol (MCP) binding for the food [Checkout Capability](http://ucp.dev/draft/specification/food/checkout/index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise MCP transport availability through their UCP profile at `/.well-known/ucp`.

```json
{
  "ucp": {
    "version": "draft",
    "services": {
      "dev.ucp.food": [
        {
          "version": "draft",
          "spec": "https://ucp.dev/draft/specification/overview",
          "transport": "mcp",
          "schema": "https://ucp.dev/draft/services/food/mcp.openrpc.json",
          "endpoint": "https://food.example.com/ucp/mcp"
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
          "spec": "https://ucp.dev/draft/specification/food/extensions/fulfillment",
          "schema": "https://ucp.dev/draft/schemas/food/fulfillment.json",
          "extends": "dev.ucp.food.checkout"
        }
      ],
      "dev.ucp.food.tip": [
        {
          "version": "draft",
          "spec": "https://ucp.dev/draft/specification/food/extensions/tip",
          "schema": "https://ucp.dev/draft/schemas/food/tip.json",
          "extends": "dev.ucp.food.checkout"
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

### Request Metadata

MCP clients **MUST** include a `meta` object in every request containing protocol metadata:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "create_checkout",
    "arguments": {
      "meta": {
        "ucp-agent": {
          "profile": "https://platform.example/profiles/food-agent.json"
        },
        "idempotency-key": "550e8400-e29b-41d4-a716-446655440000"
      },
      "checkout": {
        "food_establishment": {...},
        "line_items": [...]
      }
    }
  }
}
```

The `meta["ucp-agent"]` field is **required** on all requests to enable [capability negotiation](http://ucp.dev/draft/specification/overview/#negotiation-protocol). The `complete_checkout` and `cancel_checkout` operations also require `meta["idempotency-key"]` for retry safety — retrying `complete_checkout` without the same key risks sending the same order to the kitchen twice. Platforms **MAY** include additional metadata fields.

## Tools

UCP Capabilities map 1:1 to MCP Tools.

### Identifier Pattern

MCP tools separate resource identification from payload data:

- **Requests:** For operations on existing checkouts (`get`, `update`, `complete`, `cancel`), a top-level `id` parameter identifies the target resource. The `checkout` object in the request payload **MUST NOT** contain an `id` field.
- **Responses:** All responses include `checkout.id` as part of the full resource state.
- **Create:** The `create_checkout` operation does not require an `id` in the request, and the response includes the newly assigned `checkout.id`.

| Tool                | Operation                                                                                | Description                |
| ------------------- | ---------------------------------------------------------------------------------------- | -------------------------- |
| `create_checkout`   | [Create Checkout](http://ucp.dev/draft/specification/food/checkout/#create-checkout)     | Create a checkout session. |
| `get_checkout`      | [Get Checkout](http://ucp.dev/draft/specification/food/checkout/#get-checkout)           | Get a checkout session.    |
| `update_checkout`   | [Update Checkout](http://ucp.dev/draft/specification/food/checkout/#update-checkout)     | Update a checkout session. |
| `complete_checkout` | [Complete Checkout](http://ucp.dev/draft/specification/food/checkout/#complete-checkout) | Place the order.           |
| `cancel_checkout`   | [Cancel Checkout](http://ucp.dev/draft/specification/food/checkout/#cancel-checkout)     | Cancel a checkout session. |

The examples below follow the same order used in the [REST Binding](http://ucp.dev/draft/specification/food/checkout/rest/#examples): two customized pizzas and a salad from Luigi's, delivered ASAP with an 18% tip.

### `create_checkout`

Maps to the [Create Checkout](http://ucp.dev/draft/specification/food/checkout/#create-checkout) operation. The Platform sends the establishment and the configured dishes; the Business prices them and asks for a fulfillment method.

#### Input Schema

- `checkout` ([Checkout](http://ucp.dev/draft/specification/food/checkout/#create-checkout)): **Required**. Contains the establishment, dishes, and optional buyer and extension data.
  - Extensions (Optional):
    - `dev.ucp.food.fulfillment`: [Fulfillment](http://ucp.dev/draft/specification/food/extensions/fulfillment/index.md)
    - `dev.ucp.food.tip`: [Tip](http://ucp.dev/draft/specification/food/extensions/tip/index.md)
    - `dev.ucp.common.payment.ap2_mandate`: [AP2 Mandates](http://ucp.dev/draft/specification/payment/extensions/ap2-mandates/index.md)

#### Output Schema

- [Checkout](http://ucp.dev/draft/specification/food/checkout/#create-checkout) object.

#### Example

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "create_checkout",
    "arguments": {
      "meta": {
        "ucp-agent": {
          "profile": "https://platform.example/profiles/food-agent.json"
        }
      },
      "checkout": {
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
          {"type": "delivery", "fulfillable_on": "2026-04-10T18:25:00-07:00", "scheduling": "asap_and_scheduled"},
          {"type": "pickup", "fulfillable_on": "2026-04-10T18:15:00-07:00", "scheduling": "asap_and_scheduled"}
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

The kitchen has stopped taking orders — no checkout resource is created:

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
          "code": "location_closed",
          "content": "Luigi's is closed for the night. Ordering reopens at 11:00 AM.",
          "severity": "unrecoverable"
        }
      ],
      "continue_url": "https://food.example.com/"
    },
    "content": [
      {"type": "text", "text": "{\"ucp\":{…},…}"}
    ]
  }
}
```

### `get_checkout`

Maps to the [Get Checkout](http://ucp.dev/draft/specification/food/checkout/#get-checkout) operation. Use it to re-read Business-authored state (prices, delivery windows, tip resolution) or to poll while the checkout is `complete_in_progress`.

#### Input Schema

- `id` (String): **Required**. The ID of the checkout session.

#### Output Schema

- [Checkout](http://ucp.dev/draft/specification/food/checkout/#get-checkout) object.

### `update_checkout`

Maps to the [Update Checkout](http://ucp.dev/draft/specification/food/checkout/#update-checkout) operation. Update is a full replacement of the writable state: the Platform resends every line item (with its `id`), the buyer, the fulfillment selection, and the tip — anything omitted is removed.

The Platform **MUST NOT** start a new `update_checkout` operation while the Checkout is `complete_in_progress`. Duplicate requests remain subject to [Replay Protection](http://ucp.dev/draft/specification/signatures/#replay-protection). If the Business receives a new `update_checkout` request in that state, it **MUST** leave the Checkout unchanged and return the current Checkout with a recoverable error Message.

#### Input Schema

- `id` (String): **Required**. The ID of the checkout session to update.
- `checkout` ([Checkout](http://ucp.dev/draft/specification/food/checkout/#update-checkout)): **Required**. Contains the full writable checkout state.
  - Extensions (Optional):
    - `dev.ucp.food.fulfillment`: [Fulfillment](http://ucp.dev/draft/specification/food/extensions/fulfillment/index.md)
    - `dev.ucp.food.tip`: [Tip](http://ucp.dev/draft/specification/food/extensions/tip/index.md)
    - `dev.ucp.common.payment.ap2_mandate`: [AP2 Mandates](http://ucp.dev/draft/specification/payment/extensions/ap2-mandates/index.md)

#### Output Schema

- [Checkout](http://ucp.dev/draft/specification/food/checkout/#update-checkout) object.

#### Example

The Platform adds a delivery address and selects the 18% tip preset. The Business returns delivery options, drop-off preferences, fees, and the resolved tip line.

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "update_checkout",
    "arguments": {
      "meta": {
        "ucp-agent": {
          "profile": "https://platform.example/profiles/food-agent.json"
        }
      },
      "id": "chk_food_7187",
      "checkout": {
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

### `complete_checkout`

Maps to the [Complete Checkout](http://ucp.dev/draft/specification/food/checkout/#complete-checkout) operation. The Platform submits payment; the Business places the order with the kitchen and returns the order confirmation.

#### Input Schema

- `id` (String): **Required**. The ID of the checkout session.
- `checkout` ([Checkout](http://ucp.dev/draft/specification/food/checkout/#complete-checkout)): **Required**. Contains `payment` and optional `signals`.
  - Extensions (Optional):
    - `dev.ucp.common.payment.ap2_mandate`: [AP2 Mandates](http://ucp.dev/draft/specification/payment/extensions/ap2-mandates/index.md)

#### Output Schema

- [Checkout](http://ucp.dev/draft/specification/food/checkout/#complete-checkout) object.

**Note:** Response **MUST** include an `order` object (`id`, `tracking_url`, and optionally a pickup `label`) if completion succeeds. See [Order Confirmation & Tracking](http://ucp.dev/draft/specification/food/checkout/#order-confirmation-tracking).

#### Example

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "complete_checkout",
    "arguments": {
      "meta": {
        "ucp-agent": {
          "profile": "https://platform.example/profiles/food-agent.json"
        },
        "idempotency-key": "772d0622-941d-4e86-9a38-668877662222"
      },
      "id": "chk_food_7187",
      "checkout": {
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
  "id": 3,
  "result": {
    "structuredContent": {
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

### `cancel_checkout`

Maps to the [Cancel Checkout](http://ucp.dev/draft/specification/food/checkout/#cancel-checkout) operation. Cancels an in-progress checkout before an order is placed; it does not cancel an order the kitchen has already accepted.

#### Input Schema

- `id` (String): **Required**. The ID of the checkout session.

#### Output Schema

- [Checkout](http://ucp.dev/draft/specification/food/checkout/#cancel-checkout) object.

**Note:** Response **MUST** include `"status": "canceled"` if cancellation succeeds.

## Error Handling

UCP distinguishes between protocol errors and business outcomes. See the [Core Specification](http://ucp.dev/draft/specification/overview/#error-handling) for the complete error code registry and [Error Handling](http://ucp.dev/draft/specification/food/checkout/#error-handling) for the food-specific codes.

- **Protocol errors**: Transport-level failures (authentication, rate limiting, unavailability) that prevent request processing. Returned as JSON-RPC `error` with code `-32000` (or `-32001` for discovery errors).
- **Business outcomes**: Application-level results from successful request processing, returned as JSON-RPC `result` with UCP envelope and `messages`.

### Business Outcomes

Business outcomes — a sold-out dish, a closed kitchen, an address outside the delivery zone — are returned as JSON-RPC `result` with `structuredContent` containing the UCP envelope and `messages`:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "structuredContent": {
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
    },
    "content": [
      {"type": "text", "text": "{\"ucp\":{…},…}"}
    ]
  }
}
```

For `create_checkout`, when no checkout session can be created, the Business returns JSON-RPC `result` with `structuredContent` containing the UCP envelope and `messages` (see the `create_checkout` [Error Response](#create_checkout) example):

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
          "code": "location_closed",
          "content": "This location is no longer taking orders.",
          "severity": "unrecoverable"
        }
      ],
      "continue_url": "https://food.example.com/"
    },
    "content": [
      {"type": "text", "text": "{\"ucp\":{…},…}"}
    ]
  }
}
```

## Message Signing

Platforms **SHOULD** authenticate agents when using MCP transport. When using HTTP Message Signatures, all checkout operations follow the [Message Signatures](http://ucp.dev/draft/specification/signatures/index.md) specification.

### Request Signing

UCP's MCP transport uses **streamable HTTP**, allowing the same RFC 9421 signature mechanism as REST. The signature is applied at the HTTP layer:

| Header            | Required | Description                      |
| ----------------- | -------- | -------------------------------- |
| `Signature-Input` | Yes      | Describes signed components      |
| `Signature`       | Yes      | Contains the signature value     |
| `Content-Digest`  | Yes      | SHA-256 hash of request body     |
| `UCP-Agent`       | Yes      | Signer identity (profile URL)    |
| `Idempotency-Key` | Cond.\*  | Unique key for replay protection |

\* Required for `complete_checkout` and `cancel_checkout`

**Example Signed Request:**

```http
POST /mcp HTTP/1.1
Host: food.example.com
Content-Type: application/json
UCP-Agent: profile="https://platform.example/.well-known/ucp"
Idempotency-Key: 772d0622-941d-4e86-9a38-668877662222
Content-Digest: sha-256=:RK/0qy18MlBSVnWgjwz6lZEWjP/lF5HF9bvEF8FabDg=:
Signature-Input: sig1=("@method" "@authority" "@path" "content-digest" "content-type" "ucp-agent" "idempotency-key");keyid="platform-2026"
Signature: sig1=:MEUCIQDXyK9N3p5Rt...:

{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"complete_checkout","arguments":{"id":"chk_food_7187","checkout":{"payment":{...}}}}}
```

The `Content-Digest` binds the JSON-RPC body to the signature. No JSON canonicalization is required.

See [Message Signatures - MCP Transport](http://ucp.dev/draft/specification/signatures/#mcp-transport) for details.

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

{"jsonrpc":"2.0","id":3,"result":{"content":[{"type":"text","text":"..."}],"structuredContent":{"id":"chk_food_7187","status":"completed","order":{"id":"ord_food_9876543210","label":"#42",...}}}}
```

See [Message Signatures - REST Response Signing](http://ucp.dev/draft/specification/signatures/#rest-response-signing) for the signing algorithm (identical for MCP over HTTP).

## Conformance

A conforming MCP transport implementation **MUST**:

1. Implement JSON-RPC 2.0 protocol correctly.
1. Provide all core checkout tools defined in this specification.
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
- `checkout` contains the domain payload (body equivalent)
