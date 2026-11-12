/**
 * End-to-end evaluation against a running deployment.
 *
 *   npm run eval -- https://<host>/v1/ask [--min 0.9] [--only answer]
 *
 * For every case in questions.json it asks the question and checks the
 * reply kind reported in the `meta` event (answer, off_topic, company,
 * english_only) and, where given, that an expected page is among the
 * sources. Prints each failure and the pass rate, and exits non-zero when
 * the rate is below --min. The deployment's rate limits apply, so point it
 * at an instance configured for evaluation.
 */
import { readFileSync } from "node:fs";

interface Case {
  q: string;
  kind: string;
  source?: string;
}

const args = process.argv.slice(2);
const endpoint = args.find((a: string) => a.startsWith("http"));
const flag = (name: string) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : undefined;
};
if (!endpoint) {
  throw new Error(
    "usage: npm run eval -- https://<host>/v1/ask [--min 0.9] [--only <kind>]"
  );
}
const min = Number(flag("--min") ?? 0.9);
const only = flag("--only");
const file = decodeURIComponent(
  new URL("./questions.json", import.meta.url).pathname
);
const cases: Case[] = JSON.parse(readFileSync(file, "utf8")).cases.filter(
  (c: Case) => !only || c.kind === only
);

async function ask(
  q: string
): Promise<{ kind: string; sources: string[]; text: string; status: number }> {
  const res = await fetch(endpoint as string, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ question: q }),
  });
  if (!res.ok)
    return {
      kind: `http_${res.status}`,
      sources: [],
      text: "",
      status: res.status,
    };
  let kind = "";
  let text = "";
  const sources = new Set<string>();
  for (const frame of (await res.text()).split("\n\n")) {
    const event = frame.match(/^event: (.*)$/m)?.[1];
    const data = frame.match(/^data: (.*)$/m)?.[1];
    if (!event || !data) continue;
    const d = JSON.parse(data);
    if (event === "meta") kind = d.kind ?? "";
    if (event === "delta") text += d.text ?? "";
    if (event === "replace") text = d.text ?? "";
    if (event === "sources") for (const s of d) sources.add(s.url);
    if (event === "done") for (const s of d.sources ?? []) sources.add(s.url);
    if (event === "error") kind = "error";
  }
  return { kind, sources: [...sources], text, status: res.status };
}

let passed = 0;
const failures: string[] = [];
/** One retry: a dropped connection should not sink a 100-question run. */
async function askWithRetry(q: string) {
  try {
    return await ask(q);
  } catch {
    try {
      return await ask(q);
    } catch (err) {
      return {
        kind: `network_error: ${String(err)}`,
        sources: [],
        text: "",
        status: 0,
      };
    }
  }
}

for (const [i, c] of cases.entries()) {
  const r = await askWithRetry(c.q);
  if ((i + 1) % 10 === 0) console.log(`  ${i + 1}/${cases.length} asked`);
  const kindOk = r.kind === c.kind;
  const sourceOk =
    !c.source || r.sources.some((u) => u.includes(c.source as string));
  if (kindOk && sourceOk) {
    passed++;
  } else {
    failures.push(
      `- ${c.q}\n    expected ${c.kind}${c.source ? ` with source ~ ${c.source}` : ""}, got ${r.kind}${
        kindOk ? " but the source was missing" : ""
      }`
    );
  }
}
const rate = passed / cases.length;
if (failures.length) console.log(`Failures:\n${failures.join("\n")}\n`);
console.log(
  `${passed}/${cases.length} passed (${(rate * 100).toFixed(1)}%), minimum ${(min * 100).toFixed(0)}%`
);
process.exitCode = rate >= min ? 0 : 1;
