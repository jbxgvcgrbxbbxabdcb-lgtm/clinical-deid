"""Tests for document-aware openmed validation patch."""

from __future__ import annotations

import pytest
from openmed.utils.validation import validate_input

from backend.deid.openmed_validation import contains_suspicious_content


def test_dot_leaders_are_not_suspicious() -> None:
    text = "目录 标题页 " + ("." * 136) + " 12\nPatient John Doe"
    assert contains_suspicious_content(text) is False
    assert validate_input(text) == text.strip()


def test_repeated_letters_still_suspicious() -> None:
    text = "A" * 150
    assert contains_suspicious_content(text) is True
    with pytest.raises(ValueError, match="suspicious content"):
        validate_input(text)


def test_control_char_runs_still_suspicious() -> None:
    text = "hello" + ("\x01" * 12) + "world"
    assert contains_suspicious_content(text) is True
