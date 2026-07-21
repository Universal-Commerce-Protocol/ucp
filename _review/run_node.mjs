import { readFileSync } from 'fs';
const dir = new URL('.', import.meta.url).pathname;
const schema = JSON.parse(readFileSync(dir + '../source/schemas/shopping/ap2_mandate.json', 'utf8'));
const pat = schema['$defs'].checkout_mandate.pattern;
// JSON Schema semantics: unanchored search, ECMA-262 'u'-less regex
const re = new RegExp(pat);
const vectors = JSON.parse(readFileSync(dir + 'vectors.json', 'utf8'));
let fails = 0;
for (const [group, expected] of [['expect_accept', true], ['expect_reject', false]]) {
  for (const [name, s] of vectors[group]) {
    const got = re.test(s);
    if (got !== expected) { fails++; console.log(`FAIL [${group}] ${name}: ${JSON.stringify(s)} -> ${got}`); }
  }
}
console.log(fails === 0 ? 'accept/reject tables: ALL PASS (node)' : `${fails} FAILURES (node)`);
for (const [name, s] of vectors.questionable) {
  console.log(`Q: ${name}: ${JSON.stringify(s)} -> ${re.test(s) ? 'ACCEPT' : 'reject'}`);
}
// engine semantics: trailing newline
for (const s of ['a.b.c~\n', 'a.b.c\n', 'a.b.c~d~\n']) {
  console.log(`NEWLINE node: ${JSON.stringify(s)} -> ${re.test(s)}`);
}
