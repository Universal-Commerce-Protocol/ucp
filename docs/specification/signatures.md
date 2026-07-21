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
|  Algorithms: must verify ES256 (baseline); other algorithms     |
|              optional — open vocabulary, counterparty-driven    |
|              (see Signature Algorithms)                         |
|  Key Format: JWK (RFC 7517 + RFC 8037 for Ed25519)              |
|  Key Discovery: keys[] (RFC 7517 JWK Set) in /.well-known/ucp   |
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
* Support for `EdDSA` (Ed25519) is **OPTIONAL**. A WBA-aware verifier
  **SHOULD** support the algorithms its signers actually use (Ed25519 is
  the most common among WBA signers today); UCP imposes no algorithm
  requirement beyond the universal `ES256` baseline.
* The `kty`/`crv`/`alg` vocabularies are **open**. A verifier that
  encounters a key whose type, curve, or algorithm it does not support
  **MUST NOT** reject the published key set; the unsupported key simply
  remains unusable to that verifier. A signature that references such a
  key fails with `algorithm_unsupported` (and, in a multi-signature
  request, is skipped per the [Identity Resolution
  Algorithm](overview.md#identity-resolution-algorithm)).

**Usage guidance:**

* **Algorithm choice is counterparty-driven.** A signer **SHOULD** use an
  algorithm accepted by every verifier the same signature must satisfy —
  the receiving UCP verifier, plus any WBA verifier or AP2 layer it opts
  that signature into. One key suffices when a single algorithm satisfies
  all of them; publish multiple keys of different algorithms (selected
  per-signature by `kid`) only when no single algorithm does.
* **Default to `ES256`** absent a specific counterparty constraint — it is
  the universal UCP baseline and also a valid Web Bot Auth algorithm.
  (WBA's algorithm rules and the current deployment landscape are in
  [WBA Interop](#wba-interop).)
* **AP2 mandate signing follows AP2's own JWS algorithm rule** — see
  [AP2 Mandates](ap2-mandates.md). Its accepted algorithms do not extend the
  HTTP Message Signatures implementation requirements above.
* The algorithm is derived from the key's `kty`/`crv` field in the JWK;
  `alg` is **NOT** included in `Signature-Input` parameters.

**Number of signing keys.** How many keys a party publishes follows from
algorithm compatibility, not a UCP rule. One key suffices when a single
algorithm is accepted by every audience it signs for; separate keys
(selected by `kid`) are needed only when audiences impose incompatible
algorithm constraints — for example, a WBA verifier that accepts only
Ed25519 together with an AP2 mandate algorithm requirement that excludes
it (see [AP2 Mandates](ap2-mandates.md)). When one algorithm satisfies
every audience, a single key serves all of them. See
[Business Profile](overview.md#business-profile) for a two-key example.

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

<!-- ucp:example schema=profile extract=$ target=$.keys[0] -->
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

<!-- ucp:example schema=profile extract=$ target=$.keys[0] -->
```json
{
  "kid": "poqkLGiymh_W0uP6PZFw-dvez3QJT5SolqXBCW38r0U",
  "kty": "OKP",
  "crv": "Ed25519",
  "x": "JrQLj5P_89iXES9-vFgrIy29clF9CC_oPPsw3c5D0bs",
  "use": "sig",
  "alg": "EdDSA"
}
```

A key used for **dual-audience** signatures (those carrying
`tag="web-bot-auth"`) **MUST** publish its `kid` as the key's JWK SHA-256
Thumbprint ([RFC 7638](https://www.rfc-editor.org/rfc/rfc7638)) in every
array that lists it. The WBA-shape signature's `keyid` is that thumbprint,
and a UCP verifier resolves the key by matching `keyid` to a published
`kid`; setting both to the thumbprint lets the `UCP-Agent` and
`Signature-Agent` lookups find the same key. For other keys `kid` is an
opaque identifier (RFC 7517) and MAY be any stable value.

### Key Discovery

Public keys are published in the signer's UCP profile. See
[Profile Structure](overview.md#profile-structure) for the publishing
contract and [Key Discovery](overview.md#key-discovery) for the
verifier lookup rule (which key list to read for each resolution
mechanism).

### Key Rotation

To rotate keys without service interruption:

1. **Add new key** — Publish the new key in the profile's `keys[]`
   alongside existing keys
2. **Start signing** — Begin signing with the new key
3. **Grace period** — Continue accepting signatures from old keys (minimum 7 days)
4. **Remove old key** — Remove the old key from `keys[]`. A key still
   listed in `keys[]` continues to verify.

**Recommendations:**

* Operators SHOULD rotate keys every 90 days.
* Profiles SHOULD support multiple active keys during transitions.

**Key Compromise Response:**

1. Immediately remove the compromised key from `keys[]`; it continues
   to verify until absent from the array
2. Add new key with different `kid`
3. Reject all signatures made with compromised key

### WBA Interop

A UCP integrator MAY opt their primary signature into a Web Bot Auth-
compatible shape: a single **dual-audience** signature — one key, one
signing operation, one signature on the wire — that both a UCP verifier
(resolving via `UCP-Agent`) and a WBA verifier (resolving via
`Signature-Agent`) accept. This is the RECOMMENDED path for integrators
wanting interop with WBA-conformant verifiers; the requirements below
apply to any signature carrying `tag="web-bot-auth"`. WBA interop is
request-scoped: responses are signed with standard UCP signatures
(covering `@status`) and do not carry `tag="web-bot-auth"`.

**On the wire.** A dual-audience signature is a normal UCP signature with
a few additions: it carries a `Signature-Agent` header **alongside**
`UCP-Agent` (additive — `Signature-Agent` does not replace `UCP-Agent`),
signs the `signature-agent` component, uses the signing key's RFC 7638
thumbprint as `keyid`, and adds `created`, `expires`, and
`tag="web-bot-auth"`:

<!-- ucp:example schema=shopping/checkout op=create direction=request -->
```json
POST /checkout-sessions HTTP/1.1
Host: merchant.example.com
Content-Type: application/json
UCP-Agent: profile="https://platform.example/.well-known/ucp"
Signature-Agent: sig1="https://platform.example/.well-known/ucp";type=jwks_uri
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Digest: sha-256=:X48E9q...:
Signature-Input: sig1=("@method" "@authority" "@path" "signature-agent";key="sig1" "ucp-agent" "idempotency-key" "content-digest" "content-type");keyid="poqkLGiymh_W0uP6PZFw-dvez3QJT5SolqXBCW38r0U";created=1738617600;expires=1738621200;tag="web-bot-auth"
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

One signature on the wire, two audiences. UCP-shape verifiers resolve via
`UCP-Agent`, find their expected components (`ucp-agent`,
`idempotency-key`), and ignore the rest; WBA-shape verifiers resolve via
`Signature-Agent` and find theirs (`@authority`, `signature-agent`,
`tag`, `created`/`expires`). Both verify the same bytes against the same
key. Here both headers point at the same `/.well-known/ucp` URL
(`type=jwks_uri`, so WBA verifiers read the profile's `keys[]` as the JWK
Set — see
[Deployment Patterns](overview.md#deployment-patterns-for-wba-interop)),
but `Signature-Agent` MAY point elsewhere.

The three `sig1` labels are bound together — the `Signature-Agent`
dictionary member key, the `;key="sig1"` parameter on the signed
`signature-agent` component, and the `Signature-Input` signature label —
per item 3 of the opt-in list below.

To opt in, a signer makes the following changes to their primary UCP
signature. Items marked **MUST** are required by
[draft-meunier-webbotauth-httpsig-protocol-00](https://datatracker.ietf.org/doc/draft-meunier-webbotauth-httpsig-protocol/00/)
§4.2; consult that draft for full details.

1. **Use an algorithm the WBA verifier accepts.** WBA permits any
   algorithm in the RFC 9421 HTTP Message Signatures Algorithm registry
   (e.g. `ed25519`, `ecdsa-p256-sha256` = `ES256`, `ecdsa-p384-sha384`,
   `rsa-pss-sha512`). Confirm
   acceptance with your target verifiers. (Non-normative: Ed25519 is the
   most widely deployed today.)
2. **MUST send a `Signature-Agent` header** alongside `UCP-Agent`. An
   RFC 8941 Dictionary Structured Field whose member's sf-string value
   is an HTTPS URL and whose `type` parameter selects the discovery
   mechanism; the member key matches the `Signature-Input` signature
   label. See
   [Deployment Patterns](overview.md#deployment-patterns-for-wba-interop)
   for the `jwks_uri`/`cimd`/`directory` variants and how each can reuse
   the UCP profile. (`data:` URI inline form is out of scope.)
3. **MUST sign the `signature-agent` component with `;key="<label>"`**
   matching the `Signature-Agent` dictionary member key (which equals
   the `Signature-Input` signature label). Per WBA §4.2.1.
4. **MUST set `keyid` to the JWK SHA-256 Thumbprint** of the signing
   key per [RFC 7638](https://www.rfc-editor.org/rfc/rfc7638), and
   publish that key with `kid` set to the same thumbprint (see
   [Key Format](#key-format-jwk)) so the `UCP-Agent` and `Signature-Agent`
   lookups resolve it identically. For Ed25519 (OKP) keys, the thumbprint
   members are `crv`, `kty`, `x` per
   [RFC 8037](https://www.rfc-editor.org/rfc/rfc8037) §2; Appendix A.3 has
   a worked example.
5. **MUST include `created` and `expires` parameters.** The `expires`
   interval SHOULD be at most 24 hours.
6. **SHOULD include a `nonce`** for anti-replay — a base64url-encoded
   random value (RECOMMENDED 64 bytes), unique within the
   `created`/`expires` window (WBA §4.2.3). UCP's `Idempotency-Key` is
   business-layer payload deduplication, not a transport-bound nonce,
   and does not substitute. A verifying origin **MAY** require a `nonce` and
   re-challenge (HTTP 429) a signature that lacks or replays one
   (WBA §4.3–4.4).
7. **MUST include `tag="web-bot-auth"`.** WBA verifiers select
   signatures by this tag.

**Component requirements preserved — and enforced.** A WBA-shape
signature **MUST** still cover the same components a default UCP
signature does (the Required set in the
[Signed Components](#rest-request-signing) table); WBA accepts them as
"additional components" per
[draft-meunier-webbotauth-httpsig-protocol-00](https://datatracker.ietf.org/doc/draft-meunier-webbotauth-httpsig-protocol/00/)
§4.2.4. The verifier enforces this regardless of `tag` per the
[Identity Resolution Algorithm](overview.md#identity-resolution-algorithm),
so opting into Web Bot Auth never widens what UCP authenticates.

**Interop is one-way.** A UCP signer satisfies a Web Bot Auth
verifier — WBA verifiers accept UCP's richer covered set as
permitted "additional components" (protocol-00 §4.2.4). The
reverse does not hold: a minimal WBA signature (covering only
`@authority`) fails UCP's coverage gate and is rejected. UCP's goal
is to be verifiable *by* WBA verifiers, not to accept arbitrary WBA
signers — a UCP verifier accepts a strict subset of what a WBA
verifier does.

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
* `created` and `expires` are required in WBA-shape signatures
  (item 5, per WBA §4.2). Enforcing them is **application-defined**
  (RFC 9421 §3.2.1) — not an automatic consequence of RFC 9421
  conformance, and not separately mandated by UCP, whose own replay
  protection is the business-layer `Idempotency-Key`. A WBA-aware
  verifier enforcing freshness rejects out-of-window signatures.

**Identity resolution.** WBA opt-in does not change default UCP
verification; see
[Identity Resolution Algorithm](overview.md#identity-resolution-algorithm).

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

| Header            | Direction        | Required   | Description                                  |
| :---------------- | :--------------- | :--------- | :------------------------------------------- |
| `Signature-Input` | Request/Response | Yes        | Describes signed components                  |
| `Signature`       | Request/Response | Yes        | Contains signature value                     |
| `Content-Digest`  | Request/Response | Cond. `*`  | SHA-256 hash of request/response body        |
| `Signature-Agent` | Request          | Cond. `**` | WBA key source ([WBA Interop](#wba-interop)) |

* `*` Required when request/response has a body

* `**` Required when opting into Web Bot Auth-compatible signature shape;
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

| Component         | Required     | Description                                                  |
| :---------------- | :----------- | :----------------------------------------------------------- |
| `@method`         | Yes          | HTTP method (GET, POST, etc.)                                |
| `@authority`      | Yes          | Target host (prevents cross-host relay)                      |
| `@path`           | Yes          | Request path                                                 |
| `@query`          | Cond. `*`    | Query string (if present)                                    |
| `ucp-agent`       | Cond. `**`   | Profile URL (binds identity)                                 |
| `signature-agent` | Cond. `***`  | WBA key source (when [WBA Interop](#wba-interop) opted into) |
| `idempotency-key` | Cond. `****` | Idempotency header (state-changing)                          |
| `content-digest`  | Cond. `†`    | Body digest (if body present)                                |
| `content-type`    | Cond. `†`    | Content-Type (if body present)                               |

* `*` Required if request has query parameters

* `**` Required if `UCP-Agent` header is present

* `***` Required if `Signature-Agent` header is present (i.e., WBA-shape signature)

* `****` Required for POST, PUT, DELETE, PATCH

* `†` Required if request has a body

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

| Component        | Required   | Description                       |
| :--------------- | :--------- | :-------------------------------- |
| `@status`        | Yes        | HTTP status code (200, 201, etc.) |
| `content-digest` | Cond. `*`  | Body digest (if body present)     |
| `content-type`   | Cond. `*`  | Content-Type (if body present)    |

* `*` Required if response has a body

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

**Resolving the Signer's Keys:**

See
[Identity Resolution Algorithm](overview.md#identity-resolution-algorithm)
for the key-resolution rule (chosen by verifier capability and the
headers present, not by the signature's `tag`). This section specifies
header parsing only — `UCP-Agent` for the default UCP regime,
`Signature-Agent` for the WBA-shape regime.

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
   URL. Its `type` parameter selects resolution — `jwks_uri` (a JWK
   Set URL, e.g. the UCP profile), `cimd` (a Client ID Metadata
   Document), or `directory` (an origin hosting a well-known
   directory); see
   [Deployment Patterns](overview.md#deployment-patterns-for-wba-interop).
   `data:` URI inline form is out of scope for UCP-WBA interop.
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
Signature-Agent: sig1="https://platform.example/.well-known/ucp";type=jwks_uri
Signature-Input: sig1=("@method" "@authority" ...);...

// Parsed (member key matches sig1)
type = jwks_uri
jwks_uri = "https://platform.example/.well-known/ucp"
```

**Applicability:**

* **Platform → Business requests:** Profile URL from `UCP-Agent` header
* **Business → Platform webhooks:** Profile URL from `UCP-Agent` header

Both routines below verify a **single candidate** signature.
`skip_signature(reason)` means the candidate does not authenticate the
message: under multi-signature handling
([RFC 9421 §4.3](https://www.rfc-editor.org/rfc/rfc9421#section-4.3); see
the [Identity Resolution Algorithm](overview.md#identity-resolution-algorithm)),
the verifier tries the next candidate and rejects the message only when
**every** candidate skips. `success()` authenticates the message.

```text
verify_rest_request(request):
    // 1. Parse Signature-Input
    sig_input = parse_signature_input(request.headers["Signature-Input"])
    keyid = sig_input.keyid
    components = sig_input.components

    // 2. Resolve signer's public key (capability-based; see
    // overview.md#identity-resolution-algorithm).
    key_set = resolve_signer_key_set(request.headers)
    // sig_capable skips keys not usable for verification: use:"enc", or
    // key_ops present without "verify" (RFC 7517 §4.2, §4.3)
    public_key = find_key_by_kid(sig_capable(key_set), keyid)
    if not public_key:
        return skip_signature("key_not_found")

   // pre-2a. WBA-shape signatures bind key identity to key bytes:
   // keyid MUST equal the matched JWK's RFC 7638 thumbprint
   // (see IRA step 4 / WBA architecture draft §4.2).
   if sig_input.tag == "web-bot-auth":
       if keyid != rfc7638_thumbprint(public_key):
           return skip_signature("signature_invalid")
    // 2a. Skip keys whose algorithm this verifier does not support.
    // The kty/crv/alg vocabularies are open (see Signature Algorithms);
    // an unsupported key never invalidates the whole key set.
    if not algorithm_supported(public_key):
        return skip_signature("algorithm_unsupported")

    // 2b. Enforce covered-component requirements (all regimes/transports).
    // Bind the target, the body when present, and every integrity-relevant
    // header the request carries. A signature covering only WBA's minimum
    // (@authority, signature-agent) does not authenticate a request whose
    // body/method/path is unbound.
    // (Which requests must CARRY Idempotency-Key is a binding rule,
    // separate from this coverage check.)
    required = ["@method", "@authority", "@path"]
    if request.query:                        required += ["@query"]
    if request.has_body:                     required += ["content-digest", "content-type"]
    if "Idempotency-Key" in request.headers: required += ["idempotency-key"]
    if "UCP-Agent" in request.headers:       required += ["ucp-agent"]
    if "Signature-Agent" in request.headers: required += ["signature-agent"]
    for component in required:
        if component not in components:
            // coverage failure, a target/body/header the signature does not
            // cover is treated as unsigned (see IRA step 5)
            return skip_signature("coverage_insufficient")

    // 3. Verify body digest (if body present)
    if "content-digest" in components:
        expected = "sha-256=:" + base64(sha256(request.body_bytes)) + ":"
        if request.headers["Content-Digest"] != expected:
            return skip_signature("digest_mismatch")

    // 4. Reconstruct signature base
    signature_base = build_signature_base(
        components, request.method, request.path, request.query,
        request.headers, keyid
    )

    // 5. Verify signature
    signature = parse_signature(request.headers["Signature"])
    if not verify(signature_base, signature, public_key):
        return skip_signature("signature_invalid")

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

    // 2. Resolve signer's public key from the signer's profile.
    profile = fetch_profile(signer_profile_url)
    // signature-capable keys only (see request path; RFC 7517 §4.2, §4.3)
    public_key = find_key_by_kid(sig_capable(profile.keys), keyid)
    if not public_key:
        return skip_signature("key_not_found")

    // 2a. Skip keys whose algorithm this verifier does not support.
    // The kty/crv/alg vocabularies are open (see Signature Algorithms);
    // an unsupported key never invalidates the whole key set.
    if not algorithm_supported(public_key):
        return skip_signature("algorithm_unsupported")

    // 2b. Enforce covered-component requirements for responses (all regimes).
    // No method/idempotency to bind, but the body still MUST be covered.
    required = ["@status"]
    if response.has_body: required += ["content-digest", "content-type"]
    for component in required:
        if component not in components:
            return skip_signature("signature_invalid")

    // 3. Verify body digest (if body present)
    if "content-digest" in components:
        expected = "sha-256=:" + base64(sha256(response.body_bytes)) + ":"
        if response.headers["Content-Digest"] != expected:
            return skip_signature("digest_mismatch")

    // 4. Reconstruct signature base
    signature_base = build_signature_base(
        components, response.status,
        response.headers, keyid
    )

    // 5. Verify signature
    signature = parse_signature(response.headers["Signature"])
    if not verify(signature_base, signature, public_key):
        return skip_signature("signature_invalid")

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
| **On duplicate (matching payload)** | Return cached response, do not re-execute |
| **On duplicate (mismatched payload)** | Reject with `409 Conflict` (REST) / `-32000` (MCP); do not execute |
| **On storage failure** | Fail closed (reject request with 503) |

**Payload Matching:** Businesses **MUST** detect whether the payload of
a duplicate-key request matches the payload of the original by
comparing the SHA-256 hash of the raw body bytes — the same digest
RFC 9530 mandates as `Content-Digest`. When signing is in use, this
value is supplied in the `Content-Digest` header and the Intermediary
Warning above guarantees byte fidelity end-to-end; businesses persist
it alongside the idempotency key. For unsigned requests, businesses
compute the same digest from the received body bytes. Platforms
therefore **MUST** generate a fresh idempotency key whenever they
modify the request payload — including retries with modified payment
instruments, updated shipping addresses, swapped line items, or any
other change to the request body.

**Note:** For **default UCP** signatures, the RFC 9421 `created`
parameter is **OPTIONAL** and replay protection is handled at the
business layer through idempotency keys, not signature timestamps.
**WBA-shape** signatures additionally carry `created`/`expires` (and
SHOULD carry a `nonce`) for WBA verifiers; enforcing that freshness
window is application-defined (RFC 9421 §3.2.1). See
[WBA Interop](#wba-interop).
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
* The `UCP-Agent` header works identically to REST; `Idempotency-Key` is
  signed when present, but since every MCP request is a POST, whether one
  is required follows the JSON-RPC operation (state-changing), not the
  HTTP method

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
