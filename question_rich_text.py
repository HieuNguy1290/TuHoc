"""Small, display-only Markdown bold renderer for Pygame question prompts.

Only **paired spans** are styled; answer data and stored strings are untouched.
"""
import re

_BOLD = re.compile(r'\*\*(.+?)\*\*')

def plain(value):
    return _BOLD.sub(lambda m: m.group(1), str(value))

def width(font, value):
    return font.size(plain(value))[0]

def draw(surface, font, value, color, x, y):
    text = str(value)
    cursor = x
    offset = 0
    for match in _BOLD.finditer(text):
        normal = text[offset:match.start()]
        if normal:
            image = font.render(normal, True, color)
            surface.blit(image, (cursor, y))
            cursor += image.get_width()
        previous = font.get_bold()
        try:
            font.set_bold(True)
            image = font.render(match.group(1), True, color)
        finally:
            font.set_bold(previous)
        surface.blit(image, (cursor, y))
        cursor += image.get_width()
        offset = match.end()
    tail = text[offset:]
    if tail:
        image = font.render(tail, True, color)
        surface.blit(image, (cursor, y))
        cursor += image.get_width()
    return cursor - x

def wrap(value, font, max_width):
    """Wrap on spaces while retaining ** delimiters across line breaks."""
    lines = []
    for paragraph in str(value).split('\n'):
        if not paragraph.strip():
            lines.append('')
            continue
        line = ''
        for token in re.findall(r'\*\*.*?\*\*|\S+', paragraph):
            candidate = (line + ' ' + token).strip()
            if line and width(font, candidate) > max_width:
                lines.append(line)
                line = token
            else:
                line = candidate
        lines.append(line)
    return lines or ['']
