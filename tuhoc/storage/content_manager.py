"""Offline JSON content editing for Tu Hoc."""
import json
import shutil
import time
import uuid
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from tuhoc.lessons.lesson_flow import TOPIC_COLUMNS, QUESTION_COLUMNS, topics, questions, topic_file, question_file, write_json, QUESTION_TYPES

CATEGORIES=('dictation','picture','error','reading','matching')
HEADERS=['id','type','icon','title','prompt','answer','accepted_answers','options','image','audio','manual_review']
GAME_HEADERS=['game','key','word','meaning','image','audio','level']


def user_content_dir(data_dir):
    path=Path(data_dir)/'content_library'
    path.mkdir(parents=True,exist_ok=True)
    return path


def local_lessons_path(data_dir):
    return user_content_dir(data_dir)/'my_lessons.json'


def games_path(data_dir):
    return user_content_dir(data_dir)/'my_games.json'


def read_custom_lessons(data_dir):
    p=local_lessons_path(data_dir)
    if not p.exists(): return []
    obj=json.loads(p.read_text(encoding='utf-8-sig'))
    return obj.get('exercises',[])


def save_custom_lessons(data_dir, lessons):
    ids=[x.get('id') for x in lessons]
    if len(ids)!=len(set(ids)) or any(not x for x in ids):raise ValueError('ID bài học phải có giá trị và không trùng nhau.')
    for ex in lessons:
        if not all(str(ex.get(k,'')).strip() for k in ('type','title','prompt')):raise ValueError('Thiếu loại, tên hoặc câu hỏi.')
        if ex['type'] not in CATEGORIES:raise ValueError('Loại bài học không hợp lệ.')
    p=local_lessons_path(data_dir)
    if p.exists():shutil.copy2(p,p.with_suffix('.json.bak'))
    p.write_text(json.dumps({'package_id':'user_lessons','version':'1.2','exercises':lessons},ensure_ascii=False,indent=2),encoding='utf-8')


def read_games(data_dir):
    p=games_path(data_dir)
    if p.exists():
        obj=json.loads(p.read_text(encoding='utf-8-sig'))
        return obj if isinstance(obj,list) else []
    return []


def save_games(data_dir, rows):
    valid={'pair','spell','read'}
    if any(x.get('game') not in valid or not str(x.get('word','')).strip() for x in rows):raise ValueError('Cần game hợp lệ và từ vựng không rỗng.')
    p=games_path(data_dir)
    if p.exists(): shutil.copy2(p,p.with_suffix('.json.bak'))
    p.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')


