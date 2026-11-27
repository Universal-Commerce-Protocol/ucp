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

# UI Actions Extension

## Overview

A Business's page may present a Cart or Checkout session as a sequence of
views, on a single page or across several, that require an explicit UI action
to advance. The negotiation then spans view boundaries that the tools alone
cannot cross: when a Platform negotiates with such a page through its tools
(see the [WebMCP Transport](../../webmcp.md)), the Business cannot continue
until its page has advanced, and only a UI action advances it.

The UI Actions extension gives the Business a way to say so. It declares the
`dev.ucp.shopping.ui.transition` Action type, through which the Business names
the control that performs the transition it is waiting at. The Platform
performs the UI action, waits for the page to settle, and reads the resource
again. The page stays coherent with the resource at every step, so the Buyer
can observe the current state at any moment and take over.

**Key features:**

- One Action type, `dev.ucp.shopping.ui.transition`, surfaced as outstanding
  work in the response-only `actions` map
- The control identified two ways: by accessible name, for Platforms operating
  the accessibility tree, and by DOM `id`, for Platforms operating the DOM
- Processing defined in web platform terms: activate the control, wait for the
  resulting navigation, read again

**Dependencies:**

- Cart Capability or Checkout Capability
- A Buyer-facing page the Platform can operate, such as the
  [WebMCP Transport](../../webmcp.md) provides

## Discovery

Businesses advertise the extension in their profile. It can extend cart,
checkout, or both:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.ui": [
        {
          "version": "{{ ucp_version }}",
          "extends": ["dev.ucp.shopping.cart", "dev.ucp.shopping.checkout"],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/extensions/ui",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/ui.json"
        }
      ]
    }
  }
}
```

On the WebMCP transport the contract is inherited from the page the Business
served, and the Platform learns that the extension is active from the `ucp`
object on each response (see
[WebMCP Transport — Requests](../../webmcp.md#requests)).

## Schema

When this extension is active, the `actions` map of a cart or checkout may
carry the `dev.ucp.shopping.ui.transition` key, following the common rules in
[Overview — Actions](../../overview/index.md#actions). Each instance has the
common `id` and a required `config`:

### Transition Config

{{ extension_schema_fields('ui.json#/$defs/transition_config', 'shopping/extensions/ui') }}

Both handles identify the same control on the current view. `label` is the
control's accessible name as the accessibility tree exposes it, which is how
agents operating that tree locate controls and how the Buyer recognizes it;
the Platform also presents it as the description of the transition. `element`
is the control's DOM `id`, resolvable with a single `getElementById`.

```html
<button type="submit" id="continue-shipping">Continue to shipping</button>
```

<!-- ucp:example schema=shopping/ui def=transition op=read -->
```json
{
  "id": "t_shipping",
  "config": { "label": "Continue to shipping", "element": "continue-shipping" }
}
```

## Transition Action

A transition moves the Business's page from one view to the next. It may be a
soft navigation, which changes the browser's history without unloading the
page, or a hard navigation, which performs a full page load; the extension
treats both alike, and [Processing](#processing) describes how the Platform
waits for each. The Business surfaces a transition when, and only when, the
current view's requirements are met and the page must move to the next view
before the negotiation can continue. Missing or invalid inputs are reported
first, as `recoverable` messages on the fields concerned; a transition is
therefore always the only remaining work when it appears.

The Business surfaces at most one transition at a time, the one it is waiting
at, and pairs it with a message whose `path` selects the instance. After a
successful write the message is an `info` message explaining the transition.
If a requested effect was not applied because of the transition, the message
is a `recoverable` error, as [Overview — Actions](../../overview/index.md#actions)
defines.

Until the transition is performed, the Business does not bring into force any
part of the resource beyond the boundary. For a checkout it reports
`status: incomplete`, and a Complete Checkout received while a transition is
outstanding is answered as [Checkout — Actions](../checkout/index.md#actions)
defines: the current Checkout, `incomplete`, and a `recoverable` error whose
`path` selects the transition. For a cart, which has no status lifecycle, the
transition gates only the effect the Business names in its message.

The instance `id` is the Action's identifier, not the control's. It follows
the common identity rules for Actions, so a transition that becomes
outstanding again after the Buyer steps back carries a new instance `id`,
while `config.element` keeps naming the same DOM `id`, which does not change.

## Processing

The Platform processes a transition by activating the named control on the
Business's page. It locates the control by `label` on the accessibility tree
(matching an interactive control by accessible name, as WebDriver BiDi's
`accessibility` locator does) or by `element` in the DOM, whichever its
environment supports.

The activation starts a navigation, and the Platform waits for it to complete
before reading again:

- For a hard navigation, which loads a new document, the new document's `load`
  event. Tools are per document, so the Platform discovers them again on the
  new page.
- For a soft navigation, which changes history without unloading the page, the
  Navigation API's `navigatesuccess` event when the page intercepts
  navigations, otherwise `currententrychange`.

The Platform then reads the resource with the capability's read operation. The
transition is complete when its instance is no longer present; that is the
authoritative signal, as [Overview — Actions](../../overview/index.md#actions)
requires. The response carries the next transition, or none and, for a
checkout, `ready_for_complete`.

If the instance is still present after the read, the Platform reads again with
bounded backoff set by its own policy. If the Platform cannot locate the
control on the current view, or the instance does not clear within that
policy's bounds or before `expires_at`, the Platform hands off to the Buyer via
`continue_url`; the Buyer performs the transition on the page.

A Business keeps `label` unique among the interactive controls of the view the
transition belongs to, and implements each transition as a navigation, so that
the Platform can observe its completion. A view change that is not a
navigation gives the Platform nothing to wait on, and only the bounded re-read
above remains.

The Business accepts activation of the named control from the Platform, even
where it otherwise rejects agent-originated UI events (see
[Checkout WebMCP — Escalation](../checkout/webmcp.md#escalation-and-buyer-authorization)):
the outstanding transition is its explicit request for that activation.

## Example

A Checkout negotiated over WebMCP on a page that presents its views in
sequence. The Platform has written the buyer, fulfillment, and payment with
`update_checkout`; the Business has persisted everything, but the page is on
its first view and will not advance unasked:

<!-- ucp:example schema=shopping/checkout op=read -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "status": "success",
    "capabilities": {
      "dev.ucp.shopping.checkout": [{ "version": "{{ ucp_version }}" }],
      "dev.ucp.shopping.ui": [
        { "version": "{{ ucp_version }}", "extends": "dev.ucp.shopping.checkout" }
      ]
    },
    "payment_handlers": {}
  },
  "id": "checkout_abc123",
  "status": "incomplete",
  "currency": "USD",
  "line_items": [ ... ],
  "totals": [ ... ],
  "links": [ ... ],
  "actions": {
    "dev.ucp.shopping.ui.transition": [
      {
        "id": "t_shipping",
        "config": {
          "label": "Continue to shipping",
          "element": "continue-shipping"
        }
      }
    ]
  },
  "messages": [
    {
      "type": "info",
      "code": "transition_required",
      "content": "Continue to shipping to confirm the delivery options.",
      "path": "$.actions['dev.ucp.shopping.ui.transition'][0]"
    }
  ],
  "continue_url": "https://business.example.com/checkout-sessions/checkout_abc123"
}
```

