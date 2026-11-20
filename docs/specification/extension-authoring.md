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

UCP already defines features such as checkout. Sometimes you need to share an
extra piece of information, such as a carbon estimate for an order. This guide
shows how to add that field, publish its schema on your own website, and tell
other UCP participants that you support it.

Here are the terms used in this guide:

- A **Business** is the merchant or service offering a UCP feature.
- A **Platform** is the app, shopping assistant, or other system using it.
- A **capability** is a UCP feature, such as checkout.
- An **extension** adds fields or behavior to an existing capability.
- A **profile** is the JSON document that lists what a participant supports.

These roles describe who offers and who uses a feature, not a particular
industry. For the protocol rules, see the
[Specification Overview](overview/index.md). If you are changing UCP itself
rather than publishing your own extension, see the
[Schema Authoring Guide](/documentation/schema-authoring/).

An extension is the right tool when you need to add typed fields to another
capability's requests or responses, and both parties need to agree to support
them. Consider the alternatives first:

- **Profile configuration.** If you only need to tell the other party how you
  are set up, a capability's `config` may already cover it.
- **Signals.** Environment data a Platform observes, for the Business's
  authorization and abuse prevention, belongs in
  [signals](overview/index.md#signals), keyed in your own namespace (for
  example, `com.example.device_id`), not in a new extension.
- **A new capability.** If your feature is not about augmenting an existing
  capability's payloads, it may be a capability of its own.

## Walkthrough: Add a Carbon Estimate to Checkout

Acme estimates the order's carbon footprint in whole grams of CO2 equivalent.
The Business returns the estimate; the Platform can display it, but does not
send or calculate it. The optional `methodology` identifies Acme's calculation
method. This is an estimate, not a certification.

The field is named `acme_carbon_estimate` to distinguish it from UCP's fields
and other vendors' additions. In particular, it does not reuse the existing
`loyalty` field from `dev.ucp.common.loyalty`.

This example uses the published UCP release `2026-08-25` and Acme's extension
version `2026-09-01`. Keep the UCP version in the schema URLs and declarations
consistent. Replace the fictional Acme name and domain when publishing your
own extension.

### 1. Write the Extension Schema

Install the validation tool and create a directory for the example:

```bash
cargo install ucp-schema
mkdir -p schemas
```

Save the following complete file as `schemas/carbon.json`:

