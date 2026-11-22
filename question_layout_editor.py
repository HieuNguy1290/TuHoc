"""Stage 2: optional per-question visual layout editor (Tk only).

Does not modify Pygame drawing or input hitboxes. Coordinates are relative
and stored by the caller only after explicit confirmation.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from copy import deepcopy
from question_layout_store import layout_v2, validate_layout
from layout_render import DESKTOP, MOBILE, PAGE_LIMIT, fit_pixels, to_pixels, to_relative

DEFAULTS = {
    'question_text': dict(x=.06, y=.12, width=.88, height=.15, font_size=24),
    'question_image': dict(x=.31, y=.31, width=.38, height=.28),
    'audio_player': dict(x=.08, y=.64, width=.84, height=.09),
    'answer_area': dict(x=.10, y=.76, width=.80, height=.15),
    'input_area': dict(x=.08, y=.68, width=.82, height=.10),
    'dropdown_area': dict(x=.18, y=.58, width=.36, height=.08),
    'word_bank': dict(x=.07, y=.79, width=.85, height=.055),
}


def edit_layout(parent, question, initial=None, *, preview=None):
    """Open a modal editor. Return validated layout, or None if cancelled."""
    initial = validate_layout(initial or {})
    stored = initial
    if stored.get('version') in (2, 3):
        initial = {key: to_relative(rect, DESKTOP) for key, rect in stored['desktop'].items()}
    working = deepcopy(initial)
    saved_layout = deepcopy(initial)
    mobile_layout = {key: to_relative(rect, MOBILE) for key, rect in stored.get('mobile', {}).items()}
    saved_mobile = deepcopy(mobile_layout)
    desktop_layout = working
    history = []
    future = []
    result = [None]
    win = tk.Toplevel(parent)
    win.title('Studio bố cục câu hỏi')
    win.geometry('1200x820')
    # Use the OS maximized work area (excludes Windows taskbar), not -fullscreen.
    # Defer until the window is mapped so Windows can calculate its work area.
    def maximize_work_area():
        try:
            win.state('zoomed')
        except tk.TclError:
            try:
                win.attributes('-zoomed', True)
            except tk.TclError:
                pass
    win.after_idle(maximize_work_area)
    win.minsize(800, 600)
    win.transient(parent)
    win.grab_set()
    toolbar = ttk.Frame(win, padding=10)
    toolbar.pack(fill='x')
    viewport_var = tk.StringVar(value='Máy tính')
    view = ttk.Combobox(toolbar, values=('Máy tính', 'Điện thoại'), textvariable=viewport_var,
                        state='readonly', width=12)
    view.pack(side='left', padx=(0, 8))
    view.bind('<<ComboboxSelected>>', lambda _event: switch_view())
    snap = tk.BooleanVar(value=False)
    ttk.Checkbutton(toolbar, text='Bám lưới 8 px', variable=snap, command=lambda: redraw()).pack(side='left')
    main = ttk.Frame(win, padding=(12, 0, 12, 8))
    main.pack(fill='both', expand=True)
    metadata = ttk.Frame(main, width=180, padding=(0, 6, 8, 0))
    metadata.pack(side='left', fill='y')
    metadata.pack_propagate(False)
    ttk.Label(metadata, text='Câu hỏi', font=('Segoe UI', 12, 'bold')).pack(anchor='w')
    for title, key in (('Mã', 'id'), ('Chủ đề', 'theme'), ('Level', 'level'),
                       ('Lesson', 'lesson'), ('Dạng', 'type')):
        text = str(question.get(key) or '')
        if text:
            ttk.Label(metadata, text=f'{title} · {text}', wraplength=168).pack(anchor='w', pady=2)
    elements_list = tk.Listbox(metadata, exportselection=False, height=14, foreground='#1e293b')
    elements_list.pack(fill='both', expand=True, pady=(10, 5))
    ttk.Label(metadata, text='A, B… là vị trí hiển thị. Thứ tự có thể được xáo khi chạy.',
              wraplength=168, foreground='#475569').pack(anchor='w', pady=4)
    elements_list.bind('<<ListboxSelect>>', lambda _event: select_from_list())
    workspace = ttk.Frame(main)
    workspace.pack(side='left', fill='both', expand=True)
    ruler_top = tk.Canvas(workspace, height=28, bg='#edf2f7', highlightthickness=0)
    ruler_top.grid(row=0, column=1, sticky='ew')
    ruler_left = tk.Canvas(workspace, width=38, bg='#edf2f7', highlightthickness=0)
    ruler_left.grid(row=1, column=0, sticky='ns')
    canvas = tk.Canvas(workspace, bg='#e2e8f0', highlightthickness=1, takefocus=True)
    canvas.grid(row=1, column=1, sticky='nsew')
    yscroll = ttk.Scrollbar(workspace, orient='vertical', command=lambda *a: scroll_y(*a))
    yscroll.grid(row=1, column=2, sticky='ns')
    xscroll = ttk.Scrollbar(workspace, orient='horizontal', command=lambda *a: scroll_x(*a))
    xscroll.grid(row=2, column=1, sticky='ew')
    workspace.columnconfigure(1, weight=1)
    workspace.rowconfigure(1, weight=1)
    # Fixed design-space dimensions: window resizing never alters saved coordinates.
    page_w, page_h = DESKTOP
    max_page_h = page_h * PAGE_LIMIT
    extended_h = [max(page_h, min(max_page_h, int(max((v.get('y', 0) + v.get('height', 0)) for v in working.values()) * page_h + 250))) if working else page_h]
    page_origin_x, page_origin_y = 16, 16
    zoom = [1.0]
    zoom_var = tk.StringVar(value="100%")
    canvas.configure(scrollregion=(0, 0, (page_w+40)*zoom[0], (extended_h[0]+40)*zoom[0]))
    def scroll_x(*args):
        canvas.xview(*args)
        redraw()
    def scroll_y(*args):
        canvas.yview(*args)
        redraw()
    canvas.configure(xscrollcommand=xscroll.set, yscrollcommand=yscroll.set)
    def wheel(event):
        # Stop Tk's global/all wheel bindings from reaching the underlying app.
        if event.state & 0x0004:  # Ctrl + wheel: zoom editor only
            step = 1 if (event.delta > 0 or event.num == 4) else -1
            change_zoom(zoom[0] + step * .1)
        elif event.state & 0x0001:  # Shift + wheel: horizontal
            canvas.xview_scroll(-3 if (event.delta > 0 or event.num == 4) else 3, 'units')
            redraw()
        else:
            canvas.yview_scroll(-3 if (event.delta > 0 or event.num == 4) else 3, 'units')
            redraw()
        return 'break'

    def isolate_wheel(event):
        # Catch wheel events from editor controls too, preventing parent bind_all.
        return 'break'

    canvas.bind('<MouseWheel>', wheel)
    canvas.bind('<Button-4>', wheel)
    canvas.bind('<Button-5>', wheel)
    win.bind('<MouseWheel>', isolate_wheel)
    win.bind('<Button-4>', isolate_wheel)
    win.bind('<Button-5>', isolate_wheel)
    sidebar = ttk.Frame(main, width=220, padding=(12, 0))
    sidebar.pack(side='right', fill='y')
    sidebar.pack_propagate(False)
    ttk.Label(sidebar, text='Thuộc tính phần tử', font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(5, 12))
    selection = tk.StringVar(value='Chọn thành phần')
    ttk.Label(sidebar, textvariable=selection, wraplength=185).pack(anchor='w', pady=4)
    font_var = tk.IntVar(value=24)
    ttk.Label(sidebar, text='Cỡ chữ thành phần được chọn').pack(anchor='w', pady=(18, 4))
    font_spin = ttk.Spinbox(sidebar, from_=8, to=96, textvariable=font_var, width=8)
    font_spin.pack(anchor='w')
    ttk.Label(sidebar, text='Số câu và nút Hoàn thành được khóa.', wraplength=180, foreground='#64748b').pack(anchor='w', pady=22)
    fields = ttk.Frame(sidebar)
    fields.pack(anchor='w', pady=4)
    pixel_vars = {}
    for row, (field, label) in enumerate(zip(('x', 'y', 'width', 'height'), ('X', 'Y', 'W', 'H'))):
        ttk.Label(fields, text=label).grid(row=row, column=0, sticky='w', padx=(0, 8))
        variable = tk.StringVar()
        entry = ttk.Entry(fields, textvariable=variable, width=8)
        entry.grid(row=row, column=1, pady=2)
        entry.bind('<Return>', lambda _event: apply_pixels())
        pixel_vars[field] = variable
    ttk.Button(fields, text='Áp dụng (px)', command=lambda: apply_pixels()).grid(row=4, columnspan=2, sticky='ew')
    ttk.Label(sidebar, text='Khung 960 × 640 px. Nội dung có thể kéo xuống đến Y = 2560 px.',
              wraplength=180, foreground='#475569').pack(anchor='w', pady=6)
    active = [None]
    status = tk.StringVar(value='Đã nạp bố cục')
    scroll_job = None
    last_motion = None
    registered_motion = False
    preview_image = None
    canvas_image = None
    drag = [None]
    boxes = {}
    dims = [page_w, page_h]
    option_defaults = {}
    image_options = question.get('image_options') or []
    is_image_choice = question.get('type') == 'listening_image_choice' and isinstance(image_options, (list, tuple)) and bool(image_options)
    if is_image_choice:
        # Use the source option order: option_N corresponds to the Nth image.
        options = [str(item.get('label') or 'Ảnh đáp án %s' % chr(65+i))
                   if isinstance(item, dict) else 'Ảnh đáp án %s' % chr(65+i)
                   for i, item in enumerate(image_options)]
    else:
        options = question.get('options') or []
        if isinstance(options, str):
            options = [v.strip() for v in options.split('|') if v.strip()]
        if not isinstance(options, (list, tuple)):
            options = []
        options = [str(v) for v in options]
    if question.get('type') in {'image_multi_choice', 'listening_image_choice'} and image_options:
        options = [str(item.get('label') or item.get('image') or '') if isinstance(item, dict) else str(item)
                   for item in image_options]
    if question.get('type') == 'matching':
        from matching_widget import parse_pairs
        pairs = parse_pairs(options)
        options = [pair[side] for side in (0, 1) for pair in pairs]
    elif question.get('type') in {'image_letter_pick', 'image_sentence_fill'}:
        options = [*question.get('blank_answers', []), *question.get('distractors', [])]
    elif question.get('type') == 'picture_missing_letters':
        options = ['Kích thước ô chữ']
    options = options[:20]
    area_keys = ['question_text', 'question_image', 'audio_player', 'answer_area']
    if question.get('type') in {'image_write_answer', 'fill', 'listening_fill', 'error'}:
        area_keys.append('input_area')
    if question.get('type') in {'dropdown_fill_blank', 'inline_dropdown_fill'}:
        area_keys.append('dropdown_area')
    if question.get('type') in {'sentence_gaps', 'passage_gaps', 'conversation_gaps'}:
        area_keys.append('word_bank')
    area_keys.extend(el for el in initial if el in DEFAULTS and el not in area_keys)
    # Independent positions; no changes to correctness or answer ordering.
    for i, option in enumerate(options):
        key = 'option_%d' % i
        if is_image_choice:
            cols = 3 if len(options) > 4 else 2
            rows = (len(options) + cols - 1) // cols
            width = .25 if cols == 3 else .36
            height = min(.19, .42 / max(1, rows))
            x = .08 + (i % cols) * (.84 / cols)
            y = .46 + (i // cols) * (.45 / max(1, rows))
            option_defaults[key] = dict(x=x, y=y, width=width, height=height, font_size=18)
        else:
            option_defaults[key] = dict(x=.12, y=min(.91, .46+i*.095),
                                        width=.76, height=.075, font_size=18)

    elements = [*area_keys, *option_defaults]
    for el in elements:
        elements_list.insert('end', el)

    def current(el):
        base = option_defaults.get(el) or DEFAULTS[el]
        return {**base, **desktop_layout.get(el, {}), **working.get(el, {})}

    def select(el, from_list=False):
        active[0] = el
        selection.set(el or 'Chọn thành phần')
        if not from_list:
            elements_list.selection_clear(0, 'end')
            if el:
                row = elements.index(el)
                elements_list.selection_set(row)
                elements_list.see(row)
        if el:
            font_var.set(int(current(el).get('font_size', 24)))
        show_pixels()

    def select_from_list():
        rows = elements_list.curselection()
        if rows:
            select(elements[rows[0]], from_list=True)
            redraw()

    def switch_view():
        nonlocal page_w, page_h, max_page_h, working
        page_w, page_h = MOBILE if viewport_var.get() == 'Điện thoại' else DESKTOP
        max_page_h = page_h * PAGE_LIMIT
        dims[:] = [page_w, page_h]
        working = mobile_layout if viewport_var.get() == 'Điện thoại' else desktop_layout
        extended_h[0] = page_h
        for el in elements:
            expand_to(current(el))
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)
        show_pixels()
        redraw()

    def draft():
        result = layout_v2(desktop_layout)
        if mobile_layout or 'mobile' in stored:
            result['mobile'] = {el: fit_pixels(to_pixels(rect, MOBILE), MOBILE)
                                for el, rect in mobile_layout.items()}
        if stored.get('version') == 3:
            result.update(version=3, extras=stored['extras'])
        return validate_layout(result)

    def dirty():
        return desktop_layout != saved_layout or mobile_layout != saved_mobile

    def show_frame(size, pixels):
        nonlocal preview_image
        from PIL import Image
        preview_image = Image.frombytes('RGB', size, pixels)
        redraw()

    def try_preview():
        if preview is None:
            return
        try:
            if hasattr(parent, 'media_file'):
                win.media_file = parent.media_file
            current_layout = draft()

            def show_current_frame(size, pixels):
                if draft() == current_layout:
                    show_frame(size, pixels)

            preview(current_layout, win, show_current_frame)
        except (ValueError, RuntimeError, OSError) as exc:
            messagebox.showwarning('Xem trước', str(exc), parent=win)

    def expand_to(values):
        needed = round((values['y'] + values['height']) * page_h) + 80
        extended_h[0] = max(extended_h[0], min(max_page_h, needed))

    def show_pixels():
        if active[0]:
            values = current(active[0])
            for field, variable in pixel_vars.items():
                scale = page_w if field in ('x', 'width') else page_h
                variable.set(str(round(values[field] * scale)))
        else:
            for variable in pixel_vars.values():
                variable.set('')

    def apply_pixels():
        if not active[0]:
            return
        try:
            values = current(active[0])
            for field, variable in pixel_vars.items():
                scale = page_w if field in ('x', 'width') else page_h
                values[field] = int(variable.get()) / scale
            if values['width'] <= 0 or values['height'] <= 0:
                raise ValueError('W và H phải lớn hơn 0.')
            validate_layout({active[0]: values})
        except ValueError as exc:
            messagebox.showerror('Tọa độ không hợp lệ', str(exc), parent=win)
            return
        snapshot()
        working[active[0]] = values
        expand_to(values)
        redraw()

    def capture():
        return deepcopy(desktop_layout), deepcopy(mobile_layout)

    def snapshot():
        nonlocal preview_image
        preview_image = None
        history.append(capture())
        future.clear()
        if len(history) > 50:
            history.pop(0)

    def redraw(_event=None):
        nonlocal canvas_image
        canvas.delete('all')
        status.set('Có thay đổi chưa lưu' if dirty() else 'Đã nạp bố cục')
        w, h = page_w, page_h
        canvas.configure(scrollregion=(0, 0, (page_w+40)*zoom[0], (extended_h[0]+40)*zoom[0]))
        ox, oy = page_origin_x, page_origin_y
        canvas.create_rectangle(ox, oy, ox+w, oy+extended_h[0], fill='white', outline='#94a3b8')
        live = preview_image is not None and viewport_var.get() == 'Máy tính'
        if live:
            from PIL import Image, ImageTk
            size = tuple(round(value*zoom[0]) for value in preview_image.size)
            image = preview_image.resize(size, Image.Resampling.LANCZOS)
            canvas_image = ImageTk.PhotoImage(image, master=canvas)
            canvas.create_image(ox, oy, image=canvas_image, anchor='nw')
        else:
            canvas_image = None
        if snap.get():
            for x in range(0, w, 16):
                canvas.create_line(ox+x, oy, ox+x, oy+extended_h[0], fill='#e2e8f0')
            for y in range(0, extended_h[0], 16):
                canvas.create_line(ox, oy+y, ox+w, oy+y, fill='#e2e8f0')
        canvas.create_line(ox, oy+h, ox+w, oy+h, fill='#f59e0b', dash=(6, 4))
        ruler_top.delete('all')
        ruler_left.delete('all')
        ruler_top.create_text(7, 13, anchor='w', text='px', fill='#64748b', font=('Segoe UI', 8))
        x0, x1 = canvas.canvasx(0), canvas.canvasx(canvas.winfo_width())
        y0, y1 = canvas.canvasy(0), canvas.canvasy(canvas.winfo_height())
        for n in range(0, w+1, 25):
            xx = (ox+n)*zoom[0]-x0
            if 0 <= xx <= ruler_top.winfo_width():
                major = n % 100 == 0
                ruler_top.create_line(xx, 28, xx, 8 if major else 19, fill='#64748b')
                if major:
                    ruler_top.create_text(xx+3, 3, anchor='nw', text=str(n), font=('Segoe UI', 8), fill='#475569')
        for n in range(0, extended_h[0]+1, 25):
            yy = (oy+n)*zoom[0]-y0
            if 0 <= yy <= ruler_left.winfo_height():
                major = n % 100 == 0
                ruler_left.create_line(38, yy, 16 if major else 29, yy, fill='#64748b')
                if major:
                    ruler_left.create_text(2, yy+2, anchor='nw', text=str(n), font=('Segoe UI', 8), fill='#475569')
        if not live:
            canvas.create_text(ox+w-18, oy+22, text='Câu: --/--  (khóa)', anchor='e', fill='#475569', font=('Segoe UI', 11, 'bold'))
        boxes.clear()
        for el in elements:
            v = current(el)
            x, y, width, height = [v[k] for k in ('x', 'y', 'width', 'height')]
            rect = (ox+x*w, oy+y*h, ox+(x+width)*w, oy+(y+height)*h)
            boxes[el] = rect
            selected = active[0] == el
            canvas.create_rectangle(*rect, fill='' if live else '#eff6ff' if selected else '#f8fafc', outline='#2563eb' if selected else '#cbd5e1', width=2 if selected else 1)
            if live and not selected:
                continue
            if live:
                canvas.create_rectangle(rect[2]-9, rect[3]-9, rect[2]+3, rect[3]+3, fill='#2563eb', outline='white')
                continue
            if el == 'question_text':
                prompt = str(question.get('prompt') or 'Nội dung câu hỏi')
                canvas.create_text(rect[0]+9, rect[1]+8, text=prompt, anchor='nw', width=max(40, rect[2]-rect[0]-18), font=('Segoe UI', min(40, int(v['font_size'])), 'bold' if '**' in prompt else 'normal'), fill='#1e293b')
            elif el == 'question_image':
                canvas.create_text((rect[0]+rect[2])/2, (rect[1]+rect[3])/2, text='ẢNH CÂU HỎI\n(vùng bố cục)', justify='center', fill='#475569', font=('Segoe UI', 12))
            elif el == 'audio_player':
                canvas.create_text((rect[0]+rect[2])/2, (rect[1]+rect[3])/2, text='▶  ~  ~  ~  ~  ~  ~  ~     WAVEFORM', fill='#334155', font=('Segoe UI', 12))
            elif el in ('answer_area', 'input_area', 'dropdown_area', 'word_bank'):
                labels = {'answer_area': 'VÙNG ĐÁP ÁN', 'input_area': 'Ô NHẬP', 'dropdown_area': 'MENU CHỌN', 'word_bank': 'NGÂN HÀNG TỪ'}
                canvas.create_text(rect[0]+8, rect[1]+8, text=labels[el], anchor='nw', fill='#64748b', font=('Segoe UI', 10))
            else:
                i = int(el.split('_')[1])
                if is_image_choice:
                    canvas.create_text((rect[0]+rect[2])/2, (rect[1]+rect[3])/2,
                                       text='%s\n%s' % (chr(65+i), options[i]),
                                       justify='center', width=max(40,rect[2]-rect[0]-16),
                                       fill='#1e293b', font=('Segoe UI', min(40,int(v.get('font_size',18)))))
                else:
                    canvas.create_text(rect[0]+8, (rect[1]+rect[3])/2,
                                       text='%s · Vị trí %d' % (chr(65+i), i+1),
                                       anchor='w', width=max(40,rect[2]-rect[0]-16),
                                       fill='#1e293b', font=('Segoe UI', min(40,int(v.get('font_size',18)))))
            canvas.create_text(rect[0]+4, rect[1]-4, text=el, anchor='sw', fill='#2563eb', font=('Segoe UI', 9))
            if selected:
                canvas.create_rectangle(rect[2]-9, rect[3]-9, rect[2]+3, rect[3]+3, fill='#2563eb', outline='white')
        if not live:
            canvas.create_rectangle(ox+w-155, oy+h-64, ox+w-24, oy+h-22, fill='#176347', outline='')
            canvas.create_text(ox+w-89, oy+h-43, text='Hoàn thành (khóa)', fill='white', font=('Segoe UI', 10, 'bold'))
        # Scale the complete design in view only. Saved layout remains unchanged.
        if zoom[0] != 1:
            canvas.scale('all', 0, 0, zoom[0], zoom[0])
            for item in canvas.find_all():
                if canvas.type(item) == 'text':
                    f = canvas.itemcget(item, 'font').split()
                    if len(f) >= 2:
                        try:
                            old_size = int(f[-2] if f[-1] in ('bold', 'normal', 'italic') else f[-1])
                            family = ' '.join(f[:-2] if f[-1] in ('bold', 'normal', 'italic') else f[:-1])
                            style = f[-1] if f[-1] in ('bold', 'normal', 'italic') else ''
                            canvas.itemconfigure(item, font=(family or 'Segoe UI', max(6, round(old_size*zoom[0])), style))
                        except (ValueError, tk.TclError):
                            pass
            for key, rect in list(boxes.items()):
                boxes[key] = tuple(v * zoom[0] for v in rect)


    def hit(x, y):
        for el in reversed(list(boxes)):
            a,b,c,d = boxes[el]
            if a <= x <= c and b <= y <= d:
                return el, ('resize' if x >= c-18 and y >= d-18 else 'move')
        return None, None

    def down(event):
        nonlocal registered_motion
        canvas.focus_set()
        el, mode = hit(canvas.canvasx(event.x), canvas.canvasy(event.y))
        select(el)
        registered_motion = False
        if el:
            drag[0] = (el, mode, canvas.canvasx(event.x), canvas.canvasy(event.y), deepcopy(current(el)))
        else:
            drag[0] = None
        redraw()

    def repeat_motion():
        nonlocal scroll_job
        scroll_job = None
        if drag[0] and last_motion is not None:
            move(last_motion)

    def release(_event=None):
        nonlocal scroll_job, last_motion
        drag[0] = None
        last_motion = None
        if scroll_job is not None:
            canvas.after_cancel(scroll_job)
            scroll_job = None

    def move(event):
        nonlocal scroll_job, last_motion, registered_motion
        last_motion = event
        if not drag[0] or not dims[0] or not dims[1]:
            return
        el, mode, ox, oy, start = drag[0]
        # Scroll before calculating drag deltas.  The pointer coordinates must
        # be converted with the *current* viewport offset, not the previous one.
        edge = 28
        view_w, view_h = canvas.winfo_width(), canvas.winfo_height()
        if event.y >= view_h-edge:
            if canvas.yview()[1] >= .95 and extended_h[0] < max_page_h:
                extended_h[0] = min(max_page_h, extended_h[0] + 160)
                canvas.configure(scrollregion=(0, 0, (page_w+40)*zoom[0], (extended_h[0]+40)*zoom[0]))
            canvas.yview_scroll(2, 'units')
        elif event.y <= edge:
            canvas.yview_scroll(-2, 'units')
        if event.x >= view_w-edge and (page_w+40)*zoom[0] > view_w:
            canvas.xview_scroll(2, 'units')
        elif event.x <= edge:
            canvas.xview_scroll(-2, 'units')
        dx = (canvas.canvasx(event.x)-ox)/(dims[0]*zoom[0])
        dy = (canvas.canvasy(event.y)-oy)/(dims[1]*zoom[0])
        v = dict(start)
        if snap.get():
            dx = round(dx*page_w/8)*8/page_w
            dy = round(dy*page_h/8)*8/page_h
        vertical_limit = max_page_h / page_h
        if mode == 'move':
            v['x'] = max(0., min(1.-v['width'], start['x']+dx))
            v['y'] = max(0., min(vertical_limit-v['height'], start['y']+dy))
        else:
            v['width'] = min(1.-v['x'], max(1/page_w, start['width']+dx))
            v['height'] = min(vertical_limit-v['y'], max(1/page_h, start['height']+dy))
        if v != start and not registered_motion:
            snapshot()
            registered_motion = True
        if registered_motion:
            working[el] = v
        auto = event.y >= view_h-edge or event.y <= edge or event.x >= view_w-edge or event.x <= edge
        if auto and scroll_job is None:
            scroll_job = canvas.after(60, repeat_motion)
        expand_to(v)
        show_pixels()
        redraw()

    def font_change(_event=None):
        if active[0] != 'question_text' and active[0] not in option_defaults:
            return
        try:
            value = int(font_var.get())
        except (ValueError, tk.TclError):
            return
        if 8 <= value <= 96:
            snapshot()
            working[active[0]] = {**current(active[0]), 'font_size': value}
            redraw()

    def restore(state):
        nonlocal preview_image
        preview_image = None
        for target, values in zip((desktop_layout, mobile_layout), state):
            target.clear()
            target.update(deepcopy(values))
        for el in elements:
            expand_to(current(el))
        show_pixels()
        redraw()

    def undo():
        if history:
            future.append(capture())
            restore(history.pop())

    def redo():
        if future:
            history.append(capture())
            restore(future.pop())

    def apply_template():
        from layout_templates import template_for
        preset = template_for(question.get('type'))['desktop']
        snapshot()
        working.clear()
        working.update({el: to_relative(rect, DESKTOP) for el, rect in preset.items()})
        for el in elements:
            expand_to(current(el))
        show_pixels()
        redraw()

    def reset():
        if messagebox.askyesno('Khôi phục', 'Khôi phục bố cục mặc định của câu hỏi này?', parent=win):
            snapshot()
            working.clear()
            show_pixels()
            redraw()

    def restore_saved():
        if dirty():
            snapshot()
            restore((saved_layout, saved_mobile))

    def cancel():
        if dirty() and not messagebox.askyesno('Chưa lưu bố cục',
                                              'Bỏ các thay đổi bố cục chưa lưu?', parent=win):
            return
        release()
        win.destroy()

    def save():
        try:
            validate_layout(working)
            result[0] = draft() if dirty() else stored
        except ValueError as exc:
            messagebox.showerror('Bố cục không hợp lệ', str(exc), parent=win)
            return
        release()
        win.destroy()

    def grow_page():
        extended_h[0] = min(max_page_h, extended_h[0] + 500)
        redraw()

    def change_zoom(value):
        value = max(.25, min(2.0, round(float(value), 2)))
        old = zoom[0]
        if value == old:
            return
        # Keep the viewport center anchored to the same design coordinate.
        cx = canvas.canvasx(canvas.winfo_width()/2) / old
        cy = canvas.canvasy(canvas.winfo_height()/2) / old
        zoom[0] = value
        zoom_var.set('%d%%' % round(value*100))
        redraw()
        total_w = (page_w+40)*value
        total_h = (extended_h[0]+40)*value
        canvas.xview_moveto(max(0, (cx*value-canvas.winfo_width()/2)/max(total_w, 1)))
        canvas.yview_moveto(max(0, (cy*value-canvas.winfo_height()/2)/max(total_h, 1)))
        redraw()

    zoom_controls = ttk.Frame(toolbar)
    zoom_controls.pack(side='right', padx=8)
    ttk.Button(zoom_controls, text='−', width=3, command=lambda: change_zoom(zoom[0]-.1)).pack(side='left')
    ttk.Label(zoom_controls, textvariable=zoom_var, width=6, anchor='center').pack(side='left')
    ttk.Button(zoom_controls, text='+', width=3, command=lambda: change_zoom(zoom[0]+.1)).pack(side='left')
    ttk.Button(zoom_controls, text='100%', command=lambda: change_zoom(1)).pack(side='left', padx=3)

    ttk.Button(toolbar, text='Mở rộng trang +500 px', command=grow_page).pack(side='right', padx=4)
    canvas.bind('<Configure>', redraw)
    ruler_top.bind('<Configure>', redraw)
    ruler_left.bind('<Configure>', redraw)
    def toggle_fullscreen():
        # Maximize within the OS work area, leaving the taskbar accessible.
        # Avoid -fullscreen, which covers the taskbar on Windows.
        try:
            maximized = win.state() == 'zoomed'
            win.state('normal' if maximized else 'zoomed')
        except tk.TclError:
            maximized = bool(win.attributes('-zoomed'))
            win.attributes('-zoomed', not maximized)
        fullscreen_btn.configure(text='Phóng to cửa sổ' if maximized else 'Thu nhỏ cửa sổ')
        win.after_idle(redraw)
    fullscreen_btn = ttk.Button(toolbar, text='Thu nhỏ cửa sổ', command=toggle_fullscreen)
    fullscreen_btn.pack(side='right', padx=4)
    ttk.Label(toolbar, text='Thước: px | Ctrl+cuộn: zoom | Shift+cuộn: ngang').pack(side='right', padx=10)
    canvas.bind('<ButtonPress-1>', down)
    canvas.bind('<B1-Motion>', move)
    canvas.bind('<ButtonRelease-1>', release)
    font_spin.bind('<Return>', font_change)
    font_spin.bind('<FocusOut>', font_change)
    edit_controls = ttk.Frame(sidebar)
    edit_controls.pack(fill='x', pady=8)
    for label, command in (('Dùng mẫu', apply_template), ('Mặc định', reset),
                           ('Hoàn tác', undo), ('Làm lại', redo), ('Khôi phục đã lưu', restore_saved)):
        ttk.Button(edit_controls, text=label, command=command).pack(fill='x', pady=2)
    win.bind('<Control-z>', lambda _e: undo())
    win.bind('<Control-y>', lambda _e: redo())
    footer = ttk.Frame(win, padding=10)
    footer.pack(fill='x')
    ttk.Label(footer, textvariable=status).pack(side='left')
    if preview is not None:
        ttk.Button(footer, text='Xem trước Pygame', command=try_preview).pack(side='left', padx=12)
    ttk.Button(footer, text='Lưu bố cục', command=save).pack(side='right', padx=5)
    ttk.Button(footer, text='Hủy', command=cancel).pack(side='right')
    # ESC closes the modal editor as before; maximize is not exclusive fullscreen.
    win.bind('<Escape>', lambda e: cancel())
    win.protocol('WM_DELETE_WINDOW', cancel)
    win.wait_window()
    return result[0]


def edit_question_layout(parent, question):
    """Edit a question's persisted layout and return an updated question copy.

    The caller must replace the question in its collection and save that
    collection to JSON. Cancelling returns None and never mutates the input.
    """
    from question_layout_store import get_layout, set_layout

    if not isinstance(question, dict):
        raise TypeError('question must be a dictionary')
    saved = edit_layout(parent, question, initial=get_layout(question))
    if saved is None:
        return None
    return set_layout(question, saved)
