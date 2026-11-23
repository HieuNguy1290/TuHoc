"""Read-only, full-question review for the five additional Pygame formats."""
import re
from pathlib import Path
from tuhoc.exercises.new_exercise_runtime import expected, gaps


def draw(screen, question, answer, y=205, height=325, scroll=0, area=None):
    import pygame
    from tuhoc.exercises.pygame_window_utils import vietnamese_font
    normal = vietnamese_font(pygame, 21)
    small = vietnamese_font(pygame, 16)
    ink, green, red = (35,52,78), (26,135,88), (186,55,70)
    area = area or pygame.Rect(54,y,852,height)
    scale=area.width/852
    left=area.left+24
    right=area.right-24
    pygame.draw.rect(screen, 'white', area, border_radius=12)
    old = screen.get_clip()
    screen.set_clip(area.inflate(-15,-10))
    top = y+15-scroll
    def write(value,x,yy,font=normal,color=ink):
        screen.blit(font.render(str(value),True,color),(int(x),int(yy)))
    def image(path,rect):
        try:
            if not path or not Path(str(path)).is_file():return False
            im=pygame.image.load(str(path))
            ratio=min(rect.width/im.get_width(),rect.height/im.get_height())
            im=pygame.transform.smoothscale(im,(max(1,int(im.get_width()*ratio)),max(1,int(im.get_height()*ratio))))
            screen.blit(im,im.get_rect(center=rect.center))
            return True
        except (OSError,ValueError,pygame.error):return False
    def chip(value,x,yy,width=None):
        width=max(65,normal.size(str(value))[0]+20) if width is None else width
        rect=pygame.Rect(x,yy-3,width,34)
        pygame.draw.rect(screen,(219,244,229),rect,border_radius=6)
        pygame.draw.rect(screen,green,rect,2,border_radius=6)
        write(value,x+9,yy+2,normal,green)
        return width
    def wrap_words(source,x,yy,limit=right):
        for token in re.findall(r'\S+\s*|\s+',source):
            w=normal.size(token)[0]
            if x+w>limit and x>left:x=left;yy+=42
            write(token,x,yy);x+=w
        return x,yy
    kind=question.get('type')
    if kind=='image_multi_choice':
        opts=question.get('image_options') or [{'image':p} for p in question.get('options',[])]
        right=str(expected(question))
        for i,opt in enumerate(opts):
            ref=str(opt.get('image','') if isinstance(opt,dict) else opt)
            x=left+(i%4)*max(75,(area.width-50)//4); yy=top+(i//4)*126
            r=pygame.Rect(x,yy,max(65,(area.width-60)//4),112)
            pygame.draw.rect(screen,(219,244,229) if ref==right else (239,244,249),r,border_radius=9)
            pygame.draw.rect(screen,green if ref==right else (199,213,227),r,2,border_radius=9)
            path=(question.get('_choice_images') or {}).get(ref,ref)
            if not image(path,pygame.Rect(x+31,yy+7,120,80)):write('Không có ảnh',x+23,yy+38,small)
            write(chr(65+i)+('  (Đúng)' if ref==right else ''),x+9,yy+89,small,green if ref==right else ink)
    elif kind=='picture_missing_letters':
        path=question.get('_pygame_image') or question.get('image','')
        if not image(path,pygame.Rect(left+min(240,area.width//3),top,240,135)):write('Hình ảnh câu hỏi',left+min(260,area.width//3),top+55,small)
        word=str(expected(question));hidden=set(question.get('hidden_indices',[]))
        xx=left;yy=top+146
        for i,c in enumerate(word):
            if xx+39>right:xx=left;yy+=46
            rect=pygame.Rect(xx,yy,34,37)
            pygame.draw.rect(screen,(219,244,229) if i in hidden else (235,240,245),rect,border_radius=5)
            pygame.draw.rect(screen,green if i in hidden else (195,210,225),rect,2 if i in hidden else 1,border_radius=5)
            write(c,xx+8,yy+6,normal,green if i in hidden else ink);xx+=40
        write('Học viên nhập: '+str(answer or 'Chưa trả lời'),left,yy+46,small,ink)
    else:
        # Use the same token boundaries as the exercise runner, preserving original spaces/punctuation.
        slot=0;yy=top
        parts=gaps(question)
        for j,(source,indices) in enumerate(parts):
            x=left
            if kind=='conversation_gaps':
                dialogue=question.get('dialogue') or []
                speaker=str(dialogue[j].get('speaker','')) if j<len(dialogue) else ''
                prefix=speaker+': '
                write(prefix,x,yy,normal,(33,104,176));x+=normal.size(prefix)[0]
            hidden=set(indices);last=0
            for i,m in enumerate(re.finditer(r'\S+',source)):
                if i not in hidden:continue
                x,yy=wrap_words(source[last:m.start()],x,yy)
                token=m.group()
                w=max(68,normal.size(token)[0]+20)
                if x+w>right:x=left;yy+=42
                x+=chip(token,x,yy,w)+5
                slot+=1;last=m.end()
            x,yy=wrap_words(source[last:],x,yy)
            yy+=49 if kind=='conversation_gaps' else 42
        write('Đáp án đúng đã điền vào tất cả '+str(slot)+' ô trống.',left,yy+2,small,green)
        yy+=29
        if isinstance(answer,(list,tuple)):
            user=' | '.join(str(v) for v in answer)
        else:user=str(answer or 'Chưa trả lời')
        # The caller currently stores the user response as a pipe-separated string.
        write('Bài làm: '+user[:100],left,yy,small,ink)
    screen.set_clip(old)
