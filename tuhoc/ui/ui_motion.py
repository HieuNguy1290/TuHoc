"""Safe Tkinter micro-interactions and cancellable easing animations."""
import tkinter as tk

from tuhoc.ui.ui_tokens import DURATION


def ease_out_cubic(t):
    return 1 - (1-t)**3


def animate_position(root, widget, start, end, duration=DURATION['slow'], on_complete=None):
    """Animate an already-placed widget; stale callbacks are ignored after destroy."""
    import time
    token = object()
    widget._motion_token = token
    if getattr(root,'reduce_motion',False) or duration<=0:
        widget.place_configure(x=end)
        if on_complete:on_complete()
        return
    started = time.monotonic()
    def frame():
        try:
            if not widget.winfo_exists() or getattr(widget, '_motion_token', None) is not token:
                return
            t = min(1., (time.monotonic()-started)/(duration/1000.))
            widget.place_configure(x=round(start+(end-start)*ease_out_cubic(t)))
            if t < 1: root.after(16, frame)
            elif on_complete: on_complete()
        except (tk.TclError, RuntimeError):
            pass
    frame()


def add_hover(widget, normal='#FFFFFF', hover='#EFF4FF', foreground=None):
    def change(bg):
        try:
            if widget.winfo_exists():
                widget.configure(bg=bg)
                if foreground is not None: widget.configure(fg=foreground)
        except tk.TclError: pass
    widget.bind('<Enter>', lambda _e=None: change(hover), add='+')
    widget.bind('<Leave>', lambda _e=None: change(normal), add='+')


def reveal(widget, root, duration=DURATION['normal']):
    """Short, non-blocking reveal via widget padding (no alpha flicker)."""
    import time
    token = object()
    widget._reveal_token = token
    if getattr(root,'reduce_motion',False) or duration<=0:
        widget.configure(pady=0)
        return
    start = time.monotonic()
    def frame():
        try:
            if not widget.winfo_exists() or getattr(widget,'_reveal_token',None) is not token: return
            t = min(1., (time.monotonic()-start)/(duration/1000.))
            widget.configure(pady=round(12*(1-ease_out_cubic(t))))
            if t<1: root.after(16,frame)
        except (tk.TclError,RuntimeError): pass
    frame()

def smoothstep(t):
    t=max(0.,min(1.,t));return t*t*(3-2*t)

def interpolate_color(widget,a,b,t):
    a=widget.winfo_rgb(a);b=widget.winfo_rgb(b)
    return '#%02x%02x%02x'%tuple(round((x+(y-x)*smoothstep(t))/257) for x,y in zip(a,b))

class MotionJobs:
    def __init__(self,root,reduced=False):self.root=root;self.reduced=reduced;self.jobs=set()
    def schedule(self,callback,delay=16):
        if self.reduced:return None
        token=[None]
        def run():
            self.jobs.discard(token[0]);callback()
        token[0]=self.root.after(delay,run);self.jobs.add(token[0]);return token[0]
    def cancel_all(self):
        for job in tuple(self.jobs):
            try:self.root.after_cancel(job)
            except Exception:pass
        self.jobs.clear()
