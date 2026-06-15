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

# Message Signatures

This specification defines how UCP messages are cryptographically signed to
ensure authenticity and integrity.

## Overview

This specification defines how to sign and verify UCP messages using
[RFC 9421](https://www.rfc-editor.org/rfc/rfc9421) HTTP Message Signatures.
For UCP's identity model, supported authentication mechanisms, and key
discovery protocol, see
[Identity & Authentication](overview.md#identity-authentication).

HTTP Message Signatures protect against:

* **Impersonation** — Attackers sending messages claiming to be legitimate
    participants
* **Tampering** — Modification of message contents in transit
* **Replay attacks** — Captured messages resent to different endpoints or at
    different times
* **Method/endpoint confusion** — Signed payloads replayed with different
    HTTP methods or to different paths

### Architecture

UCP uses HTTP Message Signatures ([RFC 9421](https://www.rfc-editor.org/rfc/rfc9421))
for all HTTP-based transports:

```text
+-----------------------------------------------------------------+
|                     SHARED FOUNDATION                           |
+-----------------------------------------------------------------+
|  Signature Format: RFC 9421 (HTTP Message Signatures)           |
|  Body Digest: RFC 9530 (Content-Digest, raw bytes)              |
|  Algorithms: ES256 (required); EdDSA (Ed25519) optional,        |
|              required when supporting Web Bot Auth interop;     |
|              ES384 optional                                     |
|  Key Format: JWK (RFC 7517 + RFC 8037 for Ed25519)              |
|  Key Discovery: signing_keys[] (canonical) or top-level keys[]  |
|                 (RFC 7517 JWK Set mirror) in /.well-known/ucp   |
|  Replay Protection: idempotency-key (business layer)            |
+-----------------------------------------------------------------+
                              |
                              v
+-----------------------------------------------------------------+
|                     HTTP TRANSPORTS                             |
+-----------------------------------------------------------------+
|  REST API: Standard HTTP requests                               |
|  MCP: Streamable HTTP transport (JSON-RPC over HTTP)            |
+-----------------------------------------------------------------+
|  Headers:                                                       |
|    Signature-Input    (describes signed components)             |
|    Signature          (contains signature value)                |
|    Content-Digest     (body hash, raw bytes)                    |
+-----------------------------------------------------------------+
```

**Note:** UCP specifies streamable HTTP for MCP transport, replacing SSE-based
transports. This allows the same RFC 9421 signature mechanism to apply uniformly
across all UCP transports.

## Shared Foundation

The following cryptographic primitives are shared across all UCP HTTP transports.

### Signature Algorithms

UCP recognizes two algorithm families: ECDSA (over NIST P-curves) and
EdDSA (Ed25519). ECDSA P-256 is the universal baseline; EdDSA is an
additive option that unlocks Web Bot Auth (WBA) interop.

| Family | JWK `kty` / `crv` | JWA `alg` | Hash |
| :----- | :---------------- | :-------- | :--- |
| ECDSA P-256 | `EC` / `P-256` | `ES256` | SHA-256 |
| ECDSA P-384 | `EC` / `P-384` | `ES384` | SHA-384 |
| EdDSA Ed25519 | `OKP` / `Ed25519` | `EdDSA` | (built-in) |

**Implementation requirements:**

* All implementations **MUST** support verifying `ES256` (ECDSA P-256)
  signatures. This is the universal UCP baseline.
* Support for `ES384` (ECDSA P-384) is **OPTIONAL**.
* Support for `EdDSA` (Ed25519) is **OPTIONAL** for general UCP
  verifiers. Verifiers that explicitly support Web Bot Auth-compatible
  signatures **MUST** support `EdDSA`.
* The `kty`/`crv`/`alg` vocabularies are **open**. A verifier that
  encounters a key whose type, curve, or algorithm it does not support
  **MUST NOT** reject the published key set; the unsupported key simply
  remains unusable to that verifier. A signature that references such a
  key fails with `algorithm_unsupported` (and, in a multi-signature
  request, is skipped per the [Identity Resolution
  Algorithm](overview.md#identity-resolution-algorithm)).

**Usage guidance:**

* Signers **MAY** use any supported algorithm. A single party MAY publish
  multiple keys of different algorithms in their published key set
  (`keys[]` or `signing_keys[]`, see
  [Key Discovery](#key-discovery)) and select per-signature; verifiers
  select by `kid`.
* `ES256` is **RECOMMENDED** for signers wanting maximum interoperability
  with all UCP verifiers today.
* `EdDSA` (Ed25519) is **RECOMMENDED** for signers opting into Web Bot
  Auth interop — see [WBA Interop](#wba-interop) for the recommended
  signature shape. Signers using Ed25519 SHOULD confirm Ed25519
  verifier support with their counterparties.
* `ES256` is **RECOMMENDED** for AP2 mandate signing
  (`ap2.merchant_authorization`), which currently requires a
  non-deterministic signature scheme per
  [AP2 v0.2 §Payment Mandate](https://ap2-protocol.org/ap2/specification/).
  See [AP2 Mandates](ap2-mandates.md) for details.
* The algorithm is derived from the key's `kty`/`crv` field in the JWK;
  `alg` is **NOT** included in `Signature-Input` parameters.

**Two-key vs. one-key configurations.** A merchant participating in
both UCP HTTP transport (with WBA interop) and AP2 mandate signing
today operates two keys — one Ed25519 for HTTP transport identity,
one ECDSA P-256 for `merchant_authorization` — selected per signature
by `kid`. UCP-only sites that do not interact with WBA or AP2 may
operate a single ES256 key. See
[Business Profile](overview.md#business-profile) for a two-key
example.

For on-the-wire signature encoding details, see
[REST Request Signing — Signature Encoding](#rest-request-signing).

### Key Format (JWK)

Public keys **MUST** be represented using **JSON Web Key (JWK)** format as
defined in [RFC 7517](https://datatracker.ietf.org/doc/html/rfc7517).
UCP defines two well-known JWK shapes: **EC** (per RFC 7518 §6.2) for ECDSA
keys and **OKP** (per [RFC 8037](https://datatracker.ietf.org/doc/html/rfc8037))
for EdDSA keys. The JWK vocabulary is open (see [Signature
Algorithms](#signature-algorithms)): profiles MAY publish keys of other
types, and verifiers skip those they cannot use.

**EC Key Structure (ECDSA P-256, P-384):**

| Field | Type   | Required | Description                              |
| :---- | :----- | :------- | :--------------------------------------- |
| `kid` | string | Yes      | Key ID (referenced in signatures)        |
| `kty` | string | Yes      | Key type (`EC`)                          |
| `crv` | string | Yes      | Curve name (`P-256` or `P-384`)          |
| `x`   | string | Yes      | X coordinate (base64url encoded)         |
| `y`   | string | Yes      | Y coordinate (base64url encoded)         |
| `use` | string | No       | Key usage (`sig` for signing)            |
| `alg` | string | No       | Algorithm (`ES256`, `ES384`)             |

**OKP Key Structure (EdDSA Ed25519):**

| Field | Type   | Required | Description                                          |
| :---- | :----- | :------- | :--------------------------------------------------- |
| `kid` | string | Yes      | Key ID (referenced in signatures)                    |
| `kty` | string | Yes      | Key type (`OKP`)                                     |
| `crv` | string | Yes      | Curve name (`Ed25519`)                               |
| `x`   | string | Yes      | Public key value (base64url encoded per RFC 8037 §2) |
| `use` | string | No       | Key usage (`sig` for signing)                        |
| `alg` | string | No       | Algorithm (`EdDSA`)                                  |

**EC Example (ES256):**

<!-- ucp:example schema=profile extract=$ target=$.signing_keys[0] -->
```json
{
  "kid": "key-2024-01-15",
  "kty": "EC",
  "crv": "P-256",
  "x": "WKn-ZIGevcwGIyyrzFoZNBdaq9_TsqzGl96oc0CWuis",
  "y": "y77t-RvAHRKTsSGdIYUfweuOvwrvDD-Q3Hv5J0fSKbE",
  "use": "sig",
  "alg": "ES256"
}
```

**OKP Example (Ed25519 / EdDSA):**

<!-- ucp:example schema=profile extract=$ target=$.signing_keys[0] -->
```json
{
  "kid": "kPrK_qmxVWaYVA9wwBF6Iuo3vVzz7TxHCTwXBygrS4k",
  "kty": "OKP",
  "crv": "Ed25519",
  "x": "11qYAYKxCrfVS_7TyWQHOg7hcvPapiMlrwIaaPcHURo",
  "use": "sig",
  "alg": "EdDSA"
}
```

For WBA-shape signatures, the JWK SHA-256 Thumbprint
([RFC 7638](https://www.rfc-editor.org/rfc/rfc7638)) is
**RECOMMENDED** as the `kid` value.

### Key Discovery

Public keys are published in the party's UCP profile (see
[Profile Structure](overview.md#profile-structure) for the publishing
contract). Verifiers read by signature regime:

* **Default UCP signature** — read `signing_keys[]`.
* **WBA-shape signature** (resolved via `Signature-Agent`) — read
  top-level `keys[]`.

For the full identity resolution algorithm and deployment patterns,
see [Identity & Authentication](overview.md#identity-authentication).

### Key Rotation

To rotate keys without service interruption:

1. **Add new key** — Publish new key in the profile's `signing_keys[]`
   (and mirror in `keys[]` if the profile uses the JWKS-superset form)
   alongside existing keys
2. **Start signing** — Begin signing with the new key
3. **Grace period** — Continue accepting signatures from old keys (minimum 7 days)
4. **Remove old key** — Remove the old key from `signing_keys[]` (and
   from `keys[]` if published). A key still listed in either array
   continues to verify.

**Recommendations:**

* Operators SHOULD rotate keys every 90 days.
* Profiles SHOULD support multiple active keys during transitions.

**Key Compromise Response:**

1. Immediately remove the compromised key from `signing_keys[]` and
   `keys[]` (if published); it continues to verify until absent from
   both arrays
2. Add new key with different `kid`
3. Reject all signatures made with compromised key

### WBA Interop

A UCP integrator MAY opt their primary signature into a Web Bot Auth-
compatible shape, enabling the same signature to be verified by both UCP
and WBA verifiers with **one key and one signing operation**. This is the
RECOMMENDED path for integrators wanting interop with WBA-conformant
verifiers.

To opt in, a signer makes the following changes to their primary UCP
signature. Items marked **MUST** are required by
[draft-meunier-web-bot-auth-architecture](https://datatracker.ietf.org/doc/draft-meunier-web-bot-auth-architecture/)
§4.2; consult that draft for full details.

1. **Algorithm SHOULD be Ed25519.** Ed25519 is the convention across
   WBA-conformant verifiers; other algorithms work only if the
   counterparty accepts them.
2. **MUST send a `Signature-Agent` header** alongside `UCP-Agent`. An
   RFC 8941 Dictionary Structured Field whose member's sf-string value
   is the HTTPS directory URL; the member key matches the
   `Signature-Input` signature label. (`data:` URI inline form is out
   of scope; see
   [Identity Resolution Algorithm](overview.md#identity-resolution-algorithm).)
   See [Identity & Authentication](overview.md#identity-authentication)
   for directory shape and deployment patterns.
3. **MUST sign the `signature-agent` component with `;key="<label>"`**
   matching the `Signature-Agent` dictionary member key (which equals
   the `Signature-Input` signature label). Per WBA §4.2.1.
4. **MUST set `keyid` to the JWK SHA-256 Thumbprint** of the signing
   key per [RFC 7638](https://www.rfc-editor.org/rfc/rfc7638). For
   Ed25519 (OKP) keys, the thumbprint members are `crv`, `kty`, `x`
   per [RFC 8037](https://www.rfc-editor.org/rfc/rfc8037) §2;
   Appendix A.3 has a worked example.
5. **MUST include `created` and `expires` parameters.** The `expires`
   interval SHOULD be at most 24 hours.
6. **MUST include `tag="web-bot-auth"`.** WBA verifiers select
   signatures by this tag.

**Component requirements preserved.** UCP's existing signed components
(`ucp-agent`, `idempotency-key`, `content-digest`, `content-type`)
stay in the signed list. WBA accepts them as "additional components"
per
[draft-meunier-web-bot-auth-architecture](https://datatracker.ietf.org/doc/draft-meunier-web-bot-auth-architecture/)
§4.2.3.

UCP verifiers see the same signature with three new things:

* The `tag` parameter is an RFC 9421 §2.3 signature parameter unknown
  to UCP-only verifiers and ignored per RFC 9421's permissive
  parameter handling.
* The `signature-agent` component is processed normally as a covered
  HTTP field; the `;key="<label>"` parameter selects a Dictionary
  member per RFC 9421 §2.1.2. Verifying WBA-shape signatures requires
  §2.1.2 support — UCP-default signatures don't use Dictionary-member
  component selection, so verifiers built only for UCP-default may
  need to add it.
* The `created` and `expires` parameters are standard RFC 9421 §2.3
  parameters, so RFC 9421-conformant UCP verifiers **will** enforce
  the freshness window.

**Identity resolution.** WBA opt-in does not change the default UCP
regime: verifiers dispatch by `tag`. See
[Identity Resolution Algorithm](overview.md#identity-resolution-algorithm).

**Unknown signature parameters.** Verifiers **MUST** ignore signature
parameters they do not recognize (RFC 9421 §2.3).

**Complete WBA-shape Request Example:**

<!-- ucp:example schema=shopping/checkout op=create direction=request -->
```json
POST /checkout-sessions HTTP/1.1
Host: merchant.example.com
Content-Type: application/json
UCP-Agent: profile="https://platform.example/.well-known/ucp"
Signature-Agent: sig1="https://platform.example/.well-known/ucp"
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Digest: sha-256=:X48E9q...:
Signature-Input: sig1=("@method" "@authority" "@path" "signature-agent";key="sig1" "ucp-agent" "idempotency-key" "content-digest" "content-type");keyid="kPrK_qmxVWaYVA9wwBF6Iuo3vVzz7TxHCTwXBygrS4k";created=1738617600;expires=1738621200;tag="web-bot-auth"
Signature: sig1=:base64_ed25519_signature_value:

{
  "line_items": [
    {
      "item": {"id": "item_123"},
      "quantity": 2
    }
  ]
}
```

One signature on the wire. UCP-shape verifiers find their expected
components (`ucp-agent`, `idempotency-key`); WBA-shape verifiers find
theirs (`@authority`, `signature-agent`, `tag`, `created`/`expires`).
Both verify the same bytes against the same key. The two header URLs
match here because the same well-known endpoint serves both regimes
(see
[Deployment Patterns](overview.md#deployment-patterns-for-wba-interop)).

In the example, the three `sig1` labels are bound together — the
`Signature-Agent` dictionary member key, the `;key="sig1"` parameter
on the signed `signature-agent` component, and the `Signature-Input`
signature label — per item 3 of the opt-in list above.

**Tags.** UCP does not define its own `tag` (RFC 9421 §2.3). UCP
verifiers identify their signatures via the `UCP-Agent` header,
signed-components set, and URL routing.

**Multiple signatures.** UCP requests **MAY** carry multiple signatures
using the [RFC 9421 §4.3](https://www.rfc-editor.org/rfc/rfc9421#section-4.3)
label mechanism. Use this pattern only when genuine separation is
required (different keys per audience, multi-party countersigning,
audience-specific component sets that conflict). For UCP + WBA interop
with one key, prefer the single-signature shape described above.

## REST Binding

For HTTP REST transport, UCP uses
[RFC 9421 (HTTP Message Signatures)](https://www.rfc-editor.org/rfc/rfc9421).

### Headers

| Header            | Direction        | Required | Description                                           |
| :---------------- | :--------------- | :------- | :---------------------------------------------------- |
| `Signature-Input` | Request/Response | Yes      | Describes signed components                           |
| `Signature`       | Request/Response | Yes      | Contains signature value                              |
| `Content-Digest`  | Request/Response | Cond.\*  | SHA-256 hash of request/response body                 |
| `Signature-Agent` | Request          | Cond.\** | Key directory for [WBA Interop](#wba-interop)         |

\* Required when request/response has a body

\** Required when opting into Web Bot Auth-compatible signature shape;
absent for default UCP signatures (verifiers fall back to `UCP-Agent`-
derived identity).

`Content-Digest` follows [RFC 9530](https://www.rfc-editor.org/rfc/rfc9530) and
hashes the raw body bytes. This binds the message body to the signature without
requiring JSON canonicalization. Implementations **MUST** use `sha-256`. For
durable artifacts requiring canonicalization, see
[AP2 Mandates - Canonicalization](ap2-mandates.md#canonicalization).

**Intermediary Warning:** Proxies, API gateways, and other intermediaries
**MUST NOT** re-serialize JSON bodies, as this would invalidate the signature.
The `Content-Digest` is computed over raw bytes; any modification breaks
verification.

### REST Request Signing

**Signed Components:**

| Component         | Required   | Description                                                           |
| :---------------- | :--------- | :-------------------------------------------------------------------- |
| `@method`         | Yes        | HTTP method (GET, POST, etc.)                                         |
| `@authority`      | Yes        | Target host (prevents cross-host relay)                               |
| `@path`           | Yes        | Request path                                                          |
| `@query`          | Cond.\*    | Query string (if present)                                             |
| `ucp-agent`       | Cond.\**   | Profile URL (binds identity)                                          |
| `signature-agent` | Cond.\***  | WBA-style key directory (when [WBA Interop](#wba-interop) opted into) |
| `idempotency-key` | Cond.\**** | Idempotency header (state-changing)                                   |
| `content-digest`  | Cond.†     | Body digest (if body present)                                         |
| `content-type`    | Cond.†     | Content-Type (if body present)                                        |

\* Required if request has query parameters

\** Required if `UCP-Agent` header is present

\*** Required if `Signature-Agent` header is present (i.e., WBA-shape signature)

\**** Required for POST, PUT, DELETE, PATCH

† Required if request has a body

**Signature Generation:**

```text
sign_rest_request(method, path, query, body_bytes, idempotency_key, private_key, kid):
    // 1. Compute body digest (if body present)
    if body_bytes:
        digest = sha256(body_bytes)  // Hash raw bytes, no canonicalization
        digest_header = "sha-256=:" + base64(digest) + ":"

    // 2. Build component list
    components = ["@method", "@authority", "@path"]
    if query: components.append("@query")
    if ucp_agent: components.append("ucp-agent")
    if idempotency_key: components.append("idempotency-key")
    if body: components.extend(["content-digest", "content-type"])

    // 3. Build signature base (RFC 9421)
    signature_base = build_signature_base(
        components=components,
        method=method,
        path=path,
        query=query,
        headers={
            "idempotency-key": idempotency_key,
            "content-digest": digest_header,
            "content-type": "application/json"
        },
        keyid=kid
    )

    // 4. Sign
    signature = sign(signature_base, private_key)  // ecdsa for EC, eddsa for OKP

    // 5. Return headers
    return {
        "Idempotency-Key": idempotency_key,
        "Content-Digest": digest_header,
        "Signature-Input": format_signature_input(components, kid),
        "Signature": "sig1=:" + base64(signature) + ":"
    }
```

**Signature Encoding:**

* **ECDSA** signatures **MUST** use fixed-width raw `r||s` encoding per
  RFC 9421 §3.3.1, **not** ASN.1/DER. The signature value is the
  concatenation of `r` and `s` as fixed-length unsigned big-endian
  integers: 64 bytes for P-256 (32 + 32), 96 bytes for P-384 (48 + 48).
  Many crypto libraries (OpenSSL, Java, .NET) default to DER encoding and
  require explicit conversion.
* **EdDSA (Ed25519)** signatures **MUST** use the encoding defined by
  RFC 8032 §5.1.6 — the 64-byte concatenation of the encoded `R` point
  and the integer `S`. This is the standard output of Ed25519 signing
  libraries; no DER conversion is involved.

**Complete Request Example:**

<!-- ucp:example schema=shopping/checkout op=create direction=request -->
```json
POST /checkout-sessions HTTP/1.1
Host: merchant.example.com
Content-Type: application/json
UCP-Agent: profile="https://platform.example/.well-known/ucp"
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Digest: sha-256=:X48E9q...:
Signature-Input: sig1=("@method" "@authority" "@path" "ucp-agent" "idempotency-key" "content-digest" "content-type");keyid="platform-2026"
Signature: sig1=:MEUCIQDTxNq8h7LGHpvVZQp1iHkFp9+3N8Mxk2zH1wK4YuVN8w...:

{
  "line_items": [
    {
      "item": {"id": "item_123"},
      "quantity": 2
    }
  ]
}
```

**GET Request Example (no body, no idempotency):**

```http
GET /checkout-sessions/chk_123 HTTP/1.1
Host: merchant.example.com
Signature-Input: sig1=("@method" "@authority" "@path");keyid="platform-2026"
Signature: sig1=:MEQCIBx7kL9nM2oP5qR8sT1uV4wX6yZaB3cD...:
```

### REST Response Signing

Response signatures use `@status` instead of `@method`:

**Signed Components:**

| Component        | Required | Description                       |
| :--------------- | :------- | :-------------------------------- |
| `@status`        | Yes      | HTTP status code (200, 201, etc.) |
| `content-digest` | Cond.*   | Body digest (if body present)     |
| `content-type`   | Cond.*   | Content-Type (if body present)    |

\* Required if response has a body

**Complete Response Example:**

The response body below is abbreviated for clarity — only the key fields
used in signing are shown. A full checkout response includes additional
required fields (`ucp`, `currency`, `line_items`, `totals`, `links`); see
[Create Checkout response](checkout-rest.md#create-checkout) for the
complete shape.

```http
HTTP/1.1 201 Created
Content-Type: application/json
Content-Digest: sha-256=:Y5fK8nLmPqRsT3vWxYzAbCdEfGhIjKlMnO...:
Signature-Input: sig1=("@status" "content-digest" "content-type");created=1738617601;keyid="merchant-2026"
Signature: sig1=:MFQCIH7kL9nM2oP5qR8sT1uV4wX6yZaB3cD...:

{
  "id": "chk_123",
  "status": "ready_for_complete",
  "...": "abbreviated; see linked spec for full shape"
}
```

**Response Signature Generation:**

Response signing mirrors request signing with `@status` replacing `@method`:

```text
sign_rest_response(status, body_bytes, private_key, kid):
    // 1. Compute body digest (if body present)
    if body_bytes:
        digest = sha256(body_bytes)  // Hash raw bytes, no canonicalization
        digest_header = "sha-256=:" + base64(digest) + ":"

    // 2. Build signature base (RFC 9421)
    signature_base = build_signature_base(
        components=["@status", "content-digest", "content-type"],
        status=status,
        headers={"content-digest": digest_header, "content-type": "application/json"},
        created=current_timestamp(),
        keyid=kid
    )

    // 3. Sign
    signature = sign(signature_base, private_key)  // ecdsa for EC, eddsa for OKP

    // 4. Return headers
    return {
        "Content-Digest": digest_header,
        "Signature-Input": 'sig1=("@status" "content-digest" "content-type");created=...;keyid="..."',
        "Signature": "sig1=:" + base64(signature) + ":"
    }
```

### REST Request Verification

**Determining the Signer's Key Directory:**

UCP and Web Bot Auth define parallel verification regimes; the
signature's `tag` parameter determines which header carries the key
directory pointer.

1. **WBA-shape signatures** (`tag="web-bot-auth"`) resolve the key
   directory via the **`Signature-Agent`** header — an RFC 8941
   Dictionary Structured Field whose member's sf-string value is
   the HTTPS directory URL. The dictionary key matches the signature
   label in `Signature-Input`. See [WBA Interop](#wba-interop).
2. **Default UCP signatures** (without `tag="web-bot-auth"`) resolve
   the key directory via the **`UCP-Agent`** header — the UCP profile
   URL in RFC 8941 Dictionary form.

Sites supporting WBA interop emit **both** headers: `UCP-Agent` for
capability discovery and default UCP key lookup; `Signature-Agent`
for WBA-shape key lookup.

For the full identity resolution algorithm (including directory self-
signature verification and inline-form handling), see
[Identity Resolution Algorithm](overview.md#identity-resolution-algorithm).

**`UCP-Agent` parsing rules** (default UCP regime):

1. Parse as RFC 8941 Dictionary
2. Extract the `profile` key (REQUIRED)
3. Value MUST be a quoted string containing an HTTPS URL
4. For business profiles, URL MUST point to `/.well-known/ucp`; platform
   profile URLs are not path-constrained
5. Reject non-HTTPS URLs

**`Signature-Agent` parsing rules** (WBA-shape regime):

1. Parse as RFC 8941 Dictionary.
2. **MUST** locate the dictionary member whose key equals the
   signature label being verified (for `Signature-Input: sig1=...`,
   find member `sig1`). If no matching member exists, verification
   of this signature **MUST** fail.
3. The member's value **MUST** be an sf-string containing an HTTPS
   URL pointing to a JWK Set per RFC 7517 (which **MAY** also be a
   UCP profile in JWKS-superset form). `data:` URI inline form is
   out of scope for UCP-WBA interop (see
   [Identity Resolution](overview.md#identity-resolution-algorithm)).
4. Verification of this signature **MUST** fail if the URL is
   non-HTTPS.

**Example (default UCP):**

```text
// Header
UCP-Agent: profile="https://platform.example/.well-known/ucp"

// Parsed
profile_url = "https://platform.example/.well-known/ucp"
```

**Example (Signature-Agent, WBA-shape):**

```text
// Headers
Signature-Agent: sig1="https://platform.example/.well-known/ucp"
Signature-Input: sig1=("@method" "@authority" ...);...

// Parsed (member key matches sig1)
directory_url = "https://platform.example/.well-known/ucp"
```

**Applicability:**

* **Platform → Business requests:** Profile URL from `UCP-Agent` header
* **Business → Platform webhooks:** Profile URL from `UCP-Agent` header

```text
verify_rest_request(request):
    // 1. Parse Signature-Input
    sig_input = parse_signature_input(request.headers["Signature-Input"])
    keyid = sig_input.keyid
    components = sig_input.components

    // 2. Fetch signer's public key
    // See overview.md#identity-resolution-algorithm for the full algorithm.
    // The signature's tag selects the verification regime:
    //   tag="web-bot-auth"  -> resolve via Signature-Agent (WBA-shape);
    //                          read keys from top-level keys[] (RFC 7517).
    //   no/other tag        -> resolve via UCP-Agent (default UCP);
    //                          read keys from signing_keys[].
    directory = resolve_key_directory(request.headers, sig_input.tag)
    public_key = find_key_by_kid(directory, keyid)
    if not public_key:
        return error("key_not_found")

    // 2a. Skip keys whose algorithm this verifier does not support.
    // The kty/crv/alg vocabularies are open (see Signature Algorithms);
    // an unsupported key never invalidates the whole key set.
    if not algorithm_supported(public_key):
        return error("algorithm_unsupported")

    // 3. Verify body digest (if body present)
    if "content-digest" in components:
        expected = "sha-256=:" + base64(sha256(request.body_bytes)) + ":"
        if request.headers["Content-Digest"] != expected:
            return error("digest_mismatch")

    // 4. Reconstruct signature base
    signature_base = build_signature_base(
        components, request.method, request.path, request.query,
        request.headers, keyid
    )

    // 5. Verify signature
    signature = parse_signature(request.headers["Signature"])
    if not verify(signature_base, signature, public_key):
        return error("signature_invalid")

    return success()

    // Note: Replay protection handled by the signed idempotency-key header
```

### REST Response Verification

Response verification mirrors request verification with `@status` replacing
`@method`:

```text
verify_rest_response(response, signer_profile_url):
    // 1. Parse Signature-Input
    sig_input = parse_signature_input(response.headers["Signature-Input"])
    keyid = sig_input.keyid
    components = sig_input.components

    // 2. Fetch signer's public key (regime-aware: keys[] for WBA-shape,
    // signing_keys[] for default UCP; see overview.md#identity-resolution-algorithm)
    profile = fetch_profile(signer_profile_url)
    public_key = find_key_by_kid(profile, keyid)
    if not public_key:
        return error("key_not_found")

    // 2a. Skip keys whose algorithm this verifier does not support.
    // The kty/crv/alg vocabularies are open (see Signature Algorithms);
    // an unsupported key never invalidates the whole key set.
    if not algorithm_supported(public_key):
        return error("algorithm_unsupported")

    // 3. Verify body digest (if body present)
    if "content-digest" in components:
        expected = "sha-256=:" + base64(sha256(response.body_bytes)) + ":"
        if response.headers["Content-Digest"] != expected:
            return error("digest_mismatch")

    // 4. Reconstruct signature base
    signature_base = build_signature_base(
        components, response.status,
        response.headers, keyid
    )

    // 5. Verify signature
    signature = parse_signature(response.headers["Signature"])
    if not verify(signature_base, signature, public_key):
        return error("signature_invalid")

    return success()
```

### Replay Protection

UCP handles replay protection at the **business layer** through idempotency keys,
not at the signature layer. This provides separation of concerns:

| Layer | Responsibility |
| :---- | :------------- |
| **Signature** | Authentication (who), Integrity (what) |
| **Idempotency** | Safe retries, Replay protection |

**How it works:**

1. State-changing operations include an `idempotency-key` in the request
2. The idempotency key is part of the signed payload
3. Attackers cannot modify the key without invalidating the signature
4. Duplicate requests return cached responses (no new side effects)

**Idempotency Key Placement:**

The `Idempotency-Key` header is included in the signed components:

```http
POST /checkout-sessions HTTP/1.1
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Signature-Input: sig1=("@method" "@authority" "@path" "idempotency-key" ...);keyid="platform-2026"
Signature: sig1=:MEUCIQD...:
```

**Idempotency Key Requirements:**

| Requirement | Value |
| :---------- | :---- |
| **Entropy** | Minimum 128 bits (e.g., UUID v4, 22+ char alphanumeric) |
| **Uniqueness** | Per-client, per-operation type |
| **Server storage** | Minimum 24 hours, recommended 48 hours |
| **On duplicate** | Return cached response, do not re-execute |
| **On storage failure** | Fail closed (reject request with 503) |

**Note:** The RFC 9421 `created` parameter is **OPTIONAL**. UCP handles replay
protection at the business layer through idempotency keys, not signature timestamps.
Key rotation (removing compromised keys from the profile's published key
set) provides the mechanism
for invalidating old signatures.

### When Signatures Apply

**Requests:** Platforms **SHOULD** sign all requests when using HTTP Message
Signatures. Alternative authentication mechanisms (API keys, OAuth, mTLS) may
be used instead.

**Webhooks:** Webhook notifications **MUST** be signed. Recipients cannot
otherwise verify authenticity of server-initiated push messages.

**Other responses:** Signatures are **RECOMMENDED** for:

* Payment authorization responses
* Checkout completion responses

Signatures are **OPTIONAL** for:

* Cart operations (low-value, synchronous)
* Catalog queries (read-only)
* Error responses (4xx, 5xx)

## MCP Transport

UCP specifies **streamable HTTP** for MCP transport, replacing SSE-based transports.
Since MCP requests are standard HTTP requests with JSON-RPC bodies, the same
RFC 9421 signature mechanism applies:

* The `Content-Digest` header covers the JSON-RPC message body
* The `Signature-Input` and `Signature` headers provide authentication
* The `UCP-Agent` and `Idempotency-Key` headers work identically to REST

**Example MCP Request with Signature:**

```http
POST /mcp HTTP/1.1
Host: business.example.com
Content-Type: application/json
UCP-Agent: profile="https://platform.example/.well-known/ucp"
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Digest: sha-256=:RK/0qy18MlBSVnWgjwz6lZEWjP/lF5HF9bvEF8FabDg=:
Signature-Input: sig1=("@method" "@authority" "@path" "content-digest" "content-type" "ucp-agent" "idempotency-key");keyid="platform-2026"
Signature: sig1=:MEUCIQDXyK9N3p5Rt...:

{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"complete_checkout","arguments":{"id":"chk_123","checkout":{...}}}}
```

The JSON-RPC message is the HTTP body. `Content-Digest` binds it to the signature.
No JSON canonicalization is required.

## Error Handling

Signature verification errors use standard UCP error codes. See
[Error Handling](overview.md#error-handling) in the specification overview for
the complete error code registry and transport bindings.

**Signature-specific errors:**

| Code                    | HTTP | Description                                          |
| :---------------------- | :--- | :--------------------------------------------------- |
| `signature_missing`     | 401  | Required signature header/field not present          |
| `signature_invalid`     | 401  | Signature verification failed                        |
| `key_not_found`         | 401  | Key ID not found in signer's published key set       |
| `digest_mismatch`       | 400  | Body digest doesn't match `Content-Digest` header    |
| `algorithm_unsupported` | 400  | Signature algorithm not supported                    |

**Profile-related errors** (also used for capability negotiation):

| Code                    | HTTP | Description                                               |
| :---------------------- | :--- | :-------------------------------------------------------- |
| `invalid_profile_url`   | 400  | Profile URL malformed or invalid scheme                   |
| `profile_unreachable`   | 424  | Unable to fetch signer's profile                          |
| `profile_not_trusted`   | 403  | Profile URL not in registry of pre-approved platforms     |

**Note:** Replay protection is handled at the business layer through idempotency
keys, not at the signature layer. Duplicate requests return cached responses
rather than signature errors.

### REST Error Response

```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "code": "signature_invalid",
  "content": "Request signature verification failed for key kid=platform-2026"
}
```

### MCP Error Response

<!-- ucp:example schema=transports/jsonrpc def=error_response -->
```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "error": {
    "code": -32000,
    "message": "Signature verification failed",
    "data": {
      "code": "signature_invalid",
      "content": "Signature verification failed for key kid=platform-2026"
    }
  }
}
```

## References

* [RFC 7517](https://datatracker.ietf.org/doc/html/rfc7517) — JSON Web Key (JWK)
* [RFC 7518](https://datatracker.ietf.org/doc/html/rfc7518) — JSON Web Algorithms (JWA), §6.2 (EC public keys)
* [RFC 8032](https://datatracker.ietf.org/doc/html/rfc8032) — Edwards-Curve Digital Signature Algorithm (EdDSA)
* [RFC 8037](https://datatracker.ietf.org/doc/html/rfc8037) — CFRG Elliptic Curve Diffie-Hellman (ECDH) and Signatures in JOSE
* [RFC 9421](https://www.rfc-editor.org/rfc/rfc9421) — HTTP Message Signatures
* [RFC 9530](https://www.rfc-editor.org/rfc/rfc9530) — Digest Fields (Content-Digest)
