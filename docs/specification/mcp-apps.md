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

# MCP Apps Integration

## Overview

[MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview)
(`io.modelcontextprotocol/ui`, specification version `2026-01-26`) is a Model
Context Protocol extension that lets MCP servers attach interactive, sandboxed
HTML views (`ui://` resources with media type `text/html;profile=mcp-app`) to
MCP tools.

This document specifies how UCP Businesses (acting as MCP servers) and UCP
Platforms (acting as MCP Apps hosts) use MCP Apps alongside UCP's MCP transport
bindings for **Catalog** (`dev.ucp.shopping.catalog.search` and
`dev.ucp.shopping.catalog.lookup`), **Cart** (`dev.ucp.shopping.cart`), and
**Ask** (`dev.ucp.common.ask`):

1. **Standard UCP tools and schemas remain unchanged.** Adding an MCP Apps view
   decorates a UCP tool's `_meta.ui` metadata without changing the tool's name,
   `inputSchema`, `outputSchema`, or `structuredContent` payload.
2. **Static templates, dynamic `structuredContent`.** Every `ui://` resource is
   a static, data-agnostic HTML template that Platforms can prefetch, cache, or
   vet ahead of time. Runtime commerce data arrives via
   `ui/notifications/tool-result` in `structuredContent`.
3. **Host-mediated UCP operations.** Views mutate UCP resources only by calling
   standard UCP MCP tools (`tools/call`) through the Platform host. The Platform
   enforces UCP capability negotiation, overwrites Platform-owned metadata
   (`arguments.meta`, `context`, `signals`, `attribution`), and keeps payment
   and order placement out of views.

MCP Apps is negotiated at the MCP protocol layer during `initialize` and does
not modify UCP JSON schemas or response payloads.

### Scope: Catalog, Cart, and Ask

MCP Apps views in UCP apply to pre-purchase discovery, cart building, and
guided inquiry (**Catalog**, **Cart**, and **Ask** capabilities). Tools of
capabilities that place a purchase or reservation, in any vertical (such as
`dev.ucp.shopping.checkout`, `dev.ucp.food.checkout`, and
`dev.ucp.lodging.booking`), and **Order** tools (such as those of
`dev.ucp.shopping.order`) **MUST NOT** attach MCP Apps views
(`_meta.ui.resourceUri`). See [Out of Scope](#out-of-scope).

When a Buyer is ready to purchase, a Catalog or Cart view hands off by calling
`create_checkout` (or opening `continue_url` via `ui/open-link`). Checkout then
continues in the Platform's checkout experience: its own trusted checkout UI,
or the Business's checkout embedded through the
[Embedded Protocol](embedded-protocol.md).

### Relationship to the Embedded Protocol

MCP Apps and the [Embedded Protocol](embedded-protocol.md) serve distinct
integration patterns:

| Aspect | MCP Apps (`io.modelcontextprotocol/ui`) | Embedded Protocol (`embedded-protocol.md`) |
| :--- | :--- | :--- |
| **Where it runs** | Business-authored template rendered by the Platform host on a host-controlled sandbox origin | The Business's own checkout web application, on the Business's origin |
| **Transport layer** | MCP transport only (`tools/list`, `resources/read`, `tools/call`) | Any UCP transport that returns a Checkout or Cart `continue_url` |
| **UI resource** | Static, data-agnostic `ui://` HTML template (`text/html;profile=mcp-app`) populated via `structuredContent` | Live per-session Business web application loaded from `continue_url` (`?ec_version=...`) |
| **Capability scope** | Catalog (`search_catalog`, `lookup_catalog`, `get_product`), Cart (`create_cart`, `get_cart`, `update_cart`), and Ask (`ask_business`) | Interactive Checkout and Cart handoff sessions (`continue_url`) |
| **Credentials & completion** | Prohibited in views; Checkout and `complete_checkout` remain Platform-owned | Supports payment/address/credential delegation (`ec.payment.*`, `ec.fulfillment.address_change_request`) and merchant-hosted completion |

### Out of Scope

**Checkout, payment, and order placement in views.** UCP defines payment and
Buyer consent on two surfaces: the Platform's own trusted checkout UI, which
[Checkout](shopping/checkout/index.md) requires for placing an order, and the
Business's own checkout through the [Embedded Protocol](embedded-protocol.md),
which runs on the Business's origin with negotiated payment delegation. An MCP
Apps view is neither: it is a Business-authored template that the Platform host
renders and whose rendered content the Platform cannot observe. A view
therefore never collects payment credentials, triggers order completion, or
replaces the Platform's checkout review.

## Discovery and Negotiation

MCP Apps support is negotiated during the MCP `initialize` handshake via
`capabilities.extensions["io.modelcontextprotocol/ui"]`:

<!-- ucp:example skip reason="MCP initialize capability snippet, not a UCP payload" -->
```json
{
  "capabilities": {
    "extensions": {
      "io.modelcontextprotocol/ui": {
        "mimeTypes": [
          "text/html;profile=mcp-app"
        ]
      }
    }
  }
}
```

UCP capability negotiation proceeds independently using the Platform profile and
the Business discovery profile (`/.well-known/ucp`), as defined in the
[Specification Overview](overview/index.md#negotiation-protocol).

To let a sandboxed view adapt its UI controls to the capabilities active in the
current session (for example, whether `dev.ucp.shopping.cart` or
`dev.ucp.shopping.checkout` is in the negotiated set when rendering a
`search_catalog` view), the Platform host **SHOULD** include the negotiated UCP
capability map in `McpUiInitializeResult.hostContext` under the `"dev.ucp"` key
when responding to the view's `ui/initialize` request. `"dev.ucp"` is a
UCP-defined key, not one of the host context fields defined by MCP Apps. If the
negotiated set changes while a view is displayed, the Platform host **SHOULD**
send the complete updated `"dev.ucp"` object in
`ui/notifications/host-context-changed`:

<!-- ucp:example skip reason="MCP Apps ui/initialize result, not a UCP payload" -->
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2026-01-26",
    "hostInfo": {
      "name": "example-platform-host",
      "version": "1.0.0"
    },
    "hostCapabilities": {
      "openLinks": {},
      "serverTools": {}
    },
    "hostContext": {
      "theme": "light",
      "platform": "web",
      "dev.ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.shopping.catalog.search": [{ "version": "{{ ucp_version }}" }],
          "dev.ucp.shopping.cart": [{ "version": "{{ ucp_version }}" }],
          "dev.ucp.shopping.checkout": [{ "version": "{{ ucp_version }}" }]
        }
      }
    }
  }
}
```

## Tool Declarations and Static `ui://` Templates

