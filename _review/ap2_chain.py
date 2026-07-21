"""dSD-JWT chain orchestration (draft-gco-oauth-delegate-sd-jwt-00 §6).

This module owns the *chain-level* concerns:

- Compact serialization: tokens are joined by ``~~`` in AP2's dSD-JWT chain.
- Per-hop dispatch: ``verify_chain`` calls
  :func:`ap2.sdk.sdjwt.sd_jwt.verify` for the first hop and
  :func:`ap2.sdk.sdjwt.kb_sd_jwt.verify` for KB-SD-JWT hops.
- ``cnf`` walking: each hop's signing key is the previous hop's
  ``cnf.jwk``.
- Time checks and x5c root-of-trust verification for the first hop.

The per-token crypto + ``typ`` + ``sd_hash``/``issuer_jwt_hash`` checks live
in the per-primitive modules, not here.
"""

from __future__ import annotations

import binascii
import json
import logging
import time

from collections.abc import Callable
from typing import Any, Protocol

from ap2.sdk.sdjwt import common, kb_sd_jwt, sd_jwt
from ap2.sdk.sdjwt.common import ParsedToken
from ap2.sdk.utils import b64url_decode
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec
from jwcrypto.jwk import JWK


class PublicKeyProvider(Protocol):
    """Resolve the root token's verification key."""

    def __call__(self, token: ParsedToken) -> JWK: ...


class X5cOrKidPublicKeyProvider:
    """Resolve a root key from ``x5c`` or fall back to a ``kid`` lookup."""

    def __init__(
        self,
        kid_lookup: Callable[[str], JWK],
        trusted_roots: list[x509.Certificate] | None = None,
    ) -> None:
        self._kid_lookup = kid_lookup
        self._trusted_roots = trusted_roots

    def __call__(self, token: ParsedToken) -> JWK:
        header = token.header
        if 'x5c' in header:
            return self._resolve_x5c_key(header)

        key_id = header.get('kid')
        if not key_id:
            raise ValueError(
                "Missing or invalid 'kid' or 'x5c' in the first token header"
            )
        key = self._kid_lookup(key_id)
        if key is None:
            raise ValueError(f'Provider returned no key for key_id: {key_id}')
        if not isinstance(key, JWK):
            raise TypeError(
                'PublicKeyProvider must return a jwcrypto.jwk.JWK; got '
                f'{type(key).__name__}. Wrap cryptography EC keys with '
                'JWK.from_pyca(...).'
            )
        return key

    def _resolve_x5c_key(self, header: dict[str, Any]) -> JWK:
        """Resolve the verification :class:`JWK` from an ``x5c`` header."""
        x5c = header['x5c']
        if not isinstance(x5c, list) or not x5c:
            raise ValueError('x5c header must be a non-empty list')
        certs = [
            x509.load_der_x509_certificate(b64url_decode(cert_b64))
            for cert_b64 in x5c
        ]
        for i in range(len(certs) - 1):
            issuer_cert = certs[i + 1]
            subject_cert = certs[i]
            issuer_cert.public_key().verify(
                subject_cert.signature,
                subject_cert.tbs_certificate_bytes,
                ec.ECDSA(subject_cert.signature_hash_algorithm),
            )
        if self._trusted_roots:
            verified = False
            last_cert = certs[-1]
            for root in self._trusted_roots:
                try:
                    root.public_key().verify(
                        last_cert.signature,
                        last_cert.tbs_certificate_bytes,
                        ec.ECDSA(last_cert.signature_hash_algorithm),
                    )
                    verified = True
                    break
                except Exception:
                    continue
            if not verified:
                raise ValueError(
                    'Certificate chain does not chain to a trusted root'
                )
        return JWK.from_pyca(certs[0].public_key())


# RFC 9901 §4.2: a disclosure is the base64url of a JSON array of either
# 2 elements (array-element disclosure: [salt, value]) or 3 elements
# (object-property disclosure: [salt, name, value]).
_SD_JWT_DISCLOSURE_ARRAY_LEN = 2
_SD_JWT_DISCLOSURE_PROPERTY_LEN = 3


# ── Chain verification ───────────────────────────────────────────────────


