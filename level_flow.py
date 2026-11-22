"""Five themes, three modes and ten levels per theme. User content overrides bundled demo."""
from strings_vi import t
from ui_tokens import COLORS as TOKEN_COLORS, font_at
import json, random, time, tkinter as tk
from pathlib import Path
from card_motion import animate_card
from icon_animations import register as register_icon, play as play_icon
from tkinter import messagebox, simpledialog, filedialog, colorchooser
import ui_dialogs as dialogs
from lesson_display_names import display_name, breadcrumb
from theme_config import load as load_themes, save as save_themes, tuples as theme_tuples, max_level as theme_max, normalize_code, icon_file, lesson_count as theme_lesson_count

THEMES=[('Family & Friends','Family & Friends','⌂','#E8F3FF'),('sports','Thể Thao','★','#FFF2DF'),('actions','Hành Động','➤','#F1E9FF'),('animals','Con Vật','♣','#E8F7E8'),('fruits','Trái Cây','●','#FFF0EF')]
LESSON_KEYS=['theme','level','lesson','title','instructions','content','image']
QUESTION_KEYS=['theme','level','lesson','id','type','prompt','options','answer','accepted_answers','image','audio']
VOCAB_KEYS=['theme','level','lesson','word','meaning','image']
BLOCK_KEYS=['theme','level','lesson','order','title','content','image','audio','title_audio','content_audio']
READING_KEYS=['theme','level','lesson','title','content','image']
QUESTION_TYPES=('choice','picture_choice','true_false','fill','error','order','matching','listening_choice','listening_fill','image_multi_choice','listening_image_choice','picture_missing_letters','sentence_gaps','conversation_gaps','passage_gaps','image_multi_select','text_multi_select','audio_multi_select','image_write_answer','image_underline_choice','sentence_underline_words','dropdown_fill_blank','multi_fill_blanks','image_sentence_fill','image_letter_pick','inline_dropdown_fill')
QUESTION_LABELS={'choice':'Đọc câu hỏi – chọn đáp án','picture_choice':'Nhìn hình – chọn đáp án','true_false':'Đúng / Sai','fill':'Điền đáp án','error':'Tìm lỗi','order':'Sắp xếp','matching':'Nối chữ / hình / hỗn hợp','listening_choice':'Nghe – chọn đáp án','listening_fill':'Nghe – điền đáp án'}

from new_exercise_editors import NEW_TYPES, LABELS as NEW_LABELS
QUESTION_LABELS.update(NEW_LABELS)

def library_file(data_dir,name):return Path(data_dir)/'content_library'/('level_'+name+'.json')
def load_rows(data_dir,name,base):
    path=library_file(data_dir,name)
    if path.exists():
        try:return json.loads(path.read_text(encoding='utf-8-sig'))
        except (OSError,ValueError):pass
    demo=Path(__file__).resolve().parent/'content_library'/'demo_levels'/f'{name}.json'
    return json.loads(demo.read_text(encoding='utf-8-sig')) if demo.exists() else []
def save_rows(data_dir,name,rows):
    path=library_file(data_dir,name);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
def validate_level(v):
    n=int(v)
    if n<1:raise ValueError('Level phải từ 1 trở lên.')
    return n

def import_levels(path,data_dir):
    from openpyxl import load_workbook
    book=load_workbook(path,read_only=True,data_only=True)
    definitions={'lessons':('CapHoc',LESSON_KEYS),'questions':('CauHoiCap',QUESTION_KEYS),'vocab':('TuVungCap',VOCAB_KEYS),'blocks':('NoiDungBaiHoc',BLOCK_KEYS),'reading':('BaiDoc',READING_KEYS)}
    output={}
    for kind,(sheet,cols) in definitions.items():
        if sheet not in book:continue
        rows=book[sheet].iter_rows(values_only=True)
        header=next(rows,None)
        old_cols=[c for c in cols if c!='lesson']
        incoming=list(header[:len(cols)]) if header else []
        if not header or (incoming!=cols and list(header[:len(old_cols)])!=old_cols):raise ValueError(f'Sheet {sheet} sai tên cột.')
        actual=cols if incoming==cols else old_cols
        converted=[]
        for values in rows:
            if not any(v is not None and str(v).strip() for v in values):continue
            obj={key:(values[i] if i<len(values) and values[i] is not None else '') for i,key in enumerate(actual)}
            obj['theme']=normalize_code(obj['theme'],data_dir)
            if obj['theme'] not in {t[0] for t in theme_tuples(data_dir)}:raise ValueError(f'Chủ đề không hợp lệ: {obj["theme"]}')
            obj['level']=validate_level(obj['level'])
            if obj['level']>theme_max(data_dir,obj['theme']):raise ValueError('Level vượt giới hạn của chủ đề.')
            obj['lesson']=int(obj.get('lesson') or 1)
            if not 1 <= obj['lesson'] <= theme_lesson_count(data_dir,obj['theme'],obj['level']):raise ValueError('Lesson vượt số lượng của Level.')
            if kind=='blocks':
                obj['order']=int(obj['order'])
                if obj['order']<1:raise ValueError('Thứ tự phải từ 1 trở lên.')
            for key in ('options','accepted_answers'):
                if key in obj:obj[key]=[a.strip() for a in str(obj[key]).split('|') if a.strip()]
            if kind=='questions':
                if obj['type'] not in QUESTION_TYPES:raise ValueError(f'Dạng câu hỏi không hợp lệ: {obj["type"]}')
                if obj['type'] in ('listening_choice','listening_fill','listening_image_choice') and not obj.get('audio'):raise ValueError('Bài nghe cần đường dẫn audio.')
                if obj['type']=='picture_choice' and (not obj.get('image') or len(obj.get('options',[]))<2 or not obj.get('answer')):raise ValueError('Nhìn hình chọn đáp án cần ảnh, ít nhất 2 lựa chọn và đáp án đúng.')
            converted.append(obj)
        output[kind]=converted
    if not output:raise ValueError('Không tìm thấy sheet CapHoc, CauHoiCap hoặc TuVungCap.')
    from safe_storage import commit_json
    commit_json({library_file(data_dir, kind): rows for kind, rows in output.items()})
    return {key:len(value) for key,value in output.items()}

def export_levels(path,data_dir):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    wb=Workbook()
    if wb.active is not None:
        wb.remove(wb.active)
    for kind,sheet,keys in [('lessons','CapHoc',LESSON_KEYS),('questions','CauHoiCap',QUESTION_KEYS),('vocab','TuVungCap',VOCAB_KEYS),('blocks','NoiDungBaiHoc',BLOCK_KEYS),('reading','BaiDoc',READING_KEYS)]:
        ws=wb.create_sheet(sheet);ws.append(keys)
        for item in load_rows(data_dir,kind,None):
            ws.append(['|'.join(map(str,item.get(k,[]))) if isinstance(item.get(k),list) else item.get(k,'') for k in keys])
        ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions
        for col,heading in enumerate(keys,1):ws.column_dimensions[get_column_letter(col)].width=60 if heading in ('content','prompt','instructions') else 26
        for c in ws[1]:c.font=Font(bold=True,color='FFFFFF');c.fill=PatternFill('solid',fgColor='39865B');c.alignment=Alignment(wrap_text=True)
    info=wb.create_sheet('HuongDan')
    for row in [('Hướng dẫn','Chủ đề và số level tùy chỉnh riêng theo môn trong themes.json'),('theme','Sử dụng mã code trong themes.json của môn tương ứng'),('level','Nhập số từ 1 đến max_level của chủ đề'),('CapHoc','Mỗi theme+level có 1 nội dung bài học'),('CauHoiCap','Có thể thêm hoặc xóa câu. Mỗi lượt bốc tối đa 10 câu ở cùng level.'),('type','choice / picture_choice / listening_choice / listening_fill / true_false / fill / error / order / matching'),('options','Ngăn cách các phương án bằng dấu |'),('accepted_answers','Ngăn cách đáp án đúng bằng dấu |'),('TuVungCap','Danh sách từ của từng level; có thể chọn từ để lưu Flashcard'),('NoiDungBaiHoc','Mỗi dòng là một khối hình bên trái - chữ bên phải, dùng order để sắp xếp; xóa dòng để xóa khối.'),('BaiDoc','Mỗi theme+level có thể có một hoặc nhiều bài đọc: tiêu đề, nội dung bên trái, hình tùy chọn bên phải.'),('Ảnh / âm thanh','Cột image dùng cho hình; cột audio dùng cho câu nghe hoặc từng block. Chọn tệp trong trình quản lý để sao chép vào media.'),('Lưu ý','Khi nhập, mỗi sheet có trong Excel sẽ thay thế dữ liệu tương ứng; sao lưu file Excel trước.')]:info.append(row)
    info.column_dimensions['A'].width=25;info.column_dimensions['B'].width=105
    wb.save(path)

