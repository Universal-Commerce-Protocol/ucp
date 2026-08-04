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

# Payment Authentication Extension

## Overview

The Payment Authentication extension defines browser-surface interactions that
a Platform may need to process while a payment attempt is underway. It declares
two concrete [Action types](overview.md#actions):

| Action type | Platform interaction |
| :---------- | :------------------- |
| `dev.ucp.payment.device_data_collection` | Run an invisible browser-capable device data collection surface. |
| `dev.ucp.payment.three_ds_challenge` | Present a buyer-facing 3DS challenge surface. |

The extension is named:

```text
dev.ucp.shopping.payment_authentication
```

It extends `dev.ucp.shopping.checkout`. Negotiating this extension activates the
complete contract for both Action types. A Business **MUST NOT** emit either type
unless this extension is active for the Checkout.

The extension standardizes only the Platform-facing interaction. It does not
re-specify EMV 3DS, carry EMV 3DS messages, report authentication outcomes, or
replace payment-handler processing. The Business, its payment handler, and its
payment provider remain responsible for provider protocol state and for the
authoritative payment outcome.

## Discovery and Negotiation

Businesses and Platforms advertise this extension in their profiles:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.payment_authentication": [
        {
          "version": "{{ ucp_version }}",
          "extends": "dev.ucp.shopping.checkout",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/payment-authentication",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/payment_authentication.json"
        }
      ]
    }
  }
}
```

A Platform advertises the extension only if it can process both the invisible
and buyer-facing browser surfaces, enforce the security requirements in this
specification, and process the embedded notifications. A Business advertises it
only when each payment handler that may cause these Actions defines the required
trust and fallback contract.

Negotiating the extension does not make every runtime URL trustworthy. Each
instance remains subject to its schema, the payment handler and instrument
context established by the payment attempt, and Platform policy.

## Runtime Shape

Actions are keyed by type in the Checkout response. For example, a device data
collection step can be followed by a challenge in a later response:

<!-- ucp:example schema=shopping/payment_authentication def=dev.ucp.shopping.checkout op=read -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "status": "success",
    "capabilities": {
      "dev.ucp.shopping.payment_authentication": [
        {
          "version": "{{ ucp_version }}",
          "extends": "dev.ucp.shopping.checkout"
        }
      ]
    },
    "payment_handlers": {
      "com.example.card": [
        { "id": "card_handler_1", "version": "{{ ucp_version }}" }
      ]
    }
  },
  "id": "checkout_123",
  "status": "complete_in_progress",
  "currency": "USD",
  "line_items": [],
  "totals": [
    { "type": "subtotal", "amount": 100 },
    { "type": "total", "amount": 100 }
  ],
  "links": [],
  "payment": {
    "instruments": [
      {
        "id": "instrument_1",
        "handler_id": "card_handler_1",
        "type": "card",
        "selected": true
      }
    ]
  },
  "actions": {
    "dev.ucp.payment.device_data_collection": [
      {
        "id": "ddc-1",
        "config": {
          "payment_instrument_id": "instrument_1",
          "url": "https://payments.example.com/3ds/method/session_123"
        }
      }
    ]
  }
}
```

A Business **SHOULD** keep at most one Payment Authentication Action
outstanding per payment attempt at a time, emitting only the next interaction
the Platform can process, because collection completes or times out before a
challenge is emitted. When collection must precede a challenge, the Business
emits the device data collection Action first and emits the challenge under
`dev.ucp.payment.three_ds_challenge` only in a later Checkout response.

When `dev.ucp.shopping.split_payments` is active a Checkout can carry an attempt
per instrument, each with its own outstanding authentication action, and
`config.payment_instrument_id` is what distinguishes them.

Each Action's `config.payment_instrument_id` **MUST** identify an instrument in
the containing Checkout. The Platform resolves that instrument's `handler_id`
against `ucp.payment_handlers` and applies that handler's trust and fallback
rules. The Platform **MUST** decline an Action whose instrument or handler
association cannot be resolved unambiguously.

## Checkout Lifecycle

