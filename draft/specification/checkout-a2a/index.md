# Checkout Capability - A2A Binding

This document specifies the Agent2Agent Protocol (A2A) binding for [Checkout Capability](https://ucp.dev/draft/specification/checkout/index.md).

## Transport Discovery

Businesses that support A2A transport must specify the agent card endpoint as part of `services` in UCP Profile at `/.well-known/ucp`. This allows capable platforms to interact with the business services over A2A Protocol.

```json
{
  "ucp": {
    "version": "2026-01-11",
    "services": {
      "dev.ucp.shopping": [
        {
          "version": "2026-01-11",
          "spec": "https://ucp.dev/specification/overview",
          "transport": "a2a",
          "endpoint": "https://example-business.com/.well-known/agent-card.json"
        }
      ]
    }
  }
}
```

## Shopping Agent Profile Advertisement

Shopping platforms interacting with the business agent must send their profile URI as `UCP-Agent` request headers with every request.

```text
UCP-Agent: profile="https://agent.example/profiles/v2025-11/shopping-agent.json"
Content-Type: application/json
```

### Header Mapping Reference

The following table defines the required headers for enabling an A2A Agent to communicate UCP data types with platforms.

| Header Name        | Description                                |
| ------------------ | ------------------------------------------ |
| `UCP-Agent`        | Shopping platform application profile URI. |
| `X-A2A-Extensions` | UCP Extension URI (specified below).       |

## A2A Interactions

The A2A Protocol provides a strong foundation for inter-agent communication. [A2A extensions](https://a2a-protocol.org/latest/topics/extensions/) enable communication between agents with structured data types. This enables businesses to build AI applications to leverage UCP data types for communication with platforms.

The URI for UCP A2A extension: `https://ucp.dev/specification/reference?v=2026-01-11`

Businesses supporting UCP must advertise the extension and any optional capabilities in their A2A Agent Card to allow platforms to activate the extension.

An example:

```json
{
  "extensions": [
    {
      "uri": "https://ucp.dev/specification/reference?v=2026-01-11",
      "description": "Business agent supporting UCP",
      "params": {
        "capabilities": {
          "dev.ucp.shopping.checkout": [
            {"version": "2026-01-11"}
          ],
          "dev.ucp.shopping.fulfillment": [
            {
              "version": "2026-01-11",
              "extends": "dev.ucp.shopping.checkout"
            }
          ]
        }
      }
    }
  ]
}
```

### Agent2Agent Negotiation

The business agents can leverage A2A `Message` objects for allowing interaction with shopping agents/platforms. The A2A `Message` object returned by the agent will return structured data in `DataPart` objects within the message. Platforms must pass the business agent generated `contextId` for subsequent turns in a session to preserve the current context.

Business agents may also leverage A2A `Task` objects for scenarios where applicable. In such scenarios, the business agent will return `Task` objects with appropriate payload for interaction with the platforms. Platforms must pass the server generated `taskId` along with the `contextId` for subsequent turns until the task is completed.

Platforms must be capable of handling further negotiation in the same session even after a task reaches a terminal state (e.g. user places an order and wants to place another order in the same context or if the task reaches a failed state due to an exception). Platforms must reset the `taskId` once a task reaches terminal state to allow further interactions with the agent, although the current `contextId` can be reused for subsequent interactions.

## Request Idempotency

Business agents must leverage the `messageId` sent as part of the A2A `Message` to detect duplicate messages from platform retries.

## Checkout Functionality

The Checkout capability allows consumers to manage items in a checkout session and complete the purchase process. The business agent typically integrates with the business's checkout APIs for offering this functionality.

The extension defines the data schema for representing the Checkout functionality by business agent for any checkout related actions, completing or canceling the checkout. `Checkout` entity is a profile of an A2A `Message`. The Checkout entity must be returned by the business agent to the platform that activated UCP-A2A Extension in an A2A `Message`'s `DataPart`. The checkout object **MUST** be returned as part of a `DataPart` object with key `a2a.ucp.checkout`.

**Request format:** Agentic applications can accept natural language input from users interacting with the agent to identify the user's intent, negotiate with the user to capture any required information and then invoke the appropriate tools to perform the operation. Inputs from platforms can be sent to the remote business agent as an A2A `Message`.

Examples:

- Natural language input

```json
{
  "message": {
    "role": "user",
    "parts": [
      {
        "type": "text",
        "text": "add Pixel 10 Pro to my checkout"
      }
    ],
    "messageId": "69da8f87-991b-479e-80dc-ed92fcb57cbe",
    "kind": "message",
    "contextId": "aad14abc-4082-4748-84ca-4afff85aedfa"
  }
}
```

- Structured inputs on user actions

```json
{
  "message": {
    "role": "user",
    "parts": [
      {
        "type": "data",
        "data": {
          "action": "add_to_checkout",
          "product_id": "PIXEL-10-PRO",
          "quantity": 1
        }
      }
    ],
    "messageId": "e94a8c10-69f4-4c4c-b988-21a298302da6",
    "kind": "message",
    "contextId": "aad14abc-4082-4748-84ca-4afff85aedfa"
  }
}
```

**Response format:** Following is an example response from a business agent implementing Checkout functionality:

```json
{
  "id": 33,
  "jsonrpc": "2.0",
  "result": {
    "contextId": "4629ea79-7201-4ece-bc7a-ce19fff76e61",
    "kind": "message",
    "messageId": "8e8566e0-6d7c-4f29-bd90-26a132385baa",
    "parts": [
      {
        "data": {
          "a2a.ucp.checkout": {...checkoutObject}
        },
        "kind": "data"
      }
    ],
    "role": "agent"
  }
}
```

### Checkout Completion

When a user is ready to make a payment, `payment` must be submitted to the business agent to complete the checkout process. `payment` is a structured data type specified as part of UCP. When processing a payment to complete the checkout, `payment` must be submitted to the business agent as a `DataPart` with attribute name `a2a.ucp.checkout.payment`. Any associated risk signals should be sent with attribute name `a2a.ucp.checkout.risk_signals`.

Upon completion of the checkout process, the business agent must return the checkout object containing an `order` attribute with `id` and `permalink_url`.

**Request format:**

```json
{
  "message": {
    "role": "user",
    "parts": [
      {
        "type": "data",
        "data": {"action":"complete_checkout"}
      },
      {
        "kind": "data",
        "data": {
          "a2a.ucp.checkout.payment": {
            ...paymentObject
          },
          "a2a.ucp.checkout.risk_signals":{...content}
        }
      }
    ],
    "messageId": "e94a8c10-69f4-4c4c-b988-21a298302da6",
    "kind": "message",
    "contextId": "aad14abc-4082-4748-84ca-4afff85aedfa"
  }
}
```

**Response format:** Following is an example response from a business agent implementing Checkout functionality:

```json
{
  "id": 33,
  "jsonrpc": "2.0",
  "result": {
    "contextId": "4629ea79-7201-4ece-bc7a-ce19fff76e61",
    "kind": "message",
    "messageId": "8e8566e0-6d7c-4f29-bd90-26a132385baa",
    "parts": [
      {
        "data": {
          "a2a.ucp.checkout": { ...checkoutObject }
        },
        "kind": "data"
      }
    ],
    "role": "agent"
  }
}
```

#### AP2 based Checkout Completion

Business agents can implement AP2 mandates extension that enables secure exchange of user intents and authorizations for Agent-to-Agent payment interactions. Businesses that support AP2 mandates extension for UCP must specify this in the UCP discovery document and the A2A agent card. The AP2 mandates extension is considered implicitly active when a platform and business agent advertise AP2 mandates extension in their respective profiles.

When AP2 mandates extension is enabled, the business agent must create a detached JWS for the checkout object and must return the generated signature as part of the `DataPart` as `ap2.merchant_authorization`. This will allow the platform to cryptographically verify the checkout payload against the business's public keys.

```json
{
  "id": 33,
  "jsonrpc": "2.0",
  "result": {
    "contextId": "4629ea79-7201-4ece-bc7a-ce19fff76e61",
    "kind": "message",
    "messageId": "8e8566e0-6d7c-4f29-bd90-26a132385baa",
    "parts": [
      {
        "data": {
          "a2a.ucp.checkout": {
            ...checkoutObject,
            "ap2": {
              "merchant_authorization": "<detached jws signature>"
            }
          }
        },
        "kind": "data"
      }
    ],
    "role": "agent"
  }
}
```

When the user confirms the payment on a platform, the user signed checkout and payment mandate objects must be sent as `DataPart`s to the business agent for completing checkout. The `payment` which includes the payment mandate must be submitted as part of a `DataPart` with attribute name `a2a.ucp.checkout.payment`. Signed checkout mandate must be specified in the `DataPart` as `ap2.checkout_mandate`. The `token` attribute of `payment.instruments[*].credential` contains the payment mandate. Refer to [AP2 Mandates Extension](https://ucp.dev/draft/specification/ap2-mandates/index.md) documentation for more details about verification and processing of the mandates to complete the checkout.

**Request format:**

```json
{
  "message": {
    "role": "user",
    "parts": [
      {
        "type": "data",
        "data": {
          "action": "complete_checkout"
        }
      },
      {
        "kind": "data",
        "data": {
          "a2a.ucp.checkout.payment": {
            "instruments": [
              {
                "id": "instr_1",
                "handler_id": "gpay_1234",
                "type": "card",
                "selected": true,
                "display": {
                  "description": "Visa •••• 1234",
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
          "ap2": {
            "checkout_mandate": "eyJhbGciOiJFUz..."
          }
        }
      }
    ],
    "messageId": "e94a8c10-69f4-4c4c-b988-21a298302da6",
    "kind": "message",
    "contextId": "aad14abc-4082-4748-84ca-4afff85aedfa"
  }
}
```
