"""Domain operations wrapping openmed deidentify / DOCX helpers."""

from __future__ import annotations

import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from openmed import deidentify

from backend.deid.constants import (
    DEIDENTIFICATION_METHODS,
    DETECTION_CONFIDENCE_THRESHOLD,
    PDF_SCANNED_HINT,
    REPLACE_SEED,
)
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
    kwargs: dict[str, Any] = {
        "method": method,
        "confidence_threshold": DETECTION_CONFIDENCE_THRESHOLD,
    }
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
    from backend.deid.rules_detect import (
        entities_from_custom_recognizer,
        merge_entities_prefer_rules,
    )
    from backend.deid.script_policy import is_cjk_heavy_span

    # Always run the model, drop its Chinese guesses, then re-attach CN via rules.
    result = deidentify(
        text,
        **deidentify_kwargs(method, custom_recognizer, surrogate_vault=surrogate_vault),
    )
    model_entities = [
        entity
        for entity in serialize_review_entities(result.pii_entities)
        if not is_cjk_heavy_span(entity.text)
    ]
    rule_entities = entities_from_custom_recognizer(text, method, custom_recognizer)
    return ReviewView(
        text=text,
        entities=merge_entities_prefer_rules(model_entities, rule_entities),
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
    from backend.deid.docx_ooxml import load_enriched_docx

    enriched = load_enriched_docx(source)
    return run_review(
        enriched.text,
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

    from openmed.multimodal import write_redacted_docx

    from backend.deid.docx_ooxml import (
        apply_textbox_redactions,
        load_enriched_docx,
        partition_docx_spans,
    )

    enriched = load_enriched_docx(source)
    selective = apply_selected_redaction(
        enriched.text,
        method,
        selected_spans,
        custom_recognizer=custom_recognizer,
        surrogate_vault=surrogate_vault,
        review_entities=review_entities,
    )
    out_dir = Path(tempfile.mkdtemp(prefix="openmed-deid-web-"))
    output_path = out_dir / f"{source.stem}_redacted.docx"
    body_spans, box_spans = partition_docx_spans(
        enriched, selective.applied_entities
    )
    span_payload = [
        {
            "start": entity.start,
            "end": entity.end,
            "label": entity.label,
            "text": entity.text,
            "redacted_text": entity.replacement,
        }
        for entity in body_spans
    ]
    if span_payload:
        write_redacted_docx(source, output_path, span_payload)
    else:
        output_path.write_bytes(source.read_bytes())
    if box_spans:
        apply_textbox_redactions(
            output_path,
            output_path,
            enriched.textboxes,
            box_spans,
        )
    return SelectiveRedactionView(
        deidentified_text=selective.deidentified_text,
        applied_entities=selective.applied_entities,
        output_path=str(output_path),
    )


# ---------------------------------------------------------------------------
# PDF (non-scanned) review + redaction
# ---------------------------------------------------------------------------


def _extract_pdf_document(source: str | Path) -> Any:
    """Extract a PDF document, raising a clear error for scanned / empty PDFs."""
    from openmed.multimodal import extract_pdf

    document = extract_pdf(source)
    if not document.text.strip():
        raise ValueError(PDF_SCANNED_HINT)
    return document


def run_pdf_review(
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
    if source.suffix.lower() != ".pdf":
        raise ValueError("Only .pdf uploads are supported.")
    document = _extract_pdf_document(source)
    return run_review(
        document.text,
        method,
        custom_recognizer=custom_recognizer,
        surrogate_vault=surrogate_vault,
    )


def _import_pymupdf() -> Any:
    import importlib

    return importlib.import_module("pymupdf")


def _write_redacted_pdf(
    source: str | Path,
    output_path: str | Path,
    rectangles: Sequence[Any],
) -> None:
    """Draw black boxes over the given (page, bbox) rectangles and strip the
    underlying text layer using PyMuPDF redaction annotations."""
    pymupdf = _import_pymupdf()
    doc = pymupdf.open(source)
    try:
        for rectangle in rectangles:
            page_index = int(rectangle.page)
            if page_index < 0 or page_index >= len(doc):
                continue
            page = doc[page_index]
            page.add_redact_annot(
                pymupdf.Rect(*rectangle.bbox),
                fill=(0, 0, 0),
                cross_out=False,
            )
        for page in doc:
            page.apply_redactions()
        doc.save(output_path)
    finally:
        doc.close()


def _verify_pdf_fidelity(
    source: str | Path,
    output_path: str | Path,
    rectangles: Sequence[Any],
) -> dict:
    """Fail-closed fidelity check using PyMuPDF directly (pdfplumber cannot
    parse PyMuPDF redaction paths as rects, so the openmed verifier would
    misreport visible boxes)."""
    pymupdf = _import_pymupdf()
    source_doc = pymupdf.open(source)
    output_doc = pymupdf.open(output_path)
    results: list[dict[str, Any]] = []
    try:
        for rectangle in rectangles:
            page_index = int(rectangle.page)
            if page_index < 0 or page_index >= len(source_doc):
                continue
            bbox = tuple(float(value) for value in rectangle.bbox)
            rect = pymupdf.Rect(*bbox)
            words = [
                str(word[4]).strip()
                for word in output_doc[page_index].get_text("words", clip=rect)
                if str(word[4]).strip()
            ]
            src_crop = source_doc[page_index].get_pixmap(dpi=150, clip=rect)
            out_crop = output_doc[page_index].get_pixmap(dpi=150, clip=rect)
            pixels_changed = src_crop.samples != out_crop.samples
            passed = not words and pixels_changed
            results.append(
                {
                    "page": page_index,
                    "bbox": list(bbox),
                    "label": getattr(rectangle, "label", None),
                    "residual_text_found": bool(words),
                    "residual_word_count": len(words),
                    "pixels_changed": pixels_changed,
                    "passed": passed,
                }
            )
    finally:
        source_doc.close()
        output_doc.close()
    return {
        "check": "pdf_redaction_fidelity",
        "passed": bool(results) and all(result["passed"] for result in results),
        "region_count": len(results),
        "failing_region_count": sum(1 for result in results if not result["passed"]),
        "regions": results,
    }


def apply_selected_pdf_redaction(
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
    if source.suffix.lower() != ".pdf":
        raise ValueError("Only .pdf uploads are supported.")

    document = _extract_pdf_document(source)
    selective = apply_selected_redaction(
        document.text,
        method,
        selected_spans,
        custom_recognizer=custom_recognizer,
        surrogate_vault=surrogate_vault,
        review_entities=review_entities,
    )
    out_dir = Path(tempfile.mkdtemp(prefix="openmed-deid-web-"))
    output_path = out_dir / f"{source.stem}_redacted.pdf"
    if not selective.applied_entities:
        output_path.write_bytes(source.read_bytes())
        fidelity: dict | None = None
    else:
        from openmed.multimodal import project_text_spans

        rectangles = project_text_spans(document, selective.applied_entities)
        try:
            _write_redacted_pdf(source, output_path, rectangles)
        except ImportError as exc:
            raise ValueError(
                'PDF redaction needs: pip install "pymupdf".'
            ) from exc
        fidelity = _verify_pdf_fidelity(source, output_path, rectangles)
    return SelectiveRedactionView(
        deidentified_text=selective.deidentified_text,
        applied_entities=selective.applied_entities,
        output_path=str(output_path),
        fidelity=fidelity,
    )
