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

# Payment 3DS Challenge Action

This specification defines the 3DS challenge Action type declared by the
[Payment Authentication extension](../payment-authentication.md):

```text
dev.ucp.payment.three_ds_challenge
```

It asks the Platform to present a buyer-facing payment-authentication surface to
complete 3DS challenges.

## Purpose and Scope

A 3DS challenge Action lets the Business and payment handler ask the Platform to
present an issuer or provider challenge to the Buyer. UCP does not carry EMV 3DS
payloads such as CReq/CRes, AReq/ARes, RReq/RRes, or `transStatus`. Those details
remain within the loaded surface and the Business, payment handler, PSP, 3DS
server, issuer, or ACS integration.

The Platform presents the surface and observes only when the Platform-facing
interaction finishes or cannot continue. The Business determines the
authentication and payment outcome from its server-side provider state.

## Blocking Action

The 3DS challenge Action gates the associated payment attempt from producing a
completed Checkout while the occurrence remains outstanding. It does not assert
that the Complete Checkout operation was rejected, and a terminal surface event
does not itself lift the gate.

A Business **SHOULD** accept Complete Checkout, begin the payment attempt, and
return `complete_in_progress` with the challenge Action. If the Business cannot
accept completion before the challenge, it follows the core Checkout rule: it
returns `incomplete` with a recoverable error Message whose `path` selects the
challenge occurrence.

## Runtime Shape

The Action is emitted under its type key:

<!-- ucp:example schema=shopping/payment_authentication def=dev.ucp.shopping.checkout extract=$.actions target=$.actions op=read -->
```json
{
  "actions": {
    "dev.ucp.payment.three_ds_challenge": [
      {
        "id": "three-ds-challenge-1",
        "config": {
          "payment_instrument_id": "instrument_1",
          "url": "https://payments.example.com/ucp/payment/3ds/session_456"
        }
      }
    ]
  }
}
```

The config shape is defined inline by the
[Payment Authentication extension schema](site:schemas/shopping/payment_authentication.json).

| Field | Type | Required | Notes |
| :---- | :--- | :------- | :---- |
| `payment_instrument_id` | string | ✓ | ID of the associated instrument in the containing Checkout. |
| `url` | string | ✓ | Absolute HTTPS URL for the buyer-facing challenge surface. |

`config.url` **SHOULD** be Business- or provider-operated and own any
provider-specific POST, such as submitting CReq to an ACS challenge URL. The
Platform performs an ordinary navigation to it; it **MUST NOT** construct
provider requests, parse challenge payloads, or relay 3DS protocol data.

## Platform Behavior

The Platform **MUST**:

1. validate the URL according to the Payment Authentication contract, the
   payment handler and instrument context, and Platform policy;
2. load the URL in an isolated, visible browser-capable surface;
3. complete the `action.ready` handshake before presenting the challenge;
4. prevent interaction with the rest of Checkout while the challenge is
   outstanding;
5. correlate embedded notifications with both this Action occurrence and the
   mounted surface; and
6. close the surface after `action.done`, `action.error`, unrecoverable load
   failure, or abandonment.

