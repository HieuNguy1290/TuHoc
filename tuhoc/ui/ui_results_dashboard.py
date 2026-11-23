"""Reference-inspired result dashboard. Presentation only; never modifies learning data."""
import tkinter as tk
from datetime import date, datetime, timedelta
from collections import defaultdict
from tuhoc.ui.ui_components import Badge, RoundedButton
from tuhoc.ui.ui_tokens import font_at

BLUE='#327ED9'; YELLOW='#F5C34D'; DARK='#31435F'; MUTED='#6D7890'; LINE='#E4E8F0'; WHITE='#FFFFFF'
FONT='Segoe UI'

def text(parent,value,size=11,bold=False,**kwargs):
    return tk.Label(parent,text=value,font=font_at(size,'bold' if bold else 'normal'),bg=kwargs.pop('bg',WHITE),fg=kwargs.pop('fg',DARK),**kwargs)

def dashboard(parent,db,sid,on_retry=None):
    """Build a three-tier dashboard based on recorded sessions, with no invented scores."""
    rows=db.conn.execute('SELECT theme,level,started,seconds,correct,total FROM learning_sessions WHERE student_id=?',(sid,)).fetchall()
    sessions=len(rows); secs=sum(float(r[3] or 0) for r in rows)
    good=sum(int(r[4] or 0) for r in rows); total=sum(int(r[5] or 0) for r in rows)
    scores=db.conn.execute('SELECT theme,level,stars FROM level_scores WHERE student_id=?',(sid,)).fetchall()
    completed=sum(1 for s in scores if int(s[2] or 0)>0)
    known=len(scores)
    outer=tk.Frame(parent,bg=WHITE,bd=1,relief='solid');outer.pack(fill='x',padx=8,pady=(8,18))
    top=tk.Frame(outer,bg=WHITE);top.pack(fill='x',padx=22,pady=(22,18))
    def metric(column,title,value,subtitle,icon):
        card=tk.Frame(top,bg='#F9FAFD',highlightbackground=LINE,highlightthickness=1)
        card.grid(row=0,column=column,sticky='nsew',padx=7)
        top.columnconfigure(column,weight=1,uniform='metrics')
        inner=tk.Frame(card,bg='#F9FAFD');inner.pack(fill='both',padx=14,pady=15)
        text(inner,icon,25,bg='#F9FAFD',fg=BLUE if column!=2 else '#E8AE24').pack(side='left',padx=(0,12))
        info=tk.Frame(inner,bg='#F9FAFD');info.pack(side='left',fill='x')
        text(info,title,11,True,bg='#F9FAFD').pack(anchor='w')
        line=tk.Frame(info,bg='#F9FAFD');line.pack(anchor='w')
        text(line,value,23,True,bg='#F9FAFD').pack(side='left')
        text(line,'  '+subtitle,10,bg='#F9FAFD').pack(side='left')
    metric(0,'Tiến độ khóa học',f'{completed}/{known}' if known else '—','Level đã đạt','◉')
    metric(1,'Thời gian học',f'{secs/3600:.1f}','giờ đã ghi nhận','◷')
    metric(2,'Kết quả kiểm tra',f'{good/total:.0%}' if total else '—','tỷ lệ đúng','🏆')
    note=tk.Frame(outer,bg=WHITE,padx=22)
    note.pack(fill='x',pady=(0,12))
    if total:
        Badge(note,f'★  Đã trả lời đúng {good}/{total} câu',tone='success').pack(side='left')
    else:
        text(note,'Bắt đầu một bài luyện tập để xem tiến độ ở đây.').pack(side='left')
    if on_retry:
        RoundedButton(note,'Ôn lại câu sai',on_retry,variant='outline',width=155).pack(side='right')
    tk.Frame(outer,bg=LINE,height=1).pack(fill='x')
    middle=tk.Frame(outer,bg=WHITE);middle.pack(fill='x',padx=26,pady=20)
    left=tk.Frame(middle,bg=WHITE);left.grid(row=0,column=0,sticky='nsew',padx=(0,18))
    right=tk.Frame(middle,bg=WHITE);right.grid(row=0,column=1,sticky='nsew',padx=(18,0))
    middle.columnconfigure(0,weight=3);middle.columnconfigure(1,weight=2)
    text(left,'Hoạt động học tập',15,True).pack(anchor='w',pady=(0,6))
    text(left,'●  Thời gian học (phút)       ●  Số bài luyện tập',10,fg=BLUE).pack(anchor='w')
    linechart=tk.Canvas(left,height=238,bg=WHITE,highlightthickness=0);linechart.pack(fill='x')
    today=date.today();days=[today-timedelta(days=6-i) for i in range(7)]
    minutes=defaultdict(float);quizzes=defaultdict(int)
    for theme,level,started,seconds,correct,total_q in rows:
        try: d=datetime.fromtimestamp(float(started)).date()
        except (ValueError,TypeError,OverflowError,OSError): continue
        minutes[d]+=max(0,float(seconds or 0))/60;quizzes[d]+=1
    vals1=[minutes[d] for d in days];vals2=[quizzes[d] for d in days]
    def draw_lines(event=None):
        c=linechart;c.delete('all');w=max(320,c.winfo_width());h=238
        x0=43;x1=w-20;y0=22;y1=193;max1=max(1,max(vals1,default=0)*1.2);max2=max(1,max(vals2,default=0)*1.2)
        for k in range(5):
            y=y0+(y1-y0)*k/4;c.create_line(x0,y,x1,y,fill=LINE)
            c.create_text(x0-8,y,text=f'{max1*(4-k)/4:.0f}',anchor='e',fill=MUTED,font=(FONT,9))
        for vals,color,high in ((vals1,BLUE,max1),(vals2,YELLOW,max2)):
            pts=[(x0+(x1-x0)*i/6,y1-(y1-y0)*v/high) for i,v in enumerate(vals)]
            if len(pts)>1:c.create_line(*[a for p in pts for a in p],fill=color,width=3,smooth=True)
            for x,y in pts:c.create_oval(x-4,y-4,x+4,y+4,fill=color,outline=WHITE,width=1)
        for i,d in enumerate(days):c.create_text(x0+(x1-x0)*i/6,216,text=d.strftime('%d/%m'),fill=MUTED,font=(FONT,9))
    linechart.bind('<Configure>',draw_lines);linechart.after_idle(draw_lines)
    text(left,f'{secs/60:.0f} phút học     |     {sessions} lượt luyện tập',11,True).pack(pady=(5,0))
    text(right,'Tiến độ kỹ năng',15,True).pack(anchor='w',pady=(0,12))
    bylevel=defaultdict(lambda:[0,0])
    for theme,level,started,seconds,correct,total_q in rows:
        bylevel[(theme,level)][0]+=int(correct or 0);bylevel[(theme,level)][1]+=int(total_q or 0)
    ranked=sorted(bylevel.items(),key=lambda x:x[0])[:4]
    if not ranked:text(right,'Chưa có dữ liệu theo chủ đề/Level.',10,fg=MUTED).pack(anchor='w')
    for (theme,level),(good_level,total_level) in ranked:
        pct=round(100*good_level/total_level) if total_level else 0
        text(right,f'{str(theme).replace("vi:", "Tiếng Việt · ")} · Level {level}',10).pack(anchor='w',pady=(7,2))
        track=tk.Canvas(right,height=26,bg=WHITE,highlightthickness=0);track.pack(fill='x')
        def drawbar(e=None,c=track,p=pct):
            c.delete('all');w=max(50,c.winfo_width()-8)
            c.create_rectangle(0,2,w,23,fill='#EFF1F6',outline='')
            if p:c.create_rectangle(0,2,w*p/100,23,fill=BLUE,outline='')
            c.create_text(max(25,min(w-20,w*p/100-22)),12,text=f'{p}%',fill=WHITE if p>=18 else DARK,font=(FONT,10,'bold'))
        track.bind('<Configure>',drawbar);track.after_idle(drawbar)
    tk.Frame(outer,bg=LINE,height=1).pack(fill='x')
    bottom=tk.Frame(outer,bg=WHITE);bottom.pack(fill='x',padx=26,pady=20)
    text(bottom,'Phân bổ môn học',15,True).pack(anchor='w',pady=(0,10))
    lower=tk.Frame(bottom,bg=WHITE);lower.pack(fill='x')
    pie=tk.Canvas(lower,width=260,height=205,bg=WHITE,highlightthickness=0);pie.pack(side='left',padx=(20,30))
    legend=tk.Frame(lower,bg=WHITE);legend.pack(side='left',fill='both',expand=True)
    groups=defaultdict(int)
    for theme,level,started,seconds,correct,total_q in rows:groups[str(theme)]+=1
    palette=[BLUE,YELLOW,'#8CB5E5','#536B8B','#55B7A4','#B29EE8']
    all_count=sum(groups.values());angle=90
    if all_count:
        for i,(name,count) in enumerate(sorted(groups.items(),key=lambda p:-p[1])):
            span=360*count/all_count;pie.create_arc(27,8,217,198,start=angle,extent=-span,fill=palette[i%len(palette)],outline=WHITE,width=2)
            angle-=span
            row=tk.Frame(legend,bg='#F6F7FA');row.pack(fill='x',pady=3,ipady=7)
            tk.Label(row,text='■',bg='#F6F7FA',fg=palette[i%len(palette)],font=(FONT,13)).pack(side='left',padx=10)
            text(row,name,10,bg='#F6F7FA').pack(side='left')
            text(row,f'{count/all_count:.0%}',10,True,bg='#F6F7FA').pack(side='right',padx=12)
    else:
        text(legend,'Chưa có phiên học để phân bổ.',11,fg=MUTED).pack(anchor='w')
    text(bottom,'Biểu đồ sử dụng dữ liệu học tập đã lưu; các nhóm chưa có dữ liệu sẽ không được tự tạo.',9,fg=MUTED).pack(anchor='w',pady=(10,0))
    return outer
