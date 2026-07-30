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

# Gift Extension

## Overview

The Gift extension represents a buyer-paid purchase for another person. The
buyer selects and pays for the product, while the recipient is selected and
validated by the Business.

Gift purchases differ from ordinary checkout because the buyer and recipient
are distinct participants. A recipient is not necessarily a fulfillment
destination: the Business may manage recipient selection, recipient acceptance,
and delivery details in its own experience.

The extension exposes only the information needed for an agent or platform to
continue the checkout and address the buyer's selected recipient. It does not
expose a friend graph, contact book, address book, recipient identifier, or
recipient-selection credential.

## Scope

This version extends Checkout only. It supports a buyer who has selected a
product and wants to send it as a gift. The Business may require the buyer to
select a recipient in its own checkout experience before checkout can complete.

This version does not define a recipient-selection API. The Business owns the
recipient selection and stores its result as private Checkout-bound state. The
Platform never submits, stores, or reuses a recipient identifier or selection
credential.

## Data Boundaries

| Data | Owner | UCP visibility |
| --- | --- | --- |
| Recipient display name | Business | Buyer-facing display value |
| Recipient selection state | Business | Checkout status and optional display value only |
| Friend graph, contact details, address | Business | Never exposed by this extension |
| Recipient eligibility and acceptance | Business | Reflected only through normal Checkout state and messages |

The Business remains authoritative for recipient identity and for whether a
recipient is eligible for the selected gift. The Platform MUST NOT infer a
recipient identity from the display value or use it as an authorization
credential.

## Discovery

Businesses advertise Gift support alongside Checkout:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.checkout": [
        {
          "version": "{{ ucp_version }}",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/checkout.json"
        }
      ],
      "dev.ucp.shopping.gift": [
        {
          "version": "{{ ucp_version }}",
          "extends": "dev.ucp.shopping.checkout",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/gift",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/gift.json"
        }
      ]
    }
  }
}
```

Platforms MUST negotiate both Checkout and Gift before sending `gift` data.

## Schema

When this extension is active, Checkout gains an optional top-level `gift`
object. An empty `gift` object is a no-op. A recipient-based gift checkout is
requested only by `gift.recipient_required: true`.

### Gift Object

{{ extension_schema_fields('gift.json#/$defs/gift', 'gift') }}

### Recipient

{{ extension_schema_fields('gift.json#/$defs/recipient', 'gift') }}

### Recipient Display

{{ extension_schema_fields('gift.json#/$defs/recipient_display', 'gift') }}

`recipient_required: true` means that a selected, eligible recipient is a
precondition for Complete Checkout. It does not prescribe the recipient
selection UI: the Business may collect the input in its own experience, or use
an applicable UCP interaction mechanism.

`recipient` is response-only. Its `display.name` is a merchant-approved
buyer-facing name or relationship name, such as `Mom`; it is not necessarily a
legal or account name, verified identity, or authorization credential.

## Checkout Flow

### Start Gift Checkout

The Platform requests a recipient-based gift checkout when the buyer chose a
product but has not yet selected a recipient.

<!-- ucp:example schema=shopping/gift def=gift op=create direction=request extract=$.gift -->
```json
{
  "gift": {
    "recipient_required": true
  }
}
```

If recipient selection is required, the Business uses the ordinary Checkout
handoff flow.

<!-- ucp:example schema=shopping/gift def=gift extract=$.gift -->
```json
{
  "status": "requires_escalation",
  "messages": [
    {
      "type": "error",
      "code": "recipient_selection_required",
      "content": "Select a recipient before completing this gift checkout.",
      "severity": "requires_buyer_input",
      "path": "$.gift"
    }
  ],
  "continue_url": "https://business.example.com/checkout-sessions/chk_123",
  "gift": {
    "recipient_required": true
  }
}
```

The Platform opens `continue_url` for the buyer. The Business stores the
recipient selection and its authorization as private state bound to the
Checkout session. Returning from this experience does not itself prove that a
recipient was selected; the Platform uses Get Checkout to read the
authoritative Checkout status.

### Read a Selected Recipient

After the buyer returns from the Business experience, the Platform uses Get
Checkout to obtain the current checkout. When selection succeeds, the Business
may return its buyer-facing presentation.

<!-- ucp:example schema=shopping/gift def=recipient extract=$.gift.recipient -->
```json
{
  "status": "ready_for_complete",
  "gift": {
    "recipient_required": true,
    "recipient": {
      "display": {
        "name": "Mom"
      }
    }
  }
}
```

The Platform MAY use `display.name` when speaking to the buyer, for example:
"This cake will be sent to Mom." It MUST use the latest Checkout response and
MUST NOT treat the display name as an independently verified identity.

### Update Gift Checkout

For this extension, Update replaces the Platform-writable Gift request state.
To retain recipient-based gifting, the Platform MUST include
`recipient_required: true` again. Omitting `gift` or `recipient_required`
removes Gift request state; the Business MUST clear its private recipient
selection.

<!-- ucp:example schema=shopping/gift def=gift op=update direction=request extract=$.gift -->
```json
{
  "gift": {
    "recipient_required": true
  }
}
```

When the request retains Gift state, the Business MUST atomically revalidate an
existing recipient selection against the resulting Checkout and current
authorization. It MAY retain a valid selection; otherwise it MUST clear the
selection and return the normal `requires_escalation` handoff flow. The
Platform MUST NOT send recipient data back to the Business.

`gift` data is omitted from Complete Checkout requests. Immediately before
accepting Complete Checkout, the Business MUST atomically verify that a
recipient selection exists, remains authorized and eligible, and matches the
current Checkout. If that verification fails, the Business MUST produce no
payment or order effect and MUST return the appropriate Checkout state. Before
returning `complete_in_progress`, the Business MUST freeze or reserve the
recipient state needed to make completion unambiguous.

## Privacy and Security

The Business MUST NOT expose raw friend lists, contact details, address-book
entries, delivery addresses, or an identifier or credential that a Platform can
resolve outside the Business. A Platform MUST NOT use `recipient.display.name`
to construct a cross-Business recipient profile or to infer information beyond
the display value the Business returned.

The Business MUST clear a recipient selection when Gift request state is
removed, the Checkout is canceled or expires, the buyer selects a different
recipient, or the Business revokes the selection. Selection MUST NOT outlive
the Checkout's `expires_at`.

Missing, expired, revoked, unauthorized, or ineligible selection
normally requires the same generic recipient-selection handoff: a
`requires_escalation` Checkout with a `requires_buyer_input` message and
`continue_url`. The Business MUST NOT expose distinguishable recipient errors
that let a Platform enumerate recipient state.

## Out of Scope

This version does not define:

* recipient-first catalog search or cart flows,
* raw recipient identity, contact data, or selection credentials,
* multiple recipients in one checkout,
* gift messages, card artwork, recipient acceptance, or scheduled gifting, or
* recipient data in Order resources or events.
