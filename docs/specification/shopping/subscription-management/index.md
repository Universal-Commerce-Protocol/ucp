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

# Subscription Management Capability

* **Capability Name:** `dev.ucp.shopping.subscription_management`

## Overview

A subscription is the arrangement under which a Business places recurring
orders on a buyer's behalf. The
[Purchase Options extension](../extensions/purchase-options.md) covers how a
buyer agrees to one: a checkout line selects a purchase option with
`schedules`, a subscription policy and its disclosure state the terms, and the
Order keeps what was agreed. What happens after that (pausing, skipping an
order, cancelling) belongs to the subscription, which that extension leaves to
a separate capability. This is that capability.

It lets a Platform:

* list the subscriptions a buyer has, and find the ones an Order started;
* read one: what each recurring order contains, on what terms, and when the
  next ones are placed;
* pause and resume it, skip and unskip an upcoming order, and cancel it;
* be told when it changes, wherever the change was made.

It does not create subscriptions: a buyer subscribes by completing a checkout.
It does not change what is bought, how much, how often, where it is delivered,
or how it is paid. Those changes stay on the Business's site: payment through
the [`update_payment`](#handing-off-a-payment-update) handoff, the rest at the
subscription's `permalink_url` (see [Out of scope](#out-of-scope)).

### Key Concepts

**Subscription**: a Business-defined grouping of one or more recurring line
items that are placed, paused, and canceled together. How lines group into
subscriptions is the Business's own choice; one checkout can start several.

**Line items**: what each recurring order contains, and the purchase option it
recurs on, as currently in effect.

**Upcoming orders**: the recurring orders the Business plans to place, each
with an `id` a Platform uses to skip it.

**Operations**: what the Business accepts on the subscription, or on one of its
upcoming orders, right now. Business rules such as skip limits, minimum
commitments, or which system manages a subscription are expressed as data, not
as protocol.

**Revision**: an opaque token naming the state the buyer saw. Every change a
Platform requests carries it, so a change applies only to that state.

**Events**: one thin `updated` event telling a subscribed Platform that a
subscription changed, so it does not have to poll.

**Dependencies:**

* [Identity Linking](../../common/identity-linking/index.md): every operation
  acts for an identified buyer (see [Authorization](#authorization)).
* The `purchase_option` and `subscription_schedule` types and the
  `dev.ucp.shopping.policy.subscription` policy type defined by the
  [Purchase Options extension](../extensions/purchase-options.md).

## Discovery

A Business advertises the capability in its profile, and declares the
subscription scopes in its identity linking configuration:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.subscription_management": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/subscription-management",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/subscription_management.json",
          "config": {
            "webhook": {
              "events": ["dev.ucp.shopping.subscription_management:updated"]
            }
          }
        }
      ],
      "dev.ucp.common.identity_linking": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/common/identity-linking/",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/identity_linking.json",
          "config": {
            "providers": {
              "com.example.idp": [
                { "type": "oauth2", "auth_url": "https://accounts.example.com/" }
              ]
            },
            "scopes": {
              "dev.ucp.shopping.subscription_management:read": {},
              "dev.ucp.shopping.subscription_management:manage": {}
            }
          }
        }
      ]
    }
  }
}
```

The capability is a root capability: it extends no other capability and is
negotiated on its own. A Business that advertises it **MUST** implement every
operation it defines, **MUST** declare both scopes in `config.scopes`, and
expresses which operations apply to a given subscription through
[`operations`](#operations-on-a-subscription).

## Schema

### Subscription

{{ schema_fields('types/subscription', 'shopping/subscription-management') }}

### Subscription Line Item

{{ schema_fields('types/subscription_line_item', 'shopping/subscription-management') }}

### Upcoming Order

{{ schema_fields('types/upcoming_order', 'shopping/subscription-management') }}

### Subscription Operation

{{ schema_fields('types/subscription_operation', 'shopping/subscription-management') }}

### Subscription Response

Returned by Get Subscription and by every operation that changes a
subscription.

{{ extension_schema_fields('subscription_management.json#/$defs/subscription_response', 'shopping/subscription-management') }}

### List Request

{{ extension_schema_fields('subscription_management.json#/$defs/list_request', 'shopping/subscription-management') }}

### List Response

{{ extension_schema_fields('subscription_management.json#/$defs/list_response', 'shopping/subscription-management') }}

### Subscription Event

{{ extension_schema_fields('subscription_management.json#/$defs/event', 'shopping/subscription-management') }}

### Subscription Event Data

{{ extension_schema_fields('subscription_management.json#/$defs/event_data', 'shopping/subscription-management') }}

### Platform Config

{{ extension_schema_fields('subscription_management.json#/$defs/platform_schema', 'shopping/subscription-management') }}

{{ extension_schema_fields('subscription_management.json#/$defs/platform_webhook', 'shopping/subscription-management') }}

### Business Config

{{ extension_schema_fields('subscription_management.json#/$defs/business_schema', 'shopping/subscription-management') }}

{{ extension_schema_fields('subscription_management.json#/$defs/business_webhook', 'shopping/subscription-management') }}

## Status

`status` is an open vocabulary. The well-known values are:

| Status | Meaning |
| :-- | :-- |
| `active` | The Business is placing recurring orders. |
| `paused` | The Business places no recurring orders until the subscription is resumed. |
| `canceled` | The buyer or the Business canceled it. Orders its terms still require remain in `upcoming_orders`; no others are placed. |
| `ended` | It reached the end of its last schedule. |

A Platform **MUST NOT** infer from `status` which operations are possible; it
reads [`operations`](#operations-on-a-subscription), which the Business sets
for every status, including ones the Platform does not recognize.

## Terms

Each line carries the `purchase_option` it recurs on: the same object the Order
line records, kept current. Its `title` and `description` name the plan, its
`price` is the unit price of the next recurring order (and the line's
`item.price`), and its `schedules` state the recurring orders still to come,
starting with the run in effect now. They have the meaning they have on a
selected purchase option at checkout: each `description` is a complete
buyer-facing statement, `totals` carry exactly one `total` and follow the
line's `quantity`, and the Business owns the calendar. Unlike the Order line's
snapshot, a subscription line reflects every change since checkout, and its
`id` need not resolve in the catalog.

The Business **MUST** include in `policies[]` a
`dev.ucp.shopping.policy.subscription` policy covering every line, stating the
terms in effect: until when the orders continue, how the buyer cancels and any
minimum commitment or notice period, and where they manage the subscription.
Its `applies_to` targets are relative to the response root, for example
`$.subscription.line_items[0]`.

A buyer has already agreed to the terms, so a subscription response does not
repeat the disclosure that accompanied the policy at checkout. When the terms
in effect differ from those the buyer last agreed to, for example a price
change the Business has notified, the Business **MUST** emit a `messages[]`
warning with `presentation: "disclosure"`, `code` set to
`dev.ucp.shopping.policy.subscription`, and `path` naming the affected line,
stating the change and when it takes effect.

## Upcoming orders

`upcoming_orders` lists the recurring orders the Business plans to place, in
the order it plans to place them:

* While the subscription is `active`, it **MUST** include at least the next
  order the Business will place, and **MAY** include later ones. A Business
  that accepts skipping an order further ahead **SHOULD** list every order up
  to that point.
* An order that has been skipped stays listed, with `status: "skipped"`, until
  its `expected_at` has passed.
* While the subscription is `paused`, it lists no order with
  `status: "scheduled"`.
* Once the subscription is `canceled`, it lists only the orders the Business's
  terms still require, such as those owed under a minimum commitment.

An upcoming order is an order, not a delivery. Billing cadence does not imply
delivery cadence: where one recurring order pays for several deliveries, as a
prepaid subscription does, that order is one entry, and skipping it skips
everything it would have paid for. An upcoming order's `id` is stable while
the order is planned; it is not the ID of the Order the Business places, and a
Platform **MUST NOT** use it as one.

`totals`, where present, state what the order is expected to cost, with the
same rule as a schedule's `totals`: before taxes, fulfillment, and fees unless
the Business can state them. `expected_at` is when the Business expects to
place the order; it is indicative, not a guarantee.

## Operations on a subscription

`operations` on the subscription, and on each upcoming order, is keyed by
operation name. The well-known keys are the operations of this capability:

| Where | Keys |
| :-- | :-- |
| `subscription.operations` | `pause_subscription`, `resume_subscription`, `cancel_subscription`, and the handoff-only `update_payment` |
| `upcoming_orders[].operations` | `skip_subscription_order`, `unskip_subscription_order` |

Each entry says whether the Business accepts the operation now:

| Entry | Meaning |
| :-- | :-- |
| `available: true` | The Business accepts the operation now from a caller authorized to perform it. |
| `available: false` | The operation applies, but the Business does not accept it through this capability now. A message says why; `continue_url`, when present, is where the buyer can do it on the Business's site. |
| Absent | The operation does not apply in the current state, such as `resume_subscription` on an active subscription. |

This is how business rules travel without changes to the protocol. A skip
limit is a `skip_subscription_order` entry with `available: false` once the
limit is reached. A subscription that only the Business's site can change is
one whose entries carry `available: false` and a `continue_url`.

`available` reflects the subscription's state and the Business's rules, not
the scopes the caller holds. A Platform that lacks a scope for an available
operation requests it and receives `identity_required` or
`insufficient_scope`, which drive
[incremental authorization](../../common/identity-linking/index.md#insufficient_scope).

When an entry other than `update_payment` has `available: false`, the
Business **MUST** include a `messages[]` entry whose `path` names it (for
example `$.subscription.operations.pause_subscription`) and whose `content`
tells the buyer why, such as "Pausing is available after your third order."

### Handing off a payment update

`update_payment` is not an operation of this capability. Collecting and storing
a payment credential belongs to payment handlers, so this entry only tells a
Platform where to send the buyer. A Business that lets buyers change the
payment method of a subscription on its site **SHOULD** include it, always with
`available: false` and a `continue_url` to the page where the buyer does so for
this subscription. A Business that needs the buyer to act on a payment, such as
after a failed charge, **SHOULD** say so in a `messages[]` warning whose `path`
names this entry.

Operations are what a Platform may request. They are not
[Actions](../../overview/index.md#actions): an Action is outstanding work that
gates an effect, and this capability does not adopt them.

### Disclosure before an operation

Where performing an operation has a consequence for the buyer that the
subscription policy does not already state for this subscription in its
current state, the Business **MUST** state it before the operation is
requested: a `messages[]` warning with `presentation: "disclosure"`, `code`
set to `dev.ucp.shopping.policy.subscription`, and `path` naming the operation
entry. Examples are a commitment not yet met and the orders still owed if the
buyer cancels, a price that changes on resume, or a skip that uses the last
one allowed this year.

A Platform **MUST** present such a disclosure to the buyer under the
[`disclosure` rendering contract](../checkout/index.md#warning-presentation)
before requesting the operation, and requests it with the `revision` of the
response that carried it. Requesting the operation under these obligations is
the buyer's agreement to it, on the same trust model as completing a checkout.
A Business that requires affirmative acknowledgment beyond display **MAY**
reject the request with an error of `severity: "requires_buyer_review"` and a
`continue_url`, which the Platform **MUST** honor by handing the buyer off.

### Cancellation

Cancelling **MUST** be possible whenever the subscription is not already
`canceled` or `ended`:

* The Business **MUST** include `cancel_subscription` in `operations` on every
  such subscription. Where it cannot process cancellation through this
  capability, the entry carries `available: false` and **MUST** carry a
  `continue_url` where the buyer can cancel without further obstacles.
* The Business **MUST NOT** gate `cancel_subscription` behind a custom scope,
  or a per-scope policy such as `min_acr`, that is stricter than the one
  governing the other operations of `dev.ucp.shopping.subscription_management:manage`.
* The Business **MUST NOT** make a successful cancellation depend on the buyer
  accepting an offer, giving a `reason`, or taking any step beyond the request.
  It **MAY** include informational messages in the response.

## Revision

`revision` is an opaque token. The Business **MUST** change it whenever the
subscription changes, and whenever a policy, disclosure, or message that
targets the subscription changes. Every operation that changes a subscription
carries the `revision` the buyer saw.

The Business applies the operation only if `revision` is still current. If it
is not, the Business **MUST** reject the request with an error of
`code: "revision_mismatch"` and `severity: "recoverable"`, and **MUST NOT**
apply it. The Platform reads the subscription again, presents any disclosure
that changed, and asks the buyer again where what they agreed to no longer
holds.

A retried request with the same idempotency key returns the original outcome
rather than `revision_mismatch`.

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

Every operation returns the full subscription as it stands afterwards, or an
error response. For transport-specific details, see the
[REST Binding](rest.md) and the [MCP Binding](mcp.md).

Every operation that changes a subscription requires an idempotency key
(`Idempotency-Key` on REST, `meta["idempotency-key"]` on MCP) and the
subscription's current `revision`. An operation whose entry is absent or has
`available: false` is rejected with `code: "operation_unavailable"`, without
effect.

### List Subscriptions

Returns the authenticated buyer's subscriptions (see
[Authorization](#authorization)), most recently started first, as full
subscription entities. `filters.status` returns only subscriptions in one of
the given statuses; `filters.order_id` returns only those whose
`origin.order_id` is that Order, which is how a Platform finds the
subscriptions a checkout started. Pagination follows the common
[pagination](../../reference.md#pagination-request) contract.

### Get Subscription

Returns the current state of one subscription. A Platform **SHOULD** get the
subscription immediately before requesting a change, so that the buyer sees
current operations, disclosures, and `revision`.

### Pause Subscription

Pauses an `active` subscription indefinitely: `status` becomes `paused` and the
Business places no recurring orders until it is resumed. An order the Business
has already begun to place is not affected.

### Resume Subscription

Returns a `paused` subscription to `active`. A Business **MAY** also offer it
on a `canceled` subscription, to reactivate it. The Business decides when the
next recurring order is placed and lists it in `upcoming_orders`; where that
differs from what the buyer would expect, such as a changed price, it states it
in a disclosure on `resume_subscription` first.

### Skip Subscription Order

Skips the upcoming order named by `upcoming_order_id`: its `status` becomes
`skipped` and the Business does not place it. The Business decides whether
later orders keep their dates, and the response states the result.

### Unskip Subscription Order

Reverses a skip before the order's `expected_at`: its `status` becomes
`scheduled` and the Business places it as planned.

### Cancel Subscription

Cancels the subscription: `status` becomes `canceled`. The Business places no
further recurring orders except those its terms still require, which remain in
`upcoming_orders`. The request **MAY** carry the buyer's `reason`, in their own
words. See [Cancellation](#cancellation) for what the Business guarantees.

### Authorization

A subscription is the buyer's own, cross-channel data: it may have started on
the Business's site, in another Platform, or in a conversation with this one.
Every operation therefore acts for an identified buyer. The Platform obtains
buyer authorization through
[Identity Linking](../../common/identity-linking/index.md) with the scopes
below, and the Business returns only subscriptions that buyer owns. Platform
credentials alone grant no access: the Business **MUST** answer a request
without a valid user identity token with `identity_required`.

### Scopes

| Scope | Operations |
| :-- | :-- |
| `dev.ucp.shopping.subscription_management:read` | List Subscriptions, Get Subscription |
| `dev.ucp.shopping.subscription_management:manage` | Pause, Resume, Skip, Unskip, and Cancel |

Scope declaration, derivation, and custom scopes follow
[Identity Linking scopes](../../common/identity-linking/index.md#scopes),
subject to the limit on cancellation in [Cancellation](#cancellation).

### Errors

| Code | Severity | When |
| :-- | :-- | :-- |
| `not_found` | `unrecoverable` | The subscription, or the upcoming order named by `upcoming_order_id`, does not exist or is not accessible to the caller. |
| `unauthorized` | `unrecoverable` | The caller is not authenticated for the operation. |
| `identity_required` | `requires_buyer_review` | See [Identity Linking](../../common/identity-linking/index.md#identity_required). |
| `insufficient_scope` | `requires_buyer_review` | See [Identity Linking](../../common/identity-linking/index.md#insufficient_scope). |
| `revision_mismatch` | `recoverable` | The `revision` sent is no longer current. See [Revision](#revision). |
| `operation_unavailable` | `unrecoverable` | The operation's entry is absent or has `available: false`. |

Errors are returned in an error response, with a `continue_url` where the
buyer can complete the operation on the Business's site.

## Events

A subscription changes outside any conversation with the Platform: the buyer
cancels on the Business's site or through another Platform, the merchant
changes a price, a payment fails, or the Business places a recurring order.
This capability defines one event, so a Platform does not have to poll to
notice.

| Event | Sent when |
| :-- | :-- |
| `dev.ucp.shopping.subscription_management:updated` | The subscription's `revision` changed. |

### Subscribing

A Business that sends events lists them in `config.webhook.events` of its
capability entry (see [Discovery](#discovery)). A Platform that wants them adds
`config.webhook`, with a `url` and optionally `events`, to its capability entry
in its platform profile. The events delivered are those both list; a Platform
that omits `events` gets every event the Business sends. A Business without
`config.webhook` sends none, and Platforms poll with Get Subscription instead.

This is the shape the capability-wide event mechanism proposed in #938 takes;
when one is adopted, these events move onto it without change.

<!-- ucp:example schema=profile def=platform_schema target=$.ucp.capabilities -->
```json
{
  "dev.ucp.shopping.subscription_management": [
    {
      "version": "{{ ucp_version }}",
      "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/subscription-management",
      "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/subscription_management.json",
      "config": {
        "webhook": {
          "url": "https://platform.example.com/webhooks/ucp/subscriptions"
        }
      }
    }
  ]
}
```

### Who receives them

Events follow the buyer's authorization, not the checkout that started the
subscription. The Business **MUST** send an event about a subscription only to
a Platform that subscribed as above and holds a current grant from that
subscription's buyer that includes `dev.ucp.shopping.subscription_management:read`.
It stops when that grant is revoked or expires, when the Platform removes
`config.webhook`, or when deliveries keep failing.

### What they carry

An event is thin: the subscription's `id`, its new `revision`, hints in
`changed`, and an `order_id` when the change is a recurring order being
placed. It carries no other subscription data. The Platform reads current
state with Get Subscription and the buyer's token, so the content goes through
the same authorization as any other read. Because the read is authoritative,
an event that arrives twice, late, or out of order is harmless.

The Business **MUST** send `updated` after every committed change that changes
`revision`, whoever made it: the Platform itself, the buyer elsewhere, the
merchant, or the Business placing or failing to place a recurring order. It
**MAY** combine several changes into one event.

### Recurring orders

Each recurring order is an Order. When the Business places one, the `updated`
event carries its `order_id`, and from then on the order's fulfillment,
delivery, and refunds are the [Order capability](../order/index.md)'s concern,
read with Get Order under `dev.ucp.shopping.order:read`. Order events go to
the Platform that completed an order's checkout, and no Platform completes the
checkout of a recurring order, so this event is how a Platform learns of one.

What has not happened yet is not an Order, and only this capability covers it:
upcoming orders and their dates, skips, pauses, cancellation, price changes,
and a payment that failed before any order was placed.

### Delivery

Delivery follows the [Order Event Webhook](../order/index.md#order-event-webhook):
an HTTP `POST` to `webhook.url`, also for Platforms that use MCP, with
`Webhook-Id` and `Webhook-Timestamp` headers and an RFC 9421 signature from a
key in the Business profile's `keys`, covering `webhook-id`,
`webhook-timestamp`, and `ucp-agent`. The Platform acknowledges with a `2xx`
and processes it afterwards; the Business retries failures with the same
`Webhook-Id`. Before acting, the Platform **MUST** verify the signature and
that the signer is the Business the subscription belongs to.

The request body is a [Subscription Event](#subscription-event); the
Platform answers with its `ucp` metadata.

## Relationship to other capabilities

* **Checkout and Purchase Options.** A subscription starts when a checkout
  line whose selected purchase option carries `schedules` is completed. Its
  lines' `schedules` begin as those agreed at checkout, and its subscription
  policy begins as the one carried onto the Order.
* **Order.** `origin.order_id` and `origin.line_item_ids` link the
  subscription to the Order and lines that started it, and List Subscriptions
  filters on `order_id`. The Order line's `purchase_option` and policies remain
  the record of what was agreed; the subscription line's `purchase_option` is
  what is in effect now. The recurring orders the Business places are Orders in
  their own right.
* **Events.** One thin `updated` event, in the shape #938 proposes for every
  capability. Recurring orders, once placed, are covered by the Order
  capability (see [Recurring orders](#recurring-orders)).

## Out of scope

* **Creating a subscription.** Checkout, with the Purchase Options extension.
* **Changing what each order contains or how it is delivered or paid:** items,
  quantities, purchase option or frequency, delivery address or method, and
  payment instrument. The Business's site, at `permalink_url`, remains the
  place for these. Each can later be added as an operation of its own,
  discovered through `operations` the same way.
* **Changing when orders are placed** beyond skipping: rescheduling an order,
  pausing until a date, or placing the next order now.
* **Retention offers and cancellation reasons.** A later extension may add
  them; it cannot make cancellation depend on them.
* **Payment execution and recovery.** Credential storage, mandates, and
  off-session retries are payment-handler behavior; this capability only hands
  off through [`update_payment`](#handing-off-a-payment-update).
* **A link from the Order.** Naming the subscription on each Order line would
  take an Order extension. Until then, a Platform lists by `order_id`.

## Responsibilities

Businesses **MUST**:

* Return the full subscription, with `operations`, policies, and messages,
  from Get Subscription and from every operation that changes one.
* Set `operations` for the current state, include
  `cancel_subscription` on every subscription that is not `canceled` or
  `ended`, and explain every entry with `available: false` other than
  `update_payment` in a message.
* Require buyer authorization for every operation.
* Where it advertises events, send `updated` after every change to `revision`,
  only to Platforms holding the buyer's `:read` grant, signed and retried as
  the Order Event Webhook is.
* Reject any operation whose entry is absent or has `available: false` with
  `operation_unavailable`, and any whose `revision` is not current with
  `revision_mismatch`, without effect.
* Disclose, on the operation, every consequence of performing it that the
  subscription policy does not already state for this subscription.
* Change `revision` whenever the subscription, or anything that targets it,
  changes.
* Include a subscription policy covering every line, keep each line's
  `purchase_option` current, and disclose terms that differ from those the
  buyer last agreed to.

Platforms **MUST**:

* Treat `id`, `revision`, and every upcoming order `id` as opaque.
* Request only operations whose entry has `available: true`, and send the
  `revision` of the response the buyer saw.
* Present every disclosure whose `path` names an operation before requesting
  it, under the `disclosure` rendering contract.
* Hand the buyer off through `continue_url` or `permalink_url` for anything
  this capability does not expose or the Business does not accept, including
  a payment update.

* Verify every event's signature and signer, and read the subscription back
  rather than act on the event alone.

Platforms **SHOULD**:

* Get the subscription immediately before requesting a change.

## Examples

### An active subscription

A monthly coffee subscription with a three-order minimum, started on
November 2, 2026. Pausing is not available until the minimum is met,
cancelling now still places the two orders it requires, and the payment method
is changed on the Business's site. Fetched with
`GET /subscriptions/sub_8f2k1`:

<!-- ucp:example schema=shopping/subscription_management op=get -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.subscription_management": [{"version": "{{ ucp_version }}"}]
    }
  },
  "subscription": {
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
        "totals": [
          { "type": "subtotal", "amount": 1700 },
          { "type": "total", "amount": 1700 }
        ],
        "operations": {
          "skip_subscription_order": { "available": true }
        }
      },
      {
        "id": "uo_2027_01",
        "status": "scheduled",
        "expected_at": "2027-01-02T00:00:00Z",
        "operations": {
          "skip_subscription_order": { "available": true }
        }
      }
    ],
    "operations": {
      "pause_subscription": { "available": false },
      "cancel_subscription": { "available": true },
      "update_payment": {
        "available": false,
        "continue_url": "https://business.example.com/account/subscriptions/sub_8f2k1/payment"
      }
    }
  },
  "policies": [
    {
      "type": "dev.ucp.shopping.policy.subscription",
      "description": {
        "plain": "Renews every month until you cancel, with a minimum of 3 orders. You can cancel any time; orders owed under the minimum are still placed. Manage it in your account."
      },
      "applies_to": ["$.subscription.line_items[0]"],
      "url": "https://business.example.com/policies/subscriptions"
    }
  ],
  "messages": [
    {
      "type": "info",
      "code": "operation_unavailable",
      "path": "$.subscription.operations.pause_subscription",
      "content": "Pausing is available after your third order, on January 2, 2027."
    },
    {
      "type": "warning",
      "code": "dev.ucp.shopping.policy.subscription",
      "presentation": "disclosure",
      "path": "$.subscription.operations.cancel_subscription",
      "content": "You agreed to at least 3 orders. If you cancel now, your orders on December 2, 2026 and January 2, 2027 are still placed and charged at $17.00 plus tax and shipping each, and none after that."
    }
  ]
}
```

