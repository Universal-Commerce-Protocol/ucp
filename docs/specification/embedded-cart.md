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

### Message Format

All ECaP messages **MUST** use JSON-RPC 2.0 format
([RFC 7159](https://datatracker.ietf.org/doc/html/rfc7159)). Each message **MUST** contain:

- `jsonrpc`: **MUST** be `"2.0"`
- `method`: The message name (e.g., `"ep.cart.start"`)
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
between the host and Cart windows. The host **MUST** listen for
`postMessage` calls from the embedded window, and when a message is received,
they **MUST** validate the origin matches the `continue_url` used to start the
embedded cart.

Upon validation, the host **MAY** create a `MessageChannel`, and transfer one of
its ports in the result of the [`ep.cart.ready` response](#epcartready). When a host
responds with a `MessagePort`, all subsequent messages **MUST** be sent over
that channel. Otherwise, the host and business **MUST** continue using
`postMessage()` between their `window` objects, including origin validation.

#### Communication Channel for Native Hosts

When the host is a native application, they **MUST** inject globals into the
Embedded Cart that allows `postMessage` communication between the web and
native environments. The host **MUST** create at least one of the following
globals:

- `window.EmbeddedCartProtocolConsumer` (preferred)
- `window.webkit.messageHandlers.EmbeddedCartProtocolConsumer`

This object **MUST** implement the following interface:

```javascript
{
  postMessage(message: string): void
}
```

Where `message` is a JSON-stringified JSON-RPC 2.0 message. The host **MUST**
parse the JSON string before processing.

For messages traveling from the host to the Embedded Cart, the host **MUST**
inject JavaScript in the webview that will call
`window.EmbeddedCartProtocol.postMessage()` with the JSON RPC message. The
Embedded Cart **MUST** initialize this global object — and start listening
for `postMessage()` calls — before the `ep.cart.ready` message is sent.

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

- **Direction:** Embedded Cart → host
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

### Authentication

#### `ep.cart.auth`

Embedded cart **MAY** request authorization from the host in the following scenarios:

1. **Reauth**: Certain authentication methods (i.e. OAuth token) have strict expiration timestamps.
If a session lasted longer than the allowed duration, business can request for a refreshed
authorization to be provided by the host before the session continues.

- **Direction:** Embedded Cart → Host
- **Type:** Request
- **Payload:**
    - `type` (string, **REQUIRED**): The requested authorization type.

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "id": "auth_1",
    "method": "ep.cart.auth",
    "params": {
        "type": "oauth"
    }
}
```

The `ep.cart.auth` message is a request, which means that host
**MUST** respond to exchange the authorization. The host **MUST** respond with either an error,
or the authorization data requested by Embedded Cart.

- **Direction:** host → Embedded Cart
- **Type:** Response
- **Result Payload:**
    - `credential` (string, **REQUIRED**): The requested authorization data,
    can be in the form of an OAuth token, JWT, API keys, etc.

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "id": "auth_1",
    "result": {
        "credential": "fake_identity_linking_oauth_token"
    }
}
```

**Example Error Message:**

```json
{
    "jsonrpc": "2.0",
    "id": "auth_1",
    "result": {
        "ucp": { "version": "{{ ucp_version }}", "status": "error" },
        "messages": [
            {
                "type": "error",
                "code": "timeout_error",
                "content": "An internal service timed out when fetching the required authorization data.",
                "severity": "recoverable"
            }
        ]
    }
}
```

If the error appears to be transient within the host (i.e. `timeout_error`) - as indicated with
`recoverable` severity - Embedded Cart **MAY** re-initiate this request with the host again.
Otherwise, Embedded Cart **MUST** issue an `ep.cart.error` notification containing an `unrecoverable`
error response. The same mechanism can also be used in the happy path if Embedded Cart is
unable to process the host-provided authorization data (i.e. credential is corrupted).
This response **SHOULD** also contain a `continue_url` to allow buyer handoff.

**Example Error Response Message Through ep.cart.error:**

```json
{
    "jsonrpc": "2.0",
    "method": "ep.cart.error",
    "params": {
        "ucp": { "version": "{{ ucp_version }}", "status": "error" },
        "messages": [
            {
                "type": "error",
                "code": "not_supported_error",
                "content": "Requested auth credential type is not supported",
                "severity": "unrecoverable"
            }
        ],
        "continue_url": "https://merchant.example.com"
    }
}
```

When the host receives this error response, they **MUST** tear down the iframe and **SHOULD**
display a custom error screen to set proper buyer expectation. If a `continue_url` is present in
the error response, host **MUST** use it to handoff the buyer for session recovery.

### Lifecycle Messages

#### `ep.cart.start`

Signals that cart is visible and ready for interaction.

- **Direction:** Embedded Cart → host
- **Type:** Notification
- **Payload:**
    - `cart` (object, **REQUIRED**): The latest state of the cart,
    using the same structure as the `cart` object in UCP responses.

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

Indicates completion of cart building process and buyer now is ready to be transitioned to
the next stage of their purchase journey.

This marks the completion of Embedded Cart. If `dev.ucp.shopping.checkout` is part of the negotiated
capabilities during service discovery, host **MAY** proceed to initiate a checkout session based on the
completed cart by issuing a [create checkout](checkout.md#create-checkout) operation.

- **Direction:** Embedded Cart → host
- **Type:** Notification
- **Payload:**
    - `cart` (object, **REQUIRED**): The latest state of the cart, using the same structure
        as the `cart` object in UCP responses.

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

State change messages inform the host of changes that have already occurred
in the cart interface. These are informational only. The cart has
already applied the changes and rendered the updated UI.

#### `ep.cart.line_items.change`

Line items have been modified (quantity changed, items added/removed) in the
cart UI.

- **Direction:** Embedded Cart → host
- **Type:** Notification
- **Payload:**
    - `cart`: The latest state of the cart

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

Buyer information has been updated in the cart UI.

- **Direction:** Embedded Cart → host
- **Type:** Notification
- **Payload:**
    - `cart`: The latest state of the cart

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

- **Direction:** Embedded Cart → host
- **Type:** Notification
- **Payload:**
    - `cart`: The latest state of the cart

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

Signals a session-level error unrelated to the cart resource itself — for example,
a terminal auth failure that prevents the session from continuing.

- **Direction:** Embedded Cart → host
- **Type:** Notification
- **Payload:**
    - `ucp` (object, **REQUIRED**): UCP protocol metadata. `status` **MUST** be `"error"`.
    - `messages` (array, **REQUIRED**): One or more messages describing the failure.
    - `continue_url` (string, **OPTIONAL**): URL for buyer handoff or session recovery.

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "method": "ep.cart.error",
    "params": {
        "ucp": { "version": "{{ ucp_version }}", "status": "error" },
        "messages": [
            {
                "type": "error",
                "code": "not_supported_error",
                "content": "Requested auth credential type is not supported.",
                "severity": "unrecoverable"
            }
        ],
        "continue_url": "https://merchant.example.com/cart/abc123"
    }
}
```

When the host receives `ep.cart.error`, it **MUST** tear down the embedded context and **SHOULD**
display an appropriate error state to the buyer. If `continue_url` is present, host **MUST**
use it to hand off the buyer for session recovery.

## Security & Error Handling

### Error Codes

The message responder **SHOULD** use
error codes mapped to
**[W3C DOMException](https://webidl.spec.whatwg.org/#idl-DOMException)** names
where possible.

| Code                         | Description                                                                                                                                    |
| :--------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------- |
| `abort_error`                | The user cancelled the interaction (e.g., closed the sheet).                                                                                   |
| `security_error`             | The host origin validation failed.                                                                                                             |
| `invalid_state_error`        | Handshake was attempted out of order.                                                                                                          |
| `not_supported_error`        | The requested operation or authorization type is not supported by the host.                                                                    |

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
<iframe credentialless src="https://business.example.com/cart"></iframe>
```

#### Strict Origin Validation

Enforce strict validation of the `origin` for all `postMessage` communications
between frames.

## Schema Definitions

The following schemas define the data structures used within the Embedded
Cart protocol.

### Cart

The core object representing the current state of the cart, including
line items, totals, and buyer information.

{{ schema_fields('cart_resp', 'cart') }}