### Tool Metadata (`_meta.ui`)

A Business **MAY** declare an MCP Apps view on UCP Catalog, Cart, and Ask tools
by setting `_meta.ui.resourceUri` (and optional `_meta.ui.visibility`) in
`tools/list`. A Business **MUST NOT** change the UCP tool's name, `inputSchema`,
or `outputSchema` to do so.

* **Catalog, Cart, and Ask tools** (`search_catalog`, `lookup_catalog`,
  `get_product`, `create_cart`, `get_cart`, `update_cart`, `ask_business`)
  **MAY** declare `_meta.ui.resourceUri` and set
  `visibility: ["model", "app"]` (the default when omitted).
* **Checkout handoff (`create_checkout`):** A Business **MAY** set
  `visibility: ["model", "app"]` on `create_checkout` (without attaching a
  `_meta.ui.resourceUri`) so a Catalog or Cart view can initiate checkout
  handoff to the Platform's checkout experience.
* **Platform-only tools** (`get_checkout`, `update_checkout`,
  `complete_checkout`, `cancel_checkout`, `cancel_cart`, and Order tools such
  as `get_order`) **MUST** set `visibility: ["model"]` (and **MUST NOT**
  include `"app"`), ensuring a sandboxed view cannot directly read, modify, or
  complete a checkout, read an order, or cancel a cart or checkout.
* Any helper tool with `visibility: ["app"]` **MUST** be read-only and **MUST
  NOT** mutate UCP Cart, Checkout, or Order resources.

<!-- ucp:example skip reason="MCP tools/list definitions, not a UCP payload" -->
```json
{
  "tools": [
    {
      "name": "get_cart",
      "description": "Retrieve the current cart state.",
      "inputSchema": { "...": "..." },
      "outputSchema": { "...": "..." },
      "_meta": {
        "ui": {
          "resourceUri": "ui://merchant.example/cart-view.html",
          "visibility": ["model", "app"]
        }
      }
    },
    {
      "name": "complete_checkout",
      "description": "Complete the checkout and place the order.",
      "inputSchema": { "...": "..." },
      "outputSchema": { "...": "..." },
      "_meta": {
        "ui": {
          "visibility": ["model"]
        }
      }
    }
  ]
}
```

