"""Domain operations wrapping openmed deidentify / DOCX helpers."""

from __future__ import annotations

import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from openmed import deidentify

from backend.deid.constants import DEIDENTIFICATION_METHODS, REPLACE_SEED
from backend.deid.models import (
    ReviewEntity,
    ReviewView,
    SelectiveRedactionView,
)


def make_session_vault() -> Any:
    from openmed import SurrogateVault
    from backend.deid.constants import REPLACE_VAULT_SECRET

    return SurrogateVault.in_memory(REPLACE_VAULT_SECRET)


def _entity_confidence(entity: Any) -> float:
    raw = getattr(entity, "confidence", None)
    try:
        return float(raw) if raw is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _entity_replacement(entity: Any, *, label: str) -> str:
    for attr in ("redacted_text", "surrogate"):
        value = getattr(entity, attr, None)
        if value is not None and str(value) != "":
            return str(value)
    return f"[{label or 'PII'}]"


def serialize_review_entities(entities: Sequence[Any]) -> list[ReviewEntity]:
    rows: list[ReviewEntity] = []
    for index, entity in enumerate(entities):
        label = str(getattr(entity, "label", "") or "")
        start = int(getattr(entity, "start", 0) or 0)
        end = int(getattr(entity, "end", 0) or 0)
        text = str(
            getattr(entity, "text", "") or getattr(entity, "original_text", "") or ""
        )
        rows.append(
            ReviewEntity(
                id=f"e{index}",
                label=label,
                text=text,
                start=start,
                end=end,
                confidence=_entity_confidence(entity),
                replacement=_entity_replacement(entity, label=label),
            )
        )
    return rows


def review_entities_to_dicts(entities: Sequence[ReviewEntity]) -> list[dict[str, Any]]:
    return [
        {
            "id": entity.id,
            "label": entity.label,
            "text": entity.text,
            "start": entity.start,
            "end": entity.end,
            "confidence": entity.confidence,
            "replacement": entity.replacement,
        }
        for entity in entities
    ]


def deidentify_kwargs(
    method: str,
    custom_recognizer: Any | None = None,
    surrogate_vault: Any | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"method": method}
    if method in {"replace", "format_preserve"}:
        kwargs["consistent"] = True
        kwargs["seed"] = REPLACE_SEED
        if method == "replace" and surrogate_vault is not None:
            kwargs["surrogate_vault"] = surrogate_vault
    if custom_recognizer is not None:
        kwargs["custom_recognizer"] = custom_recognizer
    return kwargs


def run_review(
    text: str,
    method: str,
    custom_recognizer: Any | None = None,
    surrogate_vault: Any | None = None,
) -> ReviewView:
    if method not in DEIDENTIFICATION_METHODS:
        raise ValueError(
            f"Unsupported method {method!r}; choose one of {DEIDENTIFICATION_METHODS}."
        )
    result = deidentify(
        text,
        **deidentify_kwargs(method, custom_recognizer, surrogate_vault=surrogate_vault),
    )
    return ReviewView(
        text=text,
        entities=serialize_review_entities(result.pii_entities),
        method=method,
    )


def run_docx_review(
    upload_path: str | Path,
    method: str,
    custom_recognizer: Any | None = None,
    surrogate_vault: Any | None = None,
) -> ReviewView:
    if method not in DEIDENTIFICATION_METHODS:
        raise ValueError(
            f"Unsupported method {method!r}; choose one of {DEIDENTIFICATION_METHODS}."
        )
    source = Path(upload_path)
    if source.suffix.lower() != ".docx":
        raise ValueError("Only .docx uploads are supported (not legacy .doc).")
    from openmed.multimodal import extract_docx

    document = extract_docx(source)
    return run_review(
        document.text,
        method,
        custom_recognizer=custom_recognizer,
        surrogate_vault=surrogate_vault,
    )


