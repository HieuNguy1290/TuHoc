"""Vietnamese dictation from local MP3/WAV with user-editable answer key.

No network required. Dictation content is separate from level content.
"""
from tuhoc.paths import PROJECT_ROOT
from pathlib import Path
import json
import re
import shutil
import sys
import unicodedata
import tkinter as tk
import subprocess
import threading
import queue
import shutil as shutil_module
from array import array
from tkinter import filedialog, messagebox
from difflib import SequenceMatcher

DEFAULT_ITEMS = [
    {"id":"ct001", "title":"Bài 1 - Buổi sáng ở Sài Gòn", "audio":"audio/ct001.mp3", "answer":"Sáng nay, má dẫn em ra chợ. Hai má con ghé mua trái cây.", "note":"Thêm file MP3 tương ứng hoặc đổi đường dẫn trong giao diện."},
    {"id":"ct002", "title":"Bài 2 - Ghé thăm bà ngoại", "audio":"audio/ct002.mp3", "answer":"Chiều thứ bảy, anh Hai chở em qua thăm ngoại.", "note":"Thêm file MP3 tương ứng hoặc đổi đường dẫn trong giao diện."}
]


def text_tokens(text):
    text=unicodedata.normalize('NFC',str(text)).casefold()
    return re.findall(r'[^\W_]+',text,flags=re.UNICODE)


def _canonical_tokens(text, equivalences):
    """Replace explicitly authorized equivalent phrases with one comparison token.

    Sort by length so a longer expression wins over an overlapping short one.
    No automatic contraction expansion: e.g. 'he\'s' may mean 'he has'.
    """
    tokens=text_tokens(text)
    groups=[]
    for index, group in enumerate(equivalences or []):
        if not isinstance(group,(list,tuple)) or len(group)<2:
            continue
        for phrase in group:
            phrase_tokens=text_tokens(phrase)
            if phrase_tokens:
                groups.append((phrase_tokens, f'__equiv_{index}__'))
    groups.sort(key=lambda x:len(x[0]),reverse=True)
    output=[];i=0
    while i<len(tokens):
        found=next(((v,len(t)) for t,v in groups if tokens[i:i+len(t)]==t),None)
        if found:
            output.append(found[0]);i+=found[1]
        else:
            output.append(tokens[i]);i+=1
    return output


def check_dictation(expected, given, accepted_variants=None, equivalences=None):
    """Accent-sensitive word comparison, punctuation and casing ignored."""
    # A whole-answer variant is an alternative reference text; the highest score wins.
    candidates=[expected]+list(accepted_variants or [])
    if len(candidates)>1:
        results=[check_dictation(ref,given,equivalences=equivalences) for ref in candidates]
        best=max(results,key=lambda r:(r['passed'],r['score'],-len(r['issues'])))
        return dict(best, accepted_reference=candidates[results.index(best)])
    reference=_canonical_tokens(expected,equivalences)
    actual=_canonical_tokens(given,equivalences)
    matcher=SequenceMatcher(a=reference,b=actual,autojunk=False)
    correct=sum(block.size for block in matcher.get_matching_blocks())
    total=max(len(reference),1)
    issues=[]
    for tag,a,b,c,d in matcher.get_opcodes():
        if tag=='equal':continue
        issues.append({'kind':tag,'expected':' '.join(reference[a:b]),'written':' '.join(actual[c:d])})
    return {'score':round(100*correct/total,1),'matched':correct,'total':len(reference),'issues':issues,
            'passed':len(reference)>0 and reference==actual}



# Decode only a low-rate mono preview for lightweight waveform visualization.
_WAVE_CACHE = {}

