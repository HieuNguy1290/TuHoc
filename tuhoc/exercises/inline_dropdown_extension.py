from tuhoc.exercises.exercise_gfx import open_exercise_window
"""Chọn đáp án từ danh sách thả xuống ngay trong câu (một hoặc nhiều chỗ).

Ví dụ: 'The pizza .... yummy.' với lựa chọn are / is / am, đáp án đúng is.

Dữ liệu:
  type='inline_dropdown_fill', prompt, image (không bắt buộc),
  blank_text    : câu có chỗ chấm (.... hoặc ___)
  blank_options : list các list lựa chọn, mỗi chỗ chấm một list
  blank_answers : đáp án đúng của từng chỗ chấm
  preselect     : True = hiện sẵn lựa chọn đầu tiên (dạng "tìm và sửa lỗi")
"""
from pathlib import Path
from tuhoc.exercises.image_sentence_extension import BLANK, blank_count, split_text, fill_text  # noqa: F401


def expected(question):
    return [str(x) for x in (question.get('blank_answers') or [])]


def correct(question, answer):
    exp = expected(question)
    return (isinstance(answer, (list, tuple)) and len(answer) == len(exp) and bool(exp)
            and all(str(a).strip().casefold() == str(b).strip().casefold() for a, b in zip(answer, exp)))


def build_editor(parent, original, import_media, resolve_media=None):
    import tkinter as tk
    from tkinter import filedialog

    def label(value, target=None):
        tk.Label(target or parent, text=value, bg='white', fg='#285D40', anchor='w').pack(fill='x', pady=(9, 3))

    label('Hình minh họa (không bắt buộc)')
    row = tk.Frame(parent, bg='white'); row.pack(fill='x')
    image = tk.Entry(row, font=('Segoe UI', 11)); image.pack(side='left', fill='x', expand=True)
    image.insert(0, str(original.get('image') or ''))

    def browse():
        f = filedialog.askopenfilename(parent=parent.winfo_toplevel(), filetypes=[('Ảnh', '*.png *.jpg *.jpeg *.gif *.webp')])
        if f:
            image.delete(0, 'end'); image.insert(0, import_media(f))

    tk.Button(row, text='Chọn ảnh', command=browse).pack(side='left', padx=5)

    label('Câu có chỗ chọn: gõ .... (4 dấu chấm) tại mỗi vị trí hiện danh sách thả xuống (Enter để xuống dòng)')
    template = tk.Text(parent, height=3, wrap='word', font=('Segoe UI', 11)); template.pack(fill='x')
    template.insert('1.0', original.get('blank_text') or 'The pizza .... yummy.')

    pre = tk.BooleanVar(master=parent, value=bool(original.get('preselect', False)))
    tk.Checkbutton(parent, text='Hiện sẵn lựa chọn đầu tiên trong ô (dùng cho dạng "tìm và sửa lỗi")',
                   variable=pre, bg='white', anchor='w').pack(fill='x', pady=(6, 0))

    holder = tk.Frame(parent, bg='white'); holder.pack(fill='x')
    saved_opts = [list(x) for x in (original.get('blank_options') or [])]
    saved_ans = [str(x) for x in (original.get('blank_answers') or [])]
    if not saved_opts and not original.get('blank_text'):
        saved_opts, saved_ans = [['are', 'is', 'am']], ['is']
    widgets = []   # [(Text, Entry)]

    def snapshot():
        opts, ans = [], []
        for t, e in widgets:
            opts.append([s.strip() for s in t.get('1.0', 'end-1c').splitlines() if s.strip()])
            ans.append(e.get().strip())
        return opts, ans

    def render(*_):
        opts, ans = snapshot() if widgets else (saved_opts, saved_ans)
        n = blank_count(template.get('1.0', 'end-1c'))
        for c in holder.winfo_children():
            c.destroy()
        widgets.clear()
        for i in range(n):
            box = tk.LabelFrame(holder, text=f' Chỗ chấm {i + 1} ', bg='white', fg='#285D40'); box.pack(fill='x', pady=6)
            label('Các lựa chọn (mỗi dòng một lựa chọn, 2–8 lựa chọn)', box)
            t = tk.Text(box, height=4, font=('Segoe UI', 11)); t.pack(fill='x', padx=6)
            t.insert('1.0', '\n'.join(opts[i]) if i < len(opts) else '')
            label('Đáp án đúng (phải trùng một lựa chọn)', box)
            e = tk.Entry(box, font=('Segoe UI', 11)); e.pack(fill='x', padx=6, pady=(0, 6))
            e.insert(0, ans[i] if i < len(ans) else '')
            widgets.append((t, e))

    template.bind('<KeyRelease>', render, add='+')
    render()

    def collect():
        text = template.get('1.0', 'end-1c').strip()
        n = blank_count(text)
        if n < 1:
            raise ValueError('Câu cần có ít nhất một chỗ chấm (gõ ....).')
        opts, ans = snapshot()
        if len(opts) != n:
            raise ValueError('Số ô lựa chọn chưa khớp số chỗ chấm, hãy thử gõ lại câu.')
        for i, (o, a) in enumerate(zip(opts, ans), 1):
            if not 2 <= len(o) <= 8:
                raise ValueError(f'Chỗ chấm {i}: cần từ 2 đến 8 lựa chọn.')
            if len({x.casefold() for x in o}) != len(o):
                raise ValueError(f'Chỗ chấm {i}: các lựa chọn không được trùng nhau.')
            if a not in o:
                raise ValueError(f'Chỗ chấm {i}: đáp án đúng phải trùng chính xác một lựa chọn.')
        ref = image.get().strip()
        if ref and resolve_media:
            path = resolve_media(ref)
            if not path or not Path(path).is_file():
                raise ValueError('Không tìm thấy ảnh minh họa.')
        return {'type': 'inline_dropdown_fill', 'blank_text': text, 'blank_options': opts, 'blank_answers': ans,
                'preselect': bool(pre.get()), 'options': [], 'answer': ' | '.join(ans), 'image': ref}

    return collect


