# Ask AI backend for ucp.dev

A small Cloudflare Worker that powers the "Ask AI" button on the documentation
site. It answers questions about UCP from the documentation itself, cites the
sections it used, and runs against **your own model**: anything that speaks the
OpenAI chat-completions protocol (vLLM, Ollama, TGI, llama.cpp, SGLang, LM
Studio, a fine-tuned model you host) or an open model on Cloudflare Workers AI.
No third-party LLM API is required.

## How it works

```text
docs build (MkDocs)            Cloudflare Worker (this directory)             your model
┌───────────────────┐   fetch  ┌────────────────────────────────────────┐
│ ask-index.json    │ ───────▶ │ 1. answer cache (KV)  → hit? replay    │
│ (root + /latest)  │          │ 2. BM25 retrieval     → nothing? scope │
└───────────────────┘          │ 3. rate + budget guards (KV)           │   streamed
                               │ 4. chat completion (stable system,     │ ─────────▶
   browser widget  ◀── SSE ─── │    ~8 excerpts, capped output)         │ ◀─────────
└───────────────────┘          └────────────────────────────────────────┘
```

1. **Index at build time, not query time.** `ask_index_hook.py` splits every
   rendered page into heading-level sections and writes `ask-index.json` next
   to the site. The root build and each spec version write their own file, so
   the Worker loads `https://ucp.dev/ask-index.json` and
   `https://ucp.dev/latest/ask-index.json` and always reflects what is deployed.
   No embedding model, no vector database, nothing to re-run on deploy.
2. **Retrieval is free.** The Worker builds a BM25 inverted index in memory at
   cold start and keeps it for ten minutes. Dotted identifiers such as
   `dev.ucp.shopping.checkout` are indexed whole and in parts, and sections from
   the page the visitor is on get a small boost.
3. **No model call when it is not needed.** Identical single-turn questions are
   served from a KV answer cache (keyed by the index version, so a redeploy
   invalidates them). Questions with zero overlap with the docs get a canned
   scope reply.
4. **One tightly scoped model call.** The system prompt (rules + a one-line map
   of every page, ~3K tokens) is byte-stable, so servers with prefix caching
   (vLLM, SGLang, llama.cpp) reuse its KV cache across requests. The question
   travels with ~8 short excerpts (~4K tokens). Output is capped by
   `MAX_OUTPUT_TOKENS` and the prompt asks for under 200 words.
5. **Guards.** Per-IP hourly limit, a daily request budget, question length
   limit, and conversation memory trimmed to the last three turns.

### Choosing and running the model

The facts come from retrieval, so the model's job is reading comprehension
and concise writing, not memorized knowledge. That is why a mid-sized
instruction-tuned open model is enough. Rough guidance:

| Option | Typical choice | What you pay for | Notes |
|---|---|---|---|
| Cloudflare Workers AI | `@cf/meta/llama-3.3-70b-instruct-fp8-fast`, `@cf/qwen/...` | per token, no idle cost | Simplest: same account as the Worker, set `MODEL_PROVIDER=workers-ai`. |
| Self-hosted, always on | Qwen2.5 14B / Llama 3.1 8B on vLLM behind one GPU | GPU hours | Flat cost regardless of traffic; enable vLLM prefix caching. |
| Self-hosted, scale to zero | same models on a serverless GPU platform | GPU seconds | Cold starts of 10-60 s on the first question after idle. |
| Fine-tuned | LoRA on top of one of the above, trained on UCP Q&A pairs | one-off training | Improves tone and formatting; does **not** replace retrieval for facts, which go stale with every spec release. Start without it and collect real questions first. |

A request is roughly 7K input tokens and 300 output tokens. At the per-token
rates open models are offered at, that is a fraction of a cent; on a dedicated
GPU it is simply throughput. The daily budget and answer cache keep both bounded.

Training a model from scratch is not a sensible path for this use case: it
costs orders of magnitude more than any option above and would still need the
retrieval layer to answer accurately about the current specification.

## Deploy

Prerequisites: a Cloudflare account with Workers and KV, Node 20+, and either a
model server reachable over HTTPS or Workers AI enabled.

