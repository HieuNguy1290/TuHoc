from pygame_session_guard import shutdown as _app_shutdown
"""Responsive Pygame exam with independently scrollable reading and answer panels."""
import random
import datetime
import copy
import os
import time
import pygame
from exam_bank import ExamBank, SUBJECTS
from exam_grading import is_correct

VIRTUAL=(1100,720)
BG=(244,247,252); INK=(31,48,72); MUTED=(102,117,139); WHITE=(255,255,255)
BLUE=(51,110,211); GREEN=(43,155,110); BORDER=(215,225,238)
RESOLUTIONS=[(1024,768),(1280,720),(1366,768),(1600,900),(1920,1080)]


def wrap(font,text,width):
    """Wrap on pixel width, including long tokens, while preserving paragraph breaks."""
    result=[]
    for paragraph in str(text or '').split('\n'):
        words=paragraph.split()
        if not words:
            result.append('');continue
        line=''
        for word in words:
            trial=(line+' '+word).strip()
            if font.size(trial)[0]<=width:
                line=trial;continue
            if line:result.append(line);line=''
            while word and font.size(word)[0]>width:
                cut=max(1,len(word)//2)
                while cut<len(word) and font.size(word[:cut+1])[0]<=width:cut+=1
                result.append(word[:cut]);word=word[cut:]
            line=word
        if line:result.append(line)
    return result or ['']


class ExamUI:
    def __init__(self,root,student_id=None):
        self.bank=ExamBank(root);self.student_id=student_id
        self.running=True;self.mode='select';self.subject='tieng_anh';self.grade='';self.lesson='';self.level=1
        self.exam=None;self.answers={};self.index=0;self.deadline=0
        self.scroll=0;self.dropdown=None;self.buttons=[];self.mouse=(-1,-1)
        self.resolution=(1280,720);self.window=None;self.error=None
        self.flagged=set();self.nav_page=0;self.nav_filter='all';self.nav_page_size=40;self.nav_area=pygame.Rect(791,202,254,404);self.read_scroll={};self.scroll_limit=0;self.read_area=pygame.Rect(0,0,0,0)
        self.group_scroll={};self.passage_scroll={};self._focus_child_id=None;self._reading_active_child=None;self.group_passage_area=pygame.Rect(0,0,0,0);self.group_answer_area=pygame.Rect(0,0,0,0)
        self.font=None;self.bold=None;self.big=None;self.small=None
        self.match_pending=None;self.order_inputs={};self.gap_focus=0;self.review_scroll=0;self.review_detail=None;self._image_cache={};self._audio_path=None;self._audio_error=''

    def open(self):
        pygame.init()
        if not pygame.display.get_init():pygame.display.init()
        if not pygame.font.get_init():pygame.font.init()
        try:
            self._set_mode(self.resolution)
            self.font=self._font(22);self.bold=self._font(24,True)
            self.big=self._font(36,True);self.small=self._font(18)
            self.grade=next(iter(self.bank.grades()),'')
            self.lesson=next(iter(self.bank.lessons(self.grade,self.subject)),'')
            self._ensure_family_demo()
            clock=pygame.time.Clock()
            while self.running and not _app_shutdown.is_set():
                for ev in pygame.event.get():
                    if ev.type==pygame.QUIT:self.running=False
                    elif ev.type==pygame.VIDEORESIZE:self._set_mode((max(800,ev.w),max(600,ev.h)))
                    elif ev.type==pygame.KEYDOWN:
                        if ev.key==pygame.K_ESCAPE:
                            if self.dropdown:self.dropdown=None
                            elif self.mode=='exam':self.mode='confirm'
                            elif self.mode=='confirm':self.mode='exam'
                            else:self.running=False
                        elif ev.key==pygame.K_RETURN and self.mode=='confirm':self._submit()
                        elif self.mode=='exam' and self._current_reading_group() and ev.key in (pygame.K_TAB,pygame.K_a,pygame.K_b,pygame.K_c,pygame.K_d):
                            self._reading_key(ev)
                        elif self.mode=='exam' and ev.key in (pygame.K_LEFT,pygame.K_RIGHT):self._move(-1 if ev.key==pygame.K_LEFT else 1)
                        elif self.mode=='exam' and ev.key in (pygame.K_PAGEUP,pygame.K_PAGEDOWN,pygame.K_HOME,pygame.K_END):
                            self._scroll_active_pane(ev.key)
                        elif self.mode=='result' and ev.key==pygame.K_ESCAPE:self.review_detail=None;self._image_cache={};self._audio_path=None;self._audio_error=''
                        elif self.mode=='exam' and self.exam:
                            q=self.exam['questions'][self.index]
                            if q.get('type') in ('sentence_gaps','conversation_gaps','passage_gaps'):
                                self._gap_key(q,ev)
                            if q.get('type') in ('fill','error','picture_missing_letters','listening_fill') and ev.key==pygame.K_BACKSPACE:
                                self.answers[q['id']]=str(self.answers.get(q['id'],''))[:-1]
                    elif ev.type==pygame.TEXTINPUT and self.mode=='exam' and self.exam:
                        q=self.exam['questions'][self.index]
                        if q.get('type') in ('sentence_gaps','conversation_gaps','passage_gaps'):
                            self._gap_text(q,ev.text)
                        if q.get('type') in ('fill','error','picture_missing_letters','listening_fill'):
                            previous=str(self.answers.get(q['id'],''))
                            chunk=''.join(c for c in ev.text if c.isprintable())
                            if chunk:self.answers[q['id']]=(previous+chunk)[:120]
                    elif ev.type==pygame.MOUSEMOTION:self.mouse=self._to_logical(ev.pos) or (-1,-1)
                    elif ev.type==pygame.MOUSEWHEEL:
                        # Wheel events do not carry a reliable cursor position on all Pygame versions.
                        self.mouse=self._to_logical(pygame.mouse.get_pos()) or (-1,-1)
                        if self.dropdown:self.dropdown['scroll']=max(0,min(self.dropdown['maxscroll'],self.dropdown['scroll']-ev.y))
                        elif self.mode=='exam' and self.nav_area.collidepoint(self.mouse):
                            self._set_nav_page(self.nav_page-(1 if ev.y>0 else -1))
                        elif self.mode=='exam' and self._current_reading_group() and (self.group_passage_area.collidepoint(self.mouse) or self.group_answer_area.collidepoint(self.mouse)):
                            self._scroll_reading_pane('passage' if self.group_passage_area.collidepoint(self.mouse) else 'questions',-ev.y*44)
                        elif self.mode=='exam' and self.read_area.collidepoint(self.mouse):
                            self.scroll=max(0,min(self.scroll_limit,self.scroll-ev.y*44));self.read_scroll[self.index]=self.scroll
                        elif self.mode=='result':self.review_scroll=max(0,min(self.review_scroll_limit,self.review_scroll-ev.y*45))
                    elif ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                        pos=self._to_logical(ev.pos)
                        if pos is not None:self._click(pos)
                if self.mode in ('exam','confirm') and time.time()>=self.deadline:self._submit()
                self._draw();clock.tick(30)
        finally:
            try:pygame.mixer.stop()
            except pygame.error:pass
            pygame.quit()

    def _font(self,size,bold=False):
        path=next((pygame.font.match_font(x) for x in ('segoeui','arial','dejavusans','notosans') if pygame.font.match_font(x)),None)
        font=pygame.font.Font(path,size) if path else pygame.font.SysFont(None,size)
        font.set_bold(bold);return font

    def _set_mode(self,res):
        self.resolution=tuple(res);self.window=pygame.display.set_mode(self.resolution,pygame.RESIZABLE)
        pygame.display.set_caption('Kiểm tra - Cùng Học Cùng Vui')
        # Recalculate hover/hit-testing immediately after a resolution change.
        self.mouse=self._to_logical(pygame.mouse.get_pos()) or (-1,-1)

    @staticmethod
    def _viewport_geometry(window_size):
        """Return a centered, aspect-preserving logical viewport (scale, offset)."""
        w,h=window_size
        if w<=0 or h<=0:
            return 0.0,(0.0,0.0)
        scale=min(w/VIRTUAL[0],h/VIRTUAL[1])
        return scale,((w-VIRTUAL[0]*scale)/2,(h-VIRTUAL[1]*scale)/2)

    @staticmethod
    def _map_pointer(pos,window_size):
        """Ignore clicks in letterbox margins; map only the virtual canvas."""
        if pos is None:return None
        scale,(ox,oy)=ExamUI._viewport_geometry(window_size)
        if scale<=0:return None
        x=(pos[0]-ox)/scale;y=(pos[1]-oy)/scale
        return (x,y) if 0<=x<VIRTUAL[0] and 0<=y<VIRTUAL[1] else None

    def _transform(self):
        return self._viewport_geometry(self.window.get_size())

    def _to_logical(self,pos):
        return self._map_pointer(pos,self.window.get_size())

    def _text(self,s,text,x,y,font=None,color=INK,width=None):
        font=font or self.font
        for line in (wrap(font,text,width) if width else [str(text)]):
            if line:s.blit(font.render(line,True,color),(int(x),int(y)))
            y+=font.get_linesize()+5
        return y

    def _button(self,s,label,rect,action,primary=False,small=False):
        r=pygame.Rect(rect);hover=r.collidepoint(self.mouse)
        pygame.draw.rect(s,(37,92,181) if primary and hover else BLUE if primary else (241,247,255) if hover else WHITE,r,border_radius=10)
        pygame.draw.rect(s,(31,92,188) if hover else BLUE if primary else BORDER,r,3 if hover else 2,border_radius=10)
        font=self.small if small else self.bold
        text=font.render(label,True,WHITE if primary else INK)
        if text.get_width()>r.width-14:text=pygame.transform.smoothscale(text,(r.width-14,text.get_height()))
        s.blit(text,text.get_rect(center=r.center));self.buttons.append((r,action))

    def _select(self,s,label,value,rect,choices,handler):
        x,y,w,h=rect;self._text(s,label,x,y-32,self.small,MUTED)
        hover=pygame.Rect(rect).collidepoint(self.mouse)
        pygame.draw.rect(s,(241,247,255) if hover else WHITE,rect,border_radius=9)
        pygame.draw.rect(s,BLUE if hover else BORDER,rect,3 if hover else 2,border_radius=9)
        display=str(value or 'Chưa có dữ liệu')
        while display and self.font.size(display)[0]>w-58:display=display[:-1]
        self._text(s,display,x+12,y+10)
        # Draw dropdown chevron as geometry, independent of Unicode font coverage.
        cx=x+w-24;cy=y+h//2
        pygame.draw.lines(s,BLUE if hover else MUTED,False,[(cx-6,cy-3),(cx,cy+3),(cx+6,cy-3)],2)
        self.buttons.append((pygame.Rect(rect),lambda:self._open_dropdown(rect,choices,handler)))

    def _open_dropdown(self,rect,choices,handler):
        choices=list(choices);self.dropdown={'rect':rect,'choices':choices,'handler':handler,'scroll':0,'maxscroll':max(0,len(choices)-8)}

    def _click(self,pos):
        if self.dropdown:
            d=self.dropdown;x,y,w,h=d['rect'];top=min(y+h+4,685-min(len(d['choices']),8)*42)
            idx=int((pos[1]-top)//42)+d['scroll']
            if x<=pos[0]<=x+w and top<=pos[1]<top+min(len(d['choices']),8)*42 and idx<len(d['choices']):d['handler'](d['choices'][idx])
            self.dropdown=None;return
        for rect,action in reversed(self.buttons):
            if rect.collidepoint(pos):action();return

    def _draw(self):
        s=pygame.Surface(VIRTUAL);s.fill(BG);self.buttons=[]
        pygame.draw.rect(s,WHITE,(28,23,1044,676),border_radius=16)
        if self.mode=='select':self._draw_select(s)
        elif self.mode=='exam':self._draw_exam(s)
        elif self.mode=='confirm':self._draw_confirm(s)
        else:self._draw_result(s)
        if self.dropdown:
            d=self.dropdown;x,y,w,h=d['rect'];top=min(y+h+4,685-min(len(d['choices']),8)*42)
            for i,choice in enumerate(d['choices'][d['scroll']:d['scroll']+8]):
                rr=pygame.Rect(x,top+i*42,w,42);hover=rr.collidepoint(self.mouse)
                pygame.draw.rect(s,(240,247,255) if hover else WHITE,rr)
                pygame.draw.rect(s,BLUE if hover else BORDER,rr,2 if hover else 1)
                label=str(choice)
                while label and self.font.size(label)[0]>w-18:label=label[:-1]
                self._text(s,label,x+10,top+i*42+7)
        scale,(ox,oy)=self._transform();self.window.fill((223,230,239))
        output=pygame.transform.smoothscale(s,(max(1,round(VIRTUAL[0]*scale)),max(1,round(VIRTUAL[1]*scale))))
        self.window.blit(output,(round(ox),round(oy)));pygame.display.flip()

    def _draw_select(self,s):
        self._text(s,'TRUNG TÂM KIỂM TRA',65,53,self.big)
        self._text(s,'Chọn môn học, lớp, bài học và Level',65,105,self.font,MUTED)
        self._select(s,'1. Môn học',SUBJECTS[self.subject],(65,192,292,54),list(SUBJECTS.values()),self._subject_changed)
        self._select(s,'2. Chọn lớp',self.grade,(400,192,292,54),self.bank.grades(),self._grade_changed)
        self._select(s,'3. Chọn bài học',self.lesson,(735,192,292,54),self.bank.lessons(self.grade,self.subject),self._lesson_changed)
        self._select(s,'4. Chọn Level',f'Level {self.level}',(65,319,292,54),[f'Level {i}' for i in range(1,11)],self._level_changed)
        self._select(s,'Độ phân giải',f'{self.resolution[0]} x {self.resolution[1]}',(735,319,292,54),[f'{w} x {h}' for w,h in RESOLUTIONS],lambda v:self._set_mode(tuple(map(int,v.split(' x ')))))
        cfg=self.bank.config();self._text(s,f'Số câu: {cfg["question_count"]}    |    Thời gian: {cfg["minutes"]} phút',65,425,self.bold)
        self._text(s,'Đề ngẫu nhiên theo tỷ lệ độ khó. Tất cả Level đều mở tự do.',65,472,self.font,MUTED)
        if self.error:self._text(s,self.error,65,513,self.small,(180,50,50),width=950)
        self._button(s,'Làm bài',(390,573,320,65),self._start,True)
        self._button(s,'Thoát',(65,573,180,65),lambda:setattr(self,'running',False))

    def _subject_changed(self,label):
        self.subject=next((k for k,v in SUBJECTS.items() if v==label),'tieng_anh')
        self.lesson=next(iter(self.bank.lessons(self.grade,self.subject)),'');self.error=None
    def _grade_changed(self,grade):
        self.grade=grade;self.lesson=next(iter(self.bank.lessons(grade,self.subject)),'');self.error=None
    def _lesson_changed(self,lesson):self.lesson=lesson;self.error=None
    def _level_changed(self,level):self.level=int(level.split()[-1]);self.error=None

    def _ensure_family_demo(self):
        """One-time, additive Grade 1 English Family demo setup for Patch 02.

        Never remove teacher-created questions; never touch other subjects.
        """
        if self.subject != 'tieng_anh' or str(self.grade) != '1' or 'family' not in self.lesson.casefold():
            return
        try:
            from seed_family_grade1 import install
            rows=self.bank.questions()
            demo=[q for q in rows if str(q.get('id','')).startswith('DEMO_EN_G1_FAMILY_') and
                  str(q.get('grade'))=='1' and str(q.get('lesson'))==str(self.lesson) and
                  str(q.get('subject','tieng_anh'))=='tieng_anh']
            if len(demo)<75:
                install(self.bank.folder.parent,self.lesson)
        except Exception as exc:
            self.error='Không thể nạp bộ câu hỏi mẫu: '+str(exc)

    def _start(self):
        try:
            if not self.grade or not self.lesson:raise ValueError('Hãy chọn lớp và bài học.')
            self.error=None
            self._ensure_family_demo()
            if self.error:raise ValueError(self.error)
            self.exam=self.bank.create_exam(self.grade,self.lesson,self.level,subject=self.subject)
        except (ValueError,KeyError,TypeError) as exc:self.error=str(exc);return
        self.answers={};self.index=0;self.scroll=0;self.flagged=set();self.nav_page=0;self.nav_filter='all';self.read_scroll={};self.match_pending=None;self.order_inputs={}
        self.gap_focus=0;self.group_scroll={};self.passage_scroll={};self._focus_child_id=None;self._reading_active_child=None
        self.deadline=time.time()+self.exam['minutes']*60;self.mode='exam';self.error=None
        pygame.key.start_text_input()

    def _group_span(self,index):
        """Return inclusive indices of a contiguous, eligible reading group."""
        questions=self.exam.get('questions',[]) if self.exam else []
        if not 0<=index<len(questions):return index,index
        gid=questions[index].get('reading_group')
        if not gid:return index,index
        indices=[i for i,q in enumerate(questions) if q.get('reading_group')==gid]
        if len(indices)<2 or any(questions[i].get('type')!='choice' for i in indices):return index,index
        if indices!=list(range(indices[0],indices[-1]+1)):return index,index
        return indices[0],indices[-1]

    def _nav_indices(self):
        """Return original question indices matching the current palette filter."""
        if not self.exam:return []
        questions=self.exam.get('questions',[])
        if self.nav_filter=='answered':
            return [i for i,q in enumerate(questions) if bool(self.answers.get(q['id']))]
        if self.nav_filter=='unanswered':
            return [i for i,q in enumerate(questions) if not self.answers.get(q['id'])]
        if self.nav_filter=='flagged':
            return [i for i in range(len(questions)) if self._flagged_for(i)]
        return list(range(len(questions)))

    def _set_nav_filter(self,value):
        if value not in ('all','answered','unanswered','flagged'):return
        self.nav_filter=value
        self.nav_page=0

    def _nav_page_count(self):
        n=len(self._nav_indices())
        return max(1,(n+self.nav_page_size-1)//self.nav_page_size)

    def _set_nav_page(self,page):
        self.nav_page=max(0,min(self._nav_page_count()-1,int(page)))

    def _sync_nav_page(self,index):
        indices=self._nav_indices()
        if index in indices:self._set_nav_page(indices.index(index)//self.nav_page_size)
        else:self._set_nav_page(self.nav_page)

    def _flagged_for(self,index):
        """A reading-group flag applies to its whole group."""
        start,end=self._group_span(index)
        return any(i in self.flagged for i in range(start,end+1))

    def _move(self,step):
        """Previous/next navigates by a whole reading group, never by child."""
        if not self.exam:return
        self.read_scroll[self.index]=self.scroll
        start,end=self._group_span(self.index)
        target=(end+1 if step>0 else start-1) if step else self.index
        if step<0 and target>=0:target=self._group_span(target)[0]
        self.index=max(0,min(len(self.exam['questions'])-1,target))
        self.scroll=self.read_scroll.get(self.index,0);self.gap_focus=0;self._focus_child_id=None;self._sync_nav_page(self.index)

    def _jump(self,index,focus_child=False):
        """Palette jumps to the containing group, retaining its first child as anchor."""
        if not self.exam:return
        self.read_scroll[self.index]=self.scroll
        start,end=self._group_span(index)
        self._focus_child_id=self.exam['questions'][index]['id'] if focus_child and end>start else None
        self.index=max(0,min(len(self.exam['questions'])-1,start))
        self.scroll=self.read_scroll.get(self.index,0);self.gap_focus=0;self._sync_nav_page(index)

    def _unanswered_indices(self):
        if not self.exam:return []
        return [i for i,q in enumerate(self.exam['questions']) if not self.answers.get(q['id'])]

    def _go_first_unanswered(self):
        missing=self._unanswered_indices()
        if missing:self._jump(missing[0],focus_child=True)
        self.mode='exam'

    def _flagged_indices(self):
        """Return unique, ordered question indices whose group is marked."""
        if not self.exam:return []
        return [i for i in range(len(self.exam['questions'])) if self._flagged_for(i)]

    def _go_first_flagged(self):
        """Open the first flagged group, including its first child question."""
        marked=self._flagged_indices()
        if marked:self._jump(marked[0],focus_child=True)
        self.nav_filter='flagged' if marked else 'all'
        self._sync_nav_page(self.index)
        self.mode='exam'

    def _toggle_flag(self):
        """Toggle one group-level flag; do not leave stale child flags behind."""
        start,end=self._group_span(self.index)
        existing=[i for i in range(start,end+1) if i in self.flagged]
        if existing:
            for i in existing:self.flagged.discard(i)
        else:self.flagged.add(start)
        self._sync_nav_page(self.index)

    def _draw_exam(self,s):
        questions=self.exam['questions'];q=questions[self.index];n=len(questions)
        remaining=max(0,int(self.deadline-time.time()));timer=f'{remaining//60:02d}:{remaining%60:02d}'
        pygame.draw.rect(s,(25,58,99),(28,23,1044,137),border_top_left_radius=16,border_top_right_radius=16)
        self._text(s,'BÀI KIỂM TRA',56,41,self.bold,WHITE)
        summary=f'{SUBJECTS[self.subject]}  |  Lớp {self.grade}  |  {self.lesson}  |  Level {self.level}'
        self._text(s,summary,56,83,self.small,(209,226,245),width=770)
        pygame.draw.rect(s,(52,85,123),(879,39,157,75),border_radius=9)
        self._text(s,timer,903,45,self.big,(255,194,170) if remaining<300 else WHITE)
        self._text(s,'Còn lại',925,91,self.small,(218,230,245))
        answered=sum(bool(self.answers.get(item['id'])) for item in questions)
        self._text(s,f'Đã trả lời {answered}/{n} câu',56,127,self.small,WHITE)
        pygame.draw.rect(s,(214,225,240),(55,176,990,7),border_radius=4)
        if answered:pygame.draw.rect(s,GREEN,(55,176,max(2,int(990*answered/n)),7),border_radius=4)
        # Two independent columns: scroll content is clipped, controls remain fixed.
        left=pygame.Rect(55,202,721,404);right=pygame.Rect(791,202,254,404)
        pygame.draw.rect(s,(247,249,253),left,border_radius=11)
        pygame.draw.rect(s,WHITE,right,border_radius=11);pygame.draw.rect(s,BORDER,right,2,border_radius=11)
        start,end=self._group_span(self.index)
        position=f'Bài đọc: câu {start+1}-{end+1}/{n}' if end>start else f'Câu {self.index+1}/{n}'
        self._text(s,position,72,216,self.small,MUTED)
        self._button(s,'Bỏ cờ' if self._flagged_for(self.index) else 'Đánh dấu',(614,211,145,39),self._toggle_flag,small=True)
        self.read_area=pygame.Rect(68,260,694,331)
        self.group_passage_area=pygame.Rect(0,0,0,0);self.group_answer_area=pygame.Rect(0,0,0,0)
        if self._current_reading_group():self._draw_reading_group(s)
        elif q.get('type') in ('fill','error','picture_missing_letters','listening_fill','order','matching','sentence_gaps','conversation_gaps','passage_gaps'):self._draw_interactive(s,q)
        else:self._draw_reading(s,q)
        self._text(s,'DANH SÁCH CÂU',806,218,self.small,INK)
        # Filter buttons preserve original question numbers and reading-group anchors.
        filter_names=(('all','Tất cả'),('answered','Đã làm'),('unanswered','Chưa làm'),('flagged','Đánh dấu'))
        for col,(key,title) in enumerate(filter_names):
            x=799+col*62
            rect=pygame.Rect(x,244,60,28)
            active_filter=self.nav_filter==key
            pygame.draw.rect(s,BLUE if active_filter else (237,242,250),rect,border_radius=5)
            pygame.draw.rect(s,BORDER,rect,1,border_radius=5)
            font=self._font(12,active_filter)
            label=font.render(title,True,WHITE if active_filter else INK)
            s.blit(label,label.get_rect(center=rect.center))
            self.buttons.append((rect,lambda v=key:self._set_nav_filter(v)))
        indices=self._nav_indices()
        self._set_nav_page(self.nav_page)
        first=self.nav_page*self.nav_page_size
        visible=indices[first:first+self.nav_page_size]
        cell=40;gap=6;startx=806;starty=283
        for local,i in enumerate(visible):
            row,col=divmod(local,5)
            rect=pygame.Rect(startx+col*(cell+gap),starty+row*28,cell,25)
            active=self._group_span(i)==self._group_span(self.index)
            answered_i=bool(self.answers.get(questions[i]['id']))
            bg=BLUE if active else (205,239,222) if answered_i else (239,243,248)
            pygame.draw.rect(s,bg,rect,border_radius=5)
            pygame.draw.rect(s,(29,90,189) if rect.collidepoint(self.mouse) else BORDER,rect,2 if rect.collidepoint(self.mouse) else 1,border_radius=5)
            label=self.small.render(str(i+1),True,WHITE if active else INK)
            s.blit(label,label.get_rect(center=rect.center))
            pygame.draw.circle(s,GREEN if answered_i else (211,126,67),(rect.x+5,rect.y+5),3)
            if self._flagged_for(i):pygame.draw.circle(s,(230,139,42),(rect.right-4,rect.top+4),4)
            self.buttons.append((rect,lambda index=i:self._jump(index,focus_child=True)))
        pages=self._nav_page_count()
        self._button(s,'<',(806,514,45,36),lambda:self._set_nav_page(self.nav_page-1),small=True)
        self._text(s,f'{self.nav_page+1}/{pages}',873,520,self.small,MUTED)
        self._button(s,'>',(986,514,45,36),lambda:self._set_nav_page(self.nav_page+1),small=True)
        if visible:self._text(s,f'Hiển thị {first+1}-{first+len(visible)}/{len(indices)}',806,554,self.small,MUTED)
        else:self._text(s,'Không có câu phù hợp',806,554,self.small,MUTED)
        self._text(s,f'Đã trả lời: {answered}/{n}',805,577,self.small,GREEN)
        self._button(s,'Nhóm trước',(55,625,195,53),lambda:self._move(-1),small=True)
        self._button(s,'Nhóm tiếp',(270,625,195,53),lambda:self._move(1),small=True)
        self._button(s,'Nộp bài',(807,625,238,53),lambda:setattr(self,'mode','confirm'),True,small=True)

    def _play_audio(self,path):
        try:
            if not pygame.mixer.get_init():pygame.mixer.init()
            pygame.mixer.music.stop()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            self._audio_path=path;self._audio_error=''
        except (pygame.error,OSError,ValueError) as exc:
            self._audio_error='Không thể phát file nghe: '+str(exc)[:90]

    def _audio_button(self,s,q,x,y,local=False):
        path=str(q.get('audio',''))
        rect=pygame.Rect(x,y,255,49)
        pygame.draw.rect(s,(225,238,253),rect,border_radius=8)
        pygame.draw.rect(s,BLUE,rect,2,border_radius=8)
        self._text(s,'▶ Phát lại âm thanh',x+12,y+10,self.small,INK)
        if local:
            self.buttons.append((rect,lambda p=path:self._play_audio(p)))
        else:
            screen_rect=pygame.Rect(self.read_area.x+rect.x,self.read_area.y+rect.y-self.scroll,rect.w,rect.h)
            clipped=screen_rect.clip(self.read_area)
            if clipped.width and clipped.height:self.buttons.append((clipped,lambda p=path:self._play_audio(p)))
        if self._audio_error:self._text(s,self._audio_error,x,y+53,self.small,(176,57,57),width=620)

    def _draw_interactive(self,s,q):
        """Text entry, ordered tokens, and clickable pair matching (Patch 05B)."""
        kind=q['type'];qid=q['id'];x=16;y=14
        # Render into a virtual content surface, then clip to the answer viewport.
        # This keeps all fields accessible regardless of question length.
        original_buttons=self.buttons
        self.buttons=[]
        count=len(q.get('gap_answers',[]))
        pairs=len(q.get('pairs',[]))
        words=len(q.get('sequence',[]))
        prompt_height=len(wrap(self.bold,str(q.get('prompt','')),645))*(self.bold.get_linesize()+5)+50
        estimated=max(self.read_area.height, prompt_height+max(count*62+80,pairs*46+115,((words+3)//4)*60+230,380 if kind=='picture_missing_letters' else 180))
        canvas=pygame.Surface((self.read_area.width,estimated),pygame.SRCALPHA)
        self._interactive_target=s
        s=canvas
        y=self._text(s,str(q.get('prompt','')),x,y,self.bold,INK,width=645)+18
        if kind=='listening_fill':
            self._audio_button(s,q,x,y,local=True);y+=75
        if kind in ('sentence_gaps','conversation_gaps','passage_gaps'):
            count=len(q.get('gap_answers',[]));values=self.answers.get(qid,[])
            if not isinstance(values,list) or len(values)!=count:values=['']*count
            self._text(s,'Nhấn vào ô để nhập; Tab chuyển ô tiếp theo.',x,y,self.small,MUTED)
            y+=36
            for i in range(count):
                rect=pygame.Rect(x,y+i*62,615,50)
                pygame.draw.rect(s,WHITE,rect,border_radius=8)
                pygame.draw.rect(s,BLUE if i==self.gap_focus else BORDER,rect,3 if i==self.gap_focus else 1,border_radius=8)
                label=f'{i+1}.  '+values[i]+(' |' if i==self.gap_focus else '')
                self._text(s,label[:80],rect.x+12,rect.y+11,self.small,INK)
                self.buttons.append((rect,lambda ix=i:setattr(self,'gap_focus',ix)))
            self._finish_interactive(s,original_buttons,estimated);return
        if kind in ('fill','error','picture_missing_letters','listening_fill'):
            if kind=='error':
                y=self._text(s,'Từ / cụm từ sai: '+str(q.get('wrong','')),x,y,self.font,MUTED)+16
            self._text(s,'Nhập đáp án bằng bàn phím (Backspace để xóa):',x,y,self.small,MUTED)
            value=str(self.answers.get(qid,''))
            rect=pygame.Rect(x,y+40,635,62)
            pygame.draw.rect(s,WHITE,rect,border_radius=9);pygame.draw.rect(s,BLUE,rect,2,border_radius=9)
            self._text(s,value+' |',x+15,y+53,self.font,INK,width=600)
            self._finish_interactive(s,original_buttons,estimated);return
        if kind=='order':
            sequence=list(q.get('sequence',[]))
            rng=random.Random(str(qid));rng.shuffle(sequence)
            picked=self.order_inputs.setdefault(qid,[])
            self._text(s,'Chọn lần lượt các từ theo đúng thứ tự:',x,y,self.small,MUTED);y+=39
            self._text(s,' '.join(picked) or '(Chưa chọn)',x,y,self.font,BLUE,width=635);y+=73
            for i,word in enumerate(sequence):
                if word in picked:continue
                col=i%4;row=i//4
                self._button(s,str(word),(x+col*160,y+row*60,150,50),lambda w=word:self._pick_order(q,w),small=True)
            self._button(s,'Làm lại',(x,y+155,160,43),lambda:self._reset_order(qid),small=True)
            self._finish_interactive(s,original_buttons,estimated);return
        if kind=='matching':
            pairs=q.get('pairs',[])
            left=[p[0] for p in pairs];right=[p[1] for p in pairs]
            random.Random(str(qid)).shuffle(right)
            matched=self.answers.get(qid,{})
            if not isinstance(matched,dict):matched={}
            self._text(s,'Chọn một mục bên trái, sau đó chọn mục tương ứng bên phải.',x,y,self.small,MUTED)
            y+=40
            for i,word in enumerate(left):
                active=self.match_pending==(qid,word)
                label=('✓ ' if word in matched else '→ ' if active else '')+word
                self._button(s,label,(x,y+i*46,285,40),lambda w=word:self._select_match_left(qid,w),small=True)
            for i,word in enumerate(right):
                linked=next((a for a,b in matched.items() if b==word),None)
                label=('✓ ' if linked else '')+word
                self._button(s,label,(x+327,y+i*46,285,40),lambda w=word:self._select_match_right(qid,w),small=True)
            self._button(s,'Xóa các cặp',(x,y+len(pairs)*46+9,190,37),lambda:self._clear_match(qid),small=True)
        self._finish_interactive(s,original_buttons,estimated)

    def _finish_interactive(self,canvas,original_buttons,height):
        """Clip long interactive forms and remap hit targets to visible coordinates."""
        content_buttons=self.buttons
        self.buttons=original_buttons
        self.scroll_limit=max(0,height-self.read_area.height)
        self.scroll=max(0,min(self.scroll,self.scroll_limit))
        self.read_scroll[self.index]=self.scroll
        visible=pygame.Rect(0,int(self.scroll),self.read_area.width,self.read_area.height)
        self._interactive_target.blit(canvas,self.read_area.topleft,visible)
        for rect,action in content_buttons:
            target=pygame.Rect(rect).move(self.read_area.x,self.read_area.y-int(self.scroll))
            target=target.clip(self.read_area)
            if target.width>0 and target.height>0:self.buttons.append((target,action))
        if self.scroll_limit:
            track=pygame.Rect(self.read_area.right-5,self.read_area.y,4,self.read_area.height)
            pygame.draw.rect(self._interactive_target,(225,232,242),track,border_radius=3)
            thumb_h=max(25,int(track.height*self.read_area.height/height))
            thumb_y=track.y+int((track.height-thumb_h)*self.scroll/self.scroll_limit)
            pygame.draw.rect(self._interactive_target,BLUE,(track.x,thumb_y,4,thumb_h),border_radius=3)

    def _gap_text(self,q,text):
        count=len(q.get('gap_answers',[]))
        values=self.answers.get(q['id'],[])
        if not isinstance(values,list) or len(values)!=count:values=['']*count
        if count:
            i=min(max(0,self.gap_focus),count-1)
            values[i]=(values[i]+''.join(c for c in text if c.isprintable()))[:120]
            self.answers[q['id']]=values

    def _gap_key(self,q,event):
        count=len(q.get('gap_answers',[]))
        if not count:return
        if event.key==pygame.K_TAB:
            self.gap_focus=(self.gap_focus+1)%count
            # Keep the newly focused field visible within the scroll viewport.
            prompt_height=len(wrap(self.bold,str(q.get('prompt','')),645))*(self.bold.get_linesize()+5)+50
            field_top=prompt_height+36+self.gap_focus*62
            if field_top+50>self.scroll+self.read_area.height:
                self.scroll=field_top+50-self.read_area.height+12
            elif field_top<self.scroll:
                self.scroll=max(0,field_top-12)
            self.scroll=min(self.scroll,self.scroll_limit)
            return
        if event.key==pygame.K_BACKSPACE:
            values=self.answers.get(q['id'],[])
            if not isinstance(values,list) or len(values)!=count:values=['']*count
            values[self.gap_focus]=values[self.gap_focus][:-1]
            self.answers[q['id']]=values

    def _pick_order(self,q,word):
        qid=q['id'];picked=self.order_inputs.setdefault(qid,[])
        if word not in picked:picked.append(word)
        self.answers[qid]=' '.join(picked) if len(picked)==len(q.get('sequence',[])) else ''
        if not self.answers[qid]:self.answers.pop(qid,None)

    def _reset_order(self,qid):
        self.order_inputs[qid]=[];self.answers.pop(qid,None)

    def _select_match_left(self,qid,word):self.match_pending=(qid,word)
    def _select_match_right(self,qid,word):
        if not self.match_pending or self.match_pending[0]!=qid:return
        left=self.match_pending[1];mapping=self.answers.setdefault(qid,{})
        for k in list(mapping):
            if mapping[k]==word:del mapping[k]
        mapping[left]=word;self.match_pending=None
    def _clear_match(self,qid):self.answers.pop(qid,None);self.match_pending=None

    def _is_correct(self,q):
        return is_correct(q,self.answers.get(q['id']),self.order_inputs.get(q['id']))

    def _current_reading_group(self):
        """Return (group ID, ordered children) only for a genuine multi-question group."""
        if not self.exam or self.mode != 'exam':return None
        questions=self.exam.get('questions',[])
        if not 0<=self.index<len(questions):return None
        q=questions[self.index];gid=q.get('reading_group')
        if not gid:return None
        positions=[i for i,x in enumerate(questions) if x.get('reading_group')==gid]
        # The renderer must use the same contiguous-group rule as navigation.
        # A malformed/imported exam must never merge nonadjacent questions.
        if len(positions)<2 or positions!=list(range(positions[0],positions[-1]+1)):
            return None
        children=[questions[i] for i in positions]
        if any(x.get('type')!='choice' for x in children):return None
        return gid,children

    @staticmethod
    def _next_reading_child(ids,current,backward=False):
        """Cycle focus through ordered child IDs; does not change stored answers."""
        if not ids:return None
        if current not in ids:return ids[-1] if backward else ids[0]
        return ids[(ids.index(current)+(-1 if backward else 1))%len(ids)]

    def _reading_key(self,event):
        """Tab/Shift+Tab selects a child; A-D answers only the focused child."""
        group=self._current_reading_group()
        if not group:return
        _,children=group
        ids=[child['id'] for child in children]
        if event.key==pygame.K_TAB:
            backwards=bool(event.mod & pygame.KMOD_SHIFT)
            self._reading_active_child=self._next_reading_child(ids,self._reading_active_child,backwards)
            self._focus_child_id=self._reading_active_child
            return
        if self._reading_active_child not in ids:
            self._reading_active_child=ids[0]
        child=next(child for child in children if child['id']==self._reading_active_child)
        option_ix=event.key-pygame.K_a
        options=child.get('options',[])
        if 0<=option_ix<len(options):
            self.answers[child['id']]=options[option_ix]
            self._focus_child_id=child['id']

    def _choose_reading_option(self,qid,value):
        """Mouse selection also updates keyboard focus."""
        self.answers[qid]=value
        self._reading_active_child=qid

    @staticmethod
    def _bounded_scroll(current,delta,limit):
        """Clamp reading-pane scrolling even with stale offsets or short content."""
        return max(0,min(max(0,int(limit)),int(current)+int(delta)))

    def _scroll_reading_pane(self,pane,delta,absolute=False):
        """Scroll exactly one pane; do not modify answers or the other pane."""
        group=self._current_reading_group()
        if not group or pane not in ('passage','questions'):
            return False
        gid=group[0]
        offsets=self.passage_scroll if pane=='passage' else self.group_scroll
        limit=getattr(self,'_passage_scroll_limit',0) if pane=='passage' else getattr(self,'_group_scroll_limit',0)
        previous=offsets.get(gid,0)
        offsets[gid]=self._bounded_scroll(0 if absolute else previous,delta,limit)
        return offsets[gid]!=previous

    def _scroll_active_pane(self,key):
        """PageUp/PageDown/Home/End target the pane beneath the mouse."""
        group=self._current_reading_group()
        if not group:
            return
        if self.group_passage_area.collidepoint(self.mouse):
            pane='passage';height=self.group_passage_area.height;limit=getattr(self,'_passage_scroll_limit',0)
        else:
            pane='questions';height=self.group_answer_area.height;limit=getattr(self,'_group_scroll_limit',0)
        if key==pygame.K_HOME:self._scroll_reading_pane(pane,0,absolute=True)
        elif key==pygame.K_END:self._scroll_reading_pane(pane,limit,absolute=True)
        elif key==pygame.K_PAGEUP:self._scroll_reading_pane(pane,-max(40,height-40))
        elif key==pygame.K_PAGEDOWN:self._scroll_reading_pane(pane,max(40,height-40))

    @staticmethod
    def _reading_child_status(child_id,answers,active_id):
        """Pure status helper shared by mouse/keyboard reading UI."""
        answered=bool(answers.get(child_id))
        return ('active_answered' if answered else 'active_unanswered') if child_id==active_id else ('answered' if answered else 'unanswered')

    def _focus_reading_child(self,qid):
        """Select a child without modifying its answer; reveal it on next draw."""
        group=self._current_reading_group()
        if group and any(child['id']==qid for child in group[1]):
            self._reading_active_child=qid
            self._focus_child_id=qid

    def _draw_reading_group(self,s):
        """Fixed passage on left; all child questions on right, independently scrollable."""
        gid,children=self._current_reading_group()
        ids=[child['id'] for child in children]
        if self._reading_active_child not in ids:self._reading_active_child=ids[0]
        completed=sum(bool(self.answers.get(cid)) for cid in ids)
        outer=self.read_area
        gap=12;left_w=320;right_x=outer.x+left_w+gap;right_w=outer.width-left_w-gap
        self.group_passage_area=pygame.Rect(outer.x,outer.y,left_w,outer.height)
        self.group_answer_area=pygame.Rect(right_x,outer.y,right_w,outer.height)
        pygame.draw.rect(s,WHITE,self.group_passage_area,border_radius=7)
        pygame.draw.rect(s,WHITE,self.group_answer_area,border_radius=7)
        pygame.draw.rect(s,BORDER,self.group_passage_area,1,border_radius=7)
        pygame.draw.rect(s,BORDER,self.group_answer_area,1,border_radius=7)
        # Compact progress above the pane, always visible while either pane scrolls.
        self._text(s,f'Bài đọc: {completed}/{len(ids)} câu đã làm',self.group_answer_area.x+7,242,self.small,GREEN if completed==len(ids) else MUTED)
        def text_lines(surface,txt,font,x,y,width,color=INK):
            for line in wrap(font,txt,width):
                if line:surface.blit(font.render(line,True,color),(x,y))
                y+=font.get_linesize()+5
            return y
        # Passage is rendered once and scrolls without moving the questions.
        passage=str(children[0].get('passage') or children[0].get('reading') or '')
        pw=left_w-24;py=12
        pitems=[('BÀI ĐỌC: '+str(children[0].get('reading_title','')),self.small,BLUE)]
        pitems.extend((paragraph,self.font,INK) for paragraph in passage.split('\n'))
        for txt,font,_ in pitems:py+=len(wrap(font,txt,pw))*(font.get_linesize()+5)+15
        self._passage_scroll_limit=max(0,py-self.group_passage_area.height)
        ps=max(0,min(self.passage_scroll.get(gid,0),self._passage_scroll_limit));self.passage_scroll[gid]=ps
        # Render only the visible passage viewport, not a surface as tall as the text.
        passage_surface=pygame.Surface((left_w,outer.height),pygame.SRCALPHA)
        y=12
        for txt,font,color in pitems:
            lines=wrap(font,txt,pw)
            line_h=font.get_linesize()+5
            for line in lines:
                visible_y=y-ps
                if line and -line_h < visible_y < outer.height:
                    passage_surface.blit(font.render(line,True,color),(12,visible_y))
                y+=line_h
            y+=15
        s.blit(passage_surface,(outer.x,outer.y))
        # Each child retains its own answer ID. Scroll only the question pane.
        qw=right_w-24;line_h=self.font.get_linesize()+5
        entries=[];child_tops={};y=12
        for ix,child in enumerate(children):
            qid=child['id'];child_tops[qid]=y;prompt=str(child.get('prompt',''))
            entries.append(('heading',(ix,child),y));y+=self.small.get_linesize()+13
            entries.append(('prompt',prompt,y));y+=len(wrap(self.font,prompt,qw)) * line_h+14
            for option_ix,opt in enumerate(child.get('options',[])):
                lines=wrap(self.small,f'{chr(65+option_ix)}. {opt}',qw-22)
                h=max(39,len(lines)*(self.small.get_linesize()+4)+14)
                entries.append(('option',(qid,opt,lines),y,h));y+=h+7
            y+=20
        self._group_scroll_limit=max(0,y-self.group_answer_area.height)
        gs=max(0,min(self.group_scroll.get(gid,0),self._group_scroll_limit))
        if self._focus_child_id in child_tops:
            gs=max(0,min(child_tops[self._focus_child_id]-12,self._group_scroll_limit))
            self._focus_child_id=None
        self.group_scroll[gid]=gs
        # Viewport-sized surface bounds memory for long passages and many children.
        answers_surface=pygame.Surface((right_w,outer.height),pygame.SRCALPHA)
        for entry in entries:
            kind,value,top=entry[:3]
            entry_height=(entry[3] if kind=='option' else (self.small.get_linesize()+13 if kind=='heading' else len(wrap(self.font,value,qw))*line_h+14))
            if top+entry_height < gs or top > gs+outer.height:
                continue
            top-=gs
            if kind=='heading':
                ix,child=value
                qid=child['id']
                status=self._reading_child_status(qid,self.answers,self._reading_active_child)
                active=status.startswith('active_')
                answered=status.endswith('answered') and not status.endswith('unanswered')
                color=BLUE if active else GREEN if answered else MUTED
                label=f'CÂU {ix+1}/{len(children)}' + ('  [ĐANG CHỌN]' if active else '') + ('  • ĐÃ LÀM' if answered else '  • CHƯA LÀM')
                header=pygame.Rect(7,top-3,right_w-14,self.small.get_linesize()+8)
                if active:pygame.draw.rect(answers_surface,(224,237,255),header,border_radius=5)
                answers_surface.blit(self.small.render(label,True,color),(12,top))
                screen_header=pygame.Rect(right_x+header.x,outer.y+header.y,header.w,header.h).clip(self.group_answer_area)
                if screen_header.width and screen_header.height:
                    self.buttons.append((screen_header,lambda key=qid:self._focus_reading_child(key)))
            elif kind=='prompt':text_lines(answers_surface,value,self.font,12,top,qw)
            else:
                qid,opt,lines=value;h=entry[3]
                selected=self.answers.get(qid)==opt
                rect=pygame.Rect(9,top,right_w-18,h)
                pygame.draw.rect(answers_surface,(220,235,255) if selected else (249,251,254),rect,border_radius=6)
                focused=qid==self._reading_active_child
                pygame.draw.rect(answers_surface,BLUE if selected else (155,190,240) if focused else BORDER,rect,2 if selected or focused else 1,border_radius=6)
                yy=top+7
                for line in lines:
                    answers_surface.blit(self.small.render(line,True,INK),(rect.x+10,yy));yy+=self.small.get_linesize()+4
                screen_rect=pygame.Rect(right_x+rect.x,outer.y+rect.y,rect.w,rect.h)
                clipped=screen_rect.clip(self.group_answer_area)
                if clipped.width and clipped.height:
                    self.buttons.append((clipped,lambda val=opt,key=qid:self._choose_reading_option(key,val)))
        s.blit(answers_surface,(right_x,outer.y))
        # Lightweight scroll indicators; scrolling uses the mouse wheel over each pane.
        for area,offset,limit in ((self.group_passage_area,ps,self._passage_scroll_limit),(self.group_answer_area,gs,self._group_scroll_limit)):
            if limit:
                track=area.height-12;thumb=max(20,int(track*area.height/(area.height+limit)))
                thumb_y=area.y+6+int((track-thumb)*offset/limit)
                pygame.draw.rect(s,(174,191,213),(area.right-5,thumb_y,3,thumb),border_radius=2)

    def _draw_reading(self,s,q):
        """Render all text to an offscreen surface; clip and scroll without overlap."""
        w=self.read_area.width-28;line_h=self.font.get_linesize()+6
        blocks=[];height=10
        passage=q.get('passage') or q.get('reading') or ''
        if passage:
            blocks.append(('heading',('BÀI ĐỌC: '+str(q.get('reading_title',''))) if q.get('reading_group') else 'ĐỌC ĐOẠN VĂN SAU'))
            for paragraph in str(passage).split('\n'):
                blocks.append(('paragraph',paragraph))
        if q.get('type')=='listening_choice':
            blocks.append(('audio',str(q.get('audio',''))))
            _img=str(q.get('image','')).strip()
            if _img and os.path.isfile(_img):blocks.append(('picture',_img))  # optional: no image -> no space
        if q.get('type')=='picture_choice':
            blocks.append(('picture',str(q.get('image',''))))
        blocks.append(('heading',f'CÂU {q.get("reading_index")}/{q.get("reading_total")} TRONG BÀI ĐỌC' if q.get('reading_group') else 'CHỌN ĐÁP ÁN ĐÚNG'))
        blocks.append(('question',str(q.get('prompt',''))))
        items=[]
        for kind,text in blocks:
            if kind=='audio':
                items.append((kind,text,height,None));height+=82;continue
            if kind=='picture':
                items.append((kind,text,height,None));height+=200;continue
            font=self.small if kind=='heading' else self.bold if kind=='question' else self.font
            lines=wrap(font,text,w-20)
            block_height=max(1,len(lines))*(font.get_linesize()+5)+15
            items.append((kind,lines,height,font));height+=block_height
        options=q.get('options',[])
        for i,opt in enumerate(options):
            if q.get('type')=='image_multi_choice':
                items.append(('image_option',(i,str(opt)),height,None));height+=152
            else:
                label=f'{chr(65+i)}. {opt}'
                lines=wrap(self.font,label,w-38)
                card_h=max(50,len(lines)*line_h+22)
                items.append(('option',(i,str(opt),lines),height,None));height+=card_h+9
        height+=16
        self.scroll_limit=max(0,height-self.read_area.height)
        self.scroll=max(0,min(self.scroll,self.scroll_limit))
        surface=pygame.Surface((self.read_area.width,max(self.read_area.height,height)),pygame.SRCALPHA)
        for kind,value,y,font in items:
            if kind=='option':
                i,opt,lines=value;h=max(50,len(lines)*line_h+22)
                selected=self.answers.get(q['id'])==opt
                rect=pygame.Rect(8,y,w,h)
                pygame.draw.rect(surface,(220,235,255) if selected else WHITE,rect,border_radius=8)
                pygame.draw.rect(surface,BLUE if selected else BORDER,rect,2 if selected else 1,border_radius=8)
                yy=y+10
                for line in lines:
                    surface.blit(self.font.render(line,True,INK),(rect.x+14,yy));yy+=line_h
                screen_rect=pygame.Rect(self.read_area.x+rect.x,self.read_area.y+rect.y-self.scroll,rect.w,rect.h)
                clipped=screen_rect.clip(self.read_area)
                if clipped.width and clipped.height:self.buttons.append((clipped,lambda val=opt,qid=q['id']:self.answers.__setitem__(qid,val)))
            elif kind=='image_option':
                i,opt=value;rect=pygame.Rect(8,y,w,141)
                selected=self.answers.get(q['id'])==opt
                pygame.draw.rect(surface,(220,235,255) if selected else WHITE,rect,border_radius=8)
                pygame.draw.rect(surface,BLUE if selected else BORDER,rect,3 if selected else 1,border_radius=8)
                surface.blit(self.small.render(chr(65+i)+'.',True,INK),(rect.x+13,rect.y+12))
                try:
                    if opt not in self._image_cache:
                        img=pygame.image.load(opt).convert_alpha()
                        scale=min((w-75)/max(1,img.get_width()),124/max(1,img.get_height()),1)
                        self._image_cache[opt]=pygame.transform.smoothscale(img,(max(1,int(img.get_width()*scale)),max(1,int(img.get_height()*scale))))
                    img=self._image_cache[opt]
                    surface.blit(img,(rect.x+45,rect.y+max(8,(rect.h-img.get_height())//2)))
                except (pygame.error,OSError,ValueError):
                    surface.blit(self.small.render('Không thể tải ảnh đáp án',True,(176,57,57)),(rect.x+45,rect.y+52))
                screen_rect=pygame.Rect(self.read_area.x+rect.x,self.read_area.y+rect.y-self.scroll,rect.w,rect.h)
                clipped=screen_rect.clip(self.read_area)
                if clipped.width and clipped.height:self.buttons.append((clipped,lambda val=opt,qid=q['id']:self.answers.__setitem__(qid,val)))
            elif kind=='audio':
                self._audio_button(surface,q,12,y)
            elif kind=='picture':
                try:
                    if value not in self._image_cache:
                        img=pygame.image.load(value).convert_alpha()
                        scale=min((w-24)/max(1,img.get_width()),180/max(1,img.get_height()))
                        self._image_cache[value]=pygame.transform.smoothscale(img,(max(1,int(img.get_width()*scale)),max(1,int(img.get_height()*scale))))
                    img=self._image_cache[value]
                    surface.blit(img,(max(10,(w-img.get_width())//2),y+5))
                except (pygame.error,OSError,ValueError):
                    surface.blit(self.small.render('Không thể tải hình minh họa',True,(176,57,57)),(12,y+20))
            else:
                color=MUTED if kind=='heading' else INK
                yy=y
                for line in value:
                    if line:surface.blit(font.render(line,True,color),(12,yy))
                    yy+=font.get_linesize()+5
        visible=pygame.Rect(0,int(self.scroll),self.read_area.width,self.read_area.height)
        s.blit(surface,self.read_area.topleft,visible)
        if self.scroll_limit:
            track=pygame.Rect(self.read_area.right-5,self.read_area.y,4,self.read_area.height)
            pygame.draw.rect(s,(225,232,242),track,border_radius=3)
            thumb_h=max(25,int(track.height*self.read_area.height/height))
            thumb_y=track.y+int((track.height-thumb_h)*self.scroll/self.scroll_limit)
            pygame.draw.rect(s,BLUE,(track.x,thumb_y,4,thumb_h),border_radius=3)

    def _draw_confirm(self,s):
        self._text(s,'Xác nhận nộp bài',80,108,self.big)
        n=len(self.exam['questions']);missing=self._unanswered_indices();done=n-len(missing)
        self._text(s,f'Đã trả lời {done}/{n} câu; còn {len(missing)} câu chưa làm.',80,175)
        self._text(s,'Những câu chưa trả lời được tính là sai.',80,218,self.font,MUTED)
        flagged=self._flagged_indices()
        flagged_groups={self._group_span(i) for i in flagged}
        self._text(s,f'Đánh dấu xem lại: {len(flagged)} câu / {len(flagged_groups)} nhóm.',80,245,self.small,(172,106,32))

        if missing:
            # Compact missing ranges, preserving the distinction between independent
            # questions and child questions in a reading group.
            labels=[];seen=set()
            for i in missing:
                start,end=self._group_span(i)
                if end>start:
                    gid=self.exam['questions'][i].get('reading_group')
                    if gid not in seen:
                        seen.add(gid)
                        children=[j+1 for j in missing if start<=j<=end]
                        labels.append('Bài đọc '+str(start+1)+'-'+str(end+1)+': '+', '.join(map(str,children)))
                else:labels.append('Câu '+str(i+1))
            lines=wrap(self.small,'Chưa làm: '+'; '.join(labels),880)
            for k,line in enumerate(lines[:4]):self._text(s,line,80,290+k*29,self.small,(170,71,48))
            self._button(s,'Đến câu chưa làm',(125,457,345,76),self._go_first_unanswered,small=True)
        else:
            self._button(s,'Tiếp tục xem lại',(125,457,345,76),lambda:setattr(self,'mode','exam'),small=True)
        if flagged:
            self._text(s,'Bạn vẫn có câu đánh dấu cần xem lại trước khi nộp.',80,413,self.small,(172,106,32))
            self._button(s,'Đến câu đánh dấu',(125,555,345,52),self._go_first_flagged,small=True)
        self._button(s,'Xác nhận nộp',(595,457,345,76),self._submit,True)

    def _submit(self):
        if self.mode=='result' or not self.exam:return
        qlist=self.exam['questions']
        correct=sum(self._is_correct(q) for q in qlist)
        self.result={'id':self.exam['id'],'student_id':self.student_id,'grade':self.grade,'lesson':self.lesson,'subject':self.subject,'level':self.level,
                     'total':len(qlist),'correct':correct,'score_percent':round(correct*100/len(qlist),2),
                     'submitted_at':datetime.datetime.now().isoformat(timespec='seconds'),
                     'answers':copy.deepcopy(self.answers),'question_ids':[q['id'] for q in qlist],
                     'question_snapshot':copy.deepcopy(qlist),
                     'ordered_answers':copy.deepcopy(self.order_inputs),
                     'graded_answers':{str(q['id']):bool(self._is_correct(q)) for q in qlist}}
        try:self.bank.save_result(self.result);self.error=None
        except (OSError,ValueError) as exc:self.error='Không lưu được lịch sử: '+str(exc)
        self.mode='result'
        self.review_scroll=0;self.review_detail=None;self._image_cache={};self._audio_path=None;self._audio_error='';self.review_scroll_limit=0
        pygame.key.stop_text_input()

    def _draw_result(self,s):
        """Review every graded answer without changing the submitted result."""
        self._text(s,'KẾT QUẢ KIỂM TRA',65,48,self.big)
        self._text(s,f'{self.result["correct"]}/{self.result["total"]} câu đúng  |  Điểm: {self.result["score_percent"]}%',65,104,self.bold,GREEN)
        if self.error:self._text(s,self.error,65,143,self.small,(180,50,50),width=940)
        area=pygame.Rect(65,186,962,374)
        pygame.draw.rect(s,(245,248,252),area,border_radius=10)
        questions=self.exam['questions']
        heights=[]
        for q in questions:
            prompt=str(q.get('prompt',''))
            heights.append(max(72,len(wrap(self.small,prompt,710))*26+38))
        total=sum(heights)+12
        self.review_scroll_limit=max(0,total-area.height)
        self.review_scroll=min(self.review_scroll,self.review_scroll_limit)
        canvas=pygame.Surface((area.width,max(total,area.height)),pygame.SRCALPHA)
        y=6;targets=[]
        for i,(q,h) in enumerate(zip(questions,heights)):
            correct=self._is_correct(q)
            rect=pygame.Rect(7,y,area.width-28,h-5)
            pygame.draw.rect(canvas,WHITE,rect,border_radius=8)
            pygame.draw.rect(canvas,(44,153,103) if correct else (211,88,83),rect,2,border_radius=8)
            label=f'Câu {i+1}  |  {"Đúng" if correct else "Sai"}'
            self._text(canvas,label,rect.x+12,rect.y+8,self.small,GREEN if correct else (177,65,60))
            self._text(canvas,str(q.get('prompt',''))[:350],rect.x+145,rect.y+8,self.small,INK,width=710)
            targets.append((rect.move(area.x,area.y-int(self.review_scroll)),i))
            y+=h
        s.blit(canvas,area.topleft,pygame.Rect(0,int(self.review_scroll),area.width,area.height))
        for rect,i in targets:
            visible=rect.clip(area)
            if visible.width and visible.height:self.buttons.append((visible,lambda ix=i:self._show_review(ix)))
        if self.review_scroll_limit:
            track=pygame.Rect(area.right-7,area.y,5,area.height)
            pygame.draw.rect(s,BORDER,track,border_radius=3)
            thumb=max(28,int(track.height*area.height/total))
            top=track.y+int((track.height-thumb)*self.review_scroll/self.review_scroll_limit)
            pygame.draw.rect(s,BLUE,(track.x,top,track.width,thumb),border_radius=3)
        self._text(s,'Nhấp vào câu để xem đáp án đã nộp và đáp án đúng.',65,574,self.small,MUTED)
        self._button(s,'Kiểm tra khác',(65,620,305,55),self._another_exam,True,small=True)
        self._button(s,'Thoát',(790,620,237,55),lambda:setattr(self,'running',False),small=True)
        if self.review_detail is not None:
            self.buttons=[]
            self._draw_review_detail(s,questions[self.review_detail])

    def _another_exam(self):
        self.mode='select';self.review_detail=None;self._image_cache={};self._audio_path=None;self._audio_error=''

    def _show_review(self,index):
        self.review_detail=index

    def _draw_review_detail(self,s,q):
        overlay=pygame.Surface(VIRTUAL,pygame.SRCALPHA)
        overlay.fill((18,30,48,180));s.blit(overlay,(0,0))
        panel=pygame.Rect(120,104,860,500)
        pygame.draw.rect(s,WHITE,panel,border_radius=14)
        self._text(s,f'XEM LẠI CÂU {self.review_detail+1}',148,132,self.bold)
        self._text(s,str(q.get('prompt','')),148,190,self.font,INK,width=800)
        answer=self.answers.get(q['id'])
        kind=q.get('type')
        if kind=='order':answer=self.order_inputs.get(q['id'],[])
        expected=q.get('gap_answers',[]) if kind in ('sentence_gaps','conversation_gaps','passage_gaps') else q.get('pairs',[]) if kind=='matching' else q.get('sequence',[]) if kind=='order' else q.get('corrected','') if kind=='error' else q.get('answer','')
        def formatted(value):
            if isinstance(value,dict):return '; '.join(f'{k} → {v}' for k,v in value.items())
            if isinstance(value,list):return ' | '.join(' → '.join(map(str,v)) if isinstance(v,(list,tuple)) else str(v) for v in value)
            return str(value) if value is not None and value!='' else '(Chưa trả lời)'
        self._text(s,'Đáp án đã nộp:',148,326,self.small,MUTED)
        self._text(s,formatted(answer),148,358,self.font,INK,width=785)
        self._text(s,'Đáp án đúng:',148,440,self.small,MUTED)
        self._text(s,formatted(expected),148,470,self.font,GREEN,width=785)
        self._button(s,'Đóng xem lại',(680,542,265,44),lambda:setattr(self,'review_detail',None),small=True)


def run_exam(root,student_id=None):ExamUI(root,student_id).open()
