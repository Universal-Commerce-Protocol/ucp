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

# Checkout Capability

* **Capability Name:** `dev.ucp.shopping.checkout`
* **Version:** `2026-01-11`

## Overview

Allows platforms to facilitate checkout sessions. The checkout has to be
finalized manually by the user through a trusted UI unless the AP2 Mandates
extension is supported.

The business remains the Merchant of Record (MoR), and they don't need to become
PCI DSS compliant to accept card payments through this Capability.

### Flow overview

![High-level checkout flow sequence diagram](site:specification/images/ucp-checkout-flow.png)

### Payments

Payment handlers are discovered from the business's UCP profile at
`/.well-known/ucp` and checkout.ucp.payment_handlers. The handlers define
the processing specifications for collecting payment instruments
(e.g., Google Pay, Shop Pay). When the buyer submits payment, the platform
populates the `payment.instruments` array with the collected instrument data.

The `payment` object is optional on checkout creation and may be omitted for
use cases that don't require payment processing (e.g., quote generation, cart
management).

### Fulfillment

Fulfillment is modelled as an extension in UCP to account for diverse use cases.

Fulfillment is optional in the checkout object. This is done to enable a
platform to perform checkout for digital goods without needing to furnish
fulfillment details more relevant for physical goods.

### Checkout Status Lifecycle

The checkout `status` field indicates the current phase of the session and
determines what action is required next. The business sets the status; the
platform receives messages indicating what's needed to progress.

```text
┌────────────┐    ┌─────────────────────┐
│ incomplete │◀──▶│ requires_escalation │
└─────┬──────┘    │                     │
      │           │  (buyer handoff     │
      │           │   via continue_url) │
      │           └──────────┬──────────┘
      │                      │
      │ all info collected   │ continue_url
      ▼                      │
┌──────────────────┐         │
│ready_for_complete│         │
│                  │         │
│ (platform can    │         │
│ call Complete    │         │
│   Checkout).     │         │
└────────┬─────────┘         │
         │                   │
         │ Complete Checkout │
         ▼                   │
┌────────────────────┐       │
│complete_in_progress│       │
└─────────┬──────────┘       │
          │                  │
          └────────┬─────────┘
                   ▼
            ┌─────────────┐
            │  completed  │
            └─────────────┘

            ┌─────────────┐
            │  canceled   │  (session invalid/expired - can occur from any state)
            └─────────────┘
```

### Status Values

* **`incomplete`**: Checkout session is missing required information or has
    issues that need resolution. Platform should inspect `messages` array for
    context and should attempt to resolve via Update Checkout.

* **`requires_escalation`**: Checkout session requires information that
    cannot be provided via API, or buyer input is required. Platform should
    inspect `messages` to understand what's needed (see Error Handling below).
    If any `recoverable` errors exist, resolve those first.
    Then hand off to buyer via `continue_url`.

* **`ready_for_complete`**: Checkout session has all necessary information
    and platform can finalize programmatically. Platform can call
    Complete Checkout.

* **`complete_in_progress`**: Business is processing the Complete Checkout
    request.

* **`completed`**: Order placed successfully.

* **`canceled`**: Checkout session is invalid or expired. Platform should
    start a new checkout session if needed.

### Error Handling

The `messages` array contains errors, warnings, and informational messages
about the checkout state. Error messages include a `severity` field that
declares **who resolves the error**:

| Severity                | Meaning                                       | Platform Action               |
| :---------------------- | :-------------------------------------------- | :---------------------------- |
| `recoverable`           | Platform can fix via API                      | Resolve using Update Checkout |
| `requires_buyer_input`  | Business requires input not available via API | Hand off via `continue_url`   |
| `requires_buyer_review` | Buyer review and authorization is required    | Hand off via `continue_url`   |

Errors with `requires_*` severity contribute to `status: requires_escalation`.
Both result in buyer handoff, but represent different checkout states.

* `requires_buyer_input` means the checkout is **incomplete** — the business
requires information their API doesn't support collecting programmatically.
* `requires_buyer_review` means the checkout is **complete** — but policy,
regulatory, or entitlement rules require buyer authorization before order
placement (e.g., high-value order approval, first-purchase policy).

#### Error Processing Algorithm

When status is `incomplete` or `requires_escalation`, platforms should process
errors as a prioritized stack. The example below illustrates a checkout with
three error types: a recoverable error (invalid phone), a buyer input
requirement (delivery scheduling), and a review requirement (high-value order).
The latter two require handoff and serve as explicit signals to the platform.
Businesses **SHOULD** surface such messages as early as possible, and platforms
**SHOULD** prioritize resolving recoverable errors before initiating handoff.

```json
{
  "status": "requires_escalation",
  "messages": [
    {
      "type": "error",
      "code": "invalid_phone",
      "severity": "recoverable",
      "content": "Phone number format is invalid"
    },
    {
      "type": "error",
      "code": "schedule_delivery",
      "severity": "requires_buyer_input",
      "content": "Select delivery window for your purchase"
    },
    {
      "type": "error",
      "code": "high_value_order",
      "severity": "requires_buyer_review",
      "content": "Orders over $500 require additional verification"
    }
  ]
}
```

