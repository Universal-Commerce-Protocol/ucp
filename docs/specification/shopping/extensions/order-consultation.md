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

<!-- cSpell:ignore linearizable linearizably linearization idempotently -->
<!-- cSpell:ignore unwithdrawn -->
<!-- cSpell:ignore unbilled unrecoverable repricing repriced reprice -->
<!-- cSpell:ignore digestable tolerantly -->

# Order Consultation Extension

!!! warning "Working Draft: proposed namespace, not approved, not published"

    This page is a **Working Draft reference implementation** for Enhancement
    Proposal [#944](https://github.com/Universal-Commerce-Protocol/ucp/issues/944).
    It has no Technical Council approval and is not requested for merge before
    the proposal reaches Provisional.

    **Namespace.** `dev.ucp.shopping.order_consultation` is a **proposed**
    standardization target. It is **not approved** by the UCP governing body or
    the Technical Council and it is **not published**; nothing here reserves it.
    Per the [Governance Model](../../overview/index.md#governance-model),
    `dev.ucp.*` is reserved for capabilities the governing body sanctions.

    This draft uses that name because the extension is proposed for the UCP
    Shopping vertical and its schema is served from `ucp.dev`, the only origin
    that passes [Authority Binding](../../overview/index.md#authority-binding)
    for a `dev.ucp.*` name. Binding proves provenance, not approval. Whether
    the extension should instead start **vendor-first** under a publisher-owned
    namespace, as UCP contribution guidance prefers for emerging extensions, is
    an open governance question (see [Open decisions](#open-decisions)). A
    vendor-first publisher cannot reuse this schema URL: its schema must be
    served from its own domain, and the identifiers (schema `name`, scope
    strings, examples) would be renamed, not the behavior.

## Overview

The Order Consultation extension lets a Business, **after an Order is
placed**, propose a commercial change that exceeds the authority the buyer
already gave, and obtain one explicit, revision-bound decision from the buyer
or an appropriately delegated Platform.

The contract has exactly this shape:

**Business proposal → buyer decision → authoritative receipt → application to
the Order.**

Each arrow is a different fact with different validity, concurrency, and
recovery rules. This extension keeps them apart:

| # | Fact | Authority | Recorded as |
| :- | :--- | :-------- | :---------- |
| 1 | The Business issued a proposal | Business | Immutable [revision](#proposal-revisions) |
| 2 | The buyer's approve/decline was recorded | Business, on an authenticated and authorized decision | [Decision receipt](#decision-receipt) |
| 3 | The approved change was applied to the Order | Business, after re-validation | [Application](#application-lifecycle) and the Order's `consultation_applications[]` |
| 4 | A payment or refund occurred | Payment rails and the Order's `adjustments[]` | **Outside this extension** |

### Scope

This extension applies to a single Business proposal and a single terminal
decision on an existing Order. It does **not** define buyer-initiated
cancellation or modification ([#348](https://github.com/Universal-Commerce-Protocol/ucp/issues/348)
/ [#943](https://github.com/Universal-Commerce-Protocol/ucp/issues/943);
authority flows the opposite way), pre-Checkout quotation
([#929](https://github.com/Universal-Commerce-Protocol/ucp/issues/929)),
Checkout restart, multi-round bargaining or counteroffers, partial approval,
automatic acceptance, payment capture or refund, or a generic negotiation
engine. It has **no dependency** on #943 and shares no schema, method, or
schedule with it.

### Relationship to other proposals

| Proposal | Relationship |
| :------- | :----------- |
| [#896](https://github.com/Universal-Commerce-Protocol/ucp/issues/896) contingencies | A change already covered by an accepted contingency needs **no** consultation. Consultation covers what falls outside. See [Pre-existing authority](#pre-existing-authority). |
| [#845](https://github.com/Universal-Commerce-Protocol/ucp/issues/845) accepted-term handoff | The accepted basis stays auditable through `baseline_reference`; consultation amends it only after a new decision. |
| [#641](https://github.com/Universal-Commerce-Protocol/ucp/issues/641) Order Actions | May later announce that a consultation exists. An Action is **not** the proposal, the decision, or the receipt. |
| [#929](https://github.com/Universal-Commerce-Protocol/ucp/issues/929) Quote | Pre-order only. This extension never creates a quote flow. |

None of these is assumed merged or mandatory.

## Capability Declaration

The extension is **optional** and MUST be explicitly negotiated. An Order from
a Business that does not declare it, or a Platform that does not negotiate it,
is the unchanged base [Order](../order/index.md); no field, operation, or
behavior in this page applies.

The extension composes onto `dev.ucp.shopping.order` through
`$defs["dev.ucp.shopping.order"]` in its schema (`allOf` over the base Order),
adding one response-only member, `consultation_applications[]`.

### Business profile

A complete Business profile declares the shopping service bindings, the Order
capability, this extension (extending Order), and the Identity Linking scopes
that gate it:

<!-- ucp:example schema=profile def=business_schema -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": {
      "dev.ucp.shopping": [
        {
          "version": "{{ ucp_version }}",
          "transport": "rest",
          "schema": "https://ucp.dev/{{ ucp_version }}/services/shopping/rest.openapi.json",
          "endpoint": "https://business.example.com/ucp/v1"
        },
        {
          "version": "{{ ucp_version }}",
          "transport": "mcp",
          "schema": "https://ucp.dev/{{ ucp_version }}/services/shopping/mcp.openrpc.json",
          "endpoint": "https://business.example.com/ucp/mcp"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.shopping.order": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/order",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/order.json"
        }
      ],
      "dev.ucp.shopping.order_consultation": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/extensions/order-consultation",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/order_consultation.json",
          "extends": "dev.ucp.shopping.order",
          "config": {
            "supported_change_types": ["usage_tariff_change", "item_substitution"]
          }
        }
      ],
      "dev.ucp.common.identity_linking": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/common/identity-linking/",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/common/identity_linking.json",
          "config": {
            "scopes": {
              "dev.ucp.shopping.order:read": {},
              "dev.ucp.shopping.order_consultation:read": {
                "description": {
                  "plain": "See proposed changes to your orders and their decisions."
                }
              },
              "dev.ucp.shopping.order_consultation:decide": {
                "description": {
                  "plain": "Approve or decline a proposed change to your order. This does not authorize a payment."
                }
              }
            }
          }
        }
      ]
    },
    "payment_handlers": {}
  }
}
```

### Platform profile

A Platform that supports the extension declares it, extending the Order
capability it also declares:

<!-- ucp:example schema=profile def=platform_schema -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "services": {
      "dev.ucp.shopping": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/overview/",
          "transport": "rest",
          "schema": "https://ucp.dev/{{ ucp_version }}/services/shopping/rest.openapi.json",
          "endpoint": "https://platform.example.com/ucp/v1"
        },
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/overview/",
          "transport": "mcp",
          "schema": "https://ucp.dev/{{ ucp_version }}/services/shopping/mcp.openrpc.json",
          "endpoint": "https://platform.example.com/ucp/mcp"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.shopping.order": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/order",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/order.json",
          "config": {"webhook_url": "https://platform.example.com/webhooks/orders"}
        }
      ],
      "dev.ucp.shopping.order_consultation": [
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/extensions/order-consultation",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/order_consultation.json",
          "extends": "dev.ucp.shopping.order"
        }
      ]
    },
    "payment_handlers": {}
  }
}
```

### Discovery, negotiation, and operation resolution

1. **Authority Binding.** Each entity's `schema` URL must bind to its name.
   `dev.ucp.shopping.order_consultation` served from `ucp.dev` derives the
   authority prefix `dev.ucp` and passes. A `com.example.*` name served from
   `ucp.dev` would derive `dev.ucp` and be **rejected**, so a placeholder
   namespace cannot be paired with a `ucp.dev` schema. Binding is provenance
   only; it does not mean the extension is approved or trustworthy.
2. **Negotiation.** The capability is active only if both profiles declare it
   with a mutual version **and** its parent `dev.ucp.shopping.order` is also
   active; otherwise the intersection algorithm prunes it.
3. **Operation resolution.** A Platform resolves operations from the
   `dev.ucp.shopping` service entry for a transport: its `schema` names the
   shopping OpenAPI (REST) or OpenRPC (MCP) description, and the entry's
   `endpoint` is the base URL. The six consultation operations are defined
   **additively in those shared descriptors**
   (`source/services/shopping/rest.openapi.json` and `mcp.openrpc.json`), and
   each states in its description that it requires this extension to be
   negotiated. A standalone, extension-local descriptor would not be reachable:
   negotiation intersects capabilities, not services, and nothing in a profile
   links a capability to a descriptor outside its parent service.
4. **Gating.** A Platform **MUST NOT** call a consultation operation unless the
   extension is in the negotiated set. A Business **MUST** reject an
   un-negotiated invocation with the core `capabilities_incompatible` outcome
   and record nothing.
5. **Composition.** Platforms compose the Order schema with this extension's
   `$defs["dev.ucp.shopping.order"]`. When it is not negotiated the base Order
   applies unchanged and `consultation_applications` is not interpreted.

## Buyer authorization

Recording a new buyer commercial decision requires **buyer authorization**: a
user-authenticated identity token obtained through
[Identity Linking](../../common/identity-linking/index.md), not Platform
credentials.

| Scope | Grants |
| :---- | :----- |
| `dev.ucp.shopping.order_consultation:read` | List and read consultations, revisions, decision receipts, and look up a decision by key, for the buyer's Orders. |
| `dev.ucp.shopping.order_consultation:decide` | Record an approve or decline decision. |

**Declaration.** A Business lists both scopes in `config.scopes` of its
`dev.ucp.common.identity_linking` entry (see the
[Business profile](#business-profile) above). Listing a scope declares that the
operations it covers require a user identity token. The per-scope policy object
MAY carry Identity Linking constraints such as `min_acr` or `max_token_age` to
require stronger or fresher authentication for `:decide`; Platforms derive the
requested scope set per
[Scope Derivation](../../common/identity-linking/index.md#scope-derivation).

**Required context for a decision.** All of the following MUST hold, evaluated
before any replay or admission logic:

1. The request carries a **buyer-authenticated** identity token: validated for
   `iss`, `aud`, `exp`, scope, and `client_id`/`azp` as issued to the calling
   Platform (Identity Linking validation requirements). Platform credentials
   alone (API key, client credentials, request signature) are not buyer
   authorization.
2. The token's scope includes `dev.ucp.shopping.order_consultation:decide`.
3. The token's subject is the **owner of the Order** named in the path, and the
   consultation belongs to that Order. The decision binds to the exact
   consultation and revision.
4. Any delegation or mandate limits on the Platform (for example a permitted
   consultation set or a maximum price impact) cover this exact proposal.

**Behavior when authorization is not established.** A Business **MUST** fail
closed: no admission, no receipt, no idempotency record is created.

| Condition | Response |
| :-------- | :------- |
| No token, Platform credentials only, expired, invalid, or unverifiable token | `401` `identity_required` with `WWW-Authenticate: Bearer` (and `error="invalid_token"` when a token was presented), per Identity Linking |
| Token lacks `:decide` (for example `:read` only, or `dev.ucp.shopping.order:manage` only) | `403` `insufficient_scope` |
| Token's buyer does not own the Order, or the consultation is not on it | `404` `not_found`, so existence is not disclosed |
| Delegation or mandate does not cover the proposal or consultation | `403` `decision_not_authorized` |

Authentication is evaluated **before** replay: a token that has expired between
a submission and its retry gets `401`, never a replay of the cached receipt, and
the same holds for the lookup. Read operations require `:read` from a buyer
token as well; a Business MAY additionally allow Platform credentials to read
consultations for Orders that Platform originated, as for Get Order, but this
never extends to recording a decision.

The following are **never** decision authority, and a Business **MUST** refuse
the decision (`identity_required`, `insufficient_scope`, or
`decision_not_authorized`):

* Platform identity or credentials alone;
* `dev.ucp.shopping.order:manage`, `dev.ucp.shopping.order:read`, or any other
  generalized Order scope;
* the `:read` scope above, or merely being able to read a proposal;
* an Action notification, webhook, or Order read;
* possession of an Order ID or consultation ID;
* an agent preference, inferred buyer intent, or silence.

## Pre-existing authority

Before issuing a proposal, a Business **MUST** determine whether the change is
already authorized: by the accepted commercial terms, by a buyer-approved
contingency (#896), or by another valid authorization. If it is, the Business
applies it under that authority and **MUST NOT** ask for a duplicate decision.
If the proposed change exceeds that authority, the Business **MUST NOT** treat
the original Checkout, a prior unrelated mandate, or a prior consultation
decision as authority for the new terms.

## Proposal revisions

A consultation is a Business-issued resource attached to one Order. It has a
durable `consultation_id` and one or more **immutable, addressable
revisions**.

{{ extension_schema_fields('order_consultation.json#/$defs/proposal', 'shopping/extensions/order-consultation') }}

### Immutability

A revision **MUST** be immutable. Only its `status` changes after publication.
A change to price, quantity, affected items, usage period, deadlines, or any
other approval-relevant term requires a **new revision** (or a new
consultation); a Business **MUST NOT** edit a published revision in place.

The digest is specified in [Proposal digest](#proposal-digest).

A Business **MUST** retain every revision's exact terms and scope for as long
as any decision, application, or Order record references them. The minimum
retention period is an [open decision](#open-decisions).

### Proposal digest

`proposal_digest` binds every approval-relevant member of a revision so that a
receipt identifies exactly the terms that were approved, independent of any
later read.

**Algorithm.**

1. Build the **digest input object** from the revision. Include exactly these
   members, each only when present on the revision (an absent member is omitted,
   never `null`): `consultation_id`, `order_id`, `revision`, `change_type`,
   `scope`, `proposed_terms`, `baseline_reference`, `decision_deadline`,
   `effective_from`, `effective_time_rule`, `application_deadline`. Add the
   constant member `digest_context` with the value
   `dev.ucp.shopping.order_consultation.proposal.v1`.
2. Serialize it with the
   [RFC 8785 JSON Canonicalization Scheme](https://datatracker.ietf.org/doc/html/rfc8785):
   members sorted by UTF-16 code unit, no insignificant whitespace, I-JSON
   numbers. Digest inputs contain only strings, integers, objects, and arrays;
   a floating-point number or an integer outside the I-JSON safe range makes
   the revision invalid.
3. Encode the result as UTF-8, compute SHA-256, and write
   `sha-256:` followed by the 64 lowercase hex characters.

Values are the published JSON values **verbatim**: timestamps are the exact
published strings and are never re-normalized before hashing. `status`,
`reason`, `supersedes_revision`, `superseded_by_revision`,
`follows_consultation_id`, links, and the digest itself are **excluded**,
because they are display or lifecycle data that may change without changing
what is being authorized. Order identity and the accepted basis are covered by
`order_id` and `baseline_reference`; commercial terms by `proposed_terms`;
affected scope by `scope`; effective-time rules by `effective_from` and
`effective_time_rule`; deadlines by `decision_deadline` and
`application_deadline`.

**Not an HTTP digest.** This is a digest of a canonical JSON *object*, not of
raw wire bytes, and it is hex, not the base64 `sha-256=:...:` form of an RFC 9530
`Content-Digest`. The raw-body digest of a request is a different value used for
idempotency payload matching; the two MUST NOT be compared or substituted.

A revision read **MUST** reproduce the same digest at every point in its life,
whatever its `status`; a Platform **MAY** recompute it from the returned members
and **SHOULD** do so before showing terms to a buyer. A receipt's
`proposal_digest` **MUST** equal the digest of the revision it was admitted
against.

For revision 3 above, the digest input is this canonical string:

```text
{"baseline_reference":{"order_version":"v12"},"change_type":"usage_tariff_change","consultation_id":"consult_17","decision_deadline":"2026-10-20T18:00:00Z","digest_context":"dev.ucp.shopping.order_consultation.proposal.v1","effective_from":"2026-10-21T00:00:00Z","order_id":"ord_rental_1","proposed_terms":{"billing_unit":"hour","current_rate_amount":1000,"proposed_rate_amount":1400},"revision":3,"scope":{"rental_id":"equipment_1","usage_from":"2026-10-21T00:00:00Z"}}
```

Changing any single approval-relevant member changes the digest. These vectors
change one member of revision 3 at a time; all are different from the baseline
and from each other:

| Case | Digest |
| :--- | :----- |
| Revision 3 as published (baseline) | `sha-256:f82b10ec6e0551e08a93baddb08f920ed58b6fae1189d39ec1e2391ce8fd8900` |
| `proposed_rate_amount` 1400 to 1500 | `sha-256:90718e97cb01e1c8db452770c996cc73eb8a1f004c433f8b5f74989ab0e341eb` |
| `scope.usage_from` earlier (broader scope) | `sha-256:7c971946641fbe7387b99bde443ba5d5d4f811d19827db3d18f8cbfa8bcc7edc` |
| `scope.rental_id` equipment_2 | `sha-256:25bf9051ad3dda57bc5975deb7798d35fd12a79483ba4acfb8d80fc238db8d7e` |
| `effective_time_rule` set to `exact` | `sha-256:c5b5693c4f1ff228371232923805b65daf8d786baf554eaaabfc51086cf714e8` |
| `effective_from` one hour later | `sha-256:a4b025068b8504e02998ed8a175604ec93b7953950ac7a0a942ca799951d619d` |
| `baseline_reference.order_version` v13 | `sha-256:497b8848c6327df272584542684ebf1d01dfbcf0b3aea5199fb1a49537fc3999` |
| `decision_deadline` one hour later | `sha-256:afabe1c93434dec44924fa1dcbdfa21197c5d762a625fc645e2e3011eb4db59c` |
| `application_deadline` added | `sha-256:98e7a5b2607647156a5c2d28611efad71d03f0b2ac0672fd0034dc745cf5e366` |
| `revision` 4 | `sha-256:0ed303b02340d12007288125f59468b343dd605a385183fc61da8cc8ccf5f7d9` |
| `order_id` ord_rental_2 | `sha-256:6f61cab9ed78c21dfd5e9748f9289d10bae929b059141e6505fdc998c839de06` |
| `consultation_id` consult_18 | `sha-256:13b4e18f49c9b41628f08cd2d06180c1c629357ebb94c2336edfaea89ba6e36e` |

Adding `reason`, changing `status`, or adding `supersedes_revision` does **not**
change the digest. The conformance harness recomputes these values and checks
them against an independent JCS implementation in a second language.

### Lifecycle

| `status` | Meaning |
| :------- | :------ |
| `open` | The **current** revision can receive a decision. |
| `approved` | A valid approval was recorded against this revision. |
| `declined` | A valid decline was recorded against this revision. |
| `expired` | `decision_deadline` passed with no recorded decision. |
| `withdrawn` | The Business withdrew an undecided revision. |
| `superseded` | A newer revision replaced this undecided revision. |

* Only the **current**, `open`, unexpired, unwithdrawn revision can accept a
  new decision.
* `approve` and `decline` are mutually exclusive terminal decisions for a
  revision. Exactly one can commit.
* A new revision supersedes **undecided** revisions only. It **MUST NOT**
  invalidate, replace, or erase a recorded decision. After a terminal decision
  the Business **MUST NOT** add revisions to that consultation; materially
  different terms require a **new `consultation_id`** that MAY name the earlier
  one in `follows_consultation_id`.
* Silence, timeout, or a non-response is never approval. An unanswered
  proposal becomes `expired`.
* `status` is an **open vocabulary**. A Platform **MUST** treat an
  unrecognized `status` as **not actionable** and **MUST NOT** submit a
  decision against it. A Business **MUST NOT** emit a status that permits a
  decision unless it is `open`.

### Effective time and deadlines

`decision_deadline` is the last instant (inclusive) at which a **new** decision
may be admitted. It is evaluated by the Business at **admission time**, never
when a request was generated or sent. A request that left the Platform before
the deadline but is admitted after it is refused as `proposal_expired`.

`effective_from` is the proposed effective time for time-based changes.
`effective_time_rule` states how it binds application:

| `effective_time_rule` | Meaning |
| :-------------------- | :------ |
| `not_before` (default) | `effective_from` is the **earliest** authorized start. The actual boundary is the later of `effective_from` and the authoritative application-commit time. |
| `exact` | Buyer acceptance is conditioned on that exact instant. If it cannot be honored, application MUST fail or a new proposal MUST be issued. |

`application_deadline` is optional and separate. A decision validly recorded
before `decision_deadline` stays authorized afterward, but application MUST
still satisfy `application_deadline` when present. Unknown
`effective_time_rule` values are treated as `exact` by Platforms and rejected
at issuance by Businesses.

## Domain profiles

The common envelope is deliberately not a pricing or fulfillment schema.
`scope` and `proposed_terms` are defined per `change_type`. This draft defines
two **illustrative** profiles, enforced in the schema by `if`/`then` on
`change_type`, to prove the envelope carries both a metered and a Shopping
case. They are not a registry of standard change types.

| `change_type` | `scope` | `proposed_terms` | Authoritative applied terms |
| :------------ | :------ | :--------------- | :-------------------------- |
| `usage_tariff_change` | `rental_id`, `usage_from` | `current_rate_amount`, `proposed_rate_amount`, `billing_unit` | `consultation_applications[].applied_terms.rate_schedule` |
| `item_substitution` | `line_item_id`, `quantity` | `replacement_item`, `price_delta_amount` | The Order's own `line_items[]`, linked by `consultation_applications[]` |

The generic UCP Order has no `rental_rate` field. A domain **MUST** state where
newly accepted terms are authoritatively represented and link them to the
baseline and the decision receipt. Here that is the Order's
`consultation_applications[]` record (below). A domain MAY define a richer
Order-linked extension instead; it **MUST** still preserve the baseline and
reference the `decision_id` and `proposal_digest`.

Amounts are integer minor units. Currency comes from the Order.

### Example: metered rental tariff (revision 3 open, revision 2 superseded)

A buyer accepted a rental at 1000 per hour. The Business proposes 1400 per
hour for future usage. Revision 3 is current; revision 2 was superseded by it.

Consultation read:

<!-- ucp:example schema=shopping/order_consultation def=consultation -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.order_consultation": [{"version": "{{ ucp_version }}"}]
    }
  },
  "consultation_id": "consult_17",
  "order_id": "ord_rental_1",
  "status": "open",
  "current_revision": 3,
  "proposal": {
    "consultation_id": "consult_17",
    "order_id": "ord_rental_1",
    "revision": 3,
    "status": "open",
    "change_type": "usage_tariff_change",
    "scope": {
      "rental_id": "equipment_1",
      "usage_from": "2026-10-21T00:00:00Z"
    },
    "proposed_terms": {
      "current_rate_amount": 1000,
      "proposed_rate_amount": 1400,
      "billing_unit": "hour"
    },
    "baseline_reference": {"order_version": "v12"},
    "decision_deadline": "2026-10-20T18:00:00Z",
    "effective_from": "2026-10-21T00:00:00Z",
    "reason": "Updated rental tariff for future usage.",
    "supersedes_revision": 2,
    "proposal_digest": "sha-256:f82b10ec6e0551e08a93baddb08f920ed58b6fae1189d39ec1e2391ce8fd8900"
  },
  "revisions": [
    {
      "revision": 1,
      "status": "superseded",
      "proposal_digest": "sha-256:26a514f31271b82ca4a8ec8c98b801f942c04e2963f4a2409a1a11f0def8d179"
    },
    {
      "revision": 2,
      "status": "superseded",
      "proposal_digest": "sha-256:ce91608857acb193cba3bfc2e2506668cc3bba9d4f5cc7c4e81a03fb84177305"
    },
    {
      "revision": 3,
      "status": "open",
      "proposal_digest": "sha-256:f82b10ec6e0551e08a93baddb08f920ed58b6fae1189d39ec1e2391ce8fd8900"
    }
  ]
}
```

The exact terms of superseded revision 2 remain retrievable. The revision read
returns the original immutable terms; only `status` and
`superseded_by_revision` describe what happened to it afterward:

<!-- ucp:example schema=shopping/order_consultation def=consultation_revision -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.order_consultation": [{"version": "{{ ucp_version }}"}]
    }
  },
  "consultation_id": "consult_17",
  "order_id": "ord_rental_1",
  "revision": 2,
  "status": "superseded",
  "change_type": "usage_tariff_change",
  "scope": {
    "rental_id": "equipment_1",
    "usage_from": "2026-10-21T00:00:00Z"
  },
  "proposed_terms": {
    "current_rate_amount": 1000,
    "proposed_rate_amount": 1300,
    "billing_unit": "hour"
  },
  "baseline_reference": {"order_version": "v12"},
  "decision_deadline": "2026-10-20T18:00:00Z",
  "effective_from": "2026-10-21T00:00:00Z",
  "superseded_by_revision": 3,
  "proposal_digest": "sha-256:ce91608857acb193cba3bfc2e2506668cc3bba9d4f5cc7c4e81a03fb84177305"
}
```

### Example: substitution not covered by a contingency (Shopping Order)

A buyer ordered two cartons of oat milk. The item is unavailable. No accepted
contingency covers a more expensive substitute, so the Business needs a fresh
decision:

<!-- ucp:example schema=shopping/order_consultation def=consultation_revision -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.order_consultation": [{"version": "{{ ucp_version }}"}]
    }
  },
  "consultation_id": "consult_21",
  "order_id": "ord_grocery_1",
  "revision": 1,
  "status": "open",
  "change_type": "item_substitution",
  "scope": {"line_item_id": "li_1", "quantity": 2},
  "proposed_terms": {
    "replacement_item": {
      "id": "oat_milk_barista_1l",
      "title": "Barista Oat Milk 1L",
      "price": 520
    },
    "price_delta_amount": 140
  },
  "baseline_reference": {"order_version": "v4"},
  "decision_deadline": "2026-10-20T20:00:00Z",
  "reason": "Requested item unavailable; substitute costs more than any accepted contingency allows.",
  "proposal_digest": "sha-256:54a907946111d7fe4c4476ae5adb82147a2482969a4b5a826e93d77d36e76a88"
}
```

`price_delta_amount` is an additional obligation. Approving this does not
authorize charging it; see [Payment authority](#payment-authority-is-separate).

## Discovery

A Business implementing this extension **MUST** expose exactly one
authoritative, Order-scoped discovery path for actionable consultations. This
draft selects the **Order-scoped list operation**,
`GET /orders/{id}/consultations`, and it is mandatory. (The alternative
in #944, negotiated references on `get_order`, is deliberately not defined, so
the two are not both optional.)

* By default the list returns every consultation of the Order whose current
  revision is `open`. The `status` filter selects other states (repeatable).
  The default MUST be `open`, so a request without a filter lists exactly the
  actionable consultations.
* An empty `consultations` array on a successful read is an authoritative
  statement that no matching consultation exists at read time.
* A Platform **MUST** follow `pagination.cursor` until `has_next_page` is
  `false` before concluding that nothing is actionable.
* A webhook, Action, or other notification **MAY** announce a consultation but
  **MUST NOT** be the only way to find one. A missed notification **MUST NOT**
  permanently hide an outstanding proposal.

<!-- ucp:example schema=shopping/order_consultation def=consultation_list -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.order_consultation": [{"version": "{{ ucp_version }}"}]
    }
  },
  "order_id": "ord_rental_1",
  "consultations": [
    {
      "consultation_id": "consult_17",
      "order_id": "ord_rental_1",
      "status": "open",
      "current_revision": 3,
      "change_type": "usage_tariff_change",
      "decision_deadline": "2026-10-20T18:00:00Z",
      "proposal_digest": "sha-256:f82b10ec6e0551e08a93baddb08f920ed58b6fae1189d39ec1e2391ce8fd8900"
    }
  ],
  "pagination": {"has_next_page": false}
}
```

## Decision admission

A decision request carries only `proposal_revision`, `decision`, and an
optional `proposal_digest`. The Business resolves scope and terms from its
immutable revision. A request that supplies `scope`, `proposed_terms`, or
`authorized_scope` **MUST** be refused (`decision_scope_not_accepted`);
a Platform cannot widen or narrow what the Business authored. Partial
acceptance is not supported: to authorize narrower or different terms, the
Business issues a new proposal.

<!-- ucp:example schema=shopping/order_consultation def=decision_request direction=request op=decide -->
```json
POST /orders/ord_rental_1/consultations/consult_17/decisions HTTP/1.1
Idempotency-Key: b3b8f086-8f4e-41ab-bdc5-3f9156f05f79
Content-Type: application/json

{
  "proposal_revision": 3,
  "decision": "approve",
  "proposal_digest": "sha-256:f82b10ec6e0551e08a93baddb08f920ed58b6fae1189d39ec1e2391ce8fd8900"
}
```

`proposal_digest` is optional but **RECOMMENDED**: it is the digest of what the
buyer was shown. When present and different from the revision's digest, the
Business **MUST** refuse with `proposal_digest_mismatch` and record nothing.

### Admission procedure

The Business **MUST** perform the following as one **linearizable** step per
consultation: decision admission is serialized against the authoritative
current revision, so exactly one terminal decision can win and every later
attempt observes it. Checks run in this order and the first failure decides
the response; nothing is recorded on failure.

1. **Authenticate and authorize.** The actor is authenticated and holds
   `:decide` for the buyer who owns the Order. If the Order or consultation is
   unknown, belongs to a different Order, or belongs to a different buyer,
   respond `not_found` (404) so existence is not disclosed. Insufficient scope
   is `insufficient_scope` (403).
2. **Replay store.** If the idempotency/replay store cannot be read or written,
   **fail closed**: `replay_store_unavailable` (503), nothing recorded.
3. **Idempotency.** Same scoped key and identical raw body bytes: return the
   original response and perform no new side effect. Same key and different
   bytes: `idempotency_key_conflict` (409).
4. **Request validity.** Forbidden members: `decision_scope_not_accepted`
   (422).
5. **Terminal decision already recorded:** `decision_conflict` (409), with
   `data.decision_id` naming the authoritative receipt.
6. **Revision.** An older revision is `proposal_superseded` (409) with
   `data.current_revision`. A revision that does not exist is `not_found`.
7. **Status.** `withdrawn` is `proposal_withdrawn` (409). `open` but past
   `decision_deadline` at admission time is `proposal_expired` (409).
8. **Digest.** Mismatch is `proposal_digest_mismatch` (422).
9. **Still applicable.** If `baseline_reference` no longer matches the
   authoritative Order basis, `proposal_stale` (409) with
   `data.current_revision`.
10. **Delegation and mandate constraints.** An actor whose delegation or
    mandate does not cover this proposal gets `decision_not_authorized` (403).
11. **Commit** the receipt, the idempotency record, and the consultation's
    terminal state atomically.

Possession of an Order ID, or the ability to read a proposal, does not by
itself establish decision authority.

### Serialization point

Decision admission, expiry, withdrawal, and supersession of one consultation
**MUST** be totally ordered by a single **serialization point**: one atomic
operation on the consultation's authoritative record at which the Business
reads the current state, evaluates the clock, decides, and commits. Everything
a decision depends on is evaluated at that point:

* the current revision and status (including withdrawal and supersession);
* `decision_deadline`, against the Business clock **at that point**, never the
  time a request was generated, sent, or received;
* whether a terminal decision already exists.

The clock is monotonic across serialization points. `recorded_at` is assigned at
the point and never exceeds `decision_deadline` for a recorded decision. A
withdrawal or supersession is also a serialization point; it takes effect for
every later point and cannot take effect after a decision that was admitted
earlier. Consequently:

* **An admitted decision cannot commit invisibly later.** There is no step
  between the checks and the commit that sits outside the point. A pipeline that
  checks first and commits afterward without holding that serialization (for
  example admission on request *arrival* time, then a delayed commit) is
  non-conforming.
* **A decision serialized before closure is visible to every read that follows
  closure.** Closure therefore cannot report non-commitment while an earlier
  decision can still commit.
* **A lookup is itself a serialization point.** A `final: true` result is
  produced at a point after which the consultation can accept no decision, so
  nothing, including the original attempt, can commit afterward.

An attempt that has been received but has not reached its serialization point is
**in flight**. Until it reaches it, the Business cannot say how it will resolve,
so a lookup reports `in_flight`, never `final`. If closure occurs first, the
attempt is refused when it reaches its point.

### Races

* **Approve versus decline.** Whichever admission commits first wins. The loser
  receives `decision_conflict` and **MAY** read the authoritative receipt named
  in `data.decision_id`. Two approvals race the same way: one receipt, one
  conflict.
* **Withdrawal or supersession versus decision.** Whichever becomes authoritative
  first decides. If a withdrawal or supersession commits first, a new approval
  is refused and no authorization is recorded. If the approval commits first,
  it remains historically authoritative and a later withdrawal **MUST NOT**
  erase it; a recorded decision can only be followed by a separately authorized
  amendment or cancellation, never rewritten.
* **Expiry** is evaluated when the decision is admitted, not when a delayed
  request was generated.

### Revision binding

An approval of revision 3 **never** authorizes revision 4:

<!-- ucp:example schema=shopping/order_consultation def=consultation_error_response -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "status": "error",
    "capabilities": {
      "dev.ucp.shopping.order_consultation": [{"version": "{{ ucp_version }}"}]
    }
  },
  "messages": [
    {
      "type": "error",
      "code": "proposal_superseded",
      "severity": "requires_buyer_review",
      "content": "Revision 3 was superseded. Review revision 4 before deciding.",
      "data": {"current_revision": 4}
    }
  ]
}
```

### Expired and withdrawn proposals refuse new decisions

<!-- ucp:example schema=shopping/order_consultation def=consultation_error_response -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "status": "error",
    "capabilities": {
      "dev.ucp.shopping.order_consultation": [{"version": "{{ ucp_version }}"}]
    }
  },
  "messages": [
    {
      "type": "error",
      "code": "proposal_expired",
      "severity": "unrecoverable",
      "content": "The decision deadline passed before this request was admitted.",
      "data": {"consultation_status": "expired"}
    }
  ]
}
```

<!-- ucp:example schema=shopping/order_consultation def=consultation_error_response -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "status": "error",
    "capabilities": {
      "dev.ucp.shopping.order_consultation": [{"version": "{{ ucp_version }}"}]
    }
  },
  "messages": [
    {
      "type": "error",
      "code": "proposal_withdrawn",
      "severity": "unrecoverable",
      "content": "The Business withdrew this proposal before the decision was admitted.",
      "data": {"consultation_status": "withdrawn"}
    }
  ]
}
```

### Concurrent approve and decline

Two authorized actors race. Approval commits first; the decline loses with a
deterministic conflict that points to the authoritative receipt:

<!-- ucp:example schema=shopping/order_consultation def=consultation_error_response -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "status": "error",
    "capabilities": {
      "dev.ucp.shopping.order_consultation": [{"version": "{{ ucp_version }}"}]
    }
  },
  "messages": [
    {
      "type": "error",
      "code": "decision_conflict",
      "severity": "unrecoverable",
      "content": "A terminal decision is already recorded for this revision.",
      "data": {"decision_id": "dec_52", "consultation_status": "approved"}
    }
  ]
}
```

## Decision receipt

The Business assigns a durable `decision_id` when a valid terminal decision
commits. The receipt is attributable to the immutable proposal through
`proposal_revision` and `proposal_digest`.

{{ extension_schema_fields('order_consultation.json#/$defs/decision_receipt_body', 'shopping/extensions/order-consultation') }}

The `application` member:

{{ extension_schema_fields('order_consultation.json#/$defs/application', 'shopping/extensions/order-consultation') }}

`status: recorded` means a decision **committed**. It does not mean the Order
was amended and it does not authorize any payment.

### Approval receipt

An approval **MUST** carry `authorized_scope` (a copy of the Business-authored
scope) and an `application_status` other than `not_applicable`. A new approval
starts at `pending`:

<!-- ucp:example schema=shopping/order_consultation def=decision_receipt -->
```json
HTTP/1.1 201 Created
Content-Type: application/json

{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.order_consultation": [{"version": "{{ ucp_version }}"}]
    }
  },
  "decision_id": "dec_52",
  "consultation_id": "consult_17",
  "order_id": "ord_rental_1",
  "proposal_revision": 3,
  "proposal_digest": "sha-256:f82b10ec6e0551e08a93baddb08f920ed58b6fae1189d39ec1e2391ce8fd8900",
  "decision": "approve",
  "status": "recorded",
  "recorded_at": "2026-10-20T17:30:00Z",
  "decided_by": {"type": "buyer", "id": "buyer_8a1f"},
  "authorized_scope": {
    "rental_id": "equipment_1",
    "usage_from": "2026-10-21T00:00:00Z"
  },
  "application_status": "pending"
}
```

### Decline receipt

A decline is recorded as a terminal decision but **grants no authority to amend
the Order**. The schema makes this mechanically verifiable: a decline receipt
**MUST** omit `authorized_scope` and `application`, and **MUST** omit
`application_status` or set it to `not_applicable`. It is **never** `pending`,
`applied`, `failed`, or `indeterminate`. A decline never enters the application
lifecycle.

This is an **alternative** outcome to the approval above, not a second decision
on the same revision:

<!-- ucp:example schema=shopping/order_consultation def=decision_receipt -->
```json
HTTP/1.1 201 Created
Content-Type: application/json

{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.order_consultation": [{"version": "{{ ucp_version }}"}]
    }
  },
  "decision_id": "dec_53",
  "consultation_id": "consult_17",
  "order_id": "ord_rental_1",
  "proposal_revision": 3,
  "proposal_digest": "sha-256:f82b10ec6e0551e08a93baddb08f920ed58b6fae1189d39ec1e2391ce8fd8900",
  "decision": "decline",
  "status": "recorded",
  "recorded_at": "2026-10-20T17:35:00Z",
  "decided_by": {"type": "buyer", "id": "buyer_8a1f"},
  "application_status": "not_applicable"
}
```

A Platform **MUST** treat a `decision` value other than `approve` as granting
no authority, and an unrecognized `application_status` as `indeterminate`.

## Idempotency and lost-response recovery

A decision submission **MUST** carry an `Idempotency-Key` per
[Message Signatures — Replay Protection](../../signatures.md#replay-protection):

* **Generation.** At least 128 bits of entropy (for example a UUID v4). A
  Platform generates a new key for each new decision request. Placeholders such
  as `decision-attempt-001` are not valid keys.
* **Scope.** The key is scoped to the **authenticated Platform identity, Order
  ID, consultation ID, and operation type (`decide`)**. The same string under a
  different scope is a different key.
* **Replay.** Same scoped key and identical **raw body bytes** (compared by
  SHA-256 of the received bytes, the same digest as `Content-Digest`) returns
  the original response with no second side effect. Different bytes under the
  same key is `idempotency_key_conflict`. Re-serializing the same JSON with
  different whitespace is a different payload.
* **Retention.** The replay record is kept for **at least 24 hours** (48
  recommended). On replay-store failure the Business **MUST fail closed**
  (`replay_store_unavailable`, 503) and record nothing.
* **Receipt durability is separate.** The decision receipt is a **durable
  reconciliation record**, not the replay cache. The Business **MUST** retain
  the association between the original scoped key and the `decision_id`, and
  the receipt itself, beyond the replay window for as long as the revision it
  binds to is retained. After the replay window a repeated POST is no longer
  guaranteed to replay, but [lookup by key](#lookup-by-original-key) still
  resolves.

A replayed response is the **original** response and reflects the state at the
original admission (for example `application_status: pending`). Read the
decision resource for the current application state.

Replay applies to **committed** admissions. A refusal records no decision and
need not be cached: the states behind `proposal_expired`,
`proposal_withdrawn`, `proposal_superseded`, and `decision_conflict` never
revert, so recomputing them for a repeated request is stable. A Business
**MUST NOT** let a retried request succeed after an earlier identical request
was refused for one of those reasons.

### Lookup by original key

If the POST returned no response, the request may still have committed. The
Platform **MUST NOT** assume it was rejected. Recovery:

1. **Look up the decision** with the original scoped key
   (`GET .../decisions` with the original key in the `Original-Idempotency-Key` header) or, if
   known, by `decision_id`.
2. **Read the consultation** for a competing decision, expiry, supersession, or
   withdrawal.
3. **Read the Order** to see whether the change was applied.
4. If still unresolved, **retry the same POST with the same key and identical
   body bytes**. This is always safe: it replays the committed result or
   deterministically admits or refuses once.

A Platform **MUST NOT** retry with a new key, and **MUST NOT** swap `approve`
for `decline` (or the reverse), merely because a lookup returned nothing.

The lookup is scoped like the key: it never returns another Platform's or
another buyer's decision, and an unauthorized caller gets `not_found`. The key
is carried in the `Original-Idempotency-Key` header so it does not appear in URLs
or logs. The lookup is read-only: it is **not** itself idempotency-keyed, the
Business **MUST NOT** store a replay record for it, and the header is a lookup
argument, not an idempotency key for the lookup.

The lookup distinguishes three outcomes so that absence is never misread:

| `outcome` | `final` | Meaning |
| :-------- | :------ | :------ |
| `recorded` | n/a | The decision committed. `decision` carries the receipt. |
| `in_flight` | never `true` | An admission under this scoped key is still being processed. Not a failure. |
| `not_recorded` | `false` or absent | **Provisional.** No record is visible. This is **not** proof the request cannot still commit. |
| `not_recorded` | `true` | **Authoritative no-commit.** `final_reason` states the guarantee. |

A Business **MUST NOT** return `final: true` unless it can guarantee that no
admission under that scoped key can later commit. The one reason defined here is
`consultation_closed`: at the lookup's [serialization point](#serialization-point)
the consultation can accept **no** further decision (expired, withdrawn,
superseded, or already decided). Because admission, expiry, withdrawal, and
supersession share that ordering, every attempt not yet committed, including
one still in flight, is refused when it reaches its own point. An attempt that
is in flight when the consultation is still open is `in_flight`, not final.
`final: true` is permanent for that scoped key: a same-key retry returns the
refusal and creates no decision.
A Business that cannot provide that guarantee returns `final: false` and relies
on the same-key retry above.

<!-- ucp:example schema=shopping/order_consultation def=decision_lookup -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.order_consultation": [{"version": "{{ ucp_version }}"}]
    }
  },
  "outcome": "recorded",
  "checked_at": "2026-10-20T17:31:10Z",
  "decision": {
    "decision_id": "dec_52",
    "consultation_id": "consult_17",
    "order_id": "ord_rental_1",
    "proposal_revision": 3,
    "proposal_digest": "sha-256:f82b10ec6e0551e08a93baddb08f920ed58b6fae1189d39ec1e2391ce8fd8900",
    "decision": "approve",
    "status": "recorded",
    "recorded_at": "2026-10-20T17:30:00Z",
    "authorized_scope": {
      "rental_id": "equipment_1",
      "usage_from": "2026-10-21T00:00:00Z"
    },
    "application_status": "pending"
  }
}
```

An in-flight admission is not a negative:

<!-- ucp:example schema=shopping/order_consultation def=decision_lookup -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.order_consultation": [{"version": "{{ ucp_version }}"}]
    }
  },
  "outcome": "in_flight",
  "checked_at": "2026-10-20T17:30:01Z"
}
```

Absence while the consultation is still `open` is provisional:

<!-- ucp:example schema=shopping/order_consultation def=decision_lookup -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.order_consultation": [{"version": "{{ ucp_version }}"}]
    }
  },
  "outcome": "not_recorded",
  "final": false,
  "checked_at": "2026-10-20T17:30:02Z"
}
```

Only after the consultation has closed can absence be final:

<!-- ucp:example schema=shopping/order_consultation def=decision_lookup -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.order_consultation": [{"version": "{{ ucp_version }}"}]
    }
  },
  "outcome": "not_recorded",
  "final": true,
  "final_reason": "consultation_closed",
  "checked_at": "2026-10-20T18:00:05Z"
}
```

A reused key with a different body is refused without executing:

<!-- ucp:example schema=shopping/order_consultation def=consultation_error_response -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "status": "error",
    "capabilities": {
      "dev.ucp.shopping.order_consultation": [{"version": "{{ ucp_version }}"}]
    }
  },
  "messages": [
    {
      "type": "error",
      "code": "idempotency_key_conflict",
      "severity": "unrecoverable",
      "content": "This Idempotency-Key was already used with a different request body. Nothing was executed."
    }
  ]
}
```

## Application lifecycle

A recorded **approval** authorizes the proposed change within its exact scope
and conditions. Applying it is a **separate Business operation**. Only
approvals enter this lifecycle; a decline is `not_applicable`.

| `application_status` | Meaning |
| :------------------- | :------ |
| `pending` | Authorization recorded; amendment not yet applied. |
| `applied` | Amendment committed to the authoritative Order. |
| `failed` | Application conclusively did not commit. |
| `indeterminate` | Whether application committed is not currently authoritative. |
| `not_applicable` | No application is authorized or required (decline). |

Permitted transitions: `pending → applied | failed | indeterminate`;
`indeterminate → applied | failed`. `applied` and `failed` are final. The
receipt's decision members never change; only `application_status` and
`application` evolve.

Before applying, the Business **MUST** re-validate against the current
authoritative Order: the scope still applies, the order state and constraints
allow it, and any required payment authority exists. If the approved change is
no longer possible the Business **MUST** record `failed` (for example
`order_changed`) or issue a **new** proposal. It **MUST NOT** silently apply
different, broader, or narrower terms under the old approval.

The schema enforces the shape of each state: `applied` requires an
`application` with `applied_at` and `resulting_order_version`; `failed`
requires `application.failure`; `pending` and `indeterminate` carry no applied
timestamps.

### Prospective effective boundary (late application)

!!! note "Domain-specific timing rule"

    The later-of boundary below is the rule for the illustrative
    `usage_tariff_change` profile, where moving the start earlier would reprice
    usage the buyer already incurred. It is **not** a universal rule for every
    consultation type: delaying the effective date of a buyer-favorable change
    (for example an approved discount) could disadvantage the buyer. Each domain
    profile **MUST** state its own timing rule. The cross-domain principle is
    only this: application **MUST NOT** materially change the approved
    commercial terms, and a change the approval did not cover requires a new
    proposal.

For a prospective, usage-priced change with `effective_time_rule: not_before`,
if the Business commits the amendment later than `effective_from`, the actual
boundary is the **later of** the approved `effective_from` and the
authoritative application-commit time (`applied_at`). The Business **MUST**
publish `applied_at` and `actual_effective_from`. Usage accrued **before** the
boundary stays at the previously accepted tariff, **including usage that has not
yet been billed**. A generic `effective_from` never implies retroactive repricing
authority. A domain that permits historical repricing needs a separately
explicit, bounded window in its own `scope` and valid authorization for it.

If acceptance was conditioned on an exact instant (`exact`) and that instant can
no longer be honored, application **MUST** fail or a new proposal **MUST** be
issued. The Business **MUST NOT** silently move the boundary.

#### Adversarial example: approval before the deadline, application after `effective_from`

* `2026-10-20T17:30:00Z`: revision 3 approved. This is before the
  `decision_deadline` of `2026-10-20T18:00:00Z`. Receipt `dec_52`, `pending`.
* `2026-10-21T00:00:00Z`: the proposed `effective_from` passes. The change is
  **not** yet applied.
* `2026-10-21T01:00:00Z`: the renter uses 1 hour of equipment. It accrues
  at the **accepted rate of 1000**.
* `2026-10-21T02:00:00Z`: the Business commits the amendment. `applied_at` and
  `actual_effective_from` are both `2026-10-21T02:00:00Z`.
* `2026-10-21T03:00:00Z`: the renter uses another hour. It accrues at the
  **applied rate of 1400**.

The 01:00 usage is **not** repriced to 1400, even though it happened after
`effective_from` and has not been invoiced. The authoritative decision receipt
now reports the application:

<!-- ucp:example schema=shopping/order_consultation def=decision_receipt -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.order_consultation": [{"version": "{{ ucp_version }}"}]
    }
  },
  "decision_id": "dec_52",
  "consultation_id": "consult_17",
  "order_id": "ord_rental_1",
  "proposal_revision": 3,
  "proposal_digest": "sha-256:f82b10ec6e0551e08a93baddb08f920ed58b6fae1189d39ec1e2391ce8fd8900",
  "decision": "approve",
  "status": "recorded",
  "recorded_at": "2026-10-20T17:30:00Z",
  "authorized_scope": {
    "rental_id": "equipment_1",
    "usage_from": "2026-10-21T00:00:00Z"
  },
  "application_status": "applied",
  "application": {
    "applied_at": "2026-10-21T02:00:00Z",
    "actual_effective_from": "2026-10-21T02:00:00Z",
    "resulting_order_version": "v13",
    "affected_components": ["rental:equipment_1"]
  }
}
```

