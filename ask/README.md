# Ask AI backend for ucp.dev

A small Cloudflare Worker that powers the "Ask AI" button on the documentation
site. It answers questions about UCP from the documentation itself, cites the
sections it used, and is built to keep model spend low and predictable.

## How it works

```text
docs build (MkDocs)            Cloudflare Worker (this directory)              Claude API
┌───────────────────┐   fetch  ┌────────────────────────────────────────┐
│ ask-index.json    │ ───────▶ │ 1. answer cache (KV)  → hit? replay    │
│ (root + /latest)  │          │ 2. BM25 retrieval     → nothing? scope │
└───────────────────┘          │ 3. rate + budget guards (KV)           │   streamed
                               │ 4. messages.stream(cached system,      │ ─────────▶
   browser widget  ◀── SSE ─── │    6 excerpts, 1 optional search)      │ ◀─────────
└───────────────────┘          └────────────────────────────────────────┘
```

1. **Index at build time, not query time.** `ask_index_hook.py` splits every
   rendered page into heading-level sections and writes `ask-index.json` next
   to the site. The root build and each spec version write their own file, so
   the Worker loads `https://ucp.dev/ask-index.json` and
   `https://ucp.dev/latest/ask-index.json` and always reflects what is deployed.
   No embedding API, no vector database, nothing to re-run on deploy.
2. **Retrieval is free.** The Worker builds a BM25 inverted index in memory at
   cold start and keeps it for ten minutes. Dotted identifiers such as
   `dev.ucp.shopping.checkout` are indexed whole and in parts, and sections from
   the page the visitor is on get a small boost.
3. **No model call when it is not needed.** Identical single-turn questions are
   served from a KV answer cache (keyed by the index version, so a redeploy
   invalidates them). Questions with zero overlap with the docs get a canned
   scope reply.
4. **One tightly scoped model call.** The system prompt (rules + a one-line map
   of every page) is byte-stable and cached with a one-hour TTL, so it costs a
   cache read per question. The question travels with ~6 short excerpts.
   Output is capped by `MAX_OUTPUT_TOKENS`, and the prompt asks for under 200
   words. The model may call `search_docs` once if the excerpts miss; the
   second round forbids further tool use. Effort is `low`.
5. **Guards.** Per-IP hourly limit, a daily request budget, question length
   limit, and conversation memory trimmed to the last three turns.

### Cost per answered question (Claude Sonnet 5.5, list prices)

| Component | Tokens | Cost |
|---|---|---|
| Cached system prefix (read) | ~3,500 | ~$0.0004 |
| Excerpts + question (uncached input) | ~3,500 | ~$0.007 |
| Answer (output, incl. thinking at low effort) | ~400 | ~$0.004 |
| **Typical total** | | **~$0.01** |
| Repeated question (KV hit) | 0 | $0 |
| Off-topic question | 0 | $0 |

With `MODEL=claude-haiku-5-5` the same request is roughly $0.0007; with
`claude-opus-5-5` roughly $0.02. The daily budget default (5,000 requests)
therefore caps spend at about $50/day on Sonnet even under abuse.

## Deploy

Prerequisites: a Cloudflare account with Workers and KV, an Anthropic API key,
Node 20+.

```bash
cd ask
npm install
npx wrangler login
npx wrangler kv namespace create ASK_KV        # paste the id into wrangler.toml
npx wrangler secret put ANTHROPIC_API_KEY
npm run deploy
```

Point the `ask.ucp.dev` custom domain at the Worker (the `routes` entry in
`wrangler.toml` does this when the zone is on Cloudflare), or change
`extra.ask_ai.endpoint` in `mkdocs.yml` / the `ASK_AI_ENDPOINT` env var to
wherever the Worker is served. Leaving the endpoint empty hides the widget.

Check it:

```bash
curl https://ask.ucp.dev/v1/health
curl -N https://ask.ucp.dev/v1/ask -H 'content-type: application/json' \
  -d '{"question":"What does the checkout capability do?"}'
```

## Configuration (`wrangler.toml` `[vars]`)

| Var | Default | Purpose |
|---|---|---|
| `MODEL` | `claude-sonnet-5-5` | Answer model. `claude-haiku-5-5` for lowest cost, `claude-opus-5-5` for highest quality. |
| `EFFORT` | `low` | Thinking/verbosity effort. The main quality-vs-cost dial. |
| `MAX_OUTPUT_TOKENS` | `900` | Hard cap per answer. |
| `TOP_K` / `TOOL_TOP_K` | `6` / `4` | Excerpts in the first prompt / returned by the one allowed search. |
| `MAX_HISTORY_TURNS` | `3` | Conversation pairs replayed to the model. |
| `PER_IP_HOURLY_LIMIT` | `40` | Soft per-visitor limit. |
| `DAILY_REQUEST_BUDGET` | `5000` | Soft site-wide daily cap on model calls. |
| `ANSWER_CACHE_TTL` | `604800` | Seconds to keep a cached answer (also dropped on redeploy). |
| `INDEX_URLS` | root + latest | Which `ask-index.json` files to load. |
| `ALLOWED_ORIGINS` | `https://ucp.dev` | Browser origins allowed to call the API. |

## Local development

```bash
cd ask
cp .dev.vars.example .dev.vars        # add ANTHROPIC_API_KEY
# Build the docs so a local ask-index.json exists, then serve them:
(cd .. && DOCS_MODE=root uv run mkdocs build && python3 -m http.server 8000 -d site)
# Point the Worker at the local index and allow the local origin:
INDEX_URLS=http://localhost:8000/ask-index.json ALLOWED_ORIGINS=http://localhost:8000 npm run dev
```

Then run the docs with `ASK_AI_ENDPOINT=http://localhost:8787/v1/ask` so the
widget talks to the local Worker.

```bash
npm run typecheck && npm test        # Worker
uv run python scripts/test_ask_index.py   # indexer
```

## API

`POST /v1/ask` with JSON `{ "question": string, "history"?: [{ "role": "user" | "assistant", "content": string }], "page"?: string }`.

Response is `text/event-stream`:

| event | data |
|---|---|
| `meta` | `{ cached: boolean, model: string }` |
| `sources` | `[{ n, title, heading, url }]` (may be sent again if the model searched) |
| `delta` | `{ text }` incremental answer text, with `[n]` citations |
| `done` | `{ sources }` only the sources actually cited |
| `error` | `{ message }` |

Errors before streaming starts are plain JSON with HTTP 4xx/5xx; 429 carries `Retry-After`.

## Excluding a page from the index

Add `ask_index: false` to the page's front matter.
