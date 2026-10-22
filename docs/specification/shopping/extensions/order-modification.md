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

# Order Modification Extension (Draft)

!!! warning "Draft - not an approved UCP capability"

    This page is a **Working Draft reference implementation of Enhancement
    Proposal [#943](https://github.com/Universal-Commerce-Protocol/ucp/issues/943)**,
    following the draft-reference approach of PR #930. It has not been accepted
    by the Tech Council and is not requested for merge before the proposal
    reaches Provisional. Normative keywords below describe the *proposed*
    contract.

    **Namespace: `dev.ucp.shopping.order_modification` is a name *proposed to
    the Tech Council*. It is not approved, sanctioned, or published, and nothing
    here implies the `dev.ucp.*` namespace has been granted.** The
    `dev.ucp.*` namespace is reserved for capabilities sanctioned by the UCP
    governing body, and contribution guidance says emerging extensions
    normally start under a publisher-controlled vendor namespace. Whether a
    draft may use the shared name before Provisional, or should move to a
    publisher-owned `com.{publisher}.*` name served from that publisher's own
    domain, is an open Tech Council decision. The schema validates under either
    name provided the schema is served from a host that satisfies authority
    binding.

* **Capability Name:** `dev.ucp.shopping.order_modification`
  (proposed, unapproved; see above)
* **Extends:** [Order Capability](../order/index.md)
  (`dev.ucp.shopping.order`)
* **Maturity:** Draft, breaking changes expected
* **Scope:** `cancel` only. Quantity changes, swaps, exchanges, returns, and
  new payment-capture operations are out of scope.

## Overview

The Order capability exposes authoritative Order state, fulfillment, and
adjustments, but standardizes no Platform-initiated post-purchase operation.
This extension adds an **optional, capability-negotiated, cancellation-first**
contract with six invariants:

1. Modification support is explicitly negotiated.
2. Stable modification units and available operations are declared on Order
   read, together with a version precondition.
3. Structural unavailability is distinguished from Business policy refusal.
4. Atomicity is explicit; `per_unit` attempts return per-unit outcomes.
5. State-changing requests reuse UCP's `Idempotency-Key`; durable attempt
   records support authoritative lost-response reconciliation.
6. Order mutation commitment is distinct from downstream financial
   adjustment finality.

The Business keeps authority over whether a request is accepted and executed.
Submitting a request never authorizes cancellation by itself.

### What is schema, what is spec, what is illustration

| Layer | Where | Status |
| :---- | :---- | :---- |
| **Implemented schema** | `source/schemas/shopping/order_modification.json` | Machine-checked: every example on this page and every fixture is validated |
| **Normative behavior** | This page | Proposed `MUST`/`SHOULD` rules; **not** machine-checkable by schema alone |
| **Binding proposals** | Additive operations in `source/services/shopping/rest.openapi.json` and `mcp.openrpc.json` | The only discovery path existing registry semantics provide; see [Discovery](#discovery) |
| **Illustrative Business processing** | Worked example and sequence tables | Not a merchant server; no endpoint here executes anything |
| **Runtime conformance vectors** | `scripts/fixtures/order_modification/vectors/` | Inputs for a future runtime suite; **none has been executed against an implementation** |

## Discovery

A Business advertises the extension only when it supports it. The base Order
capability and the `dev.ucp.shopping.order:manage` scope alone do **not**
imply that mutation is supported.

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
        },
        {
          "version": "{{ ucp_version }}",
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/overview",
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
      "dev.ucp.shopping.order_modification": [
        {
          "version": "{{ ucp_version }}",
          "extends": [
            "dev.ucp.shopping.order"
          ],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/extensions/order-modification",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/order_modification.json"
        }
      ]
    },
    "payment_handlers": {}
  }
}
```

**How a client finds the operations.** Under existing registry semantics a
capability belongs to the service named by its namespace
(`dev.ucp.shopping.order_modification` belongs to `dev.ucp.shopping`), and a
profile's `services["dev.ucp.shopping"][]` entry for a transport references
the single OpenAPI or OpenRPC descriptor for that service. There is no
mechanism for an extension to attach its own descriptor, and a service key is
a vertical, not a capability. A separate descriptor file under
`source/services/` would therefore be unreachable from any profile.

This draft integrates the smallest compliant way: the four operations are
added, additively, to the existing `dev.ucp.shopping` descriptors, exactly as
Cart and Checkout operations already are even though those capabilities are
optional. Their descriptions state that they apply only when this extension is
negotiated. A client therefore:

1. reads the Business profile and confirms
   `capabilities["dev.ucp.shopping.order_modification"]` is advertised and
   extends an Order capability it also negotiated;
2. takes the `dev.ucp.shopping` service entry for the transport it uses;
3. fetches that entry's `schema` descriptor and finds
   `create_modification`, `get_modification`, `lookup_modification`, and
   `fence_modification`.

If the extension is not advertised, a client **MUST NOT** call these
operations even though the shared descriptor lists them. The fixture test
`test_discovery` performs this resolution from the example profile above for
both transports and checks that a profile without the extension yields no
callable modification operation.

Editing the shared descriptors is a shared-surface change that this draft
makes only because discovery requires it. Whether the Tech Council prefers
this, or a new registry mechanism for extension-declared operations, is an
[open decision](#open-decisions).

### Negotiation

When the extension is **not** negotiated:

* `order_version` and `modification` are absent from Order responses.
* Platforms **MUST NOT** infer programmatic cancellation support, and
  **MUST NOT** call the operations below.
* Existing Order behavior is unchanged.

**Gating is enforced on both sides.** Negotiation succeeds only when the
Platform's profile and the Business's profile both advertise
`dev.ucp.shopping.order_modification` at a common version, and the parent
`dev.ucp.shopping.order` is also negotiated. The `dev.ucp.shopping` service
descriptor lists the four operations for every shopping Business, but listing
is not availability:

* A **Platform** **MUST NOT** expose or invoke `create_modification`,
  `get_modification`, `lookup_modification`, or `fence_modification` unless
  negotiation succeeded for
  the request's Platform and Business profiles.
* A **Business** **MUST** reject any invocation of them on a request where the
  extension was not negotiated, with `modification_not_supported`, and **MUST
  NOT** create a record, claim a key, or fence a key.

When it **is** negotiated, every Order response **MUST** carry `order_version`
and `modification`. This makes three states distinguishable:

| State | `modification` | Meaning |
| :---- | :---- | :---- |
| Not negotiated | absent | No programmatic cancellation support may be inferred |
| Negotiated, Order-only | `granularity: order_only` | Only whole-Order operations |
| Negotiated, by unit | `granularity: by_unit` | Whole-Order and/or unit operations |

## Read-Side Modification Declaration

The authoritative Order read carries a response-only `modification`
declaration and an opaque `order_version`.

{{ extension_schema_fields('order_modification.json#/$defs/modification_declaration', 'shopping/extensions/order-modification') }}

### Whole-Order Cancellation

{{ extension_schema_fields('order_modification.json#/$defs/order_cancellation', 'shopping/extensions/order-modification') }}

### Units

{{ extension_schema_fields('order_modification.json#/$defs/unit', 'shopping/extensions/order-modification') }}

{{ extension_schema_fields('order_modification.json#/$defs/unit_target', 'shopping/extensions/order-modification') }}

Rules:

* `order_cancellation` is declared whether or not whole-Order cancellation is
  available and regardless of `granularity`. If `available` is `true`,
  `processing_mode` **MUST** be declared even when `granularity` is
  `by_unit`.
* `order_cancellation.available` is `true` **if and only if** the Order-level
  `operations` list contains `cancel`. Unit cancellation MAY be available
  while whole-Order cancellation is not (and the reverse).
* A unit is a stable modification **target**, not necessarily a payment
  settlement unit. Its `id` is opaque and **MUST NOT** be interpreted as an
  array index, a line item ID, or a payment identifier. A single pooled
  payment does **not** make line-level cancellation structurally impossible;
  the Business decides actual modifiability.
* `reversible_amount` and `estimated_refund_amount` are non-negative minor
  units of the Order's own `currency`. An omitted `estimated_refund_amount`
  means **unknown**, not zero and not a guarantee. It is distinct from the
  final value in `adjustments[]`.
* `granularity` and `atomicity` are **open vocabularies** with documented
  well-known values, per the Schema Authoring Guide: the sets are plausible to
  grow (for example grouped commitment), and an extension cannot widen a
  closed enum. Safe behavior for unknown values is normative. A Platform that
  does not recognize `granularity` **MUST NOT** address units and **MAY**
  submit only a whole-Order operation when `order_cancellation.available` is
  `true`. A Platform that does not recognize `atomicity` **MUST** submit
  single-operation requests only and **MUST** treat any non-`committed`
  result as unresolved. The same open treatment applies to `processing_mode`:
  an unrecognized value **MUST** be treated as `merchant_review`, never
  `immediate`.

### Examples

**Smallest valid profile**: Order-only, atomic, immediate.

<!-- ucp:example schema=shopping/order_modification def=dev.ucp.shopping.order op=read -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "status": "success",
    "capabilities": {
      "dev.ucp.shopping.order": [
        {
          "version": "{{ ucp_version }}"
        }
      ],
      "dev.ucp.shopping.order_modification": [
        {
          "version": "2026-10-13"
        }
      ]
    }
  },
  "id": "ord_9f2",
  "checkout_id": "chk_7c1",
  "permalink_url": "https://business.example.com/orders/ord_9f2",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": {
        "id": "prod_li_1",
        "title": "Trail Running Shoes",
        "price": 1750
      },
      "quantity": {
        "original": 2,
        "total": 2,
        "fulfilled": 0
      },
      "totals": [
        {
          "type": "subtotal",
          "amount": 3500
        },
        {
          "type": "total",
          "amount": 3500
        }
      ],
      "status": "processing"
    },
    {
      "id": "li_2",
      "item": {
        "id": "prod_li_2",
        "title": "Merino Hiking Socks",
        "price": 2000
      },
      "quantity": {
        "original": 1,
        "total": 1,
        "fulfilled": 0
      },
      "totals": [
        {
          "type": "subtotal",
          "amount": 2000
        },
        {
          "type": "total",
          "amount": 2000
        }
      ],
      "status": "processing"
    }
  ],
  "fulfillment": {
    "expectations": [
      {
        "id": "exp_1",
        "line_items": [
          {
            "id": "li_1",
            "quantity": 2
          }
        ],
        "method_type": "shipping",
        "destination": {
          "street_address": "123 Main St",
          "address_locality": "Austin",
          "address_region": "TX",
          "address_country": "US",
          "postal_code": "78701"
        },
        "description": "Ships to 123 Main St"
      },
      {
        "id": "exp_2",
        "line_items": [
          {
            "id": "li_2",
            "quantity": 1
          }
        ],
        "method_type": "shipping",
        "destination": {
          "street_address": "123 Main St",
          "address_locality": "Austin",
          "address_region": "TX",
          "address_country": "US",
          "postal_code": "78701"
        },
        "description": "Ships to 123 Main St"
      }
    ],
    "events": []
  },
  "adjustments": [],
  "totals": [
    {
      "type": "subtotal",
      "amount": 5500
    },
    {
      "type": "fulfillment",
      "amount": 600
    },
    {
      "type": "total",
      "amount": 6100
    }
  ],
  "order_version": "v14",
  "modification": {
    "granularity": "order_only",
    "atomicity": "atomic",
    "operations": [
      "cancel"
    ],
    "order_cancellation": {
      "available": true,
      "processing_mode": "immediate",
      "reversible_amount": 5500,
      "estimated_refund_amount": 5500
    }
  }
}
```

