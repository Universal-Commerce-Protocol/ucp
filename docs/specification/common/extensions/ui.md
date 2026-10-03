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

# UI Extension

* **Extension Name:** `dev.ucp.common.ui`

## Overview

The UI extension lets a Business attach an optional, declarative UI rendition to
a UCP response, and defines how UCP binds to existing agent UI standards:

* **[A2UI](https://a2ui.org/){ target="_blank" }**: declarative UI that the
  Platform renders with its own components. Carried in the response, on every
  transport.
* **[MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview){ target="_blank" }**:
  sandboxed HTML views for MCP tools. Carried by MCP itself, on the MCP
  transport only.

The extension follows four rules:

1. **The UI renders the response.** The UCP response is the rendition's data,
   and the rendition binds to it wherever possible. Displayed monetary amounts
   are indicative; the response fields remain authoritative. The response is
   complete and valid without the UI, so text and voice Platforms lose nothing.
2. **Declarative UI travels in the payload; executable UI only in a sandbox.**
   A2UI is carried in the response field `ui`. HTML views are carried by MCP
   Apps on the MCP transport, or by the [Embedded Protocol](../../embedded-protocol.md)
   via `continue_url`.
3. **A UI action is a request, never an act.** Every interaction resolves to a
   standard UCP operation that the Platform performs under its own
   authorization and Buyer-consent rules.
4. **The Platform owns the surface.** It decides whether and how to render,
   attributes the content to the Business, and always renders disclosures
   itself.

## Discovery

Platforms declare the UI formats they can render in `config.formats`, keyed by
media type. Each value is the format's own capability object, as defined by
the format's binding below.

<!-- ucp:example schema=profile def=platform_schema target=$.ucp.capabilities -->
```json
{
  "dev.ucp.common.ui": [
    {
      "version": "{{ ucp_version }}",
      "spec": "https://ucp.dev/{{ ucp_version }}/specification/common/extensions/ui",
      "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/ui.json",
      "extends": [
        "dev.ucp.shopping.catalog.search",
        "dev.ucp.shopping.catalog.lookup",
        "dev.ucp.shopping.cart"
      ],
      "config": {
        "formats": {
          "application/a2ui+json": {
            "v0.9": {
              "supportedCatalogIds": [
                "https://a2ui.org/specification/v0_9/catalogs/basic/catalog.json"
              ]
            }
          }
        }
      }
    }
  ]
}
```

Platforms and Businesses **MAY** extend any subset of
`dev.ucp.shopping.catalog.search`, `dev.ucp.shopping.catalog.lookup`, and
`dev.ucp.shopping.cart`. Businesses advertise the extension for the
capabilities they render, and **MAY** declare the formats they emit in
`config.formats`. The Business format declaration is informational.

<!-- ucp:example schema=profile def=business_schema target=$.ucp.capabilities -->
```json
{
  "dev.ucp.common.ui": [
    {
      "version": "{{ ucp_version }}",
      "spec": "https://ucp.dev/{{ ucp_version }}/specification/common/extensions/ui",
      "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/ui.json",
      "extends": [
        "dev.ucp.shopping.catalog.search",
        "dev.ucp.shopping.catalog.lookup",
        "dev.ucp.shopping.cart"
      ],
      "config": {
        "formats": {
          "application/a2ui+json": {
            "v0.9": {
              "supportedCatalogIds": [
                "https://a2ui.org/specification/v0_9/catalogs/basic/catalog.json"
              ]
            }
          }
        }
      }
    }
  ]
}
```

**Dependencies:**

* Catalog Search Capability, Catalog Lookup Capability, or Cart Capability

MCP Apps is negotiated by MCP, not by this extension; see
[MCP Apps Binding](#mcp-apps-binding).

## Schema

### UI Rendition

{{ extension_schema_fields('ui.json#/$defs/rendition', 'common/extensions/ui') }}

## Negotiation and Carriage

* `dev.ucp.common.ui` is active for a response when the response's capability
  is in the negotiated set and **both** the Platform and the Business include
  that capability in `extends` on `dev.ucp.common.ui`. A Business **MUST**
  include `ui` only when the extension is active for the response, and only in
  a format and version that the Platform's `config.formats` declares. Format
  bindings define how capability objects match.
* Transport-native signals (for example, A2UI capabilities in MCP or A2A
  metadata) **MAY** narrow the Platform's declaration but **MUST NOT** widen
  it.
* `ui` is **additive**. The response **MUST** be complete and valid without it,
  and information that the owning capability defines a field for **MUST NOT**
  appear only in `ui`.
* `ui` is **declarative**. `type` **MUST NOT** be an executable format such as
  HTML or JavaScript; executable UI uses the [MCP Apps Binding](#mcp-apps-binding)
  or the Embedded Protocol.
* `ui` is carried in the response unchanged on every transport: the REST body,
  MCP `structuredContent`, or the UCP data part over A2A. Over MCP, the
  serialized response in `content[]` **MUST** omit `ui`, so Business-authored
  UI strings do not enter model context.
* A Platform **MAY** ignore `ui` for any reason, including size, and render the
  response natively. A Platform **SHOULD** render `ui` only from the most recent
  response it holds for a resource; an idempotent replay never restores a
  superseded rendition.

## Interactions

Every interaction a UI offers is a request for the Platform to perform one UCP
operation. The Platform decides whether to perform it.

* **Operation identifier.** An operation is identified by its REST
  `operationId`, which is also its MCP tool name (for example, `create_cart`,
  `get_product`). The Platform resolves it within the service that returned
  the response.
* **Arguments.** Arguments take the shape of the operation's MCP `arguments`
  object without `meta`. Over REST, `id` (when present) maps to the path
  parameter and the remaining member (when present, for example `cart` or
  `catalog`) is the request body; over A2A, the Platform dispatches the
  operation and arguments using a `DataPart` per the capability's A2A binding.
  The Platform supplies all transport metadata: `UCP-Agent`, idempotency keys,
  and signatures.
* **Validation.** A Business **MUST** offer only interactions whose target
  capability is active in the negotiated set. The Platform **MUST** validate
  arguments against the composed request schema, **MUST** target only the
  Business that issued the UI, and **MUST** target only capabilities active in
  the negotiated set. Any stateful resource identifier in the arguments (such as
  a top-level cart or checkout `id`, or `checkout.cart_id`) **MUST** identify a
  resource the Platform already holds for that Business. Except for input
  normalizations defined by a format binding, the Platform **MUST NOT** coerce
  argument types; when validation fails, it sends no request and reports the
  failure in the interaction result.
* **Duplicates.** The Platform **SHOULD** allow at most one in-flight request
  per UI control, so a repeated gesture does not perform an operation twice.
* **Consent.** The Platform **MUST** derive any confirmation it shows from the
  resolved operation and arguments, never from labels in the UI.

| Category | Operations | Platform behavior |
| :--- | :--- | :--- |
| Read-only | `search_catalog`, `lookup_catalog`, `get_product`, `get_cart`, and other operations the Platform knows do not change resource state | **MAY** perform on a Buyer gesture. |
| Non-committing | `create_cart`, `create_checkout` | **MAY** perform on a Buyer gesture. |
| Modifying | `update_cart`, `update_checkout` | **MUST** obtain Buyer confirmation in Platform-owned UI, showing the change against the Platform's most recent response. `update_cart` replaces the cart, so a stale argument can drop line items. |
| Platform UI only | `complete_checkout`, `cancel_checkout`, `cancel_cart`, and any other operation | **MUST NOT** perform from a Business UI interaction. |

Operations in the Platform UI only category remain available: the Platform
performs them only from its own UI, such as its checkout review and
place-order step, never from a Business UI interaction. A Business UI hands
off to that UI instead, adapting to the capabilities active in the negotiated
set:

* When `dev.ucp.shopping.checkout` is in the negotiated set, a cart or catalog
  UI hands off with `create_checkout` (passing `cart_id` from a cart when
  `dev.ucp.shopping.cart` is negotiated, or `line_items` directly when
  `dev.ucp.shopping.cart` is not in the negotiated set), after which the
  Platform continues in its own checkout experience.
* When `dev.ucp.shopping.checkout` is not in the negotiated set, a cart UI
  hands off to checkout by opening `continue_url` via `ucp.open_link` (or
  `ui/open-link` in MCP Apps) instead of requesting `create_checkout`.
* When neither `dev.ucp.shopping.cart` nor `dev.ucp.shopping.checkout` is in
  the negotiated set, a catalog UI hands off by opening the product or variant
  `url` (or a [Permalink](../../permalink.md) URL when
  `dev.ucp.shopping.permalink` is advertised) via `ucp.open_link` or
  `ui/open-link`. Likewise, a cart or catalog search UI **MUST NOT** offer
  `get_product` or `lookup_catalog` interactions when
  `dev.ucp.shopping.catalog.lookup` is not in the negotiated set.

When a catalog rendition requests `create_cart` and the Platform already holds
an active cart for that Business, the Platform **SHOULD** merge the requested
`line_items` into its held cart (retaining only request-eligible line item
fields) and perform `update_cart` under the Modifying confirmation rule instead
of creating a second cart.

After performing an operation, the Platform renders the authoritative result:
natively, or from the new response's own `ui`.

## A2UI Binding

This binding covers [A2UI](https://a2ui.org/){ target="_blank" } messages with
`version` `"v0.9"` or `"v0.9.1"`, media type `application/a2ui+json`.

### Capabilities

The Platform's `formats["application/a2ui+json"]` value is the A2UI renderer
capability object, keyed by A2UI version. The `"v0.9"` key covers `v0.9` and
`v0.9.1` messages. A rendition **MUST** use one A2UI `version` and only a
`catalogId` the Platform lists. Catalog identifiers match as exact strings.
`inlineCatalogs` is not supported.

### Content

`content` is an array of A2UI messages. A rendition **MUST** contain only
`createSurface`, `updateComponents`, and `updateDataModel` messages, and
**MUST NOT** set `sendDataModel` to `true`. A Platform **MUST** discard a
rendition in which any message fails validation, and render the response
natively.

### Data Model

For each surface a rendition creates, the Platform initializes the A2UI data
model as:

<!-- ucp:example skip reason="A2UI data model layout, not a UCP payload" -->
```json
{
  "response": { "...": "the UCP response, without ui" },
  "view": {},
  "result": {}
}
```

* `/response` is read-only and set by the Platform.
* `/view` is the only location a rendition writes. Every `updateDataModel`
  `path` **MUST** begin with `/view/`, and input components **MUST** bind
  under `/view`. A Platform **MAY** discard a rendition that writes elsewhere,
  and render the response natively.
* `/result` is set by the Platform after an interaction completes, fails
  validation, or is canceled by the Buyer:
  `{ "operation": "<operationId>", "status": "success" | "error" | "canceled", "messages": [...] }`,
  where `messages` is an array of UCP `Message` objects (defaulting to `[]`).
  When an interaction fails validation or is canceled by the Buyer, the
  Platform **SHOULD** restore `/view` to the response's initial state by
  re-applying the rendition's `updateDataModel` messages.

### Surfaces

A surface lives for one response. A rendition **MUST** create every surface it
uses and **MUST NOT** reference surfaces from other responses. The Platform
rewrites surface identifiers so they are unique per Business and response, and
owns surface teardown. When a newer response for the same resource arrives
(matched by `id` for stateful resources, `product.id` for `get_product`, or a
response to a `search_catalog` or `lookup_catalog` interaction initiated from
that surface), the Platform **MUST** disable interactions on older surfaces for
that resource.

### Actions

* A server `event` whose `name` is an operation identifier is an
  [interaction](#interactions); its resolved `context` is assembled into the
  operation's `arguments`. Object-valued arguments **MAY** be staged under
  `/view` and bound by path, or constructed using `/`-delimited JSON Pointer
  keys in `event.context` (for example, `"catalog/id": { "path": "id" }` or
  `"cart/line_items/0/item/id": { "path": "variants/0/id" }`). When assembling
  `arguments`, the Platform **MUST** operate on a deep copy of the resolved
  `context` values (never mutating `/view` in the A2UI data model), apply
  entries in ascending path-depth order so deeper pointers override fields in
  base objects, and construct JSON arrays (`[...]`) when creating missing
  intermediate containers for non-negative integer segments (or where the
  operation's request schema specifies `type: "array"`). Before validation, the
  Platform recursively normalizes leaf values in the cloned `arguments` tree
  against the operation's composed request schema: it unwraps a single-element
  `string[]` to its `string` element where the schema requires `string`, and
  parses a base-10 integer string (`^-?[0-9]+$`) within IEEE-754 safe integer
  bounds (`[-(2^53 - 1), 2^53 - 1]`) where the schema requires `integer`.
* The event `ucp.open_link` with context `url` asks the Platform to open an
  `https` URL under its own link policy, for example a policy page, a product
  page, or `continue_url`. The Platform **MAY** restrict it to URLs that appear
  in `/response` or belong to the Business's domain.
* A Platform **MUST** ignore other events, **MUST NOT** honor functions that
  call tools or remote endpoints, and **MUST** either disable client-side
  navigation functions (such as `openUrl`) or route them through the
  `ucp.open_link` link policy.

> **Note (A2UI v0.9 limitations):** The `/`-delimited `event.context` keys,
> `/view` staging, and schema-directed leaf normalizations above work around
> specific constraints in A2UI v0.9 and its Basic Catalog:
>
> * `DynamicValue` in v0.9 rejects plain JSON objects (`"type": "object"`), so a
>   rendition cannot nest `{ "path": "..." }` bindings inside an inline object
>   literal in `event.context` (for example, inside a `List` item template).
> * In the v0.9 Basic Catalog, `ChoicePicker.value` always writes `string[]`
>   (even for `variant: "mutuallyExclusive"`), `TextField.value` always writes
>   `string` (even for `variant: "number"`), and `Button` cannot mutate `/view`
>   before dispatching an `event`.
> * Surface initialization in v0.9 requires separate `createSurface`,
>   `updateDataModel`, and `updateComponents` messages, and `action.event` is a
>   one-way dispatch without a correlation ID (addressed here via `/result`).
>
> A future A2UI v1.0 binding under `config.formats["application/a2ui+json"]`
> can relax the `event.context` staging and multi-message surface rules where
> v1.0 supports native nested objects in `DynamicValue` (via `@path` and
> `@call`) and inline `components` and `dataModel` on `createSurface`.

### Monetary Amounts

UCP amounts are integers in the currency's minor unit, which A2UI formatting
functions do not convert. A rendition that displays a monetary amount **MUST**
derive the displayed text from the corresponding amount and currency in the
response, converted to the currency's major unit using its ISO 4217 exponent,
and **SHOULD** format it for the Buyer's `language` from the request
`context`. A rendition **SHOULD** stage formatted amounts under `/view`.

Displayed amounts are indicative: the response fields are authoritative, and
the Platform's checkout review is the authoritative presentation before
purchase. A Platform **MAY** decline to render a rendition whose displayed
amounts do not match the response.

### Presentation

* The Platform sets attribution from the Business profile and overrides any
  A2UI identity fields (such as `theme.agentDisplayName` and `theme.iconUrl`).
* The Platform **MAY** restrict or proxy media URLs that do not appear in
  `/response`.
* Businesses **SHOULD** set A2UI `accessibility` labels on controls without
  visible text.

### Example

A cart rendition that lists line items, shows the total, and offers checkout.
Item titles and quantities are bound from the response; the formatted total is
staged under `/view`.

<!-- ucp:example schema=common/ui def=dev.ucp.shopping.cart op=read -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "status": "success",
    "capabilities": {
      "dev.ucp.shopping.cart": [{ "version": "{{ ucp_version }}" }],
      "dev.ucp.shopping.checkout": [{ "version": "{{ ucp_version }}" }],
      "dev.ucp.common.ui": [{ "version": "{{ ucp_version }}" }]
    }
  },
  "id": "cart_abc123",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": { "id": "var_alpine_m", "title": "Alpine Shell Jacket (M)", "price": 18900 },
      "quantity": 1,
      "totals": [
        { "type": "subtotal", "amount": 18900 },
        { "type": "total", "amount": 18900 }
      ]
    }
  ],
  "totals": [
    { "type": "subtotal", "amount": 18900 },
    { "type": "total", "amount": 18900 }
  ],
  "ui": {
    "type": "application/a2ui+json",
    "content": [
      { "version": "v0.9.1", "createSurface": { "surfaceId": "cart", "catalogId": "https://a2ui.org/specification/v0_9/catalogs/basic/catalog.json" } },
      { "version": "v0.9.1", "updateDataModel": { "surfaceId": "cart", "path": "/view/total", "value": "$189.00" } },
      { "version": "v0.9.1", "updateDataModel": { "surfaceId": "cart", "path": "/view/checkout", "value": { "cart_id": "cart_abc123", "line_items": [] } } },
      { "version": "v0.9.1", "updateComponents": { "surfaceId": "cart", "components": [
        { "id": "root", "component": "Column", "children": ["items", "total", "checkout"] },
        { "id": "items", "component": "List", "children": { "componentId": "item", "path": "/response/line_items" } },
        { "id": "item", "component": "Row", "children": ["item_title", "item_qty"] },
        { "id": "item_title", "component": "Text", "text": { "path": "item/title" } },
        { "id": "item_qty", "component": "Text", "text": { "call": "formatString", "args": { "value": "Qty ${quantity}" }, "returnType": "string" } },
        { "id": "total", "component": "Row", "children": ["total_label", "total_amount"] },
        { "id": "total_label", "component": "Text", "variant": "h3", "text": "Total" },
        { "id": "total_amount", "component": "Text", "variant": "h3", "text": { "path": "/view/total" } },
        { "id": "checkout", "component": "Button", "child": "checkout_label", "action": { "event": { "name": "create_checkout", "context": { "checkout": { "path": "/view/checkout" } } } } },
        { "id": "checkout_label", "component": "Text", "text": "Check out" }
      ] } }
    ]
  }
}
```

When the Buyer selects **Check out**, the Platform resolves
`create_checkout` with `{"checkout": {"cart_id": "cart_abc123", "line_items": []}}`, validates
it, performs it, and continues in its own checkout experience.

## MCP Apps Binding

This binding covers [MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview){ target="_blank" }
(`io.modelcontextprotocol/ui`, specification version 2026-01-26). It applies to
any UCP MCP server whose tools declare MCP Apps views, whether or not
`dev.ucp.common.ui` is negotiated, because MCP Apps is negotiated by MCP during
`initialize`.

### Business Requirements

* A Business **MAY** declare an MCP Apps view on any UCP tool with
  `_meta.ui.resourceUri`. It **MUST NOT** change the tool's name, input schema,
  or output schema to do so.
* The view's data is the tool result's `structuredContent`, which is the UCP
  response. The `ui://` resource itself **MUST** be a static, data-agnostic
  template so that Platforms can prefetch, cache, or pre-register and vet it
  ahead of time. A decorated tool **MUST** also return the serialized UCP
  response (without `ui`) in `content[]`.
* The tool `visibility` of `complete_checkout`, `cancel_checkout`, and
  `cancel_cart` **MUST NOT** include `"app"`. Tools visible only to the app
  **MUST NOT** change the state of UCP resources.
* A view **MUST** change UCP resources only by calling UCP tools through the
  host, and **SHOULD** inspect `ucp.capabilities` in `structuredContent` before
  offering or calling cross-capability tools (such as `create_checkout`,
  `create_cart`, or `get_product`), falling back to `ui/open-link` when the
  target capability is not active. A Business **MUST NOT** list an endpoint
  that changes UCP resource state in the view's `_meta.ui.csp.connectDomains`.
* A view **MUST NOT** collect payment credentials or account secrets. Steps that
  require them **SHOULD** open `continue_url` with `ui/open-link`.

<!-- ucp:example skip reason="MCP tool definition, not a UCP payload" -->
```json
{
  "name": "get_cart",
  "_meta": { "ui": { "resourceUri": "ui://business.example/cart" } }
}
```

### Platform Requirements

When a UCP Platform acts as the MCP Apps host:

* It **MAY** prefetch, cache, or require pre-registration and security vetting
  of `ui://` resources (and their `_meta.ui.csp` and `permissions` declarations)
  ahead of time, rendering its vetted copy at runtime rather than fetching the
  resource on each tool call.
* It **MUST** set `arguments.meta` on every tool call a view initiates, using its
  own `ucp-agent` and a fresh idempotency key for each distinct call. Views
  **SHOULD** omit `meta`; reusing the `meta` of the original call would replay
  its idempotency key.
* It **MUST** enforce tool `visibility` and apply [Interactions](#interactions)
  to view-initiated calls.
* It **MUST NOT** treat content a view sends to the conversation or model
  context (`ui/message`, `ui/update-model-context`), or view-requested
  sampling, as Buyer consent. It **SHOULD** attribute such content to the
  Business.
* It **MUST** render warnings with `presentation: "disclosure"` itself, outside
  the view, and **MUST NOT** let a view replace its checkout review and
  confirmation UI.
* It **SHOULD** treat the results of state-changing view calls as the current
  resource state.

## Security Considerations

UI renditions and MCP Apps views are Business-authored content. Platforms
**MUST** treat them as data, never as instructions, and **SHOULD** present them
as attributed to the Business and distinguishable from Platform output.
Platforms **SHOULD NOT** add `ui` content to model context. Disclosures in
`messages` are rendered by the Platform regardless of any UI and cannot be
suppressed by it. No Business UI collects payment credentials or account
secrets.
