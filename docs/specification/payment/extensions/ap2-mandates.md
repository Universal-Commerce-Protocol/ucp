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

# AP2 Mandates Extension

## Overview

The AP2 Mandates extension enables the secure exchange of user intents and
authorizations using **Verifiable Digital Credentials**. It extends the
standard Shopping Service Checkout capability to support the
**[AP2 Protocol](https://ap2-protocol.org/){ target="_blank" }**.

When this capability is negotiated and active, it transforms a standard
checkout session into a cryptographically bound agreement:

* **Businesses** **MUST** embed a cryptographic signature in checkout
    responses, proving the terms (price, line items) are authentic.
* **Platforms** **MUST** provide cryptographically signed proofs (Mandates)
    during the `complete` operation, proving the user explicitly authorized the
    specific checkout state and funds transfer.

**Security Binding:** Once this extension is negotiated in the capability
intersection, the session is **Security Locked**. Neither party may revert to
a standard (unprotected) checkout flow.

![High-level AP2 flow sequence diagram](site:specification/images/ucp-ap2-checkout-flow.png)

### Design

All AP2-specific fields are nested under an `ap2` object in both requests and
responses. This design provides:

* **Schema modularity** — Base checkout schema stays clean; AP2 adds one
    field containing all its data.
* **Consistent canonicalization** — One rule: exclude `ap2` from the business's
    signature computation. Future AP2 fields are automatically handled.
* **Extension coexistence** — Multiple security extensions can coexist
    without namespace collisions.
* **Capability signal** — Presence of `ap2` object clearly indicates AP2
    is active.

## Discovery and Negotiation

This extension follows the standard UCP negotiation protocol. It is activated
only when it appears in the **Capability Intersection** of both the business
and the platform.

### Business Profile Advertisement

Businesses declare support by adding `dev.ucp.common.payment.ap2_mandate` to their
`capabilities` list in `/.well-known/ucp`.

**Business Profile Example:**

<!-- ucp:example schema=profile def=business_schema -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": {},
    "capabilities": {
      "dev.ucp.shopping.checkout": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/checkout",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/checkout.json"
        }
      ],
      "dev.ucp.common.payment.ap2_mandate": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/payment/extensions/ap2-mandates",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/payment_ap2_mandate.json",
          "extends": "dev.ucp.shopping.checkout",
          "config": {
            "vp_formats_supported": {
              "dc+sd-jwt": { }
            }
          }
        }
      ]
    },
    "payment_handlers": {}
  }
}
```

### Platform Profile Advertisement

Platforms declare support in their profile. If the platform is operating under
the trusted platform provider model, the platform **MUST** provide at least one
key in the top-level `keys` array in their profile.

### Activation and Session Locking

1. The platform advertises its profile URI (transport-specific mechanism).
2. The business fetches the profile and computes the intersection.
3. If `dev.ucp.common.payment.ap2_mandate` is present in the intersection:
    * The business **MUST** include `ap2.merchant_authorization` in all
        checkout responses.
    * The business **MUST NOT** accept a `complete_checkout` request that
        lacks `ap2.checkout_mandate`.
    * The platform **MUST** verify the business's signature before presenting
        the checkout to the user.

### Signing Key Requirements

To utilize this extension, a public signing key **MUST** be available for the
business to verify the mandate's signature.

* **Platform Provider Flow:** Key provided in the platform profile's `keys`.
* **User Credential Flow:** Key bound to the digital payment credential.

If a public key cannot be resolved, or if the signature is invalid, the business
**MUST** return an error.

## Cryptographic Requirements

This extension uses the cryptographic primitives defined in the
[Message Signatures](../../signatures.md) specification:

* **Algorithm:** per AP2's Checkout JWT signing rule — AP2 v0.2 requires
  ECDSA (`ES256`/`ES384`/`ES512`); see the note below.
* **Canonicalization:** JCS ([RFC 8785](https://datatracker.ietf.org/doc/html/rfc8785))
* **Key Format:** JWK ([RFC 7517](https://datatracker.ietf.org/doc/html/rfc7517))
* **Key Discovery:** `keys[]` in `/.well-known/ucp` (see
  [Key Discovery](../../overview/index.md#key-discovery))

See [Message Signatures](../../signatures.md) for key format and rotation.

> **Note (algorithm requirement).** AP2 binds the Payment Mandate to the
> Checkout via `hash(checkout_jwt)`; the underlying security property is
> per-session unpredictability of the signed bytes — which UCP's unique
> per-session Checkout `id` supplies structurally. AP2 v0.2 is internally
> inconsistent on how to require this: `specification.md` states an
> algorithm-class rule (non-deterministic only, e.g. ECDSA), while the
> Security and Privacy considerations state an entropy rule satisfied by any
> algorithm given sufficient payload entropy.
> [AP2 #268](https://github.com/google-agentic-commerce/AP2/issues/268)
> tracks converging on the entropy formulation. Follow AP2 for the
> authoritative rule; under the entropy reading a UCP Checkout JWT may be
> signed with any algorithm (including Ed25519), letting one key serve both
> AP2 mandate signing and Web Bot Auth.

### Business Authorization

Businesses **MUST** embed their signature in the checkout response body under
`ap2.merchant_authorization` using **JWS Detached Content** format
([RFC 7515 Appendix F](https://datatracker.ietf.org/doc/html/rfc7515#appendix-F){target="_blank"}).

**Checkout Response with Embedded Signature:**

<!-- ucp:example schema=shopping/checkout op=read -->
```json
{
  "ucp": { ... },
  "id": "chk_abc123",
  "status": "ready_for_complete",
  "currency": "USD",
  "line_items": [ ... ],
  "totals": [ ... ],
  "links": [ ... ],
  "ap2": {
    "merchant_authorization": "eyJhbGciOiJFUzI1NiIsImtpZCI6Im1lcmNoYW50XzIwMjUifQ..<signature>"
  }
}
```

The `merchant_authorization` value is a JWS with detached payload in the format
`<header>..<signature>`. The double dot (`..`) indicates the payload is
transmitted separately (as the checkout body itself).

**JWS Header Claims:**

| Claim | Type   | Required | Description                                        |
| :---- | :----- | :------- | :------------------------------------------------- |
| `alg` | string | Yes      | Signature algorithm accepted by AP2 (e.g. `ES256`) |
| `kid` | string | Yes      | Key ID referencing the business's `keys`           |

**Signature Computation:**

The signature **MUST** cover both the JWS header and the checkout payload. This
prevents algorithm substitution attacks where an attacker modifies the `alg`
claim without invalidating the signature.

```text
sign_checkout(checkout, private_key, kid, alg="ES256"):
    // Extract payload (checkout minus ap2)
    payload = checkout without "ap2" field

    // Canonicalize using JCS (RFC 8785)
    canonical_bytes = jcs_canonicalize(payload)

    // Create protected header
    header = {"alg": alg, "kid": kid}
    encoded_header = base64url_encode(json_encode(header))

    // Sign header + payload per JWS
    signing_input = encoded_header + "." + base64url_encode(canonical_bytes)
    signature = sign(signing_input, private_key, alg)

    // Return detached JWS (header..signature, no payload)
    checkout.ap2.merchant_authorization = encoded_header + ".." + base64url_encode(signature)
    return checkout
