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

# Checkout Capability - EP Binding

## Introduction

Embedded Checkout Protocol (ECP) is a checkout-specific implementation of
UCP's Embedded Protocol (EP) transport binding that enables a
**host** to embed a **business's** checkout interface, receive events as the
buyer interacts with the checkout, and delegate key user actions such as address
and payment selection. ECP is a transport binding (like REST)—it defines **how**
to communicate, not **what** data exists.

### W3C Payment Request Conceptual Alignment

ECP draws inspiration from the
**[W3C Payment Request API](https://www.w3.org/TR/payment-request/){ target="_blank" }**,
adapting its mental model for embedded checkout scenarios. Developers familiar
with Payment Request will recognize similar patterns, though the execution model
differs:

**W3C Payment Request:** Browser-controlled. The business calls `show()` and the
browser renders a native payment sheet. Events flow from the payment handler to
the business.

**Embedded Checkout:** Business-controlled. The host embeds the business's
checkout UI in an iframe/webview. Events flow bidirectionally, with optional
delegation allowing the host to handle specific interactions natively.

<!-- cSpell:ignore paymentmethodchange -->
| Concept                   | W3C Payment Request              | Embedded Checkout                                                   |
| :------------------------ | :------------------------------- | :------------------------------------------------------------------ |
| **Initialization**        | `new PaymentRequest()`           | Load embedded context with `continue_url`                           |
| **UI Ready**              | `show()` returns Promise         | `ec.start` notification                                             |
| **Payment Method Change** | `paymentmethodchange` event      | `ec.payment.change` notification                                    |
| **Address Change**        | `shippingaddresschange` event    | `ec.fulfillment.change` and `ec.fulfillment.address_change_request` |
| **Submit Payment**        | User accepts → `PaymentResponse` | Delegated `ec.payment.credential_request`                           |
| **Completion**            | `response.complete()`            | `ec.complete` notification                                          |
| **Errors/Messages**       | Promise rejection                | `ec.messages.change` notification                                   |

**Key difference:** In W3C Payment Request, the browser orchestrates the payment
flow. In Embedded Checkout, the business orchestrates within the embedded
context, optionally delegating specific UI (payment method selection, address
picker) to the host for native experiences.

## Terminology & Actors

### Commerce Roles

- **Business:** The seller providing goods/services and the checkout
    experience.
- **Buyer:** The end user making a purchase.

### Technical Components

- **Host:** The application embedding the checkout (e.g., AI Agent app,
    Super
    App, Browser). Responsible for the **Payment Handler** and user
    authentication.
- **Embedded Checkout:** The business's checkout interface rendered in an
    iframe or webview. Responsible for the checkout flow and order creation.
- **Payment Handler:** The secure component that performs user authentication
    (biometric/PIN) and credential issuance.

## Requirements

### Discovery

ECP availability is signaled at two levels: service-level discovery declares
capability, checkout responses confirm availability and allowed per-session configuration.

#### Service-Level Discovery

When a business advertises the `embedded` transport in their `/.well-known/ucp`
profile, they declare support for the Embedded Checkout Protocol.

**Service Discovery Example:**

```json
{
    "services": {
        "dev.ucp.shopping": [
            {
                "version": "2026-01-11",
                "transport": "rest",
                "schema": "https://ucp.dev/services/shopping/openapi.json",
                "endpoint": "https://merchant.example.com/ucp/v1"
            },
            {
                "version": "2026-01-11",
                "transport": "mcp",
                "schema": "https://ucp.dev/services/shopping/mcp.openrpc.json",
                "endpoint": "https://merchant.example.com/ucp/mcp"
            },
            {
                "version": "2026-01-11",
                "transport": "embedded",
                "schema": "https://ucp.dev/services/shopping/embedded.openrpc.json"
            }
        ]
    }
}
```

When `embedded` is absent from the service definition, the business only
supports redirect-based checkout continuation via `continue_url`.

#### Per-Checkout Configuration

Service-level discovery declares that a business supports ECP, but does not
guarantee that every checkout session will enable it. Businesses **MUST** include
an embedded service binding with `config.delegate` in checkout responses to
indicate ECP availability and allowed delegations for a specific session.

**Checkout Response Example:**

```json
{
    "id": "checkout_abc123",
    "status": "open",
    "continue_url": "https://merchant.example.com/checkout/abc123",
    "ucp": {
        "version": "2026-01-11",
        "services": {
            "dev.ucp.shopping": [
                {
                    "version": "2026-01-11",
                    "transport": "embedded",
                    "config": {
                        "delegate": ["payment.credential", "fulfillment.address_change"]
                    }
                }
            ]
        },
        "capabilities": {...},
        "payment_handlers": {...}
    }
}
```

The `config.delegate` array confirms the delegations the business accepted for
this checkout session—the intersection of what the host requested via
`ec_delegate` and what the business allows. This may vary based on:

- **Cart contents**: Some products may require business-handled payment flows
- **Agent authorization**: Authenticated agents may receive more delegations
- **Business policy**: Risk rules, regional restrictions, etc.

When an embedded service binding with `config.delegate` is present:

- ECP is available for this checkout via `continue_url`
- `config.delegate` confirms which delegations the business accepted
- This mirrors the `delegate` field in the `ec.ready` handshake

When the embedded service binding is absent from a checkout response (even if
service-level discovery advertises embedded support), the checkout only supports
redirect-based continuation via `continue_url`.

### Loading an Embedded Checkout URL

When a host receives a checkout response with an embedded service binding, it
**MAY** initiate an ECP session by loading the `continue_url` in an embedded
context.

Before loading the embedded context, the host **SHOULD**:

1. Check `config.delegate` for available delegations
2. Prepare handlers for delegations the host wants to support
3. Optionally prepare authentication credentials if required by the business

To initiate the session, the host **MUST** augment the `continue_url` with ECP
query parameters using the `ec_` prefix.

All ECP parameters are passed via URL query string, not HTTP headers, to ensure
maximum compatibility across different embedding environments. Parameters use
the `ec_` prefix to avoid namespace pollution and clearly distinguish ECP
parameters from business-specific query parameters:

- `ec_version` (string, **REQUIRED**): The UCP version for this session
    (format: `YYYY-MM-DD`). Must match the version from the checkout response.
- `ec_auth` (string, **OPTIONAL**): Authentication token in business-defined
    format
- `ec_delegate` (string, **OPTIONAL**): Comma-delimited list of delegations
    the host wants to handle. **SHOULD** be a subset of `config.delegate`
    from the embedded service binding.
- `ec_color_scheme` (string, **OPTIONAL**): The color scheme preference for
    the checkout UI. Valid values: `light`, `dark`. When not provided, the
    Embedded Checkout follows system preference.

#### Authentication

**Token Format:**

- The `auth` parameter format is entirely business-defined
- Common formats include JWT, OAuth tokens, API keys, or session identifiers
- Businesses **MUST** document their expected token format and validation process

**Example (Informative - JWT-based):**

```json
// One possible implementation using JWT
{
  "alg": "HS256",
  "typ": "JWT"
}
{
  "iat": 1234567890,
  "exp": 1234568190,
  "jti": "unique-id",
  // ... business-specific claims ...
}
```

Businesses **MUST** validate authentication according to their security
requirements.

**Example initialization with authentication:**

```text
https://example.com/checkout/abc123?ec_version=2026-01-11&ec_auth=eyJ...
```

Note: All query parameter values must be properly URL-encoded per RFC 3986.

#### Delegation

The optional `ec_delegate` parameter declares which operations the host wants
to handle natively, instead of having a buyer handle them in the Embedded
Checkout UI. Each delegation identifier maps to a corresponding `_request`
message following a consistent pattern: `ec.{delegation}_request`

**Example delegation identifiers:**

| `ec_delegate` value          | Corresponding message                   |
| ---------------------------- | --------------------------------------- |
| `payment.instruments_change` | `ec.payment.instruments_change_request` |
| `payment.credential`         | `ec.payment.credential_request`         |
| `fulfillment.address_change` | `ec.fulfillment.address_change_request` |

Extensions define their own delegation identifiers; see each extension's
specification for available options.

```text
?ec_version=2026-01-11&ec_delegate=payment.instruments_change,payment.credential,fulfillment.address_change
```

#### Color Scheme

The optional `ec_color_scheme` parameter allows the host to specify which color
scheme the Embedded Checkout should use, enabling visual consistency between
the host application and the checkout UI.

**Valid Values:**

| Value   | Description                                          |
| :------ | :--------------------------------------------------- |
| `light` | Use light color scheme (light background, dark text) |
| `dark`  | Use dark color scheme (dark background, light text)  |

**Default Behavior:**

When `ec_color_scheme` is not provided, the Embedded Checkout can
use the buyer's system preference via the
[`prefers-color-scheme`](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-color-scheme)
media query or the
[`Sec-CH-Prefers-Color-Scheme`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Sec-CH-Prefers-Color-Scheme)
HTTP client hint, and **SHOULD** listen for changes and update accordingly.

**Implementation Notes:**

- By default, the Embedded Checkout **SHOULD** respect the buyer's system
  color scheme preference and listen for changes to update accordingly
- When `ec_color_scheme` is explicitly provided, it **MUST** override the
  system preference, be applied immediately upon load, and be enforced
  for the duration of the session.
- Businesses **MAY** ignore unsupported values

**Example:**

```text
https://example.com/checkout/abc123?ec_version=2026-01-11&ec_color_scheme=dark
```

#### Delegation Negotiation

Delegation follows a narrowing chain from business policy to final acceptance:

```text
config.delegate ⊇ ec_delegate ⊇ ec.ready delegate
```

1. **Business allows** (`config.delegate` in checkout response): The set of
    delegations the business permits for this checkout session
2. **Host requests** (`ec_delegate` URL parameter): The subset the host wants
    to handle natively
3. **ECP accepts** (`delegate` in `ec.ready`): The final subset the Embedded
    Checkout will actually delegate

Each stage is a subset of the previous:

- The host **SHOULD** only request delegations present in `config.delegate`
- The business **SHOULD NOT** accept delegations not present in
    `config.delegate` and **MUST** confirm accepted delegations in `ec.ready`

### Delegation Contract

Delegation creates a binding contract between the host and Embedded Checkout.
However, the Embedded Checkout **MAY** restrict delegation to authenticated or
approved hosts based on business policy.

#### Delegation Acceptance

The Embedded Checkout determines which delegations to honor based on:

- Authentication status (via `ec_auth` parameter)
- host authorization level
- Business policy

The Embedded Checkout **MUST** indicate accepted delegations in the `ec.ready`
request via the `delegate` field (see [`ec.ready`](#ecready)). If a
requested delegation is not accepted, the Embedded Checkout **MUST** handle that
capability using its own UI.

#### Binding Requirements

**Once delegation is accepted**, both parties enter a binding contract:

**Embedded Checkout responsibilities:**

1. **MUST** fire the appropriate `{action}_request` message when that action is
    triggered
2. **MUST** wait for the host's response before proceeding
3. **MUST NOT** show its own UI for that delegated action

**Host responsibilities:**

1. **MUST** respond to every `{action}_request` message it receives
2. **MUST** respond with an appropriate error if the user cancels
3. **SHOULD** show loading/processing states while handling delegation

#### 3.3.3 Delegation Flow

1. **Request**: Embedded Checkout sends an `ec.{capability}.{action}_request`
    message with current state (includes `id`)
2. **Native UI**: Host presents native UI for the delegated action
3. **Response**: host sends back a JSON-RPC response with matching `id` and
    `result` or `error`
4. **Update**: Embedded Checkout updates its state and may send subsequent
    change notifications

See [Payment Extension](#payment-extension) and
[Fulfillment Extension](#fulfillment-extension) for
capability-specific delegation details.

### Navigation Constraints

When checkout is rendered in embedded mode, the implementation **SHOULD**
prevent off-checkout navigation to maintain a focused checkout experience.
The embedded view is intended to provide a checkout flow, not a general-purpose
browser.

**Navigation Requirements:**

- The embedded checkout **SHOULD** block or intercept navigation attempts to
    URLs outside the checkout flow
- The embedded checkout **SHOULD** remove or disable UI elements that would
    navigate away from checkout (e.g., external links, navigation bars)
- The embedder **MAY** implement additional navigation restrictions at the
    container level

**Permitted Exceptions:** The following navigation scenarios **MAY** be allowed
when required for checkout completion:

- Payment provider redirects: off-site payment flows
- 3D Secure verification: card authentication frames and redirects
- Bank authorization: open banking or similar authorization flows
- Identity verification: KYC/AML compliance checks when required

These exceptions **SHOULD** return the user to the checkout flow upon
completion.

## Transport & Messaging

### Message Format

All ECP messages **MUST** use JSON-RPC 2.0 format
([RFC 7159](https://datatracker.ietf.org/doc/html/rfc7159)). Each message **MUST** contain:

- `jsonrpc`: **MUST** be `"2.0"`
- `method`: The message name (e.g., `"ec.start"`)
- `params`: Message-specific payload (may be empty object)
- `id`: (Optional) Present only for requests that expect responses

### Message Types

**Requests** (with `id` field):

- Require a response from the receiver
- **MUST** include a unique `id` field
- Receiver **MUST** respond with matching `id`
- Response **MUST** be either a `result` or `error` object
- Used for operations requiring acknowledgment or data

**Notifications** (without `id` field):

- Informational only, no response expected
- **MUST NOT** include an `id` field
- Receiver **MUST NOT** send a response
- Used for state updates and informational events

### Response Handling

For requests (messages with `id`), receivers **MUST** respond with either:

**Success Response:**

```json
{ "jsonrpc": "2.0", "id": "...", "result": {...} }
```

**Error Response:**

```json
{ "jsonrpc": "2.0", "id": "...", "error": {...} }
```

### Communication Channels

#### Communication Channel for Web-Based Hosts

When the host is a web application, communication starts using `postMessage`
between the host and Checkout windows. The host **MUST** listen for
`postMessage` calls from the embedded window, and when a message is received,
they **MUST** validate the origin matches the `checkout_url` used to start the
checkout.

Upon validation, the host **MAY** create a `MessageChannel`, and transfer one of
its ports in the result of the [`ec.ready` response](#ecready). When a host
responds with a `MessagePort`, all subsequent messages **MUST** be sent over
that channel. Otherwise, the host and business **MUST** continue using
`postMessage()` between their `window` objects, including origin validation.

#### Communication Channel for Native Hosts

When the host is a native application, they MUST inject globals into the
Embedded Checkout that allows `postMessage` communication between the web and
native environments. The host **MUST** create at least one of the following
globals:

- `window.EmbeddedCheckoutProtocolConsumer` (preferred)
- `window.webkit.messageHandlers.EmbeddedCheckoutProtocolConsumer`

This object **MUST** implement the following interface:

```javascript
{
  postMessage(message: string): void
}
```

Where `message` is a JSON-stringified JSON-RPC 2.0 message. The host **MUST**
parse the JSON string before processing.

For messages traveling from the host to the Embedded Checkout, the host **MUST**
inject JavaScript in the webview that will call
`window.EmbeddedCheckoutProtocol.postMessage()` with the JSON RPC message. The
Embedded Checkout **MUST** initialize this global object — and start listening
for `postMessage()` calls — before the `ec.ready` message is sent.

## Message API Reference

### Message Categories

#### Core Messages

Core messages are defined by the ECP specification and **MUST** be supported by
all implementations. All messages are sent from Embedded Checkout to host.

| Category         | Purpose                                                 | Pattern      | Core Messages                                                                        |
| :--------------- | :------------------------------------------------------ | :----------- | :----------------------------------------------------------------------------------- |
| **Handshake**    | Establish connection between host and Embedded Checkout | Request      | `ec.ready`                                                                           |
| **Lifecycle**    | Inform of checkout state transitions                    | Notification | `ec.start`, `ec.complete`                                                            |
| **State Change** | Inform of checkout field changes                        | Notification | `ec.line_items.change`, `ec.buyer.change`, `ec.payment.change`, `ec.messages.change` |

#### Extension Messages

Extensions **MAY** extend the Embedded protocol by defining additional messages.
Extension messages **MUST** follow the naming convention:

- **Notifications**: `ec.{capability}.change` — state change notifications (no
    `id`)
- **Delegation requests**: `ec.{capability}.{action}_request` — requires
    response (has `id`)

Where:

- `{capability}` matches the capability identifier from discovery
- `{action}` describes the specific action being delegated (e.g.,
    `instruments_change`, `address_change`)
- `_request` suffix signals this is a delegation point requiring a response

### Handshake Messages

#### `ec.ready`

Upon rendering, the Embedded Checkout **MUST** broadcast readiness to the parent
context using the `ec.ready` message. This message initializes a secure
communication channel between the host and Embedded Checkout, communicates which
delegations were accepted, and allows the host to provide additional,
display-only state for the checkout that was not communicated over UCP checkout
actions.

- **Direction:** Embedded Checkout → host
- **Type:** Request
- **Payload:**
    - `delegate` (array of strings, **REQUIRED**): List of delegation
        identifiers accepted by the Embedded Checkout. **MUST** be a subset of
        both `ec_delegate` (what host requested) and `config.delegate` from the
        checkout response (what business allows). An empty array means no
        delegations were accepted.

**Example Message (no delegations accepted):**

```json
{
    "jsonrpc": "2.0",
    "id": "ready_1",
    "method": "ec.ready",
    "params": {
        "delegate": []
    }
}
```

**Example Message (delegations accepted):**

```json
{
    "jsonrpc": "2.0",
    "id": "ready_1",
    "method": "ec.ready",
    "params": {
        "delegate": ["payment.credential", "fulfillment.address_change"]
    }
}
```

The `ec.ready` message is a request, which means that the host **MUST** respond
to complete the handshake.

- **Direction:** host → Embedded Checkout
- **Type:** Response
- **Result Payload:**
    - `upgrade` (object, **OPTIONAL**): An object describing how the Embedded
        Checkout should update the communication channel it uses to communicate
        with the host.
    - `checkout` (object, **OPTIONAL**): Additional, display-only state for
        the checkout that was not communicated over UCP checkout actions. This
        is used to populate the checkout UI, and may only be used to populate
        the following fields, under specific conditions:
        - `payment.instruments`: can be overwritten when the host and Embedded
            Checkout both accept the `payment.instruments_change` delegation.

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "id": "ready_1",
    "result": {}
}
```

Hosts **MAY** respond with an `upgrade` field to update the communication
channel between host and Embedded Checkout. Currently, this object only supports
a `port` field, which **MUST** be a `MessagePort` object, and **MUST** be
transferred to the embedded checkout context (e.g., with `{transfer: [port2]}`
on the host's `iframe.contentWindow.postMessage()` call):

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "id": "ready_1",
    "result": {
        "upgrade": {
            "port": "[Transferable MessagePort]"
        }
    }
}
```

When the host responds with an `upgrade` object, the Embedded Checkout **MUST**
discard any other information in the message, send a new `ec.ready` message
over the upgraded communication channel, and wait for a new response. All
subsequent messages **MUST** be sent only over the upgraded communication
channel.

The host **MAY** also respond with a `checkout` object, which will be used to
populate the checkout UI according to the delegation contract between host and
business.

**Example Message: Providing payment instruments, including display
information:**

```json
{
    "jsonrpc": "2.0",
    "id": "ready_1",
    "result": {
        "checkout": {
            "payment": {
                // The instrument structure is defined by the handler's instrument schema
                "instruments": [
                    {
                        "id": "payment_instrument_123",
                        "handler_id": "merchant_psp_handler_123",
                        "type": "card",
                        "selected": true,
                        "display": {
                            "brand": "visa",
                            "expiry_month": 12,
                            "expiry_year": 2026,
                            "last_digits": "1111",
                            "description": "Visa •••• 1111",
                            "card_art": "https://host.com/cards/visa-gold.png"
                        }
                    }
                ]
            }
        }
    }
}
```

### Lifecycle Messages

#### `ec.start`

Signals that checkout is visible and ready for interaction.

- **Direction:** Embedded Checkout → host
- **Type:** Notification
- **Payload:**
    - `checkout`: The latest state of the checkout, using the same structure
        as the `checkout` object in UCP responses.

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "method": "ec.start",
    "params": {
        "checkout": {
            "id": "checkout_123",
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
            "totals": [/* ... */],
            "line_items": [/* ... */],
            "buyer": {/* ... */},
            "payment": {/* ... */}
        }
    }
}
```

#### `ec.complete`

Indicates successful checkout completion.

- **Direction:** Embedded Checkout → host
- **Type:** Notification
- **Payload:**
    - `checkout`: The latest state of the checkout, using the same structure
        as the `checkout` object in UCP responses.

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "method": "ec.complete",
    "params": {
        "checkout": {
            "id": "checkout_123",
            // ... other checkout fields
            "order": {
                "id": "ord_99887766",
                "permalink_url": "https://merchant.com/orders/ord_99887766"
            }
        }
    }
}
```

### State Change Messages

State change messages inform the embedder of changes that have already occurred
in the checkout interface. These are informational only. The checkout has
already applied the changes and rendered the updated UI.

#### `ec.line_items.change`

Line items have been modified (quantity changed, items added/removed) in the
checkout UI.

- **Direction:** Embedded Checkout → host
- **Type:** Notification
- **Payload:**
    - `checkout`: The latest state of the checkout

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "method": "ec.line_items.change",
    "params": {
        "checkout": {
            "id": "checkout_123",
            // The entire checkout object is provided, including the updated line items and totals
            "totals": [
                /* ... */
            ],
            "line_items": [
                /* ... */
            ]
            // ...
        }
    }
}
```

#### `ec.buyer.change`

Buyer information has been updated in the checkout UI.

- **Direction:** Embedded Checkout → host
- **Type:** Notification
- **Payload:**
    - `checkout`: The latest state of the checkout

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "method": "ec.buyer.change",
    "params": {
        "checkout": {
            "id": "checkout_123",
            // The entire checkout object is provided, including the updated buyer information
            "buyer": {
                /* ... */
            }
            // ...
        }
    }
}
```

#### `ec.messages.change`

Checkout messages have been updated. Messages include errors, warnings, and
informational notices about the checkout state.

- **Direction:** Embedded Checkout → host
- **Type:** Notification
- **Payload:**
    - `checkout`: The latest state of the checkout

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "method": "ec.messages.change",
    "params": {
        "checkout": {
            "id": "checkout_123",
            "messages": [
                {
                    "type": "error",
                    "code": "invalid_address",
                    "path": "$.buyer.shipping_address",
                    "content": "We cannot ship to this address",
                    "severity": "recoverable"
                },
                {
                    "type": "info",
                    "code": "free_shipping",
                    "content": "Free shipping applied!"
                }
            ]
            // ...
        }
    }
}
```

#### `ec.payment.change`

Payment state has been updated. See [`ec.payment.change`](#ecpaymentchange) for
full documentation.

## Payment Extension

The payment extension defines how a host can use state change notifications and
delegation requests to orchestrate user escalation flows. When a checkout URL
includes `ec_delegate=payment.instruments_change,payment.credential`, the host
gains control over payment method selection and token acquisition, providing
state updates to the Embedded Checkout in response.

### Payment Overview & Host Choice

Payment delegation allows for two different patterns of orchestrating the host
and Embedded Checkout:

**Option A: Host Delegates to Embedded Checkout** The host does NOT include
payment delegation in the URL. The Embedded Checkout handles payment selection
and processing using its own UI and payment flows. This is the standard,
non-delegated flow.

**Option B: Host Takes Control** The host includes
`ec_delegate=payment.instruments_change,payment.credential` in the Checkout URL,
informing the Embedded Checkout to delegate payment UI and token acquisition to
the host. When delegated:

- **Embedded Checkout responsibilities**:
    - Display current payment method with a change intent (e.g., "Change
        Payment Method" button)
    - Wait for a response to the `ec.payment.credential_request` message
        before submitting the payment
- **Host responsibilities**:
    - Respond to the `ec.payment.instruments_change_request` by rendering
        native UI for the buyer to select alternative payment methods, then
        respond with the selected method
    - Respond to the `ec.payment.credential_request` by obtaining a payment
        token for the selected payment method, and sending that token to the
        Embedded Checkout

### Payment Message API Reference

#### `ec.payment.change`

Informs the host that something has changed in the payment section of the
checkout UI, such as a new payment method being selected.

- **Direction:** Embedded Checkout → host
- **Type:** Notification
- **Payload:**
    - `checkout`: The latest state of the checkout

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "method": "ec.payment.change",
    "params": {
        "checkout": {
            "id": "checkout_123",
            // The entire checkout object is provided, including the updated payment details
            "payment": {
                "instruments": [
                    {
                        "id": "payment_instrument_123",
                        "selected": true
                        /* ... */
                    }
                ]
            }
            // ...
        }
    }
}
```

#### `ec.payment.instruments_change_request`

Requests the host to present payment instrument selection UI.

- **Direction:** Embedded Checkout → host
- **Type:** Request
- **Payload:**
    - `checkout`: The latest state of the checkout

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "id": "payment_instruments_change_request_1",
    "method": "ec.payment.instruments_change_request",
    "params": {
        "checkout": {
            "id": "checkout_123",
            // The entire checkout object is provided, including the current payment details
            "payment": {
                /* ... */
            }
            // ...
        }
    }
}
```

The host **MUST** respond with either an error, or the newly-selected payment
instruments. In successful responses, the host **MUST** respond with a partial
update to the `checkout` object, with only the `payment.instruments` field updated. The Embedded Checkout **MUST**
treat this update as a PUT-style change by entirely replacing the existing state
for the provided fields, rather than attempting to merge the new data with
existing state.

- **Direction:** host → Embedded Checkout
- **Type:** Response
- **Payload:**
    - `checkout`: The update to apply to the checkout object

**Example Success Response:**

```json
{
    "jsonrpc": "2.0",
    "id": "payment_instruments_change_request_1",
    "result": {
        "checkout": {
            "payment": {
                // The instrument structure is defined by the handler's instrument schema
                "instruments": [
                    {
                        "id": "payment_instrument_123",
                        "handler_id": "merchant_psp_handler_123",
                        "type": "card",
                        "selected": true,
                        "display": {
                            "brand": "visa",
                            "expiry_month": 12,
                            "expiry_year": 2026,
                            "last_digits": "1111",
                            "description": "Visa •••• 1111",
                            "card_art": "https://host.com/cards/visa-gold.png"
                        }
                        // No `credential` yet; it will be attached in the `ec.payment.credential_request` response
                    }
                ]
            }
        }
    }
}
```

**Example Error Response:**

```json
{
    "jsonrpc": "2.0",
    "id": "payment_instruments_change_request_1",
    "error": {
        "code": "abort_error",
        "message": "User closed the payment sheet without authorizing."
    }
}
```

#### `ec.payment.credential_request`

Requests a credential for the selected payment instrument during checkout
submission.

- **Direction:** Embedded Checkout → Host
- **Type:** Request
- **Payload:**
    - `checkout`: The latest state of the checkout

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "id": "payment_credential_request_1",
    "method": "ec.payment.credential_request",
    "params": {
        "checkout": {
            "id": "checkout_123",
            // The entire checkout object is provided, including the current payment details
            "payment": {
                "instruments": [
                    {
                        "id": "payment_instrument_123",
                        "selected": true
                        /* ... */
                    }
                ]
            }
            // ...
        }
    }
}
```

The host **MUST** respond with either an error, or the credential for the
selected payment instrument. In successful responses, the host **MUST** supply a
partial update to the `checkout` object, updating the instrument with
`selected: true` with the new `credentials` field. The Embedded Checkout
**MUST** treat this update as a PUT-style change by entirely replacing the
existing state for `payment.instruments`, rather than attempting to merge the
new data with existing state.

- **Direction:** host → Embedded Checkout
- **Type:** Response
- **Payload:**
    - `checkout`: The update to apply to the checkout object

**Example Success Response:**

```json
{
    "jsonrpc": "2.0",
    "id": "payment_credential_request_1",
    "result": {
        "checkout": {
            "payment": {
                "instruments": [
                    {
                        "id": "payment_instrument_123",
                        "handler_id": "merchant_psp_handler_123",
                        "type": "card",
                        "selected": true,
                        "display": {
                            "brand": "visa",
                            "expiry_month": 12,
                            "expiry_year": 2026,
                            "last_digits": "1111",
                            "description": "Visa •••• 1111",
                            "card_art": "https://host.com/cards/visa-gold.png"
                        },
                        // The credential structure is defined by the handler's instrument schema
                        "credential": {
                            "type": "token",
                            "token": "tok_123"
                        }
                    }
                ]
            }
        }
    }
}
```

**Example Error Response:**

```json
{
    "jsonrpc": "2.0",
    "id": "payment_credential_request_1",
    "error": {
        "code": "abort_error",
        "message": "User closed the payment sheet without authorizing."
    }
}
```

**Host responsibilities during payment token delegation:**

1. **Confirmation:** Host displays the Trusted Payment UI (Payment Sheet /
    Biometric Prompt). The host **MUST NOT** silently release a token based
    solely on the message.
2. **Auth:** host performs User Authorization via the Payment Handler.
3. **AP2 Integration (Optional):** If `ucp.ap2_mandate` is active (see
    **[AP2 extension](https://ap2-extension.org/)**), the host generates the
    `payment_mandate` here using trusted user interface.

## Fulfillment Extension

The fulfillment extension defines how a host can delegate address selection to
provide a native address picker experience. When a checkout URL includes
`ec_delegate=fulfillment.address_change`, the host gains control over shipping
address selection, providing address updates to the Embedded Checkout in
response.

### Fulfillment Overview & Host Choice

Fulfillment delegation allows for two different patterns:

**Option A: Host Delegates to Embedded Checkout** The host does NOT include
fulfillment delegation in the URL. The Embedded Checkout handles address input
using its own UI and address forms. This is the standard, non-delegated flow.

**Option B: host Takes Control** The host includes
`ec_delegate=fulfillment.address_change` in the Checkout URL, informing the
Embedded Checkout to delegate address selection UI to the host. When delegated:

**Embedded Checkout responsibilities**:

- Display current shipping address with a change intent (e.g., "Change
    Address" button)
- Send `ec.fulfillment.address_change_request` when the buyer triggers address
    change
- Update shipping options based on the address returned by the host

**Host responsibilities**:

- Respond to the `ec.fulfillment.address_change_request` by rendering native
    UI for the buyer to select or enter a shipping address
- Respond with the selected address in UCP PostalAddress format

### Fulfillment Message API Reference

#### `ec.fulfillment.change`

Informs the host that the fulfillment details have been changed in the checkout
UI.

- **Direction:** Embedded Checkout → Host
- **Type:** Notification
- **Payload:**
    - `checkout`: The latest state of the checkout

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "method": "ec.fulfillment.change",
    "params": {
        "checkout": {
            "id": "checkout_123",
            // The entire checkout object is provided, including the updated fulfillment details
            "fulfillment": {
                /* ... */
            }
            // ...
        }
    }
}
```

#### `ec.fulfillment.address_change_request`

Requests the host to present address selection UI for a shipping fulfillment
method.

- **Direction:** Embedded Checkout → Host
- **Type:** Request
- **Payload:**
    - `checkout`: The latest state of the checkout

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "id": "fulfillment_address_change_request_1",
    "method": "ec.fulfillment.address_change_request",
    "params": {
        "checkout": {
            "id": "checkout_123",
            // The entire checkout object is provided, including the current fulfillment details
            "fulfillment": {
                "methods": [
                    {
                        "id": "method_1",
                        "type": "shipping",
                        "selected_destination_id": "address_123",
                        "destinations": [
                            {
                                "id": "address_123",
                                "address_street": "456 Old Street"
                                // ...
                            }
                        ]
                        // ...
                    }
                ]
            }
            // ...
        }
    }
}
```

The host **MUST** respond with either an error, or the newly-selected address.
In successful responses, the host **MUST** respond with an updated
`fulfillment.methods` object, updating the `selected_destination_id` and
`destinations` fields for fulfillment methods, and otherwise preserving the
existing state. The Embedded Checkout **MUST** treat this update as a PUT-style
change by entirely replacing the existing state for `fulfillment.methods`,
rather than attempting to merge the new data with existing state.

- **Direction:** host → Embedded Checkout
- **Type:** Response
- **Payload:**
    - `checkout`: The update to apply to the checkout object

**Example Success Response:**

```json
{
    "jsonrpc": "2.0",
    "id": "fulfillment_address_change_request_1",
    "result": {
        "checkout": {
            "fulfillment": {
                "methods": [
                    {
                        "id": "method_1",
                        "type": "shipping",
                        "selected_destination_id": "address_789",
                        "destinations": [
                            {
                                "id": "address_789",
                                "first_name": "John",
                                "last_name": "Doe",
                                "street_address": "123 New Street"
                            }
                        ]
                    }
                ]
            }
        }
    }
}
```

**Example Error Response:**

```json
{
    "jsonrpc": "2.0",
    "id": "fulfillment_address_change_request_1",
    "error": {
        "code": "abort_error",
        "message": "User cancelled address selection."
    }
}
```

### Address Format

The address object uses the UCP
[PostalAddress](site:specification/checkout/#postal-address) format:

{{ schema_fields('postal_address', 'embedded-checkout') }}

## Security & Error Handling

### Error Codes

Responses to delegation request messages from the
embedded checkout may resolve to errors. The message responder **SHOULD** use
error codes mapped to
**[W3C DOMException](https://webidl.spec.whatwg.org/#idl-DOMException)** names
where possible.

| Code                  | Description                                                                                                                                    |
| :-------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------- |
| `abort_error`         | The user cancelled the interaction (e.g., closed the sheet).                                                                                   |
| `security_error`      | The host origin validation failed.                                                                                                             |
| `not_supported_error` | The requested payment method is not supported by the host.                                                                                     |
| `invalid_state_error` | Handshake was attempted out of order.                                                                                                          |
| `not_allowed_error`   | The request was missing valid User Activation (see [Prevention of Unsolicited Payment Requests](#prevention-of-unsolicited-payment-requests)). |

### Security for Web-Based Hosts

#### Content Security Policy (CSP)

To ensure security, both parties **MUST** implement appropriate
**[Content Security Policy (CSP)](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)**
directives:

- **Business:** **MUST** set `frame-ancestors <host_origin>;` to ensure it's
    only embedded by trusted hosts.

- **Host:**
    - **Direct Embedding:** If the host directly embeds the business's page,
        specifying a `frame-src` directive listing every potential business
        origin can be impractical, especially if there are many businesses. In
        this scenario, while a strict `frame-src` is ideal, other security
        measures like those in [Iframe Sandbox Attributes](#iframe-sandbox-attributes)
        and [Credentialless Iframes](#credentialless-iframes) are critical.
    - **Intermediate Iframe:** The host **MAY** use an intermediate iframe
        (e.g., on a host-controlled subdomain) to embed the business's page.
        This offers better control:
        - The host's main page only needs to allow the origin of the
            intermediate iframe in its `frame-src` (e.g.,
            `frame-src <intermediate_iframe_origin>;`).
        - The intermediate iframe **MUST** implement a strict `frame-src`
            policy, dynamically set to allow _only_ the specific
            `<merchant_origin>` for the current embedded session (e.g.,
            `frame-src <merchant_origin>;`). This can be set via HTTP headers
            when serving the intermediate iframe content.

#### Iframe Sandbox Attributes

All business iframes **MUST** be sandboxed to restrict their capabilities. The
following sandbox attributes **SHOULD** be applied, but a host and business
**MAY** negotiate additional capabilities:

```html
<iframe sandbox="allow-scripts allow-forms allow-same-origin"></iframe>
```

#### Credentialless Iframes

Hosts **SHOULD** use the `credentialless` attribute on the iframe to load it in
a new, ephemeral context. This prevents the business from correlating user
activity across contexts or accessing existing sessions, protecting user
privacy.

```html
<iframe credentialless src="https://business.example.com/checkout"></iframe>
```

#### Strict Origin Validation

Enforce strict validation of the `origin` for all `postMessage` communications
between frames.

### Prevention of Unsolicited Payment Requests

**Vulnerability:** A malicious or compromised business could programmatically
trigger `ec.payment.credential_request` without user interaction.

**Mitigation (Host-Controlled Execution):** To eliminate this risk, the host is
designated as the sole trusted initiator of the payment execution. The host
SHOULD display a User Confirmation UI before releasing the token. Silent
tokenization is strictly PROHIBITED when the trigger originates from the
Embedded Checkout.

## Schema Definitions

The following schemas define the data structures used within the Embedded
Checkout protocol and its extensions.

### Checkout

The core object representing the current state of the transaction, including
line items, totals, and buyer information.

{{ schema_fields('checkout_resp', 'checkout') }}

### Order

The object returned upon successful completion of a checkout, containing
confirmation details.

{{ schema_fields('order', 'order') }}

### Payment

{{ schema_fields('payment_resp', 'embedded-checkout')}}

### Payment Instrument

Represents a specific method of payment (e.g., a specific credit card, bank
account, or wallet credential) available to the buyer.

{{ schema_fields('payment_instrument', 'embedded-checkout') }}

### Payment Handler Response

Represents the processor or wallet provider responsible for authenticating and
processing a specific payment instrument (e.g., Google Pay, Stripe, or a Bank
App).

{{ schema_fields('payment_handler_resp', 'embedded-checkout') }}
