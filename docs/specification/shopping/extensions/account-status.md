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

# Account Status Extension

## Overview

[Identity Linking](../../common/identity-linking/index.md) lets a Business say
that sign-in would help (`identity_optional`), that sign-in is needed
(`identity_required`) or that a scope is missing (`insufficient_scope`). This
extension lets a Business say that the buyer is signed in, but the Business
does not apply that account's terms yet.

It defines two info codes and one [Action type](../../overview/index.md#actions):

| Name | Kind | Meaning |
| :--- | :--- | :--- |
| `account_pending` | Info code | The Business has not applied this account's terms yet. |
| `account_ineligible` | Info code | The Business does not apply account terms to this account. |
| `dev.ucp.shopping.account_status.step` | Action type | A hosted step the buyer still has to finish before account terms apply. |

The codes and the Action describe the signed-in account. They never describe a
product.

The extension is named:

```text
dev.ucp.shopping.account_status
```

It extends `dev.ucp.shopping.catalog.search` and
`dev.ucp.shopping.catalog.lookup`.

**Dependencies:**

- Catalog Search, Catalog Lookup, or both
- Identity Linking (see [Activation](#activation))

## Discovery and Negotiation

Businesses advertise account status support in their profile:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.account_status": [
        {
          "version": "{{ ucp_version }}",
          "extends": [
            "dev.ucp.shopping.catalog.search",
            "dev.ucp.shopping.catalog.lookup"
          ],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/extensions/account-status",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/account_status.json"
        }
      ]
    }
  }
}
```

A Business adopts this extension when it applies terms per account. Examples
are negotiated prices behind an approval or behind an agreement.

### Activation

UCP has no way for one extension to require another. So the Business treats
this extension as inactive unless `dev.ucp.common.identity_linking` is also in
the negotiated intersection.

### Account

Here "account" is what the Business applies terms to for this token. It is the
signed-in user, or a buying organization the Business links that user to. This
extension does not define which buying organization applies when one token maps
to several.

## Account Status Codes

On a capability where this extension is active, when a request carries a valid
user identity token, the Business **MUST** include exactly one of these `info`
codes on every successful response while that state holds, whatever the
response contains:

| Code | Meaning |
| :--- | :--- |
| `account_pending` | The Business has not applied this account's terms yet. |
| `account_ineligible` | The Business does not apply account terms to this account. This holds until the Business changes its decision. It is not permanent. |

"Every successful response" includes a response with no products.

On a request with a valid token, a response with no account code means the
account's terms apply. So the Business **MUST NOT** fail open. If it cannot
tell the account's state, it sends `account_pending` or an error.

If the Business rejects the token, it **MUST** answer `401` with
[`identity_required`](../../common/identity-linking/index.md#identity_required),
as for a gated operation.

A Business **SHOULD NOT** send `identity_optional` for the same reason as one
of these codes.

## Step Action

When the buyer must finish a hosted step before account terms apply, such as
accepting an agreement, the Business **MUST** include an Action of type
`dev.ucp.shopping.account_status.step` with `config.url` set to that step. The
`account_pending` message's `path` **MUST** point to it.

When several steps are outstanding, the Business includes all of them, as for
every Action, in the order the buyer should finish them. `path` points to the
first. A step that can only start after another is done is not outstanding yet.

The step is for the person, so the Platform hands `config.url` to the buyer.

`config.url` **MUST** be an absolute `https` URL with no userinfo. A Platform
**MUST NOT** hand the buyer a step URL that breaks this rule.

The effect this Action gates is the account's terms. `config.url` **MUST NOT**
differ by product. The Business **MUST NOT** use it to carry an OAuth
authorization request. This is the same rule as for
[`continue_url`](../../common/identity-linking/index.md#identity_required).

A step can also come after approval, for example a renewed agreement. The
account is then pending again until the step is done.

After the buyer finishes the step, the Platform repeats the request. As for
every Catalog Action, the later Business response is authoritative (see
[Catalog Actions](../catalog/index.md#actions)). While the step stays
outstanding, the account stays pending.

### Step Config

{{ extension_schema_fields('account_status.json#/$defs/step_config', 'shopping/extensions/account-status') }}

## `continue_url` or Step

A Business uses `continue_url` on the `401` when the step must happen before it
issues a token. It uses the `step` Action when the buyer already holds a valid
token.

## Privacy

While an account is pending or ineligible, the Business **MUST** show each
variant as it would without this account's terms. That covers every
per-product field and message. Buyer-asserted `context.eligibility` benefits
still apply.

The codes, their `content` and the Action **MUST NOT** differ by product. So
they tell the token holder about its own account, and nothing about which
products carry account prices.

## Platform Behavior

What a Platform does in each state, with the extension active:

| State | Signal | Platform |
| :--- | :--- | :--- |
| Waiting on the buyer | `account_pending` with a `step` Action | Hand the step to the buyer, then repeat the request |
| Waiting on the business | `account_pending`, no Action | Explain the wait and repeat later. This version gives no retry time |
| Not eligible | `account_ineligible` | Don't restart sign-in for this account. The decision can change later |
| Approved | No account code | The terms shown are the account's terms |

## Examples

### Waiting on the buyer

A signed-in buyer searches before accepting the business's trade terms. The
response carries the step and a message that points to it:

<!-- ucp:example schema=shopping/account_status def=search_response op=search -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.catalog.search": [{ "version": "{{ ucp_version }}" }],
      "dev.ucp.common.identity_linking": [{ "version": "{{ ucp_version }}" }],
      "dev.ucp.shopping.account_status": [{ "version": "{{ ucp_version }}" }]
    }
  },
  "products": [ ... ],
  "actions": {
    "dev.ucp.shopping.account_status.step": [
      {
        "id": "trade-terms",
        "config": { "url": "https://business.example.com/account/trade-terms" }
      }
    ]
  },
  "messages": [
    {
      "type": "info",
      "code": "account_pending",
      "content": "Accept the trade terms to finish setting up this account. Account prices appear after the business approves it.",
      "path": "$.actions['dev.ucp.shopping.account_status.step'][0]"
    }
  ]
}
```

