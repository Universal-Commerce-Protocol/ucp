# AP2 Mandates Extension

## Overview

The AP2 Mandates extension enables the secure exchange of user intents and authorizations using **Verifiable Digital Credentials**. It extends the standard Shopping Service Checkout capability to support the **[AP2 Protocol](https://ap2-protocol.org/)**.

When this capability is negotiated and active, it transforms a standard checkout session into a cryptographically bound agreement:

- **Businesses** **MUST** embed a cryptographic signature in checkout responses, proving the terms (price, line items) are authentic.
- **Platforms** **MUST** provide cryptographically signed proofs (Mandates) during the `complete` operation, proving the user explicitly authorized the specific checkout state and funds transfer.

**Security Binding:** Once this extension is negotiated in the capability intersection, the session is **Security Locked**. Neither party may revert to a standard (unprotected) checkout flow.

### Design

All AP2-specific fields are nested under an `ap2` object in both requests and responses. This design provides:

- **Schema modularity** — Base checkout schema stays clean; AP2 adds one field containing all its data.
- **Consistent canonicalization** — One rule: exclude `ap2` from the business's signature computation. Future AP2 fields are automatically handled.
- **Extension coexistence** — Multiple security extensions can coexist without namespace collisions.
- **Capability signal** — Presence of `ap2` object clearly indicates AP2 is active.

## Discovery & Negotiation

This extension follows the standard UCP negotiation protocol. It is activated only when it appears in the **Capability Intersection** of both the business and the platform.

### Business Profile Advertisement

Businesses declare support by adding `dev.ucp.shopping.ap2_mandate` to their `capabilities` list in `/.well-known/ucp`.

**Business Profile Example:**

```json
{
  "capabilities": {
    "dev.ucp.shopping.checkout": [
      {
        "version": "2026-01-11",
        "spec": "https://ucp.dev/specification/checkout",
        "schema": "https://ucp.dev/schemas/shopping/checkout.json"
      }
    ],
    "dev.ucp.shopping.ap2_mandate": [
      {
        "version": "2026-01-11",
        "spec": "https://ucp.dev/specification/ap2-mandates",
        "schema": "https://ucp.dev/schemas/shopping/ap2_mandate.json",
        "extends": "dev.ucp.shopping.checkout",
        "config": {
          "vp_formats_supported": {
            "dc+sd-jwt": { }
          }
        }
      }
    ]
  }
}
```

### Platform Profile Advertisement

Platforms declare support in their profile. If the platform is operating under the trusted platform provider model, the platform **MUST** provide at least one key in the top-level `signing_keys` array in their profile.

### Activation and Session Locking

1. The platform advertises its profile URI (transport-specific mechanism).
1. The business fetches the profile and computes the intersection.
1. If `dev.ucp.shopping.ap2_mandate` is present in the intersection:
   - The business **MUST** include `ap2.merchant_authorization` in all checkout responses.
   - The business **MUST NOT** accept a `complete_checkout` request that lacks `ap2.checkout_mandate`.
   - The platform **MUST** verify the business's signature before presenting the checkout to the user.

### Signing Key Requirements

To utilize this extension, a public signing key **MUST** be available for the business to verify the mandate's signature.

- **Platform Provider Flow:** Key provided in the platform profile's `signing_keys`.
- **User Credential Flow:** Key bound to the digital payment credential.

If a public key cannot be resolved, or if the signature is invalid, the business **MUST** return an error.

## Cryptographic Requirements

### Signature Algorithm

All signatures **MUST** use one of the following algorithms:

| Algorithm | Description                                           |
| --------- | ----------------------------------------------------- |
| `ES256`   | ECDSA using P-256 curve and SHA-256 (**RECOMMENDED**) |
| `ES384`   | ECDSA using P-384 curve and SHA-384                   |
| `ES512`   | ECDSA using P-521 curve and SHA-512                   |

### Business Authorization

Businesses **MUST** embed their signature in the checkout response body under `ap2.merchant_authorization` using **JWS Detached Content** format ([RFC 7515 Appendix F](https://datatracker.ietf.org/doc/html/rfc7515#appendix-F)).

**Checkout Response with Embedded Signature:**

```json
{
  "id": "chk_abc123",
  "status": "ready_for_complete",
  "currency": "USD",
  "line_items": [...],
  "totals": [...],
  "ap2": {
    "merchant_authorization": "eyJhbGciOiJFUzI1NiIsImtpZCI6Im1lcmNoYW50XzIwMjUifQ..<signature>"
  }
}
```

The `merchant_authorization` value is a JWS with detached payload in the format `<header>..<signature>`. The double dot (`..`) indicates the payload is transmitted separately (as the checkout body itself).

**JWS Header Claims:**

| Claim | Type   | Required | Description                                      |
| ----- | ------ | -------- | ------------------------------------------------ |
| `alg` | string | Yes      | Signature algorithm (`ES256`, `ES384`, `ES512`)  |
| `kid` | string | Yes      | Key ID referencing the business's `signing_keys` |

**Signature Computation:**

The signature **MUST** cover both the JWS header and the checkout payload. This prevents algorithm substitution attacks where an attacker modifies the `alg` claim without invalidating the signature.

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

Mandates are **SD-JWT** credentials with Key Binding (`+kb`). The platform **MUST** produce two distinct mandate artifacts:

| Mandate              | UCP Placement                             | Purpose                                              |
| -------------------- | ----------------------------------------- | ---------------------------------------------------- |
| **checkout_mandate** | `ap2.checkout_mandate`                    | Proof bound to checkout terms, protects business     |
| **payment_mandate**  | `payment.instruments[*].credential.token` | Proof bound to payment authorization, protects funds |

The checkout mandate **MUST** contain the full checkout response including the `ap2.merchant_authorization` field. This creates a nested cryptographic binding where the platform's signature covers the business's signature.

**Specification Boundary:** This extension defines *where* mandates are placed in UCP requests and responses. The mandate credential structure (claims, selective disclosure, key binding) is defined by the [AP2 Protocol Specification](https://ap2-protocol.org/specification).

### Canonicalization

For signature computation over JSON payloads, implementations **MUST** use **JSON Canonicalization Scheme (JCS)** as defined in [RFC 8785](https://datatracker.ietf.org/doc/html/rfc8785).

JCS produces a deterministic, byte-for-byte identical representation of JSON data, ensuring signatures can be verified regardless of whitespace, key ordering, or Unicode normalization differences.

**Canonicalization Rule:** When computing the business's signature, exclude the `ap2` field entirely. This ensures future AP2 fields are automatically handled.

## The Mandate Flow

Once the `dev.ucp.shopping.ap2_mandate` capability is negotiated, the session is locked into the following flow. Both parties **MUST** follow these steps to ensure cryptographic integrity; any attempt to bypass these steps or submit a completion request without mandates **MUST** result in a session failure.

### Step 1: Checkout Creation & Signing

The platform initiates the session. The business returns the `Checkout` object with `ap2.merchant_authorization` embedded in the response body.

**Error:** Definition '#/$defs/checkout' not found in 'source/schemas/shopping/ap2_mandate.json'

**Example Response:**

```json
{
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
    assert header.alg in ["ES256", "ES384", "ES512"]

    // Reconstruct signed payload (checkout minus ap2)
    payload = checkout without "ap2" field
    canonical_bytes = jcs_canonicalize(payload)

    // Reconstruct signing input (header + payload)
    signing_input = encoded_header + "." + base64url_encode(canonical_bytes)

    // Get business's public key and verify
    public_key = get_key_by_kid(merchant_profile.signing_keys, header.kid)
    return verify(encoded_signature, signing_input, public_key, header.alg)
```

### Step 2: User Consent & Mandate Generation

When the user confirms the purchase, the platform **MUST** facilitate the generation of cryptographically verifiable mandates.

#### Option 1: Trusted Platform Provider

A trusted platform provider acts on the user's behalf to generate the mandate credentials. The platform provider **MUST** ensure that mandates are not created without explicit user consent from trusted, deterministic channels.

Upon user consent, the platform signs the mandates using their server-side key. The business trusts the platform's signature implies user consent.

#### Option 2: Digital Payment Credential

In this model the user has a VDC issued from a source trusted by the business (for example: a digital payment credential issued by a bank or network).

The platform requests a presentation via a protocol like OpenID4VP. The User's Wallet (or equivalent) processes the request and signs the mandates using the private key associated with their payment credential.

The business trusts the Credential Issuer (Bank) and verifies the user's Key Binding (+kb) signature.

### Step 3: Submission (`complete_checkout`)

Once the mandates are generated, the platform submits them in the completion request:

| Name             | Type                                                                    | Required | Description                                      |
| ---------------- | ----------------------------------------------------------------------- | -------- | ------------------------------------------------ |
| checkout_mandate | [Checkout Mandate](/draft/specification/ap2-mandates/#checkout-mandate) | No       | SD-JWT+kb proving user authorized this checkout. |

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
          "description": "Visa •••• 1234",
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

- `ap2.checkout_mandate`: The SD-JWT+kb checkout mandate containing the full checkout (with `ap2.merchant_authorization`)
- `payment.instruments[*].credential.token`: Contains the payment mandate (composite token)

## Verification & Processing

### Business Verification

Upon receiving the `complete` request, the business **MUST**:

1. **Enforce Negotiation:** If AP2 was negotiated, reject the request with `mandate_required` error code if `ap2.checkout_mandate` is missing.

**Mandate Verification (per AP2 spec):**

1. **Verify Mandate:** Decode and verify the SD-JWT signature, key binding, and expiration per the [AP2 Protocol Specification](https://ap2-protocol.org/specification).
1. **Extract Embedded Checkout:** Extract the checkout object from the verified mandate claims.

**UCP Verification:**

1. **Verify Business Authorization:** Confirm `ap2.merchant_authorization` in the embedded checkout is the business's own valid signature:

   ```text
   jws = embedded_checkout.ap2.merchant_authorization
   [encoded_header, _, encoded_signature] = jws.split(".")
   header = json_decode(base64url_decode(encoded_header))

   payload = embedded_checkout without "ap2" field
   signing_input = encoded_header + "." + base64url_encode(jcs_canonicalize(payload))

   my_key = get_key_by_kid(my_signing_keys, header.kid)
   verify(encoded_signature, signing_input, my_key, header.alg)
   ```

1. **Verify Terms Match:** Confirm the embedded checkout terms match the current session state (id, totals, line items).

### PSP Verification

The business passes the `token` (composite object) to their Payment Handler / PSP. The PSP verifies the `payment_mandate` per the [AP2 Protocol Specification](https://ap2-protocol.org/specification), including signature validation, expiration, and correlation with the checkout.

## Schema

### Business Authorization

JWS Detached Content signature (RFC 7515 Appendix F) over the checkout response body (excluding ap2 field). Format: `<base64url-header>..<base64url-signature>`. The header MUST contain 'alg' (ES256/ES384/ES512) and 'kid' claims. The signature covers both the header and JCS-canonicalized checkout payload.

**Pattern:** `^[A-Za-z0-9_-]+\.\.[A-Za-z0-9_-]+$`

### AP2 Checkout Response

The `ap2` object included in checkout responses.

| Name                   | Type                                                                                | Required | Description                                                |
| ---------------------- | ----------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------- |
| merchant_authorization | [Merchant Authorization](/draft/specification/ap2-mandates/#merchant-authorization) | No       | Merchant's signature proving checkout terms are authentic. |

### Checkout Mandate

SD-JWT+kb credential in `ap2.checkout_mandate`. Proving user authorization for the checkout. Contains the full checkout including `ap2.merchant_authorization`.

**Pattern:** `^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+(~[A-Za-z0-9_-]+)*$`

### AP2 Complete Request

The `ap2` object included in COMPLETE checkout requests.

| Name             | Type                                                                    | Required | Description                                      |
| ---------------- | ----------------------------------------------------------------------- | -------- | ------------------------------------------------ |
| checkout_mandate | [Checkout Mandate](/draft/specification/ap2-mandates/#checkout-mandate) | No       | SD-JWT+kb proving user authorized this checkout. |

### Error Codes

Error codes specific to AP2 mandate verification.

**Enum:** `mandate_required`, `agent_missing_key`, `mandate_invalid_signature`, `mandate_expired`, `mandate_scope_mismatch`, `merchant_authorization_invalid`, `merchant_authorization_missing`

| Error Code                       | Description                                                       |
| -------------------------------- | ----------------------------------------------------------------- |
| `mandate_required`               | AP2 was negotiated, but the request lacks `ap2.checkout_mandate`. |
| `agent_missing_key`              | Platform profile lacks a valid `signing_keys` entry.              |
| `mandate_invalid_signature`      | The mandate signature cannot be verified.                         |
| `mandate_expired`                | The mandate `exp` timestamp has passed.                           |
| `mandate_scope_mismatch`         | The mandate is bound to a different checkout.                     |
| `merchant_authorization_invalid` | The business authorization signature could not be verified.       |
