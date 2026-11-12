/**
 * ucp.dev "Ask AI" backend.
 *
 * POST /v1/ask  { question, history?: [{role, content}], page?: string }
 *   -> text/event-stream with events: meta, sources, delta, done, error
 * GET  /v1/health
 *
 * Cost model per answered question (see README.md):
 *   - retrieval: free (BM25 in the Worker)
 *   - repeated question: free (answer served from KV, no model call)
 *   - otherwise one streamed chat completion against your own model with a
 *     stable system prefix, ~8 short excerpts and a capped output.
 *
 * The model is pluggable (src/providers.ts): any OpenAI-compatible server
 * (vLLM, Ollama, TGI, llama.cpp, ...) or Cloudflare Workers AI.
 */

import { checkLimits, normalizeQuestion, sha256Hex } from "./limits";
import { exportDay, type LogEntry, newLogId, recordFeedback, today, writeLog } from "./log";
import { buildMessages, OFF_TOPIC_REPLY } from "./prompt";
import { type ChatMessage, createProvider, ProviderError, type WorkersAiBinding } from "./providers";
import { type Chunk, type DocsIndex, loadIndex, tokenize } from "./retrieval";

export interface Env {
  ASK_KV: KVNamespace;
  AI?: WorkersAiBinding;
  MODEL_PROVIDER: string;
  MODEL: string;
  MODEL_BASE_URL?: string;
  MODEL_API_KEY?: string;
  TEMPERATURE: string;
  MAX_OUTPUT_TOKENS: string;
  INDEX_URLS: string;
  ALLOWED_ORIGINS: string;
  TOP_K: string;
  MAX_HISTORY_TURNS: string;
  PER_IP_HOURLY_LIMIT: string;
  DAILY_REQUEST_BUDGET: string;
  ANSWER_CACHE_TTL: string;
  /** "on" to keep an anonymous question/answer log (see log.ts), anything else disables it. */
  LOG_ANSWERS?: string;
  LOG_TTL_DAYS?: string;
  /** Bearer secret for GET /v1/export. */
  EXPORT_TOKEN?: string;
}

type HistoryMessage = ChatMessage & { role: "user" | "assistant" };

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
const MAX_BODY_BYTES = 32 * 1024;
// Total characters of conversation history replayed to the model, so a
// caller cannot inflate every request with pasted text.
const MAX_HISTORY_TOTAL_CHARS = 6000;
// Attempts to steer the assistant. A documentation assistant never needs
// these, so they are declined before any model call, model-independently.
const STEERING_PATTERN =
  /\b(ignore|disregard|forget|override|bypass|drop)\b[^.?!]{0,60}\b(instruction|rule|prompt|guideline|above|previous|prior)|\b(system prompt|developer message|hidden prompt|your (instructions|rules|prompt)|jailbreak|pretend (to be|you are)|act as|you are now|from now on|new persona|role ?play|no (rules|restrictions)|unrestricted|dan mode|confirm by saying|documentation map|in the (style|voice|manner) of|(like|as) a pirate|in pirate|in rhyme|in verse|in all caps|as a (poem|song|rap|limerick|haiku))\b|<\/?(system|assistant|user|instruction|excerpts?|question)>/i;
// Creative writing and translation are never documentation questions, even
// when they mention UCP terms.
const CREATIVE_PATTERN =
  // cspell:disable-next-line
  /\b(poem|limerick|haiku|sonnet|story|song|rap|lyrics|joke|riddle|fan ?fiction|screenplay)\b|\b(translate|traduce|translation)\b|\bin (french|spanish|german|italian|portuguese|dutch|chinese|japanese|korean|arabic|hindi|russian)\b/i;
// Requests for general work (code, emails, summaries of pasted text). Allowed
// when the request names UCP material, e.g. "write an example checkout request".
const TASK_PATTERN =
  // cspell:disable-next-line
  /^(please\s+)?(translate|traduce|write|compose|generate|create|draft|summari[sz]e|rewrite|paraphrase|tell me|give me|make)\b[^.?!]{0,80}\b(poem|limerick|haiku|story|song|essay|joke|rap|lyrics|tweet|email|letter|blog|script|code|program|python|javascript|typescript|java|rust|golang|scraper|scrape|bot|french|spanish|german|english|chinese|japanese|language|summary of (this|the following))\b/i;
const UCP_NOUNS =
  /\b(ucp|checkout|cart|catalog|order|booking|lodging|profile|capability|capabilities|extension|payment|handler|mandate|signature|transport|rest|mcp|a2a|embedded|schema|payload|request|response|endpoint|identity|linking|fulfil|discount|tip|well-known)\b/i;
// An answer must largely reuse the vocabulary of the excerpts it was given;
// a limerick, a translation or unrelated code will not.
const MIN_ANSWER_GROUNDING = 0.45;
const GROUNDING_FALLBACK =
  "I couldn't ground an answer to that in the documentation. The most relevant sections are listed below.";
