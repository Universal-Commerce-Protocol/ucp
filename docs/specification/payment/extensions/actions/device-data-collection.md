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
the [Payment Authentication extension](../authentication.md):

```text
dev.ucp.common.payment.device_data_collection
```

It asks the Platform to mount an invisible payment-authentication surface to
complete device data collection.

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

## Blocking Action

A Business **MAY** emit this type from a Create, Update, or Complete Checkout
response after it can associate collection with a payment instrument and
negotiated payment handler. `config.payment_instrument_id` identifies that
instrument.

The Action gates advancement of the associated payment attempt while the
occurrence remains outstanding in the authoritative Checkout. A terminal surface
event starts reconciliation; it does not itself lift the gate or assert that
collection succeeded. If collection is merely an optimization that the Business
will not wait for, the Business **MUST NOT** emit an Action.

## Runtime Shape

The Action is emitted under its type key:

<!-- ucp:example schema=common/payment_authentication def=dev.ucp.shopping.checkout extract=$.actions target=$.actions op=read -->
```json
{
  "actions": {
    "dev.ucp.common.payment.device_data_collection": [
      {
        "id": "ddc-1",
        "config": {
          "payment_instrument_id": "instrument_1",
          "url": "https://payments.example.com/ucp/payment/ddc/session_123"
        }
      }
    ]
  }
}
```

The config shape is defined inline by the
[Payment Authentication extension schema](site:schemas/common/payment_authentication.json).

| Field | Type | Required | Notes |
| :---- | :--- | :------- | :---- |
| `payment_instrument_id` | string | ✓ | ID of the associated instrument in the containing Checkout. |
| `url` | string | ✓ | Absolute HTTPS URL for the invisible collection surface. |

`config.url` **SHOULD** be Business- or provider-operated and own any
provider-specific POST, such as posting `threeDSMethodData` to an ACS method
URL. The Platform performs an ordinary navigation to it.

## Platform Behavior

The Platform **MUST**:

1. validate the URL according to the Payment Authentication contract, the
   payment handler and instrument context, and Platform policy;
2. load the URL in an isolated, invisible browser-capable surface;
3. complete the `action.ready` handshake before allowing collection to begin;
4. correlate embedded notifications with both this Action occurrence and the
   mounted surface; and
5. unmount the surface after `action.done`, `action.error`, load failure, or
   timeout.

Mounting the surface **MUST** follow the shared
[Payment Authentication rendering contract](../authentication.md#surface-rendering-and-notifications)
and [Embedded Protocol security requirements](../../../embedded-protocol.md#security).

On the web the surface is typically a hidden iframe. A native Platform may use
an isolated webview or equivalent browser surface. It **MUST NOT** be visible to
the Buyer or request Buyer interaction.

The Platform distinguishes only whether its surface finished or could not
continue. It does not determine whether device data was collected successfully,
whether an ACS method timed out, or whether 3DS authentication should proceed.

## Embedded Notifications

After completing the shared
[`action.ready` handshake](../authentication.md#ready-handshake), the
surface sends JSON-RPC 2.0 notifications defined by the
[payment Action embedded contract](../authentication.md#surface-rendering-and-notifications).

### Done

When the Platform-facing collection step is finished, the surface **MUST** send:

<!-- ucp:example schema=transports/jsonrpc def=request op=read -->
```json
{
  "jsonrpc": "2.0",
  "method": "action.done",
  "params": {
    "id": "ddc-1"
  }
}
```

Handler-owned logic determines when that step is finished. The notification does
not reveal whether collection succeeded, was unavailable, was skipped, or mapped
to a particular provider completion indicator.

### Error

If the surface cannot continue from the Platform-facing transport perspective,
it **MAY** send:

<!-- ucp:example schema=transports/jsonrpc def=request op=read -->
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

Surface-level codes are the shared
[well-known `action.error` codes](../authentication.md#surface-rendering-and-notifications).
They are not EMV 3DS or payment outcomes: a provider-domain timeout or
unavailable method that the handler can safely continue past should normally
result in `action.done`, with the Business and provider recording the domain
outcome server-side. After either notification, the Platform follows the shared
Payment Authentication reconciliation contract.

## Deadline and Fallback

[EMV 3-D Secure Protocol and Core Functions v2.3.1.1](https://www.emvco.com/specifications/emv-3-d-secure-protocol-and-core-functions-specification-6/){ target="_blank" }
requires the 3DS Server to set `threeDSCompInd` to `N` when the 3DS Method does
not complete within five seconds (Req 315). That provider-domain timer begins
when the method is invoked and remains owned by the Business and provider; the
Platform **MUST NOT** derive it from the outer surface's load event.

The Platform applies a bounded outer-surface deadline defined by the handler or
Platform policy, measured from navigation and capped by Checkout `expires_at`.
That deadline controls only how long the Platform keeps the UCP surface mounted;
it does not set `threeDSCompInd` or another provider outcome.

If no valid `action.done` or `action.error` arrives before the outer deadline,
the Platform **MUST** unmount the surface, treat the interaction as timed out,
and follow the non-successful surface reconciliation path. It may unmount sooner
after load failure or a valid terminal notification. The Platform **MUST NOT**
remount the same Action type and `id`; an unchanged occurrence follows the
parent Checkout Actions fallback, handoff, and cancellation rules.

## Security

The common [Payment Authentication security requirements](../authentication.md#security-and-data-handling)
apply. In addition:

- The handler's trust policy **MUST** authorize the initial and redirect origins
  before the Platform loads them.
- The surface **MUST NOT** receive Platform credentials or access Platform
  storage.
- Provider payloads and collected device data **MUST NOT** be copied into the
  Action, notification params, Checkout, or payment instrument.
- `action.done` and `action.error` are advisory surface signals. A later
  Checkout response, based on Business/provider state, remains authoritative.
