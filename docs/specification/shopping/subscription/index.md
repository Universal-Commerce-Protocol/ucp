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

# Subscription Capability

* **Capability Name:** `dev.ucp.shopping.subscription`

## Overview

A subscription is an agreement between a buyer and a Business under which the
Business places recurring orders for the buyer. The
[Purchase Options extension](../extensions/purchase-options.md) lets a buyer
enter that agreement at checkout and records it on the Order line it was
bought on. This capability gives the agreement an identity of its own and lets
a Platform read its current state: what recurs and on which terms, the Order
that started it, the Orders placed under it, and the orders the Business plans
to place. A Platform reads one subscription by its `id`, or lists the
subscriptions it may access.

The capability is read-only. It defines no operation that creates or changes a
subscription; the buyer manages a subscription with the Business, at the
subscription's `permalink_url` (see [Out of scope](#out-of-scope)).

### Key Concepts

A subscription has three main components:

**Identity** — the agreement as the Business tracks it:

* An opaque `id` the Business assigns, a `status`, and a `permalink_url` to the
  page where the buyer manages it
* Which recurring line items form one subscription is the Business's choice;
  one checkout can start several

**Line Items** — what recurs, and on which terms:

* The item, its quantity, and a `purchase_option` whose `schedules` state the
  recurring orders
* The terms currently in effect, not those agreed to at checkout; the Order
  line keeps that record

**Orders** — what the agreement has produced, and what comes next:

* `origin` — the Order that started the subscription
* `orders` — the Orders that belong to it: the origin Order and each recurring
  Order placed since
* `upcoming_orders` — the recurring orders the Business plans to place; they
  are not Orders yet

## Data Model

### Identity and Grouping

The Business assigns a subscription's `id`. It is opaque to the Platform,
stable for the life of the subscription, and never reused for another
subscription.

A subscription holds the line items the Business places recurring orders for
together: they share its `status`, its Orders, and its `permalink_url`. How
recurring line items group into subscriptions is the Business's choice. One
checkout can start several subscriptions, and two line items bought together
can belong to different ones. The subscriptions state the grouping; it cannot
be inferred from the checkout or the Order.

