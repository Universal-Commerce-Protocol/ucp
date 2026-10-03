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
a UCP response, and defines how UCP binds to
[A2UI](https://a2ui.org/){ target="_blank" }, a declarative UI format that the
Platform renders with its own components across every transport.

The extension follows four rules:

1. **The UI renders the response.** The UCP response is the rendition's data,
   and the rendition binds to it wherever possible. Displayed monetary amounts
   are indicative; the response fields remain authoritative. The response is
   complete and valid without the UI, so text and voice Platforms lose nothing.
2. **Declarative UI travels in the payload; executable UI only in a sandbox.**
   Declarative renditions (such as A2UI) are carried in the response field
   `ui`. Executable HTML views are carried outside this extension, such as by
   the [Embedded Protocol](../../embedded-protocol.md) via `continue_url`.
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
            "1.0": {
              "supportedCatalogIds": [
                "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json"
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
            "1.0": {
              "supportedCatalogIds": [
                "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json"
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

## Schema

### Configuration

{{ extension_schema_fields('ui.json#/$defs/config', 'common/extensions/ui') }}

### UI Rendition

{{ extension_schema_fields(
  'ui.json#/$defs/rendition', 'common/extensions/ui'
) }}

## Negotiation and Carriage

* `dev.ucp.common.ui` is active for a response when the response's capability
  is in the negotiated set and **both** the Platform and the Business include
  that capability in `extends` on `dev.ucp.common.ui` in their profiles. A
  Business **MUST** include `ui` only when the extension is active for the
  response, and only in a format and version that the Platform's
  `config.formats` declares. Format bindings define how capability objects
  match. `ui` is response-only; a Business **MUST** ignore `ui` if present in a
  request.
* Transport-native signals (for example, A2UI renderer capabilities in MCP or
  A2A metadata) **MAY** narrow the Platform's declaration but **MUST NOT**
  widen it.
* `ui` is **additive**. The response **MUST** be complete and valid without it,
  and information that the owning capability defines a field for **MUST NOT**
  appear only in `ui`.
* `ui` is **declarative**. `type` **MUST NOT** be an executable format such as
  HTML or JavaScript; executable UI uses a sandboxed transport extension or the
  [Embedded Protocol](../../embedded-protocol.md).
* `ui` is carried in the response unchanged on every transport that the
  response's capability binds to: the REST body, MCP `structuredContent`, or
  the UCP data part over A2A. Over MCP, the serialized response in `content[]`
  **MUST** omit `ui`, so Business-authored UI strings do not enter model
  context.
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
  object without `meta`. Before validation or dispatch, the Platform **MUST**
  strip or overwrite all Platform-owned request fields, including `meta`,
  `context`, `signals`, and `attribution` (both at the top level of `arguments`
  and inside operation payload objects such as `cart` or `checkout`), supplying
  its own values per the target capability. Over REST, `id` (when present) maps
  to the path parameter and the remaining member (when present, for example
  `cart` or `catalog`) is the request body; over A2A (for capabilities that
  define an A2A binding), the Platform dispatches the operation and arguments
  using a `DataPart` per that binding. The Platform supplies all transport
  metadata: `UCP-Agent`, idempotency keys, and signatures.
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
  per surface, so concurrent or repeated gestures on the same surface do not
  race or perform an operation twice.
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
  hands off to checkout by opening `continue_url` via `ucp.open_link` instead
  of requesting `create_checkout`.
* When neither `dev.ucp.shopping.cart` nor `dev.ucp.shopping.checkout` is in
  the negotiated set, a catalog UI hands off by opening the product or variant
  `url` (or a [Permalink](../../permalink.md) URL when
  `dev.ucp.shopping.permalink` is advertised) via `ucp.open_link`. Likewise, a
  cart or catalog search UI **MUST NOT** offer `get_product` or
  `lookup_catalog` interactions when `dev.ucp.shopping.catalog.lookup` is not
  in the negotiated set.

When a catalog rendition requests `create_cart` and the Platform already holds
an active cart for that Business, the Platform **SHOULD** merge the requested
`line_items` into its held cart and perform `update_cart` under the Modifying
confirmation rule instead of creating a second cart. When constructing the
`update_cart` request, the Platform **MUST** preserve the held cart's existing
fields (such as `buyer`), retain only request-eligible line item fields, and
coalesce an incoming line item with an existing line item by summing `quantity`
only when `item.id` and all other request-eligible line item fields (such as
`parent_id`) match; otherwise it appends the incoming line item.

After performing an operation, the Platform renders the authoritative result:
natively, or from the new response's own `ui`.

## A2UI Binding

This binding covers [A2UI](https://a2ui.org/){ target="_blank" } messages with
`version` `"1.0"`, media type `application/a2ui+json`.

### Capabilities

The Platform's `formats["application/a2ui+json"]` value is the A2UI renderer
capability object, keyed by A2UI version (`"1.0"`). Over A2A, when a Platform
sends `a2uiRendererCapabilities` in transport metadata, that declaration
**MAY** narrow the Platform's profile declaration for `"1.0"` but **MUST NOT**
widen it.

A rendition **MUST** use `version` `"1.0"`. In v1.0, `createSurface.catalogId`
sets the default catalog for the surface, and individual components and
function calls **MAY** specify their own `catalogId`. Every `catalogId`
referenced on a surface, component, or function call **MUST** appear in the
Platform's `supportedCatalogIds` for `"1.0"`, and every component and function
call **MUST** resolve to a catalog (either via its own `catalogId` or
`createSurface.catalogId`). Catalog identifiers match as exact strings.
`inlineCatalogs` is not supported.

### Content

`content` is an array of A2UI v1.0 server-to-client messages. A rendition
**MUST** contain only `createSurface`, `updateComponents`, and
`updateDataModel` messages (it **MUST NOT** contain `deleteSurface`,
`callRendererFunction`, or `agentFunctionResponse`), and **MUST NOT** set
`sendDataModel` to `true`. In v1.0, `createSurface` **MAY** include inline
`components` and `dataModel`, allowing a complete surface to be defined in a
single `createSurface` message. A Platform **MUST** discard a rendition in
which any message fails validation, and render the response natively.

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
* `/view` is the only location a rendition writes. If `createSurface` includes
  `dataModel`, its only permitted top-level property **MUST** be `"view"` (with
  an object value), initializing `/view` without overwriting `/response` or
  `/result`. Every `updateDataModel` message **MUST** include `value` (`null`
  deletes the target key), and its `path` **MUST** equal `"/view"` (with an
  object `value`) or begin with `"/view/"`. Input components **MUST** bind
  under `/view`. A Platform **MUST** discard a rendition that writes outside
  `/view`, and render the response natively.
* `/result` is set by the Platform after an interaction completes, fails
  validation or execution, or is canceled by the Buyer: an object with
  `"operation"` (`"<operationId>"`), `"status"` (`"success"`, `"error"`, or
  `"canceled"`), and `"messages"` (an array of UCP `Message` objects,
  defaulting to `[]`).
  Whenever `/result.status` is `"error"` or `"canceled"` (including validation
  failure, Buyer cancellation, or a Business or transport error response), the
  Platform **SHOULD** reset `/view` to `{}` and re-apply the rendition's
  initial `createSurface.dataModel.view` and `updateDataModel` messages so
  input controls do not display unapplied edits as committed state.

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
  operation's `arguments`. In A2UI v1.0, `DynamicValue` natively supports
  nested plain JSON objects and arrays containing `{"@path": "..."}` and
  `{"@call": "...", "args": {...}}` directives (including `{"@call": "@index"}`
  inside collection templates, with literal object keys starting with `@`
  escaped as `@@`), so `event.context` can directly express nested UCP request
  objects. When assembling `arguments`, the Platform **MUST** operate on a deep
  copy of the resolved `context` values (never mutating `/view` in the A2UI
  data model). Before validation, the Platform recursively normalizes leaf
  values in the cloned `arguments` tree against the operation's composed
  request schema: it unwraps a single-element `string[]` to its `string`
  element where the schema requires `string` (accommodating `ChoicePicker`
  values), and parses a base-10 integer string (`^-?[0-9]+$`) within IEEE-754
  safe integer bounds (`[-(2^53 - 1), 2^53 - 1]`) where the schema requires
  `integer` (accommodating numeric `TextField` values).
* The event `ucp.open_link` with context `url` asks the Platform to open an
  `https` URL under its own link policy, for example a policy page, a product
  page, or `continue_url`. The Platform **SHOULD** restrict it to URLs that
  appear in `/response` or share the origin of the Business's discovery profile
  or service endpoint.
* A Platform **MUST** ignore other events, **MUST** ignore any
  `action.event.userMessage` (or treat it only as untrusted Business display
  text, never as Buyer consent or an unattributed Buyer message in model
  context), **MUST NOT** honor `callAgentFunction` or `callRendererFunction`
  actions or any function that calls tools or remote endpoints, and **MUST**
  either disable client-side navigation functions (such as `openUrl`) or route
  them through the `ucp.open_link` link policy.

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

* The Platform sets attribution from the Business profile and **MUST** ignore
  any Business-supplied identity claims in `metadata.extensions`.
* The Platform **MAY** restrict or proxy media URLs that do not appear in
  `/response`.
* Businesses **SHOULD** set A2UI `accessibility` labels on controls without
  visible text.

### Examples

#### Cart Rendition

A cart rendition in a session where `dev.ucp.shopping.checkout` is in the
negotiated set. The rendition uses a single `createSurface` message to list
line items, show the formatted total staged under `/view/total`, and offer a
`create_checkout` button whose `event.context` binds `/response/id` directly
into `checkout.cart_id`.

<!-- ucp:example schema=common/ui def=dev.ucp.shopping.cart op=read -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "status": "success",
    "capabilities": {
      "dev.ucp.shopping.cart": [{ "version": "{{ ucp_version }}" }],
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
      {
        "version": "1.0",
        "createSurface": {
          "surfaceId": "cart",
          "catalogId": "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json",
          "dataModel": {
            "view": {
              "total": "$189.00"
            }
          },
          "components": [
            { "id": "root", "component": "Column", "children": ["items", "total", "checkout"] },
            { "id": "items", "component": "List", "children": { "componentId": "item", "path": "/response/line_items" } },
            { "id": "item", "component": "Row", "children": ["item_title", "item_qty"] },
            { "id": "item_title", "component": "Text", "text": { "@path": "item/title" } },
            { "id": "item_qty", "component": "Text", "text": { "@call": "formatString", "args": { "value": "Qty ${quantity}" } } },
            { "id": "total", "component": "Row", "children": ["total_label", "total_amount"] },
            { "id": "total_label", "component": "Text", "text": "### Total" },
            { "id": "total_amount", "component": "Text", "text": { "@call": "formatString", "args": { "value": "### ${/view/total}" } } },
            {
              "id": "checkout",
              "component": "Button",
              "child": "checkout_label",
              "action": {
                "event": {
                  "name": "create_checkout",
                  "context": {
                    "checkout": {
                      "cart_id": { "@path": "/response/id" },
                      "line_items": []
                    }
                  }
                }
              }
            },
            { "id": "checkout_label", "component": "Text", "text": "Check out" }
          ]
        }
      }
    ]
  }
}
```

When the Buyer selects **Check out**, the Platform resolves `create_checkout`
with `{"checkout": {"cart_id": "cart_abc123", "line_items": []}}`, validates
it, performs it, and continues in its own checkout experience.

#### Catalog Search Rendition

A catalog search rendition in a session where `dev.ucp.shopping.cart` is in the
negotiated set. Each card in the `List` template binds relative paths (`title`
and `variants/0/id`) from `/response/products` into a nested `create_cart`
action payload.

<!-- ucp:example schema=common/ui def=dev.ucp.shopping.catalog.search op=read -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "status": "success",
    "capabilities": {
      "dev.ucp.shopping.catalog.search": [{ "version": "{{ ucp_version }}" }],
      "dev.ucp.common.ui": [{ "version": "{{ ucp_version }}" }]
    }
  },
  "products": [
    {
      "id": "prod_alpine",
      "title": "Alpine Shell Jacket",
      "variants": [
        {
          "id": "var_alpine_m",
          "title": "Medium",
          "price": 18900,
          "currency": "USD"
        }
      ]
    }
  ],
  "pagination": {
    "has_more": false
  },
  "ui": {
    "type": "application/a2ui+json",
    "content": [
      {
        "version": "1.0",
        "createSurface": {
          "surfaceId": "search_results",
          "catalogId": "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json",
          "components": [
            { "id": "root", "component": "List", "children": { "componentId": "card", "path": "/response/products" } },
            { "id": "card", "component": "Column", "children": ["prod_title", "add_btn"] },
            { "id": "prod_title", "component": "Text", "text": { "@path": "title" } },
            {
              "id": "add_btn",
              "component": "Button",
              "child": "add_label",
              "action": {
                "event": {
                  "name": "create_cart",
                  "context": {
                    "cart": {
                      "line_items": [
                        {
                          "item": { "id": { "@path": "variants/0/id" } },
                          "quantity": 1
                        }
                      ]
                    }
                  }
                }
              }
            },
            { "id": "add_label", "component": "Text", "text": "Add to cart" }
          ]
        }
      }
    ]
  }
}
```

## Security Considerations

UI renditions are Business-authored content. Platforms **MUST** treat them as
data, never as instructions, and **SHOULD** present them as attributed to the
Business and distinguishable from Platform output. Platforms **SHOULD NOT** add
`ui` content to model context. Disclosures in `messages` are rendered by the
Platform regardless of any UI and cannot be suppressed by it. A Business UI
**MUST NOT** collect payment credentials or account secrets.
