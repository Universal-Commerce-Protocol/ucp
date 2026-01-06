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

# Checkout Capability

## Overview

Allows agents to facilitate the checkout session. The checkout has to be
finalized manually by the user through a trusted UI unless the AP2 Mandates
extension is supported.

The Merchant remains the Merchant of Record (MoR), and they don't need to become
PCI DSS compliant to support this Capability.

**Flow overview**

1.  Build Checkout Session: The User and optionally an Agent are in a loop
    adding items to the session.
2.  Handoff to a trusted UI: Once the User decides to checkout the Agent (if
    engaged) passes the control to a Trusted UI (passing the checkout session
    data)
3.  Manual Checkout: The User now interacts only with the Trusted UI to fill in
    sensitive fulfillment and payment details and submit the order. The Agent is
    not involved in this part, ensuring determinism.
4.  Completion & Return: The Trusted UI shows a "Thank You" page to confirm the
    order. Optionally, the User can be redirected back to the Agent, who may
    have already been notified of the completed purchase.

![High-level checkout flow sequence diagram](site:specification/images/ucp-checkout-flow.png)

**Payments**

On checkout creation, merchants are required to define a payment configuration.
The Checkout object includes `payment.handlers` which define the processing
specifications for collecting payment instruments (e.g., Google Pay, direct
tokenization). When the buyer submits payment, the agent populates the
`payment.instruments` array with the collected instrument data.

**Fulfillment**

Fulfillment will be an extension in the protocol instead of a core
construct to account for diverse use cases.

Fulfillment is optional in the checkout object. This is done to enable an agent
to perform checkout for digital goods without needing to furnish fulfillment
details more relevant for physical goods.

For physical goods (or digital goods needing fulfillment data) there is a flat
structured fulfillment option that works for single item, single destination
checkout that can be added to the checkout object as specified below.

The spec will introduce more advanced fulfillment constructs as extensions
in the future.

**Checkout Status Lifecycle**

The checkout `status` field indicates the current phase of the session and
determines what action is required next. The Merchant sets the status; the
Platform receives messages indicating what's needed to progress.

```
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
│ (agent can call  │         │
│Complete Checkout)│         │
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

**Status Values**

*   **`incomplete`**: Checkout session is missing required information or has
    issues that need resolution. Agent should inspect `messages` array for
    context and should attempt to resolve via Update Checkout.

*   **`requires_escalation`**: Checkout session requires information that
    cannot be provided via API, or buyer input is required. Agent should
    inspect `messages` to understand what's needed (see Error Handling below).
    If any `recoverable` errors exist, resolve those first.
    Then hand off to buyer via `continue_url`.

*   **`ready_for_complete`**: Checkout session has all necessary information
    and agent can finalize programmatically. Agent can call Complete Checkout.

*   **`complete_in_progress`**: Merchant is processing the Complete Checkout
    request.

*   **`completed`**: Order placed successfully.

*   **`canceled`**: Checkout session is invalid or expired. Agent should start
    a new checkout session if needed.

### Error Handling

The `messages` array contains errors, warnings, and informational messages
about the checkout state. Error messages include a `severity` field that
declares **who resolves the error**:

| Severity | Meaning | Agent Action |
|----------|---------|--------------|
| `recoverable` | Agent can fix via API | Resolve using Update Checkout |
| `requires_buyer_input` | Merchant requires input not available via API | Hand off via `continue_url` |
| `requires_buyer_review` | Buyer review and authorization is required | Hand off via `continue_url` |

Errors with `requires_*` severity contribute to `status: requires_escalation`.
Both result in buyer handoff, but represent different checkout states.
`requires_buyer_input` means the checkout is **incomplete** — the merchant
requires information their API doesn't support collecting programmatically.
`requires_buyer_review` means the checkout is **complete** — but policy,
regulatory, or entitlement rules require buyer authorization before order
placement (e.g., high-value order approval, first-purchase policy).

#### Error Processing Algorithm

When status is `incomplete` or `requires_escalation`, agents should process
errors as a prioritized stack. The example below illustrates a checkout with
three error types: a recoverable error (invalid phone), a buyer input
requirement (delivery scheduling), and a review requirement (high-value order).
The latter two require handoff and serve as explicit signals to the agent.
Merchants SHOULD surface such messages as early as possible, and agents SHOULD
prioritize resolving recoverable errors before initiating handoff.

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

```
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

