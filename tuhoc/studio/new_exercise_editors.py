"""Additional question authoring widgets; existing question types are untouched.

These five formats are stored as explicit structured JSON. Runtime rendering/scoring
is deliberately not changed by this editor-only extension.
"""
import re
import tkinter as tk
from tkinter import ttk, filedialog

NEW_TYPES = ('image_multi_choice', 'listening_image_choice', 'picture_missing_letters', 'sentence_gaps', 'conversation_gaps', 'passage_gaps', 'image_multi_select', 'text_multi_select', 'audio_multi_select','image_write_answer','image_underline_choice','sentence_underline_words','dropdown_fill_blank','multi_fill_blanks','image_sentence_fill','image_letter_pick','inline_dropdown_fill')
LABELS = dict(zip(NEW_TYPES, ('Trắc nghiệm đáp án bằng hình (120x80)', 'Nghe – chọn đáp án bằng hình', 'Nhìn hình - điền chữ thiếu', 'Ghép từ vào câu (nhiều chỗ trống)', 'Hoàn thành hội thoại', 'Hoàn thành đoạn văn', 'Nhìn hình – chọn nhiều đáp án', 'Đọc – chọn nhiều đáp án', 'Nghe – chọn nhiều đáp án', 'Nhìn hình – ghi đáp án', 'Nhìn hình – gạch chân đáp án', 'Gạch chân từ trong câu', 'Chọn đáp án từ danh sách thả xuống', 'Điền nhiều ô trống (nhập số/chữ)', 'Nhìn hình – bấm từ điền chỗ chấm', 'Nhìn hình – bấm chọn chữ cái thiếu', 'Chọn đáp án thả xuống ngay trong câu')))
TOKEN = re.compile(r'\S+')