<!-- extension-authoring-example: carbon-schema -->
<!-- ucp:example skip reason="third-party extension schema; checked by test_extension_authoring_examples.py" -->
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://acme.com/ucp/schemas/carbon.json",
  "name": "com.acme.shopping.carbon",
  "version": "2026-09-01",
  "title": "Acme Carbon Estimate",
  "description": "Adds Acme's carbon estimate for an order, in whole grams of CO2 equivalent.",
  "requires": {
    "protocol": { "min": "2026-08-25" },
    "capabilities": {
      "dev.ucp.shopping.checkout": { "min": "2026-08-25" }
    }
  },
  "$defs": {
    "acme_carbon_estimate": {
      "type": "object",
      "required": ["grams_co2e"],
      "properties": {
        "grams_co2e": { "type": "integer", "minimum": 0 },
        "methodology": { "type": "string" }
      }
    },
    "dev.ucp.shopping.checkout": {
      "title": "Checkout with Acme Carbon Estimate",
      "allOf": [
        { "$ref": "https://ucp.dev/2026-08-25/schemas/shopping/checkout.json" },
        {
          "type": "object",
          "properties": {
            "acme_carbon_estimate": {
              "$ref": "#/$defs/acme_carbon_estimate",
              "ucp_request": "omit"
            }
          }
        }
      ]
    }
  }
}
```

The top-level metadata identifies the extension: `$id` is its canonical schema
URL, `name` is its reverse-domain name, `version` is an ISO 8601 date you
control, and `title` and `description` explain it to readers. `requires`
declares the UCP protocol and capability versions it depends on (see
[Version Your Extension](#version-your-extension)).

`$defs` holds named schema parts. Here, `acme_carbon_estimate` describes the new
data and `dev.ucp.shopping.checkout` describes how it adds to checkout. `allOf`
means the same payload must satisfy both the checkout schema and the added
rules. It does not replace the checkout schema.

`ucp_request: "omit"` keeps the Business-computed field out of the resolved
request schema. The Business remains responsible for treating its own
calculated estimate as authoritative, rather than trusting unsolicited input.

### 2. Advertise Support on Both Sides

Save this minimal Business profile as `business-profile.json`:

<!-- extension-authoring-example: carbon-profile -->
<!-- ucp:example schema=profile def=business_schema -->
```json
{
  "ucp": {
    "version": "2026-08-25",
    "services": {},
    "capabilities": {
      "dev.ucp.shopping.checkout": [
        {
          "version": "2026-08-25",
          "spec": "https://ucp.dev/2026-08-25/specification/checkout",
          "schema": "https://ucp.dev/2026-08-25/schemas/shopping/checkout.json"
        }
      ],
      "com.acme.shopping.carbon": [
        {
          "version": "2026-09-01",
          "spec": "https://acme.com/docs/ucp/carbon",
          "schema": "https://acme.com/ucp/schemas/carbon.json",
          "extends": "dev.ucp.shopping.checkout"
        }
      ]
    },
    "payment_handlers": {}
  }
}
```

For this example, the Platform supports the same features and versions, so
save the same minimal declarations as `platform-profile.json`:

```bash
cp business-profile.json platform-profile.json
ucp-schema validate business-profile.json \
  --schema https://ucp.dev/2026-08-25/schemas/profile.json \
  --def business_schema --op read --response --json
ucp-schema validate platform-profile.json \
  --schema https://ucp.dev/2026-08-25/schemas/profile.json \
  --def platform_schema --op read --response --json
