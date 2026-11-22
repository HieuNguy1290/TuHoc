"""Waveform and seekable speed-controlled audio for pygame listening exercises."""
import math
import pygame

BLUE = (40, 102, 232)
PALE = (165, 195, 245)

class WaveformAudio:
    def __init__(self, path):
        import numpy as np
        self.np = np
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        self.source = pygame.mixer.Sound(path)
        self.rate = pygame.mixer.get_init()[0]
        self.samples = pygame.sndarray.array(self.source)
        self.duration = len(self.samples) / self.rate
        self.position = 0.0
        self.speed = 1.0
        self.volume = 0.85
        self.channel = None
        self.started = None
        self.active = False
        self.paused = False
        mono = self.samples.astype(np.float32)
        if mono.ndim == 2: mono = mono.mean(axis=1)
        bins = 500
        edges = np.linspace(0, len(mono), bins + 1, dtype=int)
        peak = np.array([float(np.max(np.abs(mono[edges[i]:max(edges[i]+1,edges[i+1])])) ) if edges[i] < len(mono) else 0 for i in range(bins)])
        peak /= max(float(peak.max()), 1.0)
        self.peaks = peak.tolist()

    def current(self):
        import time
        if self.active and not self.paused and self.started is not None:
            return min(self.duration, self.position + (time.monotonic()-self.started)*self.speed)
        return self.position

    def play(self):
        import time
        if self.active and not self.paused:
            self.pause(); return
        if self.paused and self.channel and self.channel.get_busy():
            self.channel.unpause(); self.paused=False; self.started=time.monotonic(); return
        if self.position >= self.duration: self.position = 0
        self._start()

    def _start(self):
        import time
        np = self.np
        if self.channel: self.channel.stop()
        start = min(len(self.samples),int(self.position*self.rate))
        tail = self.samples[start:]
        if len(tail) < 2:
            self.active=False; return
        if self.speed != 1:
            indices = np.minimum(len(tail)-1, (np.arange(max(1,int(len(tail)/self.speed)))*self.speed).astype(np.int64))
            tail = tail[indices]
        sound = pygame.sndarray.make_sound(np.ascontiguousarray(tail))
        sound.set_volume(self.volume)
        self.channel = sound.play()
        self._sound = sound
        self.started=time.monotonic();self.active=True;self.paused=False

    def pause(self):
        self.position=self.current()
        if self.channel: self.channel.pause()
        self.paused=True

    def seek(self, seconds):
        self.position=max(0,min(self.duration,float(seconds)))
        if self.active and not self.paused: self._start()
        elif self.channel: self.channel.stop()

    def set_speed(self, speed):
        self.position=self.current()
        self.speed=float(speed)
        if self.active and not self.paused: self._start()

    def set_volume(self, volume):
        self.volume=max(0,min(1,float(volume)))
        if hasattr(self,'_sound'): self._sound.set_volume(self.volume)

    def stop(self):
        if self.channel:self.channel.stop()
        self.position=0;self.active=False;self.paused=False;self.started=None

    def update(self):
        if self.active and not self.paused and self.current()>=self.duration:
            self.active=False;self.position=self.duration;self.started=None

    def draw(self, surface, rect, font, mouse=None):
        # Compact player: border is only visible on hover.
        mouse = mouse if mouse is not None else pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse)
        if hover:
            pygame.draw.rect(surface, (172, 193, 230), rect, 1, border_radius=9)
        wave = pygame.Rect(rect.x+12, rect.y+5, rect.width-24, max(12,rect.height-34))
        cy = wave.centery
        pygame.draw.line(surface, (218,228,246), (wave.left,cy), (wave.right,cy))
        progress = self.current()/max(self.duration,0.001)
        for x in range(wave.width):
            idx = min(len(self.peaks)-1, int(x*len(self.peaks)/wave.width))
            h = max(1, int(self.peaks[idx]*(wave.height-5)/2))
            pygame.draw.line(surface, BLUE if x/wave.width<=progress else PALE,
                             (wave.x+x,cy-h),(wave.x+x,cy+h),1)
        px = wave.x+int(progress*wave.width)
        pygame.draw.line(surface, BLUE, (px,wave.y),(px,wave.bottom),2)
        pygame.draw.circle(surface, BLUE, (px,wave.y+2),3)
        control_y = rect.bottom-27
        play = pygame.Rect(rect.x+12,control_y,24,24)
        # Antialiased play icon, drawn at 3x resolution.
        icon = pygame.Surface((96,96),pygame.SRCALPHA)
        pygame.draw.circle(icon, BLUE, (48,48),46)
        if self.active and not self.paused:
            pygame.draw.rect(icon,(255,255,255),(32,27,10,42),border_radius=2)
            pygame.draw.rect(icon,(255,255,255),(54,27,10,42),border_radius=2)
        else:
            pygame.draw.polygon(icon,(255,255,255),[(37,24),(37,72),(70,48)])
        surface.blit(pygame.transform.smoothscale(icon,(24,24)),play.topleft)
        def stamp(t):
            t=int(max(0,t));return f'{t//60:02d}:{t%60:02d}'
        surface.blit(font.render(stamp(self.current())+' / '+stamp(self.duration),True,(37,57,96)),(rect.x+45,control_y+2))
        speed = pygame.Rect(rect.right-78,control_y-1,69,27)
        pygame.draw.rect(surface,(236,240,248),speed,border_radius=9)
        speed_font = pygame.font.SysFont('segoeui',16,bold=True)
        label = speed_font.render(f'{self.speed:g}x',True,(38,65,110))
        surface.blit(label,(speed.centerx-label.get_width()//2-5,speed.centery-label.get_height()//2))
        pygame.draw.polygon(surface,(38,65,110),[(speed.right-16,speed.centery-2),(speed.right-8,speed.centery-2),(speed.right-12,speed.centery+2)])
        volume = pygame.Rect(speed.x-111,control_y+8,86,7)
        pygame.draw.rect(surface,(210,219,235),volume,border_radius=4)
        pygame.draw.rect(surface,BLUE,(volume.x,volume.y,int(volume.width*self.volume),volume.height),border_radius=4)
        pygame.draw.circle(surface,BLUE,(volume.x+int(volume.width*self.volume),volume.centery),5)
        menu = []
        if getattr(self,'speed_menu_open',False):
            options=(0.75,1.0,1.25,1.5,2.0)
            # Overlay upward so the menu does not cover the answer choices.
            for i,value in enumerate(options):
                item=pygame.Rect(speed.x, speed.y-5-(len(options)-i)*29, speed.width,28)
                pygame.draw.rect(surface,(225,237,255) if value==self.speed else (255,255,255),item,border_radius=5)
                pygame.draw.rect(surface,(181,198,228),item,1,border_radius=5)
                txt=speed_font.render(f'{value:g}x',True,(37,66,114))
                surface.blit(txt,(item.centerx-txt.get_width()//2,item.centery-txt.get_height()//2))
                menu.append((item,value))
        self.speed_menu_rects=menu
        return wave,play,speed,volume

    def draw_mini(self, surface, rect, opacity, font):
        """Floating mini player (play/pause + tiny waveform + time).
        Drawn translucent; returns (wave_rect, play_rect) in surface coords."""
        pad = 4
        layer = pygame.Surface((rect.width, rect.height + pad), pygame.SRCALPHA)
        body = pygame.Rect(0, 0, rect.width, rect.height)
        radius = rect.height // 2
        # Soft shadow, then the pill itself.
        pygame.draw.rect(layer, (20, 35, 60, 45), body.move(0, 3), border_radius=radius)
        pygame.draw.rect(layer, (255, 255, 255, 246), body, border_radius=radius)
        pygame.draw.rect(layer, (172, 193, 230, 255), body, 1, border_radius=radius)
        size = rect.height - 14
        play = pygame.Rect(8, 7, size, size)
        icon = pygame.Surface((96, 96), pygame.SRCALPHA)
        pygame.draw.circle(icon, BLUE, (48, 48), 46)
        if self.active and not self.paused:
            pygame.draw.rect(icon, (255, 255, 255), (32, 27, 10, 42), border_radius=2)
            pygame.draw.rect(icon, (255, 255, 255), (54, 27, 10, 42), border_radius=2)
        else:
            pygame.draw.polygon(icon, (255, 255, 255), [(37, 24), (37, 72), (70, 48)])
        layer.blit(pygame.transform.smoothscale(icon, (size, size)), play.topleft)
        label = font.render('%02d:%02d' % divmod(int(max(0, self.current())), 60), True, (37, 57, 96))
        label_x = rect.width - label.get_width() - 16
        wave = pygame.Rect(play.right + 10, 9, label_x - (play.right + 10) - 10, rect.height - 18)
        progress = self.current() / max(self.duration, 0.001)
        cy = wave.centery
        for x in range(0, wave.width, 3):
            idx = min(len(self.peaks) - 1, int(x * len(self.peaks) / max(1, wave.width)))
            h = max(1, int(self.peaks[idx] * wave.height / 2))
            pygame.draw.line(layer, BLUE if x / max(1, wave.width) <= progress else PALE,
                             (wave.x + x, cy - h), (wave.x + x, cy + h), 2)
        px = wave.x + int(progress * wave.width)
        pygame.draw.line(layer, BLUE, (px, wave.y), (px, wave.bottom), 2)
        layer.blit(label, (label_x, body.centery - label.get_height() // 2))
        layer.set_alpha(int(255 * max(0.0, min(1.0, opacity))))
        surface.blit(layer, rect.topleft)
        return wave.move(rect.topleft), play.move(rect.topleft)
