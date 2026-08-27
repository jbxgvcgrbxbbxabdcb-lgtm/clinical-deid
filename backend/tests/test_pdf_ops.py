"""Unit tests for the PDF (non-scanned) review + redaction ops."""

from __future__ import annotations

from pathlib import Path

import pytest
import pymupdf

from backend.deid.constants import PDF_SCANNED_HINT
from backend.deid.ops import (
    apply_selected_pdf_redaction,
    run_pdf_review,
)


def _make_text_pdf(path: Path, text: str = "Patient John Doe, MRN 123456.") -> Path:
    """Create a PDF with a real text layer at a known position."""
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 100), text, fontsize=11)
    doc.save(path)
    doc.close()
    return path


def _make_scanned_pdf(path: Path) -> Path:
    """Create an image-only PDF (no text layer)."""
    doc = pymupdf.open()
    page = doc.new_page()
    # Pure vector drawing content — no text operators, hence no text layer.
    page.draw_rect(pymupdf.Rect(0, 0, 100, 100), color=(0, 0, 0), fill=(0.5, 0.5, 0.5))
    doc.save(path)
    doc.close()
    return path


def _make_toc_pdf(path: Path) -> Path:
    """Create a PDF whose extracted text includes long TOC dot leaders."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text(
        (72, 100),
        f"Table of Contents  {'.' * 136}  12",
        fontsize=11,
    )
    page.insert_text((72, 120), "Patient John Doe, MRN 123456.", fontsize=11)
    doc.save(path)
    doc.close()
    return path


@pytest.fixture()
def text_pdf(tmp_path: Path) -> Path:
    return _make_text_pdf(tmp_path / "note.pdf")


@pytest.fixture()
def scanned_pdf(tmp_path: Path) -> Path:
    return _make_scanned_pdf(tmp_path / "scan.pdf")


def test_run_pdf_review_detects_entities(text_pdf: Path) -> None:
    view = run_pdf_review(text_pdf, "mask")
    assert view.text and "John" in view.text
    labels = {entity.label for entity in view.entities}
    assert "first_name" in labels or "last_name" in labels


def test_run_pdf_review_rejects_non_pdf(tmp_path: Path) -> None:
    fake = tmp_path / "note.docx"
    fake.write_bytes(b"not a pdf")
    with pytest.raises(ValueError, match="Only .pdf"):
        run_pdf_review(fake, "mask")


def test_run_pdf_review_rejects_scanned(scanned_pdf: Path) -> None:
    with pytest.raises(ValueError) as excinfo:
        run_pdf_review(scanned_pdf, "mask")
    assert PDF_SCANNED_HINT in str(excinfo.value) or "text layer" in str(
        excinfo.value
    )


def test_run_pdf_review_accepts_toc_dot_leaders(tmp_path: Path) -> None:
    toc_pdf = _make_toc_pdf(tmp_path / "protocol.pdf")
    view = run_pdf_review(toc_pdf, "mask")
    assert "John" in view.text
    assert len(view.entities) > 0


def test_iter_model_chunks_covers_full_text() -> None:
    from backend.deid.ops import _MODEL_CHUNK_CHARS, _iter_model_chunks

    text = ("Patient John Doe.\n" * 2000) + "END"
    chunks = _iter_model_chunks(text)
    assert len(chunks) > 1
    assert all(len(chunk) <= _MODEL_CHUNK_CHARS for _, chunk in chunks)
    # First chunk starts at 0; reconstructed coverage reaches the end.
    assert chunks[0][0] == 0
    last_start, last_chunk = chunks[-1]
    assert last_start + len(last_chunk) == len(text)


def test_apply_selected_pdf_redaction_writes_black_box_and_strips_text(
    text_pdf: Path, tmp_path: Path
) -> None:
    from openmed.multimodal import extract_pdf

    view = run_pdf_review(text_pdf, "mask")
    selected = [
        {
            "start": entity.start,
            "end": entity.end,
            "label": entity.label,
            "text": entity.text,
            "replacement": "[REDACTED]",
        }
        for entity in view.entities
    ]
    result = apply_selected_pdf_redaction(text_pdf, "mask", selected)
    assert result.output_path is not None
    out = Path(result.output_path)
    assert out.exists()

    # Text layer must be stripped for every redacted span.
    remaining = extract_pdf(out).text
    for entity in view.entities:
        assert entity.text not in remaining

    # Fidelity must pass (black box present + no residual text).
    assert result.fidelity is not None
    assert result.fidelity["passed"] is True
    for region in result.fidelity["regions"]:
        assert region["residual_text_found"] is False
        assert region["pixels_changed"] is True


def test_apply_selected_pdf_redaction_empty_selection_copies_source(
    text_pdf: Path,
) -> None:
    result = apply_selected_pdf_redaction(text_pdf, "mask", [])
    assert result.output_path is not None
    assert result.applied_entities == []
    # No redaction applied -> fidelity omitted.
    assert result.fidelity is None
    from openmed.multimodal import extract_pdf

    assert extract_pdf(Path(result.output_path)).text == extract_pdf(text_pdf).text