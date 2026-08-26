"""Chinese-script policy: skip English-model guesses on CJK text."""

from __future__ import annotations

import re

# Unified Ideographs + common extension A (enough for clinical CN notes).
_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
_LATIN_RE = re.compile(r"[A-Za-z]")

# Share of letter-like chars that are CJK → treat document as Chinese-first.
CHINESE_DOMINANT_THRESHOLD = 0.35


def cjk_char_count(text: str) -> int:
    return len(_CJK_RE.findall(text or ""))


def latin_char_count(text: str) -> int:
    return len(_LATIN_RE.findall(text or ""))


def is_chinese_dominant(
    text: str, *, threshold: float = CHINESE_DOMINANT_THRESHOLD
) -> bool:
    """True when the note is primarily Chinese (model should not run)."""
    cjk = cjk_char_count(text)
    latin = latin_char_count(text)
    total = cjk + latin
    if total == 0:
        return False
    return (cjk / total) >= threshold


def is_cjk_heavy_span(text: str) -> bool:
    """True when a detected span is Chinese enough that the EN model is untrusted."""
    raw = (text or "").strip()
    if not raw:
        return False
    cjk = cjk_char_count(raw)
    if cjk == 0:
        return False
    # Drop model guesses like partial 阿里巴巴 / 医院 names.
    non_space = max(len(re.sub(r"\s+", "", raw)), 1)
    return cjk >= 2 or (cjk / non_space) >= 0.3