The Order is the authoritative place for the applied terms. It keeps the
earlier tariff and links the new one to the baseline, the exact revision
digest, and the receipt:

<!-- ucp:example schema=shopping/order_consultation def=dev.ucp.shopping.order -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.order": [{"version": "{{ ucp_version }}"}],
      "dev.ucp.shopping.order_consultation": [{"version": "{{ ucp_version }}"}]
    }
  },
  "id": "ord_rental_1",
  "checkout_id": "chk_rental_1",
  "permalink_url": "https://business.example.com/orders/ord_rental_1",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_rental",
      "item": {"id": "equipment_1", "title": "Excavator rental", "price": 1000},
      "quantity": {"original": 1, "total": 1, "fulfilled": 0},
      "totals": [
        {"type": "subtotal", "amount": 1000},
        {"type": "total", "amount": 1000}
      ],
      "status": "processing"
    }
  ],
  "fulfillment": {},
  "totals": [
    {"type": "subtotal", "amount": 1000},
    {"type": "total", "amount": 1000}
  ],
  "consultation_applications": [
    {
      "consultation_id": "consult_17",
      "decision_id": "dec_52",
      "proposal_revision": 3,
      "proposal_digest": "sha-256:f82b10ec6e0551e08a93baddb08f920ed58b6fae1189d39ec1e2391ce8fd8900",
      "change_type": "usage_tariff_change",
      "baseline_reference": {"order_version": "v12"},
      "applied_at": "2026-10-21T02:00:00Z",
      "actual_effective_from": "2026-10-21T02:00:00Z",
      "resulting_order_version": "v13",
      "applied_terms": {
        "rental_id": "equipment_1",
        "rate_schedule": [
          {
            "valid_from": "2026-10-01T00:00:00Z",
            "valid_until": "2026-10-21T02:00:00Z",
            "rate_amount": 1000,
            "billing_unit": "hour"
          },
          {
            "valid_from": "2026-10-21T02:00:00Z",
            "rate_amount": 1400,
            "billing_unit": "hour",
            "decision_id": "dec_52"
          }
        ]
      }
    }
  ]
}
```

A Platform that did not negotiate the extension sees the unchanged base Order,
and `consultation_applications[]` is never present for a decline.

### Payment authority is separate

Commercial approval **MUST NOT** be treated as authorization to execute a new
payment or charge. An approval receipt records authorization only within the
scope and conditions of that decision. Payment and mandate checks continue to
apply on their own terms (for example
[AP2 Mandates](../../payment/extensions/ap2-mandates.md)), and any charge or
refund appears in the Order's `adjustments[]`, never inferred from the receipt.
If application would create a new obligation without payment authority, the
Business **MUST** fail application (`payment_authority_missing`) or obtain that
authority separately.

## Operations

The operations are defined **additively** in the shared shopping service
descriptors, `source/services/shopping/rest.openapi.json` and
`source/services/shopping/mcp.openrpc.json`, and are reached through the
`dev.ucp.shopping` entries of the [Business profile](#business-profile). Each
operation's description states that it requires this extension to be negotiated.

| Operation | REST | MCP tool | Purpose |
| :-------- | :--- | :------- | :------ |
| List consultations | `GET /orders/{id}/consultations` | `list_order_consultations` | **Mandatory** discovery. |
| Get consultation | `GET /orders/{id}/consultations/{consultation_id}` | `get_order_consultation` | Current revision, status, index, decision. |
| Get revision | `GET .../revisions/{revision}` | `get_order_consultation_revision` | Exact immutable historical terms. |
| Record decision | `POST .../decisions` | `decide_order_consultation` | One terminal decision. Idempotent. |
| Look up by key | `GET .../decisions` with `Original-Idempotency-Key` | `lookup_order_consultation_decision` | Lost-response recovery. |
| Get decision | `GET .../decisions/{decision_id}` | `get_order_consultation_decision` | Durable receipt and application state. |

State-changing operations: only **Record decision**. Platforms **MUST** include
`UCP-Agent` on all requests and `Idempotency-Key` on Record decision, and sign
requests per [Message Signatures](../../signatures.md) when signing is in use
(covering `idempotency-key` and `content-digest`). Record decision additionally
requires [buyer authorization](#buyer-authorization).

A Business **MUST NOT** create consultations through this protocol: proposals
are issued through the Business's own authorized process. There is no
Platform-side `create_consultation`.

### Errors

Consultation refusals are **non-2xx on REST** so that no intermediary or naive
client can read a refusal as success. This intentionally differs from the Order
read, which reports `not_found` as a business outcome with HTTP 200; see
[Open decisions](#open-decisions).

| Code | REST | MCP | Severity | Condition |
| :--- | :--: | :-- | :------- | :-------- |
| `capabilities_incompatible` | 200 | result, `isError` | `unrecoverable` | The extension was not negotiated; core negotiation outcome, unchanged. |
| `not_found` | 404 | result, `isError` | `unrecoverable` | Unknown ID, wrong Order, or not visible to the caller (cross-buyer, cross-Order). |
| `insufficient_scope` | 403 | result, `isError` | `unrecoverable` | Missing `:read` or `:decide`. |
| `decision_not_authorized` | 403 | result, `isError` | `requires_buyer_review` | Delegation or mandate constraints do not cover the proposal. |
| `proposal_superseded` | 409 | result, `isError` | `requires_buyer_review` | Revision is no longer current. `data.current_revision`. |
| `proposal_stale` | 409 | result, `isError` | `requires_buyer_review` | `baseline_reference` no longer applies. |
| `proposal_expired` | 409 | result, `isError` | `unrecoverable` | Admitted after `decision_deadline`. |
| `proposal_withdrawn` | 409 | result, `isError` | `unrecoverable` | Withdrawal committed first. |
| `decision_conflict` | 409 | result, `isError` | `unrecoverable` | A terminal decision exists. `data.decision_id`. |
| `idempotency_key_conflict` | 409 | JSON-RPC `-32000` | `unrecoverable` | Key reused with different raw body. |
| `proposal_digest_mismatch` | 422 | result, `isError` | `unrecoverable` | Echoed digest differs. |
| `decision_scope_not_accepted` | 422 | result, `isError` | `unrecoverable` | Request supplied scope or terms. |
| `replay_store_unavailable` | 503 | JSON-RPC `-32000` | `recoverable` | Failed closed; nothing recorded. |
| `identity_required` | 401 | JSON-RPC `-32000` | `requires_buyer_review` | No, expired, invalid, or Platform-only credentials for a scope-gated operation; see [Buyer authorization](#buyer-authorization). |

On MCP, **business outcomes** are returned as a tool `result` whose
`structuredContent` is the consultation error response, with `isError: true`.
**Protocol errors** (authentication, idempotency conflict, replay-store failure)
use JSON-RPC error `-32000`, and when MCP runs over HTTP the HTTP status in the
table remains the primary signal.

### REST example: decision POST

The request is shown [above](#decision-admission). The first admission returns
the [approval receipt](#approval-receipt) with `201 Created`. A replay with the
same key and identical bytes returns that same response.

### MCP example

<!-- ucp:example schema=transports/mcp_tool_call def=request direction=request -->
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "decide_order_consultation",
    "arguments": {
      "meta": {
        "ucp-agent": {
          "profile": "https://platform.example/.well-known/ucp"
        },
        "idempotency-key": "b3b8f086-8f4e-41ab-bdc5-3f9156f05f79"
      },
      "order_id": "ord_rental_1",
      "consultation_id": "consult_17",
      "decision": {
        "proposal_revision": 3,
        "decision": "approve",
        "proposal_digest": "sha-256:f82b10ec6e0551e08a93baddb08f920ed58b6fae1189d39ec1e2391ce8fd8900"
      }
    }
  }
}
```

