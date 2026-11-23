"""Viewport scrollbar geometry and left-button thumb dragging."""
import pygame


class ScrollThumb:
    def __init__(self):
        self.track = self.thumb = None
        self.limit = 0
        self.grab = None

    def configure(self, track, viewport_height, offset, limit, *, minimum=24):
        self.limit = max(0, limit)
        if not self.limit or track.height < 2:
            self.track = self.thumb = self.grab = None
            return
        self.track = pygame.Rect(track)
        height = min(track.height - 1, max(minimum, round(track.height * viewport_height / (viewport_height + limit))))
        travel = track.height - height
        offset = max(0, min(limit, offset))
        self.thumb = pygame.Rect(track.x, track.y + round(travel * offset / limit), track.width, height)

    def event(self, event, pos=None):
        """Return (consumed, new_offset) in viewport coordinates."""
        if self.track is None:
            return False, None
        if event.type == pygame.WINDOWFOCUSLOST:
            self.grab = None
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.grab is not None:
            self.grab = None
            return True, None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            x, y = event.pos if pos is None else pos
            if not self.track.inflate(12, 0).collidepoint(x, y):
                return False, None
            if self.thumb.top <= y < self.thumb.bottom:
                self.grab = y - self.thumb.top
                return True, None
            self.grab = self.thumb.height // 2
        elif event.type == pygame.MOUSEMOTION and self.grab is not None:
            if not getattr(event, 'buttons', (True,))[0]:
                self.grab = None
                return False, None
            _, y = event.pos if pos is None else pos
        else:
            return False, None
        travel = self.track.height - self.thumb.height
        target = max(0, min(travel, y - self.track.y - self.grab))
        return True, round(target * self.limit / travel)
