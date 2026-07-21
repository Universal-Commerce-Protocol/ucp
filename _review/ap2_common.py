"""Common SD-JWT hashing, issuance, and claim-validation helpers."""

from __future__ import annotations

import binascii
import hashlib
import json

from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from typing import Any, Literal

from ap2.sdk.disclosure_metadata import DisclosureMetadata
from ap2.sdk.generated.types.jwk import JsonWebKey
from ap2.sdk.utils import b64url_decode, b64url_encode
from jwcrypto.jwk import JWK
from pydantic import BaseModel
from sd_jwt.issuer import SDJWTIssuer


HashMode = Literal['sd_hash', 'issuer_jwt_hash']
_COMPACT_JWT_PARTS = 3

_HASH_BY_SD_ALG: dict[str, Callable[[bytes], Any]] = {
    'sha-256': hashlib.sha256,
    'sha-384': hashlib.sha384,
    'sha-512': hashlib.sha512,
}


@dataclass(frozen=True)
class ParsedToken:
    """Parsed SD-JWT token with header and payload available once."""

    issuer_jwt: str
    disclosures: list[str]
    kb_jwt: str | None
    header: dict[str, Any]
    payload: dict[str, Any]
    verified_payload: dict[str, Any] | None = None
    delegate_items: list[dict[str, Any]] | None = None

    @property
    def typ(self) -> str | None:
        typ = self.header.get('typ')
        return typ if isinstance(typ, str) else None

    @property
    def sd_alg(self) -> str | None:
        alg = self.payload.get('_sd_alg')
        return alg if isinstance(alg, str) else None

    @property
    def sd_jwt(self) -> str:
        if self.disclosures:
            return self.issuer_jwt + '~' + '~'.join(self.disclosures) + '~'
        return self.issuer_jwt + '~'

    @property
    def canonical(self) -> str:
        if self.kb_jwt:
            return self.sd_jwt + self.kb_jwt
        return self.sd_jwt

    def with_verified_payload(
        self,
        payload: dict[str, Any],
        delegate_items: list[dict[str, Any]],
    ) -> ParsedToken:
        """Return a copy with verified, disclosure-resolved payload state."""
        return replace(
            self,
            verified_payload=payload,
            delegate_items=delegate_items,
        )

    def cnf_jwk(self) -> JWK | None:
        """Return this verified token's resolved ``cnf.jwk``, if present."""
        if self.verified_payload is None:
            raise ValueError(
                'Token has not been verified; cnf.jwk is unavailable'
            )
        cnf = self._find_cnf()
        if isinstance(cnf, dict) and 'jwk' in cnf:
            jwk_model = JsonWebKey.model_validate(cnf['jwk'])
            return JWK(**jwk_model.model_dump(exclude_none=True))
        return None

    def _find_cnf(self) -> dict[str, Any] | None:
        delegate_items = self.delegate_items or []
        for item in delegate_items:
            cnf = item.get('cnf')
            if isinstance(cnf, dict) and 'jwk' in cnf:
                return cnf
        if self.verified_payload is None:
            return None
        delegate_payload = self.verified_payload.get('delegate_payload')
        if isinstance(delegate_payload, list):
            for item in delegate_payload:
                if not isinstance(item, dict):
                    continue
                cnf = item.get('cnf')
                if isinstance(cnf, dict) and 'jwk' in cnf:
                    return cnf
        cnf = self.verified_payload.get('cnf')
        if isinstance(cnf, dict) and 'jwk' in cnf:
            return cnf
        return None


def parse_token(token: str) -> ParsedToken:
    """Parse and canonicalize a compact SD-JWT token."""
    if token.startswith('~'):
        raise ValueError('Malformed SD-JWT: empty issuer JWT')
    if '~' not in token:
        raise ValueError('Malformed SD-JWT: missing disclosure separator')

    parts = token.split('~')
    issuer_jwt = parts[0]
    disclosure_parts = parts[1:-1]
    if any(not disclosure for disclosure in disclosure_parts):
        raise ValueError('Malformed SD-JWT: empty disclosure segment')
    if token.endswith('~'):
        disclosures = disclosure_parts
        kb_jwt = None
    else:
        kb_jwt = parts[-1]
        if len(kb_jwt.split('.')) != _COMPACT_JWT_PARTS:
            raise ValueError(
                'Malformed KB-JWT: expected header.payload.signature'
            )
        disclosures = disclosure_parts

    jwt_parts = issuer_jwt.split('.')
    if len(jwt_parts) != _COMPACT_JWT_PARTS:
        raise ValueError(
            'Malformed SD-JWT: issuer JWT must have header.payload.signature'
        )
    header_segment, payload_segment, _signature_segment = jwt_parts
    header = decode_jwt_segment(header_segment, 'header')
    payload = decode_jwt_segment(payload_segment, 'payload')
    return ParsedToken(issuer_jwt, disclosures, kb_jwt, header, payload)


def decode_jwt_segment(segment: str, part_name: str) -> dict[str, Any]:
    """Decode a compact JWT header or payload segment into a JSON object."""
    try:
        decoded = json.loads(b64url_decode(segment))
    except (binascii.Error, json.JSONDecodeError) as exc:
        raise ValueError(f'Cannot parse JWT {part_name}: {exc}') from exc
    if not isinstance(decoded, dict):
        raise ValueError(f'JWT {part_name} must decode to a JSON object')
    return decoded


