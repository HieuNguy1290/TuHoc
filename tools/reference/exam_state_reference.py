"""Kịch bản rà soát Exam Mode. Bản kiểm thử nằm trong tests/."""
import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.environ.get('TUHOC_ROOT', '.'))
pg = MagicMock()
for name in ('pygame', 'pygame.mixer', 'pygame.font', 'pygame.display', 'pygame.key', 'pygame.time'):
    sys.modules[name] = pg

import tuhoc.exams.exam_pygame as ep

ui = ep.ExamUI.__new__(ep.ExamUI)
questions = [
    dict(id='c1', type='choice', prompt='p', difficulty=1, options=['a', 'b'], answer='a'),
    dict(id='g1', type='sentence_gaps', prompt='{1} {2}', difficulty=1, gap_answers=['x', 'y']),
    dict(id='m1', type='matching', prompt='p', difficulty=1, pairs=[['a', '1'], ['b', '2']]),
    dict(id='o1', type='order', prompt='p', difficulty=1, sequence=['I', 'am', 'ok']),
    dict(id='f1', type='fill', prompt='p', difficulty=1, answer='dog'),
]
ui.exam = {'questions': questions}
ui.answers = {}
ui.order_inputs = {}
ui.flagged = set()
ui.match_pending = None
ui.gap_focus = 0
ui.mode = 'exam'
ui.index = 0
ui.nav_filter = 'all'
ui.nav_page = 0
ui.nav_page_size = 15


def show(label):
    print(label, [questions[i]['id'] for i in ui._unanswered_indices()])


show('Ban đầu')
ui._gap_text(questions[1], 'x')
show('Gõ chữ vào ô trống')
ui._gap_key(questions[1], MagicMock(key=pg.K_BACKSPACE))
show('Xóa hết chữ')
ui._select_match_left('m1', 'a')
ui._select_match_right('m1', '1')
show('Nối 1/2 cặp')
ui._pick_order(questions[3], 'I')
ui._pick_order(questions[3], 'am')
show('Chọn 2/3 từ')
ui.answers['f1'] = '   '
show('Trả lời bằng khoảng trắng')
print('Chấm:', ep.is_correct(questions[4], ui.answers['f1']))
print('Đã trả lời:', sum(bool(ui.answers.get(q['id'])) for q in questions), '/', len(questions))