A business outcome returns the error response in `structuredContent`:

<!-- ucp:example schema=shopping/order_consultation def=consultation_error_response extract=$.result.structuredContent -->
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "isError": true,
    "structuredContent": {
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "error",
        "capabilities": {
          "dev.ucp.shopping.order_consultation": [{"version": "{{ ucp_version }}"}]
        }
      },
      "messages": [
        {
          "type": "error",
          "code": "decision_conflict",
          "severity": "unrecoverable",
          "content": "A terminal decision is already recorded for this revision.",
          "data": {"decision_id": "dec_52"}
        }
      ]
    }
  }
}
```

A protocol error for a reused key with a different body (HTTP `409` alongside):

<!-- ucp:example schema=transports/jsonrpc def=error_response -->
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32000,
    "message": "Idempotency-Key reused with a different request body",
    "data": {"code": "idempotency_key_conflict"}
  }
}
```

## Conformance

### Platform

A Platform:

* **MUST** negotiate the extension before relying on it and **MUST NOT**
  assume any behavior from the base Order.
* **MUST** discover actionable consultations through the list operation and
  follow pagination to exhaustion; it **MUST NOT** rely on notifications alone.
* **MUST** decide only against the exact `proposal_revision` the buyer was shown
  and **SHOULD** echo `proposal_digest`.
