"""Left-button grab-to-scroll for the active, scrollbar-free Tkinter page.

Dragging starts on passive page content. Interactive widgets (buttons, text
editors, links, quiz drag tiles) keep their native click/selection behaviour.
Mouse-wheel scrolling remains active independently.
"""

INTERACTIVE_CLASSES = frozenset({
    'Button', 'TButton', 'Checkbutton', 'TCheckbutton', 'Radiobutton',
    'TRadiobutton', 'Entry', 'TEntry', 'Text', 'Listbox', 'Treeview',
    'TCombobox', 'Combobox', 'Scale', 'TScale', 'Scrollbar', 'TScrollbar',
    'Spinbox', 'TSpinbox', 'Menubutton', 'TMenubutton',
})


def safe_drag_origin(widget):
    """Never hijack widget-specific clicks, dragging, typing or selecting."""
    # Tk can deliver the string path of a widget destroyed during navigation.
    # Ignore stale events rather than raising AttributeError.
    if not hasattr(widget, 'winfo_class') or not callable(getattr(widget, 'winfo_class', None)):
        return False
    try:
        if (hasattr(widget, 'winfo_exists') and not widget.winfo_exists()) or widget.winfo_class() in INTERACTIVE_CLASSES:
            return False
        # Existing application card/tile handlers use <Button-1> and/or drag.
        return not any(widget.bind(seq) for seq in (
            '<Button-1>', '<ButtonPress-1>', '<B1-Motion>',
            '<ButtonRelease-1>',
        ))
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return False


def drag_fraction(start_fraction, start_y, current_y, scroll_range):
    """Move page with the pointer: pulling downward reveals preceding text."""
    if scroll_range <= 0:
        return start_fraction
    return max(0.0, min(1.0, start_fraction + (start_y - current_y) / scroll_range))


def install_drag_scroll(root):
    """Install once per Tk root; page switching uses active_scroll_canvas."""
    if getattr(root, '_drag_scroll_installed', False):
        return
    root._drag_scroll_installed = True
    drag = {'start_y': None, 'fraction': 0.0, 'canvas': None, 'range': 0}

    def reset():
        drag.update(start_y=None, canvas=None)

    def on_press(event):
        reset()
        canvas = getattr(root, 'active_scroll_canvas', None)
        if canvas is None or not safe_drag_origin(getattr(event, "widget", None)):
            return
        try:
            if not canvas.winfo_exists():
                return
            bbox = canvas.bbox('all')
            if not bbox:
                return
            scroll_range = max(0, bbox[3] - bbox[1] - canvas.winfo_height())
            if scroll_range <= 0:
                return
            drag.update(start_y=event.y_root, fraction=canvas.yview()[0],
                        canvas=canvas, range=scroll_range)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            reset()

    def on_move(event):
        canvas = drag['canvas']
        if canvas is None or getattr(root, 'active_scroll_canvas', None) is not canvas:
            return
        try:
            if not canvas.winfo_exists():
                reset()
                return
            if abs(event.y_root - drag['start_y']) < 5:
                return
            fraction = drag_fraction(drag['fraction'], drag['start_y'],
                                     event.y_root, drag['range'])
            # Tk's yview_moveto fraction is measured over total content,
            # whereas the scrollable distance excludes viewport height.
            bbox = canvas.bbox('all')
            content_height = max(1, bbox[3] - bbox[1]) if bbox else 1
            canvas.yview_moveto(fraction * drag['range'] / content_height)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            reset()

    def on_release(_event):
        reset()

    # Bind on 'all' to receive events in nested frames, icons and labels.
    # These events don't consume widget-specific binding sequences.
    root.bind_all('<ButtonPress-1>', on_press, add='+')
    root.bind_all('<B1-Motion>', on_move, add='+')
    root.bind_all('<ButtonRelease-1>', on_release, add='+')
