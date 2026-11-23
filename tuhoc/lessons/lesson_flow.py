"""Lesson topics, selectable vocabulary, mixed quizzes and progress."""
import json, random, time, tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path
from tuhoc.ui.card_motion import animate_card

TOPIC_COLUMNS=['id','title','icon','intro','instructions','content','image','audio']
QUESTION_COLUMNS=['topic_id','id','type','prompt','options','answer','accepted_answers','points']
QUESTION_TYPES=('choice','true_false','fill','order','error','matching')

def topic_file(data):return Path(data)/'content_library'/'topics.json'
def question_file(data):return Path(data)/'content_library'/'questions.json'
def read_json(p):
    if not p.exists():return []
    value=json.loads(p.read_text(encoding='utf-8-sig'))
    return value if isinstance(value,list) else []
def write_json(p,rows):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
def topics(data):return read_json(topic_file(data))
def questions(data):return read_json(question_file(data))

def bundled_topics(exercises):
    # Preserve original sample exercises as lesson topics with one practice question.
    result=[]
    for ex in exercises:
        result.append(dict(id='legacy_'+str(ex['id']),title=ex['title'],icon=ex.get('icon','📘'),
                           intro='Cùng tìm hiểu bài học này nhé!',instructions='Đọc kỹ nội dung trước khi bắt đầu làm bài.',
                           content=ex.get('prompt',''),image=ex.get('image',''),audio=ex.get('audio','')))
    return result

def bundled_questions(exercises):
    return [dict(topic_id='legacy_'+str(ex['id']),id='legacy_question_'+str(ex['id']),
                 type='fill',prompt=ex.get('prompt',''),answer=ex.get('answer',''),
                 accepted_answers=ex.get('accepted_answers') or [ex.get('answer','')],points=1,
                 manual_review=ex.get('manual_review',False)) for ex in exercises]

