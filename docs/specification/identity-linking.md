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

Platforms **MUST** select the mechanism they support from the
`supported_mechanisms` array to proceed with identity linking.

## Capability-Driven Scope Negotiation (Least Privilege)

To maintain the **Principle of Least Privilege**, authorization scopes are
**NOT** hardcoded within the identity linking capability.

Instead, **authorization scopes are dynamically derived from the final
intersection of negotiated capabilities**.

1. **Schema Declaration:** Each individual capability schema explicitly defines
   its own required identity scopes (e.g., `dev.ucp.shopping.checkout` declares
   `ucp:scopes:checkout_session`).
2. **Dynamic Derivation:** During UCP Discovery, when the platform computes the
   intersection of supported capabilities between itself and the business, it
   extracts the required scopes from **only** the successfully negotiated
   capabilities.
3. **Authorization:** The platform initiates the connection requesting **only**
   the derived scopes. If a capability (e.g., `order`) is excluded from the
   active capability set, its respective scopes **MUST NOT** be requested by the
   platform.

### Scope Structure & Mapping

The scope complexity should be hidden in the consent screen shown to the user:
they shouldn't see one row for each action, but rather a general one, for
example "Allow \[platform\] to manage checkout sessions". A requested scope
granting access to a capability must grant access to all operations strictly
associated with the capability.

Example capability-to-scope mapping based on UCP schemas:

| Resources       | Operation                                     | Scope Action                  |
| :-------------- | :-------------------------------------------- | :---------------------------- |
| CheckoutSession | Get, Create, Update, Delete, Cancel, Complete | `ucp:scopes:checkout_session` |

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
   directly from that exact URI.
2. **RFC 8414 Standard Discovery**: If no explicit endpoint is provided, the
   platform **MUST** append `/.well-known/oauth-authorization-server` to the
   defined `issuer` string and fetch.
3. **OIDC Fallback (Lowest Priority)**: If the RFC 8414 fetch returns a
   `404 Not Found`, the platform **MUST** append
   `/.well-known/openid-configuration` to the defined `issuer` string and fetch.

Example metadata retrieved via RFC 8414:

```json
{
    "issuer": "https://auth.merchant.example.com",
    "authorization_endpoint": "https://auth.merchant.example.com/oauth2/authorize",
    "token_endpoint": "https://auth.merchant.example.com/oauth2/token",
    "revocation_endpoint": "https://auth.merchant.example.com/oauth2/revoke"
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
- **MUST** enforce Client Authentication at the Token Endpoint.
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

### Scenario: An AI Shopping Agent Checking Out

1. **Profile Discovery & Capability Negotiation**: The agent fetches the
   merchant's `/.well-known/ucp` profile. The agent intersects its own profile
   with the business's and successfully negotiates `dev.ucp.shopping.checkout`
   and `dev.ucp.common.identity_linking`. If the business supported
   `dev.ucp.shopping.order`, but the agent did not, it is excluded.
2. **Schema Fetch & Scope Derivation**: The agent parses the schema logic for
   `dev.ucp.shopping.checkout` and derives that the required scope is strictly
   `ucp:scopes:checkout_session`. `ucp:scopes:order_management` is strictly
   omitted.
3. **Identity Mechanism Execution**: Because `identity_linking` matched and
   defined mechanism `type: oauth2` with issuer
   `https://auth.merchant.example.com`, the agent executes standard OAuth
   discovery by appending `/.well-known/oauth-authorization-server` to the
   issuer string.
4. **User Consent & Authorization**: The agent generates a consent URL to prompt
   the user (or invokes the authorization flow directly in the GUI), using the
   dynamically derived scopes.

    ```http
    GET https://auth.merchant.example.com/oauth2/authorize
      ?response_type=code
      &client_id=agent_client_123
      &redirect_uri=https://agent.example.com/callback
      &scope=ucp:scopes:checkout_session
      &state=xyz123
    ```

    _The user is prompted to consent **only** to "Manage Checkout Sessions"._

5. **Authorized UCP Execution**: The platform securely exchanges the
   authorization code for an `access_token` bound only to checkout and
   successfully utilizes the UCP REST APIs via
   `Authorization: Bearer <access_token>`.
