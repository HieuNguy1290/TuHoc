import tkinter as tk
from tkinter import ttk
import unittest

from new_exercise_editors import build
from question_layout_editor import edit_layout
from question_layout_runtime import element
from token_picker import TokenPicker


def pixel_fields(root):
    return [w for w in widgets(root, ttk.Entry) if type(w) is ttk.Entry]


def widgets(root, widget_type):
    matches = [root] if isinstance(root, widget_type) else []
    for child in root.winfo_children():
        matches.extend(widgets(child, widget_type))
    return matches


class StudioTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(str(exc))
        self.addCleanup(self.root.destroy)

    def interact(self, question, layout, action, preview=None):
        errors = []

        def drive():
            window = widgets(self.root, tk.Toplevel)[0]
            try:
                window.update_idletasks()
                action(window)
            except BaseException as exc:
                errors.append(exc)
                window.destroy()

        self.root.after(60, drive)
        outcome = edit_layout(self.root, question, layout, preview=preview)
        if errors:
            raise errors[0]
        return outcome

    def test_pixel_edits_mobile_undo_and_preview(self):
        question = {'id': 'q-drag', 'type': 'fill', 'prompt': 'Điền từ', 'answer': 'mèo'}
        captured = []

        def edit(win):
            def button(label):
                return next(b for b in widgets(win, ttk.Button) if b.cget('text') == label)

            def select(key):
                choices = widgets(win, tk.Listbox)[0]
                choices.selection_clear(0, 'end')
                choices.selection_set(choices.get(0, 'end').index(key))
                choices.event_generate('<<ListboxSelect>>')

            def pixels(values):
                fields = pixel_fields(win)
                self.assertEqual(len(fields), 4)
                for field, value in zip(fields, values):
                    field.delete(0, 'end')
                    field.insert(0, str(value))
                button('Áp dụng (px)').invoke()

            select('input_area')
            pixels((72, 820, 580, 48))
            button('Hoàn tác').invoke()
            self.assertNotEqual(pixel_fields(win)[1].get(), '820')
            button('Làm lại').invoke()
            self.assertEqual(pixel_fields(win)[1].get(), '820')
            combo = widgets(win, ttk.Combobox)[0]
            combo.set('Điện thoại')
            combo.event_generate('<<ComboboxSelected>>')
            pixels((32, 950, 300, 46))
            combo.set('Máy tính')
            combo.event_generate('<<ComboboxSelected>>')
            button('Xem trước Pygame').invoke()
            self.assertTrue(any('image' in [canvas.type(i) for i in canvas.find_all()]
                                for canvas in widgets(win, tk.Canvas)))
            button('Lưu bố cục').invoke()

        def preview(draft, _owner, on_frame):
            captured.append(draft)
            on_frame((960, 640), b'\xff' * (960 * 640 * 3))

        initial = {'input_area': {'x': .1, 'y': 1.1, 'width': .5, 'height': .1}}
        result = self.interact(question, initial, edit, preview)
        self.assertEqual(result, captured[0])
        self.assertEqual(element({**question, 'layout': result}, 'input_area')['y'], 820)
        self.assertEqual(element({**question, 'layout': result}, 'input_area', (390, 760))['y'], 950)
        self.assertEqual(question['answer'], 'mèo')

        def reopen(win):
            choices = widgets(win, tk.Listbox)[0]
            choices.selection_set(choices.get(0, 'end').index('input_area'))
            choices.event_generate('<<ListboxSelect>>')
            self.assertEqual(pixel_fields(win)[1].get(), '820')
            next(b for b in widgets(win, ttk.Button) if b.cget('text') == 'Lưu bố cục').invoke()

        self.assertEqual(self.interact(question, result, reopen), result)

    def test_drag_at_zoom_with_scrolled_origin(self):
        question = {'type': 'fill', 'prompt': 'Câu hỏi'}
        initial = {'input_area': {'x': 100/960, 'y': 750/640, 'width': 300/960, 'height': 50/640}}

        def edit(win):
            def button(label):
                return next(b for b in widgets(win, ttk.Button) if b.cget('text') == label)

            canvas = max(widgets(win, tk.Canvas), key=lambda w: w.winfo_width()*w.winfo_height())
            button('+').invoke()
            canvas.yview_moveto(.42)
            sx = round((16 + 180)*1.1 - canvas.canvasx(0))
            sy = round((16 + 775)*1.1 - canvas.canvasy(0))
            self.assertTrue(30 < sy < canvas.winfo_height()-138, (sy, canvas.winfo_height()))
            canvas.event_generate('<ButtonPress-1>', x=sx, y=sy)
            canvas.event_generate('<B1-Motion>', x=sx+44, y=sy+110)
            canvas.event_generate('<ButtonRelease-1>', x=sx+44, y=sy+110)
            button('Lưu bố cục').invoke()

        result = self.interact(question, initial, edit)
        pixel = element({**question, 'layout': result}, 'input_area')
        self.assertLessEqual(abs(pixel['x']-140), 1)
        self.assertLessEqual(abs(pixel['y']-850), 1)

    def test_four_token_collectors(self):
        examples = (
            ('picture_missing_letters', {'image': 'cat.png', 'answer': 'MÈO', 'hidden_indices': [1]}),
            ('sentence_gaps', {'source_text': 'mèo ngủ ngon', 'hidden_indices': [1]}),
            ('passage_gaps', {'source_text': 'mèo ngủ ngon', 'hidden_indices': [1]}),
            ('conversation_gaps', {'dialogue': [{'speaker': 'An', 'text': 'mèo ngủ ngon', 'hidden_indices': [1]}]}),
        )
        for kind, question in examples:
            with self.subTest(kind=kind):
                frame = ttk.Frame(self.root)
                collect = build(frame, kind, question, lambda name: name)
                picker = widgets(frame, TokenPicker)[0]

                def indices():
                    result = collect()
                    if kind == 'conversation_gaps':
                        result = result['dialogue'][0]
                    return result['hidden_indices']

                self.assertEqual(indices(), [1])
                picker.refresh()
                self.assertEqual(indices(), [1])
                widgets(picker, ttk.Checkbutton)[2].invoke()
                self.assertEqual(indices(), [1, 2])
                self.assertEqual((question.get('dialogue') or [question])[0]['hidden_indices'], [1])
                frame.destroy()


if __name__ == '__main__':
    unittest.main()
