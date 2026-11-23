"""One shared 'Hoàn thành' button so every exercise type looks and sits the same."""

LABEL = 'Hoàn thành'
SIZE = (195, 48)
RIGHT = 888            # right edge, identical in every exercise window
RADIUS = 10
_READY, _HOVER, _PRESSED, _DISABLED = (30, 146, 110), (22, 176, 127), (18, 128, 96), (154, 177, 169)


def complete_rect(y, right=RIGHT):
    import pygame
    return pygame.Rect(right - SIZE[0], y, SIZE[0], SIZE[1])


def draw_complete(surface, rect, font, enabled, hover=False, pressed=False):
    import pygame
    if not enabled:
        color = _DISABLED
    elif pressed and hover:
        color = _PRESSED
    elif hover:
        color = _HOVER
    else:
        color = _READY
    from tuhoc.exercises.exercise_gfx import draw_rect
    draw_rect(surface, color, rect, border_radius=RADIUS)
    label = font.render(LABEL, True, (255, 255, 255))
    surface.blit(label, label.get_rect(center=rect.center))
