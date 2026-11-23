"""Home dashboard UI only. Reads existing storage; writes only via existing claim API."""
from tuhoc.ui.strings_vi import t
from tuhoc.ui.ui_tokens import COLORS as TOKEN_COLORS, font_at
import datetime
import time
import tkinter as tk
from tuhoc.ui.ui_components import Card, ProgressRing, ProgressBar, Toast, bind_hover
from tuhoc.ui.ui_motion import smoothstep, MotionJobs
from tuhoc.ui.theme_config import UI_COLORS

GREEN=TOKEN_COLORS['primary']; DARK=TOKEN_COLORS['text']; MUTED=TOKEN_COLORS['muted']; BG=TOKEN_COLORS['background']

class HomeDashboard:
    def __init__(self, app, body):
        self.app=app;self.body=body
        self.jobs=MotionJobs(app, reduced=bool(getattr(app,'reduce_motion',False) or getattr(app,'reduced_motion',False)))
        self.alive=True
        body.bind('<Destroy>',self._destroy,add='+')
        self.render()

    def _destroy(self,event):
        if event.widget is self.body:
            self.alive=False;self.jobs.cancel_all()
            for job in self._timers:
                try:self.app.after_cancel(job)
                except (tk.TclError,RuntimeError):pass
            self._timers.clear()

    def schedule(self,ms,fn):
        if not self.alive:return
        # Clock remains active in reduced-motion mode; animations do not.
        def run():
            self._timers.discard(job)
            self._safe(fn)
        job=self.app.after(ms,run)
        self._timers.add(job)
        return job

    def _safe(self,fn):
        if self.alive and self.body.winfo_exists():fn()

    def label(self,parent,text,size=12,bold=False,fg=DARK,bg=None,**kw):
        return tk.Label(parent,text=text,font=font_at(size,'bold' if bold else 'normal'),fg=fg,bg=bg or parent.cget('bg'),**kw)

    def button(self,parent,text,command,primary=True):
        button=tk.Button(parent,text=text,command=command,font=font_at(11, 'bold'),bg=GREEN if primary else 'white',fg='white' if primary else GREEN,activebackground=TOKEN_COLORS['primary_dark'] if primary else TOKEN_COLORS['tint'],activeforeground='white' if primary else GREEN,relief='flat',bd=0,padx=12,pady=10,cursor='hand2',takefocus=True,highlightthickness=2,highlightcolor=GREEN)
        normal=GREEN if primary else 'white'
        hover='#236743' if primary else TOKEN_COLORS['tint']
        def paint(color):
            if getattr(button,'_ready',True) and str(button.cget('state')) != 'disabled':button.configure(bg=color)
        button.bind('<Enter>',lambda e:paint(hover),add='+')
        button.bind('<Leave>',lambda e:paint(normal),add='+')
        button.bind('<FocusIn>',lambda e:paint(hover),add='+')
        button.bind('<FocusOut>',lambda e:paint(normal),add='+')
        return button

    def _hover_zoom(self, card, slot):
        """Hover a single card without changing the geometry of its siblings."""
        labels=[child for child in card.winfo_children() if isinstance(child,tk.Label)]
        original=[(label,label.cget('font'),label.cget('fg')) for label in labels]
        state={'active':False}
        def set_hover(active):
            if not card.winfo_exists() or state['active']==active or not getattr(card,'_ready',True):return
            state['active']=active
            # No font or padding changes: these trigger Tk geometry propagation.
            # A stronger border and text emphasis provide a stable zoom-like focus.
            card.configure(highlightbackground=GREEN if active else UI_COLORS['border'])
            # Zoom inside the fixed slot: siblings and layout never move.
            if active:
                card.lift()
                card.place_configure(x=-4,y=-4,relwidth=1,relheight=1,width=8,height=8)
            else:
                card.place_configure(x=0,y=0,relwidth=1,relheight=1,width=0,height=0)
            for label,font,fg in original:
                if label.winfo_exists():label.configure(fg=GREEN if active else fg)
        bind_hover(card,set_hover,region=slot,also=(slot,))

    def render(self):
        app=self.app;sid=app.student['id'];self._timers=set()
        grid=tk.Frame(self.body,bg=BG);grid.pack(fill='both',expand=True)
        grid.grid_columnconfigure(0,weight=1);grid.grid_columnconfigure(1,minsize=320)
        left=tk.Frame(grid,bg=BG);left.grid(row=0,column=0,sticky='nsew',padx=(0,16))
        right=tk.Frame(grid,bg=BG,width=320);right.grid(row=0,column=1,sticky='ns');right.grid_propagate(False)
        # Paint the complete empty dashboard layout before querying progress.
        self._home_left=left;self._home_right=right
        self._title_lbl=next((c for c in self.body.winfo_children() if isinstance(c,tk.Label)),None)
        self._title_done=False
        if self._title_lbl is not None:
            self._title_fg=str(self._title_lbl.cget('fg'));self._title_bg=str(self._title_lbl.cget('bg'))
            self._title_lbl.configure(fg=self._title_bg)
        self.schedule(1, self._populate)

    def _populate(self):
        if not self.alive:return
        # Cover the grid while widgets are built: any redraw (e.g. update_idletasks used
        # for measuring) can then only paint this veil, never half-built, unhidden widgets.
        veil=tk.Frame(self._home_left.master,bg=BG);veil.place(x=0,y=0,relwidth=1,relheight=1)
        try:self._populate_inner()
        finally:
            try:veil.destroy()
            except tk.TclError:pass
            if not self._title_done:self._title_show(None)

    def _populate_inner(self):
        app=self.app;sid=app.student['id']
        # Existing lesson_progress and curriculum theme IDs are authoritative.
        rows=app.db.lesson_progress(sid)
        completed={str(r['topic_id']) for r in rows if r['completed']}
        themes=app._quest_themes()
        next_lesson=None;total=0;done=0
        for theme in themes:
            code=str(theme[0]);title=str(theme[1]) if len(theme)>1 else code
            max_level=app._max_level(code)
            for level in range(1,max_level+1):
                for lesson in range(1,self._lessons(code,level)+1):
                    total+=1;key=f'{code}:{level}:{lesson}'
                    if key in completed:done+=1
                    elif next_lesson is None:next_lesson=(title,level,lesson,code)
        if next_lesson is None and themes:
            theme=themes[0];next_lesson=(str(theme[1]) if len(theme)>1 else str(theme[0]),1,1,str(theme[0]))
        due=len(app.db.words(sid,due=True))
        quests=[]
        try:
            for theme in themes:
                quests.extend(app._quests_for_theme(theme[0]))
        except Exception:pass
        claimed={r[0] for r in app.db.conn.execute('SELECT achievement_id FROM achievement_claims WHERE student_id=?',(sid,))}
        quest_rows=[]
        # One grouped read instead of one SQL query per quest (hundreds on a full curriculum).
        try:
            buckets={}
            for kind,ident,secs in app.db.conn.execute(
                    "SELECT activity_type,activity_id,seconds FROM completion_events WHERE student_id=? "
                    "AND perfect=1 AND seconds>0 AND activity_type IN ('level','lesson_level')",(sid,)):
                buckets.setdefault((kind,str(ident)),[]).append(float(secs))
            def quest_count(q):
                lesson=q.get('lesson')
                key=('level',f"{q['theme']}:{int(q['level'])}") if lesson is None else ('lesson_level',f"{q['theme']}:{int(q['level'])}:{int(lesson)}")
                limit=float(q['max_seconds'])
                return sum(1 for s in buckets.get(key,()) if s<limit)
        except Exception:
            def quest_count(q):
                return app.db.level_achievement_count(sid,q['theme'],q['level'],q['max_seconds'],q.get('lesson'))
        for q in quests:
            count=quest_count(q)
            if q['id'] not in claimed:quest_rows.append((q,count))
        quest_rows.sort(key=lambda x:(x[1]<int(x[0]['required']),-min(x[1],int(x[0]['required']))))
        # Streak based on recorded completion dates, no mutation.
        dates={str(r[0])[:10] for r in app.db.conn.execute('SELECT DISTINCT date(created_at) FROM completion_events WHERE student_id=?',(sid,))} if self._has_column('completion_events','created_at') else set()
        today=datetime.date.today();day=today;streak=0
        if day.isoformat() not in dates:day-=datetime.timedelta(days=1)
        while day.isoformat() in dates:
            streak+=1;day-=datetime.timedelta(days=1)
        left=self._home_left;right=self._home_right
        W={'hooks':{},'cards':[]}
        def stage_0():
            if not self.alive:return
            hero=tk.Frame(left,bg=GREEN,padx=22,pady=20);hero.pack(fill='x',pady=(0,18))
            hero.grid_columnconfigure(0,weight=1)
            self.label(hero,f"Chào {app.student['name']} · Welcome back",12,fg='white',bg=GREEN).grid(row=0,column=0,sticky='w')
            new=not completed
            title='Bắt đầu học · Start' if new else f'Tiếp tục: {next_lesson[0]} · Level {next_lesson[1]}' if next_lesson else 'Bắt đầu học · Start'
            self.label(hero,title,19,True,'white',GREEN,wraplength=510,justify='left').grid(row=1,column=0,sticky='w',pady=(9,5))
            self.label(hero,f'Bài {next_lesson[2]}/{self._lessons(next_lesson[3],next_lesson[1])}' if next_lesson else 'Chọn bài học đầu tiên',11,fg=TOKEN_COLORS['tint'],bg=GREEN).grid(row=2,column=0,sticky='w')
            btn=self.button(hero,'Học tiếp · Continue' if not new else 'Bắt đầu học · Start',app.topic_page,False)
            btn.grid(row=3,column=0,sticky='w',pady=(16,0))
            btn.bind('<Return>',lambda e:app.topic_page(),add='+')
            lesson_n=self._lessons(next_lesson[3],next_lesson[1]) if next_lesson else 10
            pct=(sum(1 for i in range(1,lesson_n+1) if next_lesson and f'{next_lesson[3]}:{next_lesson[1]}:{i}' in completed)/lesson_n) if next_lesson else 0
            ring=ProgressRing(hero,value=0,size=96,bg=GREEN);ring.grid(row=0,column=1,rowspan=4,padx=(12,0))
            W['hooks'][ring]=lambda r=ring,p=pct:self.animate_ring(r,p)
            W['hero']=hero
        def stage_1():
            if not self.alive:return
            W['title2']=self.label(left,'Hôm nay học gì? · What to do today',16,True);W['title2'].pack(anchor='w',pady=(0,12))
            shortcuts=tk.Frame(left,bg=BG);shortcuts.pack(fill='x')
            shortcuts.grid_columnconfigure((0,1,2),weight=1,uniform='short')
            actions=[('▤','Ôn Flashcard',f'{due} thẻ cần ôn',app.flashcards),('▣',t('reading'),'Đọc bài tiếp theo',app.reading_menu),('✎','Chép chính tả','Luyện nghe và viết',app.dictation_page)]
            for i,(icon,title,sub,action) in enumerate(actions):
                slot=tk.Frame(shortcuts,bg=BG,width=10)
                slot.grid(row=0,column=i,sticky='nsew',padx=(0 if i==0 else 5,0 if i==2 else 5),pady=4)
                card=Card(shortcuts)   # child of the common parent so zoom is not clipped by the slot
                self.label(card,icon,21,True,fg=GREEN).pack(anchor='w')
                self.label(card,title,12,True).pack(anchor='w',pady=(7,2))
                self.label(card,sub,10,fg=MUTED,wraplength=150,justify='left').pack(anchor='w')
                go=self.button(card,'Mở  →',action,False);go.pack(anchor='w',pady=(10,0))
                card.update_idletasks()
                slot.configure(height=card.winfo_reqheight())
                card.place(in_=slot,x=0,y=0,relwidth=1,relheight=1)
                card._ready=False;W['cards'].append(card)
                self._hover_zoom(card,slot)
        def stage_2():
            if not self.alive:return
            games=self.button(left,'🎮  Chơi trò chơi · Games',app.games_page,False);games.pack(anchor='w',pady=(16,0))
            W['footer']=self.label(left,'Mỗi ngày một chút, bạn sẽ tiến xa hơn! · Keep going!',11,fg=MUTED);W['footer'].pack(anchor='w',pady=(22,0))
            W['games']=games
        def stage_3():
            if not self.alive:return
            quest=Card(right);quest.pack(fill='x',pady=(0,14))
            self.label(quest,'Nhiệm vụ · Quests',15,True).pack(anchor='w',pady=(0,10))
            for q,count in quest_rows[:3]:
                item=tk.Frame(quest,bg='white');item.pack(fill='x',pady=5)
                self.label(item,str(q.get('title') or 'Nhiệm vụ'),10,True,wraplength=265,justify='left').pack(anchor='w')
                needed=max(1,int(q['required']))
                self.label(item,f'{min(count,needed)}/{needed} lượt',10,fg=MUTED).pack(anchor='w')
                bar=ProgressBar(item,value=0,width=265,height=8,bg='white');bar.pack(anchor='w',pady=(3,5))
                W['hooks'][bar]=lambda b=bar,v=min(1,count/needed):self.animate_bar(b,v)
                ready=count>=needed
                claim=self.button(item,f"Nhận thưởng · +{q['gems']} ngọc",lambda item=q:self.claim(item),True)
                claim.configure(state='normal' if ready else 'disabled');claim.pack(anchor='w')
            if not quest_rows:self.label(quest,'Bạn đã hoàn thành các nhiệm vụ hiện có!',10,fg=MUTED,wraplength=260).pack(anchor='w')
            self.button(quest,'Xem tất cả nhiệm vụ',app.level_achievements_page,False).pack(anchor='w',pady=(8,0))
            W['quest']=quest
        def stage_4():
            if not self.alive:return
            streak_card=Card(right);streak_card.pack(fill='x')
            self.label(streak_card,'Chuỗi ngày học · Streak',15,True).pack(anchor='w')
            self.label(streak_card,f'🔥 {streak} ngày liên tiếp',17,True,fg=GREEN).pack(anchor='w',pady=(12,4))
            clock=self.label(streak_card,'',12,fg=MUTED);clock.pack(anchor='w')
            def tick():
                if not self.alive:return
                clock.configure(text=datetime.datetime.now().strftime('%d/%m/%Y  ·  %H:%M:%S'))
                job=app.after(1000,tick);self._timers.add(job)
            tick()
            W['streak']=streak_card
            self._enter_binding=None

        stage_0();stage_1();stage_2();stage_3();stage_4()
        self._intro(W)

    # ---------- entrance choreography ----------
    def _blend(self,a,b,f):
        x=self.body.winfo_rgb(a);y=self.body.winfo_rgb(b);f=max(0.0,min(1.0,f))
        return '#{:02x}{:02x}{:02x}'.format(*[round((p+(q-p)*f)/257) for p,q in zip(x,y)])

    def _snap(self,root):
        items=[];seen={}
        def walk(w):
            if isinstance(w,tk.Canvas):
                pm=w.master
                items.append({'w':w,'canvas':True,'opts':{'bg':str(w.cget('bg'))},'pbg':seen[pm]['bg'] if pm in seen else BG})
                return
            opts={}
            for o in ('bg','fg','highlightbackground','disabledforeground'):
                try:opts[o]=str(w.cget(o))
                except tk.TclError:pass
            seen[w]=opts
            pm=w.master
            items.append({'w':w,'canvas':False,'opts':opts,'pbg':seen[pm]['bg'] if (w is not root and pm in seen) else BG})
            for c in w.winfo_children():walk(c)
        walk(root)
        return items

    def _hide(self,items):
        for it in items:
            w=it['w']
            try:
                if it['canvas']:
                    w.configure(bg=BG);w.delete('all');continue
                if isinstance(w,tk.Button):w._ready=False
                for o in it['opts']:w.configure(**{o:BG})
            except tk.TclError:pass

    def _at(self,ms,fn):
        self.schedule(max(1,int(ms)),fn)

    def _field(self,items,start,dur=220,steps=6):
        """Field (container) fades in first: backgrounds and borders only."""
        for k in range(steps+1):
            f=k/steps
            def go(f=f):
                for it in items:
                    w=it['w'];o=it['opts']
                    try:
                        if it['canvas']:
                            w.configure(bg=self._blend(BG,o['bg'],f));continue
                        if isinstance(w,tk.Button):
                            c=self._blend(BG,it['pbg'],f)
                            w.configure(bg=c,fg=c,highlightbackground=c)
                            if 'disabledforeground' in o:w.configure(disabledforeground=c)
                            continue
                        c=self._blend(BG,o['bg'],f);kw={'bg':c}
                        if 'fg' in o:kw['fg']=c
                        if 'highlightbackground' in o:
                            kw['highlightbackground']=self._blend(BG,o['highlightbackground'],f) if (it is items[0] and not isinstance(w,tk.Label)) else c
                        w.configure(**kw)
                    except tk.TclError:pass
            self._at(start+dur*f,go)
        return start+dur

    def _content(self,items,start,stagger=50,dur=200,steps=5,hooks=None):
        """Texts / buttons / canvases fade in one after another, in creation order."""
        hooks=hooks or {}
        index=0
        for it in items:
            w=it['w'];o=it['opts']
            if not it['canvas'] and 'fg' not in o:continue
            t0=start+index*stagger;index+=1
            if it['canvas']:
                def show(w=w,o=o,h=hooks.get(w)):
                    try:
                        w.configure(bg=o['bg'])
                        if h:h()
                    except tk.TclError:pass
                self._at(t0,show);continue
            for k in range(steps+1):
                f=k/steps
                def go(w=w,o=o,pbg=it['pbg'],f=f,last=(k==steps)):
                    try:
                        if last:
                            w.configure(**o)
                            if isinstance(w,tk.Button):w._ready=True
                            return
                        if isinstance(w,tk.Button):
                            bgc=self._blend(pbg,o['bg'],f)
                            kw={'bg':bgc,'fg':self._blend(bgc,o['fg'],f),'highlightbackground':self._blend(pbg,o.get('highlightbackground',pbg),f)}
                            if 'disabledforeground' in o:kw['disabledforeground']=self._blend(bgc,o['disabledforeground'],f)
                            w.configure(**kw)
                        else:
                            w.configure(fg=self._blend(o['bg'],o['fg'],f))
                    except tk.TclError:pass
                self._at(t0+dur*f,go)
        return start+index*stagger+dur

    def _title_show(self,start):
        """Fade the page title in (start=None: show immediately)."""
        self._title_done=True
        lbl=self._title_lbl
        if lbl is None:return
        if start is None:
            try:lbl.configure(fg=self._title_fg)
            except tk.TclError:pass
            return
        for k in range(7):
            f=k/6
            self._at(start+220*f,lambda f=f:lbl.configure(fg=self._blend(self._title_bg,self._title_fg,f)) if lbl.winfo_exists() else None)

    def _intro(self,W):
        if self.jobs.reduced:
            self._title_show(None)
            for h in W['hooks'].values():h()
            for c in W['cards']:c._ready=True
            return
        fields={k:W[k] for k in ('hero','quest','streak') if k in W}
        fields.update({f'card{i}':c for i,c in enumerate(W['cards'])})
        leaves={k:W[k] for k in ('title2','games','footer') if k in W}
        snaps={k:self._snap(w) for k,w in {**fields,**leaves}.items()}
        for sn in snaps.values():self._hide(sn)
        shell=getattr(self.app,'_shell',None)
        delay=shell.content_delay() if shell is not None and hasattr(shell,'content_delay') else 0
        hooks=W['hooks'];T=delay if delay else 100  # shell intro sets the start, else blank page 0.1 s
        self._title_show(T);T+=150   # page title first, then the hero
        # Left column, top -> bottom; every field first, then its content.
        t=self._field(snaps['hero'],T)+70
        t=self._content(snaps['hero'],t,55,hooks=hooks)+60
        t=self._content(snaps['title2'],t,50)+40
        card_end=t
        for i in range(len(W['cards'])):
            fe=self._field(snaps[f'card{i}'],t+i*80)
            card_end=max(card_end,self._content(snaps[f'card{i}'],fe+60,45,hooks=hooks))
        W_cards=W['cards']
        def ready():
            for c in W_cards:c._ready=True
        self._at(card_end,ready)
        t=card_end+40
        t=self._content(snaps['games'],t,50)+40
        if 'footer' in snaps:
            if shell is not None and hasattr(shell,'request_footer'):t=shell.request_footer(t)
            self._content(snaps['footer'],t,50)
        # Right column, top -> bottom, trailing the left by one beat.
        r=T+60
        if 'quest' in snaps:
            r=self._field(snaps['quest'],r)+70
            r=self._content(snaps['quest'],r,45,hooks=hooks)+60
        if 'streak' in snaps:
            r=self._field(snaps['streak'],r)+70
            self._content(snaps['streak'],r,55)

    def _slide_in(self, widget):
        return
        """Reveal a packed section with a short, settled end bounce."""
        if self.jobs.reduced:return
        try:
            original=widget.pack_info().get('padx',0)
            widget.pack_configure(padx=(14,0))
        except tk.TclError:return
        offsets=(11,8,5,2,0,2,0)
        def step(i=0):
            if not self.alive or not widget.winfo_exists():return
            try:
                if i>=len(offsets):
                    widget.pack_configure(padx=original)
                    return
                widget.pack_configure(padx=(offsets[i],0))
                self.schedule(18,lambda:step(i+1))
            except tk.TclError:return
        self.schedule(18,step)

    def _lessons(self,code,level):
        try:return max(1,int(self.app._lesson_count(code,level)))
        except Exception:return 10

    def _has_column(self,table,column):
        return any(r[1]==column for r in self.app.db.conn.execute(f'PRAGMA table_info({table})'))

    def animate_ring(self,ring,target):
        if self.jobs.reduced: self._ring_value(ring,target);return
        start=time.monotonic()
        def frame():
            t=min(1,(time.monotonic()-start)/.4);self._ring_value(ring,target*smoothstep(t))
            if t<1:self.jobs.schedule(frame)
        frame()

    def _ring_value(self,ring,value):
        ring.delete('all');s=96
        ring.create_oval(7,7,s-7,s-7,outline='#A5D0B4',width=8)
        ring.create_arc(7,7,s-7,s-7,start=90,extent=-360*value,style='arc',outline=TOKEN_COLORS['accent'],width=8)
        ring.create_text(s/2,s/2,text=f'{value:.0%}',fill='white',font=font_at(16, 'bold'))

    def animate_bar(self,bar,target):
        if self.jobs.reduced:bar.value=target;bar.draw(265,8);return
        start=time.monotonic()
        def frame():
            t=min(1,(time.monotonic()-start)/.4);bar.value=target*smoothstep(t);bar.draw(265,8)
            if t<1:self.jobs.schedule(frame)
        frame()

    def claim(self,q):
        sid=self.app.student['id']
        if self.app.db.claim_level_achievement(sid,q):
            Toast(self.body,f"+{q['gems']} ngọc · Đã nhận thưởng")
            self.app.home()