def _hash_for_alg(sd_alg: str | None) -> Callable[[bytes], Any]:
    if sd_alg is None:
        return hashlib.sha256
    try:
        return _HASH_BY_SD_ALG[sd_alg]
    except KeyError as exc:
        raise ValueError(f'Unsupported _sd_alg: {sd_alg!r}') from exc


def _hash_ascii(value: str, sd_alg: str | None) -> str:
    digest = _hash_for_alg(sd_alg)(value.encode('ascii')).digest()
    return b64url_encode(digest)


def compute_sd_hash(token: ParsedToken) -> str:
    """Hash an SD-JWT including disclosures, excluding a trailing KB-JWT."""
    return _hash_ascii(token.sd_jwt, token.sd_alg)


def compute_issuer_jwt_hash(token: ParsedToken) -> str:
    """Hash only the issuer-signed JWT portion of an SD-JWT."""
    return _hash_ascii(token.issuer_jwt, token.sd_alg)


def compute_disclosure_digest(disclosure: str, sd_alg: str | None) -> str:
    """Hash a disclosure string using the issuer token's SD algorithm."""
    return _hash_ascii(disclosure, sd_alg)


def compute_binding(
    prev_token: ParsedToken, hash_mode: HashMode
) -> tuple[str, str]:
    """Return the (claim_name, value) pair for the binding hash."""
    if hash_mode == 'sd_hash':
        return 'sd_hash', compute_sd_hash(prev_token)
    if hash_mode == 'issuer_jwt_hash':
        return 'issuer_jwt_hash', compute_issuer_jwt_hash(prev_token)
    raise ValueError(
        f"hash_mode must be 'sd_hash' or 'issuer_jwt_hash', got {hash_mode!r}"
    )


def verify_binding(payload: dict[str, Any], prev_token: ParsedToken) -> None:
    """Enforce that exactly one binding claim is present and matches."""
    has_sd = 'sd_hash' in payload
    has_iss = 'issuer_jwt_hash' in payload
    if has_sd == has_iss:
        raise ValueError(
            "KB-SD-JWT payload must contain exactly one of 'sd_hash' or "
            f"'issuer_jwt_hash' (got sd_hash={has_sd}, "
            f'issuer_jwt_hash={has_iss})'
        )
    if has_sd:
        expected = compute_sd_hash(prev_token)
        actual = payload['sd_hash']
        if actual != expected:
            raise ValueError(
                f"sd_hash mismatch: expected '{expected}', got '{actual}'"
            )
    else:
        expected = compute_issuer_jwt_hash(prev_token)
        actual = payload['issuer_jwt_hash']
        if actual != expected:
            raise ValueError(
                f"issuer_jwt_hash mismatch: expected '{expected}', "
                f"got '{actual}'"
            )


def delegate_claims_from_model(payload: BaseModel) -> dict[str, Any]:
    """Serialize a Pydantic payload into AP2 delegate claims."""
    if not isinstance(payload, BaseModel):
        raise TypeError('payload must be an instance of pydantic.BaseModel')
    return payload.model_dump(by_alias=True, exclude_none=True)


def selectively_disclosable_claims(
    delegate_claims: dict[str, Any],
    sd: DisclosureMetadata | None,
    extra_claims: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build SDObj-wrapped claims with ``delegate_payload`` as the SD root."""
    claims: dict[str, Any] = {
        'delegate_payload': [delegate_claims],
        '_sd': {
            'children': {
                'delegate_payload': {'disclose_all': True},
            }
        },
    }
    if extra_claims:
        claims.update(extra_claims)
    if sd is not None:
        claims['_sd']['children']['delegate_payload']['all_array_children'] = (
            asdict(sd)
        )

    user_claims = claims.copy()
    metadata = DisclosureMetadata.from_dict(user_claims.pop('_sd'))
    return metadata.apply(user_claims)


def header_parameters(
    signing_key: JWK, typ: str | None = None
) -> dict[str, Any]:
    """Return SD-JWT header parameters, including ``kid`` when present."""
    jwk_dict = json.loads(signing_key.export())
    kid = jwk_dict.get('kid')
    params: dict[str, Any] = {}
    if typ is not None:
        params['typ'] = typ
    if kid:
        params['kid'] = kid
    return params


def issue_sd_jwt(
    *,
    claims: dict[str, Any],
    issuer_key: JWK,
    header_params: dict[str, Any],
    add_decoy_claims: bool,
    serialization_format: str,
) -> SDJWTIssuer:
    """Create an ``SDJWTIssuer`` with AP2's common issuer options."""
    return SDJWTIssuer(
        user_claims=claims,
        issuer_key=issuer_key,
        holder_key=None,
        sign_alg=None,
        add_decoy_claims=add_decoy_claims,
        serialization_format=serialization_format,
        extra_header_parameters=header_params,
    )


def verify_expected_claims(
    payload: dict[str, Any],
    *,
    expected_aud: str | None,
    expected_nonce: str | None,
    token_label: str,
) -> None:
    """Validate common KB-SD-JWT claims after signature verification."""
    if 'iat' not in payload:
        raise ValueError(f"{token_label} missing required 'iat' claim")
    if expected_aud is not None and payload.get('aud') != expected_aud:
        raise ValueError(
            f"{token_label} aud mismatch: expected '{expected_aud}',"
            f" got '{payload.get('aud')}'"
        )
    if expected_nonce is not None and payload.get('nonce') != expected_nonce:
        raise ValueError(
            f"{token_label} nonce mismatch: expected '{expected_nonce}',"
            f" got '{payload.get('nonce')}'"
        )
