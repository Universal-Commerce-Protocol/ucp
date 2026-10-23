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

# Offer Extension

The Offer extension lets a Business propose a complete Cart transition bound to
the exact Cart state it was generated against:

```text
dev.ucp.shopping.offer
```

An Offer states: *given this exact Cart state, the Business proposes this
resulting Cart state.* Binding each proposal to its source state means a
proposal cannot be silently applied to a Cart that has since changed.

## Offer Action Type

An outstanding Offer — one the Business is currently proposing and the Platform
has not yet applied — is surfaced as an
[Action](../../overview/index.md#actions) under the type key
`dev.ucp.shopping.offer`. The extension declares this Action type and its
`config`; it adds no generic Action machinery of its own.

An outstanding Offer Action gates exactly one effect: applying that exact
proposed Cart transition. Per
[Cart — Actions](../cart/index.md#actions), the Business **MUST NOT** treat an
outstanding Offer Action as a reason to reject an unrelated Cart operation. The
Platform **MAY** continue to add, remove, and update items while an Offer Action
is outstanding.

### Runtime Shape

<!-- ucp:example schema=shopping/offer def=dev.ucp.shopping.cart extract=$.actions target=$.actions op=read -->
```json
{
  "actions": {
    "dev.ucp.shopping.offer": [
      {
        "id": "act_offer_charger_s0",
        "config": {
          "offer_id": "offer_travel_charger",
          "revision": "1",
          "applies_to": {
            "cart_id": "cart_123",
            "state_ref": "s0"
          },
          "expires_at": "2026-09-26T00:00:00Z",
          "proposed_update": {
            "line_items": [
              {
                "id": "li_laptop",
                "item": {
                  "id": "var_laptop",
                  "title": "Laptop",
                  "price": 129900
                },
                "quantity": 1,
                "totals": [
                  { "type": "subtotal", "amount": 129900 },
                  { "type": "total", "amount": 129900 }
                ]
              },
              {
                "id": "li_charger",
                "item": {
                  "id": "var_charger",
                  "title": "Travel Charger",
                  "price": 1999
                },
                "quantity": 1,
                "totals": [
                  { "type": "subtotal", "amount": 1999 },
                  { "type": "total", "amount": 1999 }
                ]
              }
            ]
          },
          "impact": {
            "total_delta": 1999
          },
          "presentation": {
            "title": "Add a travel charger"
          }
        }
      }
    ]
  }
}
```

### Config Fields

The config shape is defined by the
[Offer extension schema](site:schemas/shopping/offer.json).

| Field | Type | Required | Notes |
| :---- | :--- | :------- | :---- |
| `offer_id` | string | ✓ | Business-assigned Offer identifier, stable across revisions. Distinct from the Action instance's own `id`. |
| `revision` | string | ✓ | Immutable revision. `offer_id` + `revision` is the exact operational identity of the proposal. |
| `applies_to` | object | ✓ | The exact Cart state this Offer was generated against (`cart_id`, `state_ref`). |
| `expires_at` | string | ✓ | RFC 3339 expiry. Invalidates the Offer independently of source-state staleness. |
| `proposed_update` | object | ✓ | The proposed resulting Cart state. `line_items` uses existing Cart full-replacement semantics. |
| `impact` | object | ✓ | Structured preview of the change for agent evaluation. Not authoritative. |
| `presentation` | object | | Non-authoritative display copy. Changing it does not change what the Offer proposes. |

### Identity

Action identity and Offer identity are distinct concepts and the Business
**MUST NOT** collapse them:

- the Action instance's `id` identifies this outstanding occurrence, and follows
  the common [Action identity rules](../../overview/index.md#actions): it stays
  stable while the same work remains outstanding, replacement work gets a new
  `id`, and an `id` is not reused during the Cart's lifetime;
- `config.offer_id` + `config.revision` identifies the immutable proposal
  artifact itself, and remains recoverable from the Action config so the
  Platform can apply the Offer by reference.

Any change to decision-relevant terms **MUST** be issued as a new `revision`,
which is necessarily replacement work: the Business surfaces it as a new Action
instance with a new Action `id`.

## Applying an Offer

The Platform applies an Offer by reference with the `apply_offer` operation,
passing the Cart id together with `config.offer_id` and `config.revision`. The
Platform **MUST NOT** resubmit the proposed `line_items`; the Business applies
the stored proposal.

Concrete processing belongs to the declaring extension, so the Offer extension
retains this narrow reference-based operation. The common Actions contract
defines no generic executor, and this extension introduces none.

### Validity

An Offer is applicable only while all of the following hold. The conditions are
conjunctive: a stale but unexpired Offer is not applicable.

1. the bound source state still matches the current Cart state exactly;
2. the Offer has not expired; and
3. the Business can still honor the exact stored revision.

For a new logical application attempt that fails any condition, the Business
**MUST** reject the request without mutating the Cart and **MUST** return a
`recoverable` error Message. When the Offer is still outstanding, that Message's
`path` **MUST** select the exact Action occurrence, per
[Actions](../../overview/index.md#actions). These outcomes remain
machine-distinct and **MUST NOT** be collapsed into a single generic
invalid-offer outcome:

| `messages[].code` | Condition |
| :---------------- | :-------- |
| `offer_source_state_mismatch` | The Cart no longer matches `applies_to.state_ref`. |
| `offer_expired` | The Offer is past `expires_at`. |
| `offer_unavailable` | The Business can no longer honor the exact stored revision. |

The Business determines whether the source state still matches using exact
token-value equality on `applies_to.state_ref`. Implementations **MUST NOT**
parse, normalize, canonicalize, or semantically compare `state_ref` values.

### Idempotency

Offer application follows the existing
[Replay Protection](../../signatures.md#replay-protection) rules. An idempotent
replay of the same application request returns the cached original result
without re-executing the Offer or re-evaluating `state_ref`. Any new logical
application attempt **MUST** be evaluated against the Cart's current state.

### Authoritative Result

The Cart returned by the Business after application is authoritative. Neither
the Action's presence, nor `impact`, nor successful transport substitutes for
that subsequent Business-authoritative Cart.

## Authorization Boundary

Applying an Offer establishes only the resulting commerce-state mutation.
Successful Offer application **MUST NOT**, by itself, be interpreted as
authorization to complete Checkout, execute a payment, move funds, or otherwise
authorize a consequential transaction. Any applicable authorization mechanism
evaluates the resulting state independently.

## Lifecycle

Offer Actions follow the common Action lifecycle. Given a Cart at state `S0`:

**Outstanding.** Offers A and B, both bound to `S0`, appear as two instances
under `dev.ucp.shopping.offer`. Their presence does not prevent unrelated Cart
operations.

**Unrelated mutation.** The Platform adds an item and the Cart becomes `S1`.
Offers A and B are bound to `S0` and are no longer valid outstanding work. A
subsequent authoritative Business response **MUST NOT** continue to advertise
them as outstanding Offer Actions. A direct attempt to apply the stale stored
reference still fails with `offer_source_state_mismatch`.

**Replacement.** If the Business wants to make an equivalent proposal against
`S1`, it issues replacement work: a new `revision` bound to `S1`, surfaced as a
new Action instance with a new Action `id`. The Business **MUST NOT** silently
rebind an existing Offer revision from `S0` to `S1`.

**Application.** Applying Offer A succeeds and the Cart transitions. Offer A
**MUST** cease to appear as an outstanding Action. Because the Cart state has
changed, sibling Offer B — bound to the previous state — is likewise stale and
**MUST NOT** continue to appear as outstanding.

**Provenance.** Actions carry no resolved or completed state, so an applied
Offer is never represented as an Action. Where the Business retains provenance,
it does so in extension-owned Cart state under `offers.applied`, which records
which exact Offer revision caused the transition:

<!-- ucp:example schema=shopping/offer def=dev.ucp.shopping.cart extract=$.offers target=$.offers op=read -->
```json
{
  "offers": {
    "applied": [
      {
        "id": "offer_travel_charger",
        "revision": "1",
        "affected_line_item_ids": ["li_charger"]
      }
    ]
  }
}
```

The Business **MUST NOT** use `actions` as an event log.
