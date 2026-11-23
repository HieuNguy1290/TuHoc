from tuhoc.exercises.exercise_gfx import open_exercise_window
"""Two additive underline exercise types: image choice and sentence word selection."""
import re
from pathlib import Path

TYPES = ('image_underline_choice', 'sentence_underline_words')
TOKEN = re.compile(r'\S+')

def _answers(question):
    values = question.get('answers')
    if isinstance(values, (list, tuple, set)):
        return [str(v) for v in values]
    return [str(question.get('answer', ''))]

def _multiple(question):
    return question.get('answer_mode') == 'multiple' or isinstance(question.get('answers'), (list, tuple, set)) and len(question['answers']) > 1

def expected(question):
    if question.get('type') == TYPES[0]:
        answers = _answers(question)
        return answers if _multiple(question) else answers[0]
    return sorted(set(int(i) for i in question.get('correct_word_indices', [])))

def correct(question, response):
    if question.get('type') == TYPES[0]:
        expected_values = set(_answers(question))
        if _multiple(question):
            return isinstance(response, (list, tuple, set)) and set(str(x) for x in response) == expected_values
        return str(response) == next(iter(expected_values))
    try:
        return isinstance(response, (list, tuple, set)) and sorted(set(int(i) for i in response)) == expected(question)
    except (ValueError, TypeError):
        return False

def build_editor(parent, kind, original, import_media, resolve_media=None):
    import tkinter as tk
    from tkinter import filedialog
    def label(text):
        tk.Label(parent,text=text,bg='white',fg='#285D40',anchor='w').pack(fill='x',pady=(8,3))
    if kind == TYPES[0]:
        label('Ảnh câu hỏi (bắt buộc)')
        row=tk.Frame(parent,bg='white');row.pack(fill='x')
        photo=tk.Entry(row,font=('Segoe UI',11));photo.pack(side='left',fill='x',expand=True)
        photo.insert(0,original.get('image',''))
        def browse():
            filename=filedialog.askopenfilename(parent=parent.winfo_toplevel(),filetypes=[('Hình ảnh','*.png *.jpg *.jpeg *.gif *.webp')])
            if filename:photo.delete(0,'end');photo.insert(0,import_media(filename))
        tk.Button(row,text='Chọn / thay ảnh',command=browse).pack(side='left',padx=6)
        label('Các đáp án (2–8); đánh dấu đáp án đúng')
        initial=original.get('options') or ['quả cam','cây mít','quả táo','quả mít','quả sầu riêng']
        saved_answers = _answers(original)
        saved_mode = 'multiple' if _multiple(original) else 'single'
        mode = tk.StringVar(master=parent, value=saved_mode)
        chosen = set(i for i, v in enumerate(initial) if str(v) in saved_answers)
        if not chosen: chosen.add(0)
        label('Chế độ đáp án đúng')
        modes = tk.Frame(parent, bg='white');modes.pack(anchor='w')
        tk.Radiobutton(modes, text='Chỉ 1 đáp án đúng', variable=mode, value='single', bg='white').pack(side='left')
        tk.Radiobutton(modes, text='Cho phép nhiều đáp án đúng', variable=mode, value='multiple', bg='white').pack(side='left', padx=14)
        rows=[]
        holder=tk.Frame(parent,bg='white');holder.pack(fill='x')
        def refresh():
            for i,(var,_,_) in enumerate(rows):
                var.set(i in chosen)
        def toggle(index):
            if mode.get() == 'single':
                chosen.clear();chosen.add(index)
            elif index in chosen: chosen.remove(index)
            else: chosen.add(index)
            refresh()
        def mode_changed(*_):
            if mode.get() == 'single' and len(chosen)>1:
                first=min(chosen);chosen.clear();chosen.add(first)
            refresh()
        mode.trace_add('write', mode_changed)
        def add(value=''):
            i=len(rows);r=tk.Frame(holder,bg='white');r.pack(fill='x',pady=2)
            checked=tk.BooleanVar(master=parent,value=i in chosen)
            tk.Checkbutton(r,variable=checked,bg='white',command=lambda index=i:toggle(index)).pack(side='left')
            e=tk.Entry(r,font=('Segoe UI',11));e.pack(side='left',fill='x',expand=True);e.insert(0,value)
            rows.append((checked,e,r))
        for v in initial:add(str(v))
        tk.Button(parent,text='+ Thêm phương án',command=lambda:add() if len(rows)<8 else None).pack(anchor='w',pady=5)
        def collect():
            values=[e.get().strip() for _,e,_ in rows]
            if not 2<=len([v for v in values if v])<=8:raise ValueError('Cần từ 2 đến 8 phương án.')
            if any(not v for v in values):raise ValueError('Không để trống phương án ở giữa; hãy nhập đủ các ô đã thêm.')
            if len(set(values))!=len(values):raise ValueError('Các phương án không được trùng nhau.')
            if not chosen:raise ValueError('Cần đánh dấu ít nhất một đáp án đúng.')
            if mode.get() == 'single' and len(chosen)!=1:raise ValueError('Chế độ một đáp án chỉ được chọn một đáp án đúng.')
            ref=photo.get().strip()
            if not ref:raise ValueError('Cần chọn ảnh câu hỏi.')
            if resolve_media and not Path(resolve_media(ref) or '').is_file():raise ValueError('Không tìm thấy ảnh câu hỏi.')
            answers=[values[i] for i in sorted(chosen)]
            result={'type':kind,'image':ref,'options':values,'answer':answers[0],'answer_mode':mode.get()}
            if mode.get()=='multiple':result['answers']=answers
            return result
        return collect
    label('Nội dung câu (các từ hiển thị cách nhau như câu bình thường)')
    sentence=tk.Text(parent,height=3,wrap='word',font=('Segoe UI',11));sentence.pack(fill='x')
    sentence.insert('1.0',original.get('source_text','Em đi học trên máy bay.'))
    label('Nhấp từng từ để đánh dấu đáp án đúng')
    holder=tk.Frame(parent,bg='white');holder.pack(fill='x')
    selected=set(original.get('correct_word_indices') or [])
    def render(*_):
        for child in holder.winfo_children():child.destroy()
        words=TOKEN.findall(sentence.get('1.0','end-1c'))
        selected.intersection_update(range(len(words)))
        # Natural word spacing: 4px gap, no large card padding.
        line=tk.Frame(holder,bg='white');line.pack(anchor='w',fill='x')
        for i,word in enumerate(words):
            def toggle(index=i):
                if index in selected:selected.remove(index)
                else:selected.add(index)
                render()
            tk.Button(line,text=word,command=toggle,bd=0,relief='flat',padx=2,pady=2,
                bg='#E4F1FF' if i in selected else 'white',fg='#1764A0' if i in selected else '#26394B',
                font=('Segoe UI',11,'underline' if i in selected else 'normal')).pack(side='left',padx=0)
    sentence.bind('<KeyRelease>',render,add='+');render()
    def collect():
        source=sentence.get('1.0','end-1c').strip()
        if len(TOKEN.findall(source))<2:raise ValueError('Câu phải có ít nhất 2 từ.')
        if not selected:raise ValueError('Cần đánh dấu ít nhất một từ đúng.')
        return {'type':kind,'source_text':source,'correct_word_indices':sorted(selected),'options':[], 'answer':' | '.join(TOKEN.findall(source)[i] for i in sorted(selected))}
    return collect