**By unit, per-unit commitment, mixed processing modes.** Whole-Order
cancellation is merchant-reviewed with an estimate; `unit_goods_1` is
immediate; `unit_goods_2` needs merchant review.

<!-- ucp:example schema=shopping/order_modification def=dev.ucp.shopping.order op=read -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "status": "success",
    "capabilities": {
      "dev.ucp.shopping.order": [
        {
          "version": "{{ ucp_version }}"
        }
      ],
      "dev.ucp.shopping.order_modification": [
        {
          "version": "2026-10-13"
        }
      ]
    }
  },
  "id": "ord_9f2",
  "checkout_id": "chk_7c1",
  "permalink_url": "https://business.example.com/orders/ord_9f2",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": {
        "id": "prod_li_1",
        "title": "Trail Running Shoes",
        "price": 1750
      },
      "quantity": {
        "original": 2,
        "total": 2,
        "fulfilled": 0
      },
      "totals": [
        {
          "type": "subtotal",
          "amount": 3500
        },
        {
          "type": "total",
          "amount": 3500
        }
      ],
      "status": "processing"
    },
    {
      "id": "li_2",
      "item": {
        "id": "prod_li_2",
        "title": "Merino Hiking Socks",
        "price": 2000
      },
      "quantity": {
        "original": 1,
        "total": 1,
        "fulfilled": 0
      },
      "totals": [
        {
          "type": "subtotal",
          "amount": 2000
        },
        {
          "type": "total",
          "amount": 2000
        }
      ],
      "status": "processing"
    }
  ],
  "fulfillment": {
    "expectations": [
      {
        "id": "exp_1",
        "line_items": [
          {
            "id": "li_1",
            "quantity": 2
          }
        ],
        "method_type": "shipping",
        "destination": {
          "street_address": "123 Main St",
          "address_locality": "Austin",
          "address_region": "TX",
          "address_country": "US",
          "postal_code": "78701"
        },
        "description": "Ships to 123 Main St"
      },
      {
        "id": "exp_2",
        "line_items": [
          {
            "id": "li_2",
            "quantity": 1
          }
        ],
        "method_type": "shipping",
        "destination": {
          "street_address": "123 Main St",
          "address_locality": "Austin",
          "address_region": "TX",
          "address_country": "US",
          "postal_code": "78701"
        },
        "description": "Ships to 123 Main St"
      }
    ],
    "events": []
  },
  "adjustments": [],
  "totals": [
    {
      "type": "subtotal",
      "amount": 5500
    },
    {
      "type": "fulfillment",
      "amount": 600
    },
    {
      "type": "total",
      "amount": 6100
    }
  ],
  "order_version": "v14",
  "modification": {
    "granularity": "by_unit",
    "atomicity": "per_unit",
    "operations": [
      "cancel"
    ],
    "order_cancellation": {
      "available": true,
      "processing_mode": "merchant_review",
      "reversible_amount": 5500,
      "estimated_refund_amount": 5100
    },
    "units": [
      {
        "id": "unit_goods_1",
        "targets": [
          {
            "type": "line_item",
            "id": "li_1",
            "quantity": 2
          }
        ],
        "operations": [
          "cancel"
        ],
        "processing_mode": "immediate",
        "reversible_amount": 3500,
        "estimated_refund_amount": 3500
      },
      {
        "id": "unit_goods_2",
        "targets": [
          {
            "type": "line_item",
            "id": "li_2",
            "quantity": 1
          }
        ],
        "operations": [
          "cancel"
        ],
        "processing_mode": "merchant_review",
        "reversible_amount": 2000,
        "estimated_refund_amount": 1900
      }
    ]
  }
}
```

**Whole-Order cancellation unavailable, unit cancellation still offered.**
Part of the Order has shipped. The shipped unit is declared with no
operations and a machine-readable reason, so the Platform does not retry it.

<!-- ucp:example schema=shopping/order_modification def=dev.ucp.shopping.order op=read -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "status": "success",
    "capabilities": {
      "dev.ucp.shopping.order": [
        {
          "version": "{{ ucp_version }}"
        }
      ],
      "dev.ucp.shopping.order_modification": [
        {
          "version": "2026-10-13"
        }
      ]
    }
  },
  "id": "ord_9f2",
  "checkout_id": "chk_7c1",
  "permalink_url": "https://business.example.com/orders/ord_9f2",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": {
        "id": "prod_li_1",
        "title": "Trail Running Shoes",
        "price": 1750
      },
      "quantity": {
        "original": 2,
        "total": 2,
        "fulfilled": 2
      },
      "totals": [
        {
          "type": "subtotal",
          "amount": 3500
        },
        {
          "type": "total",
          "amount": 3500
        }
      ],
      "status": "fulfilled"
    },
    {
      "id": "li_2",
      "item": {
        "id": "prod_li_2",
        "title": "Merino Hiking Socks",
        "price": 2000
      },
      "quantity": {
        "original": 1,
        "total": 1,
        "fulfilled": 0
      },
      "totals": [
        {
          "type": "subtotal",
          "amount": 2000
        },
        {
          "type": "total",
          "amount": 2000
        }
      ],
      "status": "processing"
    }
  ],
  "fulfillment": {
    "expectations": [
      {
        "id": "exp_1",
        "line_items": [
          {
            "id": "li_1",
            "quantity": 2
          }
        ],
        "method_type": "shipping",
        "destination": {
          "street_address": "123 Main St",
          "address_locality": "Austin",
          "address_region": "TX",
          "address_country": "US",
          "postal_code": "78701"
        },
        "description": "Ships to 123 Main St"
      },
      {
        "id": "exp_2",
        "line_items": [
          {
            "id": "li_2",
            "quantity": 1
          }
        ],
        "method_type": "shipping",
        "destination": {
          "street_address": "123 Main St",
          "address_locality": "Austin",
          "address_region": "TX",
          "address_country": "US",
          "postal_code": "78701"
        },
        "description": "Ships to 123 Main St"
      }
    ],
    "events": [
      {
        "id": "evt_1",
        "occurred_at": "2026-10-12T15:04:00Z",
        "type": "shipped",
        "line_items": [
          {
            "id": "li_1",
            "quantity": 2
          }
        ],
        "tracking_number": "1Z999AA10123456784",
        "tracking_url": "https://carrier.example/track/1Z999AA10123456784",
        "description": "Left the warehouse"
      }
    ]
  },
  "adjustments": [],
  "totals": [
    {
      "type": "subtotal",
      "amount": 5500
    },
    {
      "type": "fulfillment",
      "amount": 600
    },
    {
      "type": "total",
      "amount": 6100
    }
  ],
  "order_version": "v14",
  "modification": {
    "granularity": "by_unit",
    "atomicity": "atomic",
    "operations": [],
    "order_cancellation": {
      "available": false,
      "reason_code": "partially_fulfilled"
    },
    "units": [
      {
        "id": "unit_goods_1",
        "targets": [
          {
            "type": "line_item",
            "id": "li_1",
            "quantity": 2
          }
        ],
        "operations": [],
        "reason_code": "already_shipped",
        "reason": "Shipped on 2026-10-12."
      },
      {
        "id": "unit_goods_2",
        "targets": [
          {
            "type": "line_item",
            "id": "li_2",
            "quantity": 1
          }
        ],
        "operations": [
          "cancel"
        ],
        "processing_mode": "merchant_review",
        "reversible_amount": 2000,
        "estimated_refund_amount": 1900
      }
    ]
  }
}
```

**Order-only with cancellation unavailable.** Distinguishable from an Order
that did not negotiate the extension.

