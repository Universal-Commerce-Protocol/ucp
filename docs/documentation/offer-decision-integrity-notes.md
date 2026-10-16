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

# Offer decision-integrity notes (non-normative)

**Status: non-normative conformance-evidence note, not a specification change.** Nothing
on this page is a schema, a protocol requirement, or an adopted UCP capability. It records
two narrow, independently-reproducible observations surfaced while building an executable
prototype against [#738](https://github.com/Universal-Commerce-Protocol/ucp/issues/738)
and [#724](https://github.com/Universal-Commerce-Protocol/ucp/discussions/724), offered to
maintainers as evidence to use or discard. No Tech Council review or Enhancement Proposal
has been sought for this page, because it proposes no schema or behavior change — see
`CONTRIBUTING.md`'s "Significant Change" criteria, none of which this page triggers.

A full executable prototype (state-bound Offer apply semantics, a canonical digest, and
conformance vectors) accompanies this note at
<https://github.com/arjun2075/ucp-offer-v0>, under its own Apache-2.0 license, independent
of and not merged into this repository.

## 1. A digest limited to today's sketched fields can under-bind commercial provenance

If an Offer's evidence digest is computed only over the fields currently sketched in
discussion of #738 (something like `applies_to`, `proposed_update`, `impact`,
`expires_at`), two Offers that are commercially identical in price and line items but
differ only in *who proposed them and why* — e.g. ordinary merchandising vs. a paid or
sponsored placement — produce the same digest. A buyer-side policy that would treat those
two cases differently has no way to detect the difference from the digest alone.

This is not a defect in anything shipped today — no Offer digest is normative yet in this
repository. It is a generalizable hazard worth recording before a digest profile is
finalized: extending an Offer-like shape with commercial-provenance data without also
extending whatever digest subject accompanies it reproduces this problem. To name it
precisely: this is **digest-subject underbinding** — the digest's *subject* (the fields
selected to be hashed) omits a decision-relevant field, so two objects differing only
there produce identical subjects and therefore identical digests. This is not a
cryptographic hash collision; the hash function itself is not implicated.

See `example-offers/provenance-underbinding.json` (alongside this note) for two minimal,
illustrative Offer-shaped objects that are commercially identical except for an
illustrative `provenance` field, to make the shape of the observation concrete.

## 2. "Applied" and "committed" are easy to conflate in an implementation

A merchant Offer successfully applied to a Cart is not automatically the same fact as that
Offer's effect surviving into a final, authorized Checkout. Three cases an implementation
can get wrong if it isn't careful:

- the offered line is removed from the cart before checkout,
- the buyer independently reprices or replaces the same line item through an ordinary cart
  update, without re-applying the Offer, and
- the buyer happens to choose the same item the Offer proposed, without ever applying the
  Offer at all.

None of these should be reported as a committed Offer application, and causation should
never be inferred from item/id equality alone — only from an explicit record of how a line
arrived in the cart. This is adjacent to the Cart-to-Checkout projection question raised in
[#788](https://github.com/Universal-Commerce-Protocol/ucp/issues/788).

## What this note does not claim

- No specific digest-subject field list is proposed here as normative.
- No claim is made that UCP maintainers have adopted, endorsed, or agreed to either
  observation above.
- No schema under `source/` is touched by this note or by the linked prototype's
  interaction with this repository.
