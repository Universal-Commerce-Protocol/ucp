# Mandate Evaluation and Receipts

- **Namespace:** `com.merchantstamp.mandate-evaluation`
- **Status:** Working Draft
- **Target:** Checkout capability extension
- **Resolves:** #512
- **Proposing vendor:** MerchantStamp (Arnaud Buisine)

This extension is a vendor-namespace addition under the UCP extension process. It MAY be promoted toward core on proven adoption per the "significant usage" rule. Breaking changes are permitted while in Working Draft.

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, MAY, and OPTIONAL are to be interpreted as described in RFC 2119 and RFC 8174.

## 1. Scope

This extension defines **when** AP2 mandate liveness is evaluated relative to the UCP Checkout state machine, and **how** that admission decision is made auditable, when an AP2 mandate's TTL may elapse during checkout completion. It resolves the `complete_in_progress` TTL ambiguity reported in #512.

It does **not** introduce a new lifecycle status, a new error code, a new receipt envelope, a new signature algorithm, or a new key-discovery mechanism. UCP owns the lifecycle semantics; AP2/FIDO owns the receipt construction and verification. This extension adds only the information required to make the admission-time evaluation auditable.

## 2. Conceptual model

"TTL validity" conflates two distinct properties, which this extension separates:

- **Authorization** — *did the buyer permit this charge?* Settled the instant the business admits Complete Checkout against a mandate valid at that instant. A processing delay the buyer did not cause does not unsettle it.
- **Liveness** — *is the grant inside its window right now?* Gates whether a payment **MAY be admitted** into processing. It does not determine whether work already admitted stays authorized.

AP2 reinforces this: an Intent Mandate carries the TTL as a hard constraint, and AP2 provides no in-protocol channel to revoke a mandate before its TTL. The TTL is therefore a pre-agreed bound on *when the grant may be exercised*, not a live withdrawal signal. This is analogous to the PSD2 separation between consent/withdrawal and irrevocability timing: once a payment order has reached the applicable irrevocability point, later withdrawal does not necessarily unwind the admitted action. This extension defines the UCP admission point for mandate-TTL purposes only; it does **not** define legal irrevocability under PSD2.

## 3. Evaluation

The business **MUST** evaluate mandate liveness **exactly once**, when it receives and admits Complete Checkout, against binding transaction data. A mandate valid at that point remains the authorization basis for the checkout throughout processing; later TTL expiry **MUST NOT** reverse the admission decision.

### 3.1 Valid at admission

If the mandate is live at admission, the checkout:

- **MAY** transition to `complete_in_progress`;
- **MUST** run to a terminal state.

Later expiry **MUST NOT** abort or reverse an admitted checkout, nor shorten the settlement window.

### 3.2 Expired at admission

If the mandate has already lapsed at admission, the checkout:

- **MUST NOT** enter `complete_in_progress`;
- **MUST** terminate as `canceled` with the existing `mandate_expired` error.

### 3.3 Invariant

`mandate_expired` **MUST NOT** be emitted because the TTL elapsed *after* admission. It is emitted only as an admission-time terminal outcome, and never after the checkout has entered `complete_in_progress`.

No new lifecycle status is introduced; the extension constrains which transition is taken out of `ready_for_complete`.

## 4. Error semantics

`mandate_expired` already exists in the AP2 Mandates extension ("the mandate `exp` timestamp has passed"). This extension **refines** its UCP lifecycle meaning so it is emitted only as an admission-time terminal outcome. It does not add a new code.

## 5. Receipt outcomes

The extension preserves the AP2 terminal receipt model. The lifecycle outcome is represented as an AP2-aligned Checkout/Payment Receipt:

- admitted and successfully completed → AP2 receipt with `status: Success`;
- expired at admission → AP2 receipt with `status: Error` and `error: mandate_expired`.

No competing envelope or discriminator is introduced.

### 5.1 Placement — extension field on the terminal receipt

For the synchronous path, the mandate-evaluation fields **MUST** be carried as a namespaced extension on the AP2-aligned terminal receipt, under the `com.merchantstamp.mandate-evaluation` key. The merchant signs both the admission decision and the terminal receipt; splitting them into two artifacts buys no verification independence, because there is no second party for a separate attestation to be independent from.

The terminal receipt's `iat` retains its existing meaning — the time the receipt was created. It is **NOT** overloaded to represent the admission decision; `evaluated_at` carries that.

| Field | Description |
| --- | --- |
| `evaluated_at` | The issuer's signed attestation of when mandate liveness was checked (the admission decision anchor). |
| `reference` | The AP2 mandate reference: the hash of the **closed mandate credential**, per AP2's existing definition. It **MUST NOT** be the `checkout_hash` (which hashes the inner `checkout_jwt`, equal to the Payment Mandate `transaction_id`). |
| `checkout_id` | The UCP checkout/session identifier (the flow binding). Distinct from `reference` and never conflated with it. |
| `mandate_exp` | The mandate's `exp`. Lets a verifier that cannot independently resolve the mandate still confirm `evaluated_at` falls inside the window for that specific mandate. |
| `result` | `valid` \| `expired`. |

