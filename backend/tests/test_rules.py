"""Built-in deny patterns for email / org / address coverage."""

from __future__ import annotations

from openmed.core.custom_recognizer import CustomRecognizer

from backend.deid.constants import DEFAULT_CONFIDENCE_FILTER, DETECTION_CONFIDENCE_THRESHOLD
from backend.deid.ops import deidentify_kwargs
from backend.deid.rules import build_custom_recognizer, resolve_custom_recognizer


def _deny_pattern_labels(config: dict) -> set[str]:
    patterns = config["deny"]["patterns"]
    return {entry["label"] for entry in patterns}


def _matches(config: dict, text: str) -> list[tuple[str, str]]:
    recognizer = CustomRecognizer.from_config(config)
    return [(m.label, text[m.start : m.end]) for m in recognizer.deny_matches(text)]


def test_builtin_patterns_present_without_user_terms() -> None:
    config = build_custom_recognizer([], [])
    assert config is not None
    labels = _deny_pattern_labels(config)
    assert "email" in labels
    assert "company_name" in labels
    assert "street_address" in labels
    assert "date" in labels


def test_chinese_date_rules_catch_common_forms() -> None:
    config = build_custom_recognizer([], [])
    assert config is not None
    text = (
        "方案日期 2023 年 12 月 14 日；修订于2022年3月7日。"
        "随访安排在 3 月 15 日。另见 2019/06/15 与 2020-01-02。"
    )
    date_hits = [span for label, span in _matches(config, text) if label == "date"]
    assert any("2023 年 12 月 14 日" in span for span in date_hits)
    assert any("2022年3月7日" in span for span in date_hits)
    assert any("3 月 15 日" in span for span in date_hits)
    assert "2019/06/15" in date_hits
    assert "2020-01-02" in date_hits


def test_chinese_date_rules_reject_implausible_numeric() -> None:
    config = build_custom_recognizer([], [])
    assert config is not None
    matched = _matches(config, "版本号片段 2020.38.15 不是日期")
    assert not any(label == "date" for label, _ in matched)


def test_builtin_patterns_catch_previous_misses() -> None:
    config = build_custom_recognizer([], [])
    assert config is not None
    text = (
        "Mail admin@localhost. Employer: Tencent Holdings Ltd. "
        "Address: 北京市朝阳区建国路88号. Unit: 某某医疗科技有限公司."
    )
    matched = _matches(config, text)
    texts = {span for _, span in matched}
    assert "admin@localhost" in texts
    assert "Tencent Holdings Ltd." in texts or "Tencent Holdings Ltd" in texts
    assert any("建国路88号" in span or "北京市朝阳区建国路88号" in span for span in texts)
    assert any("有限公司" in span for span in texts)


def test_chinese_address_rule_ignores_instructional_false_positives() -> None:
    """Phrases with 号/路 must not be treated as street_address."""
    config = build_custom_recognizer([], [])
    assert config is not None
    false_positives = [
        "所有的脚注必须左对齐以减号开头",
        "包括程序路径和名称",
        "所有列表将按照参与者随机号和参与者分组先排序",
        "频率和百分率的左括号之间留一个空格",
    ]
    for phrase in false_positives:
        matched = _matches(config, phrase)
        assert matched == [], f"unexpected hits for {phrase!r}: {matched}"

    real = "联系地址：北京市朝阳区建国路88号SOHO现代城A座1201室"
    real_hits = [span for label, span in _matches(config, real) if label == "street_address"]
    assert real_hits
    assert any("建国路88号" in span for span in real_hits)

    digit_hao = _matches(config, "请寄到门牌 88号 签收")
    assert any(
        label == "street_address" and "88号" in span for label, span in digit_hao
    )


def test_force_and_protect_merge_with_builtins() -> None:
    config = build_custom_recognizer(["Ward Phoenix"], ["Mercy Trial"])
    assert config is not None
    terms = [entry["term"] for entry in config["deny"]["terms"]]
    assert "Ward Phoenix" in terms
    assert "Mercy Trial" in config["allow"]["terms"]
    assert config["deny"]["patterns"]  # builtins kept


def test_protect_suppresses_overlapping_builtin_match() -> None:
    config = build_custom_recognizer([], ["admin@localhost"])
    assert config is not None
    matched = _matches(config, "Contact admin@localhost please")
    assert matched == []


def test_resolve_always_returns_recognizer() -> None:
    assert resolve_custom_recognizer() is not None


def test_detection_threshold_lowered_for_review_defaults() -> None:
    assert DETECTION_CONFIDENCE_THRESHOLD == 0.5
    assert DEFAULT_CONFIDENCE_FILTER == 0.5
    kwargs = deidentify_kwargs("mask")
    assert kwargs["confidence_threshold"] == 0.5
