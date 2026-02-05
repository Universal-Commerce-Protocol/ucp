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
ensure authenticity and integrity across all transports (REST, MCP) and
directions (requests and responses).

## Overview

UCP message signatures protect against:

* **Impersonation** — Attackers sending messages claiming to be legitimate
    participants
* **Tampering** — Modification of message contents in transit
* **Replay attacks** — Captured messages resent to different endpoints or at
    different times
* **Method/endpoint confusion** — Signed payloads replayed with different
    HTTP methods or to different paths

### Architecture

UCP uses a layered signature architecture that maximizes cryptographic reuse
while allowing protocol-appropriate signature formats:

```text
┌─────────────────────────────────────────────────────────────────┐
│                     SHARED FOUNDATION                           │
├─────────────────────────────────────────────────────────────────┤
│  Canonicalization: JCS (RFC 8785)                               │
│  Algorithms: ES256 (required), ES384, ES512                     │
│  Key Format: JWK (RFC 7517)                                     │
│  Key Discovery: signing_keys[] in /.well-known/ucp              │
│  Replay Protection: idempotency-key (business layer)            │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│      REST BINDING       │     │      MCP BINDING        │
├─────────────────────────┤     ├─────────────────────────┤
│ Format: RFC 9421        │     │ Format: RFC 7515 App F  │
│ Headers:                │     │ Location:               │
│   Signature             │     │   meta.signature        │
│   Signature-Input       │     │   meta.idempotency-key  │
│   UCP-Content-Digest-JCS│     │   meta.ucp-agent        │
└─────────────────────────┘     └─────────────────────────┘
```

## Shared Foundation

The following cryptographic primitives are shared across all UCP transports
and signature contexts.

### JSON Canonicalization (JCS)

