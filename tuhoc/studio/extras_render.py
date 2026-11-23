"""Draw static, non-interactive v3 text in the question's content coordinates."""
from functools import lru_cache

import pygame

from tuhoc.studio.layout_typography import TextBlock, _font

from tuhoc.exercises.exercise_layout import wrap
from tuhoc.studio.layout_render import DESKTOP
from tuhoc.studio.question_layout_store import pixel_extras


@lru_cache(maxsize=128)
def _lines(text, family, size, bold, italic, underline, width, color):
    font = _font(family, size, bold, italic, underline)
    return font.get_linesize(), tuple(font.render(line, True, color)
                                      for line in wrap(text, font, width))


def draw_extras(screen, question, screen_size=DESKTOP, *, offset=(0, 0), mobile=None):
    layout = question.get('layout')
    if not isinstance(layout, dict) or not layout.get('extras'):
        return
    clip = screen.get_clip()
    try:
        for extra in pixel_extras(layout, screen_size, mobile=mobile):
            g = extra['rect']
            rect = pygame.Rect(g['x'] + offset[0], g['y'] + offset[1], g['width'], g['height'])
            visible = rect.clip(clip)
            if not visible:
                continue
            screen.set_clip(visible)
            if extra['bg']:
                screen.fill(extra['bg'], rect)
            if extra.get('runs'):
                size = extra['font_size']
                font = _font(extra.get('font_family', ''), size, extra['bold'], extra['italic'], extra.get('underline', False))
                block = TextBlock(extra['text'], {**extra, 'height': rect.height}, font, size,
                                  (rect.x, rect.y, rect.width), font.get_linesize(), markdown=False)
                block.draw(screen, extra['color'], align=extra['align'])
                continue
            step, lines = _lines(extra['text'].replace('\0', ''), extra.get('font_family', ''),
                                 extra['font_size'], extra['bold'], extra['italic'],
                                 extra.get('underline', False), rect.width, extra['color'])
            for i, line in enumerate(lines):
                y = rect.y + i * step
                if y >= visible.bottom:
                    break
                x = {'left': rect.left, 'center': rect.centerx - line.get_width() // 2,
                     'right': rect.right - line.get_width()}[extra['align']]
                screen.blit(line, (x, y))
    finally:
        screen.set_clip(clip)
