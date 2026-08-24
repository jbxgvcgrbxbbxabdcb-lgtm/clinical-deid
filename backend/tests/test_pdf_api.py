"""End-to-end API test for the PDF detect → apply → download flow."""

from __future__ import annotations

from pathlib import Path

import pymupdf
from fastapi.testclient import TestClient

from backend.app import create_app


def _pdf_bytes(text: str = "Patient John Doe (MRN 123456) seen 01/15/2023.") -> bytes:
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 100), text, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


def test_pdf_detect_apply_download_flow() -> None:
    client = TestClient(create_app())

    # 1. Detect entities from a PDF upload
    files = {"file": ("note.pdf", _pdf_bytes(), "application/pdf")}
    detect = client.post("/api/detect/pdf", files=files, data={"method": "mask"})
    assert detect.status_code == 200, detect.text
    payload = detect.json()
    assert payload["kind"] == "pdf"
    assert len(payload["entities"]) > 0
    session_id = payload["session_id"]

    # 2. Apply redaction to all detected spans
    selected = [
        {
            "id": entity["id"],
            "start": entity["start"],
            "end": entity["end"],
            "label": entity["label"],
            "text": entity["text"],
            "confidence": entity["confidence"],
            "replacement": "[REDACTED]",
        }
        for entity in payload["entities"]
    ]
    apply_resp = client.post(
        "/api/apply",
        json={
            "session_id": session_id,
            "method": "mask",
            "selected_spans": selected,
        },
    )
    assert apply_resp.status_code == 200, apply_resp.text
    result = apply_resp.json()
    assert result["session_kind"] == "pdf"
    assert result["download_url"]
    assert result["fidelity"]["passed"] is True

    # 3. Download the redacted PDF
    dl = client.get(result["download_url"])
    assert dl.status_code == 200
    assert dl.headers["content-type"].startswith("application/pdf")
    out_path = Path("/tmp") / "redacted_api_test.pdf"
    out_path.write_bytes(dl.content)
    text = ""
    with pymupdf.open(out_path) as out_doc:
        text = out_doc[0].get_text()
    out_path.unlink(missing_ok=True)
    for entity in payload["entities"]:
        assert entity["text"].strip() not in text


def test_scanned_pdf_returns_clear_error() -> None:
    client = TestClient(create_app())

    doc = pymupdf.open()
    page = doc.new_page()
    page.draw_rect(pymupdf.Rect(0, 0, 100, 100), color=(0, 0, 0), fill=(0.5, 0.5, 0.5))
    doc.save("/tmp/scan_no_text.pdf")
    doc.close()
    # Re-open as binary fixture path-less: use bytes via BytesIO.
    from backend.services import review as service

    try:
        service.detect_pdf(
            file_bytes=Path("/tmp/scan_no_text.pdf").read_bytes(),
            filename="scan_no_text.pdf",
            method="mask",
            force_terms=[],
            protect_terms=[],
        )
        assert False, "expected ServiceError for scanned PDF"
    except service.ServiceError as exc:
        assert "scanned" in exc.message or "text layer" in exc.message
    finally:
        Path("/tmp/scan_no_text.pdf").unlink(missing_ok=True)