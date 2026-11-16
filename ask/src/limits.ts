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
  return [...new Uint8Array(digest)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
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
  dailyBudget: number
): Promise<LimitResult> {
  const now = new Date();
  const hour = `${now.toISOString().slice(0, 13)}`; // YYYY-MM-DDTHH
  const day = now.toISOString().slice(0, 10);
  const ipKey = `rl:ip:${(await sha256Hex(ip)).slice(0, 24)}:${hour}`;
  const dayKey = `rl:day:${day}`;

  const [ipCountRaw, dayCountRaw] = await Promise.all([
    kv.get(ipKey),
    kv.get(dayKey),
  ]);
  const ipCount = Number(ipCountRaw ?? 0);
  const dayCount = Number(dayCountRaw ?? 0);

  if (ipCount >= perIpHourly) {
    const secondsLeft = 3600 - (now.getUTCMinutes() * 60 + now.getUTCSeconds());
    return { allowed: false, retryAfterSeconds: secondsLeft, reason: "ip" };
  }
  if (dayCount >= dailyBudget) {
    const secondsLeft =
      86400 -
      (now.getUTCHours() * 3600 +
        now.getUTCMinutes() * 60 +
        now.getUTCSeconds());
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

/**
 * Cache key text for a question. Reduces the question to its sorted set of
 * content terms (stemmed, filler words dropped), so different wordings such as
 * "What status values can a checkout have?", "checkout status values" and
 * "which statuses does a checkout have" share one cached answer and only
 * the first of them costs a model call. Words that flip the meaning are
 * kept, so "can" and "cannot" questions never share an entry. Falls back
 * to the normalized text when nothing is left.
 */
export function cacheSignature(question: string, tokens: string[]): string {
  const normalized = normalizeQuestion(question);
  const polarity =
    /\b(not|no|never|without|cannot|can't|isn't|doesn't|don't|won't|except|unless)\b/.test(
      normalized
    )
      ? "neg"
      : "pos";
  const terms = [...new Set(tokens)].sort();
  return terms.length >= 2
    ? `${polarity}|${terms.join(" ")}`
    : `${polarity}|${normalized}`;
}

// cspell:disable
const FOREIGN_WORDS = new Set(
  // Very common function words in Spanish, French, German, Portuguese,
  // Italian, Dutch, Turkish and Indonesian that are not also English words.
  (
    "el la los las una unos qué como cómo para por con del está puedo quiero necesito hacer " +
    "le les des une est avec pour dans que qui comment puis veux faire sur " +
    "der die das und ist nicht wie kann ich mit für ein eine auf wird " +
    "o os uma não é com em posso fazer você " +
    "il gli che non sono posso voglio fare della " +
    "het een niet hoe kan ik voor " +
    "bir ve nasıl için bu " +
    "yang dan bagaimana untuk saya"
  ).split(" ")
);
// cspell:enable
const ENGLISH_WORDS = new Set(
  "the is are does do how what why when where which can could should would with for and of to in on it this that my i we you".split(
    " "
  )
);

/**
 * True when a question is clearly not written in English: mostly a
 * non-Latin script, or Latin script with several foreign function words and
 * no English ones. Deliberately conservative, since product names, code and
 * the odd borrowed word must not trip it.
 */
export function isClearlyNotEnglish(question: string): boolean {
  const letters = question.match(/\p{L}/gu) ?? [];
  if (letters.length < 4) return false;
  const nonLatin = letters.filter((c) => !/\p{Script=Latin}/u.test(c)).length;
  if (nonLatin / letters.length >= 0.3) return true;
  const words = question.toLowerCase().match(/\p{L}+/gu) ?? [];
  const foreign = words.filter((w) => FOREIGN_WORDS.has(w)).length;
  const english = words.filter((w) => ENGLISH_WORDS.has(w)).length;
  return foreign >= 2 && english === 0;
}
