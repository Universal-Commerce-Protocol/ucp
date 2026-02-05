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
**host** to embed a **business's** cart interface, receive events as the
buyer interacts with the cart, and offer a seamless transition into
lower-funnel capabilities (i.e. checkout)'s EP binding (i.e. ECP).
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
        "dev.ucp.shopping": {
            "version": "2026-01-23",
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

- All `continue_url` values returned by that business support ECaP
- ECaP version matches the service's UCP version
- If business also supports Embedded Checkout Protocol (ECP) via their `embedded`
  service definition, then transition from ECaP to ECP is supported

When `embedded` is absent from the service definition, the business only
supports redirect-based cart continuation via `continue_url`.

### Loading an Embedded Checkout URL

When a host receives a cart response with a `continue_url` from a business
that advertises ECaP support, it **MAY** initiate an ECaP session by loading the
URL in an embedded context.

Before loading the embedded context, the host **SHOULD**:

1. Optionally complete authentication mechanisms (i.e. identity linking)
   if required by the business

To initiate the session, the host **MUST** augment the `continue_url` with ECaP
query parameters using the `ect_` prefix.

All ECaP parameters are passed via URL query string, not HTTP headers, to ensure
maximum compatibility across different embedding environments. Parameters use
the `ect_` prefix to avoid namespace pollution and clearly distinguish ECaP
parameters from business-specific query parameters:

- `ect_version` (string, **REQUIRED**): The UCP version for this session
    (format: `YYYY-MM-DD`). Must match the version from service discovery.

## Transport & Messaging

### Message Format

All ECaP messages **MUST** use JSON-RPC 2.0 format
([RFC 7159](https://datatracker.ietf.org/doc/html/rfc7159)). Each message **MUST** contain:

- `jsonrpc`: **MUST** be `"2.0"`
- `method`: The message name (e.g., `"ect.start"`)
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
checkout.

Upon validation, the host **MAY** create a `MessageChannel`, and transfer one of
its ports in the result of the [`ect.ready` response](#ectready). When a host
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
for `postMessage()` calls — before the `ect.ready` message is sent.

## Message API Reference

### Message Categories

#### Core Messages

Core messages are defined by the ECaP specification and **MUST** be supported by
all implementations.

| Category          | Communication Direction | Purpose                                                                   | Pattern                | Core Messages                                                                             |
| :---------------- | :---------------------- | :------------------------------------------------------------------------ | :--------------------- | :---------------------------------------------------------------------------------------- |
| **Handshake**     | Embedded Cart -> Host   | Establish connection between host and Embedded Cart.                      | Request                | `ect.ready`                                                                               |
| **Authentication**| Host <-> Embedded Cart  | Communicate auth data exchanges between Embedded Cart and host.           | Notification & Request | `ect.auth` (Request), `ect.auth.change` (Notification)                                    |
| **Lifecycle**     | Embedded Cart -> Host   | Inform of cart state in Embedded Cart.                                    | Notification           | `ect.start`                                                                               |
| **Transition**    | Embedded Cart -> Host   | Establish transition from cart to other capabilities.                     | Request                | `ect.transition.checkout`                                                                 |
| **State Change**  | Embedded Cart -> Host   | Inform of cart field changes.                                             | Notification           | `ect.line_items.change`, `ect.buyer.change`, `ect.context.change`, `ect.messages.change`  |

### Handshake Messages

#### `ect.ready`

Upon rendering, the Embedded Cart **MUST** broadcast readiness to the parent
context using the `ect.ready` message. This message initializes a secure
communication channel between the host and Embedded Cart, communicates whether
or not additional auth exchange is needed, and allows the host to provide
additional, display-only state for the cart that was not communicated over
UCP cart actions.

- **Direction:** Embedded Cart → host
- **Type:** Request
- **Payload:**
    - `require_auth` (boolean, **REQUIRED**): This boolean bit indicates
    whether business requires additional auth exchanges with the host
    prior to injecting the cart state.

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "id": "ready_1",
    "method": "ect.ready",
    "params": {
        "require_auth": true
    }
}
```

The `ect.ready` message is a request, which means that the host **MUST** respond
to complete the handshake.

- **Direction:** host → Embedded Cart
- **Type:** Response
- **Result Payload:**
    - `upgrade` (object, **OPTIONAL**): An object describing how the Embedded
        Cart should update the communication channel it uses to communicate
        with the host.

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "id": "ready_1",
    "result": {}
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
discard any other information in the message, send a new `ect.ready` message
over the upgraded communication channel, and wait for a new response. All
subsequent messages **MUST** be sent only over the upgraded communication
channel.

### Authentication

#### `ect.auth`

Exchange any required auth data from host per business
requirements (i.e. when identity linking is a pre-requisite).

- **Direction:** Host → Embedded Cart
- **Type:** Request
- **Payload:**
    - `authorization` (string, **REQUIRED**): The required authorization data by
    business, can be in the form of an OAuth token, JWT, API keys, etc.

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "id": "auth_1",
    "method": "ect.auth",
    "params": {
        "authorization": "fake_token_from_identity_linking"
    }
}
```

The `ect.auth` message is a request, which means that Embedded Cart
**MUST** respond to acknowledge receiving the authorization.

- **Direction:** Embedded Cart → host
- **Type:** Response
- **Result Payload:**
    - Empty payload means the exchange is successful (Embedded Cart
    is able to ingest the authorization shared by the host).

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "id": "auth_1",
    "result": {}
}
```

Embedded Cart **MAY** respond with errors if the ingestion of
the authorization is not successful.

**Example Message (errors):**

```json
{
    "jsonrpc": "2.0",
    "id": "auth_1",
    "error": {...}
}
```

Embedded Cart **SHOULD** use error codes mapped to
**[W3C DOMException](https://webidl.spec.whatwg.org/#idl-DOMException)** names
where possible.

#### `ect.auth.change`

Informs host that auth state has changed on Embedded Cart side. A common
example would be when OAuth access token has expired.

- **Direction:** Embedded Cart → host
- **Type:** Notification
- **Payload:**
    - `require_reauth` (boolean, **REQUIRED**): This boolean bit indicates
    whether business requires another auth exchange via `ect.auth` with
    host as a result of the auth state change.

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "method": "ect.auth.change",
    "params": {
        "require_reauth": true
    }
}
```

When a notification is received indicating reauth is required,
host **MUST** reprepare relevant authorization per business
requirements and initiate an `ect.auth`
request back to Embedded Cart.

### Lifecycle Messages

#### `ect.start`

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
    "method": "ect.start",
    "params": {
        "cart": {
            "id": "cart_123",
            "currency": "USD",
            "totals": [/* ... */],
            "line_items": [/* ... */],
            "buyer": {/* ... */},
            "context": {/* ... */}
        }
    }
}
```

### Transition Messages

#### `ect.transition.checkout`

Indicates completion of cart building process and buyer now seamlessly transitions from
ECaP to ECP. This marks the completion of Embedded Cart and host **MUST** listen for
`ec.ready` handshake adhering to [ECP's specification](site:specification/embedded-checkout)
over the same communication channel established during `ect.ready`.

- **Direction:** Embedded Cart → host
- **Type:** Request
- **Payload:**
    - `cart` (object, **REQUIRED**): The latest state of the cart, using the same structure
        as the `cart` object in UCP responses.
    - `checkout` (object, **REQUIRED**): The initial state of the checkout session
        based on the cart object above.

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "id": "transition_1",
    "method": "ect.transition.checkout",
    "params": {
        "cart": {
            "id": "cart_123",
            "currency": "USD",
            "totals": [/* ... */],
            "line_items": [/* ... */],
            "buyer": {/* ... */},
            "context": {/* ... */}
        },
        "checkout": {
            "id": "checkout_123",
            "cart_id": "cart_123",
            // ... other checkout fields based on the cart
        }
    }
}
```

The `ect.transition.checkout` message is a request, which means that the
host **MUST** respond to acknowledge the transition.

- **Direction:** host → Embedded Cart
- **Type:** Response
- **Result Payload:**
    - `delegation` (array, **OPTIONAL**): An array containing delegation
    requests from host as part of Embedded Checkout Protocol.

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "id": "transition_1",
    "result": {}
}
```

Hosts **MAY** respond with a `delegate` field to request for operations
they would like to handle natively. See [ECP's
documentation](site:specification/embedded-checkout/#delegation) for more details.

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "id": "transition_1",
    "result": {
        "delegate": ["payment.credential"]
    }
}
```

