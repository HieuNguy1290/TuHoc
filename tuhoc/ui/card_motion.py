"""Non-blocking card feedback. No ImageGrab, screenshots or per-frame image allocation."""
import tkinter as tk

def animate_card(card, action, duration=115):
    if getattr(card, '_motion_busy', False):
        return
    card._motion_busy=True
    try:
        original={}
        for key in ('highlightbackground','highlightthickness'):
            try:original[key]=card.cget(key)
            except tk.TclError:pass
        try:card.configure(highlightbackground='#64b89b',highlightthickness=2)
        except tk.TclError:pass
        def finish():
            try:
                if card.winfo_exists():
                    for key,val in original.items():
                        try:card.configure(**{key:val})
                        except tk.TclError:pass
            finally:
                card._motion_busy=False
                action()
        card.after(duration,finish)
    except tk.TclError:
        card._motion_busy=False
        action()
