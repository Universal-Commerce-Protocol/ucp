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

# Incentives - REST Binding

This document specifies the HTTP/REST binding for the
[Incentives List capability](index.md#listing-incentives).

## Protocol Fundamentals

### Discovery

Businesses advertise REST transport availability for the Common service and
the Incentives List capability through their UCP profile at
`/.well-known/ucp`.

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
      "dev.ucp.common.incentives.list": [{
        "version": "{{ ucp_version }}",
        "spec": "https://ucp.dev/{{ ucp_version }}/specification/common/incentives",
        "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/incentives_list.json"
      }]
    },
    "payment_handlers": {}
  }
}
```

## Endpoints

| Endpoint | Method | Capability | Description |
| :--- | :--- | :--- | :--- |
| `/incentives/list` | POST | [Incentives List](index.md#listing-incentives) | List the incentives the Business is offering. |

### `POST /incentives/list`

Maps to the [Incentives List](index.md#listing-incentives) capability.

{{ method_fields('list_incentives', 'common/rest.openapi.json', 'common/incentives/rest') }}

#### Example

=== "Request"

    <!-- ucp:example schema=common/incentives_list def=list_request op=list direction=request -->
    ```json
    POST /incentives/list HTTP/1.1
    Host: business.example.com
    Content-Type: application/json
    Request-Id: 8ef9b0c2-78d1-4e4b-91c2-3e2ef0d3ab9f
    UCP-Agent: profile="https://platform.example/profiles/v2026-01/agent.json"

    {
      "context": {
        "address_country": "US",
        "currency": "USD"
      }
    }
    ```

=== "Response"

    <!-- ucp:example schema=common/incentives_list def=list_response op=list direction=response -->
    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.common.incentives.list": [
            {"version": "{{ ucp_version }}"}
          ]
        }
      },
      "incentives": [
        {
          "id": "inc_fs50",
          "title": "Free standard shipping over $50",
          "application": "automatic",
          "benefit": { "type": "free_shipping" },
          "conditions": {
            "minimum_order_amount": { "amount": 5000, "currency": "USD" }
          }
        },
        {
          "id": "inc_candles",
          "title": "Buy 2 candles, get 1 free",
          "application": "automatic",
          "benefit": { "type": "free_item", "quantity": 1 },
          "conditions": { "minimum_quantity": 2 },
          "active_period": { "end_time": "2026-12-01T23:59:59Z" }
        },
        {
          "id": "inc_welcome",
          "title": "$10 off your first order with code WELCOME10",
          "application": "code",
          "code": "WELCOME10",
          "benefit": {
            "type": "amount_off",
            "amount": { "amount": 1000, "currency": "USD" }
          },
          "url": "https://business.example.com/offers/welcome"
        }
      ],
      "pagination": { "has_next_page": false }
    }
    ```
