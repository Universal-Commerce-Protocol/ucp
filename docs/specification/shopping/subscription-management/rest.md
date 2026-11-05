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

# Subscription Management Capability - REST Binding

This document specifies the REST binding for the
[Subscription Management Capability](index.md).

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
      "dev.ucp.shopping.subscription_management": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/subscription-management",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/subscription_management.json"
        }
      ]
    },
    "payment_handlers": {}
  }
}
```

### Base URL

All UCP REST endpoints are relative to the business's base URL, which is
discovered through the UCP profile at `/.well-known/ucp`. The endpoint for the
subscription capability is defined in the `rest.endpoint` field of the
business profile.

### Content Types

* **Request**: `application/json`
* **Response**: `application/json`

All request and response bodies **MUST** be valid JSON as specified in
[RFC 8259](https://tools.ietf.org/html/rfc8259){ target="_blank" }.

### Transport Security

All REST endpoints **MUST** be served over HTTPS with minimum TLS version 1.3.

## Operations

| Operation | Method | Endpoint | Description |
| :-- | :-- | :-- | :-- |
| [List Subscriptions](#list-subscriptions) | `GET` | `/subscriptions` | List the buyer's subscriptions. |
| [Get Subscription](#get-subscription) | `GET` | `/subscriptions/{id}` | Get the current state of a subscription. |
| [Pause Subscription](#pause-subscription) | `POST` | `/subscriptions/{id}/pause` | Stop placing recurring orders until resumed. |
| [Resume Subscription](#resume-subscription) | `POST` | `/subscriptions/{id}/resume` | Start placing recurring orders again. |
| [Skip Subscription Order](#skip-subscription-order) | `POST` | `/subscriptions/{id}/skip` | Do not place one upcoming order. |
| [Unskip Subscription Order](#unskip-subscription-order) | `POST` | `/subscriptions/{id}/unskip` | Reverse a skip. |
| [Cancel Subscription](#cancel-subscription) | `POST` | `/subscriptions/{id}/cancel` | End the subscription. |

### List Subscriptions

#### Input Schema

Query parameters, all optional:

* `status` (String, repeatable): return only subscriptions in one of these
  statuses, e.g. `?status=active&status=paused`.
* `order_id` (String): return only subscriptions whose `origin.order_id` is
  this Order.
* `cursor` (String): the `pagination.cursor` of a previous response.
* `limit` (Integer): requested page size.

#### Output Schema

{{ extension_schema_fields('subscription_management.json#/$defs/list_response', 'shopping/subscription-management') }}

#### Example

=== "Request"

    ```http
    GET /subscriptions?order_id=order_abc123 HTTP/1.1
    UCP-Agent: profile="https://platform.example/.well-known/ucp"
    Authorization: Bearer eyJhbGciOiJSUzI1NiJ9...
    Accept: application/json
    ```

=== "Response"

    <!-- ucp:example schema=shopping/subscription_management op=list -->
    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.shopping.subscription_management": [{"version": "{{ ucp_version }}"}]
        }
      },
      "subscriptions": [
        {
          "id": "sub_8f2k1",
          "label": "House Blend, every month",
          "status": "active",
          "revision": "r_41",
          "permalink_url": "https://business.example.com/account/subscriptions/sub_8f2k1",
          "currency": "USD",
          "origin": { "order_id": "order_abc123", "line_item_ids": ["li_1"] },
          "line_items": [
            {
              "id": "sli_1",
              "item": {
                "id": "gid://example/Variant/coffee-340g",
                "title": "House Blend 340g",
                "price": 850
              },
              "quantity": 2,
              "purchase_option": {
                "id": "po_monthly",
                "title": "Subscribe & save 15%",
                "price": { "amount": 850, "currency": "USD" },
                "schedules": [
                  {
                    "description": {
                      "plain": "$17.00 plus applicable tax and shipping every month from December 2, 2026, until you cancel."
                    },
                    "totals": [
                      { "type": "subtotal", "amount": 1700 },
                      { "type": "total", "amount": 1700 }
                    ],
                    "interval": "P1M",
                    "starts_at": "2026-12-02T00:00:00Z"
                  }
                ]
              }
            }
          ],
          "upcoming_orders": [
            {
              "id": "uo_2026_12",
              "status": "scheduled",
              "expected_at": "2026-12-02T00:00:00Z",
              "operations": {
                "skip_subscription_order": { "available": true }
              }
            }
          ],
          "operations": {
            "pause_subscription": { "available": true },
            "cancel_subscription": { "available": true },
            "update_payment": {
              "available": false,
              "continue_url": "https://business.example.com/account/subscriptions/sub_8f2k1/payment"
            }
          }
        }
      ],
      "pagination": { "has_next_page": false },
      "policies": [
        {
          "type": "dev.ucp.shopping.policy.subscription",
          "description": {
            "plain": "Renews every month until you cancel. You can cancel any time. Manage it in your account."
          },
          "applies_to": ["$.subscriptions[0].line_items[0]"]
        }
      ]
    }
    ```

