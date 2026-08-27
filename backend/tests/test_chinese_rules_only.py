"""Chinese-dominant notes skip the EN model; rules own CJK (+ shared patterns)."""

from __future__ import annotations

from backend.deid.ops import run_review
from backend.deid.rules import resolve_custom_recognizer
from backend.deid.script_policy import is_chinese_dominant, is_cjk_heavy_span


def test_chinese_note_is_dominant() -> None:
    text = "患者就职于某某医疗科技有限公司，住址：北京市朝阳区建国路88号。"
    assert is_chinese_dominant(text)
    assert not is_chinese_dominant(
        "Patient John Doe works at Acme Biotech Inc in San Francisco."
    )


def test_chinese_spans_come_from_rules_not_model_labels() -> None:
    text = (
        "患者就职于某某医疗科技有限公司，邮箱：zhang.san@example.com.cn，"
        "住址：北京市朝阳区建国路88号。所属单位：北京大学第一医院。"
    )
    view = run_review(text, "mask", custom_recognizer=resolve_custom_recognizer())
    labels_and_texts = {(e.label, e.text) for e in view.entities}
    assert any(t == "zhang.san@example.com.cn" for _, t in labels_and_texts)
    assert any("有限公司" in t for _, t in labels_and_texts)
    assert any("建国路" in t or "朝阳区" in t for _, t in labels_and_texts)
    for label, span in labels_and_texts:
        if is_cjk_heavy_span(span):
            assert label in {"company_name", "street_address", "email", "OTHER"}


def test_chinese_dominant_skips_model_loader(monkeypatch) -> None:
    """Long CN notes must not invoke openmed NER (avoids Docker OOM)."""
    calls: list[str] = []

    def boom(*_a, **_k):  # pragma: no cover - should never run
        calls.append("deidentify")
        raise AssertionError("model should be skipped for Chinese-dominant text")

    monkeypatch.setattr("backend.deid.ops.deidentify", boom)
    text = "患者就职于某某医疗科技有限公司，住址：北京市朝阳区建国路88号。" * 50
    assert is_chinese_dominant(text)
    view = run_review(text, "mask", custom_recognizer=resolve_custom_recognizer())
    assert calls == []
    assert any("有限公司" in e.text for e in view.entities)


def test_english_review_keeps_latin_model_hits() -> None:
    text = (
        "Patient Jane Doe was seen by Dr. Alice Smith. "
        "Reach her at jane.doe@example.com or (415) 555-0142."
    )
    view = run_review(text, "mask", custom_recognizer=resolve_custom_recognizer())
    texts = {e.text for e in view.entities}
    assert "jane.doe@example.com" in texts
    assert not any(is_cjk_heavy_span(e.text) for e in view.entities)


def test_mixed_note_strips_model_cjk_then_adds_rules() -> None:
    text = (
        "Referral from Pacific Heart Center. "
        "中文单位：某某医疗科技有限公司。Email nina.w@example.com."
    )
    view = run_review(text, "mask", custom_recognizer=resolve_custom_recognizer())
    texts = {e.text for e in view.entities}
    assert "nina.w@example.com" in texts or any("acme.com" in t for t in texts)
    assert any("有限公司" in t for t in texts)
    for entity in view.entities:
        if is_cjk_heavy_span(entity.text):
            assert entity.label in {"company_name", "street_address", "email", "OTHER"}