These Action types use the parent Checkout lifecycle defined in
[Checkout — Actions](checkout.md#actions):

- Every emitted Payment Authentication Action gates advancement of its associated
  payment attempt while the same Action type and `id` remain outstanding in the
  authoritative Checkout. A terminal surface event ends the Platform's current
  processing attempt; it does not lift the gate.
- A Business **MAY** emit device data collection from Create or Update Checkout
  to perform it before payment completion. While the Checkout is `incomplete`,
  the Action prevents `ready_for_complete` until it resolves; unrelated Updates
  remain allowed.
- A Business **SHOULD** accept Complete Checkout before beginning a
  payment-authentication interaction needed during payment processing and return
  `complete_in_progress` with the Action. This represents an accepted payment
  attempt that is waiting for Platform work.
- If an Action instead prevents Complete Checkout from being accepted, the
  Business **MUST** return `status: incomplete` and a `recoverable` error Message
  whose `path` selects the exact Action occurrence.
- While the Checkout is `complete_in_progress`, the Platform **MUST NOT** start
  another Update or Complete Checkout operation. It uses Get Checkout to observe
  Business processing and follows the parent fallback, handoff, and cancellation
  rules.

A Payment Authentication Action occurrence is single-use. After starting its
surface, the Platform **MUST NOT** process the same Action type and `id` again,
including after `action.done`, `action.error`, a load failure, timeout, or Buyer
dismissal. If the Business needs the Platform to retry the interaction, it
**MUST** replace the occurrence with a new `id`.

After a terminal surface outcome, the Platform unmounts the surface and
reconciles with the authoritative Checkout:

| Surface outcome | Reconciliation |
| :-------------- | :------------- |
| `action.done` | Use Get Checkout and repeat with bounded backoff for no more than 30 seconds, stopping earlier at `expires_at`. |
| `action.error`, load failure, timeout, or Buyer dismissal | Use Get Checkout once before applying fallback. The Action type or handler may define additional bounded reconciliation. |

If the later response removes the Action, replaces it with a new `id`, or
advances the Checkout, that response is authoritative. After learning a terminal
provider outcome, the Business **MUST** remove the original occurrence, replace
it with new work under a new `id`, or advance the Checkout. It **MUST NOT**
continue returning an occurrence that no longer represents processable work.

If the same occurrence remains after its reconciliation window, the Platform
**MUST NOT** reopen it and follows the parent Checkout Actions fallback, handoff,
and cancellation rules.

An `action.done` notification means only that the Platform-facing surface
finished. The Business determines whether collection or authentication succeeded
from its server-side payment-provider state.

## Decline, Failure, and Abandonment

A Platform **MAY** decline an instance that violates its runtime policy. If it
cannot process the instance, it **SHOULD** use a valid `continue_url` to hand the
session to the Business when available.

For an Action on an `incomplete` Checkout, the Platform may instead choose a
different payment instrument through an ordinary Update and later submit a new
Complete operation. This option is unavailable during `complete_in_progress`,
when Update Checkout is frozen. The Business treats work associated with the
previous instrument as superseded and stops using it for the new payment
attempt. Superseded work is no longer outstanding, so those Action occurrences
do not appear in later Checkout responses, and a Business **MUST** drop Actions
for instruments that are no longer present in the Checkout.

The individual Action specifications define type-specific timeout and fallback
behavior:

- [Payment Device Data Collection](payment-actions/device-data-collection.md)
- [Payment 3DS Challenge](payment-actions/three-ds-challenge.md)

## Surface Rendering and Notifications

Returning a Payment Authentication Action asks the Platform to render its
`config.url`. The payment handler specification names the origins its Action
surfaces load from; those are the occurrence's **allowed origins**. They may be
provider-operated, Business-operated, or both, so this specification does not
choose which party holds that trust, only that the expectation exists before the
Action is emitted. The Platform **MUST** decline an occurrence whose
`config.url` origin is not among them, and **MUST** install its message receiver
before navigating so an immediately completing surface cannot race
initialization.

The `postMessage` and native-webview mechanics follow
[Embedded Protocol — Communication Channels](embedded-protocol.md#communication-channels).
Payment Authentication uses the Action methods below. It does not use a
capability-specific Embedded Protocol `ready` method or `MessageChannel` upgrade;
`action.ready` is its scoped handshake.

Each Action occurrence uses a fresh, isolated browsing context. Device data
collection is hidden and non-interactive. A 3DS challenge is visible, blocks
interaction with the rest of Checkout, and **SHOULD** show a loading state until
its content renders. Web Platforms use an iframe or other handler-approved
browser context. For messages from a native surface to the Platform, native
Platforms **MUST** expose a JSON-string bridge through
`window.EmbeddedActionProtocolConsumer` (Android) or
`window.webkit.messageHandlers.EmbeddedActionProtocolConsumer` (iOS). For the
ready response from the Platform to the surface, the Platform calls
`window.EmbeddedActionProtocol.postMessage()` with the JSON-stringified JSON-RPC
response.

### Ready Handshake

Before beginning Action-specific work, every surface **MUST** send an
`action.ready` JSON-RPC request. Its `params.id` identifies the outstanding
Action occurrence, while the JSON-RPC envelope `id` correlates the ready
response. Its `params.version` **MUST** equal the active Payment Authentication
extension version in the containing Checkout.

<!-- ucp:example schema=transports/jsonrpc def=request op=read -->
```json
{
  "jsonrpc": "2.0",
  "id": "ready-1",
  "method": "action.ready",
  "params": {
    "id": "ddc-1",
    "version": "{{ ucp_version }}"
  }
}
```

The Platform **MUST** validate the message source, allowed origin, Action
occurrence, and version before responding. A source or origin failure is
untrusted and receives no response. If the trusted surface names an unknown
Action occurrence or a version other than the active version, the Platform
returns an error result, unmounts the surface, and follows non-successful
reconciliation.

For a valid request, the Platform returns an empty JSON-RPC result. The
successful response confirms that the requested Payment Authentication extension
version was accepted:

<!-- ucp:example schema=transports/jsonrpc def=success_response op=read -->
```json
{
  "jsonrpc": "2.0",
  "id": "ready-1",
  "result": {}
}
```

The surface **MUST** wait for this successful response before beginning device
data collection, presenting a challenge, or sending `action.done` or
`action.error`. The version remains fixed for the lifetime of that Action
occurrence.

After the handshake, surfaces send `action.done` or `action.error` notifications
defined by the
[payment Action OpenRPC](site:services/payment-actions/embedded.openrpc.json).
On the web, the Platform **MUST** validate `event.source` against the mounted
surface and `event.origin` against the occurrence's allowed origins. After a
valid terminal notification, it unmounts the surface and ignores duplicate or
late notifications from that context.

This extension defines the following well-known `action.error` codes:

| Code | Meaning |
| :--- | :------ |
| `action_unavailable` | The surface could not initialize. |
| `action_expired` | The surface's session expired. |
| `action_failed` | Another terminal surface error. |

These are diagnostic surface codes, never authentication or payment outcomes.
Following [Error Code](site:schemas/common/types/error_code.json), the set stays
open: a surface **MAY** send another value, and a Platform **MUST** tolerate one
it does not recognize and reconcile the same way.

### Buyer Dismissal

Cancellation inside a 3DS surface is a provider outcome, not a surface error.
After recording it for the Business, the surface **SHOULD** send `action.done`.
If the Buyer instead dismisses a Platform-owned container before a terminal
notification, the Platform unmounts it and follows the non-successful surface
reconciliation path above.

## Security and Data Handling

Web Platforms **MUST** follow the shared
[Embedded Protocol security requirements](embedded-protocol.md#security) for
CSP, iframe sandboxing, credentialless iframe evaluation, and strict origin
validation. [Embedded Checkout security](embedded-checkout.md#security-for-web-based-hosts)
shows how a UCP capability applies those requirements. Payment Authentication
uses its own `action.ready` handshake and terminal notification methods; it does
not adopt the Embedded Protocol's capability lifecycle or delegation messages.

In addition, Platforms **MUST**:

- parse `config.url` with a conformant URL parser; it **MUST** be absolute, use
  the `https` scheme, and carry no userinfo component;
- keep the surface within the allowed origins; on the web, a `frame-src`
  directive naming only them makes a cross-origin redirect fail to load rather
  than silently widen trust;
- grant only the frame or webview capabilities required by the handler, which
  **MUST** document any deviation from the shared sandbox baseline;
- avoid logging session URLs or leaking them through referrers; and
- treat all completion and diagnostic notifications as advisory.
