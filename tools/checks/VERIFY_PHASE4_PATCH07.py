"""Non-destructive Phase 4 regression checks. Run in the application directory.
No GUI is opened. Only an in-memory SQLite database is used.
"""
import ast
import importlib
import pathlib
import sqlite3
import sys
import time
import types
import unittest

from tools.checks.paths import ROOT, source_file

sys.path.insert(0, str(ROOT))

class Phase4Regression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.drafts = importlib.import_module('tuhoc.storage.quiz_draft_store')
        cls.history = importlib.import_module('tuhoc.ui.quiz_history_ui')
        cls.analytics = importlib.import_module('tuhoc.ui.learning_analytics_ui')
        cls.wrong = importlib.import_module('tuhoc.ui.wrong_answers_ui')
        cls.insights = importlib.import_module('tuhoc.ui.result_insights')

    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.executescript('''
            CREATE TABLE learning_sessions(id INTEGER PRIMARY KEY, student_id INTEGER,
                theme TEXT, level INTEGER, started REAL, seconds REAL, correct INTEGER, total INTEGER);
            CREATE TABLE attempts(id INTEGER PRIMARY KEY, student_id INTEGER,
                exercise_id TEXT, exercise_type TEXT, answer TEXT, correct INTEGER,
                created_at TEXT);
        ''')

    def tearDown(self):
        self.db.close()

    def test_01_draft_resumes_and_isolated_by_student(self):
        store = self.drafts.QuizDraftStore(self.db)
        questions = [{'id': str(i), 'type': 'choice'} for i in range(1, 17)]
        store.save(1, 'en', 'animals', 1, questions, [('A', True), ('B', False), ('C', True)], 33.5)
        saved = store.load(1, 'en', 'animals', 1)
        self.assertEqual(len(saved['answers']), 3)
        self.assertEqual(len(saved['questions']), 16)
        self.assertEqual(saved['elapsed'], 33.5)
        self.assertIsNone(store.load(2, 'en', 'animals', 1))
        self.assertIsNone(store.load(1, 'vi', 'animals', 1))
        self.assertIsNone(store.load(1, 'en', 'animals', 2))
        store.delete(1, 'en', 'animals', 1)
        self.assertIsNone(store.load(1, 'en', 'animals', 1))

    def test_02_invalid_draft_rejected(self):
        store = self.drafts.QuizDraftStore(self.db)
        with self.assertRaises(ValueError):
            store.save(1, 'en', 'animals', 1, [], [('A', True)], 1)
        with self.assertRaises(ValueError):
            store.save(1, 'en', 'animals', 1, [], [], float('nan'))

    def test_03_history_pagination_and_student_filter(self):
        now = time.time()
        for i in range(46):
            self.db.execute('INSERT INTO learning_sessions(student_id,theme,level,started,seconds,correct,total) VALUES(?,?,?,?,?,?,?)',
                            (1, 'animals', 1, now-i*60, 120, 12, 16))
        self.db.execute('INSERT INTO learning_sessions(student_id,theme,level,started,seconds,correct,total) VALUES(?,?,?,?,?,?,?)',
                        (2, 'animals', 1, now, 20, 1, 1))
        count, page1 = self.history.fetch_history(self.db, 1, 0, 20)
        _, page2 = self.history.fetch_history(self.db, 1, 20, 20)
        _, page3 = self.history.fetch_history(self.db, 1, 40, 20)
        self.assertEqual((count, len(page1), len(page2), len(page3)), (46, 20, 20, 6))
        self.assertTrue({row[0] for row in page1}.isdisjoint({row[0] for row in page2}))
        self.assertEqual(self.history.fetch_history(self.db, 2)[0], 1)

    def test_04_analytics_aggregates_only_active_student(self):
        now = time.time()
        for sid, theme, correct, total in [(1, 'animals', 8, 10), (1, 'vi:words', 5, 10), (2, 'animals', 10, 10)]:
            self.db.execute('INSERT INTO learning_sessions(student_id,theme,level,started,seconds,correct,total) VALUES(?,?,?,?,?,?,?)',
                            (sid, theme, 1, now-100, 60, correct, total))
        all_result = self.analytics.aggregate(self.db, 1, 30)
        en = self.analytics.aggregate(self.db, 1, 30, 'en')
        vi = self.analytics.aggregate(self.db, 1, 30, 'vi')
        self.assertEqual((all_result['sessions'], all_result['correct'], all_result['total']), (2, 13, 20))
        self.assertEqual((en['sessions'], en['correct']), (1, 8))
        self.assertEqual((vi['sessions'], vi['correct']), (1, 5))

    def test_05_wrong_answers_latest_attempt_only(self):
        rows = [(1, 'q1', 0), (1, 'q1', 1), (1, 'q2', 0), (2, 'q3', 0)]
        for sid, qid, ok in rows:
            self.db.execute('INSERT INTO attempts(student_id,exercise_id,exercise_type,answer,correct,created_at) VALUES(?,?,?,?,?,?)',
                            (sid, qid, 'choice', 'A', ok, '2026-10-28'))
        curriculum = types.SimpleNamespace(rows={'questions':[
            {'id':'q1', 'theme':'animals', 'level':1},
            {'id':'q2', 'theme':'animals', 'level':1},
            {'id':'q3', 'theme':'animals', 'level':1}]})
        pending = self.wrong.collect_wrong(self.db, 1, curriculum)
        self.assertEqual([item['id'] for item in pending], ['q2'])

    def test_06_insights_grouping_does_not_mutate_answers(self):
        answers = [({'type':'choice'}, 'A', True), ({'type':'choice'}, 'B', False),
                   ({'type':'matching'}, {0:1}, True)]
        result = self.insights.summarize(answers)
        self.assertEqual((result['correct'], result['total'], result['wrong_numbers']), (2, 3, [2]))
        self.assertEqual(len(answers), 3)

    def test_07_source_integration_contracts(self):
        source = (source_file('upgrade_v2.py')).read_text(encoding='utf-8')
        ast.parse(source)
        for token in ('_save_quiz_draft', 'start_wrong_review', 'session_finish',
                      'learning_analytics_page', 'wrong_answers_page', 'quiz_history_page',
                      '_quiz_generation', 'on_cancel=on_cancel', 'result_insights'):
            self.assertIn(token, source, token)
        for filename in ('pygame_exercises.py', 'new_exercise_runtime.py'):
            if (source_file(filename)).exists():
                ast.parse((source_file(filename)).read_text(encoding='utf-8'))

if __name__ == '__main__':
    print('Phase 4 regression suite — in-memory database, no GUI, no changes to user data')
    unittest.main(verbosity=2)
