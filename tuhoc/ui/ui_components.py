"""Lightweight shared Tk canvas primitives; no external packages."""
from tuhoc.ui.ui_tokens import DURATION, RADIUS, font_at
import tkinter as tk
from tuhoc.ui.theme_config import UI_COLORS

def rounded_rect(canvas,x1,y1,x2,y2,r=16,fill='white',outline='',**kw):
    r=max(0,min(r,(x2-x1)/2,(y2-y1)/2))
    points=[x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1]
    return canvas.create_polygon(points,smooth=True,splinesteps=12,fill=fill,outline=outline,**kw)

class RoundedButton(tk.Canvas):
    def __init__(self,parent,text,command=None,variant='primary',width=160,height=44,
                 *,disabled=False,loading=False,icon=None,tooltip=None,**kw):
        width,height=max(44,width),max(44,height)
        options=dict(width=width,height=height,highlightthickness=2,
                     highlightbackground=UI_COLORS['border'],takefocus=1,cursor='hand2')
        options.update(kw)
        super().__init__(parent,**options)
        self.command=command
        self.text=text
        self.icon=icon
        self.disabled=disabled
        self.loading=loading
        self.variant=variant
        self._spinner=None
        self._frame=0
        self._colors={'primary':UI_COLORS['primary'],'outline':'white',
                      'ghost':UI_COLORS['background']}
        self._shape=rounded_rect(self,2,2,width-2,height-2,RADIUS['normal'],
                                 fill=self._colors[variant],
                                 outline=UI_COLORS['border'] if variant=='outline' else '')
        self._label=self.create_text(width/2,height/2,font=font_at(12,'bold'))
        self.bind('<Button-1>',self._click)
        self.bind('<Return>',self._click)
        self.bind('<space>',self._click)
        self.bind('<FocusIn>',lambda _e:self.configure(highlightbackground=UI_COLORS['focus']))
        self.bind('<FocusOut>',lambda _e:self.configure(highlightbackground=UI_COLORS['border']))
        self.bind('<Destroy>',self._dispose,add='+')
        if tooltip:
            self.tooltip=Tooltip(self,tooltip)
        self.set_state(disabled=disabled,loading=loading)

    def _click(self,event):
        if event.keysym=='??':
            self.focus_set()
        self.invoke()
        return 'break'

    def invoke(self):
        if not self.disabled and not self.loading and self.command:
            return self.command()

    def _dispose(self,event=None):
        if self._spinner is not None:
            self.after_cancel(self._spinner)
            self._spinner=None

    def _render(self):
        blocked=self.disabled or self.loading
        icons=('◐','◓','◑','◒')
        icon=icons[self._frame%len(icons)] if self.loading else self.icon
        self.itemconfigure(self._shape,fill=UI_COLORS['disabled'] if blocked else self._colors[self.variant])
        self.itemconfigure(self._label,text=f'{icon}  {self.text}' if icon else self.text,
                           fill=UI_COLORS['disabled_text'] if blocked else 'white'
                           if self.variant=='primary' else UI_COLORS['text'])

    def _next_frame(self):
        self._spinner=None
        if self.loading and self.winfo_exists():
            self._frame+=1
            self._render()
            self._spinner=self.after(DURATION['fast'],self._next_frame)

    def set_state(self,*,disabled=None,loading=None):
        if disabled is not None:self.disabled=bool(disabled)
        if loading is not None:self.loading=bool(loading)
        self._dispose()
        blocked=self.disabled or self.loading
        self.configure(takefocus=not blocked,cursor='' if blocked else 'hand2')
        self._render()
        if self.loading:
            self._spinner=self.after(DURATION['fast'],self._next_frame)


