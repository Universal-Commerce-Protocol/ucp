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

This specification defines the standard payment 3DS challenge action. It uses
the common [Runtime Actions](../overview.md#runtime-actions) envelope and is
intended for payment handlers that need the platform to present a buyer-facing
3DS challenge during payment completion.

The action code is:

```text
dev.ucp.payment.three_ds_challenge
```

## Purpose

A 3DS challenge action lets the business or payment handler ask the platform to
present a payment-authentication surface to the buyer. UCP does not carry 3DS
protocol payloads such as challenge requests, challenge responses, or
transaction-status values. Those details remain within the loaded challenge
surface and the business, PSP, 3DS server, issuer, or ACS integration.

The platform only presents the scoped challenge surface and resumes the UCP
operation when the surface signals that it is done.

## Runtime Shape

The action is emitted in an entity response using the common action envelope:

```json
{
  "code": "dev.ucp.payment.three_ds_challenge",
  "severity": "blocking",
  "config": {
    "url": "https://business.example.com/ucp/payment/3ds/session_456",
    "timeout_seconds": 300
  }
}
```

### Config

The config schema is defined at
[`source/schemas/payment/actions/three_ds_challenge.json`](site:schemas/payment/actions/three_ds_challenge.json).

| Field | Type | Required | Notes |
| :---- | :--- | :------- | :---- |
| `url` | string | ✓ | HTTPS URL for the buyer-facing challenge surface. The URL owns any ACS, issuer, PSP, or 3DS-provider protocol details. |
| `timeout_seconds` | integer | optional | Number of seconds the platform should wait after loading the surface before treating the action as abandoned or failed. If absent, the platform may apply its own timeout. |

The `url` **MUST** be an absolute HTTPS URL. The business **SHOULD** provide a
business-owned or business-authorized wrapper URL rather than requiring the
platform to load a raw issuer, ACS, or PSP URL directly.

## Platform Behavior

The platform **MUST** load `config.url` in an isolated buyer-facing,
browser-capable surface. On web this may be a full-page frame, modal frame, or
top-level navigation according to the owning handler's rules. On native
platforms it may be an equivalent isolated webview, browser view, or system
browser handoff.

For the standard UCP 3DS challenge action, the default platform behavior is to
present a visible full-page surface that blocks interaction with the rest of
checkout until the action completes, is abandoned, times out, or the platform
follows the owning handler's fallback path.

The platform **MUST NOT** parse, transform, or relay 3DS protocol payloads. The
challenge surface and the payment-provider integration own those details.

## Embedded Transport

The embedded transport for payment action surfaces is defined by
[`source/services/payment-actions/embedded.openrpc.json`](site:services/payment-actions/embedded.openrpc.json).
Messages are JSON-RPC 2.0 notifications sent from the loaded action surface to
the platform using `postMessage` or the equivalent native bridge.

### Done Message

When the challenge interaction is complete from the platform-facing surface's
perspective, the loaded surface **MUST** send a `pa.done` notification to its
parent/opener:

```json
{
  "jsonrpc": "2.0",
  "method": "pa.done",
  "params": {
    "code": "dev.ucp.payment.three_ds_challenge"
  }
}
```

The done message does not assert that authentication succeeded. It means only
that the platform can close the challenge surface and resume the UCP operation.
The business determines the payment outcome from its payment-provider state after
the platform resubmits the UCP request.

The platform **MUST** correlate the message to the surface it mounted for the
outstanding action. On web, this means validating `event.source` against the
mounted frame or window and validating `event.origin` according to the owning
handler's security policy. The `code` value is not a trust boundary; it is a
typed signal that the mounted surface believes the action is complete.

### Error Message

If the loaded surface cannot continue, it **MAY** send a `pa.error`
notification:

```json
{
  "jsonrpc": "2.0",
  "method": "pa.error",
  "params": {
    "code": "dev.ucp.payment.three_ds_challenge",
    "error": {
      "ucp": { "version": "{{ ucp_version }}", "status": "error" },
      "messages": [
        {
          "type": "error",
          "code": "action_failed",
          "content": "3DS challenge failed.",
          "severity": "recoverable"
        }
      ]
    }
  }
}
```

## Resuming the UCP Operation

After receiving the done message, the platform **MUST** resubmit the UCP request
that led to the action, using the same checkout/payment state it would have used
before the action was emitted. The platform **MUST NOT** add 3DS result fields to
checkout or payment instruments unless another active capability or handler
explicitly defines such fields.

For checkout, this means that after a challenge returned from
`complete_checkout`, the platform calls `complete_checkout` again with the same
selected payment instrument and credential. The business then decides, using its
payment-provider state, whether checkout completes, payment fails, another action
is required, or escalation is necessary.

## Severity

This action is normally emitted with `blocking` severity because it blocks the
current payment-completion transition:

```json
{
  "code": "dev.ucp.payment.three_ds_challenge",
  "severity": "blocking",
  "config": {
    "url": "https://business.example.com/ucp/payment/3ds/session_456"
  }
}
```

A payment handler specification **MAY** define other severities for specialized
flows, but it must document what ignoring or deferring the challenge means for
payment processing. A standard 3DS challenge required during payment completion
should be treated as `blocking`.

## Abandonment, Timeout, and Instrument Switching

If the buyer closes the challenge surface, the surface fails to load, or
`timeout_seconds` elapses, the platform follows the fallback behavior defined by
the owning payment handler. For checkout, fallback is typically one of:

- Retry the same payment instrument, causing the business to create or reuse a
  safe payment-authentication attempt according to its payment-provider rules.
- Select another payment instrument and call `complete_checkout` again.
- Escalate to the business-hosted checkout using `continue_url`. When ECP is
  available, the platform may load the `continue_url` in an embedded context.

If the platform submits a different selected payment instrument while a 3DS
challenge is outstanding for the previous selected instrument, the business
**MUST** treat the previous payment attempt as superseded. Before processing the
new selected instrument, the business **MUST** cancel, fail, release, or
otherwise make safe any pending authorization, challenge session, or payment
attempt associated with the previous instrument, according to its
payment-provider contract.

The platform does not need to add abandonment state to checkout or the previous
instrument to trigger this behavior. A subsequent `complete_checkout` with a
different selected payment instrument while the prior challenge is outstanding is
sufficient to indicate that the prior payment attempt has been abandoned or
superseded, unless the owning payment handler defines a more specific state
transition.

## Security

The owning payment handler **MUST** define the trust policy for `config.url`,
including allowed origins or URL patterns when appropriate. Platforms **SHOULD**
apply that policy before loading the surface.

The challenge surface should be isolated from the platform's own buyer session
and credentials. The platform should not grant capabilities beyond those required
by the owning payment handler's 3DS challenge contract.

The business-hosted or business-authorized challenge URL is responsible for any
issuer, ACS, PSP, or 3DS-provider communication. UCP platforms should not be
required to understand or forward CReq/CRes, AReq/ARes, RReq/RRes, transStatus,
or other 3DS protocol details.
