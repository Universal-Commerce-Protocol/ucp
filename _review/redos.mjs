import { readFileSync } from 'fs';
const dir = new URL('.', import.meta.url).pathname;
const schema = JSON.parse(readFileSync(dir + '../source/schemas/shopping/ap2_mandate.json', 'utf8'));
const re = new RegExp(schema['$defs'].checkout_mandate.pattern);

const families = {
  'A: ("a.b.c~~"*n)+"!"':            n => 'a.b.c~~'.repeat(n) + '!',
  'B: ("a.b.c~"*n)':                 n => 'a.b.c~'.repeat(n),
  'C: "a.b.c"+("~a"*n)+"~!"':        n => 'a.b.c' + '~a'.repeat(n) + '~!',
  'D: ("a.a.a~a.a.a~~"*n)+"a"':      n => 'a.a.a~a.a.a~~'.repeat(n) + 'a',
  'E: ("a.b.c~aa~~"*n)+"~"':         n => 'a.b.c~aa~~'.repeat(n) + '~',
  'F: ("a.b.c~a~"*n)+"!"':           n => 'a.b.c~a~'.repeat(n) + '!',
  'G: "a.b.c"+("~aaaa"*n)+"."':      n => 'a.b.c' + '~aaaa'.repeat(n) + '.',
  'H: ("a..a~~"*n)+"a..a~a"+"!"':    n => 'a..a~~'.repeat(n) + 'a..a~a' + '!',
  'I: ("a.b.c~~a.b.c~a"*n)':         n => 'a.b.c~~a.b.c~a'.repeat(n),
  'J: ("aaaa.aaaa.aaaa~"*n)+"+"':    n => 'aaaa.aaaa.aaaa~'.repeat(n) + '+',
};
for (const [name, gen] of Object.entries(families)) {
  const times = [];
  for (const n of [1000, 2000, 4000, 8000, 16000]) {
    const s = gen(n);
    const t0 = process.hrtime.bigint();
    re.test(s);
    const ms = Number(process.hrtime.bigint() - t0) / 1e6;
    times.push(`n=${n}(len ${s.length}): ${ms.toFixed(1)}ms`);
    if (ms > 3000) { times.push('BLOWUP - stopping family'); break; }
  }
  console.log(name + '\n  ' + times.join('  '));
}
