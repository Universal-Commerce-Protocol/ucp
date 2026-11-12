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
    "about into than then there these those we our they their me my ucp"
  ).split(" "),
);

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

function stem(word: string): string {
  if (word.length <= 4) return word;
  return word
    .replace(/(ies)$/, "y")
    .replace(/(ss)es$/, "$1")
    .replace(/(ing|ed|ly)$/, "")
    .replace(/(s)$/, "");
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

  constructor(chunks: Chunk[], pages: PageEntry[], version: string) {
    this.chunks = chunks;
    this.pages = pages;
    this.version = version;
    this.lengths = new Array(chunks.length);
    let total = 0;
    chunks.forEach((chunk, i) => {
      this.byId.set(chunk.id, chunk);
      // Headings and page titles are strong signals: weight them by repetition.
      const tokens = tokenize(
        `${chunk.page} ${chunk.page} ${chunk.heading} ${chunk.heading} ${chunk.heading} ${chunk.text}`,
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
  }

  get(id: string): Chunk | undefined {
    return this.byId.get(id);
  }

  /**
   * BM25 ranking. `boostUrlPrefix` nudges sections from the page the visitor is
   * currently reading, which disambiguates follow-ups like "what does this field mean".
   */
  search(query: string, k: number, opts: { exclude?: Set<string>; boostUrlPrefix?: string } = {}): Hit[] {
    const terms = tokenize(query);
    if (!terms.length) return [];
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
        scores.set(doc, (scores.get(doc) ?? 0) + idf * ((tf * (k1 + 1)) / norm));
      }
    }
    const hits: Hit[] = [];
    for (const [doc, raw] of scores) {
      const chunk = this.chunks[doc];
      if (opts.exclude?.has(chunk.id)) continue;
      let score = raw;
      if (opts.boostUrlPrefix && chunk.url.startsWith(opts.boostUrlPrefix)) score *= 1.15;
      hits.push({ chunk, score });
    }
    hits.sort((a, b) => b.score - a.score);
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
export function buildIndex(raws: RawIndex[], baseUrls: (string | undefined)[] = []): DocsIndex {
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
export async function loadIndex(urls: string[]): Promise<DocsIndex> {
  if (cached && Date.now() - cached.loadedAt < RELOAD_MS) return cached.index;
  const raws = await Promise.all(
    urls.map(async (url) => {
      const res = await fetch(url, { cf: { cacheTtl: 600, cacheEverything: true } } as RequestInit);
      if (!res.ok) throw new Error(`index fetch failed: ${url} ${res.status}`);
      return (await res.json()) as RawIndex;
    }),
  );
  const index = buildIndex(
    raws,
    urls.map((u) => u.slice(0, u.lastIndexOf("/") + 1)),
  );
  cached = { index, loadedAt: Date.now() };
  return index;
}
