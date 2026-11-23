"""Coverage for the built-in Grade 2 exam pack and its import workflow."""
from collections import Counter
import json
import random
import sqlite3

import pytest

from tuhoc.exams.exam_bank import ExamBank, SUBJECTS, validate_question
from exam_content.grade2 import LESSON, build_questions, install
from tuhoc.exams.exam_grading import is_correct
from tuhoc.exams.exam_history_bridge import exam_records


@pytest.mark.parametrize("subject", ["toan", "tieng_viet"])
def test_pack_has_valid_questions_for_every_level_and_size(tmp_path, subject):
    bank = ExamBank(tmp_path)
    assert install(bank) == 200
    rows = [row for row in bank.questions() if row["subject"] == subject]
    assert len({row["id"] for row in rows}) == len(rows) == 100
    assert Counter(question["difficulty"] for question in rows) == {
        1: 35, 2: 15, 3: 15, 4: 18, 5: 17,
    }
    types = {row["type"] for row in rows}
    assert {"choice", "fill", "true_false", "order", "matching"} <= types
    if subject == "tieng_viet":
        assert "sentence_gaps" in types
        assert any(row.get("passage") for row in rows)
    for row in rows:
        validate_question(row)
        correct = {"matching": dict(row.get("pairs", [])),
                   "sentence_gaps": row.get("gap_answers")}.get(row["type"], row.get("answer"))
        assert is_correct(row, correct, row.get("sequence")), row["id"]
    assert bank.lessons("2", subject) == [LESSON]
    assert bank.lessons("3", subject) == []

    for count in (1, 10, 25, 49, 50):
        cfg = bank.config()
        cfg["question_count"] = count
        bank.save_config(cfg)
        for level in range(1, 11):
            exam = bank.create_exam("2", LESSON, level, random.Random(level), subject)
            assert len(exam["questions"]) == count
            assert {q["subject"] for q in exam["questions"]} == {subject}
            counts = Counter(q["difficulty"] for q in exam["questions"])
            assert [counts[i] for i in range(1, 6)] == exam["counts"]


def test_reinstall_preserves_teacher_edits_and_original_backup(tmp_path):
    bank = ExamBank(tmp_path)
    builtin, *remaining = build_questions()
    edited = {**builtin, "prompt": "Câu giáo viên đã chỉnh."}
    teacher = {**remaining[0], "id": "teacher", "subject": "tieng_anh", "grade": "3"}
    original = json.dumps([edited, teacher], ensure_ascii=False).encode("utf-8")
    bank.folder.mkdir()
    bank.questions_path.write_bytes(original)
    assert install(bank) == 199
    entries = {q["id"]: q for q in bank.questions()}
    assert entries[builtin["id"]] == edited
    assert entries["teacher"] == teacher
    assert len(entries) == 201
    backups = list((bank.folder / "backups").glob("*/0_exam_questions.json"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == original
    imported = bank.questions_path.read_bytes()
    assert install(bank) == 0
    assert bank.questions_path.read_bytes() == imported
    assert list((bank.folder / "backups").glob("*/0_exam_questions.json")) == backups


def test_invalid_batch_cannot_partially_import(tmp_path):
    bank = ExamBank(tmp_path)
    first = build_questions()[0]
    with pytest.raises(ValueError):
        bank.add_text_questions([first, {**first, "id": "bad", "type": "invalid"}])
    assert bank.questions() == []


def test_math_results_are_filtered_under_math(tmp_path):
    bank = ExamBank(tmp_path)
    for subject in SUBJECTS:
        bank.save_result(dict(id=subject, student_id=42, subject=subject, grade="2", lesson=LESSON,
                              level=1, submitted_at="2025-01-01T10:00:00", total=10, correct=8))
    with sqlite3.connect(tmp_path / "tu_hoc.sqlite3") as conn:
        assert {row[1] for row in exam_records(conn, 42)} == set(SUBJECTS)
        assert [row[1] for row in exam_records(conn, 42, "toan")] == ["toan"]
        assert [row[1] for row in exam_records(conn, 42, "en")] == ["tieng_anh"]
        assert [row[1] for row in exam_records(conn, 42, "vi")] == ["tieng_viet"]
        assert exam_records(conn, 43, "toan") == []


def test_editor_imports_pack_and_saves_passage_again(tmp_path):
    pytest.importorskip("tkinter")
    pytest.importorskip("pygame")
    from tuhoc.exams.exam_bank_pygame import BankManager

    ui = BankManager(tmp_path)
    ui.install_grade2()
    assert (ui.subject, ui.grade, ui.lesson) == ("toan", "2", LESSON)
    assert len(ui.scope()) == 100
    ui.change("subject", list(SUBJECTS))
    assert ui.subject == "tieng_anh"
    ui.change("subject", list(SUBJECTS))
    assert ui.subject == "tieng_viet"
    row = next(q for q in ui.scope() if q.get("passage"))
    ui.begin(row)
    assert ui.multiline_form()["passage"] == row["passage"]
    ui.multiline_form()["passage"] += " Em kể lại cho má nghe."
    ui.save()
    saved = next(q for q in ui.scope() if q["id"] == row["id"])
    assert saved["passage"].endswith("Em kể lại cho má nghe.")
    assert saved["answer"] == row["answer"]
