"""Tự Học 2.0 — service layer + interactive Tkinter learning experience.
Compatible with historical 1.5.1 content and student database.
"""
from tuhoc.paths import PROJECT_ROOT
from tuhoc.ui.strings_vi import t
from tuhoc.ui.ui_components import Badge, LoadingState
from tuhoc.ui.ui_tokens import font_at

import json, random, time, datetime, re, shutil, math, os, sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from tuhoc.lessons.level_flow import THEMES, load_rows, library_file, LESSON_KEYS, QUESTION_KEYS, VOCAB_KEYS, BLOCK_KEYS, READING_KEYS
from tuhoc.ui.theme_config import tuples as theme_tuples, max_level as theme_max, normalize_code

def kind_is_picture(q):return q.get('type') in ('picture_choice','listening_choice')  # image only if the author set one; never guess it from the answer

BG='#F5F7FF'; INK='#26345E'; MUTED='#687694'; PURPLE='#6A5AE0'; MINT='#20B98C'; GOLD='#F1B83B'

class Curriculum:
    """Validated and cached JSON curriculum, with stable synthetic IDs for legacy rows."""
    def __init__(self, data_dir):
        self.data_dir=Path(data_dir);self.language='vi' if self.data_dir.name in ('vi','tieng_viet') else 'en';self.errors=[];self.rows={};self.reload()
    def reload(self):
        self.errors=[];self.rows={}
        # Read themes.json once per reload, not twice per row (was O(rows) disk reads).
        try:
            theme_rows=theme_tuples(self.data_dir)
            theme_codes={t[0] for t in theme_rows}
            theme_levels={t[0]:theme_max(self.data_dir,t[0]) for t in theme_rows}
            theme_error=None
        except (OSError,ValueError,TypeError,KeyError) as exc:
            theme_codes=set();theme_levels={};theme_error=exc
        def to_code(code):
            code=str(code).strip()
            if code in ('family','Family') and 'Family & Friends' in theme_codes:return 'Family & Friends'
            return code
        for kind in ('lessons','questions','vocab','blocks','reading'):
            try:
                rows=load_rows(self.data_dir,kind,None)
                if not isinstance(rows,list):raise ValueError('Dữ liệu phải là danh sách')
                valid=[];ids=set()
                for number,obj in enumerate(rows,1):
                    if not isinstance(obj,dict):self.errors.append(f'{kind}, dòng {number}: Không phải object');continue
                    try:
                        if theme_error is not None:raise ValueError(f'Không đọc được themes.json: {theme_error}')
                        theme=to_code(obj['theme']);level=int(obj['level'])
                        if theme not in theme_codes or not 1<=level<=theme_levels.get(theme,0):raise ValueError('Chủ đề/level không hợp lệ')
                        if kind=='questions' and not obj.get('answer') and obj.get('blank_answers'):
                            # Multi-blank rows (e.g. dropdown_fill_blank) store answers per blank; heal older rows saved with answer=''.
                            obj=dict(obj,answer=' | '.join(str(x) for x in obj['blank_answers']))
                        if kind=='questions' and (not obj.get('answer') or (obj.get('type') != 'picture_missing_letters' and not obj.get('prompt'))):raise ValueError('Thiếu prompt hoặc answer')
                        if kind=='vocab' and (not obj.get('word') or (self.language=='en' and not obj.get('meaning'))):raise ValueError('Thiếu word hoặc meaning')
                        unique=obj.get('id') or f'{kind}:{theme}:{level}:{obj.get("word",obj.get("order",number))}'
                        if unique in ids and kind=='blocks' and not obj.get('id'):
                            unique=f'{unique}:row{number}'
                        if unique in ids:raise ValueError(f'ID trùng: {unique}')
                        obj=dict(obj,theme=theme,id=str(unique),schema_version=str(obj.get('schema_version','2.0')))
                        ids.add(unique);valid.append(obj)
                    except (ValueError,TypeError,KeyError) as exc:self.errors.append(f'{kind}, dòng {number}: {exc}')
                self.rows[kind]=valid
            except (OSError,ValueError) as exc:self.errors.append(f'{kind}: {exc}');self.rows[kind]=[]
    def get(self,kind,theme,level):return [x for x in self.rows[kind] if x['theme']==theme and x['level']==level]
    def meaning(self,word):
        return next((v.get('meaning','') for v in self.rows['vocab'] if v['word'].casefold()==str(word).casefold()),'')
    def image(self,word,theme,level):
        return next((v.get('image','') for v in self.get('vocab',theme,level) if v['word'].casefold()==str(word).casefold()),'')

