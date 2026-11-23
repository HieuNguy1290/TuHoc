"""Soan bai 'Nghe va chon dap an bang hinh' (type: listening_image_choice).

Du lieu luu:
    audio, image_options=[{'image','label'}], options=[ref...], answer=ref dung, correct_index
"""
from pathlib import Path

TYPE = 'listening_image_choice'
MIN_IMAGES, MAX_IMAGES = 2, 6
THUMB = (120, 80)


def validate(question):
    options = question.get('image_options') or []
    refs = [str(o.get('image', '') if isinstance(o, dict) else o).strip() for o in options]
    if not str(question.get('audio', '')).strip():
        raise ValueError('Dạng nghe cần chọn tệp âm thanh.')
    if not MIN_IMAGES <= len(refs) <= MAX_IMAGES or any(not r for r in refs):
        raise ValueError(f'Cần từ {MIN_IMAGES} đến {MAX_IMAGES} ảnh đáp án.')
    if len(set(refs)) != len(refs):
        raise ValueError('Các ảnh đáp án không được trùng nhau.')
    if str(question.get('answer', '')).strip() not in refs:
        raise ValueError('Đáp án đúng phải là một trong các ảnh đã chọn.')
    return question


def build_editor(parent, original, import_media, resolve_media=None):
    import tkinter as tk
    from tkinter import filedialog
    bg = 'white'

    def label(text):
        tk.Label(parent, text=text, bg=bg, fg='#285D40', anchor='w', font=('Segoe UI', 10)).pack(fill='x', pady=(8, 3))

    def resolve(ref):
        try:
            path = resolve_media(ref) if resolve_media and ref else None
            return path if path and Path(path).is_file() else None
        except (OSError, ValueError, TypeError):
            return None

    # ---- âm thanh ----
    label('Âm thanh câu hỏi (học sinh nghe rồi chọn hình đúng)')
    bar = tk.Frame(parent, bg=bg); bar.pack(fill='x')
    audio = tk.Entry(bar, font=('Segoe UI', 11)); audio.pack(side='left', fill='x', expand=True)
    audio.insert(0, original.get('audio', '') or '')
    audio_note = tk.Label(parent, bg=bg, fg='#496175', anchor='w', font=('Segoe UI', 9)); audio_note.pack(fill='x')

    def check_audio(*_):
        ref = audio.get().strip()
        audio_note.config(text='' if not ref else 'Đã tìm thấy tệp.' if resolve(ref) else 'Không tìm thấy tệp âm thanh.',
                          fg='#285D40' if resolve(ref) else '#B54747')

    def browse_audio():
        f = filedialog.askopenfilename(parent=parent.winfo_toplevel(), filetypes=[('Âm thanh', '*.mp3 *.wav *.ogg')])
        if f:
            audio.delete(0, 'end'); audio.insert(0, import_media(f)); check_audio()
    tk.Button(bar, text='Chọn tệp', command=browse_audio).pack(side='left', padx=6)
    audio.bind('<FocusOut>', check_audio, add='+'); check_audio()

    # ---- hình đáp án ----
    label(f'Chọn từ {MIN_IMAGES} đến {MAX_IMAGES} ảnh (nhập liên tiếp từ A). Chọn nút tròn ở ảnh ĐÚNG. '
          'Ô "Chữ dưới ảnh" là không bắt buộc.')
    options = original.get('image_options') or [{'image': x} for x in original.get('options', []) if x]
    correct = tk.IntVar(master=parent, value=int(original.get('correct_index', 0) or 0))
    if original.get('answer'):
        for i, opt in enumerate(options):
            if (opt.get('image') if isinstance(opt, dict) else opt) == original.get('answer'):
                correct.set(i)
    rows = []

    def refresh(field, thumb):
        ref = field.get().strip()
        path = resolve(ref)
        if not path:
            thumb.configure(image='', text='Chưa có ảnh' if not ref else 'Không tìm thấy ảnh'); thumb.image = None
            return
        try:
            from PIL import Image, ImageTk
            with Image.open(path) as src:
                pic = src.convert('RGBA'); pic.thumbnail(THUMB, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(pic, master=thumb)
            thumb.configure(image=photo, text=''); thumb.image = photo
        except (OSError, ValueError, ImportError):
            thumb.configure(image='', text='Không đọc được ảnh'); thumb.image = None

    for i in range(MAX_IMAGES):
        row = tk.Frame(parent, bg=bg); row.pack(fill='x', pady=3)
        tk.Radiobutton(row, text=chr(65 + i), variable=correct, value=i, bg=bg).pack(side='left')
        col = tk.Frame(row, bg=bg); col.pack(side='left', fill='x', expand=True)
        def captioned(text, **kw):
            line = tk.Frame(col, bg=bg); line.pack(fill='x', pady=1)
            tk.Label(line, text=text, width=22, anchor='w', bg=bg, fg='#496175', font=('Segoe UI', 9)).pack(side='left')
            box = tk.Entry(line, font=('Segoe UI', 10), **kw); box.pack(side='left', fill='x', expand=True)
            return box
        ref_entry = captioned('Tệp ảnh:')
        label_entry = captioned('Chữ dưới ảnh (tuỳ chọn):', fg='#285D40')
        if i < len(options):
            opt = options[i]
            ref_entry.insert(0, opt.get('image', '') if isinstance(opt, dict) else str(opt))
            if isinstance(opt, dict):
                label_entry.insert(0, opt.get('label', '') or '')
        thumb = tk.Label(row, text='Chưa có ảnh', width=18, height=5, bg='#F1F5F8', fg='#496175')
        thumb.pack(side='left', padx=5)

        def pick(field=ref_entry, t=thumb):
            f = filedialog.askopenfilename(parent=parent.winfo_toplevel(), filetypes=[('Ảnh', '*.png *.jpg *.jpeg *.gif *.webp')])
            if f:
                field.delete(0, 'end'); field.insert(0, import_media(f)); refresh(field, t)
        tk.Button(row, text='Chọn ảnh', command=pick).pack(side='left')
        ref_entry.bind('<FocusOut>', lambda e, field=ref_entry, t=thumb: refresh(field, t), add='+')
        rows.append((ref_entry, label_entry)); refresh(ref_entry, thumb)

    def collect():
        refs = [r.get().strip() for r, _ in rows]
        labels = [l.get().strip() for _, l in rows]
        filled = [bool(r) for r in refs]
        if sum(filled) < MIN_IMAGES:
            raise ValueError(f'Cần ít nhất {MIN_IMAGES} ảnh đáp án.')
        if filled != sorted(filled, reverse=True):
            raise ValueError('Hãy nhập ảnh liên tiếp từ A, không bỏ trống ở giữa.')
        n = sum(filled)
        refs, labels = refs[:n], labels[:n]
        if len(set(refs)) != n:
            raise ValueError('Các ảnh đáp án không được trùng nhau.')
        ref_audio = audio.get().strip()
        if not ref_audio:
            raise ValueError('Cần chọn tệp âm thanh.')
        if not resolve(ref_audio):
            raise ValueError(f'Không tìm thấy tệp âm thanh: {ref_audio}')
        for i, ref in enumerate(refs):
            if not resolve(ref):
                raise ValueError(f'Không tìm thấy ảnh đáp án {chr(65 + i)}: {ref}')
        picked = correct.get()
        if picked not in range(n):
            raise ValueError('Hãy chọn một đáp án đúng trong các ảnh đã nhập.')
        result = {'audio': ref_audio,
                  'image_options': [{'image': r, **({'label': l} if l else {})} for r, l in zip(refs, labels)],
                  'options': refs, 'answer': refs[picked], 'correct_index': picked}
        return validate(dict(result))
    return collect
