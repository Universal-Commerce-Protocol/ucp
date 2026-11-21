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

# B2B Catalog Extension

!!! note "Draft - Work in Progress"
    This extension is a **Working Draft** for proposal
    [#1110](https://github.com/Universal-Commerce-Protocol/ucp/issues/1110),
    submitted as Phase 1 input to the B2B Procurement charter
    ([#947](https://github.com/Universal-Commerce-Protocol/ucp/issues/947)).
    Field names, placement and namespace are open for Technical Council
    review and may change.

- **Capability Name:** `dev.ucp.shopping.b2b_catalog`

## Overview

A procurement agent shortlists suppliers on facts that a retail catalog does
not carry: the minimum order quantity, the price at a given quantity and trade
term, how long production takes, whether the seller is the manufacturer, which
certifications the product holds and how far they have been checked, and
where each technical value comes from. Without these facts an agent either
skips business-to-business suppliers or ranks them on incomplete data, and the
buyer cannot verify a claim before contacting the supplier.

This extension adds, all optional and response-only:

- `trade_terms` on a catalog variant — minimum order quantity and quantity
    brackets priced under an Incoterms® rule and a named place.
- `supply` on a catalog variant — sample and production lead time and
    production capacity.
- `specifications[]` on a catalog variant — technical attributes, each with a
    `source` pointer.
- `supplier_type` and `supplier_type_evidence` on the variant's `seller`.
- `certifications[]` on a catalog product — scheme, certificate number,
    expiry and a verification level with an optional evidence pointer.
- Search filters for these facts.

A Business that does not advertise this extension behaves exactly as it does
today.

**Dependencies:**

- Catalog Search and/or Catalog Lookup, which this extension extends.

### Relationship to other proposals

This draft deliberately does not redefine work that other proposals cover:

- **Price on request (#1110 item 1).** Items without a public unit price are
  addressed by the pricing states in
  [#969](https://github.com/Universal-Commerce-Protocol/ucp/issues/969) /
  draft PR [#1042](https://github.com/Universal-Commerce-Protocol/ucp/pull/1042).
  #1110 asks that an indicative range there can carry a visibility
  (`public` | `approved_buyers`, using the buyer account status in
  [#1047](https://github.com/Universal-Commerce-Protocol/ucp/issues/1047)) and
  a basis (`maker_list` | `dealer`). This extension adds no price-on-request
  fields of its own.
- **RFQ and sample requests (#1110 item 7).** These map onto the quotation
  lifecycle in [#929](https://github.com/Universal-Commerce-Protocol/ucp/issues/929)
  / draft PR [#930](https://github.com/Universal-Commerce-Protocol/ucp/pull/930)
  and the quote-to-checkout binding in
  [#845](https://github.com/Universal-Commerce-Protocol/ucp/issues/845).
- **Trade classification (#1110 item 6).** No new field is needed. A Business
  lists the HS code as a `categories[]` entry with `taxonomy: "hs"`, next to
  entries with `taxonomy: "unspsc"` or `taxonomy: "eclass"`.
- **Order multiple.** The ordering step is the variant's existing
  `quantity_unit.increment`.

## Discovery

Businesses advertise the extension in their profile:

<!-- ucp:example schema=profile def=business_schema extract=$.ucp.capabilities target=$.ucp.capabilities -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.shopping.b2b_catalog": [
        {
          "version": "{{ ucp_version }}",
          "extends": [
            "dev.ucp.shopping.catalog.search",
            "dev.ucp.shopping.catalog.lookup"
          ],
          "spec": "https://ucp.dev/{{ ucp_version }}/specification/shopping/extensions/b2b-catalog",
          "schema": "https://ucp.dev/{{ ucp_version }}/schemas/shopping/b2b_catalog.json"
        }
      ]
    }
  }
}
```

## Schema

### Source Pointer

{{ extension_schema_fields('b2b_catalog.json#/$defs/source_pointer', 'shopping/extensions/b2b-catalog') }}

### Specification

{{ extension_schema_fields('b2b_catalog.json#/$defs/specification', 'shopping/extensions/b2b-catalog') }}

### Trade Terms

{{ extension_schema_fields('b2b_catalog.json#/$defs/trade_terms', 'shopping/extensions/b2b-catalog') }}

### Price Bracket

{{ extension_schema_fields('b2b_catalog.json#/$defs/price_bracket', 'shopping/extensions/b2b-catalog') }}

### Supply Signals

{{ extension_schema_fields('b2b_catalog.json#/$defs/supply_signals', 'shopping/extensions/b2b-catalog') }}

### Supplier

{{ extension_schema_fields('b2b_catalog.json#/$defs/supplier', 'shopping/extensions/b2b-catalog') }}

### Certification

{{ extension_schema_fields('b2b_catalog.json#/$defs/certification', 'shopping/extensions/b2b-catalog') }}

## Facts and their sources

### Source pointer

Every specification may carry a `source`. Its `type` says who stated the
fact:

| `type` | Meaning | Pointer fields |
| --- | --- | --- |
| `supplier_authored` | Entered by the supplier as structured data. | Optional |
| `supplier_document` | Extracted from the supplier's own datasheet, catalog or product page. | `url` required; `page`, `section`, `quote` recommended |
| `inferred` | Derived by a Platform or Business from other facts. | Optional |

The pointer uses the same flat shape (`type`, `url`, `page`, `section`,
`quote`) proposed for compatibility claims in
[#385](https://github.com/Universal-Commerce-Protocol/ucp/issues/385) and for
product attributes in
[#401](https://github.com/Universal-Commerce-Protocol/ucp/issues/401), so that
attributes, compatibility claims and certificate evidence read the same way.

A Business MUST NOT mark safety-critical attributes, such as food contact,
medical use or pressure ratings, as `inferred`. A Platform SHOULD show the
source type alongside a value and SHOULD NOT present an `inferred` value as a
supplier statement.

### Certification verification

`verification.level` states how far a certification claim has been checked:

- `self_declared` — stated by the supplier only.
- `document_checked` — a copy of the certificate was compared with the claim.
- `third_party_verified` — confirmed with the issuer or by an independent
  party.

UCP does not run a verification authority. The fields state the claimed
level, who checked and when; a Platform decides how much weight to give them.
`evidence` is optional and is intended for certificates that are public. It
does not replace `valid_until` and `verified_at`, which stay dates that a
Platform can check.

## Trade terms

`min_order_quantity` and `brackets[].min_quantity` are counted in steps of the
variant's `quantity_unit`, like a line-item `quantity`. A bracket price is per
one whole `quantity_unit.unit`, like the variant's `price`, and applies from
its `min_quantity` under its `incoterm` and `named_place`. Bracket prices are
indicative: the binding price is the one confirmed in Checkout or in a
quotation.

The variant's `price` remains the price a Platform shows without further
context. A Business SHOULD set it to the price of the lowest bracket it is
willing to show publicly.

## Search filters

A Platform can narrow results with these filters. A Business that does not
support a filter MUST ignore it rather than fail the request.

<!-- ucp:example schema=shopping/b2b_catalog def=search_request op=search direction=request -->
```json
{
  "query": "sanitary ball valve DN50",
  "filters": {
    "max_min_order_quantity": 200,
    "certifications": ["3-A"],
    "min_verification_level": "document_checked",
    "supplier_types": ["manufacturer"],
    "incoterms": ["FOB", "CIF"],
    "max_production_lead_time": "P30D"
  }
}
```

## Example

A stainless-steel sanitary ball valve from a manufacturer. The maximum
operating temperature was extracted from the supplier's datasheet; the 3-A
certificate was compared with a copy of the certificate.

<!-- ucp:example schema=shopping/b2b_catalog def=get_product_response op=get_product target=$.product -->
```json
{
  "id": "gid://example/Product/sbv-dn50",
  "title": "Sanitary ball valve DN50, 316L",
  "description": { "plain": "Tri-clamp sanitary ball valve for dairy and beverage lines." },
  "categories": [
    { "value": "848180", "taxonomy": "hs" },
    { "value": "40141600", "taxonomy": "unspsc" }
  ],
  "price_range": {
    "min": { "amount": 2100, "currency": "USD" },
    "max": { "amount": 2400, "currency": "USD" }
  },
  "certifications": [
    {
      "scheme": "3-A",
      "certificate_id": "XXXX-XXXX",
      "issuer": "3-A SSI",
      "valid_until": "2027-09-30",
      "verification": {
        "level": "document_checked",
        "verified_at": "2026-11-10",
        "verified_by": "platform",
        "evidence": {
          "url": "https://example.com/certs/3a-xxxx.pdf",
          "page": 1,
          "quote": "Certificate No. XXXX-XXXX, valid until 30 September 2027"
        }
      }
    }
  ],
  "variants": [
    {
      "id": "gid://example/Variant/sbv-dn50-tc",
      "title": "DN50, tri-clamp ends",
      "description": { "plain": "DN50 316L body, PTFE seats, tri-clamp ends." },
      "price": { "amount": 2400, "currency": "USD" },
      "seller": {
        "name": "Example Valve Co.",
        "supplier_type": "manufacturer",
        "supplier_type_evidence": ["business_license", "factory_audit"]
      },
      "trade_terms": {
        "min_order_quantity": 100,
        "brackets": [
          { "min_quantity": 100, "price": { "amount": 2400, "currency": "USD" }, "incoterm": "FOB", "named_place": "CNNGB" },
          { "min_quantity": 500, "price": { "amount": 2100, "currency": "USD" }, "incoterm": "FOB", "named_place": "CNNGB" },
          { "min_quantity": 500, "price": { "amount": 2350, "currency": "USD" }, "incoterm": "CIF", "named_place": "DEHAM" }
        ]
      },
      "supply": {
        "sample_lead_time": "P7D",
        "production_lead_time": "P25D",
        "capacity": {
          "quantity": { "value": 20000, "unit": "C62", "display_text": "pieces" },
          "period": "P1M"
        }
      },
      "specifications": [
        {
          "key": "max_operating_temperature",
          "label": "Max. operating temperature",
          "value": { "value": 150, "unit": "CEL", "display_text": "°C" },
          "source": {
            "type": "supplier_document",
            "url": "https://example.com/datasheets/sbv-dn50.pdf",
            "page": 4,
            "section": "Technical data",
            "quote": "Max. operating temperature: 150 °C"
          }
        },
        {
          "key": "seat_material",
          "label": "Seat material",
          "value": "PTFE",
          "source": { "type": "supplier_authored" }
        }
      ]
    }
  ]
}
```

## Open questions for the Technical Council

1. **Namespace.** Should these fields live under `dev.ucp.shopping`, or under
   a namespace owned by the B2B Procurement Technical Council?
2. **Placement of supplier identity.** This draft extends the variant's
   `seller`. A product- or Business-level supplier profile may fit better.
3. **Bracket resolution.** Should the spec define how brackets combine with
   pricing states from #969 when a variant has no public `price`?
4. **Verification levels.** Are three levels enough, and should
   `verified_by` be an open vocabulary or a reverse-domain identifier?
