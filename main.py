"""Tu Hoc v1.0 - offline desktop prototype (Python standard library)."""
from ui_tokens import COLORS as TOKEN_COLORS, font_at, set_font_scale
import json
import os
import sqlite3
import sys
import time
import unicodedata
import wave
import tempfile
import traceback
import datetime
import array
import math
import webbrowser
from pathlib import Path
from learning_audio import LearningAudio
from waveform_player import WaveformPlayer
import tkinter as tk
from tkinter import ttk, messagebox
import ui_dialogs as dialogs

# Python 3.13: Tcl callbacks can fire during widget teardown after the
# associated command list has already been cleared.
_original_tk_deletecommand = tk.Misc.deletecommand
def _safe_tk_deletecommand(self, name):
    if getattr(self, '_tclCommands', None) is None:
        return
    try:
        return _original_tk_deletecommand(self, name)
    except tk.TclError:
        return
tk.Misc.deletecommand = _safe_tk_deletecommand
from recording_tools import RecordingSession, recording_folder, microphone_choices, resolve_microphone
from mouse_effects import MouseEffects
from floating_vocabulary import FloatingVocabulary
from ui_shell import AppShell
from ui_components import Toast
from profile_ui import ProfilePage
from ui_grid import UIGrid
from minigames import MiniGamesMixin
from modern_games import ModernGamesMixin
from lesson_flow import LessonFlowMixin
from upgrade_v2 import GameAppMixin
from dictation_vi import DictationMixin
from level_flow import LevelFlowMixin
from wheel_scroll import install_wheel_scroll
from drag_scroll import install_drag_scroll
from ui_motion import animate_position, add_hover
from panel_animations import animate_magnetic_cascade, animate_reverse_cascade_left
from icon_animations import micro_rotation
from content_manager import ContentManager, read_custom_lessons, user_content_dir
from navigation_profiler import install as install_navigation_profiler, record as navigation_record

BASE = Path(__file__).resolve().parent
CONTENT = BASE / 'content_library' / 'vi_VN_south'
if not CONTENT.exists() and getattr(sys, 'frozen', False):
    CONTENT = Path(sys.executable).resolve().parent / 'content_library' / 'vi_VN_south'
import shutil as _runtime_shutil
DATA = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / 'AppData' / 'Local')) / 'TuHocBeta'
DATA.mkdir(parents=True, exist_ok=True)
# New installations create a clean database through Storage().
# Never import the developer's testing database into a user's profile.
if not (DATA / 'content_library').exists() and (BASE / 'content_library').is_dir():
    _runtime_shutil.copytree(BASE / 'content_library', DATA / 'content_library')
DB = DATA / 'tu_hoc.sqlite3' 
AVATAR_OPTIONS = [('👤', 'Mặc định', 0), ('🐱', 'Mèo', 1), ('🐼', 'Gấu trúc', 2), ('🦊', 'Cáo', 3), ('🐸', 'Ếch', 4), ('🐰', 'Thỏ', 2), ('🐻', 'Gấu', 3), ('🐨', 'Koala', 3), ('🐯', 'Hổ', 4), ('🦁', 'Sư tử', 4), ('🐧', 'Chim cánh cụt', 4), ('🦄', 'Kỳ lân', 5), ('🐲', 'Rồng', 7), ('👑', 'Vương miện', 8), ('🚀', 'Tên lửa', 6), ('🌈', 'Cầu vồng', 5), ('🌟', 'Ngôi sao', 5)]
GREEN, DARK, PALE, YELLOW, BG = '#39865B', '#285D40', '#E2F0E2', '#F9E9AC', TOKEN_COLORS['background']


def normalize(text):
    from review_normalize import normalize as shared_normalize
    return shared_normalize(text)


ACHIEVEMENTS_FILE = DATA / 'level_achievements.json'
# A default quest is available for every configured theme and level.
# Existing user-edited achievements are preserved by the loader.
DEFAULT_QUEST_TIERS = ((1, 10, 1), (2, 20, 3), (3, 50, 10))
DEFAULT_LEVEL_ACHIEVEMENTS = []  # Generated from live curriculum, not a fixed five-theme list.

def load_level_achievements():
    try:
        rows=json.loads(ACHIEVEMENTS_FILE.read_text(encoding='utf-8')) if ACHIEVEMENTS_FILE.exists() else []
        return [r for r in rows if isinstance(r,dict) and all(k in r for k in ('id','theme','level','required','max_seconds','gems'))]
    except (OSError,ValueError,TypeError):return []

def lesson_quest_defaults(theme, level, lesson):
    return [{'id':f'lesson_v2_{theme}_{level}_{lesson}_tier_{tier}',
             'theme':theme,'level':level,'lesson':lesson,
             'title':f'Level {level} · Lesson {lesson} · Cấp {tier}',
             'required':required,'max_seconds':15,'gems':gems}
            for tier,required,gems in DEFAULT_QUEST_TIERS]


def save_level_achievements(items):
    ACHIEVEMENTS_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')


class Storage:
    def __init__(self, path=DB):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript('''
            CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY, name TEXT NOT NULL, grade INTEGER NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS attempts (id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, exercise_id TEXT NOT NULL, exercise_type TEXT NOT NULL, content_version TEXT NOT NULL, correct INTEGER, seconds REAL NOT NULL, answer TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS vocabulary (id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, word TEXT NOT NULL, meaning TEXT NOT NULL, due_at REAL NOT NULL, interval_days INTEGER NOT NULL DEFAULT 0, repetitions INTEGER NOT NULL DEFAULT 0, lapses INTEGER NOT NULL DEFAULT 0, UNIQUE(student_id, word));
            CREATE TABLE IF NOT EXISTS game_points (student_id INTEGER PRIMARY KEY, points INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, vocabulary_id INTEGER NOT NULL, rating TEXT NOT NULL, reviewed_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS completion_events (id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, activity_type TEXT NOT NULL, activity_id TEXT NOT NULL, correct INTEGER NOT NULL, total INTEGER NOT NULL, perfect INTEGER NOT NULL, seconds REAL NOT NULL DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS achievement_claims (student_id INTEGER NOT NULL, achievement_id TEXT NOT NULL, gems INTEGER NOT NULL, claimed_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(student_id,achievement_id));
            CREATE TABLE IF NOT EXISTS quest_notification_reads (student_id INTEGER NOT NULL, achievement_id TEXT NOT NULL, read_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(student_id,achievement_id));
            CREATE TABLE IF NOT EXISTS avatar_purchases (student_id INTEGER NOT NULL, avatar TEXT NOT NULL, price INTEGER NOT NULL, purchased_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(student_id,avatar));
            CREATE TABLE IF NOT EXISTS avatar_selection (student_id INTEGER PRIMARY KEY, avatar TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS vocabulary_deck_names (student_id INTEGER NOT NULL, source_type TEXT NOT NULL, theme TEXT NOT NULL DEFAULT '', level INTEGER NOT NULL DEFAULT 0, source_title TEXT NOT NULL DEFAULT '', display_name TEXT NOT NULL, PRIMARY KEY(student_id,source_type,theme,level,source_title));
            CREATE TABLE IF NOT EXISTS vocabulary_sources (student_id INTEGER NOT NULL, vocabulary_id INTEGER NOT NULL, source_type TEXT NOT NULL, theme TEXT NOT NULL DEFAULT '', level INTEGER NOT NULL DEFAULT 0, source_title TEXT NOT NULL DEFAULT '', PRIMARY KEY(student_id,vocabulary_id,source_type,theme,level,source_title));
        ''')
        self.conn.executescript('''
            CREATE TABLE IF NOT EXISTS lesson_progress (student_id INTEGER NOT NULL, topic_id TEXT NOT NULL, correct INTEGER NOT NULL, total INTEGER NOT NULL, completed INTEGER NOT NULL DEFAULT 0, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(student_id,topic_id));
        ''')
        self.conn.commit()

    def save_lesson_progress(self,student,topic,correct,total,completed):
        with self.conn:
            if completed:
                self.conn.execute('INSERT INTO completion_events(student_id,activity_type,activity_id,correct,total,perfect) VALUES(?,?,?,?,?,?)',(student,'lesson',str(topic),correct,total,int(total>0 and correct==total)))
            self.conn.execute("INSERT INTO lesson_progress(student_id,topic_id,correct,total,completed) VALUES(?,?,?,?,?) ON CONFLICT(student_id,topic_id) DO UPDATE SET correct=excluded.correct,total=excluded.total,completed=MAX(lesson_progress.completed,excluded.completed),updated_at=CURRENT_TIMESTAMP",(student,topic,correct,total,int(completed)))

    def lesson_completed(self,student,topic):
        row=self.conn.execute('SELECT completed FROM lesson_progress WHERE student_id=? AND topic_id=?',(student,topic)).fetchone()
        return bool(row and row['completed'])

    def lesson_progress(self,student):
        return self.conn.execute('SELECT * FROM lesson_progress WHERE student_id=?',(student,)).fetchall()

    def completion_summary(self,student):
        row=self.conn.execute('SELECT COUNT(*) completed, COALESCE(SUM(perfect),0) perfect, COALESCE(MIN(CASE WHEN seconds>0 THEN seconds END),0) best_seconds FROM completion_events WHERE student_id=?',(student,)).fetchone()
        return dict(row)

    def gems(self,student):
        row=self.conn.execute('SELECT COALESCE(SUM(gems),0) FROM achievement_claims WHERE student_id=?',(student,)).fetchone()
        spent=self.conn.execute('SELECT COALESCE(SUM(price),0) FROM avatar_purchases WHERE student_id=?',(student,)).fetchone()[0]
        return max(0,int(row[0] or 0)-int(spent or 0))

    def selected_avatar(self,student):
        row=self.conn.execute('SELECT avatar FROM avatar_selection WHERE student_id=?',(student,)).fetchone()
        value=row['avatar'] if row else '👤'
        return value if any(value==item[0] for item in AVATAR_OPTIONS) else '👤'

    def owned_avatars(self,student):
        rows=self.conn.execute('SELECT avatar FROM avatar_purchases WHERE student_id=?',(student,)).fetchall()
        return {'👤'} | {row['avatar'] for row in rows}

    def buy_or_select_avatar(self,student,avatar):
        """Returns (success, message); purchase and selection are one transaction."""
        option=next((item for item in AVATAR_OPTIONS if item[0]==avatar),None)
        if option is None:return False,'Biểu tượng không hợp lệ.'
        price=option[2]
        with self.conn:
            owned=self.conn.execute('SELECT 1 FROM avatar_purchases WHERE student_id=? AND avatar=?',(student,avatar)).fetchone()
            if avatar!='👤' and not owned:
                if self.gems(student)<price:return False,'Bạn chưa đủ ngọc để mở khóa biểu tượng này.'
                self.conn.execute('INSERT INTO avatar_purchases(student_id,avatar,price) VALUES(?,?,?)',(student,avatar,price))
            self.conn.execute('INSERT INTO avatar_selection(student_id,avatar) VALUES(?,?) ON CONFLICT(student_id) DO UPDATE SET avatar=excluded.avatar',(student,avatar))
        return True,'Đã thay đổi biểu tượng tài khoản!'

    def claim_achievement(self,student,key,required):
        count=self.conn.execute('SELECT COUNT(*) FROM completion_events WHERE student_id=? AND activity_type=?',(student,'lesson')).fetchone()[0]
        if count<required:return False
        with self.conn:
            result=self.conn.execute('INSERT OR IGNORE INTO achievement_claims(student_id,achievement_id,gems) VALUES(?,?,1)',(student,key))
        return result.rowcount>0

    def level_achievement_count(self,student,theme,level,max_seconds,lesson=None):
        if lesson is None:
            key=f'{theme}:{int(level)}'
            row=self.conn.execute("""SELECT COUNT(*) FROM completion_events WHERE student_id=?
                AND activity_type='level' AND activity_id=? AND perfect=1
                AND seconds>0 AND seconds<?""",(student,key,float(max_seconds))).fetchone()
        else:
            key=f'{theme}:{int(level)}:{int(lesson)}'
            row=self.conn.execute("""SELECT COUNT(*) FROM completion_events WHERE student_id=?
                AND activity_type='lesson_level' AND activity_id=? AND perfect=1
                AND seconds>0 AND seconds<?""",(student,key,float(max_seconds))).fetchone()
        return int(row[0] or 0)

    def record_lesson_completion(self,student,theme,level,lesson,correct,total,seconds=0):
        key=f'{theme}:{int(level)}:{int(lesson)}'
        with self.conn:
            self.conn.execute("""INSERT INTO completion_events(student_id,activity_type,activity_id,correct,total,perfect,seconds)
                VALUES(?,?,?,?,?,?,?)""",(student,'lesson_level',key,correct,total,int(total>0 and correct==total),max(0,seconds)))
            self.conn.execute("""INSERT INTO lesson_progress(student_id,topic_id,correct,total,completed)
                VALUES(?,?,?,?,1) ON CONFLICT(student_id,topic_id) DO UPDATE SET
                correct=excluded.correct,total=excluded.total,completed=1,updated_at=CURRENT_TIMESTAMP""",
                (student,key,correct,total))

    def lesson_stats(self,student,theme=None):
        rows=self.conn.execute("""SELECT activity_id,COUNT(*) attempts,
            SUM(perfect) perfect, MIN(CASE WHEN seconds>0 THEN seconds END) best_seconds
            FROM completion_events WHERE student_id=? AND activity_type='lesson_level'
            GROUP BY activity_id""",(student,)).fetchall()
        result={}
        for row in rows:
            parts=row['activity_id'].rsplit(':',2)
            if len(parts)!=3:continue
            t,l,n=parts
            if theme is not None and t!=theme:continue
            result[(t,int(l),int(n))]=dict(row)
        return result

    def claim_level_achievement(self, student, achievement):
        count = self.level_achievement_count(student, achievement['theme'], achievement['level'], achievement['max_seconds'],achievement.get('lesson'))
        if count < int(achievement['required']): return False
        with self.conn:
            cur = self.conn.execute('INSERT OR IGNORE INTO achievement_claims(student_id,achievement_id,gems) VALUES(?,?,?)',
                                    (student, achievement['id'], int(achievement['gems'])))
        return cur.rowcount == 1

    def rename_student(self, student, name):
        name = name.strip()
        if not name or len(name)>80: raise ValueError('Tên phải có từ 1 đến 80 ký tự.')
        with self.conn:
            self.conn.execute('UPDATE students SET name=? WHERE id=?',(name,student))

    def record_level_completion(self,student,level_id,correct,total,seconds=0):
        """Integration point for level engine: call only on an actual finished level."""
        with self.conn:
            self.conn.execute('INSERT INTO completion_events(student_id,activity_type,activity_id,correct,total,perfect,seconds) VALUES(?,?,?,?,?,?,?)',(student,'level',str(level_id),correct,total,int(total>0 and correct==total),max(0,seconds)))

    def points(self, student):
        row=self.conn.execute("SELECT points FROM game_points WHERE student_id=?", (student,)).fetchone()
        return row[0] if row else 0

    def add_points(self, student, amount=1):
        with self.conn:
            self.conn.execute("INSERT INTO game_points(student_id, points) VALUES(?,?) ON CONFLICT(student_id) DO UPDATE SET points=points+excluded.points", (student, amount))

    def students(self):
        return self.conn.execute('SELECT * FROM students ORDER BY id').fetchall()

    def add_student(self, name, grade):
        with self.conn:
            cur = self.conn.execute('INSERT INTO students(name,grade) VALUES(?,?)', (name, grade))
        return cur.lastrowid

    def delete_student(self, student_id):
        """Remove exactly one profile and its dependent learning records atomically."""
        sid = int(student_id)
        if not self.conn.execute('SELECT 1 FROM students WHERE id=?', (sid,)).fetchone():
            return False
        with self.conn:
            # Delete reviews first: they refer to vocabulary rows.
            for table in ('reviews', 'attempts', 'vocabulary', 'game_points',
                          'lesson_progress', 'level_scores', 'word_mastery',
                          'rewards', 'learning_sessions', 'completion_events', 'achievement_claims',
                          'avatar_purchases', 'avatar_selection', 'vocabulary_sources', 'vocabulary_deck_names', 'quest_notification_reads'):
                if self.conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                    self.conn.execute(f'DELETE FROM {table} WHERE student_id=?', (sid,))
            self.conn.execute('DELETE FROM students WHERE id=?', (sid,))
        return True

    def record(self, student, ex, correct, seconds, answer):
        with self.conn:
            self.conn.execute('INSERT INTO attempts(student_id,exercise_id,exercise_type,content_version,correct,seconds,answer) VALUES(?,?,?,?,?,?,?)', (student, ex['id'], ex['type'], ex.get('version','1.0'), correct, max(0,seconds), answer))

    def stats(self, student):
        return self.conn.execute('SELECT exercise_type,COUNT(*) total,SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END) correct,SUM(CASE WHEN correct=0 THEN 1 ELSE 0 END) wrong,ROUND(SUM(seconds)/60.0,1) minutes FROM attempts WHERE student_id=? GROUP BY exercise_type', (student,)).fetchall()

    def save_word(self, student, word, meaning):
        with self.conn:
            self.conn.execute('INSERT OR IGNORE INTO vocabulary(student_id,word,meaning,due_at) VALUES(?,?,?,?)', (student, word, meaning, time.time()))

    def save_word_in_source(self, student, word, meaning, source_type='manual', theme='', level=0, source_title=''):
        """Keep spaced-repetition history intact; one word can belong to many lessons."""
        self.save_word(student, word, meaning)
        with self.conn:
            row=self.conn.execute('SELECT id FROM vocabulary WHERE student_id=? AND word=?',(student,word)).fetchone()
            if row:
                self.conn.execute('INSERT OR IGNORE INTO vocabulary_sources(student_id,vocabulary_id,source_type,theme,level,source_title) VALUES(?,?,?,?,?,?)',
                                  (student,row['id'],str(source_type),str(theme),int(level),str(source_title)))
        return row['id'] if row else None

    def vocabulary_groups(self, student):
        return self.conn.execute("""SELECT s.source_type,s.theme,s.level,s.source_title,
            COUNT(DISTINCT s.vocabulary_id) AS total,
            SUM(CASE WHEN v.due_at<=? THEN 1 ELSE 0 END) AS due
            FROM vocabulary_sources s JOIN vocabulary v ON v.id=s.vocabulary_id AND v.student_id=s.student_id
            WHERE s.student_id=? GROUP BY s.source_type,s.theme,s.level,s.source_title
            ORDER BY CASE s.source_type WHEN 'lesson' THEN 0 WHEN 'reading' THEN 1 ELSE 2 END,
            s.theme,s.level,s.source_title""",(time.time(),student)).fetchall()

    def deck_custom_name(self, student, group):
        row=self.conn.execute("""SELECT display_name FROM vocabulary_deck_names WHERE
            student_id=? AND source_type=? AND theme=? AND level=? AND source_title=?""",
            (student,group['source_type'],group['theme'],int(group['level']),group['source_title'])).fetchone()
        return row['display_name'] if row else None

    def rename_deck(self, student, group, name):
        name=name.strip()
        if not name or len(name)>100:raise ValueError('Tên bộ thẻ phải có từ 1 đến 100 ký tự.')
        with self.conn:
            self.conn.execute("""INSERT INTO vocabulary_deck_names
                (student_id,source_type,theme,level,source_title,display_name) VALUES(?,?,?,?,?,?)
                ON CONFLICT(student_id,source_type,theme,level,source_title)
                DO UPDATE SET display_name=excluded.display_name""",
                (student,group['source_type'],group['theme'],int(group['level']),group['source_title'],name))

    def delete_deck(self, student, group):
        key=(student,group['source_type'],group['theme'],int(group['level']),group['source_title'])
        with self.conn:
            self.conn.execute("""DELETE FROM vocabulary_sources WHERE student_id=?
                AND source_type=? AND theme=? AND level=? AND source_title=?""",key)
            self.conn.execute("""DELETE FROM vocabulary_deck_names WHERE student_id=?
                AND source_type=? AND theme=? AND level=? AND source_title=?""",key)
            # Delete cards only when they are not present in any other deck.
            orphan=self.conn.execute("""SELECT id FROM vocabulary WHERE student_id=? AND NOT EXISTS
                (SELECT 1 FROM vocabulary_sources s WHERE s.student_id=vocabulary.student_id
                 AND s.vocabulary_id=vocabulary.id)""",(student,)).fetchall()
            # Unlinked legacy cards must remain intact. No automatic global deletion.
        return len(orphan)

    def words_in_source(self,student,source_type,theme='',level=0,source_title='',due=False):
        query="""SELECT v.* FROM vocabulary v JOIN vocabulary_sources s ON s.vocabulary_id=v.id
            AND s.student_id=v.student_id WHERE v.student_id=? AND s.source_type=?
            AND s.theme=? AND s.level=? AND s.source_title=?"""
        args=[student,source_type,theme,int(level),source_title]
        if due:query+=' AND v.due_at<=?';args.append(time.time())
        return self.conn.execute(query+' ORDER BY v.word',args).fetchall()

    def words(self, student, due=False):
        q = 'SELECT * FROM vocabulary WHERE student_id=?'
        if due: q += ' AND due_at<=?'
        q += ' ORDER BY due_at,word'
        return self.conn.execute(q, (student, time.time()) if due else (student,)).fetchall()

    def review(self, student, word_id, rating):
        word = self.conn.execute('SELECT * FROM vocabulary WHERE id=? AND student_id=?',(word_id,student)).fetchone()
        if not word: return
        if rating == 'again':
            days, reps, lapses = 0, 0, word['lapses']+1
            due = time.time()+10*60
        else:
            reps, lapses = word['repetitions']+1, word['lapses']
            days = max(1, (word['interval_days'] or 1) * (2 if rating == 'good' else 1))
            due = time.time()+days*86400
        with self.conn:
            self.conn.execute('UPDATE vocabulary SET due_at=?,interval_days=?,repetitions=?,lapses=? WHERE id=?',(due,days,reps,lapses,word_id))
            self.conn.execute('INSERT INTO reviews(student_id,vocabulary_id,rating,reviewed_at) VALUES(?,?,?,?)',(student,word_id,rating,time.time()))