<!-- ucp:example schema=shopping/order_modification def=dev.ucp.shopping.order op=read -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "status": "success",
    "capabilities": {
      "dev.ucp.shopping.order": [
        {
          "version": "{{ ucp_version }}"
        }
      ],
      "dev.ucp.shopping.order_modification": [
        {
          "version": "2026-10-13"
        }
      ]
    }
  },
  "id": "ord_9f2",
  "checkout_id": "chk_7c1",
  "permalink_url": "https://business.example.com/orders/ord_9f2",
  "currency": "USD",
  "line_items": [
    {
      "id": "li_1",
      "item": {
        "id": "prod_li_1",
        "title": "Trail Running Shoes",
        "price": 1750
      },
      "quantity": {
        "original": 2,
        "total": 2,
        "fulfilled": 0
      },
      "totals": [
        {
          "type": "subtotal",
          "amount": 3500
        },
        {
          "type": "total",
          "amount": 3500
        }
      ],
      "status": "processing"
    },
    {
      "id": "li_2",
      "item": {
        "id": "prod_li_2",
        "title": "Merino Hiking Socks",
        "price": 2000
      },
      "quantity": {
        "original": 1,
        "total": 1,
        "fulfilled": 0
      },
      "totals": [
        {
          "type": "subtotal",
          "amount": 2000
        },
        {
          "type": "total",
          "amount": 2000
        }
      ],
      "status": "processing"
    }
  ],
  "fulfillment": {
    "expectations": [
      {
        "id": "exp_1",
        "line_items": [
          {
            "id": "li_1",
            "quantity": 2
          }
        ],
        "method_type": "shipping",
        "destination": {
          "street_address": "123 Main St",
          "address_locality": "Austin",
          "address_region": "TX",
          "address_country": "US",
          "postal_code": "78701"
        },
        "description": "Ships to 123 Main St"
      },
      {
        "id": "exp_2",
        "line_items": [
          {
            "id": "li_2",
            "quantity": 1
          }
        ],
        "method_type": "shipping",
        "destination": {
          "street_address": "123 Main St",
          "address_locality": "Austin",
          "address_region": "TX",
          "address_country": "US",
          "postal_code": "78701"
        },
        "description": "Ships to 123 Main St"
      }
    ],
    "events": []
  },
  "adjustments": [],
  "totals": [
    {
      "type": "subtotal",
      "amount": 5500
    },
    {
      "type": "fulfillment",
      "amount": 600
    },
    {
      "type": "total",
      "amount": 6100
    }
  ],
  "order_version": "v14",
  "modification": {
    "granularity": "order_only",
    "atomicity": "atomic",
    "operations": [],
    "order_cancellation": {
      "available": false,
      "reason_code": "cutoff_passed",
      "reason": "Cancellation window closed after fulfillment started."
    }
  }
}
```

## Version Preconditions and Concurrency

**Mechanism (this draft).** Every new request carries `base_order_version`
in the JSON body: the `order_version` against which the declaration was
read. The repository does not expose an HTTP `ETag` on Orders and MCP has no
equivalent of `If-Match`, so the body field is the single normative
mechanism for both transports. It is covered by `Content-Digest` and the
idempotency payload hash. HTTP `ETag`/`If-Match` is **not** used; see
[Open Decisions](#open-decisions).

`order_version` is opaque and compared only for equality. The Business
**MUST** change it whenever any Platform-visible part of the Order changes.

For a **new** request, evaluation order is normative:

1. Authentication and Order-level authorization.
2. Scoped idempotency lookup (see [Idempotency](#idempotency-and-replay)).
   A match is a **replay** and skips steps 3 to 6.
3. `base_order_version` equals the current `order_version`, else
   `stale_order_state`. No record is created and nothing is applied.
4. Request structure (unique targets; no `order` target combined with `unit`
   targets), else `invalid_modification_request`.
5. Unit addressing (`unknown_modification_unit`).
6. Operation support for each target (`operation_not_supported_for_unit`).

An already admitted attempt replays against its original durable record. It
does **not** fail merely because the Order has advanced.

**Admission is not commitment.** For `merchant_review`, admission records the
request only. Before commitment the Business **MUST** revalidate every
affected target against current authoritative Order state. A unit that
shipped, was cancelled, or became ineligible while awaiting review resolves
to `refused` (`reason_code: stale_eligibility`), never to a commit against
stale eligibility.

**Authoritative serial order.** The Business **MUST** serialize Order
mutations, including cancellation commits, in a single total order per
Order, observable as the sequence of `order_version` values. Each commit
revalidates against the state produced by the preceding commit. When two
attempts target the same unit, at most one can commit; the other resolves
`refused` (`conflicting_modification` or `unit_unavailable`). An attempt on a
unit that overlaps a still-pending attempt is admitted and decided at commit
time under this rule.

## Operations

Four operations, bound to REST and MCP below. The REST paths are
`POST /orders/{id}/modifications`,
`GET /orders/{id}/modifications/{modification_id}`,
`GET /orders/{id}/modifications/lookup`, and
`POST /orders/{id}/modifications/fence`. The literals `lookup` and `fence` are
reserved and **MUST NOT** be issued as a `modification_id`.

| Operation | REST | MCP tool | State-changing | Idempotency-Key |
| :---- | :---- | :---- | :---- | :---- |
| Create modification | `POST /orders/{id}/modifications` | `create_modification` | **Yes** | **Required**, signed |
| Get modification | `GET /orders/{id}/modifications/{modification_id}` | `get_modification` | No | Not used |
| Lookup by original key | `GET /orders/{id}/modifications/lookup?operation=cancel` | `lookup_modification` | **No, strictly read-only** | Not used; original key is a lookup argument |
| Fence original key | `POST /orders/{id}/modifications/fence` | `fence_modification` | **Yes**, the only operation that can install a tombstone | **Required**, signed; its own fresh key, distinct from the original key it names |

All MCP tool calls travel as JSON-RPC `POST`. The transport verb does not
make a call state-changing: only `create_modification` and
`fence_modification` carry `meta["idempotency-key"]`; the two reads **MUST NOT**
be treated as idempotent mutations or stored in a replay cache.

**GET is safe.** `GET .../lookup` and `GET .../{modification_id}` are safe
methods (RFC 9110 section 9.2.1): they **MUST NOT** claim a key, install a
tombstone, write a replay record, or otherwise change whether an original
request can later be admitted or commit. Retrying or prefetching them is
harmless. Establishing an authoritative negative is a deliberate,
authenticated, idempotent `POST` (`fence_modification`), never a side effect
of a read.

**No caching.** Every response of these four operations (including 4xx and
5xx) **SHOULD NOT** be reused by a cache: Businesses **MUST** send
`Cache-Control: no-store` on them over HTTP (REST, and MCP over HTTP), because
they carry order state and idempotency-scoped records and a cached or
prefetched negative would be dangerous.

### Create Modification

#### Request

{{ extension_schema_fields('order_modification.json#/$defs/create_request', 'shopping/extensions/order-modification') }}

{{ extension_schema_fields('order_modification.json#/$defs/cancel_operation', 'shopping/extensions/order-modification') }}

{{ extension_schema_fields('order_modification.json#/$defs/target', 'shopping/extensions/order-modification') }}

The same request shape cancels either the whole Order
(`{"type": "order"}`) or declared units. An `order` target **MUST NOT** carry
an `id`; a `unit` target **MUST**. Cancelling a unit cancels the whole
declared quantity of that unit. Targets **MUST** be unique within a request.

#### Response

{{ extension_schema_fields('order_modification.json#/$defs/modification_record', 'shopping/extensions/order-modification') }}

=== "REST request"

    <!-- ucp:example schema=shopping/order_modification def=create_request op=create direction=request -->
    ```json
    POST /orders/ord_9f2/modifications HTTP/1.1
    UCP-Agent: profile="https://platform.example/.well-known/ucp"
    Idempotency-Key: f5d9d412-537c-4f4c-a9da-42a87e766f34
    Content-Type: application/json
    Content-Digest: sha-256=:YlFxWEkDvYYyTPKMFliaQl5MDqCQj1c5jHg7TOLrruo=:
    Signature-Input: sig1=("@method" "@authority" "@path" "ucp-agent" "idempotency-key" "content-digest" "content-type");keyid="platform-2026";created=1760347200
    Signature: sig1=:6G4i8TS6oUkGrx8KnCFUpsSPwd74...:

    {
      "base_order_version": "v14",
      "operations": [
        {
          "op": "cancel",
          "target": {
            "type": "unit",
            "id": "unit_goods_2"
          }
        }
      ]
    }
    ```

=== "REST response (admitted, pending)"

    <!-- ucp:example schema=shopping/order_modification def=create_response op=create -->
    ```json
    HTTP/1.1 201 Created
    Content-Type: application/json
    Cache-Control: no-store
    Location: /orders/ord_9f2/modifications/mod_51a

    {
      "modification_id": "mod_51a",
      "order_id": "ord_9f2",
      "base_order_version": "v14",
      "atomicity": "per_unit",
      "status": "open",
      "results": [
        {
          "target": {
            "type": "unit",
            "id": "unit_goods_2"
          },
          "op": "cancel",
          "outcome": "awaiting_business_decision"
        }
      ],
      "created_at": "2026-10-13T09:15:02Z",
      "updated_at": "2026-10-13T09:15:02Z",
      "retained_until": "2026-11-12T09:15:02Z",
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "success",
        "capabilities": {
          "dev.ucp.shopping.order": [
            {
              "version": "{{ ucp_version }}"
            }
          ],
          "dev.ucp.shopping.order_modification": [
            {
              "version": "2026-10-13"
            }
          ]
        }
      }
    }
    ```

=== "MCP request"

    <!-- ucp:example schema=shopping/order_modification def=create_request op=create direction=request extract=$.params.arguments.modification -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "method": "tools/call",
      "params": {
        "name": "create_modification",
        "arguments": {
          "meta": {
            "ucp-agent": {
              "profile": "https://platform.example/.well-known/ucp"
            },
            "idempotency-key": "f5d9d412-537c-4f4c-a9da-42a87e766f34"
          },
          "id": "ord_9f2",
          "modification": {
                      "base_order_version": "v14",
                      "operations": [
                        {
                          "op": "cancel",
                          "target": {
                            "type": "unit",
                            "id": "unit_goods_2"
                          }
                        }
                      ]
                    }
        }
      }
    }
    ```

=== "MCP response"

    <!-- ucp:example schema=shopping/order_modification def=create_response op=create extract=$.result.structuredContent -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "result": {
        "structuredContent": {
                "modification_id": "mod_51a",
                "order_id": "ord_9f2",
                "base_order_version": "v14",
                "atomicity": "per_unit",
                "status": "open",
                "results": [
                  {
                    "target": {
                      "type": "unit",
                      "id": "unit_goods_2"
                    },
                    "op": "cancel",
                    "outcome": "awaiting_business_decision"
                  }
                ],
                "created_at": "2026-10-13T09:15:02Z",
                "updated_at": "2026-10-13T09:15:02Z",
                "retained_until": "2026-11-12T09:15:02Z",
                "ucp": {
                  "version": "{{ ucp_version }}",
                  "status": "success",
                  "capabilities": {
                    "dev.ucp.shopping.order": [
                      {
                        "version": "{{ ucp_version }}"
                      }
                    ],
                    "dev.ucp.shopping.order_modification": [
                      {
                        "version": "2026-10-13"
                      }
                    ]
                  }
                }
              }
      }
    }
    ```

#### Pre-Admission Errors

When a **new** request is rejected before admission, **no modification record
is created**. Business outcomes return HTTP 200 with the standard UCP error
envelope (the same convention as the Order and Checkout capabilities).
Protocol errors use HTTP status codes.

| Code | Where | Meaning |
| :---- | :---- | :---- |
| `modification_not_supported` | Business outcome | Extension not negotiated or unavailable for this Order |
| `stale_order_state` | Business outcome | `base_order_version` does not match; re-read the Order and form a new request |
| `invalid_modification_request` | Business outcome | Duplicate targets, or `order` combined with `unit` targets (code added by this draft) |
| `unknown_modification_unit` | Business outcome | Referenced unit is not declared for this Order version |
| `operation_not_supported_for_unit` | Business outcome | The declared target does not support the requested operation |
| `unauthorized`, `not_found` | Business outcome | Order-level authorization failed, or no such Order/modification in the caller's scope |
| `fence_not_supported` | Business outcome (`fence_modification` only) | The Business cannot keep a permanent tombstone; nothing was fenced and the Platform stays unresolved (code added by this draft) |
| `idempotency_conflict` | Protocol error, HTTP 409 (MCP: `-32000`) | Key reused with different raw body bytes; nothing executed |
| `insufficient_scope` | Protocol error, HTTP 403 | Credential lacks `dev.ucp.shopping.order:manage` |
| `service_unavailable` | Protocol error, HTTP 503 | Including idempotency storage failure; fail closed, nothing executed |

`refused_by_policy` is **not** a pre-admission error. A structurally
supported operation that Business policy declines is an admitted attempt
whose result is `refused` with `reason_code: refused_by_policy`, so that
replay and reconciliation have a record to return.

=== "stale_order_state"

    <!-- ucp:example schema=common/types/error_response op=read -->
    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json
    Cache-Control: no-store

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "error",
        "capabilities": {
          "dev.ucp.shopping.order_modification": [
            {
              "version": "2026-10-13"
            }
          ]
        }
      },
      "messages": [
        {
          "type": "error",
          "code": "stale_order_state",
          "severity": "recoverable",
          "content": "base_order_version v13 does not match current Order state."
        }
      ]
    }
    ```

