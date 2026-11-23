"""Direct formatting controls for a selection in the Studio."""
import re
import tkinter as tk
from tkinter import ttk

from tuhoc.studio.question_layout_store import FONT_FAMILIES, TEXT

FLAGS = (('bold', 'B', 'Đậm'), ('italic', 'I', 'Nghiêng'), ('underline', 'U', 'Gạch chân'))
FAMILY_DEFAULT = 'Mặc định'


def format_segments(runs, start, end, values):
    """Overlay the selected attributes and coalesce identical adjacent ranges."""
    boundaries = sorted({start, end, *(run[k] for run in runs for k in ('start', 'end'))})
    result = []
    for left, right in zip(boundaries, boundaries[1:]):
        style = {}
        for run in runs:
            if run['start'] <= left < run['end']:
                style.update({key: run[key] for key in TEXT & run.keys()})
        if start <= left < end:
            style.update(values)
        if not style:
            continue
        if result and result[-1]['end'] == left and all(
            result[-1].get(key) == style.get(key) for key in TEXT
        ):
            result[-1]['end'] = right
        else:
            result.append(dict(start=left, end=right, **style))
    return result


def display_text(raw, *, markdown):
    if not markdown:
        return raw, []
    from tuhoc.exercises.question_rich_text import _BOLD, plain

    ranges = []
    removed = 0
    for match in _BOLD.finditer(raw):
        start = match.start() - removed
        ranges.append(dict(start=start, end=start + len(match[1]), bold=True))
        removed += len(match[0]) - len(match[1])
    return plain(raw), ranges