def load_content():
    exercises = []
    for p in sorted(CONTENT.rglob('*.json')):
        try:
            data = json.loads(p.read_text(encoding='utf-8-sig'))
        except (OSError, json.JSONDecodeError) as err:
            print(f'[Nội dung] Không đọc được {p}: {err}', file=sys.stderr)
            continue
        if not isinstance(data,dict) or not isinstance(data.get('exercises'),list): continue
        for ex in data['exercises']:
            if all(k in ex for k in ('id','type','title','prompt')):
                ex = dict(ex)
                ex['version'] = data.get('version','1.0')
                exercises.append(ex)
    return exercises


class Audio:
    def __init__(self):
        self.temp = None

    def play(self, filename, speed, volume):
        if sys.platform != 'win32':
            messagebox.showinfo('Âm thanh', 'Bản chạy thử phát WAV bằng winsound trên Windows.'); return
        import winsound
        path = Path(filename).resolve()
        roots=[CONTENT.resolve(),user_content_dir(DATA).resolve()]
        if not any(path.is_relative_to(root) for root in roots) or not path.exists():
            messagebox.showwarning('Thiếu âm thanh','Chưa có file WAV cho bài học này. Hãy thêm file vào kho nội dung.'); return
        try:
            with wave.open(str(path),'rb') as src:
                channels, width, rate, frames = src.getnchannels(),src.getsampwidth(),src.getframerate(),src.getnframes()
                raw=src.readframes(frames)
            if width != 2:
                messagebox.showwarning('Định dạng','Audio WAV phải là PCM 16-bit.'); return
            samples=array.array('h'); samples.frombytes(raw)
            if sys.byteorder!='little': samples.byteswap()
            # Resampling by linear interpolation; changes both playback speed and pitch.
            nframes=len(samples)//channels
            out=array.array('h')
            for j in range(max(1,int(nframes/speed))):
                position=j*speed; a=min(int(position),nframes-1); b=min(a+1,nframes-1); f=position-a
                for ch in range(channels):
                    v=(samples[a*channels+ch]*(1-f)+samples[b*channels+ch]*f)*volume
                    out.append(max(-32768,min(32767,round(v))))
            if sys.byteorder!='little': out.byteswap()
            if self.temp and Path(self.temp).exists():
                try: Path(self.temp).unlink()
                except OSError: pass
            with tempfile.NamedTemporaryFile(suffix='.wav',delete=False) as tmp: self.temp=tmp.name
            with wave.open(self.temp,'wb') as dst:
                dst.setnchannels(channels); dst.setsampwidth(2); dst.setframerate(rate); dst.writeframes(out.tobytes())
            winsound.PlaySound(None,winsound.SND_PURGE)
            winsound.PlaySound(self.temp,winsound.SND_FILENAME|winsound.SND_ASYNC)
        except (OSError,wave.Error,ValueError) as exc:
            messagebox.showerror('Lỗi audio',str(exc))

    def stop(self):
        if sys.platform=='win32':
            import winsound
            winsound.PlaySound(None,winsound.SND_PURGE)


class TeachingTooltip:
    """Delayed, screen-clamped tooltip; no permanent window or global bindings."""
    def __init__(self, widget, title, shortcut='', detail=''):
        self.widget, self.title, self.shortcut, self.detail = widget, title, shortcut, detail
        self.pending = None
        self.popup = None
        widget.bind('<Enter>', self.schedule, add='+')
        widget.bind('<Leave>', self.hide, add='+')
        widget.bind('<ButtonPress>', self.hide, add='+')
        widget.bind('<Destroy>', self.hide, add='+')
    def schedule(self, event=None):
        self.hide()
        try: self.pending = self.widget.after(550, self.show)
        except tk.TclError: pass
    def show(self):
        self.pending = None
        try:
            if not self.widget.winfo_exists(): return
            popup = tk.Toplevel(self.widget)
            popup.wm_overrideredirect(True)
            try: popup.attributes('-topmost', True)
            except tk.TclError: pass
            frame = tk.Frame(popup, bg='#173D2C', padx=11, pady=8, bd=1, relief='solid')
            frame.pack()
            tk.Label(frame, text=self.title, bg='#173D2C', fg='white', font=font_at(10, 'bold')).pack(anchor='w')
            if self.shortcut:
                tk.Label(frame, text=''+self.shortcut, bg='#173D2C', fg='#C8F5D5', font=font_at(9)).pack(anchor='w')
            if self.detail:
                tk.Label(frame, text=self.detail, bg='#173D2C', fg='white', font=font_at(9), wraplength=280, justify='left').pack(anchor='w')
            popup.update_idletasks()
            root = self.widget.winfo_toplevel()
            left, top = root.winfo_rootx(), root.winfo_rooty()
            right = min(left + root.winfo_width(), popup.winfo_screenwidth())
            bottom = min(top + root.winfo_height(), popup.winfo_screenheight())
            width, height = popup.winfo_reqwidth(), popup.winfo_reqheight()
            x = max(left + 6, min(self.widget.winfo_rootx(), right - width - 6))
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
            if y + height > bottom - 6: y = self.widget.winfo_rooty() - height - 6
            y = max(top + 6, min(y, bottom - height - 6))
            popup.geometry(f'+{int(x)}+{int(y)}')
            self.popup = popup
        except tk.TclError: self.popup = None
    def hide(self, event=None):
        if self.pending is not None:
            try: self.widget.after_cancel(self.pending)
            except tk.TclError: pass
            self.pending = None
        if self.popup is not None:
            try: self.popup.destroy()
            except tk.TclError: pass
            self.popup = None


