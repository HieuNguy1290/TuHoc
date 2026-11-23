"""Exam bank validation, selection, and persistence using synthetic data."""
from collections import Counter
import json
import random

import pytest

from tuhoc.exams.exam_bank import ExamBank, validate_question


def choice(number=1, difficulty=1, **overrides):
    question = dict(id=f"q{number}", type="choice", grade="3", lesson="L1",
                    difficulty=difficulty, prompt=f"Question {number}",
                    options=["a", "b"], answer="a", subject="tieng_anh")
    return {**question, **overrides}


@pytest.mark.parametrize("overrides", [
    {}, dict(type="sentence_gaps", prompt="A {1} B {2}", gap_answers=["x", "y"]),
])
def test_valid_question(overrides):
    question = choice(**overrides)
    assert validate_question(question) == question


@pytest.mark.parametrize("overrides", [
    dict(answer="c"), dict(options=["a", "A"]), dict(options=list("abcde")),
    dict(difficulty=6), dict(difficulty="abc"),
    dict(type="sentence_gaps", prompt="A {1} B {3}", gap_answers=["x", "y"]),
    dict(type="order", sequence=["a", "a"]),
    dict(type="matching", pairs=[["a", "1"], ["b", "2"]], matching_mode="Chữ - Chữ"),
    dict(type="matching", pairs=[["a", "1"]], matching_mode="Chữ ↔ Chữ"),
    dict(type="dropdown"),
    pytest.param(dict(difficulty=None), marks=pytest.mark.xfail(
        strict=True, raises=TypeError, reason="EX.3: None difficulty raises TypeError")),
    pytest.param(dict(difficulty=2.7), marks=pytest.mark.xfail(
        strict=True, raises=pytest.fail.Exception, reason="EX.3: fractional difficulty is truncated")),
    pytest.param(dict(type="order", sequence=["a", "a "]), marks=pytest.mark.xfail(
        strict=True, raises=pytest.fail.Exception, reason="EX.3: order duplicates survive whitespace")),
])
def test_invalid_question(overrides):
    with pytest.raises(ValueError):
        validate_question({**choice(), **overrides})


def test_missing_audio_is_invalid(tmp_path):
    with pytest.raises(ValueError):
        validate_question(choice(type="listening_choice", audio=str(tmp_path / "missing.mp3")))


@pytest.fixture
def full_bank(tmp_path):
    bank = ExamBank(tmp_path)
    bank.folder.mkdir()
    rows = [choice(difficulty * 100 + i, difficulty)
            for difficulty in range(1, 6) for i in range(60)]
    bank.questions_path.write_text(json.dumps(rows), encoding="utf-8")
    return bank


def configure(bank, count, *, level=None, ratios=None):
    config = bank.config()
    config["question_count"] = count
    if level is not None:
        config["ratios"][str(level)] = ratios
    bank.save_config(config)


@pytest.mark.parametrize("level", [1, 5, 10])
def test_exam_preserves_quotas_and_unique_ids(full_bank, level):
    configure(full_bank, 20)
    exam = full_bank.create_exam("3", "L1", level, rng=random.Random(level))
    counts = Counter(int(q["difficulty"]) for q in exam["questions"])
    assert len({q["id"] for q in exam["questions"]}) == 20
    assert len(exam["questions"]) == 20
    assert [counts[i] for i in range(1, 6)] == exam["counts"]


@pytest.mark.parametrize("count", [1, 7, 13, 33, 50])
def test_rounding_fills_every_level(full_bank, count):
    configure(full_bank, count)
    for level in range(1, 11):
        exam = full_bank.create_exam("3", "L1", level, rng=random.Random(1))
        assert len(exam["questions"]) == sum(exam["counts"]) == count, level


def test_insufficient_questions_reports_requested_quotas(tmp_path):
    bank = ExamBank(tmp_path)
    for number in range(5):
        bank.save_question(choice(number))
    configure(bank, 10)
    with pytest.raises(ValueError, match="chưa đủ câu"):
        bank.create_exam("3", "L1", 1)


