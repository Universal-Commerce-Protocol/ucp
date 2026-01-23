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

# Loyalty Extension

* **Capability Name:** `dev.ucp.shopping.loyalty`
* **Version:** `2026-01-11`
* **Extends:** `dev.ucp.shopping.checkout`

## Overview

The Loyalty extension lets platforms link a shopper's membership and apply
eligible benefits during checkout. It pairs with Identity Linking for account
connection and uses standard checkout updates to apply benefits or redeem
points.

## Discovery

Businesses advertise loyalty support in their discovery profile:

```json
{
  "name": "dev.ucp.shopping.loyalty",
  "version": "2026-01-11",
  "spec": "https://ucp.dev/specification/loyalty",
  "schema": "https://ucp.dev/schemas/shopping/loyalty.json",
  "extends": "dev.ucp.shopping.checkout"
}
```

## Account Linking Flow

1.  The platform links the user's account using the Identity Linking capability.
2.  The business returns a loyalty `member_id` or indicates linking is required.

See [Identity Linking Capability](identity-linking.md) for OAuth requirements.

## Benefit Application Flow

1.  Platform submits `loyalty` details in a checkout update.
2.  Business applies benefits and returns `benefits_applied` with updated totals.

### Example checkout update

```json
{
  "id": "chk_123",
  "loyalty": {
    "program_id": "loyalty_prime",
    "member_id": "member_456",
    "redemption": { "points": 1200 }
  }
}
```

### Example checkout response

```json
{
  "id": "chk_123",
  "loyalty": {
    "program_id": "loyalty_prime",
    "member_id": "member_456",
    "status": "linked",
    "tier": "gold",
    "points_balance": 4200,
    "benefits_applied": [
      {
        "type": "points_redemption",
        "amount": 1200,
        "description": "Redeemed 1,200 points"
      }
    ]
  }
}
```

## Schema

{{ extension_schema_fields('loyalty.json#/$defs/loyalty_object', 'checkout') }}