Example error processing algorithm:

```text
GIVEN checkout with messages array
FILTER errors FROM messages WHERE type = "error"

PARTITION errors INTO
  recoverable           WHERE severity = "recoverable"
  requires_buyer_input  WHERE severity = "requires_buyer_input"
  requires_buyer_review WHERE severity = "requires_buyer_review"

IF recoverable is not empty
  FOR EACH error IN recoverable
    ATTEMPT to fix error (e.g., reformat phone number)
  CALL Update Checkout
  RETURN and re-evaluate response

IF requires_buyer_input is not empty
  handoff_context = "incomplete, additional input from buyer is required"
ELSE IF requires_buyer_review is not empty
  handoff_context = "ready for final review by the buyer"
```

## Continue URL

The `continue_url` field enables checkout handoff from platform to business UI,
allowing the buyer to continue and finalize the checkout session.

### Availability

Businesses **MUST** provide `continue_url` when returning `status` =
`requires_escalation`. For all other non-terminal statuses (`incomplete`,
`ready_for_complete`, `complete_in_progress`), businesses **SHOULD** provide
`continue_url`. For terminal states (`completed`, `canceled`), `continue_url`
**SHOULD** be omitted.

### Format

The `continue_url` **MUST** be an absolute HTTPS URL and **SHOULD** preserve
checkout state for seamless handoff. Businesses **MAY** implement state
preservation using either approach:

#### Server-Side State (Recommended)

An opaque URL backed by server-side checkout state:

```text
https://business.example.com/checkout-sessions/{checkout_id}
```

* Server maintains checkout state tied to `checkout_id`
* Simple, secure, recommended for most implementations
* URL lifetime typically tied to `expires_at`

#### Checkout Permalink

A stateless URL that encodes checkout state directly, allowing reconstruction
without server-side persistence. Businesses **SHOULD** implement support for
this format to facilitate checkout handoff and accelerated entry—for example, a
platform can prefill checkout state when initiating a buy-now flow.

> **Note:** Checkout permalinks are a REST-specific construct that extends the
> [REST transport binding](checkout-rest.md). Accessing a permalink returns a
> redirect to the checkout UI or renders the checkout page directly.

## Guidelines

(In addition to the overarching guidelines)

### Platform

* **MAY** engage an agent to facilitate the checkout session (e.g. add items
    to the checkout session, select fulfillment address). However, the
    agent must hand over the checkout session to a trusted and
    deterministic UI for the user to review the checkout details and place the
    order.
* **MAY** send the user from the trusted, deterministic UI back to the agent
    at any time. For example, when the user decides to exit the checkout screen
    to keep adding items to the cart.
* **MAY** provide agent context when the platform indicates that the request
    was done by an agent.
* **MUST** use `continue_url` when checkout status is `requires_escalation`.
* **MAY** use `continue_url` to hand off to business UI in other situations.
* When performing handoff, **SHOULD** prefer business-provided
    `continue_url` over platform-constructed checkout permalinks.

### Business

* **MUST** send a confirmation email after the checkout has been completed.
* **SHOULD** provide accurate error messages.
* Logic handling the checkout sessions **MUST** be deterministic.
* **MUST** provide `continue_url` when returning `status` =
    `requires_escalation`.
* **MUST** include at least one message with `severity: escalation` when
    returning `status` = `requires_escalation`.
* **SHOULD** provide `continue_url` in all non-terminal checkout responses.
* After a checkout session reaches the state "completed", it is considered
    immutable.

## Capability Schema Definition

{{ schema_fields('checkout_resp', 'checkout') }}

## Operations

The Checkout capability defines the following logical operations.

| Operation             | Description                                                                        |
| :-------------------- | :--------------------------------------------------------------------------------- |
| **Create Checkout**   | Initiates a new checkout session. Called as soon as a user adds an item to a cart. |
| **Get Checkout**      | Retrieves the current state of a checkout session.                                 |
| **Update Checkout**   | Updates a checkout session.                                                        |
| **Complete Checkout** | Finalizes the checkout and places the order.                                       |
| **Cancel Checkout**   | Cancels a checkout session.                                                        |

### Create Checkout

To be invoked by the platform when the user has expressed purchase intent
(e.g., click on Buy) to initiate the checkout session with the item details.

**Recommendation**: To minimize discrepancies and a streamlined user experience,
product data (price/title etc.) provided by the business through the feeds
**SHOULD** match the actual attributes returned in the response.

{{ method_fields('create_checkout', 'rest.openapi.json', 'checkout') }}

### Get Checkout

It provides the latest state of the checkout resource. After cancellation or
completion it is up to the business on what to return (i.e this can be a long
lived state or expire after a particular TTL - resulting in a 'not found'
error). From the platform there is no specific enforcement for a TTL of the
checkout.

The platform will honor the TTL provided by the business via `expires_at` at the
time of checkout session creation.

