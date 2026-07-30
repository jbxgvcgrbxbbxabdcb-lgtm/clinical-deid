"""Review API: sample / detect / refresh / apply / download."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from backend.routers import deps
from backend.deid.constants import SYNTHETIC_CLINICAL_TEXT
from backend.services import review as review_service
from backend.services.review import ServiceError
from backend.store import memory as store

router = APIRouter(prefix="/api", tags=["review"])


def _error(exc: ServiceError | ValueError) -> JSONResponse:
    if isinstance(exc, ServiceError):
        body: dict[str, Any] = {"error": exc.message, "kind": "error"}
        if exc.hint:
            body["hint"] = exc.hint
        return JSONResponse(body, status_code=exc.status_code)
    return JSONResponse({"error": str(exc), "kind": "error"}, status_code=400)


@router.get("/sample")
def sample_text() -> dict[str, str]:
    return {"text": SYNTHETIC_CLINICAL_TEXT}


@router.post("/detect/text")
async def detect_text(payload: dict[str, Any]) -> JSONResponse:
    try:
        force, protect = deps.rules_from_payload(payload)
        data = review_service.detect_text(
            text=str(payload.get("text") or ""),
            method=str(payload.get("method") or "mask"),
            filename=str(payload.get("filename") or "synthetic_note.txt"),
            force_terms=force,
            protect_terms=protect,
        )
    except (ServiceError, ValueError) as exc:
        return _error(exc)
    return JSONResponse(data)


@router.post("/detect/docx")
async def detect_docx(
    file: UploadFile = File(...),
    method: str = Form("mask"),
    force_terms: str = Form("[]"),
    protect_terms: str = Form("[]"),
) -> JSONResponse:
    try:
        force = deps.parse_terms_json(force_terms)
        protect = deps.parse_terms_json(protect_terms)
        data = review_service.detect_docx(
            file_bytes=await file.read(),
            filename=file.filename or "upload.docx",
            method=method,
            force_terms=force,
            protect_terms=protect,
        )
    except (ServiceError, ValueError) as exc:
        return _error(exc)
    return JSONResponse(data)


@router.post("/review/refresh")
async def review_refresh(payload: dict[str, Any]) -> JSONResponse:
    try:
        force, protect = deps.rules_from_payload(payload)
        data = review_service.refresh_review(
            session_id=str(payload.get("session_id") or ""),
            method=str(payload.get("method") or "mask"),
            force_terms=force,
            protect_terms=protect,
            rules_provided=("force_terms" in payload or "protect_terms" in payload),
        )
    except (ServiceError, ValueError) as exc:
        return _error(exc)
    return JSONResponse(data)


@router.post("/apply")
async def apply_selected(payload: dict[str, Any]) -> JSONResponse:
    try:
        selected = deps.parse_selected_spans(payload.get("selected_spans"))
        force, protect = deps.rules_from_payload(payload)
        data = review_service.apply_redaction(
            session_id=str(payload.get("session_id") or ""),
            method=str(payload.get("method") or "mask"),
            selected_spans=selected,
            force_terms=force,
            protect_terms=protect,
            rules_provided=("force_terms" in payload or "protect_terms" in payload),
        )
    except (ServiceError, ValueError) as exc:
        return _error(exc)
    return JSONResponse(data)


@router.get("/download/{token}", response_model=None)
def download(token: str) -> FileResponse | JSONResponse:
    path = store.get_download(token)
    if path is None:
        return JSONResponse(
            {"error": "Download expired or not found.", "kind": "error"},
            status_code=404,
        )
    return FileResponse(
        path,
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        filename=path.name,
    )
