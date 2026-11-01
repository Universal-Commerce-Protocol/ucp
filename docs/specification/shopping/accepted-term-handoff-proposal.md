<!--
   Copyright 2026 UCP Authors

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
   implied. See the License for the specific language governing
   permissions and limitations under the License.
-->

# Accepted commercial-term handoff — architectural review note

!!! warning "Proposal-stage document — not an approved UCP specification"
    This note accompanies [Enhancement Proposal #845](https://github.com/Universal-Commerce-Protocol/ucp/issues/845).
    It is **non-normative** and requests an architectural decision. It does not
    create a UCP capability, define a data contract, modify existing Cart/Checkout
    behavior, or require an implementation. It must not be treated as an
    accepted specification or published as an active capability without the
    Shopping Domain Technical Council's decision.

## Decision requested

When commercially accepted or awarded terms are formed outside UCP Cart/Checkout,
does UCP need **a minimum shared handoff contract** even if individual verticals
carry those terms differently?

- **Option B — domain-specific contracts:** each extension independently
  defines identity, authority, commitment, rejection, retry and lifetime semantics.
- **Option C — shared semantics with domain-specific carriers:** UCP defines a
  small set of observable *outcomes and invariants* for handoff; each extension
  determines its own fields, artifact types, and operations.

**Recommendation for review: Option C**, limited to the observable properties
below. This is a requested decision, not a current UCP requirement.

The relevant boundary is:

`external term formation → accepted/awarded revision → Business evaluation and binding → subsequent transaction lifecycle`

The receiving Business remains authoritative for UCP Cart/Checkout state.
Neither the existence of an external quote nor buyer acceptance automatically
authorizes its pricing or other material commercial effects.

## Proposed minimum semantic properties

| Review question | Candidate shared property under C | What remains extension-specific |
| --- | --- | --- |
| Artifact identity | A binding outcome can be related to the particular commercially authorized revision, not an unspecified latest version. | Artifact shape, identifiers and origin lookup. |
| Commercial authority and scope | The parties must not treat issuer identity, buyer acceptance or proof of possession alone as unrestricted authority. Binding cannot silently expand the authorized scope. | Who can authorize which terms; scope granularity and proof mechanism. |
| Commitment type | Recognized-but-revalidatable terms and a firm Business commitment need distinguishable behavior when their consequences differ. | Lifecycle states, withdrawal rights, invalidation policy and terms of validity. |
| Rejection vs invalidity | A recognized revision the Business cannot honor should not be indistinguishable from an unknown, altered, stale or unauthorized artifact. Neither is successful binding. | Concrete error codes and recoverable guidance. |
| Commercial basis | Binding must not silently substitute materially different commercial terms; later authorized changes should not rewrite the historical binding basis without an explicit rule. | Price, cancellation, entitlement, taxes, quantity and adjustment representations. |
| Retries and finality | The commercial revision, binding attempt, authoritative binding result and downstream execution are different concepts; replay must not duplicate or silently reinterpret effects. | Attempt IDs, persistence, partial-binding policy and transport mechanics. |
| Lifetime | Issuance expiry, acceptance, withdrawal, binding and post-binding transaction lifetime are not necessarily one clock. The applicable authorized rules determine outcomes. | Expiry triggers, obligation duration and post-bind policy. |

These are possible *observable* interoperability guarantees, not proposed
cross-domain JSON members, response-code enums, new endpoints or a universal
commercial-term object.

## Two decision-focused negative cases

These cases are tested in the separate
[public review harness](https://github.com/arjun2075/ucp-term-handoff/blob/main/tests/test_architecture_decision_845.py).
The harness checks consistency of a proposed model; it does not execute UCP
conformance tests or assert that present UCP implementations support this flow.

### Case A — authentic, recognized quotation fails Business revalidation

A Business-issued quotation is accepted under a rule explicitly permitting
revalidation at binding. The artifact is authentic, correctly scoped,
unexpired and on the expected revision. The Business can no longer honor its
commercial terms at binding time.

**Question for the Council:** Must a receiving Platform be able to
distinguish this *recognized-but-not-bindable* result from an invalid artifact
and from successful binding, regardless of the quote carrier?

**Negative controls:** A modified commercial basis is not equivalent to a
recognized rejection. A separately authorized firm commitment must not be
invalidated merely because an unrelated revalidation condition would fail.

### Case B — acceptance, first binding and post-binding have different clocks

- **Pre-binding control:** a buyer accepts a quotation before its recorded
  issuance expiry, but the first attempted binding occurs after expiry. The
  candidate harness rejects that attempt under its configured binding-validity
  policy. This does **not** assert that all domains must use issuance expiry as
  their binding deadline: an explicit accepted commitment rule may differ.
- **Post-binding control:** the Business successfully binds before issuance
  expiry; a later conditional-release check takes place after issuance expiry
  but before the separately authorized transaction lifetime ends. The
  candidate harness applies that post-binding policy, records a failed release,
  preserves bound terms and does not execute. It does **not** represent
  successful Checkout completion.

**Question for the Council:** Should a cross-carrier contract at minimum
distinguish acceptance from binding and binding from execution, and require
the relevant lifetime rule to be explicit?

## Relationship to existing work

- [EP #845](https://github.com/Universal-Commerce-Protocol/ucp/issues/845)
  is the originating architectural proposal for this review.
- [Discussion #812](https://github.com/Universal-Commerce-Protocol/ucp/discussions/812)
  reports a separate, durable Shopware B2B quotation workflow and its handoff
  boundary; it does not establish adoption of this proposal.
- [EP #929](https://github.com/Universal-Commerce-Protocol/ucp/issues/929)
  and [draft PR #930](https://github.com/Universal-Commerce-Protocol/ucp/pull/930)
  are independently authored work on a *price-only quote extension*. They
  reference #845 as related architectural context and may become one
  domain-specific carrier; this document neither claims authorship of #929
  nor asks to block its independent progress.
- [AirShelf's feedback on #929](https://github.com/Universal-Commerce-Protocol/ucp/issues/929#issuecomment-6554965470)
  reports an internal test/demo quote path with **no separate acceptance
  state**, not a deployed implementation of #845 or a reproduction of Case A.
- [Lodging EP #991](https://github.com/Universal-Commerce-Protocol/ucp/issues/991)
  is an adjacent example where cancellation policy can change independently
  of price; it does not itself validate the #845 contract.

## Scope and requested review

This review does **not** standardize negotiation, RFQ, price calculation,
quote issuance, a common `accepted_id`, payment settlement, universal identity,
a partial-binding requirement, a new UCP operation or a shared wire schema.

Before a specification implementation is attempted, the Shopping DTC is asked to:

1. Select **B** or **C**, or explicitly reject shared placement.
2. If **C**, confirm which (if any) of the proposed minimum properties are
   cross-carrier interoperability guarantees, and where normative text belongs.
3. Identify a first domain-specific carrier and expected negative conformance
   cases only after that decision.
4. Record scope, owner and review milestone on [#845](https://github.com/Universal-Commerce-Protocol/ucp/issues/845).

Until that happens, no schema, SDK, core protocol behavior or conformance suite
is modified by this note.
