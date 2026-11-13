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

# Checkout Capability - WebMCP Binding

!!! note "Draft - Work in Progress"
    This binding is in **draft status** and may change in breaking ways.

This document specifies the [WebMCP](../../webmcp.md) binding for the
[Checkout Capability](index.md): the tools a page that holds a checkout
registers. The transport's general rules (tool definitions, requests without
`meta` or `id`, idempotency, settlement, responses and errors) are in
[WebMCP Transport](../../webmcp.md).

## Tools

A checkout page is the Business's Buyer-facing interface to one Checkout: it
renders the Checkout, collects the Buyer's input, and lets the Buyer place the
order. By registering these tools, the page lets an agent in the Buyer's
browser assist with that same Checkout through the operations the
[Checkout Capability](index.md) defines, instead of by operating the page's
interface.

| Tool | Operation |
| :--- | :--- |
| `get_checkout` | [Get Checkout](index.md#get-checkout) |
| `update_checkout` | [Update Checkout](index.md#update-checkout) |
| `complete_checkout` | [Complete Checkout](index.md#complete-checkout) |
| `cancel_checkout` | [Cancel Checkout](index.md#cancel-checkout) |

A page registers the operations it offers the agent for the Checkout it
presents, and **MAY** omit any of them. A Business that wants the Buyer to
place the order through the page's own control omits `complete_checkout`.
`cancel_checkout` is usually unnecessary, because the Buyer ends the session
by leaving the page; a Business that holds something against the Checkout
(reserved inventory, a delivery slot, a quote) registers it so that the Buyer's
decision to abandon the Checkout, relayed by the agent, releases what is held.

`create_checkout` belongs to the page a Checkout is created from, a cart or a
product page, and so to the binding of the capability that page presents (see
[Cart](../cart/index.md)); this binding covers the Checkout page.

### Resource identifiers

The tools act on the Checkout the page presents and define no identifier
input: the page is the authority for which Checkout that is, and no other
Checkout can be requested or loaded through them. A Business **MUST** ignore
any `id` a Platform includes. Responses carry the required Checkout `id`.

Every tool resolves to a [Checkout](index.md#checkout) object or an error
response.

### `get_checkout`

Maps to [Get Checkout](index.md#get-checkout).

#### Input Schema

* None.

#### Output Schema

* [Checkout](index.md#get-checkout) object.

### `update_checkout`

Maps to [Update Checkout](index.md#update-checkout), including its
full-replacement semantics.

The Business applies what the session accepts and reports the rest through
`status`, `messages`, and `ucp.request_constraints`; the Platform re-reads or
re-updates (see [Progressive state](../../webmcp.md#progressive-state)).

#### Input Schema

* `checkout` ([Checkout](index.md#update-checkout)): **Required**.

#### Output Schema

* [Checkout](index.md#update-checkout) object.

#### Example

<!-- ucp:example schema=shopping/checkout op=update direction=request extract=$.checkout -->
```json
{
  "checkout": {
    "buyer": {
      "email": "buyer@example.com"
    },
    "line_items": [
      {
        "id": "li_1",
        "item": {
          "id": "item_123"
        },
        "quantity": 1
      }
    ]
  }
}
```

#### Read-only fields

Some fields are presented but can be set as read-only by the Business: the
email of a signed-in Buyer, for example, or pre-negotiated line items. The
tool's `inputSchema` is the full request schema, and the Business marks such
fields read-only with
[Request Constraints](../../overview/index.md#request-constraints) in its
responses, so the Platform knows to echo their current values in the
full replacement without modification. In the response below, the `ucp` object
carries its usual `version`, `capabilities`, and `payment_handlers`, and a
`request_constraints` entry that freezes `buyer.email` at the value shown for
the signed-in Buyer:

<!-- ucp:example schema=shopping/checkout op=update direction=response -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.checkout": [{ "version": "{{ ucp_version }}" }]
    },
    "payment_handlers": { ... },
    "request_constraints": {
      "properties": {
        "buyer": {
          "properties": {
            "email": { "const": "buyer@example.com" }
          }
        }
      }
    }
  },
  "id": "checkout_abc123",
  "status": "incomplete",
  "currency": "USD",
  "buyer": {
    "email": "buyer@example.com",
    "first_name": "Jane",
    "last_name": "Doe"
  },
  "line_items": [ ... ],
  "totals": [ ... ],
  "links": [ ... ]
}
```

### `complete_checkout`

Maps to [Complete Checkout](index.md#complete-checkout).

Placing an order accepts the Business's terms and policies, acknowledges its
warnings and disclosures, and finalizes the transaction. The
[Checkout Capability](index.md#complete-checkout) requires that Complete
Checkout be invoked only once the Buyer has committed to pay and place the
order. A Business **MUST** register `complete_checkout` with
`annotations: { consequentialHint: true }` (WebMCP §6.4.5), and a Platform
**MUST** obtain the appropriate consents prior to invoking it.

The Business sets and enforces the terms and requirements of the Checkout
lifecycle. When it requires the Buyer's input, or the Buyer's review and
authorization, it returns `status: requires_escalation` with a message whose
severity says which, as the [Checkout Capability](index.md#error-handling)
defines:

* **`requires_buyer_input`** — the Checkout is incomplete, and what is missing
  is something the Business collects only from the Buyer directly: a
  configuration its tools do not expose, a choice the Buyer must make on the
  page, a verification step.
* **`requires_buyer_review`** — the Checkout is complete, and the Business
  requires the Buyer's own authorization before it places the order: terms to
  accept, a disclosure to acknowledge, a high-value or first-purchase approval.

Complete Checkout is available only when the Business reports
`status: ready_for_complete`; a Checkout in `requires_escalation` cannot be
completed until the Buyer has acted. The Platform **MUST** hand off to the
Buyer. In a co-browsing context, where the Buyer can interact with the checkout
page directly, the Platform yields the page and asks the Buyer to finalize
there; otherwise it provides `continue_url` for the Buyer to open on another
surface. The Platform **SHOULD** resolve any `recoverable` messages through
`update_checkout` before handing off. The Buyer finalizes from there.

The Platform **MUST** use the provided tools to negotiate the Checkout
lifecycle and **MUST NOT** operate the page's own controls unless the Business
explicitly requests it (see [UI Actions](../../shopping/extensions/ui.md)):
a `requires_buyer_input` or `requires_buyer_review` message is the Business's
requirement that the Buyer act and finalize.

`completed` is a terminal state: on a repeated call for a completed Checkout
the Business **MUST NOT** place another order and **MUST** return the Checkout
unchanged (see [Requests](../../webmcp.md#requests)).

#### Input Schema

* `checkout` ([Checkout](index.md#complete-checkout)): **Required**. Payment
    and other finalization data, as in [Complete Checkout](index.md#complete-checkout).

#### Output Schema

* [Checkout](index.md#complete-checkout) object.

#### Example

A signed-in Buyer pays with an instrument saved with the Business. The
response listed it as a display-safe reference, an opaque `id` with `display`
fields and no credential (see [Payment](index.md#payment)); the Platform
selects it:

<!-- ucp:example schema=shopping/checkout op=complete direction=request extract=$.checkout -->
```json
{
  "checkout": {
    "payment": {
      "instruments": [
        {
          "id": "saved_card_1",
          "handler_id": "business_vault",
          "type": "card",
          "selected": true
        }
      ]
    }
  }
}
```

Otherwise the Platform submits a tokenized payment credential issued by one of
the Business's payment handlers, never card data:

<!-- ucp:example schema=shopping/checkout op=complete direction=request extract=$.checkout -->
```json
{
  "checkout": {
    "payment": {
      "instruments": [
        {
          "id": "instr_1",
          "handler_id": "processor_tokenizer",
          "type": "card",
          "selected": true,
          "credential": {
            "type": "token",
            "token": "tok_a1b2c3d4e5f6"
          }
        }
      ]
    }
  }
}
```

### `cancel_checkout`

Maps to [Cancel Checkout](index.md#cancel-checkout). A repeated call on a
canceled Checkout returns it unchanged.

Cancellation is a terminal transition the Buyer can see on the page. A Business
that registers `cancel_checkout` **MUST** register it with
`annotations: { consequentialHint: true }`, as for `complete_checkout`.

#### Input Schema

* None.

#### Output Schema

* [Checkout](index.md#cancel-checkout) object with `status: canceled`.

## Escalation and Buyer authorization

A Business **SHOULD** apply the requirements it expresses through the
Checkout lifecycle to the page's own interface as well: when a Checkout is in
`requires_escalation`, it inspects UI events on the page and ignores those an
agent originated, as reported by `SubmitEvent.agentInvoked` on form
submissions.
[webmachinelearning/webmcp#365](https://github.com/webmachinelearning/webmcp/issues/365)
proposes extending that attribution to every agent-originated event.

### Example

A `complete_checkout` result that requires the Buyer to finalize the checkout:

<!-- ucp:example schema=shopping/checkout op=complete direction=response -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "status": "success",
    "capabilities": {
      "dev.ucp.shopping.checkout": [{ "version": "{{ ucp_version }}" }]
    },
    "payment_handlers": {}
  },
  "id": "checkout_abc123",
  "status": "requires_escalation",
  "currency": "USD",
  "line_items": [ ... ],
  "totals": [ ... ],
  "links": [ ... ],
  "messages": [
    {
      "type": "error",
      "code": "high_value_order",
      "content": "Buyer must review and authorize this order",
      "severity": "requires_buyer_review"
    }
  ],
  "continue_url": "https://business.example.com/checkout-sessions/checkout_abc123"
}
```