Mounting the surface **MUST** follow the shared
[Payment Authentication rendering contract](../payment-authentication.md#surface-rendering-and-notifications)
and [Embedded Protocol security requirements](../embedded-protocol.md#security).

On the web the surface may be a full-page frame, modal frame, or separate window
when the negotiated handler defines that presentation and its security policy.
A native Platform may use an isolated webview, browser view, or system browser.
A top-level or system-browser handoff is permitted only when the handler defines
a completion channel that the Platform can authenticate and correlate with the
Action occurrence.

The Platform **MUST NOT** infer an authentication outcome from frame content,
URL changes, or notification diagnostics.

## Embedded Notifications

After completing the shared
[`action.ready` handshake](../payment-authentication.md#ready-handshake), the
surface sends JSON-RPC 2.0 notifications defined by the
[payment Action embedded contract](../payment-authentication.md#surface-rendering-and-notifications).

### Done

When the Platform-facing challenge interaction finishes, the surface **MUST**
send:

<!-- ucp:example schema=transports/jsonrpc def=request op=read -->
```json
{
  "jsonrpc": "2.0",
  "method": "action.done",
  "params": {
    "id": "three-ds-challenge-1"
  }
}
```

`action.done` means only that the Platform should close the challenge surface
and retrieve Checkout. It does not mean authentication or payment succeeded.
After closing the surface, the Platform should issue Get Checkout to confirm
processing state. Get Checkout is a read-only observation and does not
itself advance the payment attempt; the Business advances Checkout state
from server-side provider state (typically an out-of-band provider
push/callback), independent of when the Platform calls Get Checkout.

A handler-owned surface **MAY** include provider-specific or diagnostic params
such as correlation identifiers or SDK outcomes. Platforms **MUST** ignore
unknown params for UCP processing unless the negotiated handler defines them.
They are never authoritative payment outcomes by default.

### Error

If the surface cannot continue, it **MAY** send:

<!-- ucp:example schema=transports/jsonrpc def=request op=read -->
```json
{
  "jsonrpc": "2.0",
  "method": "action.error",
  "params": {
    "id": "three-ds-challenge-1",
    "error": {
      "ucp": { "version": "{{ ucp_version }}", "status": "error" },
      "messages": [
        {
          "type": "error",
          "code": "action_failed",
          "content": "The challenge surface could not continue.",
          "severity": "recoverable"
        }
      ]
    }
  }
}
```

Surface-level codes are the shared
[well-known `action.error` codes](../payment-authentication.md#surface-rendering-and-notifications).
Buyer abandonment and provider authentication outcomes may be unavailable to the
surface or known only by the provider backend; the Business and payment provider
remain authoritative for those distinctions. After either notification, the
Platform follows the shared Payment Authentication reconciliation contract.

## Combined Provider Flows

A payment provider may serve both device data collection and a challenge from
one `config.url`. The emitted Action type describes the Platform-facing behavior:

- If the surface remains invisible and never requests Buyer interaction, the
  Business emits device data collection.
- If the surface may display a Buyer challenge, the Business emits 3DS challenge.

The Business must not emit an invisible DDC Action and then make that surface
visible. If collection completes first, the preferred flow is to remove the DDC
occurrence and emit a new challenge occurrence in a later Checkout response.
The two occurrences have different Action types and IDs even when their
`config.url` origin is the same.

## Deadline and Fallback

[EMV 3-D Secure Protocol and Core Functions v2.3.1.1](https://www.emvco.com/specifications/emv-3-d-secure-protocol-and-core-functions-specification-6/){ target="_blank" }
gives the ACS 10 minutes (600 seconds) after successfully sending each challenge
interface to the challenge iframe (Req 226). The surface and provider own that
per-interface timer. It does not define a single UCP deadline beginning at the
initial navigation.

The Platform applies a bounded outer-surface deadline defined by the handler or
Platform policy, measured from navigation and capped by Checkout `expires_at`.
The Business **MUST** choose an expiry that accommodates the handler-defined
window. The outer deadline governs only the Platform-owned container and does
not replace or reset an ACS timer.

The Platform may close sooner after a valid terminal notification, load failure,
Buyer dismissal, or terminal Checkout state. When the outer deadline elapses, it
**MUST** close the surface, treat the interaction as abandoned, and follow the
non-successful surface reconciliation path. It **MUST NOT** remount the same
Action type and `id`; further handling follows the parent Checkout Actions
fallback, handoff, and cancellation rules.

## Security

The common [Payment Authentication security requirements](../payment-authentication.md#security-and-data-handling)
apply. In addition:

- The handler's trust policy **MUST** authorize the initial and redirect origins
  before the Platform displays them.
- The Platform validates both message source and origin.
- A later Checkout response based on server-side provider state remains
  authoritative regardless of any surface notification.
