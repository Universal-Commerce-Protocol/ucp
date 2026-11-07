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

# Extension Authoring Guide

This guide walks through building a UCP extension outside the core protocol:
an extension a Business or Platform publishes under its own reverse-domain
namespace (`com.{vendor}.*`, `org.{org}.*`) to add fields or behavior to a
UCP capability such as checkout, cart, or catalog search.

It is a practical companion to the normative rules in the
[Specification Overview](../specification/overview/index.md), which this guide
links to rather than restates. If you are changing UCP itself, see the
[Schema Authoring Guide](schema-authoring.md) instead.

## Before You Start

An extension augments an existing capability. Consider the alternatives first:

- **Profile configuration.** If you only need to tell the other party how you
  are set up, a capability's `config` may already cover it.
- **Signals.** Environment data a Platform observes, for the Business's
  authorization and abuse prevention, belongs in
  [signals](../specification/overview/index.md#signals), keyed in your own
  namespace (for example, `com.example.device_id`), not in a new extension.
- **A new capability.** If your feature is not about augmenting an existing
  capability's payloads, it may be a capability of its own rather than an
  extension.

An extension is the right tool when you need to add typed fields to another
capability's requests or responses, and both parties need to agree to support
them.

## Where Your Extension Lives

You publish and maintain your extension yourself. Its schema and specification
live on your own domain, under your own namespace; they are not added to the
UCP repository, and you do not need UCP's approval to publish them (see
[Namespace Governance](../specification/overview/index.md#namespace-governance)).

If your extension proves useful to many Businesses and Platforms, it can become
a candidate for the core protocol. UCP keeps the core light: new functionality
starts self-hosted under a vendor namespace and is proposed for `dev.ucp.*`
once it has broad, multi-party adoption, through the Enhancement Proposal
process (see [Contributing](contributing.md)).

## What You'll Build

A complete extension has five parts:

1. **A name** in a namespace you control, such as `com.acme.shopping.loyalty`.
2. **A schema** hosted on your domain that describes what the extension adds
   to each capability it extends.
3. **A version** you control, plus the UCP versions it requires.
4. **A specification page** that explains the extension's behavior.
5. **Profile entries** that advertise it, so it can be negotiated.

The sections below take these in order, then cover local testing.

## Choose a Name

Extension names follow the same rules as every capability name (see
[Namespace Governance](../specification/overview/index.md#namespace-governance)):

- Use the format `{reverse-domain}.{service}.{capability}`, for example
  `com.acme.shopping.loyalty`.
- Use a domain you control. The `dev.ucp.*` namespace is reserved for the UCP
  governing body.
- Choose a registrable domain you exclusively control, not a shared suffix
  such as a hosting platform's subdomain.

The name is bound to the host that serves your schema. A Platform derives the
authority from the `schema` URL's host and rejects the extension, without
fetching it, unless that authority matches the name (see
[Authority Binding](../specification/overview/index.md#authority-binding)).
For `com.acme.shopping.loyalty`, a schema served from `acme.com` binds; one
served from a shared CDN host such as `cdn.example.net` does not.

## Write the Schema

### Metadata

An extension schema is self-describing. At the top level, declare:

| Field | Purpose |
| --- | --- |
| `$id` | Canonical URL of the schema, on the host that binds to your name |
| `name` | The extension's reverse-domain name |
| `version` | Your extension version, an ISO 8601 date you control |
| `title`, `description` | Human-readable summary |
| `requires` | The UCP protocol and capability versions the extension depends on (see [Versioning](#version-your-extension)) |

### Extend a Capability

For each capability your extension extends, add a `$defs` entry keyed by that
capability's full name. The entry composes onto the capability's schema with
`allOf`: it references the base schema, then adds your fields (see
[Extension Schema Pattern](../specification/overview/index.md#extension-schema-pattern)).

Because your schema is hosted on your domain, reference UCP base schemas by
absolute URL, including the UCP release in the path:

<!-- ucp:example skip reason="extension schema example; hosted outside ucp.dev" -->
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://acme.com/ucp/schemas/loyalty.json",
  "name": "com.acme.shopping.loyalty",
  "version": "2026-09-01",
  "title": "Acme Loyalty",
  "description": "Adds loyalty points earned on a checkout.",
  "requires": {
    "protocol": { "min": "2026-08-25" },
    "capabilities": {
      "dev.ucp.shopping.checkout": { "min": "2026-08-25" }
    }
  },
  "$defs": {
    "loyalty": {
      "type": "object",
      "required": ["points_earned"],
      "properties": {
        "points_earned": { "type": "integer", "minimum": 0 },
        "member_id": { "type": "string" }
      }
    },
    "dev.ucp.shopping.checkout": {
      "title": "Checkout with Acme Loyalty",
      "allOf": [
        { "$ref": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/checkout.json" },
        {
          "type": "object",
          "properties": {
            "loyalty": { "$ref": "#/$defs/loyalty" }
          }
        }
      ]
    }
  }
}
```

Put the types your extension introduces (`loyalty` above) in their own `$defs`
entries and reference them from the composed entry, so they can be reused across
parents.

### Control Request and Response Visibility

A capability usually uses one object for both requests and responses. Fields
that only one side sends carry visibility annotations: `ucp_request` and
`ucp_response`, with the values `omit`, `optional`, or `required`, either for
every operation or per operation (`create`, `read`, `update`, `complete`).

For example, a field the Business computes and the Platform never sends:

<!-- ucp:example skip reason="extension schema fragment" -->
```json
"loyalty": {
  "$ref": "#/$defs/loyalty",
  "ucp_request": "omit"
}
```

Or a field the Platform may send on create and update, but not on complete:

<!-- ucp:example skip reason="extension schema fragment" -->
```json
"loyalty_member_id": {
  "type": "string",
  "ucp_request": { "create": "optional", "update": "optional", "complete": "omit" }
}
```

See [Visibility Rules](https://github.com/Universal-Commerce-Protocol/ucp-schema#visibility-rules)
in the `ucp-schema` documentation for the full resolution rules.

### Extend More Than One Capability

To extend several capabilities, declare each in `extends` and add a `$defs`
entry for each (see
[Multi-Parent Extensions](../specification/overview/index.md#multi-parent-extensions)).
Each entry can add different fields; for example, a loyalty extension might
show a points preview on cart and points earned on checkout:

<!-- ucp:example skip reason="extension schema example; hosted outside ucp.dev" -->
```json
"$defs": {
  "dev.ucp.shopping.cart": {
    "allOf": [
      { "$ref": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/cart.json" },
      { "type": "object", "properties": { "loyalty_preview": { "$ref": "#/$defs/loyalty" } } }
    ]
  },
  "dev.ucp.shopping.checkout": {
    "allOf": [
      { "$ref": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/checkout.json" },
      { "type": "object", "properties": { "loyalty": { "$ref": "#/$defs/loyalty" } } }
    ]
  }
}
```

The extension stays active as long as at least one of its parents is
negotiated, and each response lists it only when it extends that response's
capability (see
[Response Capability Selection](../specification/overview/index.md#response-capability-selection)).

### Extend a Container Capability

Some capabilities use different objects for requests and responses. Catalog
search, for example, takes a query and returns a list of products. Such a
capability's schema is a container: each message body sits under `$defs`, named
`{operation}_{direction}` (`search_request`, `search_response`).

To extend a container, mirror its shape names under your `$defs` entry and
compose each one onto the base shape:

<!-- ucp:example skip reason="extension schema example; hosted outside ucp.dev" -->
```json
"$defs": {
  "dev.ucp.shopping.catalog.search": {
    "$defs": {
      "search_response": {
        "allOf": [
          { "$ref": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/catalog_search.json#/$defs/search_response" },
          {
            "type": "object",
            "properties": {
              "products": { "items": { "$ref": "#/$defs/product_with_loyalty" } }
            }
          }
        ]
      }
    }
  }
}
```

Here `product_with_loyalty` is your own `$defs` entry that composes onto the
UCP product type and adds your product fields. Mirror only the shapes you
change. `ucp-schema` rejects a container entry that
composes directly onto a response with `allOf`, without the nested shape names.
See
[Container Capabilities](https://github.com/Universal-Commerce-Protocol/ucp-schema#container-capabilities)
in the `ucp-schema` documentation.

### Type Your Profile Configuration

If your extension takes configuration in profiles, describe it under a `$defs`
entry keyed by your extension's own name, with `platform_schema` and
`business_schema` variants that compose onto UCP's capability declaration. The
UCP fulfillment extension uses this pattern for its `config`:

<!-- ucp:example skip reason="extension schema example; hosted outside ucp.dev" -->
```json
"$defs": {
  "com.acme.shopping.loyalty": {
    "business_schema": {
      "allOf": [
        { "$ref": "https://ucp.dev/{{ ucp_version }}/schemas/capability.json#/$defs/business_schema" },
        {
          "properties": {
            "config": {
              "type": "object",
              "properties": { "program_name": { "type": "string" } }
            }
          }
        }
      ]
    }
  }
}
```

### Declare Action Types

If your extension needs the Platform to carry out a step, such as a
verification or a payment challenge, it can declare Action types (see
[Actions](../specification/overview/index.md#actions)). Each Action type's key
must be in your namespace, and your specification must define its full
contract; see
[Extension-Declared Action Types](schema-authoring.md#extension-declared-action-types)
for what to cover.

### Avoid Composition Pitfalls

`allOf` only ever adds constraints, which shapes what an extension can do:

- **You can add fields, not loosen existing ones.** A composed schema must
  satisfy the base and your extension, so you cannot widen a base type, relax a
  base requirement, or add a value to a closed `enum`. See
  [Extensibility and Forward Compatibility](schema-authoring.md#extensibility-and-forward-compatibility).
- **Property names are not namespaced.** The fields your extension adds sit
  alongside UCP's own fields and those of other extensions. If two active
  extensions add a property with the same name, a payload must satisfy both
  definitions at once, and a future UCP release could add a field with the same
  name. Choose names that describe your feature specifically. A namespacing
  rule for third-party fields is under discussion in
  [#983](https://github.com/Universal-Commerce-Protocol/ucp/issues/983).
- **Expect generated types.** SDKs and code generators turn composed schemas
  into typed classes, which makes conflicting definitions of the same property,
  and closed `enum` values you later need to extend, especially costly.
- **Keep your own types open.** Avoid `additionalProperties: false` on objects
  you introduce, so later versions of your extension, or other extensions, can
  add to them.

## Version Your Extension

Third-party extensions version independently of UCP (see
[Component Versioning and Release Snapshots](../specification/overview/index.md#component-versioning-and-release-snapshots)):

- **Your version is your own.** It is an ISO 8601 date that you advance on your
  own schedule; it never has to match `ucp.version`.
- **Declare what you depend on in `requires`.** `requires.protocol` constrains
  the selected `ucp.version`, and `requires.capabilities` constrains the
  selected versions of the capabilities you extend. Each constraint has a `min`
  and an optional `max`. Every key in `requires.capabilities` must also be a
  `$defs` key in your schema (see
  [Version Requirements](../specification/overview/index.md#version-requirements)).
- **`requires` verifies; it does not select.** Versions are chosen by
  negotiation first. An extension whose requirements the chosen versions do not
  satisfy is dropped from the active set.
- **Support several versions by listing several entries.** A profile lists a
  capability as an array, one entry per supported version. Negotiation picks
  the latest version both parties list (see
  [Capability Versions](../specification/overview/index.md#capability-versions)).

## Host and Document It

The schema, like a profile, must be reliably hosted (see
[Hosting](../specification/overview/index.md#hosting)):

- Serve it over HTTPS from the host that binds to your name.
- Do not redirect. Platforms do not follow redirects when fetching a `schema`
  URL.
- Send `Cache-Control` with `public` and a `max-age` of at least 60 seconds,
  and preferably an `ETag` or `Last-Modified` validator.

The `spec` URL in your profile entries points to human-readable documentation.
It must be HTTPS but may be served from any host. Describe there what your
extension adds and how each party should behave, including what happens when
the other party does not support it. If your extension extends more than one
capability, also describe what happens to its state as a resource moves
between them, for example when a cart becomes a checkout: what carries over,
what is recomputed, and what is dropped.

## Advertise and Negotiate

An extension is active in a session only when both parties advertise it. A
Business lists it in its profile under `capabilities`, with `extends` naming
its parents:

<!-- ucp:example schema=profile def=business_schema target=$.ucp.capabilities -->
```json
{
  "com.acme.shopping.loyalty": [
    {
      "version": "2026-09-01",
      "spec": "https://acme.com/docs/ucp/loyalty",
      "schema": "https://acme.com/ucp/schemas/loyalty.json",
      "extends": "dev.ucp.shopping.checkout"
    }
  ]
}
```

A Platform that supports the extension lists it in its own profile the same
way. Negotiation then works as follows (see
[Intersection Algorithm](../specification/overview/index.md#intersection-algorithm)):

1. The extension is kept only if both profiles list it with at least one
   version in common; the latest shared version is selected.
2. It is dropped if none of its parents is active, and dropping one extension
   can in turn drop extensions of it.
3. After schemas are fetched, it is dropped if the selected versions do not
   satisfy its `requires`.

Responses then declare the extension in `ucp.capabilities` whenever it extends
that response's capability (see
[Capability Declaration in Responses](../specification/overview/index.md#capability-declaration-in-responses)).

## Test Locally

[`ucp-schema`](https://github.com/Universal-Commerce-Protocol/ucp-schema)
composes and validates schemas the way a Platform does. Install it with
`cargo install ucp-schema`.

Lint your schema for syntax, broken references, and invalid annotations:

```bash
ucp-schema lint schemas/loyalty.json
```

Validate a sample payload against your extension before publishing it. Write a
payload whose `ucp.capabilities` lists the published UCP capability and your
extension, with your extension's `schema` set to the local file path.
`ucp-schema` skips the authority-binding check for local paths and fetches the
UCP base schema from `ucp.dev`. Fill in the elided base fields with valid
checkout data:

<!-- ucp:example skip reason="local development payload; references a local schema path" -->
```json
{
  "ucp": {
    "version": "2026-08-25",
    "capabilities": {
      "dev.ucp.shopping.checkout": [
        { "version": "2026-08-25", "schema": "https://ucp.dev/2026-08-25/schemas/shopping/checkout.json" }
      ],
      "com.acme.shopping.loyalty": [
        { "version": "2026-09-01", "schema": "schemas/loyalty.json", "extends": "dev.ucp.shopping.checkout" }
      ]
    },
    "payment_handlers": {}
  },
  "id": "checkout_123",
  "status": "incomplete",
  "currency": "USD",
  "line_items": [ ... ],
  "totals": [ ... ],
  "links": [ ... ],
  "loyalty": { "points_earned": 120 }
}
```

```bash
ucp-schema validate checkout-response.json --op read --response
```

Check that a payload violating your extension fails, not just that a valid one
passes. To inspect the composed schema, run `ucp-schema compose` on the same
payload. For a container capability, pass the operation (for example,
`--op search`) to select the shape to validate.

## Checklist

- [ ] Named in a reverse-domain namespace you control
- [ ] Schema `$id` and hosting on a host that binds to that name
- [ ] A `$defs` entry for each capability in `extends`, composed with `allOf`
- [ ] UCP base schemas referenced by absolute, versioned URL
- [ ] Container parents extended per shape
- [ ] `version` and `requires` declared
- [ ] Hosted over HTTPS, without redirects, with cacheable headers
- [ ] A `spec` page describing behavior and fallbacks
- [ ] Listed in Business and Platform profiles
- [ ] Linted and validated with `ucp-schema`, including a failing case
