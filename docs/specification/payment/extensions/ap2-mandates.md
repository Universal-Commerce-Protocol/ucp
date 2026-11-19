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

When both profiles also declare `order_receipts` in the capability `config`,
the business **MUST** additionally issue a signed, mandate-bound receipt for
every money movement on the resulting Order. See
[Order Receipts](#order-receipts).

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

## Discovery & Negotiation

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
> Security & Privacy considerations state an entropy rule satisfied by any
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
    "merchant_authorization": "eyJhbGciOiJFUzI1NiIsImtpZCI6Im1lcmNoYW50XzIwMjUifQ..signature"
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

| Mandate              | UCP Placement                             | Purpose                                              |
| :------------------- | :---------------------------------------- | :--------------------------------------------------- |
| **checkout_mandate** | `ap2.checkout_mandate`                    | Proof bound to checkout terms, protects business     |
| **payment_mandate**  | `payment.instruments[*].credential.token` | Proof bound to payment authorization, protects funds |

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

### Step 1: Checkout Creation & Signing

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
    "merchant_authorization": "eyJhbGciOiJFUzI1NiIsImtpZCI6Im1lcmNoYW50XzIwMjUifQ..signature"
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

### Step 2: User Consent & Mandate Generation

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

### Step 3: Submission (`complete_checkout`)

Once the mandates are generated, the platform submits them in the completion
request:

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
    "checkout_mandate": "eyJhbGciOiJFUzI1NiIsInR5cCI6InZjK3NkLWp3dCJ9.payload.signature" // The User-Signed SD-JWT+kb / platform provider signed SD-JWT / delegated SD-JWT-KB
  }
}
```

* `ap2.checkout_mandate`: The SD-JWT+kb checkout mandate containing the
    full checkout (with `ap2.merchant_authorization`)
* `payment.instruments[*].credential.token`: Contains the payment mandate (composite token)

## Verification & Processing

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

The business passes the `token` (composite object) to their Payment
Handler / PSP. The PSP verifies the `payment_mandate` per the
[AP2 Protocol Specification](https://ap2-protocol.org/specification),
including signature validation, expiration, and correlation with the
checkout.

## Order Receipts

Mandates make everything up to `complete_checkout` verifiable. Money movements
after that point (captures, split-shipment captures, re-authorizations,
releases and refunds) are not covered by any mandate signature. Order receipts
close that gap: for every such movement, the business issues a signed receipt
that is bound to the closed Payment Mandate and hash-chained to the previous
receipt. Any party holding the receipts (the platform, the user's agent, or a
dispute reviewer) can verify offline that the movements those receipts attest
to stayed within what the user authorized and that refunds never exceeded
captures. See [Limits](#limits) for what receipts alone cannot show.

Order receipts are optional and additive. A business that does not declare
`order_receipts` behaves exactly as before.

### Negotiation

A business and a platform enable order receipts by declaring the
`order_receipts` member in the `config` of their
`dev.ucp.common.payment.ap2_mandate` capability. The business also lists
`dev.ucp.shopping.order` in `extends`, because receipts appear on the Order.

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.payment.ap2_mandate": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/payment/extensions/ap2-mandates",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/payment_ap2_mandate.json",
          "extends": ["dev.ucp.shopping.checkout", "dev.ucp.shopping.order"],
          "config": {
            "vp_formats_supported": {
              "dc+sd-jwt": { }
            },
            "order_receipts": {
              "events": ["authorization", "capture", "authorization_adjustment", "release", "refund"]
            }
          }
        }
      ]
    }
  }
}
```

Order receipts are required only when **both** profiles declare
`order_receipts`. When they are, the business **MUST** issue a receipt for
every event type listed in its own `order_receipts.events`. In the platform
profile, `order_receipts.events` is informational: it states the event types
the platform can process, and does not change which receipts the business
issues. A platform verifies every receipt it receives, including types it did
not list.

### Receipt Format

