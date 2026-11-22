"""Shared fullscreen/maximized SDL window and Vietnamese Unicode font support."""
import os
import sys
from pathlib import Path


def open_maximized(pygame, title, default_size=(1200, 800)):
    """Use a maximized resizable desktop window; fall back safely on other systems."""
    pygame.display.init()
    pygame.display.set_caption(title)
    if sys.platform == 'win32':
        try:
            import ctypes
            user32 = ctypes.windll.user32
            # DPI awareness is established by main before Tk is created.
            pass
            width, height = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
            screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
            # SDL2 window maximize retains title bar and native window controls.
            try:
                from pygame._sdl2.video import Window
                Window.from_display_module().maximize()
            except (ImportError, AttributeError, pygame.error):
                pass
            return screen
        except (OSError, AttributeError, ValueError):
            pass
    try:
        return pygame.display.set_mode(default_size, pygame.RESIZABLE | pygame.MAXIMIZED)
    except (pygame.error, AttributeError, ValueError):
        info = pygame.display.Info()
        size = (info.current_w or default_size[0], info.current_h or default_size[1])
        return pygame.display.set_mode(size, pygame.RESIZABLE)


def vietnamese_font(pygame, size, bold=False):
    """Select an actual Unicode font file with Vietnamese glyph coverage."""
    pygame.font.init()
    candidates = []
    if sys.platform == 'win32':
        root = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
        candidates += [root / name for name in ('segoeui.ttf', 'arial.ttf', 'tahoma.ttf')]
        if bold:
            candidates = [root / name for name in ('segoeuib.ttf', 'arialbd.ttf', 'tahomabd.ttf')] + candidates
    candidates += [Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
                   Path('/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf')]
    for path in candidates:
        if path.is_file():
            font = pygame.font.Font(str(path), int(size))
            if bold and ('bd.' not in path.name and 'segoeuib' not in path.name):
                font.set_bold(True)
            return font
    for family in ('segoeui', 'tahoma', 'arial', 'notosans', 'dejavusans'):
        path = pygame.font.match_font(family, bold=bold)
        if path:
            return pygame.font.Font(path, int(size))
    return pygame.font.Font(None, int(size))
