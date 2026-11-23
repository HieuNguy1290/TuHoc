"""Persistent Windows cursor overlay. Soft dithered radial gradients, no canvas rings."""
import math
import sys
import time
import tkinter as tk

class MouseEffects:
    MODES = ('off', 'click', 'laser')
    SIZE = 160
    CENTER = SIZE // 2
    KEY = '#FF00FF'

    def __init__(self, root):
        self.root = root
        self.mode = 'off'
        self.overlay = None
        self.canvas = None
        self._job = None
        self._generation = 0
        self._ripples = []
        self._images = {}
        self._image_refs = []
        self._was_down = False
        self._last_click_at = 0.0
        root.bind_all('<ButtonPress-1>', self._click, add='+')
        root.bind('<Destroy>', self._root_destroy, add='+')

    def _root_destroy(self, event):
        if event.widget is self.root:
            self.close()

    def set_mode(self, mode):
        if mode not in self.MODES: raise ValueError(mode)
        if mode == 'off':
            self.mode = 'off'
            self._destroy()
            return
        self.mode = mode
        if sys.platform != 'win32': return
        if not self._alive(): self._create()
        if self._job is None: self._tick(self._generation)

    def _alive(self):
        try:return self.overlay is not None and self.canvas is not None and bool(self.canvas.winfo_exists())
        except (tk.TclError,RuntimeError):return False

    def _destroy(self):
        self._generation += 1
        if self._job is not None:
            try:self.root.after_cancel(self._job)
            except (tk.TclError,RuntimeError):pass
        self._job = None
        old = self.overlay
        self.overlay = self.canvas = None
        # Keep pending click glows across overlay reconstruction/navigation.
        self._images.clear()
        self._image_refs.clear()
        if old is not None:
            try:old.destroy()
            except (tk.TclError,RuntimeError):pass

    def _create(self):
        self._destroy()
        win = tk.Toplevel(self.root)
        win.withdraw()
        win.overrideredirect(True)
        win.configure(bg=self.KEY)
        win.attributes('-topmost',True)
        try:win.wm_attributes('-transparentcolor',self.KEY)
        except tk.TclError:pass
        canvas = tk.Canvas(win,width=self.SIZE,height=self.SIZE,bg=self.KEY,bd=0,highlightthickness=0)
        canvas.pack()
        win.geometry(f'{self.SIZE}x{self.SIZE}+0+0')
        win.update_idletasks()
        try:
            import ctypes
            u=ctypes.windll.user32
            hwnd=u.GetParent(win.winfo_id()) or win.winfo_id()
            u.SetWindowLongW(hwnd,-20,u.GetWindowLongW(hwnd,-20)|0x80000|0x20|0x08000000)
        except Exception:pass
        self.overlay,self.canvas=win,canvas
        self._last_position=None
        win.deiconify()

    @staticmethod
    def _gradient(color, size, radius, intensity):
        """Warm soft radial glow with a bright central highlight, chroma-key transparency.

        Tk color-key windows do not support per-pixel alpha. Ordered 8x8 alpha
        coverage is used instead of outlined circles; the soft halo is cached.
        """
        from PIL import Image
        image=Image.new('RGB',(size,size),(255,0,255))
        pixels=image.load()
        r,g,b=color
        center=(size-1)/2
        bayer=((0,48,12,60,3,51,15,63),(32,16,44,28,35,19,47,31),
               (8,56,4,52,11,59,7,55),(40,24,36,20,43,27,39,23),
               (2,50,14,62,1,49,13,61),(34,18,46,30,33,17,45,29),
               (10,58,6,54,9,57,5,53),(42,26,38,22,41,25,37,21))
        for y in range(size):
            dy=y-center
            for x in range(size):
                dx=x-center
                d=math.hypot(dx,dy)/max(radius,1)
                if d>=1:continue
                # Gaussian falloff without visible ring contours.
                alpha=intensity*math.exp(-5.2*d*d)*(1-d*d)**1.1
                if alpha*64>bayer[y&7][x&7]:
                    # Cream/white hot center, amber midtones, brown-gold outer halo.
                    hot=max(0.,1.-d*7.)
                    pixels[x,y]=(min(255,int(r+(255-r)*hot)),
                                 min(255,int(g+(247-g)*hot)),
                                 min(255,int(b+(218-b)*hot)))
        return image

    def _sprite(self, color, radius, intensity):
        key=(color,round(radius/3)*3,round(intensity*12)/12)
        if key not in self._images:
            from PIL import ImageTk
            self._images[key]=ImageTk.PhotoImage(self._gradient(color,self.SIZE,key[1],key[2]),master=self.canvas)
            if len(self._images)>220:self._images.clear()
        return self._images[key]

    def _click(self,event):
        if self.mode=='off':return
        self._record_click(event.x_root,event.y_root)

    def _record_click(self,x,y):
        now=time.monotonic()
        if now-self._last_click_at < .055:return
        self._last_click_at=now
        self._ripples.append((now,x,y))
        self._ripples=self._ripples[-6:]

    def _poll_windows_click(self):
        """Capture clicks even when the Tk widget that received them is replaced."""
        if sys.platform!='win32':return
        try:
            import ctypes
            down=bool(ctypes.windll.user32.GetAsyncKeyState(0x01)&0x8000)
            if down and not self._was_down:
                self._record_click(self.root.winfo_pointerx(),self.root.winfo_pointery())
            self._was_down=down
        except (OSError,AttributeError,tk.TclError):pass

    def _tick(self,generation):
        if generation!=self._generation or self.mode=='off':return
        self._job=None
        try:
            if not self._alive():
                self._create()
                generation=self._generation
            x,y=self.root.winfo_pointerx(),self.root.winfo_pointery()
            self._poll_windows_click()
            now=time.monotonic()
            live=[r for r in self._ripples if now-r[0]<.95]
            self._ripples=live
            # Keep overlay centered on cursor, even after switching screens/pages.
            self.overlay.geometry(f'{self.SIZE}x{self.SIZE}+{x-self.CENTER}+{y-self.CENTER}')
            self.canvas.delete('all')
            self._image_refs=[]
            if self.mode=='laser':
                pulse=.88+.12*math.sin(now*5)
                sprite=self._sprite((255,36,45),58,pulse*.90)
                self.canvas.create_image(self.CENTER,self.CENTER,image=sprite)
                self._image_refs.append(sprite)
                sprite=self._sprite((255,92,95),12,.98)
                self.canvas.create_image(self.CENTER,self.CENTER,image=sprite)
                self._image_refs.append(sprite)
            for started,cx,cy in live:
                age=(now-started)/.95
                ease=1-(1-age)**2
                radius=57+18*ease
                opacity=max(0,1-age)**1.4*.96
                color=(247,159,43) if self.mode=='click' else (255,64,75)
                sprite=self._sprite(color,radius,opacity)
                # Draw relative to current cursor, preserving click origin as cursor moves.
                ox=self.CENTER+cx-x;oy=self.CENTER+cy-y
                if -self.SIZE<ox<self.SIZE*2 and -self.SIZE<oy<self.SIZE*2:
                    self.canvas.create_image(ox,oy,image=sprite)
                    self._image_refs.append(sprite)
            self._job=self.root.after(16 if self.mode=='laser' or live else 32,
                                      lambda g=generation:self._tick(g))
        except (tk.TclError,RuntimeError):
            self._job=None

    def close(self):
        self.mode='off'
        self._destroy()