=== "unknown_modification_unit"

    <!-- ucp:example schema=common/types/error_response op=read -->
    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json
    Cache-Control: no-store

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "error",
        "capabilities": {
          "dev.ucp.shopping.order_modification": [
            {
              "version": "2026-10-13"
            }
          ]
        }
      },
      "messages": [
        {
          "type": "error",
          "code": "unknown_modification_unit",
          "severity": "unrecoverable",
          "content": "Unit unit_goods_9 is not declared for this Order version."
        }
      ]
    }
    ```

=== "operation_not_supported_for_unit"

    <!-- ucp:example schema=common/types/error_response op=read -->
    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json
    Cache-Control: no-store

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "error",
        "capabilities": {
          "dev.ucp.shopping.order_modification": [
            {
              "version": "2026-10-13"
            }
          ]
        }
      },
      "messages": [
        {
          "type": "error",
          "code": "operation_not_supported_for_unit",
          "severity": "unrecoverable",
          "content": "Unit unit_goods_1 does not currently support cancel."
        }
      ]
    }
    ```

=== "idempotency_conflict (409)"

    <!-- ucp:example skip reason="protocol error body, not a UCP payload" -->
    ```json
    HTTP/1.1 409 Conflict
    Content-Type: application/json

    {
      "code": "idempotency_conflict",
      "content": "Idempotency-Key reused with different request bytes."
    }
    ```

### Get Modification

Returns the authoritative, **current** record of an admitted attempt. A
replayed cached create response is not a substitute for this read.

=== "REST request"

    ```http
    GET /orders/ord_9f2/modifications/mod_51i HTTP/1.1
    UCP-Agent: profile="https://platform.example/.well-known/ucp"
    Accept: application/json
    Signature-Input: sig1=("@method" "@authority" "@path" "ucp-agent");keyid="platform-2026";created=1760347500
    Signature: sig1=:Qk3Zp9xKd0oUq...:
    ```

=== "REST response (indeterminate resolved to committed)"

    <!-- ucp:example schema=shopping/order_modification def=read_response op=read -->
    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json
    Cache-Control: no-store

    {
      "modification_id": "mod_51i",
      "order_id": "ord_9f2",
      "base_order_version": "v14",
      "atomicity": "per_unit",
      "status": "closed",
      "results": [
        {
          "target": {
            "type": "unit",
            "id": "unit_goods_1"
          },
          "op": "cancel",
          "outcome": "committed",
          "affected_amount": 3500,
          "adjustments": [
            "adj_cancel_1"
          ]
        }
      ],
      "created_at": "2026-10-13T09:15:02Z",
      "updated_at": "2026-10-13T09:21:40Z",
      "retained_until": "2026-11-12T09:15:02Z",
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "success",
        "capabilities": {
          "dev.ucp.shopping.order": [
            {
              "version": "{{ ucp_version }}"
            }
          ],
          "dev.ucp.shopping.order_modification": [
            {
              "version": "2026-10-13"
            }
          ]
        }
      }
    }
    ```

=== "MCP response"

    <!-- ucp:example schema=shopping/order_modification def=read_response op=read extract=$.result.structuredContent -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 2,
      "result": {
        "structuredContent": {
                "modification_id": "mod_51a",
                "order_id": "ord_9f2",
                "base_order_version": "v14",
                "atomicity": "per_unit",
                "status": "closed",
                "results": [
                  {
                    "target": {
                      "type": "unit",
                      "id": "unit_goods_2"
                    },
                    "op": "cancel",
                    "outcome": "refused",
                    "reason_code": "stale_eligibility",
                    "reason": "Item shipped while the request awaited review."
                  }
                ],
                "created_at": "2026-10-13T09:15:02Z",
                "updated_at": "2026-10-13T11:02:09Z",
                "retained_until": "2026-11-12T09:15:02Z",
                "ucp": {
                  "version": "{{ ucp_version }}",
                  "status": "success",
                  "capabilities": {
                    "dev.ucp.shopping.order": [
                      {
                        "version": "{{ ucp_version }}"
                      }
                    ],
                    "dev.ucp.shopping.order_modification": [
                      {
                        "version": "2026-10-13"
                      }
                    ]
                  }
                }
              }
      }
    }
    ```

### Lookup by Original Key

Used when the response to `create_modification` never arrived and the
Platform has no `modification_id`. **Strictly read-only**: it answers `found`
or `unresolved` and never changes admission state.

**Scope.** The Business **MUST** resolve the lookup within the tuple
(authenticated Platform identity, Order ID, operation type, original
idempotency key). An unscoped key is never sufficient to read another
Platform's attempt, and a record outside the caller's scope is
indistinguishable from "no record in your scope".

**Key transport.** REST carries the original key in an
`Original-Idempotency-Key` request header rather than the URL, so it is not
written to access logs. The `operation` query parameter and the header are
both covered by the request signature (`@query` and
`original-idempotency-key`). The `Original-Idempotency-Key` header is a
lookup argument and **not** an idempotency key: the Business **MUST NOT**
store a replay record for the lookup or treat it as state-changing. MCP
passes the key as the `original_idempotency_key` tool argument, not in
`meta`.

{{ extension_schema_fields('order_modification.json#/$defs/lookup_response', 'shopping/extensions/order-modification') }}

| `status` | Meaning | Platform behavior |
| :---- | :---- | :---- |
| `found` | `modification` is the attempt's record | Use it; also read the Order |
| `unresolved` | Provisional. The original submission may still be admitted or executing, or the retention lifetime lapsed | Keep the attempt unresolved. Poll, or replay the **original** request (same key, identical bytes), or call [`fence_modification`](#fence-original-key) to obtain an authoritative negative. **Never** create a replacement attempt with a new key on this answer alone |

A lookup can never return an authoritative negative, so an empty lookup
**alone** never authorizes a new-key retry. An unrecognized `status`
(including `not_found`) **MUST** be treated as `unresolved`.

=== "REST request"

    ```http
    GET /orders/ord_9f2/modifications/lookup?operation=cancel HTTP/1.1
    UCP-Agent: profile="https://platform.example/.well-known/ucp"
    Original-Idempotency-Key: f5d9d412-537c-4f4c-a9da-42a87e766f34
    Accept: application/json
    Signature-Input: sig1=("@method" "@authority" "@path" "@query" "ucp-agent" "original-idempotency-key");keyid="platform-2026";created=1760347560
    Signature: sig1=:L0pQz7Yh3nVb...:
    ```

=== "found"

    <!-- ucp:example schema=shopping/order_modification def=lookup_response op=read -->
    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json
    Cache-Control: no-store

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "success",
        "capabilities": {
          "dev.ucp.shopping.order": [
            {
              "version": "{{ ucp_version }}"
            }
          ],
          "dev.ucp.shopping.order_modification": [
            {
              "version": "2026-10-13"
            }
          ]
        }
      },
      "status": "found",
      "modification": {
        "modification_id": "mod_51a",
        "order_id": "ord_9f2",
        "base_order_version": "v14",
        "atomicity": "per_unit",
        "status": "open",
        "results": [
          {
            "target": {
              "type": "unit",
              "id": "unit_goods_2"
            },
            "op": "cancel",
            "outcome": "awaiting_business_decision"
          }
        ],
        "created_at": "2026-10-13T09:15:02Z",
        "updated_at": "2026-10-13T09:15:02Z",
        "retained_until": "2026-11-12T09:15:02Z"
      }
    }
    ```

=== "unresolved (provisional)"

    <!-- ucp:example schema=shopping/order_modification def=lookup_response op=read -->
    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json
    Cache-Control: no-store

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "success",
        "capabilities": {
          "dev.ucp.shopping.order": [
            {
              "version": "{{ ucp_version }}"
            }
          ],
          "dev.ucp.shopping.order_modification": [
            {
              "version": "2026-10-13"
            }
          ]
        }
      },
      "status": "unresolved",
      "reason_code": "admission_in_flight",
      "retry_after": 5
    }
    ```

=== "MCP request"

    <!-- ucp:example skip reason="JSON-RPC transport binding" -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 3,
      "method": "tools/call",
      "params": {
        "name": "lookup_modification",
        "arguments": {
          "meta": {
            "ucp-agent": {
              "profile": "https://platform.example/.well-known/ucp"
            }
          },
          "id": "ord_9f2",
          "operation": "cancel",
          "original_idempotency_key": "f5d9d412-537c-4f4c-a9da-42a87e766f34"
        }
      }
    }
    ```

=== "MCP response"

    <!-- ucp:example schema=shopping/order_modification def=lookup_response op=read extract=$.result.structuredContent -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 3,
      "result": {
        "structuredContent": {
                "ucp": {
                  "version": "{{ ucp_version }}",
                  "status": "success",
                  "capabilities": {
                    "dev.ucp.shopping.order": [
                      {
                        "version": "{{ ucp_version }}"
                      }
                    ],
                    "dev.ucp.shopping.order_modification": [
                      {
                        "version": "2026-10-13"
                      }
                    ]
                  }
                },
                "status": "found",
                "modification": {
                  "modification_id": "mod_51a",
                  "order_id": "ord_9f2",
                  "base_order_version": "v14",
                  "atomicity": "per_unit",
                  "status": "open",
                  "results": [
                    {
                      "target": {
                        "type": "unit",
                        "id": "unit_goods_2"
                      },
                      "op": "cancel",
                      "outcome": "awaiting_business_decision"
                    }
                  ],
                  "created_at": "2026-10-13T09:15:02Z",
                  "updated_at": "2026-10-13T09:15:02Z",
                  "retained_until": "2026-11-12T09:15:02Z"
                }
              }
      }
    }
    ```

