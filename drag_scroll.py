"""Pointer panning for Tk canvases and scrollable menus."""
import tkinter as tk
from tkinter import ttk

INTERACTIVE_CLASSES = frozenset({
    'Button', 'TButton', 'Checkbutton', 'TCheckbutton', 'Radiobutton',
    'TRadiobutton', 'Entry', 'TEntry', 'Text', 'Listbox', 'Treeview',
    'TCombobox', 'Combobox', 'Scale', 'TScale', 'Scrollbar', 'TScrollbar',
    'Spinbox', 'TSpinbox', 'Menubutton', 'TMenubutton',
})


def safe_drag_origin(widget):
    """Keep native editing, widget clicks, and app-owned drag gestures."""
    try:
        return (widget.winfo_exists() and widget.winfo_class() not in INTERACTIVE_CLASSES
                and not any(widget.bind(seq) for seq in (
                    '<ButtonPress-1>', '<B1-Motion>', '<ButtonRelease-1>',
                )))
    except (AttributeError, tk.TclError, RuntimeError):
        return False


def belongs_to_canvas(widget, canvas):
    while widget is not None:
        if widget is canvas:
            return True
        widget = getattr(widget, 'master', None)
    return False


def canvas_extent(canvas):
    """Return the length of the Tk scroll region, in document pixels."""
    region = canvas.tk.splitlist(canvas.cget('scrollregion'))
    if len(region) == 4:
        return max(0, float(region[3]) - float(region[1]))
    return 0


def drag_fraction(start_fraction, start_y, current_y, content_height):
    if content_height <= 0:
        return start_fraction
    return max(0.0, min(1.0, start_fraction + (start_y - current_y) / content_height))


class CanvasPan:
    def __init__(self, *, on_drag_start=None):
        self.on_drag_start = on_drag_start
        self.canvas = None
        self.moved = False

    def start(self, canvas, root_y):
        self.finish()
        if canvas is None:
            return
        try:
            first, last = canvas.yview()
            if last - first >= 1:
                return
            self.extent = canvas_extent(canvas)
            if self.extent <= 0:
                return
            self.canvas, self.y, self.fraction = canvas, root_y, first
        except (tk.TclError, RuntimeError):
            self.finish()

    def move(self, root_y):
        if self.canvas is None or not self.moved and abs(root_y - self.y) < 5:
            return
        try:
            if not self.moved and self.on_drag_start is not None:
                self.on_drag_start()
            self.moved = True
            self.canvas.yview_moveto(drag_fraction(self.fraction, self.y, root_y, self.extent))
            return 'break'
        except (tk.TclError, RuntimeError):
            self.finish()

    def finish(self):
        consumed = 'break' if self.moved else None
        self.canvas = None
        self.moved = False
        return consumed


def install_drag_scroll(root):
    """Install once for passive content on the active app page."""
    if getattr(root, '_drag_scroll_installed', False):
        return
    root._drag_scroll_installed = True

    def cancel_wheel():
        cancel = getattr(root, '_cancel_wheel_scroll', None)
        if cancel is not None:
            cancel()

    pan = CanvasPan(on_drag_start=cancel_wheel)

    def on_press(event):
        pan.finish()
        canvas = getattr(root, 'active_scroll_canvas', None)
        widget = getattr(event, 'widget', None)
        if isinstance(widget, (tk.Scrollbar, ttk.Scrollbar)):
            cancel_wheel()
        if canvas is not None and belongs_to_canvas(widget, canvas) and safe_drag_origin(widget):
            pan.start(canvas, event.y_root)

    def on_move(event):
        if pan.canvas is not getattr(root, 'active_scroll_canvas', None):
            pan.finish()
        return pan.move(event.y_root)

    root.bind_all('<ButtonPress-1>', on_press, add='+')
    root.bind_all('<B1-Motion>', on_move, add='+')
    root.bind_all('<ButtonRelease-1>', lambda _event: pan.finish(), add='+')


def bind_menu_pan(canvas, widgets):
    """Consume a release after panning, before a drawer button can navigate."""
    pan = CanvasPan()

    def release(event):
        if pan.finish():
            event.widget.event_generate('<Leave>')
            return 'break'

    for widget in widgets:
        widget.bind('<ButtonPress-1>', lambda event: pan.start(canvas, event.y_root), add='+')
        widget.bind('<B1-Motion>', lambda event: pan.move(event.y_root), add='+')
        widget.bind('<ButtonRelease-1>', release, add='+')