The Platform tells the Buyer it is continuing to shipping, activates the
control, waits for the navigation to complete, and calls `get_checkout`. The
Business has brought the shipping view into force; the response carries the
next transition or, when no view remains, `status: ready_for_complete`, and the
negotiation continues with `complete_checkout`.

## Normative requirements

### Business

- **MUST** surface a transition only when the current view's requirements are
  met and the page must move to the next view before the negotiation can
  continue.
- **MUST** surface at most one outstanding transition at a time.
- **MUST** provide both `label` and `element`, identifying the same control on
  the current view.
- **MUST NOT** bring into force any part of the resource beyond the boundary
  until the transition is performed, and, for a checkout, **MUST** report
  `status: incomplete` while a transition is outstanding.
- **MUST** accept activation of the named control from the Platform while the
  transition is outstanding.
- **SHOULD** implement each transition as a navigation, soft or hard, so that
  its completion is observable.
- **SHOULD** keep `label` unique among the interactive controls of the view.

### Platform

- **MUST** activate only the control the outstanding transition names, located
  by `label` or `element`.
- **MUST** wait for the resulting navigation to complete and then read the
  resource again before acting further.
- **MUST** treat the instance's absence from the next response as the
  completion signal, and **MUST NOT** infer completion from the activation
  itself.
- **MUST** hand off via `continue_url` when it cannot locate the control or
  the instance does not clear within its policy's bounds.
- **MUST** present `label` to the Buyer as the description of the transition
  it is performing.
