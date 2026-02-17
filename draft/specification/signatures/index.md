# Message Signatures

This specification defines how UCP messages are cryptographically signed to ensure authenticity and integrity.

## Overview

This specification defines how to sign and verify UCP messages using [RFC 9421](https://www.rfc-editor.org/rfc/rfc9421) HTTP Message Signatures. For UCP's identity model, supported authentication mechanisms, and key discovery protocol, see [Identity & Authentication](https://ucp.dev/draft/specification/overview/#identity--authentication).

HTTP Message Signatures protect against:

- **Impersonation** — Attackers sending messages claiming to be legitimate participants
- **Tampering** — Modification of message contents in transit
- **Replay attacks** — Captured messages resent to different endpoints or at different times
- **Method/endpoint confusion** — Signed payloads replayed with different HTTP methods or to different paths

### Architecture

UCP uses HTTP Message Signatures ([RFC 9421](https://www.rfc-editor.org/rfc/rfc9421)) for all HTTP-based transports:

```text
┌─────────────────────────────────────────────────────────────────┐
│                     SHARED FOUNDATION                           │
├─────────────────────────────────────────────────────────────────┤
│  Signature Format: RFC 9421 (HTTP Message Signatures)           │
│  Body Digest: RFC 9530 (Content-Digest, raw bytes)              │
│  Algorithms: ES256 (required), ES384 (optional)                 │
│  Key Format: JWK (RFC 7517)                                     │
│  Key Discovery: signing_keys[] in /.well-known/ucp              │
│  Replay Protection: idempotency-key (business layer)            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     HTTP TRANSPORTS                             │
├─────────────────────────────────────────────────────────────────┤
│  REST API: Standard HTTP requests                               │
│  MCP: Streamable HTTP transport (JSON-RPC over HTTP)            │
├─────────────────────────────────────────────────────────────────┤
│  Headers:                                                       │
│    Signature-Input    (describes signed components)             │
│    Signature          (contains signature value)                │
│    Content-Digest     (body hash, raw bytes)                    │
└─────────────────────────────────────────────────────────────────┘
```

**Note:** UCP specifies streamable HTTP for MCP transport, replacing SSE-based transports. This allows the same RFC 9421 signature mechanism to apply uniformly across all UCP transports.

## Shared Foundation

The following cryptographic primitives are shared across all UCP HTTP transports.

### Signature Algorithms

UCP supports ECDSA signatures with the following curves:

| Curve | JWK `alg` | Hash    |
| ----- | --------- | ------- |
| P-256 | `ES256`   | SHA-256 |
| P-384 | `ES384`   | SHA-384 |

**Implementation requirements:**

- All implementations **MUST** support verifying P-256 (`ES256`) signatures
- Support for P-384 (`ES384`) is **OPTIONAL**

**Usage guidance:**

- Signers **SHOULD** use P-256 for maximum compatibility
- Signers **MAY** use P-384 when both parties support it
- The algorithm is derived from the key's `crv` field in the JWK; `alg` is **NOT** included in `Signature-Input` parameters

### Key Format (JWK)

Public keys **MUST** be represented using **JSON Web Key (JWK)** format as defined in [RFC 7517](https://datatracker.ietf.org/doc/html/rfc7517).

**EC Key Structure:**

| Field | Type   | Required | Description                        |
| ----- | ------ | -------- | ---------------------------------- |
| `kid` | string | Yes      | Key ID (referenced in signatures)  |
| `kty` | string | Yes      | Key type (`EC` for elliptic curve) |
| `crv` | string | Yes\*    | Curve name (`P-256`, `P-384`)      |
| `x`   | string | Yes\*    | X coordinate (base64url encoded)   |
| `y`   | string | Yes\*    | Y coordinate (base64url encoded)   |
| `use` | string | No       | Key usage (`sig` for signing)      |
| `alg` | string | No       | Algorithm (`ES256`, `ES384`)       |

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

Public keys are published in the `signing_keys` array of the party's UCP profile at `/.well-known/ucp`. For the complete key discovery protocol, profile trust model, and profile fetch requirements, see [Identity & Authentication — Key Discovery](https://ucp.dev/draft/specification/overview/#key-discovery).

### Key Rotation

To rotate keys without service interruption:

1. **Add new key** — Publish new key in `signing_keys[]` alongside existing keys
1. **Start signing** — Begin signing with the new key
1. **Grace period** — Continue accepting signatures from old keys (minimum 7 days)
1. **Remove old key** — Remove the old key from `signing_keys[]`

**Recommendations:**

- Rotate keys every 90 days
- Support multiple active keys during transitions
- Verifiers: accept any key in `signing_keys[]`

**Key Compromise Response:**

1. Immediately remove compromised key from profile
1. Add new key with different `kid`
1. Reject all signatures made with compromised key

## REST Binding

For HTTP REST transport, UCP uses [RFC 9421 (HTTP Message Signatures)](https://www.rfc-editor.org/rfc/rfc9421).

### Headers

| Header            | Direction        | Required | Description                           |
| ----------------- | ---------------- | -------- | ------------------------------------- |
| `Signature-Input` | Request/Response | Yes      | Describes signed components           |
| `Signature`       | Request/Response | Yes      | Contains signature value              |
| `Content-Digest`  | Request/Response | Cond.\*  | SHA-256 hash of request/response body |

\* Required when request/response has a body

`Content-Digest` follows [RFC 9530](https://www.rfc-editor.org/rfc/rfc9530) and hashes the raw body bytes. This binds the message body to the signature without requiring JSON canonicalization. Implementations **MUST** use `sha-256`. For durable artifacts requiring canonicalization, see [AP2 Mandates - Canonicalization](https://ucp.dev/draft/specification/ap2-mandates/#canonicalization).

**Intermediary Warning:** Proxies, API gateways, and other intermediaries **MUST NOT** re-serialize JSON bodies, as this would invalidate the signature. The `Content-Digest` is computed over raw bytes; any modification breaks verification.

### REST Request Signing

**Signed Components:**

| Component         | Required    | Description                             |
| ----------------- | ----------- | --------------------------------------- |
| `@method`         | Yes         | HTTP method (GET, POST, etc.)           |
| `@authority`      | Yes         | Target host (prevents cross-host relay) |
| `@path`           | Yes         | Request path                            |
| `@query`          | Cond.\*     | Query string (if present)               |
| `ucp-agent`       | Cond.\*\*   | Profile URL (binds identity)            |
| `idempotency-key` | Cond.\*\*\* | Idempotency header (state-changing)     |
| `content-digest`  | Cond.†      | Body digest (if body present)           |
| `content-type`    | Cond.†      | Content-Type (if body present)          |

\* Required if request has query parameters * *Required if `UCP-Agent` header is present \**\* Required for POST, PUT, DELETE, PATCH † Required if request has a body

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
    signature = ecdsa_sign(signature_base, private_key)

    // 5. Return headers
    return {
        "Idempotency-Key": idempotency_key,
        "Content-Digest": digest_header,
        "Signature-Input": format_signature_input(components, kid),
        "Signature": "sig1=:" + base64(signature) + ":"
    }
```

**Signature Encoding:** ECDSA signatures **MUST** use fixed-width raw `r||s` encoding per RFC 9421, **not** ASN.1/DER. The signature value is the concatenation of `r` and `s` as fixed-length unsigned big-endian integers: 64 bytes for P-256 (32 + 32), 96 bytes for P-384 (48 + 48). Many crypto libraries (OpenSSL, Java, .NET) default to DER encoding and require explicit conversion.

**Complete Request Example:**

```http
POST /checkout-sessions HTTP/1.1
Host: merchant.example.com
Content-Type: application/json
UCP-Agent: profile="https://platform.example/.well-known/ucp"
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Digest: sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:
Signature-Input: sig1=("@method" "@authority" "@path" "ucp-agent" "idempotency-key" "content-digest" "content-type");keyid="platform-2026"
Signature: sig1=:MEUCIQDTxNq8h7LGHpvVZQp1iHkFp9+3N8Mxk2zH1wK4YuVN8w...:

{"checkout":{"line_items":[{"id":"prod_123","quantity":2}]}}
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
| ---------------- | -------- | --------------------------------- |
| `@status`        | Yes      | HTTP status code (200, 201, etc.) |
| `content-digest` | Cond.\*  | Body digest (if body present)     |
| `content-type`   | Cond.\*  | Content-Type (if body present)    |

\* Required if response has a body

**Complete Response Example:**

```http
HTTP/1.1 201 Created
Content-Type: application/json
Content-Digest: sha-256=:Y5fK8nLmPqRsT3vWxYzAbCdEfGhIjKlMnO...:
Signature-Input: sig1=("@status" "content-digest" "content-type");created=1738617601;keyid="merchant-2026"
Signature: sig1=:MFQCIH7kL9nM2oP5qR8sT1uV4wX6yZaB3cD...:

{"checkout":{"id":"chk_123","status":"ready_for_complete"}}
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
    signature = ecdsa_sign(signature_base, private_key)

    // 4. Return headers
    return {
        "Content-Digest": digest_header,
        "Signature-Input": 'sig1=("@status" "content-digest" "content-type");created=...;keyid="..."',
        "Signature": "sig1=:" + base64(signature) + ":"
    }
```

### REST Request Verification

**Determining Signer's Profile URL:**

The signer's profile URL is obtained from the `UCP-Agent` header, which uses [RFC 8941 Dictionary](https://www.rfc-editor.org/rfc/rfc8941#section-3.2) syntax:

```text
UCP-Agent: profile="https://platform.example/.well-known/ucp"
```

**Parsing Rules:**

1. Parse as RFC 8941 Dictionary
1. Extract the `profile` key (REQUIRED)
1. Value MUST be a quoted string containing an HTTPS URL
1. For business profiles, URL MUST point to `/.well-known/ucp`; platform profile URLs are not path-constrained
1. Reject non-HTTPS URLs

**Example:**

```text
// Header
UCP-Agent: profile="https://platform.example/.well-known/ucp"

// Parsed
profile_url = "https://platform.example/.well-known/ucp"
```

**Applicability:**

- **Platform → Business requests:** Profile URL from `UCP-Agent` header
- **Business → Platform webhooks:** Profile URL from `UCP-Agent` header

```text
verify_rest_request(request):
    // 1. Parse Signature-Input
    sig_input = parse_signature_input(request.headers["Signature-Input"])
    keyid = sig_input.keyid
    components = sig_input.components

    // 2. Fetch signer's public key
    // See overview.md#profile-requirements for URL validation and fetch rules
    profile_url = get_profile_url_from_ucp_agent(request.headers["UCP-Agent"])
    profile = fetch_profile(profile_url)  // HTTPS-only, no redirects
    public_key = find_key_by_kid(profile.signing_keys, keyid)
    if not public_key:
        return error("key_not_found")

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
    if not ecdsa_verify(signature_base, signature, public_key):
        return error("signature_invalid")

    return success()

    // Note: Replay protection handled by idempotency keys in request payload
```

### REST Response Verification

Response verification mirrors request verification with `@status` replacing `@method`:

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
    if not ecdsa_verify(signature_base, signature, public_key):
        return error("signature_invalid")

    return success()
```

### Replay Protection

UCP handles replay protection at the **business layer** through idempotency keys, not at the signature layer. This provides separation of concerns:

| Layer           | Responsibility                         |
| --------------- | -------------------------------------- |
| **Signature**   | Authentication (who), Integrity (what) |
| **Idempotency** | Safe retries, Replay protection        |

**How it works:**

1. State-changing operations include an `idempotency-key` in the request
1. The idempotency key is part of the signed payload
1. Attackers cannot modify the key without invalidating the signature
1. Duplicate requests return cached responses (no new side effects)

**Idempotency Key Placement:**

The `Idempotency-Key` header is included in the signed components:

```http
POST /checkout-sessions HTTP/1.1
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Signature-Input: sig1=("@method" "@authority" "@path" "idempotency-key" ...);keyid="platform-2026"
Signature: sig1=:MEUCIQD...:
```

**Idempotency Key Requirements:**

| Requirement            | Value                                                   |
| ---------------------- | ------------------------------------------------------- |
| **Entropy**            | Minimum 128 bits (e.g., UUID v4, 22+ char alphanumeric) |
| **Uniqueness**         | Per-client, per-operation type                          |
| **Server storage**     | Minimum 24 hours, recommended 48 hours                  |
| **On duplicate**       | Return cached response, do not re-execute               |
| **On storage failure** | Fail closed (reject request with 503)                   |

**Note:** The RFC 9421 `created` parameter is **OPTIONAL**. UCP handles replay protection at the business layer through idempotency keys, not signature timestamps. Key rotation (removing compromised keys from `signing_keys`) provides the mechanism for invalidating old signatures.

### When Signatures Apply

**Requests:** Platforms **SHOULD** sign all requests when using HTTP Message Signatures. Alternative authentication mechanisms (API keys, OAuth, mTLS) may be used instead.

**Webhooks:** Webhook notifications **MUST** be signed. Recipients cannot otherwise verify authenticity of server-initiated push messages.

**Other responses:** Signatures are **RECOMMENDED** for:

- Payment authorization responses
- Checkout completion responses

Signatures are **OPTIONAL** for:

- Cart operations (low-value, synchronous)
- Catalog queries (read-only)
- Error responses (4xx, 5xx)

## MCP Transport

UCP specifies **streamable HTTP** for MCP transport, replacing SSE-based transports. Since MCP requests are standard HTTP requests with JSON-RPC bodies, the same RFC 9421 signature mechanism applies:

- The `Content-Digest` header covers the JSON-RPC message body
- The `Signature-Input` and `Signature` headers provide authentication
- The `UCP-Agent` and `Idempotency-Key` headers work identically to REST

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

The JSON-RPC message is the HTTP body. `Content-Digest` binds it to the signature. No JSON canonicalization is required.

## Error Handling

Signature verification errors use standard UCP error codes. See [Error Handling](https://ucp.dev/draft/specification/overview/#error-handling) in the specification overview for the complete error code registry and transport bindings.

**Signature-specific errors:**

| Code                    | HTTP | Description                                       |
| ----------------------- | ---- | ------------------------------------------------- |
| `signature_missing`     | 401  | Required signature header/field not present       |
| `signature_invalid`     | 401  | Signature verification failed                     |
| `key_not_found`         | 401  | Key ID not found in signer's `signing_keys`       |
| `digest_mismatch`       | 400  | Body digest doesn't match `Content-Digest` header |
| `algorithm_unsupported` | 400  | Signature algorithm not supported                 |

**Profile-related errors** (also used for capability negotiation):

| Code                  | HTTP | Description                                           |
| --------------------- | ---- | ----------------------------------------------------- |
| `invalid_profile_url` | 400  | Profile URL malformed or invalid scheme               |
| `profile_unreachable` | 424  | Unable to fetch signer's profile                      |
| `profile_not_trusted` | 403  | Profile URL not in registry of pre-approved platforms |

**Note:** Replay protection is handled at the business layer through idempotency keys, not at the signature layer. Duplicate requests return cached responses rather than signature errors.

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

- [RFC 7517](https://datatracker.ietf.org/doc/html/rfc7517) — JSON Web Key (JWK)
- [RFC 9421](https://www.rfc-editor.org/rfc/rfc9421) — HTTP Message Signatures
- [RFC 9530](https://www.rfc-editor.org/rfc/rfc9530) — Digest Fields (Content-Digest)
