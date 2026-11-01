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

# Nano Payment Instrument

* **Instrument Type:** `nano`
* **Schema:** [`nano_payment_instrument.json`](site:schemas/common/types/nano_payment_instrument.json)

## Introduction

This document defines the handler rules for the `nano` payment instrument that
JSON Schema cannot express: how the binding is verified, the single-use claim on
a settlement block, confirmation before completion, and what follows an amount
mismatch. Any payment handler that lists `{"type": "nano"}` in
`available_instruments` **MUST** follow them.

### Binding and Proof

| Field | Issued by | Role |
| :---- | :-------- | :--- |
| `receive_address` | Business | **Binding.** A Nano account unique to one checkout. |
| `amount_raw` | Business | The exact amount due, in raw (1 XNO = 10^30 raw). |
| `settlement_block` | Platform | **Proof.** The hash of the send block that paid the checkout. |

The binding lives on the business side. `receive_address` and `amount_raw` are
response-only (`ucp_request: "omit"`): the business publishes them on the
instrument in checkout responses, and the platform does not submit them. The
settlement block is proof of payment, not a credential; this instrument does
not use the base `credential` field.

Verification is always against the values the business issued for the checkout,
never against values carried in a request. Otherwise the check is circular: a
payer could send to an account it controls, submit that account as
`receive_address` together with the matching block hash, and both the
destination and amount checks would pass.

---

## Business Integration

### Issuing the Binding

For each checkout that offers the `nano` instrument, the business **MUST**:

1. Issue a `receive_address` that no other checkout uses (e.g., derived at a
    checkout-index path) and record it against the checkout, or be able to
    re-derive it from the checkout session.
2. Fix `amount_raw` for the checkout and record it the same way.
3. Return both on the `nano` instrument in checkout responses.

<!-- ucp:example schema=shopping/checkout extract=$.payment target=$.payment -->
```json
{
  "payment": {
    "instruments": [
      {
        "id": "pi_nano_1",
        "handler_id": "nano_1234",
        "type": "nano",
        "receive_address": "nano_1qno3zgq7qnr3rqbypqbs77wpan7aq3e3ou73go3rqx98eem3tckq1q4hie3",
        "amount_raw": "2500000000000000000000000000000",
        "display": {
          "address_short": "nano_1qno3z...q4hie3"
        }
      }
    ]
  }
}
```

### Processing Payments

Upon receiving Complete Checkout with a `nano` instrument, the business **MUST**:

1. **Validate Handler:** Confirm `instrument.handler_id` matches an advertised
    handler.
2. **Ensure Idempotency:** If the request is a retry of a previous Complete
    Checkout, return the previous result without re-processing.
3. **Reject Mismatched Echoes:** If the instrument carries `receive_address` or
    `amount_raw` and either differs from the value the business issued for this
    checkout, reject the instrument. Neither submitted value is used below.
4. **Look Up the Block:** Fetch `settlement_block` from the business's own Nano
    node or a ledger source it trusts. The block **MUST** be a send whose
    destination (`link`, read as an account) equals the issued `receive_address`.