class LearningService:
    def __init__(self,db,curriculum):
        self.db=db;self.content=curriculum;self.language=curriculum.language
        self.db.conn.executescript('''
        CREATE TABLE IF NOT EXISTS level_scores(student_id INTEGER,theme TEXT,level INTEGER,score REAL,stars INTEGER,updated_at TEXT DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(student_id,theme,level));
        CREATE TABLE IF NOT EXISTS word_mastery(student_id INTEGER,word TEXT,correct INTEGER DEFAULT 0,wrong INTEGER DEFAULT 0,last_seen REAL DEFAULT 0,PRIMARY KEY(student_id,word));
        CREATE TABLE IF NOT EXISTS rewards(student_id INTEGER,reward_id TEXT,PRIMARY KEY(student_id,reward_id));
        CREATE TABLE IF NOT EXISTS learning_sessions(id INTEGER PRIMARY KEY,student_id INTEGER,theme TEXT,level INTEGER,started REAL,seconds REAL,correct INTEGER,total INTEGER);
        ''');self.db.conn.commit()
    def key(self,theme):return ('vi:' + theme) if self.language=='vi' else theme
    def wordkey(self,word):return ('[VI] ' + word) if self.language=='vi' else word
    def stars(self,sid,theme,level):
        row=self.db.conn.execute('SELECT stars FROM level_scores WHERE student_id=? AND theme=? AND level=?',(sid,self.key(theme),level)).fetchone()
        return int(row[0]) if row else 0
    def unlocked(self,sid,theme,level):return level==1 or self.stars(sid,theme,level-1)>0
    def next_level(self,sid):
        for theme,*_ in theme_tuples(self.content.data_dir):
            for level in range(1,theme_max(self.content.data_dir,theme)+1):
                if self.unlocked(sid,theme,level) and not self.stars(sid,theme,level):return theme,level
        return theme_tuples(self.content.data_dir)[0][0],1
    def mastery(self,sid,word):
        row=self.db.conn.execute('SELECT correct,wrong FROM word_mastery WHERE student_id=? AND word=?',(sid,self.wordkey(str(word)).casefold())).fetchone()
        return (row[1]+1)/(row[0]+row[1]+2) if row else .5
    def select_questions(self,sid,theme,level,limit=50):
        items=self.content.get('questions',theme,level)
        return sorted(items,key=lambda q:self.mastery(sid,q.get('answer',''))+random.random()*.15,reverse=True)[:limit]
    def save_answer(self,sid,q,answer,correct,seconds):
        word=str(q.get('answer','')).strip();self.db.record(sid,{'id':q['id'],'type':q.get('type','choice'),'version':'2.0'},int(correct),seconds,answer)
        with self.db.conn:
            self.db.conn.execute('INSERT INTO word_mastery(student_id,word,correct,wrong,last_seen) VALUES(?,?,?,?,?) ON CONFLICT(student_id,word) DO UPDATE SET correct=correct+excluded.correct,wrong=wrong+excluded.wrong,last_seen=excluded.last_seen',(sid,self.wordkey(word).casefold(),int(correct),int(not correct),time.time()))
        if not correct and word:
            meaning=self.content.meaning(word)
            if meaning or self.language=='vi':self.db.save_word(sid,self.wordkey(word),meaning)
    def finish(self,sid,theme,level,correct,total,duration,threshold=.75):
        ratio=correct/max(total,1);stars=(3 if ratio>=.95 else 2 if ratio>=.85 else 1) if ratio>=threshold else 0
        previous_stars=self.stars(sid,theme,level)
        with self.db.conn:
            self.db.conn.execute('INSERT INTO learning_sessions(student_id,theme,level,started,seconds,correct,total) VALUES(?,?,?,?,?,?,?)',(sid,self.key(theme),level,time.time()-duration,duration,correct,total))
            self.db.conn.execute('INSERT INTO level_scores(student_id,theme,level,score,stars) VALUES(?,?,?,?,?) ON CONFLICT(student_id,theme,level) DO UPDATE SET score=MAX(score,excluded.score),stars=MAX(stars,excluded.stars),updated_at=CURRENT_TIMESTAMP',(sid,self.key(theme),level,ratio,stars))
        self.db.save_lesson_progress(sid,f'{self.key(theme)}_{level}',correct,total,stars>0)
        if stars:
            earned=max(0,stars-previous_stars)
            if earned:self.db.add_points(sid,earned)
        return stars
    def ensure_time_tables(self):
        self.db.conn.executescript("""CREATE TABLE IF NOT EXISTS app_usage_daily(student_id INTEGER NOT NULL,day TEXT NOT NULL,seconds REAL NOT NULL DEFAULT 0,PRIMARY KEY(student_id,day));
        CREATE TABLE IF NOT EXISTS level_time_records(student_id INTEGER NOT NULL,subject TEXT NOT NULL,theme TEXT NOT NULL,level INTEGER NOT NULL,best_seconds REAL NOT NULL,updated_at TEXT DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(student_id,subject,theme,level));""")
        self.db.conn.commit()

    def best_level_time(self,sid,theme,level):
        self.ensure_time_tables()
        row=self.db.conn.execute('SELECT best_seconds FROM level_time_records WHERE student_id=? AND subject=? AND theme=? AND level=?',(sid,self.language,theme,level)).fetchone()
        return float(row[0]) if row else None

    def record_level_time(self,sid,theme,level,seconds):
        self.ensure_time_tables()
        previous=self.best_level_time(sid,theme,level)
        if previous is None or seconds<previous:
            with self.db.conn:
                self.db.conn.execute('INSERT INTO level_time_records(student_id,subject,theme,level,best_seconds) VALUES(?,?,?,?,?) ON CONFLICT(student_id,subject,theme,level) DO UPDATE SET best_seconds=excluded.best_seconds,updated_at=CURRENT_TIMESTAMP',(sid,self.language,theme,level,seconds))
        return previous

    def streak(self,sid):
        days={r[0] for r in self.db.conn.execute('SELECT DISTINCT date(started,"unixepoch","localtime") FROM learning_sessions WHERE student_id=?',(sid,))}
        today=datetime.date.today();start=today if today.isoformat() in days else today-datetime.timedelta(days=1)
        count=0
        while start.isoformat() in days:count+=1;start-=datetime.timedelta(days=1)
        return count
    def import_merge(self,path):
        """Validate all Excel rows before atomic backups + merge by stable id."""
        from openpyxl import load_workbook
        wb=load_workbook(path,read_only=True,data_only=True)
        names={'lessons':('CapHoc',LESSON_KEYS),'questions':('CauHoiCap',QUESTION_KEYS),'vocab':('TuVungCap',VOCAB_KEYS),'blocks':('NoiDungBaiHoc',BLOCK_KEYS),'reading':('BaiDoc',READING_KEYS)}
        plan={};errors=[];report=[]
        for kind,(sheet,keys) in names.items():
            if sheet not in wb:continue
            iterator=wb[sheet].values;header=next(iterator,None)
            if not header:continue
            cols=[str(x).strip() if x is not None else '' for x in header]
            required=set(keys)-{'audio'}
            if not required.issubset(cols):errors.append(f'{sheet}: Thiếu cột: {required-set(cols)}');continue
            current={str(x['id']):x for x in self.content.rows[kind]};added=updated=0
            for number,values in enumerate(iterator,2):
                if not any(v is not None and str(v).strip() for v in values):continue
                obj={key:(values[cols.index(key)] if key in cols and cols.index(key)<len(values) and values[cols.index(key)] is not None else '') for key in keys}
                try:
                    obj['theme']=normalize_code(obj['theme'],self.content.data_dir);obj['level']=int(obj['level'])
                    if obj['theme'] not in {t[0] for t in theme_tuples(self.content.data_dir)} or not 1<=obj['level']<=theme_max(self.content.data_dir,obj['theme']):raise ValueError('theme hoặc level không hợp lệ')
                    if kind=='questions' and (not obj['answer'] or (obj['type'] != 'picture_missing_letters' and not obj['prompt'])):raise ValueError('Thiếu prompt / answer')
                    if kind=='vocab' and (not obj['word'] or (self.language=='en' and not obj['meaning'])):raise ValueError('Thiếu từ hoặc nghĩa')
                    for key in ('options','accepted_answers'):
                        if key in obj:obj[key]=[a.strip() for a in str(obj[key]).split('|') if a.strip()]
                    if kind=='blocks':obj['order']=int(obj['order'])
                    raw_id=values[cols.index('id')] if 'id' in cols and cols.index('id')<len(values) else None
                    obj['id']=str(raw_id).strip() if raw_id else f'{kind}:{obj["theme"]}:{obj["level"]}:{obj.get("word",obj.get("order",number))}'
                    obj['schema_version']='2.0'
                    if obj['id'] in current:updated+=1
                    else:added+=1
                    current[obj['id']]=obj
                except (ValueError,TypeError) as exc:errors.append(f'{sheet} dòng {number}: {exc}')
            plan[kind]=list(current.values());report.append(f'{sheet}: +{added} mới, ~{updated} cập nhật')
        if errors:return False,report+errors
        if not plan:return False,['Không có sheet dữ liệu hợp lệ']
        from tuhoc.storage.safe_storage import commit_json
        backup = commit_json({library_file(self.content.data_dir, kind): items for kind, items in plan.items()},
                             self.content.data_dir/'backups'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
        self.content.reload()
        return True, report+[f'Sao lưu: {backup}']
    def export_report(self,sid,path):
        from openpyxl import Workbook
        wb=Workbook();ws=wb.active;ws.title='TienDo';ws.append(['Chủ đề','Level','Điểm','Sao'])
        for r in self.db.conn.execute('SELECT theme,level,score,stars FROM level_scores WHERE student_id=? AND theme '+('LIKE ?' if self.language=='vi' else 'NOT LIKE ?')+' ORDER BY theme,level',(sid,'vi:%')):ws.append(list(r))
        ws2=wb.create_sheet('TuYeu');ws2.append(['Từ','Số đúng','Số sai'])
        for r in self.db.conn.execute('SELECT word,correct,wrong FROM word_mastery WHERE student_id=? ORDER BY wrong DESC',(sid,)):ws2.append(list(r))
        ws3=wb.create_sheet('PhienHoc');ws3.append(['Chủ đề','Level','Phút','Đúng','Tổng'])
        for r in self.db.conn.execute('SELECT theme,level,ROUND(seconds/60,1),correct,total FROM learning_sessions WHERE student_id=? ORDER BY id DESC',(sid,)):ws3.append(list(r))
        for sheet in wb:
            sheet.freeze_panes='A2';sheet.auto_filter.ref=sheet.dimensions
            for col in 'ABCDE':sheet.column_dimensions[col].width=23
        wb.save(path)

class GameAppMixin:
    def setup_upgrade(self):
        self.lang=getattr(self,'lang','en')
        self._setup_language()
        self.title('Cùng Học Cùng Vui (Beta) - Dev by HiHieu');self.configure(bg=BG)
        self.option_add('*Font',font_at(11))
    def _setup_language_steps(self):
        """Subject preparation split into small steps so the loading animation can
        repaint between them. _setup_language() runs them back to back."""
        state={}
        def prepare():
            # One canonical root: TuHoc/mon_hoc/{tieng_anh,tieng_viet}/{level_*.json,images/}.
            # Import old installed files ONCE, never overwrite a student's edits.
            from tuhoc.lessons.unified_subjects import prepare_subject
            state['data']=prepare_subject(PROJECT_ROOT,self.lang,PROJECT_ROOT,legacy_root=self.data_dir)
        def curriculum():self.curriculum=Curriculum(state['data'])
        def learning():self.learning=LearningService(self.db,self.curriculum)
        def settings():self._display_settings=self._read_display_settings()
        return [prepare,curriculum,learning,settings]
    def _setup_language(self):
        for step in self._setup_language_steps():step()
    def _read_display_settings(self):
        p=PROJECT_ROOT/'mon_hoc'/'hien_thi.json'
        defaults={'image_width':350,'image_height':240,'word_size':32,'text_size':18,
                  'title_size':20,'content_size':18,'title_color':'#285D40',
                  'content_color':'#233C2A','auto_next':False, 'dragon_feedback_enabled':False}
        try:
            loaded=json.loads(p.read_text(encoding='utf8'))
            if not isinstance(loaded,dict):loaded={}
        except (ValueError,OSError):loaded={}
        defaults.update(loaded)
        # Older releases only provided text_size. Use that as initial content size.
        if 'content_size' not in loaded:
            defaults['content_size']=int(defaults.get('text_size',18))
        return defaults
    def _save_display_settings(self):
        p=PROJECT_ROOT/'mon_hoc'/'hien_thi.json';p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(self._display_settings,ensure_ascii=False,indent=2),encoding='utf8')
    def display_settings(self):
        body=self.layout('⚙  Cỡ hình, cỡ chữ và màu sắc bài học')
        c=self._card(body)
        tk.Label(c,text='Thiết lập dùng cho cả hai môn học',bg='white',fg=INK,font=font_at(15, 'bold')).pack(anchor='w',pady=8)
        settings=self._display_settings
        controls={}
        from tuhoc.ui.ui_tokens import FONT_SCALES
        labels=dict(zip(FONT_SCALES,('Nhỏ','Vừa','Lớn')))
        selected=tk.StringVar(value=labels.get(settings.get('ui_font_scale'),'Vừa'))
        font_row=tk.Frame(c,bg='white')
        font_row.pack(fill='x',pady=4)
        tk.Label(font_row,text='Cỡ chữ giao diện',bg='white',fg=INK).pack(side='left',padx=(0,12))
        ttk.Combobox(font_row,values=tuple(labels.values()),textvariable=selected,
                     state='readonly',width=8).pack(side='left')
        def slider(key,caption,minimum,maximum,default):
            row=tk.Frame(c,bg='white');row.pack(fill='x',pady=(4,7))
            tk.Label(row,text=caption,bg='white',fg=INK).pack(anchor='w')
            variable=tk.IntVar(value=int(settings.get(key,default)))
            tk.Scale(row,from_=minimum,to=maximum,orient='horizontal',length=440,
                     resolution=1,variable=variable,bg='white',
                     command=lambda _value:update_preview()).pack(anchor='w')
            controls[key]=variable
        # Each lesson block consists of an independent title and content area.
        slider('image_width','Chiều rộng hình (px)',100,900,350)
        slider('image_height','Chiều cao hình (px)',80,600,240)
        slider('word_size','Cỡ chữ từ vựng',16,65,32)
        slider('title_size','Cỡ chữ Title (tiêu đề bài học)',10,65,20)
        slider('content_size','Cỡ chữ Content (nội dung bài học)',10,65,18)
        preview=tk.Frame(c,bg='#F5F8F5',padx=14,pady=12)
        preview.pack(fill='x',pady=8)
        tk.Label(preview,text='XEM TRƯỚC',bg='#F5F8F5',fg=MUTED).pack(anchor='w')
        title_demo=tk.Label(preview,text='Đây là Title của bài học',bg='#F5F8F5',anchor='w')
        title_demo.pack(fill='x',pady=(4,7))
        content_demo=tk.Label(preview,text='Đây là Content của bài học. Có thể chọn cỡ chữ và màu riêng.',
                              bg='#F5F8F5',justify='left',anchor='w',wraplength=700)
        content_demo.pack(fill='x')
        colors={key:tk.StringVar(value=str(settings.get(key,default))) for key,default in
                [('title_color','#285D40'),('content_color','#233C2A')]}
        def update_preview():
            title_demo.configure(font=('Segoe UI',controls['title_size'].get(),'bold'),fg=colors['title_color'].get())
            content_demo.configure(font=('Segoe UI',controls['content_size'].get()),fg=colors['content_color'].get())
        def select_color(key):
            result=colorchooser.askcolor(color=colors[key].get(),title='Chọn màu cho '+('Title' if key=='title_color' else 'Content'),parent=self)
            if result and result[1]:colors[key].set(result[1]);update_preview()
        for key,caption in [('title_color','Màu Title'),('content_color','Màu Content')]:
            row=tk.Frame(c,bg='white');row.pack(fill='x',pady=3)
            tk.Label(row,text=caption,width=18,anchor='w',bg='white',fg=INK).pack(side='left')
            swatch=tk.Button(row,textvariable=colors[key],command=lambda k=key:select_color(k),
                             font=font_at(11),relief='groove',padx=10)
            swatch.pack(side='left')
            colors[key].trace_add('write',lambda *_args,b=swatch,k=key:b.configure(fg=colors[k].get()))
        reduced=tk.BooleanVar(value=bool(settings.get('reduce_motion',False)))
        tk.Checkbutton(c,text='Giảm chuyển động',variable=reduced,bg='white').pack(anchor='w',pady=4)
        auto=tk.BooleanVar(value=bool(settings.get('auto_next',False)))
        tk.Checkbutton(c,text='Tự động sang câu khi trả lời đúng',variable=auto,bg='white',font=font_at(12)).pack(anchor='w',pady=10)
        sound=tk.BooleanVar(value=bool(settings.get('feedback_sound',False)))
        tk.Checkbutton(c,text='Âm báo khi trả lời',variable=sound,bg='white').pack(anchor='w',pady=4)
        dragon_enabled=tk.BooleanVar(value=bool(settings.get('dragon_feedback_enabled',False)))
        tk.Checkbutton(c,text='Rồng Lân Ú: hiệu ứng mây ngũ sắc và mưa sao khi trả lời',
                       variable=dragon_enabled,bg='white',font=font_at(12)).pack(anchor='w',pady=(4,10))
        update_preview()
        def save():
            for key,var in controls.items():settings[key]=var.get()
            for key,var in colors.items():settings[key]=var.get()
            # Keep text_size for older quiz/vocabulary views, without coupling it to lesson content.
            settings['ui_font_scale']=next(key for key,label in labels.items() if label==selected.get())
            self.apply_font_preferences()
            self.reduce_motion=settings['reduce_motion']=reduced.get()
            settings['auto_next']=auto.get()
            settings['dragon_feedback_enabled']=dragon_enabled.get()
            settings['feedback_sound']=sound.get()
            self._save_display_settings()
            messagebox.showinfo('Đã lưu',t('settings_saved'))
        self.action_button(c,'LƯU THIẾT LẬP',save).pack(anchor='w',pady=8)
    def choose_language(self):
        try:
            from tuhoc.app.subject_loading_screen import preload_async
            preload_async()   # decode the loading background while the user picks a subject
        except Exception:
            pass
        body=self.layout('Xin chào các em. Đây là phần mềm học tập giúp các em có thể tự học và ôn tập các bài tập sát với chương trình học thực tế!')
        tk.Label(body,text='Các em hãy chọn ngôn ngữ mình muốn học',bg=body['bg'],fg=MUTED,font=font_at(13)).pack(anchor='w',pady=12)
        tk.Label(body,text='Môn đang chọn: '+('Tiếng Việt' if self.lang=='vi' else 'Tiếng Anh'),bg=body['bg'],fg=PURPLE,font=font_at(14, 'bold')).pack(anchor='w',pady=8)
        for lang,title,desc in [('en','TIẾNG ANH','Học tiếng anh chuẩn English'),('vi','TIẾNG VIỆT','Chuẩn ngôn ngữ miền Nam')]:
            card=self._card(body,24)
            tk.Label(card,text=title,bg='white',fg=INK,font=font_at(22, 'bold')).pack(anchor='w')
            tk.Label(card,text=desc,bg='white',fg=MUTED,font=font_at(12)).pack(anchor='w',pady=9)
            self.button(card,('✓ ĐANG CHỌN' if self.lang==lang else 'CHỌN'),lambda l=lang:self.switch_language(l)).pack(anchor='w')
    def switch_language(self,language):
        """H2.5: 2-second clock-driven loading, gated on real data readiness.

        Tk/SQLite work remains on the main thread for compatibility. If setup
        blocks Tk, animation may pause, but the clock catches up afterwards.
        """
        if language not in ('en', 'vi'):
            raise ValueError('Môn học không hợp lệ')
        if getattr(self, '_subject_loading', False):
            return
        from tuhoc.app.subject_loading_screen import SubjectLoadingScreen
        self._subject_loading = True
        previous = (getattr(self, 'lang', 'en'),
                    getattr(self, 'curriculum', None),
                    getattr(self, 'learning', None),
                    getattr(self, '_display_settings', None))
        try:
            self.clear()
            if getattr(self, '_shell', None) is not None:
                self._shell.pack_forget()
            screen = SubjectLoadingScreen(self, 'Tiếng Việt' if language == 'vi' else 'Tiếng Anh')
            screen.pack(fill='both', expand=True)
            screen.set_progress(0, 'Đang chuẩn bị môn học...')
        except Exception:
            self._subject_loading = False
            raise

        def fail(exc):
            self.lang, self.curriculum, self.learning, self._display_settings = previous
            self._subject_loading = False
            try:
                if screen.winfo_exists():
                    screen.destroy()
            except tk.TclError:
                pass
            messagebox.showerror('Không mở được môn học', str(exc), parent=self)
            try:
                self.choose_language()
            except Exception:
                pass

        def open_home():
            if not self.winfo_exists():
                self._subject_loading = False
                return
            try:
                self.home()
                self._subject_loading = False
            except Exception as exc:
                fail(exc)

        def prepare():
            if not self.winfo_exists():
                self._subject_loading = False
                return
            try:
                screen.set_progress(0, 'Đang nạp dữ liệu bài học...')
                self.lang = language
                steps = self._setup_language_steps()
            except Exception as exc:
                fail(exc)
                return

            def run_step(index=0):
                if not self.winfo_exists():
                    self._subject_loading = False
                    return
                try:
                    if index < len(steps):
                        steps[index]()
                        # Yield to Tk between steps so the animation keeps painting.
                        self.after(15, lambda: run_step(index + 1))
                        return
                    # Never show 100% before the actual preparation has completed.
                    screen.finish_when_ready(open_home)
                except Exception as exc:
                    fail(exc)
            run_step()

        # Import the screens the home page needs on a worker thread while the loading
        # animation runs, so those imports do not freeze the UI thread later.
        def prewarm():
            import importlib
            for name in ('tuhoc.lessons.unified_subjects', 'tuhoc.ui.home_ui', 'tuhoc.ui.ui_components', 'tuhoc.ui.ui_motion'):
                try:
                    importlib.import_module(name)
                except Exception:
                    pass
        import threading
        threading.Thread(target=prewarm, daemon=True).start()
        # Let the loading frame paint before synchronous setup begins.
        self.after(100, prepare)

    def button(self,parent,text,command):
        b=tk.Button(parent,text=text,command=command,bg=PURPLE,fg='white',activebackground='#4C3EBD',activeforeground='white',font=font_at(11, 'bold'),bd=4,relief='raised',padx=19,pady=12,cursor='hand2')
        b.bind('<Enter>',lambda e:b.configure(bg='#4D43B5',cursor='hand2'))
        b.bind('<Leave>',lambda e:b.configure(bg=PURPLE))
        b.bind('<ButtonPress-1>',lambda e:b.configure(relief='sunken',bd=4),add='+')
        b.bind('<ButtonRelease-1>',lambda e:b.configure(relief='raised',bd=4),add='+')
        return b
    def _card(self,parent,pad=20):
        w=tk.Frame(parent,bg='white',padx=pad,pady=pad,highlightthickness=1,highlightbackground='#DEE4F5');w.pack(fill='x',pady=9);return w
    def home(self):
        if not hasattr(self,'learning'):self.setup_upgrade()
        sid=self.student['id'];theme,level=self.learning.next_level(sid)
        body=self.layout('✦ '+('TIẾNG VIỆT' if self.lang=='vi' else 'TIẾNG ANH'))
        tk.Label(body,text='Học mỗi ngày • tích sao • khám phá thế giới!',bg=body['bg'],fg=MUTED,font=font_at(13)).pack(anchor='w')
        c=self._card(body)
        theme_name=next(x[1] for x in theme_tuples(self.curriculum.data_dir) if x[0]==theme)
        tk.Label(c,text=f'🚀  TIẾP TỤC HỌC  •  {theme_name} — Level {level}',bg='white',fg=INK,font=font_at(19, 'bold')).pack(anchor='w',pady=(0,15))
        self.button(c,'BẮT ĐẦU NGAY  →',lambda:self.start_session(theme,level)).pack(anchor='w')
        r=self._card(body)
        due=len(self._language_words(due=True));total=self.db.points(sid)
        tk.Label(r,text=f'🔥  {self.learning.streak(sid)} ngày streak       🃏  {due} từ đến hạn ôn       ⭐  {total} sao       🎯  Mục tiêu: 1 level/ngày',bg='white',fg=INK,font=font_at(12, 'bold')).pack(anchor='w')
        self.button(body,'⚙  Chỉnh Size hình/nội dung',self.display_settings).pack(anchor='w',fill='x',pady=(16,8))
        tk.Label(body,text='Các chức năng học tập nằm trong menu ☰ góc trên bên trái.',bg=body['bg'],fg=MUTED).pack(anchor='w',pady=12)
        if self.curriculum.errors:
            self.button(body,f'⚠ {len(self.curriculum.errors)} lỗi nội dung — Xem chi tiết',self.content_errors).pack(anchor='w',fill='x',pady=8)
    def journey_page(self):
        from tuhoc.lessons.lesson_map_ui import LessonMap
        LessonMap(self, True)

    def _draft_store(self):
        from tuhoc.storage.quiz_draft_store import QuizDraftStore
        return QuizDraftStore(self.db.conn)

    def _draft_key(self):
        return (self.student['id'], self.lang, self.s_theme, self.s_level)

    def _save_quiz_draft(self):
        if getattr(self, '_wrong_review_mode', False):
            return  # Review-only sessions never overwrite the normal Level draft.
        if getattr(self, '_quiz_saved', False) or not getattr(self, 's_questions', None):
            return
        try:
            self._draft_store().save(*self._draft_key(), self.s_questions,
                                     [(a, ok) for _q, a, ok in self.s_answers],
                                     max(0.0, time.monotonic()-self._quiz_timer_started))
            self._draft_saved_ok=True
        except (OSError, ValueError, TypeError, RuntimeError) as exc:
            self._draft_saved_ok=False
            print('Không lưu được tiến độ bài tập:', exc)

    def start_session(self,theme,level,quiz_only=False):
        self._wrong_review_mode=False
        if not self.learning.unlocked(self.student['id'],theme,level):messagebox.showwarning('Level đang khóa','Em cần vượt qua level trước với ít nhất 75%.');return
        self.s_theme=theme;self.s_level=level;self.s_started=time.monotonic();self.s_questions=self.learning.select_questions(self.student['id'],theme,level)
        self._quiz_generation=getattr(self,'_quiz_generation',0)+1;self._quiz_pending_index=None;self._quiz_launch_retries=0;self.s_answers=[];self.s_wrong=[];self.s_combo=0;self.s_xp=0;self.s_retry=False;self._quiz_saved=False;self._quiz_duration=0;self._quiz_previous_best=None;self._quiz_timer_started=time.monotonic()
        # A draft belongs to exactly one student, language, theme and level.
        try:
            draft=self._draft_store().load(self.student['id'],self.lang,theme,level)
        except (ValueError, OSError, RuntimeError) as exc:
            print('Không đọc được tiến độ bài tập:',exc);draft=None
        if draft and getattr(self,'_selected_lesson',None) is not None:
            current_lesson=str(self._selected_lesson)
            if any(str(q.get('lesson') or '1').strip()!=current_lesson for q in draft['questions']):
                draft=None
        if draft and 0 < len(draft['answers']) < len(draft['questions']):
            resume=messagebox.askyesnocancel('Tiếp tục bài tập?',
                f'Bạn đã làm {len(draft["answers"])}/{len(draft["questions"])} câu.\n'
                'Có: tiếp tục câu kế tiếp.\nKhông: làm lại từ đầu.\nHủy: giữ nguyên tiến độ.',parent=self)
            if resume is None:return
            if resume:
                self.s_questions=draft['questions']
                self.s_answers=[(q,answer,ok) for q,(answer,ok) in zip(draft['questions'],draft['answers'])]
                self.s_combo=0;self.s_xp=0
                self._quiz_timer_started=time.monotonic()-draft['elapsed']
                self.session_quiz(len(self.s_answers));return
        if draft:
            self._draft_store().delete(self.student['id'],self.lang,theme,level)
        if quiz_only:
            self.session_quiz(0)
        else:
            self.session_learn(0)
    def start_wrong_review(self, theme, level, question_ids):
        'Practice only currently incorrect questions, without changing Level scores.'
        if not hasattr(self, 'learning'):
            self.setup_upgrade()
        if not self.learning.unlocked(self.student['id'], theme, level):
            messagebox.showwarning('Level đang khóa', 'Bạn chưa mở khóa Level này.', parent=self)
            return
        requested = {str(qid) for qid in question_ids}
        selected = [q for q in self.curriculum.get('questions', theme, level)
                    if str(q.get('id')) in requested]
        if not selected:
            messagebox.showinfo('Không có câu hỏi', 'Các câu sai này không còn trong nội dung hiện tại.', parent=self)
            return
        self.s_theme=theme; self.s_level=level; self.s_started=time.monotonic()
        self.s_questions=selected; self.s_answers=[]; self.s_wrong=[]
        self.s_combo=0; self.s_xp=0; self.s_retry=False
        self._quiz_saved=False; self._quiz_duration=0; self._quiz_previous_best=None
        self._quiz_timer_started=time.monotonic()
        self._quiz_generation=getattr(self,'_quiz_generation',0)+1
        self._quiz_pending_index=None; self._quiz_launch_retries=0
        self._wrong_review_mode=True
        self.session_quiz(0)

    def _finish_wrong_review(self):
        'Record attempts/mastery, but do not award stars or unlock levels.'
        from tuhoc.exercises.pygame_review_panel import show_review
        total=len(self.s_questions)
        correct=sum(bool(ok) for _q,_answer,ok in self.s_answers)
        if not getattr(self,'_quiz_saved',False):
            duration=max(0.0,time.monotonic()-self._quiz_timer_started)
            self._quiz_duration=duration
            for q,answer,ok in self.s_answers:
                self.learning.save_answer(self.student['id'],q,
                    self._quiz_answer_text(q,answer),ok,duration/max(total,1))
            with self.db.conn:
                self.db.conn.execute('''CREATE TABLE IF NOT EXISTS wrong_review_sessions
                    (id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, subject TEXT NOT NULL,
                     theme TEXT NOT NULL, level INTEGER NOT NULL, correct INTEGER NOT NULL,
                     total INTEGER NOT NULL, seconds REAL NOT NULL,
                     created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
                self.db.conn.execute('''INSERT INTO wrong_review_sessions
                    (student_id,subject,theme,level,correct,total,seconds)
                    VALUES(?,?,?,?,?,?,?)''',
                    (self.student['id'],self.lang,self.s_theme,self.s_level,
                     correct,total,duration))
            self._quiz_saved=True
        rows=[dict(question=dict(q),answer=self._quiz_answer_text(q,answer),correct=ok)
              for q,answer,ok in self.s_answers]
        from tuhoc.ui.result_insights import summarize
        insights=summarize(self.s_answers)
        payload=dict(stars=0,correct=correct,total=total,insights=insights,
                     percent=correct/max(1,total),duration=self._format_elapsed(self._quiz_duration),
                     message='Ôn tập câu sai hoàn thành. Kết quả này không thay đổi sao hoặc mở khóa Level.',
                     unlock='Không thay đổi tiến độ Level.',rows=rows)
        ids=[str(q.get('id')) for q in self.s_questions]
        body=self.layout('📝 Kết quả ôn tập câu sai')
        def action(name):
            if name=='retry':
                self.start_wrong_review(self.s_theme,self.s_level,ids)
            else:
                self._wrong_review_mode=False
                self.wrong_answers_page()
        show_review(body,payload,action,
                    on_audio=lambda q:self.play_learning_audio(q.get('_pygame_audio') or q.get('audio')))

    @staticmethod
    def _format_elapsed(seconds):
        ticks=max(0,int(round(float(seconds)*100)))
        hours,rem=divmod(ticks,360000)
        minutes,rem=divmod(rem,6000)
        sec,cent=divmod(rem,100)
        return f'{hours:02d}:{minutes:02d}:{sec:02d}.{cent:02d}' if hours else f'{minutes:02d}:{sec:02d}.{cent:02d}'

    def _quiz_timer_header(self,body,index,total):
        line=tk.Frame(body,bg=body['bg']);line.pack(fill='x',pady=(2,12))
        tk.Label(line,text=('TIẾNG VIỆT' if self.lang=='vi' else 'TIẾNG ANH')+f'  ·  Level {self.s_level}',bg=body['bg'],fg=INK,font=font_at(15, 'bold')).pack(side='left')
        tk.Label(line,text=f'Câu {index+1}/{total}',bg=body['bg'],fg=MUTED,font=font_at(12)).pack(side='right')
        clock=tk.Label(line,text='',bg='#E6F7EF',fg='#147B46',font=('Consolas',15,'bold'),padx=12,pady=5)
        clock.pack(side='top',anchor='center')
        def refresh():
            if not clock.winfo_exists() or getattr(self,'_quiz_saved',False):return
            clock.config(text='⏱ '+self._format_elapsed(time.monotonic()-self._quiz_timer_started))
            clock.after(80,refresh)
        refresh()

    def _heading(self,body,sub):
        tk.Label(body,text=sub,bg=body['bg'],fg=MUTED,font=font_at(12)).pack(anchor='w',pady=(0,15))
    def _speak(self, word):
        """Start a tracked TTS process; navigation and shutdown stop it."""
        import subprocess
        text = str(word or '').strip()
        if not text:
            return
        # Do not leave overlapping speech from earlier clicks running.
        self._stop_reading_tts()
        try:
            if os.name == 'nt':
                escaped = text.replace("'", "''")
                locale = 'vi-VN' if self.lang == 'vi' else 'en-US'
                script = (
                    'Add-Type -AssemblyName System.Speech; '
                    '$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; '
                    "if ('" + locale + "' -eq 'vi-VN') { "
                    "try { $s.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::NotSet,"
                    "[System.Speech.Synthesis.VoiceAge]::NotSet,0,"
                    "(New-Object System.Globalization.CultureInfo('vi-VN'))) } catch {} }; "
                    "$s.Speak('" + escaped + "')"
                )
                proc = subprocess.Popen(
                    ['powershell', '-NoProfile', '-NonInteractive', '-Command', script],
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                )
            else:
                import shutil
                cmd = shutil.which('espeak') or shutil.which('spd-say')
                if not cmd:
                    messagebox.showinfo('Âm thanh', 'Hãy cài espeak để dùng TTS offline trên hệ điều hành này.')
                    return
                proc = subprocess.Popen([cmd, text])
            self._reading_tts_processes = [proc]
        except OSError:
            messagebox.showinfo('Âm thanh', 'Không khởi tạo được giọng đọc.')
    def _picture(self,container,relative):
        if not relative:return
        from tuhoc.lessons.unified_subjects import subject_image
        file=subject_image(self.curriculum.data_dir,relative)
        if not file:
            tk.Label(container,text='⚠ Không tìm thấy hình: '+str(relative),bg='white',fg='#B45309').pack(pady=6)
            return
        w=int(self._display_settings.get('image_width',350));h=int(self._display_settings.get('image_height',240))
        try:
            from tuhoc.ui.animated_media import display_image
            display_image(container,file,w,h,bg='white',pady=8)
        except (ImportError,OSError,ValueError,tk.TclError):
            tk.Label(container,text='⚠ Không thể mở hình: '+str(relative),bg='white',fg='#B45309').pack(pady=6)
    def session_learn(self,index):
        theme,level=self.s_theme,self.s_level;vocab=self.curriculum.get('vocab',theme,level)
        if index>=len(vocab):self.session_practice();return
        v=vocab[index];body=self.layout('📚  Khám phá từ vựng');self._heading(body,f'Bước 1/4  •  Từ {index+1}/{len(vocab)}')
        c=self._card(body,32);word=v['word']
        tk.Label(c,text=word,bg='white',fg=PURPLE,font=('Segoe UI',int(self._display_settings.get('word_size',32)),'bold')).pack()
        self._picture(c,v.get('image',''))
        tk.Label(c,text=(v.get('example','') or v.get('meaning','') or 'Đọc từ và nghe phát âm'),bg='white',fg=INK,font=('Segoe UI',int(self._display_settings.get('text_size',18))),wraplength=800).pack(pady=12)
        self.action_button(c,'🔊  NGHE PHÁT ÂM',lambda:self._speak(word)).pack(pady=6)
        self.button(body,'TIẾP THEO  →',lambda:self.session_learn(index+1)).pack(anchor='e',pady=12)
    def session_practice(self):
        vocab=self.curriculum.get('vocab',self.s_theme,self.s_level)
        if len(vocab)<2:self.session_quiz(0);return
        self.practice_words=random.sample(vocab,min(5,len(vocab)));self.practice_index=0;self.practice_next()
    def practice_next(self):
        if self.practice_index>=len(self.practice_words):self.session_quiz(0);return
        v=self.practice_words[self.practice_index];body=self.layout('🎲  Luyện tập kéo-thả');self._heading(body,f'Bước 2/4  •  Ghép chữ cái thành từ  {self.practice_index+1}/{len(self.practice_words)}')
        word=v['word'];c=self._card(body)
        tk.Label(c,text=f'Gợi ý: {v.get("example") or v.get("meaning") or "Sắp xếp chữ cái thành từ đúng"}',bg='white',fg=INK,font=font_at(18, 'bold')).pack(anchor='w',pady=12)
        tk.Label(c,text='Kéo các ô chữ vào khung, hoặc bấm vào từng ô theo thứ tự.',bg='white',fg=MUTED).pack(anchor='w')
        target=tk.Frame(c,bg='#ECEDFF',height=58);target.pack(fill='x',pady=12)
        tray=tk.Frame(c,bg='white');tray.pack(fill='x',pady=8)
        letters=list(word);random.shuffle(letters);chosen=[];buttons=[]
        status=tk.Label(c,text='',bg='white',fg=INK);status.pack(pady=6)
        def pick(i):
            if buttons[i]['state']=='disabled':return
            chosen.append((i,letters[i]));buttons[i].configure(state='disabled',bg='#E8E9F2')
            tk.Label(target,text=letters[i],bg=PURPLE,fg='white',font=font_at(16, 'bold'),padx=10,pady=6).pack(side='left',padx=3,pady=4)
            assembled=''.join(x[1] for x in chosen)
            if len(chosen)==len(letters):
                ok=assembled.casefold()==word.casefold();status.configure(text='✓ Chính xác!' if ok else f'↻ Thử lại nhé — Đáp án: {word}',fg=MINT if ok else '#D35B67')
                self.after(900,lambda:self._practice_done(ok))
        for i,ch in enumerate(letters):
            b=tk.Button(tray,text=ch,font=font_at(16, 'bold'),bg='#EAE7FF',fg=INK,width=3,height=1,bd=0,cursor='hand2');b.pack(side='left',padx=4)
            b.configure(command=lambda n=i:pick(n));buttons.append(b)
            b.bind('<ButtonPress-1>',lambda e,idx=i:setattr(self,'drag_source',idx))
            b.bind('<ButtonRelease-1>',lambda e,idx=i:pick(idx) if target.winfo_rooty()<=e.y_root<=target.winfo_rooty()+target.winfo_height() else None)
        self.action_button(c,'🔄  Xếp lại',self.practice_next).pack(anchor='w',pady=12)
    def _practice_done(self,ok):
        if not ok:
            self.practice_next();return
        self.practice_index+=1;self.practice_next()
    def _quiz_normalize(self,value):
        from tuhoc.exercises.review_normalize import normalize
        return normalize(value)

    def _quiz_pairs(self,q):
        from tuhoc.exercises.matching_widget import parse_pairs
        opts=q.get('options',[])
        if isinstance(opts,str):opts=[x.strip() for x in opts.split('|') if x.strip()]
        return parse_pairs(opts)

    def _quiz_correct(self,q,answer):
        from tuhoc.exercises.new_exercise_runtime import NEW_TYPES, correct
        if q.get('type') in NEW_TYPES:return correct(q,answer)
        if q.get('type')=='matching':
            pairs=self._quiz_pairs(q)
            return bool(pairs) and isinstance(answer,dict) and len(answer)==len(pairs) and all(answer.get(i)==i for i in range(len(pairs)))
        if q.get('type') == 'order':
            # Compare the ordered content, not its storage separator (| vs space).
            # Single-character tiles form a word; phrase/sentence tiles retain spaces.
            import re
            parts = q.get('options') or []
            if isinstance(parts, str):
                parts = [v.strip() for v in parts.split('|') if v.strip()]
            letter_tiles = bool(parts) and all(len(str(v).strip()) == 1 for v in parts)
            def normalized_order(value):
                if isinstance(value, (list, tuple)):
                    value = list(value)
                elif '|' in str(value):
                    value = str(value).split('|')
                else:
                    value = str(value).split()
                tokens = [str(v).strip() for v in value if str(v).strip()]
                joined = ''.join(tokens) if letter_tiles else ' '.join(tokens)
                return self._quiz_normalize(re.sub(r'\s+', ' ', joined).strip())
            return normalized_order(answer) == normalized_order(q.get('answer', ''))
        accepted=q.get('accepted_answers') or [q.get('answer','')]
        if isinstance(accepted,str):accepted=[x.strip() for x in accepted.split('|') if x.strip()]
        return self._quiz_normalize(answer) in {self._quiz_normalize(x) for x in accepted}

    def _quiz_answer_text(self,q,answer):
        from tuhoc.exercises.new_exercise_runtime import NEW_TYPES, answer_text
        if q.get('type') in NEW_TYPES:return answer_text(q,answer)
        if q.get('type')!='matching':return str(answer)
        pairs=self._quiz_pairs(q)
        if not isinstance(answer,dict):return ''
        return ' | '.join(f'{pairs[i][0]} → {pairs[j][1]}' for i,j in sorted(answer.items()) if 0<=i<len(pairs) and 0<=j<len(pairs))

    def _return_to_home_lessons(self):
        """Return to the sidebar Bài học map, not the legacy level_lesson screen."""
        self._lesson_map_theme = getattr(self, 's_theme', getattr(self, '_lesson_map_theme', None))
        self._lesson_map_level = getattr(self, 's_level', getattr(self, '_lesson_map_level', 1))
        self._selected_lesson = getattr(self, 's_lesson', getattr(self, '_selected_lesson', None))
        if hasattr(self, 'topic_page'):
            self.topic_page()
        else:
            self.home()

    def _clear_quiz_busy(self):
        loading=getattr(self,'_quiz_loading',None)
        if loading is not None and loading.winfo_exists():
            loading.destroy()
        self._quiz_loading=None

    def _sound_answer_feedback(self):
        if getattr(self,'_display_settings',{}).get('feedback_sound',False):
            self.bell()

    def _quiz_back_to_lesson(self):
        """Leave an unfinished quiz explicitly, invalidating delayed callbacks."""
        answers = len(getattr(self, 's_answers', []))
        total = len(getattr(self, 's_questions', []))
        if not getattr(self, '_quiz_saved', False) and total and answers < total:
            if not messagebox.askyesno(
                'Rời bài tập?',
                f'Bạn đã hoàn thành {answers}/{total} câu.\n'
                'Tiến độ các câu đã hoàn thành sẽ được lưu để tiếp tục sau.\n\n'
                'Bạn có muốn rời bài tập không?',
                parent=self,
            ):
                return
        self._save_quiz_draft()
        review_mode=getattr(self,'_wrong_review_mode',False)
        self._lesson_quiz_active=False
        self._clear_quiz_busy()
        # A queued Pygame answer/retry must not resurrect the abandoned quiz.
        self._quiz_generation = getattr(self, '_quiz_generation', 0) + 1
        self._quiz_pending_index = None
        self._quiz_launch_retries = 0
        try:
            from tuhoc.exercises.pygame_exercises import close as pg_close
            pg_close(self)
        except (ImportError, RuntimeError, AttributeError):
            pass
        if review_mode:
            self._wrong_review_mode=False
            self.wrong_answers_page()
        else:
            self._return_to_home_lessons()

    def session_quiz(self,index):
        items=self.s_questions
        # The submitted-answer count is the source of truth for sequential progress.
        # Ignore stale/reentrant callbacks requesting an older or future question.
        if not getattr(self, "_quiz_saved", False):
            expected = len(getattr(self, "s_answers", []))
            if index != expected:
                index = expected
        if index>=len(items):self.session_finish();return
        q=items[index];kind=q.get('type','choice')
        generation=getattr(self,'_quiz_generation',0)
        # Only one pending window/retry is allowed for a question.
        if getattr(self,'_quiz_pending_index',None)==(generation,index):return
        if index==0 and (not hasattr(self,'_quiz_timer_started') or getattr(self,'_quiz_saved',False)):
            self._quiz_timer_started=time.monotonic()
        pygame_status = None
        # Pygame is the primary quiz UI. Do not render the old Tkinter exercise
        # underneath it; only fall back when Pygame is unavailable/unsupported.
        try:
            from tuhoc.exercises.pygame_exercises import available as pg_available, launch as pg_launch, SUPPORTED as pg_supported
            if pg_available() and kind in pg_supported:
                pg_q=dict(q, _index=index+1, _total=len(items))
                image_ref=q.get('image') or ('' if kind_is_picture(q) else self.curriculum.image(q.get('answer',''),self.s_theme,self.s_level))
                if image_ref:
                    from tuhoc.lessons.unified_subjects import subject_image
                    resolved=subject_image(self.curriculum.data_dir,image_ref)
                    if resolved: pg_q['_pygame_image']=str(resolved)
                if q.get('audio'):
                    try:
                        audio_path=self.media_file(q.get('audio'))
                        if audio_path: pg_q['_pygame_audio']=str(audio_path)
                    except (AttributeError,OSError,ValueError): pass
                # Matching answer indices must match the original JSON order.
                def on_answer(value, question=q, expected_index=index, question_kind=kind, expected_generation=generation):
                    if expected_generation!=getattr(self,'_quiz_generation',0):return
                    self._quiz_pending_index=None
                    if getattr(self,'_quiz_saved',False) or len(self.s_answers)!=expected_index:
                        return
                    from tuhoc.exercises.new_exercise_runtime import NEW_TYPES
                    if question_kind in NEW_TYPES:
                        answer=value
                    elif question_kind=='matching':
                        if not isinstance(value,dict): return
                        answer={int(k):int(v) for k,v in value.items()}
                        if len(answer)!=len(self._quiz_pairs(question)): return
                    else:
                        answer=str(value).strip()
                        if not answer:return
                    ok=self._quiz_correct(question,answer)
                    self._quiz_launch_retries=0
                    self.s_answers.append((question,answer,ok))
                    self._sound_answer_feedback()
                    self._save_quiz_draft()
                    if ok:self.s_combo+=1;self.s_xp+=10+min(self.s_combo,5)*2
                    else:self.s_combo=0
                    self.session_quiz(expected_index+1)
                def on_cancel(expected_generation=generation, expected_index=index):
                    # The SDL window was closed without submitting an answer.
                    # Clear the pending slot so re-entering the quiz can launch again.
                    if expected_generation != getattr(self, '_quiz_generation', 0):
                        return
                    if getattr(self, '_quiz_pending_index', None) == (expected_generation, expected_index):
                        self._quiz_pending_index = None
                    self._quiz_launch_retries = 0
                    self._lesson_quiz_active=False
                    self._save_quiz_draft()
                    # Do not create a new quiz window automatically after user closes it.
                    self._quiz_generation += 1
                    if getattr(self,'_wrong_review_mode',False):
                        self._wrong_review_mode=False
                        self.wrong_answers_page()
                    else:
                        self._quiz_exit_results()
                if pg_launch(self,pg_q,on_answer,on_cancel=on_cancel):
                    self._clear_quiz_busy()
                    self._quiz_pending_index=(generation,index)
                    return
                pygame_status = t('quiz_busy')
                # SDL is busy or the renderer failed to launch. Do not silently
                # replace the question with Tk and reset the quiz sequence.
                if getattr(self,'_quiz_launch_retries',0)<12:
                    self._quiz_launch_retries=getattr(self,'_quiz_launch_retries',0)+1
                    if self._quiz_launch_retries==3 and isinstance(self,tk.Misc):
                        self._quiz_loading=LoadingState(self,t('quiz_busy_title'))
                        self._quiz_loading.place(relx=.5,rely=.9,anchor='center')
                    self._quiz_pending_index=(generation,index)
                    def retry():
                        if getattr(self,'_quiz_generation',0)!=generation:return
                        if getattr(self,'_quiz_pending_index',None)!=(generation,index):return
                        self._quiz_pending_index=None
                        self.session_quiz(index)
                    self.after(180,retry)
                    return
                pygame_status = 'Không thể mở Pygame sau nhiều lần thử. Bạn có thể làm câu này bằng giao diện dự phòng.'
        except Exception as exc:
            import traceback
            traceback.print_exc()
            pygame_status = t('quiz_fallback')
        self._clear_quiz_busy()
        body=self.layout('🧠  Thử thách kiến thức')
        if index==0 and (not hasattr(self,'_quiz_timer_started') or getattr(self,'_quiz_saved',False)):
            self._quiz_timer_started=time.monotonic()
        self._quiz_timer_header(body,index,len(items))
        if self.s_answers:
            ok=self.s_answers[-1][2]
            Badge(body,t('correct_feedback' if ok else 'incorrect_feedback'),
                  tone='success' if ok else 'danger').pack(anchor='w',pady=(0,5))
        # Provide an explicit, recoverable exit in the Tk fallback UI.
        self.button(body, '←  QUAY VỀ BÀI HỌC', self._quiz_back_to_lesson).pack(anchor='w', pady=(0, 8))
        bar=ttk.Progressbar(body,maximum=max(len(items),1),value=index+1,length=670)
        bar.pack(anchor='w',fill='x',pady=8)
        if pygame_status:
            status=tk.Frame(body,bg='#FFF4DC',padx=12,pady=9)
            status.pack(fill='x',pady=(0,10))
            tk.Label(status,text='⚠  '+pygame_status,bg='#FFF4DC',fg='#805400',wraplength=690,justify='left').pack(side='left',fill='x',expand=True)
            def try_pygame_again():
                if getattr(self,'_quiz_saved',False) or len(self.s_answers)!=index:return
                self._quiz_launch_retries=0
                self._quiz_pending_index=None
                self.session_quiz(index)
            self.button(status,'Thử lại Pygame',try_pygame_again).pack(side='right',padx=(8,0))
        c=self._card(body)
        from tuhoc.exercises.question_prompt import display_prompt
        prompt_label=tk.Label(c,text=str(display_prompt(q)),bg='white',fg=INK,font=('Segoe UI',int(self._display_settings.get('text_size',18)),'bold'),wraplength=760,justify='left')
        prompt_label.pack(anchor='w',pady=10)
        # Fit long prompts to the actual card width (including small screens/DPI).
        c.bind('<Configure>',lambda event:prompt_label.configure(wraplength=max(180,event.width-36)),add='+')
        if kind in ('listening_choice','listening_fill','listening','listening_image_choice'):
            self.action_button(c,'🔊  NGHE ÂM THANH',lambda q=q:self.play_learning_audio(self.media_file(q.get('audio','')))).pack(anchor='w',pady=5)
        # Never play or reveal the answer before submission.
        self._picture(c,q.get('image') or ('' if kind_is_picture(q) else self.curriculum.image(q.get('answer',''),self.s_theme,self.s_level)))
        opts=q.get('options',[])
        if isinstance(opts,str):opts=[x.strip() for x in opts.split('|') if x.strip()]
        board=None;entry=None;choice=tk.StringVar(master=c,value='')
        if kind in ('image_multi_choice','picture_missing_letters','sentence_gaps','conversation_gaps','passage_gaps'):
            from tuhoc.exercises.new_exercise_runtime import gaps, expected
            import re
            if kind == 'image_multi_choice':
                options = q.get('image_options') or [{'image': v} for v in q.get('options', [])]
                for i, option in enumerate(options):
                    path = option.get('image', '') if isinstance(option, dict) else str(option)
                    line = tk.Frame(c, bg='#DDF5E5' if path == q.get('answer') else '#F5F6F9')
                    line.pack(fill='x', pady=3)
                    try:
                        self._picture(line, path)
                    except (ValueError, OSError, TypeError):
                        pass
                    tk.Label(line, text=f'{chr(65+i)}  '+('✓ Đáp án đúng' if path == q.get('answer') else ''),
                             bg=line['bg'], fg='#147B46' if path == q.get('answer') else INK).pack(side='left', padx=8)
            elif kind == 'picture_missing_letters':
                word = str(q.get('answer', ''))
                hidden = set(q.get('hidden_indices', []))
                holder = tk.Frame(c, bg='white'); holder.pack(anchor='w', pady=8)
                for i, char in enumerate(word):
                    tk.Label(holder, text=char, width=2, padx=5, pady=8,
                             bg='#DDF5E5' if i in hidden else '#EEF2F6',
                             fg='#147B46' if i in hidden else INK,
                             font=font_at(13, 'bold')).grid(row=i//16, column=i%16, padx=2, pady=2)
            else:
                # Render EVERY dialogue turn and EVERY gap at its original position.
                # Do not use q['answer']: it is only a flat answer summary.
                display = tk.Text(c, height=min(18, max(5, len(q.get('dialogue', []))*3+3)),
                                  wrap='word', bg='#F8FAFC', fg=INK,
                                  font=font_at(13), relief='flat', padx=12, pady=12)
                display.tag_configure('correct_gap', background='#DDF5E5', foreground='#147B46')
                display.pack(fill='x', pady=8)
                for j, (source, indices) in enumerate(gaps(q)):
                    if kind == 'conversation_gaps':
                        speaker = q.get('dialogue', [])[j].get('speaker', '')
                        display.insert('end', str(speaker)+': ')
                    last=0
                    for i, match in enumerate(re.finditer(r'\S+', source)):
                        if i not in indices: continue
                        display.insert('end', source[last:match.start()])
                        display.insert('end', match.group(), 'correct_gap')
                        last=match.end()
                    display.insert('end', source[last:]+ '\n' + ('\n' if kind=='passage_gaps' else ''))
                display.configure(state='disabled')
            tk.Label(c, text='Các ô màu xanh hiển thị đáp án đúng tại vị trí cần điền.',
                     bg='white', fg='#147B46', wraplength=720).pack(anchor='w', pady=5)
        elif kind=='matching':
            from tuhoc.exercises.matching_widget import MatchingBoard
            pairs=self._quiz_pairs(q)
            if not pairs:
                tk.Label(c,text='Câu nối cặp chưa có đáp án chuẩn. Vui lòng chỉnh trong Quản lý câu hỏi.',bg='white',fg='#BA3F54',wraplength=700).pack(pady=8)
            else:
                tk.Label(c,text='Chọn ô bên trái rồi chọn ô bên phải để nối. Có thể đổi lại đường nối.',bg='white',fg=MUTED).pack(anchor='w',pady=5)
                board=MatchingBoard(c,pairs,media_root=self.curriculum.data_dir/'images')
                board.pack(fill='x',pady=10)
                self.action_button(c,'↻ Xóa các đường nối',board.reset).pack(anchor='w',pady=4)
        elif kind in ('choice','true_false','listening','listening_choice','picture_choice') and opts:
            first_option=None
            for opt in opts:
                option=tk.Radiobutton(c,text=str(opt),variable=choice,value=str(opt),bg='white',activebackground='#EDF0FF',font=font_at(13),anchor='w',wraplength=700,justify='left',cursor='hand2',takefocus=True,highlightthickness=2,highlightbackground='white',highlightcolor=PURPLE)
                option.pack(anchor='w',fill='x',pady=4)
                option.bind('<Enter>',lambda _event,widget=option:widget.configure(bg='#EDF0FF'))
                option.bind('<Leave>',lambda _event,widget=option:widget.configure(bg='white'))
                option.bind('<FocusIn>',lambda _event,widget=option:widget.configure(bg='#EDF0FF'))
                option.bind('<FocusOut>',lambda _event,widget=option:widget.configure(bg='white'))
                c.bind('<Configure>',lambda event,widget=option:widget.configure(wraplength=max(160,event.width-65)),add='+')
                if first_option is None:first_option=option
            if first_option is not None:self.after_idle(lambda widget=first_option:widget.focus_set() if widget.winfo_exists() else None)
        else:
            entry=tk.Entry(c,textvariable=choice,font=font_at(15),width=46,highlightthickness=2,highlightbackground='#DCE3F3',highlightcolor=PURPLE)
            entry.pack(anchor='w',fill='x',pady=15)
            self.after_idle(lambda widget=entry:widget.focus_set() if widget.winfo_exists() else None)
        # Tk fallback is exclusive: do not launch a second Pygame question here.
        # The primary Pygame launch above already handles its own callback.
        notice=tk.Label(c,text='',bg='white',fg='#B45309',font=font_at(11))
        notice.pack(anchor='w',pady=5)
        def submit(pygame_answer=None):
            if getattr(self,'_quiz_saved',False) or len(self.s_answers)!=index:
                return
            if kind=='matching':
                if board is None:notice.config(text='Chưa có cặp nối hợp lệ.');return
                answer=pygame_answer if pygame_answer is not None else dict(board.links)
                if len(answer)!=len(board.pairs):notice.config(text='Hãy nối đủ tất cả các cặp trước khi tiếp tục.');return
            else:
                answer=choice.get().strip()
                if not answer:notice.config(text='Hãy nhập hoặc chọn đáp án trước khi tiếp tục.');return
            ok=self._quiz_correct(q,answer)
            self.s_answers.append((q,answer,ok))
            self._sound_answer_feedback()
            self._save_quiz_draft()
            if ok:self.s_combo+=1;self.s_xp+=10+min(self.s_combo,5)*2
            else:self.s_combo=0
            self.session_quiz(index+1)
        submit_button=self.button(c,'HOÀN THÀNH LEVEL →' if index==len(items)-1 else 'LƯU CÂU TRẢ LỜI & TIẾP THEO →',submit)
        submit_button.configure(takefocus=True,highlightthickness=2,highlightbackground='white',highlightcolor=PURPLE)
        submit_button.pack(anchor='w',pady=12)
        # Space activates a focused Tk button; Return is also supported here.
        submit_button.bind('<Return>',lambda _event:submit())
        if entry is not None:
            entry.bind('<Return>',lambda _event:submit())

    def _retry_current_lesson_questions(self):
        """Retry exactly the questions from the completed Lesson, not the whole Level."""
        questions = list(getattr(self, 's_questions', ()) or ())
        if not questions:
            return
        # Keep the selected Lesson and question set. Never reselect by Level here.
        self._wrong_review_mode = False
        self._lesson_quiz_active = True
        self._quiz_generation = getattr(self, '_quiz_generation', 0) + 1
        self._quiz_pending_index = None
        self._quiz_launch_retries = 0
        self.s_questions = questions
        self.s_answers = []
        self.s_wrong = []
        self.s_combo = 0
        self.s_xp = 0
        self.s_retry = False
        self._quiz_saved = False
        self._quiz_duration = 0
        self._quiz_previous_best = None
        self.s_started = time.monotonic()
        self._quiz_timer_started = self.s_started
        self.session_quiz(0)

    def _quiz_exit_results(self):
        """Read-only progress/results on closing SDL; do not score unfinished questions."""
        completed = len(getattr(self, 's_answers', ()))
        total = len(getattr(self, 's_questions', ()))
        correct = sum(bool(row[2]) for row in getattr(self, 's_answers', ()))
        body = self.layout('Kết quả bài tập')
        card = self._card(body)
        tk.Label(card, text=t('quiz_completed',completed=completed,total=total), bg='white', fg=INK,
                 font=font_at(19, 'bold')).pack(anchor='w', pady=(4, 10))
        tk.Label(card, text=f'Đúng: {correct}  |  Sai: {completed-correct}  |  Chưa làm: {total-completed}',
                 bg='white', fg=MUTED, font=font_at(13)).pack(anchor='w', pady=(0, 8))
        tk.Label(card, text=t('draft_saved' if getattr(self,'_draft_saved_ok',False) else 'draft_unsaved'),
                 bg='white', fg=MUTED, font=font_at(11)).pack(anchor='w', pady=(0, 12))
        self.button(card, 'Tiếp tục làm bài', lambda: self._resume_quiz_from_results()).pack(anchor='w', pady=5)
        self.button(card, 'Về danh sách bài học', self._return_to_home_lessons).pack(anchor='w', pady=5)

    def _resume_quiz_from_results(self):
        self._lesson_quiz_active = True
        self.session_quiz(len(getattr(self, 's_answers', ())))

    def session_finish(self):
        try:
            from tuhoc.exercises.pygame_exercises import close as _pg_close
            _pg_close(self)
        except ImportError:
            pass
        if len(self.s_answers)<len(self.s_questions):
            self.session_quiz(len(self.s_answers));return
        if getattr(self,'_wrong_review_mode',False):
            self._finish_wrong_review();return
        self._lesson_quiz_active=False
        correct=sum(int(row[2]) for row in self.s_answers)
        total=len(self.s_questions)
        if not getattr(self,'_quiz_saved',False):
            duration=time.monotonic()-getattr(self,'_quiz_timer_started',self.s_started)
            self._quiz_duration=duration
            self._quiz_previous_best=None
            if total and correct==total:
                self._quiz_previous_best=self.learning.record_level_time(self.student['id'],self.s_theme,self.s_level,duration)
            for q,answer,ok in self.s_answers:
                self.learning.save_answer(self.student['id'],q,self._quiz_answer_text(q,answer),ok,duration/max(total,1))
            self._quiz_stars=self.learning.finish(self.student['id'],self.s_theme,self.s_level,correct,total,duration) if total else 0
            self._quiz_saved=True
            self._draft_store().delete(*self._draft_key())
        stars=self._quiz_stars
        previous=getattr(self,'_quiz_previous_best',None)
        duration=getattr(self,'_quiz_duration',0)
        if total and correct==total:
            if previous is None:msg='Bạn đã hoàn thành trong '+self._format_elapsed(duration)
            elif duration<previous:msg='Chúc mừng bạn vừa đạt kỷ lục mới, nhanh hơn '+f'{previous-duration:.2f}'+' giây'
            elif duration>previous:msg='Bạn hoàn thành chậm hơn '+f'{duration-previous:.2f}'+' giây so với kỷ lục trước'
            else:msg='Bạn đã hoàn thành bằng kỷ lục hiện tại!'
        else:msg='Chưa đạt 100% đáp án đúng nên thời gian này không được ghi vào kỷ lục.'
        def review_question(q):
            item=dict(q)
            for field in ('image','audio'):
                if item.get(field):
                    try:
                        path=self.media_file(item[field])
                        if path:item['_pygame_image' if field=='image' else '_pygame_audio']=str(path)
                    except (OSError,ValueError,TypeError):pass
            if item.get('type')=='image_multi_choice':
                paths={}
                for opt in item.get('image_options',[]):
                    ref=str(opt.get('image','')) if isinstance(opt,dict) else str(opt)
                    try:
                        path=self.media_file(ref)
                        if path:paths[ref]=str(path)
                    except (OSError,ValueError,TypeError):pass
                item['_choice_images']=paths
            return item
        from tuhoc.ui.result_insights import summarize
        insights=summarize(self.s_answers)
        payload=dict(stars=stars,correct=correct,total=total,insights=insights,percent=correct/max(total,1),duration=self._format_elapsed(duration),message=msg,unlock='Mở khóa level tiếp theo!' if stars else 'Cần ít nhất 75% để mở khóa level sau.',rows=[dict(question=review_question(q),answer=a if q.get('type')=='matching' else self._quiz_answer_text(q,a),correct=ok) for q,a,ok in self.s_answers])
        body=self.layout('🎉 Kết quả Level')
        from tuhoc.exercises.pygame_review_panel import show_review
        def action(name):
            if name=='retry':
                self._retry_current_lesson_questions()
            else:
                self._quiz_back_to_lesson()
        show_review(body,payload,action,on_audio=lambda q:self.play_learning_audio(q.get('_pygame_audio') or q.get('audio')))

    def quiz_history_page(self):
        """Read-only history of completed quizzes for the active student."""
        from tuhoc.ui.quiz_history_ui import show_history
        body=self.layout('📚 Lịch sử làm bài')
        show_history(body,self.db.conn,self.student['id'],
                     on_back=self.report_page,on_retry=self.wrong_answers_page)

    def wrong_answers_page(self):
        """Review incorrect attempts without altering the current quiz session."""
        from tuhoc.ui.wrong_answers_ui import show_wrong_answers
        body=self.layout('📝 Ôn tập câu sai')
        show_wrong_answers(body,self.db.conn,self.student['id'],
                           self.curriculum if hasattr(self,'curriculum') else self.learning.content,
                           on_back=self.report_page,
                           on_retry=lambda theme,level,ids:self.start_wrong_review(theme,level,ids))

    def learning_analytics_page(self):
        from tuhoc.ui.learning_analytics_ui import show_analytics
        body=self.layout('📈 Tiến độ học tập')
        show_analytics(body,self.db.conn,self.student['id'],on_back=self.report_page,on_retry=self.wrong_answers_page)

    def time_statistics_page(self):
        self.learning.ensure_time_tables()
        sid=self.student['id'];body=self.layout('⏱ Thống kê thời gian tài khoản')
        self._heading(body,'Thời gian sử dụng ứng dụng và kỷ lục Level theo tài khoản.')
        self.button(body,'📚  Xem lịch sử làm bài',self.quiz_history_page).pack(anchor='w',pady=(5,12))
        c=self._card(body)
        tk.Label(c,text='THỐNG KÊ SỬ DỤNG ỨNG DỤNG',bg='white',fg=INK,font=font_at(15, 'bold')).pack(anchor='w')
        filters=tk.Frame(c,bg='white');filters.pack(anchor='w',pady=10)
        period=tk.StringVar(value='Tuần');offset=tk.IntVar(value=0)
        title=tk.Label(c,bg='white',fg=INK,font=font_at(12, 'bold'));title.pack(anchor='w')
        total_label=tk.Label(c,bg='white',fg=INK,font=font_at(12));total_label.pack(anchor='w',pady=6)
        chart=tk.Canvas(c,width=780,height=240,bg='white',highlightthickness=0);chart.pack(fill='x',pady=8)
        def render():
            import datetime,calendar
            today=datetime.date.today();mode=period.get();off=offset.get()
            if mode=='Ngày':
                day=today+datetime.timedelta(days=off)
                dates=[day];labels=[day.strftime('%d/%m')];heading=day.strftime('%d/%m/%Y')
            elif mode=='Tuần':
                monday=today-datetime.timedelta(days=today.weekday())+datetime.timedelta(weeks=off)
                dates=[monday+datetime.timedelta(days=i) for i in range(7)]
                labels=['T2','T3','T4','T5','T6','T7','CN'];heading=f'{dates[0]:%d/%m/%Y} - {dates[-1]:%d/%m/%Y}'
            else:
                n=today.year*12+today.month-1+off;y,m=divmod(n,12);y+=0;m+=1
                dates=[datetime.date(y,m,i) for i in range(1,calendar.monthrange(y,m)[1]+1)]
                labels=[str(d.day) for d in dates];heading=f'Tháng {m:02d}/{y}'
            rows=self.db.conn.execute('SELECT day,seconds FROM app_usage_daily WHERE student_id=?',(sid,)).fetchall()
            usage=dict(rows);vals=[float(usage.get(d.isoformat(),0))/60 for d in dates]
            total=sum(vals);overall=sum(float(v) for v in usage.values())
            title.config(text=heading)
            total_label.config(text=f'Trong kỳ: {self._format_elapsed(total*60)}    •    Tổng từ trước đến nay: {self._format_elapsed(overall)}')
            # Line + dot visualization; same underlying usage values and filters.
            from tuhoc.ui.ui_line_dot import draw_line_dot
            draw_line_dot(chart, vals, labels)
        def change(value):period.set(value);offset.set(0);render()
        for mode in ('Ngày','Tuần','Tháng'):
            tk.Button(filters,text=mode,command=lambda m=mode:change(m),bg='#E6F7EF',fg=INK,bd=0,padx=15,pady=8).pack(side='left',padx=4)
        nav=tk.Frame(c,bg='white');nav.pack(anchor='w')
        tk.Button(nav,text='← Kỳ trước',command=lambda:(offset.set(offset.get()-1),render()),bg='#E9EBF7',bd=0,padx=12,pady=7).pack(side='left',padx=5)
        tk.Button(nav,text='Hôm nay',command=lambda:(offset.set(0),render()),bg='#E9EBF7',bd=0,padx=12,pady=7).pack(side='left',padx=5)
        tk.Button(nav,text='Kỳ sau →',command=lambda:(offset.set(offset.get()+1),render()),bg='#E9EBF7',bd=0,padx=12,pady=7).pack(side='left',padx=5)
        render()
        records=self._card(body)
        tk.Label(records,text='🏆 KỶ LỤC NHANH NHẤT THEO LEVEL (ĐÚNG 100%)',bg='white',fg=INK,font=font_at(15, 'bold')).pack(anchor='w',pady=5)
        from tuhoc.ui.theme_config import tuples as theme_list,max_level as level_limit
        for lang,title_lang in [('en','Tiếng Anh'),('vi','Tiếng Việt')]:
            tk.Label(records,text=title_lang,bg='white',fg=PURPLE,font=font_at(13, 'bold')).pack(anchor='w',pady=(12,4))
            subject_dir=self.curriculum.data_dir
            try:
                from tuhoc.lessons.unified_subjects import prepare_subject
                subject_dir=prepare_subject(PROJECT_ROOT,lang,PROJECT_ROOT,legacy_root=self.data_dir)
                themes=theme_list(subject_dir)
            except Exception:themes=[]
            for theme,title_theme,*_ in themes:
                tk.Label(records,text=title_theme,bg='white',fg=INK,font=font_at(11, 'bold')).pack(anchor='w',pady=(7,2))
                row=tk.Frame(records,bg='white');row.pack(fill='x')
                for level in range(1,level_limit(subject_dir,theme)+1):
                    record=self.db.conn.execute('SELECT best_seconds FROM level_time_records WHERE student_id=? AND subject=? AND theme=? AND level=?',(sid,lang,theme,level)).fetchone()
                    text=f'Level {level}\n'+(self._format_elapsed(record[0]) if record else 'Chưa có')
                    tk.Label(row,text=text,bg='#E6F7EF' if record else '#F0F1F4',fg=INK if record else MUTED,font=font_at(9),padx=8,pady=7,justify='center').pack(side='left',padx=3,pady=4)

    def reward_shop(self):
        sid=self.student['id'];body=self.layout('🎁  Cửa hàng phần thưởng')
        balance=self.db.points(sid);self._heading(body,f'Em có {balance} sao. Mua chủ đề / avatar để trang trí hồ sơ!')
        for item,name,cost in [('avatar_fox','🦊 Avatar Cáo',5),('avatar_bear','🐻 Avatar Gấu',10),('theme_space','🚀 Chủ đề Vũ Trụ',15),('theme_ocean','🐬 Chủ đề Đại Dương',20)]:
            row=self._card(body,10);owned=self.db.conn.execute('SELECT 1 FROM rewards WHERE student_id=? AND reward_id=?',(sid,item)).fetchone()
            tk.Label(row,text=f'{name}  —  {cost} ⭐',bg='white',fg=INK,font=font_at(14, 'bold')).pack(side='left')
            def buy(k=item,c=cost):
                if self.db.points(sid)<c:messagebox.showwarning('Chưa đủ sao','Hãy học thêm để tích sao!');return
                with self.db.conn:
                    self.db.conn.execute('INSERT OR IGNORE INTO rewards(student_id,reward_id) VALUES(?,?)',(sid,k))
                    self.db.conn.execute('UPDATE game_points SET points=points-? WHERE student_id=?',(c,sid))
                self.reward_shop()
            b=self.button(row,'Đã sở hữu ✓' if owned else 'Đổi quà',buy);b.pack(side='right');b.config(state='disabled' if owned else 'normal')
    def report_page(self):
        sid=self.student['id'];body=self.layout('📊  Báo cáo phụ huynh / giáo viên')
        from tuhoc.ui.ui_results_dashboard import dashboard
        dashboard(body,self.db,sid,on_retry=self.wrong_answers_page)
        r=self.db.conn.execute('SELECT COUNT(*),COALESCE(SUM(seconds),0),COALESCE(SUM(correct),0),COALESCE(SUM(total),0) FROM learning_sessions WHERE student_id=?',(sid,)).fetchone()
        self._heading(body,f'{r[0]} phiên học  •  {r[1]/60:.1f} phút  •  {r[2]}/{r[3]} câu đúng')
        self.button(body,'📚  Xem lịch sử từng lần làm bài',self.quiz_history_page).pack(anchor='w',pady=(8,12))
        self.button(body,'📈  Xem thống kê tiến độ',self.learning_analytics_page).pack(anchor='w',pady=(0,12))
        self.button(body,'📝  Ôn tập câu trả lời sai',self.wrong_answers_page).pack(anchor='w',pady=(0,12))
        trend_card=self._card(body)
        tk.Label(trend_card,text='TIẾN ĐỘ LUYỆN TẬP · 7 NGÀY GẦN NHẤT',
                 bg='white',fg=INK,font=font_at(14, 'bold')).pack(anchor='w',pady=(0,5))
        tk.Label(trend_card,text='Tỷ lệ câu đúng theo từng ngày có lượt luyện tập (%)',
                 bg='white',fg=MUTED,font=font_at(10)).pack(anchor='w')
        trend_canvas=tk.Canvas(trend_card,width=780,height=230,bg='white',highlightthickness=0)
        trend_canvas.pack(fill='x',pady=(8,5))
        def render_trend(event=None):
            from tuhoc.ui.ui_line_dot import draw_line_dot
            import datetime
            days=[datetime.date.today()-datetime.timedelta(days=6-i) for i in range(7)]
            rows=self.db.conn.execute('SELECT started,correct,total FROM learning_sessions WHERE student_id=?',(sid,)).fetchall()
            totals={day.isoformat():[0,0] for day in days}
            for started,correct,total in rows:
                try:day=datetime.datetime.fromtimestamp(float(started)).date().isoformat()
                except (ValueError,TypeError,OverflowError,OSError):continue
                if day in totals:
                    totals[day][0]+=int(correct or 0);totals[day][1]+=int(total or 0)
            vals=[100*totals[d.isoformat()][0]/totals[d.isoformat()][1] if totals[d.isoformat()][1] else 0 for d in days]
            draw_line_dot(trend_canvas,vals,[d.strftime('%d/%m') for d in days])
        trend_canvas.bind('<Configure>',render_trend)
        trend_canvas.after_idle(render_trend)
        for item in self.db.conn.execute('SELECT word,wrong,correct FROM word_mastery WHERE student_id=? ORDER BY wrong DESC LIMIT 15',(sid,)):
            tk.Label(body,text=f'• {item[0]}: sai {item[1]} / đúng {item[2]}',bg=body['bg'],fg=INK).pack(anchor='w',pady=3)
        def export():
            path=filedialog.asksaveasfilename(defaultextension='.xlsx',filetypes=[('Excel','.xlsx')])
            if path:
                try:self.learning.export_report(sid,path);messagebox.showinfo('Đã xuất Excel',path)
                except Exception as exc:messagebox.showerror('Lỗi',str(exc))
        def pdf():
            path=filedialog.asksaveasfilename(defaultextension='.pdf',filetypes=[('PDF','.pdf')]);
            if not path:return
            try:
                from reportlab.pdfgen import canvas
                from reportlab.pdfbase import pdfmetrics
                from reportlab.pdfbase.ttfonts import TTFont
                font=next((x for x in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','C:/Windows/Fonts/arial.ttf'] if Path(x).exists()),None)
                if font:pdfmetrics.registerFont(TTFont('ReportFont',font))
                p=canvas.Canvas(path);p.setFont('ReportFont' if font else 'Helvetica',15);p.drawString(45,780,'BAO CAO HOC TAP');p.setFont('ReportFont' if font else 'Helvetica',11)
                for i,line in enumerate([f'So phien: {r[0]}',f'Tong phut: {r[1]/60:.1f}',f'Cau dung: {r[2]}/{r[3]}']):p.drawString(45,740-i*24,line)
                p.save();messagebox.showinfo('Đã xuất PDF',path)
            except Exception as exc:messagebox.showerror('Lỗi xuất PDF',str(exc))
        self.action_button(body,'⬇ XUẤT EXCEL',export).pack(anchor='w',pady=8)
        self.action_button(body,'⬇ XUẤT PDF',pdf).pack(anchor='w',pady=8)
    def content_errors(self):
        body=self.layout('⚠  Kiểm tra nội dung')
        for err in self.curriculum.errors:tk.Label(body,text='• '+err,bg=BG,fg='#BA3F54',wraplength=850,justify='left').pack(anchor='w',pady=4)
    def level_import_ui(self):
        path=filedialog.askopenfilename(filetypes=[('Excel','*.xlsx')])
        if not path:return
        try:ok,report=self.learning.import_merge(path)
        except Exception as exc:messagebox.showerror('Lỗi nhập Excel',str(exc));return
        (messagebox.showinfo if ok else messagebox.showerror)('Nhập Excel theo ID','\n'.join(report[:30]));self.manage_levels()