### Static `ui://` Resources

Every `ui://` resource referenced by a UCP tool **MUST** be a static,
data-agnostic HTML template with `mimeType: "text/html;profile=mcp-app"`. It
**MUST NOT** embed per-buyer, per-cart, or per-session data in the HTML asset
returned by `resources/read`. This is stricter than MCP Apps, which recommends
but does not require separating static templates from dynamic data.

* **Pre-registration and caching.** Because `ui://` templates are static, a
  Platform host **MAY** prefetch, cache, or require out-of-band registration
  and security vetting of `ui://` templates (along with their `_meta.ui.csp`
  and `_meta.ui.permissions` declarations) ahead of time, and serve its vetted
  copy at runtime, consistent with MCP Apps' allowance for hosts to prefetch
  and cache UI resources fetched via `resources/read`.
* **Content Security Policy (`_meta.ui.csp`).** A Business **MUST NOT** list
  any endpoint that mutates UCP resource state in `_meta.ui.csp.connectDomains`.
  All UCP state changes **MUST** flow through the Platform host via MCP
  `tools/call`.
* **No credential collection.** A view **MUST NOT** collect payment credentials
  (such as raw card numbers or card security codes) or account authentication
  secrets. Flows requiring credential entry **MUST** use
  [Identity Linking](common/identity-linking/index.md), the
  [Embedded Protocol](embedded-protocol.md), or hand off via `ui/open-link` to
  `continue_url`.

<!-- ucp:example skip reason="MCP resources/read response, not a UCP payload" -->
```json
{
  "contents": [
    {
      "uri": "ui://merchant.example/cart-view.html",
      "mimeType": "text/html;profile=mcp-app",
      "text": "<!DOCTYPE html><html>...</html>",
      "_meta": {
        "ui": {
          "csp": {
            "connectDomains": [],
            "resourceDomains": ["https://cdn.merchant.example"]
          },
          "prefersBorder": true
        }
      }
    }
  ]
}
```

## Runtime Lifecycle and Data Flow

```mermaid
sequenceDiagram
    participant Model as Agent / LLM
    participant Host as UCP Platform (MCP Host)
    participant Server as UCP Business (MCP Server)
    participant View as Sandboxed View (ui:// iframe)

    Model->>Host: Invoke UCP tool (e.g., search_catalog)
    Host->>Server: tools/call (search_catalog, arguments with meta)
    Server-->>Host: CallToolResult (structuredContent + content[])
    Host-->>Model: content[] (serialized UCP JSON)
    Host->>View: Render vetted ui:// template in sandboxed iframe
    View->>Host: ui/initialize
    Host-->>View: McpUiInitializeResult (hostContext["dev.ucp"].capabilities)
    View->>Host: ui/notifications/initialized
    Host->>View: ui/notifications/tool-input (arguments)
    Host->>View: ui/notifications/tool-result (structuredContent = UCP response)
    Note over View: Buyer selects variant & clicks "Add to Cart"
    View->>Host: tools/call (create_cart, arguments without meta)
    Note over Host: Strip/overwrite meta, context, signals, attribution;<br/>validate against composed UCP request schema
    Host->>Server: tools/call (create_cart, arguments with fresh meta)
    Server-->>Host: CallToolResult (updated Cart in structuredContent)
    Note over Host: Update held Cart state & render any<br/>presentation="disclosure" messages outside iframe
    Host-->>View: CallToolResult (updated Cart)
    View->>Host: ui/update-model-context (Cart summary for next turn)
```

The diagram shows one valid ordering. MCP Apps also permits a host to render
the view while tool execution is still in progress, in which case
`ui/notifications/tool-result` arrives once the tool completes.