### Skipping the next order

The buyer skips the December order. The Platform sends the `revision` it
presented, with `POST /subscriptions/sub_8f2k1/skip`:

<!-- ucp:example schema=shopping/subscription_management op=skip direction=request -->
```json
{
  "revision": "r_41",
  "upcoming_order_id": "uo_2026_12"
}
```

The December order is skipped and can be unskipped; the January order keeps
its date:

<!-- ucp:example schema=shopping/subscription_management op=skip extract=$.subscription.upcoming_orders target=$.subscription.upcoming_orders -->
```json
{
  "subscription": {
    "upcoming_orders": [
      {
        "id": "uo_2026_12",
        "status": "skipped",
        "expected_at": "2026-12-02T00:00:00Z",
        "operations": {
          "unskip_subscription_order": { "available": true }
        }
      },
      {
        "id": "uo_2027_01",
        "status": "scheduled",
        "expected_at": "2027-01-02T00:00:00Z",
        "operations": {
          "skip_subscription_order": { "available": true }
        }
      }
    ]
  }
}
```

### Cancelling under a minimum commitment

After the buyer sees the disclosure on `cancel_subscription`, the Platform
requests it with `POST /subscriptions/sub_8f2k1/cancel`:

<!-- ucp:example schema=shopping/subscription_management op=cancel direction=request -->
```json
{
  "revision": "r_41",
  "reason": "Too much coffee"
}
```

