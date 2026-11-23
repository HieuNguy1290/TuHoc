"""Stage 2: optional per-question visual layout editor (Tk only).

Does not modify Pygame drawing or input hitboxes. Window state and the live viewport are temporary. Canvas changes are stored
by the caller only after explicit confirmation.
"""
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
from tuhoc.studio.question_layout_store import FONT_FAMILIES, GEOMETRY, IMAGE_FITS, TEXT, layout_v2, validate_layout
from tuhoc.studio.layout_render import DESKTOP, MOBILE, PAGE_LIMIT, fit_pixels, to_pixels, to_relative

from tuhoc.studio.layout_registry import DEFAULTS, controls_for
from tuhoc.studio.layout_edit_geometry import arrange, bounds, constrain, snap_axis


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


def edit_layout(parent, question, initial=None, *, preview=None, templates=None, clipboard=None, live_question=None):
    """Open a modal editor. Return validated layout, or None if cancelled."""
    initial = validate_layout(initial or {})
    stored = initial
    if stored.get('version') in (2, 3, 4):
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
    normal_width = min(1200, max(480, win.winfo_screenwidth()-72))
    normal_height = min(820, max(420, win.winfo_screenheight()-128))
    win.geometry(f'{normal_width}x{normal_height}')
    win.minsize(min(800, normal_width), min(540, normal_height))
    # A native maximized window keeps the taskbar work area. A transient
    # window can be sized or repositioned relative to its owner instead.
    def is_maximized():
        if win.tk.call('tk', 'windowingsystem') == 'win32':
            return win.state() == 'zoomed'
        try:
            return bool(win.attributes('-zoomed'))
        except tk.TclError:
            return win.state() == 'zoomed'

    def maximize(enabled):
        if win.tk.call('tk', 'windowingsystem') == 'win32':
            win.state('zoomed' if enabled else 'normal')
        else:
            try:
                win.attributes('-zoomed', enabled)
            except tk.TclError:
                try:
                    win.state('zoomed' if enabled else 'normal')
                except tk.TclError:
                    pass
        fullscreen_btn.configure(text='Thu nhỏ cửa sổ' if is_maximized() else 'Phóng to cửa sổ')

    def maximize_on_map(event):
        if event.widget is win:
            win.unbind('<Map>', map_binding)
            maximize(True)

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
            direction = 1 if event.delta > 0 or event.num == 4 else -1
            if live_renderer is not None and working is desktop_layout and preview_image is not None and (
                practice or question.get('type') == 'reading_group'
                or (direction > 0 and scene_scroll > 0) or (direction < 0 and scene_scroll < scene_limit)
            ):
                point = (round(canvas.canvasx(event.x)/zoom[0]-page_origin_x),
                         round(canvas.canvasy(event.y)/zoom[0]-page_origin_y))
                send_live('input', ('motion', point))
                send_live('input', ('wheel', direction))
            else:
                canvas.yview_scroll(-3*direction, 'units')
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
    ribbon = ttk.Frame(win, padding=(12, 0, 12, 6))
    ribbon.pack(fill='x', before=main)
    ttk.Label(ribbon, text='Định dạng chữ').pack(side='left', padx=(0, 8))
    font_var = tk.IntVar(value=24)
    font_spin = ttk.Spinbox(ribbon, from_=8, to=96, textvariable=font_var, width=5)
    font_spin.state(['disabled'])
    ttk.Label(sidebar, text='Số câu và nút Hoàn thành được khóa.', wraplength=180, foreground='#64748b').pack(anchor='w', pady=22)
    fields = ttk.Frame(sidebar)
    fields.pack(anchor='w', pady=4)
    pixel_vars = {}
    pixel_entries = {}
    for row, (field, label) in enumerate(zip(('x', 'y', 'width', 'height'), ('X', 'Y', 'W', 'H'))):
        ttk.Label(fields, text=label).grid(row=row, column=0, sticky='w', padx=(0, 8))
        variable = tk.StringVar()
        entry = ttk.Entry(fields, textvariable=variable, width=8)
        entry.grid(row=row, column=1, pady=2)
        entry.bind('<Return>', lambda _event: apply_pixels())
        pixel_vars[field] = variable
        pixel_entries[field] = entry
    ttk.Button(fields, text='Áp dụng (px)', command=lambda: apply_pixels()).grid(row=4, columnspan=2, sticky='ew')
    ttk.Button(fields, text='Tự động bố trí', command=lambda: reset_geometry()).grid(row=5, columnspan=2, sticky='ew')
    ttk.Label(sidebar, text='Khung 960 × 640 px. Nội dung có thể kéo xuống đến Y = 2560 px.',
              wraplength=180, foreground='#475569').pack(anchor='w', pady=6)
    fit_var = tk.StringVar(value='contain')
    fit_select = ttk.Combobox(sidebar, values=IMAGE_FITS, textvariable=fit_var,
                              state='readonly', width=10)
    fit_select.bind('<<ComboboxSelected>>', lambda _e: change_fit())
    text_tools = ttk.Frame(sidebar)
    bold_var = tk.BooleanVar()
    italic_var = tk.BooleanVar()
    underline_var = tk.BooleanVar()
    family_var = tk.StringVar()
    from tuhoc.studio.studio_text_format import FAMILY_DEFAULT, FLAGS
    family_select = ttk.Combobox(ribbon, values=(FAMILY_DEFAULT, *FONT_FAMILIES[1:]),
                                 textvariable=family_var, state='readonly', width=17)
    family_select.pack(side='left')
    family_select.bind('<<ComboboxSelected>>', lambda _e: change_text_style(
        font_family='' if family_var.get() == FAMILY_DEFAULT else family_var.get()))
    font_spin.pack(side='left', padx=5)
    style_buttons = []
    variables = {'bold': bold_var, 'italic': italic_var, 'underline': underline_var}
    for field, symbol, label in FLAGS:
        button = ttk.Checkbutton(ribbon, text=f'{symbol} · {label}', variable=variables[field],
                                 style='Toolbutton', command=lambda name=field: change_text_style(
                                     **{name: variables[name].get()}))
        button.pack(side='left', padx=2)
        style_buttons.append(button)
    align_var = tk.StringVar(value='left')
    align_select = ttk.Combobox(text_tools, values=('left', 'center', 'right'),
                                textvariable=align_var, state='readonly', width=7)
    align_select.pack(anchor='w')
    align_select.bind('<<ComboboxSelected>>', lambda _e: change_text_style(align=align_var.get()))
    spacing_var = tk.IntVar(value=0)
    spacing_row = ttk.Frame(text_tools)
    ttk.Label(spacing_row, text='Thêm giãn dòng (px)').pack(side='left')
    spacing_spin = ttk.Spinbox(spacing_row, textvariable=spacing_var, from_=0, to=80, width=4)
    spacing_spin.pack(side='left')
    spacing_spin.bind('<Return>', lambda _e: spacing_change())
    spacing_spin.bind('<FocusOut>', lambda _e: spacing_change())
    ranges_button = ttk.Button(ribbon, text='Định dạng đoạn chữ…', command=lambda: edit_text_ranges())
    colors = ttk.Frame(sidebar)
    ttk.Button(colors, text='Màu chữ', command=lambda: choose_color('color')).pack(side='left')
    ttk.Button(colors, text='Nền', command=lambda: choose_color('bg')).pack(side='left')
    ttk.Button(colors, text='Xóa nền', command=lambda: change_text_style(bg='')).pack(side='left')
    pending_image = None
    active = [None]
    selected_keys = set()
    locked = set()
    hidden = set()
    group_start = {}
    marquee = None
    guides = []
    status = tk.StringVar(value='Đã nạp bố cục')
    scroll_job = None
    last_motion = None
    registered_motion = False
    preview_image = None
    scrollbar_drag = False
    drag_feedback = {}
    drag_sprite = None
    drag_photo = None
    live_renderer = None
    scene_boxes = {}
    scene_scroll = 0
    scene_limit = 0
    scene_layout = None
    requested = None
    sent_revision = 0
    sent_layout = None
    live_job = None
    poll_job = None
    practice = False
    practice_done = False
    scene_error = None
    menu_anchor = None
    menu_revision = None
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
    if question.get('type') == 'true_false' and not options:
        options = ['Đúng', 'Sai']
    if question.get('type') == 'order' and not options:
        options = question.get('sequence') or str(question.get('answer', '')).split()
    if question.get('type') == 'matching':
        from tuhoc.exercises.matching_widget import parse_pairs
        pairs = question.get('pairs') or parse_pairs(options)
        options = [pair[side] for side in (0, 1) for pair in pairs]
    elif question.get('type') == 'sentence_underline_words':
        from tuhoc.exercises.underline_extension import TOKEN
        options = TOKEN.findall(question.get('source_text', ''))
    elif question.get('type') in {'image_letter_pick', 'image_sentence_fill'}:
        options = [*question.get('blank_answers', []), *question.get('distractors', [])]
    elif question.get('type') == 'picture_missing_letters':
        options = ['Kích thước ô chữ']
    controls = controls_for(question.get('type'), question.get('_layout_context', 'lesson'))
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

    item_labels = {f'option_{i}': value for i, value in enumerate(options)}
    if 'slot_N' in controls.editable:
        slot_count = len(question.get('blank_answers') or question.get('gap_answers') or [])
        if question.get('type') in {'sentence_gaps', 'passage_gaps', 'conversation_gaps'} and not slot_count:
            from tuhoc.exercises.new_exercise_runtime import gaps
            slot_count = sum(len(indices) for _, indices in gaps(question))
        slot_indices = range(slot_count)
        if question.get('type') == 'picture_missing_letters':
            slot_indices = sorted({i for i in question.get('hidden_indices', []) if type(i) is int and i >= 0})
        for i in slot_indices:
            item_labels[f'slot_{i}'] = f'Ô trống {i + 1}'
    if 'word_N' in controls.editable:
        for i in range(slot_count + len(question.get('distractors') or [])):
            item_labels[f'word_{i}'] = f'Thẻ từ {i + 1}'
    for key in item_labels.keys() - option_defaults.keys():
        option_defaults[key] = dict(x=.09, y=.60, width=.12, height=.07, font_size=20)

    system_elements = [*area_keys, *item_labels]
    elements = []

    def sync_elements():
        elements[:] = [*system_elements, *sorted(extras, key=lambda key: extras[key]['z'])]
        elements_list.delete(0, 'end')
        for key in elements:
            label = (extras[key]['text'].replace('\n', ' ')[:32] or 'Văn bản') if key in extras else key
            elements_list.insert('end', label)
        if active[0] not in elements:
            active[0] = None
        selected_keys.intersection_update(elements)
        select(active[0],preserve=True)

    def current(el):
        if el in extras:
            extra = extras[el]
            is_mobile = working is mobile_layout and 'mobile' in extra
            frame = 'mobile' if is_mobile else 'desktop'
            screen = MOBILE if is_mobile else DESKTOP
            return to_relative(extra[frame], screen)
        base = option_defaults.get(el) or DEFAULTS[el]
        rects = scene_boxes.get(el) if working is desktop_layout else None
        overrides = {**desktop_layout.get(el, {}), **working.get(el, {})}
        if rects and preview_image is not None:
            x, y, width, height = rects[0]
            actual = to_relative(dict(x=x, y=y, width=width, height=height), (preview_image.width, DESKTOP[1]))
            if requested and scene_layout == requested[0]:
                return {**base, **overrides, **actual}
            base = {**base, **actual}
        return {**base, **overrides}

    def properties(el):
        if el in extras:
            return GEOMETRY | TEXT | {'align', 'runs'}
        if el:
            return controls.properties_for(el, question.get('type'))
        return set()

    def text_element(el):
        return 'font_size' in properties(el)

    def select(el, from_list=False, preserve=False):
        if not preserve:
            selected_keys.clear()
        if el:
            selected_keys.add(el)
        active[0] = el
        selection.set('Hộp văn bản' if el in extras else el or 'Chọn thành phần')
        for widget in (fit_select, text_tools, colors):
            widget.pack_forget()
        if el == 'question_image':
            fit_var.set(current(el).get('image_fit', 'contain'))
            fit_select.pack(anchor='w', pady=2)
        align_select.pack_forget()
        ranges_button.pack_forget()
        spacing_row.pack_forget()
        state = ['!disabled'] if text_element(el) and not practice else ['disabled']
        for widget in (font_spin, family_select, *style_buttons):
            widget.state(state)
        if text_element(el):
            style = extras[el] if el in extras else current(el)
            bold_var.set(style.get('bold', False))
            italic_var.set(style.get('italic', False))
            underline_var.set(style.get('underline', False))
            family_var.set(style.get('font_family') or FAMILY_DEFAULT)
            text_tools.pack(anchor='w')
            if 'runs' in properties(el):
                ranges_button.pack(side='left', padx=8)
            if 'align' in properties(el):
                align_var.set(style.get('align', 'left'))
                align_select.pack(anchor='w')
            if 'line_spacing' in properties(el):
                spacing_var.set(style.get('line_spacing', 0))
                spacing_row.pack(anchor='w')
            if el in extras:
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
        if practice:
            toggle_practice(force_edit=True)
        page_w, page_h = MOBILE if viewport_var.get() == 'Điện thoại' else DESKTOP
        max_page_h = page_h * PAGE_LIMIT
        dims[:] = [page_w, page_h]
        working = mobile_layout if viewport_var.get() == 'Điện thoại' else desktop_layout
        extended_h[0] = page_h
        for el in elements:
            expand_to(current(el))
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)
        if live_renderer:
            state = ['disabled'] if working is mobile_layout else ['!disabled']
            practice_button.state(state)
            if menu_button is not None:
                menu_button.state(state)
        show_pixels()
        redraw()

    def draft():
        result = layout_v2(desktop_layout)
        if mobile_layout or 'mobile' in stored:
            result['mobile'] = {el: fit_pixels(to_pixels(rect, MOBILE), MOBILE)
                                for el, rect in mobile_layout.items()}
        v4_fields = (TEXT - {'font_size'}) | {'runs', 'align', 'line_spacing'}
        v4_elements = {'answer_passage', 'answer_preview', 'answer_panel', 'answer_menu'}
        uses_v4 = any(
            (v4_fields & values.keys()) or el in v4_elements or el.startswith(('slot_', 'word_'))
            or (el == 'answer_area' and 'height' in values)
            for frame in ('desktop', 'mobile') for el, values in result.get(frame, {}).items()
        )
        uses_v4 = uses_v4 or any({'underline', 'font_family', 'runs'} & item.keys() for item in extras.values())
        if stored.get('version') == 4 or uses_v4:
            result.update(version=4, extras=list(extras.values()))
        elif stored.get('version') == 3 or extras:
            result.update(version=3, extras=list(extras.values()))
        return validate_layout(result)

    def dirty():
        return (desktop_layout != saved_layout or mobile_layout != saved_mobile
                or extras != saved_extras or pending_image is not None)

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

    def queue_live_frame(*, reset=False):
        nonlocal live_job, requested, scene_error
        if live_renderer is None or working is mobile_layout or practice:
            return
        try:
            target = (draft(), str(pending_image) if pending_image else None)
        except ValueError:
            return
        if not reset and target == requested:
            return
        requested = target
        scene_error = None
        if live_job is None:
            live_job = win.after(45, lambda: request_live_frame(reset=reset))

    def request_live_frame(*, reset=False):
        nonlocal live_job, sent_revision, sent_layout
        live_job = None
        if live_renderer is None or working is mobile_layout:
            return
        sent_revision += 1
        layout, image = requested
        sent_layout = layout
        send_live('layout', (sent_revision, layout, reset, image))

    def send_live(command, payload=None):
        nonlocal scene_error
        try:
            live_renderer.send(command, payload)
        except (OSError, EOFError) as exc:
            scene_error = str(exc)
            status.set('Không mở được mô phỏng Pygame.')

    def poll_live():
        nonlocal poll_job, scene_boxes, scene_scroll, scene_limit, scene_layout, menu_revision, drag_sprite
        nonlocal scene_error, practice_done
        poll_job = None
        if live_renderer is None:
            return
        try:
            latest = None
            for kind, payload in live_renderer.read():
                if payload[0] != sent_revision:
                    continue
                if kind == 'frame':
                    latest = payload
                elif kind == 'finished':
                    practice_done = True
                    status.set('Đã làm thử. Bấm Thử lại để làm lại câu.')
                    practice_button.configure(text='Thử lại')
                elif kind == 'error':
                    scene_error = payload[1] or 'Không tải được bài tập.'
            if latest is not None:
                _, size, pixels, scene_boxes, scene_scroll, scene_limit = latest
                scene_layout = sent_layout
                if not drag[0] and requested and scene_layout == requested[0]:
                    drag_feedback.clear()
                    drag_sprite = None
                show_frame(size, pixels)
                if not drag[0]:
                    show_pixels()
                if menu_button is not None:
                    menu_button.configure(text='Đóng menu' if 'answer_menu' in scene_boxes else 'Mở menu')
                if menu_anchor and menu_revision != sent_revision and 'answer_menu' not in scene_boxes:
                    if click_rendered(menu_anchor):
                        menu_revision = sent_revision
            if scene_error:
                status.set('Xem trước: ' + scene_error)
        except (OSError, EOFError) as exc:
            scene_error = str(exc) or 'Không tải được mô phỏng Pygame.'
            status.set(scene_error)
            return
        poll_job = win.after(30, poll_live)

    def stop_live(event):
        if event.widget is not win:
            return
        for job in (live_job, poll_job):
            if job is not None:
                win.after_cancel(job)
        if live_renderer is not None:
            live_renderer.close()

    def click_rendered(key):
        if key in scene_boxes and preview_image is not None:
            _, (x,y,width,height) = scene_boxes[key]
            point = (x+width//2, y+height//2)
            if 0 <= point[0] < preview_image.width and 0 <= point[1] < preview_image.height:
                send_live('input', ('click', point))
                send_live('input', ('release', point))
                return True
        return False

    def toggle_menu():
        nonlocal menu_anchor, menu_revision
        if practice or working is mobile_layout:
            return
        if 'answer_menu' in scene_boxes:
            menu_anchor = None
            send_live('input', ('click', (4,4)))
            send_live('input', ('release', (4,4)))
        else:
            active_key = active[0] or ''
            key = 'dropdown_area' if question['type'] == 'dropdown_fill_blank' and 'slot_0' not in scene_boxes else (
                active_key if active_key.startswith('slot_') else 'slot_0')
            if click_rendered(key):
                menu_anchor = key
                menu_revision = sent_revision

    def toggle_practice(*, force_edit=False):
        nonlocal practice, practice_done, requested, menu_anchor
        if live_renderer is None or working is mobile_layout:
            return
        retry = practice_done
        practice = (retry or not practice) if not force_edit else False
        practice_done = False
        menu_anchor = None
        if menu_button is not None:
            menu_button.state(['disabled'] if practice else ['!disabled'])
        practice_button.configure(text='Chỉnh bố cục' if practice else 'Thử làm bài')
        requested = (draft(), str(pending_image) if pending_image else None)
        send_live('play', practice)
        if live_job is not None:
            win.after_cancel(live_job)
        request_live_frame(reset=retry)
        canvas.focus_set()
        redraw()

    def live_input(kind, event):
        if preview_image is None or not scrollbar_drag and (not practice or practice_done):
            return
        point = (round(canvas.canvasx(event.x)/zoom[0]-page_origin_x),
                 round(canvas.canvasy(event.y)/zoom[0]-page_origin_y))
        if scrollbar_drag or (0 <= point[0] < preview_image.width and 0 <= point[1] < preview_image.height):
            send_live('input', (kind, point))
        return 'break'

    def live_key(event):
        if not practice or practice_done:
            return
        keys = {'Return': 'return', 'KP_Enter': 'return', 'BackSpace': 'backspace',
                'Tab': 'tab', 'ISO_Left_Tab': 'tab', 'Left': 'left', 'Right': 'right',
                'Up': 'up', 'Down': 'down', 'Delete': 'delete', 'Prior': 'pageup', 'Next': 'pagedown'}
        if event.keysym in keys:
            send_live('input', ('key', (keys[event.keysym], bool(event.state & 1))))
        elif event.char and event.char.isprintable() and not event.state & 4:
            if event.char.isascii():
                send_live('input', ('key', event.char.casefold() if event.char != ' ' else 'space'))
            kind = 'text_key' if question.get('type') == 'multi_fill_blanks' else 'text'
            send_live('input', (kind, event.char))
        return 'break'

    def expand_to(values):
        needed = round((values['y'] + values['height']) * page_h) + 80
        extended_h[0] = max(extended_h[0], min(max_page_h, needed))

    def show_pixels():
        allowed = properties(active[0])
        values = current(active[0]) if active[0] else {}
        for field, variable in pixel_vars.items():
            pixel_entries[field].state(['!disabled'] if field in allowed else ['disabled'])
            scale = page_w if field in ('x', 'width') else page_h
            variable.set(str(round(values[field] * scale)) if field in allowed else '')

    def apply_pixels():
        if not active[0] or active[0] in locked:
            return
        try:
            values = current(active[0])
            for field, variable in pixel_vars.items():
                if field not in properties(active[0]):
                    continue
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

    def reset_geometry():
        key = active[0]
        if not key or key in locked or key in extras or not (GEOMETRY & working.get(key, {}).keys()):
            return
        snapshot()
        remaining = {field: value for field, value in working[key].items() if field not in GEOMETRY}
        if remaining:
            working[key] = remaining
        else:
            del working[key]
        redraw()

    def capture():
        return deepcopy(desktop_layout), deepcopy(mobile_layout), deepcopy(extras), locked.copy(), hidden.copy(), image_path, pending_image

    def snapshot():
        nonlocal preview_image
        if live_renderer is None:
            preview_image = None
        history.append(capture())
        future.clear()
        if len(history) > 50:
            history.pop(0)


    original_image = image_path

    def set_geometry(key, values):
        if key in extras:
            screen = tuple(dims)
            frame = 'mobile' if screen == MOBILE else 'desktop'
            rect = {k: values[k] for k in GEOMETRY}
            extras[key][frame] = fit_pixels(to_pixels(rect, screen), screen)
        else:
            allowed = properties(key)
            working[key] = {name: value for name, value in values.items() if name in allowed}

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
            source = current(copy['id'])
            step_x,step_y=constrain(source,8/page_w,8/page_h)
            rect = fit_pixels(to_pixels({k:source[k] for k in GEOMETRY}|{
                'x':source['x']+step_x,'y':source['y']+step_y},tuple(dims)),tuple(dims))
            extra['desktop'] = rect if working is desktop_layout else deepcopy(copy['desktop'])
            extra.update({k: copy[k] for k in TEXT | {'text', 'color', 'bg', 'align', 'runs'} if k in copy})
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
        if not text_element(key) or key in locked:
            return
        source = extras[key] if key in extras else current(key)
        if all(source.get(field) == value for field, value in values.items()):
            return
        snapshot()
        if key in extras:
            if 'text' in values:
                extras[key].pop('runs', None)
            extras[key].update(values)
            sync_elements()
        else:
            working[key] = {**working.get(key, {}), **values}
        redraw()

    def spacing_change():
        if active[0] not in {'question_text', 'answer_passage'}:
            return
        try:
            value = spacing_var.get()
        except tk.TclError:
            return
        if 0 <= value <= 80:
            change_text_style(line_spacing=value)

    def edit_text_ranges():
        from tuhoc.studio.studio_text_format import display_text, open_text_format

        key = active[0]
        if not key or key in locked:
            return
        source = extras[key] if key in extras else current(key)
        field = 'passage' if key == 'answer_passage' else 'prompt'
        raw = source['text'] if key in extras else str(question.get(field) or '')
        value, inherited = display_text(raw, markdown=key not in extras)
        if value:
            open_text_format(win, value, source, lambda runs: change_text_style(runs=runs),
                             inherited=inherited)

    def choose_color(field):
        if active[0] in extras:
            _, value = colorchooser.askcolor(extras[active[0]][field] or '#ffffff', parent=win)
            if value:
                change_text_style(**{field: value})

    def delete_text(_event=None):
        keys = (selected_keys & extras.keys()) - locked
        if keys:
            snapshot()
            for key in keys:
                del extras[key]
                hidden.discard(key)
            sync_elements()
            redraw()
        return 'break'

    def edit_text(event):
        nonlocal edit_widget
        key, mode = hit(canvas.canvasx(event.x), canvas.canvasy(event.y))
        if practice or mode != 'move' or key not in extras or key in locked:
            return down(event)
        if edit_widget is not None:
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
        if live and live_renderer is not None and el in scene_boxes:
            _, visible = scene_boxes[el]
            x, y, w, h = visible
            rect = ((page_origin_x+x)*scale, (page_origin_y+y)*scale,
                    (page_origin_x+x+w)*scale, (page_origin_y+y+h)*scale)
        a,b,c,d = rect
        boxes[el] = rect
        selected = el in selected_keys
        tag = 'block:'+el
        extra = extras.get(el)
        fill = '' if live else (extra['bg'] if extra else '#eff6ff' if selected else '#f8fafc')
        canvas.create_rectangle(*rect, fill=fill, outline='#2563eb' if selected else '' if live and live_renderer else '#cbd5e1',
                                width=2 if selected else 1, tags=tag)

        def text(x, y, value, size=12, style='normal', **options):
            config = extra or v
            flags = ' '.join(flag for flag in ('bold', 'italic', 'underline') if config.get(flag))
            family = config.get('font_family') or 'Segoe UI'
            canvas.create_text(x,y,text=value,font=(family,max(6,round(size*scale)),flags or style),
                               tags=tag,**options)

        if not live:
            if extra or el == 'question_text' or (el == 'answer_passage' and question.get('passage')):
                from tuhoc.studio.studio_text_format import draw_text_preview

                field = 'passage' if el == 'answer_passage' else 'prompt'
                content = extra['text'] if extra else str(question.get(field) or 'Nội dung câu hỏi')
                inset = 2 if extra else 8
                draw_text_preview(canvas, content, extra or v, (a+inset,b+inset,c-inset,d-inset),
                                  scale, extra['color'] if extra else '#1e293b', tag, markdown=not extra)
            elif el == 'question_image':
                image = None
                if image_path is not None:
                    from tuhoc.studio.layout_images import fitted_image
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
            elif el in ('answer_area','input_area','dropdown_area','word_bank','answer_preview','answer_passage','answer_panel','answer_menu'):
                labels = {'answer_area':'VÙNG ĐÁP ÁN','input_area':'Ô NHẬP',
                          'dropdown_area':'MENU CHỌN','word_bank':'NGÂN HÀNG TỪ',
                          'answer_preview':'CÂU ĐÃ XẾP','answer_passage':'ĐOẠN ĐỌC','answer_panel':'CÂU HỎI CON','answer_menu':'DANH SÁCH LỰA CHỌN'}
                text(a+8,b+8,labels[el],10,anchor='nw',fill='#64748b')
            else:
                i = int(el.split('_')[1])
                label = item_labels[el] or f'Vị trí {i + 1}'
                text((a+c)/2 if is_image_choice else a+8,(b+d)/2,label,
                     min(40,int(v.get('font_size',18))),anchor='center' if is_image_choice else 'w',
                     width=max(40,c-a-16),fill='#1e293b')
            if not extra:
                text(a+4,b-4,el,9,anchor='sw',fill='#2563eb')
        if selected and len(selected_keys)==1 and el not in locked:
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
        message = ('Đã làm thử. Bấm Thử lại để làm lại câu.' if practice_done
                   else 'Thử làm bài' if practice
                   else 'Đang dựng bài tập…' if live_renderer and not preview_image and not scene_error
                   else 'Có thay đổi chưa lưu' if dirty() else 'Đã nạp bố cục')
        status.set(message)
        scale = zoom[0]
        w,h = page_w*scale,page_h*scale
        ox,oy = page_origin_x*scale,page_origin_y*scale
        limit = extended_h[0]*scale
        if live_renderer and preview_image and working is desktop_layout:
            canvas.configure(scrollregion=(0,0,(preview_image.width+40)*scale,(preview_image.height+40)*scale))
        else:
            canvas.configure(scrollregion=(0,0,(page_w+40)*scale,(extended_h[0]+40)*scale))
        page_background = canvas.create_rectangle(ox,oy,ox+w,oy+limit,fill='white',outline='#94a3b8')
        live = preview_image is not None and viewport_var.get() == 'Máy tính'
        if live:
            from PIL import Image, ImageTk
            image_size = preview_image.size
            size = tuple(round(value*scale) for value in image_size)
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
        if live and live_renderer is not None:
            visible_height = preview_image.height
            block_order = () if practice else tuple(el for el in elements if el not in hidden and el in scene_boxes
                and scene_boxes[el][1][1] < visible_height
                and scene_boxes[el][1][1] + scene_boxes[el][1][3] > 0)
        else:
            block_order = tuple(el for el in elements if el not in hidden)
        for el in block_order:
            draw_block(el,live)
        if live and drag_feedback:
            paint_drag_feedback()
        queue_live_frame()
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
        preview_ratio = preview_image.width / page_w if live_renderer and preview_image and working is desktop_layout else 1
        for n in range(0,page_w+1,25):
            xx=ox+n*scale*preview_ratio-x0
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
        if len(selected_keys)==1 and selected in boxes and selected not in locked:
            a,b,c,d=boxes[selected]
            for name,(rx,ry) in handles.items():
                if abs(x-(a+rx*(c-a)))<=8 and abs(y-(b+ry*(d-b)))<=8:
                    return selected,name
        for el in reversed(block_order):
            a,b,c,d=boxes[el]
            if a<=x<=c and b<=y<=d:
                return el,('se' if len(selected_keys)<=1 and el not in locked and x>=c-12 and y>=d-12 else 'move')
        return None,None

    def hover(event):
        if practice:
            return live_input('motion', event)
        _, mode = hit(canvas.canvasx(event.x),canvas.canvasy(event.y))
        cursor = cursors.get(mode,'fleur' if mode=='move' else '')
        if canvas.cget('cursor') != cursor:
            canvas.configure(cursor=cursor)

    drag_scene_offset = 0

    def draw_offset(el):
        rects = scene_boxes.get(el) if live_renderer and working is desktop_layout else None
        return rects[0][1]-rects[1][1] if rects else 0

    def down(event):
        nonlocal registered_motion, marquee, drag_scene_offset, scrollbar_drag, drag_sprite
        canvas.focus_set()
        if practice:
            return live_input('click', event)
        x,y=canvas.canvasx(event.x),canvas.canvasy(event.y)
        if live_renderer and working is desktop_layout:
            px,py = x/zoom[0]-page_origin_x, y/zoom[0]-page_origin_y
            for key, (_, (bx,by,bw,bh)) in scene_boxes.items():
                if key.startswith('_scrollbar') and bx-6 <= px < bx+bw+6 and by <= py < by+bh:
                    scrollbar_drag = True
                    return live_input('click', event)
        el, mode = hit(x,y)
        if event.state&1 and el:
            if el in selected_keys:
                selected_keys.discard(el)
                select(next(iter(selected_keys),None),preserve=True)
            else:
                select(el,preserve=True)
            redraw()
            return 'break'
        if el:
            select(el,preserve=el in selected_keys)
        else:
            if not event.state&1:
                select(None)
            redraw()
            marquee=(x,y,canvas.create_rectangle(x,y,x,y,outline='#2563eb',dash=(3,3),tags='marquee'))
            return 'break'
        registered_motion = False
        group_start.clear()
        if el not in locked:
            drag_feedback.clear()
            drag_sprite = None
            if mode != 'move' and live_renderer and preview_image and working is desktop_layout and el in scene_boxes:
                px, py, width, height = scene_boxes[el][1]
                if width > 0 and height > 0:
                    drag_sprite = preview_image.crop((px,py,px+width,py+height))
            drag_scene_offset = draw_offset(el)
            drag[0]=(el,mode,x,y,deepcopy(current(el)))
            if mode=='move':
                group_start.update({key:current(key) for key in selected_keys-hidden-locked})
        redraw()
        return 'break'

    def repeat_motion():
        nonlocal scroll_job
        scroll_job = None
        if drag[0] and last_motion is not None:
            move(last_motion)

    def release(event=None):
        nonlocal scroll_job, last_motion, drag_visual, marquee, scrollbar_drag
        if scrollbar_drag:
            if event is not None:
                live_input('release', event)
            scrollbar_drag = False
            return 'break'
        if practice and event is not None:
            return live_input('release', event)
        if drag_visual is not None:
            canvas.after_cancel(drag_visual)
            drag_visual = None
            if drag[0]:
                update_drag(drag[0][0], drag[0][1])
        if marquee is not None:
            x,y,item=marquee
            if event is not None:
                x2,y2=canvas.canvasx(event.x),canvas.canvasy(event.y)
                a,c=sorted((x,x2));b,d=sorted((y,y2))
                selected_keys.update(key for key,rect in boxes.items()
                                     if a<=rect[0] and b<=rect[1] and c>=rect[2] and d>=rect[3])
                select(next(iter(selected_keys),None),preserve=True)
            canvas.delete(item)
            marquee=None
            redraw()
        canvas.delete('guides')
        guides.clear()
        drag[0] = None
        last_motion = None
        if scroll_job is not None:
            canvas.after_cancel(scroll_job)
            scroll_job = None
        queue_live_frame()

    def move(event):
        nonlocal scroll_job, last_motion, registered_motion
        if practice or scrollbar_drag:
            return live_input('motion', event)
        last_motion = event
        if marquee is not None:
            x,y,item=marquee
            canvas.coords(item,x,y,canvas.canvasx(event.x),canvas.canvasy(event.y))
            return
        if not drag[0] or not dims[0] or not dims[1]:
            return
        el, mode, ox, oy, start = drag[0]
        # Scroll before calculating drag deltas.  The pointer coordinates must
        # be converted with the *current* viewport offset, not the previous one.
        edge = 28
        view_w, view_h = canvas.winfo_width(), canvas.winfo_height()
        if event.y >= view_h-edge:
            if live_renderer and preview_image and working is desktop_layout and scene_scroll < scene_limit:
                send_live('input', ('motion', (round(event.x/zoom[0]), min(520, preview_image.height-1))))
                send_live('input', ('wheel', -1))
            if canvas.yview()[1] >= .95 and extended_h[0] < max_page_h:
                extended_h[0] = min(max_page_h, extended_h[0] + 160)
                canvas.configure(scrollregion=(0, 0, (page_w+40)*zoom[0], (extended_h[0]+40)*zoom[0]))
            canvas.yview_scroll(2, 'units')
        elif event.y <= edge:
            if live_renderer and preview_image and working is desktop_layout and scene_scroll > 0:
                send_live('input', ('motion', (round(event.x/zoom[0]), min(320, preview_image.height-1))))
                send_live('input', ('wheel', 1))
            canvas.yview_scroll(-2, 'units')
        if event.x >= view_w-edge and (page_w+40)*zoom[0] > view_w:
            canvas.xview_scroll(2, 'units')
        elif event.x <= edge:
            canvas.xview_scroll(-2, 'units')
        visible_w = preview_image.width if live_renderer and preview_image and working is desktop_layout else dims[0]
        dx = (canvas.canvasx(event.x)-ox)/(visible_w*zoom[0])
        viewport_delta = (draw_offset(el) - drag_scene_offset) * zoom[0]
        dy = (canvas.canvasy(event.y)-oy+viewport_delta)/(dims[1]*zoom[0])
        v = dict(start)
        if snap.get():
            dx = round(dx*page_w/8)*8/page_w
            dy = round(dy*page_h/8)*8/page_h
        values = {}
        guides.clear()
        if mode == 'move':
            group = bounds(list(group_start.values()))
            if not event.state & (0x0008 | 0x0080 | 0x20000):
                nearby = [current(key) for key in block_order if key not in group_start]
                page = int((group['y']+dy)*page_h)//page_h
                dx,gx,distance_x=snap_axis(group,'x',dx,nearby,6/(page_w*zoom[0]),(0,.5,1))
                dy,gy,distance_y=snap_axis(group,'y',dy,nearby,6/(page_h*zoom[0]),(page,page+.5,page+1))
                guides.extend((axis,value,distance) for axis,value,distance in
                              [('x',gx,distance_x),('y',gy,distance_y)] if value is not None)
            dx,dy=constrain(group,dx,dy)
            values={key:{**rect,'x':rect['x']+dx,'y':rect['y']+dy}
                    for key,rect in group_start.items()}
        else:
            values[el]=resize_rect(start,mode,dx,dy,tuple(dims),
                                   keep_ratio=el=='question_image' and len(mode)==2 and not event.state&1)
        if any(value!=current(key) for key,value in values.items()) and not registered_motion:
            had_preview = preview_image is not None
            snapshot()
            registered_motion = True
            if had_preview:
                redraw()
        if registered_motion:
            for key,value in values.items():
                set_geometry(key,value)
                expand_to(value)
        auto = event.y >= view_h-edge or event.y <= edge or event.x >= view_w-edge or event.x <= edge
        if auto and scroll_job is None:
            scroll_job = canvas.after(60,repeat_motion)
        if live_renderer is not None:
            if working is desktop_layout and preview_image and registered_motion:
                drag_feedback.update(values)
            queue_live_frame()
        schedule_drag(el,mode)

    def schedule_drag(el,mode):
        nonlocal drag_visual
        if drag_visual is None:
            drag_visual = canvas.after(16,lambda:update_drag(el,mode))

    def paint_drag_feedback():
        nonlocal drag_photo
        canvas.delete('drag_feedback')
        drag_photo = None
        if preview_image is None:
            return
        awaiting_frame = requested is None or scene_layout != requested[0]
        scale = zoom[0]
        ox, oy = page_origin_x*scale, page_origin_y*scale
        for key, value in drag_feedback.items():
            x1 = ox+value['x']*preview_image.width*scale
            y1 = oy+(value['y']*page_h-draw_offset(key))*scale
            x2 = x1+value['width']*preview_image.width*scale
            y2 = y1+value['height']*page_h*scale
            if awaiting_frame and key == active[0] and drag_sprite and x2 > x1 and y2 > y1:
                from PIL import Image, ImageTk

                left, top = max(ox,x1), max(oy,y1)
                right = min(ox+preview_image.width*scale,x2)
                bottom = min(oy+preview_image.height*scale,y2)
                if right > left and bottom > top:
                    w,h = drag_sprite.size
                    crop = ((left-x1)*w/(x2-x1),(top-y1)*h/(y2-y1),
                            (right-x1)*w/(x2-x1),(bottom-y1)*h/(y2-y1))
                    patch = drag_sprite.transform(
                        (max(1,round(right-left)),max(1,round(bottom-top))), Image.Transform.EXTENT,
                        crop, resample=Image.Resampling.BILINEAR)
                    drag_photo = ImageTk.PhotoImage(patch, master=canvas)
                    canvas.create_image(left,top,image=drag_photo,anchor='nw',tags='drag_feedback')
            canvas.create_rectangle(x1,y1,x2,y2,outline='#2563eb',width=2,tags='drag_feedback')
            if key == active[0] and len(drag_feedback) == 1:
                for rx,ry in handles.values():
                    px,py=x1+rx*(x2-x1),y1+ry*(y2-y1)
                    canvas.create_rectangle(px-4,py-4,px+4,py+4,fill='#2563eb',outline='white',tags='drag_feedback')

    def update_drag(el,mode):
        nonlocal drag_visual
        drag_visual = None
        if el not in block_items:
            return
        if live_renderer is not None and working is desktop_layout and preview_image is not None:
            paint_drag_feedback()
            show_pixels()
            return
        if mode == 'move':
            for key in group_start:
                a,b,c,d=boxes[key]
                value=current(key)
                x=(page_origin_x+value['x']*page_w)*zoom[0]
                y=(page_origin_y+value['y']*page_h)*zoom[0]
                canvas.move(block_items[key],x-a,y-b)
                boxes[key]=(x,y,c+x-a,d+y-b)
        else:
            index = block_order.index(el)
            canvas.delete(block_items[el])
            draw_block(el,False)
            if index+1<len(block_order):
                canvas.tag_lower(block_items[el],block_items[block_order[index+1]])
            canvas.tag_raise('locked')
        a,b,c,_ = canvas.coords(page_background)
        canvas.coords(page_background,a,b,c,(page_origin_y+extended_h[0])*zoom[0])
        canvas.configure(scrollregion=(0,0,(page_w+40)*zoom[0],(extended_h[0]+40)*zoom[0]))
        canvas.delete('guides')
        if guides:
            ox,oy=page_origin_x*zoom[0],page_origin_y*zoom[0]
            for axis,value,distance in guides:
                if axis=='x':
                    x=ox+value*page_w*zoom[0]
                    canvas.create_line(x,oy,x,(page_origin_y+extended_h[0])*zoom[0],fill='#ea580c',tags='guides')
                    canvas.create_text(x+4,canvas.canvasy(8),text=f'{abs(distance)*page_w:.0f} px',
                                       anchor='nw',fill='#9a3412',tags='guides')
                else:
                    y=oy+value*page_h*zoom[0]
                    canvas.create_line(ox,y,ox+page_w*zoom[0],y,fill='#ea580c',tags='guides')
                    canvas.create_text(canvas.canvasx(8),y+4,text=f'{abs(distance)*page_h:.0f} px',
                                       anchor='nw',fill='#9a3412',tags='guides')
        show_pixels()
        draw_rulers()
        status.set('Có thay đổi chưa lưu' if dirty() else 'Đã nạp bố cục')

    def font_change(_event=None):
        try:
            value = int(font_var.get())
        except (ValueError, tk.TclError):
            return
        if 8 <= value <= 96:
            change_text_style(font_size=value)

    def restore(state):
        nonlocal preview_image, image_path, pending_image
        if live_renderer is None:
            preview_image = None
        for target, values in zip((desktop_layout, mobile_layout, extras), state):
            target.clear()
            target.update(deepcopy(values))
        locked.clear()
        locked.update(state[3])
        hidden.clear()
        hidden.update(state[4])
        image_path,pending_image=state[5:7]
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

    def apply_many(values):
        if values and any(value!=current(key) for key,value in values.items()):
            snapshot()
            for key,value in values.items():
                set_geometry(key,value)
                expand_to(value)
            show_pixels()
            redraw()

    def nudge(event):
        keys=selected_keys-hidden-locked
        if keys:
            rects={key:current(key) for key in keys}
            step=8 if event.state&1 else 1
            dx,dy={'Left':(-step/page_w,0),'Right':(step/page_w,0),
                   'Up':(0,-step/page_h),'Down':(0,step/page_h)}[event.keysym]
            dx,dy=constrain(bounds(list(rects.values())),dx,dy)
            apply_many({key:{**rect,'x':rect['x']+dx,'y':rect['y']+dy}
                        for key,rect in rects.items()})
        return 'break'

    def cycle(event):
        keys=[key for key in elements if key not in hidden]
        if keys:
            delta=-1 if event.state&1 else 1
            index=keys.index(active[0]) if active[0] in keys else (-1 if delta>0 else 0)
            select(keys[(index+delta)%len(keys)])
            redraw()
        return 'break'

    def escape_canvas(_event):
        if selected_keys:
            select(None)
            redraw()
            return 'break'

    def duplicate(_event):
        if len(selected_keys)==1 and active[0] in extras:
            add_text(deepcopy(extras[active[0]]))
        return 'break'

    def show_menu(event):
        key,_=hit(canvas.canvasx(event.x),canvas.canvasy(event.y))
        if key and key not in selected_keys:
            select(key)
            redraw()
        key=active[0]
        old=getattr(win,'_studio_menu',None)
        if old is not None:
            old.destroy()
        menu=win._studio_menu=tk.Menu(win,tearoff=False)
        if key in extras:
            for label,sign in (('Đưa lên trước',1),('Đưa xuống sau',-1)):
                def change_layer(sign=sign):
                    snapshot()
                    at=(max if sign>0 else min)(entry['z'] for entry in extras.values())
                    extras[key]['z']=at+sign
                    sync_elements()
                    redraw()
                menu.add_command(label=label,command=change_layer)
        if key:
            def toggle_lock():
                snapshot()
                if key in locked:locked.discard(key)
                else:locked.add(key)
                redraw()
            def hide_element():
                snapshot()
                hidden.add(key)
                select(None)
                redraw()
            menu.add_command(label='Mở khóa' if key in locked else 'Khóa',command=toggle_lock)
            menu.add_command(label='Ẩn khi chỉnh',command=hide_element)
        if hidden:
            def reveal():
                snapshot()
                hidden.clear()
                redraw()
            menu.add_command(label='Hiện mọi phần tử',command=reveal)
        if len(selected_keys-hidden-locked)>1:
            menu.add_separator()
            for axis,labels in (('x',('Căn trái','Căn giữa ngang','Căn phải','Dàn đều ngang')),
                                ('y',('Căn trên','Căn giữa dọc','Căn dưới','Dàn đều dọc'))):
                for position,label in zip((0,.5,1,'space'),labels):
                    menu.add_command(label=label,command=lambda a=axis,p=position:apply_many(
                        arrange({key:current(key) for key in selected_keys-hidden-locked},a,p)))
        if menu.index('end') is not None:
            try:
                menu.tk_popup(event.x_root,event.y_root)
            finally:
                menu.grab_release()
        return 'break'

    def apply_template():
        from tuhoc.studio.layout_templates import template_for, read_template
        try:
            preset = read_template(templates,question.get('type'))
            snapshot()
            if preset is not None:
                preset = layout_v2(preset)
                restore((
                    {el:to_relative(rect,DESKTOP) for el,rect in preset['desktop'].items()},
                    {el:to_relative(rect,MOBILE) for el,rect in preset.get('mobile',{}).items()},
                    {extra['id']:extra for extra in preset.get('extras',[])},set(),set(),image_path,pending_image))
                return
            working.clear()
            working.update({el:to_relative(rect,DESKTOP) for el,rect in
                            template_for(question.get('type'))['desktop'].items()})
            for el in elements:
                expand_to(current(el))
            show_pixels()
            redraw()
        except (OSError,ValueError) as exc:
            messagebox.showerror('Không nạp được mẫu',str(exc),parent=win)

    def save_as_template():
        from tuhoc.studio.layout_templates import save_template
        try:
            save_template(templates,question['type'],draft())
            status.set('Đã lưu mẫu cho dạng câu hỏi này.')
        except (OSError,ValueError,KeyError) as exc:
            messagebox.showerror('Không lưu được mẫu',str(exc),parent=win)

    def paste_image(_event=None):
        nonlocal image_path, pending_image
        from PIL import Image, ImageGrab
        try:
            image=ImageGrab.grabclipboard()
            if not isinstance(image,Image.Image):
                status.set('Clipboard chưa có ảnh.')
                return 'break'
            if image.width*image.height > 16_000_000:
                status.set('Ảnh dán phải nhỏ hơn 16 megapixel.')
                return 'break'
            candidate=clipboard.with_name(uuid4().hex+'.png')
            image.convert('RGBA').save(candidate,format='PNG')
            if candidate.stat().st_size > 16*1024*1024:
                candidate.unlink()
                raise ValueError('Ảnh PNG vượt quá 16 MB.')
            snapshot()
            image_path=pending_image=candidate
            select('question_image')
            redraw()
        except (OSError,ValueError) as exc:
            status.set(str(exc))
        return 'break'

    def reset():
        if messagebox.askyesno('Khôi phục', 'Khôi phục bố cục mặc định của câu hỏi này?', parent=win):
            snapshot()
            working.clear()
            show_pixels()
            redraw()

    def restore_saved():
        if dirty():
            snapshot()
            restore((saved_layout,saved_mobile,saved_extras,set(),set(),original_image,None))

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
    fullscreen_btn = ttk.Button(toolbar, text='Phóng to cửa sổ',
                                command=lambda: maximize(not is_maximized()))
    fullscreen_btn.pack(side='right', padx=4)
    map_binding = win.bind('<Map>', maximize_on_map)
    win.bind('<Configure>', lambda event: fullscreen_btn.configure(
        text='Thu nhỏ cửa sổ' if is_maximized() else 'Phóng to cửa sổ') if event.widget is win else None, add='+')
    ttk.Label(toolbar, text='Thước: px | Ctrl+cuộn: zoom | Shift+cuộn: ngang').pack(side='right', padx=10)
    from tuhoc.ui.drag_scroll import CanvasPan

    canvas_pan = CanvasPan()
    canvas.bind('<ButtonPress-2>', lambda event: canvas_pan.start(canvas, event.y_root))
    canvas.bind('<B2-Motion>', lambda event: (canvas_pan.move(event.y_root), draw_rulers())[0])
    canvas.bind('<ButtonRelease-2>', lambda _event: canvas_pan.finish())
    canvas.bind('<ButtonPress-1>', down)
    canvas.bind('<B1-Motion>', move)
    canvas.bind('<ButtonRelease-1>', release)
    canvas.bind('<Motion>', hover)
    canvas.bind('<Double-Button-1>',edit_text)
    canvas.bind('<Key-t>', lambda event: live_key(event) if practice else add_text())
    canvas.bind('<KeyPress>', live_key)
    canvas.bind('<Control-d>',duplicate)
    if clipboard is not None and 'question_image' in system_elements:
        canvas.bind('<Control-v>',paste_image)
        ttk.Button(toolbar,text='Dán ảnh',command=paste_image).pack(side='left',padx=4)
    canvas.bind('<Escape>',escape_canvas)
    canvas.bind('<Tab>',cycle)
    canvas.bind('<ISO_Left_Tab>',cycle)
    canvas.bind('<Button-3>',show_menu)
    for key in ('Left','Right','Up','Down'):
        canvas.bind('<'+key+'>',nudge)
    canvas.bind('<Delete>',delete_text)
    font_spin.bind('<Return>', font_change)
    font_spin.bind('<FocusOut>', font_change)
    edit_controls = ttk.Frame(sidebar)
    edit_controls.pack(fill='x', pady=8)
    for label, command in (('Dùng mẫu', apply_template), ('Mặc định', reset),
                           ('Hoàn tác', undo), ('Làm lại', redo), ('Khôi phục đã lưu', restore_saved)):
        ttk.Button(edit_controls, text=label, command=command).pack(fill='x', pady=2)
    def history_key(event, action):
        if isinstance(event.widget,(tk.Entry,tk.Text,ttk.Entry,ttk.Combobox,ttk.Spinbox)):
            return
        action()
        return 'break'
    if templates is not None:
        ttk.Button(edit_controls,text='Lưu làm mẫu',command=save_as_template).pack(fill='x',pady=2)
    win.bind('<Control-z>',lambda e:history_key(e,undo))
    win.bind('<Control-y>',lambda e:history_key(e,redo))

    def style_shortcut(event, field):
        if isinstance(event.widget, (tk.Entry, tk.Text, ttk.Entry, ttk.Combobox)):
            return
        key = active[0]
        if text_element(key) and key not in locked:
            style = extras[key] if key in extras else current(key)
            change_text_style(**{field: not style.get(field, False)})
            select(key, preserve=True)
            return 'break'

    for shortcut, field in (('b','bold'), ('i','italic'), ('u','underline')):
        win.bind(f'<Control-{shortcut}>', lambda event, prop=field: style_shortcut(event, prop))

    footer = ttk.Frame(win, padding=10)
    footer.pack(side='bottom', fill='x', before=main)
    ttk.Label(footer, textvariable=status).pack(side='left')
    menu_button = None
    if live_question is not None:
        from tuhoc.studio.studio_live_preview import LivePreview

        try:
            live_renderer = LivePreview(live_question)
            practice_button = ttk.Button(footer, text='Thử làm bài', command=toggle_practice)
            practice_button.pack(side='left', padx=12)
            if question.get('type') in ('dropdown_fill_blank', 'inline_dropdown_fill'):
                menu_button = ttk.Button(footer, text='Mở menu', command=toggle_menu)
                menu_button.pack(side='left', padx=4)
            win.bind('<Destroy>', stop_live, add='+')
            poll_job = win.after(30, poll_live)
        except (OSError, RuntimeError) as exc:
            scene_error = str(exc)
    if preview is not None and live_renderer is None:
        ttk.Button(footer, text='Xem trước Pygame', command=try_preview).pack(side='left', padx=12)
    ttk.Button(footer, text='Lưu bố cục', command=save).pack(side='right', padx=5)
    ttk.Button(footer, text='Hủy', command=cancel).pack(side='right')
    # ESC closes the modal editor as before; maximize is not exclusive fullscreen.
    win.bind('<Escape>', lambda _e: toggle_practice(force_edit=True) if practice else cancel())
    win.protocol('WM_DELETE_WINDOW', cancel)
    sync_elements()
    for el in elements:
        expand_to(current(el))
    redraw()
    win.wait_window()
    if result[0] is not None and pending_image is not None:
        from shutil import copyfile
        copyfile(pending_image, clipboard)
    return result[0]


def edit_question_layout(parent, question):
    """Edit a question's persisted layout and return an updated question copy.

    The caller must replace the question in its collection and save that
    collection to JSON. Cancelling returns None and never mutates the input.
    """
    from tuhoc.studio.question_layout_store import get_layout, set_layout

    if not isinstance(question, dict):
        raise TypeError('question must be a dictionary')
    saved = edit_layout(parent, question, initial=get_layout(question))
    if saved is None:
        return None
    return set_layout(question, saved)
