"""OOXML helpers: extract and redact Word text boxes (w:txbxContent).

python-docx / openmed.extract_docx skip DrawingML/VML text frames. This module
appends those spans to the review text and can write replacements back into the
docx package XML so detection and download stay aligned.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
TXBX = f"{{{W_NS}}}txbxContent"
T_TAG = f"{{{W_NS}}}t"
P_TAG = f"{{{W_NS}}}p"

ET.register_namespace("w", W_NS)
ET.register_namespace("xml", XML_NS)

# Parts that may contain text boxes (body + headers/footers).
_PART_PREFIXES = ("word/document.xml", "word/header", "word/footer")


@dataclass(frozen=True)
class TextboxRegion:
    """One w:txbxContent block mapped into the enriched review text."""

    part_name: str
    box_index: int
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class EnrichedDocx:
    """openmed body text plus appended text-box content."""

    text: str
    base_length: int
    textboxes: tuple[TextboxRegion, ...]


def _is_candidate_part(name: str) -> bool:
    return any(name == prefix or name.startswith(prefix) for prefix in _PART_PREFIXES)


def _local_textbox_text(box: ET.Element) -> str:
    """Approximate Word reading order: paragraph texts joined by newlines."""
    paragraphs: list[str] = []
    for paragraph in box.iter(P_TAG):
        chunks = [
            (node.text or "")
            for node in paragraph.iter(T_TAG)
            if node is not None
        ]
        # Only direct-ish w:t under this paragraph tree (iter is fine for nested).
        para_text = "".join(chunks)
        if para_text:
            paragraphs.append(para_text)
    if paragraphs:
        return "\n".join(paragraphs)
    return "".join((node.text or "") for node in box.iter(T_TAG))


def iter_textbox_texts(path: str | Path) -> list[tuple[str, int, str]]:
    """Return (part_name, box_index, text) for every non-empty text box."""
    source = Path(path)
    found: list[tuple[str, int, str]] = []
    with zipfile.ZipFile(source) as archive:
        for name in archive.namelist():
            if not _is_candidate_part(name) or not name.endswith(".xml"):
                continue
            root = ET.fromstring(archive.read(name))
            boxes = list(root.iter(TXBX))
            for index, box in enumerate(boxes):
                text = _local_textbox_text(box)
                if text:
                    found.append((name, index, text))
    return found


def enrich_docx_text(base_text: str, path: str | Path) -> EnrichedDocx:
    """Append text-box strings after openmed's extracted body text."""
    base = base_text or ""
    pieces: list[str] = []
    regions: list[TextboxRegion] = []
    cursor = 0
    if base:
        pieces.append(base)
        cursor = len(base)
    for part_name, box_index, text in iter_textbox_texts(path):
        if cursor > 0:
            pieces.append("\n")
            cursor += 1
        start = cursor
        pieces.append(text)
        cursor += len(text)
        regions.append(
            TextboxRegion(
                part_name=part_name,
                box_index=box_index,
                text=text,
                start=start,
                end=cursor,
            )
        )
    return EnrichedDocx(
        text="".join(pieces),
        base_length=len(base),
        textboxes=tuple(regions),
    )


def load_enriched_docx(path: str | Path, base_text: str | None = None) -> EnrichedDocx:
    """Build enriched text from a docx path (optionally reusing openmed text)."""
    if base_text is None:
        from openmed.multimodal import extract_docx

        base_text = extract_docx(path).text
    return enrich_docx_text(base_text, path)


def _apply_edits(text: str, edits: Sequence[tuple[int, int, str]]) -> str:
    ordered = sorted(edits, key=lambda item: (item[0], -item[1]), reverse=True)
    output = text
    cursor = len(output) + 1
    for start, end, replacement in ordered:
        if start < 0 or end > len(output) or start > end or end > cursor:
            continue
        output = output[:start] + replacement + output[end:]
        cursor = start
    return output


