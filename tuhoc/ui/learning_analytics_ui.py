"""Read-only study analytics for learning_sessions (Phase 4 Patch 03)."""
from collections import defaultdict
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk

BG='#F8FAF5'; INK='#173E2B'; MUTED='#617669'; GREEN='#287A51'
PALE='#E9F5E9'; YELLOW='#FFF7DE'; WHITE='#FFFFFF'; FONT='Segoe UI'


def aggregate(conn, student_id, days=30, subject='all', now=None):
    """Compute metrics from completed sessions only, without changing the DB."""
    now = datetime.now() if now is None else now
    cutoff=(now-timedelta(days=days-1)).replace(hour=0,minute=0,second=0,microsecond=0).timestamp()
    where='student_id=? AND started>=? AND started<=?'
    args=[student_id,cutoff,now.timestamp()]
    if subject=='vi':where+=' AND theme LIKE ?';args.append('vi:%')
    elif subject=='en':where+=' AND theme NOT LIKE ?';args.append('vi:%')
    rows=conn.execute('SELECT theme,level,started,seconds,correct,total FROM learning_sessions WHERE '+where+' ORDER BY started DESC',args).fetchall()
    by_day=defaultdict(lambda:[0,0,0]);by_topic=defaultdict(lambda:[0,0,0,0])
    correct=total=seconds=0
    for theme,level,started,duration,good,count in rows:
        good=max(0,int(good or 0));count=max(0,int(count or 0));duration=max(0,float(duration or 0))
        correct+=good;total+=count;seconds+=duration
        date=datetime.fromtimestamp(float(started)).date().isoformat()
        day=by_day[date];day[0]+=1;day[1]+=good;day[2]+=count
        topic=by_topic[(theme,level)];topic[0]+=1;topic[1]+=good;topic[2]+=count;topic[3]+=duration
    return {'sessions':len(rows),'correct':correct,'total':total,'seconds':seconds,
            'percent':round(100*correct/total) if total else None,
            'by_day':dict(by_day),'by_topic':dict(by_topic),'days':days}


