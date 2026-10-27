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

# Identity - MCP Binding

This document specifies the Model Context Protocol (MCP) binding for the
[Identity Capability](index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise MCP transport availability for the Common service and
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
          "transport": "mcp",
          "schema": "https://ucp.dev/{{ ucp_version }}/services/common/mcp.openrpc.json",
          "endpoint": "https://business.example.com/ucp/mcp"
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

### Request Metadata

A Platform using MCP **MUST** include a `meta` object with
`meta["ucp-agent"].profile` in every request. The field identifies the
Platform's UCP profile for version compatibility checks and capability
negotiation:

<!-- ucp:example schema=transports/mcp_tool_call def=request direction=request -->
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "get_identity",
    "arguments": {
      "meta": {
        "ucp-agent": {
          "profile": "https://platform.example/profiles/v2026-01/agent.json"
        }
      }
    }
  }
}
```

## Tools

| Tool | Capability | Description |
| :--- | :--- | :--- |
| `get_identity` | [Identity](index.md) | Get the authenticated Buyer's identity profile and negotiated identity extensions. |

### `get_identity`

Maps to the [Identity](index.md) capability.

#### Input Schema

* `meta` (Object, required): Request metadata with `ucp-agent.profile`.

#### Output Schema

{{ schema_fields('identity_resp', 'common/identity/mcp') }}

#### Example

=== "Request"

    <!-- ucp:example schema=transports/mcp_tool_call def=request direction=request -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "method": "tools/call",
      "params": {
        "name": "get_identity",
        "arguments": {
          "meta": {
            "ucp-agent": {
              "profile": "https://platform.example/profiles/v2026-01/agent.json"
            }
          }
        }
      }
    }
    ```

=== "Response"

    <!-- ucp:example schema=common/identity op=read direction=response extract=$.result.structuredContent -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "result": {
        "structuredContent": {
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
      }
    }
    ```

=== "Not Authorized"

    <!-- ucp:example schema=common/types/error_response op=read direction=response extract=$.result.structuredContent -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "result": {
        "structuredContent": {
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
      }
    }
    ```

## Entities

### UCP Response Identity {: #ucp-response-identity-schema }

{{ extension_schema_fields('ucp.json#/$defs/response_identity_schema', 'common/identity/mcp') }}

### Error Response {: #error-response }

{{ schema_fields('types/error_response', 'common/identity/mcp') }}

## Conformance

A conforming MCP transport implementation **MUST**:

1. Implement JSON-RPC 2.0.
2. When `dev.ucp.common.identity` is advertised in the Business's UCP profile,
   expose the `get_identity` tool at the `dev.ucp.common` service's MCP
   `endpoint`.
3. Require user authentication and return an `identity_required` or
   `insufficient_scope` error when the caller is not authorized.
4. Return a successful JSON-RPC result with `structuredContent` conforming to
   the [Identity schema](index.md) (and any negotiated extensions) for
   authorized requests.
