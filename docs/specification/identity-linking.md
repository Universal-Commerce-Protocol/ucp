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
for authorization. Direct OAuth 2.0 against the business domain (via
[Discovery](#discovery)) is always available. When the business declares
trusted external identity providers in `config.providers`, platforms
**MAY** instead chain identity from a provider via the
[Accelerated IdP Flow](#accelerated-idp-flow), skipping the
browser-based flow when they already hold a suitable upstream token.

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
* When `config.providers` is present, the platform **MAY** chain
    identity from a listed provider via the
    [Accelerated IdP Flow](#accelerated-idp-flow). If no listed provider
    is supported or suitable, the platform **MUST** fall back to direct
    OAuth on the business domain via [Discovery](#discovery) (see
    [Identity Providers](#identity-providers)).
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
* **MAY** declare trusted external identity providers in
    `config.providers` (see [Identity Providers](#identity-providers)).
    Businesses **MUST** only list providers they explicitly trust and
    **MUST NOT** list their own authorization server.
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
    domain conventions. The business **MUST** publish this metadata when
    the authorization server does not live on the business domain.
* **SHOULD** support
    [OpenID RISC Profile 1.0](https://openid.net/specs/openid-risc-1_0-final.html){ target="_blank" }
    to signal revocation and account state changes to platforms.

## Discovery

UCP discovery is a three-step pipeline.

**Step 1 — Resolve the AS issuer.** Platforms fetch the business's
protected-resource metadata per
[RFC 9728](https://datatracker.ietf.org/doc/html/rfc9728){ target="_blank" }
and use the selected entry from `authorization_servers` as the AS
issuer. The AS issuer **MAY** be hosted on a different origin than the
business domain. If the business publishes no protected-resource
metadata, the AS issuer defaults to the business domain (single-host
deployments).

**Step 2 — Fetch AS metadata.** Using the issuer from Step 1, platforms
resolve authorization-server metadata via a strict two-tier hierarchy.
Well-known URLs are constructed per
[RFC 8414 §3.1](https://datatracker.ietf.org/doc/html/rfc8414#section-3.1){ target="_blank" }
(the well-known segment is inserted between the host and any issuer
path, not appended).

1. **RFC 8414 (Primary):** Fetch
   `https://{host}/.well-known/oauth-authorization-server{path}`.
    * `2xx` response: use this metadata. Discovery complete.
    * `404 Not Found`: proceed to step 2.
    * Any other non-2xx response, network error, or timeout: **MUST**
      abort. **MUST NOT** proceed to step 2.

2. **OIDC Discovery (Fallback):** Fetch
   `{issuer}/.well-known/openid-configuration`.
    * `2xx` response: use this metadata. Discovery complete.
    * Any non-2xx response, network error, or timeout: **MUST** abort.

Platforms **MUST NOT** silently fall through on any error other than
`404` in step 1.

**Step 3 — Validate the issuer.** The `issuer` value in the discovered
metadata **MUST** byte-for-byte match the AS issuer selected in Step 1
(per
[RFC 8414 §3.3](https://datatracker.ietf.org/doc/html/rfc8414#section-3.3){ target="_blank" }).
Platforms **MUST NOT** normalize (e.g., strip trailing slashes) before
comparison.

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

The `config.providers` map declares external trusted identity providers
from which the business will accept chained identity via JWT bearer
assertions for the [Accelerated IdP Flow](#accelerated-idp-flow). Each
key identifies an IdP namespace and maps to an array of mechanism
entries — an IdP **MAY** offer multiple token acquisition mechanisms
under a single key. The map is additive metadata on top of the
always-available direct OAuth path against the business domain (see
[Discovery](#discovery)); for the chaining path, it is a closed
allowlist — a business **MUST** reject a JWT authorization grant
whose `iss` does not match a listed `oauth2` mechanism entry (see
[Business Token Issuance](#business-token-issuance)).

* **When absent or empty:** platforms run direct OAuth against the
    business domain via [Discovery](#discovery).
* **When present:** platforms **MAY** select a mechanism entry whose
    `type` they support and chain identity via the
    [Accelerated IdP Flow](#accelerated-idp-flow) — typically one
    belonging to an IdP they already hold a valid upstream token for.
    If no listed mechanism is supported or suitable, platforms **MUST**
    fall back to direct OAuth on the business domain.
* **Self-listing forbidden.** Businesses **MUST NOT** list their own
    authorization server in `config.providers`. Chaining-to-self is
    degenerate (the same server would issue and validate the assertion),
    and direct OAuth is already available via [Discovery](#discovery).
    Platforms **MUST** ignore any `oauth2` mechanism entry whose
    `auth_url` matches the business's own issuer URI.

### Provider Configuration

Each key in `config.providers` is a reverse-domain identifier for an IdP
namespace; its value is an array of mechanism entries.

A provider key is a reverse-domain **identifier**, not a schema-bearing entity:
it declares no `schema` URL, so the
[Authority Binding](overview.md#authority-binding) (which binds an entity's
`schema` URL to its namespace authority) does not apply here. A provider's trust
anchor is its `auth_url`, governed by the discovery rules below; binding
`auth_url` to the provider's namespace authority is a possible future hardening,
tracked separately.

Each entry is described by its `type`:

| Field | Type | Required | Description |
| :---- | :--- | :------- | :---------- |
| `type` | string | Yes | Provider mechanism discriminator. `oauth2` is the only type defined in this version; future versions **MAY** define additional types as non-breaking extensions. |
| `auth_url` | string (URI) | Yes, for `oauth2` | Base URL for authorization server metadata discovery. |
| `required_claims` | array of strings | No, for `oauth2` | OIDC Core §5.1 claim names the business requires in the JWT authorization grant (e.g. `email`). Optional pre-filter hint — see [Provider Selection](#provider-selection). |

The `type` value is an open string, not a closed enumeration. Platforms
**MUST** treat provider entries whose `type` they do not support as filtered
out (see [Provider Selection](#provider-selection)) rather than rejecting the
business's configuration.

For `oauth2` providers, platforms **MUST** discover the authorization server
metadata from `auth_url` using the same two-tier metadata hierarchy as
[Discovery](#discovery) Step 2 (RFC 8414 primary with §3.1 path insertion,
OIDC fallback on 404 only), treating `auth_url` as the issuer. The
protected-resource step does not apply — `auth_url` is already the IdP
issuer — and the business validates the JWT grant's `iss` against it per
[Business Token Issuance](#business-token-issuance).

### Provider Selection

Platforms iterate over the `(provider key, mechanism entry)` pairs in
the business's `config.providers` map and select an entry they support
— typically one belonging to an IdP they already hold a valid upstream
token for, enabling the [Accelerated IdP Flow](#accelerated-idp-flow).
Mechanism entries under the same provider key are alternatives; a
platform may match any one of them.

A mechanism's `type` determines whether it participates in the token
and scope model. The `oauth2` type chains identity via token exchange
and contributes to the scopes of the business-issued token. Other types
**MAY** contribute no scopes — presence in `providers` does not imply
participation in the scope or token-issuance model. Selection turns on
whether the platform *supports* a mechanism's `type` and holds (or can
obtain) a suitable upstream identity, independent of whether that type
issues a token.

When a mechanism entry declares `required_claims`, platforms **SHOULD**
filter out that entry during selection if their upstream identity lacks
any of the listed claim names (e.g., the upstream token does not carry
`email`). This avoids a wasted chaining attempt that would be rejected
at the token endpoint. Reactive enforcement remains mandatory (see
[Chaining Errors at the Token Endpoint](#chaining-errors-at-the-token-endpoint))
because not every business will declare `required_claims`, and the hint
expresses claim presence only — value constraints (e.g., requiring
`email_verified=true`) are enforced reactively.

### Profile Example

A business that trusts an external IdP for chaining, while also accepting
direct OAuth flows (always available via discovery):

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
          "providers": {
            "app.example.login": [
              {
                "type": "oauth2",
                "auth_url": "https://accounts.example-login.app/",
                "required_claims": ["email"]
              }
            ]
          },
          "scopes": {
            "dev.ucp.shopping.order:read":   {},
            "dev.ucp.shopping.order:manage": {}
          }
        }
      }]
    },
    "payment_handlers": {}
  }
}
```

The platform can use the Accelerated IdP Flow with `app.example.login` if
it already holds a valid token there; otherwise it runs the standard
[Account Linking Flow](#account-linking-flow) against the business domain
via [Discovery](#discovery).

## Accelerated IdP Flow

After a platform has linked the user's identity with a trusted IdP, it can
chain that identity to new businesses without a browser redirect: the
platform obtains a **JWT authorization grant** from the IdP and presents it
to the business's token endpoint. The business validates the grant and issues
its own access token under its own authority.

This flow profiles the identity and authorization chaining pattern in
[draft-ietf-oauth-identity-chaining](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-identity-chaining-08){ target="_blank" }.
UCP tightens the JWT authorization grant beyond what the base RFCs
mandate: `aud` **MUST** be a single-valued URI plus a unique `jti` (see
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
    * `resource` and/or `audience`: the business's authorization server
      issuer URI. Platforms **MUST** include at least one.
      [RFC 8693 §2.1](https://datatracker.ietf.org/doc/html/rfc8693#section-2.1){ target="_blank" }
      permits URI values in either parameter; IdP implementations vary
      in which they accept. The IdP maps the value to the `aud` claim
      in the resulting grant; when both are sent they **MUST** carry
      identical values.
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

* `iss` **MUST** match the `auth_url` of an `oauth2` mechanism entry
  listed in `config.providers`.
* `aud` **MUST** match the business's own AS issuer URI exactly.
* The JWT signature **MUST** be verified against the IdP's `jwks_uri`; if
  JWKS cannot be retrieved, the business **MUST** fail closed.

Once the assertion is validated, the business resolves the user from
`sub` (auto-provisioning permitted) and issues an access token scoped to
the subset of requested scopes whose per-scope policy is satisfied by
the grant's claims (`acr`, `auth_time`, `amr`, etc.). If no requested
scope can be satisfied, the business **MUST** return `invalid_scope`
per [RFC 6749 §5.2](https://datatracker.ietf.org/doc/html/rfc6749#section-5.2){ target="_blank" };
platforms recover by requesting a step-up grant from the IdP or running
direct OAuth. If user interaction is required (terms acceptance,
onboarding), the business **MUST** reject the grant with `invalid_grant`
(see [Chaining Errors at the Token Endpoint](#chaining-errors-at-the-token-endpoint));
platforms recover by running the [Account Linking Flow](#account-linking-flow)
against an interactive provider.

**Claims for user resolution.** Beyond `sub`, businesses commonly need
additional claims to provision a new account with a usable contact
identifier or to surface UX hints when an existing account may match.
The stable identity key per IdP is `(iss, sub)`. For `oauth2`
providers, IdPs **SHOULD** include relevant
[OIDC Core §5.1 standard claims](https://openid.net/specs/openid-connect-core-1_0-31.html#StandardClaims){ target="_blank" }
— particularly `email` and `email_verified` — in the JWT authorization
grant when available and the user has consented. Businesses
**SHOULD NOT** auto-link accounts across IdPs by matching email or any
other claim, and **SHOULD** require user-mediated linking (the user
authenticating to the existing account) before merging identities. See
[Security Considerations](#security-considerations).

### Chaining Errors at the Token Endpoint

Validation failures use the standard OAuth 2.0 token-endpoint error format
([RFC 6749 §5.2](https://datatracker.ietf.org/doc/html/rfc6749#section-5.2){ target="_blank" }).
JWT-grant-specific failures (signature, `iss`, `aud`, `exp`, `jti` replay,
unrecognized provider, user-interaction required) map to `invalid_grant`
per [RFC 7523 §3.1](https://datatracker.ietf.org/doc/html/rfc7523#section-3.1){ target="_blank" }.
Businesses **MAY** include `error_description` and `error_uri` to aid
diagnosis or to point to onboarding documentation; platforms **MUST NOT**
treat `error_description` as machine-readable.

**Missing or insufficient claims.** When the JWT authorization grant
lacks a claim the business requires (e.g., `email` for account
resolution), the business **MUST** reject with `invalid_grant`. The
business **MAY** include `error_description` naming the missing claim
for human diagnosis (e.g., `"missing required claim: email"`); platforms
**MUST NOT** parse it for automated recovery and **SHOULD** fall back to
direct OAuth, where the business can prompt the user for the missing
information. Businesses **SHOULD** advertise standard-claim requirements
via `required_claims` (see
[Provider Configuration](#provider-configuration)) so platforms can
pre-filter; requirements beyond OIDC Core §5.1 **SHOULD** be documented
in developer-facing materials.

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
* Verify the target business (identified by `resource` and/or `audience`,
    which **MUST** carry identical values when both are sent — see
    [Flow](#flow)) is a known relying party and the user has authorized
    identity sharing with it. The IdP **MUST NOT** issue grants for
    businesses the user has not authorized.
* Issue a JWT authorization grant conforming to the
    [JWT Authorization Grant](#jwt-authorization-grant) requirements.
* Return `issued_token_type` as `urn:ietf:params:oauth:token-type:jwt`.

IdPs **SHOULD** populate OIDC Core §5.1 standard claims in JWT
authorization grants when the user has consented to share them — at
minimum `email` and `email_verified` when applicable — to support
account provisioning and UX hints at the business. Standard claims are
advisory; stable per-IdP identification remains `(iss, sub)`.

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

Advertised scopes **MUST** apply uniformly across identity paths. The
same `config.scopes` map governs scope availability whether the platform
obtained user identity via direct OAuth or the
[Accelerated IdP Flow](#accelerated-idp-flow). Per-scope policy gates
which assertions satisfy a scope; businesses honoring `min_acr` (for
example) **MUST** apply the same threshold regardless of path.

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
* **JWT grant single-use.** Businesses **MUST** enforce single-use JWT;
  a short exp narrows the replay window, but only jti tracking closes it.
  authorization grants by tracking the `jti` claim within the grant's
  validity window.
* **Grant relay.** Businesses **MUST NOT** store or forward JWT
  authorization grants received from platforms. Grants are bearer
  credentials scoped to a single audience (`aud`) and a single use.
* **Cross-IdP account linking.** Federation collapses trust boundaries:
  a business that auto-links accounts across listed providers based on
  any IdP-asserted claim (email, phone, name) extends each provider's
  verification process into account-takeover risk. A provider that
  issues `email_verified=true` for an email the user does not control
  can hijack any account at the business sharing that email. The stable
  per-IdP identifier is `(iss, sub)`; other claims are advisory.
  Businesses **SHOULD** require user-mediated linking — the user
  demonstrating control of the existing account via current-session
  authentication or equivalent — before merging accounts across IdPs.

## Future Extensibility

The schema is designed to accommodate non-OAuth provider mechanisms as
non-breaking extensions. The `provider.type` discriminator is a required,
open string: `oauth2` is the only type defined in this version, and it
reserves space for future types — wallet attestation, verifiable
credentials, or other proof-of-identity protocols. Future versions may
define additional `type` values and the corresponding discovery and
proof-presentation mechanics.

**Forward-compatibility rule for platforms:** When `config` contains fields
not defined in this version of the spec, platforms **MUST** ignore those
fields. Platforms **MUST** treat provider entries with an unsupported
`type` as filtered out, then apply the rules in
[Identity Providers](#identity-providers) to what remains.

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
