"""Sharper drawing for the Pygame exercise windows.

* draw_rect(): drop-in for pygame.draw.rect() whose rounded corners are
  anti-aliased (pygame's own border_radius corners are hard-edged, which looks
  "broken" once the canvas is stretched to a bigger window).
* open_exercise_window(): one place that creates the exercise window with
  per-thread DPI awareness (no Windows bitmap-stretch), linear filtering and
  the same SCALED/maximised behaviour for every exercise type.
"""
from functools import lru_cache

_SS_SMALL, _SS_LARGE = 4, 2


@lru_cache(maxsize=400)
def _shape(w, h, color, radius, width, ss):
    import pygame
    big = pygame.Surface((w * ss, h * ss), pygame.SRCALPHA)
    big.fill((color[0], color[1], color[2], 0))   # keep RGB constant so edges don't get dark fringes
    pygame.draw.rect(big, color, big.get_rect(), width * ss if width else 0, border_radius=radius * ss)
    return pygame.transform.smoothscale(big, (w, h))


def draw_rect(surface, color, rect, width=0, border_radius=0, **kwargs):
    import pygame
    r = pygame.Rect(rect)
    area = r.w * r.h
    if kwargs or border_radius <= 0 or r.w < 4 or r.h < 4 or area > 1_000_000:
        return pygame.draw.rect(surface, color, rect, width, border_radius=border_radius, **kwargs)
    radius = max(1, min(int(border_radius), r.w // 2, r.h // 2))
    rgba = tuple(pygame.Color(color))
    ss = _SS_SMALL if area <= 120_000 else _SS_LARGE
    surface.blit(_shape(r.w, r.h, rgba, radius, int(width), ss), r.topleft)
    return r


def open_exercise_window(size=(960, 640)):
    """Return the shared exercise display, creating it once (SCALED, resizable, maximised)."""
    import os
    import sys
    import pygame
    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_init():
        pygame.display.init()
    screen = pygame.display.get_surface()
    if screen is not None:
        return screen
    if sys.platform == 'win32':
        try:
            import ctypes
            fn = ctypes.windll.user32.SetThreadDpiAwarenessContext
            fn.restype = ctypes.c_void_p
            fn.argtypes = [ctypes.c_void_p]
            fn(ctypes.c_void_p(-4))      # PER_MONITOR_AWARE_V2, this (SDL) thread only; Tk is untouched
        except Exception:
            pass
    os.environ['SDL_RENDER_SCALE_QUALITY'] = 'linear'
    screen = pygame.display.set_mode(tuple(size), pygame.SCALED | pygame.RESIZABLE)
    if sys.platform == 'win32':
        try:
            import ctypes
            info = pygame.display.get_wm_info()
            if info.get('window'):
                ctypes.windll.user32.ShowWindow(info['window'], 3)
        except Exception:
            pass
    return screen


def draw_question_progress(surface, question):
    """One identical counter badge across the Pygame question renderers."""
    import pygame
    try:
        index = int(question.get('_index') or 0)
        total = int(question.get('_total') or 0)
    except (TypeError, ValueError, AttributeError):
        return
    if index < 1 or total < 1:
        return
    font = pygame.font.SysFont('arial', 24, bold=True)
    label = font.render(f'Câu: {min(index, total)}/{total}', True, (255, 255, 255))
    padding_x, padding_y = 14, 8
    w, h = label.get_width() + padding_x * 2, label.get_height() + padding_y * 2
    rect = pygame.Rect(surface.get_width() - w - 42, 44, w, h)
    draw_rect(surface, (33, 52, 79), rect, border_radius=10)
    surface.blit(label, (rect.x + padding_x, rect.y + padding_y))


def present_frame(question, regions=None, *, scroll=0, limit=0, fixed=()):
    """Present the renderer's frame and deliver one RGB snapshot to a studio preview."""
    import pygame

    pygame.display.flip()
    scene = question.get('_studio_scene')
    if scene is not None:
        from question_layout_store import pixel_extras

        values = dict(regions or {})
        for extra in pixel_extras(question.get('layout')):
            box = extra['rect']
            values[extra['id']] = (box['x'], box['y'], box['width'], box['height'])
        boxes = {}
        for key, value in values.items():
            if value is not None:
                document = pygame.Rect(value)
                visible = document.move(0, -scroll) if key not in fixed else document
                boxes[key] = (tuple(document), tuple(visible))
        scene(pygame.display.get_surface(), boxes, scroll, limit)
    capture = question.get('_studio_frame')
    if capture is not None:
        capture()
