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

# Additional Fields Extension

## Overview

The Additional Fields Extension allows businesses to request extra
buyer-provided information on a checkout and, optionally, on a cart. UCP's base
commerce schemas are intentionally fixed, but commerce requirements vary across
industries, geographies, regions, regulations, and business processes. This
extension provides a first-class, type-aware representation of merchant-defined
input fields so that platforms and agents can render them, collect values from
the buyer, and submit those values without knowing anything about the
business's storage model.

Typical v1 use cases include consents and delivery windows. Delivery
instructions and gift messages are also valid v1 use cases.

**Key features:**

- A small set of typed inputs: `text`, `multiline_text`, `boolean`, `date`,
  `choice`
- Stable, human-readable `key` per field so agents can interpret payloads
- Server-authoritative validation with optional client-side hints
- Required on Checkout and optionally supported on Cart

**Dependencies:**

- Checkout Capability
- Cart Capability when cart support is advertised in `extends`

!!! note "V1 scope"
    Additional fields appear at the top level of the checkout or cart
    response. They cannot be attached to a specific line item, the buyer,
    fulfillment, or a specific shipping group. Use cases like per-item
    monogramming, buyer-profile fields, or delivery instructions on a single
    package are out of scope for this version. Future additive extensions can
    add that targeting without breaking this schema.

!!! warning "Sensitive data"
    This extension MUST NOT be used to collect payment credentials, passwords,
    authentication secrets, or equivalent high-risk secrets. Collection of
    regulated data such as government identifiers, health data, or age
    verification evidence requires separate governance and SHOULD use a
    specialized capability or buyer handoff rather than generic additional
    fields.

## Discovery

Businesses advertise additional-fields support in their profile. The extension
MUST extend checkout and MAY also extend cart. Cart-only support is invalid.
The `extends` array lists which base capabilities this extension applies to in
a given profile.

=== "Checkout and cart"

    ```json
    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.shopping.additional_fields": [
            {
              "version": "{{ ucp_version }}",
              "extends": ["dev.ucp.shopping.checkout", "dev.ucp.shopping.cart"],
              "spec": "https://ucp.dev/{{ ucp_version }}/specification/additional-fields",
              "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/additional_fields.json",
              "config": {
                "supported_input_types": ["text", "multiline_text", "boolean", "date", "choice"]
              }
            }
          ]
        }
      }
    }
    ```

=== "Checkout only"

    ```json
    {
      "ucp": {
        "version": "{{ ucp_version }}",
        "capabilities": {
          "dev.ucp.shopping.additional_fields": [
            {
              "version": "{{ ucp_version }}",
              "extends": "dev.ucp.shopping.checkout",
              "spec": "https://ucp.dev/{{ ucp_version }}/specification/additional-fields",
              "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/additional_fields.json",
              "config": {
                "supported_input_types": ["text", "multiline_text", "boolean", "date", "choice"]
              }
            }
          ]
        }
      }
    }
    ```

!!! note "Checkout required, cart optional"
    A business MAY support additional fields on checkout only or on both
    checkout and cart. Partial adoption is expressed by varying the `extends`
    value on the single capability entry — not by advertising multiple entries.
    Platforms MUST check `extends` before expecting `additional_fields` in cart
    responses. Platforms MUST NOT treat a cart-only `extends` value as valid for
    this extension.

### Input type negotiation

Both sides — the business (the merchant or seller) and the platform (the agent
or client) — declare `config.supported_input_types` in their discovery
profiles. The active input-type set for a session is the intersection of the
two declarations.

When either side omits `supported_input_types` (or omits `config` entirely),
that side is treated as declaring support for the full v1 set of well-known
types: `text`, `multiline_text`, `boolean`, `date`, and `choice`. A platform or
business that supports fewer than all v1 input types MUST declare
`config.supported_input_types` with the supported subset. Future input types MUST
be explicitly declared by clients and businesses that support them.

V1 input types are closed. Businesses MUST NOT emit `input.type` values beyond
the v1 well-known set.

- Businesses MUST emit only fields whose `input.type` is in the negotiated
  intersection.
- For a **required** field whose `input.type` is not in the intersection, the
  business MUST omit the field from renderable `additional_fields`, MUST return
  a `messages[]` entry with `code: "additional_field_unsupported_type"` and
  `severity: "requires_buyer_input"`, and MUST include a top-level
  `continue_url` for buyer handoff. On checkout responses, this also produces
  `status: "requires_escalation"` per the standard UCP rule that
  `requires_*`-severity errors contribute to that status. On cart responses,
  which have no `status` field, the `messages[]` entry plus `continue_url` is
  the entire contract.