def build(parent, kind, original, import_media, resolve_media=None):
    """Return a callable collecting and validating the edited question fields."""
    bg = 'white'
    from tuhoc.studio.exercise_authoring_help import add_help_icon
    add_help_icon(parent, kind, LABELS)
    def title(s):
        tk.Label(parent, text=s, bg=bg, fg='#285D40', anchor='w').pack(fill='x', pady=(9, 3))
    def entry(label, initial='', width=55):
        title(label)
        e = tk.Entry(parent, width=width, font=('Segoe UI', 11)); e.pack(fill='x')
        e.insert(0, initial or '')
        return e
    def textarea(label, initial='', height=4):
        title(label)
        t = tk.Text(parent, height=height, wrap='word', font=('Segoe UI', 11)); t.pack(fill='x')
        t.insert('1.0', initial or '')
        return t
    def value(t): return t.get('1.0', 'end-1c') if isinstance(t, tk.Text) else t.get().strip()
    def image(label, initial=''):
        e = entry(label, initial)
        def browse():
            f = filedialog.askopenfilename(parent=parent.winfo_toplevel(), filetypes=[('Ảnh','*.png *.jpg *.jpeg *.gif *.webp')])
            if f:
                e.delete(0,'end'); e.insert(0,import_media(f))
        tk.Button(parent, text='Chọn / thay ảnh', command=browse).pack(anchor='w', pady=3)
        return e
    def tokens_widget(label, text_widget, initial=None, letters=False):
        from tuhoc.studio.token_picker import TokenPicker
        title(label)
        picker = TokenPicker(parent, text_widget, value, initial, letters=letters)
        picker.pack(fill='x', pady=5)
        return picker
    if kind == 'inline_dropdown_fill':
        from tuhoc.exercises.inline_dropdown_extension import build_editor
        return build_editor(parent, original, import_media, resolve_media)
    if kind == 'image_letter_pick':
        from tuhoc.exercises.image_letter_pick_extension import build_editor
        return build_editor(parent, original, import_media, resolve_media)
    if kind == 'image_sentence_fill':
        from tuhoc.exercises.image_sentence_extension import build_editor
        return build_editor(parent, original, import_media, resolve_media)
    if kind == 'multi_fill_blanks':
        from tuhoc.exercises.multi_fill_blanks_extension import build_editor
        return build_editor(parent, original, import_media, resolve_media)
    if kind == 'dropdown_fill_blank':
        from tuhoc.exercises.dropdown_extension import build_editor
        return build_editor(parent, original, import_media, resolve_media)
    if kind in ('image_underline_choice','sentence_underline_words'):
        from tuhoc.exercises.underline_extension import build_editor
        return build_editor(parent, kind, original, import_media, resolve_media)
    if kind == 'image_write_answer':
        from tuhoc.exercises.image_write_extension import build_editor
        return build_editor(parent, original, import_media, resolve_media)
    if kind in ('image_multi_select','text_multi_select','audio_multi_select'):
        from tuhoc.exercises.multi_select_extension import build_editor
        return build_editor(parent, kind, original, import_media, resolve_media)
    if kind == 'listening_image_choice':
        from tuhoc.exercises.listening_image_extension import build_editor
        return build_editor(parent, original, import_media, resolve_media)
    if kind=='image_multi_choice':
        title('Ảnh đáp án hiển thị cố định 120 x 80 px, giữ tỷ lệ và căn giữa')
        title('Chọn từ 2 đến 4 ảnh; có thể để trống các ô cuối.')
        options=original.get('image_options') or [{'image':x} for x in original.get('options',[]) if x]
        rows=[]
        correct=tk.IntVar(master=parent,value=int(original.get('correct_index',0)))
        thumbnails=[]
        def resolve(ref):
            try:
                path=resolve_media(ref) if resolve_media else None
                return path if path and __import__('pathlib').Path(path).is_file() else None
            except (OSError,ValueError,TypeError):return None
        def refresh_image(field, label):
            ref=value(field)
            path=resolve(ref)
            if not path:
                label.configure(image='',text='Chưa có ảnh' if not ref else 'Không tìm thấy ảnh')
                label.image=None
                return
            try:
                from PIL import Image,ImageTk
                with Image.open(path) as source:
                    pic=source.convert('RGBA');pic.thumbnail((120,80),Image.Resampling.LANCZOS)
                photo=ImageTk.PhotoImage(pic,master=label)
                label.configure(image=photo,text='');label.image=photo
            except (OSError,ValueError,ImportError):
                label.configure(image='',text='Không đọc được ảnh');label.image=None
        def pick(field, label):
            f=filedialog.askopenfilename(parent=parent.winfo_toplevel(),filetypes=[('Ảnh','*.png *.jpg *.jpeg *.gif *.webp')])
            if f:
                field.delete(0,'end');field.insert(0,import_media(f))
                refresh_image(field,label)
        for i in range(4):
            row=tk.Frame(parent,bg=bg);row.pack(fill='x',pady=3)
            tk.Radiobutton(row,text=chr(65+i),variable=correct,value=i,bg=bg).pack(side='left')
            e=tk.Entry(row,font=('Segoe UI',10));e.pack(side='left',fill='x',expand=True)
            if i<len(options):
                opt=options[i]
                e.insert(0,opt.get('image','') if isinstance(opt,dict) else str(opt))
            preview=tk.Label(row,text='Chưa có ảnh',width=18,height=5,bg='#F1F5F8',fg='#496175')
            preview.pack(side='left',padx=5)
            tk.Button(row,text='Chọn ảnh',command=lambda field=e,label=preview:pick(field,label)).pack(side='left')
            e.bind('<FocusOut>',lambda event,field=e,label=preview:refresh_image(field,label),add='+')
            rows.append(e);thumbnails.append(preview)
            refresh_image(e,preview)
        def collect():
            paths=[value(e) for e in rows]
            if sum(bool(p) for p in paths)<2:raise ValueError('Cần ít nhất 2 ảnh đáp án.')
            if paths != [p for p in paths if p] + [''] * paths.count(''):
                raise ValueError('Hãy nhập ảnh liên tiếp từ A, không bỏ trống ở giữa.')
            paths=[p for p in paths if p]
            if len(set(paths))!=len(paths):raise ValueError('Các ảnh đáp án không được trùng nhau.')
            for i,ref in enumerate(paths):
                if not resolve(ref):raise ValueError(f'Không tìm thấy ảnh đáp án {chr(65+i)}: {ref}')
            selected=correct.get()
            if selected not in range(len(paths)):raise ValueError('Hãy chọn một đáp án đúng trong các ảnh đã nhập.')
            return {'image_options':[{'image':p} for p in paths], 'options':paths,'answer':paths[selected], 'correct_index':selected,'image_size':[120,80]}
    elif kind=='picture_missing_letters':
        pic=image('Ảnh câu hỏi',original.get('image',''))
        word=entry('Đáp án hoàn chỉnh',original.get('answer','PIZZA'))
        hidden=tokens_widget('Click các chữ cần ẩn (click lại để bỏ ẩn)',word,original.get('hidden_indices',[0,2]),True)
        def collect():
            w=value(word).strip()
            indices = hidden.indices()
            if not w or not indices:raise ValueError('Cần đáp án và ít nhất một chữ được ẩn.')
            if not value(pic):raise ValueError('Cần chọn ảnh câu hỏi.')
            return {'image':value(pic),'answer':w,'hidden_indices':indices,'options':[]}
    elif kind in ('sentence_gaps','passage_gaps'):
        illustration=image('Hình minh họa (không bắt buộc)' ,original.get('image','')) if kind=='sentence_gaps' else None
        source=textarea('Câu hoàn chỉnh' if kind=='sentence_gaps' else 'Nội dung đoạn văn',original.get('source_text') or original.get('answer') or '',5 if kind=='passage_gaps' else 3)
        hidden=tokens_widget('Click từng từ muốn ẩn (chọn nhiều từ; click lại để bỏ)',source,original.get('hidden_indices',[]))
        distract=entry('Đáp án nhiễu (phân cách bằng |)', ' | '.join(original.get('distractors',[])))
        def collect():
            text=value(source).strip(); tokens=TOKEN.findall(text)
            indices = hidden.indices()
            if not text or not indices:raise ValueError('Cần nội dung và ít nhất một từ cần ẩn.')
            choices=[tokens[i] for i in indices]+[x.strip() for x in value(distract).split('|') if x.strip()]
            result={'source_text':text,'hidden_indices':indices,'distractors':[x.strip() for x in value(distract).split('|') if x.strip()], 'options':choices,'answer':text}
            if illustration is not None:result['image']=value(illustration)
            return result
    else:
        title('Mỗi hàng là một lượt thoại. Chọn nhân vật, nhập hội thoại và click các từ cần ẩn ở cột thứ ba.')
        area=tk.Frame(parent,bg=bg);area.pack(fill='x')
        rows=[]
        def add(speaker='',speech='',hidden=None):
            line=tk.Frame(area,bg=bg);line.pack(fill='x',pady=5)
            name=tk.Entry(line,width=13);name.pack(side='left',padx=2);name.insert(0,speaker)
            speech_box=tk.Text(line,width=42,height=3,wrap='word');speech_box.pack(side='left',padx=2);speech_box.insert('1.0',speech)
            from tuhoc.studio.token_picker import TokenPicker
            picker = TokenPicker(line, speech_box, value, hidden, columns=4)
            picker.pack(side='left', fill='x', expand=True)
            def remove():line.destroy();rows.remove(record)
            tk.Button(line,text='X',command=remove).pack(side='right')
            record=(name,speech_box,picker);rows.append(record)
        for item in original.get('dialogue',[]):add(item.get('speaker',''),item.get('text',''),item.get('hidden_indices',[]))
        if not rows:add('An','Happy birthday!',[]);add('Phong','Thank you! Do you like the cake?',[0,1])
        tk.Button(parent,text='+ Thêm lượt thoại',command=add).pack(anchor='w',pady=5)
        distract=entry('Đáp án nhiễu (phân cách bằng |)',' | '.join(original.get('distractors',[])))
        def collect():
            dialogue=[];answers=[]
            for name,speech,picker in rows:
                speaker=value(name);text=value(speech).strip();tokens=TOKEN.findall(text)
                if not speaker or not text:raise ValueError('Mỗi lượt thoại cần tên và nội dung.')
                indices = picker.indices()
                dialogue.append({'speaker':speaker,'text':text,'hidden_indices':indices})
                answers.extend(tokens[i] for i in indices)
            if not answers:raise ValueError('Cần chọn ít nhất một từ ẩn trong hội thoại.')
            extras=[x.strip() for x in value(distract).split('|') if x.strip()]
            return {'dialogue':dialogue,'distractors':extras,'options':answers+extras,'answer':' | '.join(answers)}
    return collect
