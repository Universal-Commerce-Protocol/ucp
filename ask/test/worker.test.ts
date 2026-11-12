import assert from "node:assert/strict";
import { test } from "node:test";
import worker, { type Env } from "../src/index";

/** End-to-end smoke test of the request pipeline with a fake KV, index and model server. */

const index = {
  format: 1,
  version: "v1",
  base_url: "https://ucp.dev/",
  pages: [{ url: "specification/shopping/checkout/", title: "Checkout Capability", summary: "Checkout sessions." }],
  chunks: [
    {
      id: "c1",
      url: "specification/shopping/checkout/#overview",
      page: "Checkout Capability",
      heading: "Overview",
      text: "Allows platforms to facilitate checkout sessions. The business remains the merchant of record.",
      words: 14,
    },
  ],
};

function fakeKv(): KVNamespace & { store: Map<string, string> } {
  const store = new Map<string, string>();
  return {
    store,
    get: async (key: string, type?: string) => {
      const v = store.get(key);
      if (v === undefined) return null;
      return type === "json" ? JSON.parse(v) : v;
    },
    put: async (key: string, value: string) => {
      store.set(key, value);
    },
  } as unknown as KVNamespace & { store: Map<string, string> };
}

function makeEnv(kv: KVNamespace): Env {
  return {
    ASK_KV: kv,
    MODEL_PROVIDER: "openai-compatible",
    MODEL: "test-model",
    MODEL_BASE_URL: "http://model.local/v1",
    TEMPERATURE: "0",
    MAX_OUTPUT_TOKENS: "100",
    INDEX_URLS: "https://ucp.dev/ask-index.json",
    ALLOWED_ORIGINS: "https://ucp.dev",
    TOP_K: "4",
    MAX_HISTORY_TURNS: "3",
    PER_IP_HOURLY_LIMIT: "5",
    DAILY_REQUEST_BUDGET: "100",
    ANSWER_CACHE_TTL: "60",
  };
}

const ctx = { waitUntil: (p: Promise<unknown>) => void p.catch(() => {}), passThroughOnException: () => {} } as ExecutionContext;

async function readEvents(res: Response): Promise<{ event: string; data: unknown }[]> {
  const text = await res.text();
  return text
    .split("\n\n")
    .filter(Boolean)
    .map((frame) => {
      const event = frame.match(/^event: (.*)$/m)?.[1] ?? "message";
      const data = JSON.parse(frame.match(/^data: (.*)$/m)?.[1] ?? "null");
      return { event, data };
    });
}

let modelCalls = 0;
const originalFetch = globalThis.fetch;
globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
  const u = String(url);
  if (u.endsWith("/ask-index.json")) return new Response(JSON.stringify(index), { status: 200 });
  if (u.endsWith("/chat/completions")) {
    modelCalls++;
    const body = JSON.parse(String(init?.body));
    assert.equal(body.messages[0].role, "system");
    assert.match(body.messages.at(-1).content, /\[1\] Checkout Capability > Overview/);
    const frames =
      'data: {"choices":[{"delta":{"content":"The business is merchant of record [1]."}}]}\n\n' +
      'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n';
    return new Response(frames, { status: 200 });
  }
  return originalFetch(url, init);
}) as typeof fetch;

function ask(env: Env, body: unknown, origin = "https://ucp.dev") {
  return worker.fetch(
    new Request("https://ask.ucp.dev/v1/ask", {
      method: "POST",
      headers: { "content-type": "application/json", origin, "cf-connecting-ip": "1.2.3.4" },
      body: JSON.stringify(body),
    }),
    env,
    ctx,
  );
}

test("answers with citations, then serves the repeat from cache without a model call", async () => {
  const kv = fakeKv();
  const env = makeEnv(kv);
  const first = await readEvents(await ask(env, { question: "Who is the merchant of record in checkout?" }));
  assert.equal(first[0].event, "meta");
  assert.deepEqual(first[0].data, { cached: false, model: "openai-compatible:test-model" });
  const text = first.filter((e) => e.event === "delta").map((e) => (e.data as { text: string }).text).join("");
  assert.match(text, /merchant of record \[1\]/);
  const done = first.find((e) => e.event === "done")?.data as { sources: { n: number; url: string }[] };
  assert.equal(done.sources[0].url, "https://ucp.dev/specification/shopping/checkout/#overview");
  assert.equal(modelCalls, 1);

  // Background cache write is fire-and-forget; wait a tick.
  await new Promise((r) => setTimeout(r, 20));
  const second = await readEvents(await ask(env, { question: "who is the merchant of record in checkout" }));
  assert.deepEqual(second[0].data, { cached: true, model: "openai-compatible:test-model" });
  assert.equal(modelCalls, 1);
});

test("off-topic questions get the scope reply without a model call", async () => {
  const env = makeEnv(fakeKv());
  const before = modelCalls;
  const events = await readEvents(await ask(env, { question: "write me a poem about autumn" }));
  assert.equal((events[0].data as { model: string }).model, "none");
  assert.equal(modelCalls, before);
});

test("rejects disallowed origins and bad input", async () => {
  const env = makeEnv(fakeKv());
  assert.equal((await ask(env, { question: "checkout?" }, "https://evil.example")).status, 403);
  assert.equal((await ask(env, { question: "hi" })).status, 400);
});

test("per-IP limit returns 429 with Retry-After", async () => {
  const env = makeEnv(fakeKv());
  env.PER_IP_HOURLY_LIMIT = "1";
  await ask(env, { question: "checkout merchant of record" });
  const res = await ask(env, { question: "checkout sessions for platforms" });
  assert.equal(res.status, 429);
  assert.ok(Number(res.headers.get("Retry-After")) > 0);
});
