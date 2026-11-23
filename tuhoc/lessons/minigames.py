"""Tkinter adaptations of Buzz Phonics React mini-games (offline, no dependencies)."""
import random
import time
import tkinter as tk
from tkinter import ttk
from tuhoc.storage.content_manager import read_games

PAIRS = [('h','hat'),('f','frog'),('g','guitar'),('c','cat'),('t','tap'),('s','sun'),('p','penguin'),('u','umbrella'),('b','bin'),('e','egg'),('r','rat'),('a','ant')]
WORDS = ['cat','map','bus','duck','pen','sun','pig','bat','socks','crab']
READ_WORDS = ['chair','book','shoe','sweet','witch','fish','cow','shell','train','watch']
READ_MEANINGS = {'chair':'cái ghế','book':'quyển sách','shoe':'chiếc giày','sweet':'kẹo ngọt','witch':'phù thủy','fish':'con cá','cow':'con bò','shell':'vỏ sò','train':'tàu hỏa','watch':'đồng hồ đeo tay'}

class MiniGamesMixin:
    def _game_rows(self, kind):
        try:return [r for r in read_games(self.data_dir) if r.get('game')==kind]
        except (OSError,ValueError):return []

    def _game_level(self,rows):
        # If too few custom words exist at chosen level, include all custom words.
        level=int(getattr(self,'game_level',tk.IntVar(value=1)).get())
        selected=[r for r in rows if int(r.get('level',1))<=level]
        return selected or rows

    def _asset_for_game(self,word):
        for r in self._game_rows('read')+self._game_rows('spell'):
            if r.get('word','').lower()==word.lower():return r
        return {}

    def _game_media(self,body,record):
        # Tk supports PNG/GIF without Pillow; WAV is played using Windows built-in audio.
        if record.get('image'):
            path=self.media_file(record['image'])
            if path:
                try:
                    im=tk.PhotoImage(file=str(path))
                    ratio=max(1,(max(im.width(),im.height())+210)//211)
                    if ratio>1:im=im.subsample(ratio)
                    label=tk.Label(body,image=im,bg=body.cget('bg'))
                    label.image=im;label.pack(pady=8)
                except tk.TclError:pass
        if record.get('audio'):
            path=self.media_file(record['audio'])
            if path:self.action_button(body,'🔊 Nghe phát âm',lambda p=str(path):self.audio.play(p,1.0,1.0)).pack(pady=4)

    def games_page(self):
        if getattr(self,'lang','en')=='vi':
            return self.topic_page()  # Bài luyện Tiếng Việt lấy từ chương trình Tiếng Việt; không dùng kho trò chơi tiếng Anh.
        body=self.layout('Trò chơi luyện tập')
        self.label(body, 'Lấy cảm hứng từ Buzz Phonics · Bản chuyển thể cho ứng dụng desktop',12,color='#607464').pack(anchor='w',pady=(0,16))
        self.label(body, f'⭐ Điểm thưởng của em: {self.db.points(self.student["id"])}',17,True).pack(anchor='w',pady=(0,18))
        settings=tk.Frame(body,bg=body.cget('bg'));settings.pack(anchor='w',pady=6)
        self.label(settings,'Cấp độ:',12,True).pack(side='left',padx=(0,12))
        if not hasattr(self,'game_level'):self.game_level=tk.IntVar(value=1)
        for level,title in ((1,'Dễ'),(2,'Vừa'),(3,'Khó')):
            tk.Radiobutton(settings,text=title,variable=self.game_level,value=level,bg=body.cget('bg'),font=('Segoe UI',11),cursor='hand2').pack(side='left',padx=6)
        for title,fn in [('🃏  Ghép cặp chữ cái và từ',self.match_game),('🔤  Xếp chữ đánh vần',self.spelling_game),('📖  Đọc từ – Chọn đáp án',self.read_game)]:
            self.button(body,title,fn).pack(anchor='w',fill='x',pady=8)
        self.label(body,'Mỗi lượt hoàn thành trò chơi nhận 1 điểm. Điểm lưu riêng theo hồ sơ.',11,color='#607464').pack(anchor='w',pady=15)

    def _game_finish(self,name,seconds,replay):
        self.db.add_points(self.student['id'],1)
        body=self.layout('Hoàn thành trò chơi! 🎉')
        heading=self.label(body,'Giỏi lắm! +1 ⭐',26,True);heading.pack(pady=40)
        self.label(body,f'{name} · {int(seconds)} giây',14).pack(pady=7)
        self.label(body,f'Tổng điểm: {self.db.points(self.student["id"])} ⭐',16,True).pack(pady=14)
        self.action_button(body,'Chơi lại',replay).pack(pady=9)
        self.button(body,'Danh sách trò chơi',self.games_page).pack(pady=7)
        # Small celebratory text animation without external packages.
        symbols=['🎉  TUYỆT VỜI!  🎉','⭐  TUYỆT VỜI!  ⭐','🎊  TUYỆT VỜI!  🎊']
        self._animate_label(heading,symbols,0)

    def _animate_label(self,widget,items,idx):
        try:
            if not widget.winfo_exists() or idx >= 8: return
            widget.config(text=items[idx % len(items)])
            self.after(220,lambda:self._animate_label(widget,items,idx+1))
        except tk.TclError:
            return  # User navigated away before the animation ended.

    def match_game(self):
        body=self.layout('🃏 Ghép cặp chữ cái – từ vựng')
        start=time.monotonic()
        custom=self._game_level(self._game_rows('pair'))
        pair_pool=[(str(r.get('key','')).lower(),str(r.get('word','')).lower()) for r in custom if r.get('key')]
        pair_pool=pair_pool or PAIRS
        # Keep each matching key unique; prevent ambiguous duplicates.
        unique={}
        for key,word in pair_pool:unique.setdefault(key,word)
        available=list(unique.items())
        count=min(6,len(available))
        if count<2:
            self.label(body,'Cần ít nhất 2 cặp có chữ cái khác nhau.',13).pack();return
        selected=random.sample(available,count)
        cards=[(i,0,a) for i,(a,b) in enumerate(selected)]+[(i,1,b) for i,(a,b) in enumerate(selected)]
        random.shuffle(cards)
        self.label(body,'Chọn một chữ cái và một từ tiếng Anh bắt đầu bằng chữ đó.',12).pack(pady=(0,12))
        status=self.label(body,f'Đã ghép: 0/{count}',13,True);status.pack(pady=10)
        board=tk.Frame(body,bg=body.cget('bg'));board.pack(pady=10)
        buttons=[];opened=[];matched=set();lock=[False]
        def flip(index):
            if lock[0] or index in opened or cards[index][0] in matched:return
            opened.append(index)
            buttons[index].config(text=cards[index][2],bg='#F4CE57',fg='#285D40')
            if len(opened)!=2:return
            a,b=opened
            lock[0]=True
            def resolve():
                if not board.winfo_exists():return
                if cards[a][0]==cards[b][0] and cards[a][1]!=cards[b][1]:
                    matched.add(cards[a][0]);status.config(text=f'✅ Đã ghép: {len(matched)}/{count}')
                    for x in (a,b): buttons[x].config(bg='#B7E5C4',fg='#285D40',state='disabled')
                else:
                    for x in (a,b):buttons[x].config(text='?',bg='#39865B',fg='white')
                    status.config(text=f'Thử lại nhé! Đã ghép: {len(matched)}/{count}')
                opened.clear();lock[0]=False
                if len(matched)==count:self._game_finish('Ghép cặp',time.monotonic()-start,self.match_game)
            self.after(750,resolve)
        for i in range(len(cards)):
            b=tk.Button(board,text='?',width=13,height=3,bg='#39865B',fg='white',font=('Segoe UI',14,'bold'),cursor='hand2',command=lambda n=i:flip(n))
            b.grid(row=i//4,column=i%4,padx=7,pady=7);buttons.append(b)
        self.button(body,'Xáo thẻ và chơi lại',self.match_game).pack(pady=12)

    def spelling_game(self):
        custom=self._game_level(self._game_rows('spell'))
        pool=[str(r.get('word','')).lower() for r in custom if str(r.get('word','')).isalpha()]
        pool=list(dict.fromkeys(pool)) or WORDS
        words=random.sample(pool,min(len(pool),3+int(getattr(self,'game_level',tk.IntVar(value=1)).get())-1));start=time.monotonic()
        def round_page(index=0):
            if index>=len(words):self._game_finish('Đánh vần',time.monotonic()-start,self.spelling_game);return
            word=words[index];body=self.layout('🔤 Trò chơi đánh vần')
            self.label(body,f'Từ {index+1}/{len(words)}',12,True).pack(anchor='w')
            self.label(body,'Chọn lần lượt các chữ cái để tạo thành từ tiếng Anh:',13).pack(pady=18)
            self.label(body,f'Gợi ý: từ có {len(word)} chữ cái',13).pack(pady=5)
            self._game_media(body,self._asset_for_game(word))
            target=self.label(body,'_ '*len(word),28,True);target.pack(pady=18)
            notice=self.label(body,'',12);notice.pack(pady=8)
            pos=[0];options=list(dict.fromkeys(word))
            alphabet=[x for x in 'abcdefghijklmnopqrstuvwxyz' if x not in options]
            options+=random.sample(alphabet,min(6-len(options),len(alphabet)));random.shuffle(options)
            row=tk.Frame(body,bg=body.cget('bg'));row.pack(pady=15)
            next_btn=self.button(body,'Từ tiếp theo →',lambda:round_page(index+1))
            def choose(letter):
                if pos[0]>=len(word):return
                if letter==word[pos[0]]:
                    pos[0]+=1;target.config(text=word[:pos[0]].upper()+' _'*(len(word)-pos[0]))
                    notice.config(text='✅ Chính xác!',fg='#39865B')
                    if pos[0]==len(word):
                        notice.config(text=f'🎉 Hoàn thành từ {word.upper()}!');next_btn.pack(pady=15)
                else:notice.config(text='❌ Chưa đúng, thử chữ khác nhé!',fg='#B04C46')
            for i,letter in enumerate(options):
                tk.Button(row,text=letter.upper(),command=lambda c=letter:choose(c),width=4,height=2,font=('Segoe UI',16,'bold'),bg='#E2F0E2',fg='#285D40',cursor='hand2').grid(row=i//6,column=i%6,padx=5,pady=5)
            self.action_button(body,'↻ Làm lại từ này',lambda:round_page(index)).pack(pady=10)
        round_page()

    def read_game(self):
        custom=self._game_level(self._game_rows('read'))
        meanings={str(r['word']).lower():str(r.get('meaning','')) for r in custom if r.get('word') and r.get('meaning')}
        meanings=meanings if len(meanings)>=3 else READ_MEANINGS
        word_pool=list(meanings)
        words=random.sample(word_pool,min(len(word_pool),5));start=time.monotonic();correct=[0]
        def question(index=0):
            if index>=len(words):
                self.db.record(self.student['id'],{'id':'game_read','type':'game_read','version':'1.1'},int(correct[0]==len(words)),time.monotonic()-start,f'{correct[0]}/{len(words)}')
                self._game_finish(f'Đọc từ: {correct[0]}/{len(words)} câu đúng',time.monotonic()-start,self.read_game);return
            word=words[index];body=self.layout('📖 Đọc từ – Chọn đáp án')
            self.label(body,f'Câu {index+1}/{len(words)}',12,True).pack(anchor='w')
            self.label(body,'Đọc gợi ý tiếng Việt và chọn từ tiếng Anh đúng:',13).pack(pady=15)
            self.label(body,meanings[word].upper(),25,True).pack(pady=20)
            self._game_media(body,self._asset_for_game(word))
            options=[word]+random.sample([w for w in word_pool if w!=word],min(2,len(word_pool)-1));random.shuffle(options)
            hint=self.label(body,'',13,True);hint.pack(pady=10)
            buttons=[]
            def select(choice):
                for btn in buttons:btn.config(state='disabled')
                if choice==word:correct[0]+=1;hint.config(text='✅ Chính xác!',fg='#39865B')
                else:hint.config(text=f'❌ Đáp án đúng: {word}',fg='#B04C46')
                self.after(650,lambda:question(index+1) if body.winfo_exists() else None)
            for option in options:
                btn=self.button(body,option.upper(),lambda x=option:select(x));btn.pack(fill='x',pady=7);buttons.append(btn)
            self.label(body,'Có thể thêm hình và âm thanh cho mỗi từ ở phần Quản lý nội dung.',10,color='#607464').pack(pady=18)
        question()
