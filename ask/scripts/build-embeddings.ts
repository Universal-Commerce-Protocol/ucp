/**
 * Build the embeddings file used for meaning-based retrieval.
 *
 *   CLOUDFLARE_ACCOUNT_ID=... CLOUDFLARE_API_TOKEN=... \
 *     npm run embeddings -- out.json site/ask-index.json latest/ask-index.json
 *
 * Embeds every section in the given ask-index.json files with a Workers AI
 * embedding model (EmbeddingGemma by default), normalizes each vector and
 * stores it as int8, which keeps ~1,500 sections of 768 dimensions near
 * 1 MB. Serve the output next to the index and point EMBEDDINGS_URL at it.
 * Re-run after the docs change; sections without an embedding are still
 * found by keyword search.
 */
import { readFileSync, writeFileSync } from "node:fs";

const [out, ...inputs] = process.argv.slice(2);
const account = process.env.CLOUDFLARE_ACCOUNT_ID;
const token = process.env.CLOUDFLARE_API_TOKEN;
const model = process.env.EMBED_MODEL ?? "@cf/google/embeddinggemma-300m";
if (!out || !inputs.length || !account || !token) {
  throw new Error(
    "usage: CLOUDFLARE_ACCOUNT_ID=.. CLOUDFLARE_API_TOKEN=.. npm run embeddings -- <out.json> <ask-index.json>..."
  );
}

interface IndexChunk {
  id: string;
  page: string;
  heading: string;
  text: string;
}

const chunks = new Map<string, IndexChunk>();
for (const path of inputs) {
  for (const c of JSON.parse(readFileSync(path, "utf8")).chunks as IndexChunk[])
    chunks.set(c.id, c);
}
const all = [...chunks.values()];

async function embed(texts: string[]): Promise<number[][]> {
  const url = `https://api.cloudflare.com/client/v4/accounts/${account}/ai/run/${model}`;
  for (let attempt = 0; ; attempt++) {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        authorization: `Bearer ${token}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({ text: texts }),
    });
    if (res.ok)
      return ((await res.json()) as { result: { data: number[][] } }).result
        .data;
    if (attempt >= 3)
      throw new Error(
        `embedding request failed: ${res.status} ${await res.text()}`
      );
    await new Promise((r) => setTimeout(r, 1500 * (attempt + 1)));
  }
}

let dim = 0;
const rows: Int8Array[] = [];
const BATCH = 40;
for (let i = 0; i < all.length; i += BATCH) {
  const batch = all.slice(i, i + BATCH);
  const vectors = await embed(
    batch.map((c) => `title: ${c.page} > ${c.heading} | text: ${c.text}`)
  );
  for (const v of vectors) {
    dim = v.length;
    const norm = Math.sqrt(v.reduce((s, x) => s + x * x, 0)) || 1;
    rows.push(
      Int8Array.from(v, (x) =>
        Math.max(-127, Math.min(127, Math.round((x / norm) * 127)))
      )
    );
  }
  console.log(`  ${Math.min(i + BATCH, all.length)}/${all.length} embedded`);
}

const data = new Int8Array(rows.length * dim);
rows.forEach((row, i) => {
  data.set(row, i * dim);
});
writeFileSync(
  out,
  JSON.stringify({
    model,
    dim,
    ids: all.map((c) => c.id),
    data: Buffer.from(data.buffer).toString("base64"),
  })
);
console.log(`wrote ${out}: ${rows.length} sections, ${dim} dimensions`);
