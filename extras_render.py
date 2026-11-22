"""Draw static, non-interactive v3 text in the question's content coordinates."""
from functools import lru_cache

import pygame

from exercise_layout import wrap
from layout_render import DESKTOP
from question_layout_store import pixel_extras


@lru_cache(maxsize=48)
def _font(size, bold, italic):
    return pygame.font.SysFont(['Segoe UI', 'DejaVu Sans', 'Arial'], size, bold, italic)


@lru_cache(maxsize=128)
def _lines(text, size, bold, italic, width, color):
    font = _font(size, bold, italic)
    return font.get_linesize(), tuple(font.render(line, True, color)
                                      for line in wrap(text, font, width))


def draw_extras(screen, question, screen_size=DESKTOP, *, offset=(0, 0)):
    layout = question.get('layout')
    if not isinstance(layout, dict) or not layout.get('extras'):
        return
    clip = screen.get_clip()
    try:
        for extra in pixel_extras(layout, screen_size):
            g = extra['rect']
            rect = pygame.Rect(g['x'] + offset[0], g['y'] + offset[1], g['width'], g['height'])
            visible = rect.clip(clip)
            if not visible:
                continue
            screen.set_clip(visible)
            if extra['bg']:
                screen.fill(extra['bg'], rect)
            step, lines = _lines(extra['text'].replace('\0', ''), extra['font_size'], extra['bold'],
                                 extra['italic'], rect.width, extra['color'])
            for i, line in enumerate(lines):
                y = rect.y + i * step
                if y >= visible.bottom:
                    break
                x = {'left': rect.left, 'center': rect.centerx - line.get_width() // 2,
                     'right': rect.right - line.get_width()}[extra['align']]
                screen.blit(line, (x, y))
    finally:
        screen.set_clip(clip)
