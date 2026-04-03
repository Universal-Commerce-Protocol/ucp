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

# Identity Linking Capability

- **Capability Name:** `dev.ucp.common.identity_linking`

## Overview

The Identity Linking capability enables a **platform** (e.g., Google, an agentic
service) to obtain authorization to perform actions on behalf of a user on a
**business**'s site.

This linkage is foundational for commerce experiences, such as accessing loyalty
benefits, utilizing personalized offers, managing wishlists, and executing
authenticated checkouts.

**This specification implements a Mechanism Registry pattern**, allowing
platforms and businesses to negotiate the authentication mechanism dynamically.
While
<a href="https://datatracker.ietf.org/doc/html/rfc6749" target="_blank">OAuth
2.0</a> is the primary recommended mechanism, the design natively supports
future extensibility securely.

## Mechanism Registry Pattern

The Identity Linking capability configuration acts as a **registry** of
supported authentication mechanisms. Platforms and businesses discover and
negotiate the mechanism exactly like other UCP capabilities.

### UCP Capability Declaration

Businesses **MUST** declare the supported mechanisms in the capability `config`
using the `supported_mechanisms` array. Each mechanism must dictate its `type`
using an open string vocabulary (e.g., `oauth2`, `wallet_attestation`,
`verifiable_credential`) and provide the necessary resolution endpoints (like
`issuer` for OAuth or `provider_jwks` for wallet attestation).

```json
{
    "dev.ucp.common.identity_linking": [
        {
            "version": "2026-03-14",
            "config": {
                "supported_mechanisms": [
                    {
                        "type": "oauth2",
                        "issuer": "https://auth.merchant.example.com"
                    }
                ]
            }
        }
    ]
}
```

### Mechanism Selection Algorithm

The `supported_mechanisms` array is **ordered by the business's preference**
(index 0 = highest priority). Platforms **MUST** use the following algorithm to
select a mechanism:

1. Iterate the `supported_mechanisms` array from index 0 (first element).
2. For each entry, check whether the platform supports the declared `type`.
3. Select the **first** entry whose `type` the platform supports and proceed
   with that mechanism.
4. If no entry in the array has a `type` the platform supports, the platform
   **MUST** abort the identity linking process. The platform **MUST NOT**
   attempt a partial or fallback linking flow.

If the platform supports multiple `type` values that appear in the array, the
business's ordering takes precedence — the platform **MUST** use whichever
supported type appears first in the array, regardless of the platform's own
internal preference.

## Capability-Driven Scope Negotiation (Least Privilege)

To maintain the **Principle of Least Privilege**, authorization scopes are
**NOT** hardcoded within the identity linking capability.

Instead, **authorization scopes are dynamically derived from the final
intersection of negotiated capabilities**.

1. **Schema Declaration:** Each individual capability schema explicitly defines
   its own required identity scopes (e.g., `dev.ucp.shopping.checkout` declares
   `dev.ucp.shopping.scopes.checkout_session`).
2. **Dynamic Derivation:** During UCP Discovery, when the platform computes the
   intersection of supported capabilities between itself and the business, it
   extracts the required scopes from **only** the successfully negotiated
   capabilities.
3. **Authorization:** The platform initiates the connection requesting **exactly**
   the derived scopes — the union of `identity_scopes` from all capabilities in
   the finalized intersection. If a capability (e.g., `order`) is excluded from
   the active capability set, its respective scopes **MUST NOT** be requested by
   the platform. If the final derived scope list is completely empty, the platform
   **MUST** abort the identity linking process, as there are no secured resources
   to authorize.

### Scope Structure & Mapping

