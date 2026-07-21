"""KB-SD-JWT primitive (draft-gco-oauth-delegate-sd-jwt-00 §5.1.4).

This module handles both AP2 delegation hop variants:

- intermediate hop: ``typ="kb+sd-jwt+kb"``, delegate payload MUST contain
  ``cnf`` for the next delegate.
- terminal hop: ``typ="kb+sd-jwt"``, delegate payload MUST NOT contain
  ``cnf``.

Both variants carry ``iat``/``aud``/``nonce`` and one of ``sd_hash`` /
``issuer_jwt_hash``. No separate trailing KB-JWT is used in the AP2 flow.
"""

from __future__ import annotations

import json
import time

from typing import Any

from ap2.sdk.disclosure_metadata import DisclosureMetadata
from ap2.sdk.sdjwt import common
from ap2.sdk.sdjwt.common import HashMode, ParsedToken
from ap2.sdk.sdjwt.sd_jwt import verify as sd_jwt_verify
from ap2.sdk.utils import b64url_decode
from jwcrypto.jwk import JWK
from pydantic import BaseModel
from sd_jwt.issuer import SDJWTIssuer


TYP_TERMINAL = ['kb+sd-jwt', 'kb-sd-jwt']
TYP_INTERMEDIATE = ['kb+sd-jwt+kb', 'kb-sd-jwt+kb']


def create(  # noqa: PLR0913  (public create() surface: each kwarg is orthogonal)
    prev_token: ParsedToken,
    holder_key: JWK,
    payload: BaseModel,
    aud: str,
    nonce: str,
    sd: DisclosureMetadata | None = None,
    hash_mode: HashMode = 'sd_hash',
    add_decoy_claims: bool = False,
    serialization_format: str = 'compact',
) -> SDJWTIssuer:
    """Build and sign a KB-SD-JWT delegation hop.

    Args:
      prev_token: The preceding SD-JWT or KB-SD-JWT being delegated.
      holder_key: The signing key of this hop.
      payload: Delegate payload model.
      aud: Audience for this hop.
      nonce: Nonce from the verifier/next delegate.
      sd: Optional selective-disclosure metadata; ``None`` auto-derives.
      hash_mode: Binding mode against ``prev_token``.
      add_decoy_claims: Add decoy ``_sd`` digests.
      serialization_format: SD-JWT serialization format.

    Returns:
      An ``SDJWTIssuer`` whose ``.sd_jwt_issuance`` is the signed token.
    """
    if not aud or not nonce:
        raise ValueError('aud and nonce are required for KB-SD-JWT hops')

    delegate_claims = common.delegate_claims_from_model(payload)
    has_cnf = 'cnf' in delegate_claims

    if sd is None:
        sd = DisclosureMetadata.from_model(payload)

    binding_claim, binding_value = common.compute_binding(prev_token, hash_mode)

    extra_claims: dict[str, Any] = {
        'iat': int(time.time()),
        'aud': aud,
        'nonce': nonce,
        binding_claim: binding_value,
    }
    terminal = not has_cnf
    typ = TYP_TERMINAL[0] if terminal else TYP_INTERMEDIATE[0]

    sd_claims = common.selectively_disclosable_claims(
        delegate_claims, sd, extra_claims
    )
    return common.issue_sd_jwt(
        claims=sd_claims,
        issuer_key=holder_key,
        header_params=common.header_parameters(holder_key, typ),
        add_decoy_claims=add_decoy_claims,
        serialization_format=serialization_format,
    )


