"""Exercise UI components and safe modal handling under Tk."""
import tkinter as tk
import unittest
from unittest.mock import patch

import tuhoc.ui.ui_dialogs as ui_dialogs
from tuhoc.ui.ui_components import Badge, ConfirmDialog, Dialog, EmptyState, LoadingState, RoundedButton, Toast, Tooltip


class Components(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk()
        self.root.update()
        self.addCleanup(self.root.destroy)

    def test_button_states_and_focus(self):
        seen=[]
        button=RoundedButton(self.root,'Chọn',lambda:seen.append(True),height=12,
                             icon='✓',tooltip='Chọn đáp án')
        button.pack()
        self.root.update()
        self.assertGreaterEqual(int(button.cget('height')),44)
        button.focus_force()
        self.root.update()
        self.assertIs(self.root.focus_get(),button)
        button.event_generate('<Return>')
        for state in ({'disabled':True},{'disabled':False,'loading':True}):
            button.set_state(**state)
            button.invoke()
            button.event_generate('<Button-1>',x=20,y=20)
        button.set_state(loading=False)
        button.invoke()
        self.assertEqual(seen,[True, True])

    def test_dialog_keyboard_and_compatibility(self):
        dialog=ConfirmDialog(self.root,'Xác nhận','Chọn an toàn')
        dialog.secondary.focus_force()
        self.root.update()
        self.assertIs(dialog.focus_get(),dialog.secondary)
        dialog.after_idle(lambda:dialog.secondary.event_generate('<Return>'))
        self.assertFalse(dialog.show())
        dialog=Dialog(self.root,'Tin nhắn','Nội dung')
        dialog.primary.focus_force()
        dialog.after_idle(lambda:dialog.event_generate('<Escape>'))
        self.assertFalse(dialog.show())
        with patch('tuhoc.ui.ui_dialogs.ConfirmDialog') as wrapper:
            wrapper.return_value.show.return_value=True
            self.assertTrue(ui_dialogs.askyesno('Mở?','Nội dung',parent=self.root))
            self.assertTrue(wrapper.call_args.kwargs['safe'])

    def test_create_and_dispose_feedback(self):
        for cls in (EmptyState,LoadingState,Badge):
            cls(self.root,'Thử').pack()
        toast=Toast(self.root,'Đã lưu',action=('Hoàn tác',lambda:None))
        self.assertTrue(toast.frame.winfo_exists())
        toast.close()
        label=tk.Label(self.root,text='?')
        label.pack()
        self.root.update()
        tip=Tooltip(label,'Trợ giúp')
        tip.show()
        self.assertTrue(tip.tip.winfo_exists())
        tip.hide()
        self.assertIsNone(tip.tip)


if __name__=='__main__':
    unittest.main(verbosity=2)
