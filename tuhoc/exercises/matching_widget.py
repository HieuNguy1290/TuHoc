"""Matching board with text/image/mixed cards; backwards-compatible pair strings."""
import random
import tkinter as tk
from pathlib import Path

IMAGE_PREFIX = 'img:'

def parse_pairs(options):
    pairs=[]
    for option in options or []:
        text=str(option)
        for sep in (' = ', ' -> ', ' → ', '=', '→'):
            if sep in text:
                a,b=text.split(sep,1)
                if a.strip() and b.strip(): pairs.append((a.strip(),b.strip()))
                break
    return pairs

class MatchingBoard(tk.Frame):
    def __init__(self,parent,pairs,on_change=None,shuffle=True,bg='#F6FAF6',media_root=None,readonly=False):
        super().__init__(parent,bg=bg)
        self.pairs=[(str(a),str(b)) for a,b in pairs]
        self.media_root=Path(media_root) if media_root else None
        self.on_change=on_change;self.readonly=readonly
        self.selected=None;self.links={}
        self.left=list(range(len(self.pairs)));self.right=list(range(len(self.pairs)))
        if shuffle:random.shuffle(self.right)
        self._photos={}
        self.canvas=tk.Canvas(self,bg=bg,highlightthickness=0,height=max(210,len(self.pairs)*88+16))
        self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.draw())
        self.after_idle(self.draw)

    def _photo(self,token):
        if not token.startswith(IMAGE_PREFIX):return None
        path=token[len(IMAGE_PREFIX):]
        if path in self._photos:return self._photos[path]
        if self.media_root is None:return None
        candidate=(self.media_root/path).resolve()
        try:
            if not candidate.is_relative_to(self.media_root.resolve()):return None
            from PIL import Image,ImageTk
            with Image.open(candidate) as im:
                im=im.convert('RGBA');im.thumbnail((105,62),Image.Resampling.LANCZOS)
                photo=ImageTk.PhotoImage(im,master=self)
            self._photos[path]=photo
            return photo
        except (OSError,ValueError,ImportError,tk.TclError):return None

    def draw(self):
        c=self.canvas;c.delete('all')
        width=max(450,c.winfo_width());gap=88
        nodes={}
        for side,order in ((0,self.left),(1,self.right)):
            for row,index in enumerate(order):
                x1=14 if side==0 else width*.57
                x2=width*.43 if side==0 else width-14
                y1=10+row*gap;y2=y1+72
                active=side==0 and self.selected==index
                tag=f'node_{side}_{index}'
                c.create_rectangle(x1,y1,x2,y2,fill='#DDF2E5' if active else '#FFFFFF',outline='#39865B' if active else '#CADFD0',width=2 if active else 1,tags=(tag,))
                value=self.pairs[index][side]
                photo=self._photo(value)
                if photo:
                    c.create_image((x1+x2)/2,(y1+y2)/2,image=photo,tags=(tag,))
                else:
                    label=('[Không tìm thấy ảnh] '+value[4:]) if value.startswith(IMAGE_PREFIX) else value
                    c.create_text((x1+x2)/2,(y1+y2)/2,text=label,fill='#285D40',font=('Segoe UI',11,'bold'),width=max(80,int(x2-x1-16)),tags=(tag,))
                c.tag_bind(tag,'<Button-1>',lambda e,s=side,i=index:self.pick(s,i))
                nodes[(side,index)]=(x2 if side==0 else x1,(y1+y2)/2)
        palette=['#39865B','#5576C5','#D18B39','#A05CB9','#CC6470','#278C99']
        for n,(left,right) in enumerate(self.links.items()):
            a=nodes.get((0,left));b=nodes.get((1,right))
            if a and b:c.create_line(*a,*b,fill=('#17844D' if left==right else '#C53D4D') if self.readonly else palette[n%len(palette)],width=3,arrow='last',tags=('link',))
        if self.readonly:
            for left in range(len(self.pairs)):
                if self.links.get(left)!=left:
                    a=nodes.get((0,left));b=nodes.get((1,left))
                    if a and b:c.create_line(*a,*b,fill='#17844D',width=2,dash=(5,5),tags=('correct_hint',))
        c.tag_lower('correct_hint');c.tag_lower('link')

    def pick(self,side,index):
        if self.readonly:return
        if side==0:self.selected=index if self.selected!=index else None
        elif self.selected is not None:
            for k,v in list(self.links.items()):
                if v==index:del self.links[k]
            self.links[self.selected]=index;self.selected=None
            if self.on_change:self.on_change(self.links.copy())
        self.draw()

    def reset(self):
        self.selected=None;self.links.clear();self.draw()
        if self.on_change:self.on_change({})

    def result(self):
        return sum(a==b for a,b in self.links.items()),len(self.pairs),len(self.links)==len(self.pairs)