* **MUST** present a buyer-authenticated identity token carrying
  `dev.ucp.shopping.order_consultation:decide` to record a decision;
  **MUST NOT** rely on Platform credentials or `dev.ucp.shopping.order:manage`,
  and **MUST NOT** infer approval from silence, read access, agent preference,
  or any Action or notification.
* **MUST** treat unrecognized `status`, `decision`, and `change_type` values as
  not actionable, as granting no authority, and as needing buyer review,
  respectively; and unrecognized `application_status` as `indeterminate`.
* **MUST** use a new high-entropy `Idempotency-Key` for each new decision and
  the original key with byte-identical body for every retry.
* **MUST NOT**, after a lost response, retry with a new key, swap the decision,
  or treat provisional absence as proof of non-commitment.
* **MUST NOT** treat a recorded approval as application or as payment
  authorization.

### Business

A Business:

* **MUST** provide the mandatory list operation and the revision, consultation,
  decision-by-id, and decision-by-key reads.
* **MUST** keep revisions immutable, retain historical terms, and carry the
  digest on every receipt.
* **MUST** admit, expire, withdraw, and supersede through a single
  [serialization point](#serialization-point) per consultation, and apply the
  [admission procedure](#admission-procedure) in order.
* **MUST** fail closed, creating no receipt and no replay record, when buyer
  authorization is not established, and evaluate it before any replay.
* **MUST** follow the replay rules, fail closed on replay-store failure, and
  keep the key-to-decision association and receipts durably beyond the replay
  window.
* **MUST NOT** return `final: true` on a lookup without a real no-commit
  guarantee.
* **MUST** re-validate before application, publish `applied_at` and
  `actual_effective_from`, and never reprice earlier accrued usage.
* **MUST NOT** treat the original Checkout, another mandate, or a decision on
  another revision as authority for different terms.

### Conformance vectors

`scripts/test_order_consultation.py` executes these vectors against an
in-memory **reference model** of the rules above and validates every payload it
emits against the schemas. They are **protocol conformance vectors**, not a
proof that any production Business is linearizable: an implementer proves their
own server by running the same scenarios through its API.

| Vector | Covers |
| :----- | :----- |
| CV-01 | Immutable addressable revisions; digest binds terms; history index. |
| CV-02 | Discovery by list with no webhook; read scope; cross-buyer; status filter. |
| CV-03 | Approve vs decline receipts; decline never enters application. |
| CV-04 | Read, `order:manage`, cross-buyer, cross-Order, delegation cap refused; silence. |
| CV-05 | Revision 3 never authorizes revision 4; digest and scope tampering. |
| CV-06 | Deadline instant, expiry at admission, withdrawal and supersession races. |
| CV-07 | Approve/decline and approve/approve races in both admission orders. |
| CV-08 | Same-key replay, raw-byte conflict, platform-scoped keys, fail closed. |
| CV-09 | Lost response: recorded, in-flight, provisional, final; no new-key swap. |
| CV-10 | Pending, failed (`order_changed`), applied; Order linkage. |
| CV-11 | Late application: later-of boundary; prior usage stays at old tariff. |
| CV-12 | Exact-time and application-deadline failures; no retroactive repricing. |
| CV-13 | Payment authority independent of approval. |
| CV-14 | Base Order untouched; no dependency on #943. |
| CV-15 | Unknown lifecycle values fail closed. |
| CV-16 | Capability absent: `capabilities_incompatible`, base Order unchanged, no Platform-side create. |
| CV-17 | Lost approval overlapping expiry, withdrawal, and supersession: in-flight is unresolved, final only after closure, no commit after a final negative; a non-conforming arrival-time Business is detected. |
| CV-18 | All 5040 orderings of approve, decline, withdraw, supersede, time passing, lookup, and same-key retry satisfy the serialization invariants. |
| CV-19 | Buyer authorization matrix: no token, Platform-only, expired, wrong scope, `order:manage`, other buyer, delegation; authentication precedes replay. |
| CV-20 | Canonical digest: RFC 8785 sort order, every single-member change, excluded members, historical reads, second-language cross-check. |
| CV-21 | Complete profiles: Authority Binding, negotiation and pruning, REST and MCP operation resolution via `dev.ucp.shopping`, un-negotiated rejection, scope declaration. |
| CV-22 | Schema composition through `ucp-schema`: enforced when negotiated, not applied when absent. |
| CV-23 | Late application: billed and unbilled usage stays at the old rate, schedule exposed on the Order, scope and terms not changed, new terms need a new proposal. |
| BV | The six operations exist exactly once in the shared REST and OpenRPC descriptors, are capability-gated, and every `$ref` resolves. |

## Backward compatibility

The extension is additive and optional. The base `order.json` is unchanged. A
Business that does not declare it, or a Platform that does not negotiate it,
behaves exactly as before. The only change to a negotiated Order is the
response-only `consultation_applications[]` member (`ucp_request: omit`).

## Security considerations

* **Authority.** Decision authority is a dedicated scope on a
  buyer-authenticated token, plus buyer ownership and delegation checks; never
  Platform identity, read access, `order:manage`, or an Order ID.
* **Digest confusion.** The canonical proposal digest carries a context string
  and is never an HTTP body digest, so one cannot be substituted for the other.
* **Enumeration.** Cross-buyer and cross-Order access returns `not_found`.
* **Replay and tampering.** Idempotency keys are signed when signing is in use;
  the raw-body digest detects altered payloads; the request cannot carry scope.
* **Stale consent.** Revision numbers, the digest, and `baseline_reference`
  together prevent consent for one set of terms being read as consent for
  another.
* **Consent versus execution.** Application and payment are separate facts and
  separate authorities.

## Open decisions

This draft exposes the decisions listed in #944 for review:

1. **Domain-specific Orders extension versus a shared proposal/decision
    primitive.** This draft is an Order extension with illustrative domain
    profiles; it does not generalize.
2. **Namespace.** This draft proposes `dev.ucp.shopping.order_consultation`
    (unapproved, unpublished, served from `ucp.dev` so Authority Binding
    passes). Vendor-first naming under a publisher-owned namespace remains an
    open governance question; the criteria for promotion are a Technical
    Council decision.
3. **Discovery.** This draft mandates the Order-scoped list and defines no Order
    references or Actions. Either may be added later as a pointer, never as the
    sole path.
4. **Identity and delegation evidence** for post-order commercial authorization
    beyond the scope and `decided_by` attribution shown here.
5. **Receipt and application representation**, including whether
    `application` stays inline or becomes a separate resource.
6. **Negative reconciliation.** This draft defines one guarantee,
    `consultation_closed`, and provisional absence otherwise. Other guarantees
    (for example explicit key fencing) are not defined.
7. **Domain `scope` and `proposed_terms` composition.** `if`/`then` on
    `change_type` is used here; a registry or per-domain extension is an
    alternative.
8. **Revision history and receipt retention** minimums.
9. **Error status convention.** Non-2xx on REST for refusals, versus the
    existing Order read's HTTP 200 business outcomes.
10. **Additive request member.** `proposal_digest` is an optional addition to
    the request shape in #944.
11. **Timing rule scope.** The later-of effective boundary is specified only
    for the tariff profile. Whether the common envelope should carry a
    direction-aware default (for example for buyer-favorable changes such as
    discounts) is left to the Technical Council.

## Related

* [Order Capability](../order/index.md)
* [Message Signatures — Replay Protection](../../signatures.md#replay-protection)
* [Identity Linking — Scopes](../../common/identity-linking/index.md#scopes)
