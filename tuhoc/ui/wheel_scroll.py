"""Smooth wheel scrolling for the active page, including touchpads and X11."""
import tkinter as tk
from tkinter import ttk

from tuhoc.ui.drag_scroll import belongs_to_canvas, canvas_extent


def install_wheel_scroll(root):
    if getattr(root, '_wheel_scroll_installed', False): return
    root._wheel_scroll_installed = True
    root.active_scroll_canvas = None
    state = {'canvas': None, 'job': None, 'target': 0.}

    def cancel():
        if state['job'] is not None:
            try: root.after_cancel(state['job'])
            except (tk.TclError, RuntimeError): pass
        state['job'] = None

    root._cancel_wheel_scroll = cancel

    def tick():
        canvas = state['canvas']
        try:
            if canvas is None or canvas is not root.active_scroll_canvas or not canvas.winfo_exists():
                cancel(); return
            content = canvas_extent(canvas)
            first, last = canvas.yview()
            available = max(0., content*(1-last+first))
            if not available: cancel(); return
            current = first * content
            target = min(available,max(0.,state['target']))
            delta = target-current
            if abs(delta) < .9:
                canvas.yview_moveto(target/max(1.,content));cancel();return
            canvas.yview_moveto((current+delta*.28)/max(1.,content))
            state['job'] = root.after(16,tick)
        except (tk.TclError,RuntimeError,AttributeError):cancel()

    def combobox_popup_open():
        """Detect mapped ttk Combobox popdowns, including Windows native routing.

        Tk dispatches wheel events from a popdown through different widget
        paths on different Tk/Windows builds, so event.widget alone is not
        a reliable way to identify an open dropdown.
        """
        try:
            stack = [root]
            while stack:
                parent = stack.pop()
                for child in parent.winfo_children():
                    if isinstance(child, ttk.Combobox):
                        try:
                            pop = root.tk.call('ttk::combobox::PopdownWindow', str(child))
                            if root.tk.call('winfo', 'ismapped', pop) == '1' or root.tk.getboolean(root.tk.call('winfo', 'ismapped', pop)):
                                return True
                        except tk.TclError:
                            pass
                    else:
                        stack.append(child)
        except (tk.TclError, RuntimeError):
            pass
        return False

    def on_wheel(event):
        # A ttk.Combobox dropdown is a Tk Listbox in a separate popdown.
        # Its wheel event must never also scroll the underlying page.
        # Leave the event to the native Listbox class binding, even at
        # the top/bottom of the dropdown (no scroll chaining).
        try:
            widget = event.widget
            if combobox_popup_open() or widget.winfo_class() == 'Listbox':
                cancel()
                state['canvas'] = None
                return 'break'
        except (tk.TclError, AttributeError):
            pass
        canvas = root.active_scroll_canvas
        if canvas is None or not belongs_to_canvas(event.widget, canvas):
            return None
        try:
            if not canvas.winfo_exists():
                cancel(); state['canvas'] = None; return None
            content = canvas_extent(canvas)
            first, last = canvas.yview()
            if not content or last-first >= 1:
                cancel(); state['canvas'] = None
                return None
            direction = -1 if getattr(event,'num',None)==4 else (1 if getattr(event,'num',None)==5 else (-1 if event.delta>0 else 1))
            magnitude = 1 if getattr(event,'num',None) in (4,5) else max(.35,abs(event.delta)/120)
            available = max(0.,content*(1-last+first))
            if state['job'] is None or state['canvas'] is not canvas:
                cancel();state['canvas']=canvas;state['target']=canvas.yview()[0]*content
            state['target']=min(available,max(0.,state['target']+direction*magnitude*78))
            if state['job'] is None:tick()
            return 'break'
        except (tk.TclError,RuntimeError,AttributeError):
            cancel(); state['canvas'] = None; return None

    # A closed ttk.Combobox must not change selection when the user scrolls
    # the question editor. Tk's native TCombobox class binding normally
    # consumes the wheel before the page-level bind_all handler sees it.
    # Replace only that class wheel binding and forward to the existing page
    # scroll handler. Open popdowns keep their own Listbox wheel behavior.
    def on_combobox_wheel(event):
        try:
            if combobox_popup_open():
                return None
            return on_wheel(event)
        except (tk.TclError, RuntimeError, AttributeError):
            return None

    for seq in ('<MouseWheel>','<Button-4>','<Button-5>'):
        root.bind_class('TCombobox', seq, on_combobox_wheel)
        root.bind_all(seq,on_wheel,add='+')
    # Keep Tk native scrolling for editable Text/Listbox/Treeview widgets.
    # bind_all only runs when the widget's own class binding does not consume the event.

    def cleanup(_event=None):
        cancel()
        state['canvas'] = None
        state['target'] = 0.
        root.active_scroll_canvas = None

    root.bind('<Destroy>', lambda event: cleanup() if event.widget is root else None, add='+')