Consent screens **MUST** present permissions to users in clear, human-readable
language that accurately describes what access is being granted. Rather than
listing each individual operation (Get, Create, Update, Delete, etc.) as a
separate line, consent screens **SHOULD** group them under a single
capability-level description (e.g., "Allow \[platform\] to manage checkout
sessions"). This grouping is for readability — it **MUST NOT** reduce the
transparency of what access the user is authorizing. A scope grants access to
all operations associated with the capability and the consent screen must
accurately reflect that.

### Scope Naming Convention

Scopes **MUST** use **reverse DNS dot notation**, consistent with UCP capability
names, to prevent namespace collisions:

- **UCP-defined scopes:** `dev.ucp.<domain>.scopes.<capability>` (e.g.,
  `dev.ucp.shopping.scopes.checkout_session`)
- **Third-party scopes:** `<reverse-dns>.scopes.<capability>` (e.g.,
  `com.example.loyalty.scopes.points_balance`)

This format strictly adheres to the scope token syntax defined in
[RFC 6749 Section 3.3](https://datatracker.ietf.org/doc/html/rfc6749#section-3.3).

Example capability-to-scope mapping based on UCP schemas:

| Resources       | Operation                                     | Scope Action                               |
| :-------------- | :-------------------------------------------- | :----------------------------------------- |
| CheckoutSession | Get, Create, Update, Cancel, Complete         | `dev.ucp.shopping.scopes.checkout_session` |

## Supported Mechanisms

### OAuth 2.0 (`"type": "oauth2"`)

When the negotiated mechanism type is `oauth2`, platforms and businesses
**MUST** adhere to the following standard parameters.

#### Discovery Bridging

When a platform encounters `"type": "oauth2"`, it **MUST** parse the capability
configuration and securely locate the Authorization Server metadata.

Platforms **MUST** implement the following resolution hierarchy to determine the
discovery URL:

1. **Explicit Endpoint (Highest Priority)**: If the capability configuration
   provides a `discovery_endpoint` string, the platform **MUST** fetch metadata
   directly from that exact URI. If this fetch fails (e.g., non-2xx HTTP response
   or connection timeout), the platform **MUST** abort the discovery process and
   **MUST NOT** fall back to any other endpoints.
2. **RFC 8414 Standard Discovery**: If no explicit endpoint is provided, the
   platform **MUST** append `/.well-known/oauth-authorization-server` to the
   defined `issuer` string and fetch. If this fetch returns any non-2xx response
   other than `404 Not Found` (e.g., `500 Internal Server Error`, `503 Service
   Unavailable`), or if a connection timeout or network error occurs, the
   platform **MUST** abort the discovery process and **MUST NOT** proceed to the
   OIDC fallback.
3. **OIDC Fallback (Lowest Priority)**: If and only if the RFC 8414 fetch
   returns exactly `404 Not Found`, the platform **MUST** append
   `/.well-known/openid-configuration` to the defined `issuer` string and fetch.
   If this final fetch returns any non-2xx response or a network error, the
   platform **MUST** abort the identity linking process.

**Issuer Validation**: Regardless of the discovery method used above, the
platform **MUST** perform an exact string comparison between the `issuer` value
returned in the metadata and the `issuer` string defined in the capability
configuration, as required by
[RFC 8414 Section 3.3](https://datatracker.ietf.org/doc/html/rfc8414#section-3.3).
No normalization (e.g., trailing slash stripping) is permitted — the comparison
**MUST** be an exact string comparison.

Businesses **MUST** ensure the `issuer` string declared in their UCP capability
configuration exactly matches both the `issuer` field in their authorization
server metadata and the `iss` claim in any issued JWT access tokens. This
guarantees that standard JWT validation libraries, which perform exact string
equality on `iss`, will succeed without modification.

Failure to validate the issuer exposes the integration to Mix-Up Attacks and
**MUST** result in an aborted linking process.

Example metadata retrieved via RFC 8414:

```json
{
    "issuer": "https://auth.merchant.example.com",
    "authorization_endpoint": "https://auth.merchant.example.com/oauth2/authorize",
    "token_endpoint": "https://auth.merchant.example.com/oauth2/token",
    "revocation_endpoint": "https://auth.merchant.example.com/oauth2/revoke",
    "scopes_supported": [
        "dev.ucp.shopping.scopes.checkout_session"
    ],
    "response_types_supported": [
        "code"
    ],
    "grant_types_supported": [
        "authorization_code",
        "refresh_token"
    ]
}
```

#### For platforms

- **MUST** authenticate using their `client_id` and `client_secret`
  (<a href="https://datatracker.ietf.org/doc/html/rfc6749#section-2.3.1" target="_blank">RFC
  6749 2.3.1</a>) through HTTP Basic Authentication
  (<a href="https://datatracker.ietf.org/doc/html/rfc7617" target="_blank">RFC
  7617</a>) when exchanging codes for tokens.
    - **MAY** support Client Metadata
    - **MAY** support Dynamic Client Registration mechanisms to supersede static
      credential exchange.
- The platform must include the token in the HTTP Authorization header using the
  Bearer schema (`Authorization: Bearer <access_token>`)
- **MUST** implement the OAuth 2.0 Authorization Code flow
  (<a href="https://datatracker.ietf.org/doc/html/rfc6749#section-4.1" target="_blank">RFC
  6749 4.1</a>) as the primary linking mechanism.
- **MUST** strictly implement Proof Key for Code Exchange (PKCE)
  ([RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636)) using the `S256`
  challenge method to prevent authorization code interception attacks.
- **MUST** securely validate the `iss` parameter returned in the authorization
  response ([RFC 9207](https://www.rfc-editor.org/rfc/rfc9207.html)) to prevent
  Mix-Up Attacks.
- **SHOULD** include a unique, unguessable state parameter in the authorization
  request to prevent Cross-Site Request Forgery (CSRF)
  (<a href="https://datatracker.ietf.org/doc/html/rfc6749#section-10.12" target="_blank">RFC
  6749 10.12</a>).
- Revocation and security events
    - **SHOULD** call the business's revocation endpoint
      (<a href="https://datatracker.ietf.org/doc/html/rfc7009" target="_blank">RFC
      7009</a>) when a user initiates an unlink action on the platform side.
    - **SHOULD** support
      [OpenID RISC Profile 1.0](https://openid.net/specs/openid-risc-1_0-final.html)
      to handle asynchronous account updates, unlinking events, and
      cross-account protection.

#### For businesses

- **MUST** implement OAuth 2.0
  ([RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749))
- **MUST** adhere to [RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414)
  to declare the location of their OAuth 2.0 endpoints
  (`/.well-known/oauth-authorization-server`)
- **MUST** populate `scopes_supported` in their RFC 8414 metadata to allow
  platforms to detect scope mismatches early, before initiating the authorization
  flow.
- **MUST** enforce Client Authentication at the Token Endpoint.
- **MUST** enforce exact string matching for the `redirect_uri` parameter during
  the authorization request to prevent open redirects and token theft.
- **MUST** enforce Proof Key for Code Exchange (PKCE)
  ([RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636)) validation at the
  Token Endpoint for all authorization code exchanges.
- **MUST** return the `iss` parameter in the authorization response
  ([RFC 9207](https://www.rfc-editor.org/rfc/rfc9207.html)) matching the
  established issuer string.
- **MUST** provide an account creation flow if the user does not already have an
  account.
- **MUST** support dynamically requested UCP scopes mapped strictly to the
  capabilities actively negotiated in the session.
- Revocation and security events
    - **MUST** implement standard Token Revocation as defined in
      [RFC 7009](https://datatracker.ietf.org/doc/html/rfc7009).
    - **MUST** revoke the specified token and **SHOULD** recursively revoke all
      associated tokens.
    - **SHOULD** support
      [OpenID RISC Profile 1.0](https://openid.net/specs/openid-risc-1_0-final.html)
      to enable Cross-Account Protection.

### Wallet Attestation (`"type": "wallet_attestation"`)

The wallet attestation mechanism enables commerce flows where the user's
blockchain wallet address serves as the identity. Instead of redirecting to an
authorization server and establishing an account link, the platform obtains a
cryptographically signed attestation of on-chain state (token holdings,
credentials, membership) from a third-party verification provider. The business
verifies this attestation offline using the provider's published JWKS.

This mechanism is appropriate when:

- The commerce action depends on **what the user holds**, not who they are
  (e.g., token-gated merchandise, holder-exclusive discounts, membership
  verification).
- No persistent account link is needed — each transaction is independently
  verifiable.
- The business wants to verify eligibility without requiring the user to create
  an account or complete an OAuth redirect flow.

#### JWKS Resolution

When a platform encounters `"type": "wallet_attestation"`, it **MUST** use the
`provider_jwks` URI from the mechanism configuration as the JWKS endpoint for
signature verification.

Platforms **MUST** fetch the JWKS document from `provider_jwks` and cache it
according to standard HTTP caching headers. If the fetch fails (non-2xx HTTP
response or connection timeout), the platform **MUST** abort the identity
linking process.

The JWKS document **MUST** conform to
[RFC 7517 (JSON Web Key)](https://datatracker.ietf.org/doc/html/rfc7517). Each
key in the `keys` array **MUST** include a `kid` (Key ID) field. Platforms
select the verification key by matching the `kid` from the attestation response
against the `kid` values in the JWKS.

#### Attestation Flow

The wallet attestation flow is stateless — no redirect, no token exchange, no
account creation:

1. The platform determines the user's wallet address (e.g., via a connected
   wallet or user input).
2. The platform sends a verification request to the `attestation_endpoint`
   (if provided in the mechanism configuration) with the wallet address and the
   conditions to verify.
3. The provider evaluates the conditions against on-chain state and returns a
   signed attestation containing at minimum:
    - `pass` (boolean) — whether all conditions were met.
    - `sig` — cryptographic signature over the attestation payload.
    - `kid` — identifier of the signing key, resolvable via the provider's JWKS.
4. The platform attaches the attestation to the cart or checkout object. If a
   dedicated attestation extension is available (e.g., a sibling map on the
   checkout object keyed by reverse-domain eligibility claims), the platform
   **SHOULD** use that extension. Otherwise, the platform **MAY** attach the
   attestation as an opaque extension property.
5. The business verifies the attestation offline: fetch JWKS from
   `provider_jwks`, select the key matching `kid`, verify `sig` over the
   canonical serialization of the attestation payload.

#### For platforms

- **MUST** obtain the user's wallet address before initiating the attestation
  flow.
- **MUST** send verification requests to the `attestation_endpoint` declared in
  the mechanism configuration. If `attestation_endpoint` is not provided, the
  platform **MUST** determine the provider's endpoint through out-of-band
  configuration.
- **MUST** verify that the attestation response contains `sig`, `kid`, and a
  payload with a `pass` boolean before relaying it to the business.
- **MUST** check `expiresAt` (if present) and discard expired attestations
  before attaching them to cart or checkout objects.
- **SHOULD** cache JWKS responses according to HTTP caching headers to avoid
  redundant fetches.

#### For businesses

- **MUST** declare `provider_jwks` in the mechanism configuration pointing to
  the JWKS endpoint of each attestation provider they trust.
- **MUST** verify attestation signatures offline using the published JWKS. The
  business fetches the JWKS, selects the key whose `kid` matches the
  attestation's `kid`, and verifies `sig` over the canonical JSON serialization
  of the attestation payload.
- **MUST** reject attestations where `kid` does not match any key in the
  declared JWKS.
- **MUST** check `expiresAt` and reject expired attestations.
- **MUST NOT** trust attestation results without signature verification — the
  `pass` boolean alone is not sufficient.
- **MAY** accept attestations from multiple providers by listing multiple
  `wallet_attestation` entries in `supported_mechanisms`, each with a different
  `provider_jwks`.

#### Scope Considerations

The wallet attestation mechanism does not require OAuth 2.0 scopes.
Verification is stateless and self-contained — there is no authorization grant,
no access token, and no persistent session. Capabilities that use wallet
attestation exclusively (without also requiring OAuth) contribute zero scopes to
the derived scope set. The pruning algorithm in the
[overview specification](overview.md) already handles this correctly:
capabilities without `identity_scopes` are retained in the intersection without
affecting the authorization scope union.

## End-to-End Workflow & Example

### Scenario: An AI Shopping Agent (Platform) and a Shopping Merchant (Business)

#### 1. The Merchant's Profile (`/.well-known/ucp`)

The Merchant supports checkout, order management, and secure identity features.

```json
{
  "dev.ucp.shopping.checkout": [{ "version": "2026-03-14", "config": {} }],
  "dev.ucp.shopping.order": [{ "version": "2026-03-14", "config": {} }],
  "dev.ucp.common.identity_linking": [{
    "version": "2026-03-14",
    "config": {
      "supported_mechanisms": [{
        "type": "oauth2",
        "issuer": "https://auth.merchant.example.com"
      }]
    }
  }]
}
```

#### 2. The AI Agent's Profile

The AI Shopping Agent only knows how to perform checkouts. It does NOT yet know how to manage existing orders.

```json
{
  "dev.ucp.shopping.checkout": [{ "version": "2026-03-14" }],
  "dev.ucp.common.identity_linking": [{ "version": "2026-03-14" }]
}
```

#### 3. Execution Steps

1. **Capability Discovery & Intersection**: The AI Agent intersects its own profile
   with the business's and successfully negotiates `dev.ucp.shopping.checkout`
   and `dev.ucp.common.identity_linking`. `dev.ucp.shopping.order` is strictly
   excluded because the agent does not support it.
2. **Schema Fetch & Dynamic Scope Derivation**: The agent fetches the JSON Schema
   definitions for the **Active Capability List** (`checkout.json` and
   `identity_linking.json`). The agent parses the schema logic for
   `dev.ucp.shopping.checkout`, looking for the top-level `"identity_scopes"`
   annotation, and statically derives that the required scope is strictly
   `dev.ucp.shopping.scopes.checkout_session`. `dev.ucp.shopping.scopes.order_management`
   is inherently omitted.
3. **Identity Mechanism Selection & Execution**: The agent applies the
   Mechanism Selection Algorithm to the business's `supported_mechanisms` array.
   The first (and only) entry has `type: oauth2`, which the agent supports, so
   it is selected. The agent executes standard OAuth discovery (appending
   `/.well-known/oauth-authorization-server` to the issuer string) and validates
   that the returned `issuer` is an exact string match to the configured value.
4. **User Consent & Authorization**: The agent generates a consent URL to prompt
   the user (or invokes the authorization flow directly in the GUI), using the
   dynamically derived scopes.

    ```http
    GET https://auth.merchant.example.com/oauth2/authorize
      ?response_type=code
      &client_id=shopping_agent_client_123
      &redirect_uri=https://shoppingagent.com/callback
      &scope=dev.ucp.shopping.scopes.checkout_session
      &state=xyz123
      &code_challenge=code_challenge_123
      &code_challenge_method=S256
    ```

    The business will respond with the authorization code and the `iss`
    parameter per RFC 9207:

    ```http
    HTTP/1.1 302 Found
    Location: https://shoppingagent.com/callback
      ?code=code123
      &state=xyz123
      &iss=https://auth.merchant.example.com
    ```

    *The user is prompted to consent **only** to "Manage Checkout Sessions".*

5. **Authorized UCP Execution**: The platform securely exchanges the
   authorization code for an `access_token` bound only to checkout and
   successfully utilizes the UCP REST APIs via
   `Authorization: Bearer <access_token>`.

### Scenario: Token-Gated Commerce with Wallet Attestation

#### 1. The Merchant's Profile (`/.well-known/ucp`)

The Merchant sells token-gated merchandise. Holders of a specific token receive
exclusive discounts. The merchant supports both OAuth (for account-linked
experiences) and wallet attestation (for token-gated eligibility).

```json
{
  "dev.ucp.shopping.checkout": [{ "version": "2026-03-14", "config": {} }],
  "dev.ucp.common.identity_linking": [{
    "version": "2026-03-14",
    "config": {
      "supported_mechanisms": [
        {
          "type": "wallet_attestation",
          "provider_jwks": "https://verifier.example.com/.well-known/jwks.json",
          "attestation_endpoint": "https://verifier.example.com/v1/attest"
        },
        {
          "type": "oauth2",
          "issuer": "https://auth.merchant.example.com"
        }
      ]
    }
  }]
}
```

#### 2. The AI Agent's Profile

The AI Shopping Agent supports both wallet attestation and OAuth.

```json
{
  "dev.ucp.shopping.checkout": [{ "version": "2026-03-14" }],
  "dev.ucp.common.identity_linking": [{ "version": "2026-03-14" }]
}
```

#### 3. Execution Steps

1. **Capability Discovery & Intersection**: The agent intersects profiles and
   negotiates `dev.ucp.shopping.checkout` and
   `dev.ucp.common.identity_linking`.
2. **Identity Mechanism Selection**: The agent applies the Mechanism Selection
   Algorithm. The first entry is `wallet_attestation`, which the agent supports,
   so it is selected (business preference takes priority).
3. **Wallet Address Resolution**: The agent determines the user's wallet address
   — for example, by prompting the user to connect their wallet or reading a
   previously stored address.
4. **Attestation Request**: The agent sends a verification request to the
   `attestation_endpoint`:

    ```http
    POST https://verifier.example.com/v1/attest
    Content-Type: application/json

    {
      "wallet": "0x1234...abcd",
      "conditions": [
        {
          "type": "token_balance",
          "contractAddress": "0xabcd...1234",
          "chainId": 1,
          "threshold": 1,
          "decimals": 18
        }
      ]
    }
    ```

5. **Attestation Response**: The provider returns a signed attestation:

    ```json
    {
      "attestation": {
        "id": "ATST-3F7A2B1C9D4E8F06",
        "pass": true,
        "results": [{ "condition": 0, "met": true }],
        "attestedAt": "2026-03-18T12:00:00Z",
        "expiresAt": "2026-03-18T12:30:00Z"
      },
      "sig": "MEUCIQDx...base64...==",
      "kid": "verifier-key-v1"
    }
    ```

6. **Attach to Checkout**: The agent attaches the attestation to the checkout
   object as an extension property, keyed by the eligibility claim:

    ```json
    {
      "extensions": {
        "com.merchant.token_holder": {
          "provider_jwks": "https://verifier.example.com/.well-known/jwks.json",
          "kid": "verifier-key-v1",
          "attestation": { "id": "ATST-3F7A2B1C9D4E8F06", "pass": true, "results": [{ "condition": 0, "met": true }], "attestedAt": "2026-03-18T12:00:00Z", "expiresAt": "2026-03-18T12:30:00Z" },
          "sig": "MEUCIQDx...base64...=="
        }
      }
    }
    ```

7. **Business Verification (Offline)**: The merchant fetches the JWKS from
   `https://verifier.example.com/.well-known/jwks.json`, selects the key with
   `kid: "verifier-key-v1"`, verifies the signature over the canonical JSON
   serialization of the `attestation` object, checks that `expiresAt` has not
   passed, and reads `attestation.pass` to determine eligibility. If verified,
   the token-gated discount is applied. No network call to the attestation
   provider is needed at verification time.