def test_exam_filters_grade_and_subject(full_bank):
    full_bank.save_question(choice(1, grade="4"))
    full_bank.save_question(choice(2, subject="tieng_viet"))
    configure(full_bank, 20)
    exam = full_bank.create_exam("3", "L1", 1, rng=random.Random(1))
    assert all(q["grade"] == "3" and q["subject"] == "tieng_anh" for q in exam["questions"])
    with pytest.raises(ValueError, match="chưa đủ câu"):
        full_bank.create_exam("4", "L1", 1)


@pytest.fixture
def bank_with_audio(tmp_path):
    bank = ExamBank(tmp_path / "bank")
    audio = tmp_path / "example.mp3"
    audio.write_bytes(b"test fixture")
    for number in range(30):
        bank.save_question(choice(number))
    qid = bank.save_question(choice(99, type="listening_choice", audio=str(audio)))
    configure(bank, 5, level=1, ratios=[100, 0, 0, 0, 0])
    copied = next(q["audio"] for q in bank.questions() if q["id"] == qid)
    return bank, qid, copied


def test_exam_can_use_bank_with_audio(bank_with_audio):
    bank, _, _ = bank_with_audio
    assert len(bank.create_exam("3", "L1", 1, rng=random.Random(1))["questions"]) == 5


def test_missing_audio_skips_only_broken_question(bank_with_audio):
    from pathlib import Path

    bank, qid, copied = bank_with_audio
    Path(copied).unlink()
    exam = bank.create_exam("3", "L1", 1, rng=random.Random(1))
    assert len(exam["questions"]) == 5
    assert qid not in {q["id"] for q in exam["questions"]}


@pytest.fixture
def reading_bank(full_bank):
    children = [dict(prompt=f"Child {i}", options=["a", "b"], answer="a", difficulty=i)
                for i in range(1, 4)]
    full_bank.save_reading(dict(subject="tieng_anh", grade="3", lesson="L1",
                                title="Reading", passage="Passage", questions=children))
    configure(full_bank, 8, level=3, ratios=[50, 25, 25, 0, 0])
    return full_bank


def test_reading_group_keeps_all_children_contiguous(reading_bank):
    for seed in range(200):
        questions = reading_bank.create_exam("3", "L1", 3, rng=random.Random(seed))["questions"]
        positions = [i for i, q in enumerate(questions) if q.get("reading_group")]
        assert len(questions) == 8
        assert len(positions) == 3
        assert positions == list(range(positions[0], positions[0] + 3))


def test_editing_reading_preserves_child_ids(reading_bank):
    group, = reading_bank.reading_groups()
    before = [child["id"] for child in group["questions"]]
    group["questions"][0]["prompt"] = "Edited"
    reading_bank.save_reading(group)
    saved, = reading_bank.reading_groups()
    assert [child["id"] for child in saved["questions"]] == before
    assert saved["questions"][0]["prompt"] == "Edited"


def test_reading_rejects_unknown_child_id(reading_bank):
    group, = reading_bank.reading_groups()
    group["questions"][0]["id"] = "unknown"
    with pytest.raises(ValueError):
        reading_bank.save_reading(group)


def test_question_persistence(tmp_path):
    bank = ExamBank(tmp_path)
    qid = bank.save_question(choice(prompt="Xin chào đây là tiếng Việt"))
    saved, = bank.questions()
    assert saved["prompt"] == "Xin chào đây là tiếng Việt"
    assert bank.save_question({**saved, "prompt": "Sửa"}) == qid
    assert len(bank.questions()) == 1
    bank.delete_question(qid)
    assert bank.questions() == []
    with pytest.raises(ValueError):
        bank.delete_question(qid)


def test_results_ignore_duplicate_id(tmp_path):
    bank = ExamBank(tmp_path)
    bank.save_result({"id": "r1", "correct": 1})
    bank.save_result({"id": "r1", "correct": 9})
    assert json.loads(bank.results_path.read_text(encoding="utf-8")) == [{"id": "r1", "correct": 1}]


def test_malformed_question_json_raises_value_error(tmp_path):
    bank = ExamBank(tmp_path)
    bank.folder.mkdir()
    bank.questions_path.write_text("{broken", encoding="utf-8")
    with pytest.raises(ValueError):
        bank.questions()
