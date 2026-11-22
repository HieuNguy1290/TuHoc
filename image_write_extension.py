from question_rich_text import draw as draw_rich, wrap as wrap_rich
from exercise_buttons import draw_complete
from exercise_gfx import draw_question_progress
from exercise_gfx import open_exercise_window
"""Standalone image-to-written-answer editor and Pygame exercise."""
import re
import unicodedata
from pathlib import Path

def normalize(value):
    return ' '.join(unicodedata.normalize('NFC', str(value)).strip().casefold().split())

def expected(question):
    return str(question.get('answer') or '')

def correct(question, response):
    accepted = [expected(question)] + list(question.get('accepted_answers') or [])
    return bool(normalize(response)) and any(normalize(response) == normalize(x) for x in accepted)

def build_editor(parent, original, import_media, resolve_media=None):
    import tkinter as tk
    from tkinter import filedialog
    def label(text):
        tk.Label(parent, text=text, bg='white', fg='#285D40', anchor='w',font=('Segoe UI',10)).pack(fill='x',pady=(9,3))
    label('Hình ảnh câu hỏi (bắt buộc)')
    media_row=tk.Frame(parent,bg='white');media_row.pack(fill='x')
    image=tk.Entry(media_row,font=('Segoe UI',11));image.pack(side='left',fill='x',expand=True)
    image.insert(0,original.get('image','') or '')
    def browse():
        path=filedialog.askopenfilename(parent=parent.winfo_toplevel(),filetypes=[('Hình ảnh','*.png *.jpg *.jpeg *.gif *.webp')])
        if path:
            image.delete(0,'end');image.insert(0,import_media(path))
    tk.Button(media_row,text='Chọn / thay ảnh',command=browse).pack(side='left',padx=6)
    label('Đáp án đúng (học sinh tự nhập toàn bộ)')
    answer=tk.Entry(parent,font=('Segoe UI',11));answer.pack(fill='x');answer.insert(0,original.get('answer','') or '')
    label('Đáp án khác được chấp nhận (không bắt buộc, cách nhau bằng dấu |)')
    variants=tk.Entry(parent,font=('Segoe UI',11));variants.pack(fill='x')
    variants.insert(0,' | '.join(original.get('accepted_answers') or []))
    label('Không phân biệt chữ hoa/chữ thường; bỏ qua khoảng trắng thừa.')
    def collect():
        ref=image.get().strip();primary=answer.get().strip()
        if not ref:raise ValueError('Vui lòng chọn hình ảnh cho câu hỏi.')
        if not primary:raise ValueError('Vui lòng nhập đáp án đúng.')
        if resolve_media:
            path=resolve_media(ref)
            if not path or not Path(path).is_file():raise ValueError('Không tìm thấy tệp hình ảnh đã chọn.')
        alternatives=[x.strip() for x in variants.get().split('|') if x.strip()]
        return {'type':'image_write_answer','image':ref,'answer':primary,'accepted_answers':alternatives,'options':[]}
    return collect

