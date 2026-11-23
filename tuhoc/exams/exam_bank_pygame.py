from tuhoc.paths import PROJECT_ROOT
from tuhoc.exercises.pygame_session_guard import shutdown as _app_shutdown
"""Pygame bank UI, pagination, level statistics and safe question editing.
No user data is overwritten unless the Save action validates successfully.
"""
import json
import math
from pathlib import Path
import time
import os
import sys
import pygame
from tuhoc.exercises.pygame_scroll import ScrollThumb
from tkinter import Tk, filedialog
from tuhoc.exams.exam_bank import ExamBank, SUBJECTS
from tuhoc.storage.safe_storage import commit_json
from tuhoc.studio.studio_list import find_rows, remove_at

# Presentation order only: existing IDs and Vietnamese labels are unchanged.
TYPES=[('choice','Đọc câu hỏi – chọn đáp án'),('true_false','Đúng / Sai'),('picture_choice','Nhìn hình – chọn đáp án'),('image_multi_choice','Trắc nghiệm đáp án bằng hình'),('listening_choice','Nghe – chọn đáp án'),('fill','Điền đáp án'),('picture_missing_letters','Nhìn hình – điền chữ thiếu'),('listening_fill','Nghe – điền đáp án'),('sentence_gaps','Ghép từ vào câu'),('conversation_gaps','Hoàn thành hội thoại'),('passage_gaps','Hoàn thành đoạn văn'),('error','Tìm lỗi'),('order','Sắp xếp'),('matching','Nối chữ / hình / hỗn hợp'),('reading_group','Bài đọc dài + nhiều câu hỏi')]
MATCH_MODES=['Chữ ↔ Chữ','Hình ↔ Hình','Hỗn hợp (Chữ ↔ Hình)','Hỗn hợp (Hình ↔ Chữ)']
EDITABLE={'listening_choice','listening_fill','image_multi_choice','picture_missing_letters','picture_choice','choice','true_false','fill','error','order','matching','sentence_gaps','conversation_gaps','passage_gaps'}
BG=(244,247,252); WHITE=(255,255,255); INK=(32,47,71); MUTED=(104,118,139); BLUE=(47,103,206); LINE=(217,226,239); RED=(176,57,57)

