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

> [!NOTE]
> This page is an exploratory draft for review. It sketches how UCP Shopping
> could model recipient-based gifting flows before a final schema is proposed.

## Overview

In a normal shopping flow, the buyer purchases products for themselves. In a
gift shopping flow, the buyer purchases products for another recipient.

Gift flows do not require one fixed ordering. A buyer may select the recipient
before product selection, or may choose products first and select the recipient
later. The minimal protocol difference is that checkout may require recipient
selection before the purchase can be completed. A business may need to validate
gift intent, the selected recipient, whether the product can be gifted, policy
restrictions, and available checkout paths before the purchase can be completed.

This draft explores a common UCP Shopping extension:

```text
dev.ucp.shopping.gift
```

The capability is intended to model a general recipient-based gifting flow
rather than a vendor-specific API.

## Goals

* Model gift intent across the shopping flow.
* Support recipient selection before or after product selection.
* Allow business-hosted recipient selection using the business's own user
  experience and privacy controls.
* Represent selected recipients with opaque, business-scoped tokens.
* Allow selected recipient state to carry forward into checkout.
* Avoid exposing raw friend lists, address books, social graph data, or stable
  recipient identifiers to platforms or agents.
* Allow checkout-time validation of recipient and product eligibility.

## Non-goals

* Standardizing any specific business's friend graph, contact book, address
  book, or social graph.
* Exposing raw recipient identifiers to platforms or agents.
* Defining a universal contact-book protocol.
* Standardizing gift-card artwork or business-specific message card formats.
* Standardizing payment token exchange.

## Discovery

This draft treats Checkout as the minimal surface for gift support. Businesses
may also need broader gift-aware surfaces in the future, but this draft leaves
them out of scope.

The `spec` and `schema` URLs below are provisional until a normative schema is
proposed.

<!-- ucp:example skip reason="exploratory gift extension example without final schema" -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.checkout": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/checkout",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/checkout.json"
        }
      ],
      "dev.ucp.shopping.gift": [
        {
          "version": "2026-06-10",
          "extends": "dev.ucp.shopping.checkout",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/gift",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/gift.json"
        }
      ]
    }
  }
}
```

## Recipient Selection

Some gift shopping flows require the buyer to select who will receive the
purchase before the purchase can proceed. Recipient selection can happen before
product selection, after product selection, or during checkout.

The business MAY provide a business-hosted recipient picker. This lets the user
select a recipient using the business's native experience and privacy controls
without exposing the underlying friend list, address book, or social graph to
the platform.

The selected recipient is represented by an opaque selection token. The token is
scoped to the business and gift shopping context. The platform MUST NOT infer
raw recipient identity from the token.

The field names below are provisional. A future schema would likely add a
`gift` object to checkout resources. If UCP later standardizes pre-checkout gift
context, the same recipient state could be reused there. This follows the
pattern used by other extensions that add top-level fields, such as `discounts`,
`fulfillment`, and `loyalty`.

## Selection Order

The extension should not require product selection to happen before recipient
selection.

### Recipient Before Product

When the buyer selects a recipient first, the business stores that selection and
returns opaque recipient state before any line item exists. The platform can
carry that state into a later checkout request. A business may also use the
selected recipient context in its own hosted surfaces before checkout, but that
behavior is outside this checkout-focused draft.

<!-- ucp:example skip reason="exploratory gift context example without final schema" -->
```json
{
  "gift": {
    "intent": "gift",
    "recipient_selection": {
      "status": "completed",
      "mode": "business_hosted",
      "token": "opaque_recipient_selection_token"
    }
  }
}
```

The same recipient state can then be carried into checkout. Platforms should
treat it as a business-scoped context token, not as direct recipient data.

### Product Before Recipient

When the buyer selects products first, checkout can indicate that recipient
selection is still required. This draft uses the existing `continue_url` handoff
model for business-hosted recipient selection, and uses the gift payload to
explain why handoff is required.

<!-- ucp:example skip reason="exploratory recipient selection handoff example without final schema" -->
```json
{
  "status": "requires_escalation",
  "messages": [
    {
      "severity": "requires_buyer_input",
      "text": "Recipient selection is required before checkout can continue."
    }
  ],
  "continue_url": "https://example.com/ucp/recipient-picker?session_id=cs_123",
  "gift": {
    "intent": "gift",
    "recipient_selection": {
      "status": "required",
      "mode": "business_hosted"
    }
  }
}
```

After the user completes the hosted recipient picker, the business can store the
selected recipient on the gift context. Checkout can then be retried or resumed
with an opaque selection token. The exact return flow is still an open design
point: the token could be reflected in the resumed checkout state, submitted by
the business after the hosted flow completes, or carried through another UCP
return mechanism if one is standardized.

<!-- ucp:example skip reason="exploratory recipient selection completion example without final schema" -->
```json
{
  "gift": {
    "intent": "gift",
    "recipient_selection": {
      "status": "completed",
      "mode": "business_hosted",
      "token": "opaque_recipient_selection_token",
      "display": {
        "label": "Mom"
      }
    }
  }
}
```

## Checkout

The platform includes gift context when creating or updating checkout.

<!-- ucp:example skip reason="exploratory checkout example without final schema" -->
```json
{
  "line_items": [
    {
      "item": {
        "id": "prod_123"
      },
      "quantity": 1
    }
  ],
  "gift": {
    "intent": "gift",
    "recipient_selection": {
      "status": "completed",
      "token": "opaque_recipient_selection_token"
    },
    "message": {
      "text": "Happy birthday!"
    }
  }
}
```

The business validates the gift context before checkout completion.
Validation can include:

* buyer identity,
* recipient selection token validity,
* whether the product can be gifted,
* recipient eligibility,
* policy restrictions,
* gift message validity, and
* checkout or payment availability for the selected gifting flow.

If validation fails, the business returns checkout errors using the normal UCP
error model.

## Privacy

Platforms and agents should not receive raw friend lists, address books, social
graph data, or stable recipient identifiers unless a business explicitly defines
and negotiates such behavior.

The recommended initial model is business-hosted selection with an opaque token.
This lets the business enforce its privacy model and abuse-prevention policies
while still allowing an agent-mediated checkout flow.

## Open Questions

* Should v1 remain checkout-only?
* Is `continue_url` sufficient for product-before-recipient flows, and does UCP
  need a more explicit initiation or return contract for recipient-before-product
  flows?
* Which parts of recipient eligibility should be visible to platforms, and which
  should remain business-private?
