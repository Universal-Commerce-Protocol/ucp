/**
 * BM25 retrieval over the ask-index.json files emitted by the docs build.
 *
 * Retrieval runs entirely inside the Worker with no model call, so finding
 * the right sections costs nothing. The index is small (a few thousand
 * sections), so a plain in-memory inverted index built at cold start is fast
 * enough and avoids a vector database or embedding API.
 */

export interface Chunk {
  id: string;
  /** Absolute URL including heading anchor. */
  url: string;
  page: string;
  heading: string;
  text: string;
  words: number;
}

export interface PageEntry {
  url: string;
  title: string;
  summary: string;
}

export interface RawIndex {
  format: number;
  version: string;
  base_url: string;
  pages: PageEntry[];
  chunks: Chunk[];
}

export interface Hit {
  chunk: Chunk;
  score: number;
}

const STOPWORDS = new Set(
  (
    "a an and are as at be by can could do does for from has have how i if in is it its of on or " +
    "that the this to was what when where which who why will with you your does do should would " +
    "about into than then there these those we our they their me my " +
    // question filler that carries no topical signal
    "work works working use using used need needs want add get make like way mean means help " +
    "know tell explain show give also please any some one someone something"
  ).split(" ")
);

/**
 * Everyday words people use for UCP concepts, mapped to the terms the docs use.
 * Applied to queries only, so "my ecommerce store" also matches "business".
 */
const QUERY_SYNONYMS: Record<string, string[]> = {
  ecommerce: ["commerce", "business", "checkout"],
  "e-commerce": ["commerce", "business", "checkout"],
  store: ["business"],
  shop: ["business"],
  merchant: ["business"],
  retailer: ["business"],
  seller: ["business"],
  brand: ["business"],
  website: ["business", "server"],
  backend: ["server"],
  agent: ["platform"],
  assistant: ["platform"],
  chatbot: ["platform"],
  app: ["platform"],
  integrate: ["implement", "server"],
  integration: ["implement", "server"],
  build: ["implement", "server"],
  adopt: ["implement"],
  onboard: ["implement", "start"],
  setup: ["start", "setup"],
  install: ["setup", "start"],
  begin: ["start"],
  tutorial: ["start", "guide"],
  example: ["example", "guide"],
  pay: ["payment"],
  card: ["payment", "instrument"],
  wallet: ["payment", "instrument"],
  login: ["identity", "linking"],
  oauth: ["identity", "linking"],
  auth: ["authentication", "identity"],
  sign: ["signature"],
  prove: ["signature", "verify", "signing"],
  authentic: ["signature", "verify", "signing"],
  genuine: ["signature", "verify", "signing"],
  tampered: ["signature", "verify", "digest"],
  spoof: ["signature", "verify", "signing"],
  webhook: ["event", "order"],
  shipping: ["fulfillment"],
  delivery: ["fulfillment"],
  coupon: ["discount"],
  promo: ["discount"],
  hotel: ["lodging", "booking"],
  restaurant: ["food"],
  behind: ["developed", "partners", "leaders"],
  backed: ["developed", "partners", "leaders"],
  partners: ["developed", "partners", "leaders"],
  members: ["developed", "partners", "leaders"],
};

/** Pages that rarely hold the best answer to a how-to question. */
const PAGE_DEMOTIONS: { suffix: string; factor: number }[] = [
  { suffix: "documentation/announcements/", factor: 0.5 },
  { suffix: "documentation/roadmap/", factor: 0.8 },
];

/** Expand a query with UCP vocabulary. Expansions are appended, never replace. */
export function expandQuery(query: string): string {
  const extra: string[] = [];
  for (const raw of query.toLowerCase().split(/[^a-z0-9-]+/)) {
    const word = raw.replace(/s$/, "");
    const syn = QUERY_SYNONYMS[raw] ?? QUERY_SYNONYMS[word];
    if (syn) extra.push(...syn);
  }
  return extra.length ? `${query} ${extra.join(" ")}` : query;
}

/**
 * Broad "how do I start" questions are better served by the onboarding pages
 * than by whichever section happens to share the most keywords. When a query
 * matches the intent and names no specific capability, the lead section of
 * each pinned page is included in the results.
 */