### 5.2 Separate admission attestation (conditional)

A separately addressable admission attestation is **OPTIONAL** and earns its place only when the admission decision must be resolvable **before the terminal receipt exists** — for example a long-running or asynchronous `complete_in_progress`, or a verifier that must act on admission mid-flight. Where one is used, linkage runs **one way only**: the later terminal receipt points back to the admission attestation, never the reverse.

### 5.3 Binding — by content, not by a forward identifier

The admission decision is bound by **content**: the tuple `reference` + `checkout_id` + `evaluated_at`. The terminal receipt carries that same tuple, so a verifier reconstructs the link by **recomputation** and never needs a `receipt_id` that does not exist at admission time.

`reference` and `checkout_id` are two **independent** identifiers and **MUST NOT** be conflated: `reference` identifies the authorization grant being evaluated (the closed mandate, never the `checkout_hash`), while `checkout_id` scopes the decision to the flow and is what enforces per-checkout exclusivity. A verifier resolves "which grant" from `reference` and "which flow" from `checkout_id`; collapsing them would break both the grant binding and the exclusivity check.

A jwt-hash handle (digest of the canonical signed representation) **MAY** be used for *addressing* a receipt artifact (§6); it is the content tuple that makes the binding **verifiable** rather than only addressable. This extension does **not** add a required receipt `id`.

### 5.4 Required fields (normative)

When the mandate-evaluation extension is present on a receipt:

- `reference` — **REQUIRED**;
- `evaluated_at` — **REQUIRED**;
- `mandate_exp` — **REQUIRED whenever the verifier cannot independently resolve the mandate**; otherwise OPTIONAL;
- `checkout_id` — **REQUIRED** (session binding);
- `result` — **REQUIRED**.

**Timestamp units.** `evaluated_at` and `mandate_exp` **MUST** be **Unix epoch integer seconds**, consistent with AP2 core, where the Checkout Mandate and Checkout Receipt express `iat` / `exp` as Unix epoch timestamps. This keeps the extension fields homogeneous with the surrounding AP2 receipt rather than mixing epoch and RFC 3339 representations.

### 5.5 Meaning of `evaluated_at` (clock semantics)

`evaluated_at` is the issuer's **signed assertion** of when liveness was checked. Co-located with `mandate_exp`, it lets a verifier confirm the admission instant fell inside the mandate window. It does **not**, on its own, anchor that instant against an external clock — the signature proves the issuer asserted the time, not that the time is independently true. A deployment that needs the admission instant non-repudiable **beyond the issuer's assertion** is the same trigger as the separate-attestation case (§5.2), and is the place to add an external timestamp.

## 6. Signing and identification

Receipts use the existing UCP/AP2 Message Signatures cryptographic profile:

- ES256 **REQUIRED**; ES384 and ES512 OPTIONAL.
- JCS (RFC 8785) canonicalization.
- JWK key discovery through `signing_keys[]`.

This applies an existing cryptographic profile; it introduces no new algorithm or key-discovery mechanism, and is distinct from RFC 9421 HTTP Message Signatures (transport-layer).

### 6.1 Digest rules — two cases, kept separate

Receipt addressing and content binding use **different** digest rules. A single rule for both is a footgun; the two cases **MUST** be kept distinct:

1. **Addressing the signed receipt artifact** → SHA-256 over the **exact signed receipt serialization as delivered**, lowercase hex. The signature already fixes the bytes, so there is no canonicalization step and no discretion; this is the jwt-hash handle, and **JCS does NOT apply here.** Because AP2 Mandates documents the JWS *detached* content form for `ap2.merchant_authorization` (`<header>..<signature>`, payload transmitted separately) as well as full compact JWS, the addressed serialization **MUST** be pinned per representation: if the receipt is a full compact JWS, the digest covers the compact JWS bytes; if it uses detached JWS, the profile **MUST** define the detached payload bundle included in the digest, so that a handle never addresses only `header..signature` with an undefined payload. The profile **MUST** publish conformance vectors for both cases before Candidate.
2. **A content-derived digest a verifier must recompute without trusting the signed blob** (e.g. if the binding tuple of §5.3 is ever addressed directly) → **JCS (RFC 8785) first, then SHA-256**, lowercase hex, so it stays independently recomputable and cross-checkable against the `action_ref` conformance vectors.

The mandate `reference` follows whatever AP2 already defines; this extension introduces no new rule for it. Implementations **MUST NOT** apply JCS-then-hash to the signed artifact, nor raw-byte hashing to unsigned content that must be independently recomputable — keeping the two rules separate is what lets jwt-hash addressing (§5.3) and content binding coexist without ambiguity.

## 7. Open items

