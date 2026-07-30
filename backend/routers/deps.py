"""HTTP parsing helpers for API routes."""

from __future__ import annotations

import json
from typing import Any


def parse_terms_json(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "force_terms/protect_terms must be a JSON array of strings"
        ) from exc
    if not isinstance(data, list):
        raise ValueError("force_terms/protect_terms must be a JSON array of strings")
    return [str(item) for item in data]


def parse_selected_spans(raw: str | list[Any] | None) -> list[dict[str, Any]]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        data = raw
    else:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("selected_spans must be a JSON array") from exc
    if not isinstance(data, list):
        raise ValueError("selected_spans must be a JSON array")
    spans: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("selected_spans entries must be objects")
        spans.append(item)
    return spans


def rules_from_payload(payload: dict[str, Any] | None) -> tuple[list[str], list[str]]:
    payload = payload or {}
    force_terms = payload.get("force_terms") or []
    protect_terms = payload.get("protect_terms") or []
    if not isinstance(force_terms, list) or not isinstance(protect_terms, list):
        raise ValueError("force_terms and protect_terms must be arrays")
    return [str(t) for t in force_terms], [str(t) for t in protect_terms]
