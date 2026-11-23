"""Phase 3 headless regression suite. Run: python VERIFY_PATCH12.py
No Tk/Pygame window is created; no learner data is written.
"""
import ast
import importlib.util
import pathlib
import sys
import unittest
from unittest.mock import Mock, patch

from tools.checks.paths import ROOT, source_file

def load_runtime():
    spec = importlib.util.spec_from_file_location('new_exercise_runtime', source_file('new_exercise_runtime.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Phase3Regression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = load_runtime()
        cls.quiz_source = (source_file('upgrade_v2.py')).read_text(encoding='utf-8-sig')
        cls.exercise_source = (source_file('pygame_exercises.py')).read_text(encoding='utf-8-sig')

    def test_all_sources_parse(self):
        for path in (*ROOT.glob('*.py'), *(ROOT / 'tuhoc').rglob('*.py')):
            with self.subTest(path=path.name):
                ast.parse(path.read_text(encoding='utf-8-sig'), filename=path.name)

    def test_question_counter_contract(self):
        tree = ast.parse(self.quiz_source)
        quiz = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'session_quiz']
        self.assertEqual(len(quiz), 1)
        calls = [n for n in ast.walk(quiz[0]) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'dict']
        index_keywords = [kw.value for call in calls for kw in call.keywords if kw.arg == '_index']
        self.assertTrue(index_keywords, 'Quiz must pass _index to Pygame')
        self.assertTrue(any(isinstance(v, ast.BinOp) and isinstance(v.op, ast.Add) and isinstance(v.right, ast.Constant) and v.right.value == 1 for v in index_keywords), 'Quiz must pass 1-based _index')
        runtime_source = (source_file('new_exercise_runtime.py')).read_text(encoding='utf-8-sig')
        self.assertIn('draw_question_progress(', runtime_source)
        self.assertNotIn("_index', 1)) - 1", runtime_source)

        import pygame
        from tuhoc.exercises.exercise_gfx import draw_question_progress

        pygame.font.init()
        try:
            surface = pygame.Surface((960, 640))
            font = pygame.font.Font(None, 24)
            # Observe the string through a real font renderer.
            spy = Mock(wraps=font)
            with patch('pygame.font.SysFont', return_value=spy):
                draw_question_progress(surface, {'_index': 1, '_total': 26})
                draw_question_progress(surface, {'_index': 26, '_total': 26})
                self.assertEqual([call.args[0] for call in spy.render.call_args_list],
                                 ['Câu: 1/26', 'Câu: 26/26'])
        finally:
            pygame.font.quit()

    def test_sequential_progress_guard(self):
        self.assertIn('len(getattr(self, "s_answers", []))', self.quiz_source)
        self.assertIn('if index != expected:', self.quiz_source)
        self.assertIn('if expected_generation!=getattr(self,', self.quiz_source)
        self.assertIn('self.session_quiz(expected_index+1)', self.quiz_source)

    def test_extended_types_coverage(self):
        self.assertEqual(self.runtime.NEW_TYPES, frozenset({
            'image_multi_choice', 'picture_missing_letters', 'sentence_gaps',
            'conversation_gaps', 'passage_gaps', 'image_multi_select', 'text_multi_select',
            'audio_multi_select', 'image_write_answer', 'image_underline_choice', 'sentence_underline_words',
            'dropdown_fill_blank', 'multi_fill_blanks', 'image_sentence_fill', 'image_letter_pick',
            'inline_dropdown_fill'}))
        self.assertIn('NEW_TYPES', self.exercise_source)

    def test_extended_grading(self):
        cases = [
            ({'type': 'image_multi_choice', 'answer': 'dog.png'}, 'dog.png', 'cat.png'),
            ({'type': 'picture_missing_letters', 'answer': 'Apple'}, 'apple', 'pear'),
            ({'type': 'sentence_gaps', 'source_text': 'I like red apples', 'hidden_indices': [2, 3]}, ['RED', 'apples'], ['red']),
            ({'type': 'passage_gaps', 'source_text': 'one two three', 'hidden_indices': [1]}, ['TWO'], ['three']),
            ({'type': 'conversation_gaps', 'dialogue': [{'text': 'hello world', 'hidden_indices': [1]}, {'text': 'good morning', 'hidden_indices': [0]}]}, ['world', 'good'], ['world', 'bad']),
        ]
        for question, right, wrong in cases:
            with self.subTest(kind=question['type']):
                self.assertTrue(self.runtime.correct(question, right))
                self.assertFalse(self.runtime.correct(question, wrong))

    def test_gap_index_safety(self):
        q = {'type': 'sentence_gaps', 'source_text': 'a b c', 'hidden_indices': [-1, 2, 99, 2]}
        self.assertEqual(self.runtime.expected(q), ['c'])

    def test_lifecycle_guard_present(self):
        guard = (source_file('pygame_session_guard.py')).read_text(encoding='utf-8-sig')
        self.assertIn('threading.Lock()', guard)
        self.assertIn('blocking=False', guard)
        self.assertIn('release_sdl_session()', self.exercise_source)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Phase3Regression)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print('\nNOTE: Headless checks only; verify the native SDL window on Windows manually.')
    sys.exit(0 if result.wasSuccessful() else 1)
