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

## Overview

The Identity Linking capability enables a **platform** to obtain
authorization to perform actions on behalf of a buyer on a **business**'s
(relying party) site.

This linkage is foundational for commerce experiences, such as accessing
loyalty benefits, utilizing personalized offers, managing wishlists, and
executing authenticated checkouts.

**This specification leverages
[OAuth 2.0](https://datatracker.ietf.org/doc/html/rfc6749){ target="_blank" }** as the mechanism
for securely linking a buyer's platform account with their business account.

When a buyer's identity has already been established with an external identity
provider, this specification uses the
[OAuth Identity and Authorization Chaining](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-identity-chaining-08){ target="_blank" }
pattern to propagate that identity across trust boundaries — enabling a
platform to obtain business-issued tokens without a new browser-based OAuth
flow.

### Participants

| UCP Role | Identity Role | Description |
| :------- | :------------ | :---------- |
| **Identity Provider (IdP)** | Identity Provider | Authenticates buyers and issues tokens. May be the business itself or an external service. |
| **Business** | Relying Party (RP) | Validates IdP assertions and issues its own tokens to authorize buyer operations. |
| **Platform** | User Agent | Trusted intermediary that mediates IdP selection, account linking, and per-business consent on behalf of the buyer. |

## General Guidelines

(In addition to the overarching guidelines)

### For platforms

* **MUST** authenticate using their `client_id` and `client_secret`
    ([RFC 6749 2.3.1](https://datatracker.ietf.org/doc/html/rfc6749#section-2.3.1){ target="_blank" })
    through HTTP Basic Authentication
    ([RFC 7617](https://datatracker.ietf.org/doc/html/rfc7617){ target="_blank" })
    when exchanging codes for tokens.
* The platform **MUST** include the token in the HTTP Authorization header using
    the Bearer schema (`Authorization: Bearer <access_token>`)
* **MUST** implement the OAuth 2.0 Authorization Code flow
    ([RFC 6749 4.1](https://datatracker.ietf.org/doc/html/rfc6749#section-4.1){ target="_blank" })
    as the primary linking mechanism.
* **MUST** use PKCE
    ([RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636){ target="_blank" })
    with the Authorization Code flow.
* **MUST** validate the `iss` parameter in the authorization response
    ([RFC 9207](https://datatracker.ietf.org/doc/html/rfc9207){ target="_blank" }) to prevent
    Mix-Up Attacks.
* **SHOULD** include a `state` parameter per
    [OAuth 2.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-14){ target="_blank" }.
* When `config.providers` is present in the business's identity linking
    capability, the platform **SHOULD** select a provider it supports from
    the business's advertised list (see
    [Identity Providers](#identity-providers)).
* Before initiating identity chaining with a business, the platform
    **SHOULD** offer the buyer a choice of available identity providers and
    indicate that the selected provider's identity will be shared with the
    business.
* Revocation and security events
    * **SHOULD** revoke tokens at both layers when a buyer initiates an
        unlink action (see [Token Lifecycle](#token-lifecycle)).
    * **SHOULD** support
        [OpenID RISC Profile 1.0](https://openid.net/specs/openid-risc-1_0-final.html){ target="_blank" }
        to handle asynchronous account updates, unlinking events, and
        cross-account protection.

### For businesses

* **MUST** implement OAuth 2.0
    ([RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749){ target="_blank" })
* **MUST** adhere to [RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" } to
    declare the location of their OAuth 2.0 endpoints
    (`/.well-known/oauth-authorization-server`). When the business delegates
    authentication to an external identity provider, the IdP's `auth_url`
    serves as the base for RFC 8414 discovery instead.
    * **SHOULD** implement
        [RFC 9728](https://datatracker.ietf.org/doc/html/rfc9728/){ target="_blank" } (HTTP
        Resource Metadata) to allow platforms to discover the Authorization
        Server associated with specific resources.
    * **MUST** populate `scopes_supported` in their
        [RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" } metadata
        to allow platforms to detect scope mismatches early, before initiating
        the authorization flow.
* **MAY** declare trusted identity providers in `config.providers`
    (see [Identity Providers](#identity-providers)).
* Businesses **MUST** only list identity providers they explicitly trust.
* **MUST** enforce Client Authentication at the Token Endpoint.
* **MUST** enforce exact string matching for the `redirect_uri` parameter
    during the authorization request to prevent open redirects and token theft.
* **MUST** enforce PKCE
    ([RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636){ target="_blank" }) validation
    at the Token Endpoint for all authorization code exchanges.
* **MUST** return the `iss` parameter in the authorization response
    ([RFC 9207](https://datatracker.ietf.org/doc/html/rfc9207){ target="_blank" }).
* When the business lists external identity providers in `config.providers`,
    the business **MUST** support the JWT bearer assertion grant type
    ([RFC 7523](https://datatracker.ietf.org/doc/html/rfc7523){ target="_blank" })
    at its token endpoint to accept JWT authorization grants from trusted IdPs.
    The business **MUST** include
    `urn:ietf:params:oauth:grant-type:jwt-bearer` in
    `grant_types_supported` in its
    [RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" } metadata.
* **MUST** provide an account creation flow if the buyer does not already have
    an account.
* **MUST** support standard UCP scopes, as defined in the Scopes section,
    granting the tokens permission to all associated Operations for a given
    resource.
* Additional permissions **MAY** be granted beyond those explicitly requested,
    provided that the requested scopes are, at minimum, included.
* The platform and business **MAY** define additional custom scopes beyond the
    minimum scope requirements.
* Revocation and security events
    * **MUST** implement standard Token Revocation as defined in
        [RFC 7009](https://datatracker.ietf.org/doc/html/rfc7009){ target="_blank" }.
    * **MUST** revoke the specified token and **SHOULD** recursively revoke
        all associated tokens (e.g., revoking a `refresh_token` **MUST** also
        immediately revoke all active `access_token`s issued from it).
    * **SHOULD** support
        [OpenID RISC Profile 1.0](https://openid.net/specs/openid-risc-1_0-final.html){ target="_blank" }
        to enable Cross-Account Protection and securely signal revocation or
        account state changes initiated by the business side.

## Scopes

Scopes define the permissions an identified buyer grants to a platform
within a capability. Businesses declare which capabilities
offer buyer-scoped features in the `config.capabilities` map of their
identity linking configuration (see
[Capability Scope Configuration](#capability-scope-configuration)).

### Scope Naming

Scope tokens use the **capability name** directly as the scope identifier.
This ensures global uniqueness through UCP's existing reverse-DNS naming and
eliminates a separate scope namespace:

* **Coarse-grained** (no sub-scopes): the capability name is the scope.
  Example: `dev.ucp.shopping.cart`
* **Fine-grained** (sub-scopes): the capability name with a colon-separated
  operation group. Example: `dev.ucp.shopping.order:read`,
  `dev.ucp.shopping.order:manage`

Sub-scopes are defined by each capability's own spec as **operation groups**
— logical groupings of operations (e.g., `read` = Get/List, `manage` =
Cancel/Return). Each capability defines its own operation group names.

### Scope Derivation

Platforms derive the authorization scope set from the business's identity
linking configuration:

1. Read `config.capabilities` from the business's
   `dev.ucp.common.identity_linking` capability entry.
2. Intersect the map keys with the negotiated capability set — ignore
   capabilities not in the intersection.
3. For each remaining entry: if `scopes` is present, expand each sub-scope
   to `<capability-name>:<sub-scope>`; if absent, use the capability name.
4. The union of all expanded scopes is the authorization scope set.

### Scopes and External Identity Providers

When a buyer's identity is established through an external IdP via the
[Accelerated IdP Flow](#accelerated-idp-flow), UCP scopes are requested from
the **business's** token endpoint during grant presentation — not from the
IdP during account linking.

IdP tokens carry IdP-defined scopes that authorize the platform to perform
token exchange. Businesses **MUST** include UCP scopes in their
`scopes_supported`
([RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" }) metadata and
issue access tokens carrying the granted UCP scopes.

### Consent Presentation

Consent screens are rendered by the authorization server (business or IdP),
which owns the scope definitions and controls the UI. Consent screens
**SHOULD** group scopes by capability rather than listing individual
operations: for example, "Allow \[platform\] to view your order history".
This specification does not define scope description strings — the
authorization server is responsible for presenting human-readable consent
text for the scopes it supports.

## Examples

### Authorization Server Metadata

Example of
[metadata](https://datatracker.ietf.org/doc/html/rfc8414#section-2){ target="_blank" }
supposed to be hosted in `/.well-known/oauth-authorization-server` as per
[RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" }:

```json
{
  "issuer": "https://merchant.example.com",
  "authorization_endpoint": "https://merchant.example.com/oauth2/authorize",
  "token_endpoint": "https://merchant.example.com/oauth2/token",
  "revocation_endpoint": "https://merchant.example.com/oauth2/revoke",
  "jwks_uri": "https://merchant.example.com/oauth2/jwks",
  "scopes_supported": [
    "dev.ucp.shopping.checkout"
  ],
  "response_types_supported": [
    "code"
  ],
  "grant_types_supported": [
    "authorization_code",
    "refresh_token",
    "urn:ietf:params:oauth:grant-type:jwt-bearer"
  ],
  "token_endpoint_auth_methods_supported": [
    "client_secret_basic"
  ],
  "service_documentation": "https://merchant.example.com/docs/oauth2"
}
```

The `urn:ietf:params:oauth:grant-type:jwt-bearer` grant type indicates the
business accepts JWT authorization grants from trusted identity providers via
the [Accelerated IdP Flow](#accelerated-idp-flow).

## Identity Providers

Businesses **MAY** declare trusted identity providers in the `config.providers`
map of their `dev.ucp.common.identity_linking` capability entry. Each provider
is keyed by a reverse-domain identifier and specifies an `auth_url` for
OAuth 2.0 discovery.

When `config.providers` is absent, platforms fall back to
[RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" } discovery on the
business domain — preserving the baseline behavior described above.

### Provider Configuration

Each provider entry uses OAuth 2.0 with
[RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" } discovery. The only
required field is the discovery base URL:

| Field | Type | Required | Description |
| :---- | :--- | :------- | :---------- |
| `auth_url` | string (URI) | Yes | Base URL for authorization server metadata discovery. |

Platforms **MUST** discover authorization server metadata from `auth_url`
using the following resolution hierarchy:

1. **RFC 8414 (Primary)**: Append `/.well-known/oauth-authorization-server` to
   `auth_url` and fetch. If the response is `2xx`, use this metadata. If the
   response is `404 Not Found`, proceed to step 2. For any other non-2xx
   response or network error, the platform **MUST** abort — **MUST NOT**
   proceed to the fallback.
2. **OIDC Discovery (Fallback)**: Append `/.well-known/openid-configuration`
   to `auth_url` and fetch. If the response is `2xx`, use this metadata. For
   any non-2xx response or network error, the platform **MUST** abort the
   account linking process.

### Provider Discovery

The platform reads the business's `config.providers` map from the
`dev.ucp.common.identity_linking` capability entry. The platform selects a
provider it can perform account linking with (or already holds a token for).

A business **MAY** list itself as a provider entry. This represents
business-hosted OAuth using the same discovery mechanism as external providers.
When the platform selects a self-listed provider (i.e., the provider's
`auth_url` resolves to the business's own authorization server), the platform
uses the standard Authorization Code flow described in
[Account Linking](#account-linking) — the
[Accelerated IdP Flow](#accelerated-idp-flow) is not needed because the
business is both the identity provider and the relying party.

### Business Profile Example

```json
{
  "ucp": {
    "version": "2026-01-11",
    "capabilities": {
      "dev.ucp.common.identity_linking": [{
        "version": "2026-01-11",
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
          "capabilities": {
            "dev.ucp.shopping.checkout": {},
            "dev.ucp.shopping.order": {
              "required": true,
              "scopes": ["read", "manage"]
            }
          }
        }
      }]
    }
  }
}
```

In this example, the business trusts `app.example.login` as an external IdP
and also lists itself (`com.example.merchant`) as a provider for
business-hosted OAuth. Checkout has buyer-scoped features (saved addresses,
loyalty) but works without auth (guest checkout). Order requires buyer auth
and offers fine-grained sub-scopes (`read`, `manage`).

## Capability Scope Configuration

Businesses declare which capabilities offer buyer-scoped features in the
`config.capabilities` map of their identity linking configuration. This map
is the authoritative source for scope declarations — individual capability
schemas do not declare their own scopes.

### Three Access Levels

UCP capabilities operate at three distinct access levels:

| Level | Authentication | Example |
| :---- | :------------- | :------ |
| **Public** | None | Browse a public catalog |
| **Agent-authenticated** | Platform credentials | Guest checkout, read agent's own orders |
| **Buyer-authenticated** | Platform + buyer identity | Saved addresses, full order history, personalized pricing |

Identity linking is the mechanism for reaching buyer-authenticated access.
Capabilities are **never** removed from the negotiated intersection based on
identity linking. When a capability declares `required: true` and the
platform calls it without a buyer identity token (obtained via identity
linking), the business **MUST** return a UCP error response with an
`identity_required` error code and **SHOULD** include a `continue_url`
pointing to the business's login or account linking flow. This is an
application-level error — the agent is authenticated, but the business
requires buyer identity to serve the request.

### Configuration Shape

Each entry in `config.capabilities` is keyed by a capability name and
declares the identity requirements for that capability:

```json
"dev.ucp.common.identity_linking": [{
  "version": "2026-03-14",
  "config": {
    "providers": { "..." : { "auth_url": "..." } },
    "capabilities": {
      "dev.ucp.shopping.checkout": {},
      "dev.ucp.shopping.order": {
        "required": true,
        "scopes": ["read", "manage"]
      }
    }
  }
}]
```

**Fields per entry:**

{{ extension_schema_fields('common/identity_linking.json#/$defs/capability_identity_config', 'identity-linking') }}

Capabilities **absent** from the map have no buyer-scoped features.

### Platform Behavior

1. Compute the capability intersection as normal.
2. Read `config.capabilities` from the business's identity linking entry.
3. Derive the scope set (see [Scope Derivation](#scope-derivation)).
4. Plan the authentication strategy:
    * Any intended capability has `required: true`? The platform **MUST**
        complete identity linking before calling those capabilities.
    * All intended capabilities are absent or not required? The platform
        **MAY** start immediately and link later when beneficial.
5. Request the necessary scopes during identity linking. Platforms
   **SHOULD** request scopes incrementally as capabilities are used,
   not all upfront.

### Examples

**B2C retailer** — public catalog, guest checkout, buyer auth upgrades:

```json
"capabilities": {
  "dev.ucp.shopping.checkout": {}
}
```

Catalog is absent (fully public). Checkout is present without `required` —
guest checkout works, buyer auth unlocks saved addresses and loyalty.

**B2B wholesaler** — everything gated:

```json
"capabilities": {
  "dev.ucp.shopping.catalog.lookup": { "required": true },
  "dev.ucp.shopping.checkout": { "required": true },
  "dev.ucp.shopping.order": {
    "required": true,
    "scopes": ["read", "manage"]
  }
}
```

All `required: true` — the buyer must authenticate and link their identity
before the platform can access any capability. Order has sub-scopes — the
buyer can grant read-only or full manage access.

## Account Linking

Account linking is the initial OAuth flow between the platform and an identity
provider. This is a one-time operation per IdP — once complete, the token is
reusable across businesses that trust the same provider.

### Flow

1. Platform discovers `config.providers` in the business's identity linking
   capability.
2. Platform selects a provider it supports from the business's list.
3. If the platform holds no token for the selected provider, it initiates
   account linking with the preferred provider:
    * Performs [RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" }
      discovery against the provider's `auth_url`.
    * Selects a grant type from the IdP's `grant_types_supported` metadata
      and executes the corresponding OAuth 2.0 flow against the discovered
      endpoints.
    * Stores the resulting access token and refresh token.

Account linking follows the OAuth mechanics described in the
[General Guidelines](#general-guidelines) — the only difference is the
authorization server is the IdP (discovered from `auth_url`), not the
business's own domain. Platforms **MAY** support additional grant types
advertised by the IdP, such as streamlined linking extensions for
server-to-server token exchange.

### Headless and Agentic Contexts

Identity providers **SHOULD** support the device authorization grant
([RFC 8628](https://datatracker.ietf.org/doc/html/rfc8628){ target="_blank" })
for platforms operating in contexts where browser redirect is impractical
(e.g., CLI agents, voice assistants). The provider advertises support via the
`grant_types_supported` field in its
[RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" } metadata.

## Accelerated IdP Flow

After account linking, the platform holds a valid IdP token. When the platform
encounters a new business that trusts the same IdP, the platform chains the
buyer's identity across trust domains: it obtains a **JWT authorization
grant** from the IdP and presents it to the business's token endpoint. The
business validates the grant and issues its own access token — no browser
redirect required.

This flow implements the identity and authorization chaining pattern described
in
[draft-ietf-oauth-identity-chaining](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-identity-chaining-08){ target="_blank" }.

### Flow

1. Platform discovers `config.providers` in the business's identity linking
   capability.
2. Platform selects a provider it supports and already holds a valid token for.
3. Platform requests a JWT authorization grant from the IdP via token exchange
   ([RFC 8693](https://datatracker.ietf.org/doc/html/rfc8693){ target="_blank" }) at the IdP's
   token endpoint:
    * `grant_type`: `urn:ietf:params:oauth:grant-type:token-exchange`
    * `subject_token`: the platform's existing IdP access token
    * `subject_token_type`: `urn:ietf:params:oauth:token-type:access_token`
    * `resource`: the business's authorization server issuer URI (per
      [draft-ietf-oauth-identity-chaining §3.1](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-identity-chaining-08#section-3.1){ target="_blank" }).
      Platforms **MUST** use the `resource` parameter, not `audience`, because
      the target is a concrete URI. The IdP maps this value to the `aud` claim
      in the resulting JWT authorization grant.
    * `requested_token_type`: `urn:ietf:params:oauth:token-type:jwt`
4. The IdP validates the subject token, verifies the platform is authorized
   to request a grant for the target business, and returns a short-lived JWT
   authorization grant with `issued_token_type` set to
   `urn:ietf:params:oauth:token-type:jwt`.
5. Platform presents the JWT authorization grant to the business's token
   endpoint using the JWT bearer assertion grant
   ([RFC 7523](https://datatracker.ietf.org/doc/html/rfc7523){ target="_blank" }):
    * `grant_type`: `urn:ietf:params:oauth:grant-type:jwt-bearer`
    * `assertion`: the JWT authorization grant
    * `scope`: the derived scope set from
      [Scope Derivation](#scope-derivation) (e.g.,
      `dev.ucp.shopping.checkout`)
6. The business's authorization server validates the JWT authorization grant,
   resolves the buyer identity, and issues an access token under its own
   authority.
7. Platform uses the business-issued access token for subsequent API calls
   via the `Authorization: Bearer <access_token>` header.

The platform **MUST NOT** present a raw IdP token directly to a business.
Identity chaining ensures each business issues tokens under its own authority
with the correct audience binding and scope policy.

### JWT Authorization Grant

The **JWT authorization grant** is a signed JWT
([RFC 7519](https://datatracker.ietf.org/doc/html/rfc7519){ target="_blank" }) issued by the
IdP that asserts the buyer's identity for use with a specific business. It is
not an access token — it is a short-lived credential the platform presents to
the business's authorization server to obtain one.

The JWT authorization grant **MUST** contain at minimum:

| Claim | Description |
| :---- | :---------- |
| `iss` | The IdP's issuer identifier. |
| `sub` | The buyer's identifier at the IdP. |
| `aud` | The business's authorization server issuer URI. **MUST** be restricted to a single authorization server. |
| `exp` | Expiration time. **SHOULD** be no more than 60 seconds after `iat`. |
| `iat` | Time at which the JWT was issued. |
| `jti` | Unique token identifier for replay protection. |

The IdP **MAY** include additional claims to convey authorization context,
consent records, or other information relevant to the business's token
issuance policy.

### Business Token Issuance

Upon receiving a JWT authorization grant at its token endpoint, the
business's authorization server **MUST**:

1. Validate the JWT per
   [RFC 7523 Section 3](https://datatracker.ietf.org/doc/html/rfc7523#section-3){ target="_blank" }.
2. Verify the `iss` claim identifies a provider listed in the business's
   `config.providers`.
3. Verify the `aud` claim matches the business's own authorization server
   issuer URI.
4. Verify the JWT signature using the IdP's published JWKS (`jwks_uri`).
   If the JWKS cannot be retrieved, the business **MUST** fail closed and
   reject the grant.
5. Resolve the buyer identity from the `sub` claim.
    * If the buyer has an existing account, proceed to step 6.
    * If the buyer does not have an existing account, the business **MAY**
      provision one automatically. If the business requires buyer
      interaction (e.g., terms acceptance, onboarding), it **MUST** return
      a UCP error response with a `continue_url` where the buyer can
      complete the process. After the buyer completes onboarding, the
      platform retries the grant presentation.
6. Issue an access token scoped to the requested UCP scopes.

The business **MUST** reject grants that are expired, malformed, or
previously used.

The business **MAY** perform **claims transcription** — mapping the IdP's
subject identifier to a local buyer identifier, adjusting scopes, or applying
data minimization — during token issuance. The semantics of shared claims
(e.g., how `sub` maps to a local buyer identity) are established
out-of-band between the IdP and the business when the trust relationship is
configured. This specification does not prescribe the mechanism for that
agreement.

### Error Handling

When validation fails at the business's token endpoint, the business
**MUST** return a standard OAuth error response
([RFC 6749 Section 5.2](https://datatracker.ietf.org/doc/html/rfc6749#section-5.2){ target="_blank" }).
The following table maps validation failures to error responses:

| Condition | Error | HTTP Status | Description |
| :-------- | :---- | :---------- | :---------- |
| JWT from untrusted IdP | `invalid_grant` | 400 | The `iss` claim does not match any provider in `config.providers`. |
| Audience mismatch | `invalid_grant` | 400 | The `aud` claim does not match the business's issuer URI. |
| JWT expired | `invalid_grant` | 400 | The `exp` claim indicates the grant has expired. |
| JWT signature invalid | `invalid_grant` | 400 | Signature verification against the IdP's JWKS failed. |
| JWT previously used | `invalid_grant` | 400 | The `jti` has already been consumed (replay). |
| IdP JWKS unreachable | `server_error` | 500 | Business could not retrieve the IdP's JWKS. Business **MUST** fail closed. |
| Unsupported scope | `invalid_scope` | 400 | Requested scope is not recognized or not permitted. |

When account linking fails at the IdP (standard OAuth flow), the platform
receives standard OAuth errors. If the buyer declines consent, the IdP
returns `access_denied`. The platform **SHOULD** offer alternative providers
or fall back to direct business-hosted OAuth.

### Buyer Awareness

When multiple identity providers are available, the platform **SHOULD** offer
the buyer a choice of providers. Before initiating identity chaining, the
platform **SHOULD** inform the buyer which business will receive their
identity. The mechanism varies by platform modality and is not prescribed
by this specification. Consent enforcement is the responsibility of the
IdP's token exchange policy — the IdP **MUST NOT** issue JWT authorization
grants for businesses the buyer has not authorized.

### Token Lifecycle

Identity chaining produces two independent token lifecycles. Each layer is
managed through its own OAuth endpoints, and revocation at one layer does not
automatically propagate to the other.

**Business-issued tokens.** Access tokens issued by the business follow the
business's token lifecycle. Businesses **SHOULD NOT** issue refresh tokens
in response to a JWT bearer assertion grant — doing so creates credentials
that outlive the IdP session, allowing continued access after the buyer
revokes the IdP relationship
([draft-ietf-oauth-identity-chaining §5.4](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-identity-chaining-08#section-5.4){ target="_blank" }).
When the business-issued access token expires, the platform **SHOULD**
obtain a new JWT authorization grant from the IdP and re-present it to the
business. Platforms **MUST** direct revocation requests
([RFC 7009](https://datatracker.ietf.org/doc/html/rfc7009){ target="_blank" }) to the
business's endpoints as discovered via
[RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" }.

**IdP tokens.** Tokens obtained during account linking follow the IdP's
token lifecycle. Platforms **MUST** direct revocation of IdP tokens to the
IdP's revocation endpoint as discovered via
[RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" }.

Revoking an IdP token prevents the platform from obtaining **new** JWT
authorization grants, but does not retroactively invalidate business-issued
tokens already in circulation. Conversely, revoking a business-issued token
terminates access to that business but does not affect the platform's IdP
token or tokens issued by other businesses.

When the buyer initiates an unlink action:

* The platform **SHOULD** revoke both the IdP token (at the IdP's revocation
    endpoint) and the business-issued token (at the business's revocation
    endpoint).
* The business **MAY** independently revoke tokens it has issued — for
    example, in response to a fraud signal or account closure — without
    coordinating with the IdP.
* The IdP **MAY** independently revoke the platform's token — for example,
    when the buyer's IdP account is suspended — without coordinating with
    individual businesses.

## IdP Requirements

Identity providers listed in `config.providers` **MUST** publish
authorization server metadata via
[RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" }
(`/.well-known/oauth-authorization-server`) or OpenID Connect Discovery
(`/.well-known/openid-configuration`). The metadata **MUST** include, beyond
the fields the respective specification already requires:

* `revocation_endpoint` — required to support token revocation per the
    [Token Lifecycle](#token-lifecycle) section.
* `jwks_uri` — required so businesses can verify the signature on JWT
    authorization grants issued by the IdP.
* `urn:ietf:params:oauth:grant-type:token-exchange` in
    `grant_types_supported` — required to enable the
    [Accelerated IdP Flow](#accelerated-idp-flow).

When processing token exchange requests for JWT authorization grants, the
IdP **MUST**:

* Authenticate the platform and verify it is authorized to present the
    subject token
    ([RFC 8693 Section 2.1](https://datatracker.ietf.org/doc/html/rfc8693#section-2.1){ target="_blank" }).
* Verify the target business (identified by the `resource` parameter) is a
    known relying party. The IdP **MUST** reject requests where the target
    business is unknown or not permitted by policy
    ([RFC 8693 Section 2.2.2](https://datatracker.ietf.org/doc/html/rfc8693#section-2.2.2){ target="_blank" }).
* Issue a JWT authorization grant conforming to the
    [JWT authorization grant](#jwt-authorization-grant) requirements.
* Return `issued_token_type` as `urn:ietf:params:oauth:token-type:jwt` in
    the token exchange response.

## Security Considerations

* **Token scope.** IdP tokens **MUST NOT** be assumed to carry broader
    permissions than those granted during account linking consent.
* **Auth URL validation.** Platforms **SHOULD** verify that `auth_url` serves
    valid [RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414){ target="_blank" } metadata
    before initiating account linking.
* **Transport security.** All IdP and business communication **MUST** use
    HTTPS with a minimum of TLS 1.2 as required by
    [RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749){ target="_blank" }.
* **JWT grant lifetime.** JWT authorization grants **MUST** be short-lived.
    The `exp` claim **SHOULD** be no more than 60 seconds after `iat`. Short
    lifetimes limit the window for grant theft and replay.
* **JWT grant single use.** Businesses **SHOULD** enforce single-use JWT
    authorization grants by tracking the `jti` claim within the grant's
    validity window.
* **Grant replay.** Businesses **MUST NOT** store or forward JWT
    authorization grants received from platforms.
