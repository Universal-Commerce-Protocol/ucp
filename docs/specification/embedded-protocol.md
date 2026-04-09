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

# Embedded Protocol (EP)

## Introduction

The Embedded Protocol (EP) is a UCP transport binding that enables a **host** to
embed a **business's** interface in an iframe or webview and exchange structured
messages over that channel. EP defines **how** to communicate — message format,
channel setup, authentication, error handling, and security constraints. It does
not define **what** data exists; that is the responsibility of each capability
that binds to EP.

Each capability implements EP methods under its own method prefix. For example,
checkout uses the `ec.*` prefix and cart uses the `ep.cart.*` prefix. The shared
patterns described in this document apply uniformly across all EP capabilities.

Capability-specific details — discovery, URL parameters, delegation contracts,
message payloads, and schema definitions — are defined in each capability's EP
binding specification:

- [Checkout Capability — EP Binding](embedded-checkout.md)
- [Cart Capability — EP Binding](embedded-cart.md)

## Terminology & Actors

### Commerce Roles

- **Business:** The seller providing goods or services.
- **Buyer:** The end user making a purchase.

### Technical Components

- **Host:** The application embedding the business's interface (e.g., AI Agent
    app, Super App, Browser). Responsible for user authentication and, when
    delegated, native UI for actions such as payment and address selection.
- **Embedded Context:** The business's interface rendered in an iframe or
    webview. Responsible for the capability-specific flow (e.g., checkout,
    cart building).

## Transport & Messaging

### Message Format

