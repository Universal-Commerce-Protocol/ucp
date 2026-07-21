"""High-level mandate facade.

``MandateClient`` is the outer API that AP2 roles use:

- ``create(payloads, issuer_key, sd=None)`` — mint a root SD-JWT.
- ``present(holder_key, mandate_token, payloads, ...)`` — append one
  delegation hop via :mod:`ap2.sdk.sdjwt.kb_sd_jwt`.
- ``verify(token, key_or_provider, ...)`` — verify a single token or any
  ``~~``-joined delegation chain via
  :func:`ap2.sdk.sdjwt.chain.verify_chain`.

This module also owns the typed :class:`SdJwtMandate` wrapper used for
single-token convenience verification.
"""

from __future__ import annotations

import datetime
import json
import logging
import pathlib

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from ap2.sdk.disclosure_metadata import (
    DisclosureMetadata,
    sd_claims_to_disclose,
)
from ap2.sdk.sdjwt import chain as _chain
from ap2.sdk.sdjwt import common, kb_sd_jwt, sd_jwt
from ap2.sdk.sdjwt.chain import PublicKeyProvider
from ap2.sdk.utils import b64url_decode
from jwcrypto.jwk import JWK
from sd_jwt.holder import SDJWTHolder


T = TypeVar('T', bound=Any)

_SDK_ROOT = pathlib.Path(__file__).resolve().parents[3]
LOG_FILE_PATH = str(_SDK_ROOT / '.logs' / 'mandate_operations.log')

# RFC 9901 §4.2: a disclosure is the base64url of a JSON array of either
# 2 elements (array element: [salt, value]) or 3 elements
# (object property: [salt, name, value]).
_SD_JWT_DISCLOSURE_ARRAY_LEN = 2
_SD_JWT_DISCLOSURE_PROPERTY_LEN = 3
_COMPACT_JWT_PARTS = 3


