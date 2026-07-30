"""In-memory session and download token store (ephemeral process state)."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

_SESSIONS: dict[str, dict[str, Any]] = {}
_DOWNLOADS: dict[str, Path] = {}


def create_session_id() -> str:
    return uuid.uuid4().hex


def put_session(session_id: str, session: dict[str, Any]) -> None:
    _SESSIONS[session_id] = session


def get_session(session_id: str) -> dict[str, Any] | None:
    return _SESSIONS.get(session_id)


def put_download(path: Path) -> tuple[str, str]:
    token = uuid.uuid4().hex
    _DOWNLOADS[token] = path
    return token, f"/api/download/{token}"


def get_download(token: str) -> Path | None:
    path = _DOWNLOADS.get(token)
    if path is None or not path.is_file():
        return None
    return path
