"""Exercise shared Tk token defaults and scaled compatibility fonts."""
import unittest

from tuhoc.ui.theme_config import UI_COLORS, UI_FONTS
from tuhoc.ui.ui_tokens import COLORS, DURATION, ELEVATION, RADIUS, SPACING, font, set_font_scale


class Tokens(unittest.TestCase):
    def tearDown(self):
        set_font_scale('medium')

    def test_palette_and_metrics(self):
        self.assertIs(UI_COLORS,COLORS)
        self.assertLessEqual({'primary','surface','background','border','text','text_muted',
                              'success','danger','warning','info','focus','disabled'},COLORS.keys())
        self.assertEqual(SPACING,(4,8,12,16,24,32))
        self.assertLess(DURATION['fast'],DURATION['slow'])
        self.assertLess(RADIUS['small'],RADIUS['large'])
        self.assertLess(ELEVATION['flat'],ELEVATION['overlay'])

    def test_scaling_is_applied_to_new_fonts(self):
        normal=font('title',True)
        set_font_scale('large')
        self.assertGreater(UI_FONTS['page'][1], normal[1])
        self.assertEqual(UI_FONTS['page'][-1],'bold')
        set_font_scale('small')
        self.assertLess(font('title',True)[1],normal[1])
        set_font_scale('unknown')
        self.assertEqual(font('title',True),normal)


if __name__=='__main__':
    unittest.main(verbosity=2)
