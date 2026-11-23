from tuhoc.exercises.exercise_buttons import draw_complete
from tuhoc.exercises.exercise_gfx import draw_question_progress
from tuhoc.exercises.exercise_gfx import open_exercise_window
"""Isolated authoring, validation and Pygame display for three multi-answer exercises."""
from pathlib import Path

TYPES = frozenset(('image_multi_select', 'text_multi_select', 'audio_multi_select'))

def expected_answers(question):
    answer = question.get('answers') or question.get('answer', [])
    if isinstance(answer, str):
        answer = [s.strip() for s in answer.split('|') if s.strip()]
    return list(answer)

def is_correct(question, selected):
    if not isinstance(selected, (list, tuple, set)):
        return False
    correct = expected_answers(question)
    return bool(correct) and len(selected) == len(correct) and set(selected) == set(correct)

def validate(question):
    options = question.get('options', [])
    answers = expected_answers(question)
    if not 2 <= len(options) <= 8 or any(not str(x).strip() for x in options):
        raise ValueError('Cần từ 2 đến 8 phương án không để trống.')
    if len(set(options)) != len(options):
        raise ValueError('Các phương án không được trùng nhau.')
    if len(answers) < 2 or len(answers) > len(options) or len(set(answers)) != len(answers):
        raise ValueError('Cần ít nhất 2 đáp án đúng; có thể chọn toàn bộ phương án nếu chỉ có 2.')
    if not set(answers).issubset(options):
        raise ValueError('Đáp án đúng phải nằm trong danh sách phương án.')
    if question['type'] == 'image_multi_select' and not question.get('image'):
        raise ValueError('Dạng nhìn hình cần chọn hình ảnh.')
    if question['type'] == 'audio_multi_select' and not question.get('audio'):
        raise ValueError('Dạng nghe cần chọn tệp âm thanh.')
    return question

def build_editor(parent, kind, original, import_media, resolve_media=None):
    import tkinter as tk
    from tkinter import filedialog
    bg='white'; rows=[]
    def label(text):
        tk.Label(parent,text=text,bg=bg,fg='#285D40',anchor='w',font=('Segoe UI',10)).pack(fill='x',pady=(8,3))
    def media_field(field, caption, patterns):
        label(caption)
        bar=tk.Frame(parent,bg=bg);bar.pack(fill='x')
        entry=tk.Entry(bar,font=('Segoe UI',11));entry.pack(side='left',fill='x',expand=True)
        entry.insert(0,original.get(field,'') or '')
        def browse():
            filename=filedialog.askopenfilename(parent=parent.winfo_toplevel(),filetypes=patterns)
            if filename:
                entry.delete(0,'end');entry.insert(0,import_media(filename))
        tk.Button(bar,text='Chọn tệp',command=browse).pack(side='left',padx=6)
        return entry
    image=media_field('image','Hình ảnh câu hỏi',[('Hình ảnh','*.png *.jpg *.jpeg *.gif *.webp')]) if kind=='image_multi_select' else None
    audio=media_field('audio','Âm thanh câu hỏi',[('Âm thanh','*.mp3 *.wav *.ogg')]) if kind=='audio_multi_select' else None
    if kind=='text_multi_select':
        label('Đoạn văn đọc (không bắt buộc)')
        passage=tk.Text(parent,height=4,wrap='word',font=('Segoe UI',11));passage.pack(fill='x')
        passage.insert('1.0',original.get('passage','') or '')
    else:passage=None
    label('Đánh dấu ô vuông cho TẤT CẢ đáp án đúng (tối thiểu 2).')
    options=original.get('options') or ['','','','']
    correct=set(expected_answers(original))
    for i in range(8):
        row=tk.Frame(parent,bg=bg);row.pack(fill='x',pady=3)
        mark=tk.BooleanVar(master=parent,value=i<len(options) and options[i] in correct)
        tk.Checkbutton(row,text=chr(65+i),variable=mark,bg=bg).pack(side='left')
        field=tk.Entry(row,font=('Segoe UI',11));field.pack(side='left',fill='x',expand=True)
        if i<len(options):field.insert(0,str(options[i]))
        rows.append((mark,field))
    label('Chỉ nhập các phương án cần dùng, từ 2 đến 8; các ô cuối có thể để trống.')
    def collect():
        values=[];answers=[];seen_blank=False
        for marked,field in rows:
            value=field.get().strip()
            if not value:
                seen_blank=True
                if marked.get():raise ValueError('Không thể đánh dấu một phương án trống.')
                continue
            if seen_blank:raise ValueError('Hãy nhập phương án liên tiếp, không bỏ trống ở giữa.')
            values.append(value)
            if marked.get():answers.append(value)
        result={'options':values,'answers':answers,'answer':' | '.join(answers),
                'image':image.get().strip() if image else '',
                'audio':audio.get().strip() if audio else '',
                'passage':passage.get('1.0','end-1c').strip() if passage else '' , 'type':kind}
        validate(result)
        field = image if image else audio
        if field and resolve_media:
            path=resolve_media(field.get().strip())
            if not path or not Path(path).is_file():raise ValueError('Không tìm thấy tệp media đã chọn.')
        return result
    return collect