def draw_text_preview(canvas, raw, style, rect, scale, color, tag, *, markdown):
    value, inherited = display_text(raw, markdown=markdown)
    if not value:
        return
    left, top, right, bottom = rect
    base = {'start': 0, 'end': len(value), 'font_size': 24,
            **{key: style[key] for key in TEXT & style.keys()}}
    ranges = format_segments([base, *inherited, *style.get('runs', [])], 0, len(value), {})
    face_cache = {}
    line = []
    width = 0
    y = top
    padding = round(scale * style.get('line_spacing', 0))

    def font_for(run):
        flags = ' '.join(key for key, _, _ in FLAGS if run.get(key)) or 'normal'
        face = (run.get('font_family') or 'Segoe UI', -max(1, round(run.get('font_size', 24) * scale)), flags)
        if face not in face_cache:
            face_cache[face] = canvas.tk.getint(canvas.tk.call('font', 'metrics', face, '-linespace'))
        return face

    def flush():
        nonlocal y, width
        if not line:
            y += max(1, round(scale * style.get('font_size', 24))) + padding
            return
        line_height = max(face_cache[face] for _, face, _ in line)
        if y < bottom:
            align = style.get('align', 'left')
            free = max(0, right-left-width)
            x = left + (free / 2 if align == 'center' else free if align == 'right' else 0)
            for text, face, size in line:
                canvas.create_text(x, y, text=text, font=face, fill=color, anchor='nw',
                                   tags=(tag, 'formatted_text'))
                x += size
        y += line_height + padding
        width = 0
        line.clear()

    for token in re.finditer(r'\n|[^\S\n]+|[^\s]+', value):
        if y >= bottom:
            break
        word = token.group()
        if word == '\n':
            flush()
            continue
        if word.isspace() and not line:
            continue
        pieces = []
        for run in ranges:
            start = max(run['start'], token.start())
            end = min(run['end'], token.end())
            if start < end:
                face = font_for(run)
                part = value[start:end]
                measure = lambda text: canvas.tk.getint(canvas.tk.call('font', 'measure', face, text))
                while part and measure(part) > right-left:
                    part = part[:max(0, len(part)-max(1, len(part)//8))]
                if part:
                    pieces.append((part, face, measure(part)))
        token_width = sum(size for _, _, size in pieces)
        if line and width + token_width > right-left:
            flush()
            if word.isspace():
                continue
        line.extend(pieces)
        width += token_width
    if line:
        flush()


def open_text_format(owner, value, source, on_save, *, inherited=()):
    """Apply styling immediately to the selected text and commit it on Save."""
    dialog = tk.Toplevel(owner)
    dialog.title('Định dạng đoạn chữ')
    dialog.transient(owner)
    body = ttk.Frame(dialog, padding=10)
    body.pack(fill='both', expand=True)
    toolbar = ttk.Frame(body)
    toolbar.pack(fill='x')
    base = {key: source.get(key, False) for key, _, _ in FLAGS}
    base.update(font_family=source.get('font_family', ''), font_size=int(source.get('font_size', 24)))
    runs = list(source.get('runs', []))
    family = tk.StringVar(value=base['font_family'] or FAMILY_DEFAULT)
    size = tk.StringVar(value=str(base['font_size']))
    flags = {key: tk.BooleanVar(value=base[key]) for key, _, _ in FLAGS}
    feedback = tk.StringVar(value='Bôi đen đoạn chữ để định dạng.')
    font_select = ttk.Combobox(toolbar, textvariable=family, values=(FAMILY_DEFAULT, *FONT_FAMILIES[1:]),
                               state='readonly', width=18)
    font_select.pack(side='left')
    size_entry = ttk.Combobox(toolbar, textvariable=size, values=(8, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 72),
                              width=5, validate='key',
                              validatecommand=(dialog.register(lambda s: not s or s.isdecimal() and len(s) <= 2), '%P'))
    size_entry.pack(side='left', padx=6)
    buttons = {}
    for key, symbol, label in FLAGS:
        button = ttk.Checkbutton(toolbar, text=f'{symbol} · {label}', variable=flags[key],
                                 command=lambda field=key: apply({field: flags[field].get()}),
                                 style='Toolbutton')
        button.pack(side='left', padx=2)
        buttons[key] = button

    content = tk.Text(body, width=59, height=8, wrap='word', exportselection=False,
                      padx=8, pady=8)
    content.pack(fill='both', expand=True, pady=8)
    content.insert('1.0', value)
    content.configure(state='disabled')
    ttk.Label(body, textvariable=feedback).pack(anchor='w')
    marks = []
    undo_stack = []
    redo_stack = []

    def font_tuple(style):
        decorations = ' '.join(key for key, _, _ in FLAGS if style[key])
        return (style['font_family'] or 'Segoe UI', style['font_size'], decorations or 'normal')

    def render():
        if marks:
            content.tag_delete(*marks)
            marks.clear()
        content.configure(font=font_tuple(base))
        styles = format_segments([*inherited, *runs], 0, len(value), {})
        for index, run in enumerate(styles):
            tag = f'format_{index}'
            content.tag_configure(tag, font=font_tuple({**base, **run}))
            content.tag_add(tag, f"1.0+{run['start']}c", f"1.0+{run['end']}c")
            marks.append(tag)
        content.tag_raise('sel')

    def selection():
        if content.tag_ranges('sel'):
            return len(content.get('1.0', 'sel.first')), len(content.get('1.0', 'sel.last'))
        return None

    def update_controls(_event=None):
        region = selection()
        active = bool(region)
        for button in buttons.values():
            button.state(['!disabled' if active else 'disabled'])
        font_select.state(['!disabled' if active else 'disabled'])
        size_entry.state(['!disabled' if active else 'disabled'])
        if not region:
            return
        start, end = region
        styles = format_segments([*inherited, *runs], start, end, {})
        points = {start, *(run['start'] for run in styles if start < run['start'] < end),
                  *(run['end'] for run in styles if start < run['end'] < end)}
        selected = [{**base, **next((run for run in styles if run['start'] <= pos < run['end']), {})}
                    for pos in points]
        for field, button in buttons.items():
            values = {style[field] for style in selected}
            flags[field].set(values == {True})
            button.state(['alternate' if len(values) > 1 else '!alternate'])
        families = {style['font_family'] for style in selected}
        sizes = {style['font_size'] for style in selected}
        family.set((families.pop() or FAMILY_DEFAULT) if len(families) == 1 else '')
        size.set(str(sizes.pop()) if len(sizes) == 1 else '')

    def apply(values):
        region = selection()
        if not region:
            return
        if region[1] > 10000:
            feedback.set('Vùng định dạng phải nằm trong 10.000 ký tự đầu tiên.')
            return
        updated = format_segments(runs, *region, values)
        if len(updated) > 256:
            feedback.set('Đã đạt giới hạn 256 vùng định dạng.')
            return
        set_runs(updated)
        feedback.set('Định dạng đã áp dụng cho đoạn đang chọn.')

    def set_runs(updated):
        if updated != runs:
            undo_stack.append(runs[:])
            redo_stack.clear()
            runs[:] = updated
            render()
            update_controls()

    def restore(stack, other):
        if stack:
            other.append(runs[:])
            runs[:] = stack.pop()
            render()
            update_controls()
        return 'break'

    def select_all(_event):
        content.tag_add('sel', '1.0', 'end-1c')
        update_controls()
        return 'break'

    def apply_size(_event=None):
        value = size.get()
        if value.isdecimal() and 8 <= int(value) <= 96:
            apply({'font_size': int(value)})

    def shortcut(key):
        apply({key: not flags[key].get()})
        return 'break'

    def close(save):
        if save and runs != source.get('runs', []):
            on_save(runs)
        dialog.destroy()
        owner.grab_set()

    font_select.bind('<<ComboboxSelected>>', lambda _e: apply({'font_family': '' if family.get() == FAMILY_DEFAULT else family.get()}))
    size_entry.bind('<<ComboboxSelected>>', apply_size)
    size_entry.bind('<Return>', apply_size)
    content.bind('<<Selection>>', update_controls)
    content.bind('<Control-a>', select_all)
    dialog.bind('<Control-z>', lambda _e: restore(undo_stack, redo_stack))
    dialog.bind('<Control-y>', lambda _e: restore(redo_stack, undo_stack))
    for key, symbol, _ in FLAGS:
        dialog.bind(f'<Control-{symbol.lower()}>', lambda _e, field=key: shortcut(field))
    actions = ttk.Frame(body)
    actions.pack(fill='x', pady=(8, 0))
    ttk.Button(actions, text='Lưu', command=lambda: close(True)).pack(side='right')
    ttk.Button(actions, text='Hủy', command=lambda: close(False)).pack(side='right', padx=6)

    ttk.Button(actions, text='Xóa định dạng đoạn', command=lambda: set_runs([])).pack(side='left')
    dialog.bind('<Escape>', lambda _e: close(False))
    dialog.protocol('WM_DELETE_WINDOW', lambda: close(False))
    render()
    update_controls()
    dialog.wait_visibility()
    dialog.grab_set()
    content.focus_set()
    return dialog