- For an **optional** field whose type is not in the intersection, the business
  SHOULD omit the field and MAY surface a `type: "warning"` message.

## Schema

When this capability is active, checkout responses are extended with an
`additional_fields` array. Cart responses are extended with the same array when
the capability also extends cart. Businesses SHOULD include `additional_fields`
when the extension applies to that resource, even when the array is empty.
Businesses MUST include `additional_fields` when fields are currently requested,
when previously submitted additional-field values exist, or when a `messages[]`
entry references additional fields.

`AdditionalField` is the schema source of truth for both response entries and
the UCP-generated request projection. Responses use the full object. Requests
use the resolved request shape produced by `ucp_request` annotations, which
accepts only `{key, value}` entries. Field definitions (`label`, `description`,
`description_content_type`, `required`, and `input`) are business-authoritative
and invalid in request entries.

### Additional Field

{{ schema_fields('types/additional_field', 'additional-fields') }}

### Additional Field Input

{{ schema_fields('types/additional_field_input', 'additional-fields') }}

### Platform Config

{{ extension_schema_fields('additional_fields.json#/$defs/platform_config', 'additional-fields') }}

### Business Config

{{ extension_schema_fields('additional_fields.json#/$defs/business_config', 'additional-fields') }}

## Semantics

### Keys

Each `AdditionalField.key` MUST be unique within a single checkout or cart
response. The key is a business-defined stable identifier and SHOULD use a
dot-separated, namespaced form so that agents and operators can interpret
payloads unambiguously (e.g., `custom.delivery_instructions`,
`partner_acme.policy_consent`). Keys are case-sensitive. The schema permits
dot, colon, and hyphen separators.

Platforms MUST round-trip the `key` verbatim when submitting values —
businesses map keys back to their own internal storage.

### Values

The JSON type of `value` matches the field's `input.type`: `boolean` fields
submit JSON booleans, and every other v1 type submits a string. An unset field
is `null` regardless of type.

| `input.type`     | `value` serialization                           |
| ---------------- | ----------------------------------------------- |
| `text`           | Raw string                                      |
| `multiline_text` | Raw string (`\n` preserved)                    |
| `boolean`        | JSON `true` or `false`                          |
| `date`           | RFC 3339 full-date string (`YYYY-MM-DD`)        |
| `choice`         | One of `input.options[].value` entries (string) |

Choice values MUST match one of `input.options[].value` byte-for-byte.
Businesses MUST ensure `input.options[].value` values are unique within a
choice field. JSON Schema rejects exact duplicate option objects, but the
business remains authoritative for rejecting duplicate values that differ only
by display fields like `label`.

Date values and `min`/`max` bounds reflect the buyer's local calendar day. If a
business's validation depends on a specific timezone (e.g., fulfillment
warehouse local time), it SHOULD communicate that expectation in the field's
`description`.

### Required fields

When `required: true`, the buyer MUST submit a non-null `value` before the
checkout can reach `status: "ready_for_complete"`. A required field whose
`value` is `null` produces a `messages[]` entry with
`code: "additional_field_required"` and `severity: "recoverable"`. For `text`
and `multiline_text` inputs, an empty or whitespace-only string is treated the
same as `null` for required validation. For `date` and `choice`, an empty
string is invalid serialization; platforms should submit `null` when unset.

For consent-style use cases, businesses use a required `boolean` field and
reject a submitted `false` with `code: "additional_field_invalid_value"`.
`value: null` (untouched) and `value: false` (affirmatively declined) are
distinguishable on the wire, which lets platforms render useful error copy in
each case.

### Validation

Businesses are authoritative for validation. The `input` descriptor MAY carry
validation hints (`min_length`, `max_length`, `pattern`, `min`, `max`, or
`options`) that platforms SHOULD use to provide immediate client-side feedback,
but the business MUST NOT rely on those hints being enforced — every submitted
value is re-validated on the server.

`min_length` and `max_length` count Unicode code points after JSON decoding,
with no implicit normalization. `pattern` uses ECMA-262 regular expression
semantics as a validation hint, with no implicit anchoring. If the platform's
regex engine cannot express or safely evaluate the pattern, the platform SHOULD
skip client-side pattern validation and rely on business-side validation.

Businesses MUST NOT emit contradictory validation hints such as
`min_length > max_length` or `min > max`.

The wire schema does not constrain `value` against sibling hints (for example,
the schema will accept a `value` that is not in the `input.options[].value` set).
This is intentional: it allows response bodies to echo invalid buyer input
alongside a `messages[]` error explaining why the value was rejected, and keeps
platforms from having to re-implement the business's validation rules. The
authoritative answer always comes from `messages[]`.

