"""Force / protect term rules → openmed custom_recognizer (+ built-in patterns)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from backend.deid.constants import CROSS_LIST_CONFLICT_MESSAGE, FORCE_DENY_LABEL

# Deterministic deny patterns that catch common model misses (EN + CN).
# Labels match openmed PII label vocabulary used by the UI.
BUILTIN_DENY_PATTERNS: tuple[dict[str, str], ...] = (
    {
        "pattern": (
            r"(?i)\b[A-Za-z0-9._%+\-]+@"
            r"(?:[A-Za-z0-9.\-]+\.[A-Za-z]{2,}|localhost)\b"
        ),
        "label": "email",
    },
    {
        # English org / company suffixes (Inc, Ltd, Holdings, …)
        "pattern": (
            r"\b(?:[A-Z][A-Za-z0-9&.'\-]+(?:\s+[A-Z][A-Za-z0-9&.'\-]+){0,6}\s+)"
            r"(?:Inc|Incorporated|Ltd|Limited|LLC|L\.L\.C|Corp|Corporation|"
            r"Holdings|Group|Company|Co|Center|Centre|Partners|PLC|GmbH)\.?"
        ),
        "label": "company_name",
    },
    {
        # Chinese org / hospital / company suffixes
        "pattern": (
            r"(?:[\u4e00-\u9fffA-Za-z0-9（）()]{2,40})"
            r"(?:有限责任公司|股份有限公司|有限公司|集团公司|集团|医院|诊所|研究所)"
        ),
        "label": "company_name",
    },
    {
        # Chinese addresses: require locality and/or 路/街 + door number.
        # Avoid bare 号/路/道/室 — those fire on 减号/路径/括号/随机号 etc.
        # Digits + 号 (88号) are allowed; 减号/括号 are not.
        "pattern": (
            r"(?:"
            # e.g. 北京市朝阳区建国路88号… / 上海市浦东新区…
            r"(?:[\u4e00-\u9fff]{1,8}(?:省|自治区|特别行政区))?"
            r"(?:[\u4e00-\u9fff]{1,8}市)"
            r"(?:[\u4e00-\u9fff]{1,8}(?:区|县|旗|镇|乡|街道))"
            r"(?:[\u4e00-\u9fffA-Za-z0-9\-·]{0,24}"
            r"(?:路|街|巷|大道|弄))?"
            r"(?:[\u4e00-\u9fffA-Za-z0-9\-·]{0,16}\d{1,6}号(?:院)?)?"
            r"(?:[\u4e00-\u9fffA-Za-z0-9\-·]{0,16}"
            r"(?:\d{1,4}(?:栋|座|楼|层|室|单元)))?"
            r"|"
            # e.g. 建国路88号SOHO现代城A座1201室 (no city prefix)
            r"(?:[\u4e00-\u9fff]{1,20}(?:路|街|巷|大道|弄))"
            r"\d{1,6}号(?:院)?"
            r"(?:[\u4e00-\u9fffA-Za-z0-9\-·]{0,24}"
            r"(?:\d{1,4}(?:栋|座|楼|层|室|单元)|[A-Za-z]\d{0,4}座))?"
            r"|"
            # e.g. 88号 / 12号楼 / 3号院 (digit required before 号)
            r"\d{1,6}号(?:院|楼|栋|座|室|单元)?"
            r")"
        ),
        "label": "street_address",
    },
    {
        # US-ish street lines when the model only tags city/state
        "pattern": (
            r"\b\d{1,6}\s+"
            r"(?:[A-Z][A-Za-z0-9.'\-]+\s+){0,6}"
            r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|"
            r"Court|Ct|Way|Place|Pl|Suite|Ste|Apartment|Apt)\.?"
            r"(?:\s*(?:#|Suite|Ste|Apt|Apartment)\.?\s*[A-Za-z0-9\-]+)?"
        ),
        "label": "street_address",
    },
)


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
    if has_cross_list_conflict(force, protect):
        raise ValueError(CROSS_LIST_CONFLICT_MESSAGE)
    return {
        "case_sensitive": False,
        "deny": {
            "terms": [{"term": term, "label": FORCE_DENY_LABEL} for term in force],
            "patterns": [dict(pattern) for pattern in BUILTIN_DENY_PATTERNS],
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
