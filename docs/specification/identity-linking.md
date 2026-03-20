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
using an open string vocabulary (e.g., `oauth2`, `verifiable_credential`) and
provide the necessary resolution endpoints (like `issuer`).

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
