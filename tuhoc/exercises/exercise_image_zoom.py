"""Read-only image lightbox for Pygame exercises; never changes quiz answers."""
from tuhoc.exercises.exercise_gfx import draw_rect as aa_rect
from pathlib import Path


def draw(screen, image_path):
    import pygame
    width, height = screen.get_size()
    shade = pygame.Surface((width, height), pygame.SRCALPHA)
    shade.fill((12, 23, 42, 225))
    screen.blit(shade, (0, 0))
    close_rect = pygame.Rect(width - 72, 19, 48, 43)
    aa_rect(screen, (236, 242, 249), close_rect, border_radius=10)
    font = pygame.font.SysFont('arial', 26, bold=True)
    x = font.render('X', True, (30, 48, 73))
    screen.blit(x, x.get_rect(center=close_rect.center))
    try:
        original = pygame.image.load(str(Path(image_path))).convert_alpha()
        iw, ih = original.get_size()
        ratio = min((width - 90) / max(1, iw), (height - 125) / max(1, ih))
        scaled = pygame.transform.smoothscale(original, (max(1, round(iw * ratio)), max(1, round(ih * ratio))))
        screen.blit(scaled, scaled.get_rect(center=(width // 2, height // 2 + 12)))
    except (OSError, ValueError, pygame.error):
        pass
    return close_rect


def draw_zoom_icon(screen, image_rect):
    """Draw a subtle 50%-opacity zoom button to the RIGHT of an image.

    Keep it level with the image's top edge, not in the question text row.
    Return the actual click target in screen coordinates.
    """
    import pygame
    image_rect = pygame.Rect(image_rect)
    side = 30
    gap = 8
    width, height = screen.get_size()
    x = image_rect.right + gap
    y = image_rect.top
    if x + side > width:
        # No right-side gutter: use the image's upper-right corner instead
        # of placing the button above the image on top of question text.
        x = image_rect.right - side - gap
        y = image_rect.top + gap
    x = max(0, min(x, width - side))
    y = max(0, min(y, height - side))
    rect = pygame.Rect(x, y, side, side)

    # Render the entire button at 50% opacity, including its border and glyph.
    layer = pygame.Surface((side, side), pygame.SRCALPHA)
    local = pygame.Rect(0, 0, side, side)
    aa_rect(layer, (250, 252, 255), local, border_radius=7)
    aa_rect(layer, (71, 105, 145), local, 1, border_radius=7)
    cx, cy = side // 2 - 2, side // 2 - 2
    pygame.draw.circle(layer, (34, 75, 122), (cx, cy), 6, 2)
    pygame.draw.line(layer, (34, 75, 122), (cx + 5, cy + 5), (cx + 10, cy + 10), 2)
    layer.set_alpha(128)
    screen.blit(layer, rect.topleft)
    return rect