A Business creates a subscription when it chooses to, which can be after the
Order that starts it exists. A completed checkout or an Order therefore carries
no subscription `id`; [List Subscriptions](#list-subscriptions) with
`filters.order_id` returns the subscriptions an Order started, once they
exist.

### Status

`status` is the current state of the subscription:

| Status | Meaning |
| :--- | :--- |
| `active` | The Business places recurring orders as scheduled. |
| `paused` | No recurring order is placed until the subscription resumes. |
| `canceled` | The buyer or the Business ended the subscription. No further recurring order is placed. |
| `ended` | The subscription ran to its stated end. No further recurring order is placed. |

The vocabulary is open: a Business **MAY** use other values, and a Platform
**MUST** tolerate values it does not recognize.

### Line Items

Each line item states what recurs: the `item`, the `quantity` placed in each
recurring order, and the `purchase_option` it recurs on. The line item reuses
the [Purchase Option](../extensions/purchase-options.md#purchase-option) type
with `schedules` required. Its `price` is the unit price recurring orders are
currently placed at, and equals the line's `item.price`. Its `schedules` state
the recurring orders for the line at its quantity, under the rules of
[Recurring orders](../extensions/purchase-options.md#recurring-orders): each
schedule's `description` is the complete statement, and the Business owns the
dates. Its `id` need not resolve through the catalog.

These are the terms **currently in effect**. When the Business changes them (a
new price, a different cadence) the next response states the new terms. The
Order line that started the subscription keeps its own `purchase_option` as
the record of what was agreed to at checkout (see
[Purchase Options — Order](../extensions/purchase-options.md#order)); the two
differ once the terms change.

A subscription line item's `id` identifies the line within the subscription.
It is not an Order line item `id`.

### Orders

Three fields relate a subscription to orders:

| Field | States |
| :--- | :--- |
| `origin` | The Order, and its line items, that started the subscription. |
| `orders` | The Orders that belong to the subscription. |
| `upcoming_orders` | The recurring orders the Business plans to place. They are not Orders yet. |

**Origin.** `origin.order_id` names the Order that started the subscription,
and `origin.line_item_ids` the Order line items it was started from, each of
which carries the `purchase_option` agreed to at checkout. `origin` is absent
when no Order started the subscription, or when the Business cannot identify
it.

**Orders.** A recurring order is an Order in its own right. `orders` lists the
Orders that belong to the subscription, most recent first: each recurring
Order the Business has placed under it and, when there is one, the Order that
started it. Each entry is a reference (the Order's `id` and `permalink_url`),
not the Order. Reading an Order is [Get Order](../order/index.md#get-order),
under the Order capability's own
[authorization](../order/index.md#authorization); an entry in `orders` grants
no access to the Order it names. A Business **MAY** list only the most recent
Orders. `orders` is absent or empty when no Order exists yet.

**Upcoming orders.** `upcoming_orders` lists the recurring orders the Business
plans to place, next one first. Each entry states when the Business expects to
place the order (`expected_at`) and, where the Business can state it, what the
order costs (`totals`) for all the subscription's line items together, under
the same rules as a schedule's
[`totals`](../extensions/purchase-options.md#totals). `expected_at` is
indicative: the Business determines actual order dates. An upcoming order has
no `id`; once the Business places it, it is an entry in `orders`.
`upcoming_orders` is absent or empty when no order is planned.

### Policies

A Business **SHOULD** include in `policies[]` the
[subscription policy](../extensions/purchase-options.md#subscription-policy)
(`dev.ucp.shopping.policy.subscription`) that governs the subscription's line
items. It states the terms the recurring orders are placed under as they stand
when the response is returned: until when the orders continue, how the buyer
cancels, and where the buyer manages the subscription. `applies_to` is
relative to the response root, for example `$.subscription`. The Order that
started the subscription keeps the policy as it stood at checkout. See
[Policies](../../overview/index.md#policies) for the rules every policy
follows.

### Messages

A Business uses `messages[]` to tell the buyer what the subscription entity
does not state, for example that a payment needs the buyer's attention. Such a
message says what the buyer needs to know and directs the buyer to
`permalink_url` to act on it. This capability defines no message codes.

## Schema

### Subscription

{{ schema_fields('types/subscription', 'shopping/subscription') }}

### Subscription Line Item

{{ schema_fields('types/subscription_line_item', 'shopping/subscription') }}

### Upcoming Order

{{ schema_fields('types/upcoming_order', 'shopping/subscription') }}

## Examples

### An active subscription

A monthly coffee subscription started by Order `ord_8f3e2a`. The Business has
placed one recurring Order since, plans the next two, and states the amount of
the next one.

<!-- ucp:example schema=shopping/subscription op=get_subscription -->
```json
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
    "line_items": [
      {
        "id": "sli_1",
        "item": { "id": "gid://example/Variant/coffee-340g", "title": "House Blend 340g", "price": 850 },
        "quantity": 2,
        "purchase_option": {
          "id": "po_monthly",
          "title": "Subscribe & save 15%",
          "price": { "amount": 850, "currency": "USD" },
          "schedules": [
            {
              "description": { "plain": "$17.00 plus applicable tax and shipping every month from November 2, 2026, until you cancel." },
              "totals": [
                { "type": "subtotal", "amount": 1700 },
                { "type": "total", "amount": 1700 }
              ],
              "interval": "P1M",
              "starts_at": "2026-11-02T00:00:00Z"
            }
          ]
        }
      }
    ],
    "orders": [
      { "id": "ord_9c41d7", "permalink_url": "https://business.example.com/orders/9c41d7" },
      { "id": "ord_8f3e2a", "permalink_url": "https://business.example.com/orders/8f3e2a" }
    ],
    "upcoming_orders": [
      {
        "expected_at": "2026-12-02T00:00:00Z",
        "totals": [
          { "type": "subtotal", "amount": 1700 },
          { "type": "total", "amount": 1700 }
        ]
      },
      { "expected_at": "2027-01-02T00:00:00Z" }
    ]
  },
  "policies": [
    {
      "type": "dev.ucp.shopping.policy.subscription",
      "description": { "plain": "Renews automatically until you cancel. Cancel anytime from your account at business.example.com/account; no notice period or minimum commitment." },
      "applies_to": ["$.subscription"],
      "url": "https://business.example.com/subscription-terms"
    }
  ]
}
```

### A subscription with no Order yet

A subscription the Business set up outside a checkout, whose first order has
not been placed. No Order started it, so `origin` is absent; no Order belongs
to it yet, so `orders` is absent; `upcoming_orders` states the first.

<!-- ucp:example schema=shopping/subscription op=get_subscription target=$.subscription -->
```json
{
  "id": "sub_2m7qx",
  "status": "active",
  "permalink_url": "https://business.example.com/account/subscriptions/sub_2m7qx",
  "currency": "USD",
  "line_items": [
    {
      "id": "sli_1",
      "item": { "id": "gid://example/Variant/tea-100g", "title": "Breakfast Tea 100g", "price": 600 },
      "quantity": 1,
      "purchase_option": {
        "id": "po_tea_monthly",
        "title": "Monthly",
        "price": { "amount": 600, "currency": "USD" },
        "schedules": [
          {
            "description": { "plain": "$6.00 plus applicable tax and shipping every month from December 1, 2026, until you cancel." },
            "totals": [
              { "type": "subtotal", "amount": 600 },
              { "type": "total", "amount": 600 }
            ],
            "starts_at": "2026-12-01T00:00:00Z"
          }
        ]
      }
    }
  ],
  "upcoming_orders": [
    { "expected_at": "2026-12-01T00:00:00Z" }
  ]
}
```

### A payment that needs attention

The payment for a recurring order did not go through. The Business says so in
`messages[]` and directs the buyer to the subscription's page; the `code` is
the Business's own.

<!-- ucp:example schema=shopping/subscription op=get_subscription target=$.messages -->
```json
[
  {
    "type": "warning",
    "code": "payment_needs_attention",
    "path": "$.subscription",
    "content": "We could not collect payment for your December 2 order. Update your payment method at business.example.com/account/subscriptions/sub_8f2k1 to keep your subscription active."
  }
]
```

### A buyer's subscriptions

With buyer authorization and no filter, the list holds the buyer's
subscriptions, whichever channel started them: here the coffee subscription
started by Order `ord_8f3e2a` and the tea subscription the Business set up
outside a checkout. One policy states the terms both share.

<!-- ucp:example schema=shopping/subscription op=list_subscriptions direction=request -->
```json
{
  "pagination": { "limit": 10 }
}
```

<!-- ucp:example schema=shopping/subscription op=list_subscriptions -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.subscription": [{"version": "{{ ucp_version }}"}]
    }
  },
  "subscriptions": [
    {
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
    {
      "id": "sub_2m7qx",
      "status": "active",
      "permalink_url": "https://business.example.com/account/subscriptions/sub_2m7qx",
      "currency": "USD",
      "line_items": [ ... ],
      "upcoming_orders": [
        { "expected_at": "2026-12-01T00:00:00Z" }
      ]
    }
  ],
  "pagination": { "has_next_page": false },
  "policies": [
    {
      "type": "dev.ucp.shopping.policy.subscription",
      "description": { "plain": "Renews automatically until you cancel. Cancel anytime from your account at business.example.com/account; no notice period or minimum commitment." },
      "applies_to": ["$.subscriptions[0]", "$.subscriptions[1]"],
      "url": "https://business.example.com/subscription-terms"
    }
  ]
}
```

### The subscriptions an Order belongs to

A Platform that completed a checkout asks which subscriptions the resulting
Order started. The same request naming `ord_9c41d7`, the recurring Order,
returns the same subscription to a caller with buyer authorization.

<!-- ucp:example schema=shopping/subscription op=list_subscriptions direction=request -->
```json
{
  "filters": { "order_id": "ord_8f3e2a" }
}
```

<!-- ucp:example schema=shopping/subscription op=list_subscriptions -->
```json
{
  "ucp": { ... },
  "subscriptions": [
    {
      "id": "sub_8f2k1",
      "label": "House Blend, every month",
      "status": "active",
      "permalink_url": "https://business.example.com/account/subscriptions/sub_8f2k1",
      "currency": "USD",
      "origin": { "order_id": "ord_8f3e2a", "line_item_ids": ["li_1"] },
      "line_items": [ ... ],
      "orders": [ ... ],
      "upcoming_orders": [ ... ]
    }
  ],
  "pagination": { "has_next_page": false }
}
```

### An Order with no subscription yet

The Order started no subscription, or the Business has not created it yet.
The list is empty and the response is not an error.

<!-- ucp:example schema=shopping/subscription op=list_subscriptions -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.subscription": [{"version": "{{ ucp_version }}"}]
    }
  },
  "subscriptions": [],
  "pagination": { "has_next_page": false }
}
```

## Scopes

The Subscription capability defines the following well-known scope for
user-authenticated access:

| Scope | Description |
| :--- | :--- |
| `dev.ucp.shopping.subscription:read` | Read access to the user's subscriptions — Get Subscription and List Subscriptions on resources owned by the authenticated user. |

Scope declaration, derivation, and rules for extending this set with
custom scopes are defined in [Identity Linking — Scopes](../../common/identity-linking/index.md#scopes).

## Operations

The subscription entity is a **current-state snapshot**: the authoritative
latest state of the subscription at the time of retrieval. Businesses **MUST**
return the full subscription entity on every response.

The `permalink_url` is the authoritative reference for everything this
capability does not expose: cancelling, pausing, changing what recurs or
when, and payment. The API provides programmatic access to current state for
conversational and operational use cases.

| Operation | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| [Get Subscription](#get-subscription) | `GET` | `/subscriptions/{id}` | Platform retrieves current subscription state. |
| [List Subscriptions](#list-subscriptions) | `POST` | `/subscriptions/list` | Platform lists the subscriptions it may access. |

For transport-specific details, see [REST Binding](rest.md) and
[MCP Binding](mcp.md).

### Get Subscription

Returns the current-state snapshot of a subscription, with the policies and
messages that apply to it.

{{ extension_schema_fields('subscription.json#/$defs/get_subscription_response', 'shopping/subscription') }}

#### Authorization

The Business **MUST** authenticate requests to subscription data before
returning a response, using any supported UCP mechanism - API keys, OAuth 2.0,
mutual TLS, or HTTP Message Signatures (see
[Identity and Authentication](../checkout/rest.md#authentication)). The
authentication method determines which subscriptions are accessible to the
caller:

| Authentication | Accessible Subscriptions |
| :------------- | :----------------------- |
| Platform credentials | Subscriptions started by an Order the Platform originated |
| Buyer authorization | Subscriptions owned by the buyer, subject to the granted OAuth scopes |

**Platform credentials** (API key, signatures, OAuth client credentials) -
Businesses **MAY** allow access to subscriptions whose `origin.order_id` names
an Order the Platform originated. The Platform completed the checkout in which
the buyer agreed to the recurring orders, and is retrieving the latest state
of an agreement it already has context for.

**Buyer authorization** - the Platform obtains buyer authorization via
[Identity Linking](../../common/identity-linking/index.md) with the necessary
scopes, or a similar mechanism. This grants access to the buyer's
subscriptions regardless of which Platform, if any, originated the Order that
started them.

Businesses **MAY** define additional access policies (e.g., trusted partner
agreements), enforce data availability constraints (e.g., retention
windows, regulatory erasure), and omit or redact optional fields from the
response based on context, business policy, or other requirements -
independently of authorization.

#### Error Responses

When the Business cannot return a subscription, the response returns an error
that includes a `messages` array describing the outcome:

**Subscription not found:**

<!-- ucp:example schema=common/types/error_response op=read -->
```json
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

**Not authorized:**

<!-- ucp:example schema=common/types/error_response op=read -->
```json
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
      "code": "unauthorized",
      "severity": "unrecoverable",
      "content": "Not authorized to access this subscription."
    }
  ]
}
```

### List Subscriptions

Returns the subscriptions the caller may access, each as the full
current-state snapshot [Get Subscription](#get-subscription) returns, with the
policies and messages that apply to them. `applies_to` and `path` are relative
to the response root, for example `$.subscriptions[0]`.

#### Request

{{ extension_schema_fields('subscription.json#/$defs/list_subscriptions_request', 'shopping/subscription') }}

#### Response

{{ extension_schema_fields('subscription.json#/$defs/list_subscriptions_response', 'shopping/subscription') }}

#### Subscription Filters

{{ schema_fields('types/subscription_filters', 'shopping/subscription') }}

`filters.order_id` narrows the list to the subscriptions an Order belongs to:
the ones it started (their `origin.order_id`) and the ones it was placed under
as a recurring Order (an entry in their `orders`).

An empty `subscriptions` array is a successful response. With
`filters.order_id` it means the Order belongs to no subscription the caller
may access, or to none yet: a Business can create a subscription after the
Order that starts it exists.

#### Pagination

Results use the shared cursor-based pagination (see
[Pagination](../catalog/search.md#pagination)): `pagination.limit` is a
requested page size, cursors are opaque, and a response whose
`pagination.has_next_page` is `true` carries the `cursor` for the next page.

#### Authorization {: #list-subscriptions-authorization }

The Business authenticates the request as for
[Get Subscription](#authorization). The authentication method determines
which subscriptions are listed:

| Authentication | Listed Subscriptions |
| :------------- | :------------------- |
| Platform credentials | Subscriptions started by the Order named in `filters.order_id`, when the Platform originated that Order |
| Buyer authorization | Subscriptions owned by the buyer, subject to the granted OAuth scopes |

**Platform credentials** - Businesses **MAY** answer a request without buyer
authorization only when its `filters.order_id` names an Order the Platform
originated; the list holds the subscriptions that Order started. Any other
request needs buyer authorization, and the Business responds with
`identity_required` as
[Identity Linking — Error Handling](../../common/identity-linking/index.md#identity_required)
defines.

**Buyer authorization** - with the `dev.ucp.shopping.subscription:read` scope,
the list holds the buyer's subscriptions regardless of which Platform, if any,
originated the Order that started them. `filters.order_id` narrows it to the
subscriptions that Order belongs to.

The additional access policies, data availability constraints, and redaction
described for [Get Subscription](#authorization) apply.

### Guidelines {: #operations-guidelines }

**Platform:**

* **MUST** include `UCP-Agent` header with profile URL on all requests
* **MUST** treat `id` as opaque and tolerate `status` values it does not
  recognize
* **SHOULD** direct the buyer to `permalink_url` for anything this capability
  does not expose
* **SHOULD** treat subscription data as ephemeral and discard it when no longer
  needed for active commerce flows

**Business:**

* **MUST** authenticate requests to subscription data before returning a
  response (see [Authorization](#authorization))

## Out of scope

* **Starting a subscription.** A buyer enters a subscription by completing a
  checkout with a purchase option that carries `schedules` (see
  [Purchase Options](../extensions/purchase-options.md)). This capability
  defines no operation that creates one.
* **Changing a subscription.** Cancelling, pausing, resuming, skipping an
  order, and changing what recurs, how often, or where it is delivered.
* **Events.** This capability defines no webhook or event; a Platform reads
  current state with Get Subscription.
* **Payment.** Which instrument pays the recurring orders, changing it, and
  recovery when a payment fails.
* **The Orders themselves.** A subscription names its Orders; reading them is
  the [Order capability](../order/index.md)'s.

Until a capability exposes them, the buyer changes a subscription and how it
is paid with the Business, at the subscription's `permalink_url`.

## Entities

### Item

{{ schema_fields('types/item_resp', 'shopping/subscription') }}

### Order Confirmation

{{ schema_fields('types/order_confirmation', 'shopping/subscription') }}
