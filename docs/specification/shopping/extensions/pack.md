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

# Pack Extension

!!! note "Draft - Work in Progress"
    This extension is in **draft status**. Implementers are cautioned that data
    models and semantics are under active iteration and may undergo breaking
    changes as the specification evolves.

## Overview

A catalog variant can be a case of six cans. The Pack extension lets a Business
state what that item holds: how many identical inner units, their net content,
and their drained weight.

Today a variant can carry one content quantity, in
[`unit_price.measure`](../catalog/index.md#distinction-from-unit-price). It
cannot say whether that quantity is net or drained, and it cannot say that the
item holds six cans. A Platform comparing canned goods from two Businesses has
no typed drained weight to compare.

This extension adds `pack` to a catalog variant in Search and Lookup responses,
including Get Product: the declared content of the physical item the variant
sells. `pack` is response-only.

**Dependencies:**

- One or more of the parent capabilities this extension extends: Catalog
  Search or Catalog Lookup.

`pack` is catalog data. It adds no operation, changes no existing field, and
does not appear on Cart, Checkout or Order lines. Out of scope: variants not
sold by `each`, variable-weight items, packaging types, identifiers per
packaging level, nesting deeper than one level, gross weight and dimensions.

## Discovery

Businesses advertise the extension in their profile:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.pack": [
        {
          "version": "{{ ucp_version }}",
          "extends": [
            "dev.ucp.shopping.catalog.search",
            "dev.ucp.shopping.catalog.lookup"
          ],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/extensions/pack",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/pack.json"
        }
      ]
    }
  }
}
```

A Business **MAY** extend only one of the two capabilities. A Business
**MUST NOT** return `pack` in a response unless this extension is negotiated
for that response's capability. A Platform that has not negotiated it receives
the same variants without `pack`.

## Schema

### Variant Pack

{{ extension_schema_fields('pack.json#/$defs/variant_pack', 'shopping/extensions/pack') }}

### Pack

{{ schema_fields('types/pack', 'shopping/extensions/pack') }}

## Semantics

### What `pack` describes

`pack` describes one `each`: the physical item one `quantity` step buys, such
as one case or one bottle. A Business **MUST NOT** return `pack` on a variant
whose [sale basis](../catalog/index.md#sale-basis-and-quantity-units) is not
`each`. `pack` changes neither `quantity` nor `price`, and `contained.count` is
not an ordering increment.

Its values are the Business's declarations, as on a label. They are current
catalog data, not measurements and not order terms.

### One level

Each measure is stated at one level:

- Measures on `pack` describe the whole item. A Platform **MUST NOT** infer
    from the absence of `contained` that the item is a single unit.
- `contained` states that the item holds `contained.count` identical inner
    units, such as six cans in a case. Measures in `contained` describe one
    inner unit. When `contained` is present, a Business **MUST NOT** state
    measures on `pack`, and the schema rejects them.

A Business **MUST NOT** send `contained` for an item whose inner units differ
or nest further. It states measures for the whole item on `pack` instead.

With `contained`, the measure for the whole item is `contained.count` times the
inner measure: `count × value × 10^-scale` of the inner `unit`, computed
exactly under the shared
[integer rules](../../overview/index.md#integer-range-and-ingestion). A
Business that has only the total for a case of identical units states the
per-unit value when the division is exact. Otherwise it states either the count
or the total.

### Values not stated

An omitted member is not stated. A Business with nothing to state omits `pack`,
and omits a value whose source is ambiguous, such as "oz" that may be a weight
or a volume.

A Platform **MUST NOT** use `net_content` in place of an omitted
`drained_weight`. A size name in a title or option, such as "#10", is not a
measure and never implies a weight.

### Relationship to `unit_price`

[`unit_price`](../catalog/index.md#distinction-from-unit-price) is optional,
and its `measure` is one content quantity that is not marked as net or
drained. `pack` states net content and drained weight as separate members, and
`unit_price.measure` need not equal either. `unit_price` stays authoritative: a
Platform never recomputes it, and this extension places no requirement on how a
Business sets it. A figure a Platform derives from `pack`, such as a price per
declared drained weight, is the Platform's own and does not replace
`unit_price`.

### Units

Measures follow the shared
[quantities and units](../../overview/index.md#quantities-and-units) contract,
including its rules for unit codes, `scale` and unrecognized units.

A Business **MUST** use a unit of mass, such as `GRM`, `KGM` or `LBR`, for
`drained_weight`. A Platform **MUST NOT** compare or convert a
`drained_weight` whose `unit` it does not recognize as a unit of mass.
`net_content` can be any quantity a label declares, such as a mass, a volume
or a count. Where
`net_content` and `drained_weight` share a `unit`, a Business **MUST NOT**
state a drained weight greater than the net content.

This extension defines no conversion factors. A Platform **MAY** convert
between units of mass it recognizes for its own comparison. The result is the
Platform's own figure.

## GS1 mapping

`pack` is not a GDSN hierarchy. In GDSN each packaging level is a separate
trade item record, and a record's `netContent` is the total for that trade
item.

| UCP member | GS1 attribute | Defined in |
| :--- | :--- | :--- |
| `net_content`, `drained_weight` on `pack` | [`netContent`](https://ref.gs1.org/voc/netContent), [`drainedWeight`](https://ref.gs1.org/voc/drainedWeight) of the trade item the variant sells | GS1 Web Vocabulary and GDSN |
| `contained.count` | `quantityOfNextLowerLevelTradeItem` | GDSN only ([Trade Item Implementation Guideline](https://ref.gs1.org/guidelines/tiig/)) |
| `net_content`, `drained_weight` in `contained` | `netContent`, `drainedWeight` of the next lower level trade item | GS1 Web Vocabulary and GDSN |

A case record's own `netContent` is the total for the case. It is not copied
into `contained`. GS1 `netContent` can repeat in several units; `net_content`
carries one value.

## Examples

Weights in these examples are illustrative, not taken from a real product.

### Case of six #10 cans

A case of roasted red peppers. Each can declares 3,000 g net and 1,800 g
drained, so the case holds 10,800 g drained.

<!-- ucp:example schema=shopping/pack def=lookup_response op=lookup target=$.products[0].variants[0].pack -->
```json
{
  "contained": {
    "count": 6,
    "net_content": { "value": 3000, "unit": "GRM", "display_text": "g" },
    "drained_weight": { "value": 1800, "unit": "GRM", "display_text": "g" }
  }
}
```

### Case of four 500 mL bottles

A case of hand soap. Drained weight does not apply, so the Business states no
`drained_weight`.

<!-- ucp:example schema=shopping/pack def=get_product_response op=get_product target=$.product.variants[0].pack -->
```json
{
  "contained": {
    "count": 4,
    "net_content": { "value": 500, "unit": "MLT", "display_text": "mL" }
  }
}
```

### In a search response

The same peppers sold by the case and by the single can. The single can states
its measures on `pack`; the case states them in `contained`. Prices are elided.

<!-- ucp:example schema=shopping/pack def=search_response op=search -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.catalog.search": [{ "version": "{{ ucp_version }}" }],
      "dev.ucp.shopping.pack": [{ "version": "{{ ucp_version }}" }]
    }
  },
  "products": [
    {
      "id": "prod_peppers",
      "title": "Roasted Red Peppers",
      "description": { "plain": "Fire-roasted red peppers in brine." },
      "price_range": {...},
      "variants": [
        {
          "id": "var_peppers_case",
          "title": "Case, 6/#10",
          "description": { "plain": "Case of six #10 cans." },
          "price": {...},
          "pack": {
            "contained": {
              "count": 6,
              "net_content": { "value": 3000, "unit": "GRM", "display_text": "g" },
              "drained_weight": { "value": 1800, "unit": "GRM", "display_text": "g" }
            }
          }
        },
        {
          "id": "var_peppers_can",
          "title": "Single #10 can",
          "description": { "plain": "One #10 can." },
          "price": {...},
          "pack": {
            "net_content": { "value": 3000, "unit": "GRM", "display_text": "g" },
            "drained_weight": { "value": 1800, "unit": "GRM", "display_text": "g" }
          }
        }
      ]
    }
  ]
}
```