```

### Mandate Structure

Mandates are **SD-JWT** credentials with Key Binding (`+kb`). The platform
**MUST** produce two distinct mandate artifacts:

| Mandate              | Presented to                               | UCP Placement                         | Purpose                                              |
| :------------------- | :----------------------------------------- | :------------------------------------ | :--------------------------------------------------- |
| **checkout_mandate** | the business, at `complete`                | `ap2.checkout_mandate`                | Proof bound to checkout terms, protects business     |
| **payment_mandate**  | the Credential Provider, at token issuance | not carried in the `complete` request | Proof bound to payment authorization, protects funds |

The two mandates travel to different parties. The checkout mandate is submitted
to the business, which verifies the terms it committed to. The payment mandate
is presented to the Credential Provider, which verifies it and issues a payment
token in exchange (see
[Step 3](#step-3-payment-mandate-verification-and-token-issuance)). The business
receives that token, not the mandate.

The checkout mandate **MUST** contain the full checkout response including the
`ap2.merchant_authorization` field. This creates a nested cryptographic binding
where the platform's signature covers the business's signature.

**Specification Boundary:** This extension defines *where* mandates are placed
in UCP requests and responses. The mandate credential structure (claims,
selective disclosure, key binding) is defined by the
[AP2 Protocol Specification](https://ap2-protocol.org/specification).

### Canonicalization

All JSON payloads **MUST** be canonicalized using **JSON Canonicalization
Scheme (JCS)** per [RFC 8785](https://datatracker.ietf.org/doc/html/rfc8785).

**Why JCS for Mandates?** UCP request signatures use `Content-Digest` (raw
bytes) without canonicalization — the request is signed and verified
immediately over the same HTTP connection. Mandates are different:

* **Durability** — Mandates are stored as evidence of user consent. They may
    be retrieved and verified days or months later.
* **Cross-system transmission** — Mandates pass through multiple systems
    (platform → business → PSP → card network) that may re-serialize JSON.
* **Reproducibility** — Any party must reconstruct the exact signed bytes
    from the logical JSON content, regardless of serialization differences.

JCS ensures that semantically identical JSON produces byte-identical output,
making signatures reproducible across implementations and time.

Verification and mandate construction operate on the complete checkout JSON,
not a projection of schema-recognized fields; removing any member covered by
`merchant_authorization` changes the JCS payload and invalidates the signature.
This coverage includes `ucp` protocol-namespace members present in the checkout;
only the `ap2` field is excluded as specified below.

**AP2-Specific Rule:** When computing the business's `merchant_authorization`
signature, exclude the `ap2` field entirely. This ensures future AP2 fields
are automatically handled.

## The Mandate Flow

Once the `dev.ucp.common.payment.ap2_mandate` capability is negotiated, the session
is locked into the following flow. Both parties **MUST** follow these steps to
ensure cryptographic integrity; any attempt to bypass these steps or submit
a completion request without mandates **MUST** result in a session failure.

### Step 1: Checkout Creation and Signing

The platform initiates the session. The business returns the `Checkout` object
with `ap2.merchant_authorization` embedded in the response body.

{{ extension_schema_fields('payment_ap2_mandate.json#/$defs/dev.ucp.shopping.checkout', 'payment/extensions/ap2-mandates') }}

**Example Response:**

<!-- ucp:example schema=shopping/checkout op=read -->
```json
{
  "ucp": { ... },
  "id": "chk_abc123",
  "status": "ready_for_complete",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": {"id": "item_123", "title": "Widget", "price": 2500},
      "quantity": 2,
      "totals": [
        {"type": "subtotal", "amount": 5000},
        {"type": "total", "amount": 5000}
      ]
    }
  ],
  "totals": [
    {"type": "subtotal", "amount": 5000},
    {"type": "tax", "amount": 400},
    {"type": "total", "amount": 5400}
  ],
  "links": [ ... ],
  "ap2": {
    "merchant_authorization": "eyJhbGciOiJFUzI1NiIsImtpZCI6Im1lcmNoYW50XzIwMjUifQ..<signature>"
  }
}
```

The platform **MUST** verify the signature:

```text
verify_merchant_authorization(checkout, merchant_profile):
    // Parse detached JWS (header..signature)
    jws = checkout.ap2.merchant_authorization
    [encoded_header, empty, encoded_signature] = jws.split(".")

    // Decode and validate header
    header = json_decode(base64url_decode(encoded_header))
    assert header.alg in ap2_accepted_algorithms  // ES256/ES384/ES512 per AP2 v0.2

    // Reconstruct signed payload (checkout minus ap2)
    payload = checkout without "ap2" field
    canonical_bytes = jcs_canonicalize(payload)

    // Reconstruct signing input (header + payload)
    signing_input = encoded_header + "." + base64url_encode(canonical_bytes)

    // Get business's public key and verify
    public_key = get_key_by_kid(merchant_profile.keys, header.kid)
    return verify(encoded_signature, signing_input, public_key, header.alg)
