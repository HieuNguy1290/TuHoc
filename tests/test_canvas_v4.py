"""Regression checks for layout-authored typography and Exam preview dispatch."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pygame

from tuhoc.exams.exam_bank import ALLOWED_TYPES
from tuhoc.exams.exam_pygame import ExamLayoutScene, READ_VIEWPORT
from tuhoc.studio.layout_registry import controls_for
from tuhoc.studio.layout_render import MOBILE
from tuhoc.studio.layout_typography import TextBlock, _font
from tuhoc.studio.question_layout_store import layout_v3, pixel_elements, pixel_extras, validate_layout


class LayoutV4Tests(unittest.TestCase):
    def test_v4_style_round_trip(self):
        prompt = dict(font_family='DejaVu Serif', underline=True,
                      runs=[dict(start=0, end=3, bold=True, italic=True)])
        slot = dict(x=55, y=257, width=108, height=42)
        layout = dict(version=4, desktop=dict(question_text=prompt, slot_0=slot),
                      mobile=dict(question_text=dict(font_size=18)))
        checked = validate_layout(layout)
        self.assertEqual(layout_v3(checked)['version'], 4)
        self.assertEqual(pixel_elements(checked, MOBILE)['question_text'], {**prompt, 'font_size': 18})
        self.assertEqual(pixel_elements(checked)['slot_0'], slot)
        self.assertEqual(pixel_extras(checked), [])
        with self.assertRaises(ValueError):
            validate_layout(dict(version=4, desktop=dict(question_text=dict(underline='yes'))))

    def test_unicode_ranges_use_displayed_text_and_combined_style(self):
        pygame.font.init()
        fallback = pygame.font.SysFont('DejaVu Sans', 22)
        geometry = dict(runs=[dict(start=0, end=3, italic=True, underline=True)])
        block = TextBlock('**Bốn** quả', geometry, fallback, 22, (0, 0, 300), 30)
        label, face = block.styled[0][0]
        self.assertEqual(label, 'Bốn')
        self.assertTrue(face.get_bold())
        self.assertTrue(face.get_italic())
        self.assertTrue(face.get_underline())
        self.assertFalse(fallback.get_italic())

    def test_cached_fonts_are_recreated_after_leaving_exam(self):
        pygame.font.init()
        first = _font('DejaVu Sans', 21, False, False, True)
        pygame.quit()
        pygame.font.init()
        second = _font('DejaVu Sans', 21, False, False, True)
        self.assertIsNot(first, second)
        self.assertGreater(second.size('Tiếng Việt')[0], 0)

    def test_every_exam_type_can_preview_with_saved_style(self):
        pygame.font.init()
        layout = dict(version=4, desktop=dict(question_text=dict(x=12, y=25, width=500,
                                                                 height=70, italic=True)))
        draft = dict(prompt='Chọn đáp án đúng', options=['a', 'b'], sequence=['a', 'b'],
                     gap_answers=['a', 'b'], pairs=[('a', '1'), ('b', '2')], passage='Bài đọc',
                     questions=[dict(prompt='Câu 1', options=['a', 'b']),
                                dict(prompt='Câu 2', options=['a', 'b'])])
        with TemporaryDirectory() as folder:
            for kind in sorted(ALLOWED_TYPES | {'reading_group'}):
                with self.subTest(kind=kind):
                    self.assertEqual(controls_for(kind, 'exam').runtime, 'exam_pygame')
                    surface, regions, _, _ = ExamLayoutScene(Path(folder),
                                                               {**draft, 'type': kind}, layout).draw()
                    self.assertEqual(surface.get_size(), READ_VIEWPORT)
                    if kind == 'reading_group':
                        self.assertEqual({key for key in regions if not key.startswith('_')}, {'answer_passage', 'answer_panel'})
                    else:
                        self.assertEqual(regions['question_text'][0], (9, 25, 361, 70))
                        self.assertGreater(len(regions), 1)
