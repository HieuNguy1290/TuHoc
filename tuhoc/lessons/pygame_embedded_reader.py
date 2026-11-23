"""Session-only Pygame rendered reader embedded in a Tkinter Frame.
No pygame display window or second event loop. No changes to curriculum files.
"""
import copy
import os
import unicodedata
import tkinter as tk
from tkinter import colorchooser, simpledialog, filedialog, messagebox
from pathlib import Path


def available():
    try:
        import pygame
        from PIL import Image, ImageTk
        return True
    except ImportError:
        return False


class EmbeddedReader(tk.Frame):
    def __init__(self, master, item, image_file=None, speak=None, external_dock=False, on_add_vocab=None, on_play_audio=None, **kwargs):
        super().__init__(master, bg='#eaf3f9', **kwargs)
        import pygame
        from PIL import Image, ImageTk
        self.pg=pygame; self.Image=Image; self.ImageTk=ImageTk
        pygame.font.init()
        self.item=item; self.image_file=image_file; self.speak=speak
        self.on_add_vocab=on_add_vocab; self.on_play_audio=on_play_audio
        self._selection_range=None; self._selection_popup=None
        self.mode='select'; self.tool_colors={'draw':'#000000','fill':'#FFD600','highlight':'#FFF3A3','underline':'#E53935','textbox':'#202020','note':'#245c80'}; self.color=self.tool_colors['draw']; self.width=3
        self.strokes=[]; self.redo=[]; self.current=[]; self.notes=[]
        self._pictures=[]; self._picture_selected=None; self._picture_drag=None; self._picture_job=None; self._picture_history=[]; self._picture_future=[]
        self._select_start=None
        self._previous_layout=None
        self._resize_job=None; self._initial_render_job=None
        self.zoom=1.0; self.reading_dark=False; self._image_ref=None; self._page_width=0; self._page_cache_key=None; self._page_cache_image=None
        # Floating, draggable tool dock: a single icon opens the palette on hover.
        # The dock is positioned over the reader, not in the document flow.
        self._dock_open=False
        self._dock_drag_origin=None
        self._dock=tk.Frame(self,bg='#1c4567',bd=1,relief='solid')
        self._dock_handle=tk.Label(self._dock,text='✎  Công cụ',bg='#1c4567',fg='white',
                                   font=('Segoe UI',10,'bold'),padx=9,pady=7,cursor='fleur')
        self._dock_handle.pack(fill='x')
        # Toggle is handled on release unless the icon was dragged.
        self._dock_handle.bind('<ButtonPress-1>',self._dock_start)
        self._dock_handle.bind('<B1-Motion>',self._dock_move)
        self._dock_handle.bind('<ButtonRelease-1>',self._dock_stop)
        self._dock_tools=tk.Frame(self._dock,bg='#e8f3fa')
        tools=[('✎ Vẽ',lambda:self.set_mode('draw')),('↔ Cuộn',lambda:self.set_mode('read')),
               ('🖍 Tô chữ',lambda:self.set_mode('highlight')),
               ('U̲ Gạch chân',lambda:self.set_mode('underline')),
               ('▣ Textbox',lambda:self.set_mode('textbox')),('▧ Add Picture',self.add_picture),
               ('🎨 Màu',self.choose_color),('Bút +',lambda:self.set_width(2)),
               ('Bút −',lambda:self.set_width(-2)),('↶ Undo',self.undo),
               ('↷ Redo',self.redo_action),('⌫ Tẩy',lambda:self.set_mode('erase')),
               ('✍ Ghi chú',lambda:self.set_mode('note')),('🗑 Xóa',self.clear),
               ('A+',lambda:self.set_zoom(.1)),('A−',lambda:self.set_zoom(-.1)),
               ('🔊 Đọc',self.read_aloud)]
        for idx,(label,fn) in enumerate(tools):
            tk.Button(self._dock_tools,text=label,command=fn,bg='white',fg='#245c80',
                      font=('Segoe UI',9),relief='groove',padx=5,pady=3,
                      width=12).grid(row=idx//2,column=idx%2,padx=2,pady=2,sticky='ew')
        if external_dock:
            self._dock.destroy()
        else:
            self._dock.place(x=16,y=80)
            self._dock.lift()
        self._annotation_start=None
        self._selected_text_rects=[]
        self._annotations=[]
        self._inline_editor=None
        self._selected_box=None; self._box_drag=None; self._history=[]; self._future=[]
        self.status=tk.StringVar(value='Chế độ đọc: cuộn chuột để xem toàn bài. Nét vẽ chỉ tồn tại trong lần mở bài này.')
        tk.Label(self,textvariable=self.status,bg='#eaf3f9',fg='#245c80',anchor='w',font=('Segoe UI',9)).pack(fill='x',padx=10)
        outer=tk.Frame(self,bg='#eaf3f9');outer.pack(fill='both',expand=True,padx=7,pady=(3,8))
        self.canvas=tk.Canvas(outer,bg='#eaf3f9',highlightthickness=0,height=460)
        scrollbar=tk.Scrollbar(outer,orient='vertical',command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        # Stable geometry: create the canvas and scrollbar as direct children of
        # their actual packing parent. Never mix pack(in_=...) with a grid parent.
        # The reader retains the same Canvas instance and annotation objects.
        self.canvas.destroy()
        scrollbar.destroy()
        outer.grid_rowconfigure(0,weight=1)
        outer.grid_columnconfigure(0,weight=1)
        reading_column=tk.Frame(outer,bg='#eaf3f9')
        reading_column.grid(row=0,column=0,sticky='nsew')
        reading_column.grid_rowconfigure(0,weight=1)
        reading_column.grid_columnconfigure(0,weight=1)
        self.canvas=tk.Canvas(reading_column,bg='#eaf3f9',highlightthickness=0,height=460)
        scrollbar=tk.Scrollbar(reading_column,orient='vertical',command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.grid(row=0,column=0,sticky='nsew')
        scrollbar.grid(row=0,column=1,sticky='ns')
        # Use the outer frame to center a fixed-width reading column without
        # constraining its height; avoids blank pages after layout changes.
        def fit_column(event):
            if not reading_column.winfo_exists():return
            available=max(1,event.width)
            width=max(1,available-18)
            self.canvas.configure(width=max(1,width-24))
        outer.bind('<Configure>',fit_column,add='+')
        self.canvas.bind('<ButtonPress-1>',self.on_down)
        self.canvas.bind('<Delete>',lambda e:self.delete_picture())
        self.canvas.bind('<Control-c>',self.copy_selected_text)
        self.canvas.configure(takefocus=1)
        self.canvas.bind('<B1-Motion>',self.on_drag)
        self.canvas.bind('<ButtonRelease-1>',self.on_up)
        self.canvas.bind('<MouseWheel>',lambda e:self._scroll_reader(-int(e.delta/120)*3))
        self.canvas.bind('<Button-4>',lambda e:self._scroll_reader(-3))
        self.canvas.bind('<Button-5>',lambda e:self._scroll_reader(3))
        self.canvas.bind('<Configure>',self._on_resize)
        self._reader_actions=tk.Frame(self,bg='#EAF3F9')
        self._reader_actions.pack(side='bottom',fill='x',padx=12,pady=(0,16))
        for label,fn in [('🔊 Nghe bài đọc',self.play_reading_audio)]:
            tk.Button(self._reader_actions,text=label,command=fn,bg='#FFFFFF',fg='#205B88',
                activebackground='#DCEFFF',font=('Segoe UI',10,'bold'),bd=0,highlightthickness=1,
                highlightbackground='#A5C7E3',padx=14,pady=8,cursor='hand2').pack(side='left',padx=5)
        self._expand_reading_button=tk.Button(self._reader_actions,text='⛶ Mở rộng',command=lambda:None,
            bg='#FFFFFF',fg='#205B88',activebackground='#DCEFFF',font=('Segoe UI',10,'bold'),
            bd=0,highlightthickness=1,highlightbackground='#A5C7E3',padx=14,pady=8,cursor='hand2')
        self._expand_reading_button.pack(side='left',padx=5)
        self._initial_render_job=self.after(50,self.render)
        self._picture_job=self.after(45,self._animate_pictures)
        if not external_dock:self.after(70,self._dock.lift)

    def add_picture(self):
        """Select an image; next click anchors it to the reading document."""
        path=filedialog.askopenfilename(parent=self,title='Add Picture',filetypes=[('Images','*.png *.jpg *.jpeg *.gif *.webp *.bmp'),('All files','*.*')])
        if not path:return
        from PIL import Image,ImageSequence
        try:
            frames=[];durations=[]
            with Image.open(path) as image:
                for frame in ImageSequence.Iterator(image):
                    frames.append(frame.convert('RGBA').copy())
                    durations.append(max(30,int(frame.info.get('duration',image.info.get('duration',100)) or 100)))
                    if len(frames)>=300:break
            if not frames:return
            width,height=frames[0].size
            factor=min(1.0,340/max(1,width),260/max(1,height))
            self._pending_picture={'frames':frames,'durations':durations,'frame':0,'elapsed':0,
                'x':0,'y':0,'w':max(30,int(width*factor)),'h':max(30,int(height*factor)),
                'item':None,'handles':[],'photo':None,'cache_key':None}
            self.set_mode('picture')
        except (OSError,ValueError) as exc:
            messagebox.showerror('Add Picture',f'Không thể mở ảnh: {exc}',parent=self)

    def _clear_pictures(self):
        self._pending_picture=None
        for pic in self._pictures:
            self._destroy_picture_widgets(pic)
        self._pictures.clear();self._picture_selected=None
        self._picture_history.clear();self._picture_future.clear()

    def _destroy_picture_widgets(self,pic):
        # Canvas items, rather than child Labels, avoid native-window repaint trails.
        if not hasattr(self,'canvas') or not self.canvas.winfo_exists():return
        if pic.get('item') is not None:self.canvas.delete(pic['item'])
        for item in pic.get('handles',[]):self.canvas.delete(item)
        pic['item']=None;pic['handles']=[];pic['photo']=None;pic['cache_key']=None

    def _scroll_reader(self, units):
        self.canvas.yview_scroll(units,'units')

    def _schedule_picture_refresh(self):
        if not getattr(self,'_pictures',None):return
        if getattr(self,'_picture_refresh_pending',False):return
        self._picture_refresh_pending=True
        self.after_idle(self._refresh_pictures)

    def delete_picture(self):
        pic=self._picture_selected
        if pic is None:return
        self._picture_history.append(('delete',pic,None));self._picture_future.clear()
        self._pictures.remove(pic);self._picture_selected=None
        self._refresh_pictures()

    def _picture_hit(self,event):
        """Hit test screen-space image and handles, independent of document text."""
        px,py=self.canvas.canvasx(event.x),self.canvas.canvasy(event.y)
        selected=self._picture_selected
        if selected in self._pictures:
            x,y,w,h=(selected[k] for k in ('x','y','w','h'))
            for name,fx,fy in [('nw',0,0),('n',.5,0),('ne',1,0),('e',1,.5),('se',1,1),('s',.5,1),('sw',0,1),('w',0,.5)]:
                if abs(px-(x+w*fx))<=9 and abs(py-(y+h*fy))<=9:
                    return selected,name
        for pic in reversed(self._pictures):
            x,y,w,h=(pic[k] for k in ('x','y','w','h'))
            if x<=px<=x+w and y<=py<=y+h:
                return pic,None
        return None

    def _picture_press(self,event,pic,handle=None):
        self.canvas.focus_set()
        self._picture_selected=pic
        self._picture_drag=(pic,handle,event.x_root,event.y_root,(pic['x'],pic['y'],pic['w'],pic['h']))
        self._refresh_pictures()
        return 'break'

    def _picture_move(self,event):
        if not self._picture_drag:return 'break'
        pic,handle,sx,sy,orig=self._picture_drag
        dx=event.x_root-sx;dy=event.y_root-sy
        x,y,w,h=orig
        if handle is None:x+=dx;y+=dy
        else:
            if 'w' in handle:x+=dx;w-=dx
            if 'e' in handle:w+=dx
            if 'n' in handle:y+=dy;h-=dy
            if 's' in handle:h+=dy
            if w<24:
                if 'w' in handle:x-=24-w
                w=24
            if h<24:
                if 'n' in handle:y-=24-h
                h=24
        pic.update(x=int(x),y=int(y),w=int(w),h=int(h))
        self._refresh_pictures()
        return 'break'

    def _picture_release(self,event):
        if self._picture_drag:
            pic,handle,sx,sy,orig=self._picture_drag
            if orig!=(pic['x'],pic['y'],pic['w'],pic['h']):
                self._picture_history.append(('change',pic,orig));self._picture_future.clear()
        self._picture_drag=None
        return 'break'

    def _refresh_pictures(self):
        self._picture_refresh_pending=False
        if not hasattr(self,'canvas') or not self.canvas.winfo_exists():return
        canvas=self.canvas
        # Image positions are document-space Canvas coordinates, just like ink.
        # Scrolling moves the page and pictures together; no viewport offset.
        for pic in self._pictures:
            x=pic['x'];y=pic['y']
            key=(pic['frame'],pic['w'],pic['h'])
            if key!=pic.get('cache_key') or pic.get('photo') is None:
                resized=pic['frames'][pic['frame']].resize((pic['w'],pic['h']),self.Image.Resampling.BILINEAR)
                pic['photo']=self.ImageTk.PhotoImage(resized,master=canvas)
                pic['cache_key']=key
            if pic.get('item') is None:
                pic['item']=canvas.create_image(x,y,anchor='nw',image=pic['photo'],tags=('overlay_picture',))
            else:
                canvas.coords(pic['item'],x,y)
                canvas.itemconfigure(pic['item'],image=pic['photo'])
            for item in pic.get('handles',[]):canvas.delete(item)
            pic['handles']=[]
            if pic is self._picture_selected:
                for name,fx,fy in [('nw',0,0),('n',.5,0),('ne',1,0),('e',1,.5),('se',1,1),('s',.5,1),('sw',0,1),('w',0,.5)]:
                    hx=x+int(pic['w']*fx);hy=y+int(pic['h']*fy)
                    item=canvas.create_rectangle(hx-5,hy-5,hx+5,hy+5,fill='#2686DB',outline='white',tags=('overlay_picture_handle',))
                    pic['handles'].append(item)
        # Images and resize handles remain above the reading page.
        canvas.tag_raise('overlay_picture')
        canvas.tag_raise('overlay_picture_handle')
        for action,pic,old in self._picture_history+self._picture_future:
            if pic not in self._pictures and pic.get('item') is not None:self._destroy_picture_widgets(pic)

    def _animate_pictures(self):
        import time
        now=time.monotonic()*1000
        previous=getattr(self,'_picture_last_tick',now)
        elapsed=min(200,max(0,now-previous));self._picture_last_tick=now
        for pic in self._pictures:
            if len(pic['frames'])<2:continue
            pic['elapsed']+=elapsed
            changed=False
            while pic['elapsed']>=pic['durations'][pic['frame']]:
                pic['elapsed']-=pic['durations'][pic['frame']]
                pic['frame']=(pic['frame']+1)%len(pic['frames']);changed=True
            if changed:
                pic['cache_key']=None
                resized=pic['frames'][pic['frame']].resize((pic['w'],pic['h']),self.Image.Resampling.BILINEAR)
                pic['photo']=self.ImageTk.PhotoImage(resized,master=self.canvas)
                if pic.get('item') is not None:self.canvas.itemconfigure(pic['item'],image=pic['photo'])
        if self.winfo_exists():self._picture_job=self.after(45,self._animate_pictures)

    def _toggle_dock(self):
        self._dock_open=not self._dock_open
        if self._dock_open:self._dock_tools.pack(fill='both')
        else:self._dock_tools.pack_forget()
        self._dock.lift()

    def _dock_start(self,event):
        self._dock_drag_origin=(event.x_root,event.y_root,self._dock.winfo_x(),self._dock.winfo_y()); self._dock_moved=False

    def _dock_move(self,event):
        if self._dock_drag_origin is None:return
        sx,sy,ox,oy=self._dock_drag_origin
        if abs(event.x_root-sx)+abs(event.y_root-sy)>5:self._dock_moved=True
        x=max(0,min(ox+event.x_root-sx,max(0,self.winfo_width()-self._dock.winfo_width())))
        y=max(0,min(oy+event.y_root-sy,max(0,self.winfo_height()-self._dock.winfo_height())))
        self._dock.place(x=x,y=y)

    def _dock_stop(self,event):
        if self._dock_drag_origin is not None and not getattr(self,'_dock_moved',False):self._toggle_dock()
        self._dock_drag_origin=None

    def set_mode(self,mode):
        self.mode=mode
        self._picture_selected=None;self._refresh_pictures()
        self.color=self.tool_colors.get(mode,self.color)
        self.canvas.configure(cursor='xterm' if mode=='select' else ('crosshair' if mode in ('draw','erase','note','highlight','underline','textbox','fill') else 'arrow'))
        self.status.set({'draw':'Vẽ trực tiếp lên bài; cuộn chuột không làm lệch nét.','read':'Chế độ đọc: nét vẽ vẫn giữ nguyên.','erase':'Nhấp vào nét để xóa cả nét.','note':'Nhấp vị trí muốn đặt ghi chú.', 'fill':'Kéo chuột để tô một vùng.','highlight':'Kéo chuột để tô sáng vùng chữ.', 'underline':'Kéo chuột để gạch chân vùng chữ.', 'textbox':'Nhấp để đặt hộp văn bản.','select':'Kéo chuột để chọn chữ, sau đó nhấn Highlight.','picture':'Nhấp lên bài đọc để đặt ảnh.'}[mode])
    def choose_color(self):
        picked=colorchooser.askcolor(color=self.tool_colors.get(self.mode,self.color),parent=self)[1]
        if picked:self.set_tool_color(self.mode,picked)
    def set_tool_color(self,mode,color):
        self.tool_colors[mode]=color
        if self.mode==mode:self.color=color
    def set_width(self,delta):self.width=max(1,min(15,self.width+delta))
    def set_zoom(self,delta):
        self.zoom=max(.7,min(1.7,round(self.zoom+delta,2)));self.render()
    def set_reading_preferences(self,zoom=None,dark=None):
        if zoom is not None:self.zoom=max(.7,min(1.7,float(zoom)))
        if dark is not None:self.reading_dark=bool(dark)
        self.configure(bg='#101010' if self.reading_dark else '#eaf3f9')
        self.canvas.configure(bg='#101010' if self.reading_dark else '#eaf3f9')
        try:self.canvas.master.configure(bg='#101010' if self.reading_dark else '#eaf3f9')
        except tk.TclError:pass
        self.render()

    def read_aloud(self):
        self.play_reading_audio()
    def clear(self):
        self._checkpoint()
        self.strokes.clear();self.redo.clear();self.notes.clear();self._annotations.clear();self._clear_pictures();self.render()
    def _checkpoint(self):
        self._history.append((copy.deepcopy(self._annotations),copy.deepcopy(self.strokes)))
        if len(self._history)>80:self._history.pop(0)
        self._future.clear()

    def undo(self):
        if self._picture_history:
            action,pic,old=self._picture_history.pop()
            self._picture_future.append((action,pic,(pic['x'],pic['y'],pic['w'],pic['h'])))
            if action=='add' and pic in self._pictures:self._pictures.remove(pic)
            elif action=='delete' and pic not in self._pictures:self._pictures.append(pic)
            elif action=='change':pic['x'],pic['y'],pic['w'],pic['h']=old
            self._picture_selected=None;self._refresh_pictures();return
        if self._history:
            self._future.append((copy.deepcopy(self._annotations),copy.deepcopy(self.strokes)))
            self._annotations,self.strokes=self._history.pop()
            self._selected_box=None;self.render();return
        if self._annotations:self.redo.append(('annotation',self._annotations.pop()));self.render()
        elif self.strokes:self.redo.append(('stroke',self.strokes.pop()));self.render()
    def redo_action(self):
        if self._picture_future:
            action,pic,old=self._picture_future.pop()
            self._picture_history.append((action,pic,(pic['x'],pic['y'],pic['w'],pic['h'])))
            if action=='add' and pic not in self._pictures:self._pictures.append(pic)
            elif action=='delete' and pic in self._pictures:self._pictures.remove(pic)
            elif action=='change':pic['x'],pic['y'],pic['w'],pic['h']=old
            self._picture_selected=None;self._refresh_pictures();return
        if self._future:
            self._history.append((copy.deepcopy(self._annotations),copy.deepcopy(self.strokes)))
            self._annotations,self.strokes=self._future.pop()
            self._selected_box=None;self.render();return
        if self.redo:
            kind,value=self.redo.pop()
            (self._annotations if kind=='annotation' else self.strokes).append(value)
            self.render()
    def _on_resize(self,event):
        # Debounce resize storms without leaving stale callbacks behind.
        if abs(event.width-self._page_width)<=12:
            return
        if self._resize_job is not None:
            try:self.after_cancel(self._resize_job)
            except tk.TclError:pass
        self._resize_job=self.after(130,self._render_after_resize)

    def _render_after_resize(self):
        self._resize_job=None
        if self.winfo_exists() and self.canvas.winfo_exists():
            self.render()

    def destroy(self):
        # Avoid callbacks targeting a Canvas destroyed during page navigation.
        for name in ('_resize_job','_initial_render_job'):
            job=getattr(self,name,None)
            if job is not None:
                try:self.after_cancel(job)
                except tk.TclError:pass
                setattr(self,name,None)
        if self._picture_job is not None:
            try:self.after_cancel(self._picture_job)
            except tk.TclError:pass
            self._picture_job=None
        self._clear_pictures()
        super().destroy()

    def _annotation_font_size(self):
        # Notes and textboxes should follow the same reading zoom as body text.
        return max(9,min(24,round(12*self.zoom)))
    def _reading_font(self, size, bold=False):
        # Pygame's default Arial substitute may lack Vietnamese combining glyphs.
        pg=self.pg
        for name in ('Noto Sans', 'DejaVu Sans', 'Arial Unicode MS', 'Segoe UI', 'Arial'):
            path=pg.font.match_font(name, bold=bold)
            if path:
                try:return pg.font.Font(path, size)
                except (OSError, ValueError):pass
        return pg.font.SysFont('arial',size,bold=bold)

    @staticmethod
    def _line_offsets(lines):
        offsets=[]; total=0
        for line in lines:
            offsets.append(total)
            total+=len(line)+1
        return offsets

    def _text_anchor_rects(self, annotation):
        anchor=annotation.get('text_span')
        if not anchor:return annotation.get('rects',[])
        lo,hi=sorted(anchor)
        offsets=self._line_offsets([line[0] for line in self._text_lines])
        boxes=[]
        for i,(line,x,y,font,size) in enumerate(self._text_lines):
            a=max(0,lo-offsets[i]);b=min(len(line),hi-offsets[i])
            if a<b:
                boxes.append((10+x+font.size(line[:a])[0],y-2,
                              10+x+font.size(line[:b])[0],y+size+5))
        return boxes

    def _reflow_annotations(self, old, new):
        # Map ink and placed objects to their nearest text position when font size
        # or wrapping changes. Semantic text highlights use text_span separately.
        if not old or not old['lines'] or not new['lines']:return
        ow,oh=old['width'],old['height']; nw,nh=new['width'],new['height']
        old_lines=old['lines']; new_lines=new['lines']
        old_offsets=self._line_offsets([t[0] for t in old_lines])
        new_offsets=self._line_offsets([t[0] for t in new_lines])
        def remap(pos):
            px=pos[0]*ow;py=pos[1]*oh
            idx=min(range(len(old_lines)),key=lambda i:abs(old_lines[i][2]-py))
            line,lx,ly,font,size=old_lines[idx]
            if abs(py-ly)>max(65,size*2):return (pos[0],pos[1])
            dx=max(0,px-lx)
            char=min(range(len(line)+1),key=lambda j:abs(font.size(line[:j])[0]-dx))
            offset=old_offsets[idx]+char
            target=len(new_lines)-1
            for j,t in enumerate(new_lines):
                if new_offsets[j]<=offset<=new_offsets[j]+len(t[0]):target=j;break
            text,x,y,new_font,new_size=new_lines[target]
            char_new=max(0,min(len(text),offset-new_offsets[target]))
            nx=x+new_font.size(text[:char_new])[0]
            ny=y+(py-ly)*new_size/max(1,size)
            return (max(0,min(1,nx/max(1,nw))),max(0,min(1,ny/max(1,nh))))
        for a in self._annotations:
            if a['kind']=='highlight' and a.get('text_span'):continue
            a['start']=remap(a['start']);a['end']=remap(a['end'])
        self.notes=[(*remap((x,y)),note) for x,y,note in self.notes]

    def render(self):
        if not self.winfo_exists() or not self.canvas.winfo_exists():return
        # Rebuilding the page must not jump the reader back to the beginning.
        try: old_scroll=self.canvas.yview()[0]
        except (tk.TclError, IndexError): old_scroll=0.0
        pg=self.pg; w=max(240,self.canvas.winfo_width()-28);self._page_width=self.canvas.winfo_width()
        size=int(23*self.zoom);f=self._reading_font(size);titlefont=self._reading_font(int(30*self.zoom),bold=True)
        content=str(self.item.get('content') or '')
        lines=[]
        for paragraph in content.splitlines() or ['']:
            line=''
            for word in paragraph.split():
                candidate=(line+' '+word).strip()
                if line and f.size(candidate)[0]>w-65:lines.append(line);line=word
                else:line=candidate
            lines.append(line)
        picture=None
        if self.image_file:
            try:
                picture=self.Image.open(self.image_file).convert('RGB')
                picture.thumbnail((w-65,int(260*self.zoom)))
            except (OSError,ValueError):picture=None
        picture_height=picture.height+22 if picture else 0
        line_h=int(39*self.zoom)
        h=max(450,110+picture_height+len(lines)*line_h+55)
        surf=pg.Surface((w,h));surf.fill((16,16,16) if self.reading_dark else (255,255,255))
        surf.blit(titlefont.render(str(self.item.get('title') or 'Bài đọc'),True,((240,240,240) if self.reading_dark else (37,92,128))),(28,25))
        y=95
        if picture:
            pic=pg.image.fromstring(picture.tobytes(),picture.size,'RGB')
            surf.blit(pic,((w-picture.width)//2,y));y+=picture_height
        self._text_lines=[]
        for line in lines:
            if line:
                surf.blit(f.render(line,True,((231,239,231) if self.reading_dark else (38,58,73))),(30,y))
                self._text_lines.append((line,30,y,f,size))
            y+=line_h
        new_layout={'lines':self._text_lines,'width':w,'height':h,'font_size':size}
        if self._previous_layout and (self._previous_layout['width']!=w or
                                      self._previous_layout['height']!=h or
                                      self._previous_layout.get('font_size')!=size):
            self._reflow_annotations(self._previous_layout,new_layout)
        self._previous_layout=new_layout
        # Render highlight below text on the same RGB page: no Tk stipple/dots.
        # Text remains opaque and readable above the uniform highlight.
        for a in self._annotations:
            if a['kind'] != 'highlight':
                continue
            try: rgb=tuple(int(a['color'][i:i+2],16) for i in (1,3,5))
            except (ValueError,IndexError):rgb=(255,243,163)
            for bx1,by1,bx2,by2 in self._text_anchor_rects(a):
                pg.draw.rect(surf,rgb,pg.Rect(int(bx1-10),int(by1),max(1,int(bx2-bx1)),max(1,int(by2-by1))))
        if any(a['kind']=='highlight' for a in self._annotations):
            # Redraw text *after* highlights. On dark pages choose ink per
            # highlighted background luminance, not the global dark-mode ink.
            # Otherwise pale-yellow highlights with near-white ink are unreadable.
            for line,lx,ly,font,_ in self._text_lines:
                if not self.reading_dark:
                    surf.blit(font.render(line,True,(38,58,73)),(lx,ly))
                    continue
                normal_ink=(238,238,238)
                surf.blit(font.render(line,True,normal_ink),(lx,ly))
                # Clip glyphs to each highlight rectangle; this preserves the
                # original text position and any previously drawn annotations.
                for a in self._annotations:
                    if a['kind']!='highlight':continue
                    try:
                        rgb=tuple(int(a['color'][i:i+2],16) for i in (1,3,5))
                    except (ValueError,IndexError):rgb=(255,243,163)
                    luminance=(0.2126*rgb[0]+0.7152*rgb[1]+0.0722*rgb[2])
                    ink=(24,24,24) if luminance>=145 else (255,255,255)
                    glyph=font.render(line,True,ink)
                    for bx1,by1,bx2,by2 in self._text_anchor_rects(a):
                        clip=pg.Rect(int(bx1-10),int(by1),max(1,int(bx2-bx1)),max(1,int(by2-by1)))
                        previous=surf.get_clip()
                        surf.set_clip(clip)
                        surf.blit(glyph,(lx,ly))
                        surf.set_clip(previous)
        raw=pg.image.tostring(surf,'RGB')
        self._image_ref=self.ImageTk.PhotoImage(self.Image.frombytes('RGB',(w,h),raw),master=self.canvas)
        self._hide_selection_popup()
        self.canvas.delete('all')
        for pic in self._pictures:
            pic['item']=None;pic['handles']=[]
        self.canvas.create_image(10,0,anchor='nw',image=self._image_ref,tags=('page',))
        self.canvas.configure(scrollregion=(0,0,w+20,h))
        self.canvas.yview_moveto(old_scroll)
        for s in self.strokes:self._draw_stroke(s)
        for a in self._annotations:self._draw_annotation(a)
        self._draw_selection()
        self._draw_box_controls()
        self._refresh_pictures()
        for x,y,note in self.notes:self.canvas.create_text(10+x*w,y*h,text=note,anchor='nw',fill=('#BBDFFF' if self.reading_dark else '#2865aa'),font=('Segoe UI',self._annotation_font_size(),'bold'),tags='note')
        self.canvas.tag_raise('overlay_picture')
        self.canvas.tag_raise('overlay_picture_handle')
    def _draw_annotation(self,a):
        w=max(240,self.canvas.winfo_width()-28)
        h=max(1,int(self.canvas.cget('scrollregion').split()[-1]))
        x1,y1=10+a['start'][0]*w,a['start'][1]*h
        x2,y2=10+a['end'][0]*w,a['end'][1]*h
        if a['kind']=='highlight':
            # Already composited behind glyphs in the Pygame page surface.
            return
        elif a['kind']=='fill':
            self.canvas.create_rectangle(min(x1,x2),min(y1,y2),max(x1,x2),max(y1,y2),fill=a['color'],outline='',tags='annotation')
        elif a['kind']=='underline':
            self.canvas.create_line(x1,y2,x2,y2,fill=a['color'],width=3,tags='annotation')
        elif a['kind']=='textbox':
            a['_canvas_id']=self.canvas.create_text(x1,y1,text=a['text'],anchor='nw',fill=('#F0F0F0' if self.reading_dark and a['color']=='#202020' else a['color']),
                                    font=('Segoe UI',self._annotation_font_size()),tags='annotation')

    def _draw_selection(self):
        # Selection is drawn on top of the page, followed by white selected glyphs.
        # This matches native text selection rather than an opaque overlay hiding text.
        self.canvas.delete('text_selection')
        self._selection_images=[]
        if not self._selection_range:return
        start,end=sorted(self._selection_range)
        for i in range(start[0],end[0]+1):
            if i>=len(getattr(self,'_text_lines',[])):break
            line,lx,ly,font,size=self._text_lines[i]
            a=start[1] if i==start[0] else 0
            b=end[1] if i==end[0] else len(line)
            if a>=b:continue
            x1=10+lx+font.size(line[:a])[0]
            x2=10+lx+font.size(line[:b])[0]
            self.canvas.create_rectangle(x1,ly-2,x2,ly+size+5,fill='#2478D4',outline='',tags='text_selection')
            selected=line[a:b]
            surface=font.render(selected,True,(255,255,255))
            raw=self.pg.image.tostring(surface,'RGBA')
            photo=self.ImageTk.PhotoImage(self.Image.frombytes('RGBA',surface.get_size(),raw),master=self.canvas)
            if not hasattr(self,'_selection_images'):self._selection_images=[]
            self._selection_images.append(photo)
            self.canvas.create_image(x1,ly,anchor='nw',image=photo,tags='text_selection')

    def _draw_box_controls(self):
        self.canvas.delete('box_controls')
        i=self._selected_box
        if i is None or i>=len(self._annotations):return
        a=self._annotations[i]
        if a['kind']!='textbox':return
        ident=a.get('_canvas_id')
        if not ident:return
        bounds=self.canvas.bbox(ident)
        if not bounds:return
        self.canvas.create_rectangle(*bounds,outline='#2686DB',width=2,dash=(5,3),tags='box_controls')
        x1,y1,x2,y2=bounds
        self.canvas.create_rectangle(x2-5,y2-5,x2+5,y2+5,fill='#2686DB',outline='white',tags='box_controls')
        bar=tk.Frame(self.canvas,bg='white',highlightbackground='#9FC7E8',highlightthickness=1)
        for name,cmd in [('✎ Sửa',self.edit_selected_box),('✕ Xóa',self.delete_selected_box)]:
            tk.Button(bar,text=name,command=cmd,bd=0,bg='#EDF5FF',fg='#185587',cursor='hand2').pack(side='left',padx=3,pady=3)
        self.canvas.create_window(x1,max(0,y1-35),window=bar,anchor='nw',tags='box_controls')

    def _box_at(self,event):
        x,y=self.canvas.canvasx(event.x),self.canvas.canvasy(event.y)
        for i in range(len(self._annotations)-1,-1,-1):
            a=self._annotations[i]
            if a['kind']!='textbox':continue
            bounds=self.canvas.bbox(a.get('_canvas_id')) if a.get('_canvas_id') else None
            if bounds and bounds[0]-5<=x<=bounds[2]+5 and bounds[1]-5<=y<=bounds[3]+5:return i
        return None

    def edit_selected_box(self):
        i=self._selected_box
        if i is None:return
        a=self._annotations[i]
        w=max(240,self.canvas.winfo_width()-28);h=max(1,int(self.canvas.cget('scrollregion').split()[-1]))
        x=10+a['start'][0]*w;y=a['start'][1]*h
        self._open_editor(x,y,a['start'],i,a['text'])

    def delete_selected_box(self):
        if self._selected_box is None:return
        self._checkpoint();self._annotations.pop(self._selected_box)
        self._selected_box=None;self.render()

    def _text_hit(self,event):
        x=self.canvas.canvasx(event.x)-10
        y=self.canvas.canvasy(event.y)
        for i,(line,lx,ly,font,size) in enumerate(getattr(self,'_text_lines',[])):
            if ly-3<=y<=ly+size+8:
                offset=max(0,x-lx)
                index=0
                for j in range(1,len(line)+1):
                    if font.size(line[:j])[0]>=offset:
                        index=j if abs(font.size(line[:j])[0]-offset)<abs(font.size(line[:j-1])[0]-offset) else j-1
                        break
                else:index=len(line)
                return i,index
        return None

    def _selection_boxes(self,a,b):
        if a is None or b is None:return []
        if a>b:a,b=b,a
        boxes=[]
        for i in range(a[0],b[0]+1):
            line,lx,ly,font,size=self._text_lines[i]
            start=a[1] if i==a[0] else 0
            end=b[1] if i==b[0] else len(line)
            if start==end:continue
            x1=10+lx+font.size(line[:start])[0]
            x2=10+lx+font.size(line[:end])[0]
            boxes.append((x1,ly-2,x2,ly+size+5))
        return boxes

    def selected_text(self):
        rng=self._selection_range
        if not rng:return ''
        a,b=rng
        if a>b:a,b=b,a
        lines=getattr(self,'_text_lines',[])
        if not lines or a[0]>=len(lines) or b[0]>=len(lines):return ''
        parts=[]
        for i in range(a[0],b[0]+1):
            line=lines[i][0]
            parts.append(line[a[1] if i==a[0] else 0:b[1] if i==b[0] else len(line)])
        return ' '.join(parts).strip()

    def copy_selected_text(self,event=None):
        text=self.selected_text()
        if text:
            self.clipboard_clear();self.clipboard_append(text)
        return 'break'

    def _hide_selection_popup(self):
        popup=self._selection_popup
        self._selection_popup=None
        if popup is not None:
            try:popup.destroy()
            except tk.TclError:pass

    def _show_selection_popup(self):
        self._hide_selection_popup()
        text=self.selected_text()
        if not text:return
        bar=tk.Frame(self.canvas,bg='#FFFFFF',highlightthickness=1,highlightbackground='#90B4D8',bd=0)
        self._selection_popup=bar
        actions=[('☆ Thêm từ',self.add_selected_vocabulary),('🔊 Phát âm',self.speak_selected_text),('🖍 Highlight',self.apply_text_highlight),('⧉ Sao chép',self.copy_selected_text)]
        for label,command in actions:
            tk.Button(bar,text=label,command=command,bg='#F2F7FF',fg='#174E80',bd=0,
                      activebackground='#D9ECFF',font=('Segoe UI',9,'bold'),padx=7,pady=5,
                      cursor='hand2').pack(side='left',padx=2,pady=3)
        box=self._selected_text_rects[0]
        x=max(5,min(box[0],self.canvas.canvasx(0)+max(5,self.canvas.winfo_width()-390)))
        y=max(self.canvas.canvasy(0)+5,box[1]-44)
        self.canvas.create_window(x,y,window=bar,anchor='nw',tags='selection_toolbar')

    def add_selected_vocabulary(self):
        text=self.selected_text()
        if not text:return
        if callable(self.on_add_vocab):
            try:self.on_add_vocab(text)
            except Exception as exc:messagebox.showerror('Từ vựng',str(exc),parent=self)
        else:self.status.set('Chưa kết nối kho từ vựng cho bài đọc này.')

    def speak_selected_text(self):
        text=self.selected_text()
        if not text:return
        if callable(self.speak):
            try:self.speak(text)
            except Exception as exc:messagebox.showerror('Phát âm',str(exc),parent=self)
        else:self.status.set('Chưa có công cụ phát âm trên thiết bị này.')

    def play_reading_audio(self):
        if callable(self.on_play_audio):
            try:self.on_play_audio()
            except Exception as exc:messagebox.showerror('Âm thanh',str(exc),parent=self)
        else:
            self.speak_reading_fallback()

    def speak_reading_fallback(self):
        text=str(self.item.get('content') or '').strip()
        if callable(self.speak) and text:self.speak(text)
        else:self.status.set('Không có bài đọc hoặc giọng đọc tự động.')

    def apply_text_highlight(self):
        if not self._selected_text_rects:
            self.status.set('Chọn công cụ Chọn chữ, kéo bôi đen từ rồi nhấn Highlight.')
            return
        self._checkpoint()
        span=None
        if self._selection_range and self._text_lines:
            a,b=sorted(self._selection_range)
            offsets=self._line_offsets([line[0] for line in self._text_lines])
            if a[0]<len(offsets) and b[0]<len(offsets):
                span=(offsets[a[0]]+a[1],offsets[b[0]]+b[1])
        self._annotations.append({'kind':'highlight','start':(0,0),'end':(0,0),
                                  'rects':list(self._selected_text_rects),'text_span':span,
                                  'color':self.tool_colors['highlight']})
        self._selected_text_rects=[]
        self._selection_range=None
        self._hide_selection_popup()
        self.redo.clear()
        self.render()

    def _stroke_anchor(self, point):
        """Bind a stroke to a text character, without modifying its original points."""
        lines = self._text_lines
        if not lines:
            return None
        px, py = point
        index = min(range(len(lines)), key=lambda i: abs(lines[i][2] - py))
        line, lx, ly, font, size = lines[index]
        widths = [font.size(line[:i])[0] for i in range(len(line) + 1)]
        char = min(range(len(widths)), key=lambda i: abs(lx + widths[i] - px))
        offsets = self._line_offsets([item[0] for item in lines])
        return (offsets[index] + char, lx + widths[char], ly)

    def _stroke_anchor_target(self, offset):
        lines = self._text_lines
        if not lines:
            return None
        offsets = self._line_offsets([item[0] for item in lines])
        index = len(lines) - 1
        for i, (line, *_) in enumerate(lines):
            if offsets[i] <= offset <= offsets[i] + len(line):
                index = i
                break
        line, lx, ly, font, size = lines[index]
        char = max(0, min(len(line), offset - offsets[index]))
        return (lx + font.size(line[:char])[0], ly)

    def _stroke_screen_points(self, stroke):
        # Immutable source geometry. Only the render projection changes.
        source = stroke['points']
        if not source:
            return []
        origin_zoom = max(.01, float(stroke.get('zoom', self.zoom)))
        factor = self.zoom / origin_zoom
        anchor = stroke.get('text_anchor')
        if anchor is not None:
            target = self._stroke_anchor_target(anchor[0])
            if target is not None:
                ax, ay = anchor[1], anchor[2]
                tx, ty = target
                return [(tx + (x - ax) * factor, ty + (y - ay) * factor)
                        for x, y in source]
        return [(10 + (x - 10) * factor, y * factor) for x, y in source]

    def _draw_stroke(self,s):
        coords = self._stroke_screen_points(s)
        points = [v for xy in coords for v in xy]
        preview = s['points'] is self.current
        tag = 'preview_ink' if preview else 'ink'
        width = max(1, float(s['width']) * self.zoom / max(0.01, float(s.get('zoom', self.zoom))))
        if len(points) >= 4:
            self.canvas.create_line(*points, fill=s['color'], width=width,
                                    capstyle='round', joinstyle='round', smooth=True, tags=tag)
        elif points:
            x,y=points[:2]
            self.canvas.create_oval(x-2,y-2,x+2,y+2,fill=s['color'],outline='',tags=tag)
    def _ink_pos(self,event):
        return (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))

    def _pos(self,event):
        w=max(240,self.canvas.winfo_width()-28)
        h=max(1,int(self.canvas.cget('scrollregion').split()[-1]))
        return (max(0,min(1,(self.canvas.canvasx(event.x)-10)/w)),max(0,min(1,self.canvas.canvasy(event.y)/h)))
    def on_down(self,event):
        hit=self._picture_hit(event)
        if hit is not None:
            self._picture_press(event,*hit)
            return 'break'
        if self.mode=='picture' and getattr(self,'_pending_picture',None):
            pic=self._pending_picture;self._pending_picture=None
            pic['x'],pic['y']=self.canvas.canvasx(event.x),self.canvas.canvasy(event.y)
            self._pictures.append(pic);self._picture_history.append(('add',pic,None));self._picture_future.clear()
            self._picture_selected=pic;self._refresh_pictures();self.set_mode('read');self._picture_selected=pic;self._refresh_pictures();return
        if self._picture_selected is not None:
            self._picture_selected=None;self._refresh_pictures()
        if self.mode in ('select','read'):
            self.canvas.focus_set()
            box=self._box_at(event)
            if box is not None:
                self._selected_box=box;self._box_drag=(event.x_root,event.y_root,copy.deepcopy(self._annotations[box]['start']),False)
                self._draw_box_controls();return
            self._selected_box=None;self._draw_box_controls()
            self._hide_selection_popup()
            self._selection_range=None
            self._select_start=self._text_hit(event)
            self._selected_text_rects=[]
            self._draw_selection()
        elif self.mode=='draw':self.current=[self._ink_pos(event)]
        elif self.mode in ('highlight','underline','fill'):
            self._annotation_start=self._pos(event)
            self._highlight_start=self._text_hit(event) if self.mode=='highlight' else None
        elif self.mode=='textbox':
            self._start_inline_text(event)
        elif self.mode=='note':
            note=simpledialog.askstring('Ghi chú','Nhập nội dung ghi chú:',parent=self)
            if note:self.notes.append((*self._pos(event),note));self.render()
        elif self.mode=='erase':
            x,y=self._ink_pos(event)
            if self.strokes:
                nearest=min(range(len(self.strokes)),key=lambda i:min(((px-x)**2+(py-y)**2) for px,py in self._stroke_screen_points(self.strokes[i])))
                self.strokes.pop(nearest);self.render()
    def _start_inline_text(self,event):
        x,y=self.canvas.canvasx(event.x),self.canvas.canvasy(event.y)
        self._open_editor(x,y,self._pos(event),None,'')
    def _open_editor(self,x,y,pos,index,text):
        self._finish_inline_text()
        editor=tk.Text(self.canvas,width=25,height=2,wrap='word',bd=0,highlightthickness=0,
                       bg='white',fg=self.tool_colors['textbox'],font=('Segoe UI',self._annotation_font_size()),undo=True)
        window=self.canvas.create_window(x,y,window=editor,anchor='nw',tags='inline_editor')
        editor.insert('1.0',text)
        self._inline_editor=(editor,window,pos,index)
        editor.focus_set()
        editor.bind('<Control-Return>',lambda e:(self._finish_inline_text(),'break')[1])
        editor.bind('<Escape>',lambda e:(self._finish_inline_text(cancel=True),'break')[1])
        editor.bind('<FocusOut>',lambda e:self._finish_inline_text())
    def _finish_inline_text(self,cancel=False):
        active=self._inline_editor
        if not active:return
        self._inline_editor=None
        editor,window,pos,index=active
        try:value=editor.get('1.0','end-1c').strip()
        except tk.TclError:value=''
        try:self.canvas.delete(window);editor.destroy()
        except tk.TclError:pass
        if not cancel:
            if index is not None:
                if self._annotations[index]['text']!=value:
                    self._checkpoint()
                    if value:self._annotations[index]['text']=value
                    else:self._annotations.pop(index);self._selected_box=None
            elif value:
                self._checkpoint()
                self._annotations.append({'kind':'textbox','start':pos,'end':pos,'text':value,'color':self.tool_colors['textbox']})
            self.render()
    def on_drag(self,event):
        if self._picture_drag is not None:
            self._picture_move(event)
            return 'break'
        if self._box_drag is not None and self._selected_box is not None:
            sx,sy,orig,moved=self._box_drag
            dx=event.x_root-sx;dy=event.y_root-sy
            if abs(dx)+abs(dy)>4:moved=True
            self._box_drag=(sx,sy,orig,moved)
            if moved:
                w=max(240,self.canvas.winfo_width()-28);h=max(1,int(self.canvas.cget('scrollregion').split()[-1]))
                pos=(max(0,min(1,orig[0]+dx/w)),max(0,min(1,orig[1]+dy/h)))
                a=self._annotations[self._selected_box];a['start']=pos;a['end']=pos
                self.canvas.coords(a['_canvas_id'],10+pos[0]*w,pos[1]*h)
                self._draw_box_controls()
            return
        if self.mode in ('select','read'):
            end=self._text_hit(event)
            self._selection_range=(self._select_start,end) if self._select_start is not None and end is not None else None
            self._selected_text_rects=self._selection_boxes(self._select_start,end)
            self._draw_selection()
        elif self.mode=='draw' and self.current:
            self.current.append(self._ink_pos(event))
            self.canvas.delete('preview_ink')
            self._draw_stroke({'points':self.current,'color':self.tool_colors['draw'],'width':self.width,'zoom':self.zoom})
        elif self.mode in ('highlight','underline','fill') and self._annotation_start:
            self.canvas.delete('annotation_preview')
            w=max(240,self.canvas.winfo_width()-28);h=max(1,int(self.canvas.cget('scrollregion').split()[-1]))
            x1,y1=self._annotation_start; x2,y2=self._pos(event)
            x1=10+x1*w;x2=10+x2*w;y1=y1*h;y2=y2*h
            color=self.tool_colors[self.mode]
            if self.mode=='underline':self.canvas.create_line(x1,y2,x2,y2,fill=color,width=3,tags='annotation_preview')
            else:self.canvas.create_rectangle(x1,y1,x2,y2,fill=color,outline='',tags='annotation_preview')
    def on_up(self,event):
        if self._picture_drag is not None:
            self._picture_release(event)
            return 'break'
        if self._box_drag is not None:
            sx,sy,orig,moved=self._box_drag
            self._box_drag=None
            if moved:
                before=copy.deepcopy(self._annotations)
                before[self._selected_box]['start']=orig
                before[self._selected_box]['end']=orig
                self._history.append((before,copy.deepcopy(self.strokes)))
                self._future.clear()
                self.render()
            return
        if self.mode in ('select','read'):
            end=self._text_hit(event)
            self._selection_range=(self._select_start,end) if self._select_start is not None and end is not None else None
            self._selected_text_rects=self._selection_boxes(self._select_start,end)
            self._draw_selection()
            self._show_selection_popup()
        elif self.mode=='draw' and self.current:
            self._checkpoint()
            self.current.append(self._ink_pos(event))
            self.strokes.append({'points':self.current,'color':self.tool_colors['draw'],
                                 'width':self.width,'zoom':self.zoom,
                                 'text_anchor':self._stroke_anchor(self.current[0]) if self.current else None})
            self.current=[];self.redo.clear();self.render()
        elif self.mode in ('highlight','underline','fill') and self._annotation_start:
            end=self._pos(event)
            if self.mode=='highlight':
                hit_end=self._text_hit(event)
                hit_start=getattr(self,'_highlight_start',None)
                if hit_start is not None and hit_end is not None:
                    a,b=sorted((hit_start,hit_end))
                    offsets=self._line_offsets([line[0] for line in self._text_lines])
                    span=(offsets[a[0]]+a[1],offsets[b[0]]+b[1])
                    if span[0]!=span[1]:
                        self._checkpoint()
                        self._annotations.append({'kind':'highlight','start':self._annotation_start,
                            'end':end,'text_span':span,'rects':self._selection_boxes(a,b),
                            'color':self.tool_colors['highlight']})
                self._highlight_start=None
            else:
                self._checkpoint()
                self._annotations.append({'kind':self.mode,'start':self._annotation_start,
                                          'end':end,'color':self.tool_colors[self.mode]})
            self._annotation_start=None;self.redo.clear();self.canvas.delete('annotation_preview');self.render()
