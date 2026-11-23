"""Local authenticated editing mode for curriculum and UI text. No remote access."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import simpledialog, messagebox, ttk, colorchooser, font as tkfont

FIELDS=('title','content','instructions','prompt','word','meaning','example','description','label')

class AdminEditor:
    def __init__(self,app):
        self.app=app
        self.root=Path(app.data_dir)
        self.auth_file=self.root/'admin_auth.json'
        self.overrides_file=self.root/'admin_text_overrides.json'
        self.overrides=self._read(self.overrides_file,{})
        self.enabled=False
        self.styles_file=self.root/'admin_style_overrides.json'
        self.styles=self._read(self.styles_file,{})
        self._originals={}
        self.badge=None
        self.marker=None
        self._widget=None
        self._bindings={}
        self._hover_job=None
        self._scan_job=None
        self.app.bind_all('<Control-Shift-A>',self._shortcut,add='+')
        self.app.bind_all('<Control-Shift-a>',self._shortcut,add='+')

    def _shortcut(self,event=None):
        # Only activate while the main application owns the focus.
        try:
            focused=self.app.focus_get()
            if focused is not None and focused.winfo_toplevel() is not self.app:
                return
        except tk.TclError:return
        self.toggle()
        return 'break'

    @staticmethod
    def _read(path,default):
        try:return json.loads(path.read_text(encoding='utf-8'))
        except (OSError,ValueError):return default

    @staticmethod
    def _digest(password,salt):
        return hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),240000).hex()

    def toggle(self):
        if self.enabled:
            self.disable();return
        record=self._read(self.auth_file,None)
        if not record:
            one=simpledialog.askstring('Thiết lập Admin','Tạo mật khẩu Admin (tối thiểu 8 ký tự):',show='*',parent=self.app)
            if one is None:return
            if len(one)<8:
                messagebox.showwarning('Admin','Mật khẩu phải có ít nhất 8 ký tự.',parent=self.app);return
            two=simpledialog.askstring('Thiết lập Admin','Nhập lại mật khẩu:',show='*',parent=self.app)
            if one!=two:
                messagebox.showwarning('Admin','Hai mật khẩu không khớp.',parent=self.app);return
            salt=os.urandom(16).hex()
            record={'salt':salt,'hash':self._digest(one,salt)}
            self.auth_file.write_text(json.dumps(record),encoding='utf-8')
        else:
            pw=simpledialog.askstring('Admin','Nhập mật khẩu Admin:',show='*',parent=self.app)
            if pw is None:return
            if not hmac.compare_digest(self._digest(pw,record['salt']),record['hash']):
                messagebox.showerror('Admin','Mật khẩu không đúng.',parent=self.app);return
        self.enabled=self.app.admin_enabled=True
        self.badge=tk.Label(self.app,text='✎ ADMIN · Ctrl+Shift+A để khóa',bg='#FDE68A',fg='#713F12',font=('Segoe UI',10,'bold'),padx=9,pady=5)
        self.badge.place(relx=.5,y=8,anchor='n');self.badge.lift()
        self._question_shortcut=tk.Button(self.app,text='Quản lý câu hỏi',
                                         command=self._open_questions,takefocus=True)
        self._question_shortcut.place(relx=1,x=-12,y=8,anchor='ne')
        self.marker=tk.Button(self.app,text='✎',bg='#FDE68A',fg='#713F12',font=('Segoe UI',12,'bold'),bd=0,padx=6,pady=3,cursor='hand2',command=self.edit_selected)
        self.marker.place_forget()
        self.scan()
        self._periodic_scan()
        messagebox.showinfo('Admin','Chế độ sửa trực tiếp đã bật. Di chuột lên tiêu đề, văn bản hoặc ô nội dung, rồi bấm ✎. Nhấn Admin trong dấu + lần nữa để khóa.',parent=self.app)

    def _open_questions(self):
        if self.enabled:
            self.app.question_editor()

    def disable(self):
        self.enabled=self.app.admin_enabled=False
        if self._scan_job is not None:
            try:self.app.after_cancel(self._scan_job)
            except tk.TclError:pass
            self._scan_job=None
        for widget,funcid in list(self._bindings.items()):
            try:widget.unbind('<Enter>',funcid)
            except tk.TclError:pass
        self._bindings.clear()
        for w in (self.badge,self.marker,getattr(self,'_question_shortcut',None)):
            try: w.destroy()
            except (tk.TclError,AttributeError):pass
        self.badge=self.marker=self._widget=None

    def _periodic_scan(self):
        if not self.enabled:return
        self.scan()
        self._scan_job=self.app.after(700,self._periodic_scan)

    def scan(self):
        if not self.enabled:return
        def visit(parent):
            for w in parent.winfo_children():
                if w in (self.marker,self.badge):continue
                if isinstance(w,(tk.Label,tk.Button,tk.Text,tk.Entry)) and w not in self._bindings:
                    try:
                        text=self._text(w)
                        if text and not (isinstance(w,tk.Button) and text.strip() in ('✎','+','×')):
                            fid=w.bind('<Enter>',lambda _e,widget=w:self._hover(widget),add='+')
                            self._bindings[w]=fid
                            self._apply_override(w)
                    except tk.TclError:pass
                try:visit(w)
                except tk.TclError:pass
        visit(self.app)

    def _text(self,w):
        if isinstance(w,tk.Text):return w.get('1.0','end-1c')
        if isinstance(w,tk.Entry):return w.get()
        return str(w.cget('text'))

    def _key(self,w,text):
        # Include subject and current page to avoid collisions across screens.
        lang=getattr(self.app,'lang','en')
        page=getattr(self.app,'_admin_page','')
        return f'{lang}|{page}|{text}'

    def _apply_override(self,w):
        old=self._text(w)
        key=self._key(w,old)
        self._originals[w]=key
        replacement=self.overrides.get(key)
        if replacement is not None:self._set(w,replacement)
        self._apply_style(w,self.styles.get(key,{}))

    def _apply_style(self,w,style):
        if not style:return
        try:
            kwargs={}
            if 'color' in style:kwargs['fg']=style['color']
            if any(k in style for k in ('family','size','bold','italic')):
                current=tkfont.Font(font=w.cget('font'))
                kwargs['font']=(style.get('family',current.actual('family')),
                                int(style.get('size',current.actual('size'))),
                                ('bold' if style.get('bold',current.actual('weight')=='bold') else 'normal')+' '+
                                ('italic' if style.get('italic',current.actual('slant')=='italic') else 'roman'))
            if kwargs:w.configure(**kwargs)
        except (tk.TclError,ValueError,TypeError):pass

    @staticmethod
    def _atomic_json(path,value):
        tmp=path.with_suffix('.tmp')
        tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
        os.replace(tmp,path)

    def _hover(self,w):
        if not self.enabled or not self.marker:return
        try:
            if not w.winfo_exists() or not w.winfo_viewable():return
            x=w.winfo_rootx()-self.app.winfo_rootx()+w.winfo_width()-12
            y=w.winfo_rooty()-self.app.winfo_rooty()+min(5,max(0,w.winfo_height()-28))
            x=max(8,min(x,self.app.winfo_width()-42));y=max(40,min(y,self.app.winfo_height()-42))
            self._widget=w
            self.marker.place(x=x,y=y,anchor='ne');self.marker.lift()
        except tk.TclError:pass

    def _set(self,w,value):
        if isinstance(w,tk.Text):
            state=str(w.cget('state'));w.configure(state='normal');w.delete('1.0','end');w.insert('1.0',value);w.configure(state=state)
        elif isinstance(w,tk.Entry):
            state=str(w.cget('state'));w.configure(state='normal');w.delete(0,'end');w.insert(0,value);w.configure(state=state)
        else:w.configure(text=value)

    def edit_selected(self):
        w=self._widget
        if w is None or not w.winfo_exists():return
        original=self._text(w)
        key=self._originals.get(w,self._key(w,original))
        popup=tk.Toplevel(self.app)
        popup.title('Admin Studio · Biên tập nội dung & kiểu chữ')
        popup.configure(bg='#F4F6FB')
        try:popup.state('zoomed')
        except tk.TclError:
            popup.geometry(f'{popup.winfo_screenwidth()}x{popup.winfo_screenheight()}+0+0')
        popup.transient(self.app)
        popup.grab_set()
        top=tk.Frame(popup,bg='#202C4A',padx=20,pady=12);top.pack(fill='x')
        tk.Label(top,text='✎  ADMIN STUDIO',font=('Segoe UI',17,'bold'),fg='white',bg='#202C4A').pack(side='left')
        tk.Button(top,text='✕  Đóng',command=popup.destroy,bg='#384766',fg='white',bd=0,padx=15,pady=7).pack(side='right')
        toolbar=tk.Frame(popup,bg='white',padx=18,pady=12);toolbar.pack(fill='x',padx=18,pady=(16,8))
        tk.Label(toolbar,text='Font',bg='white').pack(side='left',padx=(0,6))
        existing=self.styles.get(key,{})
        try:actual=tkfont.Font(font=w.cget('font')).actual()
        except tk.TclError:actual={'family':'Segoe UI','size':12,'weight':'normal','slant':'roman'}
        family=tk.StringVar(value=existing.get('family',actual['family']))
        fonts=sorted(set(tkfont.families(popup)))
        combo=ttk.Combobox(toolbar,textvariable=family,values=fonts,width=25,state='readonly');combo.pack(side='left',padx=(0,14))
        tk.Label(toolbar,text='Cỡ chữ',bg='white').pack(side='left',padx=(0,6))
        size=tk.IntVar(value=int(existing.get('size',actual['size'])))
        tk.Spinbox(toolbar,from_=8,to=100,textvariable=size,width=5).pack(side='left',padx=(0,14))
        bold=tk.BooleanVar(value=existing.get('bold',actual['weight']=='bold'))
        italic=tk.BooleanVar(value=existing.get('italic',actual['slant']=='italic'))
        tk.Checkbutton(toolbar,text='B  Đậm',variable=bold,bg='white',font=('Segoe UI',10,'bold')).pack(side='left',padx=6)
        tk.Checkbutton(toolbar,text='I  Nghiêng',variable=italic,bg='white',font=('Segoe UI',10,'italic')).pack(side='left',padx=6)
        color=tk.StringVar(value=existing.get('color',str(w.cget('fg'))))
        def choose_color():
            result=colorchooser.askcolor(color=color.get(),parent=popup)
            if result and result[1]:color.set(result[1])
        color_btn=tk.Button(toolbar,text='🎨 Màu chữ',command=choose_color,bg='#EAEFF8',bd=0,padx=10,pady=7)
        color_btn.pack(side='left',padx=8)
        def update_preview(*_):
            try:
                n=max(8,min(100,int(size.get())))
                editor.configure(font=(family.get(),n,('bold' if bold.get() else 'normal')+' '+('italic' if italic.get() else 'roman')),fg=color.get())
                color_btn.configure(fg=color.get())
            except (tk.TclError,ValueError):pass
        info=tk.Label(popup,text='Chỉnh sửa nội dung bên dưới. Định dạng được áp dụng cho toàn bộ văn bản của thành phần này.',bg='#F4F6FB',fg='#5D6C86',font=('Segoe UI',11))
        info.pack(anchor='w',padx=22,pady=(8,4))
        frame=tk.Frame(popup,bg='white',padx=2,pady=2);frame.pack(fill='both',expand=True,padx=18,pady=(4,10))
        editor=tk.Text(frame,wrap='word',undo=True,bd=0,padx=20,pady=20)
        sc=ttk.Scrollbar(frame,command=editor.yview);sc.pack(side='right',fill='y')
        editor.configure(yscrollcommand=sc.set);editor.pack(fill='both',expand=True)
        editor.insert('1.0',original)
        for variable in (family,size,bold,italic,color):variable.trace_add('write',update_preview)
        update_preview()
        bottom=tk.Frame(popup,bg='#F4F6FB',padx=18,pady=14);bottom.pack(fill='x')
        def save():
            value=editor.get('1.0','end-1c')
            style={'family':family.get(),'size':max(8,min(100,int(size.get()))),'bold':bold.get(),'italic':italic.get(),'color':color.get()}
            if value!=original:
                persisted=self._save_curriculum(original,value)
                if not persisted:
                    self.overrides[key]=value
                    self._atomic_json(self.overrides_file,self.overrides)
                self._set(w,value)
                if persisted:
                    try:self.app.curriculum.reload()
                    except Exception:pass
            self.styles[key]=style
            self._atomic_json(self.styles_file,self.styles)
            self._apply_style(w,style)
            popup.destroy()
        tk.Button(bottom,text='✓  LƯU NỘI DUNG & ĐỊNH DẠNG',command=save,bg='#337C61',fg='white',font=('Segoe UI',12,'bold'),bd=0,padx=22,pady=12).pack(side='right')
        tk.Button(bottom,text='Hủy',command=popup.destroy,bg='#DDE4F0',fg='#253451',bd=0,padx=20,pady=12).pack(side='right',padx=12)
        popup.bind('<Escape>',lambda _e:popup.destroy())
        popup.bind('<Control-s>',lambda _e:save())
        editor.focus_set()

    def _save_curriculum(self,old,new):
        """Persist exact unique matching field; do not blindly replace multiple records."""
        content=getattr(self.app,'curriculum',None)
        if content is None:return False
        from tuhoc.lessons.level_flow import library_file
        for kind in ('blocks','lessons','questions','vocab','reading'):
            path=library_file(content.data_dir,kind)
            if not path.exists():continue
            rows=self._read(path,[])
            if not isinstance(rows,list):continue
            matches=[(r,k) for r in rows if isinstance(r,dict) for k in FIELDS if r.get(k)==old]
            if len(matches)!=1:continue
            row,key=matches[0];row[key]=new
            backup=path.with_suffix('.json.admin.bak')
            if not backup.exists():backup.write_bytes(path.read_bytes())
            temp=path.with_suffix('.tmp')
            temp.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
            os.replace(temp,path)
            return True
        return False