All EP messages **MUST** use JSON-RPC 2.0 format
([RFC 7159](https://datatracker.ietf.org/doc/html/rfc7159)). Each message
**MUST** contain:

- `jsonrpc`: **MUST** be `"2.0"`
- `method`: The message name (e.g., `"ec.start"`, `"ep.cart.start"`)
- `params`: Message-specific payload (may be empty object)
- `id`: (Optional) Present only for requests that expect responses

### Message Types

**Requests** (with `id` field):

- Require a response from the receiver
- **MUST** include a unique `id` field
- Receiver **MUST** respond with matching `id`
- Response **MUST** be either a `result` or an `error_response`
- Used for operations requiring acknowledgment or data

**Notifications** (without `id` field):

- Informational only, no response expected
- **MUST NOT** include an `id` field
- Receiver **MUST NOT** send a response
- Used for state updates and informational events

### Response Handling

For requests (messages with `id`), receivers **MUST** respond with a `result`.
Both success and error outcomes **MUST** be returned via the `result` field,
consistent with UCP's two-layer error model. The JSON-RPC `error` field is
reserved for transport-level failures (parse errors, method not found, invalid
params). Implementations **MUST NOT** use the JSON-RPC `error` field for
application-level error codes.

**Success Response:**

```json
{
  "jsonrpc": "2.0",
  "id": "...",
  "result": {
    "ucp": { "version": "{{ ucp_version }}", "status": "success" },
    ...
  }
}
```

**Error Response:**

```json
{
  "jsonrpc": "2.0",
  "id": "...",
  "result": {
    "ucp": { "version": "{{ ucp_version }}", "status": "error" },
    "messages": [...]
  }
}
```

In both cases, `result.ucp.status` serves as the discriminator between success
and error outcomes — the same pattern used across all UCP transports.

### Transport Errors

Transport errors are protocol-level failures that prevent request processing.
These are returned as JSON-RPC `error` using standard JSON-RPC error codes and
indicate the message itself is invalid or could not be processed — not that
executed business logic produced an error outcome. See the
[Core Specification](overview.md#error-codes) for the complete error code
registry.

For example, if a request cannot be processed (unknown method, malformed
params), the host **MUST** respond with a JSON-RPC `error`:

```json
{
    "jsonrpc": "2.0",
    "id": "req_1",
    "error": {
        "code": -32601,
        "message": "Method not found."
    }
}
```

## Communication Channels

### Web-Based Hosts

When the host is a web application, communication starts using `postMessage`
between the host and the embedded context's window. The host **MUST** listen for
`postMessage` calls from the embedded window, and when a message is received,
**MUST** validate that the origin matches the `continue_url` used to start the
session.

Upon validation, the host **MAY** create a `MessageChannel` and transfer one of
its ports in the `ready` response. When a host responds with a `MessagePort`,
all subsequent messages **MUST** be sent over that channel. Otherwise, the host
and business **MUST** continue using `postMessage()` between their `window`
objects, including origin validation.

### Native Hosts

When the host is a native application, it **MUST** inject globals into the
embedded context that allow `postMessage` communication between the web and
native environments. Each capability defines the names of its globals following
the pattern:

- `window.Embedded{Capability}ProtocolConsumer` (preferred)
- `window.webkit.messageHandlers.Embedded{Capability}ProtocolConsumer`

This object **MUST** implement the following interface:

```javascript
{
  postMessage(message: string): void
}
```

Where `message` is a JSON-stringified JSON-RPC 2.0 message. The host **MUST**
parse the JSON string before processing.

For messages traveling from the host to the embedded context, the host **MUST**
inject JavaScript in the webview that calls
`window.Embedded{Capability}Protocol.postMessage()` with the JSON-RPC message.
The embedded context **MUST** initialize this global object — and start listening
for `postMessage()` calls — before the capability's `ready` message is sent.

See each capability's EP binding for the specific global names:

- **Checkout:** `EmbeddedCheckoutProtocolConsumer` / `EmbeddedCheckoutProtocol`
- **Cart:** `EmbeddedCartProtocolConsumer` / `EmbeddedCartProtocol`

## Message Patterns

### Handshake

Upon rendering, the embedded context **MUST** broadcast readiness to the host
using the capability's `ready` message. This message initializes a secure
communication channel between the host and embedded context, communicates which
delegations were accepted, and signals whether additional authorization exchange
is needed.

**General flow:**

1. Embedded context sends a `ready` request with a `delegate` list and optional
   `auth` request
2. Host responds with:
    - `ucp` envelope confirming the negotiated protocol version
    - Optional `upgrade` with a `MessagePort` for channel upgrade
    - Optional `credential` with requested authorization data
    - Optional capability-specific state (e.g., checkout delegation state)
3. If the host includes an `upgrade`, the embedded context **MUST** discard all
   other fields in the response, switch to the upgraded channel, and send a new
   `ready` message over that channel
4. If the host responds with an `error_response` result, the session cannot
   proceed — the host **MUST** tear down the embedded context and **MAY**
   redirect the buyer to `continue_url` if available. The embedded context
   **MUST NOT** send further messages after receiving a handshake error.

Each capability defines the full `ready` method specification, including
capability-specific parameters and result fields.

### Authentication

The embedded context **MAY** request authorization from the host after the
initial handshake — for example, to refresh an expired OAuth token. This
exchange uses the capability's auth method (e.g., `ec.auth` for checkout,
`ep.cart.auth` for cart).

**Request:**

- **Direction:** Embedded Context → Host
- **Type:** Request
- **Payload:**
    - `type` (string, **REQUIRED**): The requested authorization type (e.g.,
        `"oauth"`, `"api_key"`, `"jwt"`).

**Success Response:**

- **Direction:** Host → Embedded Context
- **Type:** Response
- **Result Payload:**
    - `ucp` (object, **REQUIRED**): UCP protocol metadata with
        `status: "success"`.
    - `credential` (string, **REQUIRED**): The requested authorization data.

**Error Response:**

The host **MUST** respond with a `result` containing either the authorization
data or an `error_response`.

**Example Success Response:**

```json
{
    "jsonrpc": "2.0",
    "id": "auth_1",
    "result": {
        "ucp": { "version": "{{ ucp_version }}", "status": "success" },
        "credential": "eyJhbGciOiJSUzI1NiIs..."
    }
}
```

**Example Error Response:**

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

**Error Escalation:**

If the error is transient (indicated by `recoverable` severity), the embedded
context **MAY** re-initiate the auth request. Otherwise, the embedded context
**MUST** issue a session error notification (see [Session Error](#session-error))
containing an `unrecoverable` error response. This escalation also applies when
the embedded context is unable to process a host-provided credential (e.g.,
the credential is corrupted). The session error **SHOULD** include a
`continue_url` to allow buyer handoff.

**Example — auth failure escalated to session error:**

```json
{
    "jsonrpc": "2.0",
    "method": "ec.error",
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

When the host receives this notification, it **MUST** tear down the embedded
context and **SHOULD** display an appropriate error state. If `continue_url` is
present, the host **MUST** use it to hand off the buyer for session recovery.

### Session Error

A session error signals a fatal condition unrelated to the capability's resource
— for example, a terminal auth failure that prevents the session from
continuing. Each capability defines its own session error notification method
(e.g., `ec.error` for checkout, `ep.cart.error` for cart).

**Notification Payload:**

- `ucp` (object, **REQUIRED**): UCP protocol metadata. `status` **MUST** be
    `"error"`.
- `messages` (array, **REQUIRED**): One or more messages describing the failure.
- `continue_url` (string, **OPTIONAL**): URL for buyer handoff or session
    recovery.

**Example:**

```json
{
    "jsonrpc": "2.0",
    "method": "ec.error",
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
        "continue_url": "https://merchant.example.com/checkout/abc123"
    }
}
```

**Host Handling:**

When the host receives a session error notification, it **MUST** tear down the
embedded context and **SHOULD** display an appropriate error state to the buyer.
If `continue_url` is present, the host **MUST** use it to hand off the buyer for
session recovery.

### Lifecycle

Each capability defines `start` and `complete` notification methods that follow
a shared contract:

- **`start`**: The embedded context notifies the host that the UI is visible and
    ready for interaction. The notification **MUST** include the full current
    state of the capability's resource (e.g., the checkout or cart object).
- **`complete`**: The embedded context notifies the host that the capability
    flow has finished successfully. The notification **MUST** include the final
    state of the resource.

Both are notifications — the host **MUST NOT** respond.

**Example — start notification (cart):**

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
            "buyer": {/* ... */}
        }
    }
}
```

**Example — complete notification (checkout):**

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

### State Change

State change notifications inform the host of changes that have already occurred
in the embedded context. These are informational only — the embedded context has
already applied the changes and rendered the updated UI. The host **MUST NOT**
respond to state change notifications.

Each capability defines its own set of state change methods covering the
relevant resource fields (e.g., line items, buyer information, totals). State
change notifications **MUST** include the full current state of the capability's
resource, not just the changed fields.

**Example — line items changed (checkout):**

```json
{
    "jsonrpc": "2.0",
    "method": "ec.line_items.change",
    "params": {
        "checkout": {
            "id": "checkout_123",
            "totals": [/* ... */],
            "line_items": [/* ... */]
            // ... other checkout fields
        }
    }
}
```

**Example — messages changed (cart):**

```json
{
    "jsonrpc": "2.0",
    "method": "ep.cart.messages.change",
    "params": {
        "cart": {
            "id": "cart_123",
            "line_items": [/* ... */],
            "messages": [
                {
                    "type": "error",
                    "code": "invalid_quantity",
                    "path": "$.line_items[0].quantity",
                    "content": "Quantity must be at least 1",
                    "severity": "recoverable"
                }
            ]
            // ... other cart fields
        }
    }
}
```

## Error Codes

The Embedded Protocol defines a shared set of error codes. Capabilities
**MAY** define additional error codes for capability-specific scenarios.

| Code                  | Severity        | Description                                                          |
| :-------------------- | :-------------- | :------------------------------------------------------------------- |
| `abort_error`         | `recoverable`   | The user cancelled the interaction (e.g., closed the sheet).         |
| `security_error`      | `unrecoverable` | The host origin validation failed.                                   |
| `invalid_state_error` | `unrecoverable` | Handshake was attempted out of order.                                |
| `not_supported_error` | `unrecoverable` | The requested operation or authorization type is not supported.      |
| `timeout_error`       | `recoverable`   | An internal service timed out. The operation may be retried.         |

Errors **SHOULD** use only `recoverable` and `unrecoverable` severities.
`recoverable` means the operation may be re-attempted. `unrecoverable` means
the operation cannot succeed in the current session.

## Security

### Content Security Policy (CSP)

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

### Iframe Sandbox Attributes

All business iframes **MUST** be sandboxed to restrict their capabilities. The
following sandbox attributes **SHOULD** be applied, but a host and business
**MAY** negotiate additional capabilities:

```html
<iframe sandbox="allow-scripts allow-forms allow-same-origin"></iframe>
```

### Credentialless Iframes

Hosts **SHOULD** use the `credentialless` attribute on the iframe to load it in
a new, ephemeral context. This prevents the business from correlating user
activity across contexts or accessing existing sessions, protecting user
privacy.

```html
<iframe credentialless src="https://business.example.com/..."></iframe>
```

### Strict Origin Validation

Enforce strict validation of the `origin` for all `postMessage` communications
between frames.