def waveform_peaks(path, bars=320):
    """Return 0..1 peak levels derived from the real MP3/WAV waveform.

    The preview uses ffmpeg to decode the actual audio file to a mono PCM stream,
    then samples peak values per bar. The shaping keeps transients sharp so the UI
    looks closer to a modern editing/player waveform instead of rounded equalizer bars.
    """
    source = Path(path)
    stat = source.stat()
    key = (str(source.resolve()), stat.st_mtime_ns, stat.st_size, bars)
    if key in _WAVE_CACHE:
        return _WAVE_CACHE[key]
    ffmpeg = shutil_module.which('ffmpeg')
    if not ffmpeg:
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except (ImportError, OSError):
            return None
    command = [ffmpeg, '-nostdin', '-v', 'error', '-i', str(source), '-vn',
               '-ac', '1', '-ar', '1000', '-f', 's16le', '-acodec', 'pcm_s16le', 'pipe:1']
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=45, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0 or len(result.stdout) < 2:
        return None
    samples = array('h')
    samples.frombytes(result.stdout[:len(result.stdout) // 2 * 2])
    if not samples:
        return None
    size = len(samples)
    raw_peaks = []
    for index in range(bars):
        a = int(index * size / bars)
        b = max(a + 1, int((index + 1) * size / bars))
        chunk = samples[a:b]
        peak = max(abs(v) for v in chunk) / 32768
        raw_peaks.append(peak)
    if not raw_peaks:
        return None
    sorted_peaks = sorted(raw_peaks)
    ref = sorted_peaks[max(0, int(len(sorted_peaks) * 0.96) - 1)] or max(raw_peaks) or 1.0
    floor = min(raw_peaks)
    span = max(ref - floor, 1e-6)
    shaped = []
    for value in raw_peaks:
        normalized = max(0.0, min(1.0, (value - floor) / span))
        # Keep the waveform crisp: lower values remain visible but peaks stay sharp.
        shaped.append(max(0.06, normalized ** 1.18))
    if len(_WAVE_CACHE) > 25:
        _WAVE_CACHE.clear()
    _WAVE_CACHE[key] = shaped
    return shaped


class WaveformSeek(tk.Canvas):
    """Seekable waveform with current-time progress and hover-time tooltip."""
    def __init__(self, parent, seek_callback, bg='#FFFFFF', **kwargs):
        super().__init__(parent, bg=bg, bd=0, highlightthickness=0, height=96,
                         cursor='hand2', **kwargs)
        self.peaks = [0.12] * 320
        self.loaded = False
        self.position = 0.
        self.duration_ms = 0
        self.seek_callback = seek_callback
        self.hover_x = None
        self.bind('<Configure>', lambda _event: self.redraw())
        self.bind('<Motion>', self._hover)
        self.bind('<Leave>', self._leave)
        self.bind('<Button-1>', self._seek)
        self.bind('<B1-Motion>', self._seek)

    def set_peaks(self, peaks):
        self.loaded = bool(peaks)
        self.peaks = list(peaks) if peaks else [0.12] * 320
        self.redraw()

    def set_progress(self, current_ms, duration_ms):
        fraction = min(1., max(0., current_ms / duration_ms)) if duration_ms else 0.
        self.duration_ms = duration_ms
        if abs(fraction - self.position) > .0001:
            self.position = fraction
            self.redraw()

    def _fraction(self, x):
        return min(1., max(0., (x - 10) / max(1, self.winfo_width() - 20)))

    def _seek(self, event):
        self.hover_x = event.x
        self.position = self._fraction(event.x)
        self.redraw()
        self.seek_callback(self.position)

    def _hover(self, event):
        x = min(self.winfo_width() - 10, max(10, event.x))
        if self.hover_x != x:
            self.hover_x = x
            self.redraw()

    def _leave(self, _event):
        self.hover_x = None
        self.redraw()

    def _draw_segments(self, points, color, width=1):
        if len(points) < 2:
            return
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            self.create_line(x1, y1, x2, y2, fill=color, width=width)

    def redraw(self):
        self.delete('all')
        width = max(40, self.winfo_width())
        height = max(60, self.winfo_height())
        left, right = 10, width - 10
        top, bottom = 18, height - 22
        center = (top + bottom) / 2
        usable_height = (bottom - top) / 2 - 2
        progressed_x = left + self.position * (right - left)
        self.create_rectangle(left, top, right, bottom, fill='#F8FBF9', outline='')
        self.create_line(left, center, right, center, fill='#E8F0EC', width=1)

        count = len(self.peaks)
        if count <= 1:
            return
        step = (right - left) / (count - 1)
        played_top = []
        played_bottom = []
        future_top = []
        future_bottom = []
        for index, value in enumerate(self.peaks):
            x = left + index * step
            amplitude = max(4, usable_height * value)
            top_pt = (x, center - amplitude)
            bottom_pt = (x, center + amplitude)
            if x <= progressed_x:
                played_top.append(top_pt)
                played_bottom.append(bottom_pt)
            else:
                future_top.append(top_pt)
                future_bottom.append(bottom_pt)
        if played_top and future_top:
            join_x = progressed_x
            if played_top[-1][0] != join_x:
                last_played = played_top[-1]
                next_future = future_top[0]
                ratio = 0 if next_future[0] == last_played[0] else (join_x - last_played[0]) / (next_future[0] - last_played[0])
                amp_top = last_played[1] + ratio * (next_future[1] - last_played[1])
                last_played_b = played_bottom[-1]
                next_future_b = future_bottom[0]
                amp_bottom = last_played_b[1] + ratio * (next_future_b[1] - last_played_b[1])
                played_top.append((join_x, amp_top))
                played_bottom.append((join_x, amp_bottom))
                future_top.insert(0, (join_x, amp_top))
                future_bottom.insert(0, (join_x, amp_bottom))
        if future_top:
            self._draw_segments(future_top, '#CDD8D2', width=1)
            self._draw_segments(future_bottom, '#CDD8D2', width=1)
        if played_top:
            self._draw_segments(played_top, '#1F8A70', width=2)
            self._draw_segments(played_bottom, '#1F8A70', width=2)
        self.create_line(progressed_x, top - 4, progressed_x, bottom + 4,
                         fill='#146C5A', width=2)
        self.create_oval(progressed_x - 5, center - 5, progressed_x + 5, center + 5,
                         fill='#146C5A', outline='white', width=1)
        if self.hover_x is not None and self.duration_ms:
            x = min(right, max(left, self.hover_x))
            self.create_line(x, top - 1, x, bottom + 1,
                             fill='#F59E0B', width=1, dash=(3, 3))
            seconds = int(self._fraction(x) * self.duration_ms / 1000)
            label = f'{seconds // 60:02d}:{seconds % 60:02d}'
            label_x = min(right - 18, max(left + 18, x))
            self.create_rectangle(label_x - 21, 1, label_x + 21, 19,
                                  fill='#163C2A', outline='')
            self.create_text(label_x, 10, text=label, fill='white',
                             font=('Segoe UI', 9))
        if not self.loaded:
            self.create_text(width / 2, height - 7, text='Đang phân tích waveform từ file nghe…',
                             fill='#667D70', font=('Segoe UI', 9))

def should_show_floating_audio(inline_bottom, viewport_top, scroll_offset, margin=8):
    """Show compact player only after scrolling the main controls above view."""
    return scroll_offset > margin and inline_bottom <= viewport_top + margin


class ModernAudioControls(tk.Canvas):
    """Borderless player controls matching their surrounding background.

    Tk Canvas has no per-pixel alpha background; using the parent color gives
    the desired transparent appearance without an opaque black panel.
    """
    def __init__(self, parent, on_back, on_play, on_forward, on_repeat, **kwargs):
        super().__init__(parent, height=116, bg=parent.cget('bg'), bd=0,
                         highlightthickness=0, cursor='hand2', **kwargs)
        self.on_back=on_back
        self.on_play=on_play
        self.on_forward=on_forward
        self.on_repeat=on_repeat
        self.playing=False
        self.mode='once'
        self.targets={}
        self.bind('<Configure>', lambda _e: self.redraw())
        self.bind('<Button-1>', self._click)
        self.redraw()

    def _round_rect(self, x1,y1,x2,y2,r,fill):
        # Smooth polygon is supported by the standard Tk Canvas.
        coords=(x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,
                x2,y2,x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1)
        self.create_polygon(coords, smooth=True, splinesteps=16, fill=fill, outline='')

    def set_state(self, playing, mode):
        if self.playing!=playing or self.mode!=mode:
            self.playing=playing; self.mode=mode; self.redraw()

    def redraw(self):
        self.delete('all')
        w=max(300,self.winfo_width())
        cx=w/2
        # Icon row: back five seconds / play-pause / forward five seconds.
        self.targets={
            'back':(cx-86,6,cx-48,46),
            'play':(cx-22,3,cx+22,47),
            'forward':(cx+48,6,cx+86,46),
            'once':(cx-92,67,cx,103),
            'loop':(cx,67,cx+92,103),
        }
        self.create_oval(cx-22,3,cx+22,47,fill='#F2F3F4',outline='')
        self.create_text(cx-67,25,text='↶',fill='#285B48',font=('Segoe UI Symbol',22))
        self.create_text(cx+67,25,text='↷',fill='#285B48',font=('Segoe UI Symbol',22))
        self.create_text(cx,25,text='Ⅱ' if self.playing else '▶',
                         fill='#111214',font=('Segoe UI Symbol',19,'bold'))
        # segmented repeat selector
        if self.mode=='once':
            self._round_rect(cx-92,67,cx,103,18,'#DDECE3')
        else:
            self._round_rect(cx,67,cx+92,103,18,'#DDECE3')
        self.create_text(cx-46,85,text='Phát 1 lần',
                         fill='#185E43' if self.mode=='once' else '#4D6357',
                         font=('Segoe UI',10,'bold' if self.mode=='once' else 'normal'))
        self.create_text(cx+46,85,text='Lặp liên tục',
                         fill='#185E43' if self.mode=='loop' else '#4D6357',
                         font=('Segoe UI',10,'bold' if self.mode=='loop' else 'normal'))

    def _click(self, event):
        for key,(x1,y1,x2,y2) in self.targets.items():
            if x1<=event.x<=x2 and y1<=event.y<=y2:
                if key=='back': self.on_back()
                elif key=='play': self.on_play()
                elif key=='forward': self.on_forward()
                else: self.on_repeat(key)
                break


class MP3Player:
    """MP3 playback with position, duration, pause and seek (Windows MCI)."""
    def __init__(self):
        self.alias='tuhoc_dictation';self.active=False;self.paused=False
        self._pygame=False;self._duration=0;self._offset=0;self._started=0

    def _mci(self, command, query=False):
        import ctypes
        buffer=ctypes.create_unicode_buffer(256) if query else None
        err=ctypes.windll.winmm.mciSendStringW(command,buffer,256 if query else 0,None)
        if err:
            text=ctypes.create_unicode_buffer(256)
            ctypes.windll.winmm.mciGetErrorStringW(err,text,256)
            raise RuntimeError(f'Lỗi phát MP3 ({err}): {text.value}')
        return buffer.value if query else ''

    def play(self,path):
        self.stop()
        path=Path(path).resolve()
        if not path.is_file():raise FileNotFoundError('Không tìm thấy file nghe: '+str(path))
        if sys.platform=='win32':
            try:
                kind=' type mpegvideo' if path.suffix.lower()=='.mp3' else ''
                self._mci(f'open "{path}"{kind} alias {self.alias}')
                self.active=True
                self._mci(f'set {self.alias} time format milliseconds')
                self._duration=int(self._mci(f'status {self.alias} length',True))
                self._mci(f'play {self.alias} from 0')
            except Exception:
                self.stop();raise
        else:
            try:
                import pygame
            except ImportError as exc:raise RuntimeError('Cài pygame: pip install pygame') from exc
            if not pygame.mixer.get_init():pygame.mixer.init()
            pygame.mixer.music.load(str(path));pygame.mixer.music.play()
            self._pygame=True;self.active=True
            self._duration=0
            try:
                from mutagen import File
                metadata=File(path)
                if metadata and metadata.info:self._duration=int(metadata.info.length*1000)
            except (ImportError,OSError,ValueError):pass
            self._offset=0
        self.paused=False

    def duration_ms(self):return max(0,self._duration)

    def position_ms(self):
        if not self.active:return 0
        if sys.platform=='win32':
            try:return max(0,int(self._mci(f'status {self.alias} position',True)))
            except RuntimeError:return 0
        import pygame
        position=pygame.mixer.music.get_pos()
        return max(0,self._offset+(position if position>=0 else 0))

    def is_finished(self):
        if not self.active or self.paused:return False
        if sys.platform=='win32':
            try:return self._mci(f'status {self.alias} mode',True).lower()=='stopped'
            except RuntimeError:return False
        import pygame
        return not pygame.mixer.music.get_busy()

    def pause(self):
        if not self.active or self.paused:return
        if sys.platform=='win32':self._mci(f'pause {self.alias}')
        else:
            import pygame
            pygame.mixer.music.pause()
        self.paused=True

    def resume(self):
        if not self.active or not self.paused:return
        if sys.platform=='win32':self._mci(f'resume {self.alias}')
        else:
            import pygame
            pygame.mixer.music.unpause()
        self.paused=False

    def seek(self,ms):
        if not self.active:return
        ms=max(0,min(int(ms),self._duration)) if self._duration else max(0,int(ms))
        if sys.platform=='win32':
            self._mci(f'play {self.alias} from {ms}')
            if self.paused:self._mci(f'pause {self.alias}')
        else:
            import pygame
            pygame.mixer.music.play(start=ms/1000.)
            if self.paused:pygame.mixer.music.pause()
            self._offset=ms

    def stop(self):
        if not self.active:return
        if self._pygame:
            import pygame
            pygame.mixer.music.stop()
        elif sys.platform=='win32':
            try:self._mci(f'close {self.alias}')
            except RuntimeError:pass
        self.active=False;self.paused=False;self._pygame=False


class DictationMixin:
    def _dictation_paths(self):
        # The selected subject owns its own MP3s and answer key, next to main.py.
        lang = 'vi' if getattr(self,'lang','en') == 'vi' else 'en'
        folder = PROJECT_ROOT / 'mon_hoc' / ('tieng_viet' if lang == 'vi' else 'tieng_anh') / 'dictation'
        folder.mkdir(parents=True,exist_ok=True)
        (folder/'audio').mkdir(exist_ok=True)
        key=folder/'dap_an_chinh_ta.json'
        if not key.exists():
            # Migrate the previous Vietnamese dictation content only once.
            old=Path(self.data_dir)/'vi'/'dictation'
            if lang=='vi' and (old/'dap_an_chinh_ta.json').is_file():
                shutil.copy2(old/'dap_an_chinh_ta.json',key)
                if (old/'audio').is_dir():
                    for audio_file in (old/'audio').iterdir():
                        if audio_file.is_file() and not (folder/'audio'/audio_file.name).exists():
                            shutil.copy2(audio_file,folder/'audio'/audio_file.name)
            else:
                defaults=DEFAULT_ITEMS if lang=='vi' else []
                key.write_text(json.dumps({'schema_version':'1.1','language':lang,'items':defaults},ensure_ascii=False,indent=2),encoding='utf-8')
        return folder,key

    def _load_dictation(self):
        folder,key=self._dictation_paths()
        try:
            data=json.loads(key.read_text(encoding='utf-8-sig'))
            items=data.get('items')
            if not isinstance(items,list):raise ValueError('items phải là danh sách')
            seen=set()
            for i,item in enumerate(items,1):
                if not isinstance(item,dict) or any(not str(item.get(k,'')).strip() for k in ('id','title','audio','answer')):
                    raise ValueError(f'Dòng {i} thiếu id, title, audio hoặc answer')
                if item['id'] in seen:raise ValueError(f'ID trùng: {item["id"]}')
                seen.add(item['id'])
                variants=item.get('accepted_variants',[])
                equiv=item.get('equivalences',[])
                if not isinstance(variants,list) or any(not isinstance(x,str) or not x.strip() for x in variants):
                    raise ValueError(f'Dòng {i}: accepted_variants phải là danh sách câu trả lời')
                if not isinstance(equiv,list) or any(not isinstance(g,list) or len(g)<2 or any(not isinstance(v,str) or not v.strip() for v in g) for g in equiv):
                    raise ValueError(f'Dòng {i}: equivalences phải là danh sách nhóm có từ hai cách viết trở lên')
            return items
        except (OSError,ValueError,TypeError) as exc:
            messagebox.showerror('Luyện tập mỗi ngày!')
            return []

    def _audio_path(self, value):
        folder,_=self._dictation_paths()
        path=Path(value)
        # Accept explicit absolute local path, or relative path rooted at the dictation folder.
        return path.resolve() if path.is_absolute() else (folder/path).resolve()

    def dictation_page(self):
        body=self.layout('🎧 CHÉP CHÍNH TẢ • '+('TIẾNG VIỆT' if self.lang=='vi' else 'TIẾNG ANH'))
        self.label(body,'Nghe file MP3, chép lại vào ô trả lời, rồi kiểm tra với đáp án đã lưu.',12).pack(anchor='w',pady=6)
        items=self._load_dictation();folder,key=self._dictation_paths()
        for item in items:
            card=tk.Frame(body,bg='white',padx=16,pady=13);card.pack(fill='x',pady=6)
            self.label(card,item['title'],15,True).pack(anchor='w')
            exists=self._audio_path(item['audio']).is_file()
            self.label(card,('✓ Đã có file nghe' if exists else '⚠ Chưa có MP3: '+item['audio']),10,color='#247D55' if exists else '#B45D26').pack(anchor='w')
            self.button(card,'VÀO CHÉP CHÍNH TẢ →',lambda item=item:self.dictation_exercise(item['id'])).pack(anchor='w',pady=7)
        row=tk.Frame(body,bg=body['bg']);row.pack(anchor='w',pady=14)
        self.button(row,'＋ Tạo bài nghe / nhập đáp án',self.dictation_editor).pack(side='left',padx=(0,8))
        self.action_button(row,'📁 Mở thư mục file nghe',self.dictation_folder).pack(side='left')
        self.label(body,'File đáp án: '+str(key),10).pack(anchor='w',pady=5)

    def dictation_folder(self):
        folder,_=self._dictation_paths()
        import os
        if sys.platform=='win32':os.startfile(str(folder))
        else:messagebox.showinfo('Thư mục file nghe',str(folder))

    def dictation_editor(self, item_id=None):
        items=self._load_dictation()
        old=next((x for x in items if x['id']==item_id),{})
        body=self.layout('✎ TẠO / SỬA BÀI CHÉP CHÍNH TẢ')
        folder,key=self._dictation_paths()
        self.label(body,'Nhập tên bài, đường dẫn MP3 và đáp án chuẩn. Có thể bấm Chọn MP3 để sao chép file vào ứng dụng.',12).pack(anchor='w',pady=9)
        idval=tk.StringVar(value=old.get('id',f'ct{len(items)+1:03d}'))
        title=tk.StringVar(value=old.get('title',''))
        audio=tk.StringVar(value=old.get('audio',''))
        for caption,var in [('Mã bài (duy nhất)',idval),('Tên bài học',title),('Đường dẫn MP3 (ví dụ audio/ct003.mp3)',audio)]:
            self.label(body,caption,11,True).pack(anchor='w',pady=(10,2))
            tk.Entry(body,textvariable=var,font=('Segoe UI',12),width=75).pack(anchor='w',fill='x')
        def browse():
            selected=filedialog.askopenfilename(title='Chọn file nghe',filetypes=[('MP3/WAV','*.mp3 *.wav'),('Tất cả','*.*')])
            if not selected:return
            source=Path(selected)
            if source.suffix.lower() not in ('.mp3','.wav'):
                messagebox.showwarning('Định dạng','Chỉ chọn MP3 hoặc WAV.');return
            target=folder/'audio'/source.name
            if source.resolve()!=target.resolve():
                if target.exists() and not messagebox.askyesno('Trùng tên','File đã tồn tại. Ghi đè?'):return
                shutil.copy2(source,target)
            audio.set('audio/'+target.name)
        self.action_button(body,'📎 Chọn MP3 và sao chép vào ứng dụng',browse).pack(anchor='w',pady=9)
        self.label(body,'Đáp án chính tả (giữ dấu khi dùng tiếng Việt)',11,True).pack(anchor='w',pady=(9,3))
        answer=tk.Text(body,height=7,font=('Segoe UI',13),wrap='word',undo=True)
        answer.pack(fill='x');answer.insert('1.0',old.get('answer',''))
        self.label(body,'Đáp án nguyên bài khác (mỗi dòng một đáp án, không bắt buộc)',11,True).pack(anchor='w',pady=(12,3))
        variants_box=tk.Text(body,height=4,font=('Segoe UI',12),wrap='word')
        variants_box.pack(fill='x')
        variants_box.insert('1.0','\n'.join(old.get('accepted_variants',[])))
        self.label(body,'Các cách viết tương đương (mỗi dòng: he is | he\'s)',11,True).pack(anchor='w',pady=(12,3))
        equiv_box=tk.Text(body,height=4,font=('Segoe UI',12),wrap='word')
        equiv_box.pack(fill='x')
        equiv_box.insert('1.0','\n'.join(' | '.join(g) for g in old.get('equivalences',[])))
        def save():
            fields={'id':idval.get().strip(),'title':title.get().strip(),'audio':audio.get().strip(),
                    'answer':answer.get('1.0','end').strip()}
            fields['accepted_variants']=[v.strip() for v in variants_box.get('1.0','end').splitlines() if v.strip()]
            raw_groups=[line.strip() for line in equiv_box.get('1.0','end').splitlines() if line.strip()]
            groups=[[v.strip() for v in line.split('|') if v.strip()] for line in raw_groups]
            # A single expression is a valid alternative whole-answer entry, not a save error.
            fields['accepted_variants'].extend(g[0] for g in groups if len(g)==1)
            fields['equivalences']=[g for g in groups if len(g)>=2]
            required=('id','title','audio','answer')
            missing=[name for name in required if not fields[name]]
            if missing:
                labels={'id':'Mã bài','title':'Tên bài','audio':'Đường dẫn MP3','answer':'Đáp án chuẩn'}
                messagebox.showwarning('Thiếu nội dung','Cần nhập: '+', '.join(labels[name] for name in missing));return
            if not fields['audio'].lower().endswith(('.mp3','.wav')):messagebox.showwarning('File nghe','Đường dẫn phải kết thúc bằng .mp3 hoặc .wav');return
            if any(x['id']==fields['id'] and x['id']!=item_id for x in items):messagebox.showwarning('Mã trùng','Đổi mã bài khác.');return
            result=[fields if x['id']==item_id else x for x in items] if item_id else items+[fields]
            with key.open('w',encoding='utf-8') as f:json.dump({'schema_version':'1.0','items':result},f,ensure_ascii=False,indent=2)
            messagebox.showinfo('Đã lưu','Đã lưu đáp án vào '+str(key));self.dictation_page()
        self.action_button(body,'💾 LƯU BÀI CHÉP CHÍNH TẢ',save).pack(anchor='w',pady=14)

    def dictation_exercise(self,item_id):
        items=self._load_dictation()
        index=next((i for i,item in enumerate(items) if item['id']==item_id),None)
        if index is None:return self.dictation_page()
        item=items[index]
        body=self.layout('🎧 '+item['title'])
        audio=self._audio_path(item['audio'])
        self.label(body,'Nghe file MP3 và chép lại. Có thể tạm dừng, tua và chọn lặp lại.',12).pack(anchor='w',pady=8)

        player_frame=tk.Frame(body,bg=body.cget('bg'),padx=16,pady=14)
        player_frame.pack(fill='x',pady=8)
        self.label(player_frame,'🎵 '+Path(item['audio']).name,14,True).pack(anchor='w')
        player=getattr(self,'dictation_audio',None)
        if player is None:self.dictation_audio=player=MP3Player()
        repeat=tk.StringVar(value=getattr(self,'dictation_repeat_mode','once'))
        paused_label=tk.StringVar(value='▶ PHÁT MP3')
        time_label=tk.StringVar(value='00:00 / 00:00')
        alive=[True]
        def fmt(ms):
            secs=max(0,int(ms)//1000)
            return f'{secs//60:02d}:{secs%60:02d}'
        def sync_controls():
            state=bool(player.active and not player.paused)
            controls.set_state(state, repeat.get())
            floating_controls.set_state(state, repeat.get())
        def pause_or_play():
            try:
                if not player.active or player.is_finished():
                    player.play(audio)
                elif player.paused:player.resume()
                else:player.pause()
                paused_label.set('▶ TIẾP TỤC' if player.paused else '⏸ TẠM DỪNG')
            except (RuntimeError,OSError,ValueError) as exc:
                messagebox.showerror('Không phát được âm thanh',str(exc))
            sync_controls()
        def stop():
            player.stop();paused_label.set('▶ PHÁT MP3');wave.set_progress(0,player.duration_ms())
            time_label.set(f'00:00 / {fmt(player.duration_ms())}')
            sync_controls()
        def skip(seconds):
            try:
                if not player.active: player.play(audio)
                player.seek(max(0,min(player.duration_ms(),player.position_ms()+seconds*1000)))
                paused_label.set('▶ TIẾP TỤC' if player.paused else '⏸ TẠM DỪNG')
            except (RuntimeError,OSError,ValueError) as exc:
                messagebox.showerror('Không tua được',str(exc))
            sync_controls()
        def switch_repeat(mode):
            repeat.set(mode)
            self.dictation_repeat_mode=mode
            sync_controls()
        controls=ModernAudioControls(player_frame,lambda:skip(-5),pause_or_play,
                                      lambda:skip(5),switch_repeat)
        controls.pack(fill='x',pady=(9,9))
        controls.set_state(False,repeat.get())
        # Overlay belongs to the viewport canvas, not to the scrolling body.
        # It is only visible after the inline controls leave the viewport.
        viewport=getattr(self,'active_scroll_canvas',None)
        floating_controls=ModernAudioControls(viewport,lambda:skip(-5),pause_or_play,
                                              lambda:skip(5),switch_repeat)
        floating_controls.place_forget()
        floating_controls.set_state(False,repeat.get())
        def update_floating_visibility():
            # Only place the overlay once layout geometry is established. Never
            # show a duplicate mini-player before the original scrolls away.
            if (not alive[0] or getattr(self, 'active_scroll_canvas', None) is not viewport
                    or viewport is None or not viewport.winfo_exists()
                    or not controls.winfo_exists()):
                return
            if (not viewport.winfo_ismapped() or not controls.winfo_ismapped()
                    or viewport.winfo_height() < 150 or controls.winfo_height() < 40):
                floating_controls.place_forget()
                return
            viewport_top=viewport.winfo_rooty()
            inline_bottom=controls.winfo_rooty()+controls.winfo_height()
            scroll_offset=viewport.canvasy(0)
            if should_show_floating_audio(inline_bottom,viewport_top,scroll_offset):
                floating_controls.place(relx=1.0,rely=1.0,anchor='se',
                                        x=-16,y=-16,width=260,height=116)
                # Canvas.lift() is aliased to tag_raise and expects a Canvas tag.
                # Raising the widget window instead avoids TclError on Windows.
                floating_controls.tk.call('raise', floating_controls._w)
            else:
                floating_controls.place_forget()
        progress=tk.Frame(player_frame,bg=player_frame.cget('bg'));progress.pack(fill='x')
        def seek_to(fraction):
            if not player.active:
                try:player.play(audio)
                except (RuntimeError,OSError,ValueError) as exc:
                    messagebox.showerror('Không phát được âm thanh',str(exc));return
            if player.duration_ms():
                try:player.seek(fraction * player.duration_ms())
                except RuntimeError as exc:messagebox.showwarning('Không tua được',str(exc))
            paused_label.set('▶ TIẾP TỤC' if player.paused else '⏸ TẠM DỪNG')
            sync_controls()
        wave=WaveformSeek(progress,seek_to,bg=progress.cget('bg'))
        wave.pack(fill='x',expand=True)
        tk.Label(progress,textvariable=time_label,bg=progress.cget('bg'),font=('Segoe UI',11),anchor='e').pack(fill='x')
        result_queue=queue.Queue(maxsize=1)
        def waveform_worker():
            try: peaks=waveform_peaks(audio, 320)
            except (OSError,ValueError): peaks=None
            result_queue.put(peaks)
        threading.Thread(target=waveform_worker,daemon=True).start()
        def poll_wave():
            if not alive[0] or not player_frame.winfo_exists():return
            try:peaks=result_queue.get_nowait()
            except queue.Empty:player_frame.after(200,poll_wave);return
            wave.set_peaks(peaks)
        poll_wave()
        def refresh():
            if not alive[0] or not player_frame.winfo_exists():return
            if player.active:
                if player.is_finished():
                    if repeat.get()=='loop':
                        try:player.seek(0);paused_label.set('⏸ TẠM DỪNG')
                        except RuntimeError:stop()
                    else:
                        stop()
                if player.active:
                    pos=player.position_ms();duration=player.duration_ms()
                    wave.set_progress(pos,duration)
                    time_label.set(f'{fmt(pos)} / {fmt(duration)}')
            sync_controls()
            update_floating_visibility()
            player_frame.after(150,refresh)
        def cleanup(event):
            if event.widget is player_frame:alive[0]=False
        player_frame.bind('<Destroy>',cleanup,add='+')
        # Defer the first tick so answer widgets finish building before geometry checks.
        player_frame.after(150, refresh)

        self.label(body,'Bài chép của em:',13,True).pack(anchor='w',pady=(15,5))
        field=tk.Text(body,height=9,font=('Segoe UI',14),wrap='word',undo=True)
        field.pack(fill='x',pady=4)
        feedback=tk.Frame(body,bg=body['bg']);feedback.pack(fill='x',pady=8)
        def check():
            for widget in feedback.winfo_children():widget.destroy()
            entered=field.get('1.0','end').strip()
            if not entered:messagebox.showwarning('Chưa có đáp án','Em hãy nghe và chép nội dung trước khi kiểm tra.');return
            result=check_dictation(item['answer'],entered,item.get('accepted_variants',[]),item.get('equivalences',[]))
            self.label(feedback,f'Kết quả: {result["score"]}%  •  Đúng {result["matched"]}/{result["total"]} từ',16,True,color='#23865C' if result['passed'] else '#AE6630').pack(anchor='w',pady=6)
            if result['passed']:
                self.label(feedback,'🌟 Chính xác! Em đã chép đúng toàn bộ từ và dấu.',12).pack(anchor='w')
            else:
                self.label(feedback,'Cần sửa (đáp án → bài em chép):',12,True).pack(anchor='w',pady=4)
                for issue in result['issues'][:20]:
                    self.label(feedback,f'• {issue["expected"] or "(không có)"}  →  {issue["written"] or "(thiếu)"}',11).pack(anchor='w')
                self.action_button(feedback,'👁 XEM ĐÁP ÁN GỐC',lambda:messagebox.showinfo('Đáp án chính tả','\n\n'.join([item['answer']]+item.get('accepted_variants',[])))).pack(anchor='w',pady=9)
            if self.student:
                from datetime import datetime
                folder,_=self._dictation_paths()
                log=folder/'ket_qua.jsonl'
                with log.open('a',encoding='utf-8') as f:
                    f.write(json.dumps({'student_id':self.student['id'],'id':item_id,'score':result['score'],'passed':result['passed'],'at':datetime.now().isoformat()},ensure_ascii=False)+'\n')
        row2=tk.Frame(body,bg=body['bg']);row2.pack(anchor='w',pady=10)
        self.action_button(row2,'✓ KIỂM TRA ĐÁP ÁN',check).pack(side='left',padx=5)
        self.button(row2,'✎ SỬA BÀI',lambda:self.dictation_editor(item_id)).pack(side='left',padx=5)
        self.button(row2,'← VỀ DANH SÁCH CHÍNH TẢ',self.dictation_page).pack(side='left',padx=5)
        if index+1<len(items):
            self.button(row2,'BÀI TIẾP THEO →',lambda:self.dictation_exercise(items[index+1]['id'])).pack(side='left',padx=5)
        else:
            self.label(body,'Đây là bài cuối trong danh sách hiện tại.',11).pack(anchor='w',pady=6)
