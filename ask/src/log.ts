/**
 * Anonymous question/answer log.
 *
 * Purpose: build the dataset for a later fine-tune (Shopify's approach: train
 * on successful, human-rated interactions) and surface documentation gaps
 * (questions the assistant could not ground). Nothing identifying is stored:
 * no IP, user agent, cookies or timestamps finer than the day bucket.
 *
 * Storage is Workers KV: one write per answer, one per feedback click. At
 * KV's pricing that is cents per month even at tens of thousands of answers.
 * Entries expire after LOG_TTL_DAYS. Export a day as JSONL via
 * GET /v1/export?day=YYYY-MM-DD with the EXPORT_TOKEN bearer secret.
 */

export interface LogEntry {
  id: string;
  day: string;
  /** "answered" | "cached" | "gated" | "replaced" | "error" */
  outcome: string;
  question: string;
  /** Number of prior turns the question came with (content is not stored). */
  historyTurns: number;
  /** Section URLs shown to the model, in rank order. */
  sources: string[];
  answer?: string;
  model?: string;
  grounding?: number;
  latencyMs?: number;
  /** Set by /v1/feedback: true = helpful, false = not helpful. */
  helpful?: boolean;
}

export function newLogId(): string {
  const bytes = new Uint8Array(8);
  crypto.getRandomValues(bytes);
  return [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function logKey(day: string, id: string): string {
  return `log:${day}:${id}`;
}

export async function writeLog(
  kv: KVNamespace,
  entry: LogEntry,
  ttlDays: number
): Promise<void> {
  await kv.put(logKey(entry.day, entry.id), JSON.stringify(entry), {
    expirationTtl: Math.max(1, ttlDays) * 86400,
  });
}

export async function recordFeedback(
  kv: KVNamespace,
  day: string,
  id: string,
  helpful: boolean,
  ttlDays: number
): Promise<boolean> {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day) || !/^[0-9a-f]{16}$/.test(id))
    return false;
  const entry = await kv.get<LogEntry>(logKey(day, id), "json");
  if (!entry) return false;
  entry.helpful = helpful;
  await writeLog(kv, entry, ttlDays);
  return true;
}

/** All entries for one day as JSON Lines. */
export async function exportDay(kv: KVNamespace, day: string): Promise<string> {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) return "";
  const lines: string[] = [];
  let cursor: string | undefined;
  do {
    const page = await kv.list({ prefix: `log:${day}:`, cursor });
    const values = await Promise.all(page.keys.map((k) => kv.get(k.name)));
    for (const v of values) if (v) lines.push(v);
    cursor = page.list_complete ? undefined : page.cursor;
  } while (cursor);
  return lines.join("\n");
}