1. **Conformance vectors for receipt addressing** — the digest rules are pinned in §6.1; the remaining work is publishing the canonical signed-representation test vectors (compact JWS) alongside the `action_ref` set before Candidate.
2. **Validity-window commitment** — the conditions under which `mandate_exp` is treated as the committed window (§5.4) versus resolved from the live mandate, in deployments where the verifier may or may not reach the mandate.
3. **Receipt delivery** — define where the receipt (and, where used, the admission attestation) appears in the UCP response schema.
4. **FIDO push-down** — `evaluated_at` is added here as a use-case extension field; a follow-up issue against the AP2/FIDO receipt construction will propose standardizing it as an optional core field so it does not stay UCP-local.
5. **Capability-query evolution** — preserve future compatibility with DCQL / OpenID4VP advanced query syntax (targeted ~OpenID4VP 1.2 per maintainer) without making it a dependency of this extension.

*Reflecting the current direction of the #515 review (proposed after maintainer/reviewer feedback, pending explicit sign-off):* placement (§5.1, extension field for the synchronous path — @aeoess, @GarethCOliver); identifier binding (§5.3, content tuple, no forward `id` — @aeoess); digest rules (§6.1, two cases kept separate — @aeoess); clock semantics (§5.5, `evaluated_at` as issuer-asserted, not external-clock — @aeoess). The closed-enum `EXPIRED` cancellation receipt (with `effective_from`) is **out of scope** for this extension and belongs to the separate withdrawal/propagation track; for #512 the terminal artifacts are the AP2 receipts (§5).

## 8. Capability discovery

The business advertises only the policy required before Complete Checkout:

| Field | Type | Description |
| --- | --- | --- |
| `mandate_evaluation` | bool | Whether the business applies this extension. |
| `min_remaining_ttl` | ISO 8601 duration | Minimum remaining validity the business expects at admission. |
| `receipt_profile` | string | The supported receipt or admission-attestation profile. |

Future alignment with DCQL / OpenID4VP advanced query syntax is tracked separately (§7, item 5) and is not required by this extension.

## 9. Test plan

Conformance assertions (to be contributed to `Universal-Commerce-Protocol/conformance`):

1. Mandate liveness is evaluated exactly once, at admission of Complete Checkout.
2. A mandate valid at admission permits transition to `complete_in_progress`.
3. Later TTL expiry does not abort or reverse an admitted checkout.
4. A mandate expired at admission prevents entry into `complete_in_progress`.
5. The expired-at-admission outcome terminates as `canceled` with `mandate_expired`.
6. `mandate_expired` is never emitted because TTL elapsed after admission.
7. The admission decision is bound to the closed mandate and the checkout session by the content tuple, and reconstructable by recomputation.
8. The terminal AP2 receipt and any separate admission attestation can be correlated (one-way) and verified without ambiguity.

## 10. Graduation criteria

- **Working Draft** — land under `com.merchantstamp.mandate-evaluation`; breaking changes allowed; reconcile open items (§7); MerchantStamp provides the initial business-side implementation. Independent facilitator-side evidence exists for the freeze-at-admission rule (near-expiry, expired-at-acceptance, long-lived branches); independent implementation of the full extension schema and receipt profile remains a graduation requirement.
- **Candidate** — API surface frozen; conformance tests merged; digest/signed-representation fixed normatively (§6); early-adopter pilots.
- **Stable** — date-versioned; full backward compatibility; considered for promotion into core per the "significant usage" rule.

## Appendix A. Illustrative examples

The following examples illustrate §5. With placement resolved (§5.1), they use the namespaced extension on the AP2-aligned terminal receipt. The `extensions` container name and the omission of a real signature / compact JWT / digest are still illustrative; the field set and their meanings track the normative §5.

### A.1 Valid at admission, completed successfully

```json
{
  "status": "Success",
  "iss": "https://merchant.example",
  "iat": 1781793785,
  "reference": "sha256:4f2d...91ab",
  "order_id": "order_01JY...",
  "extensions": {
    "com.merchantstamp.mandate-evaluation": {
      "checkout_id": "checkout_01JY...",
      "evaluated_at": 1781793730,
      "mandate_exp": 1781793900,
      "result": "valid"
    }
  }
}
```

`iat` (1781793785 = 2026-06-18T14:43:05Z) stays the terminal receipt creation time and falls **after** `evaluated_at` (1781793730 = 2026-06-18T14:42:10Z), which records the earlier point-of-use decision that admitted the checkout into processing. `mandate_exp` (1781793900 = 14:45:00Z) is still in the future at evaluation, so the mandate was live.

### A.2 Expired at admission

```json
{
  "status": "Error",
  "iss": "https://merchant.example",
  "iat": 1781793732,
  "reference": "sha256:4f2d...91ab",
  "error": "mandate_expired",
  "error_description": "The mandate had expired when Complete Checkout was evaluated.",
  "extensions": {
    "com.merchantstamp.mandate-evaluation": {
      "checkout_id": "checkout_01JY...",
      "evaluated_at": 1781793730,
      "mandate_exp": 1781793719,
      "result": "expired"
    }
  }
}
```

Here the checkout never enters `complete_in_progress`; the receipt is the admission-time rejection itself, so `iat` (1781793732 = 14:42:12Z) sits just after `evaluated_at` (1781793730 = 14:42:10Z), while `mandate_exp` (1781793719 = 14:41:59Z) is **before** the evaluation — the mandate had already lapsed at admission. The two timestamps keep distinct meanings.
