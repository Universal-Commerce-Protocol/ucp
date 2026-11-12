import assert from "node:assert/strict";
import { test } from "node:test";
import { buildIndex, tokenize } from "../src/retrieval";
import { normalizeQuestion } from "../src/limits";

const raw = {
  format: 1,
  version: "abc",
  base_url: "https://ucp.dev/latest/",
  pages: [],
  chunks: [
    {
      id: "c1",
      url: "specification/shopping/checkout/#overview",
      page: "Checkout Capability",
      heading: "Overview",
      text: "Allows platforms to facilitate checkout sessions. Capability name dev.ucp.shopping.checkout. The business remains the merchant of record.",
      words: 20,
    },
    {
      id: "c2",
      url: "specification/shopping/cart/#overview",
      page: "Cart Capability",
      heading: "Overview",
      text: "A cart holds line items before checkout. Capability name dev.ucp.shopping.cart.",
      words: 12,
    },
    {
      id: "c3",
      url: "specification/shopping/order/#status",
      page: "Order Capability",
      heading: "Fulfillment status",
      text: "Order fulfillment events report shipped, delivered and cancelled status values.",
      words: 11,
    },
  ],
};

test("tokenize keeps dotted identifiers and their parts", () => {
  const tokens = tokenize("What is dev.ucp.shopping.checkout?");
  assert.ok(tokens.includes("dev.ucp.shopping.checkout"));
  assert.ok(tokens.includes("checkout"));
  assert.ok(!tokens.includes("what"));
});

test("search ranks the matching capability first and prefixes URLs", () => {
  const index = buildIndex([raw]);
  const hits = index.search("fulfillment status values for an order", 3);
  assert.equal(hits[0].chunk.id, "c3");
  assert.equal(hits[0].chunk.url, "https://ucp.dev/latest/specification/shopping/order/#status");
});

test("buildIndex prefers the fetch location over the recorded base_url", () => {
  const index = buildIndex([raw], ["https://ucp.dev/draft/"]);
  assert.ok(index.chunks[0].url.startsWith("https://ucp.dev/draft/specification/"));
});

test("identifier queries hit the right page", () => {
  const index = buildIndex([raw]);
  assert.equal(index.search("dev.ucp.shopping.cart", 1)[0].chunk.id, "c2");
});

test("off-topic queries return nothing", () => {
  const index = buildIndex([raw]);
  assert.deepEqual(index.search("write me a poem about autumn leaves", 3), []);
});

test("exclude removes already-provided chunks", () => {
  const index = buildIndex([raw]);
  const hits = index.search("checkout", 3, { exclude: new Set(["c1"]) });
  assert.ok(hits.every((h) => h.chunk.id !== "c1"));
});

test("normalizeQuestion collapses trivial variants", () => {
  assert.equal(normalizeQuestion("  What is UCP?? "), normalizeQuestion("what is ucp"));
});