### Fence Original Key

The only way to establish that an original request **cannot** commit. It is an
explicit, state-changing, idempotent `POST`, so a retried or prefetched `GET`
can never fence a valid cancellation.

A Platform calls it only after deciding to abandon the original attempt: if the
key is unclaimed the Business installs a **permanent tombstone** and the
original can never commit. The request:

* is authenticated and authorized like `create_modification`
  (`dev.ucp.shopping.order:manage`), signed, and carries a **fresh**
  `Idempotency-Key` of its own, distinct from the original key it names, plus
  `Content-Digest`; retries reuse that key and identical bytes and replay the
  original response;
* names the key to fence in the **body** (`original_idempotency_key`), never
  the URL, so it stays out of access logs, and covers it by `content-digest`.
  MCP passes the same `fence_request` as the `fence` argument with
  `meta["idempotency-key"]`.

The Business performs **one atomic compare-and-set** on the scoped key
(authenticated Platform, Order, operation, original key):

| Key state | Action | `status` | Platform behavior |
| :---- | :---- | :---- | :---- |
| Claimed, record retained | Install nothing | `found` + `modification` | Follow that attempt |
| Claimed, record expired | Install nothing | `unresolved` (`record_expired`) | Stay unresolved |
| Unclaimed | Install permanent tombstone | `fenced`, `key_fenced: true` | Original can never commit; MAY re-read the Order and submit a **new** request with a **new** key |
| Unclaimed, Business cannot keep it permanent | Install nothing | error `fence_not_supported` | Stay unresolved |

{{ extension_schema_fields('order_modification.json#/$defs/fence_request', 'shopping/extensions/order-modification') }}

{{ extension_schema_fields('order_modification.json#/$defs/fence_response', 'shopping/extensions/order-modification') }}

=== "REST request"

    <!-- ucp:example schema=shopping/order_modification def=fence_request op=create direction=request -->
    ```json
    POST /orders/ord_9f2/modifications/fence HTTP/1.1
    UCP-Agent: profile="https://platform.example/.well-known/ucp"
    Idempotency-Key: 3b1e8a54-6c0d-4e0a-9f7a-1d2c5b8e4a77
    Content-Type: application/json
    Content-Digest: sha-256=:mfq3Ued+tfzSwSW9NCjr5uEd401q3m9+E2HaurWwplI=:
    Signature-Input: sig1=("@method" "@authority" "@path" "ucp-agent" "idempotency-key" "content-digest" "content-type");keyid="platform-2026";created=1760347620
    Signature: sig1=:Zp4Qk9d1Vw...:

    {
      "operation": "cancel",
      "original_idempotency_key": "f5d9d412-537c-4f4c-a9da-42a87e766f34"
    }
    ```

=== "fenced"

    <!-- ucp:example schema=shopping/order_modification def=fence_response op=create -->
    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json
    Cache-Control: no-store

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "success",
        "capabilities": {
          "dev.ucp.shopping.order": [
            {
              "version": "{{ ucp_version }}"
            }
          ],
          "dev.ucp.shopping.order_modification": [
            {
              "version": "2026-10-13"
            }
          ]
        }
      },
      "status": "fenced",
      "key_fenced": true
    }
    ```

=== "found (already claimed)"

    <!-- ucp:example schema=shopping/order_modification def=fence_response op=create -->
    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json
    Cache-Control: no-store

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "success",
        "capabilities": {
          "dev.ucp.shopping.order": [
            {
              "version": "{{ ucp_version }}"
            }
          ],
          "dev.ucp.shopping.order_modification": [
            {
              "version": "2026-10-13"
            }
          ]
        }
      },
      "status": "found",
      "modification": {
        "modification_id": "mod_51a",
        "order_id": "ord_9f2",
        "base_order_version": "v14",
        "atomicity": "per_unit",
        "status": "open",
        "results": [
          {
            "target": {
              "type": "unit",
              "id": "unit_goods_2"
            },
            "op": "cancel",
            "outcome": "awaiting_business_decision"
          }
        ],
        "created_at": "2026-10-13T09:15:02Z",
        "updated_at": "2026-10-13T09:15:02Z",
        "retained_until": "2026-11-12T09:15:02Z"
      }
    }
    ```

=== "fence_not_supported"

    <!-- ucp:example schema=common/types/error_response op=read -->
    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json
    Cache-Control: no-store

    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "error",
        "capabilities": {
          "dev.ucp.shopping.order_modification": [
            {
              "version": "2026-10-13"
            }
          ]
        }
      },
      "messages": [
        {
          "type": "error",
          "code": "fence_not_supported",
          "severity": "unrecoverable",
          "content": "This Business cannot guarantee a permanent key tombstone."
        }
      ]
    }
    ```

=== "MCP request"

    <!-- ucp:example schema=shopping/order_modification def=fence_request op=create direction=request extract=$.params.arguments.fence -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 4,
      "method": "tools/call",
      "params": {
        "name": "fence_modification",
        "arguments": {
          "meta": {
            "ucp-agent": {
              "profile": "https://platform.example/.well-known/ucp"
            },
            "idempotency-key": "3b1e8a54-6c0d-4e0a-9f7a-1d2c5b8e4a77"
          },
          "id": "ord_9f2",
          "fence": {
                      "operation": "cancel",
                      "original_idempotency_key": "f5d9d412-537c-4f4c-a9da-42a87e766f34"
                    }
        }
      }
    }
    ```

=== "MCP response"

    <!-- ucp:example schema=shopping/order_modification def=fence_response op=create extract=$.result.structuredContent -->
    ```json
    {
      "jsonrpc": "2.0",
      "id": 4,
      "result": {
        "structuredContent": {
                "ucp": {
                  "version": "{{ ucp_version }}",
                  "status": "success",
                  "capabilities": {
                    "dev.ucp.shopping.order": [
                      {
                        "version": "{{ ucp_version }}"
                      }
                    ],
                    "dev.ucp.shopping.order_modification": [
                      {
                        "version": "2026-10-13"
                      }
                    ]
                  }
                },
                "status": "fenced",
                "key_fenced": true
              }
      }
    }
    ```

## Outcomes

Each requested operation has an authoritative `outcome`.

{{ extension_schema_fields('order_modification.json#/$defs/result', 'shopping/extensions/order-modification') }}

| Outcome | Contract |
| :---- | :---- |
| `awaiting_business_decision` | Admitted; the Business has not decided. **Not** committed, **not** executed |
| `committed` | Authoritative Order mutation committed. A refund may still be pending |
| `refused` | Business declined **before** any mutation (`reason_code` required) |
| `failed` | Execution conclusively did **not** commit (`reason_code` required) |
| `indeterminate` | Whether execution committed cannot yet be established. **MUST NOT** be used merely because merchant approval is pending |
| `not_attempted` | Execution did not start because of the dependency in `blocked_by` (required) |

Unrecognized outcome values **MUST** be treated as unresolved and **never**
as success. Only `committed` reports a mutation.

### State Transitions

| From | To | Trigger |
| :---- | :---- | :---- |
| *(admission)* | `awaiting_business_decision` | `merchant_review` target admitted |
| *(admission)* | `committed` | `immediate` target and the commit succeeded |
| *(admission)* | `refused` | `immediate` target and policy or eligibility declines before mutation |
| *(admission)* | `failed` | Execution conclusively did not commit |
| *(admission)* | `indeterminate` | Commit outcome unknown (timeout, partitioned backend) |
| *(admission)* | `not_attempted` | Blocked by an identified dependency (for example an atomic sibling) |
| `awaiting_business_decision` | `committed` | Approved, revalidated at commit time, commit succeeded |
| `awaiting_business_decision` | `refused` | Declined, or revalidation found the target ineligible |
| `awaiting_business_decision` | `failed` / `indeterminate` | Approved but execution failed or is unknown |
| `awaiting_business_decision` | `not_attempted` | Atomic sibling refused, so this operation was never executed |
| `indeterminate` | `committed` / `failed` | Authoritative reconciliation. **No other transition is allowed** |
| `committed`, `refused`, `failed`, `not_attempted` | *(terminal)* | None. A new attempt needs a new request and a new key |

**Request-level `status`** is derived from `results`: `open` while any result
is `awaiting_business_decision`, `indeterminate`, or unrecognized; `closed`
once every result is terminal. A `status` the Platform does not recognize is
treated as `open`. Only `indeterminate` can be resolved by recovery; recovery
is `get_modification` and `get_order`, never a new attempt.

### Atomicity

* **`atomic`**: the operations of one attempt commit as one all-or-nothing
  Order mutation. The Business **MUST NOT** report one operation `committed`
  alongside any non-`committed` result of the same attempt. The Business
  **MUST** first resolve every required decision, then commit the whole
  mutation or resolve the attempt without changing the Order. **A pending
  merchant decision is not a partial atomic commitment**: while any
  operation awaits review, none commits, including an `immediate`-eligible
  one. Siblings of a refused operation resolve `not_attempted` with
  `blocked_by.reason_code: atomic_group_not_committable`.
* **`per_unit`**: independently declared units commit and fail independently.
  Each requested unit gets its own result, unrelated eligible operations
  **SHOULD** be evaluated independently, and one failed unit **MUST NOT** be
  silently turned into request-wide success.

Atomicity governs **Order mutation commitment, not downstream financial
settlement**. The Business **MUST NOT** modify unrelated units or retained
fulfillment components without an explicitly declared consequence.

=== "Atomic, review pending: nothing committed"

    <!-- ucp:example schema=shopping/order_modification def=create_response op=create -->
    ```json
    HTTP/1.1 201 Created
    Content-Type: application/json
    Cache-Control: no-store

    {
      "modification_id": "mod_51f",
      "order_id": "ord_9f2",
      "base_order_version": "v14",
      "atomicity": "atomic",
      "status": "open",
      "results": [
        {
          "target": {
            "type": "unit",
            "id": "unit_goods_1"
          },
          "op": "cancel",
          "outcome": "awaiting_business_decision"
        },
        {
          "target": {
            "type": "unit",
            "id": "unit_goods_2"
          },
          "op": "cancel",
          "outcome": "awaiting_business_decision"
        }
      ],
      "created_at": "2026-10-13T09:15:02Z",
      "updated_at": "2026-10-13T09:15:02Z",
      "retained_until": "2026-11-12T09:15:02Z",
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "success",
        "capabilities": {
          "dev.ucp.shopping.order": [
            {
              "version": "{{ ucp_version }}"
            }
          ],
          "dev.ucp.shopping.order_modification": [
            {
              "version": "2026-10-13"
            }
          ]
        }
      }
    }
    ```

