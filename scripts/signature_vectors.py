#!/usr/bin/env python3
# cspell:ignore SECP Pvqei Xymy Juahq Nyeald Jwew oiasw
"""Generate and verify the UCP HTTP Message Signature test vectors.

The Message Signatures specification (docs/specification/signatures.md)
profiles RFC 9421 for UCP: which components a signature covers, how the
body is bound through an RFC 9530 ``Content-Digest``, how ECDSA
signatures are encoded, and how a Web Bot Auth-shaped signature differs
from a default UCP one. Every example signature on that page is a
placeholder, so an implementer has nothing to run their signer or
verifier against. This module produces vectors they can, and keeps the
published copies honest.

Where the vectors live
======================

  docs/specification/signatures/test-vectors.json
      The machine-readable corpus. Published with the specification at
      ``/{version}/specification/signatures/test-vectors.json``.

  docs/specification/signatures.md, section "Test Vectors"
      The same vectors, quoted for human readers.

  scripts/test_signature_vectors.py
      Verifies the corpus (digests, signature bases, signatures), proves
      the builder against RFC 9421's own Appendix B vectors, and checks
      that the page quotes the corpus verbatim.

Keys
====

The vectors sign with the RFC 9421 Appendix B.1.3 (``test-key-ecc-p256``)
and B.1.4 (``test-key-ed25519``) test keys, so a suite that already
carries those keys needs nothing new. The Ed25519 key's RFC 7638
thumbprint is the ``kid`` the specification already uses in its Web Bot
Auth example.

Determinism
===========

Ed25519 is deterministic by construction. The ECDSA vectors are produced
with RFC 6979 deterministic nonces, so a deterministic ES256 signer
reproduces them byte for byte; a randomized signer verifies them instead
of reproducing them (RFC 9421 §7.3.5). Both are valid outcomes.

Scope of the RFC 9421 implementation
====================================

Only what the UCP profile uses: the derived components ``@method``,
``@authority``, ``@path``, ``@query`` and ``@status``; HTTP fields by
name; Dictionary-member selection (``;key="..."``) over fields whose
members are sf-strings, tokens or integers with token, string, integer or
boolean parameters; and the ``created``, ``expires``, ``nonce``, ``keyid``
and ``tag`` signature parameters. Field values are trimmed and multiple
instances are joined with ``", "`` per RFC 9421 §2.1. Nothing else from
RFC 9421 or RFC 8941 is implemented.

CLI
===

  signature_vectors.py generate [--out PATH]   rewrite the corpus
  signature_vectors.py verify [--in PATH]      verify the corpus
  signature_vectors.py self-test               check against RFC 9421

Exit codes: 0 on success, 1 on any failure.
"""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import sys

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, ed25519
from cryptography.hazmat.primitives.asymmetric.utils import (
  decode_dss_signature,
  encode_dss_signature,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
VECTORS_PATH = (
  REPO_ROOT / "docs" / "specification" / "signatures" / "test-vectors.json"
)

# -----------------------------------------------------------
# Encoding helpers
# -----------------------------------------------------------


def b64(data: bytes) -> str:
  """Encode standard base64 with padding, as RFC 9421 and RFC 9530 use."""
  return base64.b64encode(data).decode("ascii")


def unb64(text: str) -> bytes:
  """Decode standard base64."""
  return base64.b64decode(text)


def b64url(data: bytes) -> str:
  """Encode base64url without padding, as JWK and RFC 7638 use."""
  return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def unb64url(text: str) -> bytes:
  """Decode base64url without padding."""
  return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def content_digest(body: bytes) -> str:
  """Compute the RFC 9530 ``Content-Digest`` value over raw body bytes."""
  return f"sha-256=:{b64(hashlib.sha256(body).digest())}:"


# -----------------------------------------------------------
# RFC 8941 structured fields (the subset UCP signatures need)
# -----------------------------------------------------------


def sf_string(value: str) -> str:
  """Serialize an sf-string (RFC 8941 §4.1.6)."""
  escaped = value.replace("\\", "\\\\").replace('"', '\\"')
  return f'"{escaped}"'


def sf_param_value(value: object) -> str:
  """Serialize a parameter value: token, integer, boolean or string."""
  if value is True:
    return ""
  if isinstance(value, bool):
    raise ValueError("boolean false parameters are not serializable here")
  if isinstance(value, int):
    return f"={value}"
  if isinstance(value, SfToken):
    return f"={value.text}"
  if isinstance(value, str):
    return f"={sf_string(value)}"
  raise TypeError(f"unsupported parameter value: {value!r}")


def sf_params(params: dict[str, object]) -> str:
  """Serialize a parameter list (RFC 8941 §4.1.1.2)."""
  return "".join(f";{k}{sf_param_value(v)}" for k, v in params.items())


@dataclass(frozen=True)
class SfToken:
  """Represent an sf-token (RFC 8941 §3.3.4): bare, unquoted."""

  text: str


class _Cursor:
  """Parse one RFC 8941 field value, minimally."""

  def __init__(self, text: str) -> None:
    self.text = text
    self.pos = 0

  def peek(self) -> str:
    return self.text[self.pos] if self.pos < len(self.text) else ""

  def take(self, n: int = 1) -> str:
    chunk = self.text[self.pos : self.pos + n]
    self.pos += n
    return chunk

  def skip_sp(self) -> None:
    while self.peek() == " ":
      self.pos += 1

  def skip_ows(self) -> None:
    while self.peek() in (" ", "\t"):
      self.pos += 1

  def key(self) -> str:
    start = self.pos
    while self.peek() and (self.peek().isalnum() or self.peek() in "_-.*"):
      self.pos += 1
    if start == self.pos:
      raise ValueError(f"expected key at {start}: {self.text!r}")
    return self.text[start : self.pos]

  def bare_item(self) -> object:
    ch = self.peek()
    if ch == '"':
      self.take()
      out = []
      while True:
        c = self.take()
        if c == "":
          raise ValueError("unterminated sf-string")
        if c == "\\":
          out.append(self.take())
        elif c == '"':
          return "".join(out)
        else:
          out.append(c)
    if ch == "?":
      self.take()
      flag = self.take()
      return flag == "1"
    if ch.isdigit() or ch == "-":
      start = self.pos
      self.take()
      while self.peek().isdigit():
        self.take()
      return int(self.text[start : self.pos])
    if ch.isalpha() or ch == "*":
      start = self.pos
      while self.peek() and (
        self.peek().isalnum() or self.peek() in "_-.:/%*!#$&'+^`|~"
      ):
        self.take()
      return SfToken(self.text[start : self.pos])
    raise ValueError(f"unsupported bare item at {self.pos}: {self.text!r}")

  def params(self) -> dict[str, object]:
    out: dict[str, object] = {}
    while self.peek() == ";":
      self.take()
      self.skip_sp()
      name = self.key()
      if self.peek() == "=":
        self.take()
        out[name] = self.bare_item()
      else:
        out[name] = True
    return out


def sf_serialize_item(value: object, params: dict[str, object]) -> str:
  """Serialize an Item with parameters (RFC 8941 §4.1.3)."""
  if isinstance(value, bool):
    item = "?1" if value else "?0"
  elif isinstance(value, int):
    item = str(value)
  elif isinstance(value, SfToken):
    item = value.text
  elif isinstance(value, str):
    item = sf_string(value)
  else:
    raise TypeError(f"unsupported item: {value!r}")
  return item + sf_params(params)


def sf_dictionary_member(field_value: str, key: str) -> str:
  """Serialize one member of an sf-dictionary field value, by key.

  Implements the RFC 9421 §2.1.2 ``;key`` component selection for the
  member shapes UCP uses (an Item with parameters; inner lists are out
  of scope). Raises ``KeyError`` when the member is absent.
  """
  cur = _Cursor(field_value)
  members: dict[str, str] = {}
  while True:
    cur.skip_ows()
    name = cur.key()
    if cur.peek() == "=":
      cur.take()
      if cur.peek() == "(":
        raise ValueError("inner-list dictionary members are unsupported")
      value = cur.bare_item()
      params = cur.params()
      members[name] = sf_serialize_item(value, params)
    else:
      members[name] = sf_serialize_item(True, cur.params())
    cur.skip_ows()
    if cur.peek() != ",":
      break
    cur.take()
  return members[key]


# -----------------------------------------------------------
# RFC 9421 signature base
# -----------------------------------------------------------


@dataclass(frozen=True)
class Component:
  """Identify a covered component: a name plus optional parameters."""

  name: str
  params: dict[str, object] = field(default_factory=dict)

  @classmethod
  def parse(cls, text: str) -> Component:
    """Parse ``"name";param=value`` as written in ``Signature-Input``."""
    cur = _Cursor(text)
    name = cur.bare_item()
    if not isinstance(name, str):
      raise ValueError(f"component name must be an sf-string: {text!r}")
    return cls(name, cur.params())

  def serialize(self) -> str:
    """Serialize as it appears in the signature base and header."""
    return sf_string(self.name) + sf_params(self.params)


@dataclass
class Message:
  """Model an HTTP request or response, as the signature base sees it.

  ``headers`` preserves wire order and case; lookups are
  case-insensitive. ``body`` is the exact bytes on the wire.
  """

  headers: dict[str, str]
  body: bytes = b""
  method: str | None = None
  authority: str | None = None
  path: str | None = None
  query: str | None = None
  status: int | None = None

  def field_values(self, name: str) -> list[str]:
    """Return all instances of a header, trimmed, in wire order."""
    return [
      v.strip() for k, v in self.headers.items() if k.lower() == name.lower()
    ]

  def component_value(self, comp: Component) -> str:
    """Compute the RFC 9421 §2 component value for this message."""
    name = comp.name
    if name.startswith("@"):
      derived = {
        "@method": self.method,
        "@authority": self.authority,
        "@path": self.path,
        "@query": None if self.query is None else f"?{self.query}",
        "@status": None if self.status is None else str(self.status),
      }
      if name not in derived:
        raise ValueError(f"unsupported derived component {name}")
      value = derived[name]
      if value is None:
        raise ValueError(f"{name} is not available on this message")
      if comp.params:
        raise ValueError(f"parameters on {name} are unsupported")
      return value
    values = self.field_values(name)
    if not values:
      raise ValueError(f"field {name!r} is absent from the message")
    joined = ", ".join(values)
    if "key" in comp.params:
      key = comp.params["key"]
      if not isinstance(key, str):
        raise ValueError(";key must be an sf-string")
      extra = set(comp.params) - {"key"}
      if extra:
        raise ValueError(f"unsupported component parameters: {extra}")
      return sf_dictionary_member(joined, key)
    if comp.params:
      raise ValueError(f"unsupported component parameters: {comp.params}")
    return joined


def signature_params_value(
  components: list[Component], params: dict[str, object]
) -> str:
  """Serialize the ``@signature-params`` value (RFC 9421 §2.3)."""
  inner = "(" + " ".join(c.serialize() for c in components) + ")"
  return inner + sf_params(params)


def signature_base(
  message: Message,
  components: list[Component],
  params: dict[str, object],
) -> str:
  """Build the RFC 9421 §2.5 signature base."""
  lines = [
    f"{sf_string(c.name) + sf_params(c.params)}: {message.component_value(c)}"
    for c in components
  ]
  lines.append(
    f'"@signature-params": {signature_params_value(components, params)}'
  )
  return "\n".join(lines)


def parse_signature_input(value: str) -> tuple[str, list[Component], dict]:
  """Parse a single-member ``Signature-Input`` field value."""
  cur = _Cursor(value)
  label = cur.key()
  if cur.take() != "=" or cur.take() != "(":
    raise ValueError(f"malformed Signature-Input: {value!r}")
  components: list[Component] = []
  while True:
    cur.skip_sp()
    if cur.peek() == ")":
      cur.take()
      break
    name = cur.bare_item()
    if not isinstance(name, str):
      raise ValueError("component identifiers must be sf-strings")
    components.append(Component(name, cur.params()))
  params = cur.params()
  if cur.pos != len(value):
    raise ValueError(f"trailing data in Signature-Input: {value!r}")
  return label, components, params


def parse_signature(value: str, label: str) -> bytes:
  """Extract the byte-sequence signature for ``label`` from ``Signature``."""
  prefix = f"{label}=:"
  if not value.startswith(prefix) or not value.endswith(":"):
    raise ValueError(f"malformed Signature for {label}: {value!r}")
  return unb64(value[len(prefix) : -1])


# -----------------------------------------------------------
# Keys (JWK) and algorithms
# -----------------------------------------------------------


def jwk_thumbprint(jwk: dict) -> str:
  """Compute the RFC 7638 SHA-256 thumbprint, base64url."""
  if jwk["kty"] == "EC":
    members = {"crv": jwk["crv"], "kty": "EC", "x": jwk["x"], "y": jwk["y"]}
  elif jwk["kty"] == "OKP":
    members = {"crv": jwk["crv"], "kty": "OKP", "x": jwk["x"]}
  else:
    raise ValueError(f"unsupported kty {jwk['kty']}")
  canonical = json.dumps(members, separators=(",", ":"), sort_keys=True)
  return b64url(hashlib.sha256(canonical.encode("utf-8")).digest())


def jwk_algorithm(jwk: dict) -> str:
  """Derive the JWA algorithm from ``kty``/``crv`` (never from ``alg``)."""
  if jwk["kty"] == "EC" and jwk["crv"] == "P-256":
    return "ES256"
  if jwk["kty"] == "OKP" and jwk["crv"] == "Ed25519":
    return "EdDSA"
  raise ValueError(f"unsupported key: {jwk.get('kty')}/{jwk.get('crv')}")


def _private_key(jwk: dict):
  alg = jwk_algorithm(jwk)
  d = int.from_bytes(unb64url(jwk["d"]), "big")
  if alg == "ES256":
    return ec.derive_private_key(d, ec.SECP256R1())
  return ed25519.Ed25519PrivateKey.from_private_bytes(unb64url(jwk["d"]))


def _public_key(jwk: dict):
  alg = jwk_algorithm(jwk)
  if alg == "ES256":
    x = int.from_bytes(unb64url(jwk["x"]), "big")
    y = int.from_bytes(unb64url(jwk["y"]), "big")
    return ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()
  return ed25519.Ed25519PublicKey.from_public_bytes(unb64url(jwk["x"]))


def sign(jwk: dict, base: str) -> bytes:
  """Sign a signature base; ECDSA output is raw ``r||s`` (64 bytes)."""
  key = _private_key(jwk)
  data = base.encode("ascii")
  if jwk_algorithm(jwk) == "ES256":
    der = key.sign(data, ec.ECDSA(hashes.SHA256(), deterministic_signing=True))
    r, s = decode_dss_signature(der)
    return r.to_bytes(32, "big") + s.to_bytes(32, "big")
  return key.sign(data)


def verify(jwk: dict, base: str, signature: bytes) -> bool:
  """Verify a raw signature over a signature base."""
  key = _public_key(jwk)
  data = base.encode("ascii")
  try:
    if jwk_algorithm(jwk) == "ES256":
      if len(signature) != 64:
        return False
      r = int.from_bytes(signature[:32], "big")
      s = int.from_bytes(signature[32:], "big")
      key.verify(encode_dss_signature(r, s), data, ec.ECDSA(hashes.SHA256()))
    else:
      key.verify(signature, data)
  except InvalidSignature:
    return False
  return True


def public_jwk(jwk: dict) -> dict:
  """Return the JWK without its private member."""
  return {k: v for k, v in jwk.items() if k != "d"}


# -----------------------------------------------------------
# Test keys: RFC 9421 Appendix B.1.3 and B.1.4
# -----------------------------------------------------------

TEST_KEY_ECC_P256 = {
  "kid": "test-key-ecc-p256",
  "kty": "EC",
  "crv": "P-256",
  "x": "qIVYZVLCrPZHGHjP17CTW0_-D9Lfw0EkjqF7xB4FivA",
  "y": "Mc4nN9LTDOBhfoUeg8Ye9WedFRhnZXZJA12Qp0zZ6F0",
  "d": "UpuF81l-kOxbjf7T4mNSv0r5tN67Gim7rnf6EFpcYDs",
  "use": "sig",
  "alg": "ES256",
}

TEST_KEY_ED25519 = {
  # kid is the RFC 7638 thumbprint, as WBA-shape signatures require.
  "kid": "poqkLGiymh_W0uP6PZFw-dvez3QJT5SolqXBCW38r0U",
  "kty": "OKP",
  "crv": "Ed25519",
  "x": "JrQLj5P_89iXES9-vFgrIy29clF9CC_oPPsw3c5D0bs",
  "d": "n4Ni-HpISpVObnQMW0wOhCKROaIKqKtW_2ZYb2p9KcU",
  "use": "sig",
  "alg": "EdDSA",
}

TEST_KEYS = [TEST_KEY_ECC_P256, TEST_KEY_ED25519]


def key_by_kid(keys: list[dict], kid: str) -> dict:
  """Find a JWK by ``kid``."""
  for k in keys:
    if k["kid"] == kid:
      return k
  raise KeyError(kid)


# -----------------------------------------------------------
# UCP vector definitions
# -----------------------------------------------------------

PLATFORM_PROFILE = "https://platform.example/.well-known/ucp"
BUSINESS_PROFILE = "https://merchant.example/.well-known/ucp"
IDEMPOTENCY_KEY = "550e8400-e29b-41d4-a716-446655440000"
CREATED = 1738617600  # 2025-02-03T20:40:00Z, as used throughout the spec
EXPIRES = 1738621200  # created + 1 hour
# 64 random bytes, base64url, frozen so the WBA vector is reproducible.
NONCE = (
  "p9XobbyV3_aRwb6CmcKmG3ZQejLZxwuWYimRsKPxQQ3H8tBWd4nf3h3pbg-C33JX"
  "8COWg6lbPvqeiUmUBoD-sQ"
)

CHECKOUT_BODY = b'{"line_items":[{"item":{"id":"item_123"},"quantity":2}]}'
CHECKOUT_RESPONSE_BODY = (
  b'{"id":"chk_123","status":"ready_for_complete",'
  b'"currency":"USD","line_items":[{"id":"li_1","item":{"id":"item_123"},'
  b'"quantity":2}]}'
)
WEBHOOK_BODY = b'{"id":"ord_456","checkout_id":"chk_123","status":"confirmed"}'
MCP_BODY = (
  b'{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{'
  b'"name":"complete_checkout","arguments":{"meta":{"ucp-agent":{'
  b'"profile":"https://platform.example/.well-known/ucp"},'
  b'"idempotency-key":"550e8400-e29b-41d4-a716-446655440000"},'
  b'"id":"chk_123","checkout":{"payment":{"instruments":[{"id":"pi_1",'
  b'"type":"card","handler_id":"tokenizer_1"}]}}}}}'
)


@dataclass
class VectorSpec:
  """Describe everything needed to sign one message."""

  id: str
  description: str
  kid: str
  label: str
  message: Message
  components: list[str]
  params: dict[str, object]


def _request(
  method: str,
  authority: str,
  path: str,
  headers: dict[str, str],
  body: bytes = b"",
  query: str | None = None,
) -> Message:
  if body:
    headers = dict(headers)
    headers["Content-Digest"] = content_digest(body)
  return Message(
    headers=headers,
    body=body,
    method=method,
    authority=authority,
    path=path,
    query=query,
  )


def _response(status: int, headers: dict[str, str], body: bytes) -> Message:
  headers = dict(headers)
  headers["Content-Digest"] = content_digest(body)
  return Message(headers=headers, body=body, status=status)


def vector_specs() -> list[VectorSpec]:
  """Return the UCP vectors, mirroring the examples in signatures.md."""
  ucp_agent_platform = f'profile="{PLATFORM_PROFILE}"'
  ucp_agent_business = f'profile="{BUSINESS_PROFILE}"'
  return [
    VectorSpec(
      id="rest-request-es256",
      description=(
        "Default UCP signature on a REST request with a body: the "
        "Complete Request Example from REST Request Signing."
      ),
      kid=TEST_KEY_ECC_P256["kid"],
      label="sig1",
      message=_request(
        "POST",
        "merchant.example.com",
        "/checkout-sessions",
        {
          "Host": "merchant.example.com",
          "Content-Type": "application/json",
          "UCP-Agent": ucp_agent_platform,
          "Idempotency-Key": IDEMPOTENCY_KEY,
        },
        CHECKOUT_BODY,
      ),
      components=[
        "@method",
        "@authority",
        "@path",
        "ucp-agent",
        "idempotency-key",
        "content-digest",
        "content-type",
      ],
      params={"keyid": TEST_KEY_ECC_P256["kid"]},
    ),
    VectorSpec(
      id="rest-get-es256",
      description=(
        "Default UCP signature on a REST request with no body and no "
        "idempotency key: the GET Request Example."
      ),
      kid=TEST_KEY_ECC_P256["kid"],
      label="sig1",
      message=_request(
        "GET",
        "merchant.example.com",
        "/checkout-sessions/chk_123",
        {
          "Host": "merchant.example.com",
          "UCP-Agent": ucp_agent_platform,
        },
      ),
      components=["@method", "@authority", "@path", "ucp-agent"],
      params={"keyid": TEST_KEY_ECC_P256["kid"]},
    ),
    VectorSpec(
      id="rest-response-es256",
      description=(
        "Default UCP signature on a REST response: the Complete Response "
        "Example from REST Response Signing, with the OPTIONAL created "
        "parameter."
      ),
      kid=TEST_KEY_ECC_P256["kid"],
      label="sig1",
      message=_response(
        201,
        {"Content-Type": "application/json"},
        CHECKOUT_RESPONSE_BODY,
      ),
      components=["@status", "content-digest", "content-type"],
      params={"created": CREATED, "keyid": TEST_KEY_ECC_P256["kid"]},
    ),
    VectorSpec(
      id="wba-request-ed25519",
      description=(
        "Dual-audience (Web Bot Auth-shaped) signature on a REST request: "
        "Signature-Agent alongside UCP-Agent, the signature-agent "
        "component selected by ;key, keyid set to the RFC 7638 "
        "thumbprint, and created, expires, nonce and tag parameters."
      ),
      kid=TEST_KEY_ED25519["kid"],
      label="sig1",
      message=_request(
        "POST",
        "merchant.example.com",
        "/checkout-sessions",
        {
          "Host": "merchant.example.com",
          "Content-Type": "application/json",
          "UCP-Agent": ucp_agent_platform,
          "Signature-Agent": f'sig1="{PLATFORM_PROFILE}";type=jwks_uri',
          "Idempotency-Key": IDEMPOTENCY_KEY,
        },
        CHECKOUT_BODY,
      ),
      components=[
        "@method",
        "@authority",
        "@path",
        '"signature-agent";key="sig1"',
        "ucp-agent",
        "idempotency-key",
        "content-digest",
        "content-type",
      ],
      params={
        "keyid": TEST_KEY_ED25519["kid"],
        "created": CREATED,
        "expires": EXPIRES,
        "nonce": NONCE,
        "tag": "web-bot-auth",
      },
    ),
    VectorSpec(
      id="webhook-request-es256",
      description=(
        "Business-signed order webhook delivery: Webhook-Id and "
        "Webhook-Timestamp covered, no Idempotency-Key, UCP-Agent naming "
        "the business profile."
      ),
      kid=TEST_KEY_ECC_P256["kid"],
      label="sig1",
      message=_request(
        "POST",
        "platform.example.com",
        "/webhooks/ucp/orders",
        {
          "Host": "platform.example.com",
          "Content-Type": "application/json",
          "UCP-Agent": ucp_agent_business,
          "Webhook-Timestamp": "1737000000",
          "Webhook-Id": "018f8c2a-7b3e-7c1d-9a2b-4e5f6a7b8c9d",
        },
        WEBHOOK_BODY,
      ),
      components=[
        "@method",
        "@authority",
        "@path",
        "ucp-agent",
        "content-digest",
        "content-type",
        "webhook-id",
        "webhook-timestamp",
      ],
      params={"keyid": TEST_KEY_ECC_P256["kid"]},
    ),
    VectorSpec(
      id="mcp-request-es256",
      description=(
        "Default UCP signature on an MCP tools/call request over "
        "streamable HTTP: the JSON-RPC body is bound through "
        "Content-Digest exactly as a REST body is."
      ),
      kid=TEST_KEY_ECC_P256["kid"],
      label="sig1",
      message=_request(
        "POST",
        "business.example.com",
        "/mcp",
        {
          "Host": "business.example.com",
          "Content-Type": "application/json",
          "UCP-Agent": ucp_agent_platform,
          "Idempotency-Key": IDEMPOTENCY_KEY,
        },
        MCP_BODY,
      ),
      components=[
        "@method",
        "@authority",
        "@path",
        "content-digest",
        "content-type",
        "ucp-agent",
        "idempotency-key",
      ],
      params={"keyid": TEST_KEY_ECC_P256["kid"]},
    ),
  ]


def _parse_components(items: list[str]) -> list[Component]:
  out = []
  for item in items:
    if item.startswith('"'):
      out.append(Component.parse(item))
    else:
      out.append(Component(item))
  return out


def render_message(spec_message: Message, label_headers: dict) -> str:
  """Render the signed message as an HTTP/1.1 exchange, headers in order."""
  m = spec_message
  if m.status is not None:
    reasons = {200: "OK", 201: "Created"}
    first = f"HTTP/1.1 {m.status} {reasons.get(m.status, '')}".rstrip()
  else:
    target = m.path if m.query is None else f"{m.path}?{m.query}"
    first = f"{m.method} {target} HTTP/1.1"
  headers = dict(m.headers)
  headers.update(label_headers)
  lines = [first] + [f"{k}: {v}" for k, v in headers.items()]
  text = "\n".join(lines) + "\n"
  if m.body:
    text += "\n" + m.body.decode("utf-8") + "\n"
  return text


def build_vector(spec: VectorSpec, keys: list[dict]) -> dict:
  """Sign one spec and return its JSON record."""
  jwk = key_by_kid(keys, spec.kid)
  components = _parse_components(spec.components)
  base = signature_base(spec.message, components, spec.params)
  sig = sign(jwk, base)
  sig_input = f"{spec.label}={signature_params_value(components, spec.params)}"
  signature = f"{spec.label}=:{b64(sig)}:"
  m = spec.message
  record: dict[str, object] = {
    "id": spec.id,
    "description": spec.description,
    "kid": spec.kid,
    "algorithm": jwk_algorithm(jwk),
  }
  if m.status is not None:
    record["response"] = {"status": m.status}
  else:
    req: dict[str, object] = {
      "method": m.method,
      "authority": m.authority,
      "path": m.path,
    }
    if m.query is not None:
      req["query"] = m.query
    record["request"] = req
  record["headers"] = dict(m.headers)
  record["body"] = m.body.decode("utf-8")
  record["label"] = spec.label
  record["covered_components"] = [c.serialize() for c in components]
  record["signature_params"] = dict(spec.params)
  record["signature_base"] = base
  record["signature_input"] = sig_input
  record["signature"] = signature
  record["message"] = render_message(
    m, {"Signature-Input": sig_input, "Signature": signature}
  )
  return record


def generate(keys: list[dict] | None = None) -> dict:
  """Build the whole corpus."""
  keys = keys or TEST_KEYS
  return {
    "title": "UCP HTTP Message Signature Test Vectors",
    "description": (
      "Non-normative test vectors for the UCP profile of RFC 9421 HTTP "
      "Message Signatures, as specified in the Message Signatures "
      "specification. Keys are the RFC 9421 Appendix B.1.3 and B.1.4 test "
      "keys and MUST NOT be used outside of testing. Bodies are signed as "
      "the exact bytes of the body field (UTF-8, no trailing newline). "
      "ECDSA signatures use RFC 6979 deterministic nonces and raw r||s "
      "encoding; a randomized ES256 signer verifies them rather than "
      "reproducing them."
    ),
    "keys": keys,
    "vectors": [build_vector(s, keys) for s in vector_specs()],
  }


# -----------------------------------------------------------
# Verification
# -----------------------------------------------------------


def message_from_record(record: dict) -> Message:
  """Rebuild the ``Message`` a vector record describes."""
  body = record["body"].encode("utf-8")
  if "response" in record:
    return Message(
      headers=dict(record["headers"]),
      body=body,
      status=record["response"]["status"],
    )
  req = record["request"]
  return Message(
    headers=dict(record["headers"]),
    body=body,
    method=req["method"],
    authority=req["authority"],
    path=req["path"],
    query=req.get("query"),
  )


def verify_vector(record: dict, keys: list[dict]) -> list[str]:
  """Verify one record from first principles, returning its problems."""
  problems: list[str] = []
  message = message_from_record(record)
  jwk = key_by_kid(keys, record["kid"])

  if message.body:
    expected = content_digest(message.body)
    actual = message.field_values("content-digest")
    if actual != [expected]:
      problems.append(f"content-digest {actual} != {expected}")
  elif message.field_values("content-digest"):
    problems.append("content-digest present on a message without a body")

  label, components, params = parse_signature_input(record["signature_input"])
  if label != record["label"]:
    problems.append(f"label {label} != {record['label']}")
  if [c.serialize() for c in components] != record["covered_components"]:
    problems.append("covered_components do not match signature_input")
  if params != record["signature_params"]:
    problems.append("signature_params do not match signature_input")
  if params.get("keyid") != record["kid"]:
    problems.append("keyid does not match kid")
  if params.get("tag") == "web-bot-auth" and params.get("keyid") != (
    jwk_thumbprint(jwk)
  ):
    problems.append("WBA-shape keyid is not the key's RFC 7638 thumbprint")
  if record["algorithm"] != jwk_algorithm(jwk):
    problems.append("algorithm does not match the key")

  base = signature_base(message, components, params)
  if base != record["signature_base"]:
    problems.append("signature_base does not match the rebuilt base")

  signature = parse_signature(record["signature"], label)
  if not verify(jwk, record["signature_base"], signature):
    problems.append("signature does not verify")
  if record["algorithm"] == "EdDSA" and sign(jwk, base) != signature:
    problems.append("Ed25519 signature is not the deterministic value")
  if record["algorithm"] == "ES256" and sign(jwk, base) != signature:
    problems.append("ES256 signature is not the RFC 6979 value")

  rendered = render_message(
    message,
    {
      "Signature-Input": record["signature_input"],
      "Signature": record["signature"],
    },
  )
  if rendered != record["message"]:
    problems.append("message rendering does not match")
  return problems


def verify_corpus(corpus: dict) -> dict[str, list[str]]:
  """Verify every vector; map vector id to its problems."""
  keys = corpus["keys"]
  results = {}
  for record in corpus["vectors"]:
    results[record["id"]] = verify_vector(record, keys)
  return results


# -----------------------------------------------------------
# Self-test against RFC 9421 Appendix B
# -----------------------------------------------------------

RFC_TEST_RESPONSE = Message(
  headers={
    "Date": "Tue, 20 Apr 2021 02:07:56 GMT",
    "Content-Type": "application/json",
    "Content-Digest": (
      "sha-512=:mEWXIS7MaLRuGgxOBdODa3xqM1XdEvxoYhvlCFJ41QJgJc4GTsPp29l5oG"
      "X69wWdXymyU0rjJuahq4l5aGgfLQ==:"
    ),
    "Content-Length": "23",
  },
  body=b'{"message": "good dog"}',
  status=200,
)

RFC_TEST_REQUEST = Message(
  headers={
    "Host": "example.com",
    "Date": "Tue, 20 Apr 2021 02:07:55 GMT",
    "Content-Type": "application/json",
    "Content-Digest": (
      "sha-512=:WZDPaVn/7XgHaAy8pmojAkGWoRx2UFChF41A2svX+TaPm+AbwAgBWnrIiY"
      "llu7BNNyealdVLvRwEmTHWXvJwew==:"
    ),
    "Content-Length": "18",
  },
  body=b'{"hello": "world"}',
  method="POST",
  authority="example.com",
  path="/foo",
  query="param=Value&Pet=dog",
)

# B.2.4: Signing a Response Using ecdsa-p256-sha256
RFC_B24_INPUT = (
  'sig-b24=("@status" "content-type" "content-digest" "content-length")'
  ';created=1618884473;keyid="test-key-ecc-p256"'
)
RFC_B24_BASE = (
  '"@status": 200\n'
  '"content-type": application/json\n'
  '"content-digest": sha-512=:mEWXIS7MaLRuGgxOBdODa3xqM1XdEvxoYhvlCFJ41QJ'
  "gJc4GTsPp29l5oGX69wWdXymyU0rjJuahq4l5aGgfLQ==:\n"
  '"content-length": 23\n'
  '"@signature-params": ("@status" "content-type" "content-digest" '
  '"content-length");created=1618884473;keyid="test-key-ecc-p256"'
)
RFC_B24_SIGNATURE = (
  "sig-b24=:wNmSUAhwb5LxtOtOpNa6W5xj067m5hFrj0XQ4fvpaCLx0NKocgPquLgyahnz"
  "DnDAUy5eCdlYUEkLIj+32oiasw==:"
)

# B.2.6: Signing a Request Using ed25519
RFC_B26_INPUT = (
  'sig-b26=("date" "@method" "@path" "@authority" "content-type" '
  '"content-length");created=1618884473;keyid="test-key-ed25519"'
)
RFC_B26_BASE = (
  '"date": Tue, 20 Apr 2021 02:07:55 GMT\n'
  '"@method": POST\n'
  '"@path": /foo\n'
  '"@authority": example.com\n'
  '"content-type": application/json\n'
  '"content-length": 18\n'
  '"@signature-params": ("date" "@method" "@path" "@authority" '
  '"content-type" "content-length");created=1618884473'
  ';keyid="test-key-ed25519"'
)
RFC_B26_SIGNATURE = (
  "sig-b26=:wqcAqbmYJ2ji2glfAMaRy4gruYYnx2nEFN2HN6jrnDnQCK1u02Gb04v9EDgw"
  "UPiu4A0w6vuQv5lIp5WPpBKRCw==:"
)


def self_test() -> list[str]:
  """Check the builder against RFC 9421's published vectors."""
  problems: list[str] = []
  ecc = dict(TEST_KEY_ECC_P256)
  okp = dict(TEST_KEY_ED25519, kid="test-key-ed25519")

  label, comps, params = parse_signature_input(RFC_B24_INPUT)
  base = signature_base(RFC_TEST_RESPONSE, comps, params)
  if base != RFC_B24_BASE:
    problems.append("B.2.4 signature base differs from RFC 9421")
  if not verify(ecc, base, parse_signature(RFC_B24_SIGNATURE, label)):
    problems.append("B.2.4 signature does not verify with test-key-ecc-p256")

  label, comps, params = parse_signature_input(RFC_B26_INPUT)
  base = signature_base(RFC_TEST_REQUEST, comps, params)
  if base != RFC_B26_BASE:
    problems.append("B.2.6 signature base differs from RFC 9421")
  sig = parse_signature(RFC_B26_SIGNATURE, label)
  if not verify(okp, base, sig):
    problems.append("B.2.6 signature does not verify with test-key-ed25519")
  if sign(okp, base) != sig:
    problems.append("B.2.6 signature not reproduced by deterministic Ed25519")

  if jwk_thumbprint(okp) != TEST_KEY_ED25519["kid"]:
    problems.append("Ed25519 thumbprint differs from the spec's WBA kid")
  return problems


# -----------------------------------------------------------
# CLI
# -----------------------------------------------------------


def _dump(corpus: dict) -> str:
  return json.dumps(corpus, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
  """Run the CLI."""
  parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  sub = parser.add_subparsers(dest="command", required=True)
  gen = sub.add_parser("generate", help="rewrite the vector corpus")
  gen.add_argument("--out", type=Path, default=VECTORS_PATH)
  ver = sub.add_parser("verify", help="verify the vector corpus")
  ver.add_argument("--in", dest="inp", type=Path, default=VECTORS_PATH)
  sub.add_parser("self-test", help="check against RFC 9421 Appendix B")
  args = parser.parse_args(argv)

  problems = self_test()
  for p in problems:
    print(f"SELF-TEST FAIL: {p}")
  if problems:
    return 1
  if args.command == "self-test":
    print("self-test passed against RFC 9421 Appendix B")
    return 0

  if args.command == "generate":
    corpus = generate()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(_dump(corpus), encoding="utf-8")
    print(f"wrote {len(corpus['vectors'])} vectors to {args.out}")
    return 0

  corpus = json.loads(args.inp.read_text(encoding="utf-8"))
  failures = 0
  for vid, probs in verify_corpus(corpus).items():
    status = "PASS" if not probs else "FAIL"
    print(f"  {status}  {vid}")
    for p in probs:
      print(f"          {p}")
    failures += bool(probs)
  print(f"\n{len(corpus['vectors']) - failures} passed, {failures} failed")
  return 1 if failures else 0


if __name__ == "__main__":
  sys.exit(main())
