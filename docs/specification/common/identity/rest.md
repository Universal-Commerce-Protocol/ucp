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

# Identity - REST Binding

This document specifies the HTTP/REST binding for the
[Identity Capability](index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise REST transport availability for the Common service and
the Identity capability through their UCP profile at `/.well-known/ucp`.

<!-- ucp:example schema=profile def=business_schema -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": {
      "dev.ucp.common": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/overview",
          "transport": "rest",
          "schema": "https://ucp.dev/{{ ucp_version }}/services/common/rest.openapi.json",
          "endpoint": "https://business.example.com/ucp"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.common.identity": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/common/identity",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/identity.json"
        }
      ],
      "dev.ucp.common.identity_linking": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/common/identity-linking",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/identity_linking.json",
          "config": {
            "scopes": {
              "dev.ucp.common.identity:read": {}
            }
          }
        }
      ]
    },
    "payment_handlers": {}
  }
}
```

## Endpoints

| Endpoint | Method | Capability | Description |
| :--- | :--- | :--- | :--- |
| `/identity` | GET | [Identity](index.md) | Get the authenticated Buyer's identity profile and negotiated identity extensions. |

### `GET /identity`

Maps to the [Identity](index.md) capability.

{{ method_fields('get_identity', 'common/rest.openapi.json', 'common/identity/rest') }}

#### Example

=== "Request"

    ```http
    GET /identity HTTP/1.1
    Host: business.example.com
    Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
    UCP-Agent: profile="https://platform.example/.well-known/ucp"
    Request-Id: 4f3e2d1c-0b9a-4876-9543-210fedcba987
    Accept: application/json
    ```

=== "Response"

    <!-- ucp:example schema=common/identity op=read -->
    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.common.identity": [
            { "version": "{{ ucp_version }}" }
          ]
        }
      },
      "id": "usr_9f8e7d6c",
      "email": "e.beckett@example.com",
      "email_verified": true,
      "first_name": "Elisa",
      "last_name": "Beckett",
      "links": [
        {
          "type": "privacy_policy",
          "url": "https://business.example.com/policies/privacy",
          "title": "Privacy Policy"
        }
      ]
    }
    ```

=== "Not Authorized"

    <!-- ucp:example schema=common/types/error_response op=read -->
    ```json
    HTTP/1.1 401 Unauthorized
    WWW-Authenticate: Bearer error="invalid_token", scope="dev.ucp.common.identity:read"
    Content-Type: application/json

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "error",
        "capabilities": {
          "dev.ucp.common.identity": [
            { "version": "{{ ucp_version }}" }
          ]
        }
      },
      "messages": [
        {
          "type": "error",
          "code": "identity_required",
          "severity": "recoverable",
          "content": "User authentication is required to access identity information."
        }
      ]
    }
    ```

## HTTP Headers

The following headers are defined for the HTTP binding.

{{ header_fields('get_identity', 'common/rest.openapi.json') }}

### Specific Header Requirements

{{ header_requirements('ucp_agent') }}

## Entities

### UCP Response Identity {: #ucp-response-identity-schema }

{{ extension_schema_fields('ucp.json#/$defs/response_identity_schema', 'common/identity/rest') }}

### Error Response {: #error-response }

{{ schema_fields('types/error_response', 'common/identity/rest') }}

## Conformance

A conforming REST transport implementation **MUST**:

1. When `dev.ucp.common.identity` is advertised in the Business's UCP profile,
   expose `GET /identity` under the `dev.ucp.common` service's REST `endpoint`.
2. Require a valid user identity token on `GET /identity` and emit a
   `WWW-Authenticate: Bearer` challenge on `401 Unauthorized` and
   `403 Forbidden` responses per
   [Identity Linking — Error Handling](../identity-linking/index.md#error-handling).
3. Return HTTP 200 with a payload conforming to the [Identity schema](index.md)
   (and any negotiated extensions) for authorized requests.
