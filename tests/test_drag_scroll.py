"""Regression tests for mouse panning and click isolation in Tk pages."""
import tkinter as tk
import unittest

from tuhoc.ui.drag_scroll import bind_menu_pan, install_drag_scroll
from tuhoc.ui.wheel_scroll import install_wheel_scroll


class DragScrollTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(str(exc))
        self.addCleanup(self.root.destroy)
        self.canvas = tk.Canvas(self.root, width=320, height=220, scrollregion=(0,-70,320,930))
        self.canvas.pack()
        self.inner = tk.Frame(self.canvas, width=300, height=999)
        self.canvas.create_window(0,-70,anchor='nw',window=self.inner)
        self.label = tk.Label(self.inner,text='Nội dung')
        self.label.place(x=20,y=417)
        self.root.update()
        self.canvas.yview_moveto(.4)

    def drag(self, widget, amount):
        widget.event_generate('<ButtonPress-1>', x=4, y=4, rootx=20, rooty=180)
        widget.event_generate('<B1-Motion>', x=4, y=4+amount, rootx=20, rooty=180+amount, state=0x100)
        widget.event_generate('<ButtonRelease-1>', x=4, y=4, rootx=20, rooty=180+amount)

    def test_grab_at_existing_offset_uses_document_pixels(self):
        install_wheel_scroll(self.root)
        install_drag_scroll(self.root)
        self.root.active_scroll_canvas = self.canvas
        self.drag(self.label, -85)
        self.assertAlmostEqual(self.canvas.yview()[0], .485, places=3)
        self.drag(self.label, 35)
        self.assertAlmostEqual(self.canvas.yview()[0], .45, places=3)
        dialog = tk.Toplevel(self.root)
        label = tk.Label(dialog,text='Hộp thoại')
        label.pack()
        self.root.update()
        self.drag(label, -90)
        self.assertAlmostEqual(self.canvas.yview()[0], .45, places=3)

    def test_drawer_drag_does_not_activate_button_on_release(self):
        clicked = []
        button = tk.Button(self.inner, text='Mở', command=lambda: clicked.append(True))
        button.place(x=15,y=430)
        bind_menu_pan(self.canvas, (button,))
        self.root.update()
        self.drag(button, -75)
        self.assertEqual(clicked, [])
        self.assertAlmostEqual(self.canvas.yview()[0], .475, places=3)
        button.event_generate('<Enter>', x=4, y=4)
        self.drag(button, 0)
        self.assertEqual(clicked, [True])