def verify(
    token: ParsedToken,
    prev_token: ParsedToken,
    expected_aud: str | None = None,
    expected_nonce: str | None = None,
) -> dict[str, Any]:
    """Verify a KB-SD-JWT hop.

    Checks:
      - Header ``typ`` is a known AP2 KB-SD-JWT type.
      - Signature verifies under the preceding hop's ``cnf.jwk``.
      - Exactly one of ``sd_hash`` / ``issuer_jwt_hash`` is present and
        matches the hash of ``prev_token``.
      - ``iat`` is present.
      - If ``expected_aud`` / ``expected_nonce`` are provided, they match.
      - Terminal hops do not contain ``cnf``; intermediate hops do.
    """
    typ = token.typ
    if typ not in TYP_TERMINAL + TYP_INTERMEDIATE:
        raise ValueError(
            f"Unexpected JWT typ: expected one of {TYP_TERMINAL + TYP_INTERMEDIATE}, "
            f"got '{token.typ}'"
        )

    prev_key = prev_token.cnf_jwk()
    if prev_key is None:
        raise ValueError('Previous token missing cnf.jwk')
    payload = sd_jwt_verify(token.canonical, prev_key)
    # Resolve SD-JWT digests in delegate_payload against token disclosures.
    # CMWallet places mandate commitment digests directly in delegate_payload
    # rather than via a standard top-level _sd array; this step normalises
    # them into inline dicts so the cnf check below works correctly.
    _resolve_delegate_payload(payload, token)
    common.verify_binding(payload, prev_token)
    if typ in TYP_TERMINAL:
        common.verify_expected_claims(
            payload,
            expected_aud=expected_aud,
            expected_nonce=expected_nonce,
            token_label='KB-SD-JWT',
        )
    has_cnf = _delegate_payload_has_cnf(payload)
    if typ in TYP_TERMINAL and has_cnf:
        raise ValueError("Terminal KB-SD-JWT MUST NOT carry a 'cnf' claim")
    if typ in TYP_INTERMEDIATE and not has_cnf:
        raise ValueError(f"Intermediate {typ} requires a 'cnf' claim")
    return payload


def _delegate_payload_has_cnf(payload: dict[str, Any]) -> bool:
    delegate_payload = payload.get('delegate_payload')
    if not isinstance(delegate_payload, list):
        return False
    return any(
        isinstance(item, dict) and isinstance(item.get('cnf'), dict)
        for item in delegate_payload
    )


def _try_resolve_digest(
    digest: str,
    disclosures: list[str],
    sd_alg: str | None,
) -> dict[str, Any] | None:
    """Return the dict value of the first disclosure whose hash equals ``digest``.

    Handles the CMWallet format where ``delegate_payload`` items are SD-JWT
    ``_sd``-style digest strings referencing mandate disclosures that are
    appended to the token, rather than inline dict objects.
    """
    for disc in disclosures:
        if common.compute_disclosure_digest(disc, sd_alg) != digest:
            continue
        try:
            arr = json.loads(b64url_decode(disc).decode('utf-8'))
            if not isinstance(arr, list):
                continue
            # [salt, value] for array-element disclosures; [salt, name, value]
            # for object-property disclosures.
            val = arr[1] if len(arr) == 2 else arr[2] if len(arr) == 3 else None
            if isinstance(val, dict):
                return val
        except Exception:
            continue
    return None


def _resolve_delegate_payload(
    payload: dict[str, Any],
    token: ParsedToken,
) -> None:
    """Resolve SD-JWT digests inside ``delegate_payload`` against token disclosures.

    Mutates ``payload`` in place.  Items that are already dicts are left
    unchanged; string items are checked against ``token.disclosures`` using
    the token's ``_sd_alg``.  If a matching disclosure is found its dict
    value replaces the digest string.
    """
    dp = payload.get('delegate_payload')
    if not isinstance(dp, list) or not token.disclosures:
        return
    sd_alg = token.sd_alg
    resolved = []
    for item in dp:
        if isinstance(item, dict):
            resolved.append(item)
        elif isinstance(item, str):
            decoded = _try_resolve_digest(item, token.disclosures, sd_alg)
            resolved.append(decoded if decoded is not None else item)
        else:
            resolved.append(item)
    payload['delegate_payload'] = resolved
