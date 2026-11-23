"""Exam navigation and progress regressions exercised without opening a window."""
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
pygame = pytest.importorskip("pygame")

from tuhoc.exams.exam_pygame import ExamUI, VIRTUAL


@pytest.fixture
def exam(tmp_path):
    ui = ExamUI(tmp_path)
    ui.mode = "exam"
    ui.exam = {"questions": [
        dict(id="c1", type="choice", prompt="p", options=["a", "b"], answer="a"),
        dict(id="g1", type="sentence_gaps", prompt="{1} {2}", gap_answers=["x", "y"]),
        dict(id="m1", type="matching", prompt="p", pairs=[["a", "1"], ["b", "2"]]),
        dict(id="o1", type="order", prompt="p", sequence=["I", "am", "ok"]),
        dict(id="f1", type="fill", prompt="p", answer="dog"),
    ]}
    return ui


def assert_navigation(ui, answered):
    count = len(ui.exam["questions"])
    unanswered = [index for index in range(count) if index not in answered]
    ui._set_nav_filter("answered")
    assert ui._nav_indices() == answered
    ui._set_nav_filter("unanswered")
    assert ui._nav_indices() == unanswered
    assert ui._unanswered_indices() == unanswered


def test_initial_exam_has_no_answers(exam):
    assert_navigation(exam, [])


def test_gap_with_one_value_counts_as_started(exam):
    gap = exam.exam["questions"][1]
    exam._gap_text(gap, "x")
    assert exam.answers[gap["id"]] == ["x", ""]
    assert_navigation(exam, [1])
    assert not exam._is_correct(gap)


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="EX.2: an empty gap list still counts as answered")
def test_gap_returns_to_unanswered_when_last_value_is_erased(exam):
    gap = exam.exam["questions"][1]
    exam._gap_text(gap, "x")
    exam._gap_key(gap, SimpleNamespace(key=pygame.K_BACKSPACE))
    assert exam.answers[gap["id"]] == ["", ""]
    assert_navigation(exam, [])


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="EX.2: matching counts partial pairs as answered")
def test_matching_requires_all_pairs(exam):
    exam._select_match_left("m1", "a")
    exam._select_match_right("m1", "1")
    assert_navigation(exam, [])


def test_completed_matching_counts_as_answered(exam):
    for left, right in (("a", "1"), ("b", "2")):
        exam._select_match_left("m1", left)
        exam._select_match_right("m1", right)
    assert_navigation(exam, [2])


def test_order_requires_all_words(exam):
    order = exam.exam["questions"][3]
    for word in ("I", "am"):
        exam._pick_order(order, word)
    assert exam.order_inputs["o1"] == ["I", "am"]
    assert_navigation(exam, [])
    exam._pick_order(order, "ok")
    assert_navigation(exam, [3])


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="EX.2: whitespace-only fill counts as answered")
def test_whitespace_only_fill_is_unanswered(exam):
    exam.answers["f1"] = "   "
    assert_navigation(exam, [])


def test_whitespace_only_fill_is_graded_incorrect(exam):
    exam.answers["f1"] = "   "
    assert not exam._is_correct(exam.exam["questions"][4])


def progress_label(exam, monkeypatch):
    pygame.font.init()
    for field, size in (("font", 22), ("bold", 24), ("big", 36), ("small", 18)):
        setattr(exam, field, pygame.font.Font(None, size))
    labels = []

    def record_text(_surface, label, *_args, **_kwargs):
        labels.append(label)
        return 0

    monkeypatch.setattr(exam, "_text", record_text)
    exam._draw_exam(pygame.Surface(VIRTUAL))
    return next(label for label in labels if label.startswith("Đã trả lời "))


def test_progress_counts_completed_choice(exam, monkeypatch):
    exam.answers["c1"] = "a"
    assert progress_label(exam, monkeypatch) == "Đã trả lời 1/5 câu"


@pytest.mark.xfail(strict=True, raises=AssertionError, reason="EX.2: progress counts truthy drafts")
def test_progress_excludes_empty_and_incomplete_answers(exam, monkeypatch):
    _, gap, _, order, _ = exam.exam["questions"]
    exam._gap_text(gap, "x")
    exam._gap_key(gap, SimpleNamespace(key=pygame.K_BACKSPACE))
    exam._select_match_left("m1", "a")
    exam._select_match_right("m1", "1")
    for word in ("I", "am"):
        exam._pick_order(order, word)
    exam.answers["f1"] = "   "
    assert progress_label(exam, monkeypatch) == "Đã trả lời 0/5 câu"
