/**
 * ucp.dev "Ask AI" backend.
 *
 * POST /v1/ask  { question, history?: [{role, content}], page?: string }
 *   -> text/event-stream with events: meta, sources, delta, done, error
 * GET  /v1/health
 *
 * Cost model per answered question (see README.md for the table):
 *   - retrieval: free (BM25 in the Worker)
 *   - repeated question: free (answer served from KV, no model call)
 *   - otherwise one streamed Messages call with a cached system prefix,
 *     ~6 short excerpts, a capped output, and at most one extra tool round.
 */

import Anthropic from "@anthropic-ai/sdk";
import { checkLimits, normalizeQuestion, sha256Hex } from "./limits";
import {
  buildSystem,
  buildUserTurn,
  formatExcerpts,
  OFF_TOPIC_REPLY,
  SEARCH_TOOL,
  SEARCH_TOOL_NAME,
} from "./prompt";
import { type Chunk, type DocsIndex, loadIndex } from "./retrieval";

export interface Env {
  ANTHROPIC_API_KEY: string;
  ASK_KV: KVNamespace;
  MODEL: string;
  EFFORT: string;
  MAX_OUTPUT_TOKENS: string;
  INDEX_URLS: string;
  ALLOWED_ORIGINS: string;
  TOP_K: string;
  TOOL_TOP_K: string;
  MAX_HISTORY_TURNS: string;
  PER_IP_HOURLY_LIMIT: string;
  DAILY_REQUEST_BUDGET: string;
  ANSWER_CACHE_TTL: string;
}

interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
}

interface AskRequest {
  question: string;
  history?: HistoryMessage[];
  page?: string;
}

interface Source {
  n: number;
  title: string;
  heading: string;
  url: string;
}

interface CachedAnswer {
  answer: string;
  sources: Source[];
  model: string;
}

