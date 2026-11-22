"""Reusable icon-only animations for Tkinter controls (no widget resizing)."""
import tkinter as tk
import weakref

_REGISTRY = weakref.WeakValueDictionary()

def register(name, widget):
    _REGISTRY[name] = widget
    return widget

def play(name, on_complete=None, duration=280):
    widget = _REGISTRY.get(name)
    if widget is None:
        if on_complete:
            on_complete()
        return
    micro_rotation(widget, on_complete, duration)

def micro_rotation(widget, on_complete=None, duration=280):
    """Rotate only the glyph in a fixed-size overlay; never change button geometry."""
    try:
        from PIL import Image, ImageTk, ImageDraw, ImageFont
        from tkinter import font as tkfont
        if not widget.winfo_exists():
            if on_complete: on_complete()
            return
        # Avoid overlapping animations and callbacks.
        if getattr(widget, '_icon_motion_running', False):
            return
        widget._icon_motion_running = True
        widget.update_idletasks()
        width, height = widget.winfo_width(), widget.winfo_height()
        if width < 2 or height < 2:
            widget._icon_motion_running = False
            if on_complete: on_complete()
            return
        bg = widget.cget('bg')
        fg = widget.cget('fg')
        original_text = widget.cget('text')
        source_photo = getattr(widget, '_icon_photo', None)
        if source_photo is None:
            source_photo = getattr(widget, 'image', None)
        source = None
        if source_photo is not None:
            try: source = ImageTk.getimage(source_photo).convert('RGBA')
            except Exception: pass
        if source is None:
            # Render the glyph into a transparent bitmap without modifying the widget.
            f = tkfont.Font(font=widget.cget('font'))
            font_size = abs(int(f.cget('size'))) or 18
            family = str(f.cget('family'))
            import subprocess
            path = subprocess.run(['fc-match', '-f', '%{file}', family], capture_output=True, text=True).stdout.strip()
            pil_font = ImageFont.truetype(path, max(10, font_size)) if path else ImageFont.load_default()
            source = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(source)
            draw.text((width / 2, height / 2), original_text, fill=fg, font=pil_font, anchor='mm')
        else:
            centered = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            centered.alpha_composite(source, ((width-source.width)//2, (height-source.height)//2))
            source = centered
        angles = (0, 4, 9, 12, 7, 0, -5, -2, 0)
        frames = [ImageTk.PhotoImage(source.rotate(-a, resample=Image.Resampling.BICUBIC), master=widget) for a in angles]
        # The overlay is placed over the button without changing parent layout.
        overlay = tk.Label(widget.master, bg=bg, bd=0, highlightthickness=0, image=frames[0])
        overlay.place(in_=widget, x=0, y=0, relwidth=1, relheight=1)
        overlay.lift()
        widget._icon_motion_overlay = overlay
        widget._icon_motion_frames = frames
        token = object()
        widget._icon_motion_token = token
        def finish():
            try:
                overlay.destroy()
                widget._icon_motion_overlay = None
                widget._icon_motion_frames = None
                widget._icon_motion_running = False
            except (tk.TclError, RuntimeError):
                pass
            if on_complete: on_complete()
        def tick(i=0):
            try:
                if not widget.winfo_exists() or widget._icon_motion_token is not token:
                    finish(); return
                overlay.configure(image=frames[i])
                if i + 1 < len(frames):
                    widget.after(max(16, duration//len(frames)), lambda: tick(i+1))
                else:
                    finish()
            except (tk.TclError, RuntimeError):
                finish()
        tick()
    except Exception:
        try: widget._icon_motion_running = False
        except Exception: pass
        if on_complete: on_complete()
