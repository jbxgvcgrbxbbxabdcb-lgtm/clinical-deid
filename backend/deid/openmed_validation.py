"""Document-aware patch for openmed input validation.

openmed.validate_input rejects text when any single character repeats 100+
times. PDF/DOCX extraction often preserves TOC dot leaders and form
underlines, which triggers that check even though the content is benign.

We patch openmed.utils.validation._contains_suspicious_content once at
import time so deidentify/analyze_text accept real-world documents while
still blocking binary control-character runs and non-formatting repeats.
"""

from __future__ import annotations

import re
from typing import Final

# Common layout characters from PDF/DOCX text extraction — not abuse signals.
_BENIGN_REPEAT_CHARS: Final[frozenset[str]] = frozenset(".·…-_ \t")
_LAYOUT_CHARS: Final[frozenset[str]] = frozenset(".·…-_")


def _non_layout_special_ratio(text: str) -> float:
    if not text:
        return 0.0
    special = sum(
        1
        for ch in text
        if not ch.isalnum() and not ch.isspace() and ch not in _LAYOUT_CHARS
    )
    return special / len(text)


def contains_suspicious_content(text: str) -> bool:
    """Return True when text looks like garbage or an injection payload."""
    for match in re.finditer(r"(.)\1{100,}", text):
        if match.group(1) not in _BENIGN_REPEAT_CHARS:
            return True

    if _non_layout_special_ratio(text) > 0.5:
        return True

    if re.search(r"[\x00-\x08\x0e-\x1f\x7f]{10,}", text):
        return True

    return False


_PATCHED = False


def apply_openmed_validation_patch() -> None:
    """Replace openmed's naive repeat-character guard with our document-aware one."""
    global _PATCHED
    if _PATCHED:
        return

    import openmed.utils.validation as validation

    validation._contains_suspicious_content = contains_suspicious_content
    _PATCHED = True
