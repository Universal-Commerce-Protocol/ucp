# Order Modification Fixtures (Draft, EP #943)

Fixtures for the draft Order Modification extension. The capability name
`dev.ucp.shopping.order_modification` is proposed to the Tech Council and is
not approved, sanctioned, or published.

| Path | Purpose | Executed by |
| :---- | :---- | :---- |
| `manifest.json` | Lists every payload fixture, the schema or `$defs` entry to validate against, and whether it must validate | `scripts/test_order_modification.py` |
| `orders/`, `requests/`, `responses/`, `lookups/`, `errors/`, `profiles/` | Positive and negative payloads (negative files are prefixed `invalid_`) | schema validation |
| `orders/history_*.json`, `orders/semantic_*.json` | Order state before and after a committed cancellation | reference history checks |
| `vectors/V01..V21` | Runtime conformance vectors for Business behavior | **Not executed**; structure and embedded payloads are checked only |

## Run

```bash
uv run python scripts/test_order_modification.py
uv run python scripts/validate_examples.py --schema-base source/schemas/ --file docs/specification/shopping/extensions/order-modification.md
```

The first command validates every fixture, runs illustrative reference checks
(request versus declaration, Order history and quantities, byte-exact payload
matching, unknown-vocabulary handling), exercises a small executable
specification model of claim/fence/replay/retention rules (not a merchant
implementation),, probes extension composition, and checks
that the operations in the shared REST and MCP descriptors are discoverable
from the example profile and keep reads free of idempotency keys.

## What is and is not tested

* **Schema-validator level (executed):** field shapes, closed and open
  vocabularies, `available` versus `operations`, `granularity` versus `units`,
  atomic all-or-nothing results, `open`/`closed` request status, required
  `reason_code`/`blocked_by`, fenced `not_found`.
* **Reference checks (executed, illustrative):** rules that span documents.
  They are not a merchant server.
* **Runtime Business behavior (not executed):** replay cache, claim-then-execute
  and key fencing, review queues, commit-time revalidation, serialization of
  concurrent commits, storage-outage fail-closed, cross-Platform lookup denial.
  Vectors V01 to V21 describe these for a future runtime conformance suite.
