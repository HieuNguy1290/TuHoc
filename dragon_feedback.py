"""Optional dragon-lion feedback animation for the existing SDL exercise window.
No display creation, scoring, or navigation happens in this module.
"""
import math
import random
import time

CLOUD_COLORS = [(255, 223, 113), (149, 211, 255), (255, 172, 202),
                (202, 177, 255), (161, 232, 201), (255, 243, 202)]


def _cloud(surface, pg, x, y, radius, color):
    r = max(5, int(radius))
    for dx, dy, scale in [(-.7, .08, .65), (-.34, -.28, .85), (.15, -.34, 1),
                          (.65, -.06, .7), (0, .18, 1.05)]:
        pg.draw.circle(surface, color, (int(x + dx*r), int(y + dy*r)), max(3,int(r*scale)))


def _dragon(surface, pg, x, y, scale, phase, correct):
    """Small golden Asian dragon / lion hybrid, drawn without external assets."""
    s = scale
    def point(dx, dy): return (int(x+dx*s), int(y+dy*s))
    def ellipse(color, dx, dy, w, h):
        pg.draw.ellipse(surface, color, (int(x+dx*s),int(y+dy*s),int(w*s),int(h*s)))
    gold=(255,196,55); light=(255,230,129); orange=(225,109,38); brown=(143,77,31)
    # Fluffy mane, tiny tail, four stubby paws.
    pg.draw.line(surface, orange, point(39,28), point(64,10), max(3,int(10*s)))
    pg.draw.circle(surface, orange, point(65,9), max(4,int(9*s)))
    ellipse(orange,-38,-34,81,84)
    for angle in range(0,360,45):
        rad=math.radians(angle)
        pg.draw.circle(surface, orange, point(math.cos(rad)*36, math.sin(rad)*35-1), max(4,int(12*s)))
    ellipse(gold,-40,-34,79,77)
    ellipse(light,-23,8,48,30)
    ellipse(gold,-37,32,25,16); ellipse(gold,12,32,25,16)
    # Horns, lion ears and whiskers.
    pg.draw.polygon(surface,brown,[point(-24,-25),point(-23,-54),point(-8,-37)])
    pg.draw.polygon(surface,brown,[point(15,-37),point(26,-54),point(30,-21)])
    ellipse(orange,-45,-22,22,26); ellipse(orange,23,-22,22,26)
    ellipse(light,-30,-29,61,60)
    ellipse((255,152,119),-31,8,16,11); ellipse((255,152,119),16,8,16,11)
    if correct:
        pg.draw.arc(surface,brown,(int(x-23*s),int(y-9*s),int(17*s),int(14*s)),0,math.pi,max(2,int(2*s)))
        pg.draw.arc(surface,brown,(int(x+6*s),int(y-9*s),int(17*s),int(14*s)),0,math.pi,max(2,int(2*s)))
    else:
        pg.draw.circle(surface,brown,point(-14,-2),max(2,int(3*s)))
        pg.draw.circle(surface,brown,point(14,-2),max(2,int(3*s)))
    pg.draw.circle(surface,brown,point(0,8),max(2,int(4*s)))
    pg.draw.arc(surface,brown,(int(x-10*s),int(y+7*s),int(20*s),int(14*s)),math.pi,2*math.pi,max(2,int(2*s)))
    for side in (-1,1):
        pg.draw.line(surface,brown,point(side*14,12),point(side*32,9),max(1,int(s)))
    return point(33,10)


def play(correct, duration=1.55):
    """Animate over the final rendered frame; never block with time.sleep().
    Called only from the SDL worker thread, before next question is launched.
    Returns False when the user closes the window.
    """
    import pygame as pg
    screen=pg.display.get_surface()
    if screen is None: return True
    base=screen.copy()
    w,h=screen.get_size()
    rng=random.Random()
    scale=max(.65,min(1.3,min(w/960,h/640)))
    origin=(int(w*.15),int(h*.78))
    clouds=[]; stars=[]
    for _ in range(rng.randint(2,5) if correct else 1):
        clouds.append((rng.uniform(.26,.77)*w,rng.uniform(.65,.85)*h,
                       rng.uniform(24,64)*scale,rng.choice(CLOUD_COLORS),
                       rng.uniform(-40,45),rng.uniform(-25,-5),rng.uniform(1,2.4)))
    if correct:
        for _ in range(rng.randint(9,20)):
            stars.append((rng.uniform(.24,.85)*w,rng.uniform(.66,.87)*h,
                          rng.uniform(3,8)*scale,rng.uniform(28,95)*scale,
                          rng.uniform(0,6.28)))
    font=pg.font.SysFont('segoeui,arial',max(19,int(25*scale)),bold=True)
    subfont=pg.font.SysFont('segoeui,arial',max(13,int(17*scale)))
    clock=pg.time.Clock(); start=time.monotonic()
    while time.monotonic()-start<duration:
        for event in pg.event.get():
            if event.type==pg.QUIT: return False
            if event.type==pg.KEYDOWN and event.key==pg.K_ESCAPE:return False
        t=time.monotonic()-start
        screen.blit(base,(0,0))
        # Translucent lower overlay; leave question content readable.
        overlay=pg.Surface((w,int(160*scale)),pg.SRCALPHA)
        overlay.fill((255,255,255,220))
        screen.blit(overlay,(0,h-overlay.get_height()))
        bounce=math.sin(min(t/.5,1)*math.pi)*12 if correct else math.sin(t*18)*2
        mouth=_dragon(screen,pg,origin[0],int(origin[1]-bounce),scale, t, correct)
        for cx,cy,r,color,vx,vy,speed in clouds:
            progress=max(0,min(1,(t-.15)*speed))
            _cloud(screen,pg,cx+vx*progress,cy+vy*progress,r*(.6+.4*progress),color)
        for sx,sy,r,speed,angle in stars:
            if t<.35:continue
            yy=sy+(t-.35)*speed
            if yy>h-5:continue
            pg.draw.circle(screen,(255,198,39),(int(sx+math.sin(t*3+angle)*13),int(yy)),max(2,int(r)))
            pg.draw.line(screen,(255,241,147),(int(sx-r),int(yy)),(int(sx+r),int(yy)),2)
        heading='Chính xác!' if correct else 'Chưa đúng!'
        detail='Rồng Lân Ú phun mây sao!' if correct else 'Rồng Ú cổ vũ bạn thử lại nhé!'
        screen.blit(font.render(heading,True,(30,129,74) if correct else (196,78,57)),
                    (int(w*.26),h-int(105*scale)))
        screen.blit(subfont.render(detail,True,(52,67,83)),(int(w*.26),h-int(65*scale)))
        pg.display.flip()
        clock.tick(40)
    return True