def bind_hover(root,on_change,inset=(0,0,0,0),region=None,also=()):
    """Hover by pointer position inside a stationary region of `root`.
    Child Enter/Leave events only trigger a re-check, so moving widgets or
    child boundaries never cause enter/leave flicker."""
    state={'on':False,'job':None}
    geo=region or root   # stationary widget that defines the hover area
    def check():
        state['job']=None
        try:
            if not root.winfo_exists() or not geo.winfo_exists():return
            x,y=root.winfo_pointerxy()
            l,t,r,b=inset
            x0=geo.winfo_rootx()+l;y0=geo.winfo_rooty()+t
            x1=geo.winfo_rootx()+geo.winfo_width()-r;y1=geo.winfo_rooty()+geo.winfo_height()-b
            inside=x0<=x<x1 and y0<=y<y1 and root.winfo_containing(x,y) is not None
            if inside!=state['on']:
                state['on']=inside;on_change(inside)
        except tk.TclError:pass
    def schedule(_e=None):
        if state['job'] is None:
            try:state['job']=root.after_idle(check)
            except tk.TclError:pass
    def walk(w):
        w.bind('<Enter>',schedule,add='+');w.bind('<Leave>',schedule,add='+')
        for c in w.winfo_children():walk(c)
    walk(root)
    for w in also:walk(w)
    return state

class Card(tk.Frame):
    def __init__(self,parent,**kw):super().__init__(parent,bg=UI_COLORS['surface'],highlightbackground=UI_COLORS['border'],highlightthickness=1,padx=16,pady=16,**kw)

class ProgressBar(tk.Canvas):
    def __init__(self,parent,value=0,width=200,height=14,**kw):
        super().__init__(parent,width=width,height=height,highlightthickness=0,**kw)
        self.value=value;self.draw(width,height)
    def draw(self,w,h):
        self.delete('all');rounded_rect(self,0,0,w,h,h/2,UI_COLORS['tint']);rounded_rect(self,0,0,max(h,min(w,w*self.value)),h,h/2,UI_COLORS['primary']) if self.value>0 else None

class ProgressRing(tk.Canvas):
    def __init__(self,parent,value=0,size=80,**kw):
        super().__init__(parent,width=size,height=size,highlightthickness=0,**kw)
        self.create_oval(6,6,size-6,size-6,outline=UI_COLORS['border'],width=7)
        self.create_arc(6,6,size-6,size-6,start=90,extent=-360*max(0,min(1,value)),style='arc',outline=UI_COLORS['primary'],width=7)
        self.create_text(size/2,size/2,text=f'{value:.0%}',fill=UI_COLORS['text'])

class Chip(tk.Label):
    def __init__(self,parent,text,**kw):
        opts=dict(bg=UI_COLORS['tint'],fg=UI_COLORS['text'],padx=12,pady=6,font=font_at(11));opts.update(kw)
        super().__init__(parent,text=text,**opts)

class Dialog(tk.Toplevel):
    def __init__(self,parent,title,message,*,primary='Đồng ý',secondary=None,
                 tone='info',safe=True):
        parent=parent.winfo_toplevel()
        super().__init__(parent,bg=UI_COLORS['surface'])
        self.title(title)
        self.transient(parent)
        self.resizable(False,False)
        self.result=False if secondary else True
        self._parent=parent
        self._previous_focus=parent.focus_get()
        frame=tk.Frame(self,bg=UI_COLORS['surface'],padx=22,pady=18)
        frame.pack(fill='both',expand=True)
        tk.Label(frame,text=title,fg=UI_COLORS.get(tone,UI_COLORS['text']),
                 bg=UI_COLORS['surface'],font=font_at(16,'bold'),
                 wraplength=460,justify='left').pack(anchor='w')
        tk.Label(frame,text=message,fg=UI_COLORS['text'],bg=UI_COLORS['surface'],
                 font=font_at(13),wraplength=460,justify='left').pack(anchor='w',pady=(10,15))
        row=tk.Frame(frame,bg=UI_COLORS['surface'])
        row.pack(fill='x')
        self.primary=RoundedButton(row,primary,lambda:self.close(True),width=128)
        self.primary.pack(side='right',padx=(8,0))
        self.secondary=None
        if secondary:
            self.secondary=RoundedButton(row,secondary,lambda:self.close(False),variant='outline',width=128)
            self.secondary.pack(side='right')
        safe_button=self.secondary if safe and self.secondary else self.primary
        self.bind('<Escape>',lambda _e:self.close(False))
        self.protocol('WM_DELETE_WINDOW',lambda:self.close(False))
        self.update_idletasks()
        x=parent.winfo_rootx()+(parent.winfo_width()-self.winfo_reqwidth())//2
        y=parent.winfo_rooty()+(parent.winfo_height()-self.winfo_reqheight())//2
        self.geometry(f'+{max(0,x)}+{max(0,y)}')
        self.wait_visibility()
        self._prior_grab=parent.grab_current()
        self.grab_set()
        safe_button.focus_set()

    def close(self,result):
        self.result=result
        self.grab_release()
        self.destroy()
        if self._prior_grab is not None and self._prior_grab.winfo_exists():
            self._prior_grab.grab_set()
        if self._previous_focus is not None and self._previous_focus.winfo_exists():
            self._previous_focus.focus_set()
        return 'break'

    def show(self):
        self.wait_window()
        return self.result