```

Both validations should report `"valid": true`. They check the profile's
structure, not whether the fictional Acme URLs are already hosted. These files
demonstrate capability agreement, not a complete checkout installation. Keep
the service endpoints, signing keys, and payment handlers needed by your real
deployment in its profiles.

Both profiles list Acme Carbon Estimate version `2026-09-01` and its checkout
parent, so the extension can be selected. If one side does not list it, the
parties can still use checkout without Acme Carbon Estimate. Negotiation works
as follows (see [Intersection Algorithm](overview/index.md#intersection-algorithm)):

1. The extension is kept only if both profiles list it with at least one
   version in common; the latest shared version is selected.
2. It is dropped if none of its parents is active, and dropping one extension
   can in turn drop extensions of it.
3. After schemas are fetched, it is dropped if the selected versions do not
   satisfy its `requires`.

Each response then declares the extension in `ucp.capabilities` when it extends
that response's capability (see
[Capability Declaration in Responses](overview/index.md#capability-declaration-in-responses)).
The profile advertises support; the response declares what was actually used.

### 3. Validate a Complete Response

Save this complete example as `checkout-response.json`. The local schema path
lets you test before hosting the Acme schema; the UCP base schema is fetched
from its published URL.

<!-- extension-authoring-example: carbon-response -->
<!-- ucp:example skip reason="local development payload; checked by test_extension_authoring_examples.py" -->
```json
{
  "ucp": {
    "version": "2026-08-25",
    "capabilities": {
      "dev.ucp.shopping.checkout": [
        {
          "version": "2026-08-25",
          "schema": "https://ucp.dev/2026-08-25/schemas/shopping/checkout.json"
        }
      ],
      "com.acme.shopping.carbon": [
        {
          "version": "2026-09-01",
          "schema": "schemas/carbon.json",
          "extends": "dev.ucp.shopping.checkout"
        }
      ]
    },
    "payment_handlers": {}
  },
  "id": "checkout_123",
  "status": "incomplete",
  "currency": "USD",
  "line_items": [
    {
      "id": "line_1",
      "item": { "id": "V100", "title": "Oxford Shirt", "price": 4500 },
      "quantity": 1,
      "totals": [
        { "type": "subtotal", "amount": 4500 },
        { "type": "total", "amount": 4500 }
      ]
    }
  ],
  "totals": [
    { "type": "subtotal", "amount": 4500 },
    { "type": "total", "amount": 4500 }
  ],
  "links": [
    { "type": "terms_of_service", "url": "https://merchant.example.com/terms" },
    { "type": "privacy_policy", "url": "https://merchant.example.com/privacy" }
  ],
  "acme_carbon_estimate": { "grams_co2e": 120 }
}
```

From the directory containing these files, run:

```bash
ucp-schema lint schemas/carbon.json
ucp-schema compose checkout-response.json --pretty
ucp-schema validate checkout-response.json --op read --response --json
```

The validation should succeed and report `"valid": true`. `compose` lets you
inspect the combined schema. For local schema paths, the tool skips the
name/host binding check; that shortcut is only for local development. A
published declaration must use the matching HTTPS URL shown in the profiles.

The tool needs network access for published UCP schemas. To use local copies
instead, configure `--schema-local-base` and `--schema-remote-base` when
composing, resolving, or validating.

### 4. Check a Failing Case Too

Make a second response with an invalid estimate:

```bash
python3 -c '
import json
from pathlib import Path
response = json.loads(Path("checkout-response.json").read_text())
response["acme_carbon_estimate"]["grams_co2e"] = -1
Path("checkout-bad.json").write_text(json.dumps(response))
'
ucp-schema validate checkout-bad.json --op read --response --json
```

This should fail because `grams_co2e` cannot be negative. The command returns
exit code `1` and reports `"valid": false`. A passing case alone does not show
that your extension's rules are being applied. Repeat these checks whenever
you change the schema, not only before its first publication.

Also inspect the request view:

```bash
ucp-schema resolve checkout-response.json --request --op create --pretty
```

The resolved create-request schema should not define the Business-computed
`acme_carbon_estimate` field. The annotations describe which fields belong in a
message; open-object validation can still permit unknown fields, so do not
mistake annotation resolution for a rule that automatically rejects every
extra input.

### 5. Publish the Files and Explain the Behavior

You publish and maintain your extension yourself, under your own namespace.
Its schema and specification are not added to the UCP repository, and you do
not need UCP's approval to publish them (see
[Namespace Governance](overview/index.md#namespace-governance)).

Host the schema at the URL declared in the profiles. Like a profile, it must
be reliably hosted (see [Hosting](overview/index.md#hosting)):

- Serve it over HTTPS from the host that binds to your name.
- Do not redirect. Platforms do not follow redirects when fetching a `schema`
  URL.
- Send `Cache-Control` with `public` and a `max-age` of at least 60 seconds;
  do not use `private`, `no-store`, or `no-cache` directives.
- Preferably include an `ETag` or `Last-Modified` validator.

Write the human-readable page at the `spec` URL in your profiles. It must be
HTTPS but may be served from any host. For this example, explain when the
estimate is calculated, what `methodology` identifies, and what happens when
the extension is unsupported or the estimate is absent. The Platform must not
treat an absent estimate as zero. If your extension extends more than one
capability, also describe what happens to its state as a resource moves
between them, for example when a cart becomes a checkout: what carries over,
what is recomputed, and what is dropped.

Then check the published copy. After replacing the fictional Acme name and
domain with your own, point the extension's `schema` in
`checkout-response.json` at its hosted URL instead of the local path and
validate again:

```bash
ucp-schema validate checkout-response.json --op read --response --json
curl --silent --show-error --dump-header - --output /dev/null \
  https://acme.com/ucp/schemas/carbon.json