```

### Step 2: User Consent and Mandate Generation

When the user confirms the purchase, the platform **MUST** facilitate the
generation of cryptographically verifiable mandates.

#### Option 1: Trusted Platform Provider

A trusted platform provider acts on the user's behalf to generate the
mandate credentials. The platform provider **MUST** ensure that mandates
are not created without explicit user consent from trusted, deterministic
channels.

Upon user consent, the platform signs the mandates using their server-side
key. The business trusts the platform's signature implies user consent.

#### Option 2: Digital Payment Credential

In this model the user has a VDC issued from a source trusted by the business
(for example: a digital payment credential issued by a bank or network).

The platform requests a presentation via a protocol like OpenID4VP. The User's
Wallet (or equivalent) processes the request and signs the mandates using the
private key associated with their payment credential.

The business trusts the Credential Issuer (Bank) and verifies the user's Key
Binding (+kb) signature.

### Step 3: Payment Mandate Verification and Token Issuance

The payment mandate is not submitted to the business. It is presented to the
**Credential Provider** — the participant that issues payment tokens for the
instrument the user selected — which verifies it and issues a payment token in
exchange. The business receives that token in Step 4.

Verification happens here, before a token exists, because a token issued
against an invalid mandate is indistinguishable from a valid one by the time it
reaches the business.

**Presentation.** The platform presents the payment mandate to the instrument's
payment handler as a **source credential**, using the handler's existing
tokenization interface (see [Tokenization Guide](../tokenization.md)). No
additional endpoint or request member is introduced; `ap2_payment_mandate` is a
credential type the handler accepts alongside the types it already supports.

<!-- ucp:example skip reason="tokenization API, not UCP payload" -->
```json
POST /tokenize
Content-Type: application/json

