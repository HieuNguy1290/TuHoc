"""Focused Tk exercise presentation. Scoring and persistence remain in the caller."""
import time
import tkinter as tk
from tkinter import ttk

BG='#F8FAF5'; GREEN='#2F7A50'; DARK='#1F3A2B'; MUTED='#5B6B60'; BORDER='#DDE7DE'; PALE='#E8F2E9'; ERROR='#A52D24'


def _label(parent, value, size=12, bold=False, color=DARK, **kw):
    return tk.Label(parent,text=value,font=('Segoe UI',size,'bold' if bold else 'normal'),fg=color,bg=parent.cget('bg'),**kw)


class FocusPage:
    def __init__(self, app, title):
        self.app=app; self.jobs=set(); self.alive=True
        app.clear()
        self.root=tk.Frame(app,bg=BG)
        self.root.pack(fill='both',expand=True)
        self.top=tk.Frame(self.root,bg='white',height=72)
        self.top.pack(fill='x'); self.top.pack_propagate(False)
        self.exit=tk.Button(self.top,text='←  Thoát · Exit',command=self.exit_page,bg='white',fg=DARK,bd=0,font=('Segoe UI',12,'bold'))
        self.exit.pack(side='left',padx=26,pady=12)
        self.clock=_label(self.top,'00:00',12,True); self.clock.configure(bg='white');self.clock.pack(side='right',padx=26)
        self.count=_label(self.top,'Câu 1/1',12,True);self.count.configure(bg='white');self.count.pack(side='right',padx=14)
        self.progress=tk.Canvas(self.top,height=10,width=260,bg='#E8F2E9',highlightthickness=0)
        self.progress.pack(side='right',fill='x',expand=True,padx=16)
        self.progress.bind('<Configure>',lambda e:self.draw_progress(1))
        self.main=tk.Frame(self.root,bg=BG,padx=36,pady=20)
        self.main.pack(fill='both',expand=True)
        self.bottom=tk.Frame(self.root,bg='white',height=96,padx=30,pady=18)
        self.bottom.pack(fill='x');self.bottom.pack_propagate(False)
        self.started=time.monotonic()
        self.tick()
        self.root.bind('<Destroy>',self._destroy,add='+')
        app.bind('<Escape>',self._esc,add='+')

    def later(self,delay,callback):
        if not self.alive:return
        token=[None]
        def run():
            self.jobs.discard(token[0])
            if self.alive and self.root.winfo_exists():callback()
        token[0]=self.root.after(delay,run);self.jobs.add(token[0])

    def tick(self):
        secs=int(time.monotonic()-self.started)
        self.clock.configure(text=f'{secs//60:02d}:{secs%60:02d}')
        self.later(1000,self.tick)

    def draw_progress(self,part):
        self.progress.delete('all');w=max(1,self.progress.winfo_width())
        self.progress.create_rectangle(0,0,w,10,fill=PALE,outline='')
        self.progress.create_rectangle(0,0,w*part,10,fill=GREEN,outline='')

    def _destroy(self,event):
        if event.widget is self.root:
            self.alive=False
            for job in tuple(self.jobs):
                try:self.root.after_cancel(job)
                except tk.TclError:pass
            self.jobs.clear()

    def _esc(self,event):
        if self.alive and self.root.winfo_exists():self.exit_page();return 'break'

    def exit_page(self):
        from tkinter import messagebox
        if getattr(self,'dirty',False) and not messagebox.askyesno('Thoát bài tập','Bài đang làm dở. Bạn muốn thoát?',parent=self.app):return
        self.app.topic_page()


