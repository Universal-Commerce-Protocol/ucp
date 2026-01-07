<!--
   Copyright 2025 Google LLC

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

# Checkout Capability - A2A Binding

This document specifies the Agent2Agent Protocol (A2A) binding for
[Checkout Capability](checkout.md).

## Transport Discovery

Merchants that support A2A transport must specify the agent card endpoint as
part of the transports in UCP Profile at /.well-known/ucp. This allows capable
platforms to interact with the merchant services over A2A Protocol.
```json
{
  "ucp": {
    "version": "2026-01-11",
    "services": {
      "dev.ucp.shopping": {
        "version": "2026-01-11",
        "spec": "https://ucp.dev/specs/shopping",
        "a2a": {
          "endpoint": "https://example-merchant.com/.well-known/agent-card.json"
        }
      }
    }
  }
}
```

## Shopping Agent Profile Advertisement

Shopping Agents/Client applications interacting with Merchant Agent must
send their profile URI as `UCP-Agent` request headers with every request.

```
UCP-Agent: profile="https://agent.example/profiles/v2025-11/shopping-agent.json"
Content-Type: application/json
```

### Header Mapping Reference

The following table defines the required headers for enabling an A2A Agent
to communicate UCP data types with client applications.

| Header Name | Description |
| :--- | :--- |
| `UCP-Agent` | Shopping Agent/Client application profile URI. |
| `X-A2A-Extensions` | UCP Extension URI (specified below). |

## A2A Interactions

The A2A Protocol provides a strong foundation for inter-agent communication.
[A2A extensions](https://a2a-protocol.org/latest/topics/extensions/) enable
communication between agents with structured data types. This enables merchants
building AI applications to leverage UCP data types for communication with
client applications.

The URI for UCP Extension
is https://ucp.dev/a2a/extensions/shopping?v=2026-01-11

Agents supporting UCP extension must advertise the extension and any optional
capabilities in their A2A Agent Card to allow client applications to activate
the extension.

```json
{
  "extensions": [
    {
      "uri": "https://ucp.dev/a2a/extensions/shopping?v=2026-01-11",
      "description": "Merchant agent supporting UCP",
      "params": {
        "capabilities": [
          {
            "name": "dev.ucp.shopping.fulfillment",
            "version": "2026-01-11"
          }
        ]
      }
    }
  ]
}
```

### Agent2Agent Negotiation

The merchant agents can leverage A2A Message objects for allowing interaction
with shopping agents/client applications. The A2A Message object returned by
the agent will return structured data as DataParts part of the message.
Client applications must pass the merchant agent generated contextId for
subsequent turns in a session to preserve the current context.

Merchant agents may also leverage A2A Task objects for scenarios where
applicable. In such scenarios, the Merchant agent will return Task objects
with appropriate payload for interaction with the client applications.
Client applications must pass the server generated taskId along with the
contextId for subsequent turns until the task is completed.

Client applications must be capable of handling further negotiation in the
same session even after a task reaches a terminal state (e.g. user places an
order and wants to place another order in the same context or if the task
reaches a failed state due to an exception). Client applications must reset the
taskId once a task reaches terminal state to allow further interactions with
the agent, although the current contextId can be reused for subsequent
interactions.

## Request idempotency

Merchant agents must leverage the messageId sent as part of the A2A message
to detect duplicate messages for client application retries.

## Checkout functionality

The Checkout capability allows consumers to manage items in a shopping cart
and complete the purchase process. The merchant agent typically integrates
with the merchant’s checkout APIs for offering this functionality.

The extension defines the data schema for representing the Checkout
functionality by Merchant Agent for any cart related actions, completing or
canceling the checkout. `Checkout` entity is a profile of an A2A Message.
The Checkout entity must be returned by the merchant agent to the client
applications that activate UCP-A2A Extension in a A2A Message DataPart.
The checkout object MUST be returned as part of a DataPart object with
key `a2a.ucp.checkout`.

**Request format:**
Agentic applications can accept natural language input from users interacting
 with the agent to identify the user’s intent, negotiate with the user to
 capture any required information and then invoke the appropriate tools to
 perform the operation. Inputs from client applications/platforms can be sent
 to the remote merchant agent as an A2A message.

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

**Response format:**
Following is an example response from a merchant agent implementing
Checkout functionality:

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

When a user is ready to make a payment, the PaymentData must be submitted
to the merchant agent to complete the checkout process. Payment data is a
structured data type specified as part of UCP. When processing a payment to
complete the checkout, the Payment data must be submitted to the merchant agent
as a DataPart with attribute name `a2a.ucp.checkout.payment_data`. Any
associated risk signals should be sent with attribute
name `a2a.ucp.checkout.risk_signals`.

Upon completion of the checkout process, the merchant agent must return the
 checkout object along with the order\_id and order\_permalink\_url attributes.

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
          "a2a.ucp.checkout.payment_data": {
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

**Response format:**
Following is an example response from a merchant agent implementing
Checkout functionality:

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
            ...baseCheckoutObject,
            "order_id": "<order_id>",
            "order_permalink_url": "<order_url>"
          }
        },
        "kind": "data"
      }
    ],
    "role": "agent"
  }
}

```

#### AP2 based Checkout Completion

Merchant agents can implement AP2 mandates extension that enables secure
exchange of user intents and authorizations for Agent-to-Agent payment
interactions. Merchants that support AP2 mandates extension for UCP must
specify this capability in the UCP discovery document and the A2A agent card.
The AP2 mandates extension is considered implicitly active when a Client
Application/Platform and Merchant Agent advertise AP2 capability in their
respective profiles.

When AP2 mandates extension is enabled, the Merchant Agent must create a
detached JWS for the Checkout object and must return the generated signature
as part of the DataPart as `ap2.merchant_authorization`.
This will allow the Client applications to cryptographically verify the
Checkout payload against the Merchant’s public keys.

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

When the user confirms the payment on a client application, the user signed
Checkout Mandate object and Payment Mandate object must be sent as a DataPart
to the Merchant Agent for completing the Checkout. The Payment data which
includes the Payment Mandate must be submitted as part of a DataPart
with attribute name `a2a.ucp.checkout.payment_data`. Signed Checkout Mandate
must be specified in the DataPart as`ap2.checkout_mandate`. The `token`
attribute part of the payment data contains the payment mandate. Refer
[AP2 Mandates Extension](ap2-mandates.md) documentation for more details
about verification and processing of the mandates to complete the checkout.

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
          "a2a.ucp.checkout.payment_data": {
            "id": "instr_1",
            "handler_id": "gpay",
            "type": "card",
            "description": "Visa •••• 1234",
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