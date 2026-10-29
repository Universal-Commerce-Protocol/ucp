#!/usr/bin/env python3
# cspell:ignore poqk Giymh dvez Solq XBCW Gxne kuwsx Axyuf Papi Mlrw qmark
"""Tests for the HTTP Message Signature test vectors.

The Message Signatures specification publishes test vectors for the UCP
profile of RFC 9421 (docs/specification/signatures/test-vectors.json,
quoted in docs/specification/signatures.md). These tests keep that
corpus trustworthy:

  - **Builder correctness.** The signature-base builder and signature
    primitives in scripts/signature_vectors.py are checked against the
    vectors RFC 9421 itself publishes in Appendix B.2.4 (ECDSA P-256)
    and B.2.6 (Ed25519), including byte-exact reproduction of the
    deterministic Ed25519 signature.
  - **Corpus validity.** Every published vector is rebuilt from its
    message and verified from first principles: the Content-Digest
    matches the body bytes, the signature base matches the covered
    components, the signature verifies under the published key, and the
    deterministic signatures reproduce exactly.
  - **Corpus completeness.** The corpus is byte-identical to what the
    generator produces, so an edit to the generator without a
    regenerated corpus (or vice versa) fails.
  - **Docs sync.** signatures.md quotes every vector's message,
    signature base, and the test keys verbatim.
  - **Contract enforcement.** Negative cases prove a tampered body,
    header, signature, or key is rejected, and that the spec-mandated
    coverage, encoding, and WBA keyid rules are what the builder does.

Run: uv run python scripts/test_signature_vectors.py
Exit: 0 on all pass, 1 on any failure.
"""

import copy
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import signature_vectors as sv  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
DOC_PATH = REPO_ROOT / "docs" / "specification" / "signatures.md"

# -----------------------------------------------------------
# Test harness (minimal, no deps)
# -----------------------------------------------------------

_RESULTS: list[tuple[str, bool, str]] = []


def _check(name: str, condition: bool, detail: str = "") -> None:
  """Record a test result."""
  _RESULTS.append((name, condition, detail))


def _report() -> int:
  """Print results and return exit code."""
  passed = sum(1 for _, ok, _ in _RESULTS if ok)
  failed = [(n, d) for n, ok, d in _RESULTS if not ok]
  for name, ok, detail in _RESULTS:
    status = "PASS" if ok else "FAIL"
    suffix = f" — {detail}" if detail and not ok else ""
    print(f"  {status}  {name}{suffix}")
  print(f"\n{passed} passed, {len(failed)} failed")
  return 0 if not failed else 1


def _problems_as_detail(problems: list[str]) -> str:
  return "; ".join(problems)


# -----------------------------------------------------------
# Builder correctness: RFC 9421 Appendix B
# -----------------------------------------------------------


def test_rfc9421_self_test() -> None:
  """The builder reproduces and verifies RFC 9421's own vectors."""
  problems = sv.self_test()
  _check(
    "rfc9421_appendix_b_vectors", not problems, _problems_as_detail(problems)
  )


def test_rfc9421_b26_reproduced_byte_exact() -> None:
  """Deterministic Ed25519 reproduces the RFC's B.2.6 signature bytes."""
  okp = dict(sv.TEST_KEY_ED25519, kid="test-key-ed25519")
  label, comps, params = sv.parse_signature_input(sv.RFC_B26_INPUT)
  base = sv.signature_base(sv.RFC_TEST_REQUEST, comps, params)
  produced = f"{label}=:{sv.b64(sv.sign(okp, base))}:"
  _check(
    "rfc9421_b26_signature_reproduced",
    produced == sv.RFC_B26_SIGNATURE,
    produced,
  )


def test_content_digest_matches_rfc9530_example() -> None:
  """Content-Digest follows RFC 9530: sha-256 of the raw bytes, base64."""
  # RFC 9530 §B.1 example: {"hello": "world"} with sha-256.
  body = b'{"hello": "world"}'
  expected = "sha-256=:X48E9qOokqqrvdts8nOJRJN3OWDUoyWxBf7kbu9DBPE=:"
  _check("content_digest_rfc9530_example", sv.content_digest(body) == expected)


def test_ed25519_kid_is_thumbprint() -> None:
  """The Ed25519 test key's kid is its RFC 7638 thumbprint (WBA rule)."""
  _check(
    "ed25519_kid_is_rfc7638_thumbprint",
    sv.jwk_thumbprint(sv.TEST_KEY_ED25519) == sv.TEST_KEY_ED25519["kid"],
  )


# -----------------------------------------------------------
# Corpus validity and completeness
# -----------------------------------------------------------


def _load_corpus() -> dict:
  return json.loads(sv.VECTORS_PATH.read_text(encoding="utf-8"))


def test_corpus_exists() -> None:
  """The corpus file is published alongside the specification."""
  _check("corpus_file_exists", sv.VECTORS_PATH.is_file(), str(sv.VECTORS_PATH))


def test_corpus_vectors_verify() -> None:
  """Every published vector verifies from first principles."""
  corpus = _load_corpus()
  for vid, problems in sv.verify_corpus(corpus).items():
    _check(
      f"vector_verifies[{vid}]", not problems, _problems_as_detail(problems)
    )


def test_corpus_matches_generator() -> None:
  """The committed corpus is exactly what the generator produces."""
  committed = sv.VECTORS_PATH.read_text(encoding="utf-8")
  generated = json.dumps(sv.generate(), indent=2, ensure_ascii=False) + "\n"
  _check(
    "corpus_matches_generator",
    committed == generated,
    "run: uv run python scripts/signature_vectors.py generate",
  )


def test_corpus_keys_are_rfc9421_test_keys() -> None:
  """Keys are the RFC 9421 B.1.3 / B.1.4 pairs, private part included."""
  corpus = _load_corpus()
  kids = {k["kid"] for k in corpus["keys"]}
  _check(
    "corpus_keys_are_rfc9421_keys",
    kids
    == {"test-key-ecc-p256", "poqkLGiymh_W0uP6PZFw-dvez3QJT5SolqXBCW38r0U"},
    str(kids),
  )
  _check(
    "corpus_keys_carry_private_member",
    all("d" in k for k in corpus["keys"]),
  )


def test_corpus_covers_every_signing_scenario() -> None:
  """One vector per scenario the specification describes."""
  corpus = _load_corpus()
  ids = {v["id"] for v in corpus["vectors"]}
  expected = {
    "rest-request-es256",
    "rest-get-es256",
    "rest-response-es256",
    "wba-request-ed25519",
    "webhook-request-es256",
    "mcp-request-es256",
  }
  _check("corpus_scenarios", ids == expected, str(sorted(ids ^ expected)))


def test_vectors_cover_required_components() -> None:
  """Each vector covers everything the spec's coverage gate requires."""
  corpus = _load_corpus()
  for v in corpus["vectors"]:
    covered = set(v["covered_components"])
    headers = {k.lower() for k in v["headers"]}
    if "request" in v:
      required = {'"@method"', '"@authority"', '"@path"'}
      if v["request"].get("query"):
        required.add('"@query"')
      if "ucp-agent" in headers:
        required.add('"ucp-agent"')
      if "idempotency-key" in headers:
        required.add('"idempotency-key"')
      if "webhook-id" in headers:
        required.add('"webhook-id"')
      if "webhook-timestamp" in headers:
        required.add('"webhook-timestamp"')
      if "signature-agent" in headers:
        required.add('"signature-agent";key="sig1"')
    else:
      required = {'"@status"'}
    if v["body"]:
      required |= {'"content-digest"', '"content-type"'}
    missing = required - covered
    _check(f"coverage_gate[{v['id']}]", not missing, str(sorted(missing)))


def test_ecdsa_signatures_are_raw_64_bytes() -> None:
  """ES256 signatures are raw r||s (64 bytes), never DER."""
  corpus = _load_corpus()
  for v in corpus["vectors"]:
    if v["algorithm"] != "ES256":
      continue
    raw = sv.parse_signature(v["signature"], v["label"])
    _check(f"es256_raw_encoding[{v['id']}]", len(raw) == 64, str(len(raw)))


def test_wba_vector_shape() -> None:
  """The WBA-shape vector carries what the spec's opt-in list mandates."""
  corpus = _load_corpus()
  v = next(x for x in corpus["vectors"] if x["id"] == "wba-request-ed25519")
  params = v["signature_params"]
  key = sv.key_by_kid(corpus["keys"], v["kid"])
  _check("wba_tag", params.get("tag") == "web-bot-auth")
  _check("wba_created_and_expires", "created" in params and "expires" in params)
  _check("wba_nonce_present", isinstance(params.get("nonce"), str))
  _check("wba_keyid_is_thumbprint", params["keyid"] == sv.jwk_thumbprint(key))
  _check(
    "wba_signature_agent_label_bound",
    v["headers"]["Signature-Agent"].startswith(f"{v['label']}=")
    and '"signature-agent";key="sig1"' in v["covered_components"],
  )
  _check(
    "wba_keeps_ucp_agent",
    "UCP-Agent" in v["headers"] and '"ucp-agent"' in v["covered_components"],
  )


# -----------------------------------------------------------
# Contract enforcement (negative cases)
# -----------------------------------------------------------


def _vector(corpus: dict, vid: str) -> dict:
  return copy.deepcopy(next(v for v in corpus["vectors"] if v["id"] == vid))


def test_tampered_body_fails() -> None:
  """Changing one body byte breaks the digest and the signature."""
  corpus = _load_corpus()
  v = _vector(corpus, "rest-request-es256")
  v["body"] = v["body"].replace('"quantity":2', '"quantity":3')
  problems = sv.verify_vector(v, corpus["keys"])
  _check(
    "tampered_body_rejected",
    any("content-digest" in p for p in problems),
    _problems_as_detail(problems),
  )


def test_tampered_covered_header_fails() -> None:
  """Changing a covered header without re-signing fails verification."""
  corpus = _load_corpus()
  v = _vector(corpus, "rest-request-es256")
  v["headers"]["Idempotency-Key"] = "00000000-0000-4000-8000-000000000000"
  problems = sv.verify_vector(v, corpus["keys"])
  _check(
    "tampered_header_rejected",
    any("signature_base" in p for p in problems),
    _problems_as_detail(problems),
  )


def test_tampered_signature_fails() -> None:
  """A flipped signature byte fails verification."""
  corpus = _load_corpus()
  v = _vector(corpus, "rest-response-es256")
  raw = bytearray(sv.parse_signature(v["signature"], v["label"]))
  raw[0] ^= 0x01
  v["signature"] = f"{v['label']}=:{sv.b64(bytes(raw))}:"
  problems = sv.verify_vector(v, corpus["keys"])
  _check(
    "tampered_signature_rejected",
    any("does not verify" in p for p in problems),
    _problems_as_detail(problems),
  )


def test_wrong_key_fails() -> None:
  """Verifying under a different key of the same algorithm fails."""
  corpus = _load_corpus()
  v = _vector(corpus, "wba-request-ed25519")
  other = dict(sv.TEST_KEY_ED25519)
  # A different Ed25519 key: the RFC 8032 §7.1 TEST 1 key pair.
  other["d"] = "nWGxne_9WmC6hEr0kuwsxERJxWl7MmkZcDusAxyuf2A"
  other["x"] = "11qYAYKxCrfVS_7TyWQHOg7hcvPapiMlrwIaaPcHURo"
  other["kid"] = v["kid"]
  keys = [k for k in corpus["keys"] if k["kid"] != v["kid"]] + [other]
  problems = sv.verify_vector(v, keys)
  _check(
    "wrong_key_rejected",
    any("does not verify" in p for p in problems),
    _problems_as_detail(problems),
  )


def test_der_encoded_ecdsa_rejected() -> None:
  """A DER-encoded ECDSA signature is not accepted as raw r||s."""
  corpus = _load_corpus()
  v = _vector(corpus, "rest-request-es256")
  key = sv.key_by_kid(corpus["keys"], v["kid"])
  raw = sv.parse_signature(v["signature"], v["label"])
  from cryptography.hazmat.primitives.asymmetric.utils import (
    encode_dss_signature,
  )

  der = encode_dss_signature(
    int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")
  )
  _check(
    "der_ecdsa_rejected",
    not sv.verify(key, v["signature_base"], der)
    and sv.verify(key, v["signature_base"], raw),
  )


def test_dictionary_member_selection() -> None:
  """;key selects and re-serializes one Dictionary member with its params."""
  value = 'sig1="https://platform.example/.well-known/ucp";type=jwks_uri'
  got = sv.sf_dictionary_member(value, "sig1")
  _check(
    "sf_dictionary_member_serialization",
    got == '"https://platform.example/.well-known/ucp";type=jwks_uri',
    got,
  )
  multi = 'a=1, sig1="x";type=directory, b=?1'
  _check(
    "sf_dictionary_member_among_others",
    sv.sf_dictionary_member(multi, "sig1") == '"x";type=directory',
  )
  try:
    sv.sf_dictionary_member(value, "sig2")
    _check("sf_dictionary_member_missing_raises", False)
  except KeyError:
    _check("sf_dictionary_member_missing_raises", True)


def test_missing_covered_header_raises() -> None:
  """Building a base over a field the message lacks is an error."""
  msg = sv.Message(headers={}, method="GET", authority="a", path="/")
  try:
    sv.signature_base(msg, [sv.Component("idempotency-key")], {})
    _check("missing_covered_field_raises", False)
  except ValueError:
    _check("missing_covered_field_raises", True)


def test_query_component_includes_question_mark() -> None:
  """@query is serialized with its leading '?' (RFC 9421 §2.2.7)."""
  msg = sv.Message(
    headers={}, method="GET", authority="a", path="/p", query="x=1&y=2"
  )
  base = sv.signature_base(msg, [sv.Component("@query")], {})
  _check("query_component_leading_qmark", base.startswith('"@query": ?x=1&y=2'))


# -----------------------------------------------------------
# Docs sync
# -----------------------------------------------------------


def test_docs_quote_corpus_verbatim() -> None:
  """signatures.md quotes every vector's message and signature base."""
  doc = DOC_PATH.read_text(encoding="utf-8")
  corpus = _load_corpus()
  _check(
    "docs_link_corpus",
    "signatures/test-vectors.json" in doc,
    "add a link to the machine-readable corpus",
  )
  for key in corpus["keys"]:
    rendered = json.dumps(key, indent=2)
    _check(f"docs_quote_key[{key['kid']}]", rendered in doc)
  for v in corpus["vectors"]:
    _check(f"docs_quote_message[{v['id']}]", v["message"] in doc)
    _check(f"docs_quote_base[{v['id']}]", v["signature_base"] in doc)
    _check(f"docs_name_vector[{v['id']}]", f"`{v['id']}`" in doc)


# -----------------------------------------------------------
# Signed examples on the specification pages
# -----------------------------------------------------------

SPEC_DIR = REPO_ROOT / "docs" / "specification"

PAGE_COMPONENTS = (
  '("@method" "@authority" "@path" "ucp-agent" "idempotency-key" '
  '"content-digest" "content-type")'
)

PAGE_EXAMPLE = """\
Some prose.

```http
POST /checkout-sessions HTTP/1.1
Host: merchant.example.com
Content-Type: application/json
UCP-Agent: profile="https://platform.example/.well-known/ucp"
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Digest: sha-256=:X48E9q...:
Signature-Input: sig1=PAGE_COMPONENTS;keyid="platform-2026"
Signature: sig1=:6G4i8TS6oUkGrx8KnCFUpsSPwd74...:

{"line_items":[{"item":{"id":"item_123"},"quantity":2}]}
```

A fragment that only shows the shape:

```http
POST /checkout-sessions HTTP/1.1
Signature-Input: sig1=("@method" "@authority" ...);keyid="platform-2026"
Signature: sig1=:6G4i8TS6oUkGrx8KnCFUpsSPwd74...:
```
""".replace("PAGE_COMPONENTS", PAGE_COMPONENTS)


def _page(tmp: Path, text: str = PAGE_EXAMPLE) -> Path:
  path = tmp / "page.md"
  path.write_text(text, encoding="utf-8")
  return path


def test_spec_pages_signed_examples_verify() -> None:
  """Every complete signed example on the spec pages verifies."""
  examples = sv.find_signed_examples([SPEC_DIR])
  _check(
    "spec_pages_have_signed_examples",
    len(examples) >= 20,
    f"found {len(examples)}",
  )
  for ex in examples:
    problems = sv.verify_example(ex, sv.TEST_KEYS)
    _check(f"spec_example_verifies[{ex.where}]", not problems, str(problems))


def test_spec_pages_are_signed_in_place() -> None:
  """sign-docs is a no-op on the committed pages."""
  import tempfile
  import shutil

  with tempfile.TemporaryDirectory() as tmp:
    copy_dir = Path(tmp) / "specification"
    shutil.copytree(SPEC_DIR, copy_dir)
    changed = sv.sign_docs([copy_dir])
    _check("spec_pages_signed_in_place", changed == [], str(changed))


def test_placeholder_example_fails_until_signed() -> None:
  """A placeholder example fails verification; sign-docs repairs it."""
  import tempfile

  with tempfile.TemporaryDirectory() as tmp:
    page = _page(Path(tmp))
    found = sv.find_signed_examples([page])
    _check("placeholder_found_fragment_skipped", len(found) == 1, str(found))
    problems = sv.verify_example(found[0], sv.TEST_KEYS)
    _check(
      "placeholder_rejected",
      any("not a published test key" in p for p in problems),
      str(problems),
    )
    changed = sv.sign_docs([page])
    _check("placeholder_signed", changed == [found[0].where], str(changed))
    signed = sv.find_signed_examples([page])[0]
    _check(
      "placeholder_verifies_after_signing",
      sv.verify_example(signed, sv.TEST_KEYS) == [],
    )
    body = signed.lines[-1]
    _check("placeholder_body_untouched", body == PAGE_EXAMPLE.split("\n")[12])
    digest = [
      line for line in signed.lines if line.startswith("Content-Digest")
    ]
    expected = f"Content-Digest: {sv.content_digest(body.encode())}"
    _check("placeholder_digest_is_real", digest == [expected], str(digest))
    _check(
      "placeholder_components_kept",
      PAGE_COMPONENTS in signed.lines[6],
      signed.lines[6],
    )
    _check("sign_docs_idempotent", sv.sign_docs([page]) == [])


def test_tampered_page_example_is_reported() -> None:
  """Editing a signed example's body or a covered header fails verification."""
  import tempfile

  with tempfile.TemporaryDirectory() as tmp:
    page = _page(Path(tmp))
    sv.sign_docs([page])
    good = page.read_text(encoding="utf-8")

    page.write_text(good.replace('"quantity":2', '"quantity":3'), "utf-8")
    problems = sv.verify_example(
      sv.find_signed_examples([page])[0], sv.TEST_KEYS
    )
    _check(
      "tampered_body_reported",
      any(p.startswith("content-digest") for p in problems),
      str(problems),
    )

    page.write_text(
      good.replace("Idempotency-Key: 550e", "Idempotency-Key: 660e"), "utf-8"
    )
    problems = sv.verify_example(
      sv.find_signed_examples([page])[0], sv.TEST_KEYS
    )
    _check(
      "tampered_header_reported",
      problems == ["signature does not verify"],
      str(problems),
    )


def test_page_example_coverage_gate() -> None:
  """A header the spec requires to be covered but is not is reported."""
  import tempfile

  with tempfile.TemporaryDirectory() as tmp:
    text = PAGE_EXAMPLE.replace(
      ' "ucp-agent" "idempotency-key"', ' "idempotency-key"'
    )
    page = _page(Path(tmp), text)
    sv.sign_docs([page])
    problems = sv.verify_example(
      sv.find_signed_examples([page])[0], sv.TEST_KEYS
    )
    _check(
      "coverage_gate_reported",
      problems == ["coverage gate: not covered ['\"ucp-agent\"']"],
      str(problems),
    )


def test_page_example_der_signature_rejected() -> None:
  """A DER-encoded ECDSA value on a page is named as such."""
  import tempfile

  with tempfile.TemporaryDirectory() as tmp:
    page = _page(Path(tmp))
    sv.sign_docs([page])
    text = page.read_text(encoding="utf-8")
    sig_line = next(
      line for line in text.split("\n") if line.startswith("Signature: ")
    )
    der = (
      # cspell:disable-next-line
      "MEUCIQDTxNq8h7LGHpvVZQp1iHkFp9+3N8Mxk2zH1wK4YuVN8wIgQ2hhbmdlZCB0aGUg"
      # cspell:disable-next-line
      "c2lnbmF0dXJlIHRvIERFUiBlbmNvZGluZw=="
    )
    page.write_text(text.replace(sig_line, f"Signature: sig1=:{der}:"), "utf-8")
    problems = sv.verify_example(
      sv.find_signed_examples([page])[0], sv.TEST_KEYS
    )
    _check(
      "der_page_signature_rejected",
      any("raw r||s is 64 (not DER)" in p for p in problems),
      str(problems),
    )


def test_page_example_without_body_drops_digest() -> None:
  """A GET example carries no Content-Digest after signing."""
  import tempfile

  text = """\
```http
GET /checkout-sessions/chk_123 HTTP/1.1
Host: merchant.example.com
UCP-Agent: profile="https://platform.example/.well-known/ucp"
Content-Digest: sha-256=:X48E9q...:
Signature-Input: sig1=GET_COMPONENTS;keyid="platform-2026"
Signature: sig1=:placeholder:
```
""".replace("GET_COMPONENTS", '("@method" "@authority" "@path" "ucp-agent")')
  with tempfile.TemporaryDirectory() as tmp:
    page = _page(Path(tmp), text)
    sv.sign_docs([page])
    signed = sv.find_signed_examples([page])[0]
    _check(
      "get_example_has_no_digest",
      not any(line.startswith("Content-Digest") for line in signed.lines),
      str(signed.lines),
    )
    _check(
      "get_example_verifies", sv.verify_example(signed, sv.TEST_KEYS) == []
    )
    corpus_get = next(
      v for v in _load_corpus()["vectors"] if v["id"] == "rest-get-es256"
    )
    _check(
      "get_example_matches_corpus_vector",
      signed.lines[-1] == f"Signature: {corpus_get['signature']}",
      signed.lines[-1],
    )


# -----------------------------------------------------------
# Runner
# -----------------------------------------------------------


def main() -> int:
  """Run every test and report."""
  tests = [
    test_rfc9421_self_test,
    test_rfc9421_b26_reproduced_byte_exact,
    test_content_digest_matches_rfc9530_example,
    test_ed25519_kid_is_thumbprint,
    test_corpus_exists,
    test_corpus_vectors_verify,
    test_corpus_matches_generator,
    test_corpus_keys_are_rfc9421_test_keys,
    test_corpus_covers_every_signing_scenario,
    test_vectors_cover_required_components,
    test_ecdsa_signatures_are_raw_64_bytes,
    test_wba_vector_shape,
    test_tampered_body_fails,
    test_tampered_covered_header_fails,
    test_tampered_signature_fails,
    test_wrong_key_fails,
    test_der_encoded_ecdsa_rejected,
    test_dictionary_member_selection,
    test_missing_covered_header_raises,
    test_query_component_includes_question_mark,
    test_docs_quote_corpus_verbatim,
    test_spec_pages_signed_examples_verify,
    test_spec_pages_are_signed_in_place,
    test_placeholder_example_fails_until_signed,
    test_tampered_page_example_is_reported,
    test_page_example_coverage_gate,
    test_page_example_der_signature_rejected,
    test_page_example_without_body_drops_digest,
  ]
  for test in tests:
    try:
      test()
    except Exception as e:  # noqa: BLE001
      _check(test.__name__, False, f"{type(e).__name__}: {e}")
  return _report()


if __name__ == "__main__":
  sys.exit(main())
