from pygame_session_guard import shutdown as _app_shutdown
"""Optional Pygame reading studio; additive to the existing Tk teaching toolbar."""
import hashlib
import json
import threading
from pygame_session_guard import launch as launch_guarded
from pathlib import Path


def available():
    try:
        import pygame
        from PIL import Image
        return True
    except ImportError:
        return False


def launch(item, data_dir, image_file=None, speak=None):
    """Open a separate reader; the existing Tk teaching toolbar is untouched."""
    if not available():
        return False
    return launch_guarded(_run, (dict(item), Path(data_dir), image_file), "TuHocReadingSDL")


def _run(item, data_dir, image_file):
    import pygame
    from pygame_window_utils import open_maximized, vietnamese_font
    from PIL import Image
    pygame.init()
    pygame.font.init()
    W,H=1040,740
    screen=open_maximized(pygame, 'Tu Hoc - Bai doc tuong tac')
    pygame.display.set_caption('Tu Hoc - Bai doc tuong tac | ESC: Dong')
    clock=pygame.time.Clock()
    bg=(236,245,250); navy=(37,75,105); ink=(228,84,84)
    font=vietnamese_font(pygame, 23)
    titlefont=vietnamese_font(pygame, 30,bold=True)
    small=vietnamese_font(pygame, 18)
    title=str(item.get('title') or 'Bài đọc')
    content=str(item.get('content') or '')
    identifier='|'.join(str(item.get(k,'')) for k in ('theme','level','lesson','title'))+'|'+content
    key=hashlib.sha256(identifier.encode('utf-8')).hexdigest()[:24]
    savefile=data_dir/'reading_annotations'/f'{key}.json'
    try: strokes=json.loads(savefile.read_text(encoding='utf-8')).get('strokes',[])
    except (OSError,ValueError,TypeError): strokes=[]
    redo=[]; current=None; drawing=False; showing=True; color=(228,84,84); thickness=3; scroll=0
    def persist():
        savefile.parent.mkdir(parents=True,exist_ok=True)
        temp=savefile.with_suffix('.tmp')
        temp.write_text(json.dumps({'version':1,'strokes':strokes},ensure_ascii=False),encoding='utf-8')
        temp.replace(savefile)
    def lines_for(text, maxwidth, f):
        result=[]
        for paragraph in text.splitlines():
            words=paragraph.split(); line=''
            for word in words:
                test=(line+' '+word).strip()
                if line and f.size(test)[0]>maxwidth:
                    result.append(line);line=word
                else:line=test
            result.append(line)
        return result
    def make_page():
        width=max(600,screen.get_width()-140)
        lines=lines_for(content,width-90,font)
        image=None; image_height=0
        if image_file:
            try:
                img=Image.open(image_file).convert('RGB');img.thumbnail((width-70,300))
                image=pygame.image.fromstring(img.tobytes(),img.size,'RGB')
                image_height=img.height+25
            except (OSError,ValueError): pass
        page_height=max(650,145+image_height+len(lines)*39+85)
        page=pygame.Surface((width,page_height));page.fill((255,255,255))
        page.blit(titlefont.render(title,True,navy),(40,32))
        y=100
        if image:
            page.blit(image,((width-image.get_width())//2,y));y+=image_height
        for line in lines:
            if line:page.blit(font.render(line,True,(39,57,73)),(42,y))
            y+=39
        return page
    page=make_page()
    def metrics():
        w,h=screen.get_size();return (max(30,(w-page.get_width())//2),112,max(120,h-177))
    def limit_scroll():
        nonlocal scroll
        scroll=max(0,min(scroll,max(0,page.get_height()-metrics()[2])))
    def coords(pos):
        left,top,_=metrics()
        return ((pos[0]-left)/page.get_width(),(pos[1]-top+scroll)/page.get_height())
    def save_stroke():
        nonlocal current
        if current and current['points']:
            strokes.append(current);redo.clear();persist()
        current=None
    from pygame_scroll import ScrollThumb
    scrollbar = ScrollThumb()
    buttons=[]
    running=True
    while running and not _app_shutdown.is_set():
        w,h=screen.get_size();left,top,viewh=metrics();limit_scroll()
        for event in pygame.event.get():
            consumed, offset = scrollbar.event(event)
            if consumed:
                if offset is not None:
                    scroll = offset
                continue
            if event.type==pygame.QUIT:running=False
            elif event.type==pygame.VIDEORESIZE:
                save_stroke();page=make_page();limit_scroll()
            elif event.type==pygame.KEYDOWN:
                if event.key==pygame.K_ESCAPE:running=False
                elif event.key==pygame.K_d:drawing=not drawing
                elif event.key==pygame.K_h:showing=not showing
                elif event.key==pygame.K_z and (event.mod & pygame.KMOD_CTRL) and strokes:
                    redo.append(strokes.pop());persist()
                elif event.key==pygame.K_y and (event.mod & pygame.KMOD_CTRL) and redo:
                    strokes.append(redo.pop());persist()
                elif event.key==pygame.K_UP:scroll-=75
                elif event.key==pygame.K_DOWN:scroll+=75
            elif event.type==pygame.MOUSEWHEEL:scroll-=event.y*65
            elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                hit=next((name for rect,name in buttons if rect.collidepoint(event.pos)),None)
                if hit=='draw':drawing=not drawing
                elif hit=='show':showing=not showing
                elif hit=='undo' and strokes:redo.append(strokes.pop());persist()
                elif hit=='redo' and redo:strokes.append(redo.pop());persist()
                elif hit=='red':color=(228,84,84)
                elif hit=='blue':color=(42,123,198)
                elif hit=='green':color=(36,152,100)
                elif hit=='yellow':color=(218,157,36)
                elif hit=='thin':thickness=3
                elif hit=='thick':thickness=7
                elif hit=='top':scroll=0
                elif drawing and left<=event.pos[0]<left+page.get_width() and top<=event.pos[1]<top+viewh:
                    current={'color':list(color),'width':thickness,'points':[list(coords(event.pos))]}
            elif event.type==pygame.MOUSEMOTION and current and event.buttons[0]:
                current['points'].append(list(coords(event.pos)))
            elif event.type==pygame.MOUSEBUTTONUP and event.button==1:save_stroke()
        limit_scroll()
        screen.fill(bg)
        pygame.draw.rect(screen,navy,(0,0,w,64))
        screen.blit(titlefont.render('BAI DOC TUONG TAC',True,(255,255,255)),(24,13))
        buttons=[];x=22
        controls=[('draw','TAT BUT' if drawing else 'BAT BUT'),('show','AN NET' if showing else 'HIEN NET'),('undo','UNDO'),('redo','REDO'),('red','DO'),('blue','XANH'),('green','LA'),('yellow','VANG'),('thin','3px'),('thick','7px'),('top','DAU BAI')]
        for name,label in controls:
            f=small;bw=f.size(label)[0]+19
            if x+bw>w-10:break
            rect=pygame.Rect(x,72,bw,31);buttons.append((rect,name))
            active=(name=='draw' and drawing) or (name=='show' and not showing)
            pygame.draw.rect(screen,(191,230,249) if active else (255,255,255),rect,border_radius=7)
            screen.blit(f.render(label,True,navy),(x+9,77));x+=bw+7
        clip=pygame.Rect(left,top,page.get_width(),viewh)
        screen.set_clip(clip)
        screen.blit(page,(left,top-scroll))
        if showing:
            for stroke in strokes+([current] if current else []):
                pts=[(int(left+p[0]*page.get_width()),int(top+p[1]*page.get_height()-scroll)) for p in stroke['points']]
                if len(pts)>1:pygame.draw.lines(screen,stroke['color'],False,pts,stroke['width'])
                elif pts:pygame.draw.circle(screen,stroke['color'],pts[0],max(2,stroke['width']//2))
        screen.set_clip(None)
        pygame.draw.rect(screen,bg,(0,h-58,w,58))
        ratio=scroll/max(1,page.get_height()-viewh)
        progress=f'{int(ratio*100)}%  |  {len(strokes)} net ve  |  Cuon chuot de doc  |  D: bat/tat but  |  ESC: dong'
        screen.blit(small.render(progress,True,navy),(22,h-39))
        scrollbar.configure(pygame.Rect(left+page.get_width()+8,top,9,viewh),
                            viewh, scroll, page.get_height()-viewh, minimum=28)
        if scrollbar.track:
            pygame.draw.rect(screen,(211,224,231),scrollbar.track,border_radius=4)
            pygame.draw.rect(screen,(67,135,178),scrollbar.thumb,border_radius=4)
        pygame.display.flip();clock.tick(45)
    save_stroke()