const MAX_QUESTION_CHARS = 600;
const MAX_HISTORY_MESSAGE_CHARS = 2000;

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin");
    const cors = corsHeaders(origin, env);

    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (url.pathname === "/v1/health") {
      return json({ ok: true, model: env.MODEL }, 200, cors);
    }
    if (url.pathname !== "/v1/ask" || request.method !== "POST") {
      return json({ error: "not found" }, 404, cors);
    }
    if (origin && !isAllowedOrigin(origin, env)) {
      return json({ error: "origin not allowed" }, 403, cors);
    }

    let body: AskRequest;
    try {
      body = (await request.json()) as AskRequest;
    } catch {
      return json({ error: "invalid JSON" }, 400, cors);
    }
    const question = (body.question ?? "").toString().trim();
    if (question.length < 3 || question.length > MAX_QUESTION_CHARS) {
      return json({ error: `question must be 3-${MAX_QUESTION_CHARS} characters` }, 400, cors);
    }
    const history = sanitizeHistory(body.history, Number(env.MAX_HISTORY_TURNS || 3));
    const page = typeof body.page === "string" ? body.page.slice(0, 300) : undefined;

    const index = await loadIndex(env.INDEX_URLS.split(",").map((s) => s.trim()).filter(Boolean));

    // 1. Repeated single-turn question: replay the cached answer, no model call.
    const cacheKey = history.length
      ? null
      : `a:${index.version}:${(await sha256Hex(normalizeQuestion(question))).slice(0, 32)}`;
    if (cacheKey) {
      const hit = await env.ASK_KV.get<CachedAnswer>(cacheKey, "json");
      if (hit) return streamCached(hit, cors);
    }

    // 2. Retrieval first: an empty result means nothing in the docs matches, so
    //    answer with the canned scope message and skip the model entirely.
    const retrievalQuery = history.length ? `${lastUserTurn(history)} ${question}` : question;
    let hits = index.search(retrievalQuery, Number(env.TOP_K || 6), {
      boostUrlPrefix: page ? page.split("#")[0] : undefined,
    });
    if (!hits.length && /\b(ucp|protocol|commerce)\b/i.test(retrievalQuery)) {
      // "What is UCP?" style questions have no distinctive terms; ground them
      // in the overview material instead of bouncing them.
      hits = index.search("universal commerce protocol overview core concepts", Number(env.TOP_K || 6));
    }
    if (!hits.length) return streamCached({ answer: OFF_TOPIC_REPLY, sources: [], model: "none" }, cors);

    // 3. Spend guards.
    const ip = request.headers.get("cf-connecting-ip") ?? "unknown";
    const limit = await checkLimits(
      env.ASK_KV,
      ip,
      Number(env.PER_IP_HOURLY_LIMIT || 40),
      Number(env.DAILY_REQUEST_BUDGET || 5000),
    );
    if (!limit.allowed) {
      return json(
        {
          error:
            limit.reason === "budget"
              ? "The assistant has reached today's usage budget. Please browse the docs or try again tomorrow."
              : "Too many questions from your network. Please wait a bit and try again.",
        },
        429,
        { ...cors, "Retry-After": String(limit.retryAfterSeconds) },
      );
    }

    // 4. Model call, streamed.
    const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY, maxRetries: 1, timeout: 60_000 });
    const { readable, writable } = new TransformStream();
    const writer = writable.getWriter();
    const sse = (event: string, data: unknown) =>
      writer.write(new TextEncoder().encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`));

    ctx.waitUntil(
      (async () => {
        try {
          const result = await answer(client, env, index, question, history, hits.map((h) => h.chunk), sse);
          if (cacheKey && result.cacheable) {
            await env.ASK_KV.put(
              cacheKey,
              JSON.stringify({ answer: result.text, sources: result.sources, model: env.MODEL } satisfies CachedAnswer),
              { expirationTtl: Number(env.ANSWER_CACHE_TTL || 604800) },
            );
          }
        } catch (err) {
          await sse("error", { message: describeError(err) });
        } finally {
          await writer.close();
        }
      })(),
    );

    return new Response(readable, { headers: { ...cors, ...SSE_HEADERS } });
  },
} satisfies ExportedHandler<Env>;

interface AnswerResult {
  text: string;
  sources: Source[];
  cacheable: boolean;
}

async function answer(
  client: Anthropic,
  env: Env,
  index: DocsIndex,
  question: string,
  history: HistoryMessage[],
  chunks: Chunk[],
  sse: (event: string, data: unknown) => Promise<void>,
): Promise<AnswerResult> {
  const provided: Chunk[] = [...chunks];
  const sources = toSources(provided);
  await sse("meta", { cached: false, model: env.MODEL });
  await sse("sources", sources);

  // Stable prefix: tools then system. Both are identical for every request
  // until the docs are redeployed, so the 1h cache entry is shared site-wide.
  const system: Anthropic.TextBlockParam[] = [
    { type: "text", text: buildSystem(index), cache_control: { type: "ephemeral", ttl: "1h" } },
  ];
  const messages: Anthropic.MessageParam[] = [
    ...history.map((m) => ({ role: m.role, content: m.content })),
    { role: "user", content: buildUserTurn(question, provided) },
  ];

  let text = "";
  let cacheable = true;
  const maxRounds = 2; // initial answer + at most one search_docs round

  for (let round = 0; round < maxRounds; round++) {
    const stream = client.messages.stream({
      model: env.MODEL,
      max_tokens: Number(env.MAX_OUTPUT_TOKENS || 900),
      system,
      tools: [SEARCH_TOOL],
      // After the single allowed search, forbid further tool calls.
      ...(round === maxRounds - 1 ? { tool_choice: { type: "none" as const } } : {}),
      output_config: { effort: env.EFFORT as "low" | "medium" | "high" },
      messages,
    });
    stream.on("text", (delta) => {
      text += delta;
      void sse("delta", { text: delta });
    });
    const message = await stream.finalMessage();

    if (message.stop_reason === "refusal") {
      const note = "\n\nI can't help with that request.";
      text += note;
      await sse("delta", { text: note });
      cacheable = false;
      break;
    }
    if (message.stop_reason === "max_tokens") {
      const note = "\n\n_(Answer truncated. Ask a narrower follow-up for more detail.)_";
      text += note;
      await sse("delta", { text: note });
      cacheable = false;
      break;
    }
    if (message.stop_reason !== "tool_use") break;

    const toolUses = message.content.filter((b): b is Anthropic.ToolUseBlock => b.type === "tool_use");
    messages.push({ role: "assistant", content: message.content });
    const results: Anthropic.ToolResultBlockParam[] = [];
    for (const use of toolUses) {
      let content = "No additional sections found.";
      if (use.name === SEARCH_TOOL_NAME) {
        const query = String((use.input as { query?: unknown }).query ?? "");
        const extra = index
          .search(query, Number(env.TOOL_TOP_K || 4), { exclude: new Set(provided.map((c) => c.id)) })
          .map((h) => h.chunk);
        if (extra.length) {
          content = formatExcerpts(extra, provided.length + 1);
          provided.push(...extra);
        }
      }
      results.push({ type: "tool_result", tool_use_id: use.id, content });
    }
    messages.push({ role: "user", content: results });
    sources.splice(0, sources.length, ...toSources(provided));
    await sse("sources", sources);
    await sse("delta", { text: "" });
  }

  const usedSources = sources.filter((s) => text.includes(`[${s.n}]`));
  await sse("done", { sources: usedSources });
  return { text, sources: usedSources, cacheable: cacheable && text.trim().length > 0 };
}

function toSources(chunks: Chunk[]): Source[] {
  return chunks.map((c, i) => ({ n: i + 1, title: c.page, heading: c.heading, url: c.url }));
}

function streamCached(hit: CachedAnswer, cors: Record<string, string>): Response {
  const enc = new TextEncoder();
  const parts = [
    `event: meta\ndata: ${JSON.stringify({ cached: true, model: hit.model })}\n\n`,
    `event: sources\ndata: ${JSON.stringify(hit.sources)}\n\n`,
    `event: delta\ndata: ${JSON.stringify({ text: hit.answer })}\n\n`,
    `event: done\ndata: ${JSON.stringify({ sources: hit.sources })}\n\n`,
  ];
  return new Response(enc.encode(parts.join("")), { headers: { ...cors, ...SSE_HEADERS } });
}

function sanitizeHistory(history: HistoryMessage[] | undefined, maxTurns: number): HistoryMessage[] {
  if (!Array.isArray(history)) return [];
  const clean = history
    .filter((m) => m && (m.role === "user" || m.role === "assistant") && typeof m.content === "string")
    .map((m) => ({ role: m.role, content: m.content.trim().slice(0, MAX_HISTORY_MESSAGE_CHARS) }))
    .filter((m) => m.content.length > 0);
  // Keep the last N user/assistant pairs and make sure the sequence
  // alternates and starts with a user turn, as the API requires.
  const tail = clean.slice(-maxTurns * 2);
  const out: HistoryMessage[] = [];
  for (const m of tail) {
    if (!out.length && m.role !== "user") continue;
    if (out.length && out[out.length - 1].role === m.role) {
      out[out.length - 1] = { role: m.role, content: `${out[out.length - 1].content}\n${m.content}` };
    } else {
      out.push(m);
    }
  }
  if (out.length && out[out.length - 1].role !== "assistant") out.pop();
  return out;
}

function lastUserTurn(history: HistoryMessage[]): string {
  for (let i = history.length - 1; i >= 0; i--) if (history[i].role === "user") return history[i].content;
  return "";
}

function describeError(err: unknown): string {
  if (err instanceof Anthropic.RateLimitError || err instanceof Anthropic.OverloadedError) {
    return "The assistant is busy right now. Please try again in a minute.";
  }
  if (err instanceof Anthropic.AuthenticationError) return "The assistant is misconfigured (authentication).";
  if (err instanceof Anthropic.APIConnectionError) return "The assistant could not reach its model provider.";
  if (err instanceof Anthropic.APIError) return `The assistant hit an upstream error (${err.status ?? "unknown"}).`;
  return "Something went wrong while answering.";
}

const SSE_HEADERS = {
  "Content-Type": "text/event-stream; charset=utf-8",
  "Cache-Control": "no-store",
  "X-Accel-Buffering": "no",
};

function isAllowedOrigin(origin: string, env: Env): boolean {
  return env.ALLOWED_ORIGINS.split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .includes(origin);
}

function corsHeaders(origin: string | null, env: Env): Record<string, string> {
  const headers: Record<string, string> = {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
  if (origin && isAllowedOrigin(origin, env)) headers["Access-Control-Allow-Origin"] = origin;
  return headers;
}

function json(data: unknown, status: number, headers: Record<string, string>): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...headers, "Content-Type": "application/json" },
  });
}
