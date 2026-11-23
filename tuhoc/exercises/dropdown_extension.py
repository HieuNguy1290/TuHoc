from tuhoc.exercises.exercise_gfx import open_exercise_window
"""Dropdown answer: Tk authoring widget and Pygame exercise window."""
from pathlib import Path

def build_editor(parent, original, import_media, resolve_media=None):
    import tkinter as tk
    from tkinter import filedialog, ttk
    def label(text):
        tk.Label(parent,text=text,bg='white',fg='#285D40',anchor='w').pack(fill='x',pady=(9,3))
    from tuhoc.exercises.dropdown_inline_logic import parse as parse_inline, slots as inline_slots
    label('Danh sách lựa chọn (cũ: mỗi dòng một lựa chọn; nhiều ô: dùng chung hoặc |1 lựa chọn 1, lựa chọn 2)')
    opts=original.get('options') or []
    if isinstance(opts,str):opts=opts.split('|')
    field=tk.Text(parent,height=6,font=('Segoe UI',11));field.pack(fill='x')
    field.insert('1.0', original.get('inline_options_text') or '\n'.join(str(x) for x in opts))
    label('Đáp án đúng (cũ: một đáp án; nhiều ô: mỗi dòng một đáp án hoặc |1 đáp án)')
    correct=tk.Text(parent,height=3,font=('Segoe UI',11));correct.pack(fill='x')
    correct.insert('1.0', original.get('inline_answers_text') or str(original.get('answer') or ''))
    label('Hình ảnh minh họa (không bắt buộc)')
    row=tk.Frame(parent,bg='white');row.pack(fill='x')
    image=tk.Entry(row,font=('Segoe UI',11));image.pack(side='left',fill='x',expand=True)
    image.insert(0,str(original.get('image') or ''))
    def browse():
        file=filedialog.askopenfilename(parent=parent.winfo_toplevel(),filetypes=[('Ảnh','*.png *.jpg *.jpeg *.gif *.webp')])
        if file:
            image.delete(0,'end');image.insert(0,import_media(file))
    tk.Button(row,text='Chọn ảnh',command=browse).pack(side='left',padx=5)
    def collect():
        values=[s.strip() for s in field.get('1.0','end-1c').splitlines() if s.strip()]
        answer=correct.get('1.0','end-1c').strip();ref=image.get().strip()
        prompt = collect.prompt_getter() if hasattr(collect,'prompt_getter') else ''
        if prompt and inline_slots(prompt):
            if ref and resolve_media:
                path=resolve_media(ref)
                if not path or not Path(path).is_file(): raise ValueError('Không tìm thấy ảnh minh họa.')
            parsed=parse_inline(prompt,field.get('1.0','end-1c'),answer)
            return {'type':'dropdown_fill_blank','options':values,'answer':' | '.join(parsed['blank_answers']),'image':ref,
                    'inline_options_text':field.get('1.0','end-1c'), 'inline_answers_text':answer, **parsed}
        if not 2<=len(values)<=8:raise ValueError('Cần từ 2 đến 8 lựa chọn.')
        if len(set(values))!=len(values):raise ValueError('Các lựa chọn không được trùng nhau.')
        if answer not in values:raise ValueError('Đáp án đúng phải trùng chính xác một lựa chọn.')
        if ref and resolve_media:
            path=resolve_media(ref)
            if not path or not Path(path).is_file():raise ValueError('Không tìm thấy ảnh minh họa.')
        # Clear multi-blank fields left over from an earlier save of this question.
        return {'type':'dropdown_fill_blank','options':values,'answer':answer,'image':ref,
                'blank_options':None,'blank_answers':None,'inline_options_text':'','inline_answers_text':''}
    return collect