=== "Atomic, resolved without partial change"

    <!-- ucp:example schema=shopping/order_modification def=create_response op=create -->
    ```json
    HTTP/1.1 201 Created
    Content-Type: application/json
    Cache-Control: no-store

    {
      "modification_id": "mod_51h",
      "order_id": "ord_9f2",
      "base_order_version": "v14",
      "atomicity": "atomic",
      "status": "closed",
      "results": [
        {
          "target": {
            "type": "unit",
            "id": "unit_goods_1"
          },
          "op": "cancel",
          "outcome": "not_attempted",
          "blocked_by": {
            "type": "operation",
            "target": {
              "type": "unit",
              "id": "unit_goods_2"
            },
            "reason_code": "atomic_group_not_committable"
          }
        },
        {
          "target": {
            "type": "unit",
            "id": "unit_goods_2"
          },
          "op": "cancel",
          "outcome": "refused",
          "reason_code": "stale_eligibility"
        }
      ],
      "created_at": "2026-10-13T09:15:02Z",
      "updated_at": "2026-10-13T09:15:02Z",
      "retained_until": "2026-11-12T09:15:02Z",
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "success",
        "capabilities": {
          "dev.ucp.shopping.order": [
            {
              "version": "{{ ucp_version }}"
            }
          ],
          "dev.ucp.shopping.order_modification": [
            {
              "version": "2026-10-13"
            }
          ]
        }
      }
    }
    ```

=== "per_unit: committed, refused, indeterminate, not_attempted"

    <!-- ucp:example schema=shopping/order_modification def=create_response op=create -->
    ```json
    HTTP/1.1 201 Created
    Content-Type: application/json
    Cache-Control: no-store

    {
      "modification_id": "mod_51d",
      "order_id": "ord_9f2",
      "base_order_version": "v14",
      "atomicity": "per_unit",
      "status": "open",
      "results": [
        {
          "target": {
            "type": "unit",
            "id": "unit_goods_1"
          },
          "op": "cancel",
          "outcome": "committed",
          "affected_amount": 3500,
          "adjustments": [
            "adj_cancel_1"
          ]
        },
        {
          "target": {
            "type": "unit",
            "id": "unit_goods_2"
          },
          "op": "cancel",
          "outcome": "refused",
          "reason_code": "stale_eligibility",
          "reason": "Item shipped while the request was in review."
        },
        {
          "target": {
            "type": "unit",
            "id": "unit_goods_3"
          },
          "op": "cancel",
          "outcome": "indeterminate"
        },
        {
          "target": {
            "type": "unit",
            "id": "unit_goods_4"
          },
          "op": "cancel",
          "outcome": "not_attempted",
          "blocked_by": {
            "type": "operation",
            "target": {
              "type": "unit",
              "id": "unit_goods_3"
            },
            "reason_code": "predecessor_indeterminate",
            "reason": "Bundle component must resolve first."
          }
        }
      ],
      "created_at": "2026-10-13T09:15:02Z",
      "updated_at": "2026-10-13T09:15:02Z",
      "retained_until": "2026-11-12T09:15:02Z",
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "success",
        "capabilities": {
          "dev.ucp.shopping.order": [
            {
              "version": "{{ ucp_version }}"
            }
          ],
          "dev.ucp.shopping.order_modification": [
            {
              "version": "2026-10-13"
            }
          ]
        }
      }
    }
    ```

=== "Refused (policy)"

    <!-- ucp:example schema=shopping/order_modification def=create_response op=create -->
    ```json
    HTTP/1.1 201 Created
    Content-Type: application/json
    Cache-Control: no-store

    {
      "modification_id": "mod_51c",
      "order_id": "ord_9f2",
      "base_order_version": "v14",
      "atomicity": "per_unit",
      "status": "closed",
      "results": [
        {
          "target": {
            "type": "unit",
            "id": "unit_goods_2"
          },
          "op": "cancel",
          "outcome": "refused",
          "reason_code": "refused_by_policy",
          "reason": "Item is personalized."
        }
      ],
      "created_at": "2026-10-13T09:15:02Z",
      "updated_at": "2026-10-13T09:15:02Z",
      "retained_until": "2026-11-12T09:15:02Z",
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "success",
        "capabilities": {
          "dev.ucp.shopping.order": [
            {
              "version": "{{ ucp_version }}"
            }
          ],
          "dev.ucp.shopping.order_modification": [
            {
              "version": "2026-10-13"
            }
          ]
        }
      }
    }
    ```

=== "Refused (shipped during review)"

    <!-- ucp:example schema=shopping/order_modification def=read_response op=read -->
    ```json
    HTTP/1.1 200 OK
    Content-Type: application/json
    Cache-Control: no-store

    {
      "modification_id": "mod_51a",
      "order_id": "ord_9f2",
      "base_order_version": "v14",
      "atomicity": "per_unit",
      "status": "closed",
      "results": [
        {
          "target": {
            "type": "unit",
            "id": "unit_goods_2"
          },
          "op": "cancel",
          "outcome": "refused",
          "reason_code": "stale_eligibility",
          "reason": "Item shipped while the request awaited review."
        }
      ],
      "created_at": "2026-10-13T09:15:02Z",
      "updated_at": "2026-10-13T11:02:09Z",
      "retained_until": "2026-11-12T09:15:02Z",
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "success",
        "capabilities": {
          "dev.ucp.shopping.order": [
            {
              "version": "{{ ucp_version }}"
            }
          ],
          "dev.ucp.shopping.order_modification": [
            {
              "version": "2026-10-13"
            }
          ]
        }
      }
    }
    ```

## Idempotency and Replay

`create_modification` **MUST** use UCP's existing
[`Idempotency-Key`](../../signatures.md) rules, which this extension does not
change:

* Keys carry at least 128 bits of entropy (for example UUIDv4); generate a
  new key for each new state-changing request.
* A retry **MUST** reuse the original key and **byte-identical** request body.
  Matching is the SHA-256 of the raw body bytes (the `Content-Digest`
  value), **not** parsed-JSON equality: reordering members under the same key
  is a mismatch.
* Same scope + same key + identical bytes: the Business returns the original
  response **without re-execution**, even if the Order has advanced.
* Same key + different bytes: reject with `409 Conflict` (MCP `-32000`),
  `idempotency_conflict`; nothing executes.
* If the replay store cannot be read or written, **fail closed** with
  `503`: nothing is admitted or executed.
* The key is part of the signed payload (`idempotency-key` and
  `content-digest` are signature components).

### Two retention contracts

These are separate and **MUST NOT** be conflated.

| Contract | Source | Minimum | What it protects |
| :---- | :---- | :---- | :---- |
| Replay cache | Existing UCP signatures spec | 24 hours (48 recommended) | Same-key retry returns the cached response |
| Modification record and scoped-key association | This extension, published as `retained_until` | At least 24 hours after `created_at`; Business-published and MAY be longer | `get_modification` and `lookup_modification` |
| Key tombstone and claim marker | This extension (`key_fenced`) | **Permanent** for as long as the Order can accept modifications; independent of the two lifetimes above | A `fenced` result |

Consistency rule: within `retained_until` a scoped lookup **MUST** return
`found` for that attempt. After it the Business **MUST** answer
`unresolved` with `reason_code: record_expired` (lookup and fence), and **MUST NOT** answer
`not_found`, and **MUST NOT** fence a key it claimed. A record that disappeared is never
evidence of non-commitment.

A cached replayed response is a *historical* copy. The modification record is
the *current* truth. After the replay guarantee lapses, replay **MUST NOT**
be assumed safe merely because 24 hours have elapsed.

### Lost-response recovery

A failed or missing transport response is **not** proof that cancellation
failed.

1. If the Platform has `modification_id`, call `get_modification`.
2. Otherwise call the read-only scoped lookup with the original key. It may
   repeat freely.
3. If it stays `unresolved`, either replay the original request (same key,
   identical bytes), or decide to abandon it and call `fence_modification`.
4. In every case then call `get_order` for current Order and adjustment state.

To make steps 2 and 3 trustworthy the Business **MUST** implement
**claim-then-execute**: admission durably claims the scoped key
(`platform, order, operation, key` to `modification_id`) in the same
transaction that records the attempt, before any commit, so a lookup either
finds the claim or finds nothing because nothing was claimed. The claim marker
is permanent (it outlives `retained_until`), so a claimed key is never fenced
and the fence operation can distinguish claimed from unclaimed forever.

> **Proposed extension behavior.** The claim-marker and tombstone guarantee
> below is stronger than UCP's existing idempotency requirement (24-hour
> minimum replay retention) and is proposed here, not already required. Its
> retention and operational cost are subject to Technical Council review.

#### Fence semantics (`key_fenced`)

`key_fenced: true` is an enforceable statement, not a hint:

* The claim and the fence are **mutually exclusive atomic writes** on the
  same scoped key (compare-and-set). Whichever lands first wins. A fence that
  loses to a claim returns `found` and installs nothing; an admission that
  loses to a fence fails its claim.
* **Only `fence_modification` can fence.** A read-only lookup, a `GET` of a
  modification, a retried or prefetched request, and an unrelated operation
  **MUST NOT** install or imply a tombstone.
* From the instant of fencing, for as long as the Order can accept modifications, the Business
  **MUST** reject every submission under that scoped key without executing it
  and without creating a modification record, including a request already in
  flight when the fence was written and one that arrives after
  `retained_until` or the replay-cache window has passed.
* **The fence is permanent, not a timer.** A temporary fence cannot support an
  authoritative non-commit: once it lapses, a delayed original could be
  admitted, possibly after the Platform submitted a replacement under a new
  key, and the original would then act on a unit the Platform believed it had
  re-requested. A Business that cannot keep the tombstone for the life of the
  Order **MUST NOT** fence; it rejects the operation with
  `fence_not_supported` and the Platform stays unresolved. The
  tombstone is a small key record and does not require retaining the
  modification record.
* Defense in depth, not a substitute: commit-time revalidation and the
  per-Order commit order still ensure two attempts on one unit cannot both
  commit, and a replacement that commits advances `order_version`, so the
  original's stale `base_order_version` would also be rejected. These do
  not make the tombstone optional, because an uncommitted replacement leaves
  the version unchanged.
* A fence is scoped to (authenticated Platform, Order, operation, key); a
  Platform cannot fence or observe another Platform's key.

#### Authoritative non-commitment