def run(question):
    import pygame
    from pygame_exercises import _image, _cached_font
    from exercise_image_zoom import draw_zoom_icon, draw as draw_zoom
    from question_layout_runtime import element
    pygame.init();pygame.display.init()
    screen=open_exercise_window((960, 640));pygame.display.set_caption('Tự Học - Bài tập')
    clock=pygame.time.Clock()
    font=_cached_font(None,23,False);small=_cached_font(None,17,False);title=_cached_font(None,28,True)
    navy=(32,52,77); bg=(241,247,252)
    text_layout=element(question,'question_text')
    image_layout=element(question,'question_image')
    input_layout=element(question,'answer_area') or element(question,'input_area')
    if text_layout and text_layout.get('font_size'):
        font=_cached_font(None,text_layout['font_size'],False)
    picture=None
    path=question.get('_pygame_image')
    if path:
        try:
            bounds=(max(1,image_layout.get('width',480)),max(1,image_layout.get('height',300))) if image_layout else (480,300)
            picture=_image(path,bounds)
        except (pygame.error,OSError,ValueError):pass
    from exercise_layout import Page, wrap, block_top, image_message
    from layout_scroll_extent import content_bottom as layout_content_bottom
    page=Page(screen)
    lines=wrap_rich(question.get('prompt') or 'Nhìn hình và ghi đáp án',font,max(80,text_layout.get('width',850)-12) if text_layout else 850)
    prompt_bottom=95+len(lines)*32
    note=image_message(question,picture)
    image_height=picture.get_height()+22 if picture else 32 if note else 0
    group_top=block_top(prompt_bottom,image_height+80)
    field_y=group_top+image_height+29
    if input_layout:
        field_y=input_layout.get('y',field_y)
    field_x=input_layout.get('x',70) if input_layout else 70
    field_width=max(100,input_layout.get('width',820)) if input_layout else 820
    field_height=max(35,input_layout.get('height',51)) if input_layout else 51
    # The complete button stays at its legacy position; only editable content moves.
    legacy_content_bottom=max(field_y+field_height+25,
                       (image_layout.get('y',group_top)+image_height+25) if image_layout else 0,
                       (text_layout.get('y',95)+len(lines)*32+25) if text_layout else 0)
    submit_y=max(561,field_y+75)
    answer='';active=True;zoom_open=False;zoom_hit=None
    pygame.key.start_text_input()
    try:
        while True:
            screen=page.begin(layout_content_bottom(question, max(submit_y+42, legacy_content_bottom)))
            screen.fill(bg)
            pygame.draw.rect(screen,'white',(25,25,910,screen.get_height()-50),border_radius=18)
            prompt=str(question.get('prompt') or 'Nhìn hình và ghi đáp án')
            # Wrap long prompts instead of cropping the question.
            prompt_x=text_layout.get('x',55) if text_layout else 55
            prompt_y=text_layout.get('y',95) if text_layout else 95
            for i,text in enumerate(lines):draw_rich(screen,font,text,navy,prompt_x,prompt_y+i*32)
            zoom_hit=None
            if picture:
                if image_layout:
                    image_rect=picture.get_rect(topleft=(image_layout.get('x',0),image_layout.get('y',0)))
                    screen.blit(picture,image_rect)
                else:
                    image_rect=picture.get_rect(midtop=(480,group_top))
                    screen.blit(picture,image_rect)
                if path:zoom_hit=draw_zoom_icon(screen,image_rect)
            elif note:screen.blit(small.render(note,True,(140,90,90)),(70,group_top))
            screen.blit(small.render('Nhập câu trả lời:',True,navy),(field_x,field_y-29))
            field=pygame.Rect(field_x,field_y,field_width,field_height)
            pygame.draw.rect(screen,(244,250,255),field,border_radius=8)
            pygame.draw.rect(screen,(47,120,200),field,2,border_radius=8)
            # Horizontally scroll long input to keep the caret visible.
            visible=answer
            while visible and font.size(visible+'|')[0]>max(30,field_width-30):visible=visible[1:]
            screen.blit(font.render(visible+('| ' if active else ''),True,navy),(field_x+13,field_y+max(4,(field_height-font.get_height())//2)))
            submit=pygame.Rect(705,submit_y,185,42)
            enabled=bool(answer.strip())
            draw_complete(screen,submit,small,enabled,submit.collidepoint((pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1] + page.scroll)),pygame.mouse.get_pressed()[0])

            draw_question_progress(screen, question)
            page.present()
            if zoom_open and path:draw_zoom(screen,path)
            pygame.display.flip()
            for event in page.events():
                if zoom_open:
                    if event.type in (pygame.MOUSEBUTTONDOWN,pygame.QUIT) or (event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE):zoom_open=False
                    continue
                if event.type==pygame.QUIT:return None
                if event.type==pygame.KEYDOWN:
                    if event.key==pygame.K_ESCAPE:return None
                    if event.key==pygame.K_BACKSPACE:answer=answer[:-1]
                    if event.key in (pygame.K_RETURN,pygame.K_KP_ENTER) and enabled:return answer.strip()
                if event.type==pygame.TEXTINPUT and active and len(answer)<250:
                    answer+=event.text
                if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                    if zoom_hit is not None and zoom_hit.collidepoint(event.pos):
                        zoom_open=True;continue
                    if submit.collidepoint(event.pos) and enabled:return answer.strip()
                    if input_layout:active=field.collidepoint(event.pos)
            clock.tick(45)
    finally:
        pygame.key.stop_text_input()
        # Close the SDL window on the same worker thread that created it.
        # Otherwise Windows may leave the preview window unresponsive after ESC/X.
        pass  # Session worker owns the shared SDL display