{
  "credential": {
    "type": "ap2_payment_mandate",
    "payment_mandate": "eyJhbGciOiJFUzI1NiIsInR5cCI6InZjK3NkLWp3dCJ9...~...",
    "checkout_jwt": "eyJhbGciOiJFUzI1NiIsImtpZCI6Im1lcmNoYW50XzIwMjUifQ.<payload>.<signature>"
  },
  "binding": {
    "type": "dev.ucp.shopping.checkout",
    "id": "chk_abc123"
  },
  "identity": {
    "access_token": "..."
  }
}
```

The `checkout_jwt` is the Checkout JWT for the checkout the mandate authorizes.
It is what makes the correlation check below possible: a Credential Provider
holds neither the checkout response nor `ap2.merchant_authorization`, and cannot
reconstruct the value the mandate was bound to from the token request alone.

**Verification.** Before issuing a token, the Credential Provider **MUST**:

1. **Verify the mandate** — decode and verify the SD-JWT signature, key
    binding, and expiration per the
    [AP2 Protocol Specification](https://ap2-protocol.org/specification).
2. **Verify the merchant signature** — verify `checkout_jwt` as a Compact JWS
    against the business's published key, resolved from the `kid` in its
    protected header.
3. **Correlate the mandate to the checkout** — recompute the checkout hash from
    `checkout_jwt` and confirm it equals the mandate's transaction identifier.
    A mandate that does not correlate authorizes a different purchase.
4. **Confirm the binding** — the binding rules of
    [Tokenization](../tokenization.md) apply unchanged, tying the resulting
    token to this checkout.

A Credential Provider **MUST NOT** issue a token when any of these fail, and
**MUST NOT** issue a token for a mandate it has not verified.

**Issuance.** On success the handler returns a token in its normal form. The
token is an ordinary payment token: opaque to the platform and the business,
and subject to the same generation, lifetime, and single-use policies as any
other token the handler issues. It does not embed the mandate, and no party
downstream is expected to parse it.

**Response:**

<!-- ucp:example skip reason="tokenization API, not UCP payload" -->
```json
{
  "token": "tok_abc123xyz789"
}
```

Handlers that do not implement this extension are unaffected: an
`ap2_payment_mandate` credential is an unrecognized credential type and is
rejected as such.

### Step 4: Submission (`complete_checkout`)

Once the checkout mandate is generated and the payment token has been issued,
the platform submits them in the completion request:

{{ extension_schema_fields('payment_ap2_mandate.json#/$defs/ap2_with_checkout_mandate', 'payment/extensions/ap2-mandates') }}

<!-- ucp:example schema=shopping/checkout op=complete direction=request -->
```json
{
  "payment": {
    "instruments": [
      {
        "id": "instr_1",
        "handler_id": "gpay_1234",
        "type": "card",
        "selected": true,
        "display": {
          "description": "Visa •••• 1234"
        },
        "billing_address": {
          "street_address": "123 Main St",
          "address_locality": "Anytown",
          "address_region": "CA",
          "address_country": "US",
          "postal_code": "12345"
        },
        "credential": {
          "type": "PAYMENT_GATEWAY",
          "token": "examplePaymentMethodToken"
        }
      }
    ]
  },
  "ap2": {
    "checkout_mandate": "eyJhbGciOiJFUzI1NiIsInR5cCI6InZjK3NkLWp3dCJ9..." // The User-Signed SD-JWT+kb / platform provider signed SD-JWT / delegated SD-JWT-KB
  }
}
```

* `ap2.checkout_mandate`: The SD-JWT+kb checkout mandate containing the
    full checkout (with `ap2.merchant_authorization`)
* `payment.instruments[*].credential.token`: The payment token issued in
    Step 3 against the verified payment mandate. The mandate itself is not
    carried here.

If the AP2 extension is negotiated and the selected instrument carries no
credential derived from a verified payment mandate, the business **MUST**
reject the request with `payment_mandate_required`.

## Verification and Processing

### Business Verification

Upon receiving the `complete` request, the business **MUST**:

1. **Enforce Negotiation:** If AP2 was negotiated, reject the request with
    `mandate_required` error code if `ap2.checkout_mandate` is missing.

**Mandate Verification (per AP2 spec):**

1. **Verify Mandate:** Decode and verify the SD-JWT signature, key binding,
    and expiration per the
    [AP2 Protocol Specification](https://ap2-protocol.org/specification).
2. **Extract Embedded Checkout:** Extract the checkout object from the
    verified mandate claims.

**UCP Verification:**

1. **Verify Business Authorization:** Confirm `ap2.merchant_authorization`
    in the embedded checkout is the business's own valid signature:

    ```text
    jws = embedded_checkout.ap2.merchant_authorization
    [encoded_header, _, encoded_signature] = jws.split(".")
    header = json_decode(base64url_decode(encoded_header))

    payload = embedded_checkout without "ap2" field
    signing_input = encoded_header + "." + base64url_encode(jcs_canonicalize(payload))

    my_key = get_key_by_kid(my_keys, header.kid)
    verify(encoded_signature, signing_input, my_key, header.alg)
    ```

2. **Verify Terms Match:** Confirm the embedded checkout terms match the
    current session state (id, totals, line items).

### PSP Verification

Payment mandate verification happens at issuance
([Step 3](#step-3-payment-mandate-verification-and-token-issuance)), not at
processing. By the time the business passes the `token` to their Payment
Handler / PSP, the mandate behind it has already been verified against the
[AP2 Protocol Specification](https://ap2-protocol.org/specification) —
signature, key binding, expiration, and correlation with the checkout.

At processing time the PSP resolves the token to the mandate it was issued
against and processes the payment on that authorization. A token that cannot
be resolved to a verified mandate **MUST NOT** be processed under this
extension.

## Schema

### Business Authorization {: #merchant-authorization }

{{ extension_schema_fields('payment_ap2_mandate.json#/$defs/merchant_authorization', 'payment/extensions/ap2-mandates') }}

### AP2 Checkout Response

The `ap2` object included in checkout responses.

{{ extension_schema_fields('payment_ap2_mandate.json#/$defs/ap2_with_merchant_authorization', 'payment/extensions/ap2-mandates') }}

### Checkout Mandate

{{ extension_schema_fields('payment_ap2_mandate.json#/$defs/checkout_mandate', 'payment/extensions/ap2-mandates') }}

### Payment Mandate

Presented to the Credential Provider at token issuance, not carried in any
UCP request or response.

{{ extension_schema_fields('payment_ap2_mandate.json#/$defs/payment_mandate', 'payment/extensions/ap2-mandates') }}

### AP2 Payment Mandate Credential

The source credential a platform presents to a payment handler in
[Step 3](#step-3-payment-mandate-verification-and-token-issuance). Defined in
`source/schemas/common/types/ap2_payment_mandate_credential.json`; it is a
tokenization input, not a member of any UCP request or response.

| Field             | Type   | Required | Description                                                                 |
| :---------------- | :----- | :------- | :-------------------------------------------------------------------------- |
| `type`            | string | Yes      | Constant `ap2_payment_mandate`                                              |
| `payment_mandate` | string | Yes      | The SD-JWT+kb payment mandate                                               |
| `checkout_jwt`    | string | Yes      | The Checkout JWT for the checkout the mandate authorizes, used to correlate |

### AP2 Complete Request

The `ap2` object included in COMPLETE checkout requests.

{{ extension_schema_fields('payment_ap2_mandate.json#/$defs/ap2_with_checkout_mandate', 'payment/extensions/ap2-mandates') }}

### Error Codes

{{ extension_schema_fields('payment_ap2_mandate.json#/$defs/error_code', 'payment/extensions/ap2-mandates') }}

| Error Code                       | Description                                                                   |
| :------------------------------- | :---------------------------------------------------------------------------- |
| `mandate_required`               | AP2 was negotiated, but the request lacks `ap2.checkout_mandate`.             |
| `agent_missing_key`              | Platform profile lacks a valid `keys` entry.                                  |
| `mandate_invalid_signature`      | The mandate signature cannot be verified.                                     |
| `mandate_expired`                | The mandate `exp` timestamp has passed.                                       |
| `mandate_scope_mismatch`         | The mandate is bound to a different checkout.                                 |
| `merchant_authorization_invalid` | The business authorization signature could not be verified.                   |
| `merchant_authorization_missing` | The checkout response omits `ap2.merchant_authorization`.                     |
| `payment_mandate_required`       | AP2 was negotiated, but the instrument carries no mandate-derived credential. |

Failures during payment mandate verification at issuance are returned by the
payment handler through its own error surface, which is handler-defined; they
do not appear in this list because the business never observes them.