A Platform may treat an attempt as definitely not committed only in these
cases, and in each the Business **MUST** guarantee the original operation can
never subsequently commit:

| Evidence | Why it is final |
| :---- | :---- |
| Result `refused`, `failed`, or `not_attempted` | Terminal results are immutable; the Business **MUST NOT** later move them to `committed` |
| `fence_modification` returning `fenced` | The permanent tombstone blocks any claim at any later time, so no execution can start |

Everything else is unresolved: `awaiting_business_decision`, `indeterminate`,
`unresolved` lookups, and an expired record. A same-key
replay is always safe because a matching key and identical bytes return the
original attempt and never create a second one.

A Platform that cannot obtain an authoritative outcome or a `fenced`
response **MUST** keep
the attempt unresolved, **MUST NOT** create a replacement attempt with a new
key, and **SHOULD** hand the buyer to `permalink_url`.

## Order Record and Financial Separation

Three facts are distinct and **MUST NOT** be collapsed:

| Fact | Where it is authoritative | Example |
| :---- | :---- | :---- |
| Cancellation **requested** | Modification record, `awaiting_business_decision` | `mod_51a` admitted for review |
| Cancellation **committed** | Modification record `committed` and the Order's line quantities | `li_2` `quantity.total: 0` |
| Refund **completed** | Order `adjustments[]` entry `status: completed` | `adj_refund_2` |

A committed cancellation updates the authoritative Order consistently with
the existing line item contract:

* **History is preserved.** Line items that ever appeared stay present. A
  fully cancelled, unfulfilled line reaches `quantity.total: 0` and derives
  `status: "removed"`; it is **not** deleted, and `quantity.original` is
  unchanged.
* **Unaffected state is untouched.** Fulfilled quantities, fulfillment events,
  and unrelated lines remain as they were.
* **Financial effects use existing `adjustments[]`.** The signed total
  of a refund lives in the adjustment's `totals`. `affected_amount` is a
  non-negative attribution to the target and **MUST NOT** be treated as that
  signed amount, nor as proof a refund completed. This extension defines no
  settlement, refund, or webhook envelope.
* `order_version` changes on commit.

An agent may say "Cancellation committed; refund pending." It **MUST NOT**
say "Refund completed" because cancellation committed. The final refund MAY
differ from `estimated_refund_amount`.

=== "Before (v14)"

    <!-- ucp:example schema=shopping/order_modification def=dev.ucp.shopping.order op=read -->
    ```json
    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "success",
        "capabilities": {
          "dev.ucp.shopping.order": [
            {
              "version": "{{ ucp_version }}"
            }
          ],
          "dev.ucp.shopping.order_modification": [
            {
              "version": "2026-10-13"
            }
          ]
        }
      },
      "id": "ord_9f2",
      "checkout_id": "chk_7c1",
      "permalink_url": "https://business.example.com/orders/ord_9f2",
      "currency": "USD",
      "line_items": [
        {
          "id": "li_1",
          "item": {
            "id": "prod_li_1",
            "title": "Trail Running Shoes",
            "price": 1750
          },
          "quantity": {
            "original": 2,
            "total": 2,
            "fulfilled": 2
          },
          "totals": [
            {
              "type": "subtotal",
              "amount": 3500
            },
            {
              "type": "total",
              "amount": 3500
            }
          ],
          "status": "fulfilled"
        },
        {
          "id": "li_2",
          "item": {
            "id": "prod_li_2",
            "title": "Merino Hiking Socks",
            "price": 2000
          },
          "quantity": {
            "original": 1,
            "total": 1,
            "fulfilled": 0
          },
          "totals": [
            {
              "type": "subtotal",
              "amount": 2000
            },
            {
              "type": "total",
              "amount": 2000
            }
          ],
          "status": "processing"
        }
      ],
      "fulfillment": {
        "expectations": [
          {
            "id": "exp_1",
            "line_items": [
              {
                "id": "li_1",
                "quantity": 2
              }
            ],
            "method_type": "shipping",
            "destination": {
              "street_address": "123 Main St",
              "address_locality": "Austin",
              "address_region": "TX",
              "address_country": "US",
              "postal_code": "78701"
            },
            "description": "Ships to 123 Main St"
          },
          {
            "id": "exp_2",
            "line_items": [
              {
                "id": "li_2",
                "quantity": 1
              }
            ],
            "method_type": "shipping",
            "destination": {
              "street_address": "123 Main St",
              "address_locality": "Austin",
              "address_region": "TX",
              "address_country": "US",
              "postal_code": "78701"
            },
            "description": "Ships to 123 Main St"
          }
        ],
        "events": [
          {
            "id": "evt_1",
            "occurred_at": "2026-10-12T15:04:00Z",
            "type": "shipped",
            "line_items": [
              {
                "id": "li_1",
                "quantity": 2
              }
            ],
            "tracking_number": "1Z999AA10123456784",
            "tracking_url": "https://carrier.example/track/1Z999AA10123456784",
            "description": "Left the warehouse"
          }
        ]
      },
      "adjustments": [],
      "totals": [
        {
          "type": "subtotal",
          "amount": 5500
        },
        {
          "type": "fulfillment",
          "amount": 600
        },
        {
          "type": "total",
          "amount": 6100
        }
      ],
      "order_version": "v14",
      "modification": {
        "granularity": "by_unit",
        "atomicity": "atomic",
        "operations": [],
        "order_cancellation": {
          "available": false,
          "reason_code": "partially_fulfilled"
        },
        "units": [
          {
            "id": "unit_goods_1",
            "targets": [
              {
                "type": "line_item",
                "id": "li_1",
                "quantity": 2
              }
            ],
            "operations": [],
            "reason_code": "already_shipped",
            "reason": "Shipped on 2026-10-12."
          },
          {
            "id": "unit_goods_2",
            "targets": [
              {
                "type": "line_item",
                "id": "li_2",
                "quantity": 1
              }
            ],
            "operations": [
              "cancel"
            ],
            "processing_mode": "merchant_review",
            "reversible_amount": 2000,
            "estimated_refund_amount": 1900
          }
        ]
      }
    }
    ```

=== "After commit, refund pending (v15)"

    <!-- ucp:example schema=shopping/order_modification def=dev.ucp.shopping.order op=read -->
    ```json
    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "success",
        "capabilities": {
          "dev.ucp.shopping.order": [
            {
              "version": "{{ ucp_version }}"
            }
          ],
          "dev.ucp.shopping.order_modification": [
            {
              "version": "2026-10-13"
            }
          ]
        }
      },
      "id": "ord_9f2",
      "checkout_id": "chk_7c1",
      "permalink_url": "https://business.example.com/orders/ord_9f2",
      "currency": "USD",
      "line_items": [
        {
          "id": "li_1",
          "item": {
            "id": "prod_li_1",
            "title": "Trail Running Shoes",
            "price": 1750
          },
          "quantity": {
            "original": 2,
            "total": 2,
            "fulfilled": 2
          },
          "totals": [
            {
              "type": "subtotal",
              "amount": 3500
            },
            {
              "type": "total",
              "amount": 3500
            }
          ],
          "status": "fulfilled"
        },
        {
          "id": "li_2",
          "item": {
            "id": "prod_li_2",
            "title": "Merino Hiking Socks",
            "price": 2000
          },
          "quantity": {
            "original": 1,
            "total": 0,
            "fulfilled": 0
          },
          "totals": [
            {
              "type": "subtotal",
              "amount": 0
            },
            {
              "type": "total",
              "amount": 0
            }
          ],
          "status": "removed"
        }
      ],
      "fulfillment": {
        "expectations": [
          {
            "id": "exp_1",
            "line_items": [
              {
                "id": "li_1",
                "quantity": 2
              }
            ],
            "method_type": "shipping",
            "destination": {
              "street_address": "123 Main St",
              "address_locality": "Austin",
              "address_region": "TX",
              "address_country": "US",
              "postal_code": "78701"
            },
            "description": "Ships to 123 Main St"
          },
          {
            "id": "exp_2",
            "line_items": [
              {
                "id": "li_2",
                "quantity": 1
              }
            ],
            "method_type": "shipping",
            "destination": {
              "street_address": "123 Main St",
              "address_locality": "Austin",
              "address_region": "TX",
              "address_country": "US",
              "postal_code": "78701"
            },
            "description": "Ships to 123 Main St"
          }
        ],
        "events": [
          {
            "id": "evt_1",
            "occurred_at": "2026-10-12T15:04:00Z",
            "type": "shipped",
            "line_items": [
              {
                "id": "li_1",
                "quantity": 2
              }
            ],
            "tracking_number": "1Z999AA10123456784",
            "tracking_url": "https://carrier.example/track/1Z999AA10123456784",
            "description": "Left the warehouse"
          }
        ]
      },
      "adjustments": [
        {
          "id": "adj_cancel_2",
          "type": "cancellation",
          "occurred_at": "2026-10-13T09:40:00Z",
          "status": "completed",
          "line_items": [
            {
              "id": "li_2",
              "quantity": -1
            }
          ],
          "description": "Cancellation committed for unit_goods_2."
        },
        {
          "id": "adj_refund_2",
          "type": "refund",
          "occurred_at": "2026-10-13T09:40:00Z",
          "status": "pending",
          "line_items": [
            {
              "id": "li_2",
              "quantity": -1
            }
          ],
          "totals": [
            {
              "type": "total",
              "amount": -1900
            }
          ],
          "description": "Refund for cancelled item."
        }
      ],
      "totals": [
        {
          "type": "subtotal",
          "amount": 3500
        },
        {
          "type": "fulfillment",
          "amount": 600
        },
        {
          "type": "total",
          "amount": 4100
        }
      ],
      "order_version": "v15",
      "modification": {
        "granularity": "by_unit",
        "atomicity": "atomic",
        "operations": [],
        "order_cancellation": {
          "available": false,
          "reason_code": "partially_fulfilled"
        },
        "units": [
          {
            "id": "unit_goods_1",
            "targets": [
              {
                "type": "line_item",
                "id": "li_1",
                "quantity": 2
              }
            ],
            "operations": [],
            "reason_code": "already_shipped",
            "reason": "Shipped on 2026-10-12."
          },
          {
            "id": "unit_goods_2",
            "targets": [
              {
                "type": "line_item",
                "id": "li_2",
                "quantity": 1
              }
            ],
            "operations": [],
            "reversible_amount": 0,
            "estimated_refund_amount": 1900,
            "reason_code": "already_canceled"
          }
        ]
      }
    }
    ```