All JSON payloads **MUST** be canonicalized using **JSON Canonicalization
Scheme (JCS)** as defined in
[RFC 8785](https://datatracker.ietf.org/doc/html/rfc8785) before signing.

JCS produces a deterministic, byte-for-byte identical representation of JSON
data, ensuring signatures can be verified regardless of:

* Whitespace differences
* Key ordering variations
* Unicode normalization
* Number formatting

**Canonicalization Rules:**

1. Object keys sorted lexicographically (by UTF-16 code units)
2. No insignificant whitespace
3. Numbers in shortest IEEE 754 representation
4. Strings use minimal escape sequences

**Example:**

```json
// Input (any formatting)
{
  "checkout": {
    "buyer": {"email": "alice@example.com"},
    "line_items": [{"id": "prod_123", "quantity": 2, "price": 1000}]
  }
}

// JCS output (deterministic)
{"checkout":{"buyer":{"email":"alice@example.com"},"line_items":[{"id":"prod_123","price":1000,"quantity":2}]}}
```

### Signature Algorithms

UCP supports ECDSA signatures with the following algorithms:

| Algorithm | Curve   | Hash    |
| :-------- | :------ | :------ |
| `ES256`   | P-256   | SHA-256 |
| `ES384`   | P-384   | SHA-384 |
| `ES512`   | P-521   | SHA-512 |

**Implementation requirements:**

* All implementations **MUST** support verifying `ES256` signatures
* Support for `ES384` and `ES512` is **OPTIONAL**

**Usage guidance:**

* Signers **SHOULD** use `ES256` for maximum compatibility
* Signers **MAY** use `ES384` or `ES512` when both parties support them
* The algorithm is indicated by the `alg` field in the signing key's JWK

### Key Format (JWK)

Public keys **MUST** be represented using **JSON Web Key (JWK)** format as
defined in [RFC 7517](https://datatracker.ietf.org/doc/html/rfc7517).

**EC Key Structure:**

| Field | Type   | Required | Description                              |
| :---- | :----- | :------- | :--------------------------------------- |
| `kid` | string | Yes      | Key ID (referenced in signatures)        |
| `kty` | string | Yes      | Key type (`EC` for elliptic curve)       |
| `crv` | string | Yes*     | Curve name (`P-256`, `P-384`, `P-521`)   |
| `x`   | string | Yes*     | X coordinate (base64url encoded)         |
| `y`   | string | Yes*     | Y coordinate (base64url encoded)         |
| `use` | string | No       | Key usage (`sig` for signing)            |
| `alg` | string | No       | Algorithm (`ES256`, `ES384`, `ES512`)    |

\* Required for EC keys

**Example:**

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

### Key Discovery

Public keys are published in the `signing_keys` array of the party's UCP
profile at `/.well-known/ucp`.

**Business Profile:**

```json
{
  "ucp": { ... },
  "signing_keys": [
    {
      "kid": "merchant-2026",
      "kty": "EC",
      "crv": "P-256",
      "x": "WKn-ZIGevcwGIyyrzFoZNBdaq9_TsqzGl96oc0CWuis",
      "y": "y77t-RvAHRKTsSGdIYUfweuOvwrvDD-Q3Hv5J0fSKbE",
      "alg": "ES256"
    }
  ]
}
```

**Platform Profile:**

```json
{
  "ucp": { ... },
  "signing_keys": [
    {
      "kid": "platform-2026",
      "kty": "EC",
      "crv": "P-256",
      "x": "MKBCTNIcKUSDii11ySs3526iDZ8AiTo7Tu6KPAqv7D4",
      "y": "4Etl6SRW2YiLUrN5vfvVHuhp7x8PxltmWWlbbM4IFyM",
      "alg": "ES256"
    }
  ]
}
```

**Key Lookup:**

1. Extract `kid` (key ID) from signature header/parameter
2. Fetch signer's UCP profile from `/.well-known/ucp`
3. Search `signing_keys[]` for matching `kid`
4. Use the corresponding public key for verification

### Profile Trust Model

**Profile URLs** identify the signer and locate their public keys. Implementations
**MUST** validate profile URLs to prevent attacks where malicious actors use
attacker-controlled profiles.

**Validation Requirements:**

1. **HTTPS required** — Profile URLs **MUST** use `https://` scheme
2. **Well-known path** — URL **MUST** end with `/.well-known/ucp`
3. **No open redirects** — Reject profiles that redirect to different domains
4. **Domain binding** — The profile domain identifies the organization

Profile trust is typically established through:

* **Pre-registration** — Platform/business exchange profile URLs during onboarding
* **Capability negotiation** — Profile URL discovered from partner's profile
* **Allowlists** — Implementations MAY maintain explicit allowlists of trusted profiles

**Example Allowlist Check:**

```text
validate_profile_url(url, allowlist):
    // Parse and validate URL structure
    parsed = parse_url(url)
    if parsed.scheme != "https":
        return error("invalid_profile_url")
    if not parsed.path.endsWith("/.well-known/ucp"):
        return error("invalid_profile_url")

    // Check against allowlist (if configured)
    if allowlist and parsed.host not in allowlist:
        return error("profile_not_trusted")

    return success()
```

**Profile Caching:**

Implementations **SHOULD** cache fetched profiles to reduce latency and network
load. Recommended cache policy:

* **TTL:** 5-15 minutes for normal operations
* **Stale-while-revalidate:** Accept stale profile during background refresh
* **Force refresh:** On signature verification failure with unknown `kid`
* **No cache:** For key compromise scenarios (see Key Rotation)

### Key Rotation

To rotate keys without service interruption:

1. **Add new key** — Publish new key in `signing_keys[]` alongside existing keys
2. **Start signing** — Begin signing with the new key
3. **Grace period** — Continue accepting signatures from old keys (minimum 7 days)
4. **Remove old key** — Remove the old key from `signing_keys[]`

**Recommendations:**

* Rotate keys every 90 days
* Support multiple active keys during transitions
* Verifiers: accept any key in `signing_keys[]`

**Key Compromise Response:**

1. Immediately remove compromised key from profile
2. Add new key with different `kid`
3. Reject all signatures made with compromised key

## REST Binding

For HTTP REST transport, UCP uses
[RFC 9421 (HTTP Message Signatures)](https://www.rfc-editor.org/rfc/rfc9421).

### Headers

| Header                   | Direction        | Required | Description                          |
| :----------------------- | :--------------- | :------- | :----------------------------------- |
| `Signature-Input`        | Request/Response | Yes      | Describes signed components          |
| `Signature`              | Request/Response | Yes      | Contains signature value             |
| `UCP-Content-Digest-JCS` | Request/Response | Cond.*   | JCS-canonicalized body digest        |

\* Required when request/response has a body

**Why `UCP-Content-Digest-JCS`?** RFC 9530's `Content-Digest` hashes raw bytes.
UCP uses JCS canonicalization for JSON bodies, requiring a distinct header to
indicate the different semantics.

### REST Request Signing

**Signed Components:**

| Component                | Required | Description                             |
| :----------------------- | :------- | :-------------------------------------- |
| `@method`                | Yes      | HTTP method (GET, POST, etc.)           |
| `@path`                  | Yes      | Request path                            |
| `@query`                 | Cond.*   | Query string (if present)               |
| `idempotency-key`        | Cond.**  | Idempotency header (state-changing ops) |
| `ucp-content-digest-jcs` | Cond.*** | Body digest (if body present)           |
| `content-type`           | Cond.*** | Content-Type (if body present)          |

\* Required if request has query parameters
\** Required for POST, PUT, DELETE, PATCH
\*** Required if request has a body

**Signature Generation:**

```text
sign_rest_request(method, path, query, body, idempotency_key, private_key, kid):
    // 1. Compute body digest (if body present)
    if body:
        canonical = jcs_canonicalize(body)
        digest = sha256(canonical)
        digest_header = "sha-256=:" + base64(digest) + ":"

    // 2. Build component list
    components = ["@method", "@path"]
    if query: components.append("@query")
    if idempotency_key: components.append("idempotency-key")
    if body: components.extend(["ucp-content-digest-jcs", "content-type"])

    // 3. Build signature base (RFC 9421)
    signature_base = build_signature_base(
        components=components,
        method=method,
        path=path,
        query=query,
        headers={
            "idempotency-key": idempotency_key,
            "ucp-content-digest-jcs": digest_header,
            "content-type": "application/json"
        },
        keyid=kid
    )

    // 4. Sign
    signature = ecdsa_sign(signature_base, private_key)

    // 5. Return headers
    return {
        "Idempotency-Key": idempotency_key,
        "UCP-Content-Digest-JCS": digest_header,
        "Signature-Input": format_signature_input(components, kid),
        "Signature": "sig1=:" + base64(signature) + ":"
    }
```

**Complete Request Example:**

```http
POST /checkout-sessions HTTP/1.1
Host: merchant.example.com
Content-Type: application/json
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
UCP-Content-Digest-JCS: sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:
Signature-Input: sig1=("@method" "@path" "idempotency-key" "ucp-content-digest-jcs" "content-type");keyid="platform-2026"
Signature: sig1=:MEUCIQDTxNq8h7LGHpvVZQp1iHkFp9+3N8Mxk2zH1wK4YuVN8w...:

{"checkout":{"line_items":[{"id":"prod_123","quantity":2}]}}
```

**GET Request Example (no body, no idempotency):**

```http
GET /checkout-sessions/chk_123 HTTP/1.1
Host: merchant.example.com
Signature-Input: sig1=("@method" "@path");keyid="platform-2026"
Signature: sig1=:MEQCIBx7kL9nM2oP5qR8sT1uV4wX6yZaB3cD...:
```

### REST Response Signing

Response signatures use `@status` instead of `@method`:

**Signed Components:**

| Component                | Required | Description                      |
| :----------------------- | :------- | :------------------------------- |
| `@status`                | Yes      | HTTP status code (200, 201, etc.)|
| `ucp-content-digest-jcs` | Cond.*   | Body digest (if body present)    |
| `content-type`           | Cond.*   | Content-Type (if body present)   |

\* Required if response has a body

**Complete Response Example:**

```http
HTTP/1.1 201 Created
Content-Type: application/json
UCP-Content-Digest-JCS: sha-256=:Y5fK8nLmPqRsT3vWxYzAbCdEfGhIjKlMnO...:
Signature-Input: sig1=("@status" "ucp-content-digest-jcs" "content-type");created=1738617601;keyid="merchant-2026"
Signature: sig1=:MFQCIH7kL9nM2oP5qR8sT1uV4wX6yZaB3cD...:

{"checkout":{"id":"chk_123","status":"ready_for_complete"}}
```

**Response Signature Generation:**

Response signing mirrors request signing with `@status` replacing `@method`:

```text
sign_rest_response(status, body, private_key, kid):
    // 1. Compute body digest (if body present)
    if body:
        canonical = jcs_canonicalize(body)
        digest = sha256(canonical)
        digest_header = "sha-256=:" + base64(digest) + ":"

    // 2. Build signature base (RFC 9421)
    signature_base = build_signature_base(
        components=["@status", "ucp-content-digest-jcs", "content-type"],
        status=status,
        headers={"ucp-content-digest-jcs": digest_header, "content-type": "application/json"},
        created=current_timestamp(),
        keyid=kid
    )

    // 3. Sign
    signature = ecdsa_sign(signature_base, private_key)

    // 4. Return headers
    return {
        "UCP-Content-Digest-JCS": digest_header,
        "Signature-Input": 'sig1=("@status" "ucp-content-digest-jcs" "content-type");created=...;keyid="..."',
        "Signature": "sig1=:" + base64(signature) + ":"
    }
```

### REST Request Verification

**Determining Signer's Profile URL:**

The signer's profile URL is obtained from the `UCP-Agent` header, which uses
[RFC 8941 Dictionary](https://www.rfc-editor.org/rfc/rfc8941#section-3.2) syntax:

```text
UCP-Agent: profile="https://platform.example/.well-known/ucp"
```

**Parsing Rules:**

1. Parse as RFC 8941 Dictionary
2. Extract the `profile` key (REQUIRED)
3. Value MUST be a quoted string containing an HTTPS URL
4. URL MUST point to `/.well-known/ucp` at the signer's domain
5. Reject non-HTTPS URLs

**Example:**

```text
// Header
UCP-Agent: profile="https://platform.example/.well-known/ucp"

// Parsed
profile_url = "https://platform.example/.well-known/ucp"
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
    profile_url = get_profile_url_from_ucp_agent(request.headers["UCP-Agent"])
    validate_profile_url(profile_url)
    profile = fetch_profile(profile_url)
    public_key = find_key_by_kid(profile.signing_keys, keyid)
    if not public_key:
        return error("key_not_found")

    // 3. Verify body digest (if body present)
    if "ucp-content-digest-jcs" in components:
        canonical = jcs_canonicalize(request.body)
        expected = "sha-256=:" + base64(sha256(canonical)) + ":"
        if request.headers["UCP-Content-Digest-JCS"] != expected:
            return error("digest_mismatch")

    // 4. Reconstruct signature base
    signature_base = build_signature_base(
        components, request.method, request.path, request.query,
        request.headers, keyid
    )

    // 5. Verify signature
    signature = parse_signature(request.headers["Signature"])
    if not ecdsa_verify(signature_base, signature, public_key):
        return error("signature_invalid")

    return success()

    // Note: Replay protection handled by idempotency keys in request payload
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

    // 2. Fetch signer's public key
    profile = fetch_profile(signer_profile_url)
    public_key = find_key_by_kid(profile.signing_keys, keyid)
    if not public_key:
        return error("key_not_found")

    // 3. Verify body digest (if body present)
    if "ucp-content-digest-jcs" in components:
        canonical = jcs_canonicalize(response.body)
        expected = "sha-256=:" + base64(sha256(canonical)) + ":"
        if response.headers["UCP-Content-Digest-JCS"] != expected:
            return error("digest_mismatch")

    // 4. Reconstruct signature base
    signature_base = build_signature_base(
        components, response.status,
        response.headers, keyid
    )

    // 5. Verify signature
    signature = parse_signature(response.headers["Signature"])
    if not ecdsa_verify(signature_base, signature, public_key):
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

**Transport-specific placement:**

| Transport | Location                   | Signed via                   |
| :-------- | :------------------------- | :--------------------------- |
| REST      | `Idempotency-Key` header   | Include in signed components |
| MCP       | `meta.idempotency-key`     | JCS-canonicalized payload    |

**REST Example:**

```http
POST /checkout-sessions HTTP/1.1
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Signature-Input: sig1=("@method" "@path" "idempotency-key" ...);keyid="platform-2026"
Signature: sig1=:MEUCIQD...:
```

**MCP Example:**

```json
{"meta": {"idempotency-key": "550e8400-e29b-41d4-a716-446655440000", "signature": "...", ...}, ...}
```

**Idempotency Key Requirements:**

| Requirement | Value |
| :---------- | :---- |
| **Entropy** | Minimum 128 bits (e.g., UUID v4, 22+ char alphanumeric) |
| **Uniqueness** | Per-client, per-operation type |
| **Server storage** | Minimum 24 hours, recommended 48 hours |
| **On duplicate** | Return cached response, do not re-execute |
| **On storage failure** | Fail closed (reject request with 503) |

**Note:** The RFC 9421 `created` parameter is **OPTIONAL**. UCP does not require
timestamps for signature validity. Key rotation (removing compromised keys from
`signing_keys`) provides the mechanism for invalidating old signatures.

### When Signatures Are Required

**Requests:** All UCP REST requests **MUST** include signatures.

**Responses:** Signatures are **REQUIRED** for:

* Order webhook notifications
* Payment authorization responses
* Checkout completion responses

Signatures are **OPTIONAL** for:

* Cart operations (low-value, synchronous)
* Catalog queries (read-only)
* Error responses (4xx, 5xx)

## MCP Binding

For MCP (JSON-RPC) transport, UCP uses **JWS Detached Content** format as
defined in [RFC 7515 Appendix F](https://datatracker.ietf.org/doc/html/rfc7515#appendix-F).

### Signature Location

MCP uses JSON-RPC with `tools/call` method to invoke UCP tools. The layering is:

```text
JSON-RPC (transport) → MCP (tools/call) → UCP (tool arguments)
```

Signatures are included in the `meta` object within `params.arguments` (requests)
or `result` (responses). The signed payload is the **entire JSON-RPC message**
with only `meta.signature` removed.

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "method": "tools/call",
  "params": {
    "name": "create_checkout",
    "arguments": {
      "meta": {
        "ucp-agent": {"profile": "https://platform.example/.well-known/ucp"},
        "signature": "eyJhbGciOiJFUzI1NiIsImtpZCI6InBsYXRmb3JtLTIwMjUifQ..MEUCIQD...",
        "idempotency-key": "req_abc123"
      },
      "checkout": { ... }
    }
  }
}
```

**Response:**

```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "result": {
    "content": [{"type": "text", "text": "..."}],
    "structuredContent": {
      "meta": {
        "signature": "eyJhbGciOiJFUzI1NiIsImtpZCI6Im1lcmNoYW50LTIwMjUifQ..MFQCIH..."
      },
      "checkout": { ... }
    }
  }
}
```

### Meta Fields

| Field             | Type   | Required | Description                           |
| :---------------- | :----- | :------- | :------------------------------------ |
| `ucp-agent`       | object | Yes*     | Signer identity (see below)           |
| `signature`       | string | Yes      | Detached JWS (`header..signature`)    |
| `idempotency-key` | string | Cond.**  | Unique key for replay protection      |

\* Required for requests; responses use session context for signer identity
\** Required for state-changing operations (POST, PUT, DELETE, PATCH equivalents)

**Replay Protection:**

Replay protection is handled through **idempotency keys** in the `meta` object.
Since the entire message (minus `meta.signature`) is signed, attackers cannot
modify the idempotency key without invalidating the signature.

See [Replay Protection](#replay-protection) for details.

### Detached JWS Format

The `signature` field contains a JWS with detached content in the format:

```text
<base64url-header>..<base64url-signature>
```

The double dot (`..`) indicates the payload is transmitted separately (as the
JSON-RPC message itself).

**JWS Header Claims:**

| Claim | Type   | Required | Description                           |
| :---- | :----- | :------- | :------------------------------------ |
| `alg` | string | Yes      | Algorithm (`ES256`, `ES384`, `ES512`) |
| `kid` | string | Yes      | Key ID referencing `signing_keys`     |

### MCP Request Signing

The signed payload is the **entire JSON-RPC message** with only `meta.signature`
removed. This approach:

* Signs exactly what's sent on the wire (minus the signature itself)
* Keeps `idempotency-key` and `ucp-agent` in their natural location inside `meta`
* Works with MCP's `tools/call` pattern

**Signed Payload (wire format minus `meta.signature`):**

```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "method": "tools/call",
  "params": {
    "name": "create_checkout",
    "arguments": {
      "meta": {
        "ucp-agent": {"profile": "https://platform.example/.well-known/ucp"},
        "idempotency-key": "req_abc123"
      },
      "checkout": { ... }
    }
  }
}
```

**Signature Generation:**

```text
sign_mcp_request(message, private_key, kid):
    // 1. Build signed payload (entire message, excluding meta.signature)
    signed_payload = deep_copy(message)
    delete signed_payload.params.arguments.meta.signature  // Remove if present

    // 2. JCS-canonicalize
    canonical = jcs_canonicalize(signed_payload)

    // 3. Create JWS header
    header = {"alg": "ES256", "kid": kid}
    header_b64 = base64url(json(header))

    // 4. Sign (header + canonical payload)
    signing_input = header_b64 + "." + base64url(canonical)
    signature = ecdsa_sign(signing_input, private_key)

    // 5. Create detached JWS and add to message
    detached_jws = header_b64 + ".." + base64url(signature)
    message.params.arguments.meta.signature = detached_jws

    return message
```

### MCP Response Signing

Response signing follows the same pattern: sign the entire JSON-RPC message
with only `meta.signature` removed. For MCP responses, `meta` is inside
`result.structuredContent`.

**Signed Payload (wire format minus `meta.signature`):**

```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "result": {
    "content": [{"type": "text", "text": "..."}],
    "structuredContent": {
      "meta": {},
      "checkout": { ... }
    }
  }
}
```

Note: Response `meta` only contains `signature`. The `idempotency-key` is a
request-side concept; responses are inherently tied to their originating request.

**Signature Generation:**

```text
sign_mcp_response(message, private_key, kid):
    // 1. Ensure meta exists
    sc = message.result.structuredContent
    sc.meta = sc.meta || {}

    // 2. Build signed payload (entire message, excluding meta.signature)
    signed_payload = deep_copy(message)
    delete signed_payload.result.structuredContent.meta.signature

    // 3. JCS-canonicalize
    canonical = jcs_canonicalize(signed_payload)

    // 4. Create JWS header
    header = {"alg": "ES256", "kid": kid}
    header_b64 = base64url(json(header))

    // 5. Sign (header + canonical payload)
    signing_input = header_b64 + "." + base64url(canonical)
    signature = ecdsa_sign(signing_input, private_key)

    // 6. Create detached JWS and add to message
    detached_jws = header_b64 + ".." + base64url(signature)
    sc.meta.signature = detached_jws

    return message
```

### MCP Request Verification

```text
verify_mcp_request(message):
    // 1. Extract signature from meta (inside params.arguments)
    meta = message.params.arguments.meta
    detached_jws = meta.signature

    // 2. Parse JWS header
    [header_b64, _, signature_b64] = detached_jws.split(".")
    header = json(base64url_decode(header_b64))
    kid = header.kid
    alg = header.alg

    // 3. Fetch signer's public key
    profile_url = meta["ucp-agent"].profile
    validate_profile_url(profile_url)
    profile = fetch_profile(profile_url)
    public_key = find_key_by_kid(profile.signing_keys, kid)
    if not public_key:
        return error("key_not_found")

    // 4. Reconstruct signed payload (message minus meta.signature)
    signed_payload = deep_copy(message)
    delete signed_payload.params.arguments.meta.signature

    // 5. JCS-canonicalize
    canonical = jcs_canonicalize(signed_payload)

    // 6. Verify signature
    signing_input = header_b64 + "." + base64url(canonical)
    signature = base64url_decode(signature_b64)
    if not ecdsa_verify(signing_input, signature, public_key, alg):
        return error("signature_invalid")

    return success()

    // Note: Replay protection handled by idempotency keys at business layer
```

### MCP Response Verification

**Determining the Signer's Profile URL:**

For MCP responses, the verifier must know the responder's profile URL. This is
established through the session context:

* **Platform verifying business response:** Use the business profile URL from
  capability negotiation (the platform already fetched it to initiate the session)
* **Business verifying platform response:** Use the platform profile URL from
  the `ucp-agent` in the original request

The `signer_profile_url` parameter below represents this pre-established context.

```text
verify_mcp_response(message, signer_profile_url):
    // 1. Extract signature from result.structuredContent.meta
    meta = message.result.structuredContent.meta
    detached_jws = meta.signature

    // 2. Parse JWS header
    [header_b64, _, signature_b64] = detached_jws.split(".")
    header = json(base64url_decode(header_b64))
    kid = header.kid
    alg = header.alg

    // 3. Fetch signer's public key
    profile = fetch_profile(signer_profile_url)
    public_key = find_key_by_kid(profile.signing_keys, kid)
    if not public_key:
        return error("key_not_found")

    // 4. Reconstruct signed payload (message minus meta.signature)
    signed_payload = deep_copy(message)
    delete signed_payload.result.structuredContent.meta.signature

    // 5. JCS-canonicalize
    canonical = jcs_canonicalize(signed_payload)

    // 6. Verify signature
    signing_input = header_b64 + "." + base64url(canonical)
    signature = base64url_decode(signature_b64)
    if not ecdsa_verify(signing_input, signature, public_key, alg):
        return error("signature_invalid")

    return success()
```

### When Signatures Are Required

**Requests:** All UCP MCP requests **MUST** include signatures in `meta`.

**Responses:** Signatures are **REQUIRED** for:

* Checkout completion responses

Signatures are **OPTIONAL** for:

* Cart operations
* Catalog queries

## Error Handling

Signature verification errors use standard UCP error codes. See
[Error Handling](overview.md#error-handling) in the specification overview for
the complete error code registry and transport bindings.

**Signature-specific errors:**

| Code                    | HTTP | Description                                          |
| :---------------------- | :--- | :--------------------------------------------------- |
| `signature_missing`     | 401  | Required signature header/field not present          |
| `signature_invalid`     | 401  | Signature verification failed                        |
| `key_not_found`         | 401  | Key ID not found in signer's `signing_keys`          |
| `digest_mismatch`       | 400  | Body digest doesn't match `UCP-Content-Digest-JCS`   |
| `algorithm_unsupported` | 400  | Signature algorithm not supported                    |

**Profile-related errors** (also used for capability negotiation):

| Code                    | HTTP | Description                                          |
| :---------------------- | :--- | :--------------------------------------------------- |
| `invalid_profile_url`   | 400  | Profile URL malformed or invalid scheme              |
| `profile_unreachable`   | 424  | Unable to fetch signer's profile                     |
| `profile_not_trusted`   | 403  | Profile URL not in trusted allowlist                 |

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

* [RFC 7515](https://datatracker.ietf.org/doc/html/rfc7515) — JSON Web Signature (JWS)
* [RFC 7517](https://datatracker.ietf.org/doc/html/rfc7517) — JSON Web Key (JWK)
* [RFC 8785](https://datatracker.ietf.org/doc/html/rfc8785) — JSON Canonicalization Scheme (JCS)
* [RFC 9421](https://www.rfc-editor.org/rfc/rfc9421) — HTTP Message Signatures
