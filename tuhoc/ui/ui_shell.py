"""Persistent navigation shell with scrollable, hoverable sidebar."""
from tuhoc.ui.strings_vi import t
import time
import tkinter as tk
from tuhoc.ui.theme_config import UI_COLORS, UI_FONTS
from tuhoc.ui.ui_components import Tooltip
from tuhoc.ui.ui_keys import keyboard_button
from tuhoc.ui.ui_components import bind_hover

NAV = [('⌂',t('home'),'home'),('▤',t('lessons'),'topic_page'),('▣',t('reading'),'reading_menu'),('▦','Flashcard','flashcards'),('✎','Chính tả','dictation_page'),('★','Trò chơi','games_page'),('▣','Kiểm tra','exam_page'),('♛','Phần thưởng','reward_shop'),('▤',t('history'),'quiz_history_page'),('▥','Báo cáo học tập','report_page'),('◷','Thống kê thời gian','time_statistics_page')]


class AppShell:
    def __init__(self, app):
        self.app = app
        self.sidebar = tk.Frame(app, bg=UI_COLORS['surface'])
        self.right = tk.Frame(app, bg=UI_COLORS['background'])
        self.top = tk.Frame(self.right, bg=UI_COLORS['surface'], height=68)
        self.top.pack(fill='x')
        self.top.pack_propagate(False)
        self.content = tk.Frame(self.right, bg=UI_COLORS['background'])
        self.content.pack(fill='both', expand=True)
        self.buttons = []
        self._width = None
        self._active_title = t('home')
        self.app.bind('<Configure>', self._resize, add='+')
        self._build_top()
        self._resize()
        self._intro_prepare()
        # Map only after everything is built and hidden: no un-hidden first frame.
        self.sidebar.pack(side='left', fill='y')
        self.right.pack(side='left', fill='both', expand=True)

    def pack(self, **options):
        shown = False
        if not self.sidebar.winfo_manager():
            self.sidebar.pack(side='left', fill='y')
            shown = True
        if not self.right.winfo_manager():
            self.right.pack(side='left', fill='both', expand=True)
            shown = True
        if shown:
            self._intro_prepare()

    def pack_forget(self):
        self.sidebar.pack_forget()
        self.right.pack_forget()

    def _bind_sidebar_wheel(self, widget):
        # Bind only the sidebar's widgets; do not hijack wheel scrolling of the page.
        for sequence in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            widget.bind(sequence, self._scroll_sidebar, add='+')

    def _scroll_sidebar(self, event):
        canvas = getattr(self, '_nav_canvas', None)
        if canvas is None or not canvas.winfo_exists():
            return None
        bbox = canvas.bbox('all')
        if not bbox or bbox[3] - bbox[1] <= canvas.winfo_height():
            return 'break'
        if getattr(event, 'num', None) == 4:
            steps = -1
        elif getattr(event, 'num', None) == 5:
            steps = 1
        else:
            delta = getattr(event, 'delta', 0)
            if not delta:
                return 'break'
            steps = (-1 if delta > 0 else 1) * max(1, round(abs(delta) / 120))
        canvas.yview_scroll(steps * 3, 'units')
        return 'break'

    def _update_nav_region(self, _event=None):
        canvas = getattr(self, '_nav_canvas', None)
        if canvas is not None and canvas.winfo_exists():
            canvas.configure(scrollregion=canvas.bbox('all'))
            self._toggle_scrollbar()

    def _toggle_scrollbar(self):
        canvas = getattr(self, '_nav_canvas', None)
        bar = getattr(self, '_nav_scrollbar', None)
        if canvas is None or bar is None or not canvas.winfo_exists():
            return
        bbox = canvas.bbox('all')
        overflow = bool(bbox and bbox[3] - bbox[1] > canvas.winfo_height() + 1)
        if overflow and not bar.winfo_manager():
            bar.pack(side='right', fill='y')
        elif not overflow and bar.winfo_manager():
            bar.pack_forget()

    def _resize_nav_inner(self, event):
        if getattr(self, '_nav_canvas', None) is not None:
            self._nav_canvas.itemconfigure(self._nav_window, width=event.width)
            self._toggle_scrollbar()

    def _nav_hover(self, button, entering):
        if not button.winfo_exists():
            return
        selected = bool(getattr(button, '_nav_selected', False))
        if selected:
            button.configure(bg=UI_COLORS['primary'], fg='white')
        else:
            button.configure(bg=UI_COLORS['tint'] if entering else UI_COLORS['surface'],
                             fg=UI_COLORS['primary'] if entering else UI_COLORS['text'])

    def _make_nav_button(self, parent, text, command):
        btn = tk.Button(parent, text=text, anchor='w', bg=UI_COLORS['surface'],
                        fg=UI_COLORS['text'], bd=0, relief='flat', font=UI_FONTS['body'],
                        cursor='hand2', takefocus=True, highlightthickness=2,
                        highlightcolor=UI_COLORS['primary'], command=command)
        btn.bind('<Enter>', lambda _e, b=btn: self._nav_hover(b, True), add='+')
        btn.bind('<Leave>', lambda _e, b=btn: self._nav_hover(b, False), add='+')
        btn.bind('<FocusIn>', lambda _e, b=btn: self._nav_hover(b, True), add='+')
        btn.bind('<FocusOut>', lambda _e, b=btn: self._nav_hover(b, False), add='+')
        keyboard_button(btn)
        self._bind_sidebar_wheel(btn)
        return btn

    def _resize(self, event=None):
        width = self.app.winfo_width()
        narrow = width <= 1100
        if narrow == self._width:
            return
        self._width = narrow
        self.sidebar.configure(width=64 if narrow else 244)
        self.sidebar.pack_propagate(False)
        for child in self.sidebar.winfo_children():
            child.destroy()
        header = tk.Frame(self.sidebar, bg=UI_COLORS['surface'])
        header.pack(side='top', fill='x')
        self._brand = tk.Label(header, text='TH' if narrow else 'Cùng Học Cùng Vui', bg=UI_COLORS['surface'],
                 fg=UI_COLORS['primary'], font=UI_FONTS['page'])
        self._brand.pack(pady=(20, 5))
        self._header = header
        self.subject_name = tk.Label(header, text=self._subject_title(narrow),
                                     bg=UI_COLORS['surface'], fg=UI_COLORS['primary'],
                                     font=UI_FONTS['small'])
        self.subject_name.pack(pady=(0, 8))
        subject = self._make_nav_button(header, '▾' if narrow else '▾  Đổi môn', self._subject)
        subject.configure(bg=UI_COLORS['tint'], anchor='center', font=UI_FONTS['small'])
        subject.pack(fill='x', padx=5, pady=(0, 15), ipady=8)
        self._subject_btn = subject

        # Fixed footer remains reachable even when the navigation list is long.
        footer = tk.Frame(self.sidebar, bg=UI_COLORS['surface'])
        footer.pack(side='bottom', fill='x')
        settings = self._make_nav_button(footer, '⚙' if narrow else '⚙   Cài đặt',
                                         lambda: self._go('display_settings'))
        settings.configure(anchor='center' if narrow else 'w')
        settings.pack(fill='x', padx=5, pady=(5, 12), ipady=8)
        self._settings_btn = settings

        scroll_area = tk.Frame(self.sidebar, bg=UI_COLORS['surface'])
        scroll_area.pack(side='top', fill='both', expand=True)
        self._nav_canvas = tk.Canvas(scroll_area, bg=UI_COLORS['surface'], bd=0,
                                     highlightthickness=0, yscrollincrement=16)
        self._nav_scrollbar = tk.Scrollbar(scroll_area, orient='vertical',
                                          command=self._nav_canvas.yview)
        self._nav_canvas.configure(yscrollcommand=self._nav_scrollbar.set)
        self._nav_canvas.pack(side='left', fill='both', expand=True)
        nav_inner = tk.Frame(self._nav_canvas, bg=UI_COLORS['surface'])
        self._nav_window = self._nav_canvas.create_window((0, 0), window=nav_inner, anchor='nw')
        nav_inner.bind('<Configure>', self._update_nav_region, add='+')
        self._nav_canvas.bind('<Configure>', self._resize_nav_inner, add='+')
        self._bind_sidebar_wheel(self._nav_canvas)
        self._bind_sidebar_wheel(nav_inner)
        self.buttons = []
        for symbol, title, callback in NAV:
            btn = self._make_nav_button(nav_inner, symbol if narrow else f'{symbol}   {title}',
                                        lambda name=callback: self._go(name))
            btn.configure(anchor='center' if narrow else 'w')
            # Fixed slot owns the layout and the hover area; only the button moves
            # inside it, so the pointer can never fall out of the hover region.
            slot = tk.Frame(nav_inner, bg=UI_COLORS['surface'], height=10)
            slot.pack(fill='x', padx=(5, 5), pady=2)
            slot.configure(height=btn.winfo_reqheight() + 18)
            btn.place(in_=slot, x=0, y=0, relwidth=1, relheight=1, width=-4)
            btn.lift()  # button was created before its slot; keep it above the slot
            self._bind_sidebar_wheel(slot)
            # Mouse hover is position-based; drop the per-button Enter/Leave/Focus colouring.
            for seq in ('<Enter>', '<Leave>', '<FocusIn>', '<FocusOut>'):
                btn.unbind(seq)
            def hover(active, b=btn):
                if not b.winfo_exists() or not getattr(b, '_slid', True):
                    return
                self._nav_hover(b, active)
                b.place_configure(x=4 if active else 0)
            bind_hover(btn, hover, region=slot, also=(slot,))
            self.buttons.append((title, btn))
        self.active(self._active_title, False)
        self.sidebar.after_idle(self._update_nav_region)

    # ------------------------------------------------------------------
    # Entrance choreography (runs when the shell is first shown)
    # ------------------------------------------------------------------
    def _blend(self, a, b, f):
        x = self.app.winfo_rgb(a); y = self.app.winfo_rgb(b); f = max(0.0, min(1.0, f))
        return '#{:02x}{:02x}{:02x}'.format(*[round((p + (q - p) * f) / 257) for p, q in zip(x, y)])

    def _at(self, ms, fn):
        def run():
            try:
                fn()
            except tk.TclError:
                pass
        return self.app.after(max(1, int(ms)), run)

    def _hide_widget(self, w):
        saved = {}
        for o in ('bg', 'fg', 'highlightbackground', 'disabledforeground'):
            try:
                saved[o] = str(w.cget(o))
            except tk.TclError:
                pass
        for o in saved:
            w.configure(**{o: UI_COLORS['surface']})
        return saved

    def _fade_widget(self, w, saved, start, dur=220, steps=6, with_bg=True):
        base = UI_COLORS['surface']
        for k in range(steps + 1):
            f = k / steps
            def go(f=f, last=(k == steps)):
                if not w.winfo_exists():
                    return
                if last:
                    w.configure(**saved)
                    return
                kw = {}
                bgc = self._blend(base, saved['bg'], f) if with_bg and 'bg' in saved else base
                if 'bg' in saved and with_bg:
                    kw['bg'] = bgc
                if 'highlightbackground' in saved and with_bg:
                    kw['highlightbackground'] = self._blend(base, saved['highlightbackground'], f)
                for o in ('fg', 'disabledforeground'):
                    if o in saved:
                        kw[o] = self._blend(bgc, saved[o], f)
                w.configure(**kw)
            self._at(start + dur * f, go)
        return start + dur

    def _intro_prepare(self):
        self._intro_t0 = None
        for name in ('_veil_top', '_veil_content', '_veil_side'):
            v = getattr(self, name, None)
            if v is not None:
                try: v.destroy()
                except tk.TclError: pass
            setattr(self, name, None)
        if getattr(self.app, 'reduce_motion', False) or getattr(self.app, 'reduced_motion', False):
            return
        bg = UI_COLORS['background']
        try:
            self._veil_top = tk.Frame(self.right, bg=bg)
            self._veil_top.place(in_=self.top, x=0, y=0, relwidth=1, relheight=1)
            self._veil_content = tk.Frame(self.right, bg=bg)
            self._veil_content.place(in_=self.content, x=0, y=0, relwidth=1, relheight=1)
            hh = self._header.winfo_reqheight()
            self._veil_side = tk.Frame(self.sidebar, bg=bg)
            self._veil_side.place(x=0, y=hh, relwidth=1, relheight=1)
            self._intro_hh = hh
            self._intro_saved = {
                'brand': (self._brand, self._hide_widget(self._brand)),
                'name': (self.subject_name, self._hide_widget(self.subject_name)),
                'subject': (self._subject_btn, self._hide_widget(self._subject_btn)),
                'settings': (self._settings_btn, self._hide_widget(self._settings_btn)),
            }
            for _t, btn in self.buttons:
                btn._slid = False
                btn.place_configure(x=-70)
        except tk.TclError:
            self._intro_cleanup()
            return
        # Blank, fully hidden shell for 0.1 s, then the flow starts.
        self._intro_t0 = time.monotonic() + 0.1
        self._settings_job = None
        self._at(100, self._intro_run)

    def animate_home_entry(self, *args, **kwargs):
        """Compatibility hook: the entrance flow already starts automatically."""
        return None

    def __getattr__(self, name):
        # Any other legacy animate_* hook is a harmless no-op.
        if name.startswith('animate_'):
            return lambda *a, **k: None
        raise AttributeError(name)

    def _intro_cleanup(self):
        for name in ('_veil_top', '_veil_content', '_veil_side'):
            v = getattr(self, name, None)
            if v is not None:
                try: v.destroy()
                except tk.TclError: pass
            setattr(self, name, None)
        for _t, btn in self.buttons:
            btn._slid = True
        self._intro_t0 = None

    def _elapsed(self):
        return (time.monotonic() - self._intro_t0) * 1000 if self._intro_t0 else None

    def content_delay(self):
        """ms from now until the page content may start (0 when no intro is running)."""
        e = self._elapsed()
        if e is None or getattr(self, '_content_at', None) is None:
            return 0
        return max(0, self._content_at - e)

    def request_footer(self, ms_from_now):
        """Page footer text and the sidebar settings button appear together."""
        e = self._elapsed()
        if e is None or getattr(self, '_settings_at', None) is None:
            return ms_from_now
        agreed = max(ms_from_now, self._settings_at - e)
        self._settings_at = e + agreed
        self._schedule_settings(agreed)
        return agreed

    def _schedule_settings(self, ms):
        if getattr(self, '_settings_job', None):
            try: self.app.after_cancel(self._settings_job)
            except (tk.TclError, RuntimeError): pass
        w, saved = self._intro_saved['settings']
        self._settings_job = self._at(ms, lambda: self._fade_widget(w, saved, 0, 200))

    def _intro_run(self):
        if self._intro_t0 is None:
            return
        F = 240
        S = UI_COLORS['surface']
        sv = self._intro_saved
        # 1) brand text
        self._fade_widget(sv['brand'][0], sv['brand'][1], 0, F, with_bg=False)
        # 2) subject name + subject field/text, with the top bar wiping in
        t1 = F
        self._fade_widget(sv['name'][0], sv['name'][1], t1, F, with_bg=False)
        self._fade_widget(sv['subject'][0], sv['subject'][1], t1, F)
        wipe = 300; steps = 10
        for k in range(steps + 1):
            f = k / steps
            def go(f=f):
                v = self._veil_top
                if v is None or not v.winfo_exists():
                    return
                if f >= 1:
                    return
                v.place_configure(relx=f, relwidth=1 - f)
            self._at(t1 + wipe * f, go)
        self._at(t1 + wipe, self._intro_top_items)
        # 3) sidebar field wipes in from the top (+50 ms), then nav items slide in
        t2 = t1 + F + 50
        H = max(1, self.sidebar.winfo_height()); hh = self._intro_hh
        for k in range(steps + 1):
            f = k / steps
            def go(f=f):
                v = self._veil_side
                if v is None or not v.winfo_exists():
                    return
                if f >= 1:
                    v.destroy(); self._veil_side = None; return
                y = hh + int((H - hh) * f)
                v.place_configure(y=y, relheight=0, height=max(1, H - y))
            self._at(t2 + wipe * f, go)
        t3 = t2 + wipe
        n = len(self.buttons); stagger = 60; slide = 240; k_steps = 8
        for i, (_t, btn) in enumerate(self.buttons):
            for k in range(k_steps + 1):
                f = k / k_steps; x = -round(70 * (1 - f) ** 2)
                def go(b=btn, x=x, last=(k == k_steps)):
                    if not b.winfo_exists():
                        return
                    b.place_configure(x=x)
                    if last:
                        b._slid = True
                self._at(t3 + i * stagger + slide * f, go)
        # page content slides in from the left at the same moment
        self._content_at = t3
        self._at(t3, self._intro_content)
        nav_end = t3 + max(0, n - 1) * stagger + slide
        self._settings_at = nav_end + 50
        self._schedule_settings(self._settings_at - (self._elapsed() or 0))
        self._at(self._settings_at + 400, self._intro_cleanup)

    def _intro_top_items(self):
        v = self._veil_top
        leaves = []
        def walk(w):
            if isinstance(w, (tk.Label, tk.Button)):
                leaves.append(w)
            for c in w.winfo_children():
                walk(c)
        walk(self.top)
        leaves.sort(key=lambda w: w.winfo_rootx())
        saved = [(w, self._hide_widget(w)) for w in leaves]
        if v is not None and v.winfo_exists():
            v.destroy(); self._veil_top = None
        for i, (w, sd) in enumerate(saved):
            self._fade_widget(w, sd, i * 70, 200)

    def _intro_content(self):
        v = self._veil_content
        if v is not None and v.winfo_exists():
            v.destroy(); self._veil_content = None
        canvas = getattr(self.app, 'active_scroll_canvas', None)
        window = getattr(self.app, '_sidebar_slide_window', None)
        if canvas is None or window is None:
            return
        app = self.app
        try:
            body = canvas.nametowidget(canvas.itemcget(window, 'window'))
            body_h = max(body.winfo_reqheight(), body.winfo_height(), canvas.winfo_height())
            # Same protocol as the sidebar slide in main.py: while the window is offset,
            # freeze the scrollregion (the body's <Configure> handler skips while the
            # slide job is set), otherwise the region is recomputed mid-slide and shakes.
            app._sidebar_slide_job = 'intro'
            canvas.configure(scrollregion=(0, 0, max(1, canvas.winfo_width()), body_h))
            canvas.yview_moveto(0)
            canvas.xview_moveto(0)
            canvas.coords(window, -80, 0)
        except tk.TclError:
            app._sidebar_slide_job = None
            return
        steps = 10
        for k in range(steps + 1):
            f = k / steps; x = -round(80 * (1 - f) ** 2)
            def go(x=x, last=(k == steps)):
                if not canvas.winfo_exists():
                    app._sidebar_slide_job = None
                    return
                canvas.coords(window, x, 0)
                if last:
                    app._sidebar_slide_job = None
                    canvas.configure(scrollregion=canvas.bbox('all'))
                    canvas.yview_moveto(0)
            self._at(350 * f, go)

    def _subject_title(self, narrow=False):
        lang = getattr(self.app, 'lang', None)
        if lang == 'en': return 'EN' if narrow else 'English'
        if lang == 'vi': return 'VI' if narrow else 'Tiếng Việt'
        return '—' if narrow else 'Chưa chọn môn học'

    def refresh_subject_name(self):
        label = getattr(self, 'subject_name', None)
        if label is not None and label.winfo_exists():
            label.configure(text=self._subject_title(self._width))

    def _subject(self):
        for name in ('choose_language', 'choose_subject', 'subject_page', 'subjects_page', 'home'):
            callback = getattr(self.app, name, None)
            if callable(callback):
                callback()
                return

    def _go(self, name):
        callback = getattr(self.app, name, None)
        if callable(callback):
            self.app._navigate_to(callback)

    def _build_top(self):
        back=tk.Button(self.top,text='←',command=self.app.navigation_back,
                       bg=UI_COLORS['surface'],bd=0,font=UI_FONTS['card'],width=3)
        back.pack(side='left',padx=(12,6),pady=8)
        Tooltip(back,t('back_tooltip'))
        keyboard_button(back)
        self.crumb = tk.Label(self.top, text=t('home'), bg=UI_COLORS['surface'],
                              fg=UI_COLORS['text'], font=UI_FONTS['body'])
        self.crumb.pack(side='left', padx=8)
        self.account = tk.Button(self.top, text=t('account'), command=self._account,
                                 bg=UI_COLORS['surface'], bd=0, font=UI_FONTS['small'])
        self.account.pack(side='right', padx=12)
        self.bell = tk.Button(self.top, text='🔔', command=self.app._click_notification_icon,
                              bg=UI_COLORS['surface'], bd=0, font=UI_FONTS['body'])
        self.bell.pack(side='right', padx=8)
        Tooltip(self.bell,t('notifications'))
        keyboard_button(self.bell)
        keyboard_button(self.account)
        self.tools = tk.Frame(self.top, bg=UI_COLORS['surface'])
        self.tools.pack(side='right', padx=4)

    def _account(self):
        menu = tk.Menu(self.top, tearoff=False)
        for label, name in [(t('history'), 'quiz_history_page'),
                            ('Báo cáo học tập', 'report_page'),
                            ('Thống kê thời gian', 'time_statistics_page'),
                            ('Đổi tài khoản', 'show_profiles'),
                            ('Donate', 'toggle_donate_panel'),
                            (t('shortcuts'), '_show_shortcut_guide')]:
            fn = getattr(self.app, name, None)
            if callable(fn):
                menu.add_command(label=label, command=fn)
        menu.tk_popup(self.account.winfo_rootx(),
                      self.account.winfo_rooty() + self.account.winfo_height())

    def active(self, title, reset_tools=True):
        self._active_title = title
        self.refresh_subject_name()
        subject=self._subject_title(False)
        self.crumb.configure(text=f'{subject}  /  {title}' if ' / ' in title else title)
        if reset_tools:
            for child in self.tools.winfo_children():
                child.destroy()
            self.app._teaching_header = self.tools
        for label, btn in self.buttons:
            selected = (label.casefold() in str(title).casefold()
                        or (label == t('home') and title == t('home')))
            btn._nav_selected = selected
            btn.configure(bg=UI_COLORS['primary'] if selected else UI_COLORS['surface'],
                          fg='white' if selected else UI_COLORS['text'])
        student = getattr(self.app, 'student', None)
        if student:
            self.account.configure(text=f"{student['name']} ▾")
        try:
            self.bell.configure(text='🔔 ●' if self.app._unread_quest_ids() else '🔔')
        except Exception:
            pass