class LessonFlowMixin:
    def all_topics(self):
        custom=topics(self.data_dir)
        return bundled_topics(self.exercises)+custom
    def all_questions(self):
        return bundled_questions(self.exercises)+questions(self.data_dir)
    def topic_page(self):
        body=self.layout('Chọn chủ đề học')
        rows=self.all_topics()
        self.label(body,'Chọn một ô để xem hình ảnh, kiến thức và hướng dẫn. Bài tập ở trang riêng.',12).pack(anchor='w',pady=(0,14))
        grid=tk.Frame(body,bg=body['bg']);grid.pack(fill='x')
        for col in range(4):grid.columnconfigure(col,weight=1,uniform='topic')
        for i,topic in enumerate(rows):
            done=self.db.lesson_completed(self.student['id'],topic['id'])
            box=tk.Frame(grid,bg='white',width=190,height=177,highlightthickness=1,highlightbackground='#DDE5DB',cursor='hand2')
            box.grid(row=i//4,column=i%4,padx=8,pady=8,sticky='nsew');box.grid_propagate(False)
            ico=tk.Label(box,text=topic.get('icon') or '📘',font=('Segoe UI Emoji',33),bg='#EAF3EC')
            ico.pack(pady=(13,9))
            name=tk.Label(box,text=topic.get('title','Chủ đề'),bg='white',fg='#285D40',font=('Segoe UI',11,'bold'),wraplength=160)
            name.pack(padx=5)
            status=tk.Label(box,text='✓ Đã hoàn thành' if done else 'Chưa hoàn thành',bg='white',fg='#39865B' if done else '#859189',font=('Segoe UI',9))
            status.pack(pady=4)
            for w in (box,ico,name,status):w.bind('<Button-1>',lambda e,t=topic,c=box:animate_card(c, lambda:self.lesson_detail(t)))
    def lesson_detail(self,topic):
        body=self.layout(topic.get('title','Bài học'))
        self.label(body,topic.get('intro',''),14,True).pack(anchor='w',pady=(0,14))
        if topic.get('image'):
            media=self.media_file(topic['image'])
            if media:
                try:
                    from tuhoc.ui.animated_media import display_image
                    w=int(getattr(self,'_display_settings',{}).get('image_width',350))
                    h=int(getattr(self,'_display_settings',{}).get('image_height',240))
                    display_image(body,media,w,h,bg=body['bg'],anchor='w',pady=7)
                except (ImportError,OSError,ValueError,tk.TclError):
                    pass
        if topic.get('audio'):
            self.button(body,'▶ Nghe bài học',lambda:self.audio.play(str(topic['audio']),1.0,1.0)).pack(anchor='w',pady=6)
        self.label(body,'HƯỚNG DẪN',13,True).pack(anchor='w',pady=(15,6))
        self.label(body,topic.get('instructions') or 'Đọc phần nội dung bên dưới rồi làm bài tập.',12).pack(anchor='w')
        self.label(body,'NỘI DUNG HỌC',13,True).pack(anchor='w',pady=(17,5))
        self.label(body,'Để lưu từ vựng, các em bôi đen từ/cụm từ, sau đó bấm “Lưu từ đã chọn”.',10,color='#72847A').pack(anchor='w',pady=(0,5))
        txt=tk.Text(body,width=80,height=max(7,min(18,len(topic.get('content',''))//70+5)),wrap='word',font=('Segoe UI',13),relief='flat',padx=16,pady=14,bg='white',fg='#273E31',exportselection=False)
        txt.pack(fill='x',pady=(0,8));txt.insert('1.0',topic.get('content') or 'Nội dung đang được cập nhật.');txt.configure(state='disabled')
        def scroll_lesson_text(event):
            direction = -1 if getattr(event, 'num', None) == 4 else (1 if getattr(event, 'num', None) == 5 else (-1 if event.delta > 0 else 1))
            txt.yview_scroll(direction * 3, 'units')
            return 'break'
        for sequence in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            txt.bind(sequence, scroll_lesson_text)
        def save_selected():
            try:word=txt.get('sel.first','sel.last').strip()
            except tk.TclError:word=''
            if not word:messagebox.showinfo('Chọn từ','Bôi đen từ trong nội dung trước nhé.');return
            meaning=simpledialog.askstring('Lưu từ vựng',f'Nghĩa hoặc ghi chú của “{word}”:',parent=self)
            if meaning is None:return
            self.db.save_word(self.student['id'],word,meaning.strip() or 'Từ trong bài '+topic['title'])
            messagebox.showinfo('Đã lưu','Từ đã được thêm vào Flashcard.')
        self.button(body,'☆ Lưu từ đã bôi đen',save_selected).pack(anchor='w',pady=7)
        box=tk.Frame(body,bg='#E2F0E2',padx=20,pady=18);box.pack(fill='x',pady=(22,4))
        count=len([q for q in self.all_questions() if q.get('topic_id')==topic['id']])
        self.label(box,'BÀI TẬP CỦA BÀI HỌC',17,True).pack(anchor='w')
        self.label(box,f'{count} câu trong kho · Trộn các dạng câu hỏi · Tự chấm kết quả',11).pack(anchor='w',pady=5)
        self.button(box,'Bắt đầu làm bài →',lambda:self.start_lesson_quiz(topic)).pack(anchor='w',pady=6)
        self.button(body,'← Quay về danh sách chủ đề',self.topic_page).pack(anchor='w',pady=10)
    def start_lesson_quiz(self,topic):
        pool=[q for q in self.all_questions() if q.get('topic_id')==topic['id']]
        if not pool:messagebox.showinfo('Chưa có bài tập','Hãy thêm câu hỏi trong Quản lý nội dung (JSON).');return
        random.shuffle(pool)
        self.quiz_topic=topic;self.quiz_items=pool[:min(10,len(pool))];self.quiz_answers=[];self.quiz_start=time.monotonic()
        self.quiz_question(0)
    def quiz_question(self,i):
        if i>=len(self.quiz_items):return self.finish_lesson_quiz()
        q=self.quiz_items[i];typ=q.get('type','fill');body=self.layout(f"{self.quiz_topic['title']} · Bài tập {i+1}/{len(self.quiz_items)}")
        self.label(body,f"Câu {i+1} / {len(self.quiz_items)}  ·  {typ}",12,color='#667E6D').pack(anchor='w',pady=8)
        self.label(body,q.get('prompt',''),16,True).pack(anchor='w',pady=(4,18))
        opts=q.get('options',[])
        if isinstance(opts,str):opts=[s.strip() for s in opts.split('|') if s.strip()]
        response=tk.StringVar(master=body, value='__NO_SELECTION__')
        self._quiz_response_var=response
        if typ in ('choice','true_false','matching') and opts:
            for option in opts:
                tk.Radiobutton(body,text=option,variable=response,value=option,bg=body['bg'],font=('Segoe UI',12),anchor='w').pack(anchor='w',pady=7)
        else:
            if typ=='order':self.label(body,'Nhập các từ theo thứ tự đúng, cách nhau bằng dấu cách.',11).pack(anchor='w')
            entry=tk.Entry(body,textvariable=response,font=('Segoe UI',14),width=55);entry.pack(anchor='w',pady=10)
        def submit():
            value=response.get().strip()
            if value=='__NO_SELECTION__':value=''
            if value=='' or not value:messagebox.showwarning('Thiếu đáp án','Hãy trả lời trước khi tiếp tục.');return
            accepted=q.get('accepted_answers') or [q.get('answer','')]
            if isinstance(accepted,str):accepted=[s.strip() for s in accepted.split('|')]
            normalize=lambda s:' '.join(str(s).casefold().split())
            correct=None if q.get('manual_review') else int(normalize(value) in [normalize(x) for x in accepted])
            self.quiz_answers.append((q,value,correct))
            self.quiz_question(i+1)
        self.button(body,'Xác nhận và tiếp tục →',submit).pack(anchor='w',pady=20)
    def finish_lesson_quiz(self):
        rows=self.quiz_answers
        good=sum(c==1 for _,_,c in rows)
        graded=sum(c is not None for _,_,c in rows)
        completed=all(c is not None for _,_,c in rows) and len(rows)==len(self.quiz_items)
        sid=self.student['id'];topic=self.quiz_topic
        for q,answer,correct in rows:
            self.db.record(sid,{'id':q['id'],'type':q.get('type','fill'),'version':'1.3'},correct,(time.monotonic()-self.quiz_start)/len(rows),answer)
        self.db.save_lesson_progress(sid,topic['id'],good,len(rows),completed)
        from tuhoc.exercises.pygame_review_panel import show_review
        body=self.layout('Kết quả bài tập')
        payload=dict(stars=0,correct=good,total=len(rows),percent=good/max(1,len(rows)),duration=f'{int(time.monotonic()-self.quiz_start)} giây',message='Có câu chờ giáo viên đánh giá.' if not completed else 'Đã lưu tiến độ học tập.',unlock='',rows=[dict(question=q,answer=answer,correct=c) for q,answer,c in rows])
        show_review(body,payload,lambda action:self.lesson_detail(topic) if action=='back' else self.quiz_question(0))
    def lesson_progress_page(self):
        body=self.layout('Tiến độ học tập')
        progress=self.db.lesson_progress(self.student['id']);byid={r['topic_id']:r for r in progress}
        done=sum(bool(byid.get(t['id']) and byid[t['id']]['completed']) for t in self.all_topics())
        self.label(body,f'Đã học {done}/{len(self.all_topics())} chủ đề',17,True).pack(anchor='w',pady=10)
        for topic in self.all_topics():
            p=byid.get(topic['id']);mark='✓' if p and p['completed'] else '○'
            info=f"{p['correct']}/{p['total']} câu đúng" if p else 'Chưa làm bài'
            self.label(body,f"{mark}  {topic['title']}  —  {info}",12).pack(anchor='w',pady=8)
        self.button(body,'Xem thống kê câu trả lời',self.statistics).pack(anchor='w',pady=16)
