"""Subject picker UI; delegates all content loading to switch_language()."""
from tuhoc.paths import PROJECT_ROOT
import tkinter as tk
from pathlib import Path
import time
from tuhoc.ui.theme_config import UI_COLORS as C
from tuhoc.ui.ui_motion import MotionJobs, smoothstep

LABELS={'tieng_anh':('Tiếng Anh','English','TA','#DCEEE5'), 'tieng_viet':('Tiếng Việt','Vietnamese','TV','#FFF0C5')}

class SubjectPage:
    def __init__(self, app):
        self.app=app
        self.jobs=MotionJobs(app,bool(getattr(app,'reduce_motion',False)))
        self.root=tk.Frame(app,bg=C['background'])
        self.root.pack(fill='both',expand=True)
        self.root.bind('<Destroy>',self.destroy,add='+')
        self.cards=[];self.index=0;self.leaving=False
        self._hovered_cards=set()
        self.build()
        self.root.bind('<Left>',lambda e:self.select(-1),add='+')
        self.root.bind('<Right>',lambda e:self.select(1),add='+')
        self.root.bind('<Return>',lambda e:self.open_selected(),add='+')
        self.root.bind('<Escape>',lambda e:self.back(),add='+')
        self.root.focus_set()

    def destroy(self,event):
        if event.widget is self.root:self.jobs.cancel_all()

    def animate(self,ms,draw,done=None,delay=0):
        if self.jobs.reduced:
            draw(1)
            if done:done()
            return
        def begin():
            start=time.perf_counter();previous=[start]
            def tick():
                if not self.root.winfo_exists():return
                now=time.perf_counter()
                if now-previous[0]>.032:
                    self.jobs.reduced=True;draw(1)
                    if done:done()
                    return
                previous[0]=now
                t=min(1,(now-start)*1000/max(1,ms))
                draw(smoothstep(t))
                if t<1:self.jobs.schedule(tick,16)
                elif done:done()
            tick()
        self.jobs.schedule(begin,delay)

    def subjects(self):
        base=PROJECT_ROOT/'mon_hoc'
        from tuhoc.lessons.unified_subjects import SUBJECTS
        return [(code,folder) for code,folder in SUBJECTS.items() if (base/folder).is_dir()]

    def progress(self,code):
        """Read existing completion records; never alter the current curriculum."""
        try:
            from tuhoc.lessons.unified_subjects import SUBJECTS
            base=PROJECT_ROOT/'mon_hoc'/SUBJECTS[code]
            from tuhoc.ui.theme_config import max_level
            from tuhoc.ui.theme_config import tuples
            themes=tuples(base)
            total=sum(max_level(base,t[0])*10 for t in themes)
            # Completion events already record lesson identifiers; count distinct lessons.
            if code != getattr(self.app,'lang',None):
                return 0  # Existing completion keys do not distinguish subjects.
            rows=self.app.db.lesson_stats(self.app.student['id'])
            completed=sum(1 for (theme,level,lesson) in rows if any(theme==t[0] for t in themes))
            return min(100,round(completed*100/total)) if total else 0
        except (OSError,ValueError,KeyError,TypeError,AttributeError):return 0

    def build(self):
        top=tk.Frame(self.root,bg=C['background']);top.pack(fill='x',padx=32,pady=(22,0))
        tk.Button(top,text='←  Đổi tài khoản · Switch profile',command=self.back,bg=C['background'],fg=C['primary'],bd=0,font=('Segoe UI',12,'bold'),cursor='hand2',takefocus=True).pack(side='left')
        title=tk.Frame(self.root,bg=C['background']);title.pack(pady=(60,32))
        tk.Label(title,text='Chọn Môn Học',font=('Segoe UI',30,'bold'),fg=C['text'],bg=C['background']).pack()
        name=self.app.student['name'] if self.app.student else ''
        tk.Label(title,text=f'Các em học môn nào hãy click vào chọn môn đó!',font=('Segoe UI',13),fg=C['muted'],bg=C['background']).pack(pady=8)
        self.track=tk.Frame(self.root,bg=C['background']);self.track.pack(expand=True,anchor='n')
        subjects=self.subjects()
        for i,(code,folder) in enumerate(subjects):self.card(code,folder,i,len(subjects))
        if not subjects:
            tk.Label(self.track,text='Không tìm thấy môn học.',bg=C['background'],fg=C['error'],font=('Segoe UI',13)).pack()
        tk.Label(self.root,text='Phần mềm được phát triển by HiHieu Ver 1.0',font=('Segoe UI',11),fg=C['muted'],bg=C['background']).pack(side='bottom',pady=28)

    def card(self,code,folder,i,count):
        name,english,initial,color=LABELS.get(folder,(folder.replace('_',' ').title(),folder.replace('_',' ').title(),folder[:2].upper(),C['tint']))
        outer=tk.Frame(self.track,width=396,height=420,bg=C['background']);outer.pack(side='left',padx=12);outer.pack_propagate(False)
        card=tk.Frame(outer,bg='white',width=380,height=390,highlightbackground=C['border'],highlightthickness=2)
        card.place(x=8,y=12);card.pack_propagate(False)
        banner=tk.Canvas(card,height=150,bg=color,highlightthickness=0)
        banner.pack(fill='x');banner.create_text(190,75,text=initial,font=('Segoe UI',52,'bold'),fill=C['primary'])
        inner=tk.Frame(card,bg='white',padx=22);inner.pack(fill='both',expand=True)
        tk.Label(inner,text=name,font=('Segoe UI',20,'bold'),fg=C['text'],bg='white').pack(anchor='center',pady=(14,0))
        tk.Label(inner,text=english,font=('Segoe UI',12),fg=C['muted'],bg='white').pack(anchor='center')
        pct=self.progress(code)
        label=tk.Label(inner,text=f'Tiến độ {pct}%',font=('Segoe UI',11),fg=C['muted'],bg='white')
        label.pack(anchor='center',pady=(15,5))
        bar=tk.Canvas(inner,height=8,bg=C['tint'],highlightthickness=0)
        bar.pack(fill='x');fill=bar.create_rectangle(0,0,0,8,fill=C['primary'],outline='')
        def draw(t):
            if bar.winfo_exists():bar.coords(fill,0,0,round(max(0,bar.winfo_width())*pct*t/100),8)
        self.animate(400,draw,delay=200+i*60)
        btn=tk.Button(inner,text='Chọn',font=('Segoe UI',12,'bold'),fg='white',bg=C['primary'],activebackground=C['primary_dark'],activeforeground='white',bd=0,cursor='hand2',takefocus=True,command=lambda:self.open(code))
        btn.pack(fill='x',ipady=10,pady=(18,0))
        # Track pointer over the entire card, including nested text and buttons.
        # A child-widget boundary must not toggle the parent hover state.
        def bind_card_hover(widget):
            widget.bind('<Enter>', lambda e,j=i:self._sync_card_hover(j), add='+')
            widget.bind('<Leave>', lambda e,j=i:self._queue_card_hover_check(j), add='+')
            for child in widget.winfo_children():
                bind_card_hover(child)
        bind_card_hover(card)
        banner.bind('<Button-1>',lambda e,j=i:self.set_index(j))
        btn.bind('<FocusIn>',lambda e,j=i:self.set_index(j),add='+')
        self.cards.append((card,outer,code,draw))
        card.place_configure(x=8+(-30 if i==0 else 30),y=12)
        self.animate(200,lambda t,c=card,i=i:c.place_configure(x=round(8+(-30 if i==0 else 30)*(1-t))),delay=i*60)

    def _queue_card_hover_check(self,index):
        if self.root.winfo_exists():
            self.root.after(15,lambda j=index:self._sync_card_hover(j))

    def _sync_card_hover(self,index):
        if self.leaving or not self.root.winfo_exists():return
        card=self.cards[index][0]
        if not card.winfo_exists():return
        x,y=card.winfo_pointerxy()
        left,top=card.winfo_rootx(),card.winfo_rooty()
        inside=left<=x<left+card.winfo_width() and top<=y<top+card.winfo_height()
        if inside == (index in self._hovered_cards):return
        if inside:self._hovered_cards.add(index)
        else:self._hovered_cards.discard(index)
        self.highlight(index,inside)

    def highlight(self,index,on):
        if self.leaving:return
        card,outer,code,draw=self.cards[index]
        card.configure(highlightbackground=C['primary'] if on else C['border'])
        start=card.winfo_y();target=8 if on else 12
        self.animate(120,lambda t:card.place_configure(y=round(start+(target-start)*t)))
        if on:draw(0);self.animate(400,draw)

    def set_index(self,i):
        self.index=i
        for j,(card,_,_,_) in enumerate(self.cards):card.configure(highlightbackground=C['primary'] if j==i else C['border'])

    def select(self,step):
        if self.cards:self.set_index((self.index+step)%len(self.cards))
        return 'break'

    def open_selected(self):
        if self.cards:self.open(self.cards[self.index][2])
        return 'break'

    def open(self,code):
        if self.leaving:return
        self.leaving=True
        self.jobs.cancel_all()
        for card,_,item,_ in self.cards:
            if item!=code:card.configure(highlightbackground=C['border'])
        def finish():
            self.jobs.cancel_all()
            self.app.switch_language(code)
        self.animate(120,lambda t:None,finish)

    def back(self):
        if self.leaving:return 'break'
        self.jobs.cancel_all();self.app.show_profiles()
        return 'break'
