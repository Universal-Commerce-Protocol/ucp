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

# Digital Delivery Extension

* **Capability Name:** `com.mercadopago.shopping.digital_delivery`
* **Schema:** `https://ucp.dev/schemas/shopping/digital_delivery.json`

## Overview

The Digital Delivery extension lets a Business record **delivered digital /
intangible goods** on the **Order** — gift-card codes, vouchers, top-up PINs,
license keys, and access entitlements (a course, platform/SaaS access, a
download). Unlike an in-session payment artifact, a delivered artifact **outlives
the checkout session**: a code can be redeemed weeks later, and "has it been
redeemed yet?" is a question an agent must be able to ask long after the order
closed. So the record lives on the durable [Order](order.md), not on the
checkout.

The extension deliberately stores **only a durable reference and a way to ask
the issuer** — never the balance, validity, or redemption status. The issuer is
the single source of truth; current state is always obtained by querying it, so
there is no cached copy on the Order for an integrator to trust once it is
stale.

This is a vendor-namespaced capability. The **capability** is
`com.mercadopago.shopping.digital_delivery`; it adds a `digital_delivery` record
to the Order and the shape of its artifacts.

**Key features:**

* Two delivery shapes via `kind`: a bearer **`redeemable_artifact`** (drawn down
  at an issuer) and an **`entitlement`** (a granted, revocable right)
* Durable **issuer reference** plus a defined **lookup** — the Order stores the
  pointer, never the balance
* Redemption — including **partial** redemption — reported through a typed
  issuer lookup response (never stored on the Order), so partial state stays
  expressible and is not collapsed into a boolean
* Inert display data (code / QR image / hosted instructions) under the same
  render/trust rules as other display artifacts

**Dependencies:**

* Order Capability

**Scope (prototype-first).** This extension is the vendor-namespaced,
no-core-change piece: recording the delivered artifact and its redemption
lifecycle on the Order. Reconciling the `digital` `method_type` in
`expectation.json`/`fulfillment.md` and adding a non-postal
`expectation.destination` (phone, email, account) are **core** changes and are
tracked separately as Enhancement Proposals. Discussion:
[#648](https://github.com/Universal-Commerce-Protocol/ucp/discussions/648).

## Discovery

Businesses advertise this extension in their profile, extending the Order
capability:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "com.mercadopago.shopping.digital_delivery": [
        {
          "version": "{{ ucp_version }}",
          "extends": ["dev.ucp.shopping.order"],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/digital-delivery",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/digital_delivery.json"
        }
      ]
    }
  }
}
```

## Schema

When this extension is active, the Order carries a `digital_delivery` array —
one entry per delivered artifact. Each artifact is described below.

### Delivered Artifact

{{ extension_schema_fields('digital_delivery.json#/$defs/artifact', 'digital_delivery') }}

### Issuer Lookup Response

The shape the issuer returns from `lookup.url`. This is the authoritative,
live-queried state — it is never stored on the Order.

{{ extension_schema_fields('digital_delivery.json#/$defs/lookup_response', 'digital_delivery') }}

## State and Trust Contract

The Order carries **a pointer, never the authoritative state.** Redemption state
(a balance that decrements, a validity window that can be revoked) is owned by
the issuer and changes without the order ever being touched — a chargeback, a
ToS termination, the issuer sunsetting a product. Storing it on the order would
turn every integrator into a reader of a stale copy. Implementations MUST honor:

* **`reference` is the durable pointer, not a credential.** It identifies the
  artifact at the issuer for lookup; it is not the balance and not a credential
  to spend. Because it is opaque but not necessarily unguessable, the issuer
  MUST authenticate the caller of `lookup.url`; disclosing state to any holder of
  `reference` is not acceptable unless the extension explicitly says so.
* **`lookup` is required, and it is how you ask.** Every artifact carries a
  `lookup`; current state is obtained *only* by querying the issuer via
  `lookup.url` (an `https:` origin allowlist), keyed by `reference`. The answer
  conforms to the [Issuer Lookup Response](#issuer-lookup-response) shape and MUST
  carry `as_of`, so a Platform can tell a live answer from a stale or cached one.
* **No cached state on the Order.** The Order carries no balance, validity, or
  redemption status — not even as an advisory copy — so there is nothing stale
  to trust. A Platform MUST NOT release funds, grant access, or deny a
  redemption without a fresh issuer answer.
* **Fail closed when the issuer is unreachable.** If a fresh answer cannot be
  obtained, the Platform MUST NOT act (no release, grant, or denial) and MUST NOT
  fall back to a cached copy — the absence of an answer is not a state.
* **Display data is inert.** `code` is display text, `image` is a static image
  only (`data:`/`https:`), and `instructions_url` is the only loadable field
  (`https:` origin allowlist, opened as a plain document).

## Lifecycle

**Delivery is not terminal, and it is not settlement.**

* The presence of `delivered_at` means the buyer received the artifact (the
  code/entitlement is usable). It does **not** mean the artifact was redeemed,
  and it does **not** mean funds settled. This extension records the delivery
  timestamp; it does not define a core Order state named `delivered`.
* **Delivery does not release funds.** A settlement rail MUST NOT wire delivery
  to "release funds": a delivered code may never be redeemed, or may be revoked
  later. The release trigger is agreed by the rail out of band — a redemption
  event, a dispute window expiring, an issuer attestation — and this extension's
  contribution is the `lookup` that makes such a trigger checkable.
* **`redeemable_artifact`** is drawn down at the issuer. Redemption — including
  **partial** redemption — is expressed through the [lookup
  response](#issuer-lookup-response), which MUST be able to report partial state
  (`status: partially_redeemed` with a `remaining` balance), not merely redeemed
  or not, so the history a dispute needs is not collapsed. "How much is left" is
  answered by querying the issuer.
* **`entitlement`** is a granted right with a validity window. It can be revoked
  by the issuer for reasons the order never sees; "is this still valid, until
  when" is answered by the lookup response's `valid_until`.

## Out of Scope

* **Delivery destination and vocabulary.** Capturing a non-postal delivery target
  at checkout (phone for a top-up, email for a voucher, account/device for
  e-SIM), and reconciling the `digital` `method_type` contradiction between
  `expectation.json` and `fulfillment.md`, are **core** changes tracked as
  separate Enhancement Proposals.
* **Recurring/renewable entitlements.** Time-boxed access that renews on a
  schedule (subscriptions) is payment-terms/recurring-billing territory
  (see [#587](https://github.com/Universal-Commerce-Protocol/ucp/issues/587),
  [#629](https://github.com/Universal-Commerce-Protocol/ucp/issues/629)); this
  extension records the entitlement and its validity, not its billing schedule.
