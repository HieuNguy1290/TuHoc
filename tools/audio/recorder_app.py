"""Dark standalone screen recorder UI."""
from tuhoc.paths import PROJECT_ROOT
import ctypes
import json
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from ctypes import wintypes
from pathlib import Path
from tuhoc.storage.recording_tools import RecordingSession, recording_folder, microphone_choices

def windows():
    user32 = ctypes.windll.user32
    results = []
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if not length: return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)): return True
        if rect.right - rect.left < 80 or rect.bottom - rect.top < 80: return True
        results.append((int(hwnd), buf.value))
        return True
    cb = callback_type(callback)
    user32.EnumWindows(cb, 0)
    return results

def window_bounds(hwnd):
    rect = wintypes.RECT()
    if not ctypes.windll.user32.IsWindow(hwnd) or not ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise RuntimeError('Cửa sổ đã đóng. Hãy làm mới danh sách.')
    return dict(left=rect.left, top=rect.top, width=rect.right-rect.left, height=rect.bottom-rect.top)

def screen_bounds():
    import mss
    with mss.mss() as s:
        return dict(s.monitors[0])


BG='#17212D'; PANEL='#080F19'; TILE='#2A3B4D'; TEXT='#E7EDF5'; MUTED='#A8B7C9'; GREEN='#69D6A5'; RED='#E8495A'
CONFIG=PROJECT_ROOT/'recorder_settings.json'

