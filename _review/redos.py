import json, re, os, time
d = os.path.dirname(os.path.abspath(__file__))
schema = json.load(open(os.path.join(d, '../source/schemas/shopping/ap2_mandate.json')))
r = re.compile(schema['$defs']['checkout_mandate']['pattern'])

families = {
    'A: ("a.b.c~~"*n)+"!"':        lambda n: 'a.b.c~~' * n + '!',
    'B: ("a.b.c~"*n)':             lambda n: 'a.b.c~' * n,
    'C: "a.b.c"+("~a"*n)+"~!"':    lambda n: 'a.b.c' + '~a' * n + '~!',
    'D: ("a.a.a~a.a.a~~"*n)+"a"':  lambda n: 'a.a.a~a.a.a~~' * n + 'a',
    'E: ("a.b.c~aa~~"*n)+"~"':     lambda n: 'a.b.c~aa~~' * n + '~',
    'F: ("a.b.c~a~"*n)+"!"':       lambda n: 'a.b.c~a~' * n + '!',
    'G: "a.b.c"+("~aaaa"*n)+"."':  lambda n: 'a.b.c' + '~aaaa' * n + '.',
    'H: ("a..a~~"*n)+"a..a~a!"':   lambda n: 'a..a~~' * n + 'a..a~a!',
    'I: ("a.b.c~~a.b.c~a"*n)':     lambda n: 'a.b.c~~a.b.c~a' * n,
    'J: ("aaaa.aaaa.aaaa~"*n)+"+"':lambda n: 'aaaa.aaaa.aaaa~' * n + '+',
}
for name, gen in families.items():
    out = []
    for n in (500, 1000, 2000, 4000, 8000):
        s = gen(n)
        t0 = time.perf_counter()
        r.search(s)
        ms = (time.perf_counter() - t0) * 1000
        out.append(f'n={n}(len {len(s)}): {ms:.1f}ms')
        if ms > 3000:
            out.append('BLOWUP - stopping family')
            break
    print(name + '\n  ' + '  '.join(out))
