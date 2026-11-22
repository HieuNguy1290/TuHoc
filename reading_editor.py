"""Reading group editor tab; persists independently of standalone questions."""
import tkinter as tk
from tkinter import ttk, messagebox
from exam_bank import SUBJECTS


def add_reading_tab(notebook, bank, parent):
    page=ttk.Frame(notebook,padding=12)
    notebook.add(page,text='Bài đọc + nhiều câu hỏi')
    info=ttk.Frame(page);info.pack(fill='x')
    fields={}
    for col,(key,label,default) in enumerate([
        ('subject','Môn học','tieng_anh'),('grade','Lớp','1'),('lesson','Bài học','Family & Friends'),('title','Tiêu đề','My Little Friend')]):
        ttk.Label(info,text=label).grid(row=0,column=col,sticky='w',padx=4)
        v=tk.StringVar(value=default);fields[key]=v
        widget=(ttk.Combobox(info,textvariable=v,values=list(SUBJECTS),state='readonly',width=17)
                if key=='subject' else ttk.Entry(info,textvariable=v,width=24))
        widget.grid(row=1,column=col,sticky='ew',padx=4)
        info.columnconfigure(col,weight=1)
    ttk.Label(page,text='Đoạn văn (hiển thị lại cho từng câu hỏi khi làm bài)').pack(anchor='w',pady=(10,0))
    passage=tk.Text(page,height=5,wrap='word');passage.pack(fill='x')
    child_frame=ttk.LabelFrame(page,text='Câu hỏi con — 2 đến 10 câu, mỗi câu có mức M1–M5',padding=8)
    child_frame.pack(fill='both',expand=True,pady=8)
    child_list=tk.Listbox(child_frame,height=5,exportselection=False)
    child_list.pack(fill='x')
    question=tk.StringVar();difficulty=tk.StringVar(value='1');answer=tk.StringVar()
    ttk.Label(child_frame,text='Nội dung câu hỏi').pack(anchor='w')
    ttk.Entry(child_frame,textvariable=question).pack(fill='x')
    bar=ttk.Frame(child_frame);bar.pack(fill='x',pady=4)
    ttk.Label(bar,text='Độ khó').pack(side='left')
    ttk.Combobox(bar,textvariable=difficulty,values=['1','2','3','4','5'],width=5,state='readonly').pack(side='left',padx=6)
    ttk.Label(bar,text='Đáp án đúng').pack(side='left',padx=(14,4))
    ansbox=ttk.Combobox(bar,textvariable=answer,state='readonly',width=35);ansbox.pack(side='left',fill='x',expand=True)
    ttk.Label(child_frame,text='Các lựa chọn (mỗi dòng 1 phương án, 2–4 phương án)').pack(anchor='w')
    opts=tk.Text(child_frame,height=4,wrap='word');opts.pack(fill='x')
    children=[];edit_index=[None];group_id=[None]
    def update_options(_=None):
        values=[x.strip() for x in opts.get('1.0','end').splitlines() if x.strip()]
        ansbox['values']=values
        if answer.get() not in values:answer.set('')
    opts.bind('<KeyRelease>',update_options)
    def clear_child():
        edit_index[0]=None;question.set('');difficulty.set('1');answer.set('');opts.delete('1.0','end');update_options()
    def refresh_children():
        child_list.delete(0,'end')
        for i,c in enumerate(children):child_list.insert('end',f'{i+1}. M{c["difficulty"]} | {c["prompt"][:95]}')
    def choose_child(_=None):
        if not child_list.curselection():return
        i=child_list.curselection()[0];edit_index[0]=i;c=children[i]
        question.set(c['prompt']);difficulty.set(str(c['difficulty']))
        opts.delete('1.0','end');opts.insert('1.0','\n'.join(c['options']))
        update_options();answer.set(c['answer'])
    child_list.bind('<<ListboxSelect>>',choose_child)
    def save_child():
        values=[x.strip() for x in opts.get('1.0','end').splitlines() if x.strip()]
        if not question.get().strip() or len(values)<2 or len(values)>4 or len(set(values))!=len(values) or answer.get() not in values:
            messagebox.showerror('Câu hỏi không hợp lệ','Nhập câu hỏi, 2–4 lựa chọn khác nhau và chọn đáp án đúng.',parent=parent);return
        item={'prompt':question.get().strip(),'difficulty':int(difficulty.get()),'options':values,'answer':answer.get()}
        if edit_index[0] is None:children.append(item)
        else:children[edit_index[0]]=item
        refresh_children();clear_child()
    def delete_child():
        if edit_index[0] is not None:children.pop(edit_index[0]);refresh_children();clear_child()
    buttons=ttk.Frame(child_frame);buttons.pack(fill='x',pady=5)
    for label,fn in [('Thêm / cập nhật câu con',save_child),('Câu con mới',clear_child),('Xóa câu con',delete_child)]:
        ttk.Button(buttons,text=label,command=fn).pack(side='left',padx=3)
    bottom=ttk.Frame(page);bottom.pack(fill='x')
    ttk.Label(bottom,text='Bài đọc đã lưu').pack(side='left')
    group_pick=tk.StringVar();group_box=ttk.Combobox(bottom,textvariable=group_pick,state='readonly',width=43)
    group_box.pack(side='left',padx=6,fill='x',expand=True)
    groups=[]
    def refresh_groups():
        groups[:]=bank.reading_groups()
        group_box['values']=[f'{g.get("title","")} | {g.get("subject","")} | Lớp {g.get("grade","")} | {g.get("lesson","")}' for g in groups]
    def load_group():
        i=group_box.current()
        if i<0:return
        g=groups[i];group_id[0]=g['id']
        for key,v in fields.items():v.set(str(g.get(key,'')))
        passage.delete('1.0','end');passage.insert('1.0',g['passage'])
        children[:]=[dict(c) for c in g['questions']];refresh_children();clear_child()
    def new_group():
        group_id[0]=None;passage.delete('1.0','end');children.clear();refresh_children();clear_child();group_pick.set('')
    def save_group():
        try:
            data={key:v.get().strip() for key,v in fields.items()}
            data.update(id=group_id[0],passage=passage.get('1.0','end').strip(),questions=[dict(c) for c in children])
            group_id[0]=bank.save_reading(data);refresh_groups()
            messagebox.showinfo('Đã lưu',f'Đã lưu bài đọc và {len(children)} câu hỏi con.',parent=parent)
        except (ValueError,OSError,TypeError) as exc:messagebox.showerror('Không thể lưu',str(exc),parent=parent)
    def delete_group():
        if group_id[0] and messagebox.askyesno('Xác nhận','Xóa toàn bộ bài đọc và các câu hỏi con?',parent=parent):
            bank.delete_reading(group_id[0]);new_group();refresh_groups()
    for label,fn in [('Mở bài đọc',load_group),('Bài đọc mới',new_group),('Lưu bài đọc',save_group),('Xóa bài đọc',delete_group)]:
        ttk.Button(bottom,text=label,command=fn).pack(side='left',padx=3)
    refresh_groups()
