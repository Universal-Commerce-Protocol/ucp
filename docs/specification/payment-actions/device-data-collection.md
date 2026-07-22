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

This specification defines the device data collection Action type declared by
the [Payment Authentication extension](../payment-authentication.md):

```text
dev.ucp.payment.device_data_collection
```

It asks the Platform to run a scoped, invisible browser-capable surface associated
with a payment instrument or attempt.

## Purpose and Scope

Device data collection lets a Business, payment handler, PSP, or 3DS provider
collect device or browser data before payment processing continues. UCP does not
carry the collected data. The loaded surface sends provider-specific data directly
to the Business or payment provider through its own integration.

For EMV 3DS, this Action represents only the Platform-facing instruction to
mount the collection surface. UCP does not define how a Business maps ACS method
availability, method timeouts, or collection outcomes into EMVCo state such as
`threeDSCompInd`. If a provider or Business skips collection, including when an
ACS supplies no method URL, the Business does not emit this Action.

## Emission and Gated Effect

A Business **MAY** emit this type from Create, Update, or Complete Checkout after
it can associate the collection with a payment instrument and negotiated payment
handler.

- With `required: false`, collection is an optimization. The Business
  **MUST NOT** reject or indefinitely delay the related payment attempt merely
  because the Platform skipped that occurrence.
- With `required: true`, the Action gates further processing of the associated
  payment attempt until the Platform-facing surface finishes or the handler's
  timeout/fallback policy is applied. It does not require collection itself to
  succeed.

## Runtime Shape

The Action is emitted under its type key:

<!-- ucp:example skip reason="illustrative Action map fragment" -->
```json
{
  "actions": {
    "dev.ucp.payment.device_data_collection": [
      {
        "id": "ddc-1",
        "required": true,
        "config": {
          "url": "https://payments.example.com/ucp/payment/ddc/session_123"
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
| `url` | string | ✓ | Absolute HTTPS URL for the invisible collection surface. |

The Business **SHOULD** provide a Business- or provider-operated wrapper URL that
owns any provider-specific POST, such as posting `threeDSMethodData` to an ACS
method URL. The Platform performs an ordinary navigation to `config.url`.

## Platform Behavior

The Platform **MUST**:

1. validate the URL according to the Payment Authentication contract, the
   payment handler and instrument context, and Platform policy;
2. load the URL in an isolated, invisible browser-capable surface;
3. correlate embedded notifications with both this Action occurrence and the
   mounted surface; and
4. unmount the surface after `action.done`, `action.error`, load failure, or
   timeout.

Mounting the surface **MUST** follow the shared
[Payment Authentication rendering contract](../payment-authentication.md#surface-rendering-and-notifications)
and [Embedded Protocol security requirements](../embedded-protocol.md#security).

On the web the surface is typically a hidden iframe. A native Platform may use
an isolated webview or equivalent browser surface. It must not be visible to the
Buyer or request Buyer interaction.

The Platform distinguishes only whether its surface finished or could not
continue. It does not determine whether device data was collected successfully,
whether an ACS method timed out, or whether 3DS authentication should proceed.

## Embedded Notifications

The surface sends JSON-RPC 2.0 notifications defined by the
[payment Action embedded contract](../payment-authentication.md#embedded-notifications).

### Done

When the Platform-facing collection step is finished, the surface **MUST** send:

<!-- ucp:example skip reason="payment Action embedded notification" -->
```json
{
  "jsonrpc": "2.0",
  "method": "action.done",
  "params": {
    "id": "ddc-1"
  }
}
```

The surface may send `action.done` when handler-owned logic determines that the
Platform should close the surface. The notification does not reveal whether
collection succeeded, was unavailable, was skipped, or mapped to a particular
provider completion indicator.

### Error

If the surface cannot continue from the Platform-facing transport perspective,
it **MAY** send:

<!-- ucp:example skip reason="payment Action embedded notification" -->
```json
{
  "jsonrpc": "2.0",
  "method": "action.error",
  "params": {
    "id": "ddc-1",
    "error": {
      "ucp": { "version": "{{ ucp_version }}", "status": "error" },
      "messages": [
        {
          "type": "error",
          "code": "action_unavailable",
          "content": "Device data collection could not start.",
          "severity": "recoverable"
        }
      ]
    }
  }
}
```

Recommended surface-level codes are `action_unavailable` when initialization
fails, `action_expired` when the surface's session expired, and `action_failed`
for another terminal surface error. These are diagnostic codes, not EMV 3DS or
payment outcomes. A provider-domain timeout or unavailable method that the
handler can safely continue past should normally result in `action.done`, with
the Business and provider recording the domain outcome server-side.

## Deadline and Fallback

[EMV 3-D Secure Protocol and Core Functions v2.3.1.1](https://www.emvco.com/specifications/emv-3-d-secure-protocol-and-core-functions-specification-6/){ target="_blank" }
requires the 3DS Method to complete within five seconds (Req 315). The Platform
starts the same five-second deadline when the surface finishes loading.

If no valid `action.done` or `action.error` arrives before the deadline, the
Platform **MUST** unmount the surface, treat the interaction as timed out, and
use Get Checkout. It may unmount sooner after load failure or a valid terminal
notification. The handler remains responsible for `threeDSCompInd` and all other
provider-owned state.

If the Action remains outstanding after Get Checkout, further handling follows
the parent Checkout Actions contract. An optional occurrence does not prevent
the Business from proceeding without the collected data.

## Security

The common [Payment Authentication security requirements](../payment-authentication.md#security-and-data-handling)
apply. In addition:

- The handler's trust policy **MUST** authorize the initial and redirect origins
  before the Platform loads them.
- The surface **MUST NOT** receive Platform credentials or access Platform
  storage.
- Provider payloads and collected device data **MUST NOT** be copied into the
  Action, notification params, Checkout, or payment instrument.
- `action.done` and `action.error` are advisory surface signals. A later
  Checkout response, based on Business/provider state, remains authoritative.
