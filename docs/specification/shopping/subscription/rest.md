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

# Subscription Capability - REST Binding

This document specifies the REST binding for the
[Subscription Capability](index.md).

## Protocol Fundamentals

### Discovery

Businesses advertise REST transport availability through their UCP profile at
`/.well-known/ucp`.

<!-- ucp:example schema=profile def=business_schema -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": {
      "dev.ucp.shopping": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/overview",
          "transport": "rest",
          "schema": "https://ucp.dev/{{ ucp_version }}/services/shopping/rest.openapi.json",
          "endpoint": "https://business.example.com/ucp/v1"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.shopping.subscription": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/subscription",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/subscription.json"
        }
      ]
    },
    "payment_handlers": {}
  }
}
```

### Base URL

All UCP REST endpoints are relative to the Business's base URL, which is
discovered through the UCP profile at `/.well-known/ucp`. The endpoint for the
subscription capability is defined in the `rest.endpoint` field of the Business
profile.

### Content Types

* **Response**: `application/json`

All response bodies **MUST** be valid JSON as specified in
[RFC 8259](https://tools.ietf.org/html/rfc8259){ target="_blank" }.

### Transport Security

All REST endpoints **MUST** be served over HTTPS with minimum TLS version 1.3.

## Operations

| Operation | Method | Endpoint | Description |
| :---- | :---- | :---- | :---- |
| [Get Subscription](#get-subscription) | `GET` | `/subscriptions/{id}` | Get the current state of a subscription. |

### Get Subscription

Returns the current-state snapshot of a subscription.

#### Input Schema

* `id` (String, required): The subscription ID (path parameter).

#### Output Schema

{{ extension_schema_fields('subscription.json#/$defs/get_subscription_response', 'shopping/subscription') }}

#### Example

=== "Request"

    ```http
    GET /subscriptions/sub_8f2k1 HTTP/1.1
    UCP-Agent: profile="https://platform.example/.well-known/ucp"
    Accept: application/json
    Signature-Input: sig1=("@method" "@authority" "@path" "ucp-agent");created=1706800000;keyid="platform-2026"
    Signature: sig1=:6G4i8TS6oUkGrx8KnCFUpsSPwd74...:
    ```

=== "Response"

    <!-- ucp:example schema=shopping/subscription op=get_subscription -->
    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.shopping.subscription": [{"version": "{{ ucp_version }}"}]
        }
      },
      "subscription": {
        "id": "sub_8f2k1",
        "label": "House Blend, every month",
        "status": "active",
        "permalink_url": "https://business.example.com/account/subscriptions/sub_8f2k1",
        "currency": "USD",
        "origin": { "order_id": "ord_8f3e2a", "line_item_ids": ["li_1"] },
        "line_items": [ ... ],
        "orders": [
          { "id": "ord_9c41d7", "permalink_url": "https://business.example.com/orders/9c41d7" },
          { "id": "ord_8f3e2a", "permalink_url": "https://business.example.com/orders/8f3e2a" }
        ],
        "upcoming_orders": [
          { "expected_at": "2026-12-02T00:00:00Z" }
        ]
      },
      "policies": [ ... ]
    }
    ```

=== "Not Found"

    <!-- ucp:example schema=common/types/error_response op=read -->
    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "error",
        "capabilities": {
          "dev.ucp.shopping.subscription": [{"version": "{{ ucp_version }}"}]
        }
      },
      "messages": [
        {
          "type": "error",
          "code": "not_found",
          "severity": "unrecoverable",
          "content": "Subscription not found."
        }
      ]
    }
    ```

## HTTP Headers

{{ header_fields('get_subscription', 'shopping/rest.openapi.json') }}

### Specific Header Requirements

{{ header_requirements('ucp_agent') }}

## Message Signing

Request and response signatures follow the
[Message Signatures](../../signatures.md) specification using RFC 9421 HTTP Message
Signatures. See
[REST Request Signing](../../signatures.md#rest-request-signing) and
[REST Request Verification](../../signatures.md#rest-request-verification) for
the complete algorithm.

## Conformance

Platforms implementing the REST binding:

* **MUST** include `UCP-Agent` header with profile URL on all requests
* **MUST** check the `messages` array in responses before accessing
  subscription data
* **SHOULD** delegate to the Business via `permalink_url` for everything this
  capability does not expose - the Business site is where the buyer manages
  the subscription

Businesses implementing the REST binding:

* **MUST** serve all endpoints over HTTPS with TLS 1.3+
* **SHOULD** sign responses per the
  [Message Signatures](../../signatures.md) specification

See [Subscription Capability - Guidelines](index.md#operations-guidelines) for
capability-level requirements that apply across all transports.
