"""Print and check WCAG AA contrast for explicit text/foreground token pairs."""
import unittest
from tuhoc.ui.ui_tokens import COLORS, contrast_ratio


class UIContrast(unittest.TestCase):
    def test_pairs(self):
        self.assertEqual(contrast_ratio('#000000','#ffffff'),21)
        pairs={'surface':('text','muted','primary','error','warning','info','focus'),
               'background':('text','muted'),'tint':('text','primary'),'disabled':('disabled_text',),
               'primary':('surface',),'primary_dark':('surface',)}
        for bg,foreground in pairs.items():
            for fg in foreground:
                ratio=contrast_ratio(COLORS[bg],COLORS[fg])
                print(f'{fg} on {bg}: {ratio:.2f}')
                self.assertGreaterEqual(ratio,4.5,(fg,bg,ratio))


if __name__=='__main__':
    unittest.main(verbosity=2)
