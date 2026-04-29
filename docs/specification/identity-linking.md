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

* **Capability Name:** `dev.ucp.common.identity_linking`
* **Schema:** `https://ucp.dev/schemas/common/identity_linking.json`

## Overview

The Identity Linking capability enables a **platform** to obtain authorization
to perform actions on behalf of a **user** on a **business**'s (relying
party) site.

This linkage is foundational for user-authenticated commerce experiences: accessing
loyalty benefits, personalized offers, saved addresses, wishlists, and order
history. Capabilities without identity linking still operate at public or
agent-authenticated access levels — identity linking upgrades the experience,
it does not gate it.

**This specification uses
[OAuth 2.0](https://datatracker.ietf.org/doc/html/rfc6749){ target="_blank" }**
as the v1 auth mechanism. The schema is designed for incremental extension:
future versions will add delegated identity provider support and non-OAuth
authentication mechanisms — both via a single `config.providers` extension
point — without breaking changes to this version (see
[Future Extensibility](#future-extensibility)).

### Participants

| UCP Role | Identity Role | Description |
| :------- | :------------ | :---------- |
| **Platform** | User Agent | Trusted intermediary that initiates identity linking and presents user identity tokens to businesses on behalf of the user. |
| **Business** | Authorization Server / Relying Party | Hosts its own OAuth 2.0 authorization server. Authenticates users and issues access tokens scoped to UCP capabilities. |
| **User** | Resource Owner | The person whose identity is being linked. Grants explicit consent to the platform during the OAuth authorization flow. |

### Access Levels

Capabilities operate at three access levels:

| Level | Authentication | Example |
| :---- | :------------- | :------ |
| **Public** | None | Browse a public catalog |
| **Agent-authenticated** | Platform credentials (`client_id` / `client_secret`) | Guest checkout, create a cart |
| **User-authenticated** | Platform credentials + user identity token | Saved addresses, full order history, personalized pricing |

Identity linking bridges agent-authenticated to user-authenticated access: the
platform obtains a user identity token by completing the OAuth flow described
below, and presents it on subsequent requests.

**Identity linking and capability negotiation are independent layers.** A
capability is advertised and negotiated based on its own profile presence —
never excluded because identity linking is absent. Identity linking, when
present, declares the **scopes** that gate user-authenticated operations
*within* negotiated capabilities (see [Scopes](#scopes)). A merchant whose
profile lists `dev.ucp.shopping.order` has it in the negotiated intersection
either way. If their profile *also* lists identity linking with
`dev.ucp.shopping.order:read` in `config.scopes`, operations covered by
that scope require a user identity token.

## General Guidelines

### For Platforms

* **MUST** authenticate using `client_id` and `client_secret`
    ([RFC 6749 §2.3.1](https://datatracker.ietf.org/doc/html/rfc6749#section-2.3.1){ target="_blank" })
    via HTTP Basic Authentication
    ([RFC 7617](https://datatracker.ietf.org/doc/html/rfc7617){ target="_blank" })
    when exchanging authorization codes for tokens.
* **MUST** include user identity tokens in the HTTP `Authorization` header
    using the Bearer scheme: `Authorization: Bearer <access_token>`.
* **MUST** implement the OAuth 2.0 Authorization Code flow
    ([RFC 6749 §4.1](https://datatracker.ietf.org/doc/html/rfc6749#section-4.1){ target="_blank" })
    as the account linking mechanism.
* **MUST** use PKCE
    ([RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636){ target="_blank" })
    with `code_challenge_method=S256` for all authorization code exchanges.
* **MUST** validate the `iss` parameter in the authorization response
    ([RFC 9207](https://datatracker.ietf.org/doc/html/rfc9207){ target="_blank" })
    to prevent Mix-Up Attacks. The platform **MUST** verify that the `iss`
    value matches the authorization server's issuer URI (as declared in its
    [RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" }
    metadata). If the values do not match, the platform **MUST**
    abort and discard the authorization response.
* **SHOULD** include a unique, unguessable `state` parameter in the
    authorization request to prevent CSRF
    ([RFC 6749 §10.12](https://datatracker.ietf.org/doc/html/rfc6749#section-10.12){ target="_blank" }).
* When `config.providers` is present in the business's identity linking
    capability, the platform **SHOULD** select a provider it supports from
    the business's advertised list (see [Identity Providers](#identity-providers)).
* Before initiating identity chaining with a business, the platform
    **SHOULD** offer the user a choice of available identity providers and
    indicate which provider's identity will be shared with the business.
* Revocation and security events:
    * **MUST** call the business's token revocation endpoint
        ([RFC 7009](https://datatracker.ietf.org/doc/html/rfc7009){ target="_blank" })
        when a user initiates an unlink action on the platform side.
    * **SHOULD** support
        [OpenID RISC Profile 1.0](https://openid.net/specs/openid-risc-1_0-final.html){ target="_blank" }
        to handle asynchronous account updates and cross-account protection
        events initiated by the business.

### For Businesses

* **MUST** implement OAuth 2.0
    ([RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749){ target="_blank" }).
* **MUST** publish authorization server metadata via
    [RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" }
    at `/.well-known/oauth-authorization-server`.
* **MUST** populate `scopes_supported` in
    [RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" }
    metadata to allow platforms
    to detect scope mismatches before initiating an authorization flow.
* **MUST** return the `iss` parameter in the authorization response
    ([RFC 9207](https://datatracker.ietf.org/doc/html/rfc9207){ target="_blank" }).
* **MUST** enforce PKCE
    ([RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636){ target="_blank" })
    validation at the token endpoint for all authorization code exchanges.
    Requests without a valid `code_verifier` **MUST** be rejected.
* **MUST** enforce exact string matching for the `redirect_uri` parameter
    during authorization requests to prevent open redirects and token theft.
    The `redirect_uri` in the token request **MUST** be identical to the one
    in the authorization request.
* **MUST** enforce client authentication at the token endpoint.
* **MUST** implement token revocation
    ([RFC 7009](https://datatracker.ietf.org/doc/html/rfc7009){ target="_blank" }).
    Revoking a `refresh_token` **MUST** also immediately invalidate all
    `access_token`s issued from it.
* **MUST** support revocation requests authenticated with the same client
    credentials used at the token endpoint.
* **MAY** declare trusted identity providers in `config.providers`
    (see [Identity Providers](#identity-providers)). Businesses **MUST**
    only list providers they explicitly trust.
* When the business lists external identity providers in `config.providers`,
    the business **MUST** support the JWT bearer assertion grant type
    ([RFC 7523](https://datatracker.ietf.org/doc/html/rfc7523){ target="_blank" })
    at its token endpoint to accept JWT authorization grants from those
    IdPs, and **MUST** include
    `urn:ietf:params:oauth:grant-type:jwt-bearer` in `grant_types_supported`
    in its RFC 8414 metadata.
* **SHOULD** provide an account creation flow if the user does not already have
    an account, or return a `continue_url` in an `identity_required` error
    response (see [Error Handling](#error-handling)) pointing to an onboarding
    flow.
* **MUST** support standard UCP scopes as defined in the
    [Scopes](#scopes) section.
* **SHOULD** implement
    [RFC 9728](https://datatracker.ietf.org/doc/html/rfc9728/){ target="_blank" }
    (HTTP Resource Metadata) to allow platforms to discover the authorization
    server associated with specific resources.
* **SHOULD** support
    [OpenID RISC Profile 1.0](https://openid.net/specs/openid-risc-1_0-final.html){ target="_blank" }
    to signal revocation and account state changes to platforms.

## Discovery

Platforms resolve business authorization server metadata using the following
**strict two-tier hierarchy**. The issuer URI used as the discovery base is
the business's domain as declared in its UCP profile.

1. **RFC 8414 (Primary):** Fetch
   `{business-domain}/.well-known/oauth-authorization-server`.
    * `2xx` response: use this metadata. Discovery complete.
    * `404 Not Found`: proceed to step 2.
    * Any other non-2xx response, network error, or timeout: **MUST** abort.
      **MUST NOT** proceed to step 2.

2. **OIDC Discovery (Fallback):** Fetch
   `{business-domain}/.well-known/openid-configuration`.
    * `2xx` response: use this metadata. Discovery complete.
    * Any non-2xx response, network error, or timeout: **MUST** abort the
      identity linking process.

Platforms **MUST NOT** silently fall through on any error other than `404` in
step 1. This prevents partial or undefined behavior when a server is
misconfigured or temporarily unavailable.

The `issuer` value in the discovered metadata **MUST** match the discovery
base URI exactly (per
[RFC 8414 §3.3](https://datatracker.ietf.org/doc/html/rfc8414#section-3.3){ target="_blank" }).
Platforms **MUST NOT** normalize (e.g., strip trailing slashes) before
comparison — the value must be a byte-for-byte match.

## Account Linking Flow

Identity linking uses the OAuth 2.0 Authorization Code flow with PKCE.

```text
Platform                              Business AS
   |                                       |
   |-- (1) Discover metadata via RFC 8414 -->|
   |<-- authorization_endpoint, token_endpoint, scopes_supported --|
   |                                       |
   |-- (2) Authorization Request --------->|
   |       response_type=code              |
   |       client_id, redirect_uri         |
   |       scope=<derived scope set>       |
   |       code_challenge (S256)           |
   |       state                           |
   |                                       |
   |       [user authenticates and         |
   |        grants consent at business]    |
   |                                       |
   |<-- (3) Authorization Response --------|
   |       code, state, iss                |
   |                                       |
   |  Validate: state matches, iss matches |
   |  discovered issuer URI                |
   |                                       |
   |-- (4) Token Request ----------------->|
   |       grant_type=authorization_code   |
   |       code, redirect_uri              |
   |       code_verifier                   |
   |       client_id (Basic Auth)          |
   |                                       |
   |<-- (5) Token Response ----------------|
   |       access_token, refresh_token     |
   |       token_type=Bearer, scope        |
```

**Step 2 — Scope set:** Platforms derive the authorization scope set from the
business's `config.scopes` map (see [Scope Derivation](#scope-derivation)).
Platforms **MUST** request only the derived scope set — not a superset.

**Step 3 — Validation:** The platform **MUST** verify that the `state`
parameter matches the value sent in step 2, and that the `iss` parameter
matches the authorization server's `issuer` URI from discovered metadata.
If either check fails, the platform **MUST** discard the authorization
response.

**Step 4 — PKCE:** The `code_verifier` **MUST** correspond to the
`code_challenge` sent in step 2. Businesses **MUST** reject token requests
where `code_verifier` is absent or does not verify against the stored
`code_challenge`.

## Identity Providers

Businesses **MAY** declare trusted identity providers in the `config.providers`
map of their `dev.ucp.common.identity_linking` capability entry. Each provider
is keyed by a reverse-domain identifier and specifies an `auth_url` for OAuth
2.0 discovery. When a platform already holds a token from a trusted provider
(e.g., from a prior account-linking flow with that IdP), it can chain the
user's identity to a new business via the [Accelerated IdP Flow](#accelerated-idp-flow)
— no fresh browser-based OAuth dance required.

When `config.providers` is absent, platforms run OAuth 2.0 against the
business domain using the [Discovery](#discovery) hierarchy, as described
above.

### Provider Configuration

Each provider entry specifies the discovery base URL:

| Field | Type | Required | Description |
| :---- | :--- | :------- | :---------- |
| `type` | string | No (default: `oauth2`) | Provider type discriminator. |
| `auth_url` | string (URI) | Yes | Base URL for authorization server metadata discovery. |

Platforms **MUST** discover the provider's authorization server metadata from
`auth_url` using the same two-tier hierarchy as [Discovery](#discovery)
(RFC 8414 primary, OIDC fallback on 404 only).

### Provider Selection

Platforms read the business's `config.providers` map and select a provider
they support — typically one they already hold a token for (enabling the
Accelerated IdP Flow), or one the user can authenticate with.

A business **MAY** list itself as a provider (its own `auth_url` resolving
to its own authorization server). When the platform selects a self-listed
provider, it uses the standard OAuth flow described in [Account Linking
Flow](#account-linking-flow) — the Accelerated IdP Flow is unnecessary
because the business is both the IdP and the relying party.

### Profile Example

A business that trusts an external IdP and also lists itself:

```json
"dev.ucp.common.identity_linking": [{
  "version": "Working Draft",
  "spec": "https://ucp.dev/specification/identity-linking",
  "schema": "https://ucp.dev/schemas/common/identity_linking.json",
  "config": {
    "providers": {
      "app.example.login": {
        "auth_url": "https://accounts.example-login.app/"
      },
      "com.example.merchant": {
        "auth_url": "https://merchant.example.com/"
      }
    },
    "scopes": {
      "dev.ucp.shopping.order:read":   {},
      "dev.ucp.shopping.order:manage": {}
    }
  }
}]
```

The platform can use the Accelerated IdP Flow with `app.example.login` if it
holds a token there, or fall back to the standard Account Linking Flow
against `com.example.merchant` (the business's own authorization server).

## Accelerated IdP Flow

After a platform has linked the user's identity with a trusted IdP, it can
chain that identity to new businesses without a browser redirect: the
platform obtains a **JWT authorization grant** from the IdP and presents it
to the business's token endpoint. The business validates the grant and issues
its own access token under its own authority.

This flow implements the identity and authorization chaining pattern in
[draft-ietf-oauth-identity-chaining](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-identity-chaining-08){ target="_blank" }.

### Flow

1. Platform discovers `config.providers` in the business's identity linking
   capability and selects a provider it already holds a valid token for.
2. Platform requests a JWT authorization grant from the IdP via token
   exchange ([RFC 8693](https://datatracker.ietf.org/doc/html/rfc8693){ target="_blank" })
   at the IdP's token endpoint:
    * `grant_type`: `urn:ietf:params:oauth:grant-type:token-exchange`
    * `subject_token`: the platform's existing IdP access token
    * `subject_token_type`: `urn:ietf:params:oauth:token-type:access_token`
    * `resource`: the business's authorization server issuer URI (the IdP
      maps this value to the `aud` claim in the resulting grant). Platforms
      **MUST** use `resource`, not `audience`, because the target is a
      concrete URI.
    * `requested_token_type`: `urn:ietf:params:oauth:token-type:jwt`
3. The IdP validates the subject token, verifies the platform is authorized
   to request a grant for the target business, and returns a short-lived
   JWT authorization grant with `issued_token_type` set to
   `urn:ietf:params:oauth:token-type:jwt`.
4. Platform presents the grant to the business's token endpoint via the JWT
   bearer assertion grant
   ([RFC 7523](https://datatracker.ietf.org/doc/html/rfc7523){ target="_blank" }):
    * `grant_type`: `urn:ietf:params:oauth:grant-type:jwt-bearer`
    * `assertion`: the JWT authorization grant
    * `scope`: the derived scope set (see [Scope Derivation](#scope-derivation))
5. The business validates the grant, resolves the user identity, and issues
   an access token under its own authority.
6. Platform uses the business-issued token via `Authorization: Bearer <access_token>`
   on subsequent requests.

The platform **MUST NOT** present a raw IdP token directly to a business.
Identity chaining ensures each business issues tokens under its own authority
with the correct audience binding and scope policy.

### JWT Authorization Grant

The JWT authorization grant is a signed JWT
([RFC 7519](https://datatracker.ietf.org/doc/html/rfc7519){ target="_blank" })
issued by the IdP that asserts the user's identity for use with a specific
business. It is **not** an access token — it is a short-lived credential the
platform presents to the business's authorization server to obtain one.

The grant **MUST** contain:

| Claim | Description |
| :---- | :---------- |
| `iss` | The IdP's issuer identifier. |
| `sub` | The user's identifier at the IdP. |
| `aud` | The business's authorization server issuer URI. **MUST** be a single value. |
| `exp` | Expiration time. **SHOULD** be no more than 60 seconds after `iat`. |
| `iat` | Time at which the grant was issued. |
| `jti` | Unique identifier for replay protection. |

The IdP **MAY** include additional claims to convey authorization context
(consent records, user attributes, etc.).

### Business Token Issuance

Upon receiving a JWT authorization grant at its token endpoint, the
business's authorization server **MUST**:

1. Validate the JWT per
   [RFC 7523 §3](https://datatracker.ietf.org/doc/html/rfc7523#section-3){ target="_blank" }.
2. Verify `iss` identifies a provider listed in the business's `config.providers`.
3. Verify `aud` matches the business's own authorization server issuer URI.
4. Verify the JWT signature using the IdP's published JWKS (`jwks_uri`).
   If JWKS cannot be retrieved, the business **MUST** fail closed.
5. Resolve the user from the `sub` claim. If the user has no account, the
   business **MAY** auto-provision one. If user interaction is required
   (terms acceptance, onboarding), it **MUST** return a UCP error response
   with a `continue_url`.
6. Issue an access token scoped to the requested UCP scopes.

The business **MUST** reject grants that are expired, malformed, or
previously used.

### Chaining Errors at the Token Endpoint

When validation fails, the business **MUST** return a standard OAuth error
response ([RFC 6749 §5.2](https://datatracker.ietf.org/doc/html/rfc6749#section-5.2){ target="_blank" }):

| Condition | Error | HTTP Status |
| :-------- | :---- | :---------- |
| `iss` not in `config.providers` | `invalid_grant` | 400 |
| `aud` mismatch | `invalid_grant` | 400 |
| Expired (`exp`) | `invalid_grant` | 400 |
| Signature invalid | `invalid_grant` | 400 |
| `jti` previously used (replay) | `invalid_grant` | 400 |
| IdP JWKS unreachable | `server_error` | 500 |
| Unsupported scope | `invalid_scope` | 400 |

### Token Lifecycle

Identity chaining produces two independent token lifecycles. Revocation at
one layer does not propagate to the other.

**Business-issued tokens** follow the business's lifecycle. Businesses
**SHOULD NOT** issue refresh tokens in response to a JWT bearer assertion
grant — doing so creates credentials that outlive the IdP session, allowing
continued access after the user revokes the IdP relationship
([draft-ietf-oauth-identity-chaining §5.4](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-identity-chaining-08#section-5.4){ target="_blank" }).
When a business-issued token expires, the platform **SHOULD** obtain a new
JWT grant from the IdP and re-present it.

**IdP tokens** follow the IdP's lifecycle. Platforms **MUST** direct
revocation requests to the relevant authorization server's revocation
endpoint per RFC 7009.

When the user initiates an unlink action, the platform **SHOULD** revoke
both the IdP token and any business-issued tokens it holds.

## IdP Requirements

Identity providers listed in `config.providers` **MUST** publish authorization
server metadata via
[RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" }
or OpenID Connect Discovery. The metadata **MUST** include:

* `revocation_endpoint` — to support token revocation per the
    [Token Lifecycle](#token-lifecycle) section.
* `jwks_uri` — so businesses can verify the signature on JWT authorization
    grants issued by the IdP.
* `urn:ietf:params:oauth:grant-type:token-exchange` in `grant_types_supported`
    — to enable the Accelerated IdP Flow.

When processing token exchange requests for JWT authorization grants, the
IdP **MUST**:

* Authenticate the platform and verify it is authorized to present the
    subject token
    ([RFC 8693 §2.1](https://datatracker.ietf.org/doc/html/rfc8693#section-2.1){ target="_blank" }).
* Verify the target business (identified by `resource`) is a known relying
    party and the user has authorized identity sharing with it. The IdP
    **MUST NOT** issue grants for businesses the user has not authorized.
* Issue a JWT authorization grant conforming to the
    [JWT Authorization Grant](#jwt-authorization-grant) requirements.
* Return `issued_token_type` as `urn:ietf:params:oauth:token-type:jwt`.

## Scopes

Scopes define the user-authenticated permissions a business grants to a
platform. Businesses declare the scopes they offer in `config.scopes` of their
`dev.ucp.common.identity_linking` entry. Each key is the OAuth scope string as
it appears on the wire (`{capability}:{scope}`, e.g.
`dev.ucp.shopping.order:read`); each value is a per-scope policy object.

Listing a scope in `config.scopes` declares that obtaining that scope requires
user authentication. Operations not gated by any listed scope operate at
public or agent-authenticated access.

### Scope Token Format

Scope tokens follow the convention `{capability-name}:{scope-name}`:

* `dev.ucp.shopping.order:read`
* `dev.ucp.shopping.order:manage`
* `dev.ucp.shopping.checkout:create`

The capability name uses UCP's reverse-DNS naming. The scope name denotes
the **permission** being granted — typically an operation group on a
resource (`read`, `manage`, `write`) or an entry-point operation (`create`)
defined by each capability's specification.

Scope names **MUST** match the pattern `^[a-z][a-z0-9_]*$`. Third-party
capabilities follow the same convention using their own reverse-DNS name:
`com.example.loyalty:points`.

### Per-Scope Policy and Metadata

Each scope's value is an open object that carries per-scope policy and
metadata. Empty `{}` means "user auth required, nothing else." Possible
fields include authentication constraints (`min_acr`, `max_token_age`,
`require_mfa`), declarative metadata (`claims` produced when granted,
human-readable consent descriptions), or other scope-specific configuration.
Platforms **MUST** ignore unrecognized fields.

### Scope Derivation

Platforms derive the authorization scope set from the business's
`config.scopes` before initiating the account linking flow:

1. Read `config.scopes` from the business's `dev.ucp.common.identity_linking`
   capability entry.
2. Filter to scopes whose capability prefix is in the negotiated capability
   set — ignore scopes for capabilities the platform does not support.
3. From the remaining set, select the scopes the platform intends to use
   (informed by which operations it plans to call; see each capability's spec
   for operation-to-scope mappings).
4. Apply the per-scope policy on each selected scope when constructing the
   authorization request.

If no scope is required for the operations the platform intends to call, the
platform can skip the identity linking flow — operations work with public or
agent-authenticated access. However, linking may still be beneficial to
unlock session-native personalization (saved addresses, member pricing, order
history visibility, etc.); the merchant resolves these from the authenticated
user context regardless of which scopes were granted.

### Consent Presentation

Consent screens are rendered by the business's authorization server. This
specification does not define scope description strings — the authorization
server is responsible for presenting human-readable consent text for the
scopes it supports. Consent screens **SHOULD** group related scopes
intelligibly rather than listing individual operations: for example, "Allow
[platform] to view your order history" rather than "grant
`dev.ucp.shopping.order:read`."

## Error Handling

### `identity_required`

When an operation is gated by a scope listed in `config.scopes` and the
request arrives without a valid user identity token, the business **MUST**
return a UCP error response containing a message with
`code: "identity_required"`.

The business **MAY** include a `continue_url` in the response body, pointing to
a URL where the user can complete account creation or onboarding (e.g., terms
acceptance). After the user completes the onboarding flow, the platform retries
account linking.

```json
{
  "messages": [
    {
      "type": "error",
      "code": "identity_required",
      "content": "User identity is required to access order history.",
      "severity": "requires_buyer_review"
    }
  ],
  "continue_url": "https://merchant.example.com/onboarding?return_to=..."
}
```

## Security Considerations

* **PKCE.** PKCE (`S256`) is REQUIRED for all authorization code flows.
  Plain PKCE (`plain`) **MUST NOT** be used. Businesses **MUST** reject
  authorization code exchanges without a valid `code_verifier`.
* **Mix-Up Attack prevention.** Platforms **MUST** validate the `iss`
  parameter in the authorization response
  ([RFC 9207](https://datatracker.ietf.org/doc/html/rfc9207){ target="_blank" }).
  Businesses **MUST**
  return `iss` in every authorization response. Without `iss` validation,
  an attacker that controls one authorization server can redirect a
  victim's authorization code to a different server.
* **`redirect_uri` exactness.** Businesses **MUST** enforce exact string
  matching for `redirect_uri`. Partial-match or prefix-match implementations
  are a common source of open redirect and token theft vulnerabilities.
* **`issuer` exactness.** The `issuer` value in RFC 8414 metadata and the
  `iss` parameter in authorization responses **MUST** be identical
  (byte-for-byte). Platforms **MUST NOT** normalize before comparison.
  Normalization (e.g., stripping trailing slashes) is a known source of
  `iss` validation bypass.
* **Transport security.** All communication between platform and business
  **MUST** use HTTPS with a minimum of TLS 1.2
  ([RFC 6749 §1.6](https://datatracker.ietf.org/doc/html/rfc6749#section-1.6){ target="_blank" }).
* **`scopes_supported`.** Businesses **MUST** populate `scopes_supported` in
  RFC 8414 metadata. Platforms **SHOULD** verify that the derived scope set is
  a subset of `scopes_supported` before initiating the authorization flow, to
  fail fast on scope mismatches rather than at the consent screen.
* **Token revocation.** Platforms **MUST** revoke user identity tokens at the
  business's revocation endpoint (RFC 7009) when a user unlinks their account.
  Businesses **MUST** reject subsequent requests that present revoked tokens.
* **JWT grant lifetime.** JWT authorization grants **MUST** be short-lived;
  the `exp` claim **SHOULD** be no more than 60 seconds after `iat`. Short
  lifetimes limit the window for grant theft and replay.
* **JWT grant single-use.** Businesses **SHOULD** enforce single-use JWT
  authorization grants by tracking the `jti` claim within the grant's
  validity window.
* **Grant relay.** Businesses **MUST NOT** store or forward JWT
  authorization grants received from platforms. Grants are bearer
  credentials scoped to a single audience (`aud`) and a single use.

## Future Extensibility

The schema is designed to accommodate non-OAuth provider mechanisms as
non-breaking extensions. The `provider.type` discriminator defaults to
`oauth2` and reserves space for future types — wallet attestation,
verifiable credentials, or other proof-of-identity protocols. Future
versions may define additional `type` values and the corresponding
discovery and grant exchange mechanics.

**Forward-compatibility rule for platforms:** When `config` contains fields
not defined in this version of the spec, or `provider.type` values the
platform does not support, platforms **MUST** ignore those fields/entries
and proceed using OAuth 2.0 with RFC 8414 discovery on the business domain.
This ensures current platform implementations remain valid as the spec
evolves.

## Examples

### Authorization Server Metadata

Example metadata hosted at `/.well-known/oauth-authorization-server` per
[RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" }:

```json
{
  "issuer": "https://merchant.example.com",
  "authorization_endpoint": "https://merchant.example.com/oauth2/authorize",
  "token_endpoint": "https://merchant.example.com/oauth2/token",
  "revocation_endpoint": "https://merchant.example.com/oauth2/revoke",
  "jwks_uri": "https://merchant.example.com/oauth2/jwks",
  "scopes_supported": [
    "dev.ucp.shopping.order:read",
    "dev.ucp.shopping.order:manage"
  ],
  "response_types_supported": ["code"],
  "grant_types_supported": [
    "authorization_code",
    "refresh_token",
    "urn:ietf:params:oauth:grant-type:jwt-bearer"
  ],
  "code_challenge_methods_supported": ["S256"],
  "token_endpoint_auth_methods_supported": ["client_secret_basic"],
  "authorization_response_iss_parameter_supported": true,
  "service_documentation": "https://merchant.example.com/docs/oauth2"
}
```

Note: `authorization_response_iss_parameter_supported: true` advertises
[RFC 9207](https://datatracker.ietf.org/doc/html/rfc9207){ target="_blank" } support. `code_challenge_methods_supported: ["S256"]` signals PKCE.
Both **MUST** be present in UCP-compliant metadata. The
`urn:ietf:params:oauth:grant-type:jwt-bearer` grant type indicates the
business accepts JWT authorization grants from trusted IdPs via the
[Accelerated IdP Flow](#accelerated-idp-flow).

### Business Profile (`/.well-known/ucp`)

The shape of `config.scopes` reflects the business's policy.

#### B2C retailer

Public catalog, guest checkout (no scope required), user-bound order
operations gated:

```json
{
  "ucp": {
    "capabilities": {
      "dev.ucp.common.identity_linking": [{
        "version": "Working Draft",
        "spec": "https://ucp.dev/specification/identity-linking",
        "schema": "https://ucp.dev/schemas/common/identity_linking.json",
        "config": {
          "scopes": {
            "dev.ucp.shopping.order:read":    {},
            "dev.ucp.shopping.order:manage":  {}
          }
        }
      }]
    }
  }
}
```

**Reading this config:**

* `dev.ucp.shopping.order:read` and `:manage` — listed → user auth required
  to obtain.
* Catalog, checkout, cart, and everything else — not listed → no user-auth
  scope required. Public/agent-authenticated access. The user may still
  request, or the agent may still offer, linking to access additional
  capabilities such as personalization, saved addresses and credentials,
  loyalty pricing, etc.

#### B2B wholesaler

No guest checkout — every transaction requires an authenticated user:

```json
{
  "ucp": {
    "capabilities": {
      "dev.ucp.common.identity_linking": [{
        "version": "Working Draft",
        "spec": "https://ucp.dev/specification/identity-linking",
        "schema": "https://ucp.dev/schemas/common/identity_linking.json",
        "config": {
          "scopes": {
            "dev.ucp.shopping.checkout:create":  {},
            "dev.ucp.shopping.order:read":       {},
            "dev.ucp.shopping.order:manage":     {}
          }
        }
      }]
    }
  }
}
```

**The difference:** `dev.ucp.shopping.checkout:create` is now listed. The
B2C example doesn't gate checkout creation; anyone can start a guest
session. This merchant requires the user to be authenticated before
creating a checkout. Subsequent operations on that session (update,
complete, cancel) are session-bound and require no additional scope.

Whether the user is B2B-eligible, what pricing they see, what payment terms
apply — those are user attributes the merchant resolves at runtime, not
additional scopes.

### End-to-End Walkthrough

**Setup:** Platform (AI shopping agent) + Business (B2C retailer from the
example above).

**Negotiated capabilities:** `dev.ucp.shopping.checkout`,
`dev.ucp.shopping.order`, `dev.ucp.common.identity_linking`.

**Step 1 — Scope derivation.** Platform reads business's `config.scopes`:

* `dev.ucp.shopping.order:read` (read order history)
* `dev.ucp.shopping.order:manage` (cancel/return)

The user wants the agent to be able to read order history and cancel orders
on their behalf, so the platform requests both scopes.

Derived scope set: `dev.ucp.shopping.order:read dev.ucp.shopping.order:manage`

**Step 2 — Discovery.** Platform fetches
`https://merchant.example.com/.well-known/oauth-authorization-server`,
receives `2xx`, extracts `authorization_endpoint` and `token_endpoint`.
Verifies both scopes are in `scopes_supported`.

**Step 3 — Authorization request.** Platform generates PKCE pair
(`code_verifier`, `code_challenge`), sends the user to:

```text
GET https://merchant.example.com/oauth2/authorize
  ?response_type=code
  &client_id=platform-client-id
  &redirect_uri=https://agent.example.com/callback
  &scope=dev.ucp.shopping.order:read dev.ucp.shopping.order:manage
  &code_challenge=<S256-hash>
  &code_challenge_method=S256
  &state=<random>
```

Reserved characters in `redirect_uri` and `:` in scope tokens must be
percent-encoded in the actual request; they are shown decoded here for readability.

**Step 4 — Authorization response.** User authenticates and consents.
Business redirects to:

```text
https://agent.example.com/callback
  ?code=<auth-code>
  &state=<random>
  &iss=https://merchant.example.com
```

Platform validates `state` matches and `iss` equals the discovered `issuer`.

**Step 5 — Token exchange.** Platform calls token endpoint:

```http
POST https://merchant.example.com/oauth2/token
Authorization: Basic <base64(client_id:client_secret)>
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code
&code=<auth-code>
&redirect_uri=https://agent.example.com/callback
&code_verifier=<verifier>
```

Business validates `code_verifier` against stored `code_challenge`, returns:

```json
{
  "access_token": "<token>",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "<refresh>",
  "scope": "dev.ucp.shopping.order:read dev.ucp.shopping.order:manage"
}
```

Platform now includes `Authorization: Bearer <token>` on subsequent requests
to user-authenticated capability endpoints.
