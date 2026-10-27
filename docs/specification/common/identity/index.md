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

# Identity Capability

* **Capability Name:** `dev.ucp.common.identity`
* **Schema:** `https://ucp.dev/{{ ucp_version }}/schemas/common/identity.json`

## Overview

The Identity capability provides a read-only resource representing the
authenticated Buyer's profile and account state with a Business. While
[Identity Linking](../identity-linking/index.md) establishes an OAuth 2.0
relationship and issues a user identity token, the Identity capability exposes a
structured operation (`Get Identity`) for a Platform to retrieve the
authenticated Buyer's business-scoped attributes and negotiated identity
extensions before starting a cart, checkout, or booking session.

Identity is a Common capability bound to the `dev.ucp.common` service. A single
`Get Identity` call returns user state applicable across every vertical the
Business exposes, including retail shopping and lodging.

Typical upper-funnel use cases include:

* Retrieving the authenticated Buyer's loyalty memberships, active tiers,
  benefits, reward balances, available credits, and tier progress via the
  [Loyalty Extension](../extensions/loyalty.md) to personalize discovery,
  search results, and property or product cards.
* Confirming which account or contact profile is linked with the Business.
* Retrieving saved postal addresses associated with the Buyer's account.

## Operation

| Operation | Description |
| :--- | :--- |
| **Get Identity** | Retrieve the authenticated Buyer's identity resource and any active extensions. |

## Schema

### Identity

{{ schema_fields('identity_resp', 'common/identity') }}

### Postal Address

{{ schema_fields('types/postal_address', 'common/identity') }}

### Link

{{ schema_fields('types/link', 'common/identity') }}

## Access and Relationship to Identity Linking

`dev.ucp.common.identity` operates at the
[User-authenticated](../identity-linking/index.md#access-levels) access level.
The Platform **MUST** present a valid user identity token obtained via
[Identity Linking](../identity-linking/index.md) on every `Get Identity`
request.

The Business resolves the target user exclusively from the presented user
identity token; `Get Identity` takes no user identifier in the request path or
body. This prevents horizontal privilege escalation and ensures that a Platform
can only read the profile corresponding to the subject of the presented Bearer
token.

A Business **MUST** populate `id` with an opaque, business-scoped identifier for
the authenticated user and **MAY** populate additional profile fields (`email`,
`email_verified`, `phone_number`, `phone_verified`, `first_name`, `last_name`,
`addresses`, `links`) according to the granted OAuth scopes, user consent, and
its data-minimization policy.

## Extension Composition

Extensions can compose onto `dev.ucp.common.identity` by declaring
`dev.ucp.common.identity` in their `extends` array and defining a
`dev.ucp.common.identity` entry in their schema `$defs`.

When `dev.ucp.common.loyalty` is negotiated alongside `dev.ucp.common.identity`,
the Business **MAY** populate the top-level `loyalty` map on the identity
response with the authenticated Buyer's verified loyalty memberships (see
[Loyalty Extension](../extensions/loyalty.md)).

### Example with Loyalty Extension

<!-- ucp:example schema=common/identity op=read -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.identity": [
        { "version": "{{ ucp_version }}" }
      ],
      "dev.ucp.common.loyalty": [
        {
          "version": "{{ ucp_version }}",
          "extends": "dev.ucp.common.identity"
        }
      ]
    }
  },
  "id": "usr_9f8e7d6c",
  "email": "e.beckett@example.com",
  "email_verified": true,
  "first_name": "Elisa",
  "last_name": "Beckett",
  "loyalty": {
    "com.example.hotel.rewards": {
      "id": "mem_102938",
      "display_id": "****2938",
      "name": "Example Hotel Honors",
      "provisional": false,
      "tiers": [
        {
          "id": "diamond",
          "name": "Diamond",
          "benefits": [
            {
              "id": "BEN_BREAKFAST",
              "description": "Complimentary daily continental breakfast"
            },
            {
              "id": "BEN_CHECKOUT",
              "description": "Guaranteed 4:00 PM late checkout"
            }
          ]
        }
      ],
      "tier_progress": [
        {
          "target_tier_id": "lifetime_diamond",
          "target_tier_name": "Lifetime Diamond",
          "qualification_operator": "all",
          "metrics": [
            {
              "metric_type": "nights",
              "unit": "NIGHTS",
              "current_amount": 880,
              "target_amount": 1000,
              "remaining_amount": 120,
              "description": "120 nights needed for Lifetime Diamond"
            }
          ]
        }
      ],
      "rewards": [
        {
          "currency": {
            "name": "Honors Points",
            "code": "EHP"
          },
          "balance": {
            "amount": 142500,
            "expires_at": "2027-12-31T23:59:59Z"
          }
        }
      ],
      "credits": [
        {
          "id": "cred_fna_2026",
          "name": "Free Night Award",
          "type": "certificate",
          "remaining_amount": 1,
          "total_amount": 1,
          "expires_at": "2026-12-31T23:59:59Z",
          "description": "Valid for one standard room night at Category 1-7 properties."
        }
      ]
    }
  }
}
```

## Messages and Error Handling

A Business **MAY** include a `messages` array of errors, warnings, or
informational notes on the identity response. Transport-level authentication
failures (such as a missing, expired, or revoked Bearer token, or a token
lacking the required scope) follow the normative challenge rules in
[Identity Linking — Error Handling](../identity-linking/index.md#error-handling).

### Message (Error)

{{ schema_fields('types/message_error', 'common/identity') }}

### Message (Warning)

{{ schema_fields('types/message_warning', 'common/identity') }}

### Message (Info)

{{ schema_fields('types/message_info', 'common/identity') }}

## Security Considerations

* **Token-Derived Subject:** A Business **MUST** derive the user identity
  strictly from the validated user identity token (`Authorization: Bearer` over
  REST) and **MUST NOT** return data belonging to any other user.
* **Data Minimization:** A Business **SHOULD** return only the profile fields
  and extension data needed for the negotiated capabilities and authorized
  scopes. Raw credentials or unmasked sensitive identifiers (such as full
  loyalty account numbers when a PIN is not enforced) **MUST NOT** be exposed.
* **Opaque Identifiers:** A Platform **MUST** treat `id` and any extension
  identifiers as opaque, business-scoped strings.

## Scopes

The Identity capability defines the following well-known scope for
user-authenticated access:

| Scope | Description |
| :--- | :--- |
| `dev.ucp.common.identity:read` | Read the authenticated Buyer's identity profile and negotiated identity extensions. |

Scope declaration, derivation, and rules for extending this set with custom
scopes are defined in
[Identity Linking — Scopes](../identity-linking/index.md#scopes).

## Transport Bindings

The capability is bound to specific transport protocols:

* [REST Binding](rest.md): RESTful API mapping (`GET /identity`).
* [MCP Binding](mcp.md): Model Context Protocol mapping via JSON-RPC (`get_identity` tool).
