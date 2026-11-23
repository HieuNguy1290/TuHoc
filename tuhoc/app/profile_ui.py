"""Account chooser UI only; database operations stay in the application."""
from tuhoc.ui.ui_tokens import COLORS as TOKEN_COLORS, font_at
import tkinter as tk
from tkinter import ttk
import time
from tuhoc.ui.ui_motion import MotionJobs, smoothstep
from tuhoc.ui.ui_components import EmptyState
from tuhoc.ui.theme_config import UI_COLORS as C

BG=C['background']; INK=C['text']; MUTED=C['muted']; GREEN=C['primary']; ERR=C['error']

class ProfilePage:
    def __init__(self, app):
        self.app=app; self.jobs=MotionJobs(app, bool(getattr(app,'reduce_motion',False)))
        self.root=tk.Frame(app,bg=BG); self.root.pack(fill='both',expand=True)
        self.popup=None; self.cards=[]
        self.root.bind('<Destroy>',self._destroy,add='+')
        self.draw()

    def _destroy(self,e):
        if e.widget is self.root:self.jobs.cancel_all()

    def later(self,fn,ms=16):
        return self.jobs.schedule(lambda:fn() if self.root.winfo_exists() else None,ms)

    def animate(self, duration, draw, done=None):
        if self.jobs.reduced:draw(1);done and done();return
        start=time.perf_counter();last=[start]
        def tick():
            now=time.perf_counter()
            if now-last[0]>.032:self.jobs.reduced=True;draw(1);done and done();return
            last[0]=now;t=min(1,(now-start)*1000/duration);draw(smoothstep(t))
            if t<1:self.later(tick)
            elif done:done()
        tick()

    def button(self,parent,text,command,primary=False,fg=None):
        b=tk.Button(parent,text=text,command=command,font=('Segoe UI',12,'bold' if primary else 'normal'),
                    bg=GREEN if primary else 'white',fg='white' if primary else (fg or INK),
                    activebackground=C['primary_dark'] if primary else C['tint'],
                    activeforeground='white' if primary else INK,bd=0,highlightthickness=2,
                    highlightbackground=GREEN if primary else 'white',highlightcolor=C['accent'],
                    relief='flat',cursor='hand2',takefocus=True)
        normal_bg = GREEN if primary else 'white'
        hover_bg = C['primary_dark'] if primary else C['tint']
        def update(_event=None, hover=False):
            if b.winfo_exists() and str(b.cget('state')) != 'disabled':
                b.configure(bg=hover_bg if hover else normal_bg)
        b.bind('<Enter>', lambda e: update(e, True), add='+')
        b.bind('<Leave>', lambda e: update(e, False), add='+')
        b.bind('<FocusIn>', lambda e: update(e, True), add='+')
        b.bind('<FocusOut>', lambda e: update(e, False), add='+')
        return b

    def draw(self):
        for w in self.root.winfo_children():w.destroy()
        self.cards=[]
        head=tk.Frame(self.root,bg=BG);head.pack(pady=(65,24))
        logo=tk.Canvas(head,width=76,height=76,bg=BG,highlightthickness=0)
        logo.pack();logo.create_rectangle(5,5,71,71,fill=GREEN,outline='')
        logo.create_text(38,38,text='T',fill='white',font=font_at(32, 'bold'))
        tk.Label(head,text='Cùng Học Cùng Vui xin chào các bạn',font=font_at(30, 'bold'),fg=INK,bg=BG).pack(pady=(15,2))
        tk.Label(head,text='Hãy tạo tài khoản nếu chưa có',font=font_at(13),fg=MUTED,bg=BG).pack()
        tk.Label(head,text='Phần mềm được phát triển by HiHieu Ver 1.0',font=font_at(8),fg=MUTED,bg=BG).pack(pady=(15,4))
        people=list(self.app.db.students())
        if not people:EmptyState(self.root,'Chào bạn! Hãy tạo tài khoản để bắt đầu.',background=BG).pack()
        holder=tk.Frame(self.root,bg=BG);holder.pack(fill='x',padx=24)
        canvas=tk.Canvas(holder,bg=BG,height=355,highlightthickness=0)
        canvas.pack(fill='x',expand=True)
        track=tk.Frame(canvas,bg=BG)
        win=canvas.create_window((0,0),window=track,anchor='nw')
        track.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        def center(e):
            width=track.winfo_reqwidth();canvas.coords(win,max(0,(e.width-width)//2),0)
        canvas.bind('<Configure>',center)
        def wheel(e):canvas.xview_scroll(-1 if e.delta>0 else 1,'units')
        canvas.bind('<Shift-MouseWheel>',wheel)
        for i,s in enumerate(people):self.profile_card(track,s,i)
        self.new_card(track)
        canvas.configure(xscrollincrement=55)
        if len(people)>3:
            scroll=ttk.Scrollbar(holder,orient='horizontal',command=canvas.xview);scroll.pack(fill='x',padx=32)
            canvas.configure(xscrollcommand=scroll.set)
        self.root.bind('<Delete>',lambda e:self.delete_focused(),add='+')
        self.root.bind('<Escape>',lambda e:self.close_popup(),add='+')

    def profile_card(self,parent,s,index):
        outer=tk.Frame(parent,bg=BG,width=276,height=322);outer.pack(side='left',padx=5);outer.pack_propagate(False)
        card=tk.Frame(outer,bg='white',highlightbackground=C['border'],highlightthickness=2,width=260,height=300)
        card.place(x=8,y=16);card.pack_propagate(False)
        avatar=self.app.db.selected_avatar(s['id']) or s['name'][:1].upper()
        av=tk.Canvas(card,width=80,height=80,bg='white',highlightthickness=0);av.pack(pady=(18,5))
        av.create_oval(4,4,76,76,fill=C['tint'],outline='');av.create_text(40,40,text=avatar if avatar!='👤' else s['name'][:1].upper(),font=('Segoe UI Emoji',28),fill=GREEN)
        tk.Label(card,text=s['name'],bg='white',fg=INK,font=font_at(17, 'bold'),wraplength=235).pack()
        tk.Label(card,text=f"Lớp {s['grade']} · Grade {s['grade']}",bg='white',fg=MUTED,font=font_at(11)).pack(pady=(4,12))
        start=self.button(card,'Chọn',lambda:self.enter(s),True);start.pack(fill='x',padx=16,ipady=8)
        row=tk.Frame(card,bg='white');row.pack(pady=10)
        self.button(row,'Đổi tên',lambda:self.rename(s)).pack(side='left',padx=8)
        self.button(row,'Xóa',lambda:self.confirm_delete(s),fg=ERR).pack(side='left',padx=8)
        # Bind all descendants; entering a label must not cancel the card hover.
        def track_hover(widget):
            widget.bind('<Enter>',lambda e,c=card,o=outer:self._profile_hover_check(c,o),add='+')
            widget.bind('<Leave>',lambda e,c=card,o=outer:self.later(lambda:self._profile_hover_check(c,o),1),add='+')
            for child in widget.winfo_children():track_hover(child)
        track_hover(card)
        start.bind('<FocusIn>',lambda e,s=s:setattr(self,'focused',s))
        start.bind('<Return>',lambda e,s=s:self.enter(s))
        self.cards.append((outer,card,s))
        if not self.jobs.reduced:
            card.place_configure(y=32)
            self.later(lambda c=card:self.animate(200,lambda t:c.place_configure(y=round(32-16*t)) if not getattr(c,'_hovered',False) else None),index*60+20)

    def _profile_hover_check(self,card,outer):
        if not card.winfo_exists():return
        x,y=card.winfo_pointerxy()
        on=(card.winfo_rootx() <= x < card.winfo_rootx()+card.winfo_width() and
            card.winfo_rooty() <= y < card.winfo_rooty()+card.winfo_height())
        self.hover(card,outer,on)

    def hover(self,card,outer,on):
        if not card.winfo_exists():return
        if getattr(card,'_hovered',False)==on:return
        card._hovered=on
        card.configure(highlightbackground=GREEN if on else C['border'])
        card.place_configure(y=14 if on else 16)

    def new_card(self,parent):
        outer=tk.Frame(parent,bg=BG,width=276,height=322);outer.pack(side='left',padx=5);outer.pack_propagate(False)
        c=tk.Canvas(outer,width=260,height=300,bg=BG,highlightthickness=0,cursor='hand2');c.place(x=8,y=16)
        border_items=[]
        for x in range(4,257,15):
            border_items.append(c.create_line(x,3,min(x+8,257),3,fill=GREEN,width=2))
            border_items.append(c.create_line(x,297,min(x+8,257),297,fill=GREEN,width=2))
        for y in range(4,297,15):
            border_items.append(c.create_line(3,y,3,min(y+8,297),fill=GREEN,width=2))
            border_items.append(c.create_line(257,y,257,min(y+8,297),fill=GREEN,width=2))
        c.create_text(130,115,text='+',font=font_at(46),fill=GREEN)
        c.create_text(130,185,text='Tạo tài khoản',font=font_at(16, 'bold'),fill=INK)
        c.create_text(130,211,text='New profile',font=font_at(12),fill=MUTED)
        def new_hover(on):
            c.configure(bg=C['tint'] if on else BG)
            c.place_configure(y=14 if on else 16)
            for item in border_items:c.itemconfigure(item,fill=C['primary_dark'] if on else GREEN)
        c.bind('<Enter>',lambda e:new_hover(True),add='+')
        c.bind('<Leave>',lambda e:new_hover(False),add='+')
        c.bind('<Button-1>',lambda e:self.create_popup())
        b=self.button(outer,'<3',self.create_popup);b.place(x=22,y=270,width=230,height=40)

    def dialog(self,title):
        if self.popup:self.close_popup()
        overlay=tk.Frame(self.root,bg=TOKEN_COLORS['tint']);overlay.place(relx=0,rely=0,relwidth=1,relheight=1);overlay.lift()
        panel=tk.Frame(overlay,bg='white',highlightthickness=2,highlightbackground=C['border'],padx=30,pady=25)
        panel.place(relx=.5,rely=.5,anchor='center',width=420,height=350)
        tk.Label(panel,text=title,font=font_at(20, 'bold'),fg=INK,bg='white').pack(anchor='w',pady=(0,14))
        self.popup=overlay
        self.animate(180,lambda t:panel.place_configure(width=round(399+21*t),height=round(333+17*t)))
        return panel

    def close_popup(self):
        if self.popup:
            self.popup.destroy();self.popup=None

    def field(self,panel,label):
        tk.Label(panel,text=label,bg='white',fg=INK,font=font_at(12)).pack(anchor='w')
        entry=tk.Entry(panel,font=font_at(13),highlightthickness=1,highlightcolor=GREEN,relief='solid')
        entry.pack(fill='x',ipady=7,pady=(4,8));return entry

    def error(self,panel,msg,field):
        tk.Label(panel,text=msg,fg=ERR,bg='white',font=font_at(10)).pack(anchor='w')
        if self.jobs.reduced:return
        x=field.winfo_manager()
        self.animate(200,lambda t:field.configure(highlightbackground=ERR if int(t*10)%2==0 else C['border']))

    def create_popup(self):
        p=self.dialog('Tạo tài khoản · New profile')
        name=self.field(p,'Họ tên · Full name')
        tk.Label(p,text='Lớp · Grade',bg='white',fg=INK,font=font_at(12)).pack(anchor='w')
        grade=ttk.Combobox(p,values=[str(i) for i in range(1,13)],state='readonly',font=font_at(12));grade.pack(fill='x',pady=5)
        def save():
            n=name.get().strip();g=grade.get()
            if not n or not g:self.error(p,'Vui lòng nhập họ tên và chọn lớp.',name if not n else grade);return
            self.app.db.add_student(n,int(g));self.close_popup();self.draw();self.toast('Đã tạo tài khoản')
        self.button(p,'Tạo',save,True).pack(fill='x',ipady=8,pady=10)
        name.focus_set()

    def rename(self,s):
        p=self.dialog('Đổi tên tài khoản');name=self.field(p,'Họ tên mới');name.insert(0,s['name'])
        def save():
            n=name.get().strip()
            if not n:self.error(p,'Tên không được để trống.',name);return
            try:self.app.db.rename_student(s['id'],n)
            except ValueError as ex:self.error(p,str(ex),name);return
            self.close_popup();self.draw()
        self.button(p,'Lưu tên',save,True).pack(fill='x',ipady=8,pady=10);name.focus_set()

    def confirm_delete(self,s):
        if self.app.recording_session:
            p=self.dialog('Không thể xóa');tk.Label(p,text='Vui lòng dừng ghi âm/ghi hình trước.',bg='white',fg=ERR).pack();return
        p=self.dialog('Xóa tài khoản?')
        tk.Label(p,text='Xóa là mất điểm, tiến độ, flashcard, lịch sử.\nDữ liệu không thể khôi phục.',bg='white',fg=ERR,justify='left',wraplength=350).pack(anchor='w',pady=8)
        entry=self.field(p,f'Gõ lại chính xác tên: {s["name"]}')
        delete=self.button(p,'Xóa vĩnh viễn',lambda:finish(),True);delete.configure(bg=ERR,state='disabled');delete.pack(fill='x',ipady=8,pady=12)
        def validate(*_):delete.configure(state='normal' if entry.get()==s['name'] else 'disabled')
        entry.bind('<KeyRelease>',validate)
        def finish():
            if entry.get()!=s['name']:return
            self.app.db.delete_student(s['id']);self.close_popup();self.draw()
        entry.focus_set()

    def delete_focused(self):
        if self.popup:return
        s=getattr(self,'focused',None)
        if s:self.confirm_delete(s)

    def enter(self,s):
        if self.popup:return
        self.jobs.cancel_all()
        self.app.choose(s)

    def toast(self,text):
        t=tk.Label(self.root,text=text,bg=GREEN,fg='white',font=font_at(12, 'bold'),padx=20,pady=10)
        t.place(relx=.5,rely=.93,anchor='center');self.later(lambda:t.destroy() if t.winfo_exists() else None,2000)
