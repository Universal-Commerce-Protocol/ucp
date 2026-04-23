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

# Cart Capability - EP Binding

## Introduction

Embedded Cart Protocol (ECaP) is a cart-specific implementation of
UCP's Embedded Protocol (EP) transport binding that enables a
**host** to embed a **business's** cart interface and receive events as the
buyer interacts with the cart.
ECaP is a transport binding (like REST)—it defines **how**
to communicate, not **what** data exists.

## Terminology & Actors

### Commerce Roles

- **Business:** The seller providing goods/services and the cart building
    experience.
- **Buyer:** The end user looking to make a purchase through the cart building exercise.

### Technical Components

- **Host:** The application embedding the cart (e.g., AI Agent app,
    Super App, Browser). Responsible for user
    authentication (including any prerequisites like identity linking).
- **Embedded Cart:** The business's cart interface rendered in an
    iframe or webview. Responsible for the cart building flow and potential transition
    into lower-funnel constructs like checkout creations.

### Discovery

ECaP availability is signaled via service discovery. When a business advertises
the `embedded` transport in their `/.well-known/ucp` profile, all cart
`continue_url` values support the Embedded Cart Protocol.

**Service Discovery Example:**

```json
{
    "services": {
        "dev.ucp.shopping": [
            {
                "version": "{{ ucp_version }}",
                "transport": "rest",
                "schema": "https://ucp.dev/{{ ucp_version }}/services/shopping/rest.openapi.json",
                "endpoint": "https://merchant.example.com/ucp/v1"
            },
            {
                "version": "{{ ucp_version }}",
                "transport": "mcp",
                "schema": "https://ucp.dev/{{ ucp_version }}/services/shopping/mcp.openrpc.json",
                "endpoint": "https://merchant.example.com/ucp/mcp"
            },
            {
                "version": "{{ ucp_version }}",
                "transport": "embedded",
                "schema": "https://ucp.dev/{{ ucp_version }}/services/shopping/embedded.openrpc.json"
            }
        ]
    }
}
```

When `embedded` is absent from the service definition, the business only
supports redirect-based cart continuation via `continue_url`.

#### Per-Cart Configuration

Service-level discovery declares that a business supports ECaP, but does not
guarantee that business will enable it for every cart session. Businesses **MUST** include
an embedded service binding with `config.delegate` in cart responses to
indicate ECaP availability and allowed delegations for a specific session.

**Cart Response Example:**

```json
{
    "id": "cart_123",
    "continue_url": "https://merchant.example.com/cart/cart123",
    "ucp": {
        "version": "{{ ucp_version }}",
        "services": {
            "dev.ucp.shopping": [
                {
                    "version": "{{ ucp_version }}",
                    "transport": "embedded",
                    "config": {
                        "delegate": []
                    }
                }
            ]
        },
        "capabilities": {...},
        "payment_handlers": {...}
    }
    // ...other cart fields...
}
```

### Loading an Embedded Cart URL

When a host receives a cart response with a `continue_url` from a business
that advertises ECaP support, it **MAY** initiate an ECaP session by loading the
URL in an embedded context.

**Example:**

```text
https://example.com/cart/cart123?ep_version=2026-01-23...
```

Note: All query parameter values must be properly URL-encoded per RFC 3986.

Before loading the embedded context, the host **SHOULD**:

1. Check `config.delegate` in the response for available delegations
2. Optionally complete authentication mechanisms (i.e. identity linking)
   if required by the business

To initiate the session, the host **MUST** augment the `continue_url` with supported
ECaP query parameters.

All ECaP parameters are passed via URL query string, not HTTP headers, to ensure
maximum compatibility across different embedding environments. Parameters **SHOULD**
use either `ep` or `ep_cart` prefixes to avoid namespace pollution and clearly
distinguish ECaP parameters from business-specific query parameters:

- `ep_version` (string, **REQUIRED**): The UCP version for this session
    (format: `YYYY-MM-DD`). Must match the version from service discovery.
- `ep_auth` (string, **OPTIONAL**): Authentication token in business-defined
    format.
- `ep_color_scheme` (string, **OPTIONAL**): The color scheme preference for
    the cart UI. Valid values: `light`, `dark`. When not provided, the
    Embedded Cart follows system preference.
- `ep_cart_delegate` (string, **OPTIONAL**): Comma-delimited list of delegations
    the host wants to handle. **MAY** be empty if no delegations are needed.
    **SHOULD** be a subset of `config.delegate` from the embedded service binding.

## Transport & Messaging