Each receipt is a **compact JWS**
([RFC 7515](https://datatracker.ietf.org/doc/html/rfc7515){target="_blank"}),
not detached, so it is self-contained evidence that can be stored and verified
later.

**JWS Header Claims:**

| Claim | Type   | Required | Description                                             |
| :---- | :----- | :------- | :------------------------------------------------------ |
| `alg` | string | Yes      | Per this extension's algorithm rule (e.g. `ES256`)      |
| `kid` | string | Yes      | Key ID resolving in the issuing business's `keys`       |
| `typ` | string | Yes      | `ucp-ap2-receipt+jwt`                                   |

The payload is the JCS-canonicalized
([RFC 8785](https://datatracker.ietf.org/doc/html/rfc8785){target="_blank"})
receipt payload. The example below is the decoded payload of the second receipt
in a chain: the first of two split-shipment captures against a USD 54.00
mandate.

<!-- ucp:example schema=common/payment_ap2_mandate def=receipt_payload -->
```json
{
  "iss": "https://business.example.com/.well-known/ucp",
  "order_id": "order_abc123",
  "checkout_id": "chk_abc123",
  "mandate_ref": "sha-256:zi0xDk16_GJw_QEKIHaUbkUFStkDJ6WjaKlf31sYfOk",
  "iat": 1794276000,
  "seq": 2,
  "prev": "sha-256:mbHrcoJUfBRlEA-bAgELvYEHwm9B8W-DshK4yuDHXgg",
  "event": {
    "type": "capture",
    "status": "succeeded",
    "amount": 3000,
    "currency": "USD",
    "occurred_at": "2026-11-10T02:00:00Z",
    "ref": {
      "processing_entry_id": "ent_2"
    }
  },
  "totals": {
    "mandated": 5400,
    "authorized": 5400,
    "captured": 3000,
    "refunded": 0
  }
}
```

{{ extension_schema_fields('payment_ap2_mandate.json#/$defs/receipt_payload', 'payment/extensions/ap2-mandates') }}

### Hashes and Chaining

`mandate_ref` and `prev` use the same format: `sha-256:` followed by the
unpadded base64url SHA-256 digest of the referenced artifact's exact UTF-8
bytes.

* **`mandate_ref`** is computed over the Payment Mandate exactly as carried in
    `payment.instruments[*].credential.token` of the `complete_checkout`
    request. Both the business and the platform hold this value, so both can
    compute it.
* **`prev`** is computed over the previous receipt's compact JWS in the same
    chain, and is `null` when `seq` is 1.

Receipts form one chain per **`(iss, mandate_ref)`** pair, not per Order.
`seq` starts at 1 and increases by exactly 1 within a chain. `totals` are
running totals for that chain. For a single business with one Payment Mandate,
an Order has exactly one chain.

The signature covers the payload bytes as sent, and `prev` covers the compact
JWS as sent. A business **SHOULD** emit the payload in JCS form, but verifiers
**MUST NOT** require it: canonical form is never needed to verify a receipt or
to compute `prev`.

### Running Totals

`totals.mandated` is the `payment_amount` of the Payment Mandate that
`mandate_ref` covers. The other totals start at 0 and change only on
`succeeded` events, as follows:

| Event `type`               | Effect on totals         | Used for                                                        |
| :------------------------- | :----------------------- | :-------------------------------------------------------------- |
| `authorization`            | `authorized` += `amount` | An initial authorization or a re-authorization.                 |
| `authorization_adjustment` | `authorized` += `amount` | An incremental increase to an existing authorization.           |
| `release`                  | `authorized` -= `amount` | Releasing, voiding or expiring an uncaptured authorized amount. |
| `capture`                  | `captured` += `amount`   | A capture, including each capture of a split shipment.          |
| `capture_reversal`         | `captured` -= `amount`   | Voiding a capture before it settles.                            |
| `refund`                   | `refunded` += `amount`   | Returning settled funds, whether as a refund or a reversal.     |

A capture does not reduce `authorized`. Within a chain, `captured` ≤
`authorized` ≤ `mandated` and `refunded` ≤ `captured` always hold for a
compliant business.

Each movement counts once. A later `succeeded` receipt with the same `type`
and `event.ref.processing_entry_id` as an earlier `succeeded` receipt in the
chain is a follow-up (for example, one that only adds `network_ref`) and does
not change the totals again.

### Placement and Delivery

* **Order:** `ap2.receipts` holds every receipt issued for the Order, each
    chain in `seq` order. This follows the extension's rule that all
    AP2-specific fields are nested under an `ap2` object.
* **Webhooks:** each Order event that reports a money movement **MUST** carry
    the new receipts in `ap2.receipts`. Webhook deliveries remain signed per
    [Message Signatures](../../signatures.md); the receipt signature is
    independent of the transport signature and survives storage and
    re-serialization.

The Order below carries the complete chain for the example above: an
authorization followed by two split-shipment captures.

<!-- ucp:example schema=common/payment_ap2_mandate def=dev.ucp.shopping.order op=read -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.order": [
        {
          "version": "{{ ucp_version }}"
        }
      ],
      "dev.ucp.common.payment.ap2_mandate": [
        {
          "version": "{{ ucp_version }}"
        }
      ]
    }
  },
  "id": "order_abc123",
  "checkout_id": "chk_abc123",
  "permalink_url": "https://business.example.com/orders/abc123",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_shoes",
      "item": {
        "id": "prod_shoes",
        "title": "Running Shoes",
        "price": 2800
      },
      "quantity": {
        "total": 1,
        "fulfilled": 1
      },
      "totals": [
        {
          "type": "subtotal",
          "amount": 2800
        },
        {
          "type": "total",
          "amount": 2800
        }
      ],
      "status": "fulfilled"
    },
    {
      "id": "li_jacket",
      "item": {
        "id": "prod_jacket",
        "title": "Rain Jacket",
        "price": 2200
      },
      "quantity": {
        "total": 1,
        "fulfilled": 1
      },
      "totals": [
        {
          "type": "subtotal",
          "amount": 2200
        },
        {
          "type": "total",
          "amount": 2200
        }
      ],
      "status": "fulfilled"
    }
  ],
  "fulfillment": {
    "expectations": [
      {
        "id": "exp_1",
        "line_items": [
          {
            "id": "li_shoes",
            "quantity": 1
          }
        ],
        "method_type": "shipping",
        "destination": {
          "street_address": "123 Main St",
          "address_locality": "Austin",
          "address_region": "TX",
          "address_country": "US",
          "postal_code": "78701"
        },
        "description": "Shipment 1"
      },
      {
        "id": "exp_2",
        "line_items": [
          {
            "id": "li_jacket",
            "quantity": 1
          }
        ],
        "method_type": "shipping",
        "destination": {
          "street_address": "123 Main St",
          "address_locality": "Austin",
          "address_region": "TX",
          "address_country": "US",
          "postal_code": "78701"
        },
        "description": "Shipment 2"
      }
    ]
  },
  "adjustments": [],
  "totals": [
    {
      "type": "subtotal",
      "amount": 5000
    },
    {
      "type": "tax",
      "amount": 400
    },
    {
      "type": "total",
      "amount": 5400
    }
  ],
  "ap2": {
    "receipts": [
      "eyJhbGciOiJFUzI1NiIsImtpZCI6Im1lcmNoYW50XzIwMjUiLCJ0eXAiOiJ1Y3AtYXAyLXJlY2VpcHQrand0In0.eyJjaGVja291dF9pZCI6ImNoa19hYmMxMjMiLCJldmVudCI6eyJhbW91bnQiOjU0MDAsImN1cnJlbmN5IjoiVVNEIiwib2NjdXJyZWRfYXQiOiIyMDI2LTExLTA5VDE0OjUzOjIwWiIsInN0YXR1cyI6InN1Y2NlZWRlZCIsInR5cGUiOiJhdXRob3JpemF0aW9uIn0sImlhdCI6MTc5NDIzNjAwMCwiaXNzIjoiaHR0cHM6Ly9idXNpbmVzcy5leGFtcGxlLmNvbS8ud2VsbC1rbm93bi91Y3AiLCJtYW5kYXRlX3JlZiI6InNoYS0yNTY6emkweERrMTZfR0p3X1FFS0lIYVVia1VGU3RrREo2V2phS2xmMzFzWWZPayIsIm9yZGVyX2lkIjoib3JkZXJfYWJjMTIzIiwicHJldiI6bnVsbCwic2VxIjoxLCJ0b3RhbHMiOnsiYXV0aG9yaXplZCI6NTQwMCwiY2FwdHVyZWQiOjAsIm1hbmRhdGVkIjo1NDAwLCJyZWZ1bmRlZCI6MH19.B1qq-ooaU-iv_gU4sxGg6OodmLq3kHhMyMnmI-rQTr9aziOACY7l1Vbkws7lSTm09IpVugB_QksMQiXUi6gvVQ",
      "eyJhbGciOiJFUzI1NiIsImtpZCI6Im1lcmNoYW50XzIwMjUiLCJ0eXAiOiJ1Y3AtYXAyLXJlY2VpcHQrand0In0.eyJjaGVja291dF9pZCI6ImNoa19hYmMxMjMiLCJldmVudCI6eyJhbW91bnQiOjMwMDAsImN1cnJlbmN5IjoiVVNEIiwib2NjdXJyZWRfYXQiOiIyMDI2LTExLTEwVDAyOjAwOjAwWiIsInJlZiI6eyJwcm9jZXNzaW5nX2VudHJ5X2lkIjoiZW50XzIifSwic3RhdHVzIjoic3VjY2VlZGVkIiwidHlwZSI6ImNhcHR1cmUifSwiaWF0IjoxNzk0Mjc2MDAwLCJpc3MiOiJodHRwczovL2J1c2luZXNzLmV4YW1wbGUuY29tLy53ZWxsLWtub3duL3VjcCIsIm1hbmRhdGVfcmVmIjoic2hhLTI1Njp6aTB4RGsxNl9HSndfUUVLSUhhVWJrVUZTdGtESjZXamFLbGYzMXNZZk9rIiwib3JkZXJfaWQiOiJvcmRlcl9hYmMxMjMiLCJwcmV2Ijoic2hhLTI1NjptYkhyY29KVWZCUmxFQS1iQWdFTHZZRUh3bTlCOFctRHNoSzR5dURIWGdnIiwic2VxIjoyLCJ0b3RhbHMiOnsiYXV0aG9yaXplZCI6NTQwMCwiY2FwdHVyZWQiOjMwMDAsIm1hbmRhdGVkIjo1NDAwLCJyZWZ1bmRlZCI6MH19.kffxBLFlPYyfhAD_qXCpG2KIPDtmOfyRwBS9AlHUsHcmZlrFJ5YHBqPdT2fwLAzwdhFv2InssCj344UuHag1Wg",
      "eyJhbGciOiJFUzI1NiIsImtpZCI6Im1lcmNoYW50XzIwMjUiLCJ0eXAiOiJ1Y3AtYXAyLXJlY2VpcHQrand0In0.eyJjaGVja291dF9pZCI6ImNoa19hYmMxMjMiLCJldmVudCI6eyJhbW91bnQiOjI0MDAsImN1cnJlbmN5IjoiVVNEIiwib2NjdXJyZWRfYXQiOiIyMDI2LTExLTEyVDAyOjAwOjAwWiIsInJlZiI6eyJwcm9jZXNzaW5nX2VudHJ5X2lkIjoiZW50XzMifSwic3RhdHVzIjoic3VjY2VlZGVkIiwidHlwZSI6ImNhcHR1cmUifSwiaWF0IjoxNzk0NDQ4ODAwLCJpc3MiOiJodHRwczovL2J1c2luZXNzLmV4YW1wbGUuY29tLy53ZWxsLWtub3duL3VjcCIsIm1hbmRhdGVfcmVmIjoic2hhLTI1Njp6aTB4RGsxNl9HSndfUUVLSUhhVWJrVUZTdGtESjZXamFLbGYzMXNZZk9rIiwib3JkZXJfaWQiOiJvcmRlcl9hYmMxMjMiLCJwcmV2Ijoic2hhLTI1NjotNG9URC1FS1lfQ3lwTlM1TzhXRWhYRE5ZNkVGQkRwbDR3aUxXem9EMnFnIiwic2VxIjozLCJ0b3RhbHMiOnsiYXV0aG9yaXplZCI6NTQwMCwiY2FwdHVyZWQiOjU0MDAsIm1hbmRhdGVkIjo1NDAwLCJyZWZ1bmRlZCI6MH19.J-C66O6O4XjAD_TvtvS8endj_FfRIe_u3SysJ4U2NwX0zqQ0MlAy6FeGJZuSPUuCnY8twK9-9TjQdMT7ylL7Yw"
    ]
  }
}
```

### Business Requirements

When order receipts are negotiated, the business:

1. **MUST** issue a receipt for every event type in its
    `order_receipts.events`, in the same Order update that reports the event.
2. **MUST** set `iss` to its own profile URI, and **MUST** sign with a key
    whose `kid` resolves in its own `keys`. `iss` **MUST** be the business
    whose `ap2.merchant_authorization` the referenced Payment Mandate covers.
    In a marketplace that is merchant of record, that is the marketplace, not
    the individual seller.
3. **MUST NOT** authorize or capture so that `authorized` or `captured`
    exceeds `mandated`. Any increase in what the buyer pays beyond `mandated`
    (a tip, an overage, an order change, or a re-authorization above the
    original amount) **MUST** be covered by a new closed Payment Mandate from
    the platform. Movements that spend against the new mandate form their own
    chain, keyed by its `mandate_ref`.
4. **MUST NOT** refund so that `refunded` exceeds `captured`.
5. **MUST** state `totals` that follow the [Running Totals](#running-totals)
    rules.
6. **MUST** issue at most one receipt per `seq` in a chain, and **MUST NOT**
    re-issue a chain.
7. **MUST**, on a follow-up receipt that only adds `network_ref` to a movement
    already receipted as `succeeded`, carry that movement's
    `event.ref.processing_entry_id`. A business that cannot supply a
    `processing_entry_id` issues the movement as `pending` first and adds
    `network_ref` on the `succeeded` receipt.
8. **SHOULD** set `event.seller_id` on `capture`, `refund` and `release`
    events when seller attribution is active on the Order.
9. **MUST** keep retired public keys resolvable by `kid` for at least the
    dispute window of the payment method used.
10. **MUST NOT** include card numbers, payment tokens or buyer personal data in
    a receipt.

### Platform Verification

When order receipts are negotiated, the platform:

1. **MUST** verify each receipt's signature against the `keys` of the business
    named in `iss`. A receipt whose `typ` is not `ucp-ap2-receipt+jwt`, or
    whose `kid` does not resolve in the `keys` of `iss`, is
    `receipt_invalid_signature`.
2. **MUST**, only for receipts whose signature verified, check that
    `mandate_ref` is a Payment Mandate the platform submitted and that `iss`
    is the business that signed the checkout it covers. A receipt that fails
    is `receipt_mandate_unknown`.
3. **MUST** exclude a receipt that fails rule 1 or 2 from its chain, so the
    next receipt in that chain is reported as `receipt_sequence_gap`.
4. **MUST** evaluate `seq` and `prev` continuity per `(iss, mandate_ref)`
    chain. A second, different receipt for a `seq` the platform already holds
    is `receipt_sequence_gap`; the platform keeps both.
5. **MUST** recompute `authorized`, `captured` and `refunded` for each chain
    from the `succeeded` events it holds, per
    [Running Totals](#running-totals), and **MUST** check that
    `totals.mandated` equals the `payment_amount` of the Payment Mandate that
    `mandate_ref` covers. A receipt whose stated `totals` differ from these
    values is `receipt_totals_mismatch`.
6. **MUST** check, on the recomputed totals, that `authorized` and `captured`
    do not exceed `mandated` (`receipt_exceeds_mandate`) and that `refunded`
    does not exceed `captured` (`receipt_refund_exceeds_capture`).
7. **SHOULD**, when `event.seller_id` is present, also check per seller that
    succeeded captures do not exceed that seller's attributed total and that
    refunds do not exceed that seller's captures. This is a **SHOULD** because
    a seller's chargeable amount can include Order-level shipping, tax or
    discounts that are not attributed to its line items.
8. **SHOULD** reconcile refunds against Order adjustments. The platform
    compares the sum of `event.amount` over the `succeeded` refund receipts
    that cite an `event.ref.adjustment_id` with the magnitude of that
    adjustment's `total` entry. `pending` and `failed` receipts are not
    counted. A cited `adjustment_id` that matches no adjustment on the Order
    is also `reconciliation_adjustment_mismatch`. A mismatch is a commercial
    problem, not a cryptographic one: the receipts remain valid.
9. **SHOULD**, on any failed check, alert the user or the agent's policy
    engine, and **MUST** retain every receipt it received as dispute evidence.
    See [Limits](#limits).

Platforms record these outcomes rather than returning them as errors, because
the money has already moved:

{{ extension_schema_fields('payment_ap2_mandate.json#/$defs/receipt_verification_outcome', 'payment/extensions/ap2-mandates') }}

| Outcome                              | Meaning                                                                                  |
| :----------------------------------- | :--------------------------------------------------------------------------------------- |
| `receipt_invalid_signature`          | The signature cannot be verified, `kid` does not resolve, or `typ` is wrong.             |
| `receipt_sequence_gap`               | A `seq` is missing or repeated, or `prev` does not match.                                |
| `receipt_totals_mismatch`            | Stated `totals` differ from the recomputed totals or the mandate's `payment_amount`.     |
| `receipt_exceeds_mandate`            | `authorized` or `captured` exceeds `mandated` for the chain.                             |
| `receipt_refund_exceeds_capture`     | `refunded` exceeds `captured` for the chain.                                             |
| `receipt_exceeds_seller_total`       | A seller's captures exceed what is attributed to it, or its refunds exceed its captures. |
| `receipt_mandate_unknown`            | `mandate_ref` is unknown, or `iss` is not the business it covers.                        |
| `reconciliation_adjustment_mismatch` | Succeeded refunds disagree with the cited adjustment, or it does not exist.              |

### Limits

* **A missing tail is not detectable from the chain.** `seq` and `prev` show a
    receipt missing from the middle of a chain, but not that the last receipt
    a platform holds is the last one issued. A platform **SHOULD** compare the
    chain with the payment state the Order reports and treat a movement the
    Order reports without a receipt as `receipt_sequence_gap`.
* **The business signs the whole chain.** It could sign a second, different
    chain for the same `mandate_ref`. Only a party that kept the receipts it
    was sent can show the difference, which is why platforms **MUST** retain
    them.

### Edge Cases

* **Split shipments:** multiple `capture` receipts against the same
    `mandate_ref`, with `captured` accumulating.
* **Authorization expiry:** a `release` receipt for the expired, uncaptured
    amount, then a new `authorization` receipt with the same `mandate_ref`.
    Without a new mandate, the new authorization is limited to `mandated`
    minus `captured`, so `authorized` never exceeds `mandated`.
* **Cancelled before capture:** a `release` receipt; `authorized` drops and
    `captured` stays at 0.
* **Partial capture, remainder released:** a 3000 capture followed by a
    `release` of the remaining 2400 leaves `authorized` at 3000 and `captured`
    at 3000.
* **Pending movements:** a movement may first be receipted as `pending`. A
    later receipt in the same chain for the same movement carries
    `status: succeeded`. Totals change only on the `succeeded` receipt.
* **Late network references:** when a network reference (for example the
    Acquirer Reference Number of a refund) is assigned after the movement is
    receipted as `succeeded`, it appears on a follow-up receipt with the same
    `type` and `event.ref.processing_entry_id`, which does not change the
    totals. `network_ref` is optional on every status: a refund that the
    processor settles as a reversal of the original transaction may never
    have one. It is still receipted as a `refund`.
* **Out-of-order processor callbacks:** `seq` reflects issuance order;
    `occurred_at` carries when the movement happened.
* **Marketplace as merchant of record:** the marketplace issues every receipt
    and sets `event.seller_id`, so a duplicate capture for one seller is
    detectable even when the chain's totals pass.
* **Several merchants of record in one Order:** each has its own mandate and
    keys, so each `(iss, mandate_ref)` pair is an independent chain.
* **Partial refunds under a cancellation policy:** the refund receipt proves the
    money movement and cites the cancellation adjustment through
    `event.ref.adjustment_id`; whether the amount was commercially correct is
    checked against that adjustment, not inside the receipt.
* **Disputes and chargebacks:** out of scope. They are initiated by the card
    network, and the business may not be the source of truth.

## Schema

### Business Authorization {: #merchant-authorization }

{{ extension_schema_fields('payment_ap2_mandate.json#/$defs/merchant_authorization', 'payment/extensions/ap2-mandates') }}

### AP2 Checkout Response

The `ap2` object included in checkout responses.

{{ extension_schema_fields('payment_ap2_mandate.json#/$defs/ap2_with_merchant_authorization', 'payment/extensions/ap2-mandates') }}

### Checkout Mandate

{{ extension_schema_fields('payment_ap2_mandate.json#/$defs/checkout_mandate', 'payment/extensions/ap2-mandates') }}

### AP2 Complete Request

The `ap2` object included in COMPLETE checkout requests.

{{ extension_schema_fields('payment_ap2_mandate.json#/$defs/ap2_with_checkout_mandate', 'payment/extensions/ap2-mandates') }}

### Order Receipt {: #order-receipt }

{{ extension_schema_fields('payment_ap2_mandate.json#/$defs/receipt', 'payment/extensions/ap2-mandates') }}

### AP2 Order Response

The `ap2` object included in Order responses when order receipts are
negotiated.

{{ extension_schema_fields('payment_ap2_mandate.json#/$defs/ap2_with_receipts', 'payment/extensions/ap2-mandates') }}

### Order Receipts Config

{{ extension_schema_fields('payment_ap2_mandate.json#/$defs/order_receipts_config', 'payment/extensions/ap2-mandates') }}

### Receipt Event

{{ extension_schema_fields('payment_ap2_mandate.json#/$defs/receipt_event', 'payment/extensions/ap2-mandates') }}

### Receipt Totals

{{ extension_schema_fields('payment_ap2_mandate.json#/$defs/receipt_totals', 'payment/extensions/ap2-mandates') }}

### Error Codes

{{ extension_schema_fields('payment_ap2_mandate.json#/$defs/error_code', 'payment/extensions/ap2-mandates') }}

| Error Code                       | Description                                                       |
| :------------------------------- | :---------------------------------------------------------------- |
| `mandate_required`               | AP2 was negotiated, but the request lacks `ap2.checkout_mandate`. |
| `agent_missing_key`              | Platform profile lacks a valid `keys` entry.                      |
| `mandate_invalid_signature`      | The mandate signature cannot be verified.                         |
| `mandate_expired`                | The mandate `exp` timestamp has passed.                           |
| `mandate_scope_mismatch`         | The mandate is bound to a different checkout.                     |
| `merchant_authorization_invalid` | The business authorization signature could not be verified.       |
| `merchant_authorization_missing` | The checkout response omits `ap2.merchant_authorization`.         |
