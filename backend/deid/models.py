"""Domain view models for review and redaction."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewEntity:
    """One detected span for the review → select → redact UI."""

    id: str
    label: str
    text: str
    start: int
    end: int
    confidence: float
    replacement: str


@dataclass(frozen=True)
class ReviewView:
    """Detect result ready for the review panel."""

    text: str
    entities: list[ReviewEntity]
    method: str


@dataclass(frozen=True)
class SelectiveRedactionView:
    """Result of applying only the user-selected spans."""

    deidentified_text: str
    applied_entities: list[ReviewEntity]
    output_path: str | None = None
    fidelity: dict | None = None
