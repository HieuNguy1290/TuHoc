"""Draggable fixed lesson vocabulary action; never scrolls with the lesson."""
import tkinter as tk


class FloatingVocabulary(tk.Frame):
    def __init__(self, master, action):
        super().__init__(master, bg='#FFFFFF', bd=1, relief='solid',
                         highlightbackground='#C9DCCF', highlightthickness=1)
        self._action = action
        self._position = None
        self._origin = None
        self._dragged = False
        self.button = tk.Button(self, text='＋  Lưu từ', font=('Segoe UI', 11, 'bold'),
                                bg='#5769C6', fg='white', activebackground='#4050A5',
                                activeforeground='white', relief='flat', bd=0,
                                padx=12, pady=10, cursor='hand2')
        self.button.pack(padx=3, pady=3)
        for w in (self, self.button):
            w.bind('<ButtonPress-1>', self._press)
            w.bind('<B1-Motion>', self._move)
            w.bind('<ButtonRelease-1>', self._release)
        master.bind('<Configure>', self._on_resize, add='+')
        self.show()

    def set_action(self, action):
        self._action = action

    def show(self):
        try:
            if self._position is None:
                # Different vertical placement from the recorder (+ at y=125).
                self.place(relx=1, x=-20, y=215, anchor='ne')
            else:
                x, y = self._clamp(*self._position)
                self._position = (x, y)
                self.place(x=x, y=y, anchor='nw')
            self.lift()
        except tk.TclError:
            pass

    def _clamp(self, x, y):
        width = max(1, self.master.winfo_width())
        height = max(1, self.master.winfo_height())
        return (max(0, min(int(x), max(0, width - self.winfo_width()))),
                max(0, min(int(y), max(0, height - self.winfo_height()))))

    def _press(self, event):
        self._origin = (event.x_root, event.y_root,
                        self.winfo_rootx(), self.winfo_rooty())
        self._dragged = False

    def _move(self, event):
        if self._origin is None:
            return
        sx, sy, ox, oy = self._origin
        if not self._dragged and abs(event.x_root-sx)+abs(event.y_root-sy) < 7:
            return
        self._dragged = True
        try:
            x = ox + event.x_root - sx - self.master.winfo_rootx()
            y = oy + event.y_root - sy - self.master.winfo_rooty()
            self._position = self._clamp(x, y)
            self.place(x=self._position[0], y=self._position[1], anchor='nw', relx=0, rely=0)
            self.lift()
        except tk.TclError:
            self._origin = None

    def _release(self, event):
        dragged = self._dragged
        self._origin = None
        self._dragged = False
        if not dragged and self.winfo_exists():
            self._action()

    def _on_resize(self, event):
        if event.widget is not self.master or self._position is None:
            return
        try:
            if self.winfo_exists():
                self._position = self._clamp(*self._position)
                if self.winfo_manager() == 'place':
                    self.place_configure(x=self._position[0], y=self._position[1], anchor='nw')
        except tk.TclError:
            pass