The `continue_url` field enables checkout handoff from platform to merchant UI,
allowing the buyer to continue and finalize the checkout session.

### Availability

Merchants **MUST** provide `continue_url` when returning `status` =
`requires_escalation`. For all other non-terminal statuses (`incomplete`,
`ready_for_complete`, `complete_in_progress`), merchants
**SHOULD** provide `continue_url`. For terminal states (`completed`,
`canceled`), `continue_url` **SHOULD** be omitted.

### Format

The `continue_url` **MUST** be an absolute HTTPS URL and **SHOULD** preserve
checkout state for seamless handoff. Merchants MAY implement state preservation
using either approach:

#### Server-Side State (Recommended)

An opaque URL backed by server-side checkout state:

```
https://shop.example.com/checkout-sessions/{checkout_id}
```

-   Server maintains checkout state tied to `checkout_id`
-   Simple, secure, recommended for most implementations
-   URL lifetime typically tied to `expires_at`

#### Checkout Permalink

A stateless URL that encodes checkout state directly, allowing reconstruction
without server-side persistence. Merchants **SHOULD** implement support for this
format to facilitate checkout handoff and accelerated entry—for example, a
platform can prefill checkout state when initiating a buy-now flow.

> **Note:** Checkout permalinks are a REST-specific construct that extends the
> [REST transport binding](checkout-rest.md). Accessing a permalink returns a
> redirect to the checkout UI or renders the checkout page directly.

## Guidelines

(In addition to the overarching guidelines)

**Platform**

*   May engage an Agent to facilitate the checkout session (e.g. add items to
    the checkout session, select fulfillment address). However, the agent must
    hand over the checkout session to a trusted and deterministic UI for the
    user to review the checkout details and place the order.
*   May send the user from the trusted, deterministic UI back to the agent at
    any time. For example, when the user decides to exit the checkout screen to
    keep adding items to the cart.
*   May provide agent context when the platform indicates that the request was
    done by an agent.
*   **MUST** use `continue_url` when checkout status is `requires_escalation`.
*   May use `continue_url` to hand off to merchant UI in other situations.
*   When performing handoff, **SHOULD** prefer merchant-provided `continue_url`
    over platform-constructed checkout permalinks.

**Merchant**

*   Must send a confirmation email after the checkout has been completed.
*   Should provide accurate error messages.
*   The logic handling the checkout sessions must be deterministic.
*   **MUST** provide `continue_url` when returning `status` =
    `requires_escalation`.
*   **MUST** include at least one message with `severity: escalation` when
    returning `status` = `requires_escalation`.
*   **SHOULD** provide `continue_url` in all non-terminal checkout responses.
*   After a checkout session reaches the state "completed", it is considered
    immutable.

## Capability Definition

The `Checkout` object has different fields depending on the operation.

### Create Request Body

The following fields are used when creating a checkout session.

{{ schema_fields('checkout.create_req', 'checkout') }}

### Update Request Body

The following fields are used when updating a checkout session.

{{ schema_fields('checkout.update_req', 'checkout') }}

### Response Body

The following fields are returned by the server in a checkout response.

{{ schema_fields('checkout_resp', 'checkout') }}

## Operations

The Checkout capability defines the following logical operations.

| Operation | Description |
| :--- | :--- |
| **Create Checkout** | Initiates a new checkout session. Called as soon as a user adds an item to a cart. |
| **Get Checkout** | Retrieves the current state of a checkout session. |
| **Update Checkout** | Updates a checkout session. |
| **Complete Checkout** | Finalizes the checkout and places the order. |
| **Cancel Checkout** | Cancels a checkout session. |

### Create Checkout

To be invoked by the platform when the user has expressed purchase intent
(e.g., click on Buy) to initiate the checkout session with the item details.