class ContentManager:
    def manage_page(self):
        """Admin content workspace; persistence remains in existing edit methods."""
        body=self.layout('Cài đặt › Quản lý nội dung')
        bg='#F8FAF5'; green='#2F7A50'; muted='#5B6B60'
        root=tk.Frame(body,bg=bg);root.pack(fill='both',expand=True)
        left=tk.Frame(root,bg='white',width=260,highlightbackground='#DDE7DE',highlightthickness=1)
        left.pack(side='left',fill='y',padx=(0,12),pady=6);left.pack_propagate(False)
        tk.Label(left,text='CẤU TRÚC · STRUCTURE',bg='white',fg=green,font=('Segoe UI',12,'bold')).pack(anchor='w',padx=14,pady=(16,10))
        tree=ttk.Treeview(left,show='tree',selectmode='browse');tree.pack(fill='both',expand=True,padx=8)
        try:
            from pathlib import Path
            library=Path(self.data_dir)/'content_library'
            subjects=[d for d in library.iterdir() if d.is_dir()] if library.exists() else []
            for folder in subjects:
                node=tree.insert('', 'end', text=folder.name)
                for file in sorted(folder.glob('*.json')):
                    tree.insert(node,'end',text=file.stem)
        except OSError:pass
        self.button(left,'+ Thêm mục · Add',self.edit_lesson).pack(fill='x',padx=12,pady=12)
        center=tk.Frame(root,bg=bg);center.pack(side='left',fill='both',expand=True,pady=6)
        tabs=tk.Frame(center,bg=bg);tabs.pack(fill='x',pady=(0,10))
        content=tk.Frame(center,bg=bg);content.pack(fill='both',expand=True)
        status=tk.StringVar(value='Chưa có thay đổi · No changes')
        def clear():
            for child in content.winfo_children():child.destroy()
        def line(text,action,description=''):
            row=tk.Frame(content,bg='white',padx=16,pady=12,highlightbackground='#DDE7DE',highlightthickness=1)
            row.pack(fill='x',pady=4)
            tk.Label(row,text=text,bg='white',fg='#1F3A2B',font=('Segoe UI',12,'bold'),anchor='w').pack(side='left',fill='x',expand=True)
            self.button(row,'Sửa · Edit',action).pack(side='right')
        def show(tab):
            clear()
            if tab=='Bài học':
                items=read_custom_lessons(self.data_dir)
                for i,item in enumerate(items):line(item.get('title','Bài chưa đặt tên'),lambda idx=i:self.edit_lesson(idx))
                if not items:tk.Label(content,text='Chưa có bài tự tạo',bg=bg,fg=muted).pack(pady=24)
            elif tab=='Từ vựng':
                for i,item in enumerate(read_games(self.data_dir)):
                    line(item.get('word','Từ mới'),lambda idx=i:self.edit_game_item(idx))
            elif tab=='Media':
                self.button(content,'Chọn hình ảnh / âm thanh · Browse',self.add_media_ui).pack(anchor='w',pady=12)
            else:
                tk.Label(content,text='Dữ liệu '+tab.lower()+' được chỉnh sửa qua trình quản lý Level hiện có.',bg=bg,fg=muted,wraplength=520).pack(anchor='w',pady=14)
                if hasattr(self,'manage_levels'):
                    self.button(content,'Mở trình quản lý Level',self.manage_levels).pack(anchor='w')
        for tab in ('Bài học','Từ vựng','Bài đọc','Câu hỏi','Media'):
            self.button(tabs,tab,lambda t=tab:show(t)).pack(side='left',padx=(0,5))
        footer=tk.Frame(center,bg='white',height=72);footer.pack(side='bottom',fill='x',pady=(8,0))
        tk.Label(footer,textvariable=status,bg='white',fg=muted,font=('Segoe UI',10)).pack(side='left',padx=12)
        self.button(footer,'+ Bài học',self.edit_lesson).pack(side='right',padx=6,pady=12)
        self.button(footer,'+ Từ vựng',self.edit_game_item).pack(side='right',padx=6)
        show('Bài học')

    def delete_content(self,kind,index):
        if not messagebox.askyesno('Xác nhận','Xóa mục này?'):return
        if kind=='lesson':
            items=read_custom_lessons(self.data_dir);items.pop(index);save_custom_lessons(self.data_dir,items)
        else:
            items=read_games(self.data_dir);items.pop(index);save_games(self.data_dir,items)
        self.exercises=self.reload_exercises();self.manage_page()

    def _form_window(self,title,fields,values,callback):
        win=tk.Toplevel(self);win.title(title);win.geometry('630x700');win.minsize(480,430);win.configure(bg='#F8FAF5');win.transient(self)
        canvas=tk.Canvas(win,bg='#F8FAF5',highlightthickness=0)
        scroll=tk.Scrollbar(win,command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
        frame=tk.Frame(canvas,bg='#F8FAF5',padx=20,pady=14)
        window=canvas.create_window((0,0),window=frame,anchor='nw')
        frame.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=e.width))
        inputs={}
        for key,label in fields:
            tk.Label(frame,text=label,anchor='w',bg='#F8FAF5',fg='#285D40',font=('Segoe UI',10,'bold')).pack(anchor='w',pady=(6,2))
            if key in ('prompt','accepted_answers','options'):
                widget=tk.Text(frame,height=3,width=55,wrap='word',font=('Segoe UI',10));widget.pack(fill='x');widget.insert('1.0',str(values.get(key,'')))
            else:
                widget=tk.Entry(frame,font=('Segoe UI',11));widget.pack(fill='x',ipady=5);widget.insert(0,str(values.get(key,'')))
            inputs[key]=widget
        def submit():
            vals={k:(w.get('1.0','end').strip() if isinstance(w,tk.Text) else w.get().strip()) for k,w in inputs.items()}
            try:callback(vals)
            except (ValueError,OSError) as exc:messagebox.showerror('Không lưu được',str(exc),parent=win);return
            win.destroy();self.exercises=self.reload_exercises();self.manage_page()
        self.action_button(frame,'Lưu thay đổi',submit).pack(pady=15)

    def edit_lesson(self,index=None):
        items=read_custom_lessons(self.data_dir);ex=items[index] if index is not None else {}
        fields=[('id','ID duy nhất'),('type','Loại: dictation / picture / error / reading / matching'),('icon','Icon (emoji hoặc ký tự)'),('title','Tên bài học'),('prompt','Câu hỏi / yêu cầu'),('answer','Đáp án'),('accepted_answers','Các đáp án chấp nhận (ngăn bởi |)'),('options','Gợi ý (ngăn bởi |)'),('image','Ảnh: media/tenfile.png'),('audio','Âm thanh: media/tenfile.wav')]
        vals={**ex,'id':ex.get('id','user_'+uuid.uuid4().hex[:10]),'type':ex.get('type','reading')}
        for k in ('accepted_answers','options'):
            vals[k]=' | '.join(ex.get(k,[]))
        def save(values):
            for k in ('accepted_answers','options'):values[k]=[s.strip() for s in values[k].split('|') if s.strip()]
            values={k:v for k,v in values.items() if v not in ('',[])}
            if index is None:items.append(values)
            else:items[index]=values
            save_custom_lessons(self.data_dir,items)
        self._form_window('Sửa bài học' if index is not None else 'Thêm bài học',fields,vals,save)

    def edit_game_item(self,index=None):
        items=read_games(self.data_dir);obj=items[index] if index is not None else {}
        fields=[('game','Loại trò chơi: pair / spell / read'),('key','Chữ cái / âm đầu (dùng cho pair)'),('word','Từ tiếng Anh'),('meaning','Nghĩa tiếng Việt (dùng cho read)'),('level','Cấp độ 1, 2 hoặc 3'),('image','Ảnh: media/tenfile.png'),('audio','Âm thanh: media/tenfile.wav')]
        vals={'game':'read','level':'1',**obj}
        def save(values):
            values['game']=values['game'].lower()
            values['level']=int(values['level'] or '1')
            if values['level'] not in (1,2,3):raise ValueError('Cấp độ phải là 1–3.')
            values={k:v for k,v in values.items() if v!=''}
            if index is None:items.append(values)
            else:items[index]=values
            save_games(self.data_dir,items)
        self._form_window('Sửa từ trò chơi' if index is not None else 'Thêm từ trò chơi',fields,vals,save)

    def add_media_ui(self):
        path=filedialog.askopenfilename(title='Chọn PNG/GIF/WAV',filetypes=[('Hình & âm thanh','*.png *.gif *.wav')]);
        if not path:return
        dest=user_content_dir(self.data_dir)/'media';dest.mkdir(exist_ok=True)
        filename=Path(path).name
        target=dest/filename
        if target.exists() and not messagebox.askyesno('Tệp đã tồn tại','Ghi đè file trùng tên?'):return
        shutil.copy2(path,target)
        messagebox.showinfo('Đã thêm',f'Nhập đường dẫn sau vào bài học hoặc trò chơi:\nmedia/{filename}')
