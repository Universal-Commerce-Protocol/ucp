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

# Embedded Checkout Protocol

* **Namespace:** `ec`
* **Version:** `2026-01-11`

## 1. Introduction

Embedded Checkout Protocol (ECP) is a UCP transport binding that enables a
**Host** to embed a **Merchant's** checkout interface, receive events as the
buyer interacts with the checkout, and delegate key user actions such as address
and payment selection. ECP is a transport binding (like REST)—it defines **how**
to communicate, not **what** data exists.

### 1.1 Conformance & Standards

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHOULD", "SHOULD NOT",
"RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as
described in **[RFC 2119](https://www.rfc-editor.org/rfc/rfc2119)**.

#### W3C Payment Request Conceptual Alignment

ECP draws inspiration from the
**[W3C Payment Request API](https://www.w3.org/TR/payment-request/)**, adapting
its mental model for embedded checkout scenarios. Developers familiar with
Payment Request will recognize similar patterns, though the execution model
differs:

**W3C Payment Request:** Browser-controlled. The merchant calls `show()` and the
browser renders a native payment sheet. Events flow from the payment handler to
the merchant.

**Embedded Checkout:** Merchant-controlled. The Host embeds the Merchant's
checkout UI in an iframe/webview. Events flow bidirectionally, with optional
delegation allowing the Host to handle specific interactions natively.

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
flow. In Embedded Checkout, the Merchant orchestrates within the embedded
context, optionally delegating specific UI (payment method selection, address
picker) to the Host for native experiences.

## 2. Terminology & Actors

### Commerce Roles

-   **Merchant:** The seller providing goods/services and the checkout
    experience.
-   **Buyer:** The end user making a purchase.

### Technical Components

-   **Host:** The application embedding the checkout (e.g., AI Agent app, Super
    App, Browser). Responsible for the **Payment Handler** and user
    authentication.
-   **Embedded Checkout:** The Merchant's checkout interface rendered in an
    iframe or webview. Responsible for the checkout flow and order creation.
-   **Payment Handler:** The secure component that performs user authentication
    (biometric/PIN) and credential issuance.

## 3. Requirements

### 3.1 Discovery

ECP availability is signaled via service discovery. When a merchant advertises
the `embedded` transport in their `/.well-known/ucp` profile, all checkout
`continue_url` values support the Embedded Checkout Protocol.

**Service Discovery Example:**

```json
{
    "services": {
        "dev.ucp.shopping": {
            "version": "2026-01-11",
            "rest": {
                "schema": "https://ucp.dev/services/shopping/rest.openapi.json",
                "endpoint": "https://merchant.example.com/ucp/v1"
            },
            "mcp": {
                "schema": "https://ucp.dev/services/shopping/mcp.openrpc.json",
                "endpoint": "https://merchant.example.com/ucp/mcp"
            },
            "embedded": {
                "schema": "https://ucp.dev/services/shopping/embedded.openrpc.json"
            }
        }
    }
}
```

When `embedded` is present in the service definition:

-   All `continue_url` values returned by that merchant support ECP
-   ECP version matches the service's UCP version
-   Delegations are negotiated at runtime via the `ec.ready` handshake

When `embedded` is absent from the service definition, the merchant only
supports redirect-based checkout continuation via `continue_url`.

### 3.2 Loading an Embedded Checkout URL

When a Host receives a checkout response with a `continue_url` from a merchant
that advertises ECP support, it MAY initiate an ECP session by loading the URL
in an embedded context.

Before loading the embedded context, the Host SHOULD:

1.  Prepare handlers for any delegations the Host wants to support
2.  Optionally prepare authentication credentials if required by the merchant

To initiate the session, the Host MUST augment the `continue_url` with ECP query
parameters using the `ec_` prefix.

All ECP parameters are passed via URL query string, not HTTP headers, to ensure
maximum compatibility across different embedding environments. Parameters use
the `ec_` prefix to avoid namespace pollution and clearly distinguish ECP
parameters from merchant-specific query parameters:

-   `ec_version` (string, REQUIRED): The UCP version for this session (format:
    `YYYY-MM-DD`). Must match the version from service discovery.
-   `ec_auth` (string, OPTIONAL): Authentication token in merchant-defined
    format
-   `ec_delegate` (string, OPTIONAL): Comma-delimited list of delegations the
    Host wants to handle

#### 3.2.1 Authentication

**Token Format:**

-   The `auth` parameter format is entirely merchant-defined
-   Common formats include JWT, OAuth tokens, API keys, or session identifiers
-   Merchants MUST document their expected token format and validation process

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
  // ... merchant-specific claims ...
}
```

Merchants MUST validate authentication according to their security requirements.

**Example initialization with authentication:**

```
https://example.com/checkout/abc123?ec_version=2026-01-11&ec_auth=eyJ...
```

Note: All query parameter values must be properly URL-encoded per RFC 3986.

#### 3.2.2 Delegation

The optional `ec_delegate` parameter declares which operations the Host wants
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

```
?ec_version=2026-01-11&ec_delegate=payment.instruments_change,payment.credential,fulfillment.address_change
```

### 3.3 Delegation Contract

Delegation creates a binding contract between the Host and Embedded Checkout.
However, the Embedded Checkout MAY restrict delegation to authenticated or
approved Hosts based on merchant policy.

#### 3.3.1 Delegation Acceptance

The Embedded Checkout determines which delegations to honor based on:

-   Authentication status (via `ec_auth` parameter)
-   Host authorization level
-   Merchant policy

The Embedded Checkout MUST indicate accepted delegations in the `ec.ready`
request via the `delegate` field (see [Section 5.2.1](#521-ecready)). If a
requested delegation is not accepted, the Embedded Checkout MUST handle that
capability using its own UI.

#### 3.3.2 Binding Requirements

**Once delegation is accepted**, both parties enter a binding contract:

**Embedded Checkout responsibilities:**

1.  MUST fire the appropriate `{action}_request` message when that action is
    triggered
2.  MUST wait for the Host's response before proceeding
3.  MUST NOT show its own UI for that delegated action

**Host responsibilities:**

1.  MUST respond to every `{action}_request` message it receives
2.  MUST respond with an appropriate error if the user cancels
3.  SHOULD show loading/processing states while handling delegation

#### 3.3.3 Delegation Flow

1.  **Request**: Embedded Checkout sends an `ec.{capability}.{action}_request`
    message with current state (includes `id`)
2.  **Native UI**: Host presents native UI for the delegated action
3.  **Response**: Host sends back a JSON-RPC response with matching `id` and
    `result` or `error`
4.  **Update**: Embedded Checkout updates its state and may send subsequent
    change notifications

See [Section 6 Payment Extension](#6-payment-extension) and
[Section 7 Fulfillment Extension](#7-fulfillment-extension) for
capability-specific delegation details.

### 3.4 Navigation Constraints

When checkout is rendered in embedded mode, the implementation SHOULD prevent
off-checkout navigation to maintain a focused checkout experience. The embedded
view is intended to provide a checkout flow, not a general-purpose browser.

**Navigation Requirements:**

-   The embedded checkout SHOULD block or intercept navigation attempts to URLs
    outside the checkout flow
-   The embedded checkout SHOULD remove or disable UI elements that would
    navigate away from checkout (e.g., external links, navigation bars)
-   The embedder MAY implement additional navigation restrictions at the
    container level

**Permitted Exceptions:** The following navigation scenarios MAY be allowed when
required for checkout completion:

-   Payment provider redirects: off-site payment flows
-   3D Secure verification: card authentication frames and redirects
-   Bank authorization: open banking or similar authorization flows
-   Identity verification: KYC/AML compliance checks when required

These exceptions SHOULD return the user to the checkout flow upon completion.

## 4. Transport & Messaging

### 4.1 Message Format

All ECP messages MUST use JSON-RPC 2.0 format
([RFC 7159](https://datatracker.ietf.org/doc/html/rfc7159)). Each message MUST
contain:

-   `jsonrpc`: MUST be `"2.0"`
-   `method`: The message name (e.g., `"ec.start"`)
-   `params`: Message-specific payload (may be empty object)
-   `id`: (Optional) Present only for requests that expect responses

### 4.2 Message Types

**Requests** (with `id` field):

-   Require a response from the receiver
-   MUST include a unique `id` field
-   Receiver MUST respond with matching `id`
-   Response MUST be either a `result` or `error` object
-   Used for operations requiring acknowledgment or data

**Notifications** (without `id` field):

-   Informational only, no response expected
-   MUST NOT include an `id` field
-   Receiver MUST NOT send a response
-   Used for state updates and informational events

### 4.3 Response Handling

For requests (messages with `id`), receivers MUST respond with either:

**Success Response:**

```json
{ "jsonrpc": "2.0", "id": "...", "result": {...} }
```

**Error Response:**

```json
{ "jsonrpc": "2.0", "id": "...", "error": {...} }
```

### 4.4 Communication Channels

#### 4.4.1 Communication Channel for Web-Based Hosts

When the Host is a web application, communication starts using `postMessage`
between the Host and Checkout windows. The host MUST listen for `postMessage`
calls from the embedded window, and when a message is received, they MUST
validate the origin matches the `checkout_url` used to start the checkout.

Upon validation, the Host MAY create a `MessageChannel`, and transfer one of its
ports in the result of the [`ec.ready` response](#521-ecready). When a Host
responds with a `MessagePort`, all subsequent messages MUST be sent over that
channel. Otherwise, the Host and Merchant MUST continue using `postMessage()`
between their `window` objects, including origin validation.

#### 4.4.2 Communication Channel for Native Hosts

When the Host is a native application, they MUST inject globals into the
Embedded Checkout that allows `postMessage` communication between the web and
native environments. The Host MUST create at least one of the following globals:

-   `window.EmbeddedCheckoutProtocolConsumer` (preferred)
-   `window.webkit.messageHandlers.EmbeddedCheckoutProtocolConsumer`

This object MUST implement the following interface:

```javascript
{
  postMessage(message: string): void
}
```

Where `message` is a JSON-stringified JSON-RPC 2.0 message. The Host MUST parse
the JSON string before processing.

For messages traveling from the Host to the Embedded Checkout, the Host MUST
inject JavaScript in the webview that will call
`window.EmbeddedCheckoutProtocol.postMessage()` with the JSON RPC message. The
Embedded Checkout MUST initialize this global object — and start listening for
`postMessage()` calls — before the `ec.ready` message is sent.

## 5. Message API Reference

### 5.1 Message Categories

#### 5.1.1 Core Messages

Core messages are defined by the ECP specification and MUST be supported by all
implementations. All messages are sent from Embedded Checkout to Host.

| Category         | Purpose                                                 | Pattern      | Core Messages                             |
| ---------------- | ------------------------------------------------------- | ------------ | ----------------------------------------- |
| **Handshake**    | Establish connection between Host and Embedded Checkout | Request      | `ec.ready`                                |
| **Lifecycle**    | Inform of checkout state transitions                    | Notification | `ec.start`, `ec.complete`                 |
| **State Change** | Inform of checkout field changes                        | Notification | `ec.line_items.change`, `ec.buyer.change`, `ec.payment.change`, `ec.messages.change` |

#### 5.1.2 Extension Messages

Extensions MAY extend the Embedded protocol by defining additional messages.
Extension messages MUST follow the naming convention:

-   **Notifications**: `ec.{capability}.change` — state change notifications (no
    `id`)
-   **Delegation requests**: `ec.{capability}.{action}_request` — requires
    response (has `id`)

Where:

-   `{capability}` matches the capability identifier from discovery
-   `{action}` describes the specific action being delegated (e.g.,
    `instruments_change`, `address_change`)
-   `_request` suffix signals this is a delegation point requiring a response

### 5.2 Handshake Messages

#### 5.2.1 `ec.ready`

Upon rendering, the Embedded Checkout MUST broadcast readiness to the parent
context using the `ec.ready` message. This message initializes a secure
communication channel between the Host and Embedded Checkout, communicates which
delegations were accepted, and allows the Host to provide additional,
display-only state for the checkout that was not communicated over UCP checkout
actions.

-   **Direction:** Embedded Checkout → Host
-   **Type:** Request
-   **Payload:**
    -   `delegate` (array of strings, REQUIRED): List of delegation identifiers
        accepted by the Embedded Checkout. This is a subset of the delegations
        requested via the `ec_delegate` URL parameter. Omitted or empty array
        means no delegations were accepted.

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

The `ec.ready` message is a request, which means that the Host MUST respond to
complete the handshake.

-   **Direction:** Host → Embedded Checkout
-   **Type:** Response
-   **Result Payload:**
    -   `upgrade` (object, OPTIONAL): An object describing how the Embedded
        Checkout should update the communication channel it uses to communicate
        with the Host.
    -   `checkout` (object, OPTIONAL): Additional, display-only state for the
        checkout that was not communicated over UCP checkout actions. This is
        used to populate the checkout UI, and may only be used to populate the
        following fields, under specific conditions:
        -   `payment.instruments`: can be overwritten when the Host and Embedded
            Checkout both accept the `payment.instruments_change` delegation.

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "id": "ready_1",
    "result": {}
}
```

Hosts MAY respond with an `upgrade` field to update the communication channel
between Host and Embedded Checkout. Currently, this object only supports a
`port` field, which MUST be a `MessagePort` object, and MUST be transferred to
the embedded checkout context (e.g., with `{transfer: [port2]}` on the Host's
`iframe.contentWindow.postMessage()` call):

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

When the Host responds with an `upgrade` object, the Embedded Checkout MUST
discard any other information in the message, send a new `ec.ready` message over
the upgraded communication channel, and wait for a new response. All subsequent
messages MUST be sent only over the upgraded communication channel.

The Host MAY also respond with a `checkout` object, which will be used to
populate the checkout UI according to the delegation contract between Host and
Merchant.

**Example Message: Providing payment instruments, including display
information:**

```json
{
    "jsonrpc": "2.0",
    "id": "ready_1",
    "result": {
        "checkout": {
            "payment": {
                "instruments": [
                    {
                        "type": "card",
                        "status": "created",
                        "handler_id": "merchant_psp_handler",
                        "id": "payment_instrument_123",
                        "account_info": {
                            "payment_account_reference": "V0010010000000000000000000000",
                            "fingerprint": "xyz_123"
                        },
                        "display_data": {
                            "summary": "Visa •••• 1111",
                            "brand": "visa",
                            "last_digits": "1111",
                            "expiry_month": 12,
                            "expiry_year": 2025,
                            "card_art_url": "https://host.com/cards/visa-gold.png"
                        }
                    }
                ]
            }
        }
    }
}
```

### 5.3 Lifecycle Messages

#### 5.3.1 `ec.start`

Signals that checkout is visible and ready for interaction.

-   **Direction:** Embedded Checkout → Host
-   **Type:** Notification
-   **Payload:**
    -   `checkout`: The latest state of the checkout, using the same structure
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

#### 5.3.2 `ec.complete`

Indicates successful checkout completion.

-   **Direction:** Embedded Checkout → Host
-   **Type:** Notification
-   **Payload:**
    -   `checkout`: The latest state of the checkout, using the same structure
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
            "order_id": "987654321",
            "order_permalink_url": "https://shop.com/orders/xyz123"
        }
    }
}
```

### 5.4 State Change Messages

State change messages inform the embedder of changes that have already occurred
in the checkout interface. These are informational only. The checkout has
already applied the changes and rendered the updated UI.

#### 5.4.1 `ec.line_items.change`

Line items have been modified (quantity changed, items added/removed) in the
checkout UI.

-   **Direction:** Embedded Checkout → Host
-   **Type:** Notification
-   **Payload:**
    -   `checkout`: The latest state of the checkout

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

#### 5.4.2 `ec.buyer.change`

Buyer information has been updated in the checkout UI.

-   **Direction:** Embedded Checkout → Host
-   **Type:** Notification
-   **Payload:**
    -   `checkout`: The latest state of the checkout

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

#### 5.4.3 `ec.messages.change`

Checkout messages have been updated. Messages include errors, warnings, and
informational notices about the checkout state.

-   **Direction:** Embedded Checkout → Host
-   **Type:** Notification
-   **Payload:**
    -   `checkout`: The latest state of the checkout

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

#### 5.4.4 `ec.payment.change`

Payment state has been updated. See [Section 6.2.1](#621-ecpaymentchange) for
full documentation.

## 6. Payment Extension

The payment extension defines how a Host can use state change notifications and
delegation requests to orchestrate user escalation flows. When a checkout URL
includes `ec_delegate=payment.instruments_change,payment.credential`, the Host
gains control over payment method selection and token acquisition, providing
state updates to the Embedded Checkout in response.

### 6.1 Payment Overview & Host Choice

Payment delegation allows for two different patterns of orchestrating the Host
and Embedded Checkout:

**Option A: Host Delegates to Embedded Checkout** The Host does NOT include
payment delegation in the URL. The Embedded Checkout handles payment selection
and processing using its own UI and payment flows. This is the standard,
non-delegated flow.

**Option B: Host Takes Control** The Host includes
`ec_delegate=payment.instruments_change,payment.credential` in the Checkout URL,
informing the Embedded Checkout to delegate payment UI and token acquisition to
the Host. When delegated:

-   **Embedded Checkout responsibilities**:
    -   Display current payment method with a change intent (e.g., "Change
        Payment Method" button)
    -   Wait for a response to the `ec.payment.credential_request` message
        before submitting the payment
-   **Host responsibilities**:
    -   Respond to the `ec.payment.instruments_change_request` by rendering
        native UI for the buyer to select alternative payment methods, then
        respond with the selected method
    -   Respond to the `ec.payment.credential_request` by obtaining a payment
        token for the selected payment method, and sending that token to the
        Embedded Checkout

### 6.2 Payment Message API Reference

#### 6.2.1 `ec.payment.change`

Informs the Host that something has changed in the payment section of the
checkout UI, such as a new payment method being selected.

-   **Direction:** Embedded Checkout → Host
-   **Type:** Notification
-   **Payload:**
    -   `checkout`: The latest state of the checkout

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
                "selected_instrument_id": "payment_instrument_123",
                "instruments": [
                    /* ... */
                ],
                "handlers": [
                    /* ... */
                ]
            }
            // ...
        }
    }
}
```