1. **Dual-output tool result.** A decorated UCP tool returns its result as
   defined by the [MCP transport binding](overview/index.md#response-format):
   the UCP response object in `structuredContent` and, per that binding, its
   serialized JSON representation in `content[]`.
2. **View initialization and data delivery.** Once the view sends
   `ui/initialize` and `ui/notifications/initialized`, the Platform host
   delivers the tool arguments via `ui/notifications/tool-input` and the UCP
   response via `ui/notifications/tool-result` (in `params.structuredContent`).
   Any `messages` with `presentation: "disclosure"` in that response are
   rendered in Platform-owned UI outside the iframe, as required in
   [Security Considerations](#security-considerations).
3. **Monetary amounts.** A view **MUST** display monetary amounts exactly as
   received in `structuredContent`, without recomputing them. The UCP response
   fields in `structuredContent` remain authoritative, and the Platform's own
   checkout review is the authoritative presentation before purchase.
4. **Superseded views, cancellation, and teardown.** When a newer response for
   the same stateful resource (such as a Cart) arrives in the session, views
   rendered from older responses for that resource are superseded. The
   Platform **MAY** disable state-changing `tools/call` requests from a
   superseded view, and **MUST NOT** forward one without first obtaining Buyer
   confirmation in Platform-owned UI. As required by MCP Apps, the Platform
   sends `ui/notifications/tool-cancelled` when an in-flight tool execution is
   cancelled, and sends the `ui/resource-teardown` request (waiting for the
   view's response) before tearing down a view.

## View-Initiated Tool Calls and Platform Mediation

When a Buyer interacts with a control inside an MCP Apps view, the view
requests a UCP operation by sending a JSON-RPC `tools/call` request to the
Platform host over `postMessage`.

### Platform Host Requirements

For every `tools/call` request initiated by a view, the Platform host **MUST**:

1. **Enforce visibility and target scope.** Verify that the target tool belongs
   to the Business that served the view, is in a capability active in the
   negotiated UCP set, and has `"app"` in its `_meta.ui.visibility`, and reject
   every Platform UI Only operation listed below.
2. **Overwrite Platform-owned fields.** Set or overwrite `arguments.meta` with
   the Platform's own `ucp-agent` identifier and an `idempotency-key` that the
   Platform generates for each distinct Buyer action (reusing it only when the
   Platform itself retries that call), and strip or overwrite `context`,
   `signals`, and `attribution` (both at the top level of `arguments` and
   inside payload objects such as `cart` or `checkout`) using the Platform's
   own values. Views **SHOULD** omit `meta`; the Platform ignores any
   view-supplied `meta`. Because view-supplied idempotency keys are discarded,
   the Platform **SHOULD** suppress duplicate state-changing requests from
   repeated gestures (such as a double click) while an identical earlier
   request is in flight.
3. **Validate arguments and resource ownership.** Validate `arguments` against
   the operation's composed UCP request schema. Any stateful resource identifier
   in `arguments` (such as a cart `id` or `checkout.cart_id`) **MUST** match a
   resource the Platform already holds for that Business.
4. **Synchronize host state from `CallToolResult.structuredContent`.** When a
   view-initiated `tools/call` succeeds, inspect `structuredContent` before
   returning the result to the view: update the Platform's authoritative held
   Cart or Checkout state, render any new `messages` with
   `presentation: "disclosure"` in Platform-owned UI outside the iframe, and
   (when `create_checkout` succeeds) transition to the Platform's checkout
   experience.
5. **Apply UCP interaction categories:**

| Category | UCP Tools | Platform Host Behavior |
| :--- | :--- | :--- |
| Read-only | `search_catalog`, `lookup_catalog`, `get_product`, `get_cart`, `ask_business`, and Business helper tools with `visibility: ["app"]` | **MAY** forward on a Buyer gesture in the view. |
| Non-committing | `create_cart`, `create_checkout` | **MAY** forward on a Buyer gesture in the view. When `create_checkout` succeeds, the Platform updates its held Checkout state and transitions to its checkout experience. |
| Modifying | `update_cart` | **MAY** forward on a Buyer gesture when initiated from the active view for the Platform's current Cart state, or when merging a catalog `create_cart` into an existing held cart; after a merge, the Platform **MUST** show the resulting change (such as the added items and quantities) in Platform-owned UI and **SHOULD** let the Buyer undo it. **MUST** obtain Buyer confirmation in Platform-owned UI (showing the change against the Platform's most recent Cart response) when initiated from a superseded view, or when the update would drop line items added since the view was rendered. |
| Platform UI Only | `get_checkout`, `update_checkout`, `complete_checkout`, `cancel_checkout`, `cancel_cart`, Order tools such as `get_order`, and any other UCP operation not listed above | **MUST NOT** allow a view to call. Performed only from Platform-owned UI. |

When a catalog view calls `create_cart` and the Platform already holds an
active cart for that Business, the Platform **SHOULD** merge the requested
`line_items` into its held cart's `line_items` (retaining only request-eligible
line item fields, and coalescing an incoming line item with an existing line
item by summing `quantity` only when `item.id` and all other request-eligible
line item fields such as `parent_id` match) and call `update_cart` instead of
creating a second cart.

Because `update_cart` replaces the entire cart, the Platform **MUST** build
every view-initiated `update_cart` request (including one produced by the merge
above) from its held Cart state: it carries over each request-eligible
top-level field that the view's request omits (such as `buyer` and fields
defined by negotiated extensions) rather than forwarding a request that would
clear them.