### Get Subscription

#### Input Schema

* `id` (String, required): the subscription ID (path parameter).

#### Output Schema

{{ extension_schema_fields('subscription_management.json#/$defs/subscription_response', 'shopping/subscription-management') }}

#### Example

=== "Request"

    ```http
    GET /subscriptions/sub_8f2k1 HTTP/1.1
    UCP-Agent: profile="https://platform.example/.well-known/ucp"
    Authorization: Bearer eyJhbGciOiJSUzI1NiJ9...
    Accept: application/json
    ```

=== "Response"

    See [An active subscription](index.md#an-active-subscription) for a
    complete response.

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
          "dev.ucp.shopping.subscription_management": [{"version": "{{ ucp_version }}"}]
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

### Pause Subscription

#### Input Schema

* `id` (String, required): the subscription ID (path parameter).
* Body:

{{ extension_schema_fields('subscription_management.json#/$defs/precondition', 'shopping/subscription-management') }}

#### Output Schema

The [Subscription Response](index.md#subscription-response), with `status`
`paused`.

#### Example

=== "Request"

    <!-- ucp:example schema=shopping/subscription_management op=pause direction=request -->
    ```json
    POST /subscriptions/sub_8f2k1/pause HTTP/1.1
    UCP-Agent: profile="https://platform.example/.well-known/ucp"
    Authorization: Bearer eyJhbGciOiJSUzI1NiJ9...
    Idempotency-Key: 0b9a4c1e-5d6f-4a7b-8c9d-0e1f2a3b4c5d
    Content-Type: application/json

    {
      "revision": "r_41"
    }
    ```

=== "Unavailable"

    <!-- ucp:example schema=common/types/error_response op=read -->
    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "error",
        "capabilities": {
          "dev.ucp.shopping.subscription_management": [{"version": "{{ ucp_version }}"}]
        }
      },
      "messages": [
        {
          "type": "error",
          "code": "operation_unavailable",
          "severity": "unrecoverable",
          "content": "Pausing is available after your third order, on January 2, 2027."
        }
      ]
    }
    ```

### Resume Subscription

#### Input Schema

* `id` (String, required): the subscription ID (path parameter).
* Body:

{{ extension_schema_fields('subscription_management.json#/$defs/precondition', 'shopping/subscription-management') }}

#### Output Schema

The [Subscription Response](index.md#subscription-response), with `status`
`active` and the next recurring order in `upcoming_orders`.

### Skip Subscription Order

#### Input Schema

* `id` (String, required): the subscription ID (path parameter).
* Body:

{{ extension_schema_fields('subscription_management.json#/$defs/upcoming_order_precondition', 'shopping/subscription-management') }}

#### Output Schema

The [Subscription Response](index.md#subscription-response), with the named
upcoming order's `status` `skipped`. See
[Skipping the next order](index.md#skipping-the-next-order).

#### Example

=== "Request"

    <!-- ucp:example schema=shopping/subscription_management op=skip direction=request -->
    ```json
    POST /subscriptions/sub_8f2k1/skip HTTP/1.1
    UCP-Agent: profile="https://platform.example/.well-known/ucp"
    Authorization: Bearer eyJhbGciOiJSUzI1NiJ9...
    Idempotency-Key: 6f1d2e3c-4b5a-4c6d-9e7f-8a9b0c1d2e3f
    Content-Type: application/json

    {
      "revision": "r_41",
      "upcoming_order_id": "uo_2026_12"
    }
    ```

### Unskip Subscription Order

#### Input Schema

* `id` (String, required): the subscription ID (path parameter).
* Body:

{{ extension_schema_fields('subscription_management.json#/$defs/upcoming_order_precondition', 'shopping/subscription-management') }}

#### Output Schema

The [Subscription Response](index.md#subscription-response), with the named
upcoming order's `status` `scheduled`.

### Cancel Subscription

#### Input Schema

* `id` (String, required): the subscription ID (path parameter).
* Body:

{{ extension_schema_fields('subscription_management.json#/$defs/cancel_request', 'shopping/subscription-management') }}

#### Output Schema

The [Subscription Response](index.md#subscription-response), with `status`
`canceled`. See
[Cancelling under a minimum commitment](index.md#cancelling-under-a-minimum-commitment).

#### Example

=== "Request"

    <!-- ucp:example schema=shopping/subscription_management op=cancel direction=request -->
    ```json
    POST /subscriptions/sub_8f2k1/cancel HTTP/1.1
    UCP-Agent: profile="https://platform.example/.well-known/ucp"
    Authorization: Bearer eyJhbGciOiJSUzI1NiJ9...
    Idempotency-Key: 3c2b1a0f-9e8d-4c7b-a6f5-e4d3c2b1a0f9
    Content-Type: application/json

    {
      "revision": "r_41",
      "reason": "Too much coffee"
    }
    ```

=== "Stale Revision"

    <!-- ucp:example schema=common/types/error_response op=read -->
    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "error",
        "capabilities": {
          "dev.ucp.shopping.subscription_management": [{"version": "{{ ucp_version }}"}]
        }
      },
      "messages": [
        {
          "type": "error",
          "code": "revision_mismatch",
          "severity": "recoverable",
          "content": "This subscription changed since it was last read. Get it again and confirm with the buyer."
        }
      ]
    }
    ```