def show_analytics(parent,conn,student_id,on_back=None,on_retry=None):
    outer=tk.Frame(parent,bg=BG);outer.pack(fill='both',expand=True)
    header=tk.Frame(outer,bg=BG);header.pack(fill='x',pady=(8,15))
    tk.Label(header,text='Tiến độ học tập',font=(FONT,21,'bold'),bg=BG,fg=INK).pack(side='left')
    if on_retry:
        tk.Button(header,text='Ôn lại câu sai',command=on_retry,bg=PALE,fg=INK,bd=0,padx=14,pady=9).pack(side='right',padx=6)
    if on_back:
        tk.Button(header,text='← Báo cáo',command=on_back,bg=PALE,fg=INK,bd=0,padx=14,pady=9,cursor='hand2').pack(side='right')
    tk.Label(outer,text='Thống kê từ các bài tập đã hoàn thành',font=(FONT,10),bg=BG,fg=MUTED).pack(anchor='w',pady=(0,14))
    controls=tk.Frame(outer,bg=BG);controls.pack(fill='x',pady=(0,14))
    subject=tk.StringVar(value='Tất cả');period=tk.StringVar(value='30 ngày')
    for label,var,values in [('Môn học',subject,['Tất cả','Tiếng Việt','Tiếng Anh']),('Khoảng thời gian',period,['7 ngày','30 ngày','90 ngày'])]:
        tk.Label(controls,text=label,bg=BG,fg=INK,font=(FONT,10,'bold')).pack(side='left',padx=(0,8))
        box=ttk.Combobox(controls,textvariable=var,values=values,state='readonly',width=14)
        box.pack(side='left',padx=(0,22))
    metrics=tk.Frame(outer,bg=BG);metrics.pack(fill='x',pady=(0,18))
    cards=[]
    for col,label in enumerate(['Lượt hoàn thành','Tỷ lệ đúng','Thời gian luyện tập']):
        card=tk.Frame(metrics,bg=PALE if col!=1 else YELLOW,padx=16,pady=13)
        card.grid(row=0,column=col,sticky='ew',padx=(0,9))
        metrics.grid_columnconfigure(col,weight=1,uniform='cards')
        tk.Label(card,text=label,bg=card['bg'],fg=MUTED,font=(FONT,10)).pack(anchor='w')
        value=tk.Label(card,text='—',bg=card['bg'],fg=INK,font=(FONT,23,'bold'))
        value.pack(anchor='w',pady=(5,0));cards.append(value)
    tk.Label(outer,text='Tỷ lệ đúng theo ngày',bg=BG,fg=INK,font=(FONT,14,'bold')).pack(anchor='w',pady=(2,7))
    chart=tk.Canvas(outer,bg=WHITE,height=200,bd=0,highlightthickness=0)
    chart.pack(fill='x',pady=(0,18))
    tk.Label(outer,text='Kết quả theo chủ đề và Level',bg=BG,fg=INK,font=(FONT,14,'bold')).pack(anchor='w',pady=(0,8))
    area=tk.Frame(outer,bg=BG);area.pack(fill='both',expand=True)
    table=tk.Canvas(area,bg=BG,bd=0,highlightthickness=0,height=250)
    scroll=ttk.Scrollbar(area,orient='vertical',command=table.yview)
    table.configure(yscrollcommand=scroll.set)
    scroll.pack(side='right',fill='y');table.pack(side='left',fill='both',expand=True)
    rows=tk.Frame(table,bg=BG);window=table.create_window((0,0),window=rows,anchor='nw')
    rows.bind('<Configure>',lambda _e:table.configure(scrollregion=table.bbox('all')))
    table.bind('<Configure>',lambda e:table.itemconfigure(window,width=e.width))
    state={'result':None}
    def draw(_event=None):
        result=state['result'];chart.delete('all')
        if result is None:return
        width=max(360,chart.winfo_width());left=38;right=width-20;top=22;bottom=166
        for tick in (0,25,50,75,100):
            y=bottom-(bottom-top)*tick/100
            chart.create_line(left,y,right,y,fill='#E6EEE5')
            chart.create_text(left-8,y,text=str(tick),anchor='e',fill=MUTED,font=(FONT,9))
        today=datetime.now().date();days=result['days']
        samples=[today-timedelta(days=i) for i in range(days-1,-1,-1)]
        pts=[]
        for i,d in enumerate(samples):
            good,total=result['by_day'].get(d.isoformat(),[0,0,0])[1:]
            if total:
                x=left+(right-left)*i/max(1,days-1);y=bottom-(bottom-top)*100*good/total/100
                pts.append((x,y))
                chart.create_oval(x-3,y-3,x+3,y+3,fill=GREEN,outline='')
        if len(pts)>1:
            for a,b in zip(pts,pts[1:]):chart.create_line(*a,*b,fill=GREEN,width=2)
        for i in range(0,days,max(1,(days-1)//5)):
            d=samples[i];x=left+(right-left)*i/max(1,days-1)
            chart.create_text(x,186,text=d.strftime('%d/%m'),fill=MUTED,font=(FONT,9))
        if not pts:chart.create_text(width/2,92,text='Chưa có lượt luyện tập trong kỳ',fill=MUTED,font=(FONT,11))
    chart.bind('<Configure>',draw)
    def refresh(_event=None):
        days=int(period.get().split()[0]);sub={'Tất cả':'all','Tiếng Việt':'vi','Tiếng Anh':'en'}[subject.get()]
        result=aggregate(conn,student_id,days,sub);state['result']=result
        cards[0].configure(text=str(result['sessions']))
        cards[1].configure(text=f"{result['percent']}%" if result['percent'] is not None else '—')
        cards[2].configure(text=f"{result['seconds']/60:.0f} phút")
        for child in rows.winfo_children():child.destroy()
        header_row=tk.Frame(rows,bg='#E5F1E4');header_row.pack(fill='x')
        for title,width in [('Chủ đề / Level',34),('Lượt',8),('Đúng / Tổng',14),('Tỷ lệ',10)]:
            tk.Label(header_row,text=title,width=width,anchor='w',bg='#E5F1E4',fg=INK,padx=8,pady=10,font=(FONT,10,'bold')).pack(side='left')
        ordered=sorted(result['by_topic'].items(),key=lambda item:(-item[1][0],str(item[0])))
        if not ordered:
            tk.Label(rows,text='Chưa có dữ liệu trong khoảng thời gian này',bg=BG,fg=MUTED,pady=18).pack()
        for index,((theme,level),(count,good,total,duration)) in enumerate(ordered):
            background=PALE if index%2==0 else YELLOW
            row=tk.Frame(rows,bg=background);row.pack(fill='x',pady=2)
            topic=str(theme)[3:] if str(theme).startswith('vi:') else str(theme)
            values=[f'{topic} · Level {level}',str(count),f'{good}/{total}',f'{round(100*good/total)}%' if total else '—']
            for value,width in zip(values,[34,8,14,10]):
                label=tk.Label(row,text=value,width=width,anchor='w',bg=background,fg=INK,padx=8,pady=10,font=(FONT,10))
                label.pack(side='left')
                label.bind('<Enter>',lambda _e,r=row:r.configure(bg='#D7EED8') or [c.configure(bg='#D7EED8') for c in r.winfo_children()])
                label.bind('<Leave>',lambda _e,r=row,b=background:r.configure(bg=b) or [c.configure(bg=b) for c in r.winfo_children()])
        table.yview_moveto(0);draw()
    for control in controls.winfo_children():
        if isinstance(control,ttk.Combobox):control.bind('<<ComboboxSelected>>',refresh)
    refresh()