### Capability-Aware Handoff

A view **SHOULD** inspect `hostContext["dev.ucp"].capabilities` (from
`ui/initialize`) before offering cross-capability actions. A view **MUST NOT**
conclude that a capability is not negotiated because it is missing from
`ucp.capabilities` in `structuredContent`: a response lists only the
capabilities relevant to its own operation (see [Response Capability
Selection](overview/index.md#response-capability-selection)).
When `hostContext["dev.ucp"]` is absent, the view cannot determine the
negotiated set and **SHOULD** use the `ui/open-link` fallbacks below.

* **Catalog to Cart or Checkout:** When `dev.ucp.shopping.cart` is negotiated,
  a catalog view calls `create_cart` (which the Platform merges into any held
  cart, as described above). When `dev.ucp.shopping.cart` is not negotiated
  but `dev.ucp.shopping.checkout` is, it calls `create_checkout` with
  `line_items`, handing off to the Platform's checkout experience. When
  neither is negotiated, it opens the product `url` (or
  [Permalink](permalink.md) URL) via `ui/open-link`.
* **Cart to Checkout:** When `dev.ucp.shopping.checkout` is negotiated, a cart
  view hands off by calling `create_checkout` with `checkout.cart_id` set to
  the Cart `id` and `checkout.line_items` set to `[]`, after which the Platform
  continues in its checkout experience. When `dev.ucp.shopping.checkout` is
  not negotiated, the cart view opens `continue_url` via `ui/open-link`.

<!-- ucp:example schema=shopping/checkout op=create direction=request extract=$.params.arguments.checkout -->
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "create_checkout",
    "arguments": {
      "checkout": {
        "cart_id": "cart_abc123",
        "line_items": []
      }
    }
  }
}
```

## Model Context Synchronization and External Links

* **Keeping the agent in sync (`ui/update-model-context`).** After a view
  updates state (for example, after `create_cart` or `update_cart` succeeds, or
  when the Buyer selects product options in the view), the view **SHOULD** call
  `ui/update-model-context` with a concise structured summary (such as the
  active `cart_id`, line item count, and total) so subsequent conversational
  turns have accurate context without re-fetching.
* **Untrusted Business content (`ui/update-model-context`, `ui/message`).**
  Content sent by a view via `ui/update-model-context` or `ui/message` is
  Business-authored data. The Platform **MUST** attribute such content to the
  Business and **MUST NOT** treat it as Buyer consent or as an instruction to
  perform a Platform-UI-only operation such as `complete_checkout`.
* **External links (`ui/open-link`).** When a view requests `ui/open-link`, the
  Platform **SHOULD** restrict the URL to `https` URLs that appear in the UCP
  response (`structuredContent`) or share the origin of the Business's
  discovery profile or service endpoint.

## Security Considerations

* **Sandboxed execution.** The Platform host **MUST** render `ui://` templates
  in a sandboxed iframe as required by MCP Apps (for web hosts, on an origin
  distinct from the Platform host), enforcing the resource's `_meta.ui.csp`
  policy and granting only approved `_meta.ui.permissions`.
* **Platform-owned disclosures and checkout confirmation.** The Platform
  **MUST** render UCP `messages` with `presentation: "disclosure"` in
  Platform-owned UI outside the iframe so a view cannot obscure or suppress
  required disclosures, and **MUST NOT** let a view replace the Platform's own
  checkout review and order-confirmation UI.
