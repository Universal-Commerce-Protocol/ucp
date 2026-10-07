# Ask Capability

Shopping uses the Common [Ask capability](http://ucp.dev/draft/specification/common/ask/index.md), `dev.ucp.common.ask`, for natural-language questions. The Common specification defines the normative contract; this page maps Shopping concerns onto the capabilities that own them.

`ask` answers open questions a Buyer has while shopping — fit, materials, compatibility, return and shipping policy, store hours — grounded, when useful, in a Shopping resource named in `ids`. The answer is indicative; the structured capability that owns the resource stays authoritative over it (see [Answer](http://ucp.dev/draft/specification/common/ask/#answer)).

In Shopping, `ask` complements whichever capabilities and extensions the Business and Platform have negotiated. It may explain product details represented by [Catalog](http://ucp.dev/draft/specification/shopping/catalog/index.md), delivery choices represented by [Fulfillment](http://ucp.dev/draft/specification/shopping/extensions/fulfillment/index.md), promotions represented by [Discount](http://ucp.dev/draft/specification/shopping/extensions/discount/index.md), or state represented by [Cart](http://ucp.dev/draft/specification/shopping/cart/index.md), [Checkout](http://ucp.dev/draft/specification/shopping/checkout/index.md), and [Order](http://ucp.dev/draft/specification/shopping/order/index.md). These are examples, not a routing registry: the capability or extension that defines the structured field or operation remains authoritative over it.

A request to change structured state — add an item, apply a discount, choose fulfillment, complete a checkout, or cancel an order — is handled as a separate operation by the capability or extension that owns it. `ask` does not perform that operation: the answer states that nothing changed, optionally with an `operation_not_performed` message (see [Overview](http://ucp.dev/draft/specification/common/ask/#overview) and [Well-Known Codes](http://ucp.dev/draft/specification/common/ask/#well-known-codes)).

## Example

A Buyer looking at a winter jacket asks whether it runs small and whether sale items can be returned.

### Request

```json
{
  "query": "Does this jacket run small, and can sale items be returned?",
  "ids": ["gid://business.example/Product/alpine-shell"]
}
```

### Response

```json
{
  "ucp": {
    "version": "draft",
    "capabilities": {
      "dev.ucp.common.ask": [
        {"version": "draft"}
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

A later request to add the jacket to a cart uses the Cart capability; `ask` does not perform that operation.