#### 6.2.2 `ec.payment.instruments_change_request`

Requests the Host to present payment instrument selection UI.

-   **Direction:** Embedded Checkout → Host
-   **Type:** Request
-   **Payload:**
    -   `checkout`: The latest state of the checkout

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

The Host MUST respond with either an error, or the newly-selected payment
instruments. In successful responses, the Host MUST respond with a partial
update to the `checkout` object, with only the `payment.instruments` and
`payment.selected_instrument_id` fields updated. The Embedded Checkout MUST
treat this update as a PUT-style change by entirely replacing the existing state
for the provided fields, rather than attempting to merge the new data with
existing state.

-   **Direction:** Host → Embedded Checkout
-   **Type:** Response
-   **Payload:**
    -   `checkout`: The update to apply to the checkout object

**Example Success Response:**

```json
{
    "jsonrpc": "2.0",
    "id": "payment_instruments_change_request_1",
    "result": {
        "checkout": {
            "payment": {
                "selected_instrument_id": "payment_instrument_123",
                "instruments": [
                    {
                        "id": "payment_instrument_123",
                        "handler_id": "merchant_psp_handler",
                        "type": "card",
                        "brand": "visa",
                        "last_digits": "1111",
                        "expiry_month": 12,
                        "expiry_year": 2025,
                        "summary": "Visa •••• 1111",
                        "card_art_url": "https://host.com/cards/visa-gold.png"
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

#### 6.2.3 `ec.payment.credential_request`

Requests a credential for the selected payment instrument during checkout
submission.

-   **Direction:** Embedded Checkout → Host
-   **Type:** Request
-   **Payload:**
    -   `checkout`: The latest state of the checkout

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
                "selected_instrument_id": "payment_instrument_123",
                "instruments": [
                    /* ... */
                ],
                "handlers": [
                    /* ... */
                ]
            }
            // ...
        }
    }
}
```