Platform will use known information to construct `LineItem` (i.e. price,
title), it's possible the values in request will be different from what the
Merchant has. It's fine for the Merchant to return the most up-to-date values
for the `LineItem` in the response, while also setting a MessageInfo as part
of Message to indicate this inconsistency. Platform will always use what has
been returned from the Merchant via the response and may choose to display an
informational message pertaining to the price change. It is recommended that
to minimize discrepancies and a streamlined user experience the product data
(price/title etc.) provided by the merchant through the feeds should match
the actual attributes.

{{ method_fields('create_checkout', 'rest.openapi.json', 'checkout') }}

### Get Checkout

It provides the latest state of the checkout resource. After cancellation or
completion it is up to the merchant on what they return (i.e this can be a long
lived state or expire after a particular TTL (resulting in a 'not found'
error)). From the platform there is no specific enforcement for a TTL of the
checkout.
The platform will honor the TTL provided by the merchant via expires_at at the
time of checkout session creation.

{{ method_fields('get_checkout', 'rest.openapi.json', 'checkout') }}

### Update Checkout

The update operation performs a full replacement of the checkout resource.
The platform is required to send the entire checkout resource containing any
data updates to write-only data fields. The resource provided in the request
will replace the existing checkout session state on the merchant side.

{{ method_fields('update_checkout', 'rest.openapi.json', 'checkout') }}

### Complete Checkout

This is the final checkout placement call. To be invoked when the user has
committed to pay and place an order for the chosen items. The response of this
call is the checkout object with the placed `order_id` & `order_permalink_url`
in it. The returned `order_id` is persisted by the platform for mirroring the
state of the placed order. At the time of order persistence,
fields from the `Checkout` will be used to construct the order representation
(i.e. information like `line_items`, `fulfillment_options` will be used to
create the initial order representation).

After this call, other details will be updated through subsequent events
as the order, and its associated items, moves through the supply chain.

{{ method_fields('complete_checkout', 'rest.openapi.json', 'checkout') }}

### Cancel Checkout

This operation will be used to cancel a checkout session, if it can be canceled.
If the checkout session cannot be canceled (e.g. if the checkout session is
already canceled or completed), then the server should send back an error
indicating the operation is not allowed. Any checkout session with a status that
is not equal to completed or canceled should be cancelable.

{{ method_fields('cancel_checkout', 'rest.openapi.json', 'checkout') }}

## Transport Bindings

The abstract operations above are bound to specific transport protocols as
defined below:

*   [REST Binding](checkout-rest.md): RESTful API mapping using standard HTTP verbs and JSON payloads.
*   [MCP Binding](checkout-mcp.md): Model Context Protocol mapping for agentic interaction.
*   [Embedded Checkout Binding](embedded-checkout.md): JSON-RPC for powering embedded checkout.

## Entities

### Buyer

{{ schema_fields('buyer', 'checkout') }}

### Fulfillment Option

{{ extension_schema_fields('fulfillment.json#/$defs/fulfillment_option', 'checkout') }}

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

Merchants SHOULD provide all relevant links for the transaction. The following
are the recommended well-known types:

| Type | Description |
|------|-------------|
| `privacy_policy` | Link to the merchant's privacy policy |
| `terms_of_service` | Link to the merchant's terms of service |
| `refund_policy` | Link to the merchant's refund policy |
| `shipping_policy` | Link to the merchant's shipping policy |
| `faq` | Link to the merchant's frequently asked questions |

Merchants MAY define custom types for domain-specific needs. Consumers SHOULD
handle unknown types gracefully by displaying them using the `title` field or
omitting them.

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

### Postal Address

{{ schema_fields('postal_address', 'checkout') }}

### Response

{{ extension_schema_fields('capability.json#/$defs/response', 'checkout') }}

### Total

#### Total Response

{{ schema_fields('types/total_resp', 'checkout') }}

### UCP Checkout Response

{{ extension_schema_fields('ucp.json#/$defs/checkout_response', 'checkout') }}
