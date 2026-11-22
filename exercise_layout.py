"""Display-only flow layout and vertical scrolling for exercise windows."""
from exercise_gfx import draw_rect as aa_rect, draw_question_progress
from exercise_buttons import draw_complete
import pygame


def wrap(text, font, width):
    lines = []
    for paragraph in str(text).split('\n'):
        line = ''
        for word in paragraph.split():
            candidate = (line + ' ' + word).strip()
            if font.size(candidate)[0] <= width:
                line = candidate
                continue
            if line:
                lines.append(line)
            line = ''
            for char in word:
                if line and font.size(line + char)[0] > width:
                    lines.append(line)
                    line = ''
                line += char
        lines.append(line)
    return lines or ['']


def block_top(prompt_bottom, height):
    """Center the whole answer block, keeping individual lines left aligned."""
    top = prompt_bottom + 24
    return top + max(0, (520 - top - height) // 2)


def image_message(question, picture):
    if picture is not None:
        return ''
    if question.get('image') or question.get('_pygame_image'):
        return 'Không tải được ảnh. Hãy kiểm tra lại ảnh của câu hỏi.'
    return ''


def letter_items(letters, hidden, font, *, left=70, width=820, cell=(42, 44), row_height=54):
    """Measure the original letter controls, including wrapped long words."""
    words = []; current = []
    for i, char in enumerate(letters):
        if char == ' ' and i not in hidden:
            if current:
                words.append(current); current = []
            words.append(None)
        else:
            current.append(i)
    if current:
        words.append(current)
    cell_width, cell_height = cell
    right = left + width
    row_height = max(cell_height + 5, row_height)
    x = left; y = 0; items = []
    for word in words:
        if word is None:
            x += 18
            continue
        total = sum(cell_width+5 if i in hidden else font.size(letters[i])[0]+2 for i in word)
        if x+total > right and x > left:
            x = left; y += row_height
        for i in word:
            char_width = cell_width if i in hidden else font.size(letters[i])[0]+2
            if x+char_width > right and x > left:
                x = left; y += row_height
            items.append((i, x, y))
            x += char_width + (5 if i in hidden else 0)
    return items, y+cell_height


class Page:
    """Keep drawing and click coordinates in the same scrollable space."""
    def __init__(self, display):
        self.display = display
        self.scroll = 0
        self.limit = 0
        self.surface = None

    def begin(self, bottom, *, padding=20):
        height = max(640, int(bottom + padding))
        self.limit = height - 640
        self.scroll = max(0, min(self.scroll, self.limit))
        if self.surface is None or self.surface.get_height() != height:
            self.surface = pygame.Surface((960, height))
        return self.surface

    def present(self, question=None):
        if question is not None:
            from extras_render import draw_extras
            draw_extras(self.surface, question)
        self.display.blit(self.surface, (0, 0), (0, self.scroll, 960, 640))
        if self.limit:
            track = pygame.Rect(941, 100, 7, 500)
            aa_rect(self.display, (220, 229, 236), track, border_radius=3)
            h = max(32, int(track.height * 640 / self.surface.get_height()))
            y = track.y + int((track.height-h) * self.scroll / self.limit)
            aa_rect(self.display, (80, 135, 170), (track.x, y, 7, h), border_radius=3)

    def complete(self, question, rect, font, ready):
        mouse = pygame.mouse.get_pos()
        draw_complete(self.display, rect, font, ready, rect.collidepoint(mouse),
                      pygame.mouse.get_pressed()[0])
        draw_question_progress(self.display, question)

    def events(self, scroll_enabled=True):
        # Match the frame that was actually displayed, even if a wheel event
        # and a click are delivered in the same batch.
        visible_scroll = self.scroll
        for event in pygame.event.get():
            if scroll_enabled and event.type == pygame.MOUSEWHEEL:
                self.scroll = max(0, min(self.limit, self.scroll-event.y*65))
                continue
            if scroll_enabled and event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
                self.scroll = max(0, min(self.limit, self.scroll+(-65 if event.button == 4 else 65)))
                continue
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                fields = event.dict.copy()
                fields['viewport_pos'] = event.pos
                fields['pos'] = (event.pos[0], event.pos[1]+visible_scroll)
                event = pygame.event.Event(event.type, fields)
            yield event
