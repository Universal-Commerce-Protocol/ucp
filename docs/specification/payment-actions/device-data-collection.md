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

# Payment Device Data Collection Action

This specification defines the standard payment device data collection action.
It uses the common [Runtime Actions](../overview.md#runtime-actions) envelope and
is intended for payment handlers that need the platform to run a scoped,
invisible browser-capable collection step before payment processing continues.

The action code is:

```text
dev.ucp.payment.device_data_collection
```

## Purpose

Device data collection lets a business, payment handler, PSP, or 3DS provider
collect device or browser data associated with a selected payment instrument or
payment attempt. UCP does not carry the collected data. The collection surface
communicates any domain-specific data to the business or payment provider through
its own integration. The platform only executes the scoped surface and resumes
the UCP operation when the surface signals that it is done.

## Runtime Shape

The action is emitted in an entity response using the common action envelope:

```json
{
  "code": "dev.ucp.payment.device_data_collection",
  "severity": "blocking",
  "config": {
    "url": "https://business.example.com/ucp/payment/ddc/session_123",
    "timeout_seconds": 10
  }
}
```

### Config

The config schema is defined at
[`source/schemas/payment/actions/device_data_collection.json`](site:schemas/payment/actions/device_data_collection.json).

| Field | Type | Required | Notes |
| :---- | :--- | :------- | :---- |
| `url` | string | ✓ | HTTPS URL for the invisible collection surface. The URL is loaded by the platform and owns any PSP/3DS-provider protocol details. |
| `timeout_seconds` | integer | optional | Number of seconds the platform should wait after loading the surface before treating the action as failed or abandoned. If absent, the platform may apply its own timeout. |

The `url` **MUST** be an absolute HTTPS URL. The business **SHOULD** provide a
business-owned or business-authorized URL rather than requiring the platform to
load a raw issuer, ACS, or PSP URL directly.

## Platform Behavior

The platform **MUST** load `config.url` in an isolated, invisible,
browser-capable surface. On web this is typically an iframe; on native platforms
it may be an equivalent isolated webview or browser surface. The surface should
not be visible to the buyer and should not require buyer interaction.

The platform **MUST NOT** parse, transform, or relay PSP-specific device data
payloads. Those payloads stay within the loaded surface and the business or
payment-provider integration.

## Embedded Transport

The embedded transport for payment action surfaces is defined by
[`source/services/payment-actions/embedded.openrpc.json`](site:services/payment-actions/embedded.openrpc.json).
Messages are JSON-RPC 2.0 notifications sent from the loaded action surface to
the platform using `postMessage` or the equivalent native bridge.

### Done Message

When collection is complete, the loaded surface **MUST** send a `pa.done`
notification to its parent/opener:

```json
{
  "jsonrpc": "2.0",
  "method": "pa.done",
  "params": {
    "code": "dev.ucp.payment.device_data_collection"
  }
}
```

The platform **MUST** correlate the message to the surface it mounted for the
outstanding action. On web, this means validating `event.source` against the
mounted frame and validating `event.origin` according to the owning handler's
security policy. The `code` value is not a trust boundary; it is a typed signal
that the mounted surface believes the action is complete.

### Error Message

If the loaded surface cannot continue, it **MAY** send a `pa.error`
notification:

```json
{
  "jsonrpc": "2.0",
  "method": "pa.error",
  "params": {
    "code": "dev.ucp.payment.device_data_collection",
    "error": {
      "ucp": { "version": "{{ ucp_version }}", "status": "error" },
      "messages": [
        {
          "type": "error",
          "code": "action_failed",
          "content": "Device data collection failed.",
          "severity": "recoverable"
        }
      ]
    }
  }
}
```

The action has no UCP result payload. Completion means only that the platform can
resume the UCP operation. Domain-specific collection results are observed by the
business or payment provider outside the UCP action payload.

## Resuming the UCP Operation

After receiving the done message, the platform **MUST** resubmit the UCP request
that led to the action, using the same checkout/payment state it would have used
before the action was emitted. The platform **MUST NOT** add a device-data result
field to checkout or payment instruments unless another active capability or
handler explicitly defines such a field.

For checkout, this means:

- If the action was returned from `update_checkout`, call `update_checkout` again
  with the same intended checkout state.
- If the action was returned from `complete_checkout`, call `complete_checkout`
  again with the same selected payment instrument and credential.

The business then decides, using its payment-provider state, whether checkout can
proceed, whether another action is required, or whether payment should fail.

## Severity

This action may be emitted with any common action severity:

| Severity | Meaning |
| :------- | :------ |
| `optional` | The platform may skip collection. Checkout or payment processing can continue, but risk outcomes or frictionless authorization rates may degrade. |
| `required` | Collection must complete before the entity can reach a successful terminal state, but the entity remains otherwise usable. |
| `blocking` | The current attempted transition is blocked until collection completes, times out, or the platform follows the owning handler's fallback path. |

When device data collection is emitted in response to `complete_checkout`,
`blocking` is usually appropriate: the attempted payment transition cannot
finish until collection completes or the business chooses another path.

## Ignoring, Timeout, and Instrument Switching

If the action is `optional` and the platform ignores it, the business **MUST NOT**
treat the missing collection as a protocol error. The business may continue
without the data, emit a required/blocking collection action later, request a
challenge, decline the payment, or escalate according to the owning handler's
rules.

If the action times out or the surface fails to load, the platform follows the
fallback behavior defined by the owning payment handler. For checkout, the
platform may retry, select another payment instrument, or escalate via
`continue_url` when allowed.

If the platform submits a different selected payment instrument while a device
data collection session is outstanding for the previous instrument or payment
attempt, the business **MUST** treat the previous collection session as
superseded and stop using it for the new instrument or payment attempt.

## Security

The owning payment handler **MUST** define the trust policy for `config.url`,
including allowed origins or URL patterns when appropriate. Platforms **SHOULD**
apply that policy before loading the surface.

The collection surface should be isolated from the platform's own buyer session
and credentials. The platform should not grant capabilities beyond those required
by the owning payment handler's device-data collection contract.
