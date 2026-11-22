"""Floating and draggable recording launcher (Tkinter; no external dependency)."""
import tkinter as tk


class FloatingRecorder(tk.Frame):
    """One draggable + button, separate mic/video actions, compact active state."""

    def __init__(self, master, voice, video, stop, folder, devices=None, mouse_effects=None, admin_action=None):
        super().__init__(master, bg='#FFFFFF', bd=1, relief='solid', highlightthickness=1,
                         highlightbackground='#DBE5DC')
        self.voice_action, self.video_action = voice, video
        self.stop_action, self.folder_action = stop, folder
        self.devices_action = devices
        self.mouse_effects_action = mouse_effects
        self.admin_action = admin_action
        self.expanded = False
        self.kind = None
        self._drag_origin = None
        self._dragged = False
        self._coordinates = None
        self._moving = False
        # Independent drawer: resizing it never moves the launcher.
        self.panel = tk.Frame(master, bg='#FFFFFF', bd=1, relief='solid',
                              highlightthickness=1, highlightbackground='#DBE5DC')
        self._slide_job = None
        self._visibility_job = None
        self._slide_progress = 0.0
        self._vertical_progress = 0.0
        self._slide_target = 0.0
        self._slide_anchor = None
        self._panel_side = 'left'
        self._panel_full_width = 0
        self._menu_height = 0
        self.main = tk.Button(self, text='+', font=('Segoe UI', 19, 'bold'),
                              fg='white', bg='#39865B', activebackground='#285D40',
                              relief='flat', bd=0, width=3, pady=3, cursor='hand2')
        self.main.pack(side='right', padx=4, pady=4)
        self.main.bind('<Enter>',lambda _e:self.main.configure(bg='#256F4A') if not self.kind else None,add='+')
        self.main.bind('<Leave>',lambda _e:self.main.configure(bg='#39865B') if not self.kind else None,add='+')
        self.status = tk.Label(self, text='', font=('Segoe UI', 9, 'bold'),
                               fg='#B42318', bg='#FFFFFF')
        self.main.bind('<ButtonPress-1>', self._press)
        self.main.bind('<B1-Motion>', self._move)
        self.main.bind('<ButtonRelease-1>', self._release)
        self.status.bind('<ButtonPress-1>', self._press)
        self.status.bind('<B1-Motion>', self._move)
        self.status.bind('<ButtonRelease-1>', self._release)
        master.bind('<Configure>', self._reposition, add='+')
        self.bind('<Destroy>', self._on_destroy, add='+')
        self.place(relx=1.0, x=-20, y=125, anchor='ne')
        self.lift()
        # Navigation rebuilds page frames above the launcher; restore stacking.
        self._visibility_job = self.after(180, self._keep_on_top)

    def _keep_on_top(self):
        self._visibility_job = None
        try:
            if not self.winfo_exists():
                return
            if self.winfo_manager() == 'place' and self.winfo_ismapped():
                self.lift()
                if self.expanded and self.panel.winfo_exists():
                    self.panel.lift()
                    self.lift()
            self._visibility_job = self.after(180, self._keep_on_top)
        except (tk.TclError, RuntimeError):
            return

    def _press(self, event):
        if not self.winfo_exists():
            return
        self._drag_origin = (event.x_root, event.y_root, self.winfo_rootx(), self.winfo_rooty())
        self._dragged = False

    def _move(self, event):
        if not self._drag_origin or not self.winfo_exists():
            return
        sx, sy, root_x, root_y = self._drag_origin
        if abs(event.x_root - sx) + abs(event.y_root - sy) < 6 and not self._dragged:
            return
        self._dragged = True
        self._hide_drawer()
        try:
            # Use screen coordinates; widget relative coordinates can change on
            # pack/place updates, which previously caused the button to jump.
            master_x, master_y = self.master.winfo_rootx(), self.master.winfo_rooty()
            nx = root_x + event.x_root - sx - master_x
            ny = root_y + event.y_root - sy - master_y
            nx, ny = self._clamp(nx, ny)
            self._coordinates = (nx, ny)
            self.place_configure(x=nx, y=ny, anchor='nw', relx=0, rely=0)
            self.lift()
        except tk.TclError:
            # A queued motion event must never crash if window is closing.
            self._drag_origin = None

    def _release(self, event):
        was_dragged = self._dragged
        self._drag_origin = None
        self._dragged = False
        if was_dragged or not self.winfo_exists():
            return
        if self.kind:
            self.stop_action()
        else:
            self.toggle()

    def _clamp(self, x, y):
        width = max(1, self.master.winfo_width())
        height = max(1, self.master.winfo_height())
        return (max(0, min(int(x), max(0, width - self.winfo_width()))),
                max(0, min(int(y), max(0, height - self.winfo_height()))))

    def _reposition(self, event):
        if event.widget is not self.master:
            return
        if self._coordinates is None:
            try:
                self.lift()
            except tk.TclError:
                pass
            return
        try:
            if not self.winfo_exists():
                return
            nx, ny = self._clamp(*self._coordinates)
            if (nx, ny) != self._coordinates:
                self._coordinates = (nx, ny)
                self.place_configure(x=nx, y=ny, anchor='nw', relx=0, rely=0)
        except tk.TclError:
            pass

    def _alive(self):
        try:
            return bool(self.winfo_exists() and self.master.winfo_exists())
        except (tk.TclError, RuntimeError):
            return False

    def _ensure_panel(self):
        # Page navigation destroys root-level siblings, including the drawer,
        # while preserving the launcher. Restore the drawer when clicked.
        if not self._alive():
            return False
        try:
            if self.panel.winfo_exists():
                return True
        except (tk.TclError, RuntimeError):
            pass
        self._cancel_slide()
        self.expanded = False
        self._slide_target = 0.0
        self._slide_progress = 0.0
        self._vertical_progress = 0.0
        self._slide_anchor = None
        self.panel = tk.Frame(self.master, bg='#FFFFFF', bd=1, relief='solid',
                              highlightthickness=1, highlightbackground='#DBE5DC')
        if not self.kind:
            self.main.configure(text='+')
        return True

    def _on_destroy(self, event):
        if event.widget is not self:
            return
        self._cancel_slide()
        job, self._visibility_job = self._visibility_job, None
        if job is not None:
            try:
                self.after_cancel(job)
            except (tk.TclError, RuntimeError):
                pass
        try:
            if self.panel.winfo_exists():
                self.panel.destroy()
        except (tk.TclError, RuntimeError):
            pass

    def _cancel_slide(self):
        job, self._slide_job = self._slide_job, None
        if job is not None:
            try:
                self.after_cancel(job)
            except (tk.TclError, RuntimeError):
                pass

    def _hide_drawer(self):
        self._cancel_slide()
        self.expanded = False
        self._slide_target = 0.0
        self._slide_progress = 0.0
        self._vertical_progress = 0.0
        self._slide_anchor = None
        try:
            if self.panel.winfo_exists():
                self.panel.place_forget()
            if self.winfo_exists() and not self.kind:
                self.main.configure(text='+')
        except (tk.TclError, RuntimeError):
            pass

    def _populate_panel(self):
        # Keep the exact actions and order from floating_recorder(4).py.
        options = [('🎙  Ghi âm', self.voice_action), ('🎥  Ghi hình', self.video_action),
                   ('📂  Bản ghi', self.folder_action)]
        if self.devices_action is not None:
            options.insert(2, ('🎚  Thiết bị ghi âm', self.devices_action))
        if self.mouse_effects_action is not None:
            options.extend([('✨  Hiệu ứng click', lambda: self.mouse_effects_action('click')),
                            ('🔴  Chuột laser', lambda: self.mouse_effects_action('laser')),
                            ('○  Tắt hiệu ứng chuột', lambda: self.mouse_effects_action('off'))])
        if self.admin_action is not None:
            options.append(('🛡  Admin · Chỉnh sửa', self.admin_action))
        for title, command in options:
            tk.Button(self.panel, text=title, command=lambda c=command: self._choose(c),
                      font=('Segoe UI', 10, 'bold'), bg='#FFFFFF', fg='#285D40',
                      activebackground='#E2F0E2', relief='flat', padx=12, pady=8,
                      cursor='hand2').pack(fill='x')

    def toggle(self):
        if not self._ensure_panel():
            return
        if not self.panel.winfo_children():
            self._populate_panel()
        if self._slide_anchor is None:
            self._prepare_slide()
        self.expanded = not self.expanded
        self._slide_target = 1.0 if self.expanded else 0.0
        if not self.kind:
            self.main.configure(text='×' if self.expanded else '+')
        if self._slide_job is None:
            self._slide_frame()

    def _prepare_slide(self):
        if not self._alive():
            return
        self.update_idletasks()
        self._panel_full_width = max(205, self.panel.winfo_reqwidth())
        self._menu_height = max(1, self.panel.winfo_reqheight())
        bx = self.main.winfo_rootx() - self.master.winfo_rootx()
        by = self.main.winfo_rooty() - self.master.winfo_rooty()
        self._slide_anchor = (bx, by)
        right = self.master.winfo_width() - (bx + self.main.winfo_width())
        self._panel_side = 'right' if right >= self._panel_full_width + 8 else 'left'
        self.panel.pack_propagate(False)
        self._apply_slide()

    def _apply_slide(self):
        if not self._alive() or self._slide_anchor is None:
            return
        if not self.panel.winfo_exists():
            self.expanded = False
            self._slide_anchor = None
            return
        bx, by = self._slide_anchor
        smooth = lambda t: t * t * (3 - 2 * t)
        w = round(self._panel_full_width * smooth(self._slide_progress))
        h = round(self._menu_height * smooth(self._vertical_progress))
        if w > 1:
            x = (bx - w - 6) if self._panel_side == 'left' else (bx + self.main.winfo_width() + 6)
            self.panel.place(x=x, y=by, width=w, height=max(7, h))
            self.panel.lift()
        else:
            self.panel.place_forget()
        self.lift()

    def _slide_frame(self):
        self._slide_job = None
        if not self._alive():
            return
        if not self.panel.winfo_exists():
            self._cancel_slide()
            self.expanded = False
            self._slide_anchor = None
            return
        def approach(value, target):
            diff = target - value
            if abs(diff) < 0.025:
                return target
            return max(0.0, min(1.0, value + max(-0.14, min(0.14, diff * 0.32))))
        if self._slide_target > 0:
            if self._slide_progress < 1:
                self._slide_progress = approach(self._slide_progress, 1.0)
            else:
                self._vertical_progress = approach(self._vertical_progress, 1.0)
        else:
            if self._vertical_progress > 0:
                self._vertical_progress = approach(self._vertical_progress, 0.0)
            else:
                self._slide_progress = approach(self._slide_progress, 0.0)
        try:
            self._apply_slide()
        except (tk.TclError, RuntimeError):
            self._hide_drawer()
            return
        done = (self._slide_progress == self._slide_target and
                self._vertical_progress == self._slide_target)
        if not done:
            try:
                self._slide_job = self.after(16, self._slide_frame)
            except (tk.TclError, RuntimeError):
                self._slide_job = None
        elif self._slide_target == 0:
            if self.panel.winfo_exists():
                self.panel.place_forget()
            self._slide_anchor = None

    def _choose(self, action):
        if self._alive():
            self.toggle()
        action()

    def set_state(self, kind=None, busy=False, seconds=0):
        """Reflect actual recorder state; never imply recording before successful start."""
        self.kind = kind
        if self.expanded and (kind or busy):
            self.toggle()
        if busy:
            self.main.configure(text='…', bg='#905F0C', state='disabled')
            self.status.configure(text='Đang lưu')
        elif kind:
            self.main.configure(text='🎙' if kind == 'voice' else '🎥', bg='#B42318', state='normal')
            self.status.configure(text=f'● {seconds//60:02d}:{seconds%60:02d}  ⏹')
        else:
            self.main.configure(text='+', bg='#39865B', state='normal')
            self.status.configure(text='')
        self.lift()
