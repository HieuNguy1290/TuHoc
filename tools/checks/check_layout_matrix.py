"""Check registry completeness and screen projections independently of exercise input."""
from pathlib import Path
from tools.checks.paths import ROOT, source_file
import unittest

from tools.checks.audit_layout_coverage import coverage_matrix
from tuhoc.studio.layout_registry import REGISTRY, controls_for
from tuhoc.studio.layout_render import DESKTOP, MOBILE
from tuhoc.studio.layout_templates import template_for
from tuhoc.exercises.pygame_exercises import SUPPORTED
from tuhoc.studio.question_layout_store import GEOMETRY, layout_v3, pixel_elements, validate_layout


class LayoutMatrix(unittest.TestCase):
    def test_registry_matches_dispatch_and_templates(self):
        self.assertEqual(set(REGISTRY), SUPPORTED)
        matrix = coverage_matrix(ROOT)
        for kind in SUPPORTED:
            self.assertTrue(matrix[kind]['runtime_reads_layout'], kind)
            preset = template_for(kind)
            self.assertLessEqual(set(preset['desktop']), set(controls_for(kind).editable))
            validate_layout(preset)

    def test_no_layout_v2_v3_mobile_and_deep_scroll(self):
        for kind in SUPPORTED:
            self.assertEqual(pixel_elements(None), {})
            layout = template_for(kind)
            for name in layout['desktop']:
                layout['desktop'][name]['y'] = 1330
            updated = layout_v3(layout)
            for screen in (DESKTOP,MOBILE):
                pixels = pixel_elements(updated,screen)
                self.assertEqual(pixel_elements(layout,screen),pixels)
                for rect in pixels.values():
                    self.assertEqual(set(rect),GEOMETRY)
                    self.assertGreater(rect['y'], screen[1]*2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
