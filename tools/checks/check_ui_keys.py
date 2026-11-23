"""Check shell shortcut routing and editable-field behavior."""
import unittest

from tuhoc.ui.ui_keys import GRID_MOVES, action_for


class UIKeys(unittest.TestCase):
    def test_application_keys(self):
        self.assertEqual(action_for('F1',0,'Button'),'help')
        self.assertEqual(action_for('Escape',0,'Frame'),'back')
        self.assertEqual(action_for('Left',8,'Frame'),'back')
        self.assertIsNone(action_for('Left',0,'Frame'))
        self.assertEqual((GRID_MOVES['Up'],GRID_MOVES['Right']),(-5,1))

    def test_text_fields_keep_keyboard_input(self):
        for widget in ('Entry','TEntry','Text','TCombobox','TSpinbox'):
            for key,flags in (('Escape',0),('Left',8),('F1',0),('Return',0)):
                self.assertIsNone(action_for(key,flags,widget),(widget,key))


if __name__=='__main__':
    unittest.main(verbosity=2)
