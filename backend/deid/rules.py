"""Force / protect term rules → openmed custom_recognizer."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from backend.deid.constants import CROSS_LIST_CONFLICT_MESSAGE, FORCE_DENY_LABEL


def normalize_term(term: str) -> str:
    return (term or "").strip()


def term_key(term: str) -> str:
    return normalize_term(term).casefold()


def cleaned_terms(terms: Sequence[str]) -> list[str]:
    return [normalize_term(term) for term in terms if normalize_term(term)]


def has_cross_list_conflict(
    force_terms: Sequence[str], protect_terms: Sequence[str]
) -> bool:
    force_keys = {term_key(term) for term in cleaned_terms(force_terms)}
    protect_keys = {term_key(term) for term in cleaned_terms(protect_terms)}
    return bool(force_keys & protect_keys)


def build_custom_recognizer(
    force_terms: Sequence[str], protect_terms: Sequence[str]
) -> dict[str, Any] | None:
    force = cleaned_terms(force_terms)
    protect = cleaned_terms(protect_terms)
    if not force and not protect:
        return None
    if has_cross_list_conflict(force, protect):
        raise ValueError(CROSS_LIST_CONFLICT_MESSAGE)
    return {
        "case_sensitive": False,
        "deny": {
            "terms": [{"term": term, "label": FORCE_DENY_LABEL} for term in force]
        },
        "allow": {"terms": protect},
    }


def resolve_custom_recognizer(
    force_terms: Sequence[str] | None = None,
    protect_terms: Sequence[str] | None = None,
) -> Any | None:
    return build_custom_recognizer(
        list(force_terms or ()),
        list(protect_terms or ()),
    )