def exercise(app,ex):
    page=FocusPage(app,ex.get('title','Bài tập'))
    page.dirty=False
    _label(page.main,ex.get('title','Bài tập'),12,color=MUTED).pack(anchor='w',pady=(4,14))
    _label(page.main,ex.get('prompt',''),28,True,wraplength=1050,justify='left').pack(anchor='w',pady=(0,24))
    etype=ex.get('type','')
    if etype=='picture':
        path=app.media_file(ex.get('image','')) if ex.get('image') else None
        if path:
            try:
                from tuhoc.ui.animated_media import display_image
                display_image(page.main,path,350,220,bg=BG,anchor='w',pady=6)
            except (ImportError,OSError,ValueError,tk.TclError):_label(page.main,'Không thể hiển thị hình ảnh',12,color=MUTED).pack(anchor='w')
        else:_label(page.main,'Chưa có hình minh họa',12,color=MUTED).pack(anchor='w')
    if etype=='dictation':
        controls=tk.Frame(page.bottom,bg='white');controls.pack(side='left',padx=8)
        speed=tk.DoubleVar(value=1.0);volume=tk.DoubleVar(value=100)
        ttk.Combobox(controls,textvariable=speed,values=[0.5,0.75,1.0,1.25,1.5],width=5,state='readonly').pack(side='left',padx=5)
        tk.Scale(controls,from_=0,to=100,orient='horizontal',variable=volume,bg='white',highlightthickness=0,length=105).pack(side='left')
        tk.Button(controls,text='Nghe · Listen',command=lambda:app.audio.play(str(app.media_file(ex.get('audio','')) or ''),speed.get(),volume.get()/100),bg=PALE,fg=DARK,bd=0,padx=12,pady=8).pack(side='left',padx=5)
    if etype in ('matching','picture','error','dictation','reading'):
        _label(page.main,'Câu trả lời · Your answer',12,True).pack(anchor='w',pady=(5,8))
        entry=tk.Text(page.main,height=4,font=('Segoe UI',15),wrap='word',bd=0,highlightthickness=2,highlightbackground=BORDER,highlightcolor=GREEN,padx=14,pady=12)
        entry.pack(fill='x',pady=(0,8))
        if ex.get('options'):_label(page.main,'Gợi ý: '+' · '.join(map(str,ex['options'])),11,color=MUTED,wraplength=1000).pack(anchor='w')
        error=_label(page.main,'',11,color=ERROR);error.pack(anchor='w',pady=6)
        def submit():
            text=entry.get('1.0','end').strip()
            if not text:
                error.configure(text='Vui lòng nhập câu trả lời.');entry.configure(highlightbackground=ERROR);entry.focus_set();return
            accepted=ex.get('accepted_answers',[ex.get('answer','')])
            if etype in ('picture','reading') and ex.get('manual_review',False):correct=None
            else:
                from main import normalize
                correct=int(normalize(text) in [normalize(a) for a in accepted])
            seconds=time.monotonic()-page.started
            app.db.record(app.student['id'],ex,correct,seconds,text)
            app.result(ex,correct,seconds)
        btn=tk.Button(page.bottom,text='Kiểm tra · Check',command=submit,bg=GREEN,fg='white',font=('Segoe UI',13,'bold'),bd=0,padx=28,pady=12)
        btn.pack(side='right')
        page.root.bind('<Return>',lambda e:submit(),add='+')
        entry.bind('<KeyRelease>',lambda e:setattr(page,'dirty',bool(entry.get('1.0','end').strip())))
    else:
        _label(page.main,'Dạng bài này sử dụng trình làm bài hiện có.',12,color=MUTED).pack(anchor='w')
    if ex.get('vocabulary'):
        vocab=tk.Frame(page.main,bg=BG);vocab.pack(fill='x',pady=10)
        for word in ex['vocabulary']:
            row=tk.Frame(vocab,bg=BG);row.pack(anchor='w')
            _label(row,f'{word["word"]}: {word["meaning"]}',11).pack(side='left')
            tk.Button(row,text='☆ Lưu từ',command=lambda w=word:app.save_vocab(w),bd=0,bg=PALE).pack(side='left',padx=8)
    return page


def result(app,ex,correct,seconds):
    from tuhoc.exercises.pygame_review_panel import show_review
    page=FocusPage(app,'Kết quả')
    page.dirty=False
    payload=dict(stars=0,correct=int(correct==1),total=1,percent=float(correct==1),duration=f'{round(seconds)} giây',message='Đang chờ đánh giá.' if correct is None else 'Đúng rồi!' if correct else 'Cần luyện thêm nhé!',unlock='',rows=[dict(question=ex,answer=getattr(app,'_focus_answer',''),correct=correct)])
    show_review(page.main,payload,lambda action:app.topic_page())
    return page