class ConfirmDialog(Dialog):
    def __init__(self,parent,title,message,*,safe=True):
        super().__init__(parent,title,message,primary='Có',secondary='Không',
                         tone='warning',safe=safe)


class EmptyState(tk.Frame):
    def __init__(self,parent,text,*,icon='○',action=None,background=None):
        bg=background or UI_COLORS['surface']
        super().__init__(parent,bg=bg,padx=14,pady=12)
        tk.Label(self,text=icon,bg=bg,fg=UI_COLORS['primary'],font=font_at(24,'bold')).pack()
        tk.Label(self,text=text,bg=bg,fg=UI_COLORS['muted'],font=font_at(13),
                 wraplength=460,justify='center').pack()
        if action:
            label,command=action
            RoundedButton(self,label,command,variant='outline').pack(pady=(8,0))


class LoadingState(tk.Frame):
    def __init__(self,parent,text='Đang tải…'):
        from tkinter import ttk

        super().__init__(parent,bg=UI_COLORS['surface'],padx=14,pady=12)
        tk.Label(self,text=text,bg=UI_COLORS['surface'],fg=UI_COLORS['text']).pack(anchor='w')
        self.progress=ttk.Progressbar(self,mode='indeterminate')
        self.progress.pack(fill='x',pady=(6,0))
        self._job=self.after(65,self._tick)
        self.bind('<Destroy>',self._stop,add='+')

    def _tick(self):
        self.progress.step()
        self._job=self.after(65,self._tick)

    def _stop(self,event):
        if event.widget is self:
            self.after_cancel(self._job)


class Badge(Chip):
    def __init__(self,parent,text,tone='success',**kw):
        super().__init__(parent,text,fg=UI_COLORS[tone],**kw)


class Toast:
    def __init__(self,root,text,duration=2500,action=None):
        self.root=root
        self.frame=tk.Frame(root,bg=UI_COLORS['text'])
        self.label=tk.Label(self.frame,text=text,bg=UI_COLORS['text'],fg='white',
                            padx=16,pady=10,wraplength=500,justify='left')
        self.label.pack(side='left')
        if action:
            caption,callback=action
            def run():
                self.close()
                callback()
            tk.Button(self.frame,text=caption,command=run,takefocus=True).pack(side='right',padx=8)
        self.frame.place(relx=.5,rely=.92,anchor='center')
        self.job=root.after(duration,self.close)
        self.frame.bind('<Destroy>',self._cancel,add='+')

    def _cancel(self,event):
        if event.widget is self.frame and self.job is not None:
            self.root.after_cancel(self.job)
            self.job=None

    def close(self):
        if self.job is not None:
            self.root.after_cancel(self.job)
            self.job=None
        self.frame.destroy()


class Tooltip:
    def __init__(self,widget,text):
        self.widget=widget
        self.text=text
        self.tip=None
        self.job=None
        for event in ('<Enter>','<FocusIn>'):
            widget.bind(event,self.schedule,add='+')
        for event in ('<Leave>','<FocusOut>','<Destroy>'):
            widget.bind(event,self.hide,add='+')

    def schedule(self,event=None):
        self.hide()
        self.job=self.widget.after(350,self.show)

    def show(self,event=None):
        self.job=None
        self.tip=tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.geometry(f'+{self.widget.winfo_rootx()}+{self.widget.winfo_rooty()+self.widget.winfo_height()+5}')
        tk.Label(self.tip,text=self.text,bg=UI_COLORS['text'],fg='white',padx=8,pady=5).pack()

    def hide(self,event=None):
        if self.job is not None:
            self.widget.after_cancel(self.job)
            self.job=None
        if self.tip:
            self.tip.destroy()
            self.tip=None