=== "Refund completed, differs from estimate (v16)"

    <!-- ucp:example schema=shopping/order_modification def=dev.ucp.shopping.order op=read -->
    ```json
    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "status": "success",
        "capabilities": {
          "dev.ucp.shopping.order": [
            {
              "version": "{{ ucp_version }}"
            }
          ],
          "dev.ucp.shopping.order_modification": [
            {
              "version": "2026-10-13"
            }
          ]
        }
      },
      "id": "ord_9f2",
      "checkout_id": "chk_7c1",
      "permalink_url": "https://business.example.com/orders/ord_9f2",
      "currency": "USD",
      "line_items": [
        {
          "id": "li_1",
          "item": {
            "id": "prod_li_1",
            "title": "Trail Running Shoes",
            "price": 1750
          },
          "quantity": {
            "original": 2,
            "total": 2,
            "fulfilled": 2
          },
          "totals": [
            {
              "type": "subtotal",
              "amount": 3500
            },
            {
              "type": "total",
              "amount": 3500
            }
          ],
          "status": "fulfilled"
        },
        {
          "id": "li_2",
          "item": {
            "id": "prod_li_2",
            "title": "Merino Hiking Socks",
            "price": 2000
          },
          "quantity": {
            "original": 1,
            "total": 0,
            "fulfilled": 0
          },
          "totals": [
            {
              "type": "subtotal",
              "amount": 0
            },
            {
              "type": "total",
              "amount": 0
            }
          ],
          "status": "removed"
        }
      ],
      "fulfillment": {
        "expectations": [
          {
            "id": "exp_1",
            "line_items": [
              {
                "id": "li_1",
                "quantity": 2
              }
            ],
            "method_type": "shipping",
            "destination": {
              "street_address": "123 Main St",
              "address_locality": "Austin",
              "address_region": "TX",
              "address_country": "US",
              "postal_code": "78701"
            },
            "description": "Ships to 123 Main St"
          },
          {
            "id": "exp_2",
            "line_items": [
              {
                "id": "li_2",
                "quantity": 1
              }
            ],
            "method_type": "shipping",
            "destination": {
              "street_address": "123 Main St",
              "address_locality": "Austin",
              "address_region": "TX",
              "address_country": "US",
              "postal_code": "78701"
            },
            "description": "Ships to 123 Main St"
          }
        ],
        "events": [
          {
            "id": "evt_1",
            "occurred_at": "2026-10-12T15:04:00Z",
            "type": "shipped",
            "line_items": [
              {
                "id": "li_1",
                "quantity": 2
              }
            ],
            "tracking_number": "1Z999AA10123456784",
            "tracking_url": "https://carrier.example/track/1Z999AA10123456784",
            "description": "Left the warehouse"
          }
        ]
      },
      "adjustments": [
        {
          "id": "adj_cancel_2",
          "type": "cancellation",
          "occurred_at": "2026-10-13T09:40:00Z",
          "status": "completed",
          "line_items": [
            {
              "id": "li_2",
              "quantity": -1
            }
          ],
          "description": "Cancellation committed for unit_goods_2."
        },
        {
          "id": "adj_refund_2",
          "type": "refund",
          "occurred_at": "2026-10-14T08:02:11Z",
          "status": "completed",
          "line_items": [
            {
              "id": "li_2",
              "quantity": -1
            }
          ],
          "totals": [
            {
              "type": "total",
              "amount": -1850
            }
          ],
          "description": "Refund for cancelled item."
        }
      ],
      "totals": [
        {
          "type": "subtotal",
          "amount": 3500
        },
        {
          "type": "fulfillment",
          "amount": 600
        },
        {
          "type": "total",
          "amount": 4100
        }
      ],
      "order_version": "v16",
      "modification": {
        "granularity": "by_unit",
        "atomicity": "atomic",
        "operations": [],
        "order_cancellation": {
          "available": false,
          "reason_code": "partially_fulfilled"
        },
        "units": [
          {
            "id": "unit_goods_1",
            "targets": [
              {
                "type": "line_item",
                "id": "li_1",
                "quantity": 2
              }
            ],
            "operations": [],
            "reason_code": "already_shipped",
            "reason": "Shipped on 2026-10-12."
          },
          {
            "id": "unit_goods_2",
            "targets": [
              {
                "type": "line_item",
                "id": "li_2",
                "quantity": 1
              }
            ],
            "operations": [],
            "reversible_amount": 0,
            "estimated_refund_amount": 1900,
            "reason_code": "already_canceled"
          }
        ]
      }
    }
    ```

## Authorization and Notifications

* Mutation and the two reads require an authenticated, authorized Platform.
  `dev.ucp.shopping.order:manage` is the proposed authorization basis.
  Possession of an Order ID is **not** authority; the Business verifies the
  Platform created the checkout that produced the Order, as for `get_order`.
* A cross-buyer or cross-Platform lookup or fence is denied (`unauthorized`) or finds
  nothing in the caller's scope; it never discloses another party's attempt.
* The extension introduces **no new webhook envelope**. Businesses **SHOULD**
  signal changes through existing Order update notifications. The modification
  record is authoritative for attempt-level status and the Order read for
  current Order and adjustment state; a notification is a hint to read them.

## Worked Example

A Platform cancels `unit_goods_2` (merchant review), loses a response, and
reconciles. Keys and IDs are from the fixtures.

| # | Actor | Step | Result |
| :---- | :---- | :---- | :---- |
| 1 | Platform | `GET /orders/ord_9f2`: sees `order_version: v14`, `unit_goods_2` `merchant_review` | Declaration read |
| 2 | Platform | `POST .../modifications`, key `f5d9d412-...`, `base_order_version: v14` | Sent |
| 3 | Business | Claims scoped key, admits `mod_51a`, replies `201` | Response **lost** |
| 4 | Platform | Retries `POST` with the **same key and identical bytes** | `201`, original `awaiting_business_decision` replayed, no second attempt |
| 5 | Platform | Alternatively read-only `GET .../lookup?operation=cancel` with `Original-Idempotency-Key` | `status: found` |
| 6 | Business | Review approves; revalidates `unit_goods_2` at `v14` state; commits | `mod_51a` `committed`; Order `v15`; `li_2` `removed`; refund adjustment `pending` |
| 7 | Platform | `GET .../modifications/mod_51a` and `GET /orders/ord_9f2` | "Cancellation committed; refund pending" |
| 8 | Business | Refund finishes for 1850 (estimate was 1900); Order `v16` | Adjustment `completed` |
| 9 | Platform | `GET /orders/ord_9f2` | May now say the refund completed, for 1850 |

Had `unit_goods_2` shipped between steps 3 and 6, the attempt would resolve
`refused` with `reason_code: stale_eligibility` and no cancellation would
commit.

## Conformance

### Platforms

* **MUST NOT** expose or use these operations unless the extension was
  negotiated for this Business and the Order declares the operation for the
  target.
* **MUST** send `base_order_version`, a signed high-entropy `Idempotency-Key`,
  and byte-identical bodies on retries.
* **MUST** treat unknown outcome, `status`, `processing_mode`, or lookup
  `status` values as unresolved and not successful.
* **MUST NOT** create a replacement attempt with a new key unless the prior
  attempt is resolved or `fence_modification` returned `fenced`.
* **MUST NOT** report a refund as completed from a `committed` outcome.

### Businesses

* **MUST** reject the operations with `modification_not_supported` on any
  request where the extension was not negotiated.
* **MUST** declare `modification` whenever the extension is negotiated, with
  `available` agreeing with `operations`.
* **MUST** evaluate checks in the order given under
  [Version Preconditions](#version-preconditions-and-concurrency), revalidate
  eligibility at commit time, and serialize commits per Order.
* **MUST** enforce `atomic` all-or-nothing commitment.
* **MUST** implement claim-then-execute with permanent claim markers, keep
  lookup and `GET` strictly read-only, offer `fence_modification` with a
  permanent tombstone (or reject it with `fence_not_supported`), scope all
  lookups and fences, send `Cache-Control: no-store`, and publish
  `retained_until`.
* **MUST** fail closed on idempotency storage failure.
* **MUST NOT** delete Order line items on cancellation.

### Tests

| What | How | Executed here |
| :---- | :---- | :---- |
| Schema, examples, positive and negative fixtures, composition under the proposed name | `uv run python scripts/validate_examples.py --schema-base source/schemas/` and `uv run python scripts/test_order_modification.py` | **Yes** (schema-validator level) |
| Capability gating (client exposure and Business rejection) and profile-to-operation discovery for REST and MCP | `uv run python scripts/test_order_modification.py` | **Yes** (resolves from the example profile) |
| Order invariants (history, quantities, derived status, whole-Order metadata, atomic pending, commit vs refund) | `uv run python scripts/test_order_modification.py` | **Yes**, reference checks on fixtures |
| GET safety, and reconciliation rules (claim, fence, replay, retention) | `uv run python scripts/test_order_modification.py` | **Yes**, against a tiny executable *specification model*, not a merchant implementation |
| 24 runtime vectors (`scripts/fixtures/order_modification/vectors/V01..V24`) | Future runtime conformance suite | **No.** Structure and embedded payloads are checked; no implementation was run |

## Open Decisions

These are visible review points, not blockers to this draft.

1. Namespace: may a draft use the proposed `dev.ucp.shopping.order_modification`
   before Provisional (as PR #930 does), or should it move to a
   publisher-owned `com.{publisher}.*` name served from that publisher's
   domain? The schema validates under either.
2. `order_version` in the body versus HTTP `ETag`/`If-Match` as the canonical
   precondition.
3. Operation names, the lookup encoding (header for the original key versus the
   query string suggested in the EP), and the separate `fence_modification`
   operation that keeps the lookup safe.
4. Whether whole-Order and unit cancellation should keep sharing one request
   shape.
5. A mandatory minimum for `retained_until` beyond 24 hours, and whether
   permanent tombstones are acceptable operational cost for small Businesses
   (the alternative is that they reject fencing and Platforms stay unresolved).
6. Notification representation for merchant-reviewed requests.
7. Whether `dev.ucp.shopping.order:manage` suffices for all mutation and read
   operations.
8. Whether pre-admission failures should use HTTP 200 plus an error envelope
   (the existing UCP convention, used here) or HTTP 4xx for mutations.
9. The rejection code for a late request arriving under a fenced key.
10. Placement of the operations: this draft adds them to the shared
    `dev.ucp.shopping` descriptors because existing registry semantics offer
    no other discovery path. The alternative is a new mechanism for
    extension-declared operations.
11. Whether the fixture test should be wired into `docs.yml` or a pre-commit
    hook (not done here to avoid repository-wide changes).
