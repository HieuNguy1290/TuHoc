"""Subject selection, built-in exams and submission on a clean profile."""
import json
import random

import pytest

from tuhoc.exams.exam_bank import ExamBank, SUBJECTS


@pytest.mark.parametrize(('subject', 'grade', 'lesson'), [
    ('tieng_anh', '1', 'Family & Friends'),
    ('tieng_viet', '2', 'Ôn tập lớp 2'),
])
def test_samples_fill_every_default_level_and_size(tmp_path, subject, grade, lesson, monkeypatch):
    bank = ExamBank(tmp_path)
    assert bank.exam_courses(subject) == {grade: [lesson]}
    config = bank.config()
    monkeypatch.setattr(bank, 'config', lambda: config)
    for size in range(1, 51):
        config['question_count'] = size
        for level in range(1, 11):
            result = bank.create_exam(grade, lesson, level, rng=random.Random(23),
                                      subject=subject, include_samples=True)
            assert len(result['questions']) == size
            assert {row['subject'] for row in result['questions']} == {subject}
    assert not bank.questions_path.exists()


def test_subject_switch_and_submit_saves_correct_course(tmp_path, monkeypatch):
    import pygame
    from tuhoc.exams.exam_pygame import ExamUI, VIRTUAL

    monkeypatch.setattr(pygame.key, 'start_text_input', lambda: None)
    monkeypatch.setattr(pygame.key, 'stop_text_input', lambda: None)
    pygame.font.init()
    ui = ExamUI(tmp_path)
    ui.font, ui.bold, ui.big, ui.small = ui._font(22), ui._font(24, True), ui._font(36, True), ui._font(18)
    surface = pygame.Surface(VIRTUAL)
    ui.level = 10
    persisted = []
    for subject, grade in [('tieng_anh', '1'), ('tieng_viet', '2'), ('tieng_anh', '1')]:
        ui._subject_changed(SUBJECTS[subject])
        assert ui.grade == grade
        ui.mode = 'select'
        ui.buttons.clear()
        ui._draw_select(surface)
        ui._click((500, 600))
        assert ui.mode == 'exam' and ui.error is None
        ui._draw_exam(surface)
        for row in ui.exam['questions']:
            qid = row['id']
            if row['type'] == 'order':
                ui.order_inputs[qid] = row['sequence']
            elif row['type'] == 'matching':
                ui.answers[qid] = dict(row['pairs'])
            elif 'gap_answers' in row:
                ui.answers[qid] = row['gap_answers']
            else:
                ui.answers[qid] = row['answer']
        ui._submit()
        assert ui.mode == 'result'
        assert ui.result['correct'] == ui.result['total'] == 50
        assert ui.result['subject'] == subject
        ui._draw_result(surface)
        persisted.append(ui.result['id'])
    assert {result['id'] for result in json.loads(ui.bank.results_path.read_text(encoding='utf-8'))} == set(persisted)
    assert not ui.bank.questions_path.exists()
