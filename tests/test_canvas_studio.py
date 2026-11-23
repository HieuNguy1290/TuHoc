import tkinter as tk
from tkinter import ttk
import unittest

from tuhoc.studio.new_exercise_editors import build
from tuhoc.studio.question_layout_editor import edit_layout
from tuhoc.studio.question_layout_runtime import element
from tuhoc.studio.token_picker import TokenPicker


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

    def test_direct_formatting_keeps_unselected_properties(self):
        from tuhoc.studio.studio_text_format import format_segments

        self.assertEqual(format_segments([dict(start=0, end=4, bold=True)], 2, 6, {'italic': True}), [
            dict(start=0, end=2, bold=True),
            dict(start=2, end=4, bold=True, italic=True),
            dict(start=4, end=6, italic=True),
        ])

    def test_text_formatting_is_saved_without_changing_the_question(self):
        question = {'type': 'choice', 'prompt': 'Bốn quả cam', 'options': ['4', '3'], 'answer': '4'}

        def edit(win):
            def button(owner, label):
                return next(b for b in widgets(owner, ttk.Button) if b.cget('text') == label)

            choices = widgets(win, tk.Listbox)[0]
            choices.selection_set(choices.get(0, 'end').index('question_text'))
            choices.event_generate('<<ListboxSelect>>')
            next(b for b in widgets(win, ttk.Checkbutton) if b.cget('text') == 'B · Đậm').invoke()
            button(win, 'Định dạng đoạn chữ…').invoke()
            dialog = next(child for child in win.winfo_children() if isinstance(child, tk.Toplevel))
            text = widgets(dialog, tk.Text)[0]
            text.tag_add('sel', '1.0', '1.3')
            text.event_generate('<<Selection>>')
            next(b for b in widgets(dialog, ttk.Checkbutton) if b.cget('text') == 'U · Gạch chân').invoke()
            combo = widgets(dialog, ttk.Combobox)[0]
            combo.set('DejaVu Serif')
            combo.event_generate('<<ComboboxSelected>>')
            next(b for b in widgets(dialog, ttk.Checkbutton) if b.cget('text') == 'I · Nghiêng').invoke()
            self.assertTrue(text.tag_ranges('format_0'))
            button(dialog, 'Lưu').invoke()
            canvas = next(c for c in widgets(win, tk.Canvas) if c.find_withtag('formatted_text'))
            font = next(canvas.itemcget(item, 'font') for item in canvas.find_withtag('formatted_text')
                        if canvas.itemcget(item, 'text') == 'Bốn')
            self.assertIn('DejaVu Serif', font)
            self.assertIn('underline', font)
            button(win, 'Lưu bố cục').invoke()

        layout = self.interact(question, None, edit)
        self.assertEqual(layout['version'], 4)
        self.assertTrue(layout['desktop']['question_text']['bold'])
        run = layout['desktop']['question_text']['runs'][0]
        self.assertEqual((run['start'], run['end'], run['font_family']), (0, 3, 'DejaVu Serif'))
        self.assertTrue(run['underline'])
        self.assertTrue(run['italic'])
        self.assertNotIn('bold', run)
        self.assertEqual(question['prompt'], 'Bốn quả cam')
        self.assertEqual(question['answer'], '4')

    def test_window_keeps_footer_reachable(self):
        def check(win):
            self.assertFalse(win.attributes('-fullscreen'))
            self.assertFalse(win.transient())
            buttons = widgets(win, ttk.Button)
            toggle = next(b for b in buttons if b.cget('text') in {'Phóng to cửa sổ', 'Thu nhỏ cửa sổ'})
            toggle.invoke()
            win.update_idletasks()
            save = next(b for b in buttons if b.cget('text') == 'Lưu bố cục')
            self.assertTrue(save.winfo_ismapped())
            bottom = save.winfo_rooty() + save.winfo_height()
            self.assertLessEqual(bottom, win.winfo_rooty() + win.winfo_height())
            save.invoke()

        self.interact({'type': 'choice', 'prompt': 'Câu hỏi', 'options': ['Có', 'Không']}, None, check)

    def test_live_canvas_moves_actual_answer_from_its_drawn_position(self):
        import time
        from tuhoc.studio.question_layout_editor import edit_layout

        question = {'type': 'choice', 'prompt': 'Choose the odd one out:',
                    'options': ['Dog', 'Kite', 'Cat', 'Bird']}
        self.root.wm_geometry('1100x770')
        errors = []

        def drive():
            win = widgets(self.root, tk.Toplevel)[0]
            try:
                win.update_idletasks()
                canvas = next(c for c in widgets(win, tk.Canvas) if str(c.cget('takefocus')) == '1')
                deadline = time.monotonic()+8
                while not any(canvas.type(item) == 'image' for item in canvas.find_all()):
                    self.assertLess(time.monotonic(), deadline, [label.cget('text') for label in widgets(win, ttk.Label)])
                    win.update()
                    time.sleep(.02)

                def bounds():
                    return tuple(canvas.coords(canvas.find_withtag('block:option_1')[0]))

                next(b for b in widgets(win, ttk.Button) if b.cget('text') == '+').invoke()
                before = bounds()
                x = round(before[0]+35-canvas.canvasx(0))
                y = round((before[1]+before[3])/2-canvas.canvasy(0))
                canvas.event_generate('<ButtonPress-1>', x=x, y=y)
                canvas.event_generate('<B1-Motion>', x=x+30, y=y+3, state=0x108)
                canvas.event_generate('<ButtonRelease-1>', x=x+30, y=y+3)
                choices = widgets(win, tk.Listbox)[0]
                self.assertEqual(choices.get(choices.curselection()[0]), 'option_1')
                while bounds() == before:
                    self.assertLess(time.monotonic(), deadline, 'Pygame did not redraw the moved answer')
                    win.update()
                    time.sleep(.02)
                self.assertAlmostEqual(bounds()[0]-before[0], 30, delta=2)
                old = bounds()
                deadline = time.monotonic()+4
                x = round(old[0]-canvas.canvasx(0))
                y = round((old[1]+old[3])/2-canvas.canvasy(0))
                canvas.event_generate('<ButtonPress-1>', x=x, y=y)
                canvas.event_generate('<B1-Motion>', x=x+27, y=y, state=0x108)
                while not canvas.find_withtag('drag_feedback'):
                    self.assertLess(time.monotonic(), deadline, 'Resize feedback missing while holding the mouse')
                    win.update()
                    time.sleep(.01)
                outline = next(item for item in canvas.find_withtag('drag_feedback') if canvas.type(item) == 'rectangle')
                new = canvas.coords(outline)
                self.assertAlmostEqual((old[2]-old[0]) - (new[2]-new[0]), 27, delta=2)
                canvas.event_generate('<ButtonRelease-1>', x=x+27, y=y)
                next(b for b in widgets(win, ttk.Button) if b.cget('text') == 'Lưu bố cục').invoke()
            except BaseException as exc:
                errors.append(exc)
                win.destroy()

        self.root.after(80, drive)
        saved = edit_layout(self.root, question, live_question=question)
        if errors:
            raise errors[0]
        self.assertGreater(saved['desktop']['option_1']['x'], 66)
        self.assertLess(saved['desktop']['option_1']['width'], 828)

    def test_drag_at_zoom_with_scrolled_origin(self):
        question = {'type': 'fill', 'prompt': 'Câu hỏi'}
        initial = {'input_area': {'x': 100/960, 'y': 750/640, 'width': 300/960, 'height': 50/640}}

        def edit(win):
            def button(label):
                return next(b for b in widgets(win, ttk.Button) if b.cget('text') == label)

            canvas = max(widgets(win, tk.Canvas), key=lambda w: w.winfo_width()*w.winfo_height())
            button('+').invoke()
            source_y = (16 + 775) * 1.1
            viewport_y = canvas.winfo_height() / 4
            scroll_height = float(canvas.cget('scrollregion').split()[3])
            canvas.yview_moveto((source_y - viewport_y) / scroll_height)
            sx = round((16 + 180)*1.1 - canvas.canvasx(0))
            sy = round(source_y - canvas.canvasy(0))
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
