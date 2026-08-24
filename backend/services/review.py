"""Review-flow service: detect → refresh → apply."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from backend.deid.constants import (
    DEFAULT_CONFIDENCE_FILTER,
    DEIDENTIFICATION_METHODS,
    HIGH_CONFIDENCE_THRESHOLD,
    MULTIMODAL_HINT,
    PDF_SCANNED_HINT,
)
from backend.deid.ops import (
    apply_selected_docx_redaction,
    apply_selected_pdf_redaction,
    apply_selected_redaction,
    make_session_vault,
    review_entities_to_dicts,
    run_docx_review,
    run_pdf_review,
    run_review,
)
from backend.deid.rules import resolve_custom_recognizer
from backend.store import memory as store


class ServiceError(Exception):
    def __init__(self, message: str, *, status_code: int = 400, hint: str | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.hint = hint


def _ensure_method(method: str) -> str:
    if method not in DEIDENTIFICATION_METHODS:
        raise ServiceError(f"Unsupported method {method!r}")
    return method


def _session_vault(session: dict[str, Any], method: str) -> Any | None:
    if method != "replace":
        return session.get("vault")
    vault = session.get("vault")
    if vault is None:
        vault = make_session_vault()
        session["vault"] = vault
    return vault


def _store_review(session: dict[str, Any], view: Any) -> None:
    session["review_method"] = view.method
    session["review_entities"] = list(view.entities)
    if view.method == "replace" and session.get("vault") is None:
        session["vault"] = make_session_vault()


def review_payload(
    *, session_id: str, filename: str, kind: str, view: Any
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "kind": kind,
        "filename": filename,
        "text": view.text,
        "method": view.method,
        "high_confidence_threshold": HIGH_CONFIDENCE_THRESHOLD,
        "default_confidence_filter": DEFAULT_CONFIDENCE_FILTER,
        "entities": review_entities_to_dicts(view.entities),
    }


def detect_text(
    *,
    text: str,
    method: str,
    filename: str,
    force_terms: list[str],
    protect_terms: list[str],
) -> dict[str, Any]:
    method = _ensure_method(method)
    if not text.strip():
        raise ServiceError("Paste synthetic text to detect.")
    try:
        recognizer = resolve_custom_recognizer(force_terms, protect_terms)
    except ValueError as exc:
        raise ServiceError(str(exc)) from exc

    session_id = store.create_session_id()
    session: dict[str, Any] = {
        "kind": "text",
        "text": text,
        "filename": filename,
        "path": None,
        "vault": make_session_vault() if method == "replace" else None,
        "force_terms": force_terms,
        "protect_terms": protect_terms,
    }
    try:
        view = run_review(
            text,
            method,
            custom_recognizer=recognizer,
            surrogate_vault=_session_vault(session, method),
        )
    except Exception as exc:  # noqa: BLE001
        raise ServiceError(str(exc)) from exc
    _store_review(session, view)
    store.put_session(session_id, session)
    return review_payload(
        session_id=session_id, filename=filename, kind="text", view=view
    )


def detect_docx(
    *,
    file_bytes: bytes,
    filename: str,
    method: str,
    force_terms: list[str],
    protect_terms: list[str],
) -> dict[str, Any]:
    method = _ensure_method(method)
    if Path(filename).suffix.lower() != ".docx":
        raise ServiceError("Only .docx uploads are supported (not legacy .doc).")
    try:
        recognizer = resolve_custom_recognizer(force_terms, protect_terms)
    except ValueError as exc:
        raise ServiceError(str(exc)) from exc

    tmp_dir = Path(tempfile.mkdtemp(prefix="openmed-deid-upload-"))
    safe_name = Path(filename).name or "upload.docx"
    source = tmp_dir / safe_name
    source.write_bytes(file_bytes)

    session_id = store.create_session_id()
    session: dict[str, Any] = {
        "kind": "docx",
        "text": "",
        "filename": safe_name,
        "path": str(source),
        "vault": make_session_vault() if method == "replace" else None,
        "force_terms": force_terms,
        "protect_terms": protect_terms,
    }
    try:
        view = run_docx_review(
            source,
            method,
            custom_recognizer=recognizer,
            surrogate_vault=_session_vault(session, method),
        )
    except Exception as exc:  # noqa: BLE001
        message = str(exc)
        hint = None
        if "python-docx" in message or "multimodal" in message.lower():
            message = f"{message}\n{MULTIMODAL_HINT}"
            hint = MULTIMODAL_HINT
        raise ServiceError(message, hint=hint) from exc

    session["text"] = view.text
    _store_review(session, view)
    store.put_session(session_id, session)
    return review_payload(
        session_id=session_id, filename=safe_name, kind="docx", view=view
    )


def detect_pdf(
    *,
    file_bytes: bytes,
    filename: str,
    method: str,
    force_terms: list[str],
    protect_terms: list[str],
) -> dict[str, Any]:
    method = _ensure_method(method)
    if Path(filename).suffix.lower() != ".pdf":
        raise ServiceError("Only .pdf uploads are supported.")
    try:
        recognizer = resolve_custom_recognizer(force_terms, protect_terms)
    except ValueError as exc:
        raise ServiceError(str(exc)) from exc

    tmp_dir = Path(tempfile.mkdtemp(prefix="openmed-deid-upload-"))
    safe_name = Path(filename).name or "upload.pdf"
    source = tmp_dir / safe_name
    source.write_bytes(file_bytes)

    session_id = store.create_session_id()
    session: dict[str, Any] = {
        "kind": "pdf",
        "text": "",
        "filename": safe_name,
        "path": str(source),
        "vault": make_session_vault() if method == "replace" else None,
        "force_terms": force_terms,
        "protect_terms": protect_terms,
    }
    try:
        view = run_pdf_review(
            source,
            method,
            custom_recognizer=recognizer,
            surrogate_vault=_session_vault(session, method),
        )
    except Exception as exc:  # noqa: BLE001
        message = str(exc)
        hint = None
        if "scanned" in message.lower() or "text layer" in message.lower():
            message = f"{message}\n{PDF_SCANNED_HINT}"
            hint = PDF_SCANNED_HINT
        raise ServiceError(message, hint=hint) from exc

    session["text"] = view.text
    _store_review(session, view)
    store.put_session(session_id, session)
    return review_payload(
        session_id=session_id, filename=safe_name, kind="pdf", view=view
    )


def refresh_review(
    *,
    session_id: str,
    method: str,
    force_terms: list[str] | None,
    protect_terms: list[str] | None,
    rules_provided: bool,
) -> dict[str, Any]:
    method = _ensure_method(method)
    session = store.get_session(session_id)
    if session is None:
        raise ServiceError("Review session expired. Upload again.", status_code=404)

    if not rules_provided:
        force_terms = list(session.get("force_terms") or [])
        protect_terms = list(session.get("protect_terms") or [])
    assert force_terms is not None and protect_terms is not None
    try:
        recognizer = resolve_custom_recognizer(force_terms, protect_terms)
    except ValueError as exc:
        raise ServiceError(str(exc)) from exc
    session["force_terms"] = force_terms
    session["protect_terms"] = protect_terms
    try:
        view = run_review(
            str(session["text"]),
            method,
            custom_recognizer=recognizer,
            surrogate_vault=_session_vault(session, method),
        )
    except Exception as exc:  # noqa: BLE001
        raise ServiceError(str(exc)) from exc
    _store_review(session, view)
    return review_payload(
        session_id=session_id,
        filename=str(session["filename"]),
        kind=str(session["kind"]),
        view=view,
    )


def apply_redaction(
    *,
    session_id: str,
    method: str,
    selected_spans: list[dict[str, Any]],
    force_terms: list[str] | None,
    protect_terms: list[str] | None,
    rules_provided: bool,
) -> dict[str, Any]:
    method = _ensure_method(method)
    session = store.get_session(session_id)
    if session is None:
        raise ServiceError("Review session expired. Upload again.", status_code=404)

    if not rules_provided:
        force_terms = list(session.get("force_terms") or [])
        protect_terms = list(session.get("protect_terms") or [])
    assert force_terms is not None and protect_terms is not None
    try:
        recognizer = resolve_custom_recognizer(force_terms, protect_terms)
    except ValueError as exc:
        raise ServiceError(str(exc)) from exc
    session["force_terms"] = force_terms
    session["protect_terms"] = protect_terms

    try:
        vault = _session_vault(session, method)
        review_entities = session.get("review_entities")
        if session.get("review_method") != method:
            review_entities = None
        if session["kind"] == "docx" and session.get("path"):
            selective = apply_selected_docx_redaction(
                session["path"],
                method,
                selected_spans,
                custom_recognizer=recognizer,
                surrogate_vault=vault,
                review_entities=review_entities,
            )
        elif session["kind"] == "pdf" and session.get("path"):
            selective = apply_selected_pdf_redaction(
                session["path"],
                method,
                selected_spans,
                custom_recognizer=recognizer,
                surrogate_vault=vault,
                review_entities=review_entities,
            )
        else:
            selective = apply_selected_redaction(
                str(session["text"]),
                method,
                selected_spans,
                custom_recognizer=recognizer,
                surrogate_vault=vault,
                review_entities=review_entities,
            )
    except Exception as exc:  # noqa: BLE001
        message = str(exc)
        hint = None
        if "scanned" in message.lower() or "text layer" in message.lower():
            message = f"{message}\n{PDF_SCANNED_HINT}"
            hint = PDF_SCANNED_HINT
        elif "python-docx" in message or "multimodal" in message.lower():
            message = f"{message}\n{MULTIMODAL_HINT}"
            hint = MULTIMODAL_HINT
        raise ServiceError(message, hint=hint) from exc

    response: dict[str, Any] = {
        "text": selective.deidentified_text,
        "original_text": str(session["text"]),
        "filename": str(session["filename"]),
        "applied_count": len(selective.applied_entities),
        "session_kind": session["kind"],
    }
    if selective.fidelity is not None:
        response["fidelity"] = selective.fidelity
    if selective.output_path:
        _token, download_url = store.put_download(Path(selective.output_path))
        response["download_filename"] = Path(selective.output_path).name
        response["download_url"] = download_url
    return response
