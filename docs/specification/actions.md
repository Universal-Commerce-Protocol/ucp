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

# Actions

Actions are scoped instructions that a business can emit while a UCP
entity is in progress. They are used when an operation can continue in band, but
only after the platform performs an additional step defined by the active UCP entity.

Actions are not standalone capabilities and are not negotiated as a new top-level
registry. They are part of the runtime contract of the active surface that emits
or adopts the action code.

## Design Goals

The common action model is intentionally small:

* **In-band continuation:** an action interrupts an operation without requiring a
    new UCP entity or a terminal handoff.
* **Domain generic:** the same envelope works for payment authentication,
    eligibility verification, account verification, compliance review, and other
    scoped runtime steps.
* **Owner-defined execution:** UCP defines the envelope; the owning
    specification defines how to execute the action.
* **Explicit correlation:** every action occurrence has an `id` so retries,
    repeated responses, and completion signals can be correlated safely.
* **Graceful fallback:** every required or blocking action must have an owning
    specification that explains what a platform should do when it cannot execute
    the action.

## Action Envelope

Entities that support actions define where the action array appears. When no
action is outstanding, the entity response **SHOULD** omit the action array or
return it as an empty array.

An action is carried in an entity response using the common envelope below:

<!-- ucp:example schema=common/types/action op=read -->
```json
{
  "id": "student-verification-1",
  "code": "com.example.identity.verify_student_status",
  "severity": "required",
  "config": {
    "url": "https://verify.example.com/session/abc123",
    "requested_claim": "student"
  }
}
```

| Field | Required | Meaning |
| :---- | :------- | :------ |
| `id` | Yes | Opaque identifier for this action occurrence. Stable while the same action remains outstanding. |
| `code` | Yes | Reverse-domain action code. The code resolves to the active entity specification that owns the action. |
| `severity` | Yes | Consequence of not handling the action: `optional`, `required`, or `blocking`. |
| `config` | Yes | Action-specific configuration. The owning specification defines the schema and semantics. Use `{}` when no configuration is needed. |

The base schema validates only this envelope. UCP does not define common
`state`, `mode`, `execution`, `url`, or `result` fields in the base action type.
Those concepts can be defined inside `config`, or in operation-specific request
or response fields, by the owning action specification when needed.

## Ownership and Resolution

Every action code emitted for an entity must be resolvable through an active
runtime surface, such as:

* a capability, like `dev.ucp.shopping.checkout`;
* an extension of an active capability;
* a payment handler selected for the current checkout or instrument.

The business **MUST NOT** emit an action unless the action code is defined or
adopted by an active owning spec for the current entity. The owning spec **MUST**
define:

* when the action can be emitted;
* the allowed `severity` values;
* the `config` schema and any action-specific schema variants;
* platform execution requirements;
* completion criteria and how completion is reflected in UCP state;
* fallback behavior when unsupported, abandoned, expired, or failed; and
* security and trust requirements, including origin validation for any external
    surface the platform is asked to load or invoke.

Action-specific negotiation, when needed, occurs inside the owning capability,
extension, or payment handler configuration. UCP does not add a top-level action
negotiation registry. For example, a payment handler or identity extension can
advertise its own supported action options in its existing `config` or schema.

## Severity

`severity` tells the platform what happens if the action is not handled. Entity
specifications define how these generic values map onto their own lifecycle.

| Severity | Meaning |
| :------- | :------ |
| `optional` | The platform **MAY** ignore the action. The entity can still reach a successful terminal state. |
| `required` | The platform **MUST** resolve the action before the entity can reach a successful terminal state, but the entity remains otherwise usable. |
| `blocking` | The action blocks the current attempted transition. The platform **MUST** resolve it, choose an allowed alternate path, or escalate before retrying that transition. |

A `blocking` action is scoped to the transition that produced it. Resolving that
action does not itself complete the entity; the platform re-drives the relevant
operation and the business returns the next authoritative entity state.

## Action Identity and Idempotency

The `id` field identifies an action occurrence, not just an action type.
Businesses **MUST** follow these rules:

* `id` values **MUST** be unique among outstanding actions for the containing
    entity.