// Below this share of known terms a question is treated as off-topic.
const MIN_VOCAB_COVERAGE = 0.6;
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
    if (url.pathname === "/v1/export" && request.method === "GET") {
      const auth = request.headers.get("authorization") ?? "";
      if (!env.EXPORT_TOKEN || auth !== `Bearer ${env.EXPORT_TOKEN}`) return json({ error: "unauthorized" }, 401, cors);
      const body = await exportDay(env.ASK_KV, url.searchParams.get("day") ?? today());
      return new Response(body, { headers: { ...cors, "Content-Type": "application/x-ndjson" } });
    }
    if (url.pathname === "/v1/feedback" && request.method === "POST") {
      if (origin && !isAllowedOrigin(origin, env)) return json({ error: "origin not allowed" }, 403, cors);
      if (!logEnabled(env)) return json({ ok: false }, 200, cors);
      let fb: { id?: string; day?: string; helpful?: boolean };
      try {
        fb = (await request.json()) as typeof fb;
      } catch {
        return json({ error: "invalid JSON" }, 400, cors);
      }
      const ok = await recordFeedback(env.ASK_KV, String(fb.day ?? ""), String(fb.id ?? ""), fb.helpful === true, logTtl(env));
      return json({ ok }, 200, cors);
    }
    if (url.pathname !== "/v1/ask" || request.method !== "POST") {
      return json({ error: "not found" }, 404, cors);
    }
    if (origin && !isAllowedOrigin(origin, env)) {
      return json({ error: "origin not allowed" }, 403, cors);
    }

    const declared = Number(request.headers.get("content-length") ?? 0);
    if (declared > MAX_BODY_BYTES) return json({ error: "request too large" }, 413, cors);
    let body: AskRequest;
    try {
      const raw = await request.text();
      if (raw.length > MAX_BODY_BYTES) return json({ error: "request too large" }, 413, cors);
      body = JSON.parse(raw) as AskRequest;
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
    const started = Date.now();
    const log: LogEntry = { id: newLogId(), day: today(), outcome: "answered", question, historyTurns: history.length, sources: [] };
    if (cacheKey) {
      const hit = await env.ASK_KV.get<CachedAnswer>(cacheKey, "json");
      if (hit) {
        logOutcome(env, ctx, { ...log, outcome: "cached", sources: hit.sources.map((s) => s.url) });
        return streamCached(hit, cors, log);
      }
    }

    // 2. Retrieval first: an empty result means nothing in the docs matches, so
    //    answer with the canned scope message and skip the model entirely.
    const retrievalQuery = history.length ? `${lastUserTurn(history)} ${question}` : question;
    const topK = Number(env.TOP_K || 8);
    let hits = index.search(retrievalQuery, topK, {
      boostUrlPrefix: page ? page.split("#")[0] : undefined,
    });
    if (!hits.length && /\b(ucp|protocol|commerce)\b/i.test(retrievalQuery)) {
      // "What is UCP?" style questions have no distinctive terms; ground them
      // in the overview material instead of bouncing them.
      hits = index.search("universal commerce protocol overview core concepts", topK);
    }
    // Questions whose vocabulary is mostly foreign to the docs are answered
    // with the scope message without spending a model call. Follow-ups are
    // exempt because they are often short ("and for MCP?").
    const offTopic =
      !hits.length ||
      (!history.length && index.vocabularyCoverage(question) < MIN_VOCAB_COVERAGE) ||
      STEERING_PATTERN.test(question) ||
      CREATIVE_PATTERN.test(question) ||
      (TASK_PATTERN.test(question) && !UCP_NOUNS.test(question));
    if (offTopic) {
      logOutcome(env, ctx, { ...log, outcome: "gated" });
      return streamCached({ answer: OFF_TOPIC_REPLY, sources: [], model: "none" }, cors, log);
    }
    log.sources = hits.map((h) => h.chunk.url);

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
    let provider: ReturnType<typeof createProvider>;
    try {
      provider = createProvider(env);
    } catch (err) {
      return json({ error: describeError(err) }, 500, cors);
    }
    const { readable, writable } = new TransformStream();
    const writer = writable.getWriter();
    const sse = (event: string, data: unknown) =>
      writer.write(new TextEncoder().encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`));

    ctx.waitUntil(
      (async () => {
        try {
          const result = await answer(provider, env, index, question, history, hits.map((h) => h.chunk), sse, log);
          logOutcome(env, ctx, {
            ...log,
            outcome: result.replaced ? "replaced" : "answered",
            answer: result.text,
            model: provider.name,
            grounding: result.grounding,
            latencyMs: Date.now() - started,
          });
          if (cacheKey && result.cacheable) {
            await env.ASK_KV.put(
              cacheKey,
              JSON.stringify({ answer: result.text, sources: result.sources, model: provider.name } satisfies CachedAnswer),
              { expirationTtl: Number(env.ANSWER_CACHE_TTL || 604800) },
            );
          }
        } catch (err) {
          logOutcome(env, ctx, { ...log, outcome: "error", latencyMs: Date.now() - started });
          await sse("error", { message: describeError(err) });
        } finally {
          await writer.close();
        }
      })(),
    );

    return new Response(readable, { headers: { ...cors, ...SSE_HEADERS } });
  },
} satisfies ExportedHandler<Env>;

function logEnabled(env: Env): boolean {
  return (env.LOG_ANSWERS ?? "on").toLowerCase() === "on";
}
function logTtl(env: Env): number {
  return Number(env.LOG_TTL_DAYS || 30);
}
function logOutcome(env: Env, ctx: ExecutionContext, entry: LogEntry): void {
  if (!logEnabled(env)) return;
  ctx.waitUntil(writeLog(env.ASK_KV, entry, logTtl(env)).catch(() => {}));
}

interface AnswerResult {
  text: string;
  sources: Source[];
  cacheable: boolean;
  replaced: boolean;
  grounding: number;
}

async function answer(
  provider: ReturnType<typeof createProvider>,
  env: Env,
  index: DocsIndex,
  question: string,
  history: HistoryMessage[],
  chunks: Chunk[],
  sse: (event: string, data: unknown) => Promise<void>,
  log: LogEntry,
): Promise<AnswerResult> {
  const sources = toSources(chunks);
  await sse("meta", { cached: false, model: provider.name, id: log.id, day: log.day });
  await sse("sources", sources);

  let text = "";
  const finish = await provider.stream(
    buildMessages(index, history, question, chunks),
    (delta) => {
      text += delta;
      void sse("delta", { text: delta });
    },
    { maxTokens: Number(env.MAX_OUTPUT_TOKENS || 700), temperature: Number(env.TEMPERATURE || 0.2) },
  );

  let cacheable = text.trim().length > 0;

  // Model-independent output guard: an answer that does not reuse the
  // excerpts' vocabulary, or that echoes the prompt scaffolding, is replaced.
  const grounding = answerGrounding(text, chunks);
  const leaked = /one line per page|<excerpts>|<question>|documentation map/i.test(text) || (text.match(/ \| https?:\/\//g) ?? []).length >= 2;
  if (leaked || grounding < MIN_ANSWER_GROUNDING) {
    text = GROUNDING_FALLBACK;
    await sse("replace", { text });
    const top = sources.slice(0, 3);
    await sse("done", { sources: top, grounding: Number(grounding.toFixed(2)), replaced: true });
    return { text, sources: top, cacheable: false, replaced: true, grounding };
  }

  if (finish === "length") {
    const note = "\n\n_(Answer truncated. Ask a narrower follow-up for more detail.)_";
    text += note;
    await sse("delta", { text: note });
    cacheable = false;
  }

  // Prefer the sections the model actually cited; if it cited nothing
  // (smaller models sometimes skip the [n] markers), fall back to the top
  // retrieved sections so the reader can still verify the answer.
  const cited = sources.filter((s) => text.includes(`[${s.n}]`));
  const usedSources = cited.length ? cited : sources.slice(0, 3);
  await sse("done", { sources: usedSources });
  return { text, sources: usedSources, cacheable, replaced: false, grounding };
}

/** Share of the answer's content terms that occur in the excerpts it was given. */
export function answerGrounding(answer: string, chunks: Chunk[]): number {
  const vocab = new Set<string>();
  for (const c of chunks) for (const t of tokenize(`${c.page} ${c.heading} ${c.text}`)) vocab.add(t);
  // Words any grounded answer may add on its own.
  for (const t of tokenize("documentation specify specified section page see refer according defined describe allow require must optional include example")) vocab.add(t);
  const terms = tokenize(answer).filter((t) => t.length > 2);
  if (terms.length < 4) return 1;
  const known = terms.filter((t) => vocab.has(t)).length;
  return known / terms.length;
}

function toSources(chunks: Chunk[]): Source[] {
  return chunks.map((c, i) => ({ n: i + 1, title: c.page, heading: c.heading, url: c.url }));
}

function streamCached(hit: CachedAnswer, cors: Record<string, string>, log?: LogEntry): Response {
  const enc = new TextEncoder();
  const parts = [
    `event: meta\ndata: ${JSON.stringify({ cached: true, model: hit.model, id: log?.id, day: log?.day })}\n\n`,
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
  // Cap total replayed characters, dropping the oldest turns first.
  let total = out.reduce((n, m) => n + m.content.length, 0);
  while (out.length > 2 && total > MAX_HISTORY_TOTAL_CHARS) {
    total -= out[0].content.length + out[1].content.length;
    out.splice(0, 2);
  }
  return out;
}

function lastUserTurn(history: HistoryMessage[]): string {
  for (let i = history.length - 1; i >= 0; i--) if (history[i].role === "user") return history[i].content;
  return "";
}

function describeError(err: unknown): string {
  if (err instanceof ProviderError) {
    if (err.status === 429 || err.status === 503) return "The assistant is busy right now. Please try again in a minute.";
    if (err.status && err.status >= 500) return "The model server hit an error. Please try again.";
    return err.message;
  }
  if (err instanceof TypeError) return "The assistant could not reach its model server.";
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
