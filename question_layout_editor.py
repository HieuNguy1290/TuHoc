"""Stage 2: optional per-question visual layout editor (Tk only).

Does not modify Pygame drawing or input hitboxes. Coordinates are relative
and stored by the caller only after explicit confirmation.
"""
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
from question_layout_store import GEOMETRY, IMAGE_FITS, layout_v2, validate_layout
from layout_render import DESKTOP, MOBILE, PAGE_LIMIT, fit_pixels, to_pixels, to_relative

from layout_registry import DEFAULTS, controls_for


def resize_rect(start, mode, dx, dy, screen, *, keep_ratio=False):
    """Resize on the anchored edges using logical pixels for minimum size."""
    sw, sh = screen
    x,y,w,h = (start[field] for field in ('x','y','width','height'))
    right,bottom = x+w,y+h
    if keep_ratio and w > 0 and h > 0:
        direction_x = -1 if 'w' in mode else 1
        direction_y = -1 if 'n' in mode else 1
        cap_w = right if direction_x < 0 else 1-x
        cap_h = bottom if direction_y < 0 else PAGE_LIMIT-y
        dx_scale,dy_scale=direction_x*dx/w,direction_y*dy/h
        change=dx_scale if abs(dx_scale)>=abs(dy_scale) else dy_scale
        scale=max(1/min(w*sw,h*sh),min(cap_w/w,cap_h/h,1+change))
        nw,nh=w*scale,h*scale
        return {**start,'x':right-nw if direction_x<0 else x,
                'y':bottom-nh if direction_y<0 else y,'width':nw,'height':nh}
    if 'w' in mode:
        x=max(0,min(right-1/sw,x+dx))
    if 'e' in mode:
        right=min(1,max(x+1/sw,right+dx))
    if 'n' in mode:
        y=max(0,min(bottom-1/sh,y+dy))
    if 's' in mode:
        bottom=min(PAGE_LIMIT,max(y+1/sh,bottom+dy))
    return {**start,'x':x,'y':y,'width':right-x,'height':bottom-y}


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
    extras = {entry['id']: deepcopy(entry) for entry in stored.get('extras', [])}
    saved_extras = deepcopy(extras)
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
    ttk.Button(toolbar, text='+ Văn bản', command=lambda: add_text()).pack(side='left', padx=4)
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
        draw_rulers()
    def scroll_y(*args):
        canvas.yview(*args)
        draw_rulers()
    canvas.configure(xscrollcommand=xscroll.set, yscrollcommand=yscroll.set)
    def wheel(event):
        # Stop Tk's global/all wheel bindings from reaching the underlying app.
        if event.state & 0x0004:  # Ctrl + wheel: zoom editor only
            step = 1 if (event.delta > 0 or event.num == 4) else -1
            change_zoom(zoom[0] + step * .1)
        elif event.state & 0x0001:  # Shift + wheel: horizontal
            canvas.xview_scroll(-3 if (event.delta > 0 or event.num == 4) else 3, 'units')
            draw_rulers()
        else:
            canvas.yview_scroll(-3 if (event.delta > 0 or event.num == 4) else 3, 'units')
            draw_rulers()
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
    fit_var = tk.StringVar(value='contain')
    fit_select = ttk.Combobox(sidebar, values=IMAGE_FITS, textvariable=fit_var,
                              state='readonly', width=10)
    fit_select.bind('<<ComboboxSelected>>', lambda _e: change_fit())
    text_tools = ttk.Frame(sidebar)
    bold_var = tk.BooleanVar()
    italic_var = tk.BooleanVar()
    align_var = tk.StringVar(value='left')
    ttk.Checkbutton(text_tools, text='Đậm', variable=bold_var,
                    command=lambda: change_text_style(bold=bold_var.get())).pack(side='left')
    ttk.Checkbutton(text_tools, text='Nghiêng', variable=italic_var,
                    command=lambda: change_text_style(italic=italic_var.get())).pack(side='left')
    align_select = ttk.Combobox(text_tools, values=('left', 'center', 'right'),
                                textvariable=align_var, state='readonly', width=7)
    align_select.pack(side='left')
    align_select.bind('<<ComboboxSelected>>', lambda _e: change_text_style(align=align_var.get()))
    colors = ttk.Frame(sidebar)
    ttk.Button(colors, text='Màu chữ', command=lambda: choose_color('color')).pack(side='left')
    ttk.Button(colors, text='Nền', command=lambda: choose_color('bg')).pack(side='left')
    ttk.Button(colors, text='Xóa nền', command=lambda: change_text_style(bg='')).pack(side='left')
    active = [None]
    status = tk.StringVar(value='Đã nạp bố cục')
    scroll_job = None
    last_motion = None
    registered_motion = False
    preview_image = None
    canvas_image = None
    drag = [None]
    boxes = {}
    images = {}
    edit_widget = None
    block_items = {}
    block_order = ()
    page_background = None
    drag_visual = None
    image_ref = question.get('_pygame_image') or question.get('image')
    image_path = None
    if image_ref:
        resolve = getattr(parent, 'media_file', None)
        image_path = Path((resolve(image_ref) if resolve else None) or image_ref)
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
    controls = controls_for(question.get('type'))
    area_keys = [key for key in controls.editable if key in DEFAULTS]
    if not area_keys and 'option_N' not in controls.editable:
        ttk.Label(metadata,text='Dạng này chỉ hỗ trợ hộp văn bản.',
                  wraplength=168).pack(anchor='w',pady=4)
    if 'option_N' not in controls.editable:
        options = []
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

    system_elements = [*area_keys, *option_defaults]
    elements = []

    def sync_elements():
        elements[:] = [*system_elements, *sorted(extras, key=lambda key: extras[key]['z'])]
        elements_list.delete(0, 'end')
        for key in elements:
            label = (extras[key]['text'].replace('\n', ' ')[:32] or 'Văn bản') if key in extras else key
            elements_list.insert('end', label)
        if active[0] not in elements:
            active[0] = None
        select(active[0])

    def current(el):
        if el in extras:
            extra = extras[el]
            is_mobile = working is mobile_layout and 'mobile' in extra
            frame = 'mobile' if is_mobile else 'desktop'
            screen = MOBILE if is_mobile else DESKTOP
            return to_relative(extra[frame], screen)
        base = option_defaults.get(el) or DEFAULTS[el]
        return {**base, **desktop_layout.get(el, {}), **working.get(el, {})}

    def select(el, from_list=False):
        active[0] = el
        selection.set('Hộp văn bản' if el in extras else el or 'Chọn thành phần')
        for widget in (fit_select, text_tools, colors):
            widget.pack_forget()
        if el == 'question_image':
            fit_var.set(current(el).get('image_fit', 'contain'))
            fit_select.pack(anchor='w', pady=2)
        if el in extras:
            extra = extras[el]
            bold_var.set(extra['bold'])
            italic_var.set(extra['italic'])
            align_var.set(extra['align'])
            text_tools.pack(anchor='w')
            colors.pack(anchor='w', pady=2)
        if not from_list:
            elements_list.selection_clear(0, 'end')
            if el:
                row = elements.index(el)
                elements_list.selection_set(row)
                elements_list.see(row)
        if el:
            font_var.set(int(extras[el]['font_size'] if el in extras else current(el).get('font_size', 24)))
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
        if stored.get('version') == 3 or extras:
            result.update(version=3, extras=list(extras.values()))
        return validate_layout(result)

    def dirty():
        return desktop_layout != saved_layout or mobile_layout != saved_mobile or extras != saved_extras

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
            validate_layout({'question_text' if active[0] in extras else active[0]: values})
        except ValueError as exc:
            messagebox.showerror('Tọa độ không hợp lệ', str(exc), parent=win)
            return
        snapshot()
        set_geometry(active[0], values)
        expand_to(values)
        redraw()

    def capture():
        return deepcopy(desktop_layout), deepcopy(mobile_layout), deepcopy(extras)

    def snapshot():
        nonlocal preview_image
        preview_image = None
        history.append(capture())
        future.clear()
        if len(history) > 50:
            history.pop(0)


    def set_geometry(key, values):
        if key in extras:
            screen = tuple(dims)
            frame = 'mobile' if screen == MOBILE else 'desktop'
            rect = {k: values[k] for k in GEOMETRY}
            extras[key][frame] = fit_pixels(to_pixels(rect, screen), screen)
        else:
            working[key] = values

    def add_text(copy=None):
        if len(extras) >= 20:
            status.set('Mỗi câu có tối đa 20 hộp văn bản.')
            return
        snapshot()
        key = 'text_' + uuid4().hex
        width, height = min(225, page_w), 65
        x = round((canvas.canvasx(canvas.winfo_width()/2)/zoom[0])-page_origin_x-width/2)
        y = round((canvas.canvasy(canvas.winfo_height()/2)/zoom[0])-page_origin_y-height/2)
        rect = dict(x=max(0,min(page_w-width,x)), y=max(0,min(max_page_h-height,y)),
                    width=width, height=height)
        desktop = rect if working is desktop_layout else fit_pixels(
            to_pixels(to_relative(rect,MOBILE),DESKTOP),DESKTOP)
        extra = dict(id=key, kind='text', text='Văn bản mới', desktop=desktop, font_size=22,
                     bold=False, italic=False, color='#1e293b', bg='', align='left',
                     z=max((item['z'] for item in extras.values()),default=-1)+1)
        if copy is not None:
            extra.update({k: copy[k] for k in ('text','font_size','bold','italic','color','bg','align')})
        if working is mobile_layout:
            extra['mobile'] = rect
        extras[key] = extra
        sync_elements()
        select(key)
        expand_to(current(key))
        canvas.focus_set()
        redraw()

    def change_fit():
        if active[0] == 'question_image' and current(active[0]).get('image_fit') != fit_var.get():
            snapshot()
            set_geometry(active[0], {**current(active[0]), 'image_fit': fit_var.get()})
            redraw()

    def change_text_style(**values):
        key = active[0]
        if key in extras and any(extras[key][field] != value for field, value in values.items()):
            snapshot()
            extras[key].update(values)
            sync_elements()
            redraw()

    def choose_color(field):
        if active[0] in extras:
            _, value = colorchooser.askcolor(extras[active[0]][field] or '#ffffff', parent=win)
            if value:
                change_text_style(**{field: value})

    def delete_text(_event=None):
        if active[0] in extras:
            snapshot()
            del extras[active[0]]
            sync_elements()
            redraw()
        return 'break'

    def edit_text(event):
        nonlocal edit_widget
        key, _ = hit(canvas.canvasx(event.x), canvas.canvasy(event.y))
        if key not in extras or edit_widget is not None:
            return 'break'
        release()
        x1,y1,x2,y2 = boxes[key]
        editor = tk.Text(canvas, wrap='word', undo=True, height=2)
        edit_widget = editor
        editor.insert('1.0', extras[key]['text'])
        editor.tag_add('sel', '1.0', 'end-1c')
        window = canvas.create_window(x1,y1,window=editor,anchor='nw',
                                      width=max(70,x2-x1),height=max(36,y2-y1))
        def finish(commit):
            nonlocal edit_widget
            if edit_widget is not editor:
                return 'break'
            value = editor.get('1.0','end-1c')
            if commit and len(value) > 500:
                status.set('Hộp văn bản có tối đa 500 ký tự.')
                editor.after_idle(editor.focus_set)
                return 'break'
            edit_widget = None
            canvas.delete(window)
            editor.destroy()
            if commit:
                change_text_style(text=value)
            canvas.focus_set()
            return 'break'
        editor.bind('<Return>',lambda _e:finish(True))
        editor.bind('<Escape>',lambda _e:finish(False))
        editor.bind('<FocusOut>',lambda _e:finish(True))
        editor.focus_set()
        return 'break'

    handles = {'nw':(0,0), 'n':(.5,0), 'ne':(1,0), 'w':(0,.5),
               'e':(1,.5), 'sw':(0,1), 's':(.5,1), 'se':(1,1)}
    cursors = dict(nw='top_left_corner', n='top_side', ne='top_right_corner',
                   w='left_side', e='right_side', sw='bottom_left_corner',
                   s='bottom_side', se='bottom_right_corner')

    def draw_block(el, live):
        v = current(el)
        x,y,w,h = (v[k] for k in ('x','y','width','height'))
        scale = zoom[0]
        rect = ((page_origin_x+x*page_w)*scale, (page_origin_y+y*page_h)*scale,
                (page_origin_x+(x+w)*page_w)*scale, (page_origin_y+(y+h)*page_h)*scale)
        a,b,c,d = rect
        boxes[el] = rect
        selected = active[0] == el
        tag = 'block:'+el
        extra = extras.get(el)
        fill = '' if live else (extra['bg'] if extra else '#eff6ff' if selected else '#f8fafc')
        canvas.create_rectangle(*rect, fill=fill, outline='#2563eb' if selected else '#cbd5e1',
                                width=2 if selected else 1, tags=tag)

        def text(x, y, value, size=12, style='normal', **options):
            canvas.create_text(x,y,text=value,font=('Segoe UI',max(6,round(size*scale)),style),
                               tags=tag,**options)

        if not live:
            if extra:
                anchor = {'left':'nw','center':'n','right':'ne'}[extra['align']]
                x = {'left':a,'center':(a+c)/2,'right':c}[extra['align']]
                style = ' '.join(name for name in ('bold','italic') if extra[name]) or 'normal'
                text(x,b,extra['text'],extra['font_size'],style,anchor=anchor,
                     width=max(1,c-a),justify=extra['align'],fill=extra['color'])
            elif el == 'question_text':
                prompt = str(question.get('prompt') or 'Nội dung câu hỏi')
                text(a+9,b+8,prompt,min(40,int(v['font_size'])),
                     'bold' if '**' in prompt else 'normal',anchor='nw',width=max(40,c-a-18),fill='#1e293b')
            elif el == 'question_image':
                image = None
                if image_path is not None:
                    from layout_images import fitted_image
                    from PIL import ImageTk
                    try:
                        source = fitted_image(image_path,(round(c-a),round(d-b)),v.get('image_fit','contain'))
                        image = ImageTk.PhotoImage(source, master=canvas)
                    except (OSError, ValueError, tk.TclError):
                        pass
                if image is not None:
                    images[el] = image
                    canvas.create_image((a+c)/2,(b+d)/2,image=image,tags=tag)
                else:
                    text((a+c)/2,(b+d)/2,'ẢNH CÂU HỎI\n(vùng bố cục)',justify='center',fill='#475569')
            elif el == 'audio_player':
                text((a+c)/2,(b+d)/2,'▶  ~  ~  ~  ~  ~  ~  ~     WAVEFORM',fill='#334155')
            elif el in ('answer_area','input_area','dropdown_area','word_bank'):
                labels = {'answer_area':'VÙNG ĐÁP ÁN','input_area':'Ô NHẬP',
                          'dropdown_area':'MENU CHỌN','word_bank':'NGÂN HÀNG TỪ'}
                text(a+8,b+8,labels[el],10,anchor='nw',fill='#64748b')
            else:
                i = int(el.split('_')[1])
                label = '%s\n%s' % (chr(65+i), options[i]) if is_image_choice else '%s · Vị trí %d' % (chr(65+i),i+1)
                text((a+c)/2 if is_image_choice else a+8,(b+d)/2,label,
                     min(40,int(v.get('font_size',18))),anchor='center' if is_image_choice else 'w',
                     width=max(40,c-a-16),fill='#1e293b')
            if not extra:
                text(a+4,b-4,el,9,anchor='sw',fill='#2563eb')
        if selected:
            for rx,ry in handles.values():
                px,py=a+(c-a)*rx,b+(d-b)*ry
                canvas.create_rectangle(px-4,py-4,px+4,py+4,fill='#2563eb',outline='white',tags=tag)
        block_items[el] = tag
        return rect


    def redraw(_event=None):
        nonlocal canvas_image, page_background, block_order
        canvas.delete('all')
        images.clear()
        block_items.clear()
        boxes.clear()
        status.set('Có thay đổi chưa lưu' if dirty() else 'Đã nạp bố cục')
        scale = zoom[0]
        w,h = page_w*scale,page_h*scale
        ox,oy = page_origin_x*scale,page_origin_y*scale
        limit = extended_h[0]*scale
        canvas.configure(scrollregion=(0,0,(page_w+40)*scale,(extended_h[0]+40)*scale))
        page_background = canvas.create_rectangle(ox,oy,ox+w,oy+limit,fill='white',outline='#94a3b8')
        live = preview_image is not None and viewport_var.get() == 'Máy tính'
        if live:
            from PIL import Image, ImageTk
            size = tuple(round(value*scale) for value in preview_image.size)
            canvas_image = ImageTk.PhotoImage(preview_image.resize(size,Image.Resampling.LANCZOS),master=canvas)
            canvas.create_image(ox,oy,image=canvas_image,anchor='nw')
        else:
            canvas_image = None
        if snap.get():
            for x in range(0,page_w,16):
                canvas.create_line(ox+x*scale,oy,ox+x*scale,oy+limit,fill='#e2e8f0')
            for y in range(0,extended_h[0],16):
                canvas.create_line(ox,oy+y*scale,ox+w,oy+y*scale,fill='#e2e8f0')
        canvas.create_line(ox,oy+h,ox+w,oy+h,fill='#f59e0b',dash=(6,4))
        draw_rulers()
        block_order = tuple(elements)
        for el in block_order:
            draw_block(el,live)
        if not live:
            canvas.create_text(ox+w-18*scale,oy+22*scale,text='Câu: --/--  (khóa)',
                               anchor='e',fill='#475569',font=('Segoe UI',max(6,round(11*scale)),'bold'),tags='locked')
            canvas.create_rectangle(ox+w-155*scale,oy+h-64*scale,ox+w-24*scale,oy+h-22*scale,
                                    fill='#176347',outline='',tags='locked')
            canvas.create_text(ox+w-89*scale,oy+h-43*scale,text='Hoàn thành (khóa)',fill='white',
                               font=('Segoe UI',max(6,round(10*scale)),'bold'),tags='locked')

    def draw_rulers():
        scale = zoom[0]
        ox,oy = page_origin_x*scale,page_origin_y*scale
        ruler_top.delete('all')
        ruler_left.delete('all')
        ruler_top.create_text(7,13,anchor='w',text='px',fill='#64748b',font=('Segoe UI',8))
        x0,y0=canvas.canvasx(0),canvas.canvasy(0)
        for n in range(0,page_w+1,25):
            xx=ox+n*scale-x0
            if 0<=xx<=ruler_top.winfo_width():
                major=n%100==0
                ruler_top.create_line(xx,28,xx,8 if major else 19,fill='#64748b')
                if major:
                    ruler_top.create_text(xx+3,3,anchor='nw',text=str(n),font=('Segoe UI',8),fill='#475569')
        for n in range(0,extended_h[0]+1,25):
            yy=oy+n*scale-y0
            if 0<=yy<=ruler_left.winfo_height():
                major=n%100==0
                ruler_left.create_line(38,yy,16 if major else 29,yy,fill='#64748b')
                if major:
                    ruler_left.create_text(2,yy+2,anchor='nw',text=str(n),font=('Segoe UI',8),fill='#475569')

    def hit(x,y):
        selected = active[0]
        if selected in boxes:
            a,b,c,d=boxes[selected]
            for name,(rx,ry) in handles.items():
                if abs(x-(a+rx*(c-a)))<=8 and abs(y-(b+ry*(d-b)))<=8:
                    return selected,name
        for el in reversed(block_order):
            a,b,c,d=boxes[el]
            if a<=x<=c and b<=y<=d:
                return el,('se' if x>=c-12 and y>=d-12 else 'move')
        return None,None

    def hover(event):
        _, mode = hit(canvas.canvasx(event.x),canvas.canvasy(event.y))
        cursor = cursors.get(mode,'fleur' if mode=='move' else '')
        if canvas.cget('cursor') != cursor:
            canvas.configure(cursor=cursor)

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
        nonlocal scroll_job, last_motion, drag_visual
        if drag_visual is not None:
            canvas.after_cancel(drag_visual)
            drag_visual = None
            if drag[0]:
                update_drag(drag[0][0], drag[0][1])
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
            v = resize_rect(start, mode, dx, dy, tuple(dims),
                            keep_ratio=el == 'question_image' and len(mode)==2 and not event.state&1)
        if v != start and not registered_motion:
            had_preview = preview_image is not None
            snapshot()
            registered_motion = True
            if had_preview:
                redraw()
        if registered_motion:
            set_geometry(el,v)
        auto = event.y >= view_h-edge or event.y <= edge or event.x >= view_w-edge or event.x <= edge
        if auto and scroll_job is None:
            scroll_job = canvas.after(60,repeat_motion)
        expand_to(v)
        schedule_drag(el,mode)

    def schedule_drag(el,mode):
        nonlocal drag_visual
        if drag_visual is None:
            drag_visual = canvas.after(16,lambda:update_drag(el,mode))

    def update_drag(el,mode):
        nonlocal drag_visual
        drag_visual = None
        if el not in block_items:
            return
        if mode == 'move':
            a,b,c,d = boxes[el]
            value = current(el)
            x = (page_origin_x + value['x']*page_w)*zoom[0]
            y = (page_origin_y + value['y']*page_h)*zoom[0]
            canvas.move(block_items[el],x-a,y-b)
            boxes[el] = (x,y,c+x-a,d+y-b)
        else:
            index = elements.index(el)
            canvas.delete(block_items[el])
            draw_block(el,False)
            if index+1<len(elements):
                canvas.tag_lower(block_items[el],block_items[elements[index+1]])
            canvas.tag_raise('locked')
        a,b,c,_ = canvas.coords(page_background)
        canvas.coords(page_background,a,b,c,(page_origin_y+extended_h[0])*zoom[0])
        canvas.configure(scrollregion=(0,0,(page_w+40)*zoom[0],(extended_h[0]+40)*zoom[0]))
        show_pixels()
        draw_rulers()
        status.set('Có thay đổi chưa lưu' if dirty() else 'Đã nạp bố cục')

    def font_change(_event=None):
        if active[0] != 'question_text' and active[0] not in option_defaults and active[0] not in extras:
            return
        try:
            value = int(font_var.get())
        except (ValueError, tk.TclError):
            return
        if active[0] in extras:
            if 8 <= value <= 96:
                change_text_style(font_size=value)
            return
        if 8 <= value <= 96 and value != current(active[0]).get('font_size'):
            snapshot()
            working[active[0]] = {**current(active[0]), 'font_size': value}
            redraw()

    def restore(state):
        nonlocal preview_image
        preview_image = None
        for target, values in zip((desktop_layout, mobile_layout, extras), state):
            target.clear()
            target.update(deepcopy(values))
        sync_elements()
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
            restore((saved_layout, saved_mobile, saved_extras))

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
    ruler_top.bind('<Configure>', lambda _e:draw_rulers())
    ruler_left.bind('<Configure>', lambda _e:draw_rulers())
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
    canvas.bind('<Motion>', hover)
    canvas.bind('<Double-Button-1>',edit_text)
    canvas.bind('<Key-t>',lambda _event:add_text())
    canvas.bind('<Delete>',delete_text)
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
    sync_elements()
    for el in elements:
        expand_to(current(el))
    redraw()
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
