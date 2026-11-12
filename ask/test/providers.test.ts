import assert from "node:assert/strict";
import { test } from "node:test";
import { createProvider, OpenAICompatibleProvider, sseData, WorkersAiProvider } from "../src/providers";

function streamOf(text: string): ReadableStream<Uint8Array> {
  const enc = new TextEncoder();
  const parts = text.match(/[\s\S]{1,7}/g) ?? [];
  return new ReadableStream({
    start(controller) {
      for (const p of parts) controller.enqueue(enc.encode(p));
      controller.close();
    },
  });
}

test("sseData yields each data payload even when frames are split across reads", async () => {
  const body = streamOf('data: {"a":1}\n\nevent: x\ndata: {"b":2}\n\ndata: [DONE]\n\n');
  const got: string[] = [];
  for await (const d of sseData(body)) got.push(d);
  assert.deepEqual(got, ['{"a":1}', '{"b":2}', "[DONE]"]);
});

test("OpenAI-compatible provider streams deltas and reports length finish", async () => {
  const originalFetch = globalThis.fetch;
  const captured: { url: string; body: Record<string, unknown>; auth: string | null } = { url: "", body: {}, auth: null };
  globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
    Object.assign(captured, {
      url: String(url),
      body: JSON.parse(String(init?.body)),
      auth: new Headers(init?.headers).get("authorization"),
    });
    const frames =
      'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n' +
      'data: {"choices":[{"delta":{"content":"lo"},"finish_reason":null}]}\n\n' +
      'data: {"choices":[{"delta":{},"finish_reason":"length"}]}\n\n' +
      "data: [DONE]\n\n";
    return new Response(streamOf(frames), { status: 200 });
  }) as typeof fetch;
  try {
    const provider = new OpenAICompatibleProvider("http://model.local/v1/", "my-model", "k");
    let text = "";
    const finish = await provider.stream([{ role: "user", content: "hi" }], (d) => (text += d), {
      maxTokens: 10,
      temperature: 0,
    });
    assert.equal(text, "Hello");
    assert.equal(finish, "length");
    assert.equal(captured.url, "http://model.local/v1/chat/completions");
    assert.equal(captured.body.model, "my-model");
    assert.equal(captured.body.stream, true);
    assert.equal(captured.auth, "Bearer k");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("Workers AI provider parses the binding's SSE stream", async () => {
  const ai = {
    run: async () => streamOf('data: {"response":"A"}\n\ndata: {"response":"B","usage":{"x":1}}\n\ndata: [DONE]\n\n'),
  };
  const provider = new WorkersAiProvider(ai, "@cf/meta/llama");
  let text = "";
  const finish = await provider.stream([{ role: "user", content: "hi" }], (d) => (text += d), {
    maxTokens: 10,
    temperature: 0,
  });
  assert.equal(text, "AB");
  assert.equal(finish, "stop");
});

test("createProvider validates configuration", () => {
  assert.throws(() => createProvider({ MODEL: "m", MODEL_PROVIDER: "openai-compatible" }), /MODEL_BASE_URL/);
  assert.throws(() => createProvider({ MODEL: "m", MODEL_PROVIDER: "workers-ai" }), /AI binding/);
  assert.throws(() => createProvider({ MODEL: "m", MODEL_PROVIDER: "nope" }), /unknown/);
  assert.equal(createProvider({ MODEL: "m", MODEL_BASE_URL: "http://x/v1" }).name, "openai-compatible:m");
});
