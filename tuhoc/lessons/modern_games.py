"""Standalone eight educational games: same engines, independent subject content."""
from tuhoc.paths import PROJECT_ROOT
import json, random, tkinter as tk
from pathlib import Path
from tkinter import messagebox

ROOT=PROJECT_ROOT
NAVY='#293951'; GREEN='#237e64'; PALE='#edf7f3'; MUTED='#69788c'; WHITE='#ffffff'; GOLD='#ffdb85'
TYPES={'picture','listen','difference','spell','memory','treasure','maze','sort'}

_GAME_CACHE = {}

def load_games(lang):
    f=ROOT/('games_vi.json' if lang=='vi' else 'games_en.json')
    try:
        signature=(f.stat().st_mtime_ns, f.stat().st_size)
        cached=_GAME_CACHE.get(str(f))
        if cached and cached[0]==signature:
            return cached[1]
        data=json.loads(f.read_text(encoding='utf-8'))
        if not isinstance(data.get('levels'),list):raise ValueError('Thiếu danh sách levels')
        _GAME_CACHE[str(f)]=(signature,data)
        return data
    except (ValueError,OSError) as e:
        messagebox.showerror('Trò chơi',str(e));return {'levels':[]}

class ModernGamesMixin:
    def _head(self,body,title,subtitle=''):
        tk.Label(body,text=title,font=('Segoe UI',20,'bold'),bg=body['bg'],fg=NAVY).pack(anchor='w',pady=(12,5))
        if subtitle:tk.Label(body,text=subtitle,font=('Segoe UI',11),bg=body['bg'],fg=MUTED,wraplength=800,justify='left').pack(anchor='w',pady=(0,14))
    def _btn(self,parent,text,callback,bg=WHITE):
        return tk.Button(parent,text=text,command=callback,bg=bg,fg=NAVY,activebackground=GOLD,relief='flat',bd=0,
                         padx=16,pady=13,font=('Segoe UI',12,'bold'),cursor='hand2',wraplength=600)
    def _panel(self,parent):
        f=tk.Frame(parent,bg=WHITE,padx=16,pady=14,highlightthickness=1,highlightbackground='#d9e5e3');f.pack(fill='x',pady=7);return f
    def _image(self,parent,name,width=330):
        root=(ROOT/'games_media').resolve();path=(root/str(name)).resolve()
        if not name or not path.is_relative_to(root) or not path.is_file():return None
        try:
            im=tk.PhotoImage(file=str(path));factor=max(1,(im.width()+width-1)//width)
            if factor>1:im=im.subsample(factor)
            l=tk.Label(parent,image=im,bg=parent['bg']);l.image=im;l.pack(pady=10);return l
        except tk.TclError:return None
    def games_page(self):
        lang=getattr(self,'lang','en');data=load_games(lang)
        body=self.layout('🎮  Vương quốc trò chơi')
        self._head(body,'🇻🇳  Trò chơi Tiếng Việt' if lang=='vi' else '🇬🇧  English games',
                   'Mỗi môn có nội dung riêng. Level quyết định những trò chơi được mở.')
        grid=tk.Frame(body,bg=body['bg']);grid.pack(fill='x')
        for n in range(1,11):
            rec=next((x for x in data['levels'] if x.get('level')==n),{})
            count=sum(1 for g in rec.get('games',[]) if g.get('enabled',True) and g.get('items') and g.get('type') in TYPES)
            f=tk.Frame(grid,bg=WHITE,padx=7,pady=9,highlightbackground='#deece7',highlightthickness=1)
            f.grid(row=(n-1)//5,column=(n-1)%5,padx=6,pady=7,sticky='nsew');grid.grid_columnconfigure((n-1)%5,weight=1)
            b=self._btn(f,f'{"🌟" if count else "🔒"}  Level {n}\n{count} trò chơi',lambda level=n:self.game_select_page(level),PALE if count else '#eff1f2')
            b.config(state='normal' if count else 'disabled',fg=NAVY if count else MUTED)
            b.pack(fill='both',expand=True)
        self.label(body,'Nội dung trò chơi được lưu trong games_vi.json / games_en.json cạnh main.py.',10,color=MUTED).pack(anchor='w',pady=12)
    def game_select_page(self,level):
        data=load_games(getattr(self,'lang','en'))
        rec=next((x for x in data['levels'] if x.get('level')==level),{})
        body=self.layout(f'🎲  Level {level}')
        self._btn(body,'← Bản đồ Level',self.games_page).pack(anchor='w')
        self._head(body,f'Level {level} · Chọn trò chơi','Mỗi trò dùng ngân hàng nội dung riêng của môn đang chọn.')
        for game in rec.get('games',[]):
            if not game.get('enabled',True) or not game.get('items') or game.get('type') not in TYPES:continue
            f=self._panel(body)
            self._btn(f,f'{game.get("title",game["type"])}   ·   {len(game["items"])} thử thách   →',
                      lambda g=game:self.game_play_page(level,g),PALE).pack(fill='x')
    def game_play_page(self,level,game):
        tasks=list(game['items']);random.shuffle(tasks);score=[0]
        def finish():
            body=self.layout('🎉 Hoàn thành!');self._head(body,f'🏆  {score[0]}/{len(tasks)} thử thách', 'Bé đã hoàn thành lượt chơi!')
            try:
                self.db.add_points(self.student['id'],max(1,score[0]))
                self.label(body,f'⭐ Tổng sao: {self.db.points(self.student["id"])}',16,True).pack(pady=12)
            except (AttributeError,KeyError,TypeError):pass
            self._btn(body,'↻ Chơi lại',lambda:self.game_play_page(level,game),PALE).pack(fill='x',pady=5)
            self._btn(body,'← Chọn trò',lambda:self.game_select_page(level)).pack(fill='x',pady=5)
        def round_at(i):
            if i>=len(tasks):return finish()
            task=tasks[i];typ=game['type'];body=self.layout(game.get('title','🎮 Trò chơi'))
            self._btn(body,'← Chọn trò',lambda:self.game_select_page(level)).pack(anchor='w')
            self._head(body,f'{game.get("title","Trò chơi")}  ·  {i+1}/{len(tasks)}',task.get('prompt','Hãy hoàn thành thử thách.'))
            bar=tk.Frame(body,height=9,bg='#deebe5');bar.pack(fill='x',pady=(0,12));bar.pack_propagate(False)
            tk.Frame(bar,bg=GREEN).place(relwidth=i/len(tasks),relheight=1)
            f=self._panel(body);status=tk.Label(f,text='',font=('Segoe UI',12,'bold'),bg=WHITE,fg=GREEN)
            finished=[False];controls=[]
            next_btn=self._btn(f,'Tiếp tục →' if i<len(tasks)-1 else 'Xem kết quả 🎉',lambda:round_at(i+1),GOLD)
            def complete(ok,answer=''):
                if finished[0]:return
                finished[0]=True
                if ok:score[0]+=1
                status.config(text='🎉 Chính xác!' if ok else '💡 Đáp án đúng: '+str(answer),fg=GREEN if ok else '#b64f4a')
                for c in controls:
                    try:c.configure(state='disabled')
                    except tk.TclError:pass
                next_btn.pack(fill='x',pady=9)
            def option_buttons(options,answer):
                opts=list(options);random.shuffle(opts)
                for opt in opts:
                    b=self._btn(f,str(opt),lambda a=opt:complete(str(a).casefold()==str(answer).casefold(),answer),PALE)
                    b.pack(fill='x',pady=5);controls.append(b)
            if typ in ('picture','treasure','maze','listen'):
                if typ=='picture' and task.get('picture_options'):
                    pictures=list(task['picture_options']);random.shuffle(pictures)
                    picgrid=tk.Frame(f,bg=WHITE);picgrid.pack()
                    for j,pic in enumerate(pictures):
                        tile=tk.Frame(picgrid,bg=PALE,padx=8,pady=8)
                        tile.grid(row=j//2,column=j%2,padx=7,pady=7)
                        b=self._btn(tile,str(pic['label']),lambda p=pic:complete(str(p['label'])==str(task.get('answer','')),task.get('answer','')),PALE)
                        imgpath=(ROOT/'games_media'/pic.get('image','')).resolve();imgroot=(ROOT/'games_media').resolve()
                        if imgpath.is_relative_to(imgroot) and imgpath.is_file():
                            try:
                                image=tk.PhotoImage(file=str(imgpath));factor=max(1,(image.width()+175)//176)
                                if factor>1:image=image.subsample(factor)
                                b.config(image=image,compound='top',wraplength=170)
                                b.image=image
                            except tk.TclError:pass
                        b.pack();controls.append(b)
                else:self._image(f,task.get('image',''))
                if typ=='listen':
                    # Offline Windows TTS (SAPI), no network or optional libraries.
                    speech=task.get('speech',task.get('answer',''))
                    def speak():
                        try:
                            import subprocess
                            s=str(speech).replace("'","''")
                            command="Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak('"+s+"')"
                            subprocess.Popen(['powershell','-NoProfile','-Command',command],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                        except Exception:messagebox.showinfo('Âm thanh','Máy chưa hỗ trợ đọc tự động.')
                    self._btn(f,'🔊 Nghe lại',speak,GOLD).pack(pady=10)
                if typ=='treasure':tk.Label(f,text='🔒 → 🗝️ → 🎁',font=('Segoe UI',28),bg=WHITE).pack(pady=8)
                if typ=='maze':tk.Label(f,text='🚩  ───  ?  ───  🏁',font=('Segoe UI',22),bg=WHITE).pack(pady=8)
                if typ!='picture' or not task.get('picture_options'):option_buttons(task.get('options',[]),task.get('answer',''))
            elif typ=='spell':
                self._image(f,task.get('image',''));self.label(f,'Gợi ý: '+task.get('hint',''),12).pack(pady=5)
                word=task.get('word','');chars=list(word);random.shuffle(chars);entered=[]
                display=tk.Label(f,text='＿ '*len(chars),font=('Segoe UI',22,'bold'),fg=NAVY,bg=WHITE);display.pack(pady=12)
                tiles=tk.Frame(f,bg=WHITE);tiles.pack()
                def tap(pos,btn):
                    entered.append(chars[pos]);btn.config(state='disabled')
                    display.config(text=''.join(entered)+'  '+'＿'*(len(chars)-len(entered)))
                    if len(entered)==len(chars):complete(''.join(entered).casefold()==word.casefold(),word)
                for j,ch in enumerate(chars):
                    b=self._btn(tiles,ch or '␣',None,PALE)
                    b.config(command=lambda k=j,button=b:tap(k,button));b.grid(row=j//9,column=j%9,padx=4,pady=4);controls.append(b)
                self._btn(f,'↻ Làm lại lượt này',lambda:round_at(i)).pack(pady=5)
            elif typ=='memory':
                # A consistent card size for every face; the source image's aspect
                # ratio never changes the position of surrounding cards.
                all_pairs=task.get('pairs',[])
                if not all_pairs:
                    self.label(f,'Chưa có cặp thẻ nào trong dữ liệu.',12).pack()
                    status.pack(pady=9)
                    return
                CARD_W,CARD_H=142,116
                IMG_W,IMG_H=126,86
                root=(ROOT/'games_media').resolve()
                settings=tk.Frame(f,bg=WHITE)
                settings.pack(fill='x',pady=(0,8))
                tk.Label(settings,text='Số thẻ:',bg=WHITE,fg=NAVY,font=('Segoe UI',11,'bold')).pack(side='left',padx=(0,10))
                # Card count (not an 8x8 matrix): every pair has exactly two cards.
                size_values=(8,12,16,32,64)
                available=len(all_pairs)*2
                initial=int(task.get('card_count',min(8,available)))
                if initial not in size_values:initial=next((v for v in reversed(size_values) if v<=available),available)
                selected_size=tk.StringVar(value=str(initial))
                selector=tk.OptionMenu(settings,selected_size,*[str(v) for v in size_values])
                selector.config(bg=PALE,fg=NAVY,relief='flat',font=('Segoe UI',11),width=7)
                selector.pack(side='left')
                info=tk.Label(settings,text='',bg=WHITE,fg=MUTED,font=('Segoe UI',10))
                info.pack(side='left',padx=10)
                board=tk.Frame(f,bg=WHITE);board.pack(fill='x',pady=8)
                held=[]; board_state={'busy':False,'count':0}
                def normalized(card):
                    return card if isinstance(card,dict) else {'type':'text','content':str(card)}
                def face_image(card):
                    if card.get('type')!='image':return None
                    name=str(card.get('content',''))
                    path=(root/name).resolve()
                    if not name or not path.is_relative_to(root) or not path.is_file():return None
                    try:
                        from PIL import Image,ImageTk
                        source=Image.open(path).convert('RGBA')
                        source.thumbnail((IMG_W,IMG_H),Image.Resampling.LANCZOS)
                        plate=Image.new('RGBA',(CARD_W,CARD_H),'#fffaf1')
                        plate.alpha_composite(source,((CARD_W-source.width)//2,(CARD_H-source.height)//2))
                        return ImageTk.PhotoImage(plate)
                    except (ImportError,OSError,ValueError,AttributeError):
                        try:
                            source=tk.PhotoImage(file=str(path))
                            factor=max(1,(source.width()+IMG_W-1)//IMG_W,(source.height()+IMG_H-1)//IMG_H)
                            if factor>1:source=source.subsample(factor)
                            plate=tk.PhotoImage(width=CARD_W,height=CARD_H)
                            plate.put('#fffaf1',to=(0,0,CARD_W,CARD_H))
                            plate.tk.call(str(plate),'copy',str(source),'-to',(CARD_W-source.width())//2,(CARD_H-source.height())//2)
                            return plate
                        except tk.TclError:return None
                back=tk.PhotoImage(width=CARD_W,height=CARD_H)
                back.put('#e3f3ee',to=(0,0,CARD_W,CARD_H))
                # Keep every Tk PhotoImage alive across redraws.
                held.append(back)
                def new_round():
                    try:requested=int(selected_size.get())
                    except ValueError:requested=8
                    if requested>available:
                        info.config(text=f'Cần {requested//2} cặp riêng; hiện có {len(all_pairs)} cặp.')
                        return
                    info.config(text=f'{requested//2} cặp • {requested} thẻ')
                    for widget in board.winfo_children():widget.destroy()
                    held[:]=[back]
                    chosen=random.sample(all_pairs,requested//2)
                    deck=[]
                    for j,pair in enumerate(chosen):
                        for side in ('left','right'):deck.append((j,normalized(pair.get(side,''))))
                    random.shuffle(deck)
                    buttons=[];pictures=[];opened=[];matched=set();busy=[False]
                    # Four columns on a compact laptop, six for medium boards,
                    # eight on wide windows; the outer layout scrolls vertically.
                    try:width=self.winfo_width()
                    except tk.TclError:width=850
                    columns=max(2,min(8,(max(width-120,470))//(CARD_W+16)))
                    if requested<=8:columns=min(columns,4)
                    for c in range(columns):board.grid_columnconfigure(c,weight=1)
                    def show(index,visible):
                        btn=buttons[index]
                        if not visible:
                            btn.config(image=back,text='?',compound='center',bg=PALE)
                            return
                        card=deck[index][1]
                        if card.get('type')=='image':
                            pic=pictures[index]
                            btn.config(image=pic or back,text='' if pic else 'Thiếu ảnh',compound='center',bg='#fffaf1')
                        else:
                            btn.config(image=back,text=str(card.get('content','')),compound='center',bg='#fffaf1')
                    def flip(index):
                        if finished[0] or busy[0] or index in matched or index in opened:return
                        opened.append(index);show(index,True)
                        if len(opened)==2:
                            first,second=opened
                            if deck[first][0]==deck[second][0]:
                                matched.update((first,second))
                                for k in (first,second):buttons[k].config(bg='#c9f3d7',state='disabled')
                                opened.clear()
                                if len(matched)==len(deck):complete(True)
                            else:
                                busy[0]=True
                                def hide():
                                    if not board.winfo_exists():return
                                    for k in (first,second):show(k,False)
                                    opened.clear();busy[0]=False
                                board.after(1000,hide)
                    for j,(_pid,card) in enumerate(deck):
                        picture=face_image(card)
                        pictures.append(picture)
                        if picture:held.append(picture)
                        tile=tk.Frame(board,width=CARD_W,height=CARD_H,bg=PALE)
                        tile.grid(row=j//columns,column=j%columns,padx=5,pady=5)
                        tile.grid_propagate(False)
                        button=tk.Button(tile,image=back,text='?',compound='center',command=lambda k=j:flip(k),
                            font=('Segoe UI',14,'bold'),fg=NAVY,bg=PALE,activebackground=GOLD,
                            relief='flat',bd=0,cursor='hand2',wraplength=CARD_W-14)
                        button.pack(fill='both',expand=True)
                        buttons.append(button);controls.append(button)
                self._btn(settings,'↻ Tạo bàn chơi',new_round,PALE).pack(side='left',padx=8)
                new_round()
            elif typ=='sort':
                cards=task.get('cards',[]);cats=task.get('categories',[]);random.shuffle(cards);index=[0]
                prompt=tk.Label(f,text='',font=('Segoe UI',19,'bold'),bg=WHITE,fg=NAVY);prompt.pack(pady=13)
                buttons=[]
                def render():
                    if index[0]>=len(cards):complete(True);return
                    prompt.config(text=cards[index[0]]['text'])
                def choose(cat):
                    if finished[0]:return
                    if cat==cards[index[0]]['category']:
                        index[0]+=1;render()
                    else:status.config(text='Thử lại nhé!',fg='#b64f4a')
                for cat in cats:
                    b=self._btn(f,'🧺 '+cat,lambda c=cat:choose(c),PALE);b.pack(fill='x',pady=5);controls.append(b)
                render()
            elif typ=='difference':
                a=self._image(f,task.get('image_a',''),380)
                # Click hotspots on second picture; image files are deliberately editable.
                root=(ROOT/'games_media').resolve();p=(root/task.get('image_b','')).resolve()
                if p.is_relative_to(root) and p.exists():
                    im=tk.PhotoImage(file=str(p));scale=max(1,(im.width()+379)//380)
                    if scale>1:im=im.subsample(scale)
                    canvas=tk.Canvas(f,width=im.width(),height=im.height(),highlightthickness=0,bg=WHITE,cursor='crosshair')
                    canvas.image=im;canvas.create_image(0,0,image=im,anchor='nw');canvas.pack(pady=7)
                    found=set();hotspots=task.get('hotspots',[]);radius=int(task.get('radius',30))
                    def click(event):
                        if finished[0]:return
                        for j,pt in enumerate(hotspots):
                            x,y=pt[0]/scale,pt[1]/scale
                            if j not in found and (event.x-x)**2+(event.y-y)**2 <= (radius/scale)**2:
                                found.add(j);canvas.create_oval(x-19,y-19,x+19,y+19,outline='#2fbd78',width=4)
                                status.config(text=f'✅ {len(found)}/{len(hotspots)} điểm khác biệt')
                                if len(found)==len(hotspots):complete(True)
                                return
                        status.config(text='Hãy nhìn kỹ và thử lại nhé!',fg='#b64f4a')
                    canvas.bind('<Button-1>',click)
                else:tk.Label(f,text='Thiếu ảnh so sánh.',bg=WHITE,fg=MUTED).pack()
            status.pack(pady=9)
        round_at(0)
