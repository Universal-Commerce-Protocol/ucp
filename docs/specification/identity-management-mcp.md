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

# Identity Management Capability - MCP Binding

This document specifies the Model Context Protocol (MCP) binding for the [Identity Management Capability](identity-management.md).

## Protocol Fundamentals

### Discovery

Businesses advertise MCP transport availability through their UCP profile at `/.well-known/ucp`.

```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": {
      "dev.ucp.common": {
        "version": "{{ ucp_version }}",
        "mcp": {
          "endpoint": "https://business.example.com/ucp/common/mcp"
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

### Request Metadata

MCP clients **MUST** include a `meta` object in every request containing protocol metadata (e.g., `ucp-agent`).

## Tools

UCP Capabilities map 1:1 to MCP Tools.

### Identifier Pattern

Following the pattern in `cart-mcp.md`, operations on existing resources (`get`, `update`, `delete`) separate the resource identification from payload data:

* **Requests:** A top-level `id` parameter identifies the target resource. The `identity` object in the request payload **MUST NOT** contain an `id` field.
* **Responses:** All responses include `identity.id` as part of the full resource state.

| Tool | Operation | Description |
| :---- | :---- | :---- |
| `link_identity` | [Link Identity](identity-management.md#link-identity) | Link identity via token exchange. |
| `create_identity` | [Create Identity](identity-management.md#create-identity) | Create a new identity profile. |
| `get_identity` | [Get Identity](identity-management.md#get-identity) | Get identity profile details. |
| `update_identity` | [Update Identity](identity-management.md#update-identity) | Update identity profile details. |
| `delete_identity` | [Delete Identity](identity-management.md#delete-identity) | Delete or deactivate an identity. |
| `list_identities` | [List Identities](identity-management.md#list-identities) | List or search identities. |

### `link_identity`

#### Example

=== "Request"

    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "method": "tools/call",
      "params": {
        "name": "link_identity",
        "arguments": {
          "meta": {
            "ucp-agent": {
              "profile": "https://platform.example/profiles/shopping-agent.json"
            }
          },
          "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
          "subject_token": "platform_jwt_token_here",
          "subject_token_type": "urn:ietf:params:oauth:token-type:jwt"
        }
      }
    }
    ```

=== "Response"

    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "result": {
        "structuredContent": {
          "access_token": "business_access_token_here",
          "token_type": "Bearer",
          "expires_in": 3600,
          "identity": {
            "id": "ident_12345",
            "status": "active"
          }
        }
      }
    }
    ```

### `create_identity`

#### Example

=== "Request"

    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "method": "tools/call",
      "params": {
        "name": "create_identity",
        "arguments": {
          "meta": {
            "ucp-agent": {
              "profile": "https://platform.example/profiles/shopping-agent.json"
            }
          },
          "identity": {
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe"
          }
        }
      }
    }
    ```

=== "Response"

    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "result": {
        "structuredContent": {
          "identity": {
            "id": "ident_12345",
            "email": "user@example.com",
            "email_verified": false,
            "first_name": "John",
            "last_name": "Doe",
            "status": "pending",
            "created_at": "2026-04-05T12:00:00Z"
          }
        }
      }
    }
    ```

### `get_identity`

#### Example

=== "Request"

    ```json
    {
      "jsonrpc": "2.0",
      "id": 2,
      "method": "tools/call",
      "params": {
        "name": "get_identity",
        "arguments": {
          "meta": {
            "ucp-agent": {
              "profile": "https://platform.example/profiles/shopping-agent.json"
            }
          },
          "id": "ident_12345"
        }
      }
    }
    ```

=== "Response"

    ```json
    {
      "jsonrpc": "2.0",
      "id": 2,
      "result": {
        "structuredContent": {
          "identity": {
            "id": "ident_12345",
            "email": "user@example.com",
            "email_verified": true,
            "first_name": "John",
            "last_name": "Doe",
            "status": "active",
            "created_at": "2026-04-05T12:00:00Z",
            "updated_at": "2026-04-05T12:30:00Z"
          }
        }
      }
    }
    ```

### `update_identity`

#### Example

=== "Request"

    ```json
    {
      "jsonrpc": "2.0",
      "id": 3,
      "method": "tools/call",
      "params": {
        "name": "update_identity",
        "arguments": {
          "meta": {
            "ucp-agent": {
              "profile": "https://platform.example/profiles/shopping-agent.json"
            }
          },
          "id": "ident_12345",
          "identity": {
            "first_name": "Johnny"
          }
        }
      }
    }
    ```

=== "Response"

    ```json
    {
      "jsonrpc": "2.0",
      "id": 3,
      "result": {
        "structuredContent": {
          "identity": {
            "id": "ident_12345",
            "email": "user@example.com",
            "email_verified": true,
            "first_name": "Johnny",
            "last_name": "Doe",
            "status": "active",
            "created_at": "2026-04-05T12:00:00Z",
            "updated_at": "2026-04-05T13:00:00Z"
          }
        }
      }
    }
    ```

### `delete_identity`

#### Example

=== "Request"

    ```json
    {
      "jsonrpc": "2.0",
      "id": 4,
      "method": "tools/call",
      "params": {
        "name": "delete_identity",
        "arguments": {
          "meta": {
            "ucp-agent": {
              "profile": "https://platform.example/profiles/shopping-agent.json"
            }
          },
          "id": "ident_12345"
        }
      }
    }
    ```

=== "Response"

    ```json
    {
      "jsonrpc": "2.0",
      "id": 4,
      "result": {
        "structuredContent": {
          "status": "deleted"
        }
      }
    }
    ```

### `list_identities`

#### Example

=== "Request"

    ```json
    {
      "jsonrpc": "2.0",
      "id": 5,
      "method": "tools/call",
      "params": {
        "name": "list_identities",
        "arguments": {
          "meta": {
            "ucp-agent": {
              "profile": "https://platform.example/profiles/shopping-agent.json"
            }
          },
          "email": "user@example.com"
        }
      }
    }
    ```

=== "Response"

    ```json
    {
      "jsonrpc": "2.0",
      "id": 5,
      "result": {
        "structuredContent": {
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
      }
    }
    ```

## Error Handling

Follows standard UCP error handling for MCP (Protocol errors vs Business outcomes).
