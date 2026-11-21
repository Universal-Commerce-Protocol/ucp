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

# WebMCP Transport

!!! note "Draft - Work in Progress"
    This transport is in **draft status**. It tracks the
    [WebMCP](https://github.com/webmachinelearning/webmcp){ target="_blank" }
    API incubation and may change in breaking ways.

## Overview

WebMCP lets a web page register **tools** that an AI agent in the browser can
call. The page supplies each tool's name, description, and input schema, plus
an `execute` callback. The browser brokers the call between agent and page.

In the UCP WebMCP transport, a Business page registers UCP operations as tools,
and the Platform is the agent running in the Buyer's browser. The transport is
capability-agnostic: any UCP capability a page presents (a catalog, a cart, a
checkout, a lodging booking) can be offered over it, and a Business registers
on each page the tools for the capabilities that page presents. Each
capability's WebMCP binding lists its tools; this draft defines the
[Checkout binding](shopping/checkout/webmcp.md), with Cart and Catalog bindings
to follow the same rules.

The transport differs from [MCP](overview/index.md#model-context-protocol-mcp)
in the ways that shape every rule below:

| | MCP | WebMCP |
| :--- | :--- | :--- |
| **Endpoint** | A server URL | The page that registered the tools |
| **Envelope** | JSON-RPC `tools/call` | A direct call to the tool's `execute` callback |
| **Session** | Identified by `id` on every call | The one the page presents |
| **Caller** | Identified by `meta["ucp-agent"]` and request signatures | Runs inside the Buyer's own browsing session on the Business's origin |
| **Negotiation** | Platform profile intersected per request | Inherited from the Buyer-facing session the Business served |

The page is the Buyer's view of the negotiation. A Business keeps it coherent
with the resource after every tool call, so that the Buyer can observe the
current state at any moment and take over. Where the page is a multi-view
workflow that the Business will not advance unasked, it says so with an
outstanding Transition Action, which the Platform performs before the
negotiation continues (see [UI Actions](shopping/extensions/ui.md)).

## Discovery

The Platform discovers tools through the browser-provided API: the Business
registers its tools on the page's `ModelContext`, and the Platform introspects
the registered tools, their descriptions and schemas, and invokes them. The
Business's profile is optional for discovery: the contract in force was set
when the Business served the page (see [Requests](#requests)), and the `ucp`
object on each response is authoritative for the release, capabilities, and
extensions active for that session.

A Business **MAY** advertise the transport in its profile, so that Platforms
that fetch the profile learn that its pages offer tools. A WebMCP service entry
has a `schema` and no `endpoint`.

<!-- ucp:example schema=profile def=business_schema op=read direction=response -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": {
      "dev.ucp.shopping": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/webmcp",
          "transport": "webmcp",
          "schema": "https://ucp.dev/{{ ucp_version }}/services/shopping/webmcp.openrpc.json"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.shopping.checkout": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/checkout",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/checkout.json"
        }
      ]
    },
    "payment_handlers": {}
  }
}
```

## Tool Definitions

Each service publishes its WebMCP tools as an OpenRPC document (for shopping,
`services/shopping/webmcp.openrpc.json`). A Business **MUST** register each
tool as that document defines it:

| OpenRPC | WebMCP tool |
| :--- | :--- |
| `method` name | `name` |
| `params` | Properties of `inputSchema`, with `required` params listed in `inputSchema.required` |
| `result` | The value `execute` resolves to |
| `result` schema | `outputSchema` (**SHOULD**, see [Responses](#responses)) |

The `inputSchema` of a tool **MUST** be the param schemas resolved for the
operation's request direction and for the capabilities the page offers. The
Business **MAY** write its own tool `description`, and **SHOULD** keep it
consistent with the operation it maps to.

```javascript
await document.modelContext.registerTool({
  name: 'update_checkout',
  description: 'Updates the checkout on this page. ...',
  inputSchema: {
    type: 'object',
    required: ['checkout'],
    properties: {
      checkout: {/* checkout.json, resolved for the update request */},
    },
  },
  execute: (args) => updateCheckout(args),
});
```

## Requests

* **No `meta`:** WebMCP tool inputs have no `meta` parameter. The caller
    already acts inside the Buyer's browsing session on the Business's origin,
    so there is no Platform profile to advertise and no request to sign.
* **Negotiation is inherited:** Capability negotiation on this transport
    happened before the first tool call, between the Buyer's browser and the
    Business's server, when the Business served the page: the Business decided
    which capabilities and extensions to offer this Buyer, in this session, and
    rendered the Buyer-facing checkout accordingly. The tools the page registers
    are that contract made callable, and UCP inherits it. The Platform does not
    select capabilities; it discovers what the page offers from the `ucp`
    object every response carries (see
    [Business Requirements](overview/index.md#business-requirements)). A
    Platform that needs a contract the page does not offer uses a transport
    that carries a profile.
* **No resource identifiers:** A page presents one session of a capability
    and its tools act on that session, so tool inputs carry no `id`. Responses
    carry `id` as the capability's schema requires.
* **Idempotency:** There is no `idempotency-key`; the capability's lifecycle
    carries the guarantee. An operation that fails recoverably leaves the
    resource open to correction and retry, as on any transport: a
    `complete_checkout` that fails with a recoverable `payment_failed` message
    returns the Checkout to `incomplete`, and the Platform submits again with
    a corrected instrument. A resource in a terminal state (for a Checkout,
    `completed` or `canceled`) no longer changes: on a repeated
    `complete_checkout` for a completed Checkout the Business **MUST** return
    the current Checkout and **MUST NOT** place another order. A lost,
    aborted, or navigation-interrupted result is therefore not a receipt: the
    Platform **MUST** re-read with the capability's read tool (for example
    `get_checkout`) before reporting completion, and **MUST NOT** report a
    completion it did not observe.

## Tool resolution

A Business **MUST** resolve a tool only when the resource it returns is
authoritative and the page's view reflects it. If the Business cannot
reconcile the view synchronously, it **MUST** instead return `status:
incomplete` with a `recoverable` message identifying what is pending; the
Platform re-reads or re-updates as the message directs.

A resource's readiness (for a Checkout, `ready_for_complete`) is computed from
the resource. A Business **MUST NOT** condition it on the state of its page,
such as which view of a multi-view workflow the page is showing, except through
an outstanding Transition (see [UI Actions](shopping/extensions/ui.md)).

## Progressive schema and state

An operation's request schema can change during a session, for example when
the Business progressively loads additional inputs in response to a Buyer's
choice. WebMCP carries the change through registration. A tool's `inputSchema`
is the operation's resolved request schema, so when that schema changes the
Business unregisters the tool, by aborting the `signal` it registered with, and
registers it again under the same name with the new schema. Each change to the
registered tools fires `toolchange` on the page's `ModelContext`; on
`toolchange` the Platform **MUST** re-read the registered tools and use the
updated schema for subsequent calls. A call in flight across a re-registration
may be validated against either schema, so a Business **SHOULD** re-register
while no call is pending.

Values, constraints, and outstanding work do not change the schema and do not
re-register the tool. Each response carries the resource's full current state,
even while the resource itself is still `incomplete`: the values so far, the
constraints on them in `ucp.request_constraints`, and what remains in
`messages` and `actions`. New values and tightened constraints travel as
[Request Constraints](overview/index.md#request-constraints), never as schema
changes.

## Responses

A tool resolves to the UCP response object: the same object an MCP server
returns in `result.structuredContent`, without the JSON-RPC envelope. Its `ucp`
member carries the `version` and `capabilities` from which the Platform learns
the inherited contract (see [Requests](#requests)), and the
`request_constraints` by which the Business marks fields the Platform must echo
unchanged.

* Business outcomes are the capability's resource, with `messages`, as in
  [Error Handling](overview/index.md#error-handling).
* When no resource can be returned, the tool resolves to an
  [error response](site:schemas/common/types/error_response.json) with
  `ucp.status: "error"`.
* `continue_url` keeps its meaning from the capability: it gives the Platform
  a continuation for the Buyer when the Buyer cannot interact with the page the
  tools are registered in.

A fulfilled value is the UCP outcome. A *rejection* of the tool's promise is a
transport or browser failure and carries no UCP meaning: under current WebMCP
it reaches the caller as a bare `OperationError` with the reason discarded
(webmcp #282, #339). A Business **MUST NOT** signal a UCP outcome by
rejecting; a Platform treats a rejection as a lost result and re-reads
(see [Requests](#requests)).

A Business **SHOULD** register each tool's `outputSchema` as the OpenRPC
`result` schema, so the Platform can validate the Business's response. A
Platform **SHOULD** validate the fulfilled value against the UCP schemas it
expects and, when validation fails, surface the failure as an error rather than
treat the value as the resource's state.

<!-- ucp:example schema=common/types/error_response op=read direction=response -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "status": "error"
  },
  "messages": [
    {
      "type": "error",
      "code": "invalid_request",
      "content": "checkout.line_items: expected an array.",
      "severity": "recoverable"
    }
  ]
}
```