def _selected_span_keys(
    selected_spans: Sequence[Mapping[str, Any] | ReviewEntity],
) -> set[tuple[int, int]]:
    keys: set[tuple[int, int]] = set()
    for span in selected_spans:
        if isinstance(span, ReviewEntity):
            keys.add((span.start, span.end))
            continue
        try:
            start = int(span["start"])
            end = int(span["end"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                "selected_spans entries must include integer start/end"
            ) from exc
        keys.add((start, end))
    return keys


def _review_entity_from_mapping(span: Mapping[str, Any], *, index: int) -> ReviewEntity:
    label = str(span.get("label") or "")
    text = str(span.get("text") or "")
    # Explicit "" is a valid custom replacement (e.g. remove / blank out).
    if "replacement" in span and span.get("replacement") is not None:
        replacement = str(span.get("replacement"))
    else:
        replacement = f"[{label or 'PII'}]"
    return ReviewEntity(
        id=str(span.get("id") or f"e{index}"),
        label=label,
        text=text,
        start=int(span["start"]),
        end=int(span["end"]),
        confidence=float(span.get("confidence") or 0.0),
        replacement=replacement,
    )


def _rebuild_with_entities(
    text: str, applied: Sequence[ReviewEntity]
) -> SelectiveRedactionView:
    ordered = sorted(applied, key=lambda entity: entity.start, reverse=True)
    output = text
    for entity in ordered:
        if entity.start < 0 or entity.end > len(output) or entity.start > entity.end:
            continue
        output = output[: entity.start] + entity.replacement + output[entity.end :]
    return SelectiveRedactionView(
        deidentified_text=output,
        applied_entities=list(applied),
    )


def apply_selected_redaction(
    text: str,
    method: str,
    selected_spans: Sequence[Mapping[str, Any] | ReviewEntity],
    custom_recognizer: Any | None = None,
    surrogate_vault: Any | None = None,
    review_entities: Sequence[ReviewEntity] | None = None,
) -> SelectiveRedactionView:
    if method not in DEIDENTIFICATION_METHODS:
        raise ValueError(
            f"Unsupported method {method!r}; choose one of {DEIDENTIFICATION_METHODS}."
        )
    selected_keys = _selected_span_keys(selected_spans)
    if not selected_keys:
        return SelectiveRedactionView(deidentified_text=text, applied_entities=[])

    if selected_spans and all(
        isinstance(span, ReviewEntity)
        or (isinstance(span, Mapping) and "replacement" in span)
        for span in selected_spans
    ):
        applied = []
        for index, span in enumerate(selected_spans):
            entity = (
                span
                if isinstance(span, ReviewEntity)
                else _review_entity_from_mapping(span, index=index)
            )
            if (entity.start, entity.end) in selected_keys:
                applied.append(entity)
        return _rebuild_with_entities(text, applied)

    if review_entities:
        applied = [
            entity
            for entity in review_entities
            if (entity.start, entity.end) in selected_keys
        ]
        if len(applied) == len(selected_keys):
            return _rebuild_with_entities(text, applied)

    result = deidentify(
        text,
        **deidentify_kwargs(method, custom_recognizer, surrogate_vault=surrogate_vault),
    )
    review = serialize_review_entities(result.pii_entities)
    applied = [
        entity for entity in review if (entity.start, entity.end) in selected_keys
    ]
    return _rebuild_with_entities(text, applied)


def apply_selected_docx_redaction(
    upload_path: str | Path,
    method: str,
    selected_spans: Sequence[Mapping[str, Any] | ReviewEntity],
    custom_recognizer: Any | None = None,
    surrogate_vault: Any | None = None,
    review_entities: Sequence[ReviewEntity] | None = None,
) -> SelectiveRedactionView:
    if method not in DEIDENTIFICATION_METHODS:
        raise ValueError(
            f"Unsupported method {method!r}; choose one of {DEIDENTIFICATION_METHODS}."
        )
    source = Path(upload_path)
    if source.suffix.lower() != ".docx":
        raise ValueError("Only .docx uploads are supported (not legacy .doc).")

    from openmed.multimodal import extract_docx, write_redacted_docx

    document = extract_docx(source)
    selective = apply_selected_redaction(
        document.text,
        method,
        selected_spans,
        custom_recognizer=custom_recognizer,
        surrogate_vault=surrogate_vault,
        review_entities=review_entities,
    )
    out_dir = Path(tempfile.mkdtemp(prefix="openmed-deid-web-"))
    output_path = out_dir / f"{source.stem}_redacted.docx"
    span_payload = [
        {
            "start": entity.start,
            "end": entity.end,
            "label": entity.label,
            "text": entity.text,
            "redacted_text": entity.replacement,
        }
        for entity in selective.applied_entities
    ]
    if span_payload:
        write_redacted_docx(source, output_path, span_payload)
    else:
        output_path.write_bytes(source.read_bytes())
    return SelectiveRedactionView(
        deidentified_text=selective.deidentified_text,
        applied_entities=selective.applied_entities,
        output_path=str(output_path),
    )
