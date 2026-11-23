"""Grading cases from the Exam Mode audit."""
import unicodedata

import pytest

from tuhoc.exams.exam_grading import is_correct


@pytest.mark.parametrize(("question", "answer", "ordered", "expected"), [
    ({"type": "choice", "answer": "Dog"}, "dog", None, True),
    ({"type": "choice", "answer": "Dog"}, "cat", None, False),
    ({"type": "choice", "answer": "Dog"}, None, None, False),
    ({"type": "fill", "answer": "ice cream"}, "  Ice cream ", None, True),
    ({"type": "fill", "answer": "Bà Ngoại"}, "bà ngoại", None, True),
    ({"type": "error", "wrong": "go", "corrected": "goes"}, "goes", None, True),
    ({"type": "error", "wrong": "go", "corrected": "goes"}, "go", None, False),
    ({"type": "true_false", "answer": "True"}, "true", None, True),
    ({"type": "order", "sequence": ["I", "am", "here"]}, "", ["I", "am", "here"], True),
    ({"type": "order", "sequence": ["I", "am", "here"]}, "", ["am", "I", "here"], False),
    ({"type": "order", "sequence": ["I", "am", "here"]}, "", None, False),
])
def test_grading(question, answer, ordered, expected):
    assert is_correct(question, answer, ordered) is expected


@pytest.mark.parametrize(("answer", "expected"), [
    (["IS", " a "], True), (["is", ""], False), (["is"], False), ("is a", False),
])
def test_gaps(answer, expected):
    question = {"type": "sentence_gaps", "gap_answers": ["is", "a"]}
    assert is_correct(question, answer) is expected


@pytest.mark.parametrize(("answer", "expected"), [
    ({"a": "1", "b": "2"}, True), ({"a": "1"}, False), ({"a": "2", "b": "1"}, False),
])
def test_matching(answer, expected):
    question = {"type": "matching", "pairs": [["a", "1"], ["b", "2"]]}
    assert is_correct(question, answer) is expected


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="EX.1: whitespace inside the answer is not normalized")
def test_fill_accepts_repeated_spaces():
    assert is_correct({"type": "fill", "answer": "ice cream"}, "ice  cream")


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="EX.1: canonical Unicode equivalents are not normalized")
def test_fill_accepts_canonically_equivalent_vietnamese():
    nfc = "bà ngoại"
    assert is_correct({"type": "fill", "answer": nfc}, unicodedata.normalize("NFD", nfc))