def run(question):
    if question.get('blank_answers') and question.get('blank_options'):
        from tuhoc.exercises.inline_dropdown_extension import run as inline_run
        from tuhoc.exercises.dropdown_inline_logic import display_text
        q=dict(question)
        q['blank_text']=display_text(q.get('prompt',''))
        q['prompt']='Chọn đáp án thích hợp điền vào ô trống.'
        return inline_run(q)
    import pygame
    from tuhoc.exercises.pygame_exercises import _image,_cached_font
    from tuhoc.studio.question_layout_runtime import element as layout_element, rectangle
    from tuhoc.studio.layout_scroll_extent import content_bottom as layout_content_bottom
    pygame.init();pygame.display.init()
    screen=open_exercise_window((960, 640));pygame.display.set_caption('Tự Học - Bài tập')
    clock=pygame.time.Clock();font=_cached_font(None,23,False);small=_cached_font(None,19,False);title=_cached_font(None,28,True)
    navy=(32,52,77);bg=(241,247,252)
    options=question.get('options') or []
    if isinstance(options,str):options=[x.strip() for x in options.split('|') if x.strip()]
    options=[str(x) for x in options]
    selected=None;opened=False;scroll=0
    picture=None
    if question.get('_pygame_image'):
        try:picture=_image(question['_pygame_image'],(460,240))
        except (OSError,ValueError,pygame.error):pass
    def wrapped(text,width):
        lines=[];line=''
        for word in str(text).split():
            trial=(line+' '+word).strip()
            if line and font.size(trial)[0]>width:lines.append(line);line=word
            else:line=trial
        if line:lines.append(line)
        return lines
    from tuhoc.exercises.exercise_layout import Page, wrap, block_top, image_message
    page=Page(screen)
    from tuhoc.studio.layout_typography import TextBlock, resolve_font
    prompt = TextBlock(question.get('prompt') or 'Chọn đáp án thích hợp để điền vào ô trống.',
                       layout_element(question, 'question_text'), font, 23, (55, 96, 850), 33)
    bottom = prompt.bottom
    image_geometry = layout_element(question, 'question_image')
    image_rect = None
    if picture is not None and image_geometry:
        from tuhoc.studio.layout_images import pygame_image
        picture, image_rect, _ = pygame_image(question['_pygame_image'], image_geometry,
                                               (0, 0, *picture.get_size()))
    note=image_message(question,picture)
    media_height=picture.get_height()+22 if picture else 32 if note else 0
    group_top=block_top(bottom,media_height+48)
    field_y=group_top+media_height
    submit_y = 560
    # Optional per-question geometry. The field and its popup share one origin,
    # so pointer hit testing always follows the rendered answer control.
    answer_layout = layout_element(question, 'dropdown_area') if (question.get('layout') or {}).get('version') in (2, 3, 4) else layout_element(question, 'answer_area')
    menu_geometry = layout_element(question, 'answer_menu') or {}
    menu_options = [layout_element(question, f'option_{i}') for i in range(len(options))]
    option_font = resolve_font(answer_layout, small, 19)
    if answer_layout:
        field_x = max(30, min(900, int(answer_layout.get('x', 175))))
        field_y = max(60, int(answer_layout.get('y', field_y)))
        field_width = max(120, min(925-field_x, int(answer_layout.get('width', 340))))
        field_height = max(40, min(90, int(answer_layout.get('height', 48))))
    else:
        field_x, field_width, field_height = 175, 340, 48
    # Reserve space for the expanded popup and any elements placed below the page.
    content_extent = layout_content_bottom(
        question, max(640, field_y+field_height+min(5,len(options))*43+80)
    )
    try:
        while True:
            screen=page.begin(content_extent)
            screen.fill(bg)
            pygame.draw.rect(screen,'white',(25,25,910,screen.get_height()-50),border_radius=18)
            prompt.draw(screen, navy)
            if picture:screen.blit(picture,image_rect or picture.get_rect(midtop=(480,group_top)))
            elif note:screen.blit(small.render(note,True,(140,90,90)),(55,group_top))
            screen.blit(font.render('Trả lời:',True,navy),(max(30,field_x-110),field_y+10))
            field=pygame.Rect(field_x,field_y,field_width,field_height)
            pygame.draw.rect(screen,(247,251,255),field,border_radius=8)
            pygame.draw.rect(screen,(70,119,169),field,2,border_radius=8)
            shown='Chọn đáp án' if selected is None else options[selected]
            while shown and option_font.size(shown)[0]>max(30,field.width-75):shown=shown[:-2]+'…'
            screen.blit(option_font.render(shown,True,navy if selected is not None else (126,138,150)),(field.x+15,field.y+max(5,(field.height-small.get_height())//2)))
            pygame.draw.polygon(screen,navy,[(field.right-34,field.centery-5),(field.right-20,field.centery-5),(field.right-27,field.centery+4)])
            submit=pygame.Rect(690,submit_y,200,45)

            menu=[]
            if opened:
                menu_height_per_row = max(24, int((answer_layout or {}).get('height', 48)) - 5)
                max_visible=min(5,len(options));menu_height=max_visible*menu_height_per_row
                menu_y=field.bottom+3
                if menu_y + menu_height > submit_y - 10 + page.scroll:
                    menu_y = max(bottom+8, field.top-menu_height-3)
                menu_rect = pygame.Rect(rectangle(menu_geometry, (field.x,menu_y,field.width,menu_height)))
                menu_height_per_row = max(1, menu_rect.height // max_visible)
                pygame.draw.rect(screen,'white',menu_rect,border_radius=6)
                pygame.draw.rect(screen,(95,130,167),menu_rect,2,border_radius=6)
                for j in range(scroll,min(len(options),scroll+max_visible)):
                    row_geometry = menu_options[j]
                    rect = pygame.Rect(rectangle(row_geometry, (menu_rect.x+3,
                        menu_rect.y+(j-scroll)*menu_height_per_row, max(1, menu_rect.width-6), menu_height_per_row)))
                    if j==selected:pygame.draw.rect(screen,(223,239,252),rect)
                    val=options[j]
                    row_font = resolve_font(row_geometry, resolve_font(menu_geometry, option_font, 19), 19)
                    while val and row_font.size(val)[0]>rect.width-20:val=val[:-2]+'…'
                    screen.blit(row_font.render(val,True,navy),(rect.x+10,rect.y+11))
                    menu.append((rect,j))
            page.present(question)
            page.complete(question, submit, small, selected is not None)
            regions = None
            if question.get('_studio_scene'):
                from tuhoc.studio.studio_live_preview import option_rects, text_rect
                regions = {'question_text': text_rect(prompt), 'dropdown_area': field,
                           'question_image': (image_rect or picture.get_rect(midtop=(480, group_top))) if picture else None,
                           'answer_menu': menu_rect if opened else None}
                regions.update(option_rects(menu))
            page.frame(question, regions)
            for event in page.events(scroll_enabled=not opened):
                if event.type==pygame.QUIT:return None
                if event.type==pygame.KEYDOWN:
                    if event.key==pygame.K_ESCAPE:return None
                    if event.key in (pygame.K_RETURN,pygame.K_KP_ENTER) and selected is not None:return options[selected]
                    if event.key==pygame.K_DOWN:
                        if opened:scroll=min(max(0,len(options)-5),scroll+1)
                        else:opened=True
                    if event.key==pygame.K_UP and opened:scroll=max(0,scroll-1)
                if event.type==pygame.MOUSEWHEEL and opened:scroll=max(0,min(max(0,len(options)-5),scroll-event.y))
                if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                    if submit.collidepoint(event.viewport_pos):
                        if selected is not None:
                            return options[selected]
                        continue
                    if opened and any(rect.collidepoint(event.pos) for rect,_ in menu):
                        selected=next(i for rect,i in menu if rect.collidepoint(event.pos));opened=False
                    elif field.collidepoint(event.pos):opened=not opened
                    else:opened=False
            clock.tick(45)
    finally:
        pass  # Session worker owns the shared SDL display