Submitted values whose JSON type or string format does not match the field's
`input.type` are invalid and MUST produce `additional_field_invalid_value`. For
example, `"true"` is invalid for `boolean`, JSON `true` is invalid for `text`,
`multiline_text`, `date`, and `choice`, an empty string is invalid for `date` and
`choice`, a malformed or non-full-date string is invalid for `date`, and a
`choice` string that does not match one of `input.options[].value` byte-for-byte
is invalid.

### Localization

Labels, descriptions, and choice labels are **pre-resolved** by the business
for the buyer's locale before the response is sent. Platforms do not receive a
per-locale map. `label` and choice labels are always plain text.
`description_content_type` applies only to `description`; when omitted,
platforms MUST treat the description as `plain`.

### Field lifecycle

The resolved field list MAY change between responses based on cart contents,
market, shipping address, buyer identity, inventory, policy state, or other
business rules. A business MUST NOT repurpose a `key` for a different logical
field within the same merchant integration and capability version. A `key` also
SHOULD have stable semantics within a cart or checkout lifecycle. If a business
changes a field's `input.type`, `required` flag, options, or validation hints for
the same `key`, it MUST revalidate any existing value before treating the
checkout as ready.

If a previously submitted field disappears from the resolved field list, it is
no longer active. The business MUST NOT echo it in `additional_fields`, and a
platform that submits that key again is submitting an unknown or inactive key.

## Operations

Platforms submit only `{key, value}` entries in the `additional_fields` array.
All other properties on `AdditionalField` (`label`, `description`,
`description_content_type`, `required`, `input`) are business-determined and
invalid in requests.

**Checkout operations:**

| Operation  | `additional_fields` in Request              | `additional_fields` in Response |
| ---------- | ------------------------------------------- | ------------------------------- |
| `create`   | Optional; entries submit `{key, value}`     | Present when fields, values, or messages exist; otherwise SHOULD be present as empty |
| `update`   | Optional; entries submit `{key, value}`     | Present when fields, values, or messages exist; otherwise SHOULD be present as empty |
| `complete` | Omit                                        | Present when fields, values, or messages exist; otherwise SHOULD be present as empty |

**Cart operations, when cart support is advertised:**

| Operation | `additional_fields` in Request              | `additional_fields` in Response |
| --------- | ------------------------------------------- | ------------------------------- |
| `create`  | Optional; entries submit `{key, value}`     | Present when fields, values, or messages exist; otherwise SHOULD be present as empty |
| `update`  | Optional; entries submit `{key, value}`     | Present when fields, values, or messages exist; otherwise SHOULD be present as empty |

### Cart-to-checkout carryover

When the extension also applies to cart, submitted cart additional-field values
MUST carry forward into checkout when the cart is converted into a checkout.
Carryover is keyed by `AdditionalField.key`. Consistent with the base
cart-to-checkout conversion contract, when `cart_id` is present on
`create_checkout`, the business MUST initialize checkout additional-field values
from the cart and MUST ignore overlapping `additional_fields` values in the
checkout payload. Platforms that need to change carried values SHOULD update the
checkout after creation. The checkout response remains business-authoritative:
the business re-resolves the checkout field list, revalidates carried values,
and may return messages if a carried value is no longer valid for the checkout
state.

### Replacement semantics

Submitting `additional_fields` on an `update_checkout` or `update_cart` request
replaces the full set of previously submitted additional-field values, matching
the base UCP update contract. If `additional_fields` is absent from the request
body, the business MUST preserve previously submitted additional-field values.
If `additional_fields` is present, platforms MUST include every value they want
to keep, using the `{key, value}` tuple shape. Field definitions are
business-authoritative; platforms cannot remove a field the business has
declared on the response. To clear a previously submitted value, either omit the
entry from the submitted `additional_fields` array or submit
`{ "key": "...", "value": null }` — the two are equivalent.

Additional-field values are validated with the resulting cart or checkout state
after the full request is applied. Invalid submitted values may be echoed in the
response, but checkout cannot become `ready_for_complete` while recoverable
additional-field errors remain.

### Request validation

When `additional_fields` is present in a request, each `key` MUST appear at most
once. Duplicate keys are invalid and MUST produce a `messages[]` entry with
`code: "additional_field_invalid_value"` and `severity: "recoverable"`.

