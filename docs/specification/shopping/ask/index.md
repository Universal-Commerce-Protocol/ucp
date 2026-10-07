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

# Ask Capability

Shopping uses the Common [Ask capability](../../common/ask/index.md),
`dev.ucp.common.ask`, for natural-language questions. The Common specification
defines the normative contract; this page maps Shopping concerns onto the
capabilities that own them.

`ask` answers open questions a Buyer has while shopping — fit, materials,
compatibility, return and shipping policy, store hours — grounded, when
useful, in a Shopping resource named in `ids`. The answer is indicative; the
structured capability that owns the resource stays authoritative over it (see
[Answer](../../common/ask/index.md#answer)).

In Shopping, `ask` complements whichever capabilities and extensions the
Business and Platform have negotiated. It may explain product details
represented by [Catalog](../catalog/index.md), delivery choices represented by
[Fulfillment](../extensions/fulfillment.md), promotions represented by
[Discount](../extensions/discount.md), or state represented by
[Cart](../cart/index.md), [Checkout](../checkout/index.md), and
[Order](../order/index.md). These are examples, not a routing registry: the
capability or extension that defines the structured field or operation remains
authoritative over it.

A request to change structured state — add an item, apply a discount, choose
fulfillment, complete a checkout, or cancel an order — is handled as a separate
operation by the capability or extension that owns it. `ask` does not perform
that operation: the answer states that nothing changed, optionally with an
`operation_not_performed` message (see
[Overview](../../common/ask/index.md#overview) and
[Well-Known Codes](../../common/ask/index.md#well-known-codes)).

## Example

A Buyer looking at a winter jacket asks whether it runs small and whether sale
items can be returned.

### Request

<!-- ucp:example schema=common/ask def=ask_request op=create direction=request -->
```json
{
  "query": "Does this jacket run small, and can sale items be returned?",
  "ids": ["gid://business.example/Product/alpine-shell"]
}
```

### Response

<!-- ucp:example schema=common/ask def=ask_response op=read -->
```json
{
  "ucp": {
    "version": "{{ ucp_version }}",
    "capabilities": {
      "dev.ucp.common.ask": [
        {"version": "{{ ucp_version }}"}
      ]
    }
  },
  "answer": {
    "plain": "The Alpine Shell runs true to size. Sale items can be returned within 14 days for store credit."
  },
  "links": [
    {
      "type": "product",
      "url": "https://business.example.com/products/alpine-shell",
      "title": "Alpine Shell Jacket",
      "id": "gid://business.example/Product/alpine-shell"
    },
    {
      "type": "refund_policy",
      "url": "https://business.example.com/policies/refunds",
      "title": "Refund Policy"
    }
  ]
}
```

A later request to add the jacket to a cart uses the Cart capability; `ask`
does not perform that operation.