class LevelFlowMixin:
    def _levels(self,kind):
        return self.curriculum.rows.get(kind,[]) if hasattr(self,'curriculum') else load_rows(self.data_dir,kind,None)
    def _themes(self):return theme_tuples(self.curriculum.data_dir)
    def _max_level(self,code):return theme_max(self.curriculum.data_dir,code)
    def _lesson_count(self,code,level):return theme_lesson_count(self.curriculum.data_dir,code,level)
    def _theme(self,code):return next(item for item in self._themes() if item[0]==code)
    def _theme_icon(self,parent,theme,size=56,bg='#E8F3EB',fallback='📘'):
        """Fixed-size icon slot, independent of image dimensions or emoji glyphs."""
        slot=tk.Frame(parent,width=size,height=size,bg=bg,cursor='hand2')
        slot.pack_propagate(False)
        entry=next((r for r in load_themes(self.curriculum.data_dir) if r['code']==theme),None)
        path=icon_file(self.curriculum.data_dir,entry or {})
        if path:
            try:
                from PIL import Image,ImageTk
                with Image.open(path) as original:
                    im=original.convert('RGBA')
                    im.thumbnail((size,size),Image.Resampling.LANCZOS)
                    canvas=Image.new('RGBA',(size,size),(0,0,0,0))
                    canvas.alpha_composite(im,((size-im.width)//2,(size-im.height)//2))
                    photo=ImageTk.PhotoImage(canvas,master=slot)
                label=tk.Label(slot,image=photo,bg=bg,bd=0,cursor='hand2')
                label._icon_photo=photo
                label.place(x=0,y=0,width=size,height=size)
                return slot
            except (OSError,ValueError,ImportError,tk.TclError):
                pass
        label=tk.Label(slot,text=fallback,font=('Segoe UI Symbol',28,'bold'),
                       bg=bg,fg='#285D40',bd=0,cursor='hand2')
        label.place(x=0,y=0,width=size,height=size)
        return slot

    def topic_page(self):
        from lesson_map_ui import LessonMap
        LessonMap(self, False)

    def _mode_cards(self):
        defaults=[('lesson',t('lessons'),'📖'),('quiz',t('exercises'),'✎'),('vocab',t('vocab'),'☆'),('reading','Đọc / Reading','📖')]
        path=self.curriculum.data_dir/'mode_cards.json'
        try:
            saved=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        except (OSError,ValueError):saved={}
        return [(key,str(saved.get(key,{}).get('title') or title),str(saved.get(key,{}).get('icon') or icon),str(saved.get(key,{}).get('image') or '')) for key,title,icon in defaults]

    def manage_mode_cards(self):
        """Customize four learning-mode card titles and images per language."""
        body=self.layout('Chỉnh sửa 4 mục chọn bài học')
        self.label(body,'Đổi tên và chọn ảnh icon cho 4 mục, giống quản lý chủ đề.',12).pack(anchor='w',pady=8)
        path=self.curriculum.data_dir/'mode_cards.json'
        for key,title,icon,image_path in self._mode_cards():
            panel=tk.Frame(body,bg='white',padx=12,pady=10)
            panel.pack(fill='x',pady=7)
            tk.Label(panel,text=title,bg='white',fg='#285D40',font=font_at(12, 'bold')).pack(anchor='w')
            row=tk.Frame(panel,bg='white');row.pack(fill='x',pady=5)
            tk.Label(row,text='Tên hiển thị',bg='white',width=15,anchor='w').pack(side='left')
            name=tk.Entry(row,font=font_at(11));name.insert(0,title);name.pack(side='left',fill='x',expand=True)
            row2=tk.Frame(panel,bg='white');row2.pack(fill='x',pady=5)
            tk.Label(row2,text='Icon chữ',bg='white',width=15,anchor='w').pack(side='left')
            symbol=tk.Entry(row2);symbol.insert(0,icon);symbol.pack(side='left',fill='x',expand=True)
            row3=tk.Frame(panel,bg='white');row3.pack(fill='x',pady=5)
            tk.Label(row3,text='Ảnh icon',bg='white',width=15,anchor='w').pack(side='left')
            image_entry=tk.Entry(row3);image_entry.insert(0,image_path);image_entry.pack(side='left',fill='x',expand=True)
            def pick(entry=image_entry):
                source=filedialog.askopenfilename(title='Chọn ảnh icon',filetypes=[('Ảnh','*.png *.jpg *.jpeg *.webp *.gif')])
                if not source:return
                try:
                    from PIL import Image,ImageOps
                    import uuid
                    folder=self.curriculum.data_dir/'icons';folder.mkdir(parents=True,exist_ok=True)
                    target=folder/(uuid.uuid4().hex[:12]+'.png')
                    with Image.open(source) as original:
                        original.seek(0)
                        img=ImageOps.exif_transpose(original).convert('RGBA');img.thumbnail((256,256),Image.Resampling.LANCZOS)
                        canvas=Image.new('RGBA',(256,256),(0,0,0,0))
                        canvas.alpha_composite(img,((256-img.width)//2,(256-img.height)//2));canvas.save(target)
                    entry.delete(0,'end');entry.insert(0,'icons/'+target.name)
                except (OSError,ValueError,ImportError) as exc:messagebox.showerror('Lỗi ảnh',str(exc))
            tk.Button(row3,text='🖼 Chọn ảnh',command=pick,bg='#EAF2FF',bd=0,padx=10,pady=6).pack(side='left',padx=6)
            def save(key=key,name=name,symbol=symbol,image_entry=image_entry):
                try:
                    data=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
                    data[key]={'title':name.get().strip() or key,'icon':symbol.get().strip(),'image':image_entry.get().strip()}
                    path.parent.mkdir(parents=True,exist_ok=True)
                    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
                    messagebox.showinfo('Đã lưu','Đã cập nhật mục '+data[key]['title'])
                except (OSError,ValueError) as exc:messagebox.showerror('Lỗi lưu',str(exc))
            tk.Button(panel,text='💾 Lưu thay đổi',command=save,bg='#DDF2E4',fg='#285D40',bd=0,padx=12,pady=7).pack(anchor='e')
        self.button(body,'← Quản lý nội dung',self.manage_levels).pack(anchor='w',pady=12)

    def theme_page(self,theme):
        """Frameless icon launcher, matching the topic selector."""
        title=self._theme(theme)[1]
        body=self.layout(title)
        bg=body['bg']
        self.label(body,'Chọn nội dung muốn học.',12).pack(anchor='w',pady=(0,22))
        grid=tk.Frame(body,bg=bg)
        grid.pack(fill='x',padx=18,pady=(8,0))
        for col in range(4):
            grid.grid_columnconfigure(col,weight=1,uniform='mode_apps')
        for i,(key,name,icon,image_path) in enumerate(self._mode_cards()):
            tile=tk.Frame(grid,bg=bg,width=176,height=140,cursor='hand2')
            tile.grid(row=i//4,column=i%4,padx=12,pady=(4,12),sticky='n')
            tile.pack_propagate(False)
            slot=tk.Frame(tile,bg=bg,width=76,height=76,cursor='hand2')
            slot.pack(pady=(2,8))
            slot.pack_propagate(False)
            image_label=tk.Label(slot,bg=bg,bd=0,cursor='hand2')
            image_label.place(relx=.5,rely=.5,anchor='center')
            original=None
            if image_path:
                try:
                    from PIL import Image,ImageTk
                    file=(self.curriculum.data_dir/image_path).resolve()
                    if not file.is_relative_to(self.curriculum.data_dir.resolve()):
                        raise ValueError('Invalid image path')
                    with Image.open(file) as source:
                        original=source.convert('RGBA').copy()
                except (OSError,ValueError,ImportError):
                    original=None
            def render(size,label=image_label,source=original,symbol=icon):
                if source is not None:
                    from PIL import Image,ImageTk
                    pic=source.copy()
                    pic.thumbnail((size,size),Image.Resampling.LANCZOS)
                    photo=ImageTk.PhotoImage(pic,master=label)
                    label.configure(image=photo,text='',width=size,height=size)
                    label.image=photo
                else:
                    label.configure(image='',text=symbol,font=('Segoe UI Symbol',max(24,int(size*.57)),'bold'),
                                    fg='#285D40',width=3,height=2)
            render(56)
            label=tk.Label(tile,text=name,font=font_at(13, 'bold'),bg=bg,fg='#285D40',
                           cursor='hand2',wraplength=166,justify='center')
            label.pack(fill='x')
            register_icon('mode:'+key,image_label)
            busy={'value':False}
            def open_mode(event=None,mode=key,draw=render,flag=busy,holder=tile):
                if flag['value']:return
                flag['value']=True
                play_icon('mode:'+mode,lambda:self.level_list(theme,mode))
            for widget in (tile,slot,image_label,label):
                widget.bind('<Button-1>',open_mode)
        self.button(body,'← Về danh sách chủ đề',self.topic_page).pack(anchor='w',pady=15)
    def level_list(self,theme,mode):
        names={'lesson':t('lessons'),'quiz':t('exercises'),'vocab':t('vocab'),'reading':'Đọc' if getattr(self,'lang','en')=='vi' else 'Reading'}
        body=self.layout(self._theme(theme)[1]+' / '+names[mode]);grid=tk.Frame(body,bg=body['bg']);grid.pack(fill='x')
        for col in range(5):grid.grid_columnconfigure(col,weight=1,uniform='levels')
        for level in range(1,self._max_level(theme)+1):
            done=self.db.lesson_completed(self.student['id'],f'{theme}_{level}')
            card=tk.Frame(grid,bg='white',height=112,highlightthickness=1,highlightbackground='#DCE7DC',cursor='hand2');card.grid(row=(level-1)//5,column=(level-1)%5,padx=8,pady=8,sticky='nsew');card.grid_propagate(False)
            text=tk.Label(card,text=self._display_name('level',theme,level),font=font_at(15, 'bold'),fg='#285D40',bg='white',cursor='hand2');text.pack(pady=(20,7))
            status=tk.Label(card,text='✓ Đã học' if done else self._display_name('level',theme,level),fg='#39865B' if done else '#778A7B',bg='white',cursor='hand2');status.pack()
            action=lambda t,l:self.lesson_list(t,l,mode)
            for w in (card,text,status):w.bind('<Button-1>',lambda e=None,l=level,fn=action,c=card:animate_card(c, lambda t=theme,n=l:fn(t,n)))
        self.button(body,'← Ba mục của chủ đề',lambda:self.theme_page(theme)).pack(anchor='w',pady=16)
    def lesson_list(self,theme,level,mode='lesson'):
        self._selected_lesson=None
        body=self.layout(f'{self._theme(theme)[1]} · {self._display_name("level", theme, level)} · Chọn bài học')
        self.label(body,f'Chọn một trong {self._lesson_count(theme,level)} Lesson để bắt đầu.',12).pack(anchor='w',pady=10)
        grid=tk.Frame(body,bg=body['bg']);grid.pack(fill='x')
        for col in range(5):grid.grid_columnconfigure(col,weight=1,uniform='lessons')
        for lesson in range(1,self._lesson_count(theme,level)+1):
            card=tk.Frame(grid,bg='white',height=105,highlightthickness=1,highlightbackground='#DCE7DC',cursor='hand2')
            card.grid(row=(lesson-1)//5,column=(lesson-1)%5,padx=8,pady=8,sticky='nsew');card.grid_propagate(False)
            label=tk.Label(card,text=self._display_name('lesson',theme,level,lesson),font=font_at(14, 'bold'),fg='#285D40',bg='white',cursor='hand2');label.pack(expand=True)
            def go(n=lesson):
                self._selected_lesson=n
                action={'lesson':self.level_lesson,'quiz':self.level_quiz,'vocab':self.level_vocab,'reading':self.level_reading}[mode]
                action(theme,level)
            for widget in (card,label):widget.bind('<Button-1>',lambda e=None,fn=go,c=card:animate_card(c,fn))
        self.button(body,'← Chọn Level',lambda:self.level_list(theme,mode)).pack(anchor='w',pady=15)
    def _row(self,kind,theme,level):
        lesson=getattr(self,'_selected_lesson',None)
        return [item for item in self._levels(kind) if item['theme']==theme and int(item['level'])==level and (lesson is None or int(item.get('lesson',1))==lesson)]
    def _media_panel(self,parent,relative,theme):
        w=int(getattr(self,'_display_settings',{}).get('image_width',350));h=int(getattr(self,'_display_settings',{}).get('image_height',240))
        panel=tk.Frame(parent,bg='#E8F3EB',width=w+24,height=h+30);panel.pack(side='left',padx=(0,16));panel.pack_propagate(False)
        file=self.media_file(relative)
        if file:
            try:
                from animated_media import display_image
                display_image(panel,file,w,h,bg='#E8F3EB',expand=True)
                return
            except (ImportError,OSError,ValueError,tk.TclError):
                pass
        tk.Label(panel,text=self._theme(theme)[2],font=('Segoe UI Symbol',82),bg='#F0F3FF',fg='#5269E8').pack(expand=True)
        tk.Label(panel,text=self._theme(theme)[1],font=font_at(17, 'bold'),bg='#E8F3EB',fg='#285D40').pack(pady=24)
    def _selection_button(self,parent,textbox):
        def save():
            try:word=textbox.get('sel.first','sel.last').strip()
            except tk.TclError:word=''
            if not word:dialogs.showinfo('Chọn từ','Hãy bôi đen từ/cụm từ trong nội dung.');return
            meaning=simpledialog.askstring('Lưu từ',f'Nghĩa của “{word}”:',parent=self)
            if meaning is not None:self.db.save_word_in_source(self.student['id'],self.learning.wordkey(word),meaning or 'Từ trong bài học','manual');dialogs.showinfo('Đã lưu','Đã lưu vào Flashcard.')
        self.action_button(parent,'☆ Lưu từ đã bôi đen',save).pack(anchor='w',pady=8)
    def _level_navigation(self,body,theme,level,mode='lesson'):
        """Persistent, immediately visible back/previous/next controls."""
        bar=tk.Frame(body,bg='#EDF3FF',padx=12,pady=9)
        bar.pack(fill='x',pady=(0,15))
        tk.Button(bar,text='←  Chọn Lesson',command=self.topic_page,
                  bg=TOKEN_COLORS['surface'],fg='#26345E',font=font_at(11, 'bold'),
                  bd=0,padx=12,pady=9,cursor='hand2').pack(side='left',padx=(0,9))
        tk.Button(bar,text='⌂  Chủ đề',command=self.topic_page,
                  bg=TOKEN_COLORS['surface'],fg='#26345E',font=font_at(11),
                  bd=0,padx=12,pady=9,cursor='hand2').pack(side='left')
        tk.Label(bar,text=f'LEVEL {level} / {self._max_level(theme)}',
                 bg='#EDF3FF',fg='#4F46A5',font=font_at(11, 'bold')).pack(side='left',padx=18)
        if not getattr(self,'_selected_lesson',None) and level < self._max_level(theme):
            action=self.level_lesson if mode=='lesson' else self.level_reading
            tk.Button(bar,text='Level tiếp  →',command=lambda:action(theme,level+1),
                      bg='#6A5AE0',fg='white',font=font_at(11, 'bold'),
                      bd=0,padx=13,pady=9,cursor='hand2').pack(side='right')
        if not getattr(self,'_selected_lesson',None) and level > 1:
            action=self.level_lesson if mode=='lesson' else self.level_reading
            tk.Button(bar,text='←  Level trước',command=lambda:action(theme,level-1),
                      bg=TOKEN_COLORS['surface'],fg='#26345E',font=font_at(11),
                      bd=0,padx=12,pady=9,cursor='hand2').pack(side='right',padx=8)

    def level_lesson(self,theme,level):
        body=self.layout(self._lesson_breadcrumb(theme, level, getattr(self, '_selected_lesson', 1) or 1))
        self._level_navigation(body,theme,level,'lesson')
        # Presentation-only lesson heading: original lesson content and actions remain.
        banner=tk.Frame(body,bg='#EDF1FF',padx=20,pady=15,
                        highlightbackground='#DCE3FF',highlightthickness=1)
        banner.pack(fill='x',pady=(0,14))
        tk.Label(banner,text='HÀNH TRÌNH HỌC TẬP  /  BÀI HỌC',
                 bg='#EDF1FF',fg='#5269E8',font=font_at(10, 'bold')).pack(anchor='w')
        tk.Label(banner,text=self._lesson_breadcrumb(theme, level, getattr(self, '_selected_lesson', 1) or 1),
                 bg='#EDF1FF',fg='#26345E',font=font_at(17, 'bold')).pack(anchor='w',pady=(5,3))
        tk.Label(banner,text='Đọc nội dung, nghe phát âm và lưu từ mới bằng cách bôi đen.',
                 bg='#EDF1FF',fg='#687694',font=font_at(10)).pack(anchor='w')
        # Expanded Pygame companion; original Tkinter lesson stays intact.
        def open_expanded_lesson():
            from pygame_lesson_window import available, launch
            if not available():
                dialogs.showerror('Thieu pygame', 'Hay cai pygame de mo Lesson Studio.', parent=self)
                return
            rows = self._row('lessons', theme, level)
            lesson = rows[0] if rows else {'title': 'Bai hoc', 'content': ''}
            blocks = self._row('blocks', theme, level)
            # Pass resolved absolute media paths; the SDL thread must not call Tk.
            resolved = []
            for block in blocks:
                b = dict(block)
                if b.get('image'):
                    b['image'] = self.media_file(b['image']) or b['image']
                resolved.append(b)
            lesson = dict(lesson)
            if lesson.get('image'):
                lesson['image'] = self.media_file(lesson['image']) or lesson['image']
            # Capture the expansion button's screen position before launching Pygame.
            self.update_idletasks()
            origin = (expand_button.winfo_rootx() + expand_button.winfo_width() / 2,
                      expand_button.winfo_rooty() + expand_button.winfo_height() / 2)
            launch_settings = dict(getattr(self, '_display_settings', {}) or {})
            launch_settings['_opening_origin'] = origin
            # SDL runs on a worker thread: never open Tk dialogs or write the
            # database there. Transfer selected text to the Tk event loop.
            import queue
            vocabulary_requests = queue.Queue()
            launch_settings['_on_add_vocabulary'] = vocabulary_requests.put
            def process_vocabulary_requests():
                try:
                    if not self.winfo_exists():
                        return
                    while True:
                        try:
                            phrase = vocabulary_requests.get_nowait()
                        except queue.Empty:
                            break
                        if getattr(self, 'lang', 'en') == 'vi':
                            meaning = ''
                        else:
                            meaning = simpledialog.askstring(
                                'Thêm từ vựng',
                                f'Nhập nghĩa hoặc ghi chú cho “{phrase}”:', parent=self)
                            if meaning is None:
                                continue
                        try:
                            self.db.save_word_in_source(
                                self.student['id'], self.learning.wordkey(phrase),
                                meaning.strip(), 'lesson', theme, level)
                            dialogs.showinfo('Đã lưu',
                                                f'Đã thêm “{phrase}” vào Flashcard.', parent=self)
                        except Exception as exc:
                            dialogs.showerror('Lỗi lưu từ vựng', str(exc), parent=self)
                finally:
                    if self.winfo_exists() and (not vocabulary_requests.empty() or
                            getattr(self, '_lesson_vocab_poll_until', 0) > time.monotonic()):
                        self.after(200, process_vocabulary_requests)
            self._lesson_vocab_poll_until = time.monotonic() + 86400
            self.after(200, process_vocabulary_requests)
            started = launch(self._lesson_breadcrumb(theme, level, getattr(self, '_selected_lesson', 1) or 1), lesson, resolved,
                             getattr(self, 'data_dir', None), launch_settings)
            if not started:
                dialogs.showinfo('Lesson Studio', 'Mot cua so Pygame khac dang mo.', parent=self)
        expand_button = tk.Button(banner, text='⛶  MỞ RỘNG TOÀN MÀN HÌNH', command=open_expanded_lesson,
                  font=font_at(10, 'bold'), bg='#405ED5', fg='white',
                  bd=0, padx=12, pady=8, cursor='hand2')
        expand_button.pack(anchor='e', pady=(6,0))
        data=self._row('lessons',theme,level)
        item=data[0] if data else {'title':'Cùng Học Cùng Vui','instructions':'Các em hãy đọc bài và ghi nhớ.','content':''}
        settings=getattr(self,'_display_settings',{})
        title_size=int(settings.get('title_size',20))
        content_size=int(settings.get('content_size',settings.get('text_size',18)))
        title_color=settings.get('title_color','#285D40')
        content_color=settings.get('content_color','#233C2A')
        tk.Label(body,text=item.get('title',t('lessons')),font=('Segoe UI',title_size,'bold'),
                 fg=title_color,bg=body['bg'],anchor='w',justify='left',wraplength=950).pack(fill='x',pady=(0,8))
        if item.get('instructions'):
            self.label(body,item['instructions'],11,color='#607464').pack(anchor='w',pady=(0,12))
        # One vocabulary action for the entire lesson (top-right), not one per block.
        # Text widgets use exportselection=False so clicking the button retains selection.
        selected_text=[None]
        text_widgets=[]
        def add_vocabulary():
            ordered=([selected_text[0]] if selected_text[0] is not None else []) + [w for w in text_widgets if w is not selected_text[0]]
            word=''
            for widget in ordered:
                try:
                    candidate=widget.get('sel.first','sel.last').strip()
                    if candidate:
                        word=candidate
                        break
                except tk.TclError:
                    continue
            if not word:
                dialogs.showinfo('Chọn từ', 'Hãy bôi đen một từ hoặc cụm từ trong nội dung bài học trước khi thêm.')
                return
            if getattr(self, 'lang', 'en') == 'vi':
                meaning = ''
            else:
                meaning = simpledialog.askstring('Thêm từ vựng', f'Nhập nghĩa hoặc ghi chú cho “{word}”:', parent=self)
                if meaning is None:
                    return
            self.db.save_word_in_source(self.student['id'],self.learning.wordkey(word),meaning.strip(),'lesson',theme,level)
            dialogs.showinfo('Đã lưu',f'Đã thêm “{word}” vào Flashcard.')
        # Fixed overlay on root: independent of the scrollable lesson canvas.
        # The recorder remains its own control in the upper-right corner.
        self.show_floating_vocabulary(add_vocabulary)
        blocks=sorted(self._row('blocks',theme,level),key=lambda b:int(b.get('order',1)))
        if not blocks:
            blocks=[{'title':item.get('title','Nội dung bài học'), 'content':item.get('content',''), 'image':item.get('image',''),'audio':item.get('audio','')}]
        single_block = len(blocks) == 1
        for i,block in enumerate(blocks,1):
            outer=tk.Frame(body,bg=TOKEN_COLORS['surface'],padx=20,pady=18,highlightbackground='#DFE5F4',highlightthickness=1)
            outer.pack(fill='x',pady=10)
            # Opt-in textbook layout. Existing navigation, data selection, audio,
            # vocabulary, and legacy multi-block layouts remain unchanged.
            layout_mode = str(block.get('layout') or 'auto')
            if layout_mode == 'image_wrap_left' or (single_block and layout_mode == 'auto'):
                from lesson_wrap_layout import render_wrapped_block
                wrapped_text = render_wrapped_block(
                    outer, block, self.media_file(block.get('image', '')),
                    title_size, content_size, title_color, content_color,
                    max(160, int(settings.get('image_width', 350))),
                    max(120, int(settings.get('image_height', 240))))
                if wrapped_text is not None:
                    text_widgets.append(wrapped_text)
                    self.bind_selection_plus(wrapped_text, lambda w: add_vocabulary())
                    wrapped_text.bind('<ButtonRelease-1>',
                        lambda e, w=wrapped_text: selected_text.__setitem__(0, w), add='+')
                    wrapped_text.bind('<KeyRelease>',
                        lambda e, w=wrapped_text: selected_text.__setitem__(0, w), add='+')
                    continue
            # Separate audio buttons are aligned with the title and content, not floating over the block.
            title_audio=block.get('title_audio','')
            content_audio=block.get('content_audio') or block.get('audio','')
            title_value=str(block.get('title') or '').strip()
            content_value=str(block.get('content') or '').strip()
            def play_part(value,relative):
                if relative:
                    file=self.media_file(relative)
                    if file:self.play_learning_audio(file);return
                self._speak(value)

            w=int(getattr(self,'_display_settings',{}).get('image_width',350));h=int(getattr(self,'_display_settings',{}).get('image_height',240))
            picture=tk.Frame(outer,bg='#F0F3FF',width=w+20,height=h+20)
            picture.pack(side='left',padx=(0,18),anchor='n');picture.pack_propagate(False)
            f=self.media_file(block.get('image',''))
            shown=False
            if f:
                try:
                    from animated_media import display_image
                    display_image(picture,f,w,h,bg='#F0F3FF',expand=True)
                    shown=True
                except (ImportError,OSError,ValueError,tk.TclError):
                    pass
            if not shown:
                tk.Label(picture,text=self._theme(theme)[2],font=('Segoe UI Symbol',52),
                         bg='#E8F3EB',fg='#39865B').pack(expand=True)
            # Text instead of Label allows highlighting and selecting vocabulary.
            content=str(block.get('content',''))
            # A larger font needs more vertical space; keep long content scrollable.
            chars_per_line=max(18,int(850/max(content_size,10)*1.6))
            lines=max(4,min(16,sum(max(1,(len(line)+chars_per_line-1)//chars_per_line) for line in content.split('\n'))+1))
            right_min_height=max(h+20,int(title_size*2.4)+int(content_size*1.9*lines)+28)
            right=tk.Frame(outer,bg=TOKEN_COLORS['surface'],height=right_min_height)
            right.pack(side='left',fill='both',expand=True)
            right.pack_propagate(False)
            content_wrap=tk.Frame(right,bg=TOKEN_COLORS['surface'])
            # The pointer in the reference screenshot is at the CENTER of the
            # right-hand content area (roughly X=874, Y=279). Center the actual
            # title/content text on that point, not just the containing frame.
            content_wrap.place(relx=0.5,rely=0.5,anchor='center',relwidth=1.0)
            title_row=tk.Frame(content_wrap,bg=TOKEN_COLORS['surface'])
            title_row.pack(fill='x',pady=(1,6))
            title_label=tk.Label(title_row,text=title_value,
                     font=('Segoe UI',title_size,'bold'),fg=title_color,bg=TOKEN_COLORS['surface'],
                     anchor='center',justify='center',wraplength=480)
            title_label.pack(side='left',fill='x',expand=True)
            title_label.bind('<Configure>',lambda e,w=title_label:w.configure(wraplength=max(100,e.width-16)))
            if title_value:
                tk.Button(title_row,text='🔊',font=font_at(11),bg='#EDF5FF',fg='#2563A8',
                          activebackground='#D9EBFF',bd=0,padx=7,pady=3,cursor='hand2',
                          command=lambda value=title_value,audio=title_audio:play_part(value,audio)
                          ).pack(side='right',padx=(6,0))
            content_row=tk.Frame(content_wrap,bg=TOKEN_COLORS['surface'])
            content_row.pack(fill='x')
            if content_value:
                tk.Button(content_row,text='🔊',font=font_at(11),bg='#EDF5FF',fg='#2563A8',
                          activebackground='#D9EBFF',bd=0,padx=7,pady=3,cursor='hand2',
                          command=lambda value=content_value,audio=content_audio:play_part(value,audio)
                          ).pack(side='right',anchor='n',padx=(6,0))
            text=tk.Text(content_row,height=lines,wrap='word',font=('Segoe UI',content_size),
                         bg=TOKEN_COLORS['surface'],fg=content_color,relief='flat',borderwidth=0,
                         exportselection=False,padx=0,pady=3)
            text.insert('1.0',content)
            text.tag_configure('centered',justify='center')
            text.tag_add('centered','1.0','end')
            text.config(state='disabled')
            text.pack(fill='x')
            text_widgets.append(text)
            self.bind_selection_plus(text,lambda w: add_vocabulary())
            text.bind('<ButtonRelease-1>',lambda e,w=text:selected_text.__setitem__(0,w),add='+')
            text.bind('<KeyRelease>',lambda e,w=text:selected_text.__setitem__(0,w),add='+')
        # The lesson view also shows the current vocabulary source, so edits to vocab.json
        # are visible immediately rather than only in a separate vocabulary page.
        words=self._row('vocab',theme,level)
        if words:
            vocab_panel=tk.Frame(body,bg='#F0F5FF',padx=20,pady=16);vocab_panel.pack(fill='x',pady=(12,8))
            tk.Label(vocab_panel,text='TỪ VỰNG LEVEL NÀY ('+str(len(words))+' từ)',bg='#F0F5FF',fg='#5269E8',font=font_at(13, 'bold')).pack(anchor='w')
            for entry in words:
                label=str(entry.get('word',''))
                example=str(entry.get('example','')).strip()
                tk.Label(vocab_panel,text='• '+label+(' — '+example if example else ''),bg='#F0F5FF',fg='#26345E',font=font_at(11),wraplength=740,justify='left').pack(anchor='w',pady=3)
        actions=tk.Frame(body,bg=body['bg']);actions.pack(fill='x',pady=8)
        for caption,cb in [('✎  Bài tập của bài học',lambda:self.level_quiz(theme,level)),('☆  Từ vựng bài học',lambda:self.level_vocab(theme,level))]:
            tile=tk.Button(actions,text=caption,command=cb,font=font_at(13, 'bold'),bg='#E8EDFF',fg='#354EB5',bd=0,padx=18,pady=18,cursor='hand2');tile.pack(side='left',fill='x',expand=True,padx=8)
        self.button(body,'← Chọn level khác',lambda:self.level_list(theme,'lesson')).pack(anchor='w',pady=12)
    def _v8_open_reading(self,theme,level,item):
        from pygame_embedded_reader import EmbeddedReader, available
        if not available():
            dialogs.showerror('Thiếu thư viện','Cài pygame và Pillow: py -m pip install pygame pillow',parent=self)
            return
        body=self.layout(f'{self._theme(theme)[1]} · Bài đọc tương tác {level}')
        self._level_navigation(body,theme,level,'reading')
        host=tk.Frame(body,bg='#eaf3f9')
        host.pack(fill='both',expand=True)
        media=self.media_file(item.get('image','')) if item.get('image') else None
        def add_reading_vocab(word):
            from tkinter import simpledialog
            word=word.strip()
            if not word:return
            meaning=simpledialog.askstring('Thêm từ vựng',f'Nghĩa của "{word}":',parent=self)
            if meaning is None:return
            self._save_vocab({'word':word,'meaning':meaning},theme,level)
        def play_reading_audio():
            audio=item.get('audio') or item.get('sound') or item.get('audio_file')
            path=self.media_file(audio) if audio else None
            if path:
                from pathlib import Path
                if Path(path).is_file():
                    self.play_learning_audio(path)
                    return
            self._speak(str(item.get('content') or ''))
        reader=EmbeddedReader(host,item,media,external_dock=True,
            speak=self._speak,on_add_vocab=add_reading_vocab,on_play_audio=play_reading_audio)
        reader.pack(fill='both',expand=True)
        reader._expand_reading_button.configure(command=lambda:self._reading_focus(True,origin=reader._expand_reading_button))
        self._v8_active_reader=reader
        for mode,color in getattr(self,'_v8_palette_colors',{}).items():
            reader.set_tool_color(mode,color)
        self.after_idle(self._v8_refresh_dock)

    def level_reading(self, theme, level):
        """Open interactive Pygame reader directly, without the classic reading UI."""
        entries=self._row('reading',theme,level)
        if entries:
            return self._v8_open_reading(theme,level,entries[0])
        body=self.layout(f'{self._theme(theme)[1]} · Bài đọc {level}')
        self.label(body,'Chưa có bài đọc. Vào Quản lý nội dung để tạo.',12).pack(anchor='w',pady=15)
        return
        """Legacy implementation retained below for reference, not executed."""
        heading = 'Đọc' if getattr(self, 'lang', 'en') == 'vi' else 'Reading'
        body = self.layout(f'{self._theme(theme)[1]} · {heading} {level}')
        toolbar = tk.Frame(self._teaching_header, bg='#E8F3EB', padx=5, pady=1, bd=1, relief='solid')
        toolbar.pack(side='right', fill='x', expand=True, padx=(10,0))
        status = tk.StringVar(value='Chọn chữ để đánh dấu, hoặc bật Viết tự do / Vẽ đường')
        state = {'mode': None, 'color': '#FFE66D', 'pen': '#D32F2F', 'font': int(self._display_settings.get('content_size',18)), 'active': None}
        readers, overlays, toolbuttons = [], [], {}
        note_id = [0]
        stroke_history = []  # (canvas, stroke_tag), newest stroke last
        stroke_counter = [0]
        # Reading-specific scroll gestures, independent of external scroll helpers.
        scroll_canvas = self.active_scroll_canvas
        drag_scroll = {'y': None, 'moved': False}
        def wheel_reading(event):
            if not scroll_canvas.winfo_exists(): return
            delta = (-int(event.delta / 120) if getattr(event, 'delta', 0) else
                     -1 if getattr(event, 'num', 0) == 4 else 1)
            if delta: scroll_canvas.yview_scroll(delta * 3, 'units')
            return 'break'
        def drag_begin(event):
            if state['mode'] in ('draw', 'note', 'erase'):
                return
            drag_scroll['y'] = event.y_root
            drag_scroll['moved'] = False
        def drag_move(event):
            if drag_scroll['y'] is None or state['mode'] in ('draw', 'note', 'erase'): return
            diff = event.y_root - drag_scroll['y']
            if abs(diff) >= 3:
                scroll_canvas.yview_scroll(-int(diff / 3), 'units')
                drag_scroll['y'] = event.y_root
                drag_scroll['moved'] = True
                return 'break'
        def drag_end(event):
            drag_scroll['y'] = None
        # Use a custom bindtag on reading content only; toolbar buttons remain clickable.
        scroll_tag = 'ReadingScroll_' + str(id(scroll_canvas))
        self.bind_class(scroll_tag, '<MouseWheel>', wheel_reading)
        self.bind_class(scroll_tag, '<Button-4>', wheel_reading)
        self.bind_class(scroll_tag, '<Button-5>', wheel_reading)
        self.bind_class(scroll_tag, '<ButtonPress-1>', drag_begin)
        self.bind_class(scroll_tag, '<B1-Motion>', drag_move)
        self.bind_class(scroll_tag, '<ButtonRelease-1>', drag_end)
        def enable_scroll(widget):
            try:
                tags = widget.bindtags()
                if scroll_tag not in tags: widget.bindtags((scroll_tag,) + tags)
                for child in widget.winfo_children(): enable_scroll(child)
            except tk.TclError: pass
        def select_range():
            w = state['active']
            if w is None: return None
            try: return w, w.index('sel.first'), w.index('sel.last')
            except tk.TclError:
                status.set('Hãy chọn một từ hoặc câu trong bài đọc'); return None
        def mark(kind):
            selection = select_range()
            if not selection: return
            w, first, last = selection
            if kind == 'highlight':
                tag = 'highlight_' + state['color'].lstrip('#')
                w.tag_configure(tag, background=state['color'])
            elif kind == 'color':
                tag = 'color_' + state['color'].lstrip('#')
                w.tag_configure(tag, foreground=state['color'])
            else: tag = kind
            w.tag_add(tag, first, last)
            status.set('Đã áp dụng hiệu ứng cho đoạn chọn')
        def choose_color():
            result = colorchooser.askcolor(color=state['color'], title='Chọn màu tô / màu chữ', parent=self)
            if result and result[1]:
                state['color'] = result[1]
                toolbuttons['color'].configure(bg=state['color'])
                status.set('Đã chọn màu ' + state['color'])
        def choose_pen():
            result = colorchooser.askcolor(color=state['pen'], title='Chọn màu nét vẽ', parent=self)
            if result and result[1]:
                state['pen'] = result[1]
                toolbuttons['pen'].configure(bg=state['pen'])
        def clear_marks():
            selection = select_range()
            if not selection: return
            w, first, last = selection
            for tag in w.tag_names():
                if tag in ('underline','bold') or tag.startswith(('highlight_', 'color_')):
                    w.tag_remove(tag, first, last)
        def speak():
            w = state['active']
            if w is None: return
            try: phrase = w.get('sel.first','sel.last')
            except tk.TclError: phrase = w.get('1.0','end-1c')
            self._speak(phrase)
        def add_explanation():
            selection = select_range()
            if not selection: return
            w, first, last = selection
            message = simpledialog.askstring('Giải thích','Nhập giải thích:',parent=self)
            if not message or not message.strip(): return
            note_id[0] += 1
            tag = 'teacher_note_' + str(note_id[0])
            w.configure(state='normal')
            w.insert(last, '  📝 ' + message.strip() + ' ', (tag,))
            w.configure(state='disabled')
            w.tag_configure(tag, foreground='#1459A0', background='#E6F1FF')
            w.tag_bind(tag,'<Button-1>',lambda e, m=message: dialogs.showinfo('Giải thích',m,parent=self))
        def remove_one():
            w = state['active']
            if w is None: return
            try: index = w.index('insert')
            except tk.TclError: return
            tags = [t for t in w.tag_names(index) if t.startswith('teacher_note_')]
            if not tags:
                status.set('Đặt con trỏ vào ghi chú cần xóa, hoặc nhấn Xóa đối tượng rồi click'); return
            for tag in tags:
                ranges = w.tag_ranges(tag)
                w.configure(state='normal')
                for k in range(len(ranges)-2,-1,-2): w.delete(ranges[k],ranges[k+1])
                w.configure(state='disabled')
                w.tag_delete(tag)
        def set_mode(mode):
            state['mode'] = None if state['mode'] == mode else mode
            for key in ('note','draw','erase'):
                btn = toolbuttons[key]
                active = state['mode'] == key
                btn.configure(bg='#B6E8C6' if active else 'white', fg='#124A2D' if active else '#285D40', relief='sunken' if active else 'raised', highlightthickness=2 if active else 0, highlightbackground='#29B65B')
            status.set({'note':'✍ Nhấp vị trí bất kỳ trong bài để đặt hộp chữ', 'draw':'✎ Kéo chuột để vẽ đường', 'erase':'⌫ Nhấp vào hộp chữ hoặc nét vẽ để xóa', None:'Đã tắt công cụ'}[state['mode']])
        def zoom(delta):
            state['font'] = max(12,min(36,state['font']+delta))
            for w in readers:
                w.configure(font=('Segoe UI',state['font']))
                w.tag_configure('bold',font=('Segoe UI',state['font'],'bold'))
            status.set('Cỡ chữ: ' + str(state['font']))
        def undo_stroke():
            while stroke_history:
                canvas, tag = stroke_history.pop()
                try:
                    if canvas.winfo_exists() and canvas.find_withtag(tag):
                        canvas.delete(tag)
                        status.set('Đã hoàn tác nét vẽ gần nhất')
                        return
                except tk.TclError:
                    continue
            status.set('Không còn nét vẽ để hoàn tác')
        def clear_everything():
            if not dialogs.askyesno('Xóa toàn bộ ghi chú', 'Xóa tất cả nét vẽ, hộp chữ và đánh dấu trong bài đọc này?', parent=self): return
            for w in readers:
                for tag in list(w.tag_names()):
                    if tag in ('underline', 'bold') or tag.startswith(('highlight_', 'color_', 'teacher_note_')):
                        if tag.startswith('teacher_note_'):
                            spans = w.tag_ranges(tag)
                            w.configure(state='normal')
                            for i in range(len(spans)-2, -1, -2): w.delete(spans[i], spans[i+1])
                            w.configure(state='disabled')
                        else: w.tag_remove(tag, '1.0', 'end')
            for _, c in overlays:
                for item in c.find_all():
                    if 'background' not in c.gettags(item): c.delete(item)
            stroke_history.clear()
            status.set('Đã xóa toàn bộ nét vẽ, ghi chú và đánh dấu')
        def make_button(row, key, label, command):
            btn = tk.Button(row,text=label,command=command,font=font_at(8, 'bold'),bg='white',fg='#285D40',bd=1,relief='raised',padx=3,pady=1,cursor='hand2')
            btn.pack(side='left',padx=2,pady=2)
            toolbuttons[key] = btn
            from main import TeachingTooltip
            hints = {'highlight':('Ctrl+H','Tô màu phần chữ đã chọn.'),'color':('Ctrl+K','Chọn màu tô hoặc màu chữ.'),'foreground':('Ctrl+M','Đổi màu phần chữ đã chọn.'),'underline':('Ctrl+U','Gạch chân phần chữ đã chọn.'),'bold':('Ctrl+B','In đậm phần chữ đã chọn.'),'note':('Ctrl+Q','Click vào bài đọc để đặt hộp chữ.'),'draw':('Ctrl+D','Kéo chuột để vẽ một nét.'),'pen':('Ctrl+P','Chọn màu bút vẽ.'),'undo':('Ctrl+Z','Hoàn tác nét vẽ mới nhất.'),'erase':('Ctrl+E','Click đối tượng muốn xóa.'),'plus':('Ctrl++','Tăng cỡ chữ.'),'minus':('Ctrl+-','Giảm cỡ chữ.') ,'explain':('','Giải thích đoạn chữ đã chọn.'),'clear':('','Xóa đánh dấu của đoạn đã chọn.'),'clearall':('Ctrl+Shift+X','Xóa tất cả nét vẽ, ghi chú và đánh dấu.'),'remove':('','Xóa ghi chú được chọn.'),'sound':('','Đọc phần chữ đã chọn.') }
            shortcut,detail=hints.get(key,('', ''))
            TeachingTooltip(btn,label,shortcut,detail)
        rows = [tk.Frame(toolbar,bg='#E8F3EB') for _ in range(2)]
        for row in rows: row.pack(fill='x')
        specs = [
            ('highlight','🖍 Tô màu',lambda:mark('highlight')),
            ('color','🎨 Chọn màu',choose_color),
            ('foreground','A Màu chữ',lambda:mark('color')),
            ('underline','U̲ Gạch chân',lambda:mark('underline')),
            ('bold','B In đậm',lambda:mark('bold')),
            ('clear','⌫ Xóa dấu',clear_marks),
            ('clearall','🗑 Xóa tất cả',clear_everything),
            ('explain','📝 Giải thích',add_explanation),
            ('note','✍ Viết tự do',lambda:set_mode('note')),
            ('draw','✎ Vẽ đường',lambda:set_mode('draw')),
            ('pen','🎨 Màu bút',choose_pen),
            ('undo','↶ Undo nét vẽ',undo_stroke),
            ('erase','✕ Xóa đối tượng',lambda:set_mode('erase')),
            ('remove','✕ Xóa ghi chú chọn',remove_one),
            ('sound','🔊 Đọc chọn',speak),
            ('plus','A+',lambda:zoom(2)),('minus','A−',lambda:zoom(-2)),
        ]
        for i,(key,label,callback) in enumerate(specs): make_button(rows[0 if i<9 else 1],key,label,callback)
        tk.Label(rows[1],textvariable=status,bg='#E8F3EB',fg='#42614D',font=font_at(9)).pack(side='left',padx=6)
        # Keyboard commands are page-local and replaced at each navigation.
        self._teaching_shortcuts={
            'ctrl+q':lambda:set_mode_with_overlay('note'),
            'ctrl+d':lambda:set_mode_with_overlay('draw'),
            'ctrl+e':lambda:set_mode_with_overlay('erase'),
            'ctrl+k':choose_color,
            'ctrl+p':choose_pen,
            'ctrl+z':undo_stroke,
            'ctrl+shift+x':clear_everything,
            'ctrl+h':lambda:mark('highlight'),
            'ctrl+u':lambda:mark('underline'),
            'ctrl+b':lambda:mark('bold'),
            'ctrl+m':lambda:mark('color'),
            'ctrl+plus':lambda:zoom(2),
            'ctrl+minus':lambda:zoom(-2),
        }
        self._teaching_escape=lambda:set_mode_with_overlay(state['mode']) if state['mode'] else None
        self._attach_toolbar_resize(toolbar,rows[-1])
        # Embedded Pygame-rendered reading surface, with session-only annotations.
        def open_pygame_reader(item):
            try:
                from pygame_embedded_reader import EmbeddedReader, available
                if not available():
                    dialogs.showinfo('Pygame', 'Cài pygame và Pillow: py -m pip install pygame pillow', parent=self)
                    return
                media=self.media_file(item.get('image','')) if item.get('image') else None
                for child in list(body.winfo_children()):child.destroy()
                # The original toolbar belongs to the classic reading mode; hide it
                # while the embedded reader owns the teaching controls.
                if toolbar.winfo_manager()=='pack':toolbar.pack_forget()
                host=tk.Frame(body,bg='#eaf3f9')
                host.pack(fill='both',expand=True)
                def exit_reader():
                    # Returning to the reading screen recreates an empty annotation
                    # session. Nothing is persisted to disk.
                    self.level_reading(theme,level)
                tk.Button(host,text='← Thoát bài đọc tương tác',command=exit_reader,
                          bg='#245c80',fg='white',font=font_at(10, 'bold'),padx=12,pady=7).pack(anchor='w',padx=8,pady=5)
                studio=EmbeddedReader(host,item,media)
                studio.pack(fill='both',expand=True)
            except Exception as exc:
                dialogs.showerror('Bài đọc tương tác',str(exc),parent=self)
        self._level_navigation(body,theme,level,'reading')
        entries = self._row('reading',theme,level)
        if not entries:
            self.label(body,'Chưa có bài đọc. Vào Quản lý nội dung để tạo.',12).pack(anchor='w',pady=15)
        for item in entries:
            card = tk.Frame(body,bg='white',padx=12,pady=12,highlightthickness=1,highlightbackground='#DCE8DE')
            card.pack(fill='x',pady=10)
            title = tk.Label(card,text=item.get('title') or heading,bg='white',fg='#285D40',font=('Segoe UI',int(self._display_settings.get('title_size',20)),'bold'),anchor='w',justify='left')
            title.pack(fill='x',pady=(0,8))
            title.bind('<Configure>',lambda e,w=title:w.configure(wraplength=max(140,e.width-12)))
            tk.Button(card, text='✎ Đọc tương tác Pygame · Trong giao diện · Nét vẽ tạm thời',
                      command=lambda it=item:open_pygame_reader(it), bg='#E9F3FA',fg='#245C80',
                      font=font_at(10, 'bold'),bd=1,padx=12,pady=7,cursor='hand2').pack(anchor='w',pady=(0,9))
            image_path = item.get('image','')
            if image_path:
                media = self.media_file(image_path)
                if media:
                    try:
                        from animated_media import display_image
                        panel=tk.Frame(card,bg='white');panel.pack(fill='x',pady=(0,8))
                        display_image(panel,media,min(360,int(self._display_settings.get('image_width',350))),min(220,int(self._display_settings.get('image_height',240))),bg='white')
                    except (ImportError,OSError,ValueError,tk.TclError): pass
            content = str(item.get('content',''))
            # Text and transparent-like canvas overlay share the same geometry.
            stage = tk.Frame(card,bg='white')
            stage.pack(fill='x')
            text = tk.Text(stage,height=max(5,len(content)//65+3),wrap='word',font=('Segoe UI',state['font']),bg='white',fg='#233C2A',relief='flat',bd=0,padx=6,pady=6,spacing1=3,spacing3=5,exportselection=False,selectbackground='#A8C8F8')
            text.insert('1.0',content);text.configure(state='disabled')
            text.tag_configure('underline',underline=True)
            text.tag_configure('bold',font=('Segoe UI',state['font'],'bold'))
            text.pack(fill='x')
            readers.append(text)
            # Canvas is raised only in draw/note/erase modes, allowing normal text selection otherwise.
            overlay = tk.Canvas(stage,bg='white',highlightthickness=0,bd=0,cursor='crosshair')
            overlay.place(x=0,y=0,relwidth=1,relheight=1)
            tk.Misc.lower(overlay, text)
            overlays.append((text,overlay))
            def sync_overlay(event,w=text,c=overlay):
                c.configure(width=max(1,event.width),height=max(1,event.height))
            text.bind('<Configure>',sync_overlay,add='+')
            def update_overlay(*args):
                for w,c in overlays:
                    if state['mode'] in ('note','draw','erase'): tk.Misc.lift(c, w)
                    else: tk.Misc.lower(c, w)
            # Floating notes are canvas windows with only the entered text visible.
            def put_note(event,c=overlay):
                note = simpledialog.askstring('Viết tự do','Nhập chữ muốn hiển thị:',parent=self)
                if not note or not note.strip(): return
                label = tk.Label(c,text=note.strip(),font=('Segoe UI',state['font']),fg='#1459A0',bg='white',justify='left',wraplength=max(130,int(c.winfo_width()*.6)),cursor='fleur')
                item_id = c.create_window(event.x,event.y,window=label,anchor='nw',tags=('note',))
                # Drag text box to a new location.
                drag={'x':0,'y':0}
                label.bind('<ButtonPress-1>',lambda e:drag.update(x=e.x_root,y=e.y_root))
                def move(e):
                    dx,dy=e.x_root-drag['x'],e.y_root-drag['y']
                    c.move(item_id,dx,dy);drag.update(x=e.x_root,y=e.y_root)
                label.bind('<B1-Motion>',move)
                label.bind('<Double-Button-1>',lambda e:edit_label(label))
                label.bind('<Button-3>',lambda e:c.delete(item_id))
                status.set('Đã đặt hộp chữ; kéo để di chuyển, nhấp đôi để sửa, chuột phải để xóa')
            def edit_label(label):
                new = simpledialog.askstring('Sửa chữ','Nội dung:',initialvalue=label.cget('text'),parent=self)
                if new is not None: label.configure(text=new)
            def start(e,c=overlay):
                if state['mode']=='note': put_note(e,c);return 'break'
                if state['mode']=='erase':
                    near=c.find_overlapping(e.x-7,e.y-7,e.x+7,e.y+7)
                    for obj in reversed(near):
                        tags=c.gettags(obj)
                        if 'background' in tags: continue
                        stroke=next((tag for tag in tags if tag.startswith('stroke_')),None)
                        if stroke:
                            c.delete(stroke)  # Remove the entire drawn stroke, not one segment
                            stroke_history[:]=[(cv,t) for cv,t in stroke_history if not (cv is c and t==stroke)]
                            status.set('Đã xóa nét vẽ được chọn')
                            break
                        if 'note' in tags:
                            widget=c.itemcget(obj,'window')
                            if widget:
                                try:c.nametowidget(widget).destroy()
                                except (KeyError,tk.TclError):pass
                            c.delete(obj)
                            status.set('Đã xóa ghi chú được chọn')
                            break
                    return 'break'
                if state['mode']=='draw':
                    stroke_counter[0]+=1
                    c._stroke_tag='stroke_'+str(stroke_counter[0])
                    c._stroke_started=False
                    c._draw_last=(e.x,e.y)
                    return 'break'
            def motion(e,c=overlay):
                if state['mode']=='draw' and getattr(c,'_draw_last',None):
                    x,y=c._draw_last
                    c.create_line(x,y,e.x,e.y,fill=state['pen'],width=3,capstyle='round',smooth=True,tags=('drawing',c._stroke_tag))
                    if not c._stroke_started:
                        stroke_history.append((c,c._stroke_tag))
                        c._stroke_started=True
                    c._draw_last=(e.x,e.y)
                    return 'break'
            overlay.bind('<Button-1>',start)
            overlay.bind('<B1-Motion>',motion)
            overlay.bind('<ButtonRelease-1>',lambda e,c=overlay:setattr(c,'_draw_last',None))
            def save_reading_selection(widget):
                try: word=widget.get('sel.first','sel.last').strip()
                except tk.TclError: return
                if not word:return
                meaning=simpledialog.askstring('Lưu từ bài đọc',f'Nghĩa hoặc ghi chú cho “{word}”:',parent=self)
                if meaning is None:return
                self.db.save_word_in_source(self.student['id'],self.learning.wordkey(word),meaning.strip(),
                                            'reading',theme,level)
                dialogs.showinfo('Đã lưu','Từ đã được lưu vào Flashcard của bài đọc này.',parent=self)
            self.bind_selection_plus(text,save_reading_selection)
            text.bind('<ButtonRelease-1>',lambda e,w=text:state.__setitem__('active',w),add='+')
            text.bind('<FocusIn>',lambda e,w=text:state.__setitem__('active',w),add='+')
            if state['active'] is None:state['active']=text
            def resize(event,w=text):
                try:
                    count=int(w.count('1.0','end-1c','displaylines')[0])+1
                    height=max(4,count)
                    if int(w.cget('height'))!=height:w.configure(height=height)
                except (tk.TclError,ValueError):pass
            text.bind('<Configure>',resize,add='+')
        original_set_mode=set_mode
        def set_mode_with_overlay(mode):
            original_set_mode(mode)
            for w,c in overlays:
                if state['mode'] in ('note','draw','erase'):
                    # Capture only the visible part of the reading widget. A full
                    # screen grab of a very tall Text raises on Windows/Pillow.
                    # Always raise the drawing canvas, even if capture fails.
                    try:
                        from PIL import ImageGrab, ImageTk
                        w.update_idletasks()
                        x,y=w.winfo_rootx(),w.winfo_rooty()
                        width,height=w.winfo_width(),w.winfo_height()
                        screen_w,screen_h=w.winfo_screenwidth(),w.winfo_screenheight()
                        left,top=max(0,x),max(0,y)
                        right,bottom=min(screen_w,x+width),min(screen_h,y+height)
                        if right<=left or bottom<=top:
                            raise ValueError('Text is outside the visible screen')
                        # Fill unseen portions with white; paste screen pixels at
                        # their actual offset in the full-sized canvas image.
                        from PIL import Image
                        full=Image.new('RGB',(width,height),'white')
                        crop=ImageGrab.grab(bbox=(left,top,right,bottom))
                        full.paste(crop,(left-x,top-y))
                        c._background_image=ImageTk.PhotoImage(full)
                        if not getattr(c,'_background_item',None):
                            c._background_item=c.create_image(0,0,image=c._background_image,anchor='nw',tags=('background',))
                        else:
                            c.itemconfigure(c._background_item,image=c._background_image)
                        c.tag_lower(c._background_item)
                    except Exception:
                        # Drawing must remain usable even without Pillow or
                        # desktop screenshot permissions.
                        if getattr(c,'_background_item',None):
                            c.delete(c._background_item)
                            c._background_item=None
                        status.set('Đã bật bút vẽ; không chụp được nền bài đọc trên thiết bị này')
                    tk.Misc.lift(c, w)
                    c.configure(cursor='pencil' if state['mode']=='draw' else 'crosshair')
                else:
                    tk.Misc.lower(c, w)
                    c._draw_last=None
        # Register all reading widgets, including the canvas overlays and text.
        enable_scroll(body)
        status.set('Con lăn: cuộn bài · Giữ chuột trái và kéo: cuộn · Khi vẽ: dùng con lăn để cuộn')
        # Replace button commands once all canvases exist.
        for key in ('note','draw','erase'):
            toolbuttons[key].configure(command=lambda k=key:set_mode_with_overlay(k))

    def level_vocab(self,theme,level):
        body=self.layout(f'{self._theme(theme)[1]} · Từ vựng {level}')
        entries=self._row('vocab',theme,level)
        self.label(body,f'{len(entries)} từ vựng · Nhấn Lưu để thêm vào Flashcard',12).pack(anchor='w',pady=8)
        for idx,entry in enumerate(entries):
            card=tk.Frame(body,bg=TOKEN_COLORS['surface'],padx=12,pady=9);card.pack(fill='x',pady=4)
            self.label(card,f"{idx+1}.  {entry.get('word','')}",13,True).pack(side='left',padx=(0,20))
            self.label(card,str(entry.get('meaning','')),12).pack(side='left',expand=True,fill='x')
            self.action_button(card,'☆ Lưu',lambda e=entry,t=theme,l=level:self._save_vocab(e,t,l)).pack(side='right')
        if not entries:self.label(body,'Chưa có từ vựng. Thêm tại Quản lý levels hoặc Excel.').pack(anchor='w')
        self.button(body,'→ Bài tập level này',lambda:self.level_quiz(theme,level)).pack(anchor='w',pady=14)
    def _save_vocab(self,item,theme='',level=0):
        self.db.save_word_in_source(self.student['id'],self.learning.wordkey(item['word']),item.get('meaning',''),'lesson',theme,level)
        dialogs.showinfo(t('vocab'),'Đã lưu vào Flashcard của bài học.')
    def level_quiz(self,theme,level):
        """Run the unified v2 quiz; do not invoke the removed level_question renderer."""
        # Filter the complete Level question bank BEFORE limiting to 50.
        # Limiting first can hide all questions belonging to a later Lesson.
        # Ignore a delayed/double-click navigation callback while a quiz is running.
        # It must not show a misleading "no questions" modal over question 6/11.
        if getattr(self, '_lesson_quiz_active', False):
            return
        selected_lesson=getattr(self,'_selected_lesson',None)
        items=list(self.curriculum.get('questions',theme,level))
        if selected_lesson is not None:
            items=[q for q in items if str(q.get('lesson') or '1').strip()==str(selected_lesson)]
        items=sorted(items,key=lambda q:self.learning.mastery(self.student['id'],q.get('answer',''))+random.random()*.15,reverse=True)[:50]
        if not items:
            dialogs.showinfo('Chưa có câu hỏi','Chủ đề / level này chưa có câu hỏi. Hãy nhập dữ liệu qua Quản lý levels hoặc Excel.')
            return
        self._lesson_quiz_active=True
        self._quiz_generation=getattr(self,'_quiz_generation',0)+1
        self._quiz_pending_index=None
        self._quiz_launch_retries=0
        self.s_theme=theme;self.s_level=level;self.s_lesson=selected_lesson;self.s_started=time.monotonic()
        self.s_questions=items;self.s_answers=[];self.s_wrong=[]
        self.s_combo=0;self.s_xp=0;self.s_retry=False;self._quiz_saved=False;self._quiz_timer_started=time.monotonic()
        self.session_quiz(0)

    def lesson_progress_page(self):
        body=self.layout('Tiến độ học tập · Level / Lesson')
        sid=self.student['id'];stats=self.db.lesson_stats(sid)
        for key,title,icon,color in self._themes():
            max_level=self._max_level(key)
            finished=sum(1 for (t,l,n) in stats if t==key)
            self.label(body,f'{icon} {title}: {finished}/{sum(self._lesson_count(key,lv) for lv in range(1,max_level+1))} Lesson đã luyện',14,True).pack(anchor='w',pady=(12,3))
            for level in range(1,max_level+1):
                done=sum((key,level,n) in stats for n in range(1,self._lesson_count(key,level)+1))
                self.label(body,f'Level {level}: {done}/{self._lesson_count(key,level)}  '+ ' '.join('✓' if (key,level,n) in stats else '○' for n in range(1,self._lesson_count(key,level)+1)),10).pack(anchor='w',pady=2)
        self.button(body,'Xem thống kê câu trả lời',self.statistics).pack(anchor='w',pady=20)

    def _refresh_open_theme_selectors(self):
        """Refresh only registered topic selectors after a theme is saved."""
        from tkinter import ttk
        codes = [str(t[0]) for t in self._themes()]
        def visit(parent):
            for widget in parent.winfo_children():
                if isinstance(widget, ttk.Combobox) and getattr(widget, '_theme_selector', False):
                    previous = widget.get()
                    widget.configure(values=codes)
                    if previous not in codes and codes:
                        widget.set(codes[0])
                visit(widget)
        visit(self)

    def manage_themes(self):
        """Edit theme title/icon/color/max levels without changing stable codes."""
        body=self.layout('Quản lý chủ đề · '+('Tiếng Việt' if getattr(self,'lang','en')=='vi' else 'Tiếng Anh'))
        self.label(body,'Thêm / Sửa / Xóa chủ đề. Đổi tên hiển thị sẽ đồng bộ ở Bài học, Level, Lesson, Achievement và Thống kê vì tất cả dùng chung mã chủ đề cố định.',11).pack(anchor='w',pady=7)
        rows=load_themes(self.curriculum.data_dir)
        editor=tk.Frame(body,bg='white',padx=15,pady=12);editor.pack(fill='x',pady=12)
        fields={};selected={'index':None}
        for key,label in [('code','Mã nội bộ (tự cấp khi tạo)'),('title','Tên hiển thị'),('icon','Biểu tượng'),('icon_image','Ảnh icon 256×256 PNG'),('color','Màu nền HEX'),('max_level','Số level tối đa')]:
            r=tk.Frame(editor,bg='white');r.pack(fill='x',pady=4)
            tk.Label(r,text=label,bg='white',width=28,anchor='w').pack(side='left')
            w=tk.Entry(r,font=font_at(11));w.pack(side='left',fill='x',expand=True);fields[key]=w
        # Per-level lesson count; stored on the selected theme only.
        count_row=tk.Frame(editor,bg='white');count_row.pack(fill='x',pady=5)
        tk.Label(count_row,text='Số Lesson của Level',bg='white',width=28,anchor='w').pack(side='left')
        level_choice=tk.StringVar(value='1');count_choice=tk.StringVar(value='10')
        level_box=__import__('tkinter').ttk.Combobox(count_row,textvariable=level_choice,width=8,state='readonly')
        level_box.pack(side='left',padx=(0,8))
        count_box=tk.Spinbox(count_row,from_=1,to=200,textvariable=count_choice,width=7)
        count_box.pack(side='left')
        pending_counts={}
        def sync_count(*_):
            lv=level_choice.get()
            if lv:count_choice.set(str(pending_counts.get(lv,10)))
        level_box.bind('<<ComboboxSelected>>',sync_count)
        def commit_count():
            lv=level_choice.get()
            if lv:
                n=int(count_choice.get())
                if not 1<=n<=200:raise ValueError('Số Lesson phải từ 1 đến 200.')
                pending_counts[lv]=n
        def refresh_level_options():
            try:n=max(1,min(200,int(fields['max_level'].get())))
            except ValueError:n=10
            level_box.configure(values=[str(i) for i in range(1,n+1)])
            if not level_choice.get() or int(level_choice.get())>n:level_choice.set('1')
            sync_count()
        tk.Button(count_row,text='Áp dụng số Lesson',command=lambda: apply_count(),bg='#EAF2FF',bd=0,padx=8).pack(side='left',padx=8)
        def apply_count():
            try:commit_count()
            except ValueError as exc:messagebox.showerror('Số Lesson',str(exc))
        fields['max_level'].bind('<FocusOut>',lambda e:refresh_level_options())
        def choose_icon():
            """Normalize uploaded theme icons to a transparent 256x256 PNG."""
            source=filedialog.askopenfilename(
                title='Chọn ảnh icon chủ đề',
                filetypes=[('Ảnh PNG/JPG/JPEG/WebP/GIF','*.png *.jpg *.jpeg *.webp *.gif')])
            if not source:
                return
            try:
                from PIL import Image, ImageOps
                import uuid
                destdir=self.curriculum.data_dir/'icons'
                destdir.mkdir(parents=True,exist_ok=True)
                target=destdir/(uuid.uuid4().hex[:12]+'.png')
                with Image.open(source) as original:
                    original.seek(0)
                    image=ImageOps.exif_transpose(original).convert('RGBA')
                    image.thumbnail((256,256),Image.Resampling.LANCZOS)
                    canvas=Image.new('RGBA',(256,256),(0,0,0,0))
                    canvas.alpha_composite(image,((256-image.width)//2,(256-image.height)//2))
                    canvas.save(target,format='PNG',optimize=True)
                fields['icon_image'].delete(0,'end')
                fields['icon_image'].insert(0,'icons/'+target.name)
            except (OSError,ValueError,ImportError) as exc:
                messagebox.showerror('Không xử lý được ảnh',
                    f'Không thể chuẩn hóa icon về 256×256 PNG.\n{exc}')
        tk.Button(editor,text='🖼 Chọn ảnh (tự chuẩn hóa 256×256)',command=choose_icon,
                  bg='#EAF2FF',fg='#285D80',bd=0,padx=12,pady=7).pack(anchor='e',pady=4)
        def set_field(k,value):
            w=fields[k];w.configure(state='normal');w.delete(0,'end');w.insert(0,str(value))
        def choose(index):
            selected['index']=index
            for key in fields:set_field(key,rows[index].get(key,''))
            pending_counts.clear();pending_counts.update({str(k):int(v) for k,v in rows[index].get('lesson_counts',{}).items()})
            refresh_level_options()
            fields['code'].configure(state='disabled')
        def new():
            selected['index']=None
            for key in fields:set_field(key,10 if key=='max_level' else '#E8F3FF' if key=='color' else '📘' if key=='icon' else '')
            pending_counts.clear();refresh_level_options()
            fields['code'].configure(state='disabled')
        def save():
            index=selected['index']
            try:
                obj={key:w.get().strip() for key,w in fields.items()}
                if index is not None:obj['code']=rows[index]['code']
                commit_count()
                obj['lesson_counts']={k:v for k,v in pending_counts.items() if int(k)<=int(obj['max_level']) and v!=10}
                obj['max_level']=int(obj['max_level'])
                if not (obj['color'].startswith('#') and len(obj['color'])==7):raise ValueError('Màu cần dạng #RRGGBB')
                changed=[dict(r) for r in rows]
                if any(r['title'].casefold()==obj['title'].casefold() and j!=index for j,r in enumerate(rows)):
                    raise ValueError('Tên chủ đề đã tồn tại.')
                if index is None:
                    if not obj['title']:raise ValueError('Nhập tên chủ đề.')
                    # Use a new stable internal code, never a display title.
                    used={str(r['code']) for r in rows}
                    serial=1
                    while f'theme_{serial:03d}' in used:serial+=1
                    obj['code']=f'theme_{serial:03d}'
                    changed.append(obj)
                else:changed[index]=obj
                save_themes(self.curriculum.data_dir,changed)
                self.curriculum.reload();self._refresh_open_theme_selectors();self.manage_themes()
            except (ValueError,OSError) as e:messagebox.showerror('Không lưu được',str(e))
        def remove(index):
            code=rows[index]['code']
            in_use=sum(1 for kind in ('lessons','questions','vocab','blocks','reading') for r in self._levels(kind) if r.get('theme')==code)
            # A removed theme must not orphan history, reward claims or customized quests.
            history=self.db.conn.execute('SELECT COUNT(*) FROM completion_events WHERE activity_id LIKE ?',('%'+code+'%',)).fetchone()[0]
            history+=self.db.conn.execute('SELECT COUNT(*) FROM lesson_progress WHERE topic_id LIKE ?',('%'+code+'%',)).fetchone()[0]
            history+=self.db.conn.execute('SELECT COUNT(*) FROM vocabulary_sources WHERE theme=?',(code,)).fetchone()[0]
            from main import load_level_achievements
            quests=sum(str(q.get('theme'))==code for q in load_level_achievements())
            if in_use or history or quests:
                messagebox.showwarning('Không thể xóa chủ đề',f'Chủ đề còn {in_use} dòng nội dung, {history} bản ghi lịch sử hoặc {quests} nhiệm vụ. Để giữ an toàn dữ liệu, hãy chuyển dữ liệu liên quan trước khi xóa.')
                return
            if len(rows)==1:messagebox.showwarning('Không thể xóa','Cần ít nhất một chủ đề.');return
            if messagebox.askyesno('Xóa chủ đề',f'Xóa chủ đề {code}?'):
                save_themes(self.curriculum.data_dir,[r for j,r in enumerate(rows) if j!=index]);self.curriculum.reload();self.manage_themes()
        actions=tk.Frame(editor,bg='white');actions.pack(anchor='w',pady=10)
        self.action_button(actions,'＋ Chủ đề mới',new).pack(side='left',padx=4)
        self.action_button(actions,'Lưu chủ đề',save).pack(side='left',padx=4)
        new()
        for i,r in enumerate(rows):
            line=tk.Frame(body,bg='white',padx=10,pady=7);line.pack(fill='x',pady=3)
            icon_preview=self._theme_icon(line,r['code'],38,'white',r.get('icon','📘'));icon_preview.pack(side='left',padx=(0,8))
            self.label(line,f"{r['title']}  ·  mã: {r['code']}  ·  {r['max_level']} levels · Lesson tùy chỉnh",11).pack(side='left',fill='x',expand=True)
            self.button(line,'Sửa',lambda j=i:choose(j)).pack(side='right',padx=3)
            self.button(line,'Xóa',lambda j=i:remove(j)).pack(side='right',padx=3)
        self.button(body,'← Quản lý nội dung',self.manage_levels).pack(anchor='w',pady=14)

    def _display_name(self, kind, theme, level, lesson=None):
        return display_name(self.curriculum.data_dir, kind, theme, level, lesson)

    def _lesson_breadcrumb(self, theme, level, lesson):
        return breadcrumb(self.curriculum.data_dir, theme, level, lesson)

    def edit_display_names(self):
        body=self.layout('Quản lý nội dung · Đổi tên Level / Lesson')
        self.label(body,'Chỉ thay đổi tên hiển thị. Mã chủ đề, số Level/Lesson và dữ liệu bài học giữ nguyên.',11).pack(anchor='w',pady=10)
        path=Path(self.curriculum.data_dir)/'content_library'/'display_names.json'
        try: names=json.loads(path.read_text(encoding='utf-8'))
        except (OSError,ValueError): names={}
        themes=load_themes(self.curriculum.data_dir)
        choices=[(r['code'],r['title']) for r in themes]
        if not choices:return
        from tkinter import ttk
        theme=tk.StringVar(value=choices[0][0]);level=tk.IntVar(value=1);lesson=tk.IntVar(value=1)
        kind=tk.StringVar(value='level');name=tk.StringVar()
        ttk.Label(body,text='Chủ đề').pack(anchor='w')
        combo=ttk.Combobox(body,values=[f'{code} · {title}' for code,title in choices],state='readonly',width=44)
        combo.current(0);combo.pack(anchor='w',pady=5)
        ttk.Label(body,text='Đổi tên').pack(anchor='w')
        ttk.Radiobutton(body,text='Level',variable=kind,value='level').pack(anchor='w')
        ttk.Radiobutton(body,text='Lesson',variable=kind,value='lesson').pack(anchor='w')
        ttk.Label(body,text='Số Level').pack(anchor='w')
        level_box=ttk.Spinbox(body,from_=1,to=self._max_level(theme.get()),textvariable=level,width=8);level_box.pack(anchor='w')
        ttk.Label(body,text='Số Lesson (1–10, khi đổi tên Lesson)').pack(anchor='w')
        ttk.Spinbox(body,from_=1,to=10,textvariable=lesson,width=8).pack(anchor='w')
        ttk.Label(body,text='Tên hiển thị mới').pack(anchor='w',pady=(12,0))
        ttk.Entry(body,textvariable=name,width=55).pack(anchor='w',pady=5)
        def selected():
            code=choices[combo.current()][0];return code
        def refresh(*_):
            try:
                code=selected();lv=int(level.get());ls=int(lesson.get())
                name.set(self._display_name(kind.get(),code,lv,ls))
            except (ValueError,tk.TclError,IndexError):pass
        def save():
            try:
                code=selected();lv=int(level.get());ls=int(lesson.get())
                if not 1<=lv<=self._max_level(code) or not 1<=ls<=10:raise ValueError('Số Level/Lesson không hợp lệ.')
                key=f'{code}:{lv}' if kind.get()=='level' else f'{code}:{lv}:{ls}'
                default=f'Level {lv}' if kind.get()=='level' else f'Lesson {ls}'
                value=name.get().strip()
                if not value:raise ValueError('Tên không được để trống.')
                names.setdefault(kind.get(),{})
                if value==default:names[kind.get()].pop(key,None)
                else:names[kind.get()][key]=value
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(json.dumps(names,ensure_ascii=False,indent=2),encoding='utf-8')
                messagebox.showinfo('Đã lưu','Tên hiển thị đã được cập nhật.')
            except (ValueError,OSError) as exc:messagebox.showerror('Không lưu được',str(exc))
        combo.bind('<<ComboboxSelected>>',lambda e:(theme.set(selected()),level_box.configure(to=self._max_level(theme.get())),refresh()))
        for var in (kind,level,lesson):var.trace_add('write',refresh)
        refresh()
        self.action_button(body,'Lưu tên hiển thị',save).pack(anchor='w',pady=12)
        self.button(body,'← Quản lý nội dung',self.manage_levels).pack(anchor='w',pady=8)

    def manage_levels(self):
        body=self.layout('Thêm bài học · Bài tập · Từ vựng')
        self.label(body,'Chỉnh trực tiếp một mục hoặc nhập toàn bộ bằng Excel.',12).pack(anchor='w',pady=10)
        self.button(body,'✏ Đổi tên hiển thị Level / Lesson',self.edit_display_names).pack(anchor='w',fill='x',pady=7)
        self.button(body,'🎨 Chỉnh tên và ảnh icon 4 mục chọn bài học',self.manage_mode_cards).pack(anchor='w',fill='x',pady=7)
        self.button(body,'⚙ Quản lý chủ đề và số level của môn này',self.manage_themes).pack(anchor='w',fill='x',pady=7)
        self.button(body,'📝 Quản lý ngân hàng câu hỏi kiểm tra',self.exam_bank_editor).pack(anchor='w',fill='x',pady=7)
        self.button(body,'🏅 Thêm / sửa / xóa Achievement',self.edit_level_achievements_page).pack(anchor='w',fill='x',pady=7)
        for kind,title in [('lessons','＋ Thêm/sửa Bài học'),('questions','＋ Thêm/sửa Bài tập'),('vocab','＋ Thêm/sửa Từ vựng'),('blocks','＋ Thêm/sửa Khối nội dung bài học'),('reading','＋ Thêm/sửa Bài đọc / Reading')]:
            self.button(body,title,lambda k=kind:self.level_editor(k)).pack(anchor='w',fill='x',pady=7)
        if getattr(self,'lang','en')=='vi':
            self.button(body,'⬆ Nhập vocab.json Tiếng Việt',self.import_vietnamese_json_ui).pack(anchor='w',fill='x',pady=7)
        self.button(body,'⬆ Nhập file Excel levels',self.level_import_ui).pack(anchor='w',fill='x',pady=7)
        self.button(body,'⬇ Xuất file Excel levels',self.level_export_ui).pack(anchor='w',fill='x',pady=7)
        self.button(body,'📁 Thêm hình / âm thanh',self.add_media_ui).pack(anchor='w',fill='x',pady=7)
        self.button(body,'← Về quản lý cũ',self.manage_page).pack(anchor='w',pady=14)
    def import_vietnamese_json_ui(self):
        from vocab_sync import import_vietnamese_vocab
        source=filedialog.askopenfilename(title='Chọn vocab.json Tiếng Việt',filetypes=[('JSON','*.json')])
        if not source:return
        try:
            count,location=import_vietnamese_vocab(source,self.data_dir/'vi')
            self._setup_language()
        except (OSError,ValueError) as error:
            messagebox.showerror('Không nhập được từ vựng',str(error));return
        messagebox.showinfo('Đã cập nhật',f'Đã nhập {count} từ Tiếng Việt.\nDữ liệu: {location}\nDữ liệu cũ đã được sao lưu.')
        self.manage_levels()

    def level_import_ui(self):
        p=filedialog.askopenfilename(filetypes=[('Excel','*.xlsx')])
        if not p:return
        try:counts=import_levels(p,self.curriculum.data_dir)
        except Exception as e:messagebox.showerror('Không nhập được',str(e));return
        self._setup_language();messagebox.showinfo('Đã nhập',str(counts));self.manage_levels()
    def level_export_ui(self):
        p=filedialog.asksaveasfilename(defaultextension='.xlsx',filetypes=[('Excel','*.xlsx')],initialfile='Noi_dung_'+getattr(self,'lang','en')+'_levels.xlsx')
        if p:
            try:export_levels(p,self.curriculum.data_dir);messagebox.showinfo('Đã xuất',p)
            except Exception as e:messagebox.showerror('Không xuất được',str(e))
    def _content_table(self, parent, records, columns, edit, delete, start_number=1, *, duplicate=None):
        """Presentation-only grid; original row indices drive existing actions."""
        from tkinter import ttk
        shell = tk.Frame(parent, bg=parent['bg'], bd=0, highlightthickness=0)
        shell.pack(fill='x', pady=(5, 8))
        headings = ['STT'] + [title for title, _ in columns]
        keys = [f'c{i}' for i in range(len(headings))]
        tree = ttk.Treeview(shell, columns=keys, show='headings', height=max(1, len(records)))
        from tkinter import font as tkfont
        body_font = tkfont.Font(family='Segoe UI', size=10)
        header_font = tkfont.Font(family='Segoe UI', size=10, weight='bold')
        # Fit each column to its heading and visible cell contents only.
        display_rows = [
            (number, original_index,
             [number] + [str(value(obj)).replace('\n', ' ')[:160] for _, value in columns])
            for number, (original_index, obj) in enumerate(records, start_number)
        ]
        for i, (key, heading) in enumerate(zip(keys, headings)):
            widest = max([header_font.measure(heading)] +
                         [body_font.measure(str(row_values[i])) for _, _, row_values in display_rows])
            width = max(48 if i == 0 else 64, min(widest + 24, 70 if i == 0 else 420))
            tree.heading(key, text=heading)
            tree.column(key, width=width, minwidth=width, stretch=False, anchor='center')
        style = ttk.Style(tree)
        style.configure('ContentGrid.Treeview', rowheight=31, font=font_at(10),
                        background=TOKEN_COLORS['surface'], fieldbackground=TOKEN_COLORS['surface'], foreground='#243D50', borderwidth=0, relief='flat')
        style.configure('ContentGrid.Treeview.Heading', font=font_at(10, 'bold'),
                        background='#4E91C8', foreground='#172C3A', borderwidth=0, relief='flat')
        tree.configure(style='ContentGrid.Treeview', selectmode='browse', takefocus=True)
        for number, original_index, values in display_rows:
            tree.insert('', 'end', iid=str(original_index), values=values,
                        tags=('even' if number % 2 == 0 else 'odd',))
        tree.tag_configure('even', background='#E4F0FB')
        tree.tag_configure('odd', background=TOKEN_COLORS['surface'])
        # No embedded scrollbars or visible outer frame; the parent page handles scrolling.
        tree.pack(fill='x', expand=True)
        def activate(event):
            item = tree.identify_row(event.y)
            if not item: return
            index = int(item)
            edit(index)
        tree.bind('<Double-1>', activate)
        def keyboard_edit(event):
            selected = tree.selection()
            if selected: edit(int(selected[0]))
        tree.bind('<Return>', keyboard_edit)
        actions = tk.Frame(parent, bg=parent['bg'])
        actions.pack(fill='x', pady=(0, 4))
        tk.Label(actions, text='Chọn một dòng rồi bấm Sửa hoặc Xóa (nhấp đúp dòng để sửa).',
                 bg=parent['bg'], fg='#385B70').pack(side='left')
        def selected_action(callback):
            selected = tree.selection()
            if selected: callback(int(selected[0]))
        tk.Button(actions, text='Sửa dòng chọn', command=lambda: selected_action(edit)).pack(side='right', padx=3)
        tk.Button(actions, text='Xóa dòng chọn', command=lambda: selected_action(delete)).pack(side='right', padx=3)
        if duplicate is not None:
            tk.Button(actions,text='Nhân bản',command=lambda:selected_action(duplicate)).pack(side='right',padx=3)
        return tree

    def question_editor(self):
        """Type-aware editor; persists the existing QUESTION_KEYS JSON schema."""
        from tkinter import ttk
        from studio_list import copy_question, find_rows, remove_at
        from ui_components import Toast
        from safe_storage import commit_json

        preserved_form = getattr(self, '_question_editor_form_state', None)
        body = self.layout('Thêm / sửa bài tập')
        self.label(body, 'Chọn dạng câu hỏi để hiển thị các ô nhập phù hợp. Dữ liệu cũ vẫn được giữ nguyên.', 11).pack(anchor='w', pady=(0, 12))
        panel = tk.Frame(body, bg='white', padx=16, pady=14, highlightthickness=1, highlightbackground='#DCE8DE')
        panel.pack(fill='x', pady=6)
        controls = {}
        selected = {'index': None, 'id': None, 'seed': {}}
        pending_layout = {'value': {}}
        dynamic = tk.Frame(panel, bg='white')
        sample_hints = {'choice':'Ví dụ: A. Apple | B. Banana | C. Cat | D. Dog. Chọn đáp án đúng bên dưới.', 'picture_choice':'Ví dụ: A. Cat, B. Dog, C. Bird, D. Fish. Ảnh minh họa nằm ở phần tệp đính kèm.', 'listening_choice':'Ví dụ: A. Hello, B. Goodbye, C. Thanks, D. Sorry. Tải tệp âm thanh ở dưới.', 'true_false':'Ví dụ: The sky is blue. Đáp án: Đúng.', 'fill':'Ví dụ: She ___ a student. Đáp án: is.', 'listening_fill':'Ví dụ: Listen and complete: I ___ happy. Đáp án: am.', 'order':'Ví dụ: Em | đi | đến trường | mỗi ngày. Mỗi thẻ có thể là từ, cụm từ hoặc cả câu.', 'matching':'Ví dụ: cat = con mèo; dog = con chó.', 'error':'Ví dụ: He go to school. Đáp án: go → goes.'}
        def hint(parent, message):
            icon = tk.Label(parent, text='ⓘ', fg='#357A60', bg='white', cursor='question_arrow', font=font_at(12, 'bold'))
            icon.pack(side='left', padx=(6, 0))
            popup = {'window': None}
            def show(event):
                if popup['window'] is not None: return
                tip = tk.Toplevel(icon); tip.wm_overrideredirect(True)
                tip.configure(bg='#D3E6D7')
                tk.Label(tip, text=message, bg='#F4FAF4', fg='#285D40', justify='left', wraplength=330, padx=10, pady=8, font=font_at(10)).pack(padx=1, pady=1)
                # Keep the tooltip inside the application's visible client area.
                tip.update_idletasks()
                root = icon.winfo_toplevel()
                left, top = root.winfo_rootx(), root.winfo_rooty()
                right = left + root.winfo_width()
                bottom = top + root.winfo_height()
                screen_right, screen_bottom = icon.winfo_screenwidth(), icon.winfo_screenheight()
                width, height = tip.winfo_reqwidth(), tip.winfo_reqheight()
                x = icon.winfo_rootx() + 18
                y = icon.winfo_rooty() + icon.winfo_height() + 5
                x = max(left + 6, min(x, min(right - 6, screen_right - 6) - width))
                if y + height > min(bottom - 6, screen_bottom - 6):
                    y = icon.winfo_rooty() - height - 5
                y = max(top + 6, min(y, min(bottom - 6, screen_bottom - 6) - height))
                tip.geometry(f'+{int(x)}+{int(y)}')
                popup['window'] = tip
            def hide(event):
                tip=popup.pop('window', None)
                if tip is not None:
                    try: tip.destroy()
                    except tk.TclError: pass
                popup['window']=None
            icon.bind('<Enter>', show); icon.bind('<Leave>', hide)
            return icon
        entries = {}
        answer_var = tk.StringVar(master=panel)
        kind_var = tk.StringVar(master=panel, value='choice')

        def line(title, widget_type='entry', values=None, parent=panel, height=3, tooltip=None):
            row = tk.Frame(parent, bg='white')
            row.pack(fill='x', pady=4)
            tk.Label(row, text=title, bg='white', fg='#285D40', width=23, anchor='w', font=font_at(10)).pack(side='left')
            if widget_type == 'combo':
                widget = ttk.Combobox(row, values=values or [], state='readonly', font=font_at(11))
            elif widget_type == 'text':
                widget = tk.Text(row, height=height, font=font_at(11), wrap='word')
            else:
                widget = tk.Entry(row, font=font_at(11))
            widget.pack(side='left', fill='x', expand=True)
            if tooltip: hint(row, tooltip)
            return widget

        def get(widget):
            return widget.get('1.0', 'end-1c').strip() if isinstance(widget, tk.Text) else widget.get().strip()

        def put(widget, value):
            value = '' if value is None else str(value)
            if isinstance(widget, tk.Text):
                widget.delete('1.0', 'end'); widget.insert('1.0', value)
            elif isinstance(widget, ttk.Combobox):
                widget.set(value)
            else:
                widget.delete(0, 'end'); widget.insert(0, value)

        controls['theme'] = line('Chủ đề', 'combo', [t[0] for t in self._themes()])
        controls['theme']._theme_selector = True
        controls['theme'].set(self._themes()[0][0])
        def refresh_editor_themes(event=None):
            controls['theme'].configure(values=[t[0] for t in self._themes()])
        controls['theme'].configure(postcommand=refresh_editor_themes)
        controls['theme'].bind('<FocusIn>', refresh_editor_themes)
        # Visible names are separate from the stable numeric IDs stored in JSON.
        controls['level'] = line('Level', 'combo')
        controls['lesson'] = line('Lesson', 'combo')
        question_location = {'level': {}, 'lesson': {}}

        def refresh_question_location(event=None, level_id=None, lesson_id=None):
            theme = get(controls['theme'])
            previous_level = level_id if level_id is not None else question_location['level'].get(get(controls['level']))
            previous_lesson = lesson_id if lesson_id is not None else question_location['lesson'].get(get(controls['lesson']))
            level_count = self._max_level(theme)
            level_ids = list(range(1, level_count + 1))
            # Preserve references to existing questions even if the theme configuration changed.
            level_ids = sorted(set(level_ids) | {int(q['level']) for q in self._levels('questions')
                if str(q.get('theme')) == theme and str(q.get('level', '')).isdigit()})
            level_labels = {f'{n} · {self._display_name("level", theme, n)}': n for n in level_ids}
            question_location['level'] = level_labels
            controls['level'].configure(values=list(level_labels))
            chosen_level = previous_level if previous_level in level_ids else (level_ids[0] if level_ids else None)
            put(controls['level'], next((label for label, n in level_labels.items() if n == chosen_level), ''))
            lesson_ids = list(range(1, self._lesson_count(theme,chosen_level)+1))
            lesson_ids = sorted(set(lesson_ids) | {int(q['lesson']) for q in self._levels('questions')
                if str(q.get('theme')) == theme and str(q.get('level')) == str(chosen_level)
                and str(q.get('lesson', '')).isdigit()})
            lesson_labels = {f'{n} · {self._display_name("lesson", theme, chosen_level, n)}': n for n in lesson_ids}
            question_location['lesson'] = lesson_labels
            controls['lesson'].configure(values=list(lesson_labels))
            chosen_lesson = previous_lesson if previous_lesson in lesson_ids else 1
            put(controls['lesson'], next((label for label, n in lesson_labels.items() if n == chosen_lesson), ''))

        controls['theme'].bind('<<ComboboxSelected>>', lambda e: refresh_question_location(level_id=1, lesson_id=1))
        controls['level'].bind('<<ComboboxSelected>>', lambda e: refresh_question_location(lesson_id=1))
        refresh_question_location(level_id=1, lesson_id=1)
        if preserved_form:
            desired_theme = preserved_form.get('theme')
            if desired_theme in [t[0] for t in self._themes()]:
                put(controls['theme'], desired_theme)
            refresh_question_location(level_id=preserved_form.get('level'),
                                      lesson_id=preserved_form.get('lesson'))
        controls['id'] = line('Mã câu hỏi')
        type_widget = line('Dạng câu hỏi', 'combo', [QUESTION_LABELS.get(t,t)+'  ('+t+')' for t in QUESTION_TYPES])
        type_names = [QUESTION_LABELS.get(t,t)+'  ('+t+')' for t in QUESTION_TYPES]
        type_widget.set(type_names[0])
        if preserved_form and preserved_form.get('type') in QUESTION_TYPES:
            type_widget.set(type_names[QUESTION_TYPES.index(preserved_form['type'])])
            kind_var.set(preserved_form['type'])
        controls['prompt'] = line('Nội dung câu hỏi', 'text', height=3)
        form_status=tk.StringVar()
        tk.Label(panel,textvariable=form_status,bg='white',fg='#774710',
                 anchor='w',wraplength=690).pack(fill='x')

        def check_form(_event=None):
            issues=[]
            if not get(controls['id']).strip():
                issues.append('Cần mã câu hỏi.')
            if kind_var.get()!='picture_missing_letters' and not get(controls['prompt']).strip():
                issues.append('Cần nội dung câu hỏi.')
            form_status.set(' '.join(issues))
        for key in ('id','prompt'):
            controls[key].bind('<KeyRelease>',check_form,add='+')
        dynamic.pack(fill='x', pady=(8, 5))

        def store_media(source):
            """Reuse identical content; never overwrite an unrelated same-name file."""
            import hashlib
            from shutil import copy2
            source = Path(source)
            folder = self.curriculum.data_dir / 'content_library' / 'media'
            folder.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256(source.read_bytes()).hexdigest()[:12]
            target = folder / source.name
            if target.exists() and source.resolve() != target.resolve():
                if hashlib.sha256(target.read_bytes()).hexdigest() != hashlib.sha256(source.read_bytes()).hexdigest():
                    target = folder / (source.stem + '_' + digest + source.suffix.lower())
            if not target.exists():
                if source.resolve() != target.resolve(): copy2(source, target)
            return 'media/' + target.name

        def media_picker(field, types):
            source = filedialog.askopenfilename(title='Chọn tệp', filetypes=types)
            if not source: return
            try: put(entries[field], store_media(source))
            except OSError as exc: messagebox.showerror('Không import được', str(exc))

        def media_field(field, title, types):
            row = tk.Frame(dynamic, bg='white'); row.pack(fill='x', pady=4)
            tk.Label(row, text=title, bg='white', fg='#285D40', width=23, anchor='w').pack(side='left')
            w = tk.Entry(row, font=font_at(11)); w.pack(side='left', fill='x', expand=True)
            entries[field] = w
            tk.Button(row, text='📁 Import file nghe' if field=='audio' else '📁 Chọn ảnh', bg='#E2F0E2', fg='#285D40', bd=0,
                      command=lambda:media_picker(field, types)).pack(side='left', padx=7)
            if field=='audio':
                hint(row, 'Chọn MP3, WAV hoặc OGG. Tệp được sao chép vào content_library/media và liên kết với câu hỏi.')
                tk.Button(row, text='▶ Nghe thử', bg='#EDF5FF', fg='#285D80', bd=0, command=lambda:preview_audio()).pack(side='left', padx=4)

        def preview_audio():
            path = get(entries['audio']) if 'audio' in entries else ''
            if not path:
                messagebox.showinfo('Nghe thử', 'Hãy import file nghe trước.'); return
            audio_path = self.media_file(path)
            if audio_path is None or not Path(audio_path).is_file():
                messagebox.showwarning('Thiếu file', f'Không tìm thấy: {audio_path}'); return
            try:
                if hasattr(self, 'play_learning_audio'): self.play_learning_audio(audio_path)
                else:
                    import os
                    os.startfile(str(audio_path))
            except Exception as exc: messagebox.showerror('Không phát được', str(exc))

        def rebuild(event=None, existing=None):
            for child in dynamic.winfo_children(): child.destroy()
            entries.clear()
            typ = kind_var.get()
            data = existing or {}
            opts = data.get('options') or []
            if isinstance(opts, str): opts = [x.strip() for x in opts.split('|') if x.strip()]
            if typ in NEW_TYPES:
                from new_exercise_editors import build
                entries['_collect_new'] = build(dynamic, typ, data, store_media, self.media_file)
                if typ == 'dropdown_fill_blank':
                    entries['_collect_new'].prompt_getter = lambda: get(controls['prompt'])
            elif typ == 'matching':
                from matching_widget import parse_pairs, IMAGE_PREFIX
                pairs = parse_pairs(opts)
                tk.Label(dynamic, text='MATCHING · NỐI CHỮ / HÌNH / HỖN HỢP', bg='white', fg='#39865B',
                         font=font_at(11, 'bold')).pack(anchor='w', pady=(4, 5))
                mode_row=tk.Frame(dynamic,bg='white');mode_row.pack(fill='x',pady=5)
                tk.Label(mode_row,text='Kiểu nối',bg='white',fg='#285D40',width=23,anchor='w').pack(side='left')
                modes=['Chữ ↔ Chữ','Hình ↔ Hình','Hình ↔ Chữ','Chữ ↔ Hình']
                mode=ttk.Combobox(mode_row,values=modes,state='readonly',font=font_at(11))
                mode.pack(side='left',fill='x',expand=True)
                saved_mode=data.get('matching_mode','')
                if saved_mode not in modes and pairs:
                    a,b=pairs[0]
                    saved_mode=('Hình ↔ Hình' if a.startswith(IMAGE_PREFIX) and b.startswith(IMAGE_PREFIX) else 'Hình ↔ Chữ' if a.startswith(IMAGE_PREFIX) else 'Chữ ↔ Hình' if b.startswith(IMAGE_PREFIX) else 'Chữ ↔ Chữ')
                mode.set(saved_mode if saved_mode in modes else modes[0]);entries['matching_mode']=mode
                rows_container=tk.Frame(dynamic,bg='white');rows_container.pack(fill='x')
                def render_matching_rows(event=None):
                    old=[]
                    for i in range(max(4,len(pairs))):
                        a=entries.get(f'left_{i}');b=entries.get(f'right_{i}')
                        old.append((get(a),get(b)) if a is not None and b is not None else (pairs[i] if i<len(pairs) else ('','')))
                    for child in rows_container.winfo_children():child.destroy()
                    for key in list(entries):
                        if key.startswith(('left_','right_')):del entries[key]
                    left_img=mode.get().startswith('Hình');right_img=mode.get().endswith('Hình')
                    for i,(left_val,right_val) in enumerate(old):
                        # Two full-width rows per pair: file buttons never get clipped
                        # by narrow editor windows or large display scaling.
                        group=tk.Frame(rows_container,bg='#F6FAF6',padx=9,pady=7,
                                       highlightthickness=1,highlightbackground='#DCE8DE')
                        group.pack(fill='x',pady=5)
                        tk.Label(group,text=f'ĐÁP ÁN CHUẨN {i+1}  ✓',bg='#F6FAF6',fg='#285D40',
                                 font=font_at(10, 'bold')).pack(anchor='w',pady=(0,4))
                        for side,initial,is_image in (('left',left_val,left_img),('right',right_val,right_img)):
                            field_row=tk.Frame(group,bg='#F6FAF6');field_row.pack(fill='x',pady=2)
                            tk.Label(field_row,text='Bên trái' if side=='left' else 'Bên phải',
                                     bg='#F6FAF6',fg='#285D40',width=10,anchor='w').pack(side='left')
                            # Pack the fixed-width button first so it remains visible.
                            if is_image:
                                def choose_image(widget_side=side, row_index=i):
                                    path=filedialog.askopenfilename(title='Chọn hình ghép cặp',
                                        filetypes=[('Ảnh','*.png *.jpg *.jpeg *.gif *.webp')])
                                    if path:
                                        try:
                                            widget=entries.get(f'{widget_side}_{row_index}')
                                            if widget is not None and widget.winfo_exists():
                                                put(widget,IMAGE_PREFIX+store_media(path))
                                        except OSError as exc:messagebox.showerror('Lỗi import ảnh',str(exc))
                                tk.Button(field_row,text='🖼 Thêm hình',command=choose_image,
                                          font=font_at(10, 'bold'),bg='#E2F0E2',fg='#285D40',
                                          bd=0,padx=10,pady=6,cursor='hand2').pack(side='right',padx=(7,0))
                            w=tk.Entry(field_row,font=font_at(10))
                            w.pack(side='left',fill='x',expand=True,padx=3)
                            entries[f'{side}_{i}']=w
                            if initial:
                                put(w,initial if is_image else initial.removeprefix(IMAGE_PREFIX))
                mode.bind('<<ComboboxSelected>>',render_matching_rows)
                render_matching_rows()
                self.label(dynamic,'ĐÁP ÁN CHUẨN: mỗi hàng là một cặp ĐÚNG (trái ↔ phải). Khi làm bài, cột phải tự xáo trộn; hệ thống chấm theo cặp gốc, không theo vị trí.',10).pack(anchor='w',pady=5)
                self.label(dynamic,'Hình: nhấn 🖼 để import. Có thể dùng lại ảnh ở nhiều câu, kể cả trùng tên file.',10).pack(anchor='w',pady=5)
                hint(dynamic,'Chữ ↔ Chữ: 2 ô chữ. Hình ↔ Hình: 2 ảnh. Hình ↔ Chữ / Chữ ↔ Hình: kết hợp hai loại.')
            elif typ in ('choice', 'picture_choice', 'listening_choice'):
                tk.Label(dynamic, text='CÁC PHƯƠNG ÁN TRẢ LỜI', bg='white', fg='#39865B',
                         font=font_at(11, 'bold')).pack(anchor='w', pady=(4, 5))
                for i in range(4):
                    entries['option_'+str(i)] = line('Đáp án '+chr(65+i), parent=dynamic,
                        tooltip=sample_hints.get(typ, 'Nhập nội dung đáp án mẫu.'))
                    if i<len(opts):put(entries['option_'+str(i)],opts[i])
                entries['correct'] = line('Đáp án đúng', 'combo', [], parent=dynamic,
                    tooltip='Chọn chính xác một phương án đã nhập ở trên.')
                def refresh_answer(event=None):
                    values=[get(entries['option_'+str(i)]) for i in range(4)]
                    entries['correct']['values']=[v for v in values if v]
                for i in range(4):entries['option_'+str(i)].bind('<KeyRelease>',refresh_answer,add='+')
                refresh_answer();put(entries['correct'],data.get('answer',''))
            elif typ == 'true_false':
                entries['correct'] = line('Đáp án đúng', 'combo', ['Đúng', 'Sai'], parent=dynamic)
                put(entries['correct'], data.get('answer','Đúng'))
            elif typ == 'order':
                entries['answer'] = line('Thứ tự đúng', 'text', parent=dynamic, height=2, tooltip=sample_hints['order'])
                put(entries['answer'], data.get('answer',''))
                entries['order_parts'] = line('Các thẻ theo thứ tự đúng (ngăn bằng |)', 'text', parent=dynamic, height=3,
                    tooltip='Ví dụ: Em | đi | đến trường | mỗi ngày. Để trống nếu muốn giữ cách sắp xếp từ đơn cũ.')
                parts = data.get('options') or []
                put(entries['order_parts'], ' | '.join(str(x) for x in parts) if isinstance(parts,list) else str(parts))
                self.label(dynamic, 'Mỗi phần giữa hai dấu | là một thẻ; hỗ trợ từ, cụm từ và cả câu. Để trống cho dữ liệu cũ.', 10).pack(anchor='w')
            else:
                entries['answer'] = line('Đáp án đúng', parent=dynamic, tooltip=sample_hints.get(typ, 'Nhập đáp án chuẩn.'))
                put(entries['answer'], data.get('answer',''))
            if typ in ('fill','listening_fill','error','order'):
                entries['accepted_answers'] = line('Đáp án khác được chấp nhận', parent=dynamic, tooltip='Ví dụ: colour | color. Có thể bỏ trống.')
                accepted = data.get('accepted_answers') or []
                put(entries['accepted_answers'], ' | '.join(accepted) if isinstance(accepted,list) else accepted)
                self.label(dynamic, 'Nếu có nhiều đáp án hợp lệ, ngăn cách bằng dấu |.', 10).pack(anchor='w')
            # One owner per media field: extended editors already own their own
            # media inputs. Never create a second field that can overwrite them.
            own_image = typ in {
                'picture_missing_letters', 'sentence_gaps', 'image_multi_select',
                'image_write_answer', 'image_underline_choice',
                'sentence_underline_words', 'dropdown_fill_blank',
                'multi_fill_blanks', 'inline_dropdown_fill', 'image_letter_pick',
                'image_sentence_fill',
            }
            own_audio = typ in {
                'listening_image_choice', 'audio_multi_select',
                'multi_fill_blanks', 'image_letter_pick',
            }
            if not own_image:
                media_field('image', 'Ảnh câu hỏi' if typ == 'picture_choice' else 'Ảnh câu hỏi (không bắt buộc)', [('Hình ảnh', '*.png *.jpg *.jpeg *.gif *.webp')])
            if not own_audio:
                media_field('audio', 'Âm thanh câu hỏi' if typ in ('listening_choice', 'listening_fill') else 'Âm thanh (không bắt buộc)', [('Âm thanh', '*.mp3 *.wav *.ogg')])
            for field in ('image','audio'):
                if field in entries: put(entries[field], data.get(field,''))

        def type_changed(event=None):
            index = type_widget.current()
            kind_var.set(QUESTION_TYPES[index if index >= 0 else 0])
            rebuild()
        type_widget.bind('<<ComboboxSelected>>', type_changed)
        rebuild()
        actions = tk.Frame(panel, bg='white'); actions.pack(fill='x', pady=(12, 5))

        def save():
            try:
                # Always read current editor values, including after a validation error.
                self.update_idletasks()
                typ = kind_var.get()
                # Resolve the edited record by its stable ID, not a stale list index.
                current_questions = self._levels('questions')
                edit_index = None
                if selected['index'] is not None:
                    original_id = selected.get('id')
                    matches = [i for i, q in enumerate(current_questions)
                               if str(q.get('id')) == str(original_id)] if original_id is not None else []
                    if len(matches) != 1:
                        raise ValueError('Câu hỏi đang sửa đã bị xóa hoặc danh sách đã thay đổi. Hãy chọn lại câu hỏi trước khi lưu.')
                    edit_index = matches[0]
                obj = dict(current_questions[edit_index]) if edit_index is not None else dict(selected['seed'])
                obj.update({key:get(controls[key]) for key in ('theme','id','prompt')})
                obj['level'] = question_location['level'].get(get(controls['level']))
                obj['lesson'] = question_location['lesson'].get(get(controls['lesson']))
                obj['type'] = typ
                # Stage 1: preserve a per-question layout without changing rendering.
                from question_layout_store import get_layout, set_layout
                obj = set_layout(obj, pending_layout['value'])
                obj['lesson'] = int(obj['lesson'] or 1)
                if obj['theme'] not in {t[0] for t in self._themes()}: raise ValueError('Chủ đề không hợp lệ.')
                obj['level'] = validate_level(obj['level'])
                if obj['level'] > self._max_level(obj['theme']): raise ValueError('Level vượt giới hạn.')
                if not obj['id'] or (typ != 'picture_missing_letters' and not obj['prompt']):
                    raise ValueError('Cần nhập mã câu hỏi và nội dung câu hỏi.')
                if typ in NEW_TYPES:
                    obj.update(entries['_collect_new']())
                elif typ == 'matching':
                    pairs=[]
                    for i in range(len([k for k in entries if k.startswith('left_')])):
                        left=get(entries[f'left_{i}']);right=get(entries[f'right_{i}'])
                        if bool(left)!=bool(right):raise ValueError(f'Cặp {i+1}: cần điền cả hai bên.')
                        if left and right:
                            mode=get(entries['matching_mode'])
                            from matching_widget import IMAGE_PREFIX
                            if mode.startswith('Hình') and not left.startswith(IMAGE_PREFIX):raise ValueError(f'Cặp {i+1}: thiếu ảnh bên trái.')
                            if mode.endswith('Hình') and not right.startswith(IMAGE_PREFIX):raise ValueError(f'Cặp {i+1}: thiếu ảnh bên phải.')
                            if any(x in left or x in right for x in (' = ',' -> ')):
                                raise ValueError('Không dùng dấu " = " hoặc " -> " trong nội dung ghép cặp.')
                            pairs.append((left,right))
                    if len(pairs)<2:raise ValueError('Cần ít nhất hai cặp nối.')
                    if len(set(a for a,b in pairs))!=len(pairs) or len(set(b for a,b in pairs))!=len(pairs):
                        raise ValueError('Các mục trong mỗi cột không được trùng nhau.')
                    obj['matching_mode']=get(entries['matching_mode'])
                    obj['options']=[a+' = '+b for a,b in pairs]
                    obj['answer']=' | '.join(obj['options'])
                else:
                    if typ in ('choice','picture_choice','listening_choice'):
                        opts=[get(entries[f'option_{i}']) for i in range(4)]
                        if len([v for v in opts if v]) < 2:raise ValueError('Cần ít nhất 2 phương án trả lời.')
                        if opts != [v for v in opts if v] + [''] * opts.count(''):raise ValueError('Hãy nhập phương án liên tiếp từ A, không bỏ trống ở giữa.')
                        obj['options']=[v for v in opts if v]
                    elif typ=='order':
                        parts=[v.strip() for v in get(entries['order_parts']).split('|') if v.strip()]
                        if parts and not 2 <= len(parts) <= 20:
                            raise ValueError('Bài sắp xếp cần 2–20 thẻ.')
                        obj['options']=parts
                    else:obj['options']=['Đúng','Sai'] if typ=='true_false' else []
                    obj['answer']=get(entries['correct'] if 'correct' in entries else entries['answer'])
                    if not obj['answer']:raise ValueError('Cần nhập hoặc chọn đáp án đúng.')
                    if typ in ('choice','picture_choice','listening_choice') and obj['answer'] not in obj['options']:
                        raise ValueError('Đáp án đúng phải trùng với một phương án đã nhập.')
                obj['accepted_answers'] = [v.strip() for v in get(entries['accepted_answers']).split('|') if v.strip()] if 'accepted_answers' in entries else []
                obj['image'] = get(entries['image']) if 'image' in entries else obj.get('image','')
                obj['audio'] = get(entries['audio']) if 'audio' in entries else obj.get('audio','')
                # Optional attachments must resolve before persisting. Empty fields
                # remain valid and do not reserve space in the exercise renderer.
                for media_key, media_label in (('image', 'hình ảnh'), ('audio', 'âm thanh')):
                    media_ref = str(obj.get(media_key) or '').strip()
                    if media_ref:
                        resolved = self.media_file(media_ref)
                        if not resolved or not Path(resolved).is_file():
                            raise ValueError(f'Không tìm thấy {media_label} đã chọn: {media_ref}')
                if typ == 'picture_choice' and not obj['image']: raise ValueError('Bài chọn hình cần ảnh.')
                if typ in ('listening_choice','listening_fill'):
                    if not obj['audio']: raise ValueError('Bài nghe cần âm thanh.')
                    audio_file = self.media_file(obj['audio'])
                    if audio_file is None or not Path(audio_file).is_file():
                        raise ValueError('Không tìm thấy file nghe đã import. Hãy chọn lại file âm thanh.')
                # Work on a copy: failed validation must never mutate cached questions.
                items = [dict(item) for item in current_questions]
                if edit_index is None: items.append(obj)
                else: items[edit_index] = obj
                # Persist first, then verify both disk and the curriculum cache.
                # A successful button callback alone is not proof of a saved question.
                if edit_index is None and not obj.get('id'):
                    raise ValueError('Cần nhập mã câu hỏi.')
                if sum(str(q.get('id')) == str(obj['id']) for q in items) != 1:
                    raise ValueError('Mã câu hỏi bị trùng; vui lòng dùng mã duy nhất.')
                save_rows(self.curriculum.data_dir, 'questions', items)
                disk_rows = load_rows(self.curriculum.data_dir, 'questions', None)
                if not any(str(q.get('id')) == str(obj['id']) and q.get('prompt') == obj['prompt'] for q in disk_rows):
                    raise OSError('Không xác nhận được câu hỏi trong file dữ liệu.')
                # Verify that the actual JSON record retained the edited layout,
                # not merely its id and prompt.  Do not report success on loss.
                persisted = next(q for q in disk_rows if str(q.get('id')) == str(obj['id']))
                if get_layout(persisted) != get_layout(obj):
                    raise OSError('Bố cục câu hỏi chưa được ghi đầy đủ vào JSON.')
                self.curriculum.reload()
                if not any(str(q.get('id')) == str(obj['id']) and q.get('prompt') == obj['prompt'] for q in self._levels('questions')):
                    detail = '; '.join(self.curriculum.errors[-5:])
                    raise ValueError('Dữ liệu đã ghi ra file nhưng không được tải vào danh sách. ' + detail)
                reloaded = next(q for q in self._levels('questions') if str(q.get('id')) == str(obj['id']))
                if get_layout(reloaded) != get_layout(obj):
                    raise ValueError('Bố cục đã lưu nhưng chưa được nạp đúng sau khi tải lại dữ liệu.')
            except (ValueError, OSError, KeyError, TypeError) as exc:
                # Do not rebuild the editor or clear the form after failed save.
                messagebox.showerror('Chưa lưu được bài tập', str(exc), parent=self)
                self.after_idle(lambda: self.focus_set() if self.winfo_exists() else None)
                return
            self._question_editor_form_state = {
                'theme': get(controls['theme']),
                'level': question_location['level'].get(get(controls['level'])),
                'lesson': question_location['lesson'].get(get(controls['lesson'])),
                'type': kind_var.get(),
            }
            self._question_editor_filter_state = {
                'theme': theme_var.get(), 'level': level_var.get(),
                'lesson': lesson_var.get(), 'offset': page_state['offset'],
            }
            self.question_editor()
            messagebox.showinfo('Đã lưu bài tập',
                f'Đã lưu mã {obj["id"]} vào dữ liệu môn học.\n'
                f'File: {library_file(self.curriculum.data_dir, "questions")}\n'
                'Câu hỏi mới nằm ở cuối danh sách.', parent=self)

        def reset():
            selected['seed']={}
            # A new question inherits the user's current location and exercise type.
            # Only question-specific inputs are cleared.
            selected['index'] = None
            selected['id'] = None
            pending_layout['value'] = {}
            for key, widget in controls.items():
                if key not in ('theme', 'level', 'lesson'):
                    put(widget, '')
            kind_var.set(QUESTION_TYPES[type_names.index(type_widget.get())]
                         if type_widget.get() in type_names else kind_var.get())
            type_widget.set(type_names[QUESTION_TYPES.index(kind_var.get())])
            rebuild()
        def preview(layout_override=None, owner=None, on_frame=None):
            """Use the actual exercise window for previews; never save or score."""
            typ = kind_var.get()
            try:
                prompt = get(controls['prompt'])
                question = {'type': typ, 'prompt': prompt if typ == 'picture_missing_letters' else prompt or 'Xem trước bài tập'}
                if typ in NEW_TYPES:
                    question.update(entries['_collect_new']())
                elif typ == 'matching':
                    pairs = []
                    for i in range(len([key for key in entries if key.startswith('left_')])):
                        left = get(entries[f'left_{i}'])
                        right = get(entries[f'right_{i}'])
                        if left and right:
                            pairs.append(left + ' = ' + right)
                    if len(pairs) < 2:
                        raise ValueError('Cần ít nhất hai cặp để xem trước bài nối.')
                    question.update(options=pairs, answer=' | '.join(pairs))
                    question['image'] = get(entries['image']) if 'image' in entries else ''
                else:
                    if typ in ('choice', 'picture_choice', 'listening_choice'):
                        raw_options = [get(entries[f'option_{i}']) for i in range(4)]
                        if len([v for v in raw_options if v]) < 2:
                            raise ValueError('Cần ít nhất 2 phương án để xem trước.')
                        if raw_options != [v for v in raw_options if v] + [''] * raw_options.count(''):
                            raise ValueError('Hãy nhập phương án liên tiếp từ A, không bỏ trống ở giữa.')
                        question['options'] = [v for v in raw_options if v]
                    elif typ == 'true_false':
                        question['options'] = ['Đúng', 'Sai']
                    elif typ == 'order':
                        parts=[v.strip() for v in get(entries['order_parts']).split('|') if v.strip()]
                        if parts and not 2 <= len(parts) <= 20:
                            raise ValueError('Bài sắp xếp cần 2–20 thẻ.')
                        question['options']=parts
                    else:
                        question['options'] = []
                    answer_widget = entries.get('correct', entries.get('answer'))
                    question['answer'] = get(answer_widget) if answer_widget is not None else ''
                    if not question['answer']:
                        raise ValueError('Hãy nhập đáp án để xem trước.')
                    question['image'] = get(entries['image']) if 'image' in entries else ''
                    question['audio'] = get(entries['audio']) if 'audio' in entries else ''
                # Media fields are shared by every question type, including NEW_TYPES.
                question['image'] = get(entries['image']) if 'image' in entries else question.get('image', '')
                question['audio'] = get(entries['audio']) if 'audio' in entries else question.get('audio', '')
                # Preview the current staged visual layout, including unsaved edits.
                # This is a copy only: preview must never persist or mutate a question.
                from question_layout_store import get_layout
                question['layout'] = get_layout({'layout': pending_layout['value'] if layout_override is None else layout_override})
                if typ == 'listening_image_choice':
                    import listening_image_choice  # thieu file nay thi bao loi ro rang, khong im lang
                import pygame_exercises
                if not pygame_exercises.launch(owner or self, question, lambda _answer: None, allow_feedback=False, on_frame=on_frame):
                    messagebox.showwarning('Xem trước',
                        'Không mở được cửa sổ xem trước. Hãy đóng cửa sổ bài tập khác rồi thử lại.', parent=self)
            except (ValueError, OSError, TypeError, KeyError, ImportError) as exc:
                messagebox.showwarning('Xem trước', str(exc), parent=self)
        def edit_visual_layout():
            # Stage 2: edit and stage layout only. The existing Pygame preview
            # remains unchanged until the rendering integration in Stage 3.
            from question_layout_editor import edit_layout
            typ = kind_var.get()
            question = {'type': typ, 'prompt': get(controls['prompt']), 'id': get(controls['id']),
                        'theme': get(controls['theme']), 'level': get(controls['level']),
                        'lesson': get(controls['lesson'])}
            try:
                # Read current editor values, including unsaved answer changes.
                # This is a preview-only copy; no answer/scoring logic is changed.
                if typ in NEW_TYPES and '_collect_new' in entries:
                    question.update(entries['_collect_new']())
                elif typ in ('choice', 'picture_choice', 'listening_choice'):
                    question['options'] = [get(entries['option_%d' % i]) for i in range(4)
                                           if 'option_%d' % i in entries and get(entries['option_%d' % i])]
                elif typ == 'true_false':
                    question['options'] = ['Đúng', 'Sai']
                elif typ == 'order' and 'order_parts' in entries:
                    question['options'] = [v.strip() for v in get(entries['order_parts']).split('|') if v.strip()]
                elif typ == 'matching':
                    question['options'] = [get(entries['left_%d' % i]) + ' = ' + get(entries['right_%d' % i])
                                           for i in range(20) if 'left_%d' % i in entries and 'right_%d' % i in entries
                                           and get(entries['left_%d' % i]) and get(entries['right_%d' % i])]
                from shutil import which
                from tempfile import TemporaryDirectory
                from uuid import uuid4
                import sys

                if 'image' in entries:
                    question['image'] = get(entries['image'])
                templates = self.data_dir / 'canvas_templates.json'
                can_paste = 'image' in entries and (
                    sys.platform in ('win32','darwin') or which('xclip') or which('wl-paste'))
                with TemporaryDirectory(prefix='tuhoc-clipboard-') as scratch:
                    clipboard = Path(scratch) / f'clipboard-{uuid4().hex}.png' if can_paste else None
                    updated = edit_layout(self,question,pending_layout['value'],
                                          preview=preview,templates=templates,clipboard=clipboard)
                    if updated is not None:
                        if clipboard is not None and clipboard.is_file():
                            put(entries['image'],store_media(clipboard))
                        pending_layout['value'] = updated
            except (OSError, ValueError, tk.TclError) as exc:
                messagebox.showwarning('Chỉnh bố cục', str(exc), parent=self)

        def apply_type_template():
            from layout_templates import apply_lesson_layout, read_template
            from safe_storage import commit_json
            typ=kind_var.get()
            theme=get(controls['theme'])
            location=question_location
            level=location['level'].get(get(controls['level']))
            lesson=location['lesson'].get(get(controls['lesson']))
            if not theme or level is None or lesson is None:
                messagebox.showwarning('Thiếu thông tin','Hãy chọn chủ đề, Level và Lesson.',parent=self)
                return
            try:
                layout=read_template(self.data_dir/'canvas_templates.json',typ)
                if layout is None:
                    messagebox.showinfo('Chưa có mẫu','Trong Studio, chọn Lưu làm mẫu trước.',parent=self)
                    return
                path=library_file(self.curriculum.data_dir,'questions')
                rows=load_rows(self.curriculum.data_dir,'questions',None)
                updated,matches,changes=apply_lesson_layout(rows,(str(theme),str(level),str(lesson),typ),layout)
                if not changes:
                    messagebox.showinfo('Áp dụng mẫu',f'Không có thay đổi trong {matches} câu phù hợp.',parent=self)
                    return
                if not messagebox.askyesno('Áp dụng mẫu',
                    f'Ghi đè bố cục của {changes}/{matches} câu cùng dạng trong Lesson này? '
                    'Hệ thống sẽ lưu bản sao trước khi ghi.',parent=self):
                    return
                if path.is_file():
                    from datetime import datetime
                    from shutil import copy2
                    backup=path.with_name(path.name+'.'+datetime.now().strftime('%Y%m%d%H%M%S%f')+'.bak')
                    copy2(path,backup)
                commit_json({path:updated})
                self.curriculum.reload()
                self.question_editor()
            except (OSError,ValueError,TypeError) as exc:
                messagebox.showerror('Không áp dụng được mẫu',str(exc),parent=self)

        self.action_button(actions, 'Lưu bài tập', save).pack(side='left', padx=(0,8))
        self.action_button(actions, '👁 Xem trước', preview).pack(side='left', padx=6)
        self.action_button(actions, '↔ Chỉnh bố cục', edit_visual_layout).pack(side='left', padx=6)
        self.action_button(actions, 'Áp dụng mẫu cho Lesson', apply_type_template).pack(side='left',padx=6)
        self.action_button(actions, '＋ Tạo câu mới', reset).pack(side='left')
        # Filter the existing in-memory question collection; never rebuild the editor
        # when changing filters. Limit visible rows to keep Tk widget destruction cheap.
        self.label(body, 'DANH SÁCH CÂU HỎI', 13, True).pack(anchor='w', pady=(18,7))
        filter_bar = tk.Frame(body, bg='white', padx=8, pady=8)
        filter_bar.pack(fill='x', pady=(0, 6))
        question_rows = self._levels('questions')
        theme_names = {str(t[0]): str(t[1]) for t in self._themes()}
        all_label = 'Tất cả'
        # Keep the user's filter selections when this editor is recreated
        # (for example after saving or deleting a question).
        saved_filters = getattr(self, '_question_editor_filter_state', {})
        theme_var = tk.StringVar(value=saved_filters.get('theme', all_label))
        level_var = tk.StringVar(value=saved_filters.get('level', all_label))
        lesson_var = tk.StringVar(value=saved_filters.get('lesson', all_label))
        page_state = {'offset': saved_filters.get('offset', 0)}
        page_size = 10
        search_var=tk.StringVar(value=saved_filters.get('search',''))
        type_filter=tk.StringVar(value=saved_filters.get('kind',all_label))
        sort_var=tk.StringVar(value=saved_filters.get('sort','Thứ tự lưu'))
        selectors = {}
        for caption, key, var in [('Chủ đề', 'theme', theme_var),
                                  ('Level', 'level', level_var),
                                  ('Lesson', 'lesson', lesson_var)]:
            group = tk.Frame(filter_bar, bg='white')
            group.pack(side='left', padx=(0, 12))
            tk.Label(group, text=caption, bg='white', fg='#285D40').pack(anchor='w')
            selector = ttk.Combobox(group, textvariable=var, state='readonly', width=23 if key == 'theme' else 12)
            selector.pack()
            selectors[key] = selector
        advanced=tk.Frame(body,bg='white',padx=8,pady=5)
        advanced.pack(fill='x')
        tk.Label(advanced,text='Tìm mã hoặc nội dung',bg='white').pack(side='left')
        ttk.Entry(advanced,textvariable=search_var,width=24).pack(side='left',padx=(6,12))
        tk.Label(advanced,text='Dạng',bg='white').pack(side='left')
        ttk.Combobox(advanced,textvariable=type_filter,values=(all_label,*QUESTION_TYPES),
                     state='readonly',width=20).pack(side='left',padx=(6,12))
        ttk.Combobox(advanced,textvariable=sort_var,values=('Thứ tự lưu','Mã','Nội dung'),
                     state='readonly',width=14).pack(side='left')
        status = tk.Label(body, bg='white', fg='#285D40', anchor='w')
        status.pack(fill='x', padx=8)
        list_container = tk.Frame(body, bg='white')
        list_container.pack(fill='x')
        pager = tk.Frame(body, bg='white')
        pager.pack(fill='x', pady=7)

        def available_rows():
            filters={key:(value if value!=all_label else None)
                     for key,value in (('theme',theme_var.get()),('level',level_var.get()),
                                       ('lesson',lesson_var.get()),('type',type_filter.get()))}
            return find_rows(question_rows,search_var.get(),
                             sort_by={'Mã':'id','Nội dung':'prompt'}.get(sort_var.get()),filters=filters)

        def update_selector_options(reset=False):
            # Each selector is independent: selecting one must not overwrite or
            # restrict the choices already selected in the other two selectors.
            themes = sorted({str(q.get('theme', '')) for q in question_rows if q.get('theme')} |
                            {str(t[0]) for t in self._themes()})
            levels = sorted({str(q.get('level', '')) for q in question_rows if q.get('level') is not None},
                            key=lambda x: (not x.isdigit(), int(x) if x.isdigit() else x))
            lessons = sorted({str(q.get('lesson') or 1) for q in question_rows},
                             key=lambda x: (not x.isdigit(), int(x) if x.isdigit() else x))
            for key, values, var in (('theme', themes, theme_var),
                                     ('level', levels, level_var),
                                     ('lesson', lessons, lesson_var)):
                current = var.get()
                selectors[key].configure(values=[all_label] + values)
                if reset or (current != all_label and current not in values):
                    var.set(all_label)

        def edit(i, clone=False):
            item=self._levels('questions')[i]
            selected['seed']={}
            if clone:
                item=copy_question(item)
                selected['seed']=item

            selected['index'] = None if clone else i
            selected['id'] = None if clone else item.get('id')
            from question_layout_store import get_layout
            pending_layout['value'] = get_layout(item)
            for key in ('theme','id','prompt'): put(controls[key], item.get(key,''))
            refresh_question_location(level_id=int(item.get('level') or 1), lesson_id=int(item.get('lesson') or 1))
            typ = item.get('type','choice')
            if typ not in QUESTION_TYPES: typ='choice'
            kind_var.set(typ); type_widget.set(type_names[QUESTION_TYPES.index(typ)])
            rebuild(existing=item)
            check_form()
            if clone:
                form_status.set('Bản sao chưa lưu. Kiểm tra nội dung rồi chọn Lưu bài tập.')

        def delete(i):
            if not dialogs.askyesno('Xóa câu hỏi','Xóa câu hỏi này?',parent=self):
                return
            root=self.curriculum.data_dir
            path=library_file(root,'questions')
            data=load_rows(root,'questions',None)
            identity=str(question_rows[i].get('id'))
            matches=[index for index,row in enumerate(data) if str(row.get('id'))==identity]
            if len(matches)!=1:
                dialogs.showwarning('Xóa câu hỏi','Danh sách đã thay đổi. Hãy tải lại.',parent=self)
                return
            updated,ticket=remove_at(data,matches[0])
            try:
                commit_json({path:updated})
                self.curriculum.reload()
                question_rows[:]=self._levels('questions')
                render_rows()
            except (OSError,ValueError) as exc:
                dialogs.showerror('Không xóa được câu hỏi',str(exc),parent=self)
                return

            def restore():
                try:
                    latest=load_rows(root,'questions',None)
                    commit_json({path:ticket.restore(latest,unique_id=True)})
                    self.curriculum.reload()
                    question_rows[:]=self._levels('questions')
                    render_rows()
                except (OSError,ValueError) as exc:
                    dialogs.showerror('Không hoàn tác được',str(exc),parent=self)

            Toast(body,'Đã xóa câu hỏi.',duration=6000,action=('Hoàn tác',restore))

        def render_rows():
            for child in list_container.winfo_children():
                child.destroy()
            for child in pager.winfo_children():
                child.destroy()
            matching = available_rows()
            total = len(matching)
            page_state['offset'] = max(0, min(page_state['offset'], max(0, ((total - 1) // page_size) * page_size)))
            start = page_state['offset']
            status.configure(text=f'Hiển thị {start + 1 if total else 0}–{min(start + page_size, total)} / {total} câu hỏi (tổng {len(question_rows)})')
            self._content_table(list_container, matching[start:start + page_size],
                [('Chủ đề', lambda o: theme_names.get(str(o.get('theme','')), o.get('theme',''))),
                 ('Level', lambda o: self._display_name('level', o.get('theme',''), o.get('level',''))),
                 ('Lesson', lambda o: self._display_name('lesson', o.get('theme',''), o.get('level',''), o.get('lesson') or 1)),
                 ('Dạng bài tập', lambda o: QUESTION_LABELS.get(o.get('type'), o.get('type',''))),
                 ('Nội dung câu hỏi', lambda o: o.get('prompt',''))],
                edit, delete, start + 1,duplicate=lambda i:edit(i,clone=True))
            tk.Label(pager, text=f'Trang {start // page_size + 1}/{max(1, (total + page_size - 1) // page_size)}',
                     bg='white', fg='#285D40', font=font_at(10, 'bold')).pack(side='left', padx=9)
            if start:
                tk.Button(pager, text='← Trang trước', command=lambda: change_page(-1)).pack(side='left', padx=5)
            if start + page_size < total:
                tk.Button(pager, text='Trang sau →', command=lambda: change_page(1)).pack(side='left', padx=5)

        def change_page(direction):
            page_state['offset'] += direction * page_size
            self._question_editor_filter_state = {
                'search':search_var.get(),'kind':type_filter.get(),'sort':sort_var.get(),
                'theme': theme_var.get(), 'level': level_var.get(),
                'lesson': lesson_var.get(), 'offset': page_state['offset'],
            }
            render_rows()

        def change_filter(*_):
            self._question_editor_filter_state = {
                'search':search_var.get(),'kind':type_filter.get(),'sort':sort_var.get(),
                'theme': theme_var.get(),
                'level': level_var.get(),
                'lesson': lesson_var.get(),
                'offset': 0,
            }
            page_state['offset'] = 0
            render_rows()

        selectors['theme'].configure(postcommand=update_selector_options)
        selectors['theme'].bind('<FocusIn>', lambda event: update_selector_options(reset=False))
        update_selector_options(reset=False)
        self._question_editor_filter_state = {
            'search':search_var.get(),'kind':type_filter.get(),'sort':sort_var.get(),
            'theme': theme_var.get(),
            'level': level_var.get(),
            'lesson': lesson_var.get(),
            'offset': page_state['offset'],
        }
        for var in (theme_var, level_var, lesson_var):
            var.trace_add('write', change_filter)
        for variable in (search_var,type_filter,sort_var):
            variable.trace_add('write',change_filter)
        render_rows()

    def level_editor(self,kind):
        if kind == 'questions':
            return self.question_editor()
        body=self.layout({'lessons':'Thêm bài học','questions':'Thêm bài tập','vocab':'Thêm từ vựng','blocks':'Thêm khối nội dung','reading':'Thêm bài đọc / Reading'}[kind])
        fields={'lessons':LESSON_KEYS,'questions':QUESTION_KEYS,'vocab':VOCAB_KEYS,'blocks':BLOCK_KEYS,'reading':READING_KEYS}[kind]
        if kind == 'lessons':
            from tkinter import ttk
            from multi_block_editor import open_block_editor
            chooser = tk.Frame(body, bg=body['bg'])
            chooser.pack(fill='x', pady=12)
            tk.Label(chooser, text='Tạo bài học mới (nhiều block)', bg=body['bg'],
                     font=font_at(13, 'bold')).pack(anchor='w', pady=(0, 8))
            selection = tk.Frame(chooser, bg=body['bg'])
            selection.pack(fill='x')
            theme_codes = [t[0] for t in self._themes()]
            theme_labels = {str(code): self._display_name('theme', code, None) for code in theme_codes}
            theme_var = tk.StringVar(value=theme_labels.get(str(theme_codes[0]), '') if theme_codes else '')
            level_var = tk.StringVar(value='1')
            lesson_var = tk.StringVar(value='1')
            for label, var, values in [('Chủ đề', theme_var, [theme_labels[str(c)] for c in theme_codes]),
                                       ('Level', level_var, []),
                                       ('Lesson', lesson_var, [])]:
                tk.Label(selection, text=label, bg=body['bg']).pack(side='left', padx=(0, 5))
                combo = ttk.Combobox(selection, textvariable=var, values=values,
                                     state='readonly', width=22 if label == 'Chủ đề' else 8)
                combo.pack(side='left', padx=(0, 14))
                if label == 'Level': level_combo = combo
                if label == 'Lesson': lesson_combo = combo
            def chosen_theme():
                return next((code for code in theme_codes if theme_labels[str(code)] == theme_var.get()),
                            theme_codes[0] if theme_codes else '')
            def refresh_lessons(*_):
                code = chosen_theme()
                try:
                    level = next(n for n in range(1, self._max_level(code)+1)
                                 if self._display_name('level', code, n) == level_var.get())
                except StopIteration:
                    level = 1
                used = {int(row.get('lesson') or 1) for row in self._levels('lessons')
                        if str(row.get('theme')) == code and int(row.get('level') or 0) == level}
                nxt = next((n for n in range(1, self._lesson_count(code,level)+1) if n not in used), None)
                choices = [(n, self._display_name('lesson', code, level, n)) for n in range(1, self._lesson_count(code,level)+1)]
                lesson_combo.configure(values=[label for _, label in choices])
                if nxt is not None:
                    lesson_var.set(self._display_name('lesson', code, level, nxt))
            def refresh_levels(*_):
                code = chosen_theme()
                choices = [self._display_name('level', code, n) for n in range(1, self._max_level(code)+1)]
                level_combo.configure(values=choices)
                if choices: level_var.set(choices[0])
                refresh_lessons()
            theme_var.trace_add('write', refresh_levels)
            level_var.trace_add('write', refresh_lessons)
            refresh_levels()
            def create_lesson():
                theme = chosen_theme()
                level = next((n for n in range(1, self._max_level(theme)+1)
                              if self._display_name('level', theme, n) == level_var.get()), None)
                if level is None:
                    messagebox.showwarning('Level', 'Hãy chọn Level hợp lệ.');return
                lesson = next((n for n in range(1, self._lesson_count(theme,level)+1)
                               if self._display_name('lesson', theme, level, n) == lesson_var.get()), None)
                if lesson is None:
                    messagebox.showwarning('Lesson', 'Hãy chọn bài học hợp lệ.');return
                exists = any(str(row.get('theme')) == theme and
                             int(row.get('level') or 0) == level and
                             int(row.get('lesson') or 1) == lesson
                             for row in self._levels('lessons'))
                if exists:
                    messagebox.showwarning('Bài học đã tồn tại',
                                           'Bài học này đã có. Hãy dùng nút Sửa trong danh sách.')
                    return
                open_block_editor(self, theme, level, lesson, create_mode=True)
            tk.Button(chooser, text='+ Tạo bài học và thêm các block', command=create_lesson,
                      bg='#34865C', fg='white', font=font_at(11, 'bold'),
                      bd=0, padx=15, pady=9).pack(anchor='w', pady=12)
            tk.Label(chooser, text='Chọn bài học có sẵn ở danh sách bên dưới để sửa toàn bộ block.',
                     bg=body['bg'], fg='#557263').pack(anchor='w')
        else:
            self.label(body,'Chọn mã chủ đề đã khai báo và level trong giới hạn của chủ đề. Các dạng câu hỏi có thể nhập lựa chọn bằng dấu |.',11).pack(anchor='w',pady=6)
            if 'image' in fields:self.label(body,'Ảnh: bấm Chọn ảnh... để tự sao chép và điền đường dẫn media/ten_anh.png. Khuyến nghị PNG, tỷ lệ 4:3.',11).pack(anchor='w',pady=5)
            inputs={}
            for name in fields:
                row=tk.Frame(body,bg=body['bg']);row.pack(fill='x',pady=3)
                tk.Label(row,text=name,width=19,anchor='w',bg=body['bg']).pack(side='left')
                if name == 'theme':
                    w=__import__('tkinter').ttk.Combobox(row,values=[t[0] for t in self._themes()],state='readonly',font=font_at(12));w.pack(side='left',fill='x',expand=True);w.set(self._themes()[0][0]);w._theme_selector=True
                elif name == 'lesson':
                    w=__import__('tkinter').ttk.Combobox(row,values=list(range(1,self._lesson_count(self._themes()[0][0],1)+1)),state='readonly',font=font_at(12));w.pack(side='left',fill='x',expand=True);w.set('1')
                elif name == 'type' and kind == 'questions':
                    w=__import__('tkinter').ttk.Combobox(row,values=list(QUESTION_TYPES),state='readonly',font=font_at(12));w.pack(side='left',fill='x',expand=True);w.set('choice')
                elif name in ('content','instructions','prompt'):
                    w=tk.Text(row,height=4,font=font_at(12));w.pack(side='left',fill='x',expand=True)
                else:
                    w=tk.Entry(row,font=font_at(12));w.pack(side='left',fill='x',expand=True)
                inputs[name]=w
                if name in ('audio','title_audio','content_audio'):
                    def choose_audio(entry=w):
                        from shutil import copy2
                        source=filedialog.askopenfilename(title='Chọn âm thanh',filetypes=[('Âm thanh','*.mp3 *.wav *.ogg'),('Tất cả','*.*')])
                        if not source:return
                        audio_path=Path(source)
                        if audio_path.suffix.lower() not in ('.mp3','.wav','.ogg'):
                            messagebox.showerror('Định dạng','Chỉ hỗ trợ MP3, WAV hoặc OGG.');return
                        target_dir=self.curriculum.data_dir/'content_library'/'media'
                        target_dir.mkdir(parents=True,exist_ok=True)
                        dest=target_dir/audio_path.name
                        if dest.exists() and dest.resolve()!=audio_path.resolve():
                            import hashlib
                            if dest.read_bytes()!=audio_path.read_bytes():dest=target_dir/(audio_path.stem+'_'+hashlib.sha256(audio_path.read_bytes()).hexdigest()[:12]+audio_path.suffix.lower())
                        if not dest.exists():copy2(audio_path,dest)
                        entry.delete(0,'end');entry.insert(0,'media/'+dest.name)
                    tk.Button(row,text='Chọn âm thanh...',command=choose_audio,font=font_at(10, 'bold'),
                              bg='#E2F0E2',fg='#285D40',bd=0,padx=12,pady=8).pack(side='left',padx=(8,0))
                if name == 'image':
                    def choose_image(entry=w):
                        from shutil import copy2
                        source=filedialog.askopenfilename(title='Chọn ảnh minh họa',filetypes=[('Ảnh hỗ trợ','*.png *.gif *.jpg *.jpeg'),('Tất cả','*.*')])
                        if not source:return
                        image_path=Path(source)
                        if image_path.suffix.lower() not in ('.png','.gif','.jpg','.jpeg'):
                            messagebox.showerror('Định dạng không hỗ trợ','Chọn PNG, GIF, JPG hoặc JPEG.');return
                        if image_path.suffix.lower() in ('.jpg','.jpeg'):
                            try:from PIL import Image
                            except ImportError:
                                messagebox.showerror('Thiếu Pillow','Ảnh JPG/JPEG cần Pillow. Chạy: py -m pip install pillow hoặc dùng ảnh PNG.');return
                        target_dir=self.curriculum.data_dir/'content_library'/'media'
                        target_dir.mkdir(parents=True,exist_ok=True)
                        destination=target_dir/image_path.name
                        if destination.exists() and destination.resolve()!=image_path.resolve():
                            import hashlib
                            if destination.read_bytes()!=image_path.read_bytes():destination=target_dir/(image_path.stem+'_'+hashlib.sha256(image_path.read_bytes()).hexdigest()[:12]+image_path.suffix.lower())
                        if not destination.exists():copy2(image_path,destination)
                        entry.delete(0,'end');entry.insert(0,'media/'+destination.name)
                        messagebox.showinfo('Đã chọn ảnh','Đã tự điền: media/'+destination.name+'\nBấm Lưu nội dung để hoàn tất.')
                    tk.Button(row,text='Chọn ảnh...',command=choose_image,font=font_at(10, 'bold'),bg='#E2F0E2',fg='#285D40',bd=0,padx=12,pady=8).pack(side='left',padx=(8,0))
            target={'index':None}
            def fill(idx):
                item=self._levels(kind)[idx];target['index']=idx
                if kind == 'lessons':
                    from multi_block_editor import open_block_editor
                    return open_block_editor(self, item['theme'], item['level'], item.get('lesson') or 1)
                for k,w in inputs.items():
                    val=item.get(k,'');val='|'.join(map(str,val)) if isinstance(val,list) else str(val)
                    if isinstance(w,tk.Text):w.delete('1.0','end');w.insert('1.0',val)
                    elif isinstance(w,__import__('tkinter').ttk.Combobox):w.set(val)
                    else:w.delete(0,'end');w.insert(0,val)
            def save():
                obj={k:(w.get('1.0','end').strip() if isinstance(w,tk.Text) else w.get().strip()) for k,w in inputs.items()}
                try:
                    if obj['theme'] not in {t[0] for t in self._themes()}:raise ValueError('Theme không hợp lệ.')
                    obj['level']=validate_level(obj['level'])
                    if obj['level']>self._max_level(obj['theme']):raise ValueError('Level vượt giới hạn của chủ đề.')
                    obj['lesson']=int(obj.get('lesson') or 1)
                    if not 1<=obj['lesson']<=self._lesson_count(obj['theme'],obj['level']):raise ValueError('Lesson vượt số lượng của Level.')
                    if kind=='blocks':
                        obj['order']=int(obj['order'])
                        if obj['order']<1:raise ValueError('Thứ tự phải từ 1 trở lên.')
                    for k in ('options','accepted_answers'):
                        if k in obj:obj[k]=[x.strip() for x in obj[k].split('|') if x.strip()]
                    if kind=='questions':
                        if obj['type'] not in QUESTION_TYPES:raise ValueError('Loại bài tập không hợp lệ.')
                        if obj['type'] in ('listening_choice','listening_fill','listening_image_choice') and not obj.get('audio'):raise ValueError('Cần chọn âm thanh cho bài nghe.')
                        if obj['type']=='picture_choice' and (not obj.get('image') or len(obj.get('options',[]))<2 or not obj.get('answer')):raise ValueError('Cần hình, ít nhất 2 đáp án chọn và đáp án đúng.')
                    items=self._levels(kind)
                    if target['index'] is None:items.append(obj)
                    else:items[target['index']]=obj
                    save_rows(self.curriculum.data_dir,kind,items)
                    self.curriculum.reload()
                except (ValueError,OSError) as e:messagebox.showerror('Lỗi',str(e));return
                self.level_editor(kind)
            self.action_button(body,'Lưu nội dung',save).pack(anchor='w',pady=8)
        # Lesson list only: three filters and at most ten visible rows per page.
        if kind == 'lessons':
            from tkinter import ttk
            def fill(idx):
                # The lesson editor has its own form. Do not reference the
                # legacy form's local 'fill' callback from the other branch.
                rows = self._levels('lessons')
                if not 0 <= idx < len(rows):
                    return
                item = rows[idx]
                from multi_block_editor import open_block_editor
                return open_block_editor(self, item['theme'], item['level'], item.get('lesson') or 1)
            all_rows = list(enumerate(self._levels(kind)))
            filters = tk.Frame(body, bg=body['bg'])
            filters.pack(fill='x', pady=(8, 4))
            filter_vars = {}
            for field, label in (('theme', 'Chủ đề'), ('lesson', t('lessons')), ('level', 'Level')):
                tk.Label(filters, text=label, bg=body['bg']).pack(side='left', padx=(8, 3))
                values = sorted({str(obj.get(field, 1 if field == 'lesson' else '')) for _, obj in all_rows},
                                key=lambda v: (int(v) if v.isdigit() else float('inf'), v))
                if field == 'theme':
                    values = sorted(set(values) | {str(t[0]) for t in self._themes()})
                # Keep IDs in the model; only show user-facing labels in the UI.
                def option_label(code, field=field):
                    if field == 'theme':
                        return self._display_name('theme', code, None)
                    return code
                # Keep the original IDs in option_map. Names are presentation only.
                option_map = {option_label(code): code for code in values}
                variable = tk.StringVar(value='Tất cả')
                combo = ttk.Combobox(filters, textvariable=variable, values=['Tất cả'] + list(option_map),
                                     state='readonly', width=28 if field == 'theme' else 13)
                combo.pack(side='left', padx=(0, 8))
                if field == 'theme':
                    def refresh_themes(event=None, widget=combo, mapping=option_map,
                                       make_label=option_label, selected=variable):
                        current = {str(obj.get('theme', '')) for _, obj in all_rows}
                        current.update(str(t[0]) for t in self._themes())
                        previous_code = mapping.get(selected.get())
                        mapping.clear()
                        mapping.update({make_label(code): code for code in sorted(current)})
                        widget.configure(values=['Tất cả'] + list(mapping))
                        if previous_code is not None:
                            selected.set(next((label for label, code in mapping.items()
                                               if code == previous_code), 'Tất cả'))
                    combo.bind('<FocusIn>', refresh_themes)
                    combo.configure(postcommand=refresh_themes)
                filter_vars[field] = (variable, option_map)
            list_frame = tk.Frame(body, bg=body['bg'])
            list_frame.pack(fill='x')
            navigation = tk.Frame(body, bg=body['bg'])
            navigation.pack(fill='x', pady=6)
            page = {'number': 0}
            def render_lessons():
                for child in list_frame.winfo_children(): child.destroy()
                for child in navigation.winfo_children(): child.destroy()
                matching = [(i, obj) for i, obj in all_rows if all(
                    var.get() == 'Tất cả' or str(obj.get(field, 1 if field == 'lesson' else '')) == options.get(var.get(), var.get())
                    for field, (var, options) in filter_vars.items())]
                pages = max(1, (len(matching) + 9) // 10)
                page['number'] = min(page['number'], pages - 1)
                def delete(i):
                    if messagebox.askyesno('Xóa', 'Xóa mục này?'):
                        items = self._levels(kind); items.pop(i)
                        save_rows(self.curriculum.data_dir, kind, items)
                        self.curriculum.reload(); self.level_editor(kind)
                self._content_table(list_frame, matching[page['number'] * 10:(page['number'] + 1) * 10],
                    [('Chủ đề', lambda o: display_name(self.curriculum.data_dir, 'theme', o.get('theme',''))),
                     ('Level', lambda o: self._display_name('level', o.get('theme',''), o.get('level',''))),
                     ('Lesson', lambda o: self._display_name('lesson', o.get('theme',''), o.get('level',''), o.get('lesson',1))),
                     ('Tên bài học', lambda o: self._display_name('lesson', o.get('theme',''), o.get('level',''), o.get('lesson',1)))],
                    fill, delete, page['number'] * 10 + 1)
                def move(delta):
                    page['number'] += delta
                    render_lessons()
                previous = tk.Button(navigation, text='← Trước', command=lambda: move(-1),
                                     state='normal' if page['number'] > 0 else 'disabled')
                previous.pack(side='left', padx=4)
                tk.Label(navigation, text=f"Trang {page['number'] + 1}/{pages} · {len(matching)} bài học",
                         bg=body['bg']).pack(side='left', padx=8)
                tk.Button(navigation, text='Sau →', command=lambda: move(1),
                          state='normal' if page['number'] < pages - 1 else 'disabled').pack(side='left', padx=4)
            for var, _options in filter_vars.values():
                var.trace_add('write', lambda *_: (page.update(number=0), render_lessons()))
            render_lessons()
            # Show the existing lesson list before the create form, so it is
            # visible immediately rather than below the page fold.
            filters.pack_configure(before=chooser)
            list_frame.pack_configure(before=chooser)
            navigation.pack_configure(before=chooser)
            return
        def delete(i):
            if messagebox.askyesno('Xóa','Xóa mục này?'):
                items=self._levels(kind);items.pop(i)
                save_rows(self.curriculum.data_dir,kind,items);self.curriculum.reload();self.level_editor(kind)
        self._content_table(body, list(enumerate(self._levels(kind))),
            [('Chủ đề', lambda o: display_name(self.curriculum.data_dir, 'theme', o.get('theme',''))),
             ('Level', lambda o: self._display_name('level', o.get('theme',''), o.get('level',''))),
             ('Lesson', lambda o: self._display_name('lesson', o.get('theme',''), o.get('level',''), o.get('lesson',1))),
             ('Tên / nội dung', lambda o: o.get('title') or o.get('word') or o.get('content',''))],
            fill, delete)
