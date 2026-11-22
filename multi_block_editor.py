"""Edit all existing curriculum blocks for a selected theme/level/lesson.

Keeps the existing level_blocks.json row schema and unrelated records intact.
"""
import copy
import hashlib
import json
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from level_flow import library_file, load_rows
from safe_storage import commit_json
from lesson_display_names import breadcrumb
from studio_list import find_rows, remove_at
from ui_components import Toast


def open_block_editor(app, theme, level, lesson=1, create_mode=False):
    data_dir = app.curriculum.data_dir
    level, lesson = int(level), int(lesson or 1)
    path = library_file(data_dir, 'blocks')
    original = load_rows(data_dir, 'blocks', None)
    def matches(row):
        return (str(row.get('theme', '')) == str(theme) and
                int(row.get('level') or 0) == level and
                int(row.get('lesson') or 1) == lesson)
    selected = [copy.deepcopy(row) for row in original if matches(row)]
    selected.sort(key=lambda row: int(row.get('order') or 0))
    blocks = selected
    if create_mode and selected:
        messagebox.showwarning('Đã có nội dung', 'Bài học đã có block. Hãy mở từ danh sách để sửa.')
        return None
    window = tk.Toplevel(app)
    window.title(f'{"Tạo" if create_mode else "Sửa"} bài học · {breadcrumb(data_dir, theme, level, lesson)}')
    # Start maximized on Windows; use screen-sized geometry on other systems.
    try:
        window.state('zoomed')
    except tk.TclError:
        window.geometry(f'{window.winfo_screenwidth()}x{window.winfo_screenheight()}+0+0')
    window.minsize(780, 530)
    window.configure(bg='#F5F8F5')
    # A maximized child must not be repositioned relative to its owner.
    # On Windows, zoomed uses the work area (excludes taskbar).
    window.grab_set()
    active = {'index': 0 if blocks else None}
    dirty = {'value': False}
    updating = {'value': False}

    heading = tk.Frame(window, bg='#244D3B', padx=16, pady=12)
    heading.pack(fill='x')
    tk.Label(heading, text=breadcrumb(data_dir, theme, level, lesson),
             bg='#244D3B', fg='white', font=('Segoe UI', 15, 'bold')).pack(anchor='w')
    tk.Label(heading, text='Mỗi block gồm: Giới thiệu (title) · Hình ảnh (image) · Nội dung chính (content)',
             bg='#244D3B', fg='#D6E8DB').pack(anchor='w')
    main = tk.Frame(window, bg='#F5F8F5', padx=12, pady=12)
    main.pack(fill='both', expand=True)
    left = tk.Frame(main, bg='white', padx=10, pady=10, width=330)
    left.pack(side='left', fill='y', padx=(0, 12))
    left.pack_propagate(False)
    tk.Label(left, text='DANH SÁCH BLOCK', bg='white', fg='#244D3B',
             font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(0, 8))
    search=tk.StringVar()
    tk.Label(left,text='Tìm tên hoặc nội dung',bg='white').pack(anchor='w')
    ttk.Entry(left,textvariable=search).pack(fill='x',pady=(0,6))
    sort=tk.StringVar(value='Thứ tự bài')
    ttk.Combobox(left,textvariable=sort,values=('Thứ tự bài','Tiêu đề'),
                 state='readonly').pack(fill='x',pady=(0,6))
    visible=[]
    listbox = tk.Listbox(left, font=('Segoe UI', 11), exportselection=False, activestyle='none')
    listbox.pack(fill='both', expand=True)
    right = tk.Frame(main, bg='white', padx=18, pady=12)
    right.pack(side='left', fill='both', expand=True)
    title_var = tk.StringVar()
    image_var = tk.StringVar()
    layout_var = tk.StringVar(value='auto')
    layout_row = tk.Frame(right, bg='white')
    layout_row.pack(fill='x', pady=(0, 10))
    tk.Label(layout_row, text='BỐ CỤC HIỂN THỊ', bg='white', fg='#244D3B',
             font=('Segoe UI', 10, 'bold')).pack(side='left', padx=(0, 12))
    layout_combo = ttk.Combobox(layout_row, textvariable=layout_var, state='readonly',
        values=('auto', 'image_wrap_left', 'legacy'))
    layout_combo.pack(side='left', fill='x', expand=True)
    tk.Label(layout_row, text='auto = tương thích bài cũ; image_wrap_left = chữ ôm ảnh',
             bg='white', fg='#526C59').pack(side='left', padx=(8, 0))
    tk.Label(right, text='GIỚI THIỆU / TIÊU ĐỀ BLOCK', bg='white', fg='#244D3B',
             font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(4, 5))
    title_entry = ttk.Entry(right, textvariable=title_var, font=('Segoe UI', 12))
    title_entry.pack(fill='x', pady=(0, 16))
    tk.Label(right, text='HÌNH ẢNH MINH HỌA', bg='white', fg='#244D3B',
             font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, 5))
    image_row = tk.Frame(right, bg='white')
    image_row.pack(fill='x', pady=(0, 16))
    ttk.Entry(image_row, textvariable=image_var).pack(side='left', fill='x', expand=True)
    tk.Label(right, text='NỘI DUNG CHÍNH', bg='white', fg='#244D3B',
             font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, 5))
    content = tk.Text(right, font=('Segoe UI', 12), wrap='word', undo=True)
    content.pack(fill='both', expand=True)
    scrollbar = ttk.Scrollbar(content, orient='vertical', command=content.yview)
    scrollbar.pack(side='right', fill='y')
    content.configure(yscrollcommand=scrollbar.set)
    status = tk.StringVar(value=f'Đã nạp {len(blocks)} block từ JSON.')

    def refresh_list():
        listbox.delete(0, 'end')
        visible[:]=find_rows(blocks,search.get(),fields=('title','content'),
                             sort_by='title' if sort.get()=='Tiêu đề' else None)
        for i,block in visible:
            listbox.insert('end',f'#{i+1}  {str(block.get("title",""))[:42] or "(Chưa có giới thiệu)"}')
        indices=[i for i,_row in visible]
        if active['index'] in indices:
            index=indices.index(active['index'])
            listbox.selection_set(index)
            listbox.see(index)
        status.set(f'{len(blocks)} block · ' + ('Có thay đổi chưa lưu' if dirty['value'] else 'Chưa có thay đổi'))

    def flush():
        i = active['index']
        if updating['value'] or i is None or i >= len(blocks):
            return
        block = blocks[i]
        for key, value in [('title', title_var.get()), ('image', image_var.get()),
                           ('content', content.get('1.0', 'end-1c'))]:
            if block.get(key, '') != value:
                block[key] = value
                dirty['value'] = True
        layout = layout_var.get()
        if layout != str(block.get('layout') or 'auto'):
            if layout == 'auto':
                block.pop('layout', None)
            else:
                block['layout'] = layout
            dirty['value'] = True
        refresh_list()

    def show(i):
        updating['value'] = True
        active['index'] = i
        block = blocks[i] if i is not None and i < len(blocks) else {}
        title_var.set(str(block.get('title', '')))
        image_var.set(str(block.get('image', '')))
        layout_var.set(str(block.get('layout') or 'auto'))
        content.configure(state='normal')
        content.delete('1.0', 'end')
        content.insert('1.0', str(block.get('content', '')))
        state = 'normal' if i is not None else 'disabled'
        title_entry.configure(state=state)
        content.configure(state=state)
        updating['value'] = False
        refresh_list()

    def select(_event=None):
        selection = listbox.curselection()
        if selection:
            index=visible[selection[0]][0]
            if index!=active['index']:
                flush()
                show(index)
    listbox.bind('<<ListboxSelect>>', select)
    search.trace_add('write',lambda *_args:refresh_list())
    sort.trace_add('write',lambda *_args:refresh_list())

    def add():
        flush()
        block = {'theme': theme, 'level': level, 'lesson': lesson,
                 'order': len(blocks) + 1, 'title': '', 'image': '', 'content': '', 'layout': 'image_wrap_left'}
        blocks.append(block)
        dirty['value'] = True
        show(len(blocks) - 1)

    def duplicate():
        flush()
        i = active['index']
        if i is None: return
        clone = copy.deepcopy(blocks[i])
        clone.pop('id', None)  # Never duplicate an existing explicit ID.
        blocks.insert(i + 1, clone)
        dirty['value'] = True
        show(i + 1)

    def move(delta):
        flush()
        i = active['index']
        if i is None or not 0 <= i + delta < len(blocks): return
        blocks[i], blocks[i + delta] = blocks[i + delta], blocks[i]
        dirty['value'] = True
        show(i + delta)

    def remove():
        i = active['index']
        if i is None or not messagebox.askyesno('Xóa block', 'Xóa block này khỏi bài học?', parent=window): return
        flush()
        remaining,ticket=remove_at(blocks,i)
        blocks[:]=remaining
        dirty['value']=True
        show(min(i,len(blocks)-1) if blocks else None)
        def restore():
            flush()
            blocks[:]=ticket.restore(blocks)
            dirty['value']=True
            show(min(i,len(blocks)-1))
        Toast(window,'Đã xóa block.',duration=6000,action=('Hoàn tác',restore))

    def choose_image():
        i = active['index']
        if i is None: return
        source_name = filedialog.askopenfilename(parent=window, title='Chọn ảnh',
                       filetypes=[('Hình ảnh', '*.png *.jpg *.jpeg *.gif'), ('Tất cả', '*.*')])
        if not source_name: return
        source = Path(source_name)
        target_dir = Path(data_dir) / 'content_library' / 'media'
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / source.name
            if target.exists() and target.read_bytes() != source.read_bytes():
                digest = hashlib.sha256(source.read_bytes()).hexdigest()[:12]
                target = target_dir / f'{source.stem}_{digest}{source.suffix.lower()}'
            if not target.exists(): shutil.copy2(source, target)
            image_var.set('media/' + target.name)
            flush()
        except OSError as exc:
            messagebox.showerror('Không thể thêm ảnh', str(exc), parent=window)

    layout_combo.bind('<<ComboboxSelected>>', lambda _event: flush())
    ttk.Button(image_row, text='Chọn ảnh...', command=choose_image).pack(side='left', padx=(8, 0))
    actions = tk.Frame(left, bg='white')
    actions.pack(fill='x', pady=(10, 0))
    for label, fn in [('+ Thêm block', add), ('Nhân bản', duplicate), ('Lên ↑', lambda: move(-1)),
                      ('Xuống ↓', lambda: move(1)), ('Xóa block', remove)]:
        ttk.Button(actions, text=label, command=fn).pack(fill='x', pady=2)

    def save():
        flush()
        if create_mode and not blocks:
            messagebox.showwarning('Chưa có block', 'Hãy thêm ít nhất một block trước khi tạo bài học.', parent=window)
            return
        if not blocks:
            if not messagebox.askyesno('Bài học trống', 'Lưu bài học không có block?', parent=window): return
        from unified_subjects import subject_image
        missing=[str(block.get('title') or index) for index,block in enumerate(blocks,1)
                 if block.get('image') and not subject_image(data_dir,block['image'])]
        if missing:
            messagebox.showwarning('Thiếu ảnh','Kiểm tra ảnh của block: '+', '.join(missing),parent=window)
            return
        new_rows = []
        inserted = False
        for row in original:
            if matches(row):
                if not inserted:
                    for i, block in enumerate(blocks, 1):
                        item = copy.deepcopy(block)
                        item['order'] = i
                        item['theme'], item['level'], item['lesson'] = theme, level, lesson
                        new_rows.append(item)
                    inserted = True
                continue
            new_rows.append(row)
        if not inserted:
            for i, block in enumerate(blocks, 1):
                item = copy.deepcopy(block)
                item['order'] = i
                new_rows.append(item)
        try:
            changes = {path: new_rows}
            if create_mode:
                lessons_path = library_file(data_dir, 'lessons')
                lesson_rows = load_rows(data_dir, 'lessons', None)
                if any(matches(row) for row in lesson_rows):
                    messagebox.showerror('Bài học đã tồn tại', 'Bài học này đã được tạo. Không ghi đè.', parent=window)
                    return
                lesson_rows.append({'theme': theme, 'level': level, 'lesson': lesson,
                                    'title': blocks[0].get('title', '') or f'Lesson {lesson}',
                                    'instructions': '', 'content': '', 'image': ''})
                changes[lessons_path] = lesson_rows
            commit_json(changes)
            app.curriculum.reload()
        except (OSError, ValueError) as exc:
            messagebox.showerror('Không lưu được', str(exc), parent=window)
            return
        dirty['value'] = False
        messagebox.showinfo('Đã lưu', f'Đã lưu {len(blocks)} block theo thứ tự order.', parent=window)
        window.destroy()
        app.level_editor('lessons')

    def close():
        flush()
        if dirty['value'] and not messagebox.askyesno('Chưa lưu', 'Bỏ các thay đổi chưa lưu?', parent=window): return
        window.destroy()

    footer = tk.Frame(window, bg='#F5F8F5', padx=14, pady=10)
    footer.pack(fill='x')
    tk.Label(footer, textvariable=status, bg='#F5F8F5', fg='#426451').pack(side='left')
    ttk.Button(footer, text='Lưu toàn bộ block', command=save).pack(side='right', padx=5)
    ttk.Button(footer, text='Đóng', command=close).pack(side='right', padx=5)
    window.protocol('WM_DELETE_WINDOW', close)
    show(active['index'])
    if create_mode:
        add()
    return window
