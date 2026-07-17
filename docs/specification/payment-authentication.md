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
  "actions": {
    "dev.ucp.payment.device_data_collection": [
      {
        "id": "ddc-1",
        "required": true,
        "config": {
          "url": "https://payments.example.com/3ds/method/session_123"
        }
      }
    ]
  }
}
```

A Business normally emits only the next interaction the Platform can process.
If collection must precede a challenge, it emits the DDC Action first and emits
the challenge under `dev.ucp.payment.three_ds_challenge` only in a later
Checkout response.

## Checkout Lifecycle

These Action types use the parent Checkout lifecycle defined in
[Checkout — Actions](checkout.md#actions):

- A Business **MAY** emit device data collection from Create or Update Checkout
  to perform it before payment completion. A required collection Action prevents
  `ready_for_complete` until it resolves. Unrelated Updates remain allowed.
- A Business **SHOULD** accept Complete Checkout before beginning a required
  payment-authentication interaction and return `complete_in_progress` with the
  Action. This represents an accepted payment attempt that is waiting for
  Platform work.
- If an Action instead prevents Complete Checkout from being accepted, the
  Business **MUST** return `status: incomplete` and a `recoverable` error Message
  whose `path` selects the exact Action occurrence.
- After a surface sends `action.done`, the Platform closes it and uses Get
  Checkout for the authoritative state.
- If the same Action type and `id` remain outstanding after `action.done`, the
  Platform **MUST NOT** reopen the surface. It **SHOULD** retry Get Checkout with
  bounded backoff for up to 30 seconds from receipt of the notification. When
  that reconciliation window elapses, the Platform **MUST** stop polling;
  further handling follows the parent Checkout Actions contract.

An `action.done` notification means only that the Platform-facing surface
finished. The Business determines whether collection or authentication succeeded
from its
server-side payment-provider state. A later Checkout response is authoritative.

## Decline, Failure, and Abandonment

A Platform **MAY** decline an instance that violates its runtime policy. If it
cannot process a required instance, it **SHOULD** use a valid `continue_url` to
hand the session to the Business when available.

For an Action on an `incomplete` Checkout, the Platform may instead choose a
different payment instrument through an ordinary Update and later submit a new
Complete operation. The Business treats work associated with the previous
instrument as superseded and stops using it for the new payment attempt.

The individual Action specifications define type-specific timeout and fallback
behavior:

- [Payment Device Data Collection](payment-actions/device-data-collection.md)
- [Payment 3DS Challenge](payment-actions/three-ds-challenge.md)

## Surface Rendering and Notifications

Returning a Payment Authentication Action asks the Platform to render its
`config.url`. Before navigating, the Platform **MUST** validate the URL and
install its message receiver so an immediately completing surface cannot race
initialization.

The `postMessage` and native-webview mechanics follow
[Embedded Protocol — Communication Channels](embedded-protocol.md#communication-channels).
Payment Authentication uses the Action bridge names below and does not use the
Embedded Protocol `ready` handshake or `MessageChannel` upgrade.

Each Action occurrence uses a fresh, isolated browsing context. Device data
collection is hidden and non-interactive. A 3DS challenge is visible, blocks
interaction with the rest of Checkout, and **SHOULD** show a loading state until
its content renders. Web Platforms use an iframe or other handler-approved
browser context. Native Platforms **MUST** expose an equivalent JSON-string
bridge through `window.EmbeddedActionProtocolConsumer` or
`window.webkit.messageHandlers.EmbeddedActionProtocolConsumer`.

Surfaces send `action.done` or `action.error` notifications defined by the
[payment Action OpenRPC](site:services/payment-actions/embedded.openrpc.json).
On the web, the Platform **MUST** validate both `event.source` and `event.origin`.
After a valid terminal notification, it unmounts the surface and ignores
duplicate or late notifications from that context.

### Buyer Dismissal

Cancellation inside a 3DS surface is a provider outcome, not a surface error.
After recording it for the Business, the surface **SHOULD** send `action.done`.
If the Buyer instead dismisses a Platform-owned container before a terminal
notification, the Platform unmounts it and uses Get Checkout once for
authoritative state.

## Security and Data Handling

Web Platforms **MUST** follow the shared
[Embedded Protocol security requirements](embedded-protocol.md#security) for
CSP, iframe sandboxing, credentialless iframe evaluation, and strict origin
validation. [Embedded Checkout security](embedded-checkout.md#security-for-web-based-hosts)
shows how a UCP capability applies those requirements. Payment Authentication
uses its own notification methods and does not adopt the Embedded Protocol
handshake or lifecycle messages.

In addition, Platforms **MUST**:

- parse `config.url` with a conformant URL parser; it **MUST** be absolute and
  use the `https` scheme;
- enforce the handler's trust policy on the initial URL and every redirect;
- grant only the frame or webview capabilities required by the handler, which
  **MUST** document any deviation from the shared sandbox baseline;
- avoid logging session URLs or leaking them through referrers; and
- treat all completion and diagnostic notifications as advisory.