class Recorder(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Screen Recorder | Cùng Học Cùng Vui')
        self.geometry('780x760');self.minsize(660,690)
        self.configure(bg=BG)
        self.session=None;self.busy=False;self.entries=[];self.mics=[]
        self.mode=tk.StringVar(value='desktop');self.audio=tk.BooleanVar(value=True)
        self.denoise=tk.BooleanVar(value=True);self.strength=tk.DoubleVar(value=55)
        self.gate_db=tk.DoubleVar(value=-48);self.auto_level=tk.BooleanVar(value=True)
        self.status=tk.StringVar(value='Sẵn sàng ghi hình')
        self.elapsed=tk.StringVar(value='00:00:00')
        try: settings=json.loads(CONFIG.read_text(encoding='utf-8'))
        except (OSError,ValueError):settings={}
        self.folder=tk.StringVar(value=settings.get('folder',str(recording_folder())))
        self.fps=tk.IntVar(value=int(settings.get('fps',30)) if str(settings.get('fps',30)) in ('12','24','30','60') else 30)
        self.mode.set(settings.get('mode','desktop'))
        self._build();self.refresh_windows();self.refresh_mics();self._mode_changed()
        self.after(250,self._tick)
        self.protocol('WM_DELETE_WINDOW',self.close)

    def label(self,parent,text,**kwargs):
        return tk.Label(parent,text=text,bg=kwargs.pop('bg',BG),fg=kwargs.pop('fg',TEXT),font=kwargs.pop('font',('Segoe UI',10)),**kwargs)

    def button(self,parent,text,command,bg=TILE,fg=TEXT,**kwargs):
        return tk.Button(parent,text=text,command=command,bg=bg,fg=fg,activebackground='#385268',activeforeground='white',relief='flat',bd=0,cursor='hand2',font=('Segoe UI',10,'bold'),**kwargs)

    def _build(self):
        outer=tk.Frame(self,bg=BG,padx=17,pady=13);outer.pack(fill='both',expand=True)
        top=tk.Frame(outer,bg=BG);top.pack(fill='x',pady=(0,12))
        self.label(top,'▣  Screen Recorder',font=('Segoe UI',13,'bold')).pack(side='left')
        self.button(top,'⚙  Cài đặt',self._toggle_settings).pack(side='right')
        preview=tk.Frame(outer,bg=PANEL,height=154);preview.pack(fill='x');preview.pack_propagate(False)
        self.label(preview,'▣',bg=PANEL,fg='#7990A8',font=('Segoe UI Symbol',32)).pack(pady=(20,0))
        self.label(preview,'Xem trước nguồn ghi',bg=PANEL,fg=MUTED).pack()
        self.preview_info=self.label(preview,'Chọn nguồn bên dưới · 12 FPS',bg=PANEL,fg='#CAD6E3',font=('Segoe UI',9,'bold'))
        self.preview_info.pack(pady=7)
        fps_row=tk.Frame(outer,bg=BG);fps_row.pack(fill='x',pady=(9,0))
        self.label(fps_row,'Tốc độ ghi (FPS):',fg=MUTED).pack(side='left')
        self.fps_box=ttk.Combobox(fps_row,values=('12','24','30','60'),state='readonly',width=7)
        self.fps_box.set(str(self.fps.get()));self.fps_box.pack(side='left',padx=9)
        self.fps_box.bind('<<ComboboxSelected>>',lambda e:(self.fps.set(int(self.fps_box.get())),self._mode_changed()))
        modes=tk.Frame(outer,bg=BG);modes.pack(fill='x',pady=(11,7))
        for i,(symbol,name,value) in enumerate([('▣','Toàn màn hình','desktop'),('▤','Ứng dụng','window'),('▱','Chọn vùng','region'),('♫','Chỉ ghi âm','voice')]):
            b=self.button(modes,symbol+chr(10)+name,lambda v=value:self._select_mode(v),height=2)
            b.grid(row=0,column=i,sticky='ew',padx=(0 if i==0 else 4,0));modes.grid_columnconfigure(i,weight=1)
            setattr(self,'mode_'+value,b)
        source=tk.Frame(outer,bg=BG);source.pack(fill='x',pady=(1,7))
        self.windows_box=ttk.Combobox(source,state='readonly');self.windows_box.pack(side='left',fill='x',expand=True)
        self.button(source,'↻ Làm mới',self.refresh_windows,padx=10).pack(side='left',padx=(8,0))
        self.label(outer,'Microphone',font=('Segoe UI',11,'bold')).pack(anchor='w',pady=(4,4))
        microw=tk.Frame(outer,bg=BG);microw.pack(fill='x')
        self.mic_box=ttk.Combobox(microw,state='readonly');self.mic_box.pack(side='left',fill='x',expand=True)
        self.button(microw,'↻',self.refresh_mics,width=3).pack(side='left',padx=(7,0))
        self.mic_meter=self._meter(outer,'Microphone',GREEN)
        self.sys_meter=self._meter(outer,'Âm thanh hệ thống',GREEN)
        opts=tk.Frame(outer,bg=BG);opts.pack(fill='x',pady=(5,5))
        tk.Checkbutton(opts,text='Thu micro cùng video',variable=self.audio,bg=BG,fg=TEXT,selectcolor=TILE,activebackground=BG,activeforeground=TEXT).pack(side='left')
        self.settings=tk.Frame(outer,bg=TILE,padx=12,pady=8)
        self._settings_open=False
        self._check(self.settings,'Lọc tiếng ồn micro',self.denoise)
        self._slider(self.settings,'Mức lọc tiếng ồn',self.strength,0,100)
        self._slider(self.settings,'Ngưỡng Noise Gate (dBFS)',self.gate_db,-75,-20)
        self._check(self.settings,'Tự cân bằng âm lượng',self.auto_level)
        folderbox=tk.Frame(outer,bg=BG);self.folderbox=folderbox;folderbox.pack(fill='x',pady=(10,4))
        self.label(folderbox,'Lưu bản ghi tại:',fg=MUTED).pack(anchor='w')
        row=tk.Frame(folderbox,bg=BG);row.pack(fill='x',pady=(4,0))
        self.folder_entry=tk.Entry(row,textvariable=self.folder,bg=PANEL,fg=TEXT,insertbackground='white',relief='flat',font=('Segoe UI',10))
        self.folder_entry.pack(side='left',fill='x',expand=True,ipady=8)
        self.button(row,'Chọn thư mục',self.browse,padx=9).pack(side='left',padx=(6,0))
        self.button(row,'Mở',self.open_folder,padx=10).pack(side='left',padx=(5,0))
        foot=tk.Frame(outer,bg=BG);foot.pack(fill='x',pady=(13,0))
        left=tk.Frame(foot,bg=BG);left.pack(side='left')
        self.label(left,'THỜI GIAN GHI',fg=MUTED,font=('Segoe UI',8)).pack(anchor='w')
        self.label(left,'',textvariable=self.elapsed,font=('Consolas',19,'bold')).pack(anchor='w')
        self.stop_btn=self.button(foot,'■  Dừng và lưu',self.stop,bg='#C84958',padx=18,pady=11,state='disabled')
        self.stop_btn.pack(side='right')
        self.start_btn=self.button(foot,'●  Bắt đầu ghi',self.start,bg=RED,padx=18,pady=11)
        self.start_btn.pack(side='right',padx=(0,8))
        self.label(outer,'',textvariable=self.status,fg=GREEN,wraplength=710).pack(anchor='w',pady=(11,0))

    def _meter(self,parent,title,color):
        row=tk.Frame(parent,bg=BG);row.pack(fill='x',pady=(7,1))
        self.label(row,'◖  '+title).pack(side='left')
        level=self.label(row,'Chờ tín hiệu',fg=GREEN,font=('Segoe UI',9));level.pack(side='right')
        canvas=tk.Canvas(parent,height=7,bg=TILE,highlightthickness=0);canvas.pack(fill='x',pady=(3,2))
        canvas.bind('<Configure>',lambda e,c=canvas:c.delete('bar'))
        return level

    def _check(self,parent,text,var):
        tk.Checkbutton(parent,text=text,variable=var,bg=TILE,fg=TEXT,selectcolor=BG,activebackground=TILE,activeforeground=TEXT).pack(anchor='w')

    def _slider(self,parent,text,var,low,high):
        line=tk.Frame(parent,bg=TILE);line.pack(fill='x')
        self.label(line,text,bg=TILE).pack(side='left')
        number=self.label(line,'',bg=TILE,fg=GREEN);number.pack(side='right')
        scale=tk.Scale(parent,from_=low,to=high,orient='horizontal',variable=var,bg=TILE,fg=TEXT,highlightthickness=0,showvalue=False,troughcolor=BG,command=lambda v:number.config(text=str(round(float(v)))))
        scale.pack(fill='x');number.config(text=str(round(var.get())))

    def _toggle_settings(self):
        self._settings_open=not self._settings_open
        if self._settings_open:self.settings.pack(fill='x',before=self.folderbox,pady=6)
        else:self.settings.pack_forget()

    def _select_mode(self,value):self.mode.set(value);self._mode_changed()

    def _mode_changed(self):
        for val in ('desktop','window','region','voice'):
            getattr(self,'mode_'+val).configure(bg='#386456' if self.mode.get()==val else TILE)
        self.windows_box.configure(state='readonly' if self.mode.get()=='window' else 'disabled')
        self.preview_info.config(text={'desktop':f'Toàn bộ Desktop · {self.fps.get()} FPS','window':f'Cửa sổ đã chọn · {self.fps.get()} FPS','region':f'Chọn vùng bằng tọa độ · {self.fps.get()} FPS','voice':'Chỉ thu âm micro'}[self.mode.get()])

    def refresh_windows(self):
        try:self.entries=windows()
        except Exception:self.entries=[]
        self.windows_box['values']=[f'{title} (#{hwnd})' for hwnd,title in self.entries]
        if self.entries:self.windows_box.current(0)

    def refresh_mics(self):
        try:
            self.mics=microphone_choices();self.mic_box['values']=['Mặc định']+[d['name'] for d in self.mics];self.mic_box.current(0)
        except Exception as exc:
            self.mics=[];self.mic_box['values']=['Không tìm thấy micro'];self.mic_box.current(0)
            self.status.set('Micro: '+str(exc))

    def browse(self):
        # Native Windows folder picker can hang when Tk's owner is not explicit.
        # Use a short-lived PowerShell STA dialog with a timeout, off the UI thread.
        if getattr(self, '_browsing', False):
            return
        self._browsing=True
        self.status.set('Đang mở hộp thoại chọn thư mục...')
        self.update_idletasks()
        initial=self.folder.get().strip().strip('"')
        if not Path(initial).is_dir():
            initial=str(Path.home())
        def worker():
            try:
                if sys.platform == 'win32':
                    import subprocess
                    script = ("Add-Type -AssemblyName System.Windows.Forms; "
                              "$d=New-Object System.Windows.Forms.FolderBrowserDialog; "
                              "$d.Description='Chon thu muc luu ban ghi'; "
                              "$d.SelectedPath=$env:RECORDER_INITIAL_FOLDER; "
                              "if($d.ShowDialog() -eq 'OK') { [Console]::WriteLine($d.SelectedPath) }")
                    env=os.environ.copy();env['RECORDER_INITIAL_FOLDER']=initial
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)
                    result=subprocess.run(['powershell.exe','-NoProfile','-STA','-Command',script],
                                          env=env,capture_output=True,text=True,timeout=120,
                                          creationflags=creationflags)
                    if result.returncode:
                        raise RuntimeError(result.stderr.strip() or 'Không mở được hộp thoại chọn thư mục.')
                    chosen=result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ''
                else:
                    chosen=''
                self.after(0,lambda:self._browse_done(chosen,None))
            except Exception as exc:
                error=str(exc)
                self.after(0,lambda:self._browse_done('',error))
        threading.Thread(target=worker,daemon=True).start()

    def _browse_done(self,chosen,error):
        self._browsing=False
        if chosen:self.folder.set(chosen)
        self.status.set('Đã chọn thư mục: '+chosen if chosen else 'Sẵn sàng ghi hình')
        if error:messagebox.showerror('Chọn thư mục',error,parent=self)

    def _validated_folder(self):
        raw=self.folder.get().strip().strip('"')
        if not raw:raise ValueError('Hãy nhập thư mục lưu bản ghi.')
        path=Path(raw).expanduser().resolve();path.mkdir(parents=True,exist_ok=True)
        if not path.is_dir():raise ValueError('Đường dẫn không phải thư mục.')
        return path

    def open_folder(self):
        try:
            folder=self._validated_folder()
            if sys.platform=='win32':os.startfile(str(folder))
            else:messagebox.showinfo('Thư mục',str(folder))
        except Exception as exc:messagebox.showerror('Thư mục không hợp lệ',str(exc))

    def _region(self):
        # Explicit numeric region picker, does not silently record full screen.
        from tkinter import simpledialog
        bounds=screen_bounds();coords={}
        for key,label,default in [('left','Tọa độ X',bounds['left']),('top','Tọa độ Y',bounds['top']),('width','Chiều rộng',min(1280,bounds['width'])),('height','Chiều cao',min(720,bounds['height']))]:
            val=simpledialog.askinteger('Chọn vùng ghi',label,parent=self,initialvalue=default)
            if val is None:raise ValueError('Đã hủy chọn vùng.')
            coords[key]=val
        if coords['width']<2 or coords['height']<2:raise ValueError('Kích thước vùng phải lớn hơn 1 pixel.')
        return coords

    def start(self):
        if self.session or self.busy:return
        try:
            folder=self._validated_folder();mode=self.mode.get();region=None
            if mode=='desktop':region=screen_bounds()
            elif mode=='window':
                index=self.windows_box.current()
                if index<0:raise RuntimeError('Hãy chọn cửa sổ cần ghi.')
                region=window_bounds(self.entries[index][0])
            elif mode=='region':region=self._region()
            idx=self.mic_box.current()
            mic_id=self.mics[idx-1]['id'] if 0<idx<=len(self.mics) else None
            session=RecordingSession(kind='voice' if mode=='voice' else 'video',capture_region=region,microphone_id=mic_id,with_microphone=self.audio.get(),output_dir=folder,fps=self.fps.get(),noise_settings={'enabled':self.denoise.get(),'strength':self.strength.get()/100,'gate_db':self.gate_db.get(),'auto_level':self.auto_level.get()})
            session.start();self.session=session
            CONFIG.write_text(json.dumps({'folder':str(folder),'mode':mode,'fps':self.fps.get()},ensure_ascii=False,indent=2),encoding='utf-8')
            self.status.set('Đang ghi...');self.start_btn.config(state='disabled');self.stop_btn.config(state='normal')
        except Exception as exc:messagebox.showerror('Không thể bắt đầu',str(exc))

    def stop(self):
        if not self.session or self.busy:return
        session=self.session;self.session=None;self.busy=True
        self.stop_btn.config(state='disabled');self.status.set('Đang xử lý và lưu bản ghi...')
        def worker():
            try:
                result=session.finish();self.after(0,lambda:self.done(result,None))
            except Exception as exc:
                error=str(exc);self.after(0,lambda:self.done(None,error))
        threading.Thread(target=worker,daemon=True).start()

    def done(self,result,error):
        self.busy=False;self.start_btn.config(state='normal')
        if error:self.status.set('Lỗi: '+error);messagebox.showerror('Không lưu được',error)
        else:
            path,warnings=result;self.status.set('Đã lưu: '+str(path))
            if warnings:messagebox.showwarning('Lưu có cảnh báo',str(warnings))

    def _tick(self):
        if self.session and self.session.started:
            seconds=int(time.monotonic()-self.session.started)
            self.elapsed.set(f'{seconds//3600:02d}:{seconds//60%60:02d}:{seconds%60:02d}')
        elif not self.busy:self.elapsed.set('00:00:00')
        try:self.after(250,self._tick)
        except tk.TclError:pass

    def close(self):
        if self.session or self.busy:
            messagebox.showwarning('Đang ghi','Hãy dừng và lưu bản ghi trước khi thoát.');return
        self.destroy()

if __name__=='__main__':
    if sys.platform!='win32':raise SystemExit('Ứng dụng ghi hình hỗ trợ Windows.')
    Recorder().mainloop()
