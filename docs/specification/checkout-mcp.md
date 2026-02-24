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

# Checkout Capability - MCP Binding

This document specifies the Model Context Protocol (MCP) binding for the
[Checkout Capability](checkout.md).

## Protocol Fundamentals

### Discovery

Businesses advertise MCP transport availability through their UCP profile at
`/.well-known/ucp`.

```json
{
  "ucp": {
    "version": "2026-01-11",
    "services": {
      "dev.ucp.shopping": [
        {
          "version": "2026-01-11",
          "spec": "https://ucp.dev/specification/overview",
          "transport": "mcp",
          "schema": "https://ucp.dev/services/shopping/mcp.openrpc.json",
          "endpoint": "https://business.example.com/ucp/mcp"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.shopping.checkout": [
        {
          "version": "2026-01-11",
          "spec": "https://ucp.dev/specification/checkout",
          "schema": "https://ucp.dev/schemas/shopping/checkout.json"
        }
      ],
      "dev.ucp.shopping.fulfillment": [
        {
          "version": "2026-01-11",
          "spec": "https://ucp.dev/specification/fulfillment",
          "schema": "https://ucp.dev/schemas/shopping/fulfillment.json",
          "extends": "dev.ucp.shopping.checkout"
        }
      ]
    },
    "payment_handlers": {
      "com.example.vendor.delegate_payment": [
        {
          "id": "handler_1",
          "version": "2026-01-11",
          "spec": "https://example.vendor.com/specs/delegate-payment",
          "schema": "https://example.vendor.com/schemas/delegate-payment-config.json",
          "config": {}
        }
      ]
    }
  }
}
```

### Request Metadata

MCP clients **MUST** include a `meta` object in every request containing
protocol metadata:

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
          "profile": "https://platform.example/profiles/shopping-agent.json"
        },
        "idempotency-key": "550e8400-e29b-41d4-a716-446655440000"
      },
      "checkout": { ... }
    }
  }
}
```

The `meta["ucp-agent"]` field is **required** on all requests to enable
[capability negotiation](overview.md#negotiation-protocol). The
`complete_checkout` and `cancel_checkout` operations also require
`meta["idempotency-key"]` for retry safety. Platforms **MAY** include
additional metadata fields.

## Tools

UCP Capabilities map 1:1 to MCP Tools.

### Identifier Pattern

MCP tools separate resource identification from payload data:

* **Requests:** For operations on existing checkouts (`get`, `update`,
    `complete`, `cancel`), a top-level `id` parameter identifies the target
    resource. The `checkout` object in the request payload **MUST NOT** contain
    an `id` field.
* **Responses:** All responses include `checkout.id` as part of the full resource state.
* **Create:** The `create_checkout` operation does not require an `id` in the request, and the response includes the newly assigned `checkout.id`.

| Tool                | Operation                                          | Description                |
| :------------------ | :------------------------------------------------- | :------------------------- |
| `create_checkout`   | [Create Checkout](checkout.md#create-checkout)     | Create a checkout session. |
| `get_checkout`      | [Get Checkout](checkout.md#get-checkout)           | Get a checkout session.    |
| `update_checkout`   | [Update Checkout](checkout.md#update-checkout)     | Update a checkout session. |
| `complete_checkout` | [Complete Checkout](checkout.md#complete-checkout) | Place the order.           |
| `cancel_checkout`   | [Cancel Checkout](checkout.md#cancel-checkout)     | Cancel a checkout session. |

### `create_checkout`

Maps to the [Create Checkout](checkout.md#create-checkout) operation.

#### Input Schema

* `checkout` ([Checkout](checkout.md#create-checkout)): **Required**. Contains
    the initial checkout session data and optional extensions.
    * Extensions (Optional):
        * `dev.ucp.shopping.buyer_consent`: [Buyer Consent](buyer-consent.md)
        * `dev.ucp.shopping.fulfillment`: [Fulfillment](fulfillment.md)
        * `dev.ucp.shopping.discount`: [Discount](discount.md)
        * `dev.ucp.shopping.ap2_mandate`: [AP2 Mandates](ap2-mandates.md)

#### Output Schema

* [Checkout](checkout.md#create-checkout) object.

#### Example

=== "Request"

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
              "profile": "https://platform.example/profiles/v2026-01/shopping-agent.json"
            }
          },
          "checkout": {
            "buyer": {
              "email": "jane.doe@example.com",
              "first_name": "Jane",
              "last_name": "Doe"
            },
            "line_items": [
              {
                "item": {
                  "id": "item_123"
                },
                "quantity": 1
              }
            ],
            "currency": "USD",
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
        }
      }
    }
    ```

