"""Optional visual UI alignment grid for Tkinter on Windows.

A transparent, mouse-click-through Toplevel overlays a grid without swallowing
button clicks, entry focus, scrolling or floating-recorder dragging.
Coordinates are relative to the main application's client-area top-left.
"""
import ctypes
import sys
import tkinter as tk


def grid_positions(length, step):
    return list(range(0, max(0, int(length)), max(5, int(step))))


class UIGrid:
    KEY = '#ff00ff'  # color key: fully transparent on Windows

    def __init__(self, root, spacing=50):
        self.root = root
        self.spacing = max(10, int(spacing))
        self.visible = False
        self.overlay = None
        self.canvas = None
        self._cursor = (-999, -999)
        self._last_geometry = None
        self._scheduled = None
        self._native_hwnd = None
        self._window_proc_callback = None
        self._original_window_proc = None
        self._pointer_job = None
        self._pointer_items = []
        root.bind_all('<Motion>', self._on_motion, add='+')
        root.bind('<Configure>', self._on_root_configure, add='+')
        root.bind('<Unmap>', self._on_unmap, add='+')
        root.bind('<Map>', self._on_map, add='+')
        root.bind('<Control-g>', lambda e: self.toggle(), add='+')
        root.bind('<Control-G>', lambda e: self.toggle(), add='+')
        root.bind('<Escape>', lambda e: self.hide() if self.visible else None, add='+')

    def toggle(self):
        if self.visible:
            self.hide()
        else:
            self.show()
        return self.visible

    def show(self):
        if sys.platform != 'win32':
            raise RuntimeError('Lưới phủ trong suốt hiện hỗ trợ Windows. Không thể bảo đảm click-through trên hệ điều hành này.')
        self.visible = True
        try:
            self._ensure_overlay()
            self._sync()
        except Exception:
            self.visible = False
            self._destroy_overlay()
            raise

    def hide(self):
        self.visible = False
        if self._pointer_job is not None:
            try: self.root.after_cancel(self._pointer_job)
            except tk.TclError: pass
            self._pointer_job = None
        if self.overlay is not None:
            try:
                if self.overlay.winfo_viewable():
                    self.overlay.withdraw()
            except tk.TclError: pass

    def set_spacing(self, value):
        self.spacing = max(10, min(200, int(value)))
        if self.visible: self._draw()

    def _ensure_overlay(self):
        if self.overlay is not None:
            try:
                if self.overlay.winfo_exists(): return
            except tk.TclError: pass
        self.overlay = tk.Toplevel(self.root)
        self.overlay.withdraw()
        self.overlay.overrideredirect(True)
        self.overlay.configure(bg=self.KEY)
        self.overlay.wm_attributes('-transparentcolor', self.KEY)
        self.canvas = tk.Canvas(self.overlay, highlightthickness=0, bd=0, bg=self.KEY)
        self.canvas.pack(fill='both', expand=True)
        self.overlay.update_idletasks()
        # On Windows, a Tk Toplevel's winfo_id may be the inner Tk child.
        # The OUTER native wrapper is what receives mouse hit-testing.
        user32 = ctypes.windll.user32
        LONG_PTR = ctypes.c_ssize_t
        user32.GetParent.argtypes = [ctypes.c_void_p]
        user32.GetParent.restype = ctypes.c_void_p
        user32.GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
        user32.GetWindowLongPtrW.restype = LONG_PTR
        user32.SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, LONG_PTR]
        user32.SetWindowLongPtrW.restype = LONG_PTR
        user32.CallWindowProcW.argtypes = [LONG_PTR, ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, LONG_PTR]
        user32.CallWindowProcW.restype = LONG_PTR
        inner = self.overlay.winfo_id()
        outer = user32.GetParent(inner)
        if not outer:
            raise RuntimeError('Không xác định được cửa sổ phủ Windows; lưới không được bật để tránh khóa chuột.')
        GWL_EXSTYLE = -20
        GWL_WNDPROC = -4
        WS_EX_TRANSPARENT = 0x20
        WS_EX_LAYERED = 0x80000
        WS_EX_TOOLWINDOW = 0x80
        WS_EX_NOACTIVATE = 0x08000000
        flags = WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
        style = user32.GetWindowLongPtrW(outer, GWL_EXSTYLE)
        user32.SetWindowLongPtrW(outer, GWL_EXSTYLE, style | flags)
        actual = user32.GetWindowLongPtrW(outer, GWL_EXSTYLE)
        if actual & flags != flags:
            raise RuntimeError('Không bật được click-through an toàn. Đã hủy lưới để không chặn chuột.')
        # Native hit-test defense: even if Windows ignores the transparent
        # extended style for a layered Tk window, return HTTRANSPARENT.
        # Keep callback alive until the overlay is destroyed.
        WNDPROC = ctypes.WINFUNCTYPE(LONG_PTR, ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, LONG_PTR)
        old_proc = user32.GetWindowLongPtrW(outer, GWL_WNDPROC)
        WM_NCHITTEST = 0x0084
        HTTRANSPARENT = -1
        def mouse_passthrough(hwnd, msg, wparam, lparam):
            if msg == WM_NCHITTEST:
                return HTTRANSPARENT
            return user32.CallWindowProcW(old_proc, hwnd, msg, wparam, lparam)
        cb = WNDPROC(mouse_passthrough)
        self._window_proc_callback = cb
        self._original_window_proc = old_proc
        self._native_hwnd = outer
        previous = user32.SetWindowLongPtrW(outer, GWL_WNDPROC, ctypes.cast(cb, ctypes.c_void_p).value)
        if not previous:
            self._window_proc_callback = None
            raise RuntimeError('Không kích hoạt được cơ chế click-through; lưới đã được tắt an toàn.')
        # SWP_FRAMECHANGED forces the window manager to apply updated flags.
        user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                                         ctypes.c_int, ctypes.c_int, ctypes.c_uint]
        user32.SetWindowPos(outer, None, 0, 0, 0, 0, 0x0020 | 0x0002 | 0x0001 | 0x0010)

    def _sync(self):
        if not self.visible or not self.overlay: return
        try:
            if self.root.state() == 'iconic':
                self.overlay.withdraw();return
            x, y = self.root.winfo_rootx(), self.root.winfo_rooty()
            w, h = self.root.winfo_width(), self.root.winfo_height()
            if w < 2 or h < 2: return
            geometry = (x, y, w, h)
            if geometry != self._last_geometry:
                self.overlay.geometry(f'{w}x{h}+{x}+{y}')
                self._last_geometry = geometry
                self._draw()
            # Do not raise/deiconify an already-visible layered window on every
            # Configure event: Windows repaints it, producing persistent flicker.
            if not self.overlay.winfo_viewable():
                self.overlay.deiconify()
                self.overlay.lift(self.root)
        except tk.TclError: pass

    def _draw(self):
        if not self.visible or not self.canvas: return
        try:
            c = self.canvas
            c.delete('grid')
            w, h = self.root.winfo_width(), self.root.winfo_height()
            s = self.spacing
            for x in grid_positions(w, s):
                c.create_line(x, 0, x, h, fill='#6fa5bf', width=1, tags='grid')
                if x: c.create_text(x+3, 11, anchor='nw', text=str(x), font=('Consolas', 8), fill='#28708b', tags='grid')
            for y in grid_positions(h, s):
                c.create_line(0, y, w, y, fill='#6fa5bf', width=1, tags='grid')
                if y: c.create_text(4, y+2, anchor='nw', text=str(y), font=('Consolas', 8), fill='#28708b', tags='grid')
            self._draw_pointer()
        except tk.TclError: pass

    def _draw_pointer(self):
        if not self.visible or not self.canvas: return
        c = self.canvas
        try:
            x, y = self._cursor
            w, h = self.root.winfo_width(), self.root.winfo_height()
            if not (0 <= x < w and 0 <= y < h):
                for item in self._pointer_items:
                    c.itemconfigure(item, state='hidden')
                return
            lx = min(max(0, x + 14), max(0, w - 115))
            ly = min(max(0, y + 15), max(0, h - 32))
            if len(self._pointer_items) != 4:
                c.delete('pointer')
                self._pointer_items = [
                    c.create_line(x, 0, x, h, fill='#ed7a44', dash=(3, 4), tags='pointer'),
                    c.create_line(0, y, w, y, fill='#ed7a44', dash=(3, 4), tags='pointer'),
                    c.create_rectangle(lx, ly, lx+110, ly+27, fill='#233c4d', outline='', tags='pointer'),
                    c.create_text(lx+8, ly+13, anchor='w', text='', fill='white', font=('Consolas',10,'bold'), tags='pointer'),
                ]
            a,b,rect,label = self._pointer_items
            c.coords(a, x, 0, x, h)
            c.coords(b, 0, y, w, y)
            c.coords(rect, lx, ly, lx+110, ly+27)
            c.coords(label, lx+8, ly+13)
            c.itemconfigure(label, text=f'X: {x}  Y: {y}')
            for item in self._pointer_items:
                c.itemconfigure(item, state='normal')
        except tk.TclError: pass

    def _render_pointer_once(self):
        self._pointer_job = None
        self._draw_pointer()

    def _on_motion(self, event):
        if not self.visible: return
        try:
            x = event.x_root - self.root.winfo_rootx()
            y = event.y_root - self.root.winfo_rooty()
            if (x,y) != self._cursor:
                self._cursor = (x,y)
                # At most ~30 updates per second, instead of one repaint for
                # each raw mouse movement event.
                if self._pointer_job is None:
                    self._pointer_job = self.root.after(33, self._render_pointer_once)
        except tk.TclError: pass

    def _on_root_configure(self, event):
        if event.widget is not self.root or not self.visible:return
        if self._scheduled is None:
            self._scheduled=self.root.after_idle(self._configure_once)

    def _configure_once(self):
        self._scheduled=None
        self._sync()

    def _on_unmap(self,event):
        if event.widget is self.root and self.overlay:
            try:self.overlay.withdraw()
            except tk.TclError:pass

    def _on_map(self,event):
        if event.widget is self.root and self.visible:self.root.after_idle(self._sync)

    def _destroy_overlay(self):
        # Restore native window proc while callback is still alive.
        if self._native_hwnd and self._original_window_proc:
            try:
                user32 = ctypes.windll.user32
                user32.SetWindowLongPtrW(self._native_hwnd, -4, self._original_window_proc)
            except Exception:
                pass
        if self.overlay is not None:
            try:self.overlay.destroy()
            except tk.TclError:pass
        self.overlay=None;self.canvas=None
        self._pointer_items=[]
        self._last_geometry=None
        self._native_hwnd=None
        self._original_window_proc=None
        self._window_proc_callback=None
