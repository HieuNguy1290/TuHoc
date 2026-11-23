"""Drive the real Tk Studio and different image-filling policies."""
from pathlib import Path
from tempfile import TemporaryDirectory
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch

from PIL import Image

from tuhoc.studio.layout_images import fitted_image
from tuhoc.studio.question_layout_editor import edit_layout, resize_rect


def widgets(root, kind):
    for child in root.winfo_children():
        if isinstance(child, kind):
            yield child
        yield from widgets(child, kind)


class StudioV3(unittest.TestCase):
    def test_fitted_image_and_resize(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'wide.png'
            Image.new('RGB', (100, 50), 'red').save(path)
            self.assertEqual(fitted_image(path, (80, 80)).size, (80, 40))
            for fit in ('cover', 'stretch'):
                self.assertEqual(fitted_image(path, (80, 80), fit).size, (80, 80))
        rect = dict(x=.2, y=.5, width=.3, height=.2)
        large = resize_rect(rect, 'nw', -.1, -.1, (960, 640), keep_ratio=True)
        self.assertAlmostEqual(large['width']/large['height'], 1.5)
        self.assertAlmostEqual(large['x']+large['width'], .5)
        self.assertAlmostEqual(large['y']+large['height'], .7)
        free = resize_rect(rect, 'e', .1, 0, (960,640))
        self.assertAlmostEqual(free['width'], .4)
        self.assertAlmostEqual(free['height'], .2)

    def test_create_style_undo_and_reopen(self):
        root = tk.Tk()
        self.addCleanup(root.destroy)
        errors = []

        def run(image_path, initial=None):
            def drive():
                win = next(iter(widgets(root, tk.Toplevel)))
                try:
                    win.update_idletasks()
                    canvas = next(c for c in widgets(win, tk.Canvas) if c.cget('takefocus') == '1')
                    self.assertTrue(any(canvas.type(i) == 'image' for i in canvas.find_all()))
                    buttons = {w.cget('text'): w for w in widgets(win, ttk.Button)}
                    if initial is None:
                        buttons['+ Văn bản'].invoke()
                        listing = next(widgets(win, tk.Listbox))
                        self.assertEqual(listing.get('end'), 'Văn bản mới')
                        for cb in widgets(win, ttk.Checkbutton):
                            if cb.cget('text') in ('Đậm', 'Nghiêng'):
                                cb.invoke()
                        buttons['Hoàn tác'].invoke()
                        buttons['Làm lại'].invoke()
                    else:
                        listing = next(widgets(win, tk.Listbox))
                        self.assertIn('Văn bản mới', listing.get(0, 'end'))
                    buttons['Lưu bố cục'].invoke()
                except BaseException as exc:
                    errors.append(exc)
                    win.destroy()

            root.after(50, drive)
            result = edit_layout(root, {'type':'picture_choice','image':str(image_path)}, initial)
            if errors:
                raise errors[0]
            return result

        with TemporaryDirectory() as tmp:
            asset = Path(tmp) / 'question.png'
            Image.new('RGB',(100,60),'green').save(asset)
            draft = run(asset)
            self.assertEqual(draft['version'], 3)
            self.assertEqual(len(draft['extras']), 1)
            self.assertTrue(draft['extras'][0]['bold'])
            self.assertTrue(draft['extras'][0]['italic'])
            self.assertEqual(run(asset,draft), draft)


    def test_clipboard_image_can_be_undone_before_saving(self):
        root=tk.Tk()
        self.addCleanup(root.destroy)
        errors=[]
        with TemporaryDirectory() as tmp:
            target=Path(tmp)/'selected.png'
            image=Image.new('RGB',(80,40),'blue')
            def drive():
                win=next(widgets(root,tk.Toplevel))
                try:
                    buttons={w.cget('text'):w for w in widgets(win,ttk.Button)}
                    buttons['Dán ảnh'].invoke()
                    self.assertFalse(target.exists())
                    buttons['Hoàn tác'].invoke()
                    buttons['Làm lại'].invoke()
                    buttons['Lưu bố cục'].invoke()
                except BaseException as exc:
                    errors.append(exc)
                    win.destroy()

            root.after(50,drive)
            with patch('PIL.ImageGrab.grabclipboard',return_value=image):
                result=edit_layout(root,{'type':'picture_choice'},clipboard=target)
            if errors:
                raise errors[0]
            self.assertIsNotNone(result)
            with Image.open(target) as pasted:
                self.assertEqual(pasted.size,image.size)
                self.assertEqual(pasted.getpixel((0,0)),(0,0,255,255))


if __name__ == '__main__':
    unittest.main(verbosity=2)
