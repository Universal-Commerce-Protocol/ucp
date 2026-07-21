import json, re, os, sys
d = os.path.dirname(os.path.abspath(__file__))
schema = json.load(open(os.path.join(d, '../source/schemas/shopping/ap2_mandate.json')))
pat = schema['$defs']['checkout_mandate']['pattern']
r = re.compile(pat)
vectors = json.load(open(os.path.join(d, 'vectors.json')))
fails = 0
for group, expected in (('expect_accept', True), ('expect_reject', False)):
    for name, s in vectors[group]:
        got = bool(r.search(s))  # jsonschema lib uses re.search
        if got != expected:
            fails += 1
            print(f'FAIL [{group}] {name}: {s!r} -> {got}')
print('accept/reject tables: ALL PASS (python re.search)' if fails == 0 else f'{fails} FAILURES (python)')
for name, s in vectors['questionable']:
    print(f'Q: {name}: {s!r} -> {"ACCEPT" if r.search(s) else "reject"}')
# engine semantics: trailing newline ($ before final \n in python)
for s in ['a.b.c~\n', 'a.b.c\n', 'a.b.c~d~\n', 'a.b.c\n\n', '\na.b.c']:
    print(f'NEWLINE py search: {s!r} -> {bool(r.search(s))}  fullmatch: {bool(r.fullmatch(s))}')
# jsonschema library behavior if installed
try:
    import jsonschema
    v = jsonschema.Draft202012Validator({'type': 'string', 'pattern': pat})
    for s in ['a.b.c~\n', 'a.b.c~']:
        print(f'jsonschema {jsonschema.__version__}: {s!r} valid={v.is_valid(s)}')
except ImportError:
    print('jsonschema lib not installed')
try:
    import pydantic
    from pydantic import BaseModel, StringConstraints
    from typing import Annotated
    class M(BaseModel):
        x: Annotated[str, StringConstraints(pattern=pat)]
    for s in ['a.b.c~\n', 'a.b.c~']:
        try:
            M(x=s); ok = True
        except Exception:
            ok = False
        print(f'pydantic {pydantic.VERSION}: {s!r} valid={ok}')
except ImportError:
    print('pydantic not installed')