5. **Check the Amount:** The amount the block sends **MUST** equal the issued
    `amount_raw` exactly. See [Amount Mismatch](#amount-mismatch).
6. **Claim the Block:** Take the single-use claim described below.
7. **Require Confirmation:** Complete only after the block is confirmed. See
    [Confirmation](#confirmation).
8. **Return Response:** Respond with the finalized checkout state.

### Single-Use Claim

A settlement block pays at most one checkout, once.

* The claim key is the pair (network, block hash), where network identifies the
    Nano network the handler settles on (e.g., `mainnet`) and the block hash is
    normalized to upper case before it is compared or stored.
* The claim **MUST** be atomic: taking it and binding it to the checkout happen
    in one operation that fails if the key already exists (for example, an
    insert under a unique constraint inside the transaction that records the
    payment). A check followed by a separate write is not sufficient.
* A second use of a claimed key **MUST** be rejected, whether it arrives on the
    same checkout under a new operation or on a different checkout. A retry of
    the operation that took the claim is not a second use; it returns the
    original result.
* A claim is not released once the block is confirmed.

### Confirmation

Nano blocks are final once confirmed by the network's representatives. The
business **MUST NOT** return `status: completed` until the block is confirmed
(for example, a node reports it as confirmed or cemented). While the block is
known but unconfirmed, the business **MAY** accept the operation as
`complete_in_progress` and complete it after confirmation, following
[Accepted completion](../shopping/checkout/index.md#accepted-completion). If the
block is not confirmed before the checkout's `expires_at`, the business
**MUST** fail the payment and **MUST NOT** complete the checkout.

### Amount Mismatch

The schema requires the block amount to equal `amount_raw`. When it does not,
whether lower or higher:

* The business **MUST** reject the payment and **MUST NOT** complete the
    checkout with that block.
* There is no partial credit. The business **MUST NOT** apply the block toward
    the checkout, **MUST NOT** add several blocks together to reach the amount,
    and **MUST NOT** re-issue `amount_raw` to match what arrived.
* Funds sent to the checkout's address stay with the business; Nano sends
    cannot be reversed by the protocol. Whether and how they are returned is
    business policy, and the business **SHOULD** state it in the error
    `content`.
* The payer is told through a `payment_failed` error in `messages[]`, with
    `path` pointing at `settlement_block` and `content` stating the issued and
    received amounts in raw. Severity is `recoverable`: the platform can submit
    a different block that sends exactly `amount_raw` to the same address.

<!-- ucp:example schema=shopping/checkout extract=$.messages target=$.messages -->
```json
{
  "messages": [
    {
      "type": "error",
      "code": "payment_failed",
      "path": "$.payment.instruments[0].settlement_block",
      "severity": "recoverable",
      "content": "Nano amount mismatch: issued 2500000000000000000000000000000 raw, block sent 2000000000000000000000000000000 raw. The block was not applied to this checkout."
    }
  ]
}
```

### Error Handling

| Condition | Code | Severity |
| :-------- | :--- | :------- |
| Submitted `receive_address` or `amount_raw` differs from the issued value | `payment_failed` | `recoverable` |
| Block not found, not a send, or destination is not the issued address | `payment_failed` | `recoverable` |
| Block amount differs from `amount_raw` | `payment_failed` | `recoverable` |
| Block already claimed | `payment_failed` | `recoverable` |
| Block not confirmed before `expires_at` | `payment_failed` | `unrecoverable` |

---

## Platform Integration

The platform reads `receive_address` and `amount_raw` from the checkout
response, sends exactly `amount_raw` to `receive_address`, and submits the send
block hash as `settlement_block`. It **MUST NOT** substitute its own address or
amount.

<!-- ucp:example schema=shopping/checkout op=complete direction=request -->
```json
POST /checkout-sessions/{id}/complete
Content-Type: application/json

{
  "payment": {
    "instruments": [
      {
        "id": "pi_nano_1",
        "handler_id": "nano_1234",
        "type": "nano",
        "selected": true,
        "settlement_block": "6EE79D2BA2A8995179E4C2E12B10BAA7F828C9AD5D7F2D00E8D5B8A8D5C96C29"
      }
    ]
  }
}
```

---

## Security Considerations

| Requirement | Description |
| :---------- | :---------- |
| **Business-side binding** | Destination and amount **MUST** be verified against the values the business issued for the checkout, never against request data. |
| **Unique address** | A `receive_address` **MUST NOT** be issued to more than one checkout. |
| **Single use** | A (network, block hash) pair **MUST** be claimed atomically and settles at most one checkout. |
| **Confirmation** | A checkout **MUST NOT** complete on an unconfirmed block. |
| **No bearer secret** | The block hash is public proof, not a credential. Knowing it grants nothing beyond what the single-use claim allows. |

---

## References

* **Instrument Schema:** [`nano_payment_instrument.json`](site:schemas/common/types/nano_payment_instrument.json)
* **Payment Handler Guide:** [guide.md](guide.md)