```

The hosted validation exercises the name/host check that local paths skip.
Confirm that a fresh request to the URL answers `200` directly, without a
redirect, and sends the cache headers above. Do not use `curl --location` to
hide a redirect.

If your extension proves useful to many Businesses and Platforms, it can
become a candidate for the core protocol. UCP keeps the core light: new
functionality starts self-hosted under a vendor namespace and is proposed for
`dev.ucp.*` once it has broad, multi-party adoption, through the Enhancement
Proposal process (see [Contributing](/documentation/contributing/)).

## Choose a Name

Extension names follow the same rules as every capability name (see
[Namespace Governance](overview/index.md#namespace-governance)):

- Use the format `{reverse-domain}.{service}.{capability}`, for example
  `com.acme.shopping.carbon`.
- Use a domain you control. The `dev.ucp.*` namespace is reserved for the UCP
  governing body.
- Choose a registrable domain you exclusively control, not a shared suffix
  such as a hosting platform's subdomain.

The schema host must match the domain represented by the name. This is called
*authority binding*: the Platform checks the name and host before fetching the
schema, and rejects the extension if they do not match (see
[Authority Binding](overview/index.md#authority-binding)).
For `com.acme.shopping.carbon`, a schema served from `acme.com` matches. One
served from `www.acme.com` does not, because `www` is not part of the name, and
an `acme.com` URL that redirects to `www` fails too, because Platforms do not
follow redirects. A shared CDN host such as `cdn.example.net` does not match.

## Write the Schema

### Extend a Capability

For each capability your extension extends, add a `$defs` entry keyed by that
capability's full name. The entry composes onto the capability's schema with
`allOf`: it references the base schema, then adds your fields (see
[Extension Schema Pattern](overview/index.md#extension-schema-pattern)).

Because your schema is hosted on your domain, reference UCP base schemas by
absolute URL, including the UCP release in the path.

The [complete carbon schema](#1-write-the-extension-schema) shows this pattern
with a published UCP URL. Use the release your extension supports; do not mix
schema URLs from one release with capability declarations from another.

Put the types your extension introduces (`acme_carbon_estimate` above) in their
own `$defs` entries and reference them from the composed entry, so they can be
reused across parents.

### Control Request and Response Visibility

A capability usually uses one object for both requests and responses. Fields
that only one side sends carry visibility annotations: `ucp_request` and
`ucp_response`, with the values `omit`, `optional`, or `required`, either for
every operation or per operation (`create`, `read`, `update`, `complete`).

The walkthrough uses `ucp_request: "omit"` for a Business-computed field. A
Platform-supplied reference that is optional on create and update, but omitted
on complete, could instead use:

<!-- ucp:example skip reason="extension schema fragment" -->
```json
"acme_reference": {
  "type": "string",
  "ucp_request": { "create": "optional", "update": "optional", "complete": "omit" }
}
```

See [Visibility Rules](https://github.com/Universal-Commerce-Protocol/ucp-schema#visibility-rules)
in the `ucp-schema` documentation for the full resolution rules.

### Extend More Than One Capability

To extend several capabilities, declare each in `extends` and add a `$defs`
entry for each (see
[Multi-Parent Extensions](overview/index.md#multi-parent-extensions)).
Each entry can add different fields; for example, a carbon-estimate extension
might show a preview on cart and a revised estimate on checkout:

<!-- ucp:example skip reason="extension schema example; hosted outside ucp.dev" -->
```json
"$defs": {
  "dev.ucp.shopping.cart": {
    "allOf": [
      { "$ref": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/cart.json" },
      { "type": "object", "properties": { "acme_carbon_preview": { "$ref": "#/$defs/acme_carbon_estimate", "ucp_request": "omit" } } }
    ]
  },
  "dev.ucp.shopping.checkout": {
    "allOf": [
      { "$ref": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/checkout.json" },
      { "type": "object", "properties": { "acme_carbon_estimate": { "$ref": "#/$defs/acme_carbon_estimate", "ucp_request": "omit" } } }
    ]
  }
}
```

The extension stays active as long as at least one of its parents is
negotiated, and each response lists it only when it extends that response's
capability (see
[Response Capability Selection](overview/index.md#response-capability-selection)).

### Extend a Container Capability

Some capabilities use different objects for requests and responses. Catalog
search, for example, takes a query and returns a list of products. Such a
capability's schema is a container: each message body sits under `$defs`, named
`{operation}_{direction}` (`search_request`, `search_response`).

To extend a container, mirror its shape names under your `$defs` entry and
compose each one onto the base shape:

<!-- extension-authoring-example: container-pattern -->
<!-- ucp:example skip reason="extension schema fragment; checked by test_extension_authoring_examples.py" -->
```json
{
  "$defs": {
    "dev.ucp.shopping.catalog.search": {
      "$defs": {
        "search_response": {
          "allOf": [
            { "$ref": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/catalog_search.json#/$defs/search_response" },
            {
              "type": "object",
              "properties": {
                "products": { "items": { "$ref": "#/$defs/product_with_carbon" } }
              }
            }
          ]
        }
      }
    }
  }
}
```

Here `product_with_carbon` is your own `$defs` entry that composes onto the UCP
product type and adds your product fields. Mirror only the shapes you change,
and pass the operation, such as `--op search`, when validating or resolving.
Check the nesting with a failing case: in `ucp-schema` 1.4.1, a container entry
that composes directly onto a response with `allOf`, without the nested shape
names, is not applied even though lint and validation report no error. See
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
  "com.acme.shopping.carbon": {
    "business_schema": {
      "allOf": [
        { "$ref": "https://ucp.dev/{{ ucp_version }}/schemas/capability.json#/$defs/business_schema" },
        {
          "properties": {
            "config": {
              "type": "object",
              "properties": { "methodology": { "type": "string" } }
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
[Actions](overview/index.md#actions)). Each Action type's key must be in your
namespace, and your specification must define its full contract; see
[Extension-Declared Action Types](/documentation/schema-authoring/#extension-declared-action-types)
for what to cover.

### Avoid Composition Pitfalls

`allOf` only ever adds constraints, which shapes what an extension can do:

- **You can add fields, not loosen existing ones.** A composed schema must
  satisfy the base and your extension, so you cannot widen a base type, relax a
  base requirement, or add a value to a closed `enum`. See
  [Extensibility and Forward Compatibility](/documentation/schema-authoring/#extensibility-and-forward-compatibility).
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
[Component Versioning and Release Snapshots](overview/index.md#component-versioning-and-release-snapshots)):

- **Your version is your own.** It is an ISO 8601 date that you advance on your
  own schedule; it never has to match `ucp.version`.
- **Declare what you depend on in `requires`.** `requires.protocol` constrains
  the selected `ucp.version`, and `requires.capabilities` constrains the
  selected versions of the capabilities you extend. Each constraint has a `min`
  and an optional `max`. Every key in `requires.capabilities` must also be a
  `$defs` key in your schema (see
  [Version Requirements](overview/index.md#version-requirements)).
- **`requires` verifies; it does not select.** Versions are chosen by
  negotiation first. An extension whose requirements the chosen versions do not
  satisfy is dropped from the active set.
- **Support several versions by listing several entries.** A profile lists a
  capability as an array, one entry per supported version. Negotiation picks
  the latest version both parties list (see
  [Capability Versions](overview/index.md#capability-versions)).

## Checklist

- [ ] Named in a reverse-domain namespace you control
- [ ] Schema `$id` and hosting on a host that binds to that name
- [ ] A `$defs` entry for each capability in `extends`, composed with `allOf`
- [ ] UCP base schemas referenced by absolute, versioned URL
- [ ] Container parents extended per shape, checked with a failing case
- [ ] `version` and `requires` declared
- [ ] Hosted over HTTPS, without redirects, with cacheable headers
- [ ] Hosted schema validated after replacing local paths with its URL
- [ ] A `spec` page describing behavior and fallbacks
- [ ] Listed in Business and Platform profiles, with both profiles validated
- [ ] Linted and validated with `ucp-schema`, including a failing case
