/**
 * Spend and abuse guards backed by Workers KV.
 *
 * KV counters are eventually consistent, so these are soft limits: good enough
 * to stop a runaway script or a hot loop from burning the daily budget, not a
 * billing-grade meter. The hard cap on spend is still MAX_OUTPUT_TOKENS plus
 * the bounded retrieval context per request.
 */

export async function sha256Hex(input: string): Promise<string> {
  const data = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export interface LimitResult {
  allowed: boolean;
  retryAfterSeconds: number;
  reason?: "ip" | "budget";
}

export async function checkLimits(
  kv: KVNamespace,
  ip: string,
  perIpHourly: number,
  dailyBudget: number,
): Promise<LimitResult> {
  const now = new Date();
  const hour = `${now.toISOString().slice(0, 13)}`; // YYYY-MM-DDTHH
  const day = now.toISOString().slice(0, 10);
  const ipKey = `rl:ip:${(await sha256Hex(ip)).slice(0, 24)}:${hour}`;
  const dayKey = `rl:day:${day}`;

  const [ipCountRaw, dayCountRaw] = await Promise.all([kv.get(ipKey), kv.get(dayKey)]);
  const ipCount = Number(ipCountRaw ?? 0);
  const dayCount = Number(dayCountRaw ?? 0);

  if (ipCount >= perIpHourly) {
    const secondsLeft = 3600 - (now.getUTCMinutes() * 60 + now.getUTCSeconds());
    return { allowed: false, retryAfterSeconds: secondsLeft, reason: "ip" };
  }
  if (dayCount >= dailyBudget) {
    const secondsLeft =
      86400 - (now.getUTCHours() * 3600 + now.getUTCMinutes() * 60 + now.getUTCSeconds());
    return { allowed: false, retryAfterSeconds: secondsLeft, reason: "budget" };
  }
  await Promise.all([
    kv.put(ipKey, String(ipCount + 1), { expirationTtl: 3700 }),
    kv.put(dayKey, String(dayCount + 1), { expirationTtl: 90000 }),
  ]);
  return { allowed: true, retryAfterSeconds: 0 };
}

/** Normalize a question so trivially different phrasings share one cache entry. */
export function normalizeQuestion(question: string): string {
  return question
    .toLowerCase()
    .replace(/[“”"'`]/g, "")
    .replace(/\s+/g, " ")
    .replace(/[?!.\s]+$/g, "")
    .trim();
}
