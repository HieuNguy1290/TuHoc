"""H2.4 reference-faithful rainbow loading screen.

The supplied reference is the static visual layer. Percent, progress bar and
orbit highlights are dynamic Tk canvas items. No Pygame/SDL is involved.
Requires Pillow (already used by earlier logo-loading variants).
"""
from tuhoc.paths import PROJECT_ROOT
from functools import lru_cache
import math
import os
import threading
import time
import tkinter as tk

try:
    from PIL import Image, ImageTk
except ImportError as exc:
    raise ImportError('H2.4 cần Pillow: pip install pillow') from exc

_ASSET = os.path.join(str(PROJECT_ROOT / 'assets'),
                      'subject_loading_background.png')

_IMAGE_LOCK = threading.Lock()


@lru_cache(maxsize=1)
def _native_size():
    with Image.open(_ASSET) as raw:
        return raw.size


@lru_cache(maxsize=2)
def _scaled_background(width,height):
    with Image.open(_ASSET) as raw:
        return raw.resize((width,height),Image.Resampling.BICUBIC,reducing_gap=2.0).convert('RGB')


def _target_size(w,h):
    sw,sh=_native_size()
    scale=min(w/sw,h/sh)
    return max(1,round(sw*scale)),max(1,round(sh*scale)),scale


def _background(width,height):
    with _IMAGE_LOCK:
        return _scaled_background(width,height)


def preload_async(viewport=None):
    if viewport is None or min(viewport)<30:
        return

    def preload():
        try:
            w,h,_scale=_target_size(*viewport)
            _background(w,h)
        except OSError:
            pass

    threading.Thread(target=preload,name='TuHocBackground',daemon=True).start()


class _Dyn:
    """Canvas proxy: every item it creates is tagged 'dyn' so a frame only
    replaces the animated layer and never re-submits the large background."""
    def __init__(self, canvas):
        self._c = canvas

    def __getattr__(self, name):
        target = getattr(self._c, name)
        if name.startswith('create_'):
            def make(*args, **kw):
                kw.setdefault('tags', 'dyn')
                return target(*args, **kw)
            return make
        return target