{{ method_fields('get_checkout', 'rest.openapi.json', 'checkout') }}

### Update Checkout

Performs a full replacement of the checkout resource.
The platform is **REQUIRED** to send the entire checkout resource containing any
data updates to write-only data fields. The resource provided in the request
will replace the existing checkout session state on the business side.

{{ method_fields('update_checkout', 'rest.openapi.json', 'checkout') }}

### Complete Checkout

This is the final checkout placement call. To be invoked when the user has
committed to pay and place an order for the chosen items. The response of this
call is the checkout object with the `order` field populated in it. The returned
`order` provides necessary identifiers, such as `id` and `permalink_url`,
that can be used to reference the full state of the placed order.
At the time of order persistence, fields from `Checkout` **MAY** be used
to construct the order representation (i.e. information like `line_items`,
`fulfillment` will be used to create the initial order representation).

After this call, other details will be updated through subsequent events
as the order, and its associated items, moves through the supply chain.

{{ method_fields('complete_checkout', 'rest.openapi.json', 'checkout') }}

### Cancel Checkout

This operation will be used to cancel a checkout session, if it can be canceled.
If the checkout session cannot be canceled (e.g. checkout session is
already canceled or completed), then businesses **SHOULD** send back an error
indicating the operation is not allowed. Any checkout session with a status
that is not equal to `completed` or `canceled` **SHOULD** be cancelable.

{{ method_fields('cancel_checkout', 'rest.openapi.json', 'checkout') }}

## Transport Bindings

The abstract operations above are bound to specific transport protocols as
defined below:

* [REST Binding](checkout-rest.md): RESTful API mapping using standard HTTP verbs and JSON payloads.
* [MCP Binding](checkout-mcp.md): Model Context Protocol mapping for agentic interaction.
* [A2A Binding](checkout-a2a.md): Agent-to-Agent Protocol mapping for agentic interactions.
* [Embedded Checkout Binding](embedded-checkout.md): JSON-RPC for powering embedded checkout.

## Entities

### Buyer

{{ schema_fields('buyer', 'checkout') }}

### Fulfillment Option

{{ extension_schema_fields('fulfillment_resp.json#/$defs/fulfillment_option', 'checkout') }}

### Item

#### Item Create Request

{{ schema_fields('types/item.create_req', 'checkout') }}

#### Item Update Request

{{ schema_fields('types/item.update_req', 'checkout') }}

#### Item Response

{{ schema_fields('types/item_resp', 'checkout') }}

### Line Item

#### Line Item Create Request

{{ schema_fields('types/line_item.create_req', 'checkout') }}

#### Line Item Update Request

{{ schema_fields('types/line_item.update_req', 'checkout') }}

#### Line Item Response

{{ schema_fields('types/line_item_resp', 'checkout') }}

### Link

{{ schema_fields('types/link', 'checkout') }}

#### Well-Known Link Types

Businesses **SHOULD** provide all relevant links for the transaction. The
following are the recommended well-known types:

| Type               | Description                                       |
| :----------------- | :------------------------------------------------ |
| `privacy_policy`   | Link to the business's privacy policy             |
| `terms_of_service` | Link to the business's terms of service           |
| `refund_policy`    | Link to the business's refund policy              |
| `shipping_policy`  | Link to the business's shipping policy            |
| `faq`              | Link to the business's frequently asked questions |

Businesses **MAY** define custom types for domain-specific needs. Platforms
**SHOULD** handle unknown types gracefully by displaying them using the `title`
field or omitting them.

### Message

{{ schema_fields('message', 'checkout') }}

### Message Error

{{ schema_fields('types/message_error', 'checkout') }}

### Message Info

{{ schema_fields('types/message_info', 'checkout') }}

### Message Warning

{{ schema_fields('types/message_warning', 'checkout') }}

### Payment

#### Payment Create Request

{{ schema_fields('payment.create_req', 'checkout') }}

#### Payment Update Request

{{ schema_fields('payment.update_req', 'checkout') }}

#### Payment Response

{{ schema_fields('payment_resp', 'checkout') }}

### Payment Handler Response

{{ schema_fields('types/payment_handler_resp', 'checkout') }}

### Payment Instrument

{{ schema_fields('payment_instrument', 'checkout') }}

### Card Payment Instrument

{{ schema_fields('card_payment_instrument', 'checkout') }}

### Payment Credential

{{ schema_fields('payment_credential', 'checkout') }}

### Token Credential Response

{{ schema_fields('token_credential.create_req', 'checkout') }}

### Card Credential

{{ schema_fields('card_credential', 'checkout') }}

### Postal Address

{{ schema_fields('postal_address', 'checkout') }}

### Response

{{ extension_schema_fields('capability.json#/$defs/response_schema', 'checkout') }}

### Total

#### Total Response

{{ schema_fields('types/total_resp', 'checkout') }}

### UCP Response Checkout

{{ extension_schema_fields('ucp.json#/$defs/response_checkout_schema', 'checkout') }}

### Order Confirmation

{{ schema_fields('order_confirmation', 'checkout') }}
