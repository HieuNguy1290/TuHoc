"""Show still PNG/JPEG or animated GIF/WebP via Pillow without blocking Tk."""
import tkinter as tk
from collections import OrderedDict
from pathlib import Path

# Cache is interpreter-scoped: never reuse Tk PhotoImages across different roots.
_CACHE = OrderedDict()
_CACHE_MAX_FRAMES = 300
_CACHE_MAX_BYTES = 48 * 1024 * 1024

def _image_bytes(frames):
    return sum(frame.width() * frame.height() * 4 for frame in frames)


def _cache_put(key, value):
    # Do not cache a single oversized animation; labels retain their own frames.
    if len(value[0]) > _CACHE_MAX_FRAMES or _image_bytes(value[0]) > _CACHE_MAX_BYTES:
        return
    _CACHE[key] = value
    _CACHE.move_to_end(key)
    while len(_CACHE) > 1 and (
        sum(len(v[0]) for v in _CACHE.values()) > _CACHE_MAX_FRAMES
        or sum(_image_bytes(v[0]) for v in _CACHE.values()) > _CACHE_MAX_BYTES
    ):
        _CACHE.popitem(last=False)

def _load_frames(parent, path, width, height):
    from PIL import Image, ImageTk, ImageSequence
    try:
        root = parent.winfo_toplevel()
        # Tk image handles are owned by a specific Tcl interpreter.
        interpreter = id(root.tk)
        key = (interpreter, str(path.resolve()), path.stat().st_mtime_ns, int(width), int(height))
    except OSError: key = None
    if key is not None and key in _CACHE:
        value = _CACHE[key]
        _CACHE.move_to_end(key)
        return value
    frames = []
    durations = []
    with Image.open(path) as source:
        animated = getattr(source, 'n_frames', 1) > 1
        # LANCZOS is only worth its cost for a single still image.
        method = Image.Resampling.BILINEAR if animated else Image.Resampling.LANCZOS
        for frame in ImageSequence.Iterator(source):
            fr = frame.convert('RGBA')
            ratio = min(max(1,int(width))/fr.width, max(1,int(height))/fr.height)
            fr = fr.resize((max(1, round(fr.width*ratio)), max(1, round(fr.height*ratio))), method)
            frames.append(ImageTk.PhotoImage(fr, master=parent))
            durations.append(max(40, min(10000, int(frame.info.get('duration',source.info.get('duration',100)) or 100))))
            if len(frames) >= 300: break  # avoid huge memory use in user-added files
    if key is not None and frames: _cache_put(key, (frames, durations))
    return frames, durations

def display_image(parent, path, width=350, height=240, bg='white', **pack_options):
    """Create a label; loop animated frames while its widget is alive.

    Image dimensions are maximum bounding-box dimensions; aspect ratio is maintained.
    """
    path = Path(path)
    frames, durations = _load_frames(parent, path, width, height)
    if not frames: raise ValueError('Ảnh không có khung hình')
    label = tk.Label(parent,image=frames[0],bg=bg)
    label._animation_frames = frames
    label._animation_job = None
    label.pack(**pack_options)
    if len(frames)>1:
        def tick(index):
            try:
                if not label.winfo_exists(): return
                label.configure(image=frames[index])
                label._animation_job = label.after(durations[index], lambda: tick((index+1)%len(frames)))
            except tk.TclError: pass
        label._animation_job = label.after(durations[0], lambda: tick(1))
        def cleanup(event):
            if event.widget is not label: return
            job=label._animation_job
            if job:
                try: label.after_cancel(job)
                except tk.TclError: pass
                label._animation_job=None
        label.bind('<Destroy>',cleanup,add='+')
    return label
