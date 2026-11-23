"""Consistent font selection for layout-authored text."""
from functools import lru_cache


_cleanup_registered = False


def _clear_fonts():
    global _cleanup_registered
    _new_font.cache_clear()
    _cleanup_registered = False


def _font(family, size, bold, italic, underline):
    import pygame

    global _cleanup_registered
    if not _cleanup_registered:
        pygame.register_quit(_clear_fonts)
        _cleanup_registered = True
    return _new_font(family, size, bold, italic, underline)


@lru_cache(maxsize=128)
def _new_font(family, size, bold, italic, underline):
    import pygame

    font = pygame.font.SysFont(
        [name for name in (family, 'Segoe UI', 'Noto Sans', 'DejaVu Sans', 'Arial') if name],
        size, bold, italic,
    )
    font.set_underline(underline)
    return font


def resolve_font(geometry, fallback, size):
    if not geometry or not any(key in geometry for key in ('font_family', 'font_size', 'bold', 'italic', 'underline')):
        return fallback
    return _font(geometry.get('font_family', ''), int(geometry.get('font_size', size)),
                 geometry.get('bold', fallback.get_bold()),
                 geometry.get('italic', fallback.get_italic()),
                 geometry.get('underline', fallback.get_underline()))


class TextBlock:
    """Measure and draw a wrapped, optionally clipped question text block."""

    def __init__(self, text, geometry, font, size, default, step, max_lines=None, *, markdown=True):
        from tuhoc.exercises.question_rich_text import wrap

        geometry = geometry or {}
        x, y, width = default
        self.x = geometry.get('x', x)
        self.y = geometry.get('y', y)
        self.width = max(1, geometry.get('width', width))
        self.font = resolve_font(geometry, font, size)
        self.step = step if self.font is font else max(step, self.font.get_linesize())
        self.styled = None
        if geometry.get('runs'):
            self.styled = _styled_lines(text, geometry, self.font, size, self.width, markdown)
            self.lines = [''.join(value for value, _ in line) for line in self.styled]
            self.step = max(self.step, max((face.get_linesize() for line in self.styled
                                            for _, face in line), default=self.step))
        else:
            self.lines = wrap(text, self.font, self.width)
        if max_lines is not None and 'height' not in geometry:
            self.lines = self.lines[:max_lines]
        self.align = geometry.get('align', 'left')
        self.step += geometry.get('line_spacing', 0)
        self.height = geometry.get('height', self.step * len(self.lines))
        self.clip = 'height' in geometry or 'width' in geometry
        self.bottom = self.y + self.height

    def draw(self, surface, color, start=0, count=None, *, align=None):
        from tuhoc.exercises.question_rich_text import draw, width as rich_width
        import pygame

        align = self.align if align is None else align

        def aligned_x(width):
            return self.x + {'left': 0, 'center': (self.width-width)//2,
                             'right': self.width-width}[align]

        clip = surface.get_clip()
        if self.clip:
            surface.set_clip(clip.clip(pygame.Rect(self.x, self.y, self.width, self.height)))
        try:
            end = len(self.lines) if count is None else min(len(self.lines), start + count)
            for i in range(start, end):
                y = self.y + (i-start) * self.step
                if self.styled is None:
                    line = self.lines[i]
                    x = self.x if align == 'left' else aligned_x(rich_width(self.font, line))
                    draw(surface, self.font, line, color, x, y)
                    continue
                width = sum(face.size(text)[0] for text, face in self.styled[i])
                x = aligned_x(width)
                for text, face in self.styled[i]:
                    image = face.render(text, True, color)
                    surface.blit(image, (x, y))
                    x += image.get_width()
        finally:
            if self.clip:
                surface.set_clip(clip)



def _styled_lines(text, geometry, font, size, width, markdown):
    from itertools import groupby
    import re
    from tuhoc.exercises.question_rich_text import _BOLD

    raw = str(text)
    characters = []
    offset = 0
    for match in (_BOLD.finditer(raw) if markdown else []):
        characters.extend((char, False) for char in raw[offset:match.start()])
        characters.extend((char, True) for char in match.group(1))
        offset = match.end()
    characters.extend((char, False) for char in raw[offset:])
    default = {key: geometry[key] for key in ('font_family', 'font_size', 'bold', 'italic', 'underline')
               if key in geometry}
    faces = []
    for index, (_, bold) in enumerate(characters):
        style = {**default, 'bold': True} if bold else default.copy()
        for run in geometry['runs']:
            if run['start'] <= index < run['end']:
                style.update((k, v) for k, v in run.items() if k not in {'start', 'end'})
        faces.append(resolve_font(style, font, size))

    def segments(value, start):
        parts = []
        for face, group in groupby(enumerate(faces[start:start+len(value)]), key=lambda pair: pair[1]):
            indices = [index for index, _ in group]
            parts.append((value[indices[0]:indices[-1]+1], face))
        return parts

    lines = []
    position = 0
    for paragraph in ''.join(char for char, _ in characters).split('\n'):
        line = []; used = 0; spacing = []
        for token in re.finditer(r'\S+|[^\S\n]+', paragraph):
            value = token.group()
            parts = segments(value, position+token.start())
            if value.isspace():
                spacing = parts
                continue
            token_width = sum(face.size(label)[0] for label, face in parts)
            gap = sum(face.size(label)[0] for label, face in spacing) if line else 0
            if line and used + gap + token_width > width:
                lines.append(line)
                line = []; used = 0; gap = 0
            if line:
                line.extend(spacing)
            line.extend(parts)
            used += gap + token_width
            spacing = []
        lines.append(line)
        position += len(paragraph)+1
    return lines