## Events

The Business delivers [subscription events](index.md#events) by `POST` to the
`webhook.url` the Platform declared in its profile.

The request body is a [Subscription Event](index.md#subscription-event),
with the headers below.

| Header | Description |
| :-- | :-- |
| `Webhook-Id` | Event identifier; the same across retries. |
| `Webhook-Timestamp` | Unix time of the delivery. |
| `UCP-Agent` | The Business profile URL, identifying the signer. |
| `Content-Digest`, `Signature-Input`, `Signature` | RFC 9421 signature over the request, covering `webhook-id`, `webhook-timestamp`, and `ucp-agent`. |

### Example

```http
POST /webhooks/ucp/subscriptions HTTP/1.1
Host: platform.example.com
Content-Type: application/json
UCP-Agent: profile="https://business.example.com/.well-known/ucp"
Webhook-Timestamp: 1796202012
Webhook-Id: 018f8c2a-7b3e-7c1d-9a2b-4e5f6a7b8c9d
Content-Digest: sha-256=:X48E9q...:
Signature-Input: sig1=("@method" "@authority" "@path" "ucp-agent" "content-digest" "content-type" "webhook-id" "webhook-timestamp");keyid="business-2026"
Signature: sig1=:6G4i8TS6oUkGrx8KnCFUpsSPwd74...:

{"type":"dev.ucp.shopping.subscription_management:updated","data":{"subscription_id":"sub_8f2k1",...},...}
```

The Platform answers `200` with its `ucp` metadata, then reads the subscription
with [Get Subscription](#get-subscription).

## HTTP Headers

{{ header_fields('cancel_subscription', 'shopping/rest.openapi.json') }}

### Specific Header Requirements

{{ header_requirements('ucp_agent', 'idempotency_key') }}

`Idempotency-Key` is required on Pause, Resume, Skip, Unskip, and Cancel, and
not sent on List or Get.

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
* **MUST** include `Idempotency-Key` on every operation that changes a
  subscription
* **MUST** check the `messages` array in responses before accessing
  subscription data

Businesses implementing the REST binding:

* **MUST** serve all endpoints over HTTPS with TLS 1.3+
* **SHOULD** sign responses per the
  [Message Signatures](../../signatures.md) specification

See [Subscription Management Capability - Responsibilities](index.md#responsibilities) for
capability-level requirements that apply across all transports.
