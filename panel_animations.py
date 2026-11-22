"""Centralized Tk panel transitions. Register further transitions by name here."""
import time


def _move(root, panel, start, end, duration, done=None, magnetic=False):
    began = time.monotonic()
    def tick():
        if not panel.winfo_exists():
            return
        t = min(1.0, (time.monotonic()-began)*1000/duration)
        if magnetic:
            # A modest overshoot followed by a magnetic settle.
            if t < .70:
                eased = 1.055*(1-(1-t/.70)**3)
            else:
                eased = 1.055-.055*((t-.70)/.30)
        else:
            eased = t*t*(3-2*t)
        panel.place_configure(x=round(start+(end-start)*eased))
        if t < 1:
            root.after(16,tick)
        elif done:
            done()
    tick()


def animate_magnetic_cascade(root, panel, cards_host, duration=230):
    """Magnetic slide from left; cards rise in top-to-bottom sequence."""
    _move(root,panel,panel.winfo_x(),0,duration,magnetic=False)
    # Cards remain at stable geometry. Avoid pack_configure per-frame, which
    # forces layout recalculation and makes the entire drawer jump.
    return


def animate_reverse_cascade_left(root, panel, on_complete=None):
    """Cards withdraw bottom-to-top, then panel exits to the left."""
    if not panel.winfo_exists():
        if on_complete:on_complete()
        return
    inner=getattr(root,'_menu_scroll_canvas',None)
    # Do not depend on scroll widget: caller may have already cleared it.
    def leave():
        if panel.winfo_exists():
            _move(root,panel,panel.winfo_x(),-max(315,panel.winfo_width()),170,on_complete)
        elif on_complete:on_complete()
    root.after(45,leave)
