"""Lightweight shared Tk canvas primitives; no external packages."""
from ui_tokens import font_at
import tkinter as tk
from theme_config import UI_COLORS

def rounded_rect(canvas,x1,y1,x2,y2,r=16,fill='white',outline='',**kw):
    r=max(0,min(r,(x2-x1)/2,(y2-y1)/2))
    points=[x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1]
    return canvas.create_polygon(points,smooth=True,splinesteps=12,fill=fill,outline=outline,**kw)

class RoundedButton(tk.Canvas):
    def __init__(self,parent,text,command=None,variant='primary',width=160,height=44,**kw):
        super().__init__(parent,width=width,height=max(44,height),highlightthickness=2,highlightbackground=UI_COLORS['border'],takefocus=1,cursor='hand2',**kw)
        bg={'primary':UI_COLORS['primary'],'outline':'white','ghost':UI_COLORS['background']}[variant]
        fg='white' if variant=='primary' else UI_COLORS['text']
        rounded_rect(self,2,2,width-2,max(44,height)-2,14,fill=bg,outline=UI_COLORS['border'] if variant=='outline' else '')
        self.create_text(width/2,max(44,height)/2,text=text,fill=fg,font=font_at(12, 'bold'))
        if command:
            self.bind('<Button-1>',lambda e:command())
            self.bind('<Return>',lambda e:command())
            self.bind('<space>',lambda e:command())
        self.bind('<FocusIn>',lambda e:self.configure(highlightbackground=UI_COLORS['primary']))
        self.bind('<FocusOut>',lambda e:self.configure(highlightbackground=UI_COLORS['border']))

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

class Toast:
    def __init__(self,root,text,duration=2500):
        self.label=tk.Label(root,text=text,bg=UI_COLORS['text'],fg='white',padx=16,pady=10)
        self.label.place(relx=.5,rely=.92,anchor='center')
        self.job=root.after(duration,self.label.destroy)

class Tooltip:
    def __init__(self,widget,text):
        self.widget=widget;self.text=text;self.tip=None
        widget.bind('<Enter>',self.show,add='+');widget.bind('<Leave>',self.hide,add='+')
    def show(self,event=None):
        self.hide();self.tip=tk.Toplevel(self.widget);self.tip.wm_overrideredirect(True)
        self.tip.geometry(f'+{self.widget.winfo_rootx()}+{self.widget.winfo_rooty()+self.widget.winfo_height()+5}')
        tk.Label(self.tip,text=self.text,bg=UI_COLORS['text'],fg='white',padx=8,pady=5).pack()
    def hide(self,event=None):
        if self.tip:self.tip.destroy();self.tip=None