* The same unresolved action occurrence **MUST** keep the same `id` across
    repeated responses, retries, and polling.
* A new occurrence, even with the same `code` and similar `config`, **MUST** use
    a new `id`.
* If the platform changes the underlying entity state in a way that supersedes
    an outstanding action, the business **MUST** stop treating stale completion
    signals for the old `id` as applicable to the new state.

Owning specifications that receive action completion or failure information over
UCP **MUST** bind that information by `id`. If completion is observed out of band
(for example, by an external service calling the business), the business still
uses `id` to correlate repeated responses and avoid creating duplicate runtime
steps for ordinary retries.

## Config and Execution Contracts

`config` is opaque to the base action model. The platform interprets it only
through the owning action specification. This lets the base primitive ship
without prematurely standardizing execution details that may differ across
checkout, identity, payment handlers, transports, or
out-of-band approval systems.

When an action asks the platform to load, invoke, render, or call an external
surface, the owning specification **MUST** make the executable fields explicit in
its schema and define at least:

* allowed URL schemes; executable web URLs **MUST** be HTTPS;
* origin, host, or trust-validation rules;
* whether the surface is visible or background-only;
* sandboxing, permissions, and native/web isolation requirements;
* how the platform detects completion, abandonment, timeout, and fatal failure;
    and
* which recovery paths are allowed.

The platform **MUST NOT** infer that an arbitrary URI-typed value inside
`config` is safe to load. It is loadable only when the owning specification says
so and the platform can satisfy that specification's trust policy.

## Completion, Results, and Recovery

The base action envelope does not carry an authoritative result. Completion
means only what the owning specification says it means. In many flows, action
completion is advisory: it tells the platform to resume the UCP operation, while
the business remains authoritative for the final entity state.

An owning specification can define one or more completion mechanisms, such as:

* a subsequent UCP operation that includes an action result keyed by `id`;
* an embedded or native callback observed by the platform;
* an out-of-band provider callback to the business; or
* a poll in which the platform repeats the relevant UCP operation and the
    business returns the next state.

For required and blocking actions, the owning specification **MUST** define what
the platform should do when the action is unsupported, abandoned, expired, or
failed. Examples include retrying the same step, changing the underlying input,
selecting a different instrument, canceling the entity, or escalating to a
business-hosted experience.

## Security and Trust

Actions are instructions from the business, but platforms are not required to
blindly trust every executable detail in `config`. Trust can be established with
the business itself or with a third party named by the owning specification, but
it must be independently validated according to that specification.

Owning specifications **MUST** document security expectations for every action
code. At minimum:

* executable web URLs **MUST** use HTTPS;
* platforms **MUST** validate origins or equivalent trust anchors before loading
    external surfaces;
* platforms **MUST NOT** interpolate opaque `config` values into executable code,
    HTML, shell commands, or native API calls outside the owning specification's
    rules;
* action completion signals **MUST NOT** be treated as authoritative proof of a
    business outcome unless they are independently verifiable under the owning
    specification.

## Examples

### Eligibility Verification

A discount extension might require the buyer to verify eligibility before the
checkout can complete. The extension owns the action code and defines the URL
trust policy, presentation, completion signal, and how the business observes the
verified claim.

<!-- ucp:example schema=common/types/action op=read -->
```json
{
  "id": "student-verification-1",
  "code": "com.example.identity.verify_student_status",
  "severity": "required",
  "config": {
    "url": "https://verify.example.com/session/abc123",
    "requested_claim": "student",
    "timeout_seconds": 300
  }
}
```

### Account Verification

An account-linking extension might ask the platform to collect a short code in a
native UI. The prompt and input rules are action-specific `config`; the base
action model does not standardize input rendering.

<!-- ucp:example schema=common/types/action op=read -->
```json
{
  "id": "login-code-1",
  "code": "com.example.account.verify_login",
  "severity": "blocking",
  "config": {
    "prompt": "Enter the 6-digit code sent to your phone.",
    "input_type": "numeric",
    "length": 6
  }
}
```

## Schema

{{ schema_fields('types/action', 'reference') }}