class BankManager:
    def __init__(self,root):
        self.bank=ExamBank(root);self.page=1;self.tab='bank';self.level=1;self.grade='1';self.subject='tieng_anh';self.lesson='';self.filter_type='all';self.filter_diff='all';self.search='';self.message='';self.active=None;self.actions=[];self.fields=[];self.scroll=0;self.edit_type='choice';self.edit_id='';self.form={};self.match_mode=0;self.reading_child=0;self.reading_form={};self.reading_questions=[];self.size=(1100,720);self.running=True;self.multiline_open=False;self.multiline_key='';self.multiline_scroll=0;self.match_pairs=[];self.match_focus=None;self.dropdown=None;self.dropdown_scroll=0;self.desktop=(1280,800);self.edit_scroll=0;self.maximized=False;self.config_draft=None;self.config_error="";self.focus_rect=None;self.mouse_pos=(-999,-999);self._hover_offset=0
        self.sort_by='';self.remove_request=None;self.removed=None
        self.edit_layout=None
        self._scrollbar = ScrollThumb()
        self._scrollbar_tab = None
    def font(self,size,bold=False):
        # Prefer bundled Windows Unicode fonts; pygame's default font lacks Vietnamese glyphs.
        paths=[r'C:\Windows\Fonts\segoeuib.ttf' if bold else r'C:\Windows\Fonts\segoeui.ttf',
               r'C:\Windows\Fonts\tahomabd.ttf' if bold else r'C:\Windows\Fonts\tahoma.ttf',
               r'C:\Windows\Fonts\arialbd.ttf' if bold else r'C:\Windows\Fonts\arial.ttf',
               '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
        for path in paths:
            if os.path.isfile(path):
                try:return pygame.font.Font(path,size)
                except (OSError,ValueError):pass
        for name in ('segoeui','tahoma','arial','dejavusans'):
            path=pygame.font.match_font(name,bold=bold)
            if path:
                try:return pygame.font.Font(path,size)
                except (OSError,ValueError):pass
        return pygame.font.Font(None,size)

    def maximize(self):
        if not self.maximized:
            try:
                from pygame._sdl2.video import Window
                Window.from_display_module().maximize()
            except Exception:
                self.size=self.desktop
                self.screen=pygame.display.set_mode(self.size,pygame.RESIZABLE)
            self.maximized=True
        else:
            try:
                from pygame._sdl2.video import Window
                Window.from_display_module().restore()
            except Exception:pass
            self.size=(min(1280,self.desktop[0]),min(800,self.desktop[1]))
            self.screen=pygame.display.set_mode(self.size,pygame.RESIZABLE)
            self.maximized=False

    def run(self):
        pygame.init();info=pygame.display.Info();self.desktop=(max(800,info.current_w),max(600,info.current_h));self.size=(min(1100,self.desktop[0]-80),min(720,self.desktop[1]-80));self.screen=pygame.display.set_mode(self.size,pygame.RESIZABLE);pygame.display.set_caption('Ngân hàng kiểm tra | Quản lý nội dung');pygame.key.start_text_input()
        self.f=self.font(18);self.sm=self.font(15);self.h=self.font(27,True);self.b=self.font(19,True)
        self.lesson=self.preferred_lesson()
        clock=pygame.time.Clock()
        try:
            while self.running and not _app_shutdown.is_set():
                for e in pygame.event.get():
                    if self.tab == self._scrollbar_tab and not (self.remove_request or self.multiline_open or self.dropdown):
                        consumed, offset = self._scrollbar.event(e)
                        if consumed:
                            if offset is not None:
                                if self.tab == 'bank':
                                    self.scroll = offset
                                else:
                                    self.edit_scroll = offset
                            continue
                    else:
                        self._scrollbar.grab = None
                    if e.type==pygame.QUIT:self.running=False
                    elif e.type in (pygame.VIDEORESIZE, getattr(pygame,"WINDOWSIZECHANGED",-999)):
                        self.size=(max(760,self.screen.get_width()),max(570,self.screen.get_height())) if e.type!=pygame.VIDEORESIZE else (max(760,e.w),max(570,e.h))
                        if e.type==pygame.VIDEORESIZE:self.screen=pygame.display.set_mode(self.size,pygame.RESIZABLE)
                    elif e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
                        if self.remove_request:self.click_remove(e.pos)
                        elif self.multiline_open:self.multiline_click(e.pos)
                        elif self.dropdown:self.dropdown_click(e.pos)
                        else:self.click(e.pos)
                    elif e.type==pygame.TEXTINPUT:self.text_input(e.text)
                    elif e.type==pygame.MOUSEWHEEL:
                        if self.multiline_open:self.multiline_scroll=max(0,self.multiline_scroll-e.y*3)
                        elif self.dropdown:self.dropdown_scroll=max(0,min(max(0,len(self.dropdown['values'])-self.dropdown_visible()),self.dropdown_scroll-e.y))
                        elif self.tab in ('edit','config'):self.edit_scroll=max(0,self.edit_scroll-e.y*54)
                        elif self.tab=='bank':self.scroll=max(0,self.scroll-e.y*42)
                    elif e.type==pygame.KEYDOWN:
                        if e.key==pygame.K_F11:self.maximize()
                        else:self.key(e)
                self.mouse_pos=pygame.mouse.get_pos()
                self.draw();
                if self.multiline_open:self.draw_multiline()
                elif self.dropdown:self.draw_dropdown()
                if self.remove_request:self.draw_remove()
                pygame.display.flip();clock.tick(30)
        finally:
            pygame.key.stop_text_input()
            pygame.display.quit();pygame.quit()
    def text(self,txt,x,y,font=None,color=INK,maxwidth=None):
        font=font or self.f;s=str(txt).replace('\n',' ')
        if maxwidth:
            while s and font.size(s)[0]>maxwidth:s=s[:-2]+'…'
        self.screen.blit(font.render(s,True,color),(x,y))
    def rect(self,r,color=WHITE,border=None,radius=10):
        pygame.draw.rect(self.screen,color,r,border_radius=radius)
        if border:pygame.draw.rect(self.screen,border,r,1,border_radius=radius)
    def hovering(self,r):
        mx,my=self.mouse_pos
        return r.collidepoint(mx,my+self._hover_offset)

    def btn(self,label,r,callback,selected=False,disabled=False):
        hover=not disabled and self.hovering(r)
        bg=(220,233,255) if hover else (225,235,252) if selected else (236,241,249) if not disabled else (245,246,248)
        self.rect(r,bg,BLUE if selected or hover else LINE,8)
        if hover:pygame.draw.rect(self.screen,BLUE,r,2,border_radius=8)
        self.text(label,r.x+12,r.y+(r.h-self.sm.get_height())//2,self.sm,MUTED if disabled else BLUE if selected or hover else INK,r.w-22)
        if not disabled:self.actions.append((r,callback))
    def field(self,label,key,r,placeholder='',editable=True):
        self.text(label,r.x,r.y-22,self.sm,MUTED)
        self.rect(r,WHITE,BLUE if self.active==key else LINE,7)
        if self.active==key or (editable and self.hovering(r)):
            pygame.draw.rect(self.screen,BLUE,r,2 if self.active==key else 1,border_radius=7)
        value=(self.reading_questions[self.reading_child].get(key[6:],'') if key.startswith('child_') and self.reading_questions else self.reading_form.get(key,'')) if self.tab=='edit' and self.edit_type=='reading_group' else (self.form.get(key,'') if self.tab=='edit' else getattr(self,key,''))
        self.text((value or placeholder).replace('\n',' ⏎ '),r.x+10,r.y+10,self.f,INK if value else MUTED,r.w-20)
        if self.active==key:self.draw_caret(r,str(value),self.f)
        if editable:self.actions.append((r,lambda k=key:setattr(self,'active',k)))
    def draw_caret(self,r,value,font):
        # Keep cursor visible within the focused input; clip it to the textbox.
        if pygame.time.get_ticks()//520%2:
            return
        visible=str(value).replace('\n',' ⏎ ')
        while visible and font.size(visible)[0]>r.w-26:
            visible=visible[1:]
        cx=min(r.right-9,r.x+10+font.size(visible)[0]+2)
        pygame.draw.line(self.screen,BLUE,(cx,r.y+9),(cx,r.bottom-9),2)

    def open_dropdown(self,attr,values,rect,labels=None):
        values=list(values)
        if not values:return
        if self.dropdown and self.dropdown['attr']==attr:
            self.dropdown=None;return
        self.active=None;self.dropdown={'attr':attr,'values':values,'rect':pygame.Rect(rect),'labels':labels or {}}
        self.dropdown_scroll=0
        current=getattr(self,attr,None)
        if current in values:self.dropdown_scroll=max(0,values.index(current)-3)

    def dropdown_visible(self):
        if not self.dropdown:return 0
        r=self.dropdown['rect'];available=max(120,self.size[1]-r.bottom-20)
        return max(2,min(9,available//38))

    def dropdown_box(self):
        r=self.dropdown['rect'];visible=self.dropdown_visible()
        return pygame.Rect(r.x,r.bottom+3,max(r.w,230),visible*38+8)

    def dropdown_click(self,pos):
        d=self.dropdown;box=self.dropdown_box()
        if box.collidepoint(pos):
            index=(pos[1]-box.y-4)//38+self.dropdown_scroll
            if 0<=index<len(d['values']):
                value=d['values'][index];attr=d['attr'];self.dropdown=None
                if attr=='edit_type':self.set_edit_type(value)
                else:
                    setattr(self,attr,value);self.page=1;self.scroll=0
                    if attr in ('grade','subject'):
                        lessons=self.bank.lessons(self.grade,self.subject)
                        self.lesson=self.preferred_lesson()
        else:self.dropdown=None

    def draw_dropdown(self):
        d=self.dropdown;box=self.dropdown_box();self.rect(box,WHITE,BLUE,9)
        start=self.dropdown_scroll;end=min(len(d['values']),start+self.dropdown_visible())
        for i in range(start,end):
            value=d['values'][i];label=d['labels'].get(value,str(value));r=pygame.Rect(box.x+4,box.y+4+(i-start)*38,box.w-8,37)
            if value==getattr(self,d['attr'],None) or self.hovering(r):
                self.rect(r,(227,237,252),BLUE if self.hovering(r) else None,5)
            self.text(label,r.x+10,r.y+8,self.sm,INK,r.w-20)
        if len(d['values'])>self.dropdown_visible():
            self.text(f'{start+1}–{end}/{len(d["values"])}  •  cuộn để xem thêm',box.x+8,max(0,box.y-19),self.sm,BLUE)

    def click(self,pos):
        if self.active and self.active.startswith("ratio_"):
            _,l,k=self.active.split("_")
            self.set_ratio_value(int(l),int(k),self.ratio_buffer)
            self.active=None
        for r,cb in reversed(self.actions):
            if r.collidepoint(pos):cb();return
        self.active=None
    def open_multiline(self,key):
        self.multiline_key=key;self.multiline_open=True;self.multiline_scroll=0;self.active=None
        pygame.key.start_text_input()

    def multiline_form(self):
        return self.reading_form if self.edit_type=='reading_group' else self.form

    def multiline_click(self,pos):
        w,h=self.size
        if pygame.Rect(w-156,h-95,118,42).collidepoint(pos):
            self.multiline_open=False;pygame.key.stop_text_input()
        elif pygame.Rect(38,h-95,118,42).collidepoint(pos):
            self.multiline_open=False;pygame.key.stop_text_input()

    def wrap_lines(self,value,font,width):
        result=[]
        for paragraph in value.split('\n'):
            if not paragraph:result.append('');continue
            words=paragraph.split(' ');line=''
            for word in words:
                trial=(line+' '+word).strip()
                if line and font.size(trial)[0]>width:
                    result.append(line);line=word
                else:line=trial
            result.append(line)
        return result

    def draw_multiline(self):
        w,h=self.size
        veil=pygame.Surface((w,h),pygame.SRCALPHA);veil.fill((12,26,48,185));self.screen.blit(veil,(0,0))
        box=pygame.Rect(22,42,w-44,h-68);self.rect(box,WHITE,LINE,14)
        self.text('SOẠN ĐOẠN VĂN NHIỀU DÒNG',44,60,self.b)
        self.text('Enter: xuống dòng  •  Cuộn chuột: xem nội dung  •  Esc: đóng',44,94,self.sm,MUTED,w-88)
        area=pygame.Rect(43,132,w-86,max(95,h-285));self.rect(area,(250,252,255),BLUE,8)
        value=self.multiline_form().get(self.multiline_key,'')
        lines=self.wrap_lines(value,self.f,area.w-35)
        visible=max(1,(area.h-25)//27)
        self.multiline_scroll=min(self.multiline_scroll,max(0,len(lines)-visible))
        oldclip=self.screen.get_clip();self.screen.set_clip(area.inflate(-12,-12))
        for i,line in enumerate(lines[self.multiline_scroll:self.multiline_scroll+visible]):
            self.text(line,area.x+14,area.y+12+i*27,self.f,INK)
        # Caret is drawn in the actual multiline viewport and follows wrapped lines.
        if pygame.time.get_ticks()//520%2==0:
            last=lines[-1] if lines else ''
            last_index=len(lines)-1-self.multiline_scroll
            if 0<=last_index<visible:
                cx=min(area.right-16,area.x+14+self.f.size(last)[0]+2)
                cy=area.y+12+last_index*27
                pygame.draw.line(self.screen,BLUE,(cx,cy),(cx,cy+self.f.get_height()),2)
        self.screen.set_clip(oldclip)
        self.text(f'{len(value)} ký tự  •  {len(lines)} dòng  •  đang xem {min(len(lines),self.multiline_scroll+1)}–{min(len(lines),self.multiline_scroll+visible)}',44,h-135,self.sm,MUTED)
        self.btn_modal('Đóng',pygame.Rect(38,h-95,118,42))
        self.btn_modal('Hoàn tất',pygame.Rect(w-156,h-95,118,42))

    def btn_modal(self,label,rect):
        hover=self.hovering(rect)
        self.rect(rect,(213,229,255) if hover else (225,235,252),BLUE,8)
        if hover:pygame.draw.rect(self.screen,BLUE,rect,2,border_radius=8)
        self.text(label,rect.x+15,rect.y+11,self.sm,BLUE)

    def key(self,e):
        if self.remove_request:
            if e.key==pygame.K_ESCAPE:self.remove_request=None
            return
        if self.multiline_open:
            if e.key==pygame.K_ESCAPE:self.multiline_open=False;pygame.key.stop_text_input();return
            value=self.multiline_form().get(self.multiline_key,'')
            if e.key==pygame.K_BACKSPACE:value=value[:-1]
            elif e.key==pygame.K_RETURN:value+='\n'
            elif e.key==pygame.K_TAB:value+='    '
            
            self.multiline_form()[self.multiline_key]=value
            lines=self.wrap_lines(value,self.f,self.size[0]-121)
            visible=max(1,(self.size[1]-251-25)//27)
            self.multiline_scroll=max(0,len(lines)-visible)
            return
        if e.key==pygame.K_ESCAPE:
            if self.dropdown:self.dropdown=None;return
            if self.active:self.active=None
            elif self.tab!='bank':self.tab='bank'
            else:self.running=False
            return
        if self.active:
            if self.active.startswith('ratio_'):
                if e.key==pygame.K_BACKSPACE:self.ratio_buffer=self.ratio_buffer[:-1]
                elif e.key in (pygame.K_RETURN,pygame.K_KP_ENTER):
                    _,l,k=self.active.split('_');self.set_ratio_value(int(l),int(k),self.ratio_buffer);self.active=None
                return
            if self.active.startswith('match_'):
                try:
                    _,idx,side=self.active.split('_');idx=int(idx);value=self.match_pairs[idx][side]
                    if e.key==pygame.K_BACKSPACE:value=value[:-1]
                    elif e.key==pygame.K_RETURN:self.active=None;return
                    
                    self.match_pairs[idx][side]=value
                except (ValueError,IndexError,KeyError):self.active=None
                return
            obj=self.form if self.tab=='edit' else None
            current=(self.reading_questions[self.reading_child].get(self.active[6:],'') if self.tab=='edit' and self.edit_type=='reading_group' and self.active.startswith('child_') and self.reading_questions else self.reading_form.get(self.active,'') if self.tab=='edit' and self.edit_type=='reading_group' else obj.get(self.active,'') if obj is not None else getattr(self,self.active,''))
            if e.key==pygame.K_BACKSPACE:current=current[:-1]
            elif e.key==pygame.K_RETURN:
                if self.active=='passage' and e.mod & pygame.KMOD_SHIFT:current+='\n'
                else:self.active=None;return
            
            if self.tab=='edit' and self.edit_type=='reading_group':
                if self.active.startswith('child_') and self.reading_questions:
                    self.reading_questions[self.reading_child][self.active[6:]]=current
                else:self.reading_form[self.active]=current
            elif obj is not None:obj[self.active]=current
            else:
                setattr(self,self.active,current)
                if self.tab=='bank' and self.active=='search':self.page=1;self.scroll=0
        elif self.tab=='bank':
            if e.key==pygame.K_RIGHT:self.page+=1
            if e.key==pygame.K_LEFT:self.page=max(1,self.page-1)
    def text_input(self,text):
        if not text or not text.isprintable():return
        if self.multiline_open:
            key=self.multiline_key
            form=self.multiline_form()
            form[key]=(form.get(key,'')+text)[:30000]
            return
        if not self.active:return
        if self.active.startswith('ratio_'):
            if text.isascii() and text.isdecimal():self.ratio_buffer=(self.ratio_buffer+text)[-3:]
            return
        if self.active.startswith('match_'):
            try:
                _,idx,side=self.active.split('_');pair=self.match_pairs[int(idx)]
                pair[side]=(pair[side]+text)[:150]
            except (ValueError,IndexError,KeyError):pass
        elif self.tab=='edit':
            if self.edit_type=='reading_group':
                if self.active.startswith('child_') and self.reading_questions:
                    key=self.active[6:];child=self.reading_questions[self.reading_child]
                    child[key]=(child.get(key,'')+text)[:500]
                else:self.reading_form[self.active]=(self.reading_form.get(self.active,'')+text)[:500]
            else:self.form[self.active]=(self.form.get(self.active,'')+text)[:500]
        else:
            setattr(self,self.active,(str(getattr(self,self.active,''))+text)[:500])
            if self.tab=='bank' and self.active=='search':self.page=1;self.scroll=0

    def draw_scrollable_edit(self,w,h):
        # Draw content on a virtual surface, then clip it to a scrollable viewport.
        viewport_top=262;viewport_bottom=h-58
        virtual_h=max(1370,650+len(self.match_pairs)*120) if self.edit_type=='matching' else 1160 if self.edit_type=='reading_group' else 1370
        real=self.screen;prior=len(self.actions)
        surface=pygame.Surface((w,virtual_h));surface.fill(BG)
        self.screen=surface
        self._hover_offset=self.edit_scroll
        self.draw_edit(w,virtual_h)
        self._hover_offset=0
        self.screen=real
        maximum=max(0,virtual_h-viewport_top-(viewport_bottom-viewport_top))
        self.edit_scroll=min(maximum,self.edit_scroll)
        area=pygame.Rect(0,viewport_top,w,max(1,viewport_bottom-viewport_top))
        real.blit(surface,(0,viewport_top),pygame.Rect(0,viewport_top+self.edit_scroll,w,area.h))
        transformed=[]
        for rect,cb in self.actions[prior:]:
            rr=rect.move(0,-self.edit_scroll)
            if rr.bottom>viewport_top and rr.top<viewport_bottom:
                rr=rr.clip(area)
                if rr.w>0 and rr.h>0:transformed.append((rr,cb))
        self.actions=self.actions[:prior]+transformed
        self.rect(pygame.Rect(0,h-58,w,58),BG)
        self.btn('Lưu câu hỏi' if self.edit_type!='reading_group' else 'Lưu bài đọc',pygame.Rect(w-203,h-52,175,40),self.save,disabled=self.edit_type not in EDITABLE and self.edit_type!='reading_group')
        self.btn('Quay lại',pygame.Rect(w-348,h-52,132,40),lambda:setattr(self,'tab','bank'))
        self.text('Cuộn chuột để xem toàn bộ biểu mẫu',30,h-39,self.sm,MUTED,max(100,w-400))
        self.draw_scrollbar(pygame.Rect(w-9,viewport_top,5,area.h), area.h, self.edit_scroll, maximum, 30)

    def draw_scrollbar(self, track, height, offset, limit, minimum):
        if self._scrollbar_tab != self.tab:
            self._scrollbar.grab = None
        self._scrollbar_tab = self.tab
        self._scrollbar.configure(track, height, offset, limit, minimum=minimum)
        if self._scrollbar.track:
            self.rect(self._scrollbar.track, LINE)
            self.rect(self._scrollbar.thumb, BLUE)

    def scope(self):
        rows=self.bank.questions();groups=self.bank.reading_groups()
        result=[r for r in rows if str(r.get('grade'))==self.grade and str(r.get('lesson'))==self.lesson and str(r.get('subject') or 'tieng_anh')==self.subject]
        result += [dict(g,type='reading_group',prompt=g.get('title',''),_group=True) for g in groups if str(g.get('grade'))==self.grade and str(g.get('lesson'))==self.lesson and g.get('subject')==self.subject]
        return result
    def lesson_labels(self,lessons):
        counts={str(k):0 for k in lessons}
        for q in self.bank.questions():
            if str(q.get('grade'))==str(self.grade) and str(q.get('subject') or 'tieng_anh')==self.subject:
                k=str(q.get('lesson',''));counts[k]=counts.get(k,0)+1
        for g in self.bank.reading_groups():
            if str(g.get('grade'))==str(self.grade) and str(g.get('subject') or 'tieng_anh')==self.subject:
                k=str(g.get('lesson',''));counts[k]=counts.get(k,0)+len(g.get('questions',[]))
        return {k:f'{k} ({counts.get(str(k),0)} câu)' for k in lessons}

    def preferred_lesson(self):
        """Choose a populated lesson first; never hide existing sample questions."""
        lessons=self.bank.lessons(self.grade,self.subject)
        counts={lesson:0 for lesson in lessons}
        for q in self.bank.questions():
            if str(q.get('grade'))==str(self.grade) and str(q.get('subject') or 'tieng_anh')==self.subject:
                key=str(q.get('lesson',''))
                counts[key]=counts.get(key,0)+1
        for group in self.bank.reading_groups():
            if str(group.get('grade'))==str(self.grade) and str(group.get('subject') or 'tieng_anh')==self.subject:
                key=str(group.get('lesson',''))
                counts[key]=counts.get(key,0)+len(group.get('questions',[]))
        if counts:
            return sorted(counts,key=lambda lesson:(-counts[lesson],lesson.casefold()))[0]
        return lessons[0] if lessons else ''

    def select_populated_lesson(self):
        self.lesson=self.preferred_lesson();self.page=1;self.scroll=0

    def change(self,attr,values):
        cur=getattr(self,attr);i=values.index(cur) if cur in values else -1
        setattr(self,attr,values[(i+1)%len(values)]);self.page=1;self.scroll=0
        if attr in ('grade','subject'):
            lessons=self.bank.lessons(self.grade,self.subject);self.lesson=self.preferred_lesson()
    def begin(self,row=None):
        self.edit_layout=row.get('layout') if row else None
        self.tab='edit';self.edit_scroll=0;self.active=None;self.message='';self.edit_id=str(row.get('id','')) if row else ''
        self.edit_type=row.get('type','choice') if row else 'choice';self.match_mode=MATCH_MODES.index(row.get('matching_mode')) if row and row.get('matching_mode') in MATCH_MODES else 0
        if self.edit_type=='matching' and self.size[1]<1180:
            self.message='Mẹo: cuộn trang hoặc phóng to cửa sổ để xem đủ trường nhập.'
        self.reading_child=0
        self.match_pairs=[{'left':str(a),'right':str(b)} for a,b in row.get('pairs',[])] if row and row.get('type')=='matching' else [{'left':'','right':''} for _ in range(3)]
        if self.edit_type=='reading_group':
            if self.size[1]<1040:
                self.message='Mẹo: cuộn trang hoặc phóng to cửa sổ để xem đủ trường nhập.'
            self.reading_form={'title':row.get('title','') if row else '', 'passage':row.get('passage','') if row else ''}
            self.reading_questions=[{'id':str(q.get('id','')), 'prompt':str(q.get('prompt','')), 'options':' | '.join(q.get('options',[])), 'answer':str(q.get('answer','')), 'difficulty':str(q.get('difficulty',1)), 'layout':q.get('layout')} for q in row.get('questions',[])] if row else []
            if not self.reading_questions:self.reading_questions=[{'prompt':'','options':'A | B | C | D','answer':'','difficulty':'1'},{'prompt':'','options':'A | B | C | D','answer':'','difficulty':'1'}]
        self.form={'prompt':row.get('prompt','') if row else '', 'options':' | '.join(row.get('options',[])) if row else 'A | B | C | D','answer':str(row.get('answer','')) if row else '', 'sequence':' | '.join(row.get('sequence',[])) if row else '', 'pairs':' | '.join(' = '.join(p) for p in row.get('pairs',[])) if row else '', 'wrong':row.get('wrong','') if row else '', 'corrected':row.get('corrected','') if row else '', 'difficulty':str(row.get('difficulty',1)) if row else '1', 'gap_answers':' | '.join(row.get('gap_answers',[])) if row else '', 'audio':str(row.get('audio','')) if row else '', 'image':str(row.get('image','')) if row else '', 'image_options':list(row.get('options',[])) if row and row.get('type')=='image_multi_choice' else [], 'image_correct':str(row.get('answer','')) if row and row.get('type')=='image_multi_choice' else ''}
        self.form['passage']=str(row.get('passage') or row.get('reading') or '') if row else ''

    def duplicate(self,row):
        self.begin(row)
        self.edit_id=''
        if self.edit_type=='reading_group':
            for child in self.reading_questions:
                child.pop('id',None)
        self.message='Bản sao chưa lưu. Kiểm tra nội dung rồi chọn Lưu.'

    def request_remove(self,row):
        self.remove_request=row
        self.active=None

    def remove_buttons(self):
        w,h=self.size
        center=pygame.Rect(w//2-210,h//2-80,420,160)
        yes=pygame.Rect(center.x+27,center.bottom-54,145,37)
        no=pygame.Rect(center.right-172,center.bottom-54,145,37)
        return center,yes,no

    def draw_remove(self):
        center,yes,no=self.remove_buttons()
        veil=pygame.Surface(self.size,pygame.SRCALPHA)
        veil.fill((12,25,40,175))
        self.screen.blit(veil,(0,0))
        self.rect(center,WHITE,LINE,12)
        self.text('Xóa mục đang chọn?',center.x+24,center.y+16,self.b,INK)
        self.text('Bạn có thể hoàn tác trong 6 giây.',center.x+24,center.y+54,self.sm,MUTED)
        self.rect(yes,RED,None,5);self.text('Xóa',yes.x+53,yes.y+8,self.sm,WHITE)
        self.rect(no,LINE,None,5);self.text('Hủy',no.x+53,no.y+8,self.sm,INK)

    def click_remove(self,pos):
        _center,yes,no=self.remove_buttons()
        if no.collidepoint(pos):
            self.remove_request=None
        elif yes.collidepoint(pos):
            row,self.remove_request=self.remove_request,None
            path=self.bank.readings_path if row.get('_group') else self.bank.questions_path
            try:
                data=json.loads(path.read_text(encoding='utf-8-sig'))
                hits=[i for i,item in enumerate(data) if item.get('id')==row.get('id')]
                if len(hits)!=1:
                    raise ValueError('Không xác định được mục cần xóa.')
                remaining,ticket=remove_at(data,hits[0])
                commit_json({path:remaining})
                self.removed=(time.monotonic()+6,path,ticket)
                self.message='Đã xóa mục.'
            except (OSError,ValueError,TypeError) as exc:
                self.message='Lỗi xóa: '+str(exc)

    def undo_remove(self):
        if self.removed is None:
            return
        expires,path,ticket=self.removed
        self.removed=None
        if time.monotonic()>expires:
            return
        try:
            data=json.loads(path.read_text(encoding='utf-8-sig'))
            commit_json({path:ticket.restore(data,unique_id=True)})
            self.message='Đã hoàn tác xóa.'
        except (OSError,ValueError,TypeError) as exc:
            self.message='Lỗi hoàn tác: '+str(exc)

    def save(self):
        if self.edit_type=='reading_group':
            try:
                children=[]
                for c in self.reading_questions:
                    children.append({'id':c.get('id',''), 'prompt':c['prompt'].strip(),'options':[x.strip() for x in c['options'].split('|') if x.strip()],'answer':c['answer'].strip(),'difficulty':int(c['difficulty'])})
                    if c.get('layout') is not None:
                        children[-1]['layout']=c['layout']
                group = {'id': self.edit_id, 'subject': self.subject, 'grade': self.grade,
                         'lesson': self.lesson, 'title': self.reading_form['title'].strip(),
                         'passage': self.reading_form['passage'].strip(), 'questions': children}
                if self.edit_layout is not None:
                    group['layout'] = self.edit_layout
                self.bank.save_reading(group)
                self.message='Đã lưu bài đọc và câu hỏi con.';self.tab='bank'
            except (ValueError,KeyError,OSError) as exc:self.message='Lỗi lưu: '+str(exc)
            return
        if self.edit_type not in EDITABLE:
            self.message='Dạng này chưa có Pygame runtime hoàn chỉnh. Chưa cho lưu để bảo vệ ngân hàng.';return
        try:
            f=self.form;typ=self.edit_type
            q=dict(id=self.edit_id,subject=self.subject,grade=self.grade,lesson=self.lesson,type=typ,prompt=f['prompt'].strip(),difficulty=int(f['difficulty']),answer=f['answer'].strip())
            # Optional supplementary media for every editable question type.
            # Missing media is omitted, preserving old JSON schemas.
            if f.get('audio','').strip():q['audio']=f['audio'].strip()
            if f.get('image','').strip():
                q['image']=self.bank._resolve_media(f['image'].strip())
                if not Path(q['image']).is_file():
                    raise ValueError('Không tìm thấy ảnh minh họa. Hãy chọn lại tệp.')
            if typ in ('choice','true_false') and f.get('passage','').strip():
                q['passage']=f['passage'].strip()
            if self.edit_layout is not None:
                q['layout']=self.edit_layout
            if typ=='image_multi_choice':
                q['options']=list(f.get('image_options',[]));q['answer']=f.get('image_correct','')
            if typ in ('choice','true_false','picture_choice','listening_choice'):q['options']=[x.strip() for x in f['options'].split('|') if x.strip()]
            # The shared optional image field above covers image-based types too.
            # Keep listening-specific behavior unchanged.
            if typ in ('sentence_gaps','conversation_gaps','passage_gaps'):q['gap_answers']=[x.strip() for x in f['gap_answers'].split('|')]
            if typ=='order':q['sequence']=[x.strip() for x in f['sequence'].split('|') if x.strip()]
            if typ=='matching':
                q['matching_mode']=MATCH_MODES[self.match_mode];q['pairs']=[[p['left'].strip(),p['right'].strip()] for p in self.match_pairs]
            if typ=='error':q['wrong']=f['wrong'].strip();q['corrected']=f['corrected'].strip();q['answer']=q['corrected']
            self.bank.save_question(q);self.message='Đã lưu câu hỏi thành công.';self.tab='bank'
        except (ValueError,KeyError,OSError) as exc:self.message='Lỗi lưu: '+str(exc)
    def change_tab(self,value):
        if value!=self.tab:self.edit_scroll=0
        self.tab=value;self.active=None;self.dropdown=None

    def install_grade2(self):
        from exam_content.grade2 import LESSON, install

        try:
            count = install(self.bank)
        except (ValueError, OSError) as exc:
            self.message = 'Lỗi nạp bộ lớp 2: ' + str(exc)
            return
        if self.subject not in ('toan', 'tieng_viet'):
            self.subject = 'toan'
        self.grade = '2'
        self.lesson = LESSON
        self.change_tab('bank')
        self.filter_type = self.filter_diff = 'all'
        self.search = ''
        self.set_page(1)
        self.message = (f'Đã thêm {count} câu lớp 2.' if count else
                        'Bộ lớp 2 đã có đủ 200 mã câu hỏi.')

    def draw(self):
        s=self.screen;w,h=self.size;s.fill(BG);self.actions=[]
        self.text('NGÂN HÀNG KIỂM TRA',28,22,self.h)
        self.text('Quản lý nội dung  /  Bộ câu hỏi theo Level',30,59,self.sm,MUTED)
        self.btn('Phóng to / Thu nhỏ',pygame.Rect(w-285,23,163,36),self.maximize)
        self.btn('Đóng',pygame.Rect(w-112,23,84,36),lambda:setattr(self,'running',False))
        for i,(name,key) in enumerate([('Danh sách câu hỏi','bank'),('Thêm / Sửa câu hỏi','edit'),('Cấu hình đề','config')]):
            self.btn(name,pygame.Rect(28+i*190,92,181,38),lambda v=key:(self.begin() if v=='edit' and self.tab!='edit' else self.change_tab(v)),self.tab==key)
        if self.tab=='bank':
            self.btn('Nạp bộ lớp 2',pygame.Rect(w-151,92,123,38),self.install_grade2)
        self.rect(pygame.Rect(28,148,w-56,108),WHITE,LINE)
        for i,(label,attr,values) in enumerate([('Môn học','subject',list(SUBJECTS)),('Lớp','grade',self.bank.grades()),('Bài học','lesson',self.bank.lessons(self.grade,self.subject)),('Level','level',list(range(1,11))) ]):
            x=46+i*(w-92)//4;self.text(label,x,163,self.sm,MUTED)
            current=getattr(self,attr);display=SUBJECTS.get(current,current) if attr=='subject' else ('Level '+str(current) if attr=='level' else current)
            r=pygame.Rect(x,186,(w-116)//4-14,45);self.btn(str(display)+'  ▼',r,lambda a=attr,v=values,rr=r:self.open_dropdown(a,v,rr,SUBJECTS if a=='subject' else {k:'Level '+str(k) for k in v} if a=='level' else self.lesson_labels(v) if a=='lesson' else None))
        if self.tab=='bank':self.draw_bank(w,h)
        elif self.tab=='edit':self.draw_scrollable_edit(w,h)
        else:self.draw_scrollable_config(w,h)
        if self.message:self.text(self.message,32,h-27,self.sm,RED if self.message.startswith(('Lỗi','Dạng')) else BLUE,w-65)
    def draw_bank(self,w,h):
        scoped=self.scope();counts=[0]*5
        for q in scoped:
            items=q.get('questions',[]) if q.get('_group') else [q]
            for c in items:
                d=int(c.get('difficulty',0))
                if 1<=d<=5:counts[d-1]+=1
        cfg=self.bank.config();n=cfg['question_count'];ratios=cfg['ratios'][str(self.level)];need=[int(n*p/100) for p in ratios]
        for i in sorted(range(5),key=lambda j:-(n*ratios[j]/100-need[j]))[:n-sum(need)]:need[i]+=1
        self.rect(pygame.Rect(28,272,w-56,80),WHITE,LINE)
        self.text(f'Tổng câu tính điểm: {sum(counts)}  |  Level {self.level} cần {n} câu',46,284,self.b)
        for i in range(5):self.text(f'M{i+1}: {counts[i]}/{need[i]}',46+i*(w-100)//5,321,self.sm,BLUE if counts[i]>=need[i] else RED)
        self.field('Tìm mã / nội dung','search',pygame.Rect(30,391,310,41),'Tìm câu hỏi...')
        self.btn('Dạng: '+('Tất cả' if self.filter_type=='all' else dict(TYPES).get(self.filter_type,self.filter_type)),pygame.Rect(355,391,max(155,min(365,w-680)),41),lambda:self.open_dropdown('filter_type',['all']+[t[0] for t in TYPES],pygame.Rect(355,391,max(155,min(365,w-680)),41),dict([('all','Tất cả')]+TYPES)))
        self.btn('Mức: '+('Tất cả' if self.filter_diff=='all' else 'M'+self.filter_diff),pygame.Rect(w-300,391,133,41),lambda:self.open_dropdown('filter_diff',['all','1','2','3','4','5'],pygame.Rect(w-300,391,133,41),{'all':'Tất cả',**{str(i):'M'+str(i) for i in range(1,6)}}))
        self.btn('+ Thêm câu hỏi',pygame.Rect(w-156,391,128,41),lambda:self.begin())
        matched=find_rows(scoped,self.search,sort_by=self.sort_by or None,
                          filters={'type':None if self.filter_type=='all' else self.filter_type})
        rows=[row for _,row in matched if self.filter_diff=='all'
              or str(row.get('difficulty'))==self.filter_diff
              or row.get('_group') and any(str(child.get('difficulty'))==self.filter_diff
                                           for child in row.get('questions',[]))]
        total=len(rows);pages=max(1,math.ceil(total/10));self.page=min(max(1,self.page),pages)
        if total==0:
            available=sum(1 for q in self.bank.questions() if str(q.get('grade'))==str(self.grade) and str(q.get('subject') or 'tieng_anh')==self.subject)
            if available and not self.search and self.filter_type=='all' and self.filter_diff=='all':
                self.text(f'Bài học này chưa có câu hỏi. Có {available} câu ở các bài khác.',46,490,self.sm,MUTED,max(100,w-100))
                self.btn('Xem bài có câu hỏi',pygame.Rect(46,523,195,36),self.select_populated_lesson)

        # Scrollable table viewport. Pagination lives OUTSIDE the clipped frame.
        top=447
        footer_top=max(top+120,h-75)
        frame_bottom=footer_top-12
        frame=pygame.Rect(28,top,w-56,max(70,frame_bottom-top))
        self.rect(frame,WHITE,LINE)
        header_h=35
        rowh=38
        viewport=pygame.Rect(frame.x+1,top+header_h,frame.w-2,max(1,frame.h-header_h-2))
        visible_rows=rows[(self.page-1)*10:self.page*10]
        content_h=len(visible_rows)*rowh
        max_scroll=max(0,content_h-viewport.h)
        self.scroll=min(max(0,self.scroll),max_scroll)
        # Header stays fixed while only table rows scroll.
        self.btn('MÃ' + (' ↑' if self.sort_by=='id' else ''),pygame.Rect(43,top+3,86,28),
                 lambda:self.sort_bank('id'))
        self.btn('NỘI DUNG'+(' ↑' if self.sort_by=='prompt' else ''),pygame.Rect(w//4,top+3,114,28),
                 lambda:self.sort_bank('prompt'))
        self.text('DẠNG',w*3//5,top+8,self.sm,MUTED)
        self.text('MỨC',w-239,top+8,self.sm,MUTED)
        pygame.draw.line(self.screen,LINE,(frame.x+8,top+header_h),(frame.right-8,top+header_h))
        old_clip=self.screen.get_clip()
        self.screen.set_clip(viewport)
        action_start=len(self.actions)
        for i,q in enumerate(visible_rows):
            y=viewport.y+i*rowh-self.scroll
            if y+rowh<viewport.y or y>viewport.bottom:continue
            row_rect=pygame.Rect(frame.x+8,y+1,frame.w-16,rowh-2)
            if self.hovering(row_rect):
                self.rect(row_rect,(238,245,255),BLUE,5)
            pygame.draw.line(self.screen,LINE,(40,y),(w-40,y))
            self.text(q.get('id','')[:23],43,y+9,self.sm,BLUE,w//4-55)
            self.text(q.get('prompt','') or q.get('title',''),w//4,y+9,self.sm,INK,w*7//20)
            self.text(dict(TYPES).get(q.get('type'),q.get('type')),w*3//5,y+9,self.sm,MUTED,max(55,w-245-w*3//5))
            self.text('M'+str(q.get('difficulty')) if not q.get('_group') else str(len(q.get('questions',[])))+' câu',w-239,y+9,self.sm)
            self.btn('Sửa',pygame.Rect(w-177,y+5,42,28),lambda r=q:self.begin(r))
            self.btn('Sao',pygame.Rect(w-129,y+5,42,28),lambda r=q:self.duplicate(r))
            self.btn('Xóa',pygame.Rect(w-81,y+5,42,28),lambda r=q:self.request_remove(r))
        self.screen.set_clip(old_clip)
        self.actions=self.actions[:action_start]+[(r.clip(viewport),cb) for r,cb in self.actions[action_start:] if r.colliderect(viewport)]
        self.draw_scrollbar(pygame.Rect(frame.right-9,viewport.y,5,viewport.h),
                            viewport.h, self.scroll, max_scroll, 24)
        if not visible_rows and total==0:
            self.text('Không có câu hỏi phù hợp với bộ lọc hiện tại.',46,viewport.y+18,self.sm,MUTED,max(100,w-100))
        # Footer never overlaps the table or its final row.
        y=footer_top+8
        self.text(f'Đã hiển thị: {min(self.page*10,total)}/{total}   |   Trang {self.page}/{pages}   |   10 dòng/trang',33,y+9,self.sm,INK,max(120,w-420))
        self.btn('Đầu',pygame.Rect(w-346,y,64,34),lambda:self.set_page(1),disabled=self.page==1)
        self.btn('<',pygame.Rect(w-274,y,52,34),lambda:self.set_page(max(1,self.page-1)),disabled=self.page==1)
        self.btn('>',pygame.Rect(w-214,y,52,34),lambda:self.set_page(min(pages,self.page+1)),disabled=self.page==pages)
        self.btn('Cuối',pygame.Rect(w-154,y,87,34),lambda:self.set_page(pages),disabled=self.page==pages)
        if self.removed and time.monotonic()<=self.removed[0]:
            self.btn('Hoàn tác',pygame.Rect(30,y+4,105,34),self.undo_remove)
        elif self.removed:
            self.removed=None

    def sort_bank(self,key):
        self.sort_by='' if self.sort_by==key else key
        self.set_page(1)

    def set_page(self,page):
        self.page=page
        self.scroll=0
    def draw_edit(self,w,h):
        self.text('Bộ soạn thảo theo từng dạng câu hỏi',32,274,self.b)
        self.btn('Dạng: '+dict(TYPES)[self.edit_type]+'  ▼',pygame.Rect(30,313,w-60,43),lambda:self.open_dropdown('edit_type',[t[0] for t in TYPES],pygame.Rect(30,313,w-60,43),dict(TYPES)))
        self.text('Mã: '+(self.edit_id or 'Tạo tự động khi lưu'),35,368,self.sm,MUTED)
        self.btn('Chỉnh bố cục', pygame.Rect(w-189,360,158,38), self.edit_visual_layout)
        required=[]
        if self.edit_type not in ('reading_group','picture_missing_letters') and not self.form.get('prompt','').strip():
            required.append('nội dung')
        if self.edit_type in ('choice','true_false','fill','picture_choice','picture_missing_letters','listening_choice','listening_fill') and not self.form.get('answer','').strip():
            required.append('đáp án')
        if required:
            self.text('Còn thiếu: '+', '.join(required),w//2,368,self.sm,RED,max(100,w//2-200))
        self.rect(pygame.Rect(28,397,w-56,max(150,h-485)),WHITE,LINE)
        x=47;y=435;wide=w-95
        typ=self.edit_type
        if typ!='reading_group':
            self.field('Nội dung câu hỏi','prompt',pygame.Rect(x,y,wide,43),'Nhập câu hỏi...');y+=80
        if typ in ('choice','true_false'):
            label='Sửa đoạn đọc' if self.form['passage'].strip() else 'Thêm đoạn đọc'
            self.btn(label,pygame.Rect(x,y,165,36),lambda:self.open_multiline('passage'))
            y+=55
        if typ=='reading_group':
            self.draw_reading(w,h)
            return
        if typ=='matching':
            self.text('Kiểu nối (3 loại; Hỗn hợp chọn chiều):',x,y-8,self.sm)
            for i,label in enumerate(MATCH_MODES):
                self.btn(label,pygame.Rect(x+(i%2)*(wide//2+2),y+20+(i//2)*46,wide//2-5,40),lambda j=i:self.switch_match_mode(j),self.match_mode==i)
            y+=138
            left_image=self.match_mode in (1,3);right_image=self.match_mode in (1,2)
            # Responsive two-column layout; on narrow windows stack pair inputs.
            stacked=wide<850
            row_height=116 if stacked else 68
            if not stacked:
                self.text('VẾ TRÁI',x,y,self.sm,MUTED)
                self.text('VẾ PHẢI',x+wide//2+10,y,self.sm,MUTED)
                y+=28
            else:
                self.text('Các cặp nối',x,y,self.sm,MUTED)
                y+=28
            for i,pair in enumerate(self.match_pairs):
                base_y=y+i*row_height
                for side,image_side in [('left',left_image),('right',right_image)]:
                    if stacked:
                        xx=x+65; yy=base_y+(0 if side=='left' else 54)
                        rw=wide-75
                        self.text(('Trái' if side=='left' else 'Phải')+' '+str(i+1),x,yy+13,self.sm,MUTED)
                    else:
                        xx=x if side=='left' else x+wide//2+10
                        yy=base_y;rw=wide//2-14
                    rect=pygame.Rect(xx,yy,max(90,rw),43)
                    value=pair[side]
                    if image_side:
                        self.btn(('Ảnh: '+os.path.basename(value) if value else '+ Chọn hình ảnh'),rect,lambda ix=i,sd=side:self.pick_match_image(ix,sd))
                    else:
                        self.rect(rect,WHITE,BLUE if self.active==f'match_{i}_{side}' else LINE,7)
                        self.text(value or 'Nhập chữ...',rect.x+10,rect.y+12,self.sm,INK if value else MUTED,rect.w-20)
                        if self.active==f'match_{i}_{side}':self.draw_caret(rect,value,self.sm)
                        self.actions.append((rect,lambda ix=i,sd=side:setattr(self,'active',f'match_{ix}_{sd}')))
            y+=len(self.match_pairs)*row_height+12
            self.btn('+ Thêm cặp',pygame.Rect(x,y,135,35),self.add_match_pair,disabled=len(self.match_pairs)>=5)
            self.btn('− Bớt cặp',pygame.Rect(x+148,y,135,35),self.remove_match_pair,disabled=len(self.match_pairs)<=2)
            y+=45
        elif typ=='image_multi_choice':
            self.text('Chọn 2–4 ảnh đáp án; đánh dấu một ảnh đúng.',x,y,self.sm,MUTED);y+=42
            images=self.form.setdefault('image_options',[])
            for i,path in enumerate(images):
                self.btn('Ảnh '+str(i+1)+': '+os.path.basename(path),pygame.Rect(x,y,wide-240,40),lambda ix=i:self.pick_option_image(ix))
                self.btn('Đáp án đúng' if self.form.get('image_correct')==path else 'Chọn đúng',pygame.Rect(x+wide-226,y,140,40),lambda p=path:self.form.__setitem__('image_correct',p),self.form.get('image_correct')==path)
                self.btn('Xóa',pygame.Rect(x+wide-78,y,76,40),lambda ix=i:self.remove_option_image(ix))
                y+=51
            self.btn('+ Thêm ảnh',pygame.Rect(x,y,165,40),self.add_option_image,disabled=len(images)>=4);y+=65
        elif typ in ('choice','true_false','picture_choice','listening_choice'):
            self.field('Lựa chọn, ngăn cách bằng dấu |','options',pygame.Rect(x,y,wide,43),'A | B | C | D');y+=80
        elif typ in ('sentence_gaps','conversation_gaps','passage_gaps'):
            self.text('Dùng {1}, {2}, ... trong nội dung; đáp án theo đúng thứ tự.',x,y,self.sm,MUTED);y+=45
            self.field('Đáp án các chỗ trống, ngăn cách bằng |','gap_answers',pygame.Rect(x,y,wide,43),'đáp án 1 | đáp án 2');y+=80
        elif typ=='order':self.field('Thứ tự đúng, phân cách bằng |','sequence',pygame.Rect(x,y,wide,43),'This | is | my | family');y+=80
        elif typ=='error':
            self.field('Từ / cụm từ sai','wrong',pygame.Rect(x,y,wide//2-10,43));self.field('Sửa thành','corrected',pygame.Rect(x+wide//2+8,y,wide//2-8,43));y+=80
        elif typ not in ('fill','listening_fill','picture_missing_letters'):
            self.text('Dạng chưa hỗ trợ chỉnh sửa.',x,y,self.sm,RED);y+=65
        if typ in ('choice','true_false','fill','picture_choice','picture_missing_letters','listening_choice','listening_fill'):
            self.field('Đáp án đúng','answer',pygame.Rect(x,y,wide//2,43),'Nhập đáp án đúng');y+=80
        # Supplementary media is available for all question types, independently
        # of answer-option images and audio-specific exercise behavior.
        self.btn('Chọn âm thanh (tùy chọn)',pygame.Rect(x,y,245,40),self.pick_audio)
        self.btn('Bỏ âm thanh',pygame.Rect(x+252,y,110,40),lambda:self.form.__setitem__('audio',''),disabled=not bool(self.form.get('audio','').strip()))
        self.text(os.path.basename(self.form.get('audio','')) or 'Không có âm thanh',x+375,y+10,self.sm,MUTED,max(80,wide-380))
        y+=62
        self.btn('Chọn hình (tùy chọn)',pygame.Rect(x,y,245,40),self.pick_question_image)
        self.btn('Bỏ hình',pygame.Rect(x+252,y,110,40),lambda:self.form.__setitem__('image',''),disabled=not bool(self.form.get('image','').strip()))
        self.text(os.path.basename(self.form.get('image','')) or 'Không có hình',x+375,y+10,self.sm,MUTED,max(80,wide-380))
        y+=62
        self.field('Độ khó M1–M5','difficulty',pygame.Rect(x,y+20,125,42),'1')

    def switch_match_mode(self,index):
        if self.match_mode!=index:
            self.match_mode=index
            self.match_pairs=[{'left':'','right':''} for _ in range(max(2,len(self.match_pairs)))]
            self.active=None
            self.message='Đã đổi kiểu nối; vui lòng nhập lại các cặp cho đúng loại dữ liệu.'

    def add_match_pair(self):
        if len(self.match_pairs)<5:self.match_pairs.append({'left':'','right':''})

    def remove_match_pair(self):
        if len(self.match_pairs)>2:self.match_pairs.pop()

    def add_option_image(self):
        if len(self.form.setdefault('image_options',[]))<4:self.pick_option_image(len(self.form['image_options']))

    def remove_option_image(self,index):
        options=self.form.setdefault('image_options',[])
        if 0<=index<len(options):
            removed=options.pop(index)
            if self.form.get('image_correct')==removed:self.form['image_correct']=''

    def pick_option_image(self,index):
        root=None
        try:
            root=Tk();root.withdraw();root.attributes('-topmost',True)
            filename=filedialog.askopenfilename(parent=root,title='Chọn ảnh đáp án',filetypes=[('Hình ảnh','*.png *.jpg *.jpeg *.webp *.bmp')])
            if filename:
                options=self.form.setdefault('image_options',[])
                if filename in options and (index>=len(options) or options[index]!=filename):
                    self.message='Không thể chọn ảnh trùng.';return
                if index<len(options):
                    old=options[index];options[index]=filename
                    if self.form.get('image_correct')==old:self.form['image_correct']=filename
                elif len(options)<4:options.append(filename)
        except Exception as exc:self.message='Không thể chọn ảnh: '+str(exc)
        finally:
            if root is not None:root.destroy()

    def edit_visual_layout(self, *, child=False):
        from tuhoc.studio.question_layout_editor import edit_layout
        from tkinter import TclError

        target = self.reading_questions[self.reading_child] if child else None
        data = target if child else self.reading_form if self.edit_type == 'reading_group' else self.form
        kind = 'choice' if child else self.edit_type
        question = {**data, 'id': data.get('id') or self.edit_id, 'type': kind, '_layout_context': 'exam',
                    'prompt': data.get('prompt') or data.get('title', '')}
        if kind == 'matching':
            question['pairs'] = [(pair['left'], pair['right']) for pair in self.match_pairs]
        for field in ('sequence', 'gap_answers'):
            if field in question:
                question[field] = [value.strip() for value in question[field].split('|') if value.strip()]
        def options_for(source):
            return [value.strip() for value in source.split('|') if value.strip()]

        question['options'] = (question.get('image_options', []) if kind == 'image_multi_choice'
                               else options_for(question.get('options', '')))
        if kind == 'reading_group':
            question['questions'] = [{**item, 'options': options_for(item['options'])}
                                     for item in self.reading_questions]
        initial = target.get('layout') if child else self.edit_layout

        def preview(layout, _parent, show_frame):
            from tuhoc.exams.exam_pygame import layout_preview
            show_frame(*layout_preview(self.bank.folder.parent, question, layout))
        root = None
        try:
            root = Tk()
            root.withdraw()
            live_question = {**question, '_preview_root': str(self.bank.folder.parent)}
            if child:
                live_question['_preview_child_index'] = self.reading_child
                live_question['_preview_group'] = {
                    **self.reading_form, 'layout': self.edit_layout,
                    'questions': [{**item, 'options': options_for(item['options'])} for item in self.reading_questions],
                }
            for field in ('image', 'audio'):
                if live_question.get(field):
                    live_question[field] = self.bank._resolve_media(live_question[field])
            if kind == 'image_multi_choice':
                live_question['options'] = [self.bank._resolve_media(path) for path in question['options']]
            layout = edit_layout(root, question, initial, preview=preview, live_question=live_question)
            if layout is not None:
                if child:
                    target['layout'] = layout
                else:
                    self.edit_layout = layout
                self.message = 'Đã cập nhật bản nháp bố cục.'
        except (TclError, ValueError, OSError) as exc:
            self.message = 'Không mở được Studio: ' + str(exc)
        finally:
            if root is not None:
                root.destroy()

    def pick_audio(self):
        root=None
        try:
            root=Tk();root.withdraw();root.attributes('-topmost',True)
            filename=filedialog.askopenfilename(parent=root,title='Chọn file nghe',filetypes=[('Âm thanh','*.mp3 *.ogg *.wav')])
            if filename:self.form['audio']=filename
        except Exception as exc:self.message='Không thể chọn file nghe: '+str(exc)
        finally:
            if root is not None:root.destroy()

    def pick_question_image(self):
        root=None
        try:
            root=Tk();root.withdraw();root.attributes('-topmost',True)
            filename=filedialog.askopenfilename(parent=root,title='Chọn ảnh câu hỏi',filetypes=[('Hình ảnh','*.png *.jpg *.jpeg *.webp *.bmp')])
            if filename:self.form['image']=filename
        except Exception as exc:self.message='Không thể chọn ảnh: '+str(exc)
        finally:
            if root is not None:root.destroy()

    def pick_match_image(self,index,side):
        try:
            root=Tk();root.withdraw();root.attributes('-topmost',True)
            filename=filedialog.askopenfilename(parent=root,title='Chọn hình cho Matching',filetypes=[('Hình ảnh','*.png *.jpg *.jpeg *.webp *.bmp')]);root.destroy()
            if filename:self.match_pairs[index][side]=filename
        except Exception as exc:self.message='Không mở được hộp chọn ảnh: '+str(exc)

    def set_edit_type(self,value):
        self.edit_type=value
        self.active=None
        if value=='reading_group' and not self.reading_questions:
            self.reading_questions=[{'prompt':'','options':'A | B | C | D','answer':'','difficulty':'1'} for _ in range(2)]
            self.reading_form={'title':'','passage':''}

    def next_edit_type(self):
        values=[t[0] for t in TYPES]
        self.edit_type=values[(values.index(self.edit_type)+1)%len(values)]
        self.active=None
        if self.edit_type=='reading_group' and not self.reading_questions:
            self.reading_questions=[{'prompt':'','options':'A | B | C | D','answer':'','difficulty':'1'} for _ in range(2)]
            self.reading_form={'title':'','passage':''}
        if self.edit_type=='reading_group' and self.size[1]<1040:
            self.message='Mẹo: cuộn trang hoặc phóng to cửa sổ để xem đủ trường nhập.'
        if self.edit_type=='matching' and self.size[1]<1180:
            self.message='Mẹo: cuộn trang hoặc phóng to cửa sổ để xem đủ trường nhập.'

    def reading_add(self):
        if len(self.reading_questions)>=10:
            self.message='Mỗi bài đọc tối đa 10 câu.';return
        self.reading_questions.append({'prompt':'','options':'A | B | C | D','answer':'','difficulty':'1'})
        self.reading_select(len(self.reading_questions)-1)

    def reading_remove(self):
        if len(self.reading_questions)<=2:
            self.message='Bài đọc phải có tối thiểu 2 câu.';return
        self.reading_questions.pop(self.reading_child)
        self.reading_select(min(self.reading_child,len(self.reading_questions)-1))

    def reading_select(self,index):
        """Switch child without modifying its draft or persistent ID."""
        if 0 <= index < len(self.reading_questions):
            self.reading_child=index
            self.active=None

    def draw_reading(self,w,h):
        # Compact form: all editing controls fit inside the 720px virtual
        # surface viewport with a short scroll. Child navigation stays visible
        # directly below the passage instead of requiring a long blind scroll.
        x=47;wide=w-95
        self.text('A. NỘI DUNG BÀI ĐỌC',x,410,self.b)
        self.field('Tiêu đề bài đọc','title',pygame.Rect(x,457,wide,38),'Nhập tiêu đề')
        self.text('Đoạn văn',x,512,self.sm,MUTED)
        self.rect(pygame.Rect(x,535,wide-185,42),WHITE,LINE,7)
        preview=self.reading_form.get('passage','').replace('\n','  /  ') or 'Chưa có đoạn văn'
        self.text(preview,x+10,546,self.sm,INK,wide-205)
        self.btn('Soạn đoạn văn',pygame.Rect(x+wide-176,535,176,42),lambda:self.open_multiline('passage'))

        self.text('B. CÂU HỎI CON (2–10 CÂU)',x,604,self.b)
        self.text('Chọn câu để nhập nội dung, lựa chọn và đáp án.',x,630,self.sm,MUTED)
        # Direct-access tabs for every child, including ten-question groups.
        gap=5;tab_w=max(44,min(74,(wide-18-9*gap)//10))
        for index in range(len(self.reading_questions)):
            tab_x=x+index*(tab_w+gap)
            self.btn(str(index+1),pygame.Rect(tab_x,659,tab_w,34),lambda i=index:self.reading_select(i),selected=index==self.reading_child)
        self.btn('+ Thêm câu',pygame.Rect(x,712,123,35),self.reading_add,disabled=len(self.reading_questions)>=10)
        self.btn('Xóa câu',pygame.Rect(x+132,712,108,35),self.reading_remove,disabled=len(self.reading_questions)<=2)
        self.text(f'Đang sửa câu {self.reading_child+1}/{len(self.reading_questions)}',x+256,721,self.sm,BLUE)
        self.btn('Bố cục câu con', pygame.Rect(x+wide-154,712,154,35),
                 lambda: self.edit_visual_layout(child=True))
        self.field('Nội dung câu hỏi con','child_prompt',pygame.Rect(x,800,wide,42),'Nhập nội dung câu hỏi')
        self.field('4 lựa chọn, ngăn cách bằng dấu |','child_options',pygame.Rect(x,888,wide,42),'A | B | C | D')
        self.field('Đáp án đúng (trùng một lựa chọn)','child_answer',pygame.Rect(x,979,wide//2-10,42),'Nhập đáp án đúng')
        self.field('Độ khó (1–5)','child_difficulty',pygame.Rect(x+wide//2+8,979,wide//2-8,42),'1')
        self.text('Lưu bài đọc sẽ lưu toàn bộ câu con; ID cũ được giữ nguyên.',x,1050,self.sm,MUTED,wide)


    def draw_scrollable_config(self,w,h):
        top=262;bottom=h-65;virtual_h=970
        real=self.screen;prior=len(self.actions)
        surface=pygame.Surface((w,virtual_h));surface.fill(BG)
        self.screen=surface;self._hover_offset=self.edit_scroll;self.draw_config(w,virtual_h);self._hover_offset=0;self.screen=real
        maximum=max(0,virtual_h-bottom)
        self.edit_scroll=min(maximum,self.edit_scroll)
        area=pygame.Rect(0,top,w,max(1,bottom-top))
        real.blit(surface,(0,top),pygame.Rect(0,top+self.edit_scroll,w,area.h))
        items=[]
        for r,cb in self.actions[prior:]:
            moved=r.move(0,-self.edit_scroll).clip(area)
            if moved.w>0 and moved.h>0:items.append((moved,cb))
        self.actions=self.actions[:prior]+items
        self.rect(pygame.Rect(0,h-65,w,65),BG)
        self.btn('Lưu tỷ lệ',pygame.Rect(w-190,h-55,162,40),self.save_config_draft)
        self.btn('Hoàn tác',pygame.Rect(w-325,h-55,123,40),self.reset_config_draft)
        self.text('Cuộn chuột để xem Level 1–10',30,h-42,self.sm,MUTED)

    def ensure_config_draft(self):
        if self.config_draft is None:
            import copy
            self.config_draft=copy.deepcopy(self.bank.config())

    def adjust_ratio(self,level,index,delta):
        self.ensure_config_draft()
        row=self.config_draft['ratios'][str(level)]
        # Adjust selected percentage against next level bucket to keep sum = 100.
        other=next((j for j in range(5) if j!=index and (row[j]>0 if delta>0 else row[j]<100)),None)
        if other is None:return
        amount=min(abs(delta),100-row[index] if delta>0 else row[index],row[other] if delta>0 else 100-row[other])
        if amount<=0:return
        row[index]+=amount if delta>0 else -amount
        row[other]-=amount if delta>0 else -amount

    def save_config_draft(self):
        if self.active and self.active.startswith('ratio_'):
            _,l,k=self.active.split('_');self.set_ratio_value(int(l),int(k),self.ratio_buffer);self.active=None
        try:
            self.ensure_config_draft();self.bank.save_config(self.config_draft)
            self.config_error='';self.message='Đã lưu cấu hình tỷ lệ Level.'
        except (ValueError,OSError,KeyError) as exc:self.config_error=str(exc);self.message='Lỗi lưu cấu hình: '+str(exc)

    def reset_config_draft(self):
        self.config_draft=None;self.message='Đã tải lại cấu hình từ dữ liệu đã lưu.'

    def set_ratio_value(self,level,index,value):
        self.ensure_config_draft()
        try:
            if not value.isdigit() or not 0 <= int(value) <= 100:
                raise ValueError('Tỷ lệ phải là số nguyên từ 0 đến 100.')
            self.config_draft['ratios'][str(level)][index]=int(value)
            self.config_error=''
        except ValueError as exc:
            self.config_error=str(exc)

    def ratio_input(self,level,index):
        self.active=f'ratio_{level}_{index}'
        self.ratio_buffer=str(self.config_draft['ratios'][str(level)][index])

    def draw_config(self,w,h):
        self.ensure_config_draft();cfg=self.config_draft
        self.text('Cấu hình đề - chỉnh tỷ lệ M1 đến M5',34,275,self.b)
        self.text(f"{cfg['question_count']} câu / đề  |  {cfg['minutes']} phút  |  Mỗi Level phải đủ 100%",34,312,self.sm,MUTED)
        self.text('Nhấp vào tỷ lệ để nhập trực tiếp (0–100). Mỗi hàng phải bằng 100%.',34,341,self.sm,MUTED)
        col_width=max(100,(w-210)//5)
        for i in range(10):
            level=i+1;y=382+i*48
            row=cfg['ratios'][str(level)]
            self.text(f'Level {level}',35,y+10,self.sm,INK)
            for j,v in enumerate(row):
                x=125+j*col_width
                r=pygame.Rect(x,y,clamp_width(col_width-12),36)
                focused=self.active==f'ratio_{level}_{j}'
                hover=self.hovering(r)
                self.rect(r,(246,250,255) if hover else WHITE,BLUE if focused or hover else LINE,6)
                if focused:pygame.draw.rect(self.screen,BLUE,r,2,border_radius=6)
                shown=self.ratio_buffer if focused else str(v)
                prefix=f'M{j+1}: '
                self.text(f'{prefix}{shown}%',x+8,y+9,self.sm,INK,r.w-12)
                if focused and pygame.time.get_ticks()//520%2==0:
                    cx=min(r.right-12,x+8+self.sm.size(prefix+shown)[0]+1)
                    pygame.draw.line(self.screen,BLUE,(cx,y+8),(cx,y+8+self.sm.get_height()),2)
                self.actions.append((r,lambda l=level,k=j:self.ratio_input(l,k)))
            total=sum(row)
            self.text(f'{total}%',w-75,y+10,self.sm,BLUE if total==100 else RED)
        if self.config_error:self.text(self.config_error,35,875,self.sm,RED,w-70)

def clamp_width(value):
    return max(65,value)

if __name__ == '__main__':
    root=sys.argv[1] if len(sys.argv)>1 else str(PROJECT_ROOT)
    BankManager(root).run()