ECaP uses the shared EP transport layer. See
[Embedded Protocol — Transport & Messaging](embedded-protocol.md#transport-messaging)
for message format, message types, and response handling conventions.

The `ucp.version` in all responses **MUST** echo the `ep_version` negotiated
during session initialization and confirmed by the host in the `ep.cart.ready`
response. The version is session-bound — it **MUST NOT** change for the duration
of the ECaP session.

### Communication Channels

ECaP follows the shared EP communication channel model. See
[Embedded Protocol — Communication Channels](embedded-protocol.md#communication-channels)
for the general pattern.

For native hosts, the cart-specific globals are:

- `window.EmbeddedCartProtocolConsumer` (preferred)
- `window.webkit.messageHandlers.EmbeddedCartProtocolConsumer`
- `window.EmbeddedCartProtocol` (Host → Embedded Cart)

## Message API Reference

### Message Categories

#### Core Messages

Core messages are defined by the ECaP specification and **MUST** be supported by
all implementations.

| Category          | Purpose                                                                   | Pattern                | Core Messages                                                                             |
| :---------------- | :------------------------------------------------------------------------ | :--------------------- | :---------------------------------------------------------------------------------------- |
| **Handshake**     | Establish connection between host and Embedded Cart.                      | Request                | `ep.cart.ready`                                                                           |
| **Authentication**| Communicate auth data exchanges between Embedded Cart and host.           | Request                | `ep.cart.auth`                                                                            |
| **Lifecycle**     | Inform of cart state in Embedded Cart.                                    | Notification           | `ep.cart.start`, `ep.cart.complete`                                                       |
| **State Change**  | Inform of cart field changes.                                             | Notification           | `ep.cart.line_items.change`, `ep.cart.buyer.change`, `ep.cart.messages.change`            |
| **Session Error** | Signal a session-level error unrelated to the cart resource.              | Notification           | `ep.cart.error`                                                                           |

### Handshake Messages

#### `ep.cart.ready`

Upon rendering, the Embedded Cart **MUST** broadcast readiness to the parent
context using the `ep.cart.ready` message. This message initializes a secure
communication channel between the host and Embedded Cart, communicates whether
or not additional auth exchange is needed, and allows the host to provide
any requested authorization data back to Embedded Cart.

- **Direction:** Embedded Cart → Host
- **Type:** Request
- **Payload:**
    - `delegate` (array of strings, **REQUIRED**): List of delegation
        identifiers accepted by the Embedded Cart. **MUST** be a subset of
        both `ep_cart_delegate` (what host requested) and `config.delegate`
        from the cart response (what business allows). An empty array
        means no delegations were accepted.
    - `auth` (object, **OPTIONAL**): When `ep_auth` URL param is neither sufficient
        nor applicable due to additional considerations, business can request for
        authorization during initial handshake by specifying the `type` string
        within this object. This `type` string value is a mirror of the payload content
        included in [`ep.cart.auth`](#epcartauth).

**Example Message (no delegations accepted):**

```json
{
    "jsonrpc": "2.0",
    "id": "ready_1",
    "method": "ep.cart.ready",
    "params": {
        "delegate": [],
        "auth": {
            "type": "oauth"
        }
    }
}
```

The `ep.cart.ready` message is a request, which means that the host **MUST** respond
to complete the handshake.

- **Direction:** Host → Embedded Cart
- **Type:** Response
- **Result Payload:**
    - `ucp` (object, **REQUIRED**): UCP protocol metadata. The `version`
        confirms the negotiated `ep_version` and `status` **MUST** be
        `"success"`.
    - `upgrade` (object, **OPTIONAL**): An object describing how the Embedded
        Cart should update the communication channel it uses to communicate
        with the host. When present, host **MUST NOT** include `credential`
        — the channel will be re-established and any credential sent here
        will be discarded.
    - `credential` (string, **OPTIONAL**): The requested authorization data,
        can be in the form of an OAuth token, JWT, API keys, etc. **MUST** be
        set if `auth` is present in the request. **MUST NOT** be set if
        `upgrade` is present.

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "id": "ready_1",
    "result": {
        "ucp": { "version": "{{ ucp_version }}", "status": "success" },
        "credential": "fake_identity_linking_oauth_token"
    }
}
```

Hosts **MAY** respond with an `upgrade` field to update the communication
channel between host and Embedded Cart. Currently, this object only supports
a `port` field, which **MUST** be a `MessagePort` object, and **MUST** be
transferred to the embedded cart context (e.g., with `{transfer: [port2]}`
on the host's `iframe.contentWindow.postMessage()` call):

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "id": "ready_1",
    "result": {
        "ucp": { "version": "{{ ucp_version }}", "status": "success" },
        "upgrade": {
            "port": "[Transferable MessagePort]"
        }
    }
}
```

When the host responds with an `upgrade` object, the Embedded Cart **MUST**
discard any other information in the message, send a new `ep.cart.ready` message
over the upgraded communication channel, and wait for a new response. All
subsequent messages **MUST** be sent only over the upgraded communication
channel.

If the host cannot complete the handshake (e.g., origin validation failure or
protocol state violation), it **MUST** respond with an `error_response` result.
When the host responds with an error, the session cannot proceed. The host
**MUST** tear down the embedded context and **MAY** redirect the buyer to
`continue_url` if present. The Embedded Cart **MUST NOT** send further
messages after receiving a handshake error.

### Authentication

#### `ep.cart.auth`

`ep.cart.auth` implements the shared EP authentication pattern — see
[Embedded Protocol — Authentication](embedded-protocol.md#authentication) for
the request/response contract, examples, and error escalation flow.

- **Method:** `ep.cart.auth`
- **Direction:** Embedded Cart → Host (request); Host → Embedded Cart (response)

When error escalation is required, Embedded Cart **MUST** issue an
`ep.cart.error` notification per the
[session error pattern](embedded-protocol.md#session-error).

### Lifecycle Messages

Lifecycle notifications follow the shared EP pattern — see
[Embedded Protocol — Lifecycle](embedded-protocol.md#lifecycle). All lifecycle
notifications carry the full `cart` object as their payload.

#### `ep.cart.start`

Signals that cart is visible and ready for interaction. Sent after a successful
`ep.cart.ready` handshake.

- **Direction:** Embedded Cart → Host
- **Type:** Notification
- **Payload:**
    - `cart` (object, **REQUIRED**): The full current state of the cart.

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "method": "ep.cart.start",
    "params": {
        "cart": {
            "id": "cart_123",
            "currency": "USD",
            "totals": [/* ... */],
            "line_items": [/* ... */],
            "buyer": {/* ... */},
            // ...other cart fields...
        }
    }
}
```

#### `ep.cart.complete`

Indicates completion of cart building process and buyer now is ready to be
transitioned to the next stage of their purchase journey.

This marks the completion of Embedded Cart. If `dev.ucp.shopping.checkout` is
part of the negotiated capabilities during service discovery, host **MAY**
proceed to initiate a checkout session based on the completed cart by issuing a
[create checkout](checkout.md#create-checkout) operation.

- **Direction:** Embedded Cart → Host
- **Type:** Notification
- **Payload:**
    - `cart` (object, **REQUIRED**): The final state of the cart.

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "method": "ep.cart.complete",
    "params": {
        "cart": {
            "id": "cart_123",
            "currency": "USD",
            "totals": [/* ... */],
            "line_items": [/* ... */],
            "buyer": {/* ... */},
            // ...other cart fields...
        }
    }
}
```

### State Change Messages

State change notifications follow the shared EP pattern — see
[Embedded Protocol — State Change](embedded-protocol.md#state-change). All state
change notifications are sent from the Embedded Cart to the host and carry the
full `cart` object as their payload.

#### `ep.cart.line_items.change`

Line items have been modified (quantity changed, items added/removed).

- **Direction:** Embedded Cart → Host
- **Type:** Notification
- **Payload:**
    - `cart` (object, **REQUIRED**): The full current state of the cart.

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "method": "ep.cart.line_items.change",
    "params": {
        "cart": {
            "id": "cart_123",
            // The entire cart object is provided, including the updated line items and estimated totals
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

#### `ep.cart.buyer.change`

Buyer information has been updated (email, phone, name).

- **Direction:** Embedded Cart → Host
- **Type:** Notification
- **Payload:**
    - `cart` (object, **REQUIRED**): The full current state of the cart.

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "method": "ep.cart.buyer.change",
    "params": {
        "cart": {
            "id": "cart_123",
            // The entire cart object is provided, including the updated buyer information
            "buyer": {
                /* ... */
            }
            // ...
        }
    }
}
```

#### `ep.cart.messages.change`

Cart messages have been updated. Messages include errors, warnings, and
informational notices about the cart state.

- **Direction:** Embedded Cart → Host
- **Type:** Notification
- **Payload:**
    - `cart` (object, **REQUIRED**): The full current state of the cart.

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "method": "ep.cart.messages.change",
    "params": {
        "cart": {
            "id": "cart_123",
            // The entire cart object is provided, including any updated messages
            "messages": [
                {
                    "type": "error",
                    "code": "invalid_quantity",
                    "path": "$.line_items[0].quantity",
                    "content": "Quantity must be at least 1",
                    "severity": "recoverable"
                }
            ]
            // ...
        }
    }
}
```

### Session Error Messages

#### `ep.cart.error`

`ep.cart.error` implements the shared EP session error pattern — see
[Embedded Protocol — Session Error](embedded-protocol.md#session-error) for the
payload specification and host handling requirements.

## Security & Error Handling

### Error Codes

ECaP uses the shared EP error code set — see
[Embedded Protocol — Error Codes](embedded-protocol.md#error-codes).

### Security for Web-Based Hosts

ECaP inherits the shared EP security requirements for CSP, iframe sandboxing,
credentialless iframes, and strict origin validation. See
[Embedded Protocol — Security](embedded-protocol.md#security) for the full
specification.

## Schema Definitions

The following schemas define the data structures used within the Embedded
Cart protocol.

### Cart

The core object representing the current state of the cart, including
line items, totals, and buyer information.

{{ schema_fields('cart_resp', 'cart') }}