The Host MUST respond with either an error, or the credential for the
selected payment instrument. In successful responses, the Host MUST supply a
partial update to the `checkout` object, updating only the instrument indicated
by `payment.selected_instrument_id` with the new `credentials` field. The
Embedded Checkout MUST treat this update as a PUT-style change by entirely
replacing the existing state for `payment.instruments`, rather than attempting
to merge the new data with existing state.

-   **Direction:** Host → Embedded Checkout
-   **Type:** Response
-   **Payload:**
    -   `checkout`: The update to apply to the checkout object

**Example Success Response:**

```json
{
    "jsonrpc": "2.0",
    "id": "payment_credential_request_1",
    "result": {
        "checkout": {
            "payment": {
                "instruments": [
                    // Instrument schema is determined by the payment handler's instrument_schemas
                    {
                        "id": "payment_instrument_123",
                        "handler_id": "gpay",
                        "type": "card",
                        "brand": "visa",
                        "last_digits": "1234",
                        "expiry_month": 12,
                        "expiry_year": 2026,
                        // The credential structure is defined by the handler's instrument schema
                        "credential": {
                            "type": "PAYMENT_GATEWAY",
                            "token": "{\"id\": \"tok_123\", \"object\": \"token\"...}"
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

1.  **Confirmation:** Host displays the Trusted Payment UI (Payment Sheet /
    Biometric Prompt). The Host MUST NOT silently release a token based solely
    on the message.
2.  **Auth:** Host performs User Authorization via the Payment Handler.
3.  **AP2 Integration (Optional):** If `ucp.ap2_mandate` is active (see
    **[AP2 extension](https://ap2-extension.org/)**), the Host generates the
    `payment_mandate` here using trusted user interface.

## 7. Fulfillment Extension

The fulfillment extension defines how a Host can delegate address selection to
provide a native address picker experience. When a checkout URL includes
`ec_delegate=fulfillment.address_change`, the Host gains control over shipping
address selection, providing address updates to the Embedded Checkout in
response.

### 7.1 Fulfillment Overview & Host Choice

Fulfillment delegation allows for two different patterns:

**Option A: Host Delegates to Embedded Checkout** The Host does NOT include
fulfillment delegation in the URL. The Embedded Checkout handles address input
using its own UI and address forms. This is the standard, non-delegated flow.

**Option B: Host Takes Control** The Host includes
`ec_delegate=fulfillment.address_change` in the Checkout URL, informing the
Embedded Checkout to delegate address selection UI to the Host. When delegated:

**Embedded Checkout responsibilities**:

-   Display current shipping address with a change intent (e.g., "Change
    Address" button)
-   Send `ec.fulfillment.address_change_request` when the buyer triggers address
    change
-   Update shipping options based on the address returned by the Host

**Host responsibilities**:

-   Respond to the `ec.fulfillment.address_change_request` by rendering native
    UI for the buyer to select or enter a shipping address
-   Respond with the selected address in UCP PostalAddress format

### 7.2 Fulfillment Message API Reference

#### 7.2.1 `ec.fulfillment.change`

Informs the Host that the fulfillment details have been changed in the checkout
UI.

-   **Direction:** Embedded Checkout → Host
-   **Type:** Notification
-   **Payload:**
    -   `checkout`: The latest state of the checkout

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

#### 7.2.2 `ec.fulfillment.address_change_request`

Requests the Host to present address selection UI for a shipping fulfillment
method.

-   **Direction:** Embedded Checkout → Host
-   **Type:** Request
-   **Payload:**
    -   `checkout`: The latest state of the checkout

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

The Host MUST respond with either an error, or the newly-selected address. In
successful responses, the Host MUST respond with an updated
`fulfillment.methods` object, updating the `selected_destination_id` and
`destinations` fields for fulfillment methods, and otherwise preserving the
existing state. The Embedded Checkout MUST treat this update as a PUT-style
change by entirely replacing the existing state for `fulfillment.methods`,
rather than attempting to merge the new data with existing state.

-   **Direction:** Host → Embedded Checkout
-   **Type:** Response
-   **Payload:**
    -   `checkout`: The update to apply to the checkout object

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

### 7.3 Address Format

The address object uses the UCP
[PostalAddress](site:specification/checkout/#postal-address) format:

{{ schema_fields('postal_address', 'embedded-checkout') }}

## 8. Security & Error Handling

### 8.1 Error Codes

Responses to [delegation request messages](#43-response-handling) from the
embedded checkout may resolve to errors. The message responder SHOULD use error
codes mapped to
**[W3C DOMException](https://webidl.spec.whatwg.org/#idl-DOMException)** names
where possible.

| Code                  | Description                                                                                                        |
| :-------------------- | :----------------------------------------------------------------------------------------------------------------- |
| `abort_error`         | The user cancelled the interaction (e.g., closed the sheet).                                                       |
| `security_error`      | The Host origin validation failed.                                                                                 |
| `not_supported_error` | The requested payment method is not supported by the Host.                                                         |
| `invalid_state_error` | Handshake was attempted out of order.                                                                              |
| `not_allowed_error`   | The request was missing valid User Activation (see [Section 8.3](#83-prevention-of-unsolicited-payment-requests)). |

### 8.2 Security for Web-Based Hosts

#### 8.2.1 Content Security Policy (CSP)

To ensure security, both parties MUST implement appropriate
**[Content Security Policy (CSP)](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)**
directives:

-   **Merchant:** MUST set `frame-ancestors <host_origin>;` to ensure it's only
    embedded by trusted hosts.

-   **Host:**
    -   **Direct Embedding:** If the Host directly embeds the merchant's page,
        specifying a `frame-src` directive listing every potential merchant
        origin can be impractical, especially if there are many merchants. In
        this scenario, while a strict `frame-src` is ideal, other security
        measures like those in [Section 8.2.2](#822-iframe-sandbox-attributes)
        and [Section 8.2.3](#823-credentialless-iframes) are critical.
    -   **Intermediate Iframe:** The Host MAY use an intermediate iframe (e.g.,
        on a Host-controlled subdomain) to embed the merchant's page. This
        offers better control:
        -   The Host's main page only needs to allow the origin of the
            intermediate iframe in its `frame-src` (e.g.,
            `frame-src <intermediate_iframe_origin>;`).
        -   The intermediate iframe MUST implement a strict `frame-src` policy,
            dynamically set to allow _only_ the specific `<merchant_origin>` for
            the current embedded session (e.g., `frame-src <merchant_origin>;`).
            This can be set via HTTP headers when serving the intermediate
            iframe content.

#### 8.2.2 Iframe Sandbox Attributes

All merchant iframes MUST be sandboxed to restrict their capabilities. The
following sandbox attributes SHOULD be applied, but a Host and Merchant MAY
negotiate additional capabilities:

```html
<iframe sandbox="allow-scripts allow-forms allow-same-origin"></iframe>
```

#### 8.2.3 Credentialless Iframes

Hosts SHOULD use the `credentialless` attribute on the iframe to load it in a
new, ephemeral context. This prevents the merchant from correlating user
activity across contexts or accessing existing sessions, protecting user
privacy.

```html
<iframe credentialless src="https://merchant.example.com/checkout"></iframe>
```

#### 8.2.4 Strict Origin Validation

Enforce strict validation of the `origin` for all `postMessage` communications
between frames.

### 8.3 Prevention of Unsolicited Payment Requests

**Vulnerability:** A malicious or compromised merchant could programmatically
trigger `ec.payment.credential_request` without user interaction.

**Mitigation (Host-Controlled Execution):** To eliminate this risk, the Host is
designated as the sole trusted initiator of the payment execution. The Host
SHOULD display a User Confirmation UI before releasing the token. Silent
tokenization is strictly PROHIBITED when the trigger originates from the
Embedded Checkout.

## 9. Schema Definitions

The following schemas define the data structures used within the Embedded
Checkout protocol and its extensions.

### Checkout

The core object representing the current state of the transaction, including
line items, totals, and buyer information.

{{ schema_fields('checkout_resp', 'embedded-checkout') }}

### Order

The object returned upon successful completion of a checkout, containing
confirmation details.

{{ schema_fields('order', 'embedded-checkout') }}

### Payment

{{ schema_fields('payment_resp', 'embedded-checkout')}}

### Payment Instrument

Represents a specific method of payment (e.g., a specific credit card, bank
account, or wallet credential) available to the buyer.

{{ schema_fields('payment_instrument', 'embedded-checkout') }}

### Payment Handler

Represents the processor or wallet provider responsible for authenticating and
processing a specific payment instrument (e.g., Google Pay, Stripe, or a Bank
App).

{{ schema_fields('payment_handler_resp', 'embedded-checkout') }}
