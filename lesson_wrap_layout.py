"""Optional textbook-style block renderer for Tkinter lessons.

Uses a full-width selectable Text widget with pixel-aware line wrapping around
an image. Existing lesson routing and legacy renderers are unchanged.
"""
import tkinter as tk
from tkinter import font as tkfont


def _wrap_paragraph(paragraph, font, first_width, full_width, narrow_lines):
    """Wrap text by measured pixel width, without dropping words."""
    if not paragraph:
        return ['']
    words = paragraph.split()
    result = []
    line = ''
    for word in words:
        width = first_width if len(result) < narrow_lines else full_width
        candidate = f'{line} {word}' if line else word
        if font.measure(candidate) <= width:
            line = candidate
            continue
        if line:
            result.append(line)
            line = ''
        width = first_width if len(result) < narrow_lines else full_width
        # Break unspaced long strings rather than letting them overflow.
        while word and font.measure(word) > width:
            split = 1
            while split < len(word) and font.measure(word[:split + 1]) <= width:
                split += 1
            result.append(word[:split])
            word = word[split:]
            width = first_width if len(result) < narrow_lines else full_width
        line = word
    result.append(line)
    return result


def render_wrapped_block(parent, block, image_path, title_size, content_size,
                         title_color, content_color, image_width, image_height):
    """Return the selectable text widget; never alter the source block."""
    title = str(block.get('title') or '')
    body = str(block.get('content') or '')
    tk.Label(parent, text=title, bg='white', fg=title_color,
             font=('Segoe UI', title_size, 'bold'), anchor='w',
             justify='left', wraplength=950).pack(fill='x', pady=(0, 12))

    picture = None
    image_w = image_h = 0
    if image_path:
        try:
            from PIL import Image, ImageTk
            with Image.open(image_path) as source:
                im = source.convert('RGBA')
                im.thumbnail((image_width, image_height), Image.Resampling.LANCZOS)
                image_w, image_h = im.size
                photo = ImageTk.PhotoImage(im, master=parent)
            picture = tk.Label(parent, image=photo, bg='white', bd=0)
            picture._lesson_photo = photo
        except (OSError, ValueError, ImportError, tk.TclError):
            picture = None
            image_w = image_h = 0

    holder = tk.Frame(parent, bg='white')
    holder.pack(fill='x', expand=True)
    font = tkfont.Font(family='Segoe UI', size=content_size)
    line_px = max(18, font.metrics('linespace') + 6)
    text = tk.Text(holder, font=font, bg='white', fg=content_color,
                   wrap='none', relief='flat', bd=0, padx=2, pady=3,
                   exportselection=False, cursor='xterm', undo=False)
    text.pack(fill='x', expand=True)
    if picture is not None:
        picture.place(in_=holder, x=0, y=0, width=image_w, height=image_h)
        picture.lift()

    state = {'width': 0}

    def reflow(event=None):
        width = max(260, holder.winfo_width() - 12)
        if width == state['width']:
            return
        state['width'] = width
        gap = 18 if image_w else 0
        # Only the lines beside the picture are indented. Later lines span full width.
        narrow_lines = (image_h + line_px - 1) // line_px if image_h else 0
        full_width = max(120, width - 12)
        narrow_width = max(100, full_width - image_w - gap)
        all_lines = []
        for paragraph in body.split('\n'):
            # Line budgets are global, not reset at paragraph boundaries.
            remaining = max(0, narrow_lines - len(all_lines))
            all_lines.extend(_wrap_paragraph(paragraph, font, narrow_width,
                                             full_width, remaining))
        # Tk tags indent only the lines beside the picture. This is a visual
        # layout transformation; original JSON and audio content are untouched.
        text.configure(state='normal')
        text.delete('1.0', 'end')
        text.insert('1.0', '\n'.join(all_lines))
        if narrow_lines and all_lines:
            last = min(narrow_lines, len(all_lines))
            text.tag_add('beside_picture', '1.0', f'{last}.end')
            text.tag_configure('beside_picture', lmargin1=image_w + gap,
                               lmargin2=image_w + gap)
        text.configure(height=max(len(all_lines), narrow_lines, 1), state='disabled')

    holder.bind('<Configure>', reflow, add='+')
    holder.after_idle(reflow)
    return text