class SubjectLoadingScreen(tk.Frame):
    def __init__(self, master, subject):
        super().__init__(master, bg='#082a71')
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg='#082a71')
        self.canvas.pack(fill='both', expand=True)
        self.subject = subject
        self.progress = 0.0
        self.target_progress = 0.0
        self._started = time.monotonic()
        self._duration = 0.0 if getattr(master,'reduce_motion',False) else 2.0
        self._ready = False
        self._completed = False
        self._on_complete = None
        self.status = 'Đang khởi động...'
        self.phase = 0.0
        self.alive = True
        self.job = None
        self._last_tick = time.monotonic()
        self._photo = None
        self._cached_size = None
        self._bg_item = None
        self.canvas.bind('<Configure>', self._resize)
        self.bind('<Destroy>', self._destroy, add='+')
        self._tick()

    def _destroy(self, event):
        if event.widget is not self:
            return
        self.alive = False
        if self.job is not None:
            try:
                self.after_cancel(self.job)
            except tk.TclError:
                pass
            self.job = None
        self._photo = None
        self._bg_item = None

    def set_progress(self, percent, status):
        """Backward-compatible status update; percent is now clock-driven."""
        self.status = status

    def finish_when_ready(self, callback):
        """Show 100% only when loading is ready AND 2 seconds elapsed."""
        self._ready = True
        self._on_complete = callback
        self.status = 'Hoàn tất!'

    def _resize(self, event=None):
        # A drag-resize emits many <Configure> events; the 30 fps tick repaints once
        # per frame instead of re-scaling the image for each of them.
        if self._completed:
            self._draw()

    def _tick(self):
        self.job = None
        if not self.alive or not self.winfo_exists():
            return
        now = time.monotonic()
        dt = min(0.12, max(0., now - self._last_tick))
        self._last_tick = now
        if self._duration:
            self.phase += dt * 1.25
        elapsed = now - self._started
        # Progress is based on a monotonic clock, not on loading-phase jumps.
        # Hold at 99% if preparation takes longer than two seconds.
        self.progress = min(100.0 if self._ready else 99.0,
                            100.0 * min(1.0, elapsed / max(.001,self._duration)))
        if self._ready and elapsed >= self._duration and not self._completed:
            self.progress = 100.0
            self._completed = True
            self.status = 'Hoàn tất!'
            self._draw()
            # Display the completed frame briefly before navigation.
            if self._on_complete is not None:
                self.job = self.after(120 if self._duration else 0,self._on_complete)
            return
        self._draw()
        self.job = self.after(33, self._tick)

    def _draw(self):
        c = self.canvas
        if not c.winfo_exists():
            return
        w, h = c.winfo_width(), c.winfo_height()
        if w < 30 or h < 30:
            return
        # 'contain' scaling preserves the reference composition, including logo.
        rw,rh,scale=_target_size(w,h)
        ox, oy = (w - rw) / 2, (h - rh) / 2
        if self._cached_size != (rw, rh) or self._bg_item is None:
            # reducing_gap makes the downscale much cheaper than a full LANCZOS pass.
            scaled=_background(rw,rh)
            self._photo = ImageTk.PhotoImage(scaled, master=c)
            self._cached_size = (rw, rh)
            c.delete('all')
            self._bg_item = c.create_image(w / 2, h / 2, image=self._photo, tags='bg')
        else:
            c.delete('dyn')
            c.coords(self._bg_item, w / 2, h / 2)
        c = _Dyn(c)
        def pos(x, y):
            return ox + x * scale, oy + y * scale

        # Moving light particles around the reference's central circular logo.
        # Static rendered particles stay as background detail.
        for i, color in enumerate(('#FFF9A3', '#66EFFF', '#F8A7FF', '#B1FF81')):
            a = self.phase + i * math.pi / 2
            x, y = pos(832 + 352 * math.cos(a), 354 + 180 * math.sin(a))
            r = max(2, 5.5 * scale)
            c.create_oval(x-r*2, y-r*2, x+r*2, y+r*2,
                          fill=color, outline='', stipple='gray50')
            c.create_oval(x-r, y-r, x+r, y+r, fill=color, outline='white')

        # Percentage, outside the logo and centered beneath it.
        cx, py = pos(832, 634)
        font_size = max(17, round(65 * scale))
        value = f'{int(self.progress)}%'
        c.create_text(cx+2, py+3, text=value,
                      font=('Segoe UI', font_size, 'bold'), fill='#15468C')
        c.create_text(cx, py, text=value,
                      font=('Segoe UI', font_size, 'bold'), fill='white')

        # Rounded OUTER frame; square-cornered rainbow segments are kept
        # strictly within the straight inner track (never inside rounded caps).
        x0, y0 = pos(475, 691)
        x1, y1 = pos(1189, 735)
        height = y1 - y0
        rad = height / 2
        border = max(1.0, 2 * scale)
        track_color = '#133E91'
        border_color = '#A5D9FF'

        # Draw the continuous rounded track first, with no overlapping outlines.
        c.create_oval(x0, y0, x0 + height, y1,
                      fill=track_color, outline='')
        c.create_oval(x1 - height, y0, x1, y1,
                      fill=track_color, outline='')
        c.create_rectangle(x0 + rad, y0, x1 - rad, y1,
                           fill=track_color, outline='')

        # The seven straight-edged color blocks use the inner rectangle only.
        # Both edges stay clear of the rounded ends and the frame border.
        inner_left = x0 + rad + border
        inner_right = x1 - rad - border
        inner_top = y0 + max(border, 3 * scale)
        inner_bottom = y1 - max(border, 3 * scale)
        track_width = max(0.0, inner_right - inner_left)
        fill_width = track_width * max(0.0, min(100.0, self.progress)) / 100.0
        palette = ('#FF5BCA', '#FFB45C', '#FFE86D', '#8EF46C',
                   '#23F2D4', '#54C5FF', '#8259FF')
        if fill_width > 0:
            # Each color is one rectangular segment with a 90-degree corner.
            segment = fill_width / len(palette)
            for i, color in enumerate(palette):
                xa = inner_left + segment * i
                xb = inner_left + segment * (i + 1)
                c.create_rectangle(xa, inner_top, xb, inner_bottom,
                                   fill=color, outline='')

            # Animated shimmer is also confined to the filled rectangle.
            end = inner_left + fill_width
            band_w = 110 * scale
            t = (self.phase * 0.55) % 1.0
            t = t * t * (3 - 2 * t)
            center = inner_left - band_w + (fill_width + 2 * band_w) * t
            for ratio, stip in ((1.0, 'gray12'), (0.62, 'gray25'), (0.3, 'gray50')):
                lo = max(inner_left, center - band_w * ratio / 2)
                hi = min(end, center + band_w * ratio / 2)
                if hi - lo > 0.5:
                    c.create_rectangle(lo, inner_top, hi, inner_bottom,
                                       fill='white', outline='', stipple=stip)

        # Draw the frame LAST so the light-blue rounded outline remains visible.
        c.create_arc(x0, y0, x0 + height, y1, start=90, extent=180,
                     style=tk.ARC, outline=border_color, width=border)
        c.create_arc(x1 - height, y0, x1, y1, start=-90, extent=180,
                     style=tk.ARC, outline=border_color, width=border)
        c.create_line(x0 + rad, y0, x1 - rad, y0,
                      fill=border_color, width=border)
        c.create_line(x0 + rad, y1, x1 - rad, y1,
                      fill=border_color, width=border)
        sx, sy = pos(832, 786)
        sf = max(10, round(26 * scale))
        c.create_text(sx+1, sy+2, text=self.status,
                      font=('Segoe UI', sf, 'bold'), fill='#17336C')
        c.create_text(sx, sy, text=self.status,
                      font=('Segoe UI', sf, 'bold'), fill='white')
