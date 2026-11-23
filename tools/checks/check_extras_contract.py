"""Exercise v3 validation, projection, drawing and reversible migration."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pygame

from tuhoc.studio.extras_render import draw_extras
from tools.migrations.layout_migrate import migrate_file, restore_file
from tuhoc.studio.layout_render import DESKTOP, MOBILE
from tuhoc.studio.layout_scroll_extent import content_bottom
from tuhoc.studio.question_layout_store import get_layout, layout_v2, layout_v3, pixel_elements, pixel_extras, set_layout


BOX = dict(id='note', kind='text', text='Tiếng Việt', desktop=dict(x=96, y=640, width=192, height=80),
           font_size=21, bold=True, italic=False, color='#113355', align='center', bg='#dddddd', z=2)


class ExtrasContract(unittest.TestCase):
    def test_round_trip_and_projection(self):
        layout = layout_v3({'question_text': {'x': .05}})
        layout['extras'] = [BOX]
        question = set_layout({'type': 'fill', 'answer': 'mèo'}, layout)
        self.assertEqual(question['answer'], 'mèo')
        self.assertEqual(layout_v2(get_layout(question)), layout)
        self.assertEqual(pixel_elements(layout, DESKTOP), {'question_text': {'x': 48}})
        self.assertEqual(pixel_extras(layout, MOBILE)[0]['rect']['x'], 39)
        self.assertEqual(pixel_extras(layout, MOBILE)[0]['rect']['y'], 760)
        override = deepcopy(layout)
        override['extras'][0]['mobile'] = dict(x=11, y=24, width=100, height=40)
        self.assertEqual(pixel_extras(override, MOBILE)[0]['rect'], override['extras'][0]['mobile'])
        self.assertGreater(content_bottom(question, 640), 720)
        exam_column=(350,640)
        self.assertEqual(pixel_extras(override,exam_column,mobile=False)[0]['rect'],
                         dict(x=35,y=640,width=70,height=80))

    def test_invalid_values(self):
        for patch in (dict(id='complete_button'), dict(id='option_2'), dict(text='a'*501),
                      dict(font_size=True), dict(z=1.0), dict(bg='white'),
                      dict(desktop=dict(x=959, y=0, width=2, height=8))):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                set_layout({}, dict(version=3, desktop={}, extras=[{**BOX, **patch}]))
        with self.assertRaises(ValueError):
            set_layout({}, dict(version=3, desktop={}, extras=[BOX, BOX]))

    def test_pixels_clipping_z_order_and_legacy(self):
        pygame.font.init()
        screen = pygame.Surface(DESKTOP)
        screen.fill('white')
        baseline = pygame.image.tobytes(screen, 'RGB')
        draw_extras(screen, {'type': 'fill'})
        self.assertEqual(pygame.image.tobytes(screen, 'RGB'), baseline)
        back = {**BOX, 'id': 'back', 'bg': '#ff0000', 'z': -1}
        question = {'layout': dict(version=3, desktop={}, extras=[BOX, back])}
        draw_extras(screen, question, offset=(0, -620))
        self.assertEqual(screen.get_at((97, 21)), pygame.Color('#dddddd'))
        self.assertEqual(screen.get_at((95, 21)), pygame.Color('white'))
        self.assertGreater(len(set(pygame.image.tobytes(screen.subsurface((96, 20, 192, 35)), 'RGB'))), 2)
        self.assertEqual(screen.get_clip(), screen.get_rect())

    def test_migration_is_idempotent_and_reversible(self):
        source = b'[{"type":"fill","layout":{"version":2,"desktop":{}}}]'
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'questions.json'
            path.write_bytes(source)
            self.assertEqual(migrate_file(path, version=3), 1)
            self.assertIn(b'"extras":[]', path.read_bytes())
            self.assertEqual(migrate_file(path, version=3), 0)
            restore_file(path)
            self.assertEqual(path.read_bytes(), source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