## Security Considerations

* **Same origin, same session:** Tools run in the page's JavaScript with the
    Buyer's cookies and session. A Business **MUST NOT** expose data through a
    tool that the page would not show the Buyer.
* **Credentials:** Payment credentials follow the selected payment handler's
    specification. A Platform **MUST NOT** pass raw payment credentials, such
    as a card number or security code, as tool arguments: arguments pass
    through the Platform's model context and the page's scripts. The Platform
    obtains a token for the credential from the selected payment handler,
    bound to the current Checkout (see
    [Tokenization](payment/tokenization.md#binding)), and submits the token.
    A Business **MUST NOT** return raw credentials in any response.

## Conformance

A Business that offers the WebMCP transport **MUST**:

1. Register the tools its capability bindings require, as the service's
    WebMCP OpenRPC document defines them.
2. Resolve only with authoritative, reconciled state (see
    [Tool resolution](#tool-resolution)).
3. Return UCP outcomes as fulfilled values, never by rejecting.
4. Treat an operation repeated on a resource in a terminal state as a read
    (see [Requests](#requests)).
5. Validate tool inputs against the resolved request schemas.

A Platform that uses the WebMCP transport **MUST**:

1. Re-read with the capability's read tool before reporting completion.
2. Honor escalation as the capability's binding defines (for shopping,
    [Escalation and Buyer authorization](shopping/checkout/webmcp.md#escalation-and-buyer-authorization)).
3. Operate the page's own controls only as the Business explicitly requests
    (see [UI Actions](shopping/extensions/ui.md)).

A Platform **SHOULD** validate fulfilled values against the UCP schemas it
expects (see [Responses](#responses)).