### Waiting on the business

The buyer has accepted. The same search returns `account_pending` with no
Action and no `path`:

<!-- ucp:example schema=shopping/account_status def=search_response op=search -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.catalog.search": [{ "version": "{{ ucp_version }}" }],
      "dev.ucp.common.identity_linking": [{ "version": "{{ ucp_version }}" }],
      "dev.ucp.shopping.account_status": [{ "version": "{{ ucp_version }}" }]
    }
  },
  "products": [ ... ],
  "messages": [
    {
      "type": "info",
      "code": "account_pending",
      "content": "The business is reviewing this account. Account prices appear once it is approved."
    }
  ]
}
```

### Not eligible

The business has declined the account. The code is on every response,
including a lookup that finds no products:

<!-- ucp:example schema=shopping/account_status def=lookup_response op=lookup -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.catalog.lookup": [{ "version": "{{ ucp_version }}" }],
      "dev.ucp.common.identity_linking": [{ "version": "{{ ucp_version }}" }],
      "dev.ucp.shopping.account_status": [{ "version": "{{ ucp_version }}" }]
    }
  },
  "products": [],
  "messages": [
    {
      "type": "info",
      "code": "account_ineligible",
      "content": "This account is not eligible for account pricing. Public terms apply."
    },
    {
      "type": "info",
      "code": "not_found",
      "content": "prod_unknown"
    }
  ]
}
```

### Approved

The business has approved the account. The response carries no account code,
so the prices shown are the account's prices:

<!-- ucp:example schema=shopping/account_status def=search_response op=search -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.catalog.search": [{ "version": "{{ ucp_version }}" }],
      "dev.ucp.common.identity_linking": [{ "version": "{{ ucp_version }}" }],
      "dev.ucp.shopping.account_status": [{ "version": "{{ ucp_version }}" }]
    }
  },
  "products": [ ... ]
}
```

## Scope

This version covers Catalog only. It does not extend Cart or Checkout. A
pending buyer can still check out at the terms shown, and nothing warns them.
