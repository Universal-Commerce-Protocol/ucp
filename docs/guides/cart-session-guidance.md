---
title: "Cart Session Persistence — Implementation Guidance"
---

# Cart Session Persistence — Implementation Guidance

!!! note "Non-normative"
    This section provides implementation guidance and is not part of the normative specification.

The cart capability defines `expires_at` but intentionally leaves session persistence to implementers. This guide captures recommended patterns.

## Recommended TTL Ranges

| Use case | Recommended minimum TTL | Notes |
|---|---|---|
| Quick-service / food ordering | 15–30 minutes | Short sessions; items may go out of stock |
| Retail / e-commerce | 1–24 hours | Balance availability holds with buyer convenience |
| B2B / procurement | 1–7 days | Complex carts built over multiple sessions |

Businesses SHOULD set `expires_at` on cart responses. Platforms SHOULD warn the buyer before expiry when feasible.

## Session Resumption

- **Cart ID is the canonical resumption handle.** A buyer resumes a cart by providing its `id`, regardless of transport (MCP, REST, etc.).
- **Cross-transport persistence**: A cart created over MCP SHOULD be retrievable over REST, and vice versa. The cart ID is transport-agnostic.
- **Buyer binding** is a business decision. Some businesses may scope carts to a buyer identity; others (especially guest-friendly merchants) may allow any session with the cart ID to resume.

## Expiry Handling

- Expired carts SHOULD return a specific error code (e.g., `cart_expired`) rather than a generic 404, so platforms can distinguish "this cart existed but expired" from "this cart ID was never valid."
- Platforms receiving a `cart_expired` error SHOULD offer to recreate the cart with the same items, rather than silently failing.
- Businesses MAY implement grace periods (accepting updates to recently-expired carts) but this is not required.

## Reconnection in Agent Scenarios

Voice and chat agents may lose connectivity or the buyer may return after a pause:

- If the cart is still valid (`expires_at` in the future), the agent resumes by calling `update_cart` with the same cart ID.
- If the cart has expired, the agent receives the `cart_expired` error and can recreate with the buyer's previously selected items.
- Agents SHOULD proactively check `expires_at` and warn the buyer ("Your cart expires in 5 minutes — shall I complete the order?").
