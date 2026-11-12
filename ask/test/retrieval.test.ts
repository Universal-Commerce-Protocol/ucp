import assert from "node:assert/strict";
import { test } from "node:test";
import { buildIndex, expandQuery, tokenize } from "../src/retrieval";
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
  assert.equal(
    hits[0].chunk.url,
    "https://ucp.dev/latest/specification/shopping/order/#status"
  );
});

test("buildIndex prefers the fetch location over the recorded base_url", () => {
  const index = buildIndex([raw], ["https://ucp.dev/draft/"]);
  assert.ok(
    index.chunks[0].url.startsWith("https://ucp.dev/draft/specification/")
  );
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
  assert.equal(
    normalizeQuestion("  What is UCP?? "),
    normalizeQuestion("what is ucp")
  );
});

test("vocabularyCoverage separates docs questions from unrelated ones", () => {
  const index = buildIndex([raw]);
  assert.ok(
    index.vocabularyCoverage("how does checkout work for the merchant") >= 0.6
  );
  assert.ok(
    index.vocabularyCoverage("write me a poem about autumn leaves") < 0.6
  );
});

test("expandQuery maps everyday words to UCP vocabulary", () => {
  const q = expandQuery("How do I integrate my ecommerce store?");
  assert.match(q, /business/);
  assert.match(q, /implement/);
});

test("onboarding questions pin the getting-started page first", () => {
  const onboarding = {
    ...raw,
    pages: [
      {
        url: "specification/getting-started/",
        title: "Getting Started",
        summary: "Build a basic UCP server.",
      },
      {
        url: "specification/shopping/checkout/",
        title: "Checkout Capability",
        summary: "",
      },
    ],
    chunks: [
      ...raw.chunks,
      {
        id: "gs1",
        url: "specification/getting-started/#getting-started-with-ucp",
        page: "Getting Started",
        heading: "Getting Started with UCP",
        text: "This guide walks you through building a basic UCP server.",
        words: 10,
      },
      {
        id: "gs2",
        url: "specification/getting-started/#implementing-the-server",
        page: "Getting Started",
        heading: "Implementing the Server",
        text: "The server needs to handle create checkout and get checkout.",
        words: 10,
      },
    ],
  };
  const index = buildIndex([onboarding]);
  const hits = index.search(
    "How do I implement UCP on my self-hosted ecommerce store?",
    4
  );
  assert.equal(hits[0].chunk.id, "gs1");
  // A specific question is not pinned.
  const specific = index.search("order fulfillment status values", 3);
  assert.notEqual(specific[0]?.chunk.id, "gs1");
});

test("a question naming a partner company pins the partner list", () => {
  const withPartners = {
    ...raw,
    chunks: [
      ...raw.chunks,
      {
        id: "p1",
        url: "#co-developed-by-industry-leaders",
        page: "Universal Commerce Protocol",
        heading: "Co-developed by industry leaders",
        text: "UCP is built by the industry.\nGoogle\nShopify\nTarget\nWalmart",
        words: 10,
      },
      {
        id: "t1",
        url: "documentation/schema-authoring/#annotation",
        page: "Schema Authoring",
        heading: "The annotation contract",
        text: "The target attribute is a JSONPath that selects the target node. target target target.",
        words: 14,
      },
    ],
  };
  const index = buildIndex([withPartners]);
  assert.equal(index.search("does target use ucp", 3)[0].chunk.id, "p1");
  assert.deepEqual(
    index.organizationsIn("Is Shopify's checkout on UCP?").map((o) => o.name),
    ["shopify"]
  );
  assert.deepEqual(index.organizationsIn("what is the checkout status"), []);
});
