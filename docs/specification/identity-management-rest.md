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

# Identity Management Capability - REST Binding

This document specifies the REST binding for the [Identity Management Capability](identity-management.md).

## Protocol Fundamentals

### Discovery

Businesses advertise REST transport availability through their UCP profile at `/.well-known/ucp`.

```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": {
      "dev.ucp.common": {
        "version": "{{ ucp_version }}",
        "rest": {
          "endpoint": "https://business.example.com/ucp/common/v1"
        }
      }
    },
    "capabilities": [
      {
        "name": "dev.ucp.common.identity_management",
        "version": "{{ ucp_version }}",
        "spec": "https://ucp.dev/{{ ucp_version }}/specification/identity-management",
        "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/types/identity.json"
      }
    ]
  }
}
```

### Base URL

All UCP REST endpoints are relative to the business's base URL, discovered via the UCP profile.

### Content Types

* **Request**: `application/json`
* **Response**: `application/json`

### Transport Security

All REST endpoints **MUST** be served over HTTPS with minimum TLS version 1.3.

## Operations

| Operation | Method | Endpoint | Description |
| :---- | :---- | :---- | :---- |
| [Link Identity](#link-identity) | `POST` | `/identities/link` | Link identity via token exchange (Identity Chaining). |
| [Create Identity](#create-identity) | `POST` | `/identities` | Create a new identity profile. |
| [Get Identity](#get-identity) | `GET` | `/identities/{id}` | Get identity profile details. |
| [Update Identity](#update-identity) | `PUT` | `/identities/{id}` | Update identity profile details. |
| [Delete Identity](#delete-identity) | `DELETE` | `/identities/{id}` | Delete or deactivate an identity. |
| [List Identities](#list-identities) | `GET` | `/identities` | List or search identities. |

### Link Identity

#### Example

=== "Request"

    ```json
    POST /identities/link HTTP/1.1
    UCP-Agent: profile="https://platform.example/profile"
    Content-Type: application/json

    {
      "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
      "subject_token": "platform_jwt_token_here",
      "subject_token_type": "urn:ietf:params:oauth:token-type:jwt"
    }
    ```

=== "Response"

    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "access_token": "business_access_token_here",
      "token_type": "Bearer",
      "expires_in": 3600,
      "identity": {
        "id": "ident_12345",
        "status": "active"
      }
    }
    ```

### Create Identity

#### Example

=== "Request"

    ```json
    POST /identities HTTP/1.1
    UCP-Agent: profile="https://platform.example/profile"
    Content-Type: application/json
    Authorization: Bearer platform_token_here

    {
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe"
    }
    ```

=== "Response"

    ```json
    HTTP/1.1 201 Created
    Content-Type: application/json

    {
      "id": "ident_12345",
      "email": "user@example.com",
      "email_verified": false,
      "first_name": "John",
      "last_name": "Doe",
      "status": "pending",
      "created_at": "2026-04-05T12:00:00Z"
    }
    ```

### Get Identity

#### Example

=== "Request"

    ```json
    GET /identities/ident_12345 HTTP/1.1
    UCP-Agent: profile="https://platform.example/profile"
    Authorization: Bearer platform_token_here
    ```

=== "Response"

    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "id": "ident_12345",
      "email": "user@example.com",
      "email_verified": true,
      "first_name": "John",
      "last_name": "Doe",
      "status": "active",
      "created_at": "2026-04-05T12:00:00Z",
      "updated_at": "2026-04-05T12:30:00Z"
    }
    ```

### Update Identity

#### Example

=== "Request"

    ```json
    PUT /identities/ident_12345 HTTP/1.1
    UCP-Agent: profile="https://platform.example/profile"
    Content-Type: application/json
    Authorization: Bearer platform_token_here

    {
      "first_name": "Johnny"
    }
    ```

=== "Response"

    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "id": "ident_12345",
      "email": "user@example.com",
      "email_verified": true,
      "first_name": "Johnny",
      "last_name": "Doe",
      "status": "active",
      "created_at": "2026-04-05T12:00:00Z",
      "updated_at": "2026-04-05T13:00:00Z"
    }
    ```

### Delete Identity

#### Example

=== "Request"

    ```json
    DELETE /identities/ident_12345 HTTP/1.1
    UCP-Agent: profile="https://platform.example/profile"
    Authorization: Bearer platform_token_here
    ```

=== "Response"

    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "status": "deleted"
    }
    ```

### List Identities

#### Example

=== "Request"

    ```json
    GET /identities?email=user@example.com HTTP/1.1
    UCP-Agent: profile="https://platform.example/profile"
    Authorization: Bearer platform_token_here
    ```

=== "Response"

    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "count": 1,
      "results": [
        {
          "id": "ident_12345",
          "email": "user@example.com",
          "first_name": "John",
          "last_name": "Doe",
          "status": "active"
        }
      ],
      "pagination": {
        "next": null,
        "previous": null
      }
    }
    ```

## HTTP Headers

* **UCP-Agent**: Required on all requests.
* **Authorization**: Required (Bearer token) for Get, Update, Delete, List.
* **Idempotency-Key**: Should be supported for Create, Update, Delete.

## Status Codes

Follows standard UCP status codes (see Core Specification).

* `200 OK`: Successful request.
* `201 Created`: Successful creation.
* `401 Unauthorized`: Auth failed or missing.
* `404 Not Found`: Identity not found (returned as business outcome or protocol error depending on case, but typically 404 for missing resource in REST).
