'Read-only incorrect-answer review using existing attempts and curriculum.'
from tuhoc.ui.strings_vi import t
from tuhoc.exercises.question_prompt import display_prompt
from tuhoc.ui.ui_components import EmptyState
import tkinter as tk
from tkinter import ttk

BG='#F8FAF5';INK='#173E2B';MUTED='#617669';GREEN='#287A51';PALE='#E9F5E9';YELLOW='#FFF7DE'
FONT='Segoe UI'


def collect_wrong(conn,student_id,curriculum):
    # Keep deleted questions as historical records, never invent their content.
    questions={str(q.get('id')):q for q in curriculum.rows.get('questions',[])}
    # Only the latest attempt for each question determines whether it still needs review.
    data=conn.execute('''SELECT a.exercise_id,a.exercise_type,a.answer,a.created_at
                         FROM attempts a
                         WHERE a.student_id=? AND a.correct=0
                           AND a.id=(SELECT MAX(b.id) FROM attempts b
                                     WHERE b.student_id=a.student_id
                                       AND b.exercise_id=a.exercise_id)
                         ORDER BY a.id DESC''',(student_id,)).fetchall()
    results=[]
    for qid,kind,answer,date in data:
        q=questions.get(str(qid))
        results.append({'id':str(qid),'kind':kind or '', 'given':answer or '',
                        'date':date or '', 'question':q,
                        'theme':str(q.get('theme','')) if q else '',
                        'level':int(q.get('level',0)) if q else 0})
    return results


def show_wrong_answers(parent,conn,student_id,curriculum,on_back=None,on_retry=None):
    outer=tk.Frame(parent,bg=BG);outer.pack(fill='both',expand=True)
    head=tk.Frame(outer,bg=BG);head.pack(fill='x',pady=(4,12))
    tk.Label(head,text='Ôn tập câu trả lời sai',bg=BG,fg=INK,font=(FONT,20,'bold')).pack(side='left')
    if on_back:
        tk.Button(head,text='← Báo cáo',command=on_back,bg=PALE,fg=INK,bd=0,padx=12,pady=7,cursor='hand2').pack(side='right')
    tk.Label(outer,text='Các câu có lần trả lời gần nhất bị sai. Làm đúng sẽ tự rời danh sách ôn tập.',
             bg=BG,fg=MUTED,font=(FONT,10)).pack(anchor='w',pady=(0,12))
    all_rows=collect_wrong(conn,student_id,curriculum)
    # A review session is restricted to questions of one theme and one Level.
    def launch_review(item):
        theme=item['theme'];level=item['level']
        ids=[r['id'] for r in all_rows if r['question'] is not None
             and r['theme']==theme and r['level']==level]
        if ids and on_retry:on_retry(theme,level,ids)
    controls=tk.Frame(outer,bg=BG);controls.pack(fill='x',pady=(0,12))
    lang=tk.StringVar(value='Tất cả');query=tk.StringVar(value='')
    tk.Label(controls,text='Môn học',bg=BG,fg=INK).pack(side='left',padx=(0,7))
    combo=ttk.Combobox(controls,textvariable=lang,values=['Tất cả','Tiếng Việt','Tiếng Anh'],state='readonly',width=15)
    combo.pack(side='left',padx=(0,16))
    tk.Label(controls,text='Tìm câu hỏi',bg=BG,fg=INK).pack(side='left',padx=(0,7))
    tk.Entry(controls,textvariable=query,width=26,relief='flat',highlightthickness=1,
             highlightbackground='#D9E8D9').pack(side='left',ipady=5)
    counter=tk.Label(outer,bg=BG,fg=MUTED,font=(FONT,10));counter.pack(anchor='w',pady=(0,8))
    area=tk.Frame(outer,bg=BG);area.pack(fill='both',expand=True)
    canvas=tk.Canvas(area,bg=BG,bd=0,highlightthickness=0)
    scrollbar=ttk.Scrollbar(area,orient='vertical',command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
    content=tk.Frame(canvas,bg=BG);window=canvas.create_window((0,0),window=content,anchor='nw')
    content.bind('<Configure>',lambda _e:canvas.configure(scrollregion=canvas.bbox('all')))
    canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=e.width))
    def refresh(*_):
        for child in content.winfo_children():child.destroy()
        selected=lang.get();needle=query.get().strip().casefold()
        subset=[]
        for item in all_rows:
            q=item['question'] or {}
            if selected=='Tiếng Việt' and not str(getattr(curriculum,'language','')).lower()=='vi':continue
            if selected=='Tiếng Anh' and not str(getattr(curriculum,'language','')).lower()=='en':continue
            text=str(q.get('prompt',''))+' '+str(item['id'])
            if needle and needle not in text.casefold():continue
            subset.append(item)
        counter.config(text=f'{len(subset)} lần trả lời sai · {len({r["id"] for r in subset})} câu khác nhau')
        if not subset:
            EmptyState(content,t('wrong_answers_empty'),background=BG).pack(fill='x',pady=22)
        for idx,item in enumerate(subset):
            q=item['question']
            card=tk.Frame(content,bg=PALE if idx%2==0 else YELLOW,padx=16,pady=12)
            card.pack(fill='x',pady=(0,6))
            title=str(display_prompt(q) or item['id']) if q else f'Câu hỏi {item["id"]} (đã thay đổi hoặc bị xóa)'
            tk.Label(card,text=title,wraplength=730,justify='left',anchor='w',bg=card['bg'],fg=INK,
                     font=(FONT,11,'bold')).pack(fill='x')
            tk.Label(card,text=f'Đã trả lời: {item["given"]}    ·    {item["date"]}',
                     bg=card['bg'],fg=MUTED,anchor='w',justify='left',wraplength=730).pack(fill='x',pady=(5,0))
            if q:
                answer=q.get('answer','')
                if isinstance(answer,(list,dict)):answer=str(answer)
                tk.Label(card,text=f'Đáp án hiện tại: {answer}',bg=card['bg'],fg=GREEN,
                         anchor='w',justify='left',wraplength=730,font=(FONT,10,'bold')).pack(fill='x',pady=(4,0))
                if on_retry:
                    tk.Button(card,text='Luyện các câu sai của Level',
                              command=lambda row=item:launch_review(row),
                              bg=GREEN,fg='white',activebackground='#1C603C',bd=0,
                              padx=12,pady=6,cursor='hand2').pack(anchor='e',pady=(7,0))
        canvas.yview_moveto(0)
    combo.bind('<<ComboboxSelected>>',refresh)
    query.trace_add('write',refresh)
    def wheel(event):
        if not canvas.winfo_exists():return
        canvas.yview_scroll(-1 if event.delta>0 else 1,'units')
    def enter(_):canvas.bind_all('<MouseWheel>',wheel)
    def leave(_):canvas.unbind_all('<MouseWheel>')
    canvas.bind('<Enter>',enter);canvas.bind('<Leave>',leave)
    canvas.bind('<Destroy>',lambda _e:canvas.unbind_all('<MouseWheel>'))
    refresh()