class App(ModernGamesMixin, DictationMixin, GameAppMixin, LevelFlowMixin, LessonFlowMixin, ContentManager, MiniGamesMixin, tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Dev by HiHieu (Beta)'); self.geometry('1140x780'); self.minsize(850,590)
        self._load_application_logo()
        # Windows: maximized (not borderless fullscreen); other systems use screen dimensions.
        try:
            self.state('zoomed')
        except tk.TclError:
            try: self.attributes('-zoomed', True)
            except tk.TclError: self.geometry(f'{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0')
        self.configure(bg=BG)
        self.data_dir=DATA; self.db=Storage(); self.exercises=self.reload_exercises(); self.student=None; self.started=0; self.audio=Audio();self.learning_audio=LearningAudio();self.mouse_effects=MouseEffects(self)
        self.style=ttk.Style(self); self.style.theme_use('clam')
        self.style.configure('TButton',font=font_at(11),padding=8)
        self.style.configure('TCombobox',font=font_at(11))
        self.option_add('*Font', font_at(11))
        self._shell = None
        self._navigation_history = []
        self._navigation_current = None
        self._navigation_busy = False
        self._sidebar_slide_direction = 0
        self._sidebar_slide_job = None
        self.bind_all("<Alt-Left>", self._navigation_back_key, add="+")
        self.recording_session = None
        self.recording_busy = False
        self.setup_upgrade()
        self.apply_font_preferences()
        self.ui_grid = UIGrid(self)
        install_wheel_scroll(self)
        install_drag_scroll(self)
        self.bind_all('<KeyPress>',self._teaching_key,add='+')
        self._usage_last_tick=time.monotonic()
        self._usage_account=None
        self._usage_pending_seconds=0.0
        self._usage_pending_student=None
        self._usage_pending_day=None
        self.after(1000,self._time_heartbeat)
        self.protocol("WM_DELETE_WINDOW", self._shutdown_app)
        self.show_profiles()

    def apply_font_preferences(self):
        set_font_scale(self._display_settings.get('ui_font_scale','medium'))
        self.option_add('*Font',font_at(11))
        self.style.configure('TButton',font=font_at(11))
        self.style.configure('TCombobox',font=font_at(11))

    def _stop_reading_tts(self):
        """Stop every speech subprocess started by this application."""
        processes = getattr(self, '_reading_tts_processes', [])
        self._reading_tts_processes = []
        for proc in processes:
            try:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=0.7)
                    except __import__('subprocess').TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=0.7)
            except (OSError, ValueError, __import__('subprocess').TimeoutExpired):
                pass

    def _shutdown_app(self):
        """Idempotent shutdown: cancel Tk jobs before releasing media resources."""
        if getattr(self, '_phase5_shutting_down', False):
            return
        self._phase5_shutting_down = True
        # Scheduled animations and navigation callbacks must not touch widgets
        # after root.destroy(). Cancel only known application-owned jobs.
        for name in (
            '_page_transition_job', '_page_reveal_job', '_drawer_animation_job', '_sidebar_slide_job',
            '_donate_panel_job', '_account_animation_job', '_account_close_job',
            '_notification_animation_job', '_v8_dock_job',
        ):
            job = getattr(self, name, None)
            if job is not None:
                try:
                    self.after_cancel(job)
                except (tk.TclError, RuntimeError, ValueError):
                    pass
                setattr(self, name, None)
        # Tear down the Reading Toplevel before the root window; otherwise
        # pending button and canvas events can target destroyed Tk commands.
        pending=getattr(self,'_reading_close_job',None)
        if pending is not None:
            try:self.after_cancel(pending)
            except (tk.TclError,ValueError):pass
            self._reading_close_job=None
        if getattr(self,'_reading_focus_active',False):
            self._finish_reading_focus()
        self._stop_reading_tts()
        # Ask the SDL exercise worker to exit its active question immediately.
        # Do not call pygame.quit() from Tk: SDL display belongs to the worker.
        try:
            import pygame_exercises
            pygame_exercises.close(self)
        except Exception:
            import logging
            logging.getLogger(__name__).exception('Pygame exercise shutdown failed')
        try:
            self._flush_usage_time()
        except Exception:
            import logging
            logging.getLogger(__name__).exception('Final usage flush failed')
        # Stop each playback backend before destroying Tk. LearningAudio
        # exposes stop(), not close(); the old call raised AttributeError and
        # silently left the learning MP3/WAV playback running until exit.
        for player_name in ('learning_audio', 'audio', 'dictation_audio'):
            player = getattr(self, player_name, None)
            if player is not None:
                try:
                    player.stop()
                except Exception:
                    import logging
                    logging.getLogger(__name__).exception(
                        'Audio shutdown failed for %s', player_name)
        # Wait without nested Tk update() calls or blocking the UI thread.
        import pygame_session_guard as guard
        guard.request_shutdown()
        deadline = time.monotonic() + 2.0
        def finish_when_idle():
            if not guard.active() or time.monotonic() >= deadline:
                self.destroy()
            else:
                self.after(40, finish_when_idle)
        finish_when_idle()

    def _measure_page_transition(self, origin, destination, direction, started):
        """Log transition duration after Tk has processed pending idle layout work."""
        def finished():
            elapsed = (time.perf_counter() - started) * 1000
            navigation_record(destination, 'page_transition', elapsed,
                              f'direction={direction} from={origin!r} to={destination!r}')
        try:
            self.after_idle(finished)
        except (tk.TclError, RuntimeError):
            finished()

    @staticmethod
    def _page_callback_name(callback):
        return getattr(callback, '__name__', type(callback).__name__) if callback else 'none'

    def _navigate_to(self, callback, *, replace=False):
        """Navigate with bounded history; avoid repeated clicks and duplicate entries."""
        if getattr(self, '_phase5_shutting_down', False) or self._navigation_busy:
            return
        current = self._navigation_current
        target = getattr(callback, '__func__', callback)
        # Pygame exam is a transient window, NOT a Tkinter page. Repeated
        # clicks must invoke it again even when the sidebar item is unchanged.
        # Do not store it in page history or mark it as the current page.
        #if getattr(target, '__name__', '') == 'exam_page':
        if getattr(target, '__name__', '') in ('exam_page', 'exam_bank_editor'):
            callback()
            return
        # The page may have changed through a direct callback (lesson detail, quiz).
        # Never suppress an explicit menu request based only on stale history.
        if current is not None and getattr(current, '__func__', current) is target:
            if getattr(self, '_admin_page', None) == getattr(self, '_navigation_page_title', None):
                return
        self._sidebar_slide_direction = self._sidebar_navigation_direction(current, callback)
        self._navigation_busy = True
        started = time.perf_counter()
        origin = self._page_callback_name(current)
        destination = self._page_callback_name(callback)
        try:
            callback()
            self._start_sidebar_slide()
            if current is not None and not replace:
                self._navigation_history.append(current)
                self._navigation_history = self._navigation_history[-30:]
            self._navigation_current = callback
            self._navigation_page_title = getattr(self, '_admin_page', None)
            self._measure_page_transition(origin, destination, 'forward', started)
        except Exception:
            # Preserve the previous navigation state if the target fails to render.
            navigation_record(destination, 'navigation_error', (time.perf_counter() - started) * 1000,
                              f'direction=forward from={origin!r} to={destination!r}')
            raise
        finally:
            try:
                self.after(180, self._navigation_unlock)
            except (tk.TclError, RuntimeError):
                self._navigation_unlock()

    def _sidebar_navigation_direction(self, previous, destination):
        """+1: destination lower in sidebar (slide up); -1: higher (slide down)."""
        try:
            from ui_shell import NAV
            order = {name: i for i, (_icon, _label, name) in enumerate(NAV)}
            a = order.get(getattr(previous, '__name__', ''))
            b = order.get(getattr(destination, '__name__', ''))
            if a is None or b is None or a == b:
                return 0
            return 1 if b > a else -1
        except Exception:
            return 0

    def _start_sidebar_slide(self):
        """Slide page body without moving the scroll region during animation.

        The old implementation recomputed the scrollregion while the canvas
        window was offset. On short pages this made the scrollbar and the
        window fight each other, resulting in a vertical shake.
        """
        direction = getattr(self, '_sidebar_slide_direction', 0)
        self._sidebar_slide_direction = 0
        canvas = getattr(self, 'active_scroll_canvas', None)
        item = getattr(self, '_sidebar_slide_window', None)
        if not direction or canvas is None or item is None:
            return
        if getattr(self, '_admin_page', '') in ('Lịch sử làm bài', 'Lịch sử'):
            return
        try:
            if not canvas.winfo_exists():
                return
            canvas.update_idletasks()
            height = max(1, canvas.winfo_height())
            distance = min(135, max(48, int(height * 0.16)))
            start_y = direction * distance
            # Lock scrolling while the window is moving.  Its bbox changes
            # every frame; using it as the scrollregion causes oscillation.
            body = canvas.nametowidget(canvas.itemcget(item, 'window'))
            body_height = max(body.winfo_reqheight(), body.winfo_height(), height)
            canvas.configure(scrollregion=(0, 0, max(1, canvas.winfo_width()), body_height + distance))
            canvas.yview_moveto(0)
            canvas.coords(item, 0, start_y)
            started = time.monotonic()
            duration = 0.22
            old_job = getattr(self, '_sidebar_slide_job', None)
            if old_job is not None:
                try: self.after_cancel(old_job)
                except (tk.TclError, RuntimeError): pass
            def tick():
                try:
                    if not canvas.winfo_exists() or getattr(self, 'active_scroll_canvas', None) is not canvas:
                        self._sidebar_slide_job = None
                        return
                    progress = min(1.0, (time.monotonic() - started) / duration)
                    eased = 1 - (1 - progress) ** 3
                    canvas.coords(item, 0, round(start_y * (1 - eased)))
                    if progress < 1:
                        self._sidebar_slide_job = self.after(16, tick)
                    else:
                        canvas.coords(item, 0, 0)
                        canvas.configure(scrollregion=(0, 0, max(1, canvas.winfo_width()), body_height))
                        canvas.yview_moveto(0)
                        self._sidebar_slide_job = None
                except (tk.TclError, RuntimeError):
                    self._sidebar_slide_job = None
            self._sidebar_slide_job = self.after(16, tick)
        except (tk.TclError, RuntimeError, KeyError):
            self._sidebar_slide_job = None

    def _navigation_unlock(self):
        self._navigation_busy = False

    def _navigation_back_key(self, event=None):
        if self._navigation_history and not self._navigation_busy:
            self.navigation_back()
            return 'break'

    def navigation_back(self):
        if not self._navigation_history or self._navigation_busy:
            return
        self._navigation_busy = True
        target = self._navigation_history.pop()
        self._sidebar_slide_direction = self._sidebar_navigation_direction(self._navigation_current, target)
        started = time.perf_counter()
        origin = self._page_callback_name(self._navigation_current)
        destination = self._page_callback_name(target)
        try:
            target()
            self._start_sidebar_slide()
            self._navigation_current = target
            self._navigation_page_title = getattr(self, '_admin_page', None)
            self._measure_page_transition(origin, destination, 'back', started)
        except Exception:
            self._navigation_history.append(target)
            raise
        finally:
            try:
                self.after(180, self._navigation_unlock)
            except (tk.TclError, RuntimeError):
                self._navigation_unlock()

    def _flush_usage_time(self):
        """Persist accumulated usage with one transaction, retaining pending time on failure."""
        seconds = getattr(self, '_usage_pending_seconds', 0.0)
        sid = getattr(self, '_usage_pending_student', None)
        day = getattr(self, '_usage_pending_day', None)
        if sid is None or seconds <= 0 or day is None:
            return
        self.learning.ensure_time_tables()
        with self.db.conn:
            self.db.conn.execute(
                'INSERT INTO app_usage_daily(student_id,day,seconds) VALUES(?,?,?) '
                'ON CONFLICT(student_id,day) DO UPDATE SET seconds=seconds+excluded.seconds',
                (sid, day, seconds))
        self._usage_pending_seconds = 0.0

    def _time_heartbeat(self):
        if getattr(self, '_phase5_shutting_down', False):
            return
        """Refresh clock every second but write usage in batches (or on account change)."""
        try:
            now = time.monotonic()
            elapsed = max(0.0, min(now - self._usage_last_tick, 5.0))
            self._usage_last_tick = now
            sid = self.student['id'] if self.student else None
            day = datetime.date.today().isoformat()
            previous = (self._usage_pending_student, self._usage_pending_day)
            if self._usage_pending_seconds and previous != (sid, day):
                self._flush_usage_time()
            if self._usage_pending_seconds == 0:
                self._usage_pending_student = sid
                self._usage_pending_day = day
            if sid is not None:
                self._usage_pending_seconds += elapsed
            if self._usage_pending_seconds >= 15:
                self._flush_usage_time()
            label = getattr(self, '_floating_clock', None)
            if label is not None and label.winfo_exists():
                label.configure(text=datetime.datetime.now().strftime('%H:%M:%S'))
        except Exception:
            # Keep the application responsive; retry pending writes on the next tick.
            import logging
            logging.getLogger(__name__).exception('Usage heartbeat failed')
        finally:
            try:
                if not getattr(self, '_phase5_shutting_down', False) and self.winfo_exists():
                    self.after(1000, self._time_heartbeat)
            except (tk.TclError, RuntimeError):
                pass

    def set_mouse_effect(self, mode):
        """Callback used by the floating recorder menu."""
        try:
            self.mouse_effects.set_mode(mode)
        except (ValueError, RuntimeError, tk.TclError) as exc:
            messagebox.showerror("Hiệu ứng chuột", str(exc), parent=self)

    def toggle_ui_grid(self):
        try:
            enabled = self.ui_grid.toggle()
        except Exception as exc:
            messagebox.showerror('Lưới UI',str(exc))
            return
        # No modal messagebox: grid must not block studying or keyboard/mouse input.
        try:
            self.title('Cùng Học Cùng Vui' + (' · Lưới UI đang bật' if enabled else ''))
        except tk.TclError:
            pass

    def reload_exercises(self):
        exercises=load_content()
        try:exercises.extend(read_custom_lessons(self.data_dir))
        except (OSError,ValueError) as exc:print('Content error:',exc,file=sys.stderr)
        return exercises

    def media_file(self,relative):
        """Only permit existing assets inside the bundled or personal content directories."""
        if not relative:return None
        from unified_subjects import subject_image
        if hasattr(self,'curriculum'):
            chosen=subject_image(self.curriculum.data_dir,relative)
            if chosen:return chosen
        for root in (CONTENT,user_content_dir(self.data_dir)):
            path=(root/relative).resolve()
            if path.is_relative_to(root.resolve()) and path.is_file():return path
        return None

    def report_callback_exception(self, exc, value, tb):
        """Expose Tkinter button errors to users and save technical details."""
        details = ''.join(traceback.format_exception(exc, value, tb))
        try:
            logfile = DATA / 'loi_ung_dung.log'
            with logfile.open('a', encoding='utf-8') as f:
                f.write(f"\n[{datetime.datetime.now().isoformat(timespec='seconds')}]\n{details}\n")
            messagebox.showerror('Ứng dụng gặp lỗi',
                'Không thể thực hiện thao tác.\n\n'
                f'Chi tiết lỗi đã lưu tại:\n{logfile}\n\n'
                f'{value}')
        except Exception:
            print(details, file=sys.stderr)

    def _remove_page_fade(self):
        job = getattr(self, '_page_transition_job', None)
        if job is not None:
            try: self.after_cancel(job)
            except (tk.TclError, RuntimeError): pass
        self._page_transition_job = None
        layer = getattr(self, '_page_fade_layer', None)
        self._page_fade_layer = None
        if layer is not None:
            try: layer.destroy()
            except (tk.TclError, RuntimeError): pass

    def _fast_navigation_enabled(self):
        """Avoid synchronous screen capture by default; opt in with TU_HOC_FAST_NAV=0."""
        return os.environ.get('TU_HOC_FAST_NAV', '1').strip().lower() not in ('0', 'false', 'off')

    def _snapshot_before_navigation(self):
        """Freeze the complete app client area at a fixed screen coordinate.

        Capturing only the scrolling content used to create a momentary vertical
        seam/jump when layout() rebuilt the header and canvas geometry.
        """
        self._remove_page_fade()
        if self._fast_navigation_enabled():
            return
        if sys.platform != 'win32':
            return
        try:
            from PIL import ImageGrab, ImageTk
            if not self.winfo_exists():
                return
            # Settle any pending layout *before* reading both pixels and bounds.
            self.update_idletasks()
            x, y = self.winfo_rootx(), self.winfo_rooty()
            w, h = self.winfo_width(), self.winfo_height()
            if w < 100 or h < 100:
                return
            capture_start = time.perf_counter()
            shot = ImageGrab.grab(bbox=(x, y, x+w, y+h))
            navigation_record(getattr(self, '_admin_page', '?'), 'screenshot_capture', (time.perf_counter()-capture_start)*1000)
            layer = tk.Toplevel(self)
            layer.withdraw()
            layer.overrideredirect(True)
            layer.configure(bg=TOKEN_COLORS['surface'])
            layer.geometry(f'{w}x{h}+{x}+{y}')
            # 0.999 (not 1.0) keeps the window layered from creation, so the first
            # fade step does not switch window style and flash.
            layer.attributes('-alpha', 0.999)
            label = tk.Label(layer, bd=0, highlightthickness=0)
            label._photo = ImageTk.PhotoImage(shot, master=label)
            label.configure(image=label._photo)
            label.pack(fill='both', expand=True)
            self._page_fade_layer = layer
            self._page_snapshot_started_at = time.monotonic()
            # Map the complete old window image in one go. The header and page
            # now share the same fixed coordinate system, so they cannot jump.
            layer.deiconify()
            layer.geometry(f'{w}x{h}+{x}+{y}')
            layer.lift()
            # Paint the frozen screenshot NOW. Tk only draws a newly mapped window
            # when the event loop runs, and clear() + page building (the lesson page
            # decodes images synchronously) block it for a long time: the user then
            # sees a blank/white window instead of the old page = the screen flash.
            paint_start = time.perf_counter()
            layer.update()
            navigation_record(getattr(self, '_admin_page', '?'), 'snapshot_layer_update', (time.perf_counter()-paint_start)*1000)
        except Exception:
            self._remove_page_fade()

    def _fade_in_new_page(self):
        """Fade the old frozen page over the fully constructed LIVE new page.

        Heavy pages (e.g. level list) used to be laid out *during* the fade:
        the 55 ms timer fires before Tk's idle layout, the main thread then
        blocks for a few hundred ms, and because progress was wall-clock based
        the fade jumped almost to the end (visible stutter). Now the new page
        is laid out first, the clock starts afterwards, and each frame advances
        at most MAX_STEP seconds so a hitch can only delay, never skip.
        """
        self._page_reveal_job = None
        if self._fast_navigation_enabled():
            return
        layer = getattr(self, '_page_fade_layer', None)
        if layer is None: return
        try:
            # Settle the new page completely while the frozen layer still covers it.
            # update_idletasks() alone is not enough for the lesson page: its
            # <Configure> bindings (canvas width -> text/wrap relayout) are queued
            # events that would otherwise run *inside* the fade and freeze it.
            # The layer is a top-level window over the whole client area, so mouse
            # clicks cannot reach the page while this runs.
            # Never run a nested Tk event loop here: update() may dispatch
            # another navigation callback while the transition is being built.
            self.update_idletasks()
        except (tk.TclError, RuntimeError):
            self._remove_page_fade(); return
        if getattr(self, '_page_fade_layer', None) is not layer: return
        # A light crossfade works better than a long transition: measured
        # navigation is commonly 200-500 ms, while some heavy screens take
        # considerably longer. Never add a proportional wait to slow screens.
        build_elapsed = time.monotonic() - getattr(self, '_page_snapshot_started_at', time.monotonic())
        duration = 0.260 if build_elapsed < 0.35 else (0.220 if build_elapsed < 0.8 else 0.180)
        MAX_STEP = 0.040
        state = {'t': 0., 'last': None}
        def tick():
            if getattr(self, '_page_fade_layer', None) is not layer: return
            try:
                now = time.monotonic()
                if state['last'] is not None:
                    state['t'] += min(now-state['last'], MAX_STEP)
                state['last'] = now
                progress = min(1., state['t']/duration)
                eased = progress*progress*(3-2*progress)
                layer.attributes('-alpha', max(0., 1.-eased))
                if progress < 1.:
                    self._page_transition_job = self.after(16, tick)
                else:
                    self._remove_page_fade()
            except (tk.TclError, RuntimeError):
                self._remove_page_fade()
        # First frame is a no-op (alpha stays ~1) and absorbs any remaining
        # paint work of the new page before the visible fade begins.
        self._page_transition_job = self.after(16, tick)

    def clear(self):
        slide_job = getattr(self, '_sidebar_slide_job', None)
        if slide_job is not None:
            try: self.after_cancel(slide_job)
            except (tk.TclError, RuntimeError): pass
            self._sidebar_slide_job = None
        reveal_job = getattr(self, '_page_reveal_job', None)
        if reveal_job is not None:
            try: self.after_cancel(reveal_job)
            except (tk.TclError, RuntimeError): pass
            self._page_reveal_job = None
        job = getattr(self, '_drawer_animation_job', None)
        if job is not None:
            try: self.after_cancel(job)
            except (tk.TclError, RuntimeError): pass
            self._drawer_animation_job = None
        if getattr(self, '_page_transition_ready', False):
            self._snapshot_before_navigation()
        else:
            self._remove_page_fade()
        self._hide_selection_plus()
        self._nav_drawer = None
        self._donate_panel = None
        self._account_panel = None
        self._account_animation_job = None
        self._notification_panel = None
        self._notification_animation_job = None
        self._menu_navigation_pending = False
        self._nav_container = None
        self._teaching_escape = None
        self._teaching_shortcuts = {}
        self._reading_clear_annotations = None
        self._nav_backdrop = None
        self.active_scroll_canvas = None
        self._stop_reading_tts()
        _audio_t0 = time.perf_counter()
        self.audio.stop()
        if hasattr(self,'learning_audio'):self.learning_audio.stop()
        if hasattr(self,"dictation_audio"): self.dictation_audio.stop()
        navigation_record(getattr(self, '_admin_page', '?'), 'stop_audio',
                          (time.perf_counter()-_audio_t0)*1000)
        _destroy_start = time.perf_counter()
        _destroy_count = 0
        destroy_start = time.perf_counter()
        destroyed_count = 0
        for w in self.winfo_children():
            # Floating control belongs to the root, not to the current page.
            # Do not destroy it during navigation: it may receive queued drag events.
            if w is getattr(self, '_shell', None) or (getattr(self, '_shell', None) is not None and w in (self._shell.sidebar,self._shell.right)):
                for page in list(self._shell.content.winfo_children()):page.destroy()
                continue
            if w is getattr(self, '_page_fade_layer', None):
                continue
            # This control is persistent just like the recorder. Hide it
            # outside a lesson so stale callbacks never operate on old text.
            if w is getattr(self, 'floating_vocabulary', None):
                w.place_forget()
                continue
            _widget_t0 = time.perf_counter()
            _widget_type = type(w).__name__
            _widget_path = str(w)
            w.destroy()
            _widget_ms = (time.perf_counter()-_widget_t0)*1000
            if _widget_ms >= 10:
                navigation_record(getattr(self, '_admin_page', '?'), 'destroy_widget_detail',
                                  _widget_ms, f'widget={_widget_type!r} path={_widget_path!r}')
            _destroy_count += 1
        navigation_record(getattr(self, '_admin_page', '?'), 'destroy_widgets',
                          (time.perf_counter()-_destroy_start)*1000,
                          f'root_children={_destroy_count}')

    def label(self,parent,text,size=12,bold=False,color=DARK,**kw):
        return tk.Label(parent,text=text,font=font_at(size,'bold' if bold else 'normal'),fg=color,bg=parent.cget('bg'),wraplength=750,justify='left',**kw)

    def button(self,parent,text,command):
        # A short, visible selection pulse before page navigation.  The event
        # loop gets time to paint the pressed state before a heavy page builds.
        button = tk.Button(parent,text=text,bg=GREEN,fg='white',
                           activebackground=DARK,activeforeground='white',
                           font=font_at(11, 'bold'),bd=0,padx=17,pady=10,
                           cursor='hand2')
        def activate():
            if getattr(button, '_selection_pending', False):
                return
            button._selection_pending = True
            try:
                button.configure(bg='#F9E9AC',fg='#285D40',
                                 activebackground='#F9E9AC',
                                 activeforeground='#285D40',relief='sunken',
                                 cursor='watch')
            except tk.TclError:
                return
            def navigate():
                nav_start = time.perf_counter()
                navigation_record(getattr(self, '_admin_page', '?'), 'button_pulse_wait', (nav_start-click_start)*1000, f'button={text!r}')
                try:
                    if button.winfo_exists():
                        button._selection_pending = False
                    self._navigate_to(command)
                except Exception:
                    # Preserve Tkinter's normal exception reporting.
                    self.report_callback_exception(*sys.exc_info())
                finally:
                    # A validation dialog can leave the current page intact.
                    # Restore the button's normal appearance after its callback.
                    try:
                        if button.winfo_exists():
                            button._selection_pending = False
                            button.configure(bg=GREEN, fg='white',
                                             activebackground=DARK,
                                             activeforeground='white',
                                             relief='flat', cursor='hand2')
                    except tk.TclError:
                        pass
                    page = getattr(self, '_admin_page', '?')
                    navigation_record(page, 'navigation_callback', (time.perf_counter()-nav_start)*1000, f'button={text!r}')
                    # This timer runs when the event loop becomes available again;
                    # it is NOT an exact measurement of monitor paint completion.
                    try:
                        self.after_idle(lambda p=page, t=nav_start: navigation_record(
                            p, 'event_loop_idle', (time.perf_counter()-t)*1000))
                    except (tk.TclError, RuntimeError):
                        pass
            click_start = time.perf_counter()
            self.after(125, navigate)
        # Match the soft green hover treatment used in subject selection.
        button.bind('<Enter>',lambda e,b=button: b.configure(bg='#257B56') if not getattr(b,'_selection_pending',False) else None,add='+')
        button.bind('<Leave>',lambda e,b=button: b.configure(bg=GREEN) if not getattr(b,'_selection_pending',False) else None,add='+')
        button.configure(command=activate)
        return button

    def action_button(self, parent, text, command):
        """Button for repeatable actions; do not register it as page navigation."""
        button = tk.Button(parent, text=text, bg=GREEN, fg='white',
                           activebackground=DARK, activeforeground='white',
                           font=font_at(11, 'bold'), bd=0, padx=17, pady=10,
                           cursor='hand2', command=command)
        button.bind('<Enter>', lambda e, b=button: b.configure(bg='#257B56'), add='+')
        button.bind('<Leave>', lambda e, b=button: b.configure(bg=GREEN), add='+')
        return button

    def _show_shortcut_guide(self):
        """One in-app reference, also reachable with F1."""
        existing = getattr(self, '_shortcut_guide', None)
        try:
            if existing and existing.winfo_exists():
                existing.lift(); existing.focus_force(); return
        except tk.TclError: pass
        dialog = tk.Toplevel(self)
        self._shortcut_guide = dialog
        dialog.title('HiHieu - Phím tắt giảng dạy')
        dialog.geometry('510x580')
        dialog.minsize(390,390)
        dialog.transient(self)
        dialog.configure(bg='#F5FAF6')
        tk.Label(dialog,text='⌨  Hướng dẫn phím tắt',font=font_at(16, 'bold'),bg='#F5FAF6',fg='#285D40').pack(anchor='w',padx=20,pady=(18,4))
        tk.Label(dialog,text='Các lệnh chỉ tác động lên trang đang mở.',font=font_at(10),bg='#F5FAF6',fg='#52675B').pack(anchor='w',padx=20,pady=(0,10))
        holder=tk.Frame(dialog,bg='#F5FAF6');holder.pack(fill='both',expand=True,padx=18)
        canvas=tk.Canvas(holder,bg='#F5FAF6',highlightthickness=0)
        scroll=tk.Scrollbar(holder,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
        rows=tk.Frame(canvas,bg='#F5FAF6');win=canvas.create_window((0,0),window=rows,anchor='nw')
        rows.bind('<Configure>',lambda e=None:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e=None:canvas.itemconfigure(win,width=e.width if e is not None else canvas.winfo_width()))
        sections=[('Toàn chương trình', [('F1','Mở bảng phím tắt'),('Esc','Tắt công cụ đang bật'),('Ctrl + Q','Viết ghi chú tự do'),('Ctrl + D','Vẽ đường'),('Ctrl + E','Xóa đối tượng'),('Ctrl + K','Chọn màu'),('Ctrl + Z','Hoàn tác nét vẽ'),('Ctrl + Shift + X','Xóa tất cả chú thích')]),('Riêng Tập đọc',[('Ctrl + H','Tô màu chữ'),('Ctrl + U','Gạch chân'),('Ctrl + B','In đậm'),('Ctrl + M','Đổi màu chữ'),('Ctrl + P','Chọn màu bút'),('Ctrl + +','Phóng to chữ'),('Ctrl + -','Thu nhỏ chữ')])]
        for section,items in sections:
            tk.Label(rows,text=section,bg='#F5FAF6',fg='#285D40',font=font_at(12, 'bold')).pack(anchor='w',pady=(12,5))
            for shortcut,meaning in items:
                line=tk.Frame(rows,bg='white',pady=5,padx=8);line.pack(fill='x',pady=2)
                tk.Label(line,text=shortcut,width=14,anchor='w',bg='white',fg='#12603A',font=font_at(10, 'bold')).pack(side='left')
                tk.Label(line,text=meaning,anchor='w',bg='white',fg='#283D31',font=font_at(10)).pack(side='left')
        tk.Button(dialog,text='Đóng',command=dialog.destroy,bg='#D9EFE0',fg='#285D40',bd=0,padx=16,pady=7).pack(pady=12)
        dialog.bind('<Escape>',lambda e:dialog.destroy())

    def _setup_teaching_tools(self, title):
        """Replace the drawing toolbar with a content-management shortcut."""
        self._teaching_escape = None
        self._teaching_shortcuts = {}
        if not self.student:
            return
        panel = tk.Frame(self._teaching_header, bg='#E8F3EB')
        panel.pack(side='right', fill='x', expand=True, padx=(10, 0))
        def open_content_manager():
            # Debounce rapid clicks before scheduling navigation. Never animate a
            # widget which is about to be destroyed by the destination page.
            if getattr(button, '_content_open_pending', False):
                return
            button._content_open_pending = True
            try:
                button.configure(state='disabled', cursor='watch')
                self._navigate_to(self.admin_manage_levels)
            finally:
                try:
                    if button.winfo_exists():
                        button._content_open_pending = False
                        button.configure(state='normal', cursor='hand2')
                except tk.TclError:
                    pass

        button = tk.Button(
            panel, text='⚙',
            command=open_content_manager,
            bg=TOKEN_COLORS['surface'], fg='#285D40', activebackground='#D3EBDD',
            font=('Segoe UI Symbol', 16, 'bold'), bd=0,
            padx=10, pady=5, cursor='hand2',
        )
        button.pack(side='left', padx=4, pady=3)
        TeachingTooltip(button, 'Quản lý nội dung học tập', '',
                        'Mở trang quản lý bài học, bài tập, từ vựng và bài đọc.')

    def clear_reading_annotations(self):
        """Clear annotation tags and overlay marks without changing lesson text.

        Reading-specific widgets can register an optional callback named
        _reading_clear_annotations for their own drawing state.
        """
        callback=getattr(self,'_reading_clear_annotations',None)
        if callback is not None:
            return callback()
        root=getattr(self,'_nav_container',None)
        if root is None or not root.winfo_exists(): return
        widgets=[]
        def visit(parent):
            for child in parent.winfo_children():
                widgets.append(child)
                visit(child)
        visit(root)
        texts=[w for w in widgets if isinstance(w,tk.Text)]
        tags=('highlight','underline','bold','text_color','foreground','annotation','teacher_highlight')
        affected=[(w,t) for w in texts for t in tags if t in w.tag_names() and w.tag_ranges(t)]
        if not affected: return
        if not dialogs.askyesno('Xóa tất cả đánh dấu',
                'Xóa các phần tô màu, gạch chân và đánh dấu trên bài đọc?\nNội dung chữ không bị xóa.',
                icon='warning',parent=self):return
        for w,t in affected:w.tag_remove(t,'1.0','end')

    def _attach_toolbar_resize(self,panel,content):
        grip=tk.Frame(panel,height=5,bg='#9ABBA4',cursor='sb_v_double_arrow')
        grip.pack(side='bottom',fill='x')
        def start(e):grip._start=(e.y_root,panel.winfo_height())
        def drag(e):
            y,height=grip._start
            panel.configure(height=max(32,min(160,height+e.y_root-y)))
            panel.pack_propagate(False)
        grip.bind('<ButtonPress-1>',start)
        grip.bind('<B1-Motion>',drag)

    def _reading_focus(self, enabled=None, origin=None):
        """Session-only Reading Studio window with native window zoom transition."""
        import tkinter as tk
        import time
        active=bool(getattr(self,'_reading_focus_active',False))
        if enabled is None:enabled=not active
        if bool(enabled)==active:return
        if enabled:
            base=getattr(self,'_v8_active_reader',None)
            if base is None or not base.winfo_exists():return
            button=origin or getattr(base,'_expand_reading_button',None)
            if button is None or not button.winfo_exists():return
            button.update_idletasks()
            ox=button.winfo_rootx()+button.winfo_width()//2
            oy=button.winfo_rooty()+button.winfo_height()//2
            self._reading_origin=(ox,oy)
            self._reading_base_reader=base
            self._reading_original_nav=getattr(self,'_nav_container',None)
            self._reading_focus_active=True
            top=tk.Toplevel(self)
            top.withdraw();top.configure(bg='#eaf3f9')
            top.overrideredirect(True)
            self._reading_studio_window=top
            width,height=top.winfo_screenwidth(),top.winfo_screenheight()
            host=tk.Frame(top,bg='#eaf3f9')
            # Fixed studio dimensions prevent full document reflow on every
            # animation frame (the main source of stuttering on Windows).
            host.place(x=0,y=0,width=width,height=height)
            # A fresh reader ensures all marks and pictures disappear when exiting.
            from pygame_embedded_reader import EmbeddedReader
            studio=EmbeddedReader(host,base.item,base.image_file,external_dock=True,
                speak=base.speak,on_add_vocab=base.on_add_vocab,on_play_audio=base.on_play_audio)
            studio.pack(fill='both',expand=True)
            studio._expand_reading_button.configure(text='⤢ Thu nhỏ',command=lambda:self._reading_focus(False))
            studio.set_reading_preferences(zoom=base.zoom,dark=base.reading_dark)
            self._v8_active_reader=studio
            self._nav_container=top
            old=getattr(self,'_v8_dock',None)
            if old is not None and old.winfo_exists():old.destroy()
            self._v8_dock=None
            self._v8_refresh_dock()
            top.bind('<Escape>',lambda e:self._reading_focus(False))
            top.bind('<F11>',lambda e:self._reading_focus(False))
            top.protocol('WM_DELETE_WINDOW',lambda:self._reading_focus(False))
            # Build the entire Reading Studio off-screen, then reveal it once.
            # Avoid Pygame screenshot overlays and per-frame window resizing,
            # which can cause visible flicker and multiple window flashes.
            self._reading_animating=False
            top.geometry(f'{width}x{height}+0+0')
            top.update_idletasks()
            top.deiconify()
            top.lift()
            top.focus_set()
        else:
            top=getattr(self,'_reading_studio_window',None)
            if top is None or not top.winfo_exists():return
            if getattr(self,'_reading_animating',False):return
            # Defer destruction until the button click/key event has completed.
            # Destroying the clicked Tk button inside its own event can leave
            # queued Windows/Tk events pointing to a dead widget command.
            if getattr(self, '_reading_close_job', None) is None:
                self._reading_close_job = self.after_idle(self._finish_reading_focus)

    def _reading_snapshot_animation(self, top, start, end, duration, done=None):
        """Render a single cached Reading frame using a transparent Pygame window."""
        self._reading_animating = True
        sw, sh = top.winfo_screenwidth(), top.winfo_screenheight()

        def finish():
            self._reading_animating = False
            if done is not None:
                done()
            else:
                top.geometry(f'{sw}x{sh}+0+0')
                top.deiconify()
                top.lift()
                top.focus_force()

        try:
            from reading_pygame_transition import animate
            if animate(top, start, end, duration, finish):
                return
        except Exception:
            pass
        # Native fallback when Pygame/desktop capture is unavailable.
        self._reading_animating = False
        self._reading_window_animation(top, start, end, duration, done)

    def _reading_window_animation(self,top,start,end,duration,done=None):
        """Fallback if screen capture is unavailable."""
        import time
        self._reading_animating=True
        t0=time.monotonic()
        def tick():
            if not top.winfo_exists():return
            t=min(1.0,(time.monotonic()-t0)/duration)
            eased=t*t*(3-2*t)
            x,y,w,h=(round(a+(b-a)*eased) for a,b in zip(start,end))
            top.geometry(f'{max(1,w)}x{max(1,h)}{x:+d}{y:+d}')
            if not top.winfo_viewable():top.deiconify()
            if t<1:top.after(16,tick)
            else:
                self._reading_animating=False
                if done:done()
        tick()

    def _finish_reading_focus(self):
        self._reading_close_job = None
        top=getattr(self,'_reading_studio_window',None)
        dock=getattr(self,'_v8_dock',None)
        # The floating tools panel installs a global mouse-wheel handler while
        # hovered. Its <Leave> event may never fire if the panel is destroyed.
        if dock is not None and dock.winfo_exists():
            try: dock.unbind_all('<MouseWheel>')
            except tk.TclError: pass
            dock.destroy()
        self._v8_dock=None
        job=getattr(self,'_v8_dock_job',None)
        if job is not None:
            try:self.after_cancel(job)
            except (tk.TclError,ValueError):pass
            self._v8_dock_job=None
        if top is not None and top.winfo_exists():top.destroy()
        self._reading_studio_window=None
        self._reading_focus_active=False
        self._nav_container=getattr(self,'_reading_original_nav',None)
        base=getattr(self,'_reading_base_reader',None)
        self._v8_active_reader=base if base is not None and base.winfo_exists() else None
        if self._v8_active_reader is not None:
            self._v8_active_reader.clear()
        self._reading_base_reader=None

    def _teaching_key(self,event):
        if event.keysym=='F11':
            if getattr(self,'_v8_active_reader',None) is not None:
                self._reading_focus();return 'break'
        if event.keysym=='Escape' and getattr(self,'_reading_focus_active',False):
            self._reading_focus(False);return 'break'
        if event.keysym=='F1':
            self._show_shortcut_guide();return 'break'
        if event.keysym=='Escape':
            callback=getattr(self,'_teaching_escape',None)
            if callback:callback();return 'break'
            return
        if event.state & 0x4:
            key='ctrl+'+('shift+' if event.state & 0x1 else '')+event.keysym.lower()
            action=getattr(self,'_teaching_shortcuts',{}).get(key)
            if action:action();return 'break'

    def layout(self,title):
        """Reusable shell around untouched legacy page builders."""
        if getattr(self,'_reading_focus_active',False):self._reading_focus(False)
        self._admin_page=str(title)
        self.clear()
        if self._shell is None:
            self._shell=AppShell(self)
        self._shell.pack(fill="both",expand=True)
        self._shell.active(str(title))
        container=tk.Frame(self._shell.content,bg=BG)
        container.pack(fill='both',expand=True)
        self._nav_container=container
        self._setup_teaching_tools(title)
        canvas=tk.Canvas(container,bg=BG,highlightthickness=0,bd=0)
        self.active_scroll_canvas=canvas
        canvas.pack(side='left',fill='both',expand=True)
        body=tk.Frame(canvas,bg=BG,padx=24,pady=16)
        window=canvas.create_window((0,0),window=body,anchor='nw')
        self._sidebar_slide_window=window
        body.bind('<Configure>',lambda e=None:canvas.configure(scrollregion=canvas.bbox('all')) if getattr(self, '_sidebar_slide_job', None) is None else None)
        canvas.bind('<Configure>',lambda e=None:canvas.itemconfigure(window,width=e.width if e else canvas.winfo_width()))
        self.label(body,title,20,True).pack(anchor='w',fill='x',pady=(0,12))
        self._page_transition_ready=False
        return body

    def play_learning_audio(self,path):
        if not path:
            dialogs.showwarning('Âm thanh','Chưa tìm thấy file âm thanh của câu hỏi / block.')
            return
        try:
            self.learning_audio.stop()
            old=getattr(self,'_waveform_window',None)
            if old and old.winfo_exists():old.close()
            self._waveform_window=WaveformPlayer(self,path)
        except Exception as exc:dialogs.showerror('Không phát được âm thanh',str(exc))

    def _animate_drawer(self, drawer, target, duration=390, on_complete=None):
        """Interruptible, eased drawer motion driven by Tk's event loop."""
        if not drawer.winfo_exists():
            return
        previous = getattr(self, '_drawer_animation_job', None)
        if previous is not None:
            try: self.after_cancel(previous)
            except tk.TclError: pass
        self._drawer_animation_job = None
        start = drawer.winfo_x()
        started = time.monotonic()
        def tick():
            if not drawer.winfo_exists():
                self._drawer_animation_job = None
                return
            t = min(1.0, (time.monotonic()-started)*1000/max(1,duration))
            eased = t*t*(3-2*t)  # symmetric ease-in-out for opening and closing
            drawer.place_configure(x=round(start+(target-start)*eased))
            if t < 1:
                self._drawer_animation_job = self.after(16, tick)
            else:
                self._drawer_animation_job = None
                if on_complete: on_complete()
        tick()

    def _click_menu_icon(self):
        button = getattr(self, '_menu_button', None)
        if button is not None:
            micro_rotation(button, duration=120)
        self.toggle_navigation_drawer()

    def _click_account_icon(self):
        button = getattr(self, '_account_button', None)
        if button is not None:
            micro_rotation(button, duration=120)
        self.toggle_account_panel()

    def _click_notification_icon(self):
        button = getattr(self, '_notification_button', None)
        if button is not None:
            micro_rotation(button, duration=120)
        self.toggle_notification_panel()

    def toggle_navigation_drawer(self):
        existing=getattr(self,'_nav_drawer',None)
        if existing is not None and existing.winfo_exists():
            self._close_navigation_drawer();return
        if not self.student:return
        account=getattr(self,'_account_panel',None)
        if account is not None and account.winfo_exists():
            self._close_account_panel(animate=True,on_complete=self.toggle_navigation_drawer);return
        notification=getattr(self,'_notification_panel',None)
        if notification is not None and notification.winfo_exists():
            self._close_notification_panel(animate=True,on_complete=self.toggle_navigation_drawer);return
        job=getattr(self,'_drawer_animation_job',None)
        if job is not None:
            try:self.after_cancel(job)
            except tk.TclError:pass
            self._drawer_animation_job=None
        host=self._nav_container
        # Keep the actual lesson widgets visible and live behind the drawer.
        # An opaque Canvas backdrop would conceal the display on some Windows
        # setups, even if a screenshot was attempted. No backdrop is created.
        self._nav_backdrop=None
        drawer=tk.Frame(host,bg=TOKEN_COLORS['surface'],highlightthickness=1,highlightbackground='#DDE4E8')
        self._nav_drawer=drawer
        drawer.place(x=-315,y=0,width=315,relheight=1)
        drawer.lift()
        title=tk.Frame(drawer,bg='#E2F0E2',padx=15,pady=10);title.pack(fill='x')
        tk.Label(title,text='☰  MENU',bg='#E2F0E2',fg=DARK,font=font_at(17, 'bold')).pack(side='left')
        tk.Button(title,text='✕',command=self._close_navigation_drawer,bg='#E2F0E2',bd=0,font=font_at(16)).pack(side='right')
        items=[('⌂  Trang chủ',self.home),
               ('📖  Bài học & bài tập',self.topic_page),('📚  Tập đọc / Reading',self.reading_menu),('📝  Kiểm tra',self.exam_page),
               ('🎧  Chính tả MP3',self.dictation_page),('🎮  Trò chơi',self.games_page),
               ('🃏  Flashcard',self.flashcards),('🎁  Phần thưởng',self.reward_shop),
               ('🖼  Cài đặt hiển thị',self.display_settings),
               ('▦  Lưới giao diện',self.toggle_ui_grid)]
        canvas=tk.Canvas(drawer,bg='white',highlightthickness=0)
        scroll=tk.Scrollbar(drawer,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
        inner=tk.Frame(canvas,bg='white');window=canvas.create_window((0,0),window=inner,anchor='nw')
        inner.bind('<Configure>',lambda _e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e=None:canvas.itemconfigure(window,width=e.width if e is not None else canvas.winfo_width()))
        for label,callback in items:
            def navigate(fn=callback):
                # Complete the slide-out before rebuilding the page. Destroying
                # the drawer immediately causes a visible jump in navigation.
                if getattr(self, '_menu_navigation_pending', False):
                    return
                self._menu_navigation_pending = True
                def finish():
                    self._menu_navigation_pending = False
                    # Drawer animation can finish before the prior navigation unlock.
                    # Retry once the transition is ready instead of dropping the click.
                    def navigate_when_ready(attempts=0):
                        if getattr(self, '_navigation_busy', False):
                            if attempts < 30:
                                self.after(50, lambda: navigate_when_ready(attempts + 1))
                            return
                        self._navigate_to(fn)
                    navigate_when_ready()
                self._close_navigation_drawer(animate=True, on_complete=finish)
            item=tk.Button(inner,text=label,command=navigate,bg='white',fg=DARK,bd=0,
                      font=font_at(12),anchor='w',padx=17,pady=11,
                      activebackground='#E8F3EB',cursor='hand2')
            item.pack(fill='x',padx=7,pady=2)
            add_hover(item,TOKEN_COLORS['surface'],'#E8F3EB')
        # Menu has its own wheel/drag scrolling, independent of the lesson canvas.
        self._menu_scroll_canvas=canvas
        self._menu_drag_start=None
        def menu_wheel(event):
            delta = -1 if getattr(event,'num',None)==4 else (1 if getattr(event,'num',None)==5 else (-1 if event.delta>0 else 1))
            canvas.yview_scroll(delta*3,'units')
            return 'break'
        def menu_press(event):
            self._menu_drag_start=(event.y_root,canvas.yview()[0])
        def menu_drag(event):
            if self._menu_drag_start is None:return
            bbox=canvas.bbox('all')
            if bbox:
                total=max(1,bbox[3]-bbox[1])
                canvas.yview_moveto(max(0,min(1,self._menu_drag_start[1]+(self._menu_drag_start[0]-event.y_root)/total)))
        def menu_release(event):self._menu_drag_start=None
        for widget in (canvas,inner,*inner.winfo_children()):
            for seq in ('<MouseWheel>','<Button-4>','<Button-5>'):
                widget.bind(seq,menu_wheel)
            # Buttons retain click navigation; dragging begins after a small gesture.
            widget.bind('<ButtonPress-1>',menu_press,add='+')
            widget.bind('<B1-Motion>',menu_drag,add='+')
            widget.bind('<ButtonRelease-1>',menu_release,add='+')
        # Let Tk finish mapping the drawer off-screen before starting the slide.
        # Without this idle boundary, the first visible frame may jump ahead.
        drawer.place_configure(x=-315)
        self.after_idle(lambda d=drawer: animate_magnetic_cascade(self, d, inner, duration=230)
                        if d.winfo_exists() and self._nav_drawer is d
                        and not getattr(self, '_menu_navigation_pending', False) else None)

    def _load_application_logo(self):
        """Use the supplied logo for the Windows title-bar/taskbar icon."""
        logo = BASE / 'logo.png'
        if not logo.exists():
            return
        try:
            from PIL import Image, ImageTk
            image = Image.open(logo).convert('RGBA')
            # Logo is wide; preserve its aspect ratio rather than distorting it.
            image.thumbnail((64, 64), Image.Resampling.LANCZOS)
            self._application_icon = ImageTk.PhotoImage(image, master=self)
        except (ImportError, OSError, ValueError, AttributeError):
            try:
                self._application_icon = tk.PhotoImage(file=str(logo), master=self)
            except tk.TclError:
                return
        self.iconphoto(True, self._application_icon)

    def _account_stats(self):
        sid=self.student['id']
        summary=self.db.completion_summary(sid)
        points=self.db.points(sid)
        stars=0
        try:
            row=self.db.conn.execute('SELECT COALESCE(SUM(stars),0) FROM level_scores WHERE student_id=?',(sid,)).fetchone()
            stars=int(row[0] or 0)
        except sqlite3.Error:pass
        return summary,points,stars

    def toggle_account_panel(self):
        notification=getattr(self,'_notification_panel',None)
        if notification is not None and notification.winfo_exists():
            self._close_notification_panel(animate=True,on_complete=self._open_account_panel)
            return
        panel=getattr(self,'_account_panel',None)
        if panel is not None and panel.winfo_exists():
            self._close_account_panel(animate=True);return
        if not self.student:return
        if getattr(self,'_nav_drawer',None) is not None:
            self._close_navigation_drawer(animate=True,on_complete=self._open_account_panel)
            return
        self._open_account_panel()

    def _donate_hover(self, active):
        self._donate_glow_hover=bool(active)

    def _animate_donate_button(self, canvas):
        """Red heart icon with a moving glow and brief sparkling flashes.

        Tkinter's after callback is owned by this widget. When navigation is
        rebuilt and the old canvas disappears, its animation stops safely.
        """
        try:
            if not canvas.winfo_exists() or getattr(self,'_donate_button',None) is not canvas:
                return
            tick=getattr(self,'_donate_glow_tick',0)+1
            self._donate_glow_tick=tick
            pulse=(math.sin(tick*0.21)+1.0)/2.0
            flash=(tick % 47) in (0,1,2,3,4)
            hover=getattr(self,'_donate_glow_hover',False)
            canvas.delete('all')
            # Multiple concentric rings emulate a soft animated red glow.
            rings=[(4,'#F7CFD4'),(3,'#F2A5B0'),(2,'#ED7789')]
            if pulse>.55 or hover:
                rings=[(5,'#F6B6C1'),(4,'#F38A9B'),(3,'#ED6076')]
            for margin,color in rings:
                canvas.create_oval(7-margin,8-margin,38+margin,33+margin,
                                   fill=color,outline='')
            core='#F32345' if pulse>.52 else '#D91536'
            canvas.create_oval(9,10,36,32,fill=core,outline='#B50E2B',width=1)
            canvas.create_text(22,21,text='♥',font=('Segoe UI Symbol',17,'bold'),fill='white')
            canvas.create_text(48,21,text='Donate',anchor='w',
                               font=font_at(13, 'bold'),fill='#D7193F')
            # Twinkles travel around the heart; extra bright every ~2 seconds.
            angle=tick*0.22
            for offset in (0,2.45):
                x=22+22*math.cos(angle+offset)
                y=21+16*math.sin(angle+offset)
                r=2.9 if flash else (1.5+1.2*pulse)
                canvas.create_line(x-r,y,x+r,y,fill='#FFF6F7' if flash else '#E62E55',width=2)
                canvas.create_line(x,y-r,x,y+r,fill='#FFF6F7' if flash else '#E62E55',width=2)
            if flash:
                canvas.create_text(120,9,text='✦',fill='#F23A58',font=('Segoe UI Symbol',12,'bold'))
            canvas.after(65,lambda:self._animate_donate_button(canvas))
        except tk.TclError:
            # Canvas was destroyed during page navigation.
            return

    def modern_button(self,parent,text,command,*,secondary=False,danger=False,width=155):
        """Shared accessible button with consistent subject-picker hover feedback."""
        normal = '#FFF0EF' if danger else (PALE if secondary else GREEN)
        hover = '#FFE0DD' if danger else ('#D9EFE0' if secondary else '#257B56')
        foreground = TOKEN_COLORS['error'] if danger else (DARK if secondary else 'white')
        button = tk.Button(parent,text=text,command=command,
            bg=normal,fg=foreground,activebackground=hover,
            activeforeground=foreground,font=font_at(11, 'bold'),
            relief='flat',bd=0,padx=14,pady=9,cursor='hand2',
            takefocus=True,highlightthickness=2,highlightcolor=GREEN)
        def set_hover(active):
            try:
                if button.winfo_exists() and str(button.cget('state')) != 'disabled':
                    button.configure(bg=hover if active else normal)
            except (tk.TclError, RuntimeError):
                pass
        button.bind('<Enter>',lambda event:set_hover(True),add='+')
        button.bind('<Leave>',lambda event:set_hover(False),add='+')
        button.bind('<FocusIn>',lambda event:set_hover(True),add='+')
        button.bind('<FocusOut>',lambda event:set_hover(False),add='+')
        return button

    def toggle_donate_panel(self):
        """Slide the Donate popover down; use native Tk controls (no modern_button)."""
        old=getattr(self,'_donate_panel',None)
        if old is not None and old.winfo_exists():
            self._close_donate_panel()
            return
        host=getattr(self,'_nav_container',None)
        button=getattr(self,'_donate_button',None)
        if host is None or button is None or not host.winfo_exists():return
        host.update_idletasks()
        width=min(315,max(220,host.winfo_width()-16))
        x=max(8,min(host.winfo_width()-width-8,button.winfo_rootx()-host.winfo_rootx()))
        height=132
        panel=tk.Frame(host,bg='white',highlightbackground='#D5E6DC',highlightthickness=1)
        self._donate_panel=panel
        panel.place(x=x,y=-height,width=width,height=height)
        panel.lift()
        heading=tk.Frame(panel,bg=PALE,padx=12,pady=9);heading.pack(fill='x')
        tk.Label(heading,text='💝 Donate · Ủng hộ kênh',bg=PALE,fg=DARK,
                 font=font_at(11, 'bold')).pack(side='left')
        tk.Button(heading,text='✕',command=self._close_donate_panel,
                  bg=PALE,fg=DARK,bd=0,cursor='hand2').pack(side='right')
        tk.Button(panel,text='▶  Subscribe kênh YouTube',command=self._open_donate_youtube,
                  font=font_at(11, 'bold'),bg='#E7F3EA',fg=DARK,
                  activebackground='#CDE7D6',relief='flat',bd=0,
                  padx=14,pady=10,cursor='hand2').pack(fill='x',padx=12,pady=14)
        self.after_idle(lambda p=panel: self._animate_donate_panel(p,8,320)
                        if p.winfo_exists() and self._donate_panel is p else None)

    def _animate_donate_panel(self,panel,target,duration=250,on_complete=None):
        job=getattr(self,'_donate_panel_job',None)
        if job is not None:
            try:self.after_cancel(job)
            except tk.TclError:pass
        self._donate_panel_job=None
        if not panel.winfo_exists():return
        start=panel.winfo_y();began=time.monotonic()
        def frame():
            if not panel.winfo_exists():return
            t=min(1.,(time.monotonic()-began)*1000/max(1,duration))
            eased=1-(1-t)**3
            panel.place_configure(y=round(start+(target-start)*eased))
            if t<1:self._donate_panel_job=self.after(16,frame)
            else:
                self._donate_panel_job=None
                if on_complete:on_complete()
        frame()

    def _close_donate_panel(self):
        panel=getattr(self,'_donate_panel',None)
        self._donate_panel=None
        if panel is None:return
        try:
            if panel.winfo_exists():
                self._animate_donate_panel(panel,-140,180,on_complete=panel.destroy)
        except tk.TclError:pass

    def _open_donate_youtube(self):
        self._close_donate_panel()
        webbrowser.open('https://www.youtube.com/@hocvui102')

    def _open_account_panel(self):
        if not self.student:return
        host=self._nav_container
        if host is None:return
        summary,points,stars=self._account_stats()
        panel=tk.Frame(host,bg='white',highlightbackground='#D5E6DC',highlightthickness=1)
        self._account_panel=panel
        width=340
        panel.place(x=12,y=-650,width=width,height=620)
        panel.lift()
        top=tk.Frame(panel,bg=PALE,padx=15,pady=11);top.pack(fill='x')
        tk.Label(top,text=self.db.selected_avatar(self.student['id'])+'  '+self.student['name'],bg=PALE,fg=DARK,font=font_at(14, 'bold')).pack(side='left')
        tk.Button(top,text='✕',command=self._close_account_panel,bg=PALE,bd=0,font=font_at(15)).pack(side='right')
        balance=tk.Frame(panel,bg='white',padx=14,pady=12);balance.pack(fill='x')
        for label,value in [('💎 Ngọc',self.db.gems(self.student['id'])),('⭐ Sao',stars),('🏆 Điểm',points)]:
            line=tk.Frame(balance,bg='white');line.pack(fill='x',pady=3)
            tk.Label(line,text=label,bg='white',fg=DARK,font=font_at(12)).pack(side='left')
            tk.Label(line,text=str(value),bg='white',fg=GREEN,font=font_at(12, 'bold')).pack(side='right')
        actions=[('🏅  Achievement · Nhận ngọc',self.level_achievements_page),('🎨  Đổi icon tài khoản',self.owned_avatar_page),('🛍  Cửa hàng icon',self.avatar_shop_page),('⏱  Thống kê thời gian',self.time_statistics_page),('🏅  Thành tích & Kỷ lục',self.achievement_page),('📊  Báo cáo học tập',self.report_page),('▥  Tiến độ học tập',self.lesson_progress_page),('👤  Đổi tài khoản',self.show_profiles)]
        for title,callback in actions:
            def navigate(fn=callback):
                if getattr(self,'_account_navigation_pending',False):return
                self._account_navigation_pending=True
                def finish():
                    self._account_navigation_pending=False
                    self._navigate_to(fn)
                self._close_account_panel(animate=True,on_complete=finish)
            tk.Button(panel,text=title,command=navigate,bg='white',fg=DARK,activebackground=PALE,bd=0,font=font_at(11),anchor='w',padx=20,pady=11,cursor='hand2').pack(fill='x',padx=7,pady=2)
        self.after_idle(lambda p=panel:self._animate_account_panel(p,8)
                        if p.winfo_exists() and self._account_panel is p else None)

    def _animate_account_panel(self,panel,target):
        job=getattr(self,'_account_animation_job',None)
        if job is not None:
            try:self.after_cancel(job)
            except tk.TclError:pass
        start=panel.winfo_y();started=time.monotonic()
        def frame():
            if not panel.winfo_exists():return
            progress=min(1,(time.monotonic()-started)/0.28)
            ease=1-(1-progress)**3
            panel.place_configure(y=int(start+(target-start)*ease))
            if progress<1:self._account_animation_job=self.after(16,frame)
            else:self._account_animation_job=None
        frame()

    def _close_account_panel(self,animate=False,on_complete=None):
        job=getattr(self,'_account_animation_job',None)
        if job is not None:
            try:self.after_cancel(job)
            except tk.TclError:pass
            self._account_animation_job=None
        panel=getattr(self,'_account_panel',None)
        self._account_panel=None
        def finish():
            if panel is not None:
                try:
                    if panel.winfo_exists():panel.destroy()
                except tk.TclError:pass
            if on_complete:on_complete()
        if panel is not None and animate and panel.winfo_exists():
            self._animate_account_panel(panel,-650)
            self._account_close_job=self.after(290,finish)
        else:finish()

    def owned_avatar_page(self):
        """Choose any unlocked avatar without spending more gems."""
        body=self.layout('🎨 Icon tài khoản của tôi')
        sid=self.student['id']
        self.label(body,f'💎 Số ngọc: {self.db.gems(sid)}',14,True).pack(anchor='w',pady=10)
        self.label(body,'Chọn một icon đã mở khóa để sử dụng.',12).pack(anchor='w',pady=6)
        owned=self.db.owned_avatars(sid)
        selected=self.db.selected_avatar(sid)
        for avatar,name,price in AVATAR_OPTIONS:
            if avatar not in owned:continue
            line=tk.Frame(body,bg='white',padx=12,pady=9,highlightbackground='#D5E6DC',highlightthickness=1)
            line.pack(fill='x',pady=4)
            tk.Label(line,text=avatar,font=('Segoe UI Emoji',25),bg='white').pack(side='left',padx=12)
            tk.Label(line,text=name,font=font_at(12, 'bold'),bg='white',fg=DARK).pack(side='left')
            def select(icon=avatar):
                self.db.buy_or_select_avatar(sid,icon)
                self.owned_avatar_page()
            tk.Button(line,text='Đang dùng' if avatar==selected else 'Sử dụng',command=select,state='disabled' if avatar==selected else 'normal',bg=PALE,fg=DARK,bd=0,padx=12,pady=6).pack(side='right')
        tk.Button(body,text='🛍  Mở cửa hàng icon',command=self.avatar_shop_page,bg=GREEN,fg='white',bd=0,padx=16,pady=10).pack(anchor='w',pady=15)

    def avatar_shop_page(self):
        """Avatar shop: owned icons remain available, balance persists per student."""
        body=self.layout('🛍 Cửa hàng icon')
        sid=self.student['id']
        self.label(body,'Mở khóa biểu tượng bằng ngọc và sử dụng vĩnh viễn.',15,True).pack(anchor='w',pady=(0,8))
        self.label(body,f'💎 Ngọc hiện có: {self.db.gems(sid)}',13,True).pack(anchor='w',pady=(0,10))
        self.label(body,'Biểu tượng đã mua được sử dụng vĩnh viễn. Ngọc chỉ trừ một lần khi mở khóa.',11).pack(anchor='w',pady=(0,12))
        owned=self.db.owned_avatars(sid)
        selected=self.db.selected_avatar(sid)
        for avatar,name,price in AVATAR_OPTIONS:
            line=tk.Frame(body,bg='white',padx=12,pady=9,highlightbackground='#D5E6DC',highlightthickness=1)
            line.pack(fill='x',pady=4)
            tk.Label(line,text=avatar,font=('Segoe UI Emoji',26),bg='white').pack(side='left',padx=(0,14))
            tk.Label(line,text=name,bg='white',fg=DARK,font=font_at(12, 'bold')).pack(side='left')
            is_owned=avatar in owned
            label='Đang dùng' if selected==avatar else ('Sử dụng' if is_owned else f'💎 {price} ngọc')
            def choose(icon=avatar,title=name,cost=price,has_it=is_owned):
                if not has_it and not dialogs.askyesno('Mở khóa icon',f'Dùng {cost} ngọc để mở khóa icon {title} {icon}?'):
                    return
                ok,message=self.db.buy_or_select_avatar(sid,icon)
                if not ok:dialogs.showwarning('Không thể đổi icon',message)
                self.avatar_shop_page()
            tk.Button(line,text=label,command=choose,state='disabled' if selected==avatar else 'normal',bg=PALE,fg=DARK,bd=0,padx=13,pady=7,cursor='hand2').pack(side='right')

    def achievement_page(self):
        body=self.layout('🏅 Thành tích & Kỷ lục')
        sid=self.student['id'];summary,points,stars=self._account_stats()
        self.label(body,'THỐNG KÊ HỌC TẬP',16,True).pack(anchor='w',pady=9)
        for label,value in [('Số lần hoàn thành bài',summary['completed']),('Số lần đạt 100%',summary['perfect']),('Số ngọc hiện có',self.db.gems(sid)),('Điểm',points),('Sao',stars)]:
            self.label(body,f'{label}: {value}',12).pack(anchor='w',pady=4)
        self.label(body,'KỶ LỤC',16,True).pack(anchor='w',pady=(22,7))
        row=self.db.conn.execute('SELECT MAX(correct) best_correct,MAX(CASE WHEN total>0 THEN ROUND(100.0*correct/total,1) END) best_percent FROM completion_events WHERE student_id=?',(sid,)).fetchone()
        self.label(body,f"Số câu đúng cao nhất trong một lượt: {row['best_correct'] or 0}  •  Tỷ lệ cao nhất: {row['best_percent'] or 0}%",12).pack(anchor='w',pady=5)
        self.label(body,'ACHIEVEMENT · THÀNH TỰU',16,True).pack(anchor='w',pady=(22,8))
        for key,required,title in [('first_lesson',1,'🌱 Bước đầu tiên'),('five_lessons',5,'📚 Chăm chỉ học tập'),('ten_lessons',10,'💎 Chinh phục 10 bài tập')]:
            claimed=self.db.conn.execute('SELECT 1 FROM achievement_claims WHERE student_id=? AND achievement_id=?',(sid,key)).fetchone() is not None
            count=self.db.conn.execute("SELECT COUNT(*) FROM completion_events WHERE student_id=? AND activity_type='lesson'",(sid,)).fetchone()[0]
            frame=tk.Frame(body,bg='#EDF6EE',padx=15,pady=12);frame.pack(fill='x',pady=5)
            self.label(frame,f'{title} · Hoàn thành bài tập {required} lần · +1 ngọc',12,True).pack(side='left')
            button=tk.Button(frame,text='Đã nhận' if claimed else ('Nhận ngọc' if count>=required else f'{count}/{required}'),state='disabled' if claimed or count<required else 'normal',bg=GREEN,fg='white',bd=0,padx=12,pady=7)
            button.pack(side='right')
            def claim(k=key,r=required):
                if self.db.claim_achievement(sid,k,r):Toast(self,'Bạn nhận được 1 viên ngọc!')
                self.achievement_page()
            button.configure(command=claim)
        self.label(body,'Lưu ý: 3 thành tựu là mẫu; lượt hoàn thành bài tập được tính mỗi lần nộp bài hoàn chỉnh. Kết quả level cần tích hợp sự kiện hoàn thành từ bộ máy Level.',10,color='#64748B').pack(anchor='w',pady=12)

    def reading_menu(self):
        """Open the reading section without requiring users to find its submenu."""
        return self.reading_topics()

    def reading_topics(self):
        body=self.layout('📚 Tập đọc / Reading')
        self.label(body,'Chọn chủ đề để xem danh sách bài đọc.',12).pack(anchor='w',pady=8)
        for theme in self._themes():
            code,name=theme[0],theme[1]
            self.button(body,name,lambda t=code:self.level_list(t,'reading')).pack(fill='x',pady=5)

    def admin_manage_levels(self):
        """Content management is directly available; no admin toggle or gate."""
        return self.manage_levels()

    def _close_navigation_drawer(self,animate=True,on_complete=None):
        drawer=getattr(self,'_nav_drawer',None)
        backdrop=getattr(self,'_nav_backdrop',None)
        self._nav_drawer=None
        self._nav_backdrop=None
        self._menu_scroll_canvas=None
        if backdrop is not None:
            try: backdrop.destroy()
            except (tk.TclError,RuntimeError): pass
        if drawer is None:
            if on_complete: on_complete()
            return
        def finish():
            try:
                if drawer.winfo_exists(): drawer.destroy()
            except (tk.TclError, RuntimeError):
                pass
            if on_complete: on_complete()
        try:
            if not drawer.winfo_exists() or not animate:
                finish(); return
            # Faster exit than entrance keeps menu navigation responsive.
            animate_reverse_cascade_left(self, drawer, on_complete=finish)
        except (tk.TclError,RuntimeError):
            finish()

    def show_floating_vocabulary(self, callback):
        """Legacy entry point: selection '+' is registered per Text widget instead."""
        control=getattr(self,'floating_vocabulary',None)
        if control is not None and control.winfo_exists():control.place_forget()

    def _hide_selection_plus(self):
        plus=getattr(self,'_selection_plus',None)
        if plus is not None:
            try:plus.destroy()
            except tk.TclError:pass
        self._selection_plus=None

    def _animate_selection_plus(self, button, x, y):
        """Pop the selected-text + into view without blocking the UI."""
        sizes=(15,19,23,27,25)
        def tick(i=0):
            try:
                if not button.winfo_exists() or getattr(self,'_selection_plus',None) is not button:return
                size=sizes[i]
                button.place_configure(x=x+(25-size)//2,y=y+(25-size)//2,width=size,height=size)
                if i+1<len(sizes):self.after(28,lambda:tick(i+1))
            except tk.TclError:pass
        tick()

    def bind_selection_plus(self,text_widget,save_callback):
        """Show a small + beside highlighted text, without obstructing selection."""
        def show(event=None):
            self._hide_selection_plus()
            try:
                if not text_widget.winfo_exists():return
                first=text_widget.index('sel.first');last=text_widget.index('sel.last')
                if not text_widget.get(first,last).strip():return
                # Anchor to the top-right of the final selected glyph, not
                # the next insertion point (which can be far from the highlight).
                end_char=text_widget.index(f'{last} -1c')
                box=text_widget.bbox(end_char)
                if box is None:box=text_widget.bbox(first)
                if box is None:return
                root_x=text_widget.winfo_rootx()+box[0]+box[2]+2
                root_y=text_widget.winfo_rooty()+box[1]-15
                x=max(5,min(self.winfo_width()-35,root_x-self.winfo_rootx()))
                y=max(5,min(self.winfo_height()-35,root_y-self.winfo_rooty()))
                plus=tk.Button(self,text='+',font=font_at(12, 'bold'),bg='#3B9B65',fg='white',
                    activebackground='#237548',activeforeground='white',bd=0,width=2,height=1,
                    cursor='hand2',command=lambda:(self._hide_selection_plus(),save_callback(text_widget)))
                self._selection_plus=plus
                plus.place(x=x+5,y=y+5,width=15,height=15)
                plus.lift()
                self._animate_selection_plus(plus,x,y)
                TeachingTooltip(plus,'Lưu từ','+','Thêm từ đã bôi đen vào Flashcard của bài này.')
            except tk.TclError:pass
        text_widget.bind('<ButtonRelease-1>',lambda e:self.after(20,show),add='+')
        text_widget.bind('<KeyRelease>',lambda e:self.after(20,show),add='+')
        text_widget.bind('<ButtonPress-1>',lambda e:self._hide_selection_plus(),add='+')

    def update_record_status(self):
        control = getattr(self, 'floating_recorder', None)
        if control is None or not control.winfo_exists():
            return
        session = self.recording_session
        seconds = int(time.monotonic() - session.started) if session and session.started else 0
        control.set_state(session.kind if session else None, self.recording_busy, seconds)

    def _recording_tick(self):
        if self.recording_session:
            self.update_record_status()
            self.after(1000,self._recording_tick)

    def _mic_setting_path(self):
        return DATA / 'recording_device.json'

    def get_recording_microphone_id(self):
        try:
            return json.loads(self._mic_setting_path().read_text(encoding='utf-8')).get('microphone_id')
        except (OSError, ValueError, TypeError):
            return None

    def choose_recording_device(self):
        if self.recording_session or self.recording_busy:
            dialogs.showinfo('Đang ghi', 'Hãy dừng bản ghi trước khi thay đổi thiết bị.')
            return
        try:
            devices = microphone_choices()
        except Exception as exc:
            dialogs.showerror('Thiết bị ghi âm', 'Không đọc được danh sách micro. Cài soundcard trước.\n' + str(exc))
            return
        dialog = tk.Toplevel(self)
        dialog.title('Chọn thiết bị ghi âm')
        dialog.geometry('560x285')
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        frame = tk.Frame(dialog, bg=TOKEN_COLORS['surface'], padx=18, pady=16)
        frame.pack(fill='both', expand=True)
        tk.Label(frame, text='MICRO GHI ÂM', font=font_at(14, 'bold'), bg='white', fg=DARK).pack(anchor='w')
        tk.Label(frame, text='Micro được dùng cho cả Ghi âm và Ghi hình + tiếng micro.',
                 bg='white', fg=DARK).pack(anchor='w', pady=(7, 12))
        options = [('Mặc định Windows (tự thay khi đổi thiết bị)', None)]
        for d in devices:
            name = d['name'] + ('  [Mặc định hiện tại]' if d['default'] else '')
            options.append((name, d['id']))
        names = [n for n, _ in options]
        saved = self.get_recording_microphone_id()
        index = next((i for i, item in enumerate(options) if item[1] == saved), 0)
        selected = tk.StringVar(value=names[index])
        picker = ttk.Combobox(frame, values=names, textvariable=selected, state='readonly', width=67)
        picker.pack(fill='x', pady=(0, 10))
        state = tk.StringVar(value=f'Phát hiện {len(devices)} micro. Chọn thiết bị rồi thử âm hoặc lưu.')
        tk.Label(frame, textvariable=state, bg='white', fg=DARK, wraplength=520, justify='left').pack(anchor='w')
        buttons = tk.Frame(frame, bg='white')
        buttons.pack(anchor='w', pady=15)

        def chosen_id():
            pos = picker.current()
            return options[pos][1] if 0 <= pos < len(options) else None

        def save():
            try:
                selected_id = chosen_id()
                resolve_microphone(selected_id)
                self._mic_setting_path().write_text(json.dumps({'microphone_id': selected_id}, ensure_ascii=False, indent=2), encoding='utf-8')
            except Exception as exc:
                messagebox.showerror('Không lưu được thiết bị', str(exc), parent=dialog)
                return
            dialog.destroy()
            dialogs.showinfo('Đã chọn micro', 'Thiết bị ghi âm đã được lưu. Các bản ghi tiếp theo sẽ dùng lựa chọn này.')

        def test():
            try:
                device = resolve_microphone(chosen_id())
            except Exception as exc:
                state.set('Không kết nối được: ' + str(exc))
                return
            test_button.configure(state='disabled')
            state.set('Đang thử âm 2 giây... Hãy nói vào micro.')
            def sample():
                try:
                    import numpy as np
                    with device.recorder(samplerate=44100, channels=1, blocksize=2048) as recorder:
                        blocks = [recorder.record(numframes=2048) for _ in range(43)]
                    data = np.concatenate(blocks)
                    rms = float(np.sqrt(np.mean(np.square(data.astype(float)))))
                    text = ('Đã nhận âm thanh (mức tín hiệu: %.1f%%).' % (rms * 100)) if rms > 0.002 else 'Đã kết nối nhưng tín hiệu rất nhỏ. Kiểm tra micro/mute và nói thử.'
                except Exception as exc:
                    text = 'Thử âm thất bại: ' + str(exc)
                def done():
                    if dialog.winfo_exists():
                        state.set(text)
                        test_button.configure(state='normal')
                try:
                    self.after(0, done)
                except RuntimeError:
                    pass
            import threading
            threading.Thread(target=sample, daemon=True).start()

        test_button = tk.Button(buttons, text='🎙 Thử micro (2 giây)', command=test)
        test_button.pack(side='left', padx=(0, 9))
        tk.Button(buttons, text='Lưu thiết bị', command=save, bg=GREEN, fg='white').pack(side='left', padx=(0, 9))
        tk.Button(buttons, text='Đóng', command=dialog.destroy).pack(side='left')

    def start_voice_recording(self): self._start_recording('voice')

    def start_video_recording(self): self._start_recording('video')

    def _start_recording(self,kind):
        if self.recording_session or self.recording_busy:
            dialogs.showinfo('Đang ghi','Hãy dừng bản ghi hiện tại trước.');return
        name='ghi giọng bằng micro' if kind=='voice' else 'quay cửa sổ ứng dụng kèm tiếng hệ thống và micro'
        if not dialogs.askyesno('Xác nhận ghi',f'Bắt đầu {name}?\n\nCó thể thu âm lời nói và nội dung cá nhân trên màn hình. Chỉ ghi khi bạn đồng ý.'):
            return
        try:
            if resolve_microphone(self.get_recording_microphone_id()) is None:
                raise RuntimeError('Không tìm thấy micro. Hãy kết nối micro và chọn trong menu + > Thiết bị ghi âm.')
        except Exception as exc:
            dialogs.showerror('Không tìm thấy thiết bị ghi âm', str(exc))
            return
        session=RecordingSession(self,kind='video' if kind=='video' else 'voice', microphone_id=self.get_recording_microphone_id())
        try:
            session.start()
        except Exception as exc:
            dialogs.showerror('Không thể bắt đầu ghi',str(exc));return
        self.recording_session=session
        self.update_record_status()
        self._recording_tick()

    def stop_recording(self):
        if not self.recording_session or self.recording_busy:return
        session=self.recording_session
        self.recording_session=None
        self.recording_busy=True
        self.update_record_status()
        import threading
        def worker():
            try:
                path,warnings=session.finish()
                self.after(0,lambda:self._done_recording(path,warnings,None))
            except Exception as exc:
                error=str(exc)
                self.after(0,lambda:self._done_recording(None,[],error))
        threading.Thread(target=worker,daemon=True).start()

    def _done_recording(self,path,warnings,error):
        self.recording_busy=False
        self.update_record_status()
        if error: dialogs.showerror('Lỗi lưu bản ghi',error);return
        dialogs.showinfo('Đã lưu bản ghi',f'File: {path}'+ ('\n\nLưu ý: '+str(warnings) if warnings else ''))

    def open_recording_folder(self):
        import os
        folder=recording_folder()
        if sys.platform=='win32':os.startfile(str(folder))
        else:dialogs.showinfo('Thư mục bản ghi',str(folder))

    def destroy(self):
        if self.recording_session:
            if not dialogs.askyesno('Đang ghi','Đang có bản ghi chưa lưu. Bạn muốn dừng để lưu trước khi thoát?'):
                return
            try:self.recording_session.finish()
            except Exception as exc:dialogs.showwarning('Bản ghi',str(exc))
            self.recording_session=None
        super().destroy()

    def _v8_refresh_dock(self):
        """Fixed, collapsible Tools panel on the right of the interactive reading page."""
        if not self.winfo_exists():return
        alive=lambda w:w is not None and bool(getattr(w,'winfo_exists',lambda:False)())
        reader=getattr(self,'_v8_active_reader',None)
        container=getattr(self,'_nav_container',None)
        old=getattr(self,'_v8_dock',None)
        if not (alive(reader) and alive(container) and self.student and getattr(self,'_reading_focus_active',False)):
            if alive(old):old.destroy()
            self._v8_dock=None;return
        if alive(old) and old.master is container:return
        if alive(old):old.destroy()
        from tkinter import colorchooser
        from theme_config import UI_COLORS as K
        EXPANDED,COLLAPSED=300,56
        collapsed=bool(getattr(self,'_v8_dock_collapsed',False))
        dock=tk.Frame(container,bg='white',width=COLLAPSED if collapsed else EXPANDED,
                      highlightthickness=1,highlightbackground=K['border'])
        # A floating slide-over on top of the reader, NOT a packed sibling.
        # Hiding the panel restores the entire reading viewport underneath.
        dock.place(relx=1.0,rely=0,anchor='ne',relheight=1.0,
                   width=COLLAPSED if collapsed else EXPANDED)
        dock.pack_propagate(False)
        self._v8_dock=dock;self._v8_dock_job=None
        dock.lift()  # tools remain in front of the reader
        head=tk.Frame(dock,bg='white');head.pack(fill='x',padx=8,pady=(10,4))
        title=tk.Label(head,text='Công cụ · Tools',bg='white',fg=K['text'],font=font_at(13, 'bold'))
        toggle=tk.Button(head,bd=0,bg='white',fg=K['primary'],activebackground=K['tint'],
                         font=font_at(14, 'bold'),width=3,cursor='hand2',takefocus=True)
        toggle.pack(side='right')
        wrap=tk.Frame(dock,bg='white')
        canvas=tk.Canvas(wrap,bg='white',highlightthickness=0,bd=0)
        inner=tk.Frame(canvas,bg='white')
        window=canvas.create_window((0,0),window=inner,anchor='nw')
        canvas.pack(side='left',fill='both',expand=True)
        inner.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=e.width))
        def wheel(e):
            if inner.winfo_reqheight()>canvas.winfo_height():canvas.yview_scroll(-1 if e.delta>0 else 1,'units')
        wrap.bind('<Enter>',lambda e:wrap.bind_all('<MouseWheel>',wheel))
        wrap.bind('<Leave>',lambda e:wrap.unbind_all('<MouseWheel>'))
        palette=getattr(self,'_v8_palette_colors',None) or {'draw':'#000000','fill':'#FFD600','highlight':'#FFF3A3','underline':'#E53935','textbox':'#202020','note':'#245c80'}
        self._v8_palette_colors=palette
        tool_buttons={};active={'name':None}
        def current():
            r=getattr(self,'_v8_active_reader',None)
            if not alive(r):
                dialogs.showinfo('Công cụ','Mở bài đọc để sử dụng công cụ tương tác.',parent=self);return None
            return r
        def refresh():
            for key,b in tool_buttons.items():
                on=key==active['name']
                b.configure(bg=K['accent'] if on else 'white',fg=K['text'] if on else K['primary_dark'],
                            activebackground='#FFD55C' if on else K['tint'],relief='solid' if on else 'flat')
        def pick(key):
            r=current()
            if r is None:return
            if key=='highlight':r.apply_text_highlight();return
            if active['name']==key:active['name']=None;r.set_mode('select')
            else:active['name']=key;r.set_mode(key)
            refresh()
        def reset_tool():
            r=getattr(self,'_v8_active_reader',None)
            if active['name'] and alive(r):r.set_mode('select')
            active['name']=None;refresh()
        self._teaching_escape=reset_tool
        def pick_color(key,swatch):
            chosen=colorchooser.askcolor(color=palette[key],title='Chọn màu',parent=self)[1]
            if not chosen:return
            palette[key]=chosen;swatch.configure(bg=chosen,activebackground=chosen)
            r=getattr(self,'_v8_active_reader',None)
            if alive(r):r.set_tool_color(key,chosen)
        def section(text):
            tk.Label(inner,text=text,bg='white',fg=K['muted'],font=font_at(9, 'bold'),anchor='w').pack(fill='x',padx=12,pady=(12,3))
        def plain(parent,text,cmd,**grid):
            b=tk.Button(parent,text=text,command=cmd,bg='white',fg=K['primary_dark'],activebackground=K['tint'],
                        font=font_at(10, 'bold'),bd=1,relief='solid',highlightthickness=0,cursor='hand2',pady=7,takefocus=True)
            return b
        section('VIẾT & ĐÁNH DẤU · MARK UP')
        for key,label in [('draw','✎  Vẽ · Draw'),('fill','▨  Tô vùng · Fill'),('highlight','🖍  Highlight chữ'),
                          ('underline','U̲  Gạch chân · Underline'),('textbox','▣  Textbox'),('note','✍  Ghi chú · Note')]:
            row=tk.Frame(inner,bg='white');row.pack(fill='x',padx=10,pady=2)
            b=tk.Button(row,text=label,command=lambda k=key:pick(k),anchor='w',bg='white',fg=K['primary_dark'],
                        activebackground=K['tint'],font=font_at(10, 'bold'),bd=1,relief='flat',highlightthickness=1,
                        highlightbackground=K['border'],cursor='hand2',padx=10,pady=8,takefocus=True)
            b.pack(side='left',fill='x',expand=True)
            tool_buttons[key]=b
            sw=tk.Button(row,bg=palette[key],activebackground=palette[key],width=3,bd=1,relief='solid',cursor='hand2',takefocus=True)
            sw.configure(command=lambda k=key,s=sw:pick_color(k,s));sw.pack(side='left',padx=(6,0),fill='y')
        # Add Picture belongs to the visible right-side Tools panel (the reader's
        # internal dock is disabled when external_dock=True).
        section('HÌNH ẢNH · PICTURE')
        def add_overlay_picture():
            r=current()
            if r is not None:r.add_picture()
        add_picture_btn=plain(inner,'▧  Add Picture · Thêm ảnh',add_overlay_picture)
        add_picture_btn.pack(fill='x',padx=10,pady=(2,5))
        def grid2(items):
            g=tk.Frame(inner,bg='white');g.pack(fill='x',padx=10)
            g.grid_columnconfigure(0,weight=1,uniform='c');g.grid_columnconfigure(1,weight=1,uniform='c')
            for i,(label,cmd) in enumerate(items):
                b=plain(g,label,cmd);b.grid(row=i//2,column=i%2,sticky='ew',padx=2,pady=2)
            return g
        def do(name):
            r=current()
            if r is None:return
            if name=='undo':r.undo()
            elif name=='redo':r.redo_action()
            elif name=='clear':
                if dialogs.askyesno('Xóa hết','Xóa toàn bộ nét vẽ, ghi chú và đánh dấu trong phiên này?',parent=self):r.clear()
            elif name=='zoom+':r.set_zoom(.1)
            elif name=='zoom-':r.set_zoom(-.1)
            elif name=='speak':r.read_aloud()
        section('SỬA · EDIT')
        eg=grid2([('↶ Hoàn tác',lambda:do('undo')),('↷ Làm lại',lambda:do('redo')),('⌫ Tẩy · Erase',lambda:pick('erase')),('🗑 Xóa hết',lambda:do('clear'))])
        tool_buttons['erase']=eg.winfo_children()[2]
        section('NÉT BÚT · PEN SIZE')
        def pen(value):
            r=getattr(self,'_v8_active_reader',None)
            if alive(r):r.set_width(int(float(value))-r.width)
        slider=tk.Scale(inner,from_=1,to=15,orient='horizontal',showvalue=True,command=pen,bg='white',highlightthickness=0,
                        troughcolor=K['tint'],activebackground=K['primary'],length=240)
        slider.set(getattr(reader,'width',3));slider.pack(fill='x',padx=12)
        section('ĐỌC TẬP TRUNG · READING FOCUS')
        def adjust_font(delta):
            r=current()
            if r is None:return
            r.set_zoom(delta)
            self._reading_font_zoom=r.zoom
        def toggle_dark():
            r=current()
            if r is None:return
            self._reading_dark=not bool(getattr(self,'_reading_dark',False))
            r.set_reading_preferences(dark=self._reading_dark)
            dark_btn.configure(text='☀  Chế độ sáng' if self._reading_dark else '☾  Chế độ tối')
        grid2([('A−  Giảm chữ',lambda:adjust_font(-.1)),('A+  Tăng chữ',lambda:adjust_font(.1))])
        dark_btn=plain(inner,'☀  Chế độ sáng' if getattr(self,'_reading_dark',False) else '☾  Chế độ tối',toggle_dark)
        dark_btn.pack(fill='x',padx=12,pady=(4,8))
        grid2([('A−',lambda:do('zoom-')),('A+',lambda:do('zoom+'))])
        sp=plain(inner,'🔊 Đọc to · Read aloud',lambda:do('speak'));sp.pack(fill='x',padx=12,pady=(4,12))
        refresh()
        def show_content(show):
            if show:
                title.pack(side='left',padx=4);wrap.pack(fill='both',expand=True,padx=(0,2),pady=(0,8))
            else:
                title.pack_forget();wrap.pack_forget()
        def set_state(collapse,animate=True):
            self._v8_dock_collapsed=collapse
            toggle.configure(text='‹' if collapse else '›')
            target=COLLAPSED if collapse else EXPANDED
            job=getattr(self,'_v8_dock_job',None)
            if job:
                try:self.after_cancel(job)
                except (ValueError,tk.TclError):pass
                self._v8_dock_job=None
            if not collapse:show_content(True)
            start=int(dock.place_info().get('width',dock.winfo_width()))
            if not animate or getattr(self,'reduce_motion',False) or start<=1 or start==target:
                dock.place_configure(width=target)
                if collapse:show_content(False)
                return
            t0=time.monotonic()
            def tick():
                if not dock.winfo_exists():return
                t=min(1.,(time.monotonic()-t0)/.24);e=t*t*(3-2*t)
                dock.place_configure(width=round(start+(target-start)*e))
                if t<1:self._v8_dock_job=self.after(16,tick)
                else:
                    self._v8_dock_job=None
                    if collapse:show_content(False)
            tick()
        toggle.configure(command=lambda:set_state(not getattr(self,'_v8_dock_collapsed',False),False))
        set_state(collapsed,False)

    def _v8_clamp_dock(self):
        """Kept for compatibility; the Tools panel is now docked, not floating."""
        return

    def show_profiles(self):
        self._v8_active_reader=None
        self.student=None
        self.clear()
        if self._shell is not None:
            self._shell.pack_forget()
        self._profile_page=ProfilePage(self)

    def choose_language(self):
        """Subject selection without the study sidebar; loading remains in switch_language."""
        from subject_ui import SubjectPage
        self.clear()
        if self._shell is not None:
            self._shell.pack_forget()
        self._subject_page=SubjectPage(self)

    def edit_profile_name(self, student):
        from tkinter import simpledialog
        name = simpledialog.askstring('Đổi tên tài khoản','Tên tài khoản mới:',initialvalue=student['name'],parent=self)
        if name is None:return
        try:self.db.rename_student(student['id'],name)
        except ValueError as error:dialogs.showwarning('Tên không hợp lệ',str(error));return
        self.show_profiles()

    def _quest_themes(self):
        """Use the five (or more) real curriculum themes, not guessed IDs."""
        try:return list(self._themes())
        except (AttributeError, OSError):return []

    def _quests_for_theme(self,theme):
        saved=load_level_achievements()
        entries=[r for r in saved if str(r['theme'])==str(theme)]
        signatures={(int(r['level']),int(r.get('lesson',0)),int(r['required'])) for r in entries}
        for level in range(1,self._max_level(theme)+1):
            for lesson in range(1,self._lesson_count(theme,level)+1):
                for item in lesson_quest_defaults(theme,level,lesson):
                    signature=(level,lesson,int(item['required']))
                    if signature not in signatures:entries.append(item);signatures.add(signature)
        return sorted(entries,key=lambda r:(int(r['level']),int(r.get('lesson',0)),int(r['required'])))

    def _claimable_quests(self):
        if not self.student:return []
        sid=self.student['id']
        claimed={r[0] for r in self.db.conn.execute('SELECT achievement_id FROM achievement_claims WHERE student_id=?',(sid,))}
        return [r for theme in self._quest_themes() for r in self._quests_for_theme(theme[0])
                if r['id'] not in claimed and self.db.level_achievement_count(sid,r['theme'],r['level'],r['max_seconds'],r.get('lesson'))>=int(r['required'])]

    def _unread_quest_ids(self):
        if not self.student:return set()
        sid=self.student['id']
        read={row[0] for row in self.db.conn.execute(
            'SELECT achievement_id FROM quest_notification_reads WHERE student_id=?',(sid,))}
        return {str(q['id']) for q in self._claimable_quests()}-read

    def _refresh_notification_bell(self):
        bell=getattr(self,'_notification_button',None)
        badge=getattr(self,'_notification_badge',None)
        if bell is None or not bell.winfo_exists():return
        unread=bool(self._unread_quest_ids())
        bell.configure(bg='#FFF0C2' if unread else PALE,
                       fg='#A46A00' if unread else DARK,
                       activebackground='#FFE18A' if unread else PALE)
        if badge is not None and badge.winfo_exists():
            if unread:badge.place(x=29,y=0);badge.lift()
            else:badge.place_forget()

    def toggle_notification_panel(self):
        panel=getattr(self,'_notification_panel',None)
        if panel is not None and panel.winfo_exists():
            self._close_notification_panel(animate=True);return
        if not self.student:return
        account=getattr(self,'_account_panel',None)
        if account is not None and account.winfo_exists():
            self._close_account_panel(animate=True,on_complete=self._open_notification_panel)
            return
        drawer=getattr(self,'_nav_drawer',None)
        if drawer is not None and drawer.winfo_exists():
            self._close_navigation_drawer(animate=True,on_complete=self._open_notification_panel)
        else:self._open_notification_panel()

    def _open_notification_panel(self):
        if not self.student:return
        host=getattr(self,'_nav_container',None)
        bell=getattr(self,'_notification_button',None)
        if host is None or bell is None or not host.winfo_exists() or not bell.winfo_exists():return
        quests=self._claimable_quests()
        unread_ids=self._unread_quest_ids()
        host.update_idletasks()
        width=min(355,max(235,host.winfo_width()-16))
        # Place directly below the bell, but keep the panel within the viewport.
        x=max(8,min(host.winfo_width()-width-8,bell.winfo_rootx()-host.winfo_rootx()-24))
        height=min(420,max(190,host.winfo_height()-18))
        panel=tk.Frame(host,bg='white',highlightbackground='#D5E6DC',highlightthickness=1)
        self._notification_panel=panel
        panel.place(x=x,y=-height-8,width=width,height=height)
        panel.lift()
        heading=tk.Frame(panel,bg=PALE,padx=12,pady=11);heading.pack(fill='x')
        tk.Label(heading,text='🔔 Thông báo',font=font_at(13, 'bold'),fg=DARK,bg=PALE).pack(side='left')
        tk.Button(heading,text='✕',command=self._close_notification_panel,bg=PALE,bd=0,font=font_at(13)).pack(side='right')
        notification_cards=[]
        if quests:
            tk.Label(panel,text=f'🎁 {len(quests)} phần thưởng đang chờ nhận',bg='white',fg='#A46A00',font=font_at(10, 'bold'),anchor='w').pack(fill='x',padx=13,pady=(10,5))
            outer=tk.Frame(panel,bg='white');outer.pack(fill='both',expand=True,padx=8)
            canvas=tk.Canvas(outer,bg='white',bd=0,highlightthickness=0)
            scrollbar=tk.Scrollbar(outer,orient='vertical',command=canvas.yview)
            canvas.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
            inner=tk.Frame(canvas,bg='white');win=canvas.create_window((0,0),window=inner,anchor='nw')
            inner.bind('<Configure>',lambda _e:canvas.configure(scrollregion=canvas.bbox('all')))
            canvas.bind('<Configure>',lambda e=None:canvas.itemconfigure(win,width=e.width if e is not None else canvas.winfo_width()))
            def scroll(event):
                delta=(-1 if event.num==4 else 1) if getattr(event,'num',None) in (4,5) else (-1 if event.delta>0 else 1)
                canvas.yview_scroll(delta*3,'units');return 'break'
            for quest in quests:
                title=quest.get('title',f"Level {quest['level']}")
                theme=quest['theme']
                name=next((t[1] for t in self._quest_themes() if t[0]==theme),theme)
                label=f"🎁 {name} · {title}\n💎 +{quest['gems']} ngọc  ·  Nhấn để nhận"
                def open_quest(c=theme,n=name):
                    self._close_notification_panel(animate=True,on_complete=lambda:self._open_quest_theme(c,n))
                is_unread=str(quest['id']) in unread_ids
                item=tk.Button(inner,text=label,command=open_quest,justify='left',anchor='w',wraplength=width-54,
                               bg='#FFF0B8' if is_unread else '#F2F8F2',
                               activebackground='#FFE087' if is_unread else '#E8F2E8',
                               fg='#875200' if is_unread else DARK,
                               highlightthickness=2 if is_unread else 0,
                               highlightbackground='#FFD54A',bd=0,padx=12,pady=10,
                               font=('Segoe UI',10,'bold' if is_unread else 'normal'),cursor='hand2')
                item.pack(fill='x',padx=4,pady=3)
                if is_unread:notification_cards.append(item)
                item.bind('<MouseWheel>',scroll);item.bind('<Button-4>',scroll);item.bind('<Button-5>',scroll)
            for widget in (canvas,inner):
                for seq in ('<MouseWheel>','<Button-4>','<Button-5>'):widget.bind(seq,scroll)
        else:
            tk.Label(panel,text='✓ Chưa có phần thưởng mới',font=font_at(12, 'bold'),bg='white',fg=GREEN).pack(pady=(32,9))
            tk.Label(panel,text='Khi hoàn thành nhiệm vụ Achievement,\nphần thưởng sẽ xuất hiện ở đây.',font=font_at(10),bg='white',fg='#667A6C',justify='center').pack()
        tk.Button(panel,text='🏅 Xem tất cả Achievement',command=lambda:self._close_notification_panel(animate=True,on_complete=self.level_achievements_page),
                  bg=PALE,fg=DARK,bd=0,font=font_at(10, 'bold'),pady=10,cursor='hand2').pack(fill='x',padx=12,pady=10)
        # Keep unread cards glowing while the panel opens, then softly settle
        # them to their normal appearance after the user has viewed them.
        if unread_ids:
            with self.db.conn:
                self.db.conn.executemany(
                    'INSERT OR IGNORE INTO quest_notification_reads(student_id,achievement_id) VALUES(?,?)',
                    [(self.student['id'],key) for key in unread_ids])
            self._refresh_notification_bell()
        def settle_cards():
            if self._notification_panel is not panel or not panel.winfo_exists():return
            colors=['#FFF0B8','#F8F2D5','#F2F8F2']
            def step(index=0):
                if self._notification_panel is not panel or not panel.winfo_exists():return
                for card in notification_cards:
                    if card.winfo_exists():
                        card.configure(bg=colors[index],fg='#875200' if index<2 else DARK,
                                       highlightthickness=2 if index<2 else 0,
                                       font=('Segoe UI',10,'bold' if index<2 else 'normal'))
                if index+1<len(colors):self.after(145,lambda:step(index+1))
            step()
        start=-height-8;target=8;began=time.monotonic()
        def animate():
            if not panel.winfo_exists() or self._notification_panel is not panel:return
            progress=min(1,(time.monotonic()-began)/0.39)
            ease=progress*progress*(3-2*progress)
            panel.place_configure(y=round(start+(target-start)*ease))
            if progress<1:self._notification_animation_job=self.after(16,animate)
            else:
                self._notification_animation_job=None
                if unread_ids:self.after(950,settle_cards)
        self.after_idle(animate)

    def _close_notification_panel(self,animate=False,on_complete=None):
        job=getattr(self,'_notification_animation_job',None)
        if job is not None:
            try:self.after_cancel(job)
            except tk.TclError:pass
        self._notification_animation_job=None
        panel=getattr(self,'_notification_panel',None)
        self._notification_panel=None
        def finish():
            if panel is not None:
                try:
                    if panel.winfo_exists():panel.destroy()
                except tk.TclError:pass
            if on_complete:on_complete()
        if panel is not None and animate and panel.winfo_exists():
            start=panel.winfo_y();end=-panel.winfo_height()-8;began=time.monotonic()
            def slide():
                if not panel.winfo_exists():finish();return
                progress=min(1,(time.monotonic()-began)/0.23)
                ease=progress*progress*(3-2*progress)
                panel.place_configure(y=round(start+(end-start)*ease))
                if progress<1:self._notification_animation_job=self.after(16,slide)
                else:
                    self._notification_animation_job=None
                    finish()
            slide()
        else:finish()

    def quest_notifications_page(self):
        quests=self._claimable_quests()
        if not quests:
            dialogs.showinfo('Thông báo','Hiện chưa có phần thưởng Achievement nào sẵn sàng nhận.',parent=self)
            return
        self.level_achievements_page()
        dialogs.showinfo('🎁 Quà đang chờ',f'Bạn có {len(quests)} phần thưởng đủ điều kiện nhận! Hãy chọn chủ đề để nhận ngọc.',parent=self)

    def level_achievements_page(self):
        """Game-style quest hub, organized by the actual subject themes."""
        body=self.layout('🏅 Achievement · Nhiệm vụ nhận ngọc')
        sid=self.student['id']
        self.label(body,f'💎 Ngọc đang có: {self.db.gems(sid)}',14,True).pack(anchor='w',pady=8)
        self.label(body,'Chọn một chủ đề để mở bảng nhiệm vụ. Mỗi cấp thưởng chỉ nhận một lần.',11).pack(anchor='w',pady=6)
        themes=self._quest_themes()
        grid=tk.Frame(body,bg=BG);grid.pack(fill='x',pady=15)
        for index,theme in enumerate(themes):
            code,name=theme[0],theme[1]
            icon=theme[2] if len(theme)>2 else '📚'
            ready=sum(1 for r in self._claimable_quests() if r['theme']==code)
            tile=tk.Frame(grid,bg='#E8F3EB',padx=10,pady=14,highlightthickness=1,highlightbackground='#CDE2D2')
            tile.grid(row=index//5,column=index%5,sticky='nsew',padx=5,pady=5)
            grid.grid_columnconfigure(index%5,weight=1)
            button=tk.Button(tile,text=f'{icon}\n{name}'+(f'\n🎁 {ready}' if ready else ''),
                             font=('Segoe UI Emoji',13,'bold'),bg='#E8F3EB',fg=DARK,bd=0,
                             cursor='hand2',command=lambda c=code,n=name:self._open_quest_theme(c,n))
            button.pack(fill='both',expand=True)

    def _open_quest_theme(self,theme,name):
        body=self.layout(f'🎁 Nhiệm vụ · {name}')
        sid=self.student['id']
        self.button(body,'← 5 chủ đề',self.level_achievements_page).pack(anchor='w',pady=(0,10))
        self.label(body,f'💎 Ngọc: {self.db.gems(sid)}  ·  Hoàn thành đúng 100% và nhanh hơn thời gian quy định.',12,True).pack(anchor='w',pady=9)
        quests=self._quests_for_theme(theme)
        if not quests:
            self.label(body,'Chủ đề này chưa có nhiệm vụ. Có thể tạo tại Quản lý nội dung → Quản lý Achievement.',12).pack(anchor='w')
            return
        grouped={}
        for q in quests:grouped.setdefault(int(q['level']),[]).append(q)
        content=tk.Frame(body,bg=BG);content.pack(fill='x')
        # Slide in quest cards from the right, staggered for a game-like reveal.
        cards=[]
        for level,items in sorted(grouped.items()):
            card=tk.Frame(content,bg='white',padx=13,pady=9,highlightthickness=1,highlightbackground='#D9E9DE')
            card.pack(fill='x',pady=6)
            self.label(card,f'⚔ Level {level}',13,True).pack(anchor='w',pady=(0,5))
            for q in items:
                count=self.db.level_achievement_count(sid,q['theme'],q['level'],q['max_seconds'],q.get('lesson'))
                claimed=self.db.conn.execute('SELECT 1 FROM achievement_claims WHERE student_id=? AND achievement_id=?',(sid,q['id'])).fetchone() is not None
                ready=count>=int(q['required']) and not claimed
                line=tk.Frame(card,bg='white');line.pack(fill='x',pady=3)
                title=q.get('title') or f"Lesson {q.get('lesson',1)} · Cấp {q['required']}"
                self.label(line,f"{title}   •   {count}/{q['required']} lượt   •   < {q['max_seconds']} giây",10,True).pack(side='left',fill='x',expand=True)
                def claim(item=q):
                    if self.db.claim_level_achievement(sid,item):
                        dialogs.showinfo('🎁 Nhận thưởng',f"Chúc mừng! Bạn nhận được {item['gems']} ngọc!",parent=self)
                    self._open_quest_theme(theme,name)
                color='#F2B400' if ready else '#96A7A0'
                bg='#FFF0B5' if ready else '#E7EEE9'
                tk.Button(line,text=f"{'✓ ' if claimed else ''}💎 {q['gems']}",command=claim,
                          state='normal' if ready else 'disabled',bg=bg,fg=color,
                          disabledforeground=color,bd=0,padx=12,pady=5,
                          font=('Segoe UI Emoji',11,'bold'),cursor='hand2' if ready else 'arrow').pack(side='right')
            cards.append(card)
        # Gentle reveal: the page itself remains scrollable and responsive.
        for i,card in enumerate(cards):
            card.after(20+i*25,lambda w=card:w.configure(highlightbackground='#8FC5A0') if w.winfo_exists() else None)

    def edit_level_achievements_page(self):
        body=self.layout('⚙ Quản lý Achievement')
        items=load_level_achievements()
        self.label(body,'Có thể thêm, sửa, xóa điều kiện. ID là duy nhất và nên giữ nguyên sau khi đã phát thưởng.',11).pack(anchor='w',pady=8)
        fields={}
        for key,label in [('id','Mã thành tựu'),('title','Tên thành tựu'),('theme','Mã chủ đề'),('level','Level'),('lesson','Lesson (1–10; để trống = legacy Level)'),('required','Số lần đạt'),('max_seconds','Thời gian tối đa (giây, dấu <)'),('gems','Ngọc thưởng')]:
            row=tk.Frame(body,bg='white');row.pack(fill='x',pady=3)
            tk.Label(row,text=label,bg='white',width=30,anchor='w').pack(side='left')
            field=tk.Entry(row,font=font_at(11));field.pack(side='left',fill='x',expand=True);fields[key]=field
        selected=[None]
        def load(i=None):
            selected[0]=i
            for key,w in fields.items():
                w.delete(0,'end')
                if i is not None:w.insert(0,str(items[i].get(key,'')))
        def save():
            try:
                a={k:w.get().strip() for k,w in fields.items()}
                for k in ('level','required','gems'):a[k]=int(a[k])
                a['lesson']=int(a['lesson']) if a['lesson'] else None
                a['max_seconds']=float(a['max_seconds'])
                if not all(a[k] for k in ('id','title','theme')) or a['level']<1 or a['required']<1 or a['max_seconds']<=0 or a['gems']<0 or (a['lesson'] is not None and not 1<=a['lesson']<=10):raise ValueError('Dữ liệu không hợp lệ.')
                if any(x['id']==a['id'] for j,x in enumerate(items) if j!=selected[0]):raise ValueError('Mã thành tựu đã tồn tại.')
                if selected[0] is None:items.append(a)
                else:items[selected[0]]=a
                save_level_achievements(items);self.edit_level_achievements_page()
            except (ValueError,OSError) as error:messagebox.showwarning('Không lưu được',str(error))
        def remove(i):
            if messagebox.askyesno('Xóa thành tựu','Xóa cấu hình này? Phần thưởng đã nhận vẫn được giữ.'):
                items.pop(i);save_level_achievements(items);self.edit_level_achievements_page()
        actions=tk.Frame(body,bg='white');actions.pack(anchor='w',pady=9)
        self.button(actions,'＋ Mới',lambda:load()).pack(side='left',padx=4)
        self.action_button(actions,'💾 Lưu',save).pack(side='left',padx=4)
        load()
        for i,a in enumerate(items):
            line=tk.Frame(body,bg='white');line.pack(fill='x',pady=2)
            self.label(line,f"{a.get('title',a['id'])} · {a['required']} lần · {a['max_seconds']}s · {a['gems']} ngọc",10).pack(side='left',fill='x',expand=True)
            self.button(line,'Sửa',lambda j=i:load(j)).pack(side='right',padx=3)
            self.button(line,'Xóa',lambda j=i:remove(j)).pack(side='right',padx=3)
        self.button(body,'← Quản lý nội dung',self.admin_manage_levels).pack(anchor='w',pady=12)

    def confirm_delete_profile(self, student):
        page=getattr(self,'_profile_page',None)
        if page and page.root.winfo_exists():page.confirm_delete(student)

    def choose(self, s):
        """Enter a profile without the Windows screenshot transition overlay."""
        self._remove_page_fade()
        self._page_transition_ready = False
        self.student = s
        try:
            self.choose_language()
        except Exception:
            self.student = None
            self.report_callback_exception(*sys.exc_info())
            # Do not retry automatically: a second navigation can hide the error.


    def home(self):
        """Dashboard UI using existing progress, quest and navigation APIs."""
        from home_ui import HomeDashboard
        body=self.layout('Trang chủ')
        self._home_dashboard=HomeDashboard(self,body)
        self._shell.animate_home_entry()

    def exam_page(self):
        import threading
        from exam_pygame import run_exam
        if getattr(self, '_exam_thread', None) and self._exam_thread.is_alive():
            dialogs.showinfo('Kiểm tra', 'Cửa sổ kiểm tra đang mở.')
            return
        import pygame_session_guard as guard
        if not guard.launch(run_exam, (self.data_dir, self.student['id'] if self.student else None), 'TuHocExamSDL'):
            dialogs.showinfo('Kiểm tra', 'Một cửa sổ bài tập hoặc kiểm tra đang mở.')

    #def exam_bank_editor(self):
       # from exam_editor import open_editor
        #open_editor(self,self.data_dir)

    def exam_bank_editor(self):
        from datetime import datetime
        from pathlib import Path
        import traceback

        log_dir = Path.home() / "CungHocCungVui_Logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "nhch_button_debug.log"

        def log(message):
            with log_file.open("a", encoding="utf-8") as f:
                f.write(
                    f"{datetime.now().isoformat()} | {message}\n"
                )

        log("BUTTON_CALLBACK_ENTER")

        try:
            from exam_editor import open_editor

            log("IMPORT_SUCCESS")

            result = open_editor(self, self.data_dir)

            log(
                f"OPEN_EDITOR_RETURNED | "
                f"pid={getattr(result, 'pid', None)}"
            )

        except Exception:
            log("ERROR:\n" + traceback.format_exc())
            raise

    def exercises_page(self):
        return self.topic_page()

    def do_exercise(self,ex):
        from exercise_focus_ui import exercise
        self._focus_exercise=exercise(self,ex)

    def save_vocab(self,w):
        self.db.save_word(self.student['id'],self.learning.wordkey(w['word']),w.get('meaning',''));dialogs.showinfo('Sổ từ','Đã lưu từ vào Flashcard.')

    def result(self,ex,correct,seconds):
        from exercise_focus_ui import result
        self._focus_exercise=result(self,ex,correct,seconds)

    def _language_words(self,due=False):
        items=self.db.words(self.student['id'],due=due)
        return [w for w in items if str(w['word']).startswith('[VI] ') == (self.lang=='vi')]

    def _flashcard_source_name(self,group):
        custom=self.db.deck_custom_name(self.student['id'],group) if self.student else None
        if custom:return custom
        kind=group['source_type'];theme=group['theme'];level=group['level']
        subject=next((t[1] for t in self._quest_themes() if t[0]==theme),theme)
        if kind in ('lesson','reading') and level:
            return f"{subject} · {'Bài học' if kind=='lesson' else 'Bài đọc'} Level {level}"
        return group['source_title'] or ('Từ lưu thủ công' if kind=='manual' else 'Bài học khác')

    def rename_flashcard_deck(self,group):
        from tkinter import simpledialog
        current=self._flashcard_source_name(group)
        name=simpledialog.askstring('Đổi tên bộ Flashcard','Tên mới cho bộ thẻ:',
                                    initialvalue=current,parent=self)
        if name is None:return
        try:self.db.rename_deck(self.student['id'],group,name)
        except ValueError as error:
            dialogs.showwarning('Tên không hợp lệ',str(error),parent=self);return
        self.flashcards()

    def delete_flashcard_deck(self,group):
        title=self._flashcard_source_name(group)
        if not dialogs.askyesno('Xóa bộ Flashcard',
                f'Xóa bộ thẻ “{title}” khỏi thư viện?\n\n'
                'Các từ còn thuộc bộ thẻ khác vẫn được giữ lại. '
                'Từ chỉ thuộc bộ này sẽ chuyển sang mục Từ đã lưu trước đây để tránh mất dữ liệu.',
                icon='warning',parent=self):return
        self.db.delete_deck(self.student['id'],group)
        self.flashcards()

    def _ux_hover_flashcard(self, card, normal='#D5E6DC'):
        """Highlight a card while pointer is anywhere inside its child widgets."""
        def refresh(_event=None):
            if not card.winfo_exists():
                return
            try:
                x, y = card.winfo_pointerxy()
                hovered = card.winfo_containing(x, y)
                inside = False
                while hovered is not None:
                    if hovered is card:
                        inside = True
                        break
                    hovered = hovered.master
                card.configure(highlightbackground=GREEN if inside else normal,
                               highlightthickness=2 if inside else 1)
            except tk.TclError:
                return
        def attach(widget):
            widget.bind('<Enter>', refresh, add='+')
            widget.bind('<Leave>', lambda e: widget.after_idle(refresh), add='+')
            for child in widget.winfo_children():
                attach(child)
        attach(card)

    def flashcards(self):
        body=self.layout('🃏 Flashcard · Thư viện ôn từ')
        words=self._language_words()
        groups=self.db.vocabulary_groups(self.student['id'])
        self.label(body,f'{len(words)} từ đã lưu · {len(groups)} bộ thẻ · Chọn bài để ôn riêng.',12).pack(anchor='w',pady=(0,12))
        self.button(body,'＋ Thêm từ thủ công',self.add_word_manual).pack(anchor='w',pady=(0,12))
        if not groups and not words:
            self.label(body,'Chưa có từ nào. Bôi đen từ trong bài học hoặc bài đọc, sau đó nhấn + để lưu.',12).pack(anchor='w',pady=12)
            return
        sections=[('lesson','📘 BÀI HỌC'),('reading','📖 BÀI ĐỌC'),('topic','📚 CHỦ ĐỀ KHÁC'),('manual','✍ TỪ LƯU THỦ CÔNG')]
        for kind,heading in sections:
            rows=[g for g in groups if g['source_type']==kind]
            if not rows:continue
            self.label(body,heading,14,True).pack(anchor='w',pady=(17,7))
            for g in rows:
                card=tk.Frame(body,bg='white',padx=17,pady=13,highlightbackground='#D5E6DC',highlightthickness=1)
                card.pack(fill='x',pady=5)
                self.label(card,self._flashcard_source_name(g),13,True).pack(side='left',fill='x',expand=True)
                self.button(card,'Ôn bài →',lambda a=g:self.flashcard_deck(a)).pack(side='right')
                tk.Button(card,text='🗑 Xóa',command=lambda a=g:self.delete_flashcard_deck(a),
                          bg='#FFF0EF',fg=TOKEN_COLORS['error'],bd=0,padx=10,pady=8,cursor='hand2').pack(side='right',padx=4)
                tk.Button(card,text='✎ Sửa tên',command=lambda a=g:self.rename_flashcard_deck(a),
                          bg=PALE,fg=DARK,bd=0,padx=10,pady=8,cursor='hand2').pack(side='right',padx=4)
                self.label(card,f"{g['total']} từ · {g['due']} đến hạn",10,color='#718678').pack(side='right',padx=14)
                self._ux_hover_flashcard(card)
        linked={w['id'] for g in groups for w in self.db.words_in_source(self.student['id'],g['source_type'],g['theme'],g['level'],g['source_title'])}
        legacy=[w for w in words if w['id'] not in linked]
        if legacy:
            self.label(body,'📦 TỪ ĐÃ LƯU TRƯỚC ĐÂY',14,True).pack(anchor='w',pady=(18,7))
            self.button(body,f'Ôn {len(legacy)} từ chưa phân loại →',lambda:self.flashcard_deck(None)).pack(anchor='w',pady=5)

    def _deck_words(self,group,due=False):
        if group is None:
            linked={r[0] for r in self.db.conn.execute('SELECT vocabulary_id FROM vocabulary_sources WHERE student_id=?',(self.student['id'],))}
            return [w for w in self._language_words(due=due) if w['id'] not in linked]
        return self.db.words_in_source(self.student['id'],group['source_type'],group['theme'],group['level'],group['source_title'],due=due)

    def flashcard_deck(self,group):
        words=self._deck_words(group)
        name=self._flashcard_source_name(group) if group is not None else 'Từ chưa phân loại'
        body=self.layout('🃏 '+name)
        self.button(body,'← Trở về thư viện Flashcard',self.flashcards).pack(anchor='w',pady=(0,15))
        if group is not None:
            controls=tk.Frame(body,bg=BG);controls.pack(anchor='w',pady=(0,10))
            tk.Button(controls,text='✎ Đổi tên bộ thẻ',command=lambda:self.rename_flashcard_deck(group),
                      bg=PALE,fg=DARK,bd=0,padx=12,pady=8,cursor='hand2').pack(side='left',padx=(0,8))
            tk.Button(controls,text='🗑 Xóa bộ thẻ',command=lambda:self.delete_flashcard_deck(group),
                      bg='#FFF0EF',fg=TOKEN_COLORS['error'],bd=0,padx=12,pady=8,cursor='hand2').pack(side='left')
        due=self._deck_words(group,due=True)
        self.label(body,f'{len(words)} từ trong bộ · {len(due)} từ đến hạn ôn',13,True).pack(anchor='w',pady=6)
        if words:
            self.button(body,'▶ Ôn bộ thẻ này',lambda g=group:self.review_card(0,g,False)).pack(anchor='w',pady=9)
            if due:self.button(body,'⏰ Chỉ ôn từ đến hạn',lambda g=group:self.review_card(0,g,True)).pack(anchor='w',pady=6)
        for w in words:
            card=tk.Frame(body,bg='white',padx=15,pady=10,highlightthickness=1,highlightbackground='#E0E9E2')
            card.pack(fill='x',pady=4)
            clean=str(w['word']).removeprefix('[VI] ')
            self.label(card,clean,12,True).pack(side='left',padx=(0,15))
            if w['meaning']:self.label(card,w['meaning'],11,color='#718678').pack(side='left')
            self._ux_hover_flashcard(card, '#E0E9E2')

    def add_word_manual(self):
        from tkinter import simpledialog
        word=simpledialog.askstring('Lưu từ vựng','Nhập từ cần ghi nhớ:',parent=self)
        if not word or not word.strip():return
        word=word.strip()
        meaning=self.curriculum.meaning(word) if self.lang=='en' else ''
        if self.lang=='en' and not meaning:
            meaning=simpledialog.askstring('Nghĩa của từ',f'Nhập nghĩa cho “{word}”:',parent=self)
            if meaning is None:return
        self.db.save_word_in_source(self.student['id'],self.learning.wordkey(word),meaning,'manual')
        self.flashcards()

    def review_card(self,index,group=None,due_only=True):
        words=self._deck_words(group,due=due_only)
        if not words:
            self.flashcard_deck(group);return
        word=words[min(index,len(words)-1)]
        body=self.layout('Ôn Flashcard · '+(self._flashcard_source_name(group) if group is not None else 'Từ chưa phân loại'))
        self.button(body,'← Trở về thư viện Flashcard',self.flashcards).pack(anchor='w',pady=(0,8))
        self.button(body,'← Trở về bộ thẻ',lambda:self.flashcard_deck(group)).pack(anchor='w',pady=(0,12))
        self.label(body,f'Thẻ {min(index,len(words)-1)+1}/{len(words)}',12).pack(anchor='w',pady=10)
        clean=str(word['word']).removeprefix('[VI] ')
        self.label(body,clean,28,True).pack(anchor='center',pady=25)
        self.action_button(body,'🔊 Phát âm',lambda:self._speak(clean)).pack(pady=5)
        answer=self.label(body,'Nhấn lật thẻ để xem nghĩa',15);answer.pack(pady=8)
        self.button(body,'Lật thẻ',lambda:answer.config(text=word['meaning'] or 'Từ đã lưu')).pack(pady=8)
        row=tk.Frame(body,bg=BG);row.pack(pady=20)
        for rating,name in [('again','Chưa nhớ'),('hard','Hơi nhớ'),('good','Đã nhớ')]:
            self.button(row,name,lambda r=rating,w=word['id'],i=index,g=group,d=due_only:self.rate_card(w,r,i,g,d)).pack(side='left',padx=7)

    def rate_card(self,word_id,rating,index=0,group=None,due_only=True):
        self.db.review(self.student['id'],word_id,rating)
        remaining=self._deck_words(group,due=due_only)
        if not remaining:self.flashcard_deck(group)
        elif not due_only and index+1>=len(remaining):self.flashcard_deck(group)
        else:self.review_card(index%len(remaining) if due_only else index+1,group,due_only)

    def statistics(self):
        body=self.layout('Thống kê học tập')
        stats=self.db.stats(self.student['id'])
        from exam_history_bridge import exam_records
        exam_rows=exam_records(self.db.conn, self.student['id']) if hasattr(self.db, 'conn') else []
        if not stats and not exam_rows:
            self.label(body,'Chưa có kết quả học tập. Em hãy thử làm bài nhé!').pack(anchor='w')
            return
        if exam_rows:
            total_questions=sum(row[6] for row in exam_rows)
            correct_questions=sum(row[5] for row in exam_rows)
            self.label(body, f'Kiểm tra: {len(exam_rows)} lượt · Đúng {correct_questions}/{total_questions} câu · '
                             f'Tỷ lệ {correct_questions*100/total_questions:.1f}%', 12).pack(anchor='w',pady=9)
        for s in stats:
            total=s['total'];good=s['correct'] or 0;bad=s['wrong'] or 0
            self.label(body,f'{s["exercise_type"]}: {total} lượt · Đúng {good} · Sai {bad} · Chờ chấm {total-good-bad} · {s["minutes"]} phút',12).pack(anchor='w',pady=9)
        self.label(body,'Số liệu dựa trên các lượt làm bài đã lưu. Các bài chờ chấm không tính là đúng hoặc sai.',10,color='#647567').pack(anchor='w',pady=16)


install_navigation_profiler(App)

if __name__=='__main__':
    App().mainloop()