def verify_chain(  # noqa: PLR0913  (public API; each kwarg is an independent verifier input)
    tokens: list[ParsedToken],
    public_key_provider: PublicKeyProvider,
    clock_skew_seconds: int = 300,
    expected_aud: str | None = None,
    expected_nonce: str | None = None,
    current_time: int | None = None,
) -> list[dict[str, Any]]:
    """Verify a dSD-JWT delegation chain and return per-hop effective payloads.

    Walks the chain from root:

      - index 0 (root SD-JWT): verified with ``public_key_provider(token)``.
      - index i (KB-SD-JWT): verified with the previous hop's ``cnf.jwk`` via
        :func:`ap2.sdk.sdjwt.kb_sd_jwt.verify`, enforcing ``expected_aud`` /
        ``expected_nonce`` on the terminal hop when provided.

    Returns a list of effective payload dicts (one per token, resolved from
    ``delegate_payload[0]`` when present).
    """
    if not tokens:
        raise ValueError('Tokens list cannot be empty')

    payloads: list[dict[str, Any]] = []
    now = current_time if current_time is not None else int(time.time())
    parsed_tokens = tokens

    root_token = parsed_tokens[0]
    current_key = public_key_provider(root_token)
    root_payload = sd_jwt.verify(root_token.canonical, current_key)
    root_items = _effective_payloads(root_payload, root_token, 0, True)
    # KB hops verify with the previous hop's cnf.jwk. That key may only be
    # available after SD-JWT verification resolves delegate_payload disclosures,
    # so store the verified payload on the parsed token before walking onward.
    parsed_tokens[0] = root_token.with_verified_payload(
        root_payload, root_items
    )
    _check_time_claims([root_payload], 0, now, clock_skew_seconds)
    _check_time_claims(root_items, 0, now, clock_skew_seconds)
    payloads.extend(root_items if root_items else [root_payload])

    for i, current_token in enumerate(parsed_tokens[1:], start=1):
        is_last = i == len(parsed_tokens) - 1
        payload = kb_sd_jwt.verify(
            current_token,
            parsed_tokens[i - 1],
            expected_aud=expected_aud if is_last else None,
            expected_nonce=expected_nonce if is_last else None,
        )
        delegate_items = _effective_payloads(
            payload, current_token, i, require_single=not is_last
        )
        _check_time_claims([payload], i, now, clock_skew_seconds)
        _check_time_claims(delegate_items, i, now, clock_skew_seconds)
        payloads.extend(delegate_items if delegate_items else [payload])
        parsed_tokens[i] = current_token.with_verified_payload(
            payload, delegate_items
        )

    return payloads


# ── Helpers ──────────────────────────────────────────────────────────────


def _effective_payloads(
    payload: dict[str, Any],
    token: ParsedToken,
    token_index: int,
    require_single: bool,
) -> list[dict[str, Any]]:
    delegate_items = _resolve_delegate_items(
        payload.get('delegate_payload'), token, token_index
    )
    if require_single and len(delegate_items) > 1:
        raise ValueError(
            f'Token {token_index}: delegate_payload has '
            f'{len(delegate_items)} disclosed items, expected exactly 1'
        )
    return delegate_items


def _resolve_delegate_items(
    delegate_payload: list[Any] | None,
    token: ParsedToken,
    token_index: int,
) -> list[dict[str, Any]]:
    """Decode and resolve items inside a ``delegate_payload`` list.

    Per draft-gco-oauth-delegate-sd-jwt-00 §5.1.4 the ``delegate_payload``
    claim, when present on a verified JWT, is a JSON array whose elements are
    either selectively-disclosable dicts (already resolved by
    ``SDJWTVerifier``) or base64url disclosure strings that encode dicts. We
    tolerate a non-list/``None`` value defensively and return ``[]``.
    """
    if not isinstance(delegate_payload, list):
        return []
    items: list[dict[str, Any]] = []
    for item in delegate_payload:
        if isinstance(item, dict):
            _inline_sd_claims(item, token)
            items.append(item)
        elif isinstance(item, str):
            decoded = _decode_disclosure_dict(item, token_index)
            if decoded is not None:
                items.append(decoded)
    return items


def _inline_sd_claims(
    item: dict[str, Any],
    token: ParsedToken,
) -> None:
    """Resolve ``_sd`` digests in ``item`` in place from token disclosures."""
    sd_digests = item.get('_sd', [])
    if not sd_digests or not token.disclosures:
        return
    for digest in sd_digests:
        for d in token.disclosures:
            if common.compute_disclosure_digest(d, token.sd_alg) == digest:
                decoded = json.loads(b64url_decode(d).decode('utf-8'))
                if len(decoded) == _SD_JWT_DISCLOSURE_PROPERTY_LEN:
                    item[decoded[1]] = decoded[2]
                break


def _decode_disclosure_dict(
    disclosure: str,
    token_index: int,
) -> dict[str, Any] | None:
    """Decode a base64url disclosure into its dict value, if present."""
    try:
        arr = json.loads(b64url_decode(disclosure).decode('utf-8'))
        if not isinstance(arr, list):
            return None
        if len(arr) == _SD_JWT_DISCLOSURE_PROPERTY_LEN:
            val = arr[2]
        elif len(arr) == _SD_JWT_DISCLOSURE_ARRAY_LEN:
            val = arr[1]
        else:
            val = None
        return val if isinstance(val, dict) else None
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as e:
        logging.warning(
            'Token %d: Failed to decode disclosure in delegate_payload: %s',
            token_index,
            e,
        )
        return None


def _check_time_claims(
    payloads: list[dict[str, Any]],
    token_index: int,
    now: int,
    clock_skew: int,
) -> None:
    """Validate exp/iat on a list of effective payloads."""
    for p in payloads:
        exp = p.get('exp')
        if exp is not None:
            if not isinstance(exp, (int, float)):
                raise ValueError(
                    f"Token {token_index} has invalid 'exp' claim type: "
                    f'{type(exp)}'
                )
            if now > exp + clock_skew:
                raise ValueError(f'Token {token_index} expired at {exp}')
        iat = p.get('iat')
        if iat is not None:
            if not isinstance(iat, (int, float)):
                raise ValueError(
                    f"Token {token_index} has invalid 'iat' claim type: "
                    f'{type(iat)}'
                )
            if iat > now + clock_skew:
                raise ValueError(
                    f'Token {token_index} iat is in the future: {iat}'
                )
