# Platform Notes — Magento 2 / Adobe Commerce

> **Applies to:** Adobe Commerce (Magento 2.4.x), both on-premises and Adobe Commerce Cloud.
> This document covers the specific mapping decisions required when normalizing
> Magento 2 catalog data into UCP-compliant types.

## The configurable -> simple product expansion problem

Magento 2 has two product types relevant to UCP normalization:

- **Configurable product**: the parent entity (e.g., "T-Shirt") with no
  inventory of its own. Holds the shared attributes and the product URL.
- **Simple product**: a child variant (e.g., "T-Shirt - Red, Size M") that
  carries the actual SKU, price, and inventory.

UCP's `UCPProduct` type maps to a simple product, not a configurable product.
An ACO implementing Magento -> UCP normalization **must** resolve configurable
products into their constituent simple variants before emitting `UCPProduct`
events. Emitting a configurable product directly will produce `inventory.available: 0`
(configurable products carry no stock), causing agents to incorrectly treat
all variants as out-of-stock.

### Recommended mapping

```
Magento Configurable Product
├── id: 4821 (parent - no inventory, no price)
├── attribute_set: clothing
└── configurable_options: [color, size]
    ├── Simple Product: id: 4822, sku: TSHIRT-RED-M, price: $29.99
    │   inventory: { qty: 45 }
    ├── Simple Product: id: 4823, sku: TSHIRT-RED-L, price: $29.99
    │   inventory: { qty: 12 }
    └── Simple Product: id: 4824, sku: TSHIRT-BLUE-M, price: $29.99
        inventory: { qty: 0 }
```

Maps to UCP as:

```json
{
  "ucpId": "magento::4822",
  "sourceId": "4822",
  "sourcePlatform": "magento",
  "title": "Classic T-Shirt - Red / M",
  "status": "active",
  "price": { "amount": 29.99, "currency": "USD" },
  "inventory": { "available": 45, "reserved": 0, "locationId": "default" },
  "attributes": { "color": "Red", "size": "M" }
}
```

The parent configurable product (id: 4821) does not produce a `UCPProduct` event.

## Multi-Source Inventory (MSI) and local inventory

Magento 2.3+ introduced Multi-Source Inventory (MSI), enabling per-location stock.
When MSI is enabled, each simple product has a `stocks` array with quantities per source:

```json
{
  "sku": "TSHIRT-RED-M",
  "stocks": [
    { "source_code": "warehouse-east", "quantity": 30, "status": 1 },
    { "source_code": "store-brooklyn", "quantity": 15, "status": 1 }
  ]
}
```

This maps directly to the `UCPInventorySnapshot.localInventory` extension (RFC #375),
enabling BOPIS / pickup availability queries:

```json
{
  "snapshot": { "available": 45, "locationId": "all-sources" },
  "localInventory": [
    {
      "storeId": "store-brooklyn",
      "storeName": "Brooklyn Flagship",
      "pickupAvailable": true,
      "pickupLeadTimeMinutes": 30
    }
  ]
}
```

## Webhook authentication

Magento 2 webhook payloads are HMAC-SHA256 signed using the integration's
consumer secret. Validate using `X-Magento-Webhook-Signature` (Magento 2.4.7+)
or `X-Magento-Signature` (earlier versions) before processing any payload.

A Magento -> UCP adapter **must not** process unsigned webhooks in production.
An unsigned payload that claims a product is now `status: inactive` could be
used to suppress valid products from agent discovery.

## Read-only principle

A Magento -> UCP ACO adapter reads from Magento via REST API and translates to
UCP. It does not write back to Magento. The Magento store remains the Merchant
of Record. Price changes, inventory adjustments, and product updates originate
in Magento and flow out through the ACO pipeline - never the reverse.

## Reference implementation

An open-source Magento 2 -> UCP adapter implementing these patterns is available
at: [github.com/Goofre-Agentic-Commerce-Orchestrator/agentic_commerce_orchestrator_ACO](https://github.com/Goofre-Agentic-Commerce-Orchestrator/agentic_commerce_orchestrator_ACO)

The `MagentoAdapterPlugin` covers: configurable -> simple expansion, MSI local
inventory, HMAC webhook validation, and GTIN enrichment before GMC sync.
