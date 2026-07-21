"""Root SD-JWT primitive (RFC 9901).

This module owns the root, issuer-signed SD-JWT: the very first token in a
delegation chain. It exposes:

- ``create(payload, issuer_key, sd=None)`` — sign an SD-JWT.
- ``verify(token, issuer_public_key, ...)`` — verify signature and resolve
  disclosures into a plain ``dict``.
"""

from __future__ import annotations

from typing import Any

from ap2.sdk.disclosure_metadata import DisclosureMetadata
from ap2.sdk.sdjwt import common
from jwcrypto.jwk import JWK
from pydantic import BaseModel
from sd_jwt.issuer import SDJWTIssuer
from sd_jwt.verifier import SDJWTVerifier


def create(
    payload: BaseModel,
    issuer_key: JWK,
    sd: DisclosureMetadata | None = None,
    add_decoy_claims: bool = False,
    serialization_format: str = 'compact',
) -> SDJWTIssuer:
    """Sign a root SD-JWT for ``payload``.

    The claim is wrapped under ``delegate_payload`` so the same resolver logic
    works for both root tokens and KB-SD-JWT[+KB] hops. No ``sd_hash``,
    ``iat``, ``aud``, or ``nonce`` is injected — those belong on KB-SD-JWTs.

    Args:
      payload: Pydantic model whose fields become the delegate payload.
      issuer_key: JWK used to sign the resulting JWT.
      sd: Selective-disclosure metadata. ``None`` auto-derives from model
        annotations.
      add_decoy_claims: Add decoy ``_sd`` digests (RFC 9901 §4.2.5).
      serialization_format: SD-JWT serialization format.

    Returns:
      An ``SDJWTIssuer`` whose ``.sd_jwt_issuance`` is the compact-serialized
      SD-JWT string.
    """
    delegate_claims = common.delegate_claims_from_model(payload)
    if sd is None:
        sd = DisclosureMetadata.from_model(payload)

    sd_claims = common.selectively_disclosable_claims(delegate_claims, sd)
    return common.issue_sd_jwt(
        claims=sd_claims,
        issuer_key=issuer_key,
        header_params=common.header_parameters(issuer_key),
        add_decoy_claims=add_decoy_claims,
        serialization_format=serialization_format,
    )


def verify(
    token: str,
    issuer_public_key: JWK,
    expected_aud: str | None = None,
    expected_nonce: str | None = None,
) -> dict[str, Any]:
    """Verify an SD-JWT signature and return the fully-resolved payload.

    ``issuer_public_key`` MUST be a :class:`jwcrypto.jwk.JWK`. To verify with
    a ``cryptography`` EC public key (e.g. extracted from an ``x5c`` cert),
    wrap it via ``JWK.from_pyca(pub_key)`` first.
    """

    def cb_get_issuer_key(
        _issuer: str,
        _header_parameters: dict[str, Any],
    ) -> JWK:
        return issuer_public_key

    verifier = SDJWTVerifier(
        token,
        cb_get_issuer_key,
        expected_aud=expected_aud,
        expected_nonce=expected_nonce,
        serialization_format='compact',
    )
    return verifier.get_verified_payload()
