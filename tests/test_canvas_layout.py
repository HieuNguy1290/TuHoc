import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from tools.migrations.layout_migrate import migrate_bytes, migrate_file, restore_file
from tuhoc.studio.layout_render import DESKTOP, MOBILE
from tuhoc.studio.layout_templates import template_for
from tuhoc.studio.question_layout_runtime import element
from tuhoc.studio.question_layout_store import layout_v2, validate_layout


class LayoutTests(unittest.TestCase):
    def test_coordinates_at_boundary(self):
        legacy = {'input_area': {'x': 100 / 960, 'y': 2300 / 640,
                                 'width': 825 / 960, 'height': 260 / 640}}
        for layout in (legacy, layout_v2(legacy)):
            self.assertEqual(element({'type': 'fill', 'layout': layout}, 'answer_area'),
                             {'x': 100, 'y': 2300, 'width': 825, 'height': 260})
        with self.assertRaises(ValueError):
            validate_layout({'version': 2, 'desktop': {'input_area': {'y': 2300, 'height': 261}}})

    def test_mobile_override_and_template(self):
        q = {'type': 'image_write_answer', 'layout': template_for('image_write_answer')}
        desktop = element(q, 'input_area', DESKTOP)
        derived = element(q, 'input_area', MOBILE)
        q['layout']['mobile'] = {'input_area': {'y': 890}}
        self.assertEqual(element(q, 'input_area', MOBILE), {**derived, 'y': 890})
        self.assertEqual(element(q, 'input_area', DESKTOP), desktop)
        with self.assertRaises(ValueError):
            validate_layout({'version': 2, 'desktop': {'question_counter': {'y': 0}}})

    def test_round_trip_preserves_unrelated_bytes(self):
        legacy = b'{ "input_area":{"x":0.25,"y":1.75} }'
        original = (b'\xef\xbb\xbf[\r\n { "id": "q1", "type": "fill", "layout" : ' + legacy
                    + b', "prompt":"escaped \\"layout\\"", "answer":["a","b"]},\r\n'
                      b'{"id":"q2","type":"choice","prompt":"question"}]\r\n')
        updated, count = migrate_bytes(original)
        converted = b'{"version":2,"desktop":{"input_area":{"x":240,"y":1120}}}'
        self.assertEqual(count, 1)
        self.assertEqual(updated, original.replace(legacy, converted))
        self.assertEqual(migrate_bytes(updated), (updated, 0))
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'questions.json'
            path.write_bytes(original)
            self.assertEqual(migrate_file(path), 1)
            self.assertEqual(path.read_bytes(), updated)
            self.assertEqual(migrate_file(path), 0)
            restore_file(path)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(migrate_file(path), 1)
            path.write_bytes(original + b'\n')
            with self.assertRaises(OSError):
                migrate_file(path)
            self.assertEqual(path.read_bytes(), original + b'\n')

    def test_post_replace_failure_restores_backup(self):
        import tools.migrations.layout_migrate as layout_migrate

        original = b'[{"type":"choice","prompt":"q","layout":{"option_0":{"y":0.5}}}]'
        real_replace = layout_migrate._replace
        calls = []

        def corrupt_once(path, expected, content):
            real_replace(path, expected, content)
            if not calls:
                path.write_bytes(b'[]')
            calls.append(path)

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'questions.json'
            path.write_bytes(original)
            with patch('tools.migrations.layout_migrate._replace', side_effect=corrupt_once), self.assertRaises(OSError):
                migrate_file(path)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(path.with_suffix('.json.bak').read_bytes(), original)
            self.assertEqual(len(calls), 2)
            self.assertEqual(list(path.parent.glob('*.tmp')), [])

    def test_blank_prompt_is_only_valid_for_missing_letters(self):
        from tuhoc.exams.exam_bank import validate_question
        from tuhoc.exercises.question_prompt import display_prompt
        from tuhoc.lessons.upgrade_v2 import Curriculum
        from tuhoc.lessons.level_flow import save_rows

        examples = [{'id': 'letters', 'type': 'picture_missing_letters', 'prompt': '',
                     'answer': 'Mèo', 'theme': 'Family & Friends', 'level': 1, 'lesson': 1},
                    {'id': 'fill', 'type': 'fill', 'prompt': '',
                     'answer': 'Mèo', 'theme': 'Family & Friends', 'level': 1, 'lesson': 1}]
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            save_rows(folder, 'questions', examples)
            rows = Curriculum(folder).rows['questions']
            self.assertEqual([row['id'] for row in rows], ['letters'])
            self.assertEqual(rows[0]['prompt'], '')
            self.assertEqual(display_prompt(rows[0]), 'Nhìn hình và điền chữ còn thiếu')
            q = {**examples[0], 'grade': 1, 'difficulty': 1, 'image': str(folder / 'sample.png')}
            Path(q['image']).touch()
            self.assertEqual(validate_question(q)['prompt'], '')
            with self.assertRaises(ValueError):
                validate_question({**q, 'type': 'fill'})

    def test_letter_wrap_uses_cell_width_and_row_height(self):
        from tuhoc.exercises.exercise_layout import letter_items

        class Font:
            def size(self, _text):
                return (22, 30)

        positions, height = letter_items('TỰ HỌC', {0, 1, 4}, Font(),
                                         left=70, width=90, cell=(52, 58), row_height=72)
        self.assertGreater(height, 58)
        self.assertTrue(all(70 <= x < 160 and y % 72 == 0 for _, x, y in positions))
        self.assertTrue(all(x + 52 <= 160 for i, x, _ in positions if i in {0, 1, 4}))

    def test_word_bank_pages_with_three_speakers(self):
        from canvas_p0 import play
        from tuhoc.exercises.pygame_exercises import _run
        import pygame

        q = {'type': 'conversation_gaps', 'prompt': 'Đọc lượt thoại', '_index': 1, '_total': 1,
             'dialogue': [{'speaker': name, 'text': text, 'hidden_indices': [1]}
                          for name, text in [('An', 'một cat'), ('Bình', 'hai dog'), ('Chi', 'ba bird')]],
             'distractors': [f'long option {i}' for i in range(12)],
             'layout': {'version': 2, 'desktop': {'word_bank': {'x': 75, 'y': 505, 'width': 290}}}}
        with TemporaryDirectory() as tmp, patch.dict(os.environ, {'LOCALAPPDATA': tmp}):
            pygame.init()
            try:
                result = play(_run, q, ['cat', 'dog', 'bird'], None, False,
                              '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
            finally:
                pygame.quit()
        self.assertEqual(result['answer'], ['cat', 'dog', 'bird'])

    def test_real_archive_copy(self):
        source = Path(__file__).resolve().parents[1] / 'content_library.zip'
        if not source.is_file():
            self.skipTest('Optional legacy content archive is absent from this checkout.')
        with ZipFile(source) as archive, TemporaryDirectory() as tmp:
            for name in ('exam_questions.json', 'exam_reading_groups.json'):
                data = archive.read(f'content_library/{name}')
                path = Path(tmp) / name
                path.write_bytes(data)
                self.assertEqual(migrate_file(path), 0)
                self.assertEqual(path.read_bytes(), data)
                self.assertIsInstance(json.loads(path.read_bytes()), list)


if __name__ == '__main__':
    unittest.main()