def run(question):
    import re
    import pygame
    from tuhoc.exercises.pygame_exercises import _image, _cached_font
    from tuhoc.exercises.exercise_image_zoom import draw_zoom_icon, draw as draw_zoom
    from tuhoc.studio.question_layout_runtime import element as layout_element, rectangle
    from tuhoc.studio.layout_typography import resolve_font
    from tuhoc.studio.layout_scroll_extent import content_bottom as layout_content_bottom
    from tuhoc.exercises.exercise_layout import Page
    pygame.init(); pygame.display.init()
    screen = open_exercise_window((960, 640))
    pygame.display.set_caption('Tự Học - Bài tập')
    clock = pygame.time.Clock()
    page = Page(screen)
    font = _cached_font(None, 22, False)
    sent_font = _cached_font(None, 28, False)
    small = _cached_font(None, 22, False)
    opt_font = _cached_font(None, 26, False)
    opt_bold = _cached_font(None, 26, True)
    hint_font = _cached_font(None, 19, False)
    hover_edge = (44, 143, 108)
    title = _cached_font(None, 26, True)
    navy = (32, 52, 77); bg = (241, 247, 252); green = (44, 143, 108); blue = (70, 119, 169)

    exp = expected(question)
    raw = question.get('blank_options') or []
    options = []
    for i in range(len(exp)):
        o = [str(x) for x in (raw[i] if i < len(raw) else [])]
        if exp[i] not in o:
            o.append(exp[i])
        options.append(o)
    selected = {i: 0 for i in range(len(exp))} if question.get('preselect') else {}
    opened = None

    picture = None; picture_path = question.get('_pygame_image')
    image_geometry = layout_element(question, 'question_image')
    image_rect = image_frame = None
    if picture_path:
        try:
            if image_geometry:
                from tuhoc.studio.layout_images import pygame_image
                picture, image_rect, image_frame = pygame_image(picture_path,image_geometry,(65,180,420,200))
            else:
                picture = _image(picture_path, (420, 200))
        except (OSError, ValueError, pygame.error): picture = None

    slot_geometry = [layout_element(question, f'slot_{i}') for i in range(len(options))]
    menu_geometry = layout_element(question, 'answer_menu') or {}
    field_w = [max(110, max(sent_font.size(o)[0] for o in opts) + 54) for opts in options]
    # Optional editor geometry: reposition the sentence and its interactive slots
    # together. Legacy coordinates remain unchanged for questions without layout.
    answer_style = layout_element(question, 'answer_area')
    answer_layout = layout_element(question, 'dropdown_area') or answer_style
    sent_font = resolve_font(answer_style, sent_font, 28)
    left, right, line_h = 65, 875, 52
    if (question.get('layout') or {}).get('version') == 4 and answer_layout:
        line_h = max(15, answer_layout.get('height', line_h))
    if answer_layout:
        left = max(25, min(890, int(answer_layout.get('x', left))))
        width = max(110, int(answer_layout.get('width', right - 65)))
        right = min(935, left + width)
    items = []; x = left; y = 0
    for typ, value in split_text(question.get('blank_text', '')):
        if typ == 'text':
            for line_no, part in enumerate(re.split(r'\r\n|\r|\n', value)):
                if line_no:
                    x = left; y += line_h
                for token in re.findall(r'\S+\s*|\s+', part):
                    w = sent_font.size(token)[0]
                    if x + w > right and x > left:
                        x = left; y += line_h
                    items.append(('text', token, x, y, w)); x += w
        else:
            w = field_w[value] if value < len(field_w) else 110
            if x + w > right and x > left:
                x = left; y += line_h
            items.append(('slot', value, x, y, w)); x += w + 8
    sentence_h = y + line_h

    from tuhoc.studio.layout_typography import TextBlock
    prompt = TextBlock(question.get('prompt') or 'Chọn đáp án đúng:',
                       layout_element(question, 'question_text'), font, 22, (52, 109, 845), 27, 3)
    prompt_bottom = prompt.bottom
    pic_top = prompt_bottom + 8
    sentence_top = (pic_top + picture.get_height() + 30) if picture else prompt_bottom + 34
    if answer_layout and 'y' in answer_layout:
        sentence_top = max(35, int(answer_layout['y']))

    content_extent = layout_content_bottom(question, max(640, sentence_top + sentence_h + 60))

    def can_submit():
        return len(selected) == len(exp) and bool(exp)

    def answer():
        return [options[i][selected[i]] for i in range(len(exp))]

    def leave():
        from tuhoc.ui.pygame_exit_dialog import confirm
        return confirm(screen, clock, 'Thoát bài tập?', 'Bạn muốn rời bài tập này?')

    zoom = None
    try:
        while True:
            surface = page.begin(content_extent)
            surface.fill(bg)
            pygame.draw.rect(surface, 'white', (25, 25, 910, surface.get_height()-50), border_radius=18)
            idx = max(1, int(question.get('_index') or 1)); tot = max(1, int(question.get('_total') or 1))
            prompt.draw(surface, navy)
            zoom_rects = []; fields = {}
            if picture:
                pr = image_rect or picture.get_rect(topleft=(left, pic_top))
                surface.blit(picture, pr)
                zoom_rects.append((draw_zoom_icon(surface, image_frame or pr), picture_path))
            for typ, value, ix, iy, w in items:
                ry = sentence_top + iy
                if typ == 'text':
                    surface.blit(sent_font.render(value, True, navy), (ix, ry))
                else:
                    geometry = slot_geometry[value] if value < len(slot_geometry) else None
                    rect = pygame.Rect(rectangle(geometry, (ix, ry - 4, w, max(1,line_h-10))))
                    field_font = resolve_font(geometry, sent_font, 28)
                    fields[value] = rect
                    hovered = rect.collidepoint((pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1] + page.scroll)) and opened is None
                    pygame.draw.rect(surface, (233, 247, 240) if hovered else (247, 251, 255), rect, border_radius=8)
                    edge = hover_edge if hovered else blue if opened == value else (150, 175, 205)
                    pygame.draw.rect(surface, edge, rect, 2, border_radius=8)
                    if value in selected:
                        txt = field_font.render(options[value][selected[value]], True, navy)
                    else:
                        txt = field_font.render('Chọn', True, (140, 150, 162))
                    surface.blit(txt, txt.get_rect(midleft=(rect.x + 14, rect.centery)))
                    cx, cy = rect.right - 20, rect.centery
                    pygame.draw.polygon(surface, navy, [(cx - 6, cy - 3), (cx + 6, cy - 3), (cx, cy + 4)])
            can = can_submit()
            submit = pygame.Rect(375, 556, 210, 46)

            menu = []
            if opened is not None and opened in fields:
                f = fields[opened]; n = len(options[opened]); row_h = 44; pad = 6; gap = 3
                mh = n * row_h + (n - 1) * gap + pad * 2
                my = f.bottom + 4
                if my + mh > 548 + page.scroll:
                    my = f.top - mh - 4
                mr = pygame.Rect(rectangle(menu_geometry, (f.x, my, f.width, mh)))
                row_h = max(1, (mr.height - (n-1)*gap - 2*pad)//n)
                pygame.draw.rect(surface, (214, 223, 233), mr.move(0, 4), border_radius=10)
                pygame.draw.rect(surface, 'white', mr, border_radius=10)
                pygame.draw.rect(surface, (170, 188, 208), mr, 1, border_radius=10)
                mouse = (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1] + page.scroll)
                for j, o in enumerate(options[opened]):
                    rr = pygame.Rect(mr.x + pad, mr.y + pad + j * (row_h + gap), mr.width - pad * 2, row_h)
                    is_sel = selected.get(opened) == j
                    is_hover = rr.collidepoint(mouse)
                    if is_hover:
                        pygame.draw.rect(surface, (222, 245, 233), rr, border_radius=8)
                        pygame.draw.rect(surface, hover_edge, rr, 2, border_radius=8)
                    elif is_sel:
                        pygame.draw.rect(surface, (228, 240, 253), rr, border_radius=8)
                        pygame.draw.rect(surface, (150, 180, 214), rr, 1, border_radius=8)
                    ft = resolve_font(slot_geometry[opened],
                                      resolve_font(menu_geometry, opt_bold if is_sel else opt_font, 26), 26)
                    label_surf = ft.render(o, True, navy)
                    surface.blit(label_surf, label_surf.get_rect(midleft=(rr.x + 14, rr.centery)))
                    menu.append((rr, j))
            page.present(question)
            page.complete(question, submit, small, can and opened is None)
            if zoom:
                draw_zoom(screen, zoom)
            regions = None
            if question.get('_studio_scene'):
                from tuhoc.studio.studio_live_preview import option_rects, text_rect
                regions = {'question_text': text_rect(prompt),
                           'question_image': (image_frame or pr) if picture else None,
                           'dropdown_area': (left, sentence_top, right-left, sentence_h),
                           'answer_menu': mr if opened is not None and opened in fields else None}
                regions.update(option_rects(((rect, i) for i, rect in fields.items()), 'slot'))
            page.frame(question, regions)
            for event in page.events(scroll_enabled=(opened is None and zoom is None)):
                if zoom:
                    if event.type in (pygame.MOUSEBUTTONDOWN, pygame.QUIT) or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                        zoom = None
                    continue
                if event.type == pygame.QUIT:
                    if leave(): return None
                    continue
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if opened is not None:
                            opened = None; continue
                        if leave(): return None
                        continue
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and can and opened is None:
                        return answer()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if submit.collidepoint(event.viewport_pos):
                        if can and opened is None:
                            return answer()
                        continue
                    z = next((p for r, p in zoom_rects if r.collidepoint(event.pos)), None)
                    if z:
                        zoom = z; continue
                    hit = next((j for rr, j in menu if rr.collidepoint(event.pos)), None)
                    if hit is not None:
                        selected[opened] = hit; opened = None; continue
                    if menu:
                        mr = menu[0][0].unionall([r for r, _ in menu])
                        if mr.inflate(6, 6).collidepoint(event.pos):
                            continue
                    fh = next((i for i, r in fields.items() if r.collidepoint(event.pos)), None)
                    if fh is not None:
                        opened = None if opened == fh else fh; continue
                    opened = None
            clock.tick(30)
    finally:
        pass  # Session worker owns the shared SDL display