=== "Response"

    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "result": {
        "structuredContent": {
          "checkout": {
            "ucp": {
              "version": "2026-01-11",
              "capabilities": {
                "dev.ucp.shopping.checkout": [
                  {"version": "2026-01-11"}
                ],
                "dev.ucp.shopping.fulfillment": [
                  {"version": "2026-01-11"}
                ]
              },
              "payment_handlers": {
                "com.example.vendor.delegate_payment": [
                  {"id": "handler_1", "version": "2026-01-11", "config": {}}
                ]
              }
            },
            "id": "checkout_abc123",
            "status": "incomplete",
            "buyer": {
              "email": "jane.doe@example.com",
              "first_name": "Jane",
              "last_name": "Doe"
            },
            "line_items": [
              {
                "id": "item_123",
                "item": {
                  "id": "item_123",
                  "title": "Blue Jeans",
                  "price": 5000
                },
                "quantity": 1,
                "totals": [
                  {"type": "subtotal", "amount": 5000},
                  {"type": "total", "amount": 5000}
                ]
              }
            ],
            "currency": "USD",
            "totals": [
              {
                "type": "subtotal",
                "amount": 5000
              },
              {
                "type": "fulfillment",
                "display_text": "Shipping",
                "amount": 500
              },
              {
                "type": "total",
                "amount": 5500
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
            "links": [
              {
                "type": "privacy_policy",
                "url": "https://business.example.com/privacy"
              },
              {
                "type": "terms_of_service",
                "url": "https://business.example.com/terms"
              }
            ],
            "continue_url": "https://business.example.com/checkout-sessions/checkout_abc123",
            "expires_at": "2026-01-11T18:30:00Z"
          }
        },
        "content": [
          {
            "type": "text",
            "text": "{\"checkout\":{\"ucp\":{...},\"id\":\"checkout_abc123\",...}}"
          }
        ]
      }
    }
    ```

### `get_checkout`

Maps to the [Get Checkout](checkout.md#get-checkout) operation.

#### Input Schema

* `id` (String): **Required**. The ID of the checkout session.

#### Output Schema

* [Checkout](checkout.md#get-checkout) object.

### `update_checkout`

Maps to the [Update Checkout](checkout.md#update-checkout) operation.

#### Input Schema

* `id` (String): **Required**. The ID of the checkout session to update.
* `checkout` ([Checkout](checkout.md#update-checkout)): **Required**.
    Contains the updated checkout session data.
    * Extensions (Optional):
        * `dev.ucp.shopping.buyer_consent`: [Buyer Consent](buyer-consent.md)
        * `dev.ucp.shopping.fulfillment`: [Fulfillment](fulfillment.md)
        * `dev.ucp.shopping.discount`: [Discount](discount.md)
        * `dev.ucp.shopping.ap2_mandate`: [AP2 Mandates](ap2-mandates.md)

#### Output Schema

* [Checkout](checkout.md#update-checkout) object.

#### Example

=== "Request"

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
              "profile": "https://platform.example/profiles/v2026-01/shopping-agent.json"
            }
          },
          "id": "checkout_abc123",
          "checkout": {
            "buyer": {
              "email": "jane.doe@example.com",
              "first_name": "Jane",
              "last_name": "Doe"
            },
            "line_items": [
              {
                "item": {
                  "id": "item_123"
                },
                "quantity": 1
              }
            ],
            "currency": "USD",
            "fulfillment": {
              "methods": [
                {
                  "id": "shipping_1",
                  "line_item_ids": ["item_123"],
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
        }
      }
    }
    ```

=== "Response"

    ```json
    {
      "jsonrpc": "2.0",
      "id": 2,
      "result": {
        "structuredContent": {
          "checkout": {
            "ucp": {
              "version": "2026-01-11",
              "capabilities": {
                "dev.ucp.shopping.checkout": [
                  {"version": "2026-01-11"}
                ],
                "dev.ucp.shopping.fulfillment": [
                  {"version": "2026-01-11"}
                ]
              },
              "payment_handlers": {
                "com.example.vendor.delegate_payment": [
                  {"id": "handler_1", "version": "2026-01-11", "config": {}}
                ]
              }
            },
            "id": "checkout_abc123",
            "status": "incomplete",
            "buyer": {
              "email": "jane.doe@example.com",
              "first_name": "Jane",
              "last_name": "Doe"
            },
            "line_items": [
              {
                "id": "item_123",
                "item": {
                  "id": "item_123",
                  "title": "Blue Jeans",
                  "price": 5000
                },
                "quantity": 1,
                "totals": [
                  {"type": "subtotal", "amount": 5000},
                  {"type": "total", "amount": 5000}
                ]
              }
            ],
            "currency": "USD",
            "totals": [
              {
                "type": "subtotal",
                "amount": 5000
              },
              {
                "type": "fulfillment",
                "display_text": "Shipping",
                "amount": 1000
              },
              {
                "type": "total",
                "amount": 6000
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
            "links": [
              {
                "type": "privacy_policy",
                "url": "https://business.example.com/privacy"
              },
              {
                "type": "terms_of_service",
                "url": "https://business.example.com/terms"
              }
            ],
            "continue_url": "https://business.example.com/checkout-sessions/checkout_abc123",
            "expires_at": "2026-01-11T18:30:00Z"
          }
        },
        "content": [
          {
            "type": "text",
            "text": "{\"checkout\":{\"ucp\":{...},\"id\":\"checkout_abc123\",...}}"
          }
        ]
      }
    }
    ```

### `complete_checkout`

Maps to the [Complete Checkout](checkout.md#complete-checkout) operation.

#### Input Schema

* `meta` (Object): **Required**. Request metadata containing:
    * `ucp-agent` (Object): **Required**. Platform agent identification.
    * `idempotency-key` (String, UUID): **Required**. Unique key for retry safety.
* `id` (String): **Required**. The ID of the checkout session.
* `checkout` ([Checkout](checkout.md#complete-checkout)): **Required**.
    Contains payment credentials and other finalization data to execute the transaction.

#### Output Schema

* [Checkout](checkout.md#complete-checkout) object, containing a partial
   `order` that holds only `id` and `permalink_url`.

### `cancel_checkout`

Maps to the [Cancel Checkout](checkout.md#cancel-checkout) operation.

#### Input Schema

* `meta` (Object): **Required**. Request metadata containing:
    * `ucp-agent` (Object): **Required**. Platform agent identification.
    * `idempotency-key` (String, UUID): **Required**. Unique key for retry safety.
* `id` (String): **Required**. The ID of the checkout session.

#### Output Schema

* [Checkout](checkout.md#cancel-checkout) object with `status: canceled`.

## Error Handling

UCP distinguishes between protocol errors and business outcomes. See the
[Core Specification](overview.md#error-handling) for the complete error code
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

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "structuredContent": {
      "checkout": {
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
    },
    "content": [
      {"type": "text", "text": "{\"checkout\":{\"ucp\":{...},\"id\":\"checkout_abc123\",...}}"}
    ]
  }
}
```

## Message Signing

Platforms **SHOULD** authenticate agents when using MCP transport. When using
HTTP Message Signatures, all checkout operations follow the
[Message Signatures](signatures.md) specification.

### Request Signing

UCP's MCP transport uses **streamable HTTP**, allowing the same RFC 9421
signature mechanism as REST. The signature is applied at the HTTP layer:

| Header                   | Required | Description                              |
| :----------------------- | :------- | :--------------------------------------- |
| `Signature-Input`        | Yes      | Describes signed components              |
| `Signature`              | Yes      | Contains the signature value             |
| `Content-Digest`         | Yes      | SHA-256 hash of request body             |
| `UCP-Agent`              | Yes      | Signer identity (profile URL)            |
| `Idempotency-Key`        | Cond.*   | Unique key for replay protection         |

\* Required for `complete_checkout` and `cancel_checkout`

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

{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"complete_checkout","arguments":{"id":"checkout_abc123","checkout":{"payment":{...}}}}}
```

The `Content-Digest` binds the JSON-RPC body to the signature. No JSON
canonicalization is required.

See [Message Signatures - MCP Transport](signatures.md#mcp-transport)
for details.

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
Signature-Input: sig1=("@status" "content-digest" "content-type");keyid="merchant-2026"
Signature: sig1=:MFQCIH7kL9nM2oP5qR8sT1uV4wX6yZaB3cD...:

{"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"..."}],"structuredContent":{"checkout":{"id":"checkout_abc123","status":"completed"}}}}
```

See [Message Signatures - REST Response Signing](signatures.md#rest-response-signing)
for the signing algorithm (identical for MCP over HTTP).

## Conformance

A conforming MCP transport implementation **MUST**:

1. Implement JSON-RPC 2.0 protocol correctly.
2. Provide all core checkout tools defined in this specification.
3. Return errors per the [Core Specification](overview.md#error-handling).
4. Return business outcomes as JSON-RPC `result` with UCP envelope and
    `messages` array.
5. Validate tool inputs against UCP schemas.
6. Support HTTP transport with streaming.

A conforming implementation **SHOULD**:

1. Authenticate agents using one of the supported mechanisms (API keys, OAuth,
    mTLS, or HTTP Message Signatures per [Message Signatures](signatures.md)).
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
* `checkout` contains the domain payload (body equivalent)

**Example:** Given the `complete_checkout` operation defined in OpenRPC:

```json
{
  "method": "complete_checkout",
  "params": {
    "meta": {
      "ucp-agent": { "profile": "https://..." },
      "idempotency-key": "550e8400-e29b-41d4-a716-446655440000"
    },
    "id": "checkout_abc123",
    "checkout": { "payment": {...} }
  }
}
```

Implementers **MUST** expose this as an MCP `tools/call` endpoint:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "complete_checkout",
    "arguments": {
      "meta": {
        "ucp-agent": { "profile": "https://..." },
        "idempotency-key": "550e8400-e29b-41d4-a716-446655440000"
      },
      "id": "checkout_abc123",
      "checkout": { "payment": {...} }
    }
  }
}
```