Businesses MUST NOT create or persist values for keys that are not present in
the current resolved `additional_fields` list for the checkout or cart. Unknown
or inactive keys are invalid and MUST produce a `messages[]` entry with
`code: "additional_field_invalid_value"`, `severity: "recoverable"`, and a
`path` pointing at the submitted entry.

### Payload budget

Businesses SHOULD emit no more than 10 `additional_fields` entries per
response. This limit is a budget heuristic for agentic clients; responses with
materially larger payloads risk being truncated, down-sampled, or rejected by
downstream consumers. Choice-option lists count toward the same payload budget;
businesses SHOULD keep `input.options` concise and avoid large enumerations
that require scrolling or search.

Recommended v1 payload budgets are intentionally advisory rather than schema-
enforced, because businesses remain authoritative for validation and some
verticals need longer copy. Businesses SHOULD stay within these budgets unless a
field is required for checkout completion and no shorter representation is
practical:

| Item | Recommended budget |
| ---- | ------------------ |
| Fields per response | 10 fields |
| Choice options per field | 20 options |
| Field `key` | 80 characters |
| Field `label` | 80 characters |
| Field `description` | 500 characters |
| Choice `value` | 80 characters |
| Choice `label` | 80 characters |
| `pattern` | 500 characters |
| Submitted `text` value | 1,000 characters |
| Submitted `multiline_text` value | 4,000 characters |

For larger enumerations, long-form instructions, uploads, or searchable option
sets, businesses SHOULD use a more specific capability or buyer handoff rather
than overloading additional fields.

Platforms MAY decline to render optional entries beyond their rendering or
payload capacity and SHOULD surface a platform-local warning when they do so.
Platforms MUST NOT silently drop required fields. If a platform cannot render
every required field in the response, it MUST treat the session as requiring
buyer handoff and direct the buyer to the business site via `continue_url` when
available. If no `continue_url` is available, the platform MUST fail closed: it
MUST NOT complete the checkout and MUST surface the session as blocked by an
unrenderable required field.

## Errors

Validation issues surface via the standard `messages[]` array using well-known
`code` values. All three codes are `type: "error"` entries.

| `code`                              | `severity`             | Meaning                                                                                      |
| ----------------------------------- | ---------------------- | -------------------------------------------------------------------------------------------- |
| `additional_field_required`         | `recoverable`          | A required field was not submitted or the submitted `value` was empty.                       |
| `additional_field_invalid_value`    | `recoverable`          | The submitted `value` failed business-side validation (length, pattern, type, choice, range). |
| `additional_field_unsupported_type` | `requires_buyer_input` | A required field's `input.type` is not in the negotiated intersection. Handoff via `continue_url`. |

The `path` field on each message SHOULD point at the offending field using RFC
9535 JSONPath. If the offending field appears in the response, the path SHOULD
point at the response field by key, for example:

```text
$.additional_fields[?@.key=='custom.delivery_instructions']
```

For unknown or inactive keys, the path MUST point at the submitted request
entry by array index. For duplicate keys, the path SHOULD point at one of the
duplicate submitted entries. For other malformed request entries, the path MAY
point at the submitted request entry by array index. For unsupported required
fields that were omitted from renderable `additional_fields`, the path SHOULD
point at `$.additional_fields`, and the message content SHOULD identify the
missing requirement when safe.

## Rendering Guidance

Platforms SHOULD render each field using its resolved `label`, a suitable input
control for its `input.type`, and, when present, its `description` as help text.
Platforms SHOULD preserve the field order returned by the business.

!!! warning "Sanitization"
    The `label`, `description`, choice `label`, and submitted values are
    untrusted content. `label`, choice labels, and submitted values are always
    plain text and MUST NOT be interpreted as markdown or HTML.
    `description_content_type` controls only `description` and defaults to
    `plain`. When `description_content_type` is `markdown`, platforms MAY render
    links only. Platforms MUST escape or strip raw HTML, images, embedded media,
    scripts, event handlers, emphasis, headings, lists, tables, block HTML, and
    any non-link markdown constructs before inserting output into HTML, logs,
    prompts, or other contexts. Rendered links MUST use `https` URLs; platforms
    MUST reject or strip scriptable or ambiguous schemes such as `javascript:`,
    `data:`, `file:`, and protocol-relative URLs. Platforms MAY render markdown
    descriptions as plain text. Businesses SHOULD keep descriptions
    understandable when rendered as plain text.

When `required: true`, platforms SHOULD visually mark the field as required and
SHOULD NOT allow the buyer to reach the complete step without a value.

For `input.type: "choice"`, platforms MUST only allow values that match one of
the `input.options[].value` entries.

Placeholders, grouping, defaults, multi-select, file upload, rich-text
descriptions, and conditional field dependencies are out of scope for v1.

