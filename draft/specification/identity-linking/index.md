# Identity Linking Capability

- **Capability Name:** `dev.ucp.common.identity_linking`

## Overview

The Identity Linking capability enables a **platform** (e.g., Google, an agentic service) to obtain authorization to perform actions on behalf of a user on a **business**'s site.

This linkage is foundational for commerce experiences, such as accessing loyalty benefits, utilizing personalized offers, managing wishlists, and executing authenticated checkouts.

**This specification leverages [OAuth 2.0](https://datatracker.ietf.org/doc/html/rfc6749)** as the mechanism for securely linking a user's platform account with their business account.

## General guidelines

(In addition to the overarching guidelines)

### For platforms

- **MUST** authenticate using their `client_id` and `client_secret` ([RFC 6749 2.3.1](https://datatracker.ietf.org/doc/html/rfc6749#section-2.3.1)) through HTTP Basic Authentication ([RFC 7617](https://datatracker.ietf.org/doc/html/rfc7617)) when exchanging codes for tokens.
  - **MAY** support Client Metadata
  - **MAY** support Dynamic Client Registration mechanisms to supersede static credential exchange.
- The platform must include the token in the HTTP Authorization header using the Bearer schema (`Authorization: Bearer <access_token>`)
- **MUST** implement the OAuth 2.0 Authorization Code flow ([RFC 6749 4.1](https://datatracker.ietf.org/doc/html/rfc6749#section-4.1)) as the primary linking mechanism.
- **SHOULD** include a unique, unguessable state parameter in the authorization request to prevent Cross-Site Request Forgery (CSRF) ([RFC 6749 10.12](https://datatracker.ietf.org/doc/html/rfc6749#section-10.12)) (part of [OAuth 2.1 draft](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-14#name-preventing-csrf-attacks)) .
- Revocation and security events
  - **SHOULD** call the business's revocation endpoint ([RFC 7009](https://datatracker.ietf.org/doc/html/rfc7009)) when a user initiates an unlink action on the platform side.
  - **SHOULD** support [OpenID RISC Profile 1.0](https://openid.net/specs/openid-risc-1_0-final.html) to handle asynchronous account updates, unlinking events, and cross-account protection.

### For businesses

- **MUST** implement OAuth 2.0 ([RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749))
- **MUST** adhere to [RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414) to declare the location of their OAuth 2.0 endpoints (`/.well-known/oauth-authorization-server`)
  - **SHOULD** implement [RFC 9728](https://datatracker.ietf.org/doc/html/rfc9728/) (HTTP Resource Metadata) to allow platforms to discover the Authorization Server associated with specific resources.
  - **SHOULD** fill in `scopes_supported` as part of [RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414).
- **MUST** enforce Client Authentication at the Token Endpoint.
- **MUST** provide an account creation flow if the user does not already have an account.
- **MUST** support standard UCP scopes, as defined in the Scopes section, granting the tokens permission to all associated Operations for a given resource.
- Additional permissions **MAY** be granted beyond those explicitly requested, provided that the requested scopes are, at minimum, included.
- The platform and business **MAY** define additional custom scopes beyond the minimum scope requirements.
- Revocation and security events
  - **MUST** implement standard Token Revocation as defined in [RFC 7009](https://datatracker.ietf.org/doc/html/rfc7009).
  - **MUST** revoke the specified token and **SHOULD** recursively revoke all associated tokens (e.g., revoking a `refresh_token` **MUST** also immediately revoke all active `access_token`s issued from it).
  - **MUST** support revocation requests authenticated with the same client credentials used for the token endpoint.
  - **SHOULD** support [OpenID RISC Profile 1.0](https://openid.net/specs/openid-risc-1_0-final.html) to enable Cross-Account Protection and securely signal revocation or account state changes initiated by the business side. ([See Cross-Account protection](https://developers.google.com/identity/account-linking/unlinking#cross-account_protection_risc))

## Scopes

We'd ask users to authorize the platform to have access to all the scopes that could be required for UCP, regardless of whether the business supports them.

### Structure

The scope complexity should be hidden in the consent screen shown to the user: they shouldn't see one row for each action, but rather a general one, for example "Allow [platform] to manage checkout sessions".

### Mapping between resources, actions and capabilities

| Resources       | Operation | Scope Action                  |
| --------------- | --------- | ----------------------------- |
| CheckoutSession | Get       | `ucp:scopes:checkout_session` |
| CheckoutSession | Create    | `ucp:scopes:checkout_session` |
| CheckoutSession | Update    | `ucp:scopes:checkout_session` |
| CheckoutSession | Delete    | `ucp:scopes:checkout_session` |
| CheckoutSession | Cancel    | `ucp:scopes:checkout_session` |
| CheckoutSession | Complete  | `ucp:scopes:checkout_session` |

A scope covering a capability must grant access to all operations associated to the capability. For example, ucp:scopes:checkout_session must grant all of: Get, Create, Update, Delete, Cancel, Complete.

## Examples

### Authorization server metadata

Example of [metadata](https://datatracker.ietf.org/doc/html/rfc8414#section-2) supposed to be hosted in /.well-known/oauth-authorization-server as per [RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414):

```json
{
  "issuer": "https://merchant.example.com",
  "authorization_endpoint": "https://merchant.example.com/oauth2/authorize",
  "token_endpoint": "https://merchant.example.com/oauth2/token",
  "revocation_endpoint": "https://merchant.example.com/oauth2/revoke",
  "scopes_supported": [
    "ucp:scopes:checkout_session",
  ],
  "response_types_supported": [
    "code"
  ],
  "grant_types_supported": [
    "authorization_code",
    "refresh_token"
  ],
  "token_endpoint_auth_methods_supported": [
    "client_secret_basic"
  ],
  "service_documentation": "https://merchant.example.com/docs/oauth2"
}
```