def run(question):
    """Return a list of selected option texts, or None on cancel."""
    import pygame
    from tuhoc.exercises.pygame_exercises import _image, _cached_font
    pygame.init();pygame.display.init()
    screen=open_exercise_window((960, 640))
    pygame.display.set_caption('Tự Học - Bài tập')
    clock=pygame.time.Clock()
    title=_cached_font(None,25,True); font=_cached_font(None,22,False);small=_cached_font(None,17,False)
    opts=list(question.get('options',[]));selected=set()
    picture=None
    if question.get('_pygame_image'):
        try:
            path=question.get('_pygame_image')
            if path:picture=_image(path,(420,185))
        except (OSError,ValueError,pygame.error):pass
    audio_path=question.get('_resolved_audio') or question.get('_pygame_audio')
    playing=False;audio_ready=False
    if question['type']=='audio_multi_select' and audio_path:
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(str(audio_path));audio_ready=True
        except (pygame.error,OSError):pass
    def wrapped(text,face,width):
        result=[]
        for paragraph in str(text).split('\n'):
            line=''
            for word in paragraph.split():
                if face.size((line+' '+word).strip())[0]>width and line:
                    result.append(line);line=word
                else:line=(line+' '+word).strip()
            result.append(line)
        return result
    from tuhoc.exercises.exercise_layout import Page, wrap as flow_wrap, block_top, image_message
    page=Page(screen)
    from tuhoc.studio.layout_typography import TextBlock, resolve_font
    from tuhoc.studio.question_layout_runtime import element as layout_element, rectangle
    prompt = TextBlock(question.get('prompt', ''), layout_element(question, 'question_text'),
                       font, 22, (54, 90, 850), 28)
    prompt_bottom = prompt.bottom
    kind=question['type']
    note=image_message(question,picture) if kind=='image_multi_select' else ''
    passage=flow_wrap(str(question.get('passage','')).strip(),small,835) if kind=='text_multi_select' and str(question.get('passage','')).strip() else []
    base_media_height=(picture.get_height()+22 if picture else 32 if note else 0) if kind=='image_multi_select' else 88 if kind=='audio_multi_select' else len(passage)*23+(18 if passage else 0)
    media_height=base_media_height+(picture.get_height()+12 if picture is not None and kind!='image_multi_select' else 0)
    card_lines=[flow_wrap(str(opt),font,365) for opt in opts]
    row_heights=[max(55,max((len(v)*(font.get_height()+6)+14 for v in card_lines[i:i+2]),default=55)) for i in range(0,len(opts),2)]
    answer_height=sum(h+9 for h in row_heights)
    # Optional per-option geometry; legacy questions retain their existing layout.
    picture_layout = layout_element(question, 'question_image')
    picture_rect = None
    if picture is not None and picture_layout:
        from tuhoc.studio.layout_images import pygame_image
        picture, picture_rect, _ = pygame_image(question['_pygame_image'], picture_layout,
                                                             (0, 0, *picture.get_size()))
    option_layouts = [layout_element(question, "option_%d" % i) for i in range(len(opts))]
    answer_area = layout_element(question, 'answer_area') or {}
    option_fonts = [resolve_font({**answer_area, **(geometry or {})}, font, 22) for geometry in option_layouts]
    option_lines = [flow_wrap(str(opt), option_fonts[i],
                    max(30, (v["width"] if v and "width" in v else 433) - 54))
                    for i, (opt, v) in enumerate(zip(opts, option_layouts))]
    group_top=block_top(prompt_bottom,media_height+answer_height)
    answer_x = answer_area.get('x', 54)
    answer_top = answer_area.get('y', group_top+media_height)
    if (question.get('layout') or {}).get('version') == 4 and 'height' in answer_area:
        height = max(1, (answer_area['height'] - max(0, len(row_heights)-1)*9)//max(1, len(row_heights)))
        row_heights = [height for _ in row_heights]
        answer_height = sum(row_heights) + 9*max(0,len(row_heights)-1)
    column_width = max(45, (answer_area.get('width', 886) - 20) // 2)
    passage_box = TextBlock(question.get('passage', ''), layout_element(question, 'answer_passage'),
                            small, 17, (56, group_top, 835), 23)
    submit_y=max(574,answer_top+answer_height+24)
    # Keep the fixed submit button below independently positioned options.
    # Its position is not editable; only the scrollable page grows if needed.
    custom_bottom = max((v.get('y', 0) + v.get('height', row_heights[i//2])
                         for i, v in enumerate(option_layouts) if v), default=0)
    play_rect = pygame.Rect(rectangle(layout_element(question, 'audio_player'), (54, group_top, 240, 58)))
    # Build 03C.8: content may extend beyond the viewport after layout editing.
    # Page already converts pointer events to content coordinates.
    from tuhoc.studio.layout_scroll_extent import content_bottom as layout_content_bottom
    content_end = layout_content_bottom(question, max(submit_y + 46, custom_bottom + 20))
    fixed_submit = pygame.Rect(715, 574, 210, 46)
    try:
        while True:
            screen=page.begin(content_end)
            screen.fill((242,248,252))
            screen.blit(title.render('Tự Học - Bài tập',True,(34,51,78)),(52,33))
            prompt.draw(screen, (34, 51, 78))
            y=answer_top
            rendered_image = None
            if picture is not None:
                rendered_image = picture_rect or picture.get_rect(midtop=(480, group_top + (0 if kind == 'image_multi_select' else base_media_height)))
                screen.blit(picture, rendered_image)
            if kind == 'image_multi_select':
                if not picture and note:screen.blit(small.render(note,True,(175,65,65)),(54,group_top))
            elif question['type']=='audio_multi_select':
                play=play_rect
                pygame.draw.rect(screen,(204,232,255),play,border_radius=12)
                screen.blit(font.render('▶  Nghe lại' if audio_ready else 'Không có âm thanh',True,(29,78,123)),(play_rect.x+15,play_rect.y+17))
            else:
                passage_box.draw(screen, (70, 88, 106))
            cells=[]
            for i,opt in enumerate(opts):
                col=i%2;row=i//2
                rect=pygame.Rect(answer_x+col*(column_width+20),y+sum(h+9 for h in row_heights[:row]),column_width,row_heights[row])
                custom = option_layouts[i]
                if custom:
                    rect = pygame.Rect(custom.get('x', rect.x), custom.get('y', rect.y),
                                       custom.get('width', rect.width), custom.get('height', rect.height))
                item_font = option_fonts[i]
                pygame.draw.rect(screen,(210,235,255) if i in selected else 'white',rect,border_radius=9)
                pygame.draw.rect(screen,(45,130,204) if i in selected else (187,201,213),rect,2,border_radius=9)
                mark=pygame.Rect(rect.x+12,rect.y+(rect.height-22)//2,22,22)
                pygame.draw.rect(screen,(45,130,204) if i in selected else 'white',mark,border_radius=4)
                pygame.draw.rect(screen,(45,130,204),mark,2,border_radius=4)
                if i in selected:screen.blit(small.render('✓',True,'white'),(mark.x+4,mark.y))
                lines = option_lines[i] if custom else card_lines[i]
                for line_no,line in enumerate(lines):
                    text_y = rect.y + 10 + line_no*(item_font.get_height()+6)
                    if text_y + item_font.get_height() <= rect.bottom:
                        screen.blit(item_font.render(line,True,(35,54,76)),(rect.x+44,text_y))
                cells.append((rect,i))
            screen.blit(small.render('Chọn nhiều ô, bấm lại để bỏ chọn.',True,(93,111,128)),(54,submit_y+14))
            page.present(question)
            # Fixed controls are drawn onto the viewport, not the scrolling page.
            mouse=pygame.mouse.get_pos()
            draw_complete(page.display, fixed_submit, font, bool(selected),
                          fixed_submit.collidepoint(mouse), pygame.mouse.get_pressed()[0])
            draw_question_progress(page.display, question)
            regions = None
            if question.get('_studio_scene'):
                from tuhoc.studio.studio_live_preview import enclosing, option_rects, text_rect
                regions = {'question_text': text_rect(prompt),
                           'answer_area': enclosing(rect for rect, _ in cells),
                           'audio_player': play_rect if kind == 'audio_multi_select' else None,
                           'answer_passage': text_rect(passage_box) if kind == 'text_multi_select' else None,
                           'question_image': rendered_image}
                regions.update(option_rects(cells))
            page.frame(question, regions)
            for event in page.events():
                if event.type==pygame.QUIT:return None
                if event.type==pygame.KEYDOWN:
                    if event.key==pygame.K_ESCAPE:return None
                    if event.key==pygame.K_PAGEUP:
                        page.scroll=max(0,page.scroll-320)
                    elif event.key==pygame.K_PAGEDOWN:
                        page.scroll=min(page.limit,page.scroll+320)
                if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                    # Page.events() supplies content coordinates; recover the
                    # viewport point only for the fixed completion button.
                    viewport_pos=event.viewport_pos
                    if fixed_submit.collidepoint(viewport_pos):
                        if selected:
                            return [opt for i,opt in enumerate(opts) if i in selected]
                        continue
                    if question['type']=='audio_multi_select' and play_rect.collidepoint(event.pos) and audio_ready:
                        try:pygame.mixer.music.stop();pygame.mixer.music.play()
                        except pygame.error:pass
                    for rect, i in reversed(cells):
                        if rect.collidepoint(event.pos):
                            if i in selected:selected.remove(i)
                            else:selected.add(i)
                            break
            clock.tick(30)
    finally:
        # Always release the SDL window on the same worker thread that opened it.
        # Without this, Tk's preview may remain waiting on a stale Pygame display.
        if question['type']=='audio_multi_select' and audio_ready:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            except pygame.error:
                pass
        pass  # Session worker owns the shared SDL display