## Examples

### Optional text field

A delivery-instructions field on a checkout.

=== "Request"

    ```json
    {
      "line_items": [
        { "item": { "id": "prod_1" }, "quantity": 1 }
      ],
      "additional_fields": [
        { "key": "custom.delivery_instructions", "value": "Leave with doorman" }
      ]
    }
    ```

=== "Response"

    ```json
    {
      "id": "chk_abc123",
      "line_items": [
        {
          "id": "li_1",
          "item": { "id": "prod_1", "title": "Wireless Headphones", "price": 7999 },
          "quantity": 1
        }
      ],
      "additional_fields": [
        {
          "key": "custom.delivery_instructions",
          "label": "Delivery instructions",
          "description": "Gate code or concierge details",
          "required": false,
          "value": "Leave with doorman",
          "input": {
            "type": "text",
            "max_length": 140
          }
        }
      ],
      "totals": [
        { "type": "subtotal", "display_text": "Subtotal", "amount": 7999 },
        { "type": "total",    "display_text": "Total",    "amount": 7999 }
      ]
    }
    ```

### Required boolean consent

A required terms-of-service acceptance on a checkout.

=== "Response: required, unset"

    ```json
    {
      "id": "chk_def456",
      "status": "incomplete",
      "additional_fields": [
        {
          "key": "custom.accept_terms",
          "label": "I accept the Terms of Service",
          "description": "Review the [Terms of Service](https://example.com/terms) before accepting.",
          "description_content_type": "markdown",
          "required": true,
          "value": null,
          "input": { "type": "boolean" }
        }
      ],
      "messages": [
        {
          "type": "error",
          "code": "additional_field_required",
          "severity": "recoverable",
          "content": "Please accept the Terms of Service to continue.",
          "path": "$.additional_fields[?@.key=='custom.accept_terms']"
        }
      ]
    }
    ```

=== "Request: accept"

    ```json
    {
      "additional_fields": [
        { "key": "custom.accept_terms", "value": true }
      ]
    }
    ```

### Date field with min/max

A requested-delivery date constrained to a window.

=== "Response"

    ```json
    {
      "id": "chk_ghi789",
      "additional_fields": [
        {
          "key": "custom.requested_delivery_date",
          "label": "Requested delivery date",
          "required": false,
          "value": null,
          "input": {
            "type": "date",
            "min": "2026-05-01",
            "max": "2026-05-31"
          }
        }
      ]
    }
    ```

### Choice field

A single-select delivery-window picker.

=== "Response"

    ```json
    {
      "id": "chk_jkl012",
      "additional_fields": [
        {
          "key": "custom.delivery_window",
          "label": "Delivery window",
          "required": true,
          "value": null,
          "input": {
            "type": "choice",
            "options": [
              { "value": "morning",   "label": "Morning (8am–12pm)" },
              { "value": "afternoon", "label": "Afternoon (12pm–5pm)" },
              { "value": "evening",   "label": "Evening (5pm–9pm)" }
            ]
          }
        }
      ]
    }
    ```

### Escalation for unsupported required type

A required `date` field when the negotiated intersection excludes `date`.

=== "Response"

    ```json
    {
      "id": "chk_mno345",
      "status": "requires_escalation",
      "continue_url": "https://business.example.com/checkout/chk_mno345",
      "additional_fields": [],
      "messages": [
        {
          "type": "error",
          "code": "additional_field_unsupported_type",
          "severity": "requires_buyer_input",
          "content": "This checkout requires a requested delivery date your client cannot collect. Please continue on the business site.",
          "path": "$.additional_fields"
        }
      ]
    }
    ```

### Cart-to-checkout carryover

A delivery-window value collected on cart carries into checkout by key.

=== "Cart update request"

    ```json
    {
      "id": "cart_xyz789",
      "line_items": [
        { "id": "li_1", "item": { "id": "prod_1" }, "quantity": 1 }
      ],
      "additional_fields": [
        { "key": "custom.delivery_window", "value": "morning" }
      ]
    }
    ```

=== "Checkout response"

    ```json
    {
      "id": "chk_from_cart_xyz789",
      "cart_id": "cart_xyz789",
      "status": "ready_for_complete",
      "additional_fields": [
        {
          "key": "custom.delivery_window",
          "label": "Delivery window",
          "required": true,
          "value": "morning",
          "input": {
            "type": "choice",
            "options": [
              { "value": "morning", "label": "Morning" },
              { "value": "afternoon", "label": "Afternoon" }
            ]
          }
        }
      ]
    }
    ```