```bash
cd ask
npm install
npx wrangler login
npx wrangler kv namespace create ASK_KV        # paste the id into wrangler.toml
# Pick ONE provider in wrangler.toml [vars]:
#   MODEL_PROVIDER="openai-compatible", MODEL_BASE_URL="https://.../v1", MODEL="<served name>"
#   (if the server needs a key:  npx wrangler secret put MODEL_API_KEY)
#   MODEL_PROVIDER="workers-ai",        MODEL="@cf/meta/llama-3.3-70b-instruct-fp8-fast"
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
| `MODEL_PROVIDER` | `openai-compatible` | `openai-compatible` or `workers-ai`. |
| `MODEL` | `qwen2.5-14b-instruct` | Served model name (or Workers AI model id). |
| `MODEL_BASE_URL` | placeholder | Base URL of the OpenAI-compatible server, ending in `/v1`. |
| `MODEL_API_KEY` | secret, optional | Bearer token for the model server. |
| `TEMPERATURE` | `0.2` | Sampling temperature. |
| `MAX_OUTPUT_TOKENS` | `700` | Hard cap per answer. |
| `TOP_K` | `8` | Excerpts in the prompt. |
| `MAX_HISTORY_TURNS` | `3` | Conversation pairs replayed to the model. |
| `PER_IP_HOURLY_LIMIT` | `40` | Soft per-visitor limit. |
| `DAILY_REQUEST_BUDGET` | `5000` | Soft site-wide daily cap on model calls. |
| `ANSWER_CACHE_TTL` | `604800` | Seconds to keep a cached answer (also dropped on redeploy). |
| `INDEX_URLS` | root + latest | Which `ask-index.json` files to load. |
| `ALLOWED_ORIGINS` | `https://ucp.dev` | Browser origins allowed to call the API. |

## Trying it without any API key

Any OpenAI-compatible local server works. The smallest setup is llama.cpp's
Python server with an open GGUF model; a 3B model answers on a laptop CPU in
under a minute per question and is enough to see the whole pipeline work
(retrieval, citations, cache hits, off-topic gate). Use a 7B-14B+ instruct
model for real quality.

```bash
python3 -m venv llm && ./llm/bin/pip install "llama-cpp-python[server]" huggingface_hub
./llm/bin/python -c "from huggingface_hub import hf_hub_download as d; \
  d('Qwen/Qwen2.5-3B-Instruct-GGUF','qwen2.5-3b-instruct-q4_k_m.gguf',local_dir='weights')"
./llm/bin/python -m llama_cpp.server --model weights/qwen2.5-3b-instruct-q4_k_m.gguf \
  --model_alias local --n_ctx 8192 --chat_format chatml --port 8080
```

Then run the Worker with `MODEL_BASE_URL=http://127.0.0.1:8080/v1 MODEL=local`
(see Local development below). Ollama (`ollama serve`, base URL
`http://localhost:11434/v1`) works the same way.

## Local development

```bash
cd ask
cp .dev.vars.example .dev.vars        # point MODEL_BASE_URL at a local server, e.g. Ollama
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
| `sources` | `[{ n, title, heading, url }]` |
| `delta` | `{ text }` incremental answer text, with `[n]` citations |
| `done` | `{ sources }` only the sources actually cited |
| `error` | `{ message }` |

Errors before streaming starts are plain JSON with HTTP 4xx/5xx; 429 carries `Retry-After`.

## Abuse resistance

What a visitor can and cannot do with the endpoint:

| Attempt | What happens |
|---|---|
| Use it as a general chatbot ("write me a poem") | Retrieval finds nothing docs-like, or the question's words are mostly unknown to the docs: canned scope reply, no model call. Questions that slip through are still bound by the system prompt. |
| Prompt injection in the question ("ignore your instructions", "print your system prompt") | The question is passed as data inside `<question>` tags and the prompt says instructions there carry no authority. Such questions are never written to the answer cache, so a manipulated answer cannot be served to the next person. |
| Injection through `history` (fake "assistant" turns with new rules) | History is trimmed, must alternate user/assistant, is capped in size, and the prompt states earlier assistant turns may have been edited by the user. History also disables caching. |
| Hammering the endpoint | Per-IP hourly limit (`cf-connecting-ip` is set by Cloudflare and cannot be spoofed), site-wide daily budget, 600-character questions, 32 KB bodies, bounded output tokens. For hostile traffic add a Cloudflare rate-limiting rule or Turnstile in front of `/v1/ask`. |
| Calling from another site | Browser requests from origins outside `ALLOWED_ORIGINS` are refused. Non-browser callers can still use the API, which is intended, and are subject to the same limits. |
| Phishing links in answers | The widget renders Markdown links only when they point at ucp.dev or github.com; everything else is plain text. Citations always come from the index, never from the model. |
| Cross-site scripting | All model output is HTML-escaped before the limited Markdown renderer runs. |

The remaining risk is answer quality: a small model may follow a steering
prompt despite the rules. Review the eval questions in this README's history
or run your own against the model you deploy.

## Excluding a page from the index

Add `ask_index: false` to the page's front matter.