The subscription is canceled. The two orders owed under the minimum remain
listed, and no operation applies to them:

<!-- ucp:example schema=shopping/subscription_management op=cancel -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.subscription_management": [{"version": "{{ ucp_version }}"}]
    }
  },
  "subscription": {
    "id": "sub_8f2k1",
    "label": "House Blend, every month",
    "status": "canceled",
    "revision": "r_42",
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
                "plain": "$17.00 plus applicable tax and shipping on December 2, 2026 and January 2, 2027, then no further orders."
              },
              "totals": [
                { "type": "subtotal", "amount": 1700 },
                { "type": "total", "amount": 1700 }
              ],
              "interval": "P1M",
              "starts_at": "2026-12-02T00:00:00Z",
              "ends_at": "2027-01-03T00:00:00Z"
            }
          ]
        }
      }
    ],
    "upcoming_orders": [
      {
        "id": "uo_2026_12",
        "status": "scheduled",
        "expected_at": "2026-12-02T00:00:00Z"
      },
      {
        "id": "uo_2027_01",
        "status": "scheduled",
        "expected_at": "2027-01-02T00:00:00Z"
      }
    ],
    "operations": {}
  },
  "policies": [
    {
      "type": "dev.ucp.shopping.policy.subscription",
      "description": {
        "plain": "Canceled. The 2 orders owed under the 3-order minimum are still placed."
      },
      "applies_to": ["$.subscription.line_items[0]"],
      "url": "https://business.example.com/policies/subscriptions"
    }
  ]
}
```

### Being told about a change

On December 2, 2026 the Business places the December order and sends the
Platform a thin event. The Platform reads the subscription to see the new
upcoming orders, and can read the new Order with Get Order:

<!-- ucp:example schema=shopping/subscription_management def=event -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.subscription_management": [{"version": "{{ ucp_version }}"}]
    }
  },
  "type": "dev.ucp.shopping.subscription_management:updated",
  "occurred_at": "2026-12-02T09:00:12Z",
  "data": {
    "subscription_id": "sub_8f2k1",
    "revision": "r_43",
    "changed": ["upcoming_orders"],
    "order_id": "order_def456"
  }
}
```

### The subscription changed in the meantime

A request carrying a stale `revision` is rejected without effect:

<!-- ucp:example schema=common/types/error_response op=read -->
```json
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

## Entities

### Item

{{ schema_fields('types/item_resp', 'shopping/subscription-management') }}

### Purchase Option

{{ schema_fields('types/purchase_option', 'shopping/subscription-management') }}

### Subscription Schedule

{{ schema_fields('types/subscription_schedule', 'shopping/subscription-management') }}

### Total

{{ schema_fields('types/total_resp', 'shopping/subscription-management') }}

### UCP Response Subscription Management Schema <span id="ucp"></span> {: #ucp-response-subscription-management-schema }

{{ extension_schema_fields('ucp.json#/$defs/response_subscription_management_schema', 'shopping/subscription-management') }}