def run(question):
    import pygame
    from tuhoc.exercises.pygame_exercises import _cached_font, _image
    from tuhoc.studio.question_layout_runtime import element as layout_element
    from tuhoc.studio.layout_scroll_extent import content_bottom as layout_content_bottom
    pygame.init();pygame.display.init()
    screen=open_exercise_window((960, 640));pygame.display.set_caption('Tự Học - Bài tập')
    clock=pygame.time.Clock();font=_cached_font(None,24,False);title=_cached_font(None,28,True);small=_cached_font(None,18,False)
    navy=(36,55,78);green=(39,143,105);bg=(244,249,252)
    kind=question.get('type');words=TOKEN.findall(question.get('source_text',''))
    options=list(question.get('options') or []) if kind==TYPES[0] else words
    chosen=set();picture=None
    if kind==TYPES[0] and question.get('_pygame_image'):
        try:picture=_image(question['_pygame_image'],(500,285))
        except (pygame.error,OSError,ValueError):pass
    def wrap(text,face,max_width):
        result=[];line=''
        for word in text.split():
            candidate=(line+' '+word).strip()
            if face.size(candidate)[0]>max_width and line:result.append(line);line=word
            else:line=candidate
        if line:result.append(line)
        return result
    from tuhoc.exercises.exercise_layout import Page, wrap as flow_wrap, block_top, image_message
    page=Page(screen)
    from tuhoc.studio.layout_typography import TextBlock, resolve_font
    prompt = TextBlock(question.get('prompt') or 'Gạch chân đáp án đúng',
                       layout_element(question, 'question_text'), title, 28, (55, 95, 850), 38)
    prompt_bottom = prompt.bottom
    image_geometry = layout_element(question, 'question_image')
    image_rect = None
    if picture is not None and image_geometry:
        from tuhoc.studio.layout_images import pygame_image
        picture, image_rect, _ = pygame_image(question['_pygame_image'], image_geometry,
                                               (0, 0, *picture.get_size()))
    # Optional layout applies to the answer group; without it, preserve legacy geometry.
    answer_layout = layout_element(question, 'answer_area')
    answer_left = max(25, min(875, int(answer_layout.get('x', 58)))) if answer_layout else 58
    answer_width = max(80, min(920-answer_left, int(answer_layout.get('width', 837)))) if answer_layout else 837
    answer_right = answer_left + answer_width
    font = resolve_font(answer_layout, font, 24)
    # Lay out each clickable word/option first; draw and hit-test the same boxes.
    rows=[]; x=answer_left; row_y=0
    for i,word in enumerate(options):
        suffix=(', ' if i<len(options)-1 else '.') if kind==TYPES[0] else ' '
        word_lines=flow_wrap(word,font,max(40,answer_width-12))
        width=max(font.size(line)[0] for line in word_lines)
        suffix_width=font.size(suffix)[0]
        if x+width+suffix_width>answer_right and x>answer_left:
            x=answer_left;row_y=max(r[1]+r[4] for r in rows)+12
        height=len(word_lines)*(font.get_height()+6)-6
        rows.append((x,row_y,i,word_lines,height,suffix,width))
        x+=width+suffix_width
        if len(word_lines)>1:
            x=answer_left;row_y+=height+12
    answer_height=max((r[1]+r[4] for r in rows),default=42)
    note=image_message(question,picture)
    image_height=picture.get_height()+22 if picture else 32 if note else 0
    group_top=block_top(prompt_bottom,image_height+answer_height)
    answer_y=group_top+image_height
    if answer_layout and 'y' in answer_layout:
        answer_y = max(65, int(answer_layout['y']))
    adjusted = []
    for x, dy, i, lines, height, suffix, width in rows:
        item = layout_element(question, f'option_{i}') or {}
        face = resolve_font(item, font, 24)
        if item:
            x = item.get('x', x)
            dy = item.get('y', answer_y+dy) - answer_y
            item_width = max(1, item.get('width', answer_width))
            lines = flow_wrap(options[i], face, item_width)
            width = max(face.size(line)[0] for line in lines)
            height = len(lines)*(face.get_height()+6)-6
        adjusted.append((x, dy, i, lines, item.get('height', height), suffix,
                         item.get('width', width), face, bool(item)))
    rows = adjusted
    answer_height = max((dy+height for _,dy,_,_,height,_,_,_,_ in rows), default=42)
    button_y = 552
    # Extend the scrollable drawing surface for elements placed below the page.
    content_extent = layout_content_bottom(question, max(640, answer_y + answer_height + 98))
    try:
        while True:
            screen=page.begin(content_extent)
            screen.fill(bg);pygame.draw.rect(screen,(255,255,255),(25,25,910,screen.get_height()-50),border_radius=18)
            prompt.draw(screen, navy)
            if picture:screen.blit(picture,image_rect or picture.get_rect(midtop=(480,group_top)))
            elif note:screen.blit(small.render(note,True,navy),(55,group_top))
            hit=[]
            # Layout with natural word spacing (9px), preserving compact sentences.
            for x, dy, i, word_lines, height, suffix, width, face, custom in rows:
                top = answer_y+dy
                bounds = pygame.Rect(x, top, max(1, width), max(1, height))
                clip = screen.get_clip()
                if custom:
                    screen.set_clip(clip.clip(bounds))
                    hit.append((bounds, i))
                try:
                    for j, line in enumerate(word_lines):
                        y = top+j*(face.get_height()+6)
                        rendered = face.render(line, True, green if i in chosen else navy)
                        screen.blit(rendered, (x,y))
                        if i in chosen:
                            underline = y+face.get_height()+2
                            pygame.draw.line(screen, green, (x,underline),
                                             (x+rendered.get_width(),underline), 2)
                        if not custom:
                            hit.append((pygame.Rect(x-2,y-3,rendered.get_width()+4,face.get_height()+9),i))
                finally:
                    if custom:
                        screen.set_clip(clip)
                if kind==TYPES[0] and word_lines:
                    y = top + (len(word_lines)-1)*(face.get_height()+6)
                    screen.blit(face.render(suffix,True,navy),(x+face.size(word_lines[-1])[0],y))
            button=pygame.Rect(704,button_y,200,46)
            page.present(question)
            page.complete(question, button, small, bool(chosen))
            regions = None
            if question.get('_studio_scene'):
                from tuhoc.studio.studio_live_preview import enclosing, option_rects, text_rect
                word_regions = {}
                for rect, index in hit:
                    word_regions[index] = word_regions[index].union(rect) if index in word_regions else rect
                regions = {'question_text': text_rect(prompt),
                           'question_image': (image_rect or picture.get_rect(midtop=(480, group_top))) if picture else None,
                           'answer_area': enclosing(word_regions.values())}
                regions.update(option_rects((rect, i) for i, rect in word_regions.items()))
            page.frame(question, regions)
            for event in page.events():
                if event.type==pygame.QUIT:return None
                if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:return None
                if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                    if button.collidepoint(event.viewport_pos):
                        if chosen:
                            return ([options[i] for i in sorted(chosen)] if _multiple(question) else options[next(iter(chosen))]) if kind==TYPES[0] else sorted(chosen)
                        continue
                    for rect,i in hit:
                        if rect.collidepoint(event.pos):
                            if kind==TYPES[0] and not _multiple(question):chosen=set() if i in chosen else {i}
                            elif i in chosen:chosen.remove(i)
                            else:chosen.add(i)
                            break
            clock.tick(45)
    finally:
        pass  # Session worker owns the shared SDL display
