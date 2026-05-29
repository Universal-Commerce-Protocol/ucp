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
for authorization. Platforms run OAuth 2.0 directly against the business
domain, or — when the business declares trusted identity providers in
`config.providers` — chain identity from a provider via the
[Accelerated IdP Flow](#accelerated-idp-flow). The `provider.type`
discriminator (a required open string; `oauth2` is the only type defined in
this version) reserves space for future non-OAuth provider mechanisms; see
[Future Extensibility](#future-extensibility).

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

### UCP and OAuth

UCP defines commerce semantics (which scopes mean what, which gate which
operations); OAuth ([RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" })
defines identity machinery (endpoints, flows, accepted scope
vocabulary); runtime messages carry per-request advisories.

* **UCP `config.scopes`** declares **hard gates**: scopes that *require*
    user authentication for the operations they cover.
* **OAuth `scopes_supported`** (RFC 8414) declares the **accepted scope
    vocabulary**: every scope the authorization server will honor if
    requested.
* The diff (`scopes_supported` ∖ `config.scopes`) is the **optional
    layer**: scopes the merchant accepts but doesn't gate, used to
    advertise authentication-unlocked features without requiring auth.
* **UCP `messages[]`** carry **runtime contextual hints**: per-request
    notices like `identity_optional` (see
    [Optional Authentication](#optional-authentication)) signaling that
    authenticating would unlock value in the current context.

## General Guidelines

### For Platforms

* **MUST** authenticate token endpoint requests using a method advertised in
    the business's `token_endpoint_auth_methods_supported` metadata
    ([RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" }):
    * **Confidential clients** (server-side platforms that can protect a
        credential) **SHOULD** prefer asymmetric methods —
        `private_key_jwt`
        ([RFC 7523 §2.2](https://datatracker.ietf.org/doc/html/rfc7523#section-2.2){ target="_blank" })
        or `tls_client_auth`
        ([RFC 8705](https://datatracker.ietf.org/doc/html/rfc8705){ target="_blank" })
        — and **MAY** use `client_secret_basic`
        ([RFC 6749 §2.3.1](https://datatracker.ietf.org/doc/html/rfc6749#section-2.3.1){ target="_blank" },
        [RFC 7617](https://datatracker.ietf.org/doc/html/rfc7617){ target="_blank" })
        where the business supports it.
    * **Public clients** (native, desktop, browser-extension, and on-device
        agent runtimes per
        [RFC 8252 §8.5](https://datatracker.ietf.org/doc/html/rfc8252#section-8.5){ target="_blank" })
        **MUST** use `none` and rely on PKCE with `S256`
        ([RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636){ target="_blank" })
        as proof-of-possession of the authorization code. Public clients
        **MUST NOT** embed a `client_secret`.

    Platforms **MUST** select the strongest method offered by the business
    that is compatible with the platform's deployment model.
* **MUST** include user identity tokens in the HTTP `Authorization` header
    using the Bearer scheme: `Authorization: Bearer <access_token>`
    ([RFC 6750 §2.1](https://datatracker.ietf.org/doc/html/rfc6750#section-2.1){ target="_blank" }).
* **MUST** process `WWW-Authenticate: Bearer` challenges per
    [RFC 6750 §3](https://datatracker.ietf.org/doc/html/rfc6750#section-3){ target="_blank" }
    on `401` and `403` responses to user-authenticated operations.
    Platforms **MUST** extract the `scope` parameter (when present) to
    construct subsequent authorization requests, and **SHOULD** follow
    the `resource_metadata` pointer
    ([RFC 9728](https://datatracker.ietf.org/doc/html/rfc9728){ target="_blank" })
    when present to discover the protecting authorization server.
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
* When `config.providers` is present, the platform **MUST** select a
    listed provider whose `type` it supports and **MUST NOT** fall back
    to direct OAuth on the business domain; if none is supported, the
    platform **MUST** abort (see [Identity Providers](#identity-providers)).
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
    in the authorization request. **Exception — loopback redirects:** For
    redirect URIs targeting `127.0.0.1` or `[::1]`, businesses **MUST** ignore
    the port component and match on scheme, host, and path only, to accommodate
    native and desktop clients that obtain an ephemeral port from the OS at
    runtime
    ([RFC 8252 §7.3](https://datatracker.ietf.org/doc/html/rfc8252#section-7.3){ target="_blank" }).
* **MUST** declare supported client authentication methods in
    `token_endpoint_auth_methods_supported`
    ([RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" }) and enforce one of the declared methods at the token endpoint.
    Businesses **SHOULD** support at least one asymmetric confidential-client
    method (`private_key_jwt` or `tls_client_auth`) and **MAY** support `none`
    for public clients per
    [RFC 8252](https://datatracker.ietf.org/doc/html/rfc8252){ target="_blank" }.
    When `none` is advertised, businesses **MUST** require PKCE with `S256` and
    **MUST** reject any authorization code redemption that lacks a valid
    `code_verifier`. Requests that fail the negotiated authentication method
    **MUST** be rejected with `invalid_client`; requests that fail PKCE
    **MUST** be rejected with `invalid_grant`.
* **MUST** validate user identity tokens on every user-authenticated request:
    verify `iss`, `aud` (the business's resource server identifier), `exp`,
    scopes, and `client_id` / `azp` (or equivalent) to confirm the token was
    issued to the authenticated platform client
    ([RFC 9068 §4](https://datatracker.ietf.org/doc/html/rfc9068#section-4){ target="_blank" }).
* **MUST** emit a `WWW-Authenticate: Bearer` challenge per
    [RFC 6750 §3](https://datatracker.ietf.org/doc/html/rfc6750#section-3){ target="_blank" }
    on `401 Unauthorized` (`identity_required`) and `403 Forbidden`
    (`insufficient_scope`) responses to user-authenticated operations.
    See [Error Handling](#error-handling) for the full normative
    requirements.
* **MUST** implement token revocation
    ([RFC 7009](https://datatracker.ietf.org/doc/html/rfc7009){ target="_blank" }).
    Revoking a `refresh_token` **MUST** also immediately invalidate all
    `access_token`s issued from it.
* **MUST** support revocation requests authenticated with the same client
    credentials used at the token endpoint.
* **MAY** declare trusted identity providers in `config.providers`
    (see [Identity Providers](#identity-providers)). Businesses **MUST**
    only list providers they explicitly trust.
* When the business lists external identity providers of `type: oauth2` in
    `config.providers`, the business **MUST** support the JWT bearer assertion
    grant type
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
* **SHOULD** publish protected resource metadata at
    `/.well-known/oauth-protected-resource`
    ([RFC 9728](https://datatracker.ietf.org/doc/html/rfc9728){ target="_blank" })
    and reference it via the `resource_metadata` parameter in
    `WWW-Authenticate` challenges. This lets platforms discover the
    authorization server protecting the resource without relying on
    domain conventions and prepares the deployment for future delegated
    IdP scenarios where the AS may not live on the business domain.
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
   |       client auth (per advertised     |
   |       token_endpoint_auth_method)     |
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

The `config.providers` map declares the trusted identity providers a
business accepts for authentication.

* **When absent:** by advertising the `dev.ucp.common.identity_linking`
    capability without a `providers` map, the business implicitly declares
    itself as its own (and only) identity provider. Platforms run OAuth 2.0
    directly against the business domain using the [Discovery](#discovery)
    hierarchy.
* **When present:** the map is a strict whitelist. Platforms **MUST**
    select from the listed providers and **MUST NOT** fall back to direct
    OAuth against the business domain. To accept direct OAuth alongside
    external IdPs, a business **MUST** self-list (own `auth_url` resolving
    to own authorization server); omitting self signals IdP-mediated
    authentication only.

When a platform already holds a token from a listed provider (e.g., from a
prior account-linking flow with that IdP), it can chain the user's identity
to the business via the [Accelerated IdP Flow](#accelerated-idp-flow) — no
fresh browser-based OAuth flow required.

### Provider Configuration

Each provider entry is keyed by a reverse-domain identifier and described by
its `type`:

| Field | Type | Required | Description |
| :---- | :--- | :------- | :---------- |
| `type` | string | Yes | Provider mechanism discriminator. `oauth2` is the only type defined in this version; future versions **MAY** define additional types as non-breaking extensions. |
| `auth_url` | string (URI) | Yes, for `oauth2` | Base URL for authorization server metadata discovery. |

The `type` value is an open string, not a closed enumeration. Platforms
**MUST** treat provider entries whose `type` they do not support as filtered
out (see [Provider Selection](#provider-selection)) rather than rejecting the
business's configuration.

For `oauth2` providers, platforms **MUST** discover the authorization server
metadata from `auth_url` using the same two-tier hierarchy as
[Discovery](#discovery) (RFC 8414 primary, OIDC fallback on 404 only).

### Provider Selection

Platforms read the business's `config.providers` map and select a provider
they support — typically one they already hold a token for (enabling the
Accelerated IdP Flow), or one the user can authenticate with.

A provider's `type` determines whether it participates in the token and
scope model. The `oauth2` type chains identity via token exchange and
contributes to the scopes of the business-issued token. Other types **MAY**
contribute no scopes — presence in `providers` does not imply participation
in the scope or token-issuance model. Provider selection and the abort rule
turn only on whether the platform *supports* a provider's `type`, independent
of whether that type issues a token.

Businesses **MAY** list themselves alongside external providers (own
`auth_url` resolving to own authorization server) to give platforms a
single map to consult. When the platform selects the self-listed entry,
it runs the [Account Linking Flow](#account-linking-flow) against the
business directly — chaining is unnecessary because the business is both
the IdP and the relying party.

### Profile Example

A business that trusts an external IdP and also self-lists:

```json
"dev.ucp.common.identity_linking": [{
  "version": "Working Draft",
  "spec": "https://ucp.dev/specification/identity-linking",
  "schema": "https://ucp.dev/schemas/common/identity_linking.json",
  "config": {
    "providers": {
      "app.example.login": {
        "type": "oauth2",
        "auth_url": "https://accounts.example-login.app/"
      },
      "com.example.merchant": {
        "type": "oauth2",
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

This flow profiles the identity and authorization chaining pattern in
[draft-ietf-oauth-identity-chaining](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-identity-chaining-08){ target="_blank" }.
UCP tightens two aspects beyond what the base RFCs mandate: token exchange
**MUST** use `resource` (not `audience`), and the JWT authorization grant
**MUST** carry `aud` as a single-valued URI plus a unique `jti` (see
[JWT Authorization Grant](#jwt-authorization-grant)).

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

The grant **MUST** conform to
[RFC 7523 §3](https://datatracker.ietf.org/doc/html/rfc7523#section-3){ target="_blank" },
with two UCP-specific constraints:

* `aud` **MUST** be a single value (the business's AS issuer URI), not an
  array — chaining targets one business per grant.
* `jti` **MUST** be present (RFC 7523 says MAY) so businesses can enforce
  single-use replay protection (see [Security Considerations](#security-considerations)).

`exp` **SHOULD** be no more than 60 seconds after `iat`. The IdP **MAY**
include additional claims to convey authorization context (consent records,
user attributes, etc.).

### Business Token Issuance

Upon receiving a JWT authorization grant at its token endpoint, the
business's authorization server **MUST** validate the assertion per
[RFC 7523 §3](https://datatracker.ietf.org/doc/html/rfc7523#section-3){ target="_blank" },
with the following UCP-specific requirements:

* `iss` **MUST** identify a provider listed in `config.providers`.
* `aud` **MUST** match the business's own AS issuer URI exactly.
* The JWT signature **MUST** be verified against the IdP's `jwks_uri`; if
  JWKS cannot be retrieved, the business **MUST** fail closed.

Once the assertion is validated, the business resolves the user from `sub`
(auto-provisioning permitted) and issues an access token scoped to the
requested UCP scopes. If user interaction is required (terms acceptance,
onboarding), the business **MUST** reject the grant with `invalid_grant`
(see [Chaining Errors at the Token Endpoint](#chaining-errors-at-the-token-endpoint));
platforms recover by running the [Account Linking Flow](#account-linking-flow)
against an interactive provider.

### Chaining Errors at the Token Endpoint

Validation failures use the standard OAuth 2.0 token-endpoint error format
([RFC 6749 §5.2](https://datatracker.ietf.org/doc/html/rfc6749#section-5.2){ target="_blank" }).
JWT-grant-specific failures (signature, `iss`, `aud`, `exp`, `jti` replay,
unrecognized provider, user-interaction required) map to `invalid_grant`
per [RFC 7523 §3.1](https://datatracker.ietf.org/doc/html/rfc7523#section-3.1){ target="_blank" }.
Businesses **MAY** include `error_description` and `error_uri` to aid
diagnosis or to point to onboarding documentation; platforms **MUST NOT**
treat `error_description` as machine-readable.

### Token Lifecycle

JWT bearer assertion grants don't establish long-lived sessions:
businesses **SHOULD NOT** issue refresh tokens in response, since they
would outlive the IdP session and grant continued access after the user
revokes the IdP relationship
([draft-ietf-oauth-identity-chaining §5.4](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-identity-chaining-08#section-5.4){ target="_blank" }).
When a business-issued token expires, the platform obtains a new JWT
grant from the IdP and re-presents it.

Revocation does not propagate across the chain. On unlink, platforms
**SHOULD** call the revocation endpoint
([RFC 7009](https://datatracker.ietf.org/doc/html/rfc7009){ target="_blank" })
at *both* layers — the IdP's and the business's.

## IdP Requirements

The requirements in this section apply to identity providers of
`type: oauth2`. Other provider types define their own discovery and
proof-presentation requirements (see [Future Extensibility](#future-extensibility)).

Identity providers of `type: oauth2` listed in `config.providers` **MUST**
publish authorization server metadata via
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

Listing a scope in `config.scopes` declares that the corresponding
operations require a user identity token. Operations *not* gated by any
listed scope operate at whatever access level the business permits — public,
agent-authenticated, or otherwise. The business defines the access policy
for non-scoped operations; UCP does not prescribe a default.

### Scope Token Format

Scope tokens follow the convention `{capability-name}:{scope-name}`:

* `dev.ucp.shopping.order:read`
* `dev.ucp.shopping.order:manage`
* `dev.ucp.shopping.checkout:manage`

The capability name uses UCP's reverse-DNS naming. The scope name denotes
the **permission** being granted — typically an operation group on a
resource (`read`, `manage`, `write`) or an entry-point operation (`create`)
defined by each capability's specification.

Scope names **MUST** match the pattern `^[a-z][a-z0-9_]*$`. Third-party
capabilities follow the same convention using their own reverse-DNS name:
`com.example.loyalty:points`.

Each capability's specification defines its **well-known** scopes — the
standard set platforms expect. Businesses **MAY** declare additional
**custom** scopes following the same convention to gate operations at
finer granularity (for example, to gate `complete` independently from the
well-known `dev.ucp.shopping.checkout:manage`, or to require elevated
authentication for high-value purchases). Platforms **MUST** treat any
scope listed in `config.scopes` — well-known or custom — as gating its
operations behind user authentication.

### Per-Scope Policy and Metadata

Each scope's value is an open object that carries per-scope policy and
metadata. Empty `{}` means "user auth required, nothing else." Possible
fields include authentication constraints (`min_acr`, `max_token_age`,
`require_mfa`), declarative metadata (`claims` produced when granted),
or other scope-specific configuration. Platforms **MUST** ignore
unrecognized fields.

#### `description`

Optional human-readable description of the scope that platforms can use
to present and explain context (requirement and value) to the user.

<!-- ucp:example schema=common/identity_linking def=scope_policy -->
```json
{
  "description": {
    "plain": "Manage your orders: cancel, return, or modify post-purchase.",
    "markdown": "**Manage your orders**: cancel, return, or modify post-purchase."
  }
}
```

Businesses **SHOULD** provide a description for each scope they declare.
Platforms **MAY** display the text to inform their own consent UX.

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
request arrives with an absent, expired, invalid, or unverifiable user
identity token, the business **MUST** return:

* HTTP `401 Unauthorized`
* A `WWW-Authenticate: Bearer` challenge header per
    [RFC 6750 §3](https://datatracker.ietf.org/doc/html/rfc6750#section-3){ target="_blank" }
* A UCP error response body containing a message with
    `code: "identity_required"`

The `WWW-Authenticate` header **MUST** include a `realm` parameter set to
the business's issuer URI as declared in
[RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" }
metadata. When the request included a token but it was invalid, expired, or
unverifiable, the header **MUST** also include `error="invalid_token"` and
**MAY** include `error_description` per RFC 6750 §3. When no token was
presented, the `error` parameter **SHOULD** be omitted (RFC 6750 §3.1).

The header **SHOULD** include a `resource_metadata` parameter
([RFC 9728 §5.1](https://datatracker.ietf.org/doc/html/rfc9728#section-5.1){ target="_blank" })
pointing to the protected resource metadata document
(`/.well-known/oauth-protected-resource`).

The business **MAY** include a `continue_url` in the response body for
**non-OAuth onboarding flows** (e.g., account creation, terms acceptance)
where the user must complete a hosted step before re-authenticating.
`continue_url` **MUST NOT** be used to convey a pre-baked OAuth
authorization request; the platform constructs its own authorization
request from the `WWW-Authenticate` challenge and discovered metadata,
including PKCE values, `state`, and `redirect_uri` it owns.

**No token presented** (first request to a gated operation — `error` omitted per RFC 6750 §3.1):

```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer realm="https://merchant.example.com",
                  resource_metadata="https://merchant.example.com/.well-known/oauth-protected-resource"
Content-Type: application/json

{
  "messages": [
    {
      "type": "error",
      "code": "identity_required",
      "content": "User identity is required to access order history.",
      "severity": "requires_buyer_review"
    }
  ]
}
```

**Token present but invalid or expired** (`error="invalid_token"` included per RFC 6750 §3):

```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer realm="https://merchant.example.com",
                  error="invalid_token",
                  error_description="The access token expired",
                  resource_metadata="https://merchant.example.com/.well-known/oauth-protected-resource"
Content-Type: application/json

{
  "messages": [
    {
      "type": "error",
      "code": "identity_required",
      "content": "User identity is required to access order history.",
      "severity": "requires_buyer_review"
    }
  ]
}
```

### `insufficient_scope`

When a request arrives with a valid user identity token but the token
lacks a scope required by the operation (or fails a scope-level policy
such as `min_acr` or `max_token_age`), the business **MUST** return:

* HTTP `403 Forbidden`
* A `WWW-Authenticate: Bearer` challenge header per RFC 6750 §3
* A UCP error response body containing a message with
    `code: "insufficient_scope"`

The `WWW-Authenticate` header **MUST** include:

* `realm="<business issuer URI>"`
* `error="insufficient_scope"`
* `scope="<space-separated full required scope set for the operation>"`

and **SHOULD** include a `resource_metadata` parameter pointing to the
protected resource metadata document (RFC 9728).

The `scope` parameter **MUST** list the **full** set of scopes required
for the operation, not just the missing ones. The platform compares the
full set against scopes already granted on its current token and uses
incremental authorization to request only the scopes it does not yet
have, avoiding redundant consent prompts for scopes the user has already
approved.

```http
HTTP/1.1 403 Forbidden
WWW-Authenticate: Bearer realm="https://merchant.example.com",
                  error="insufficient_scope",
                  scope="dev.ucp.shopping.order:read dev.ucp.shopping.order:manage",
                  resource_metadata="https://merchant.example.com/.well-known/oauth-protected-resource"
Content-Type: application/json

{
  "messages": [
    {
      "type": "error",
      "code": "insufficient_scope",
      "content": "This operation requires scopes: dev.ucp.shopping.order:read, dev.ucp.shopping.order:manage",
      "severity": "requires_buyer_review"
    }
  ]
}
```

> **Note:** `identity_required` and `insufficient_scope` are intentionally
> distinct. Platforms **MUST NOT** retry an `insufficient_scope` response by
> re-initiating a fresh account linking flow — they **MUST** instead request
> only the missing scope(s) via incremental authorization to preserve
> previously granted scopes.

## Optional Authentication

A mechanism for the **business** to signal to the **platform** that
authentication is available and would provide value in the current context,
even though the operation succeeded without it. The platform may then present
this signal to the user.

### `identity_optional`

Businesses **SHOULD** include this info-severity code in successful
responses when authentication is available and would meaningfully
unlock additional capabilities in the current context. The `content`
field conveys the business's value prompt to the platform (e.g.,
"Sign in for member pricing and personalized results.").

<!-- ucp:example schema=shopping/checkout extract=$.messages target=$.messages -->
```json
{
  "messages": [
    {
      "type": "info",
      "code": "identity_optional",
      "content": "Sign in for member pricing and personalized results."
    }
  ]
}
```

## Security Considerations

* **PKCE.** PKCE (`S256`) is REQUIRED for all authorization code flows.
  Plain PKCE (`plain`) **MUST NOT** be used. Businesses **MUST** reject
  authorization code exchanges without a valid `code_verifier`.
* **Client authentication.** Businesses negotiate client authentication via
  `token_endpoint_auth_methods_supported`
  ([RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" }).
  Confidential clients **SHOULD** prefer asymmetric methods
  (`private_key_jwt`, `tls_client_auth`) over `client_secret_basic` to
  eliminate shared-secret leak risk. Public clients (native, desktop, and
  on-device agents per
  [RFC 8252 §8.5](https://datatracker.ietf.org/doc/html/rfc8252#section-8.5){ target="_blank" })
  cannot keep a `client_secret` confidential and **MUST** use `none`; for
  these clients PKCE with `S256` is the proof-of-possession that
  authenticates the authorization grant. Businesses **MUST NOT** require
  `client_secret_basic` as the only method when serving native or agent
  platforms.
* **Mix-Up Attack prevention.** Platforms **MUST** validate the `iss`
  parameter in the authorization response
  ([RFC 9207](https://datatracker.ietf.org/doc/html/rfc9207){ target="_blank" }).
  Businesses **MUST**
  return `iss` in every authorization response. Without `iss` validation,
  an attacker that controls one authorization server can redirect a
  victim's authorization code to a different server.
* **Authentication challenges.** Businesses **MUST** emit
  `WWW-Authenticate: Bearer` challenges per
  [RFC 6750 §3](https://datatracker.ietf.org/doc/html/rfc6750#section-3){ target="_blank" }
  on `401` and `403` responses to user-authenticated operations. Platforms
  **MUST** process the structured `scope` and `error` parameters to drive
  authorization flow decisions; `error_description` is a human-readable
  hint only and **MUST NOT** be used for control-flow decisions. The
  `realm` parameter **MUST** match the business's issuer URI so platforms
  can correlate the challenge with the correct authorization server.
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
non-breaking extensions. The `provider.type` discriminator is a required,
open string: `oauth2` is the only type defined in this version, and it
reserves space for future types — wallet attestation, verifiable
credentials, or other proof-of-identity protocols. Future versions may
define additional `type` values and the corresponding discovery and
proof-presentation mechanics.

**Forward-compatibility rule for platforms:** When `config` contains fields
not defined in this version of the spec, platforms **MUST** ignore
those fields. Platforms **MUST** treat provider entries with an
unsupported `type` as filtered out, then apply the whitelist rule
(see [Identity Providers](#identity-providers)) to what remains.
If nothing remains, the platform **MUST** abort and **MUST NOT**
fall back to direct OAuth on the business domain unless the
business self-listed.

## Examples

### Authorization Server Metadata

Example metadata hosted at `/.well-known/oauth-authorization-server` per
[RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" }:

<!-- ucp:example skip reason="OAuth metadata, not UCP payload" -->
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
  "token_endpoint_auth_methods_supported": [
    "private_key_jwt",
    "tls_client_auth",
    "client_secret_basic",
    "none"
  ],
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

`token_endpoint_auth_methods_supported` lists every method the business
accepts. The example advertises asymmetric methods (`private_key_jwt`,
`tls_client_auth`) for confidential clients, `client_secret_basic` for
legacy compatibility, and `none` for public clients (native, desktop, and
on-device agents per
[RFC 8252](https://datatracker.ietf.org/doc/html/rfc8252){ target="_blank" });
when `none` is advertised, PKCE with `S256` is required. Businesses that
do not serve public clients **MAY** omit `none`.

### Business Profile (`/.well-known/ucp`)

The shape of `config.scopes` reflects the business's policy.

#### B2C retailer

Public catalog, guest checkout (no scope required), user-bound order
operations gated:

<!-- ucp:example schema=profile def=business_schema -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": {},
    "capabilities": {
      "dev.ucp.common.identity_linking": [{
        "version": "{{ ucp_version }}",
        "spec": "https://ucp.dev/specification/identity-linking",
        "schema": "https://ucp.dev/schemas/common/identity_linking.json",
        "config": {
          "scopes": {
            "dev.ucp.shopping.order:read":    {},
            "dev.ucp.shopping.order:manage":  {}
          }
        }
      }]
    },
    "payment_handlers": {}
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

<!-- ucp:example schema=profile def=business_schema -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": {},
    "capabilities": {
      "dev.ucp.common.identity_linking": [{
        "version": "{{ ucp_version }}",
        "spec": "https://ucp.dev/specification/identity-linking",
        "schema": "https://ucp.dev/schemas/common/identity_linking.json",
        "config": {
          "scopes": {
            "dev.ucp.shopping.checkout:manage":  {},
            "dev.ucp.shopping.order:read":       {},
            "dev.ucp.shopping.order:manage":     {}
          }
        }
      }]
    },
    "payment_handlers": {}
  }
}
```

**The difference:** `dev.ucp.shopping.checkout:manage` is now listed. The
B2C example doesn't gate checkout; anyone can start a guest session. This
merchant requires the user to be authenticated for all checkout
operations — create, update, complete, and cancel.

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

<!-- ucp:example skip reason="OAuth metadata, not UCP payload" -->
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
