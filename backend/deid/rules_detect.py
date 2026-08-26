"""Build review entities from custom deny rules only (no ML model)."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Any

from backend.deid.models import ReviewEntity


def _coerce_recognizer(custom_recognizer: Any) -> Any | None:
    if custom_recognizer is None:
        return None
    from openmed.core.custom_recognizer import coerce_custom_recognizer

    return coerce_custom_recognizer(custom_recognizer)


def replacement_for_method(method: str, *, label: str, text: str) -> str:
    if method == "remove":
        return ""
    if method == "hash":
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return digest[:10]
    if method == "format_preserve":
        return "*" * len(text)
    return f"[{label or 'PII'}]"


def _non_overlapping(matches: Sequence[Any]) -> list[Any]:
    selected: list[Any] = []
    cursor = -1
    for match in sorted(
        matches, key=lambda item: (int(item.start), -(int(item.end) - int(item.start)))
    ):
        start = int(match.start)
        end = int(match.end)
        if start < cursor:
            continue
        selected.append(match)
        cursor = end
    return selected


def entities_from_custom_recognizer(
    text: str,
    method: str,
    custom_recognizer: Any | None,
) -> list[ReviewEntity]:
    recognizer = _coerce_recognizer(custom_recognizer)
    if recognizer is None or not getattr(recognizer, "has_deny_rules", False):
        return []
    matches = _non_overlapping(recognizer.deny_matches(text))
    rows: list[ReviewEntity] = []
    for index, match in enumerate(matches):
        label = str(getattr(match, "label", "") or "OTHER")
        start = int(match.start)
        end = int(match.end)
        span_text = text[start:end]
        confidence = float(getattr(match, "confidence", 1.0) or 1.0)
        rows.append(
            ReviewEntity(
                id=f"r{index}",
                label=label,
                text=span_text,
                start=start,
                end=end,
                confidence=confidence,
                replacement=replacement_for_method(
                    method, label=label, text=span_text
                ),
            )
        )
    return rows


def merge_entities_prefer_rules(
    model_entities: Sequence[ReviewEntity],
    rule_entities: Sequence[ReviewEntity],
) -> list[ReviewEntity]:
    """Union spans; on overlap keep the rule entity."""
    selected: list[ReviewEntity] = []
    occupied: list[tuple[int, int]] = []

    def overlaps(start: int, end: int) -> bool:
        return any(not (end <= left or start >= right) for left, right in occupied)

    for entity in rule_entities:
        selected.append(entity)
        occupied.append((entity.start, entity.end))
    for entity in model_entities:
        if overlaps(entity.start, entity.end):
            continue
        selected.append(entity)
        occupied.append((entity.start, entity.end))
    selected.sort(key=lambda item: (item.start, item.end))
    return [
        ReviewEntity(
            id=f"e{index}",
            label=entity.label,
            text=entity.text,
            start=entity.start,
            end=entity.end,
            confidence=entity.confidence,
            replacement=entity.replacement,
        )
        for index, entity in enumerate(selected)
    ]