When the host responds with a `delegate` array, the Embedded Cart **MUST**
use it to instantiate the handshake on ECP.

### State Change Messages

State change messages inform the host of changes that have already occurred
in the cart interface. These are informational only. The cart has
already applied the changes and rendered the updated UI.

#### `ect.line_items.change`

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
    "method": "ect.line_items.change",
    "params": {
        "cart": {
            "id": "cart_123",
            // The entire cart object is provided, including the updated line items and totals
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

#### `ect.buyer.change`

Buyer information has been updated in the cart UI.

- **Direction:** Embedded Cart → host
- **Type:** Notification
- **Payload:**
    - `cart`: The latest state of the cart

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "method": "ect.buyer.change",
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

#### `ect.context.change`

Buyer context (i.e. localization signals) has been updated in the cart UI.

- **Direction:** Embedded Cart → host
- **Type:** Notification
- **Payload:**
    - `cart`: The latest state of the cart

**Example Message:**

```json
{
    "jsonrpc": "2.0",
    "method": "ect.context.change",
    "params": {
        "cart": {
            "id": "cart_123",
            // The entire cart object is provided, including the updated buyer context information
            "context": {
                /* ... */
            }
            // ...
        }
    }
}
```

#### `ect.messages.change`

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
    "method": "ec.messages.change",
    "params": {
        "cart": {
            "id": "cart_123",
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

## Schema Definitions

The following schemas define the data structures used within the Embedded
Cart protocol.

### Cart

The core object representing the current state of the cart, including
line items, totals, and buyer information.

{{ schema_fields('cart_resp', 'embedded-cart') }}
