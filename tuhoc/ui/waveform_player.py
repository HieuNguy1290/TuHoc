"""Interactive audio waveform window for lesson listening (Tkinter)."""
import os, wave, math, struct, subprocess, shutil, tempfile, time
import tkinter as tk
from pathlib import Path

BLUE='#2563EB'; PALE='#A9C5F4'; BORDER='#B6C5E3'; INK='#27385F'

def audio_peaks(path, count=650):
    """Decode real audio and return per-bin min/max peaks, not random artwork."""
    import array
    path=str(path)
    raw=None; channels=1; width=2
    if path.lower().endswith('.wav'):
        try:
            with wave.open(path,'rb') as f:
                channels=f.getnchannels(); width=f.getsampwidth(); raw=f.readframes(f.getnframes())
        except (wave.Error,EOFError):pass
    if raw is None and shutil.which('ffmpeg'):
        p=subprocess.run(['ffmpeg','-v','error','-i',path,'-ac','1','-ar','16000','-f','s16le','-'],capture_output=True)
        if p.returncode==0:raw=p.stdout;channels=1;width=2
    if raw is None:
        try:
            import soundfile as sf
            import numpy as np
            data,sr=sf.read(path,always_2d=True,dtype='float32')
            mono=data.mean(axis=1); edges=np.linspace(0,len(mono),count+1,dtype=int)
            return [(float(mono[a:b].min()),float(mono[a:b].max())) if b>a else (0,0) for a,b in zip(edges[:-1],edges[1:])],len(mono)/sr
        except Exception as exc:raise RuntimeError('Không giải mã được waveform. Cài ffmpeg hoặc soundfile để đọc MP3.') from exc
    if width==2:
        samples=array.array('h');samples.frombytes(raw[:len(raw)//2*2]); scale=32768
    elif width==1:
        samples=array.array('B',raw);scale=128
    else:raise RuntimeError('Định dạng WAV chưa hỗ trợ; hãy dùng WAV PCM 16-bit hoặc ffmpeg.')
    total=len(samples)//channels
    if not total:return [(0,0)]*count,0
    step=max(1,math.ceil(total/count));out=[]
    for i in range(count):
        a=i*total//count;b=max(a+1,(i+1)*total//count)
        lo=1.;hi=-1.
        for j in range(a,min(b,total)):
            v=sum(samples[j*channels+k] for k in range(channels))/channels
            v=(v-128)/scale if width==1 else v/scale
            lo=min(lo,v);hi=max(hi,v)
        out.append((lo,hi))
    duration=total/16000
    if path.lower().endswith('.wav'):
        try:
            with wave.open(path,'rb') as f:duration=total/f.getframerate()
        except Exception:pass
    return out,duration

class WaveformPlayer(tk.Toplevel):
    def __init__(self,master,path):
        super().__init__(master)
        self.path=str(Path(path).resolve());self.title('Nghe âm thanh - Waveform');self.geometry('900x310');self.minsize(540,260)
        self.configure(bg='white');self.speed=1.0;self.volume=.85;self.pos=0;self.playing=False;self.started=0;self.dragging=False
        self.peaks,self.duration=audio_peaks(self.path)
        self._temp=None
        self.canvas=tk.Canvas(self,bg='white',height=155,highlightthickness=1,highlightbackground=BORDER,cursor='hand2')
        self.canvas.pack(fill='both',expand=True,padx=18,pady=(18,0))
        self.canvas.bind('<Configure>',lambda e:self.draw())
        self.canvas.bind('<Button-1>',self.seek);self.canvas.bind('<B1-Motion>',self.seek)
        bar=tk.Frame(self,bg='#F8FAFF',highlightbackground=BORDER,highlightthickness=1)
        bar.pack(fill='x',padx=18,pady=(0,18),ipady=13)
        self.play_btn=tk.Button(bar,text='▶',bg=BLUE,fg='white',font=('Arial',17,'bold'),relief='flat',width=3,command=self.toggle)
        self.play_btn.pack(side='left',padx=(14,12))
        self.clock=tk.Label(bar,text='0:00 / 0:00',bg='#F8FAFF',fg=INK,font=('Arial',12))
        self.clock.pack(side='left')
        self.progress=tk.Scale(bar,from_=0,to=max(self.duration,.01),orient='horizontal',showvalue=False,bg='#F8FAFF',troughcolor='#D4DBE9',highlightthickness=0,command=self._progress_seek)
        self.progress.pack(side='left',fill='x',expand=True,padx=18)
        tk.Label(bar,text='◖))',bg='#F8FAFF',fg=INK,font=('Arial',16)).pack(side='left')
        self.vol=tk.Scale(bar,from_=0,to=100,orient='horizontal',showvalue=False,length=90,bg='#F8FAFF',highlightthickness=0,command=self._set_volume)
        self.vol.set(85);self.vol.pack(side='left',padx=(2,12))
        self.speed_btn=tk.Button(bar,text='1.0×',bg='#E9EDF6',fg=INK,relief='flat',font=('Arial',12),command=self.change_speed)
        self.speed_btn.pack(side='left',padx=(0,14))
        self._updating=False;self.protocol('WM_DELETE_WINDOW',self.close);self.after(80,self.tick);self.draw()
    def draw(self):
        c=self.canvas;c.delete('all');w=max(1,c.winfo_width());h=max(1,c.winfo_height());mid=h/2
        c.create_line(0,mid,w,mid,fill=BORDER)
        for i,(low,high) in enumerate(self.peaks):
            x=i*w/len(self.peaks);x2=(i+1)*w/len(self.peaks)
            color=BLUE if i/len(self.peaks)<=self.pos/max(self.duration,.001) else PALE
            c.create_rectangle(x,mid-high*h*.43,x2+.35,mid-low*h*.43,fill=color,outline='')
        x=w*self.pos/max(self.duration,.001);c.create_line(x,0,x,h,fill=BLUE,width=3);c.create_oval(x-5,3,x+5,13,fill=BLUE,outline='')
    def seek(self,event):
        self.pos=max(0,min(self.duration,event.x/max(1,self.canvas.winfo_width())*self.duration))
        if self.playing:self._start(self.pos)
        self.draw()
    def _progress_seek(self,v):
        if self._updating:return
        self.pos=float(v)
        if self.playing:self._start(self.pos)
        self.draw()
    def _set_volume(self,v):
        self.volume=float(v)/100
        try:
            import pygame;pygame.mixer.music.set_volume(self.volume)
        except Exception:pass
    def _audio_source(self):
        if self.speed==1:return self.path
        if not shutil.which('ffmpeg'):return self.path
        if self._temp and os.path.exists(self._temp):os.unlink(self._temp)
        fd,self._temp=tempfile.mkstemp(suffix='.wav');os.close(fd)
        subprocess.run(['ffmpeg','-y','-v','error','-i',self.path,'-filter:a',f'atempo={self.speed}','-ac','2',self._temp],check=True)
        return self._temp
    def _start(self,pos):
        import pygame
        if not pygame.mixer.get_init():pygame.mixer.init()
        src=self._audio_source() if not hasattr(self,'_loaded_speed') or self._loaded_speed!=self.speed else self._loaded_path
        if getattr(self,'_loaded_path',None)!=src:
            pygame.mixer.music.load(src);self._loaded_path=src;self._loaded_speed=self.speed
        pygame.mixer.music.play(start=pos/self.speed)
        pygame.mixer.music.set_volume(self.volume)
        self.started=time.monotonic()-pos/self.speed;self.playing=True;self.play_btn.configure(text='Ⅱ')
    def toggle(self):
        import pygame
        if self.playing:
            self.pos=min(self.duration,(time.monotonic()-self.started)*self.speed)
            pygame.mixer.music.pause();self.playing=False;self.play_btn.configure(text='▶')
        else:
            if self.pos>=self.duration:self.pos=0
            self._start(self.pos)
    def change_speed(self):
        speeds=[.75,1.,1.25,1.5,2.]
        self.speed=speeds[(speeds.index(self.speed)+1)%len(speeds)]
        self.speed_btn.configure(text=f'{self.speed:.2g}×')
        if self.playing:self._start(self.pos)
    def tick(self):
        if not self.winfo_exists():return
        if self.playing:
            self.pos=min(self.duration,(time.monotonic()-self.started)*self.speed)
            if self.pos>=self.duration:self.playing=False;self.play_btn.configure(text='▶')
        def fmt(t):return f'{int(t)//60}:{int(t)%60:02}'
        self.clock.configure(text=f'{fmt(self.pos)} / {fmt(self.duration)}')
        self._updating=True;self.progress.set(self.pos);self._updating=False;self.draw()
        self.after(80,self.tick)
    def close(self):
        try:
            import pygame;pygame.mixer.music.stop()
        except Exception:pass
        if self._temp:
            try:os.unlink(self._temp)
            except OSError:pass
        self.destroy()