def _log_event(event_type: str, stage: str, data: dict[str, Any]) -> None:
    """Append a structured event to the mandate operations log file."""
    log_entry = {
        'timestamp': datetime.datetime.now().isoformat(),
        'event': event_type,
        'stage': stage,
        'data': data,
    }
    try:
        log_path = pathlib.Path(LOG_FILE_PATH)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open('a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except OSError as e:
        logging.warning('Failed to write to mandate log file: %s', e)


def _canonical_chain_segment(segment: str, index: int, total: int) -> str:
    """Restore the trailing ``~`` stripped when joining dSD-JWT segments."""
    if index == total - 1 or segment.endswith('~'):
        return segment
    last_segment = segment.rsplit('~', maxsplit=1)[-1]
    if len(last_segment.split('.')) == _COMPACT_JWT_PARTS:
        return segment
    return segment + '~'


# ── Typed mandate wrappers ───────────────────────────────────────────────


class Mandate(ABC, Generic[T]):  # noqa: UP046  (PEP 695 requires py312; repo supports py311+)
    """Base interface for all mandates."""

    @property
    @abstractmethod
    def serialized(self) -> str:
        """Returns the serialized representation of the mandate."""

    @property
    @abstractmethod
    def mandate_payload(self) -> T:
        """Returns the underlying mandate payload object."""

    def is_valid(self) -> bool:
        """Checks if the mandate is currently valid."""
        return True


class SdJwtMandate(Mandate[T]):
    """Mandate backed by a single SD-JWT compact serialization."""

    def __init__(self, sd_jwt_issuance: str, mandate_payload: T):
        self._serialized = sd_jwt_issuance
        self._mandate_payload = mandate_payload

    @property
    def serialized(self) -> str:
        return self._serialized

    @property
    def mandate_payload(self) -> T:
        return self._mandate_payload

    @classmethod
    def from_sd_jwt(
        cls,
        compact_serialization: str,
        issuer_public_key: JWK,
        payload_type: type[T],
        expected_aud: str | None = None,
        expected_nonce: str | None = None,
    ) -> SdJwtMandate[T]:
        """Verify a single SD-JWT and wrap it as a Mandate."""
        verified_payload = sd_jwt.verify(
            compact_serialization,
            issuer_public_key,
            expected_aud=expected_aud,
            expected_nonce=expected_nonce,
        )
        delegate_payload = verified_payload.get('delegate_payload')
        if isinstance(delegate_payload, list):
            disclosed = [
                item for item in delegate_payload if isinstance(item, dict)
            ]
            if len(disclosed) != 1:
                raise ValueError(
                    f'delegate_payload has {len(disclosed)} disclosed items,'
                    ' expected exactly 1'
                )
            effective = disclosed[0]
        else:
            effective = verified_payload
        payload = payload_type.model_validate(effective)
        return cls(compact_serialization, payload)


# ── MandateClient facade ─────────────────────────────────────────────────


_HashMode = kb_sd_jwt.HashMode


class MandateClient:
    """Stateless client for creating, presenting, and verifying AP2 mandates."""

    def create(
        self,
        payloads: list[Any],
        issuer_key: JWK,
        sd: DisclosureMetadata | None = None,
    ) -> str:
        """Sign a root SD-JWT for ``payloads[0]``.

        See :func:`ap2.sdk.sdjwt.sd_jwt.create` for details. ``sd=None``
        auto-derives selective-disclosure metadata from the payload model's
        annotations.
        """
        issuer = sd_jwt.create(
            payload=payloads[0],
            issuer_key=issuer_key,
            sd=sd,
        )
        return issuer.sd_jwt_issuance

    def verify(  # noqa: PLR0913  (public API: each kwarg is independent input)
        self,
        token: str,
        key_or_provider: JWK | PublicKeyProvider,
        payload_type: type[T] | None = None,
        expected_aud: str | None = None,
        expected_nonce: str | None = None,
        clock_skew_seconds: int = 300,
        current_time: int | None = None,
    ) -> Mandate[T] | list[dict[str, Any]]:
        """Unified verifier for single tokens and ``~~``-joined chains.

        ``key_or_provider`` MUST be one of:

        - a :class:`jwcrypto.jwk.JWK` — used as-is for a single-token verify, or
        - a callable ``(ParsedToken) -> JWK`` — used for the root hop of a
          chain.

        Wrap a ``cryptography`` EC public key with ``JWK.from_pyca(pub)`` before
        passing it in. Returns an :class:`SdJwtMandate[T]` for single tokens
        when ``payload_type`` is given, otherwise a list of per-hop effective
        payload dicts.
        """
        tokens = token.split('~~')
        is_single = len(tokens) == 1

        if is_single:
            if not isinstance(key_or_provider, JWK):
                raise TypeError(
                    'Single mandate verification requires a jwcrypto.jwk.JWK; '
                    f'got {type(key_or_provider).__name__}. Wrap '
                    'cryptography EC keys '
                    'with JWK.from_pyca(...).'
                )
            if payload_type is None:
                raise ValueError(
                    'Single mandate verification requires payload_type.'
                )
            single_key = key_or_provider

            def public_key_provider(_token: common.ParsedToken) -> JWK:
                return single_key
        else:
            if isinstance(key_or_provider, JWK):
                raise ValueError(
                    'Chain verification requires a public key provider '
                    'function (ParsedToken -> JWK), not a single JWK.'
                )
            public_key_provider = key_or_provider

        final_token = tokens[-1]
        if '~' in final_token:
            has_kb_jwt = bool(final_token.split('~')[-1].strip())
            if has_kb_jwt and not (expected_aud and expected_nonce):
                raise ValueError(
                    'The provided presentation token contains a Key Binding '
                    'JWT, but expected_aud and expected_nonce were not '
                    'provided. Both must be supplied to securely verify '
                    'this presentation.'
                )
        elif is_single:
            raise NotImplementedError(
                'Only SD-JWT formats are currently supported for verification.'
            )
        parsed_tokens = [
            common.parse_token(_canonical_chain_segment(t, i, len(tokens)))
            for i, t in enumerate(tokens)
        ]

        _log_event(
            'verify',
            'before',
            {
                'mode': 'single' if is_single else 'chain',
                'num_tokens': len(tokens),
                'payload_type': payload_type.__name__ if payload_type else None,
                'has_aud': bool(expected_aud),
                'has_nonce': bool(expected_nonce),
            },
        )

        payloads = _chain.verify_chain(
            tokens=parsed_tokens,
            public_key_provider=public_key_provider,
            clock_skew_seconds=clock_skew_seconds,
            expected_aud=expected_aud,
            expected_nonce=expected_nonce,
            current_time=current_time,
        )

        _log_event(
            'verify',
            'after',
            {'success': True, 'num_payloads': len(payloads)},
        )

        if is_single:
            return SdJwtMandate(
                parsed_tokens[0].canonical,
                payload_type.model_validate(payloads[0]),
            )
        return payloads

    def present(  # noqa: PLR0913  (public API: one branch per arg combination)
        self,
        holder_key: JWK,
        mandate_token: str,
        payloads: list[Any],
        sd: DisclosureMetadata | None = None,
        claims_to_disclose: dict[str, Any] | None = None,
        nonce: str | None = None,
        aud: str | None = None,
        hash_mode: _HashMode = 'sd_hash',
    ) -> str:
        """Append one delegation hop on top of ``mandate_token``.

        Dispatches to :func:`ap2.sdk.sdjwt.kb_sd_jwt.create`; closed mandates
        are terminal hops, while open mandates with ``cnf`` delegate further.

        ``hash_mode`` selects how this new hop binds to ``mandate_token``:
          - ``"sd_hash"`` (default): commits to the preceding hop's exact
            disclosures. Next delegate cannot further redact them.
          - ``"issuer_jwt_hash"``: commits only to the preceding issuer-signed
            JWT, allowing the next delegate to drop disclosures from it
            (draft-gco-oauth-delegate-sd-jwt-00 §5.1.4).
        """
        _log_event(
            'create_presentation',
            'before',
            {
                'has_claims_to_disclose': claims_to_disclose is not None,
                'has_nonce': bool(nonce),
                'has_aud': bool(aud),
                'hash_mode': hash_mode,
            },
        )

        if (nonce or aud) and not holder_key:
            raise ValueError(
                'nonce and aud require the holder_key parameter to be provided.'
            )

        if not payloads:
            raise ValueError('payloads list cannot be empty.')

        if claims_to_disclose is not None:
            holder_open = SDJWTHolder(mandate_token)
            selected_disclosures = []
            # ``_input_disclosures`` is the canonical list of disclosures
            # SDJWTHolder parsed from the input token. The sd_jwt library does
            # not expose a public equivalent, so we reach in here. See
            # SDJWTHolder.__init__ in py-sd-jwt for the contract.
            for d in holder_open._input_disclosures:  # noqa: SLF001
                decoded = json.loads(b64url_decode(d).decode('utf-8'))
                if len(decoded) == _SD_JWT_DISCLOSURE_ARRAY_LEN:
                    val = decoded[1]
                    if isinstance(val, dict) and 'vct' in val:
                        selected_disclosures.append(d)
                elif len(decoded) == _SD_JWT_DISCLOSURE_PROPERTY_LEN:
                    key = decoded[1]
                    if key == 'cnf' or key in claims_to_disclose:
                        selected_disclosures.append(d)
            jwt_part = mandate_token.split('~', maxsplit=1)[0]
            redacted_open_tok = (
                jwt_part + '~' + '~'.join(selected_disclosures) + '~'
            )
            wrapped = {'delegate_payload': [claims_to_disclose]}
        else:
            redacted_open_tok = None
            wrapped = {'delegate_payload': [sd_claims_to_disclose(payloads[0])]}

        # Bind against the exact on-wire form of the preceding token. When the
        # caller filters disclosures with ``claims_to_disclose``, the
        # redacted-and-sent form is what downstream verifiers will re-hash, so
        # we must compute ``sd_hash`` over that form — not over the original
        # full-disclosure token.
        prev_token_for_binding = (
            redacted_open_tok
            if redacted_open_tok is not None
            else mandate_token
        )
        prev_token_parsed = common.parse_token(prev_token_for_binding)

        if not (aud and nonce):
            raise ValueError('aud and nonce are required for KB-SD-JWT hops.')
        issuer = kb_sd_jwt.create(
            prev_token=prev_token_parsed,
            holder_key=holder_key,
            payload=payloads[0],
            aud=aud,
            nonce=nonce,
            sd=sd,
            hash_mode=hash_mode,
        )

        holder = SDJWTHolder(issuer.sd_jwt_issuance)

        holder.create_presentation(claims_to_disclose=wrapped)
        pres_jwt = holder.sd_jwt_presentation

        _log_event(
            'create_presentation',
            'after',
            {
                'success': True,
                'pres_jwt': pres_jwt,
                'aud': aud,
                'holder_pub': (
                    json.loads(holder_key.export_public())
                    if (nonce or aud)
                    else None
                ),
            },
        )

        if redacted_open_tok is not None:
            open_tok_to_join = (
                redacted_open_tok[:-1]
                if redacted_open_tok.endswith('~')
                else redacted_open_tok
            )
            return f'{open_tok_to_join}~~{pres_jwt}'
        mandate_tok_to_join = (
            mandate_token[:-1] if mandate_token.endswith('~') else mandate_token
        )
        return f'{mandate_tok_to_join}~~{pres_jwt}'

    def get_closed_mandate_jwt(self, presentation_token: str) -> str:
        """Return the closed-mandate JWT (leaf) of a dSD-JWT chain.

        Examples:
        - ``"<jwt>"`` -> ``"<jwt>"``
        - ``"<jwt>~"`` -> ``"<jwt>"``
        - ``"<open>~~<closed_jwt>~"`` -> ``"<closed_jwt>"``
        - ``"<open>~~<mid_jwt>~d1~d2~~<closed_jwt>~"`` -> ``"<closed_jwt>"``

        Use the SHA-256 of this string as the stable receipt reference, so a
        receipt stays bound to the same closed mandate regardless of how many
        delegation hops precede it or which open-mandate disclosures were
        revealed.
        """
        last_segment = presentation_token.rsplit('~~', 1)[-1]
        return last_segment.split('~', 1)[0]