const INTENT_PINS: { intent: RegExp; pages: string[] }[] = [
  {
    intent:
      /\b(what('s| is| are)|explain|describe|about|overview of|introduction to|intro to)\b.*\b(ucp|universal commerce protocol|the protocol)\b|^(ucp|universal commerce protocol)\??$/i,
    pages: ["documentation/core-concepts/", "specification/overview/"],
  },
  {
    intent:
      /\b(implement|get(ting)? started|start|integrate|integration|build|adopt|set ?up|onboard|begin|tutorial|quick ?start|how do i (use|support))/i,
    pages: ["specification/getting-started/", "documentation/core-concepts/"],
  },
];
const BUSINESS_INTENT =
  /\b(my|our|a|small|your) (business|company|store|shop|brand|startup|team)\b|\b(benefit|benefits|advantage|advantages|value|roi|revenue|sales|conversion|customers|worth it|why (should|would|use|adopt|does)|business case|use case|who is (it|ucp) for|how (does|do) (ucp|it|this) (even )?(work|help)|what (does|can) ucp do|why ucp)\b/i;
const BUSINESS_HEADINGS =
  /^(for developers|for businesses|key goals of ucp|core concepts|get started today|see it in action|universal ?commerce ?protocol|co-developed by industry leaders|roles & participants)$/i;

function dedupe(hits: Hit[]): Hit[] {
  const seen = new Set<string>();
  const out: Hit[] = [];
  for (const h of hits) {
    if (seen.has(h.chunk.id)) continue;
    seen.add(h.chunk.id);
    out.push(h);
  }
  return out;
}

export const INSTRUCTION_PATTERN =
  /\bhow (can|do|would|should|could) (i|we|you|one)\b|\bhow to\b|\b(set ?up|enable|install|configure|turn on|do (it|this|that))\b|\b(i|we|my|our)\b/i;
const SPECIFIC_TERMS =
  /\b(cart|catalog|order|booking|lodging|food|tip|fulfil|discount|loyalty|consent|return|permalink|location|identity|signature|mandate|3ds|tokenization|tokenizer|ap2|mcp|a2a|embedded|rest|schema|extension|version)/i;

/** Lower-case, split on punctuation, light stemming; dotted identifiers keep both forms. */
export function tokenize(text: string): string[] {
  const out: string[] = [];
  for (const raw of text.toLowerCase().split(/[^a-z0-9_.\-/]+/)) {
    if (!raw) continue;
    const word = raw.replace(/^[.\-/]+|[.\-/]+$/g, "");
    if (!word) continue;
    if (/[.\-/_]/.test(word)) {
      // e.g. dev.ucp.shopping.checkout -> whole identifier plus its parts
      out.push(word);
      for (const part of word.split(/[.\-/_]+/)) {
        if (part.length > 1 && !STOPWORDS.has(part)) out.push(stem(part));
      }
      continue;
    }
    if (STOPWORDS.has(word) || word.length < 2) continue;
    out.push(stem(word));
  }
  return out;
}

/** Light English stemmer: plurals, -ing/-ed/-ly, trailing e, doubled consonants. */
function stem(word: string): string {
  if (word.length <= 3) return word;
  let w = word
    .replace(/ies$/, "y")
    .replace(/(ss)es$/, "$1")
    .replace(/([^s])s$/, "$1");
  if (w.length > 4) {
    w = w.replace(/(ing|ed|ly)$/, "");
    // Collapse a doubled consonant left by -ing/-ed (shopping -> shop) and
    // drop a trailing e so "contribute" and "contributing" share a stem.
    w = w.replace(/([^aeiou])\1$/, "$1"); // cspell:disable-line
    if (w.length > 4) w = w.replace(/e$/, "");
  }
  return w;
}

export class DocsIndex {
  readonly version: string;
  readonly chunks: Chunk[];
  readonly pages: PageEntry[];
  private readonly df = new Map<string, number>();
  private readonly postings = new Map<string, Map<number, number>>();
  private readonly lengths: number[];
  private readonly avgLen: number;
  private readonly byId = new Map<string, Chunk>();
  /** First chunk of each page, keyed by page URL (without anchor). */
  private readonly leads = new Map<string, Chunk>();
  /**
   * Organization names from the "co-developed" and "endorsed" lists, mapped
   * to the section that names them. Several are ordinary words ("Target",
   * "Block", "Gap"), so a question about the company would otherwise be
   * read as a question about the technical term.
   */
  private readonly orgs = new Map<string, { display: string; chunk: Chunk }>();
  /** Page-level document frequencies / postings over title + headings + summary. */
  private readonly pageTerms = new Map<string, Map<string, number>>();
  private readonly pageDf = new Map<string, number>();

  constructor(chunks: Chunk[], pages: PageEntry[], version: string) {
    this.chunks = chunks;
    this.pages = pages;
    this.version = version;
    this.lengths = new Array(chunks.length);
    let total = 0;
    const headingsByPage = new Map<string, string[]>();
    chunks.forEach((chunk, i) => {
      this.byId.set(chunk.id, chunk);
      const pageUrl = chunk.url.split("#")[0];
      if (!this.leads.has(pageUrl)) this.leads.set(pageUrl, chunk);
      if (/co-developed|endorsed|partners|members/i.test(chunk.heading)) {
        for (const line of chunk.text.split("\n")) {
          const name = line.trim();
          // A partner list is one short name per line.
          if (name && name.length <= 30 && name.split(/\s+/).length <= 3) {
            this.orgs.set(name.toLowerCase(), { display: name, chunk });
          }
        }
      }
      const hs = headingsByPage.get(pageUrl) ?? [];
      hs.push(chunk.heading);
      headingsByPage.set(pageUrl, hs);
      // Headings and page titles are strong signals: weight them by repetition.
      const tokens = tokenize(
        `${chunk.page} ${chunk.page} ${chunk.heading} ${chunk.heading} ${chunk.heading} ${chunk.text}`
      );
      this.lengths[i] = tokens.length;
      total += tokens.length;
      const seen = new Map<string, number>();
      for (const t of tokens) seen.set(t, (seen.get(t) ?? 0) + 1);
      for (const [t, tf] of seen) {
        this.df.set(t, (this.df.get(t) ?? 0) + 1);
        let list = this.postings.get(t);
        if (!list) {
          list = new Map();
          this.postings.set(t, list);
        }
        list.set(i, tf);
      }
    });
    this.avgLen = chunks.length ? total / chunks.length : 1;

    // Page-level term statistics: a page whose title and headings match the
    // query is a strong signal even when no single section scores highly.
    for (const page of pages) {
      const pageUrl = page.url;
      const text = `${page.title} ${page.title} ${page.title} ${(headingsByPage.get(pageUrl) ?? []).join(" ")} ${page.summary}`;
      const tf = new Map<string, number>();
      for (const t of tokenize(text)) tf.set(t, (tf.get(t) ?? 0) + 1);
      this.pageTerms.set(pageUrl, tf);
      for (const t of tf.keys())
        this.pageDf.set(t, (this.pageDf.get(t) ?? 0) + 1);
    }
  }

  /** BM25-style score of a page's title/headings/summary against query terms. */
  private pageScore(pageUrl: string, terms: Set<string>): number {
    const tf = this.pageTerms.get(pageUrl);
    if (!tf) return 0;
    const n = this.pages.length || 1;
    let score = 0;
    for (const term of terms) {
      const f = tf.get(term);
      if (!f) continue;
      const df = this.pageDf.get(term) ?? 0;
      score +=
        Math.log(1 + (n - df + 0.5) / (df + 0.5)) * ((f * 2.2) / (f + 1.2));
    }
    return score;
  }

  /** Unit-length chunk embeddings, quantized to int8, one row per chunk. */
  private vectors: Int8Array | null = null;
  private vectorDim = 0;
  /** Row in `vectors` for each chunk index, or -1 when it has no embedding. */
  private vectorRow: Int32Array | null = null;

  /** Attach embeddings produced by scripts/build-embeddings.ts. */
  setEmbeddings(ids: string[], dim: number, data: Int8Array): void {
    const rowById = new Map(ids.map((id, i) => [id, i]));
    this.vectorRow = Int32Array.from(
      this.chunks,
      (c) => rowById.get(c.id) ?? -1
    );
    this.vectors = data;
    this.vectorDim = dim;
  }

  get hasEmbeddings(): boolean {
    return this.vectors !== null;
  }

  /** Chunk indices ranked by cosine similarity to a query embedding. */
  private semanticTop(query: number[], n: number): number[] {
    if (!this.vectors || !this.vectorRow || query.length !== this.vectorDim)
      return [];
    const scored: { doc: number; score: number }[] = [];
    for (let doc = 0; doc < this.chunks.length; doc++) {
      const row = this.vectorRow[doc];
      if (row < 0) continue;
      const base = row * this.vectorDim;
      let dot = 0;
      for (let j = 0; j < this.vectorDim; j++)
        dot += query[j] * this.vectors[base + j];
      scored.push({ doc, score: dot });
    }
    scored.sort((a, b) => b.score - a.score);
    return scored.slice(0, n).map((x) => x.doc);
  }

  get(id: string): Chunk | undefined {
    return this.byId.get(id);
  }

  /** Organizations named in the query, with the section that lists them. */
  organizationsIn(
    query: string
  ): { name: string; display: string; chunk: Chunk }[] {
    const q = ` ${query.toLowerCase().replace(/[^a-z0-9.&' ]+/g, " ")} `;
    const found: { name: string; display: string; chunk: Chunk }[] = [];
    for (const [name, entry] of this.orgs) {
      if (q.includes(` ${name} `) || q.includes(` ${name}'s `)) {
        found.push({ name, display: entry.display, chunk: entry.chunk });
      }
    }
    return found;
  }

  /**
   * Share of a query's content terms that occur anywhere in the docs. A low
   * value means the question is about something the documentation never
   * mentions (e.g. "write a poem about autumn"), even if one or two common
   * words happen to match a section.
   */
  vocabularyCoverage(query: string): number {
    const terms = [...new Set(tokenize(query))];
    if (!terms.length) return 0;
    const known = terms.filter(
      (t) =>
        this.df.has(t) ||
        QUERY_SYNONYMS[t] !== undefined ||
        QUERY_SYNONYMS[`${t}s`] !== undefined
    ).length;
    return known / terms.length;
  }

  /**
   * BM25 ranking. `boostUrlPrefix` nudges sections from the page the visitor is
   * currently reading, which disambiguates follow-ups like "what does this field mean".
   */
  search(
    query: string,
    k: number,
    opts: {
      exclude?: Set<string>;
      boostUrlPrefix?: string;
      /**
       * Embedding of the query. When given and the index has embeddings,
       * keyword and meaning-based rankings are merged, so a section can be
       * found even when it shares no words with the question.
       */
      queryVector?: number[];
      /** Set by question triage; falls back to keyword detection when absent. */
      intent?: "business" | "howto";
    } = {}
  ): Hit[] {
    const terms = tokenize(expandQuery(query));
    if (!terms.length) return [];
    const termSet = new Set(terms);
    const pageScores = new Map<string, number>();
    for (const page of this.pages)
      pageScores.set(page.url, this.pageScore(page.url, termSet));
    const k1 = 1.4;
    const b = 0.75;
    const n = this.chunks.length;
    const scores = new Map<number, number>();
    for (const term of new Set(terms)) {
      const list = this.postings.get(term);
      if (!list) continue;
      const df = this.df.get(term) ?? 0;
      const idf = Math.log(1 + (n - df + 0.5) / (df + 0.5));
      for (const [doc, tf] of list) {
        const norm = tf + k1 * (1 - b + (b * this.lengths[doc]) / this.avgLen);
        scores.set(
          doc,
          (scores.get(doc) ?? 0) + idf * ((tf * (k1 + 1)) / norm)
        );
      }
    }
    // Pages that match strongly as a whole contribute their lead section even
    // if no single section of theirs scored on its own.
    const strongPages = [...pageScores.entries()]
      .filter(([, s]) => s > 0)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 2);
    for (const [pageUrl] of strongPages) {
      const lead = this.leads.get(pageUrl);
      if (lead) {
        const idx = this.chunks.indexOf(lead);
        if (!scores.has(idx)) scores.set(idx, 0);
      }
    }

    const hits: Hit[] = [];
    for (const [doc, raw] of scores) {
      const chunk = this.chunks[doc];
      if (opts.exclude?.has(chunk.id)) continue;
      const pageUrl = chunk.url.split("#")[0];
      let score = raw + 1.5 * (pageScores.get(pageUrl) ?? 0);
      if (opts.boostUrlPrefix && chunk.url.startsWith(opts.boostUrlPrefix))
        score *= 1.15;
      for (const d of PAGE_DEMOTIONS)
        if (pageUrl.endsWith(d.suffix)) score *= d.factor;
      hits.push({ chunk, score });
    }
    hits.sort((a, b) => b.score - a.score);

    // Reciprocal rank fusion of the keyword ranking with the semantic one.
    if (opts.queryVector && this.hasEmbeddings && hits.length) {
      const fused = new Map<string, { chunk: Chunk; score: number }>();
      const add = (chunk: Chunk, rank: number) => {
        if (opts.exclude?.has(chunk.id)) return;
        const entry = fused.get(chunk.id) ?? { chunk, score: 0 };
        entry.score += 1 / (60 + rank);
        fused.set(chunk.id, entry);
      };
      hits.slice(0, 40).forEach((h, rank) => {
        add(h.chunk, rank);
      });
      this.semanticTop(opts.queryVector, 40).forEach((doc, rank) => {
        add(this.chunks[doc], rank);
      });
      hits.length = 0;
      hits.push(...[...fused.values()].sort((a, b) => b.score - a.score));
    }

    // A question naming a partner organization always sees the list it is on.
    for (const { chunk } of this.organizationsIn(query)) {
      if (opts.exclude?.has(chunk.id)) continue;
      const existing = hits.findIndex((h) => h.chunk.id === chunk.id);
      if (existing >= 0) hits.splice(existing, 1);
      hits.unshift({ chunk, score: Number.POSITIVE_INFINITY });
    }

    // Business-level questions ("how does UCP work", "how will it help my
    // business", "why should we adopt it") are answered from the overview
    // material written for that audience, not from whichever spec section
    // shares a keyword.
    if (
      opts.intent === "business" ||
      (!opts.intent && BUSINESS_INTENT.test(query))
    ) {
      const wanted = this.chunks.filter(
        (c) => BUSINESS_HEADINGS.test(c.heading) && !opts.exclude?.has(c.id)
      );
      for (const chunk of wanted.slice(0, 5).reverse()) {
        const existing = hits.findIndex((h) => h.chunk.id === chunk.id);
        if (existing >= 0) hits.splice(existing, 1);
        hits.unshift({ chunk, score: Number.POSITIVE_INFINITY });
      }
      return dedupe(hits).slice(0, k);
    }

    // Intent pins: onboarding questions always see the getting-started material.
    // "How can I do it inside Shopify" names a platform and asks how: that is
    // an onboarding question even though it has none of the usual keywords.
    const instructionOnPlatform =
      opts.intent === "howto" ||
      (INSTRUCTION_PATTERN.test(query) &&
        this.organizationsIn(query).length > 0);
    if (instructionOnPlatform || !SPECIFIC_TERMS.test(query)) {
      for (const pin of INTENT_PINS) {
        const onboarding = pin.pages[0] === "specification/getting-started/";
        if (!pin.intent.test(query) && !(onboarding && instructionOnPlatform))
          continue;
        for (const suffix of [...pin.pages].reverse()) {
          const pageUrl = [...this.leads.keys()].find((u) =>
            u.endsWith(suffix)
          );
          const lead = pageUrl ? this.leads.get(pageUrl) : undefined;
          if (!lead || opts.exclude?.has(lead.id)) continue;
          // Pin the page's lead section plus its best-matching section.
          const best = hits.find(
            (h) =>
              h.chunk.url.startsWith(pageUrl ?? "") && h.chunk.id !== lead.id
          );
          for (const pinned of [best?.chunk, lead].filter((c): c is Chunk =>
            Boolean(c)
          )) {
            const existing = hits.findIndex((h) => h.chunk.id === pinned.id);
            if (existing >= 0) hits.splice(existing, 1);
            hits.unshift({ chunk: pinned, score: Number.POSITIVE_INFINITY });
          }
        }
      }
    }
    // Diversify: at most two sections per page in the top results.
    const perPage = new Map<string, number>();
    const picked: Hit[] = [];
    for (const hit of hits) {
      const pageUrl = hit.chunk.url.split("#")[0];
      const count = perPage.get(pageUrl) ?? 0;
      if (count >= 2) continue;
      perPage.set(pageUrl, count + 1);
      picked.push(hit);
      if (picked.length >= k) break;
    }
    return picked;
  }
}

/**
 * Merge several ask-index.json payloads (root docs + latest spec) into one
 * index. Each payload's page URLs are resolved against the directory the file
 * was fetched from (`baseUrls[i]`), which is where those pages are actually
 * served; the `base_url` recorded inside the file is only a fallback.
 */
export function buildIndex(
  raws: RawIndex[],
  baseUrls: (string | undefined)[] = []
): DocsIndex {
  const chunks: Chunk[] = [];
  const pages: PageEntry[] = [];
  const seen = new Set<string>();
  for (const [i, raw] of raws.entries()) {
    const rawBase = baseUrls[i] ?? raw.base_url;
    const base = rawBase.endsWith("/") ? rawBase : `${rawBase}/`;
    for (const chunk of raw.chunks) {
      if (seen.has(chunk.id)) continue;
      seen.add(chunk.id);
      chunks.push({ ...chunk, url: base + chunk.url });
    }
    for (const page of raw.pages) pages.push({ ...page, url: base + page.url });
  }
  const version = raws.map((r) => r.version).join("+");
  return new DocsIndex(chunks, pages, version);
}

let cached: { index: DocsIndex; loadedAt: number } | null = null;
const RELOAD_MS = 10 * 60 * 1000;

/**
 * Load (and memoize per isolate) the merged index. The Cache API keeps the
 * fetch cheap across isolates; the in-memory copy makes it free within one.
 */
/** Output of scripts/build-embeddings.ts. `data` is base64 of int8 rows. */
export interface EmbeddingsFile {
  model: string;
  dim: number;
  ids: string[];
  data: string;
}

/** Anything with a fetch(): global fetch or a Worker's static-assets binding. */
export interface IndexFetcher {
  fetch(input: string | Request, init?: RequestInit): Promise<Response>;
}

export async function loadIndex(
  urls: string[],
  fetcherFor: (url: string) => IndexFetcher = () => ({
    fetch: (i, init) => fetch(i, init),
  }),
  embeddingsUrl?: string
): Promise<DocsIndex> {
  if (cached && Date.now() - cached.loadedAt < RELOAD_MS) return cached.index;
  const raws = await Promise.all(
    urls.map(async (url) => {
      const res = await fetcherFor(url).fetch(url, {
        cf: { cacheTtl: 600, cacheEverything: true },
      } as RequestInit);
      if (!res.ok) throw new Error(`index fetch failed: ${url} ${res.status}`);
      return (await res.json()) as RawIndex;
    })
  );
  const index = buildIndex(
    raws,
    urls.map((u) => u.slice(0, u.lastIndexOf("/") + 1))
  );
  if (embeddingsUrl) {
    // Embeddings are optional: without them retrieval is keyword only.
    try {
      const res = await fetcherFor(embeddingsUrl).fetch(embeddingsUrl, {
        cf: { cacheTtl: 600, cacheEverything: true },
      } as RequestInit);
      if (res.ok) {
        const file = (await res.json()) as EmbeddingsFile;
        const bytes = Uint8Array.from(atob(file.data), (ch) =>
          ch.charCodeAt(0)
        );
        index.setEmbeddings(file.ids, file.dim, new Int8Array(bytes.buffer));
      }
    } catch {
      /* keyword search still works */
    }
  }
  cached = { index, loadedAt: Date.now() };
  return index;
}
