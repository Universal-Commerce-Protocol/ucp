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

# Post-Order Management Extension

* **Capability Name:** `dev.ucp.shopping.post_order`
* **Version:** `2026-01-11`
* **Extends:** `dev.ucp.shopping.order`

## Overview

The Post-Order Management extension standardizes how businesses report returns,
exchanges, and refunds after a checkout completes. These events supplement the
base `adjustments` and fulfillment logs with explicit, structured post-order
signals.

## Return Flow

1.  Platform initiates a return with the business (outside the core UCP flow).
2.  Business appends a return event to the order response.

## Exchange Flow

1.  Platform requests an exchange with desired replacements.
2.  Business appends an exchange event to the order response.

## Refund Flow

1.  Business issues a refund after return approval or cancellation.
2.  Business appends a refund event to the order response.

## Example Order Response

```json
{
  "id": "order_123",
  "post_order": {
    "returns": [
      {
        "id": "ret_1",
        "status": "approved",
        "occurred_at": "2026-01-11T14:30:00Z",
        "line_items": [{ "id": "li_1", "quantity": 1 }],
        "reason_code": "defective",
        "description": "Defective item"
      }
    ],
    "refunds": [
      {
        "id": "ref_1",
        "status": "completed",
        "occurred_at": "2026-01-12T10:15:00Z",
        "amount": 26550,
        "line_items": [{ "id": "li_1", "quantity": 1 }],
        "reason_code": "return_completed",
        "description": "Refund after return"
      }
    ]
  }
}
```

## Schema

{{ extension_schema_fields('post_order.json#/$defs/post_order_object', 'order') }}