def _rewrite_textbox_element(box: ET.Element, new_text: str) -> None:
    """Replace all w:t content in a text box with ``new_text`` (first node keeps it)."""
    nodes = list(box.iter(T_TAG))
    if not nodes:
        # Create a minimal paragraph + run + t if the box is empty structurally.
        paragraph = ET.SubElement(box, P_TAG)
        run = ET.SubElement(paragraph, f"{{{W_NS}}}r")
        node = ET.SubElement(run, T_TAG)
        node.text = new_text
        if new_text.startswith(" ") or new_text.endswith(" ") or "\n" in new_text:
            node.set(f"{{{XML_NS}}}space", "preserve")
        return
    nodes[0].text = new_text
    if new_text.startswith(" ") or new_text.endswith(" ") or "\n" in new_text:
        nodes[0].set(f"{{{XML_NS}}}space", "preserve")
    for node in nodes[1:]:
        node.text = ""


def apply_textbox_redactions(
    source_path: str | Path,
    output_path: str | Path,
    textboxes: Sequence[TextboxRegion],
    spans: Sequence[Any],
) -> Path:
    """Copy docx and rewrite text-box XML for spans that fall in textbox regions.

    ``spans`` entries are mappings/objects with start/end and replacement /
    redacted_text.
    """
    source = Path(source_path)
    output = Path(output_path)
    if not textboxes:
        if source.resolve() != output.resolve():
            output.write_bytes(source.read_bytes())
        return output

    edits_by_box: dict[tuple[str, int], list[tuple[int, int, str]]] = {}
    for span in spans:
        if hasattr(span, "start"):
            start = int(span.start)
            end = int(span.end)
            replacement = str(
                getattr(span, "replacement", None)
                or getattr(span, "redacted_text", None)
                or ""
            )
        else:
            start = int(span["start"])
            end = int(span["end"])
            replacement = str(
                span.get("replacement")
                if span.get("replacement") is not None
                else span.get("redacted_text")
                if span.get("redacted_text") is not None
                else ""
            )
        for region in textboxes:
            if end <= region.start or start >= region.end:
                continue
            local_start = max(start, region.start) - region.start
            local_end = min(end, region.end) - region.start
            # Only put the replacement on the first overlapping region piece.
            local_replacement = replacement if start >= region.start else ""
            key = (region.part_name, region.box_index)
            edits_by_box.setdefault(key, []).append(
                (local_start, local_end, local_replacement)
            )

    if not edits_by_box:
        if source.resolve() != output.resolve():
            output.write_bytes(source.read_bytes())
        return output

    buffer = io.BytesIO()
    with zipfile.ZipFile(source, "r") as zin, zipfile.ZipFile(
        buffer, "w", compression=zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename in {part for part, _ in edits_by_box}:
                root = ET.fromstring(data)
                boxes = list(root.iter(TXBX))
                for (part_name, box_index), edits in edits_by_box.items():
                    if part_name != item.filename:
                        continue
                    if box_index < 0 or box_index >= len(boxes):
                        continue
                    box = boxes[box_index]
                    original = _local_textbox_text(box)
                    updated = _apply_edits(original, edits)
                    _rewrite_textbox_element(box, updated)
                data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            zout.writestr(item, data)
    output.write_bytes(buffer.getvalue())
    return output


def _span_offsets(span: Any) -> tuple[int, int]:
    """Read start/end from a ReviewEntity or mapping (start may be 0)."""
    if hasattr(span, "start") and hasattr(span, "end"):
        return int(span.start), int(span.end)
    return int(span["start"]), int(span["end"])


def partition_docx_spans(
    enriched: EnrichedDocx, spans: Sequence[Any]
) -> tuple[list[Any], list[Any]]:
    """Split spans into openmed body spans vs text-box spans."""
    body: list[Any] = []
    boxes: list[Any] = []
    base = enriched.base_length
    for span in spans:
        start, end = _span_offsets(span)
        if end <= base:
            body.append(span)
        elif start >= base:
            boxes.append(span)
        else:
            # Rare cross-boundary: keep body portion for openmed; box write skips.
            body.append(span)
    return body, boxes
