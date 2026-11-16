import assert from "node:assert/strict";
import { test } from "node:test";
import { buildIndex, expandQuery, tokenize } from "../src/retrieval";
import {
  cacheSignature,
  isClearlyNotEnglish,
  normalizeQuestion,
} from "../src/limits";

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

test("reworded questions share a cache signature, opposite ones do not", () => {
  const sig = (q: string) => cacheSignature(q, tokenize(q));
  assert.equal(
    sig("What status values can a checkout have?"),
    sig("checkout status values")
  );
  assert.equal(
    sig("which status values does a checkout have"),
    sig("What are the checkout status values?")
  );
  assert.notEqual(
    sig("Can an agent buy without confirmation?"),
    sig("Can an agent buy with confirmation?")
  );
  assert.notEqual(sig("checkout status values"), sig("order status values"));
});

test("business questions pin the overview material written for businesses", () => {
  const biz = {
    ...raw,
    chunks: [
      ...raw.chunks,
      {
        id: "b1",
        url: "#for-developers",
        page: "Universal Commerce Protocol",
        heading: "For Developers",
        text: "For Businesses: UCP empowers businesses to meet customers wherever they are.",
        words: 12,
      },
      {
        id: "b2",
        url: "documentation/core-concepts/#key-goals-of-ucp",
        page: "Core Concepts",
        heading: "Key Goals of UCP",
        text: "Interoperability, discovery, security.",
        words: 4,
      },
    ],
  };
  const index = buildIndex([biz]);
  const ids = index
    .search("how does ucp even work? how will it help my business", 4)
    .map((h) => h.chunk.id);
  assert.ok(ids.includes("b1") && ids.includes("b2"));
  assert.ok(
    !index.search("checkout status values", 3).some((h) => h.chunk.id === "b1")
  );
});

test("how-to questions naming a platform retrieve the getting-started guide", () => {
  const data = {
    ...raw,
    pages: [
      {
        url: "specification/getting-started/",
        title: "Getting Started with UCP",
        summary: "Build a basic UCP server.",
      },
    ],
    chunks: [
      ...raw.chunks,
      {
        id: "gs",
        url: "specification/getting-started/#getting-started-with-ucp",
        page: "Getting Started with UCP",
        heading: "Getting Started with UCP",
        text: "This guide walks you through building a basic UCP server.",
        words: 10,
      },
      {
        id: "pl",
        url: "#co-developed-by-industry-leaders",
        page: "Universal Commerce Protocol",
        heading: "Co-developed by industry leaders",
        text: "Built by the industry.\nGoogle\nShopify\nTarget",
        words: 6,
      },
    ],
  };
  const index = buildIndex([data]);
  const ids = index
    .search("how can i do it inside shopify", 4)
    .map((h) => h.chunk.id);
  assert.ok(ids.includes("gs"), "getting started is retrieved");
  assert.ok(ids.includes("pl"), "partner list is retrieved");
});

// cspell:disable
test("non-English questions are detected, English ones are not", () => {
  for (const q of [
    "¿Cómo puedo implementar UCP en mi tienda?",
    "Comment faire un checkout avec UCP ?",
    "Wie kann ich UCP mit meinem Shop nutzen?",
    "UCPのチェックアウトはどのように動作しますか",
    "Как работает оформление заказа в UCP?",
    "كيف يعمل UCP",
    "Como posso fazer o checkout com UCP?",
  ]) {
    assert.equal(isClearlyNotEnglish(q), true, q);
  }
  for (const q of [
    "What status values can a checkout have?",
    "does target use ucp",
    "dev.ucp.shopping.checkout",
    "checkout status values",
    "Is Carrefour or El Corte Inglés part of UCP?",
    "hw do i start w/ ucp",
    "How do I handle the 3DS challenge für Zahlungen?",
  ]) {
    assert.equal(isClearlyNotEnglish(q), false, q);
  }
});
// cspell:enable

test("blended search finds a section that shares no words with the question", () => {
  const index = buildIndex([raw]);
  // Toy 2-d embeddings: c3 (order fulfillment) points along +x, others along +y.
  const ids = ["c1", "c2", "c3"];
  const data = Int8Array.from([0, 127, 0, 127, 127, 0]);
  index.setEmbeddings(ids, 2, data);
  // "checkout" matches c1 and c2 by keyword only; the query vector points at c3.
  const keyword = index.search("checkout", 3).map((h) => h.chunk.id);
  assert.ok(!keyword.includes("c3"));
  const blended = index
    .search("checkout", 3, { queryVector: [1, 0] })
    .map((h) => h.chunk.id);
  assert.ok(blended.includes("c3"), "the semantic match is included");
  assert.ok(blended.includes("c1"), "keyword matches are kept");
});
