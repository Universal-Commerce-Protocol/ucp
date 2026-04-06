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

# Identity Management Capability

* **Capability Name:** `dev.ucp.common.identity_management`
* **Replaces:** `dev.ucp.common.identity_linking`

## Overview

The Identity Management capability enables a **platform** to manage user identities on a **business**'s site. This evolved capability moves beyond simple identity linking to full lifecycle management: creating, retrieving, updating, deleting, and listing identities, as well as keeping them in sync via webhooks.

This capability replaces and **deprecates** `dev.ucp.common.identity_linking`. The linking functionality is now exposed as the `linkIdentity` operation within this capability.

This capability builds upon the foundations laid in PR #330 for Identity Linking, incorporating Delegated IdPs and Identity Chaining.

## Features & Operations

### 1. Identity Linking (`linkIdentity`) <a id="link-identity"></a>

The `linkIdentity` operation preserves and enhances the functionality of the deprecated `dev.ucp.common.identity_linking` capability, incorporating improvements from PR #330:

* **Standard Flow**: OAuth 2.0 Authorization Code flow.
* **Delegated IdP**: Platforms can authenticate users via trusted third-party Identity Providers declared in `config.providers`.
* **Accelerated Flow (Identity Chaining)**: Uses token exchange (RFC 8693) and JWT bearer assertion (RFC 7523) to chain identity from Platform to Business without browser redirects.

### 2. Identity Lifecycle Management (New)

Platforms can manage the lifecycle of an identity once established or linked.

* <a id="create-identity"></a>**Create Identity**: `POST /identities` - Programmatically create a new identity.
* <a id="get-identity"></a>**Get Identity**: `GET /identities/{id}` - Retrieve profile details.
* <a id="update-identity"></a>**Update Identity**: `PUT /identities/{id}` - Update profile details.
* <a id="delete-identity"></a>**Delete Identity**: `DELETE /identities/{id}` - Delete or deactivate an identity.
* <a id="list-identities"></a>**List Identities**: `GET /identities` - Search or list identities.

### 3. Identity Synchronization (Webhooks)

Bi-directional synchronization of identity updates.

* **Event**: `identity.updated`
* **Payload**: Full `Identity` schema.
* **Config**: Platform provides `webhook_url` in the capability config.

## Scopes

In alignment with the capability-driven scope model in PR #330, scopes follow the capability-prefixed format:

| Scope | Description |
| :--- | :--- |
| `dev.ucp.common.identity_management:read` | Read identity profile details and list identities. |
| `dev.ucp.common.identity_management:write` | Create, update, and delete identity details. |
| `dev.ucp.common.identity_management:sync` | Receive and send identity sync events. |

## Transport Bindings

Detailed transport bindings are specified in separate documents:

* [REST Binding](identity-management-rest.md)
* [MCP Binding](identity-management-mcp.md)

## Schemas

See [identity.json](site:schemas/common/types/identity.json) for the base user identity structure.
