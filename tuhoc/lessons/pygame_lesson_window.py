from tuhoc.exercises.pygame_session_guard import shutdown as _app_shutdown
"""Fullscreen annotation companion for the existing Tkinter lesson layout."""
from tuhoc.exercises.pygame_session_guard import launch as launch_guarded


def available():
    try:
        import pygame
        return True
    except ImportError:
        return False


def launch(title, lesson, blocks=(), data_dir=None, settings=None):
    if not available():
        return False
    args = (str(title), dict(lesson), list(blocks), data_dir, dict(settings or {}))
    return launch_guarded(_run, args, 'TuHocExpandedLesson')


def _run(title, lesson, blocks, data_dir, settings):
    import pygame
    import math
    from pathlib import Path
    from tuhoc.exercises.pygame_media_support import resolve_media, load_image
    from tuhoc.exercises.pygame_window_utils import vietnamese_font
    pygame.init()
    pygame.key.start_text_input()
    info = pygame.display.Info()
    screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
    pygame.display.set_caption('Lesson Studio - ESC: Quay lai')
    clock = pygame.time.Clock()
    # Opening transition: scale the composed frame from the center to fullscreen.
    opening_started = pygame.time.get_ticks()
    opening_duration_ms = 360
    zoom, scroll, tool, dark = 1.0, 0.0, 'select', False
    annotations, redo, drawing = [], [], None
    toolbar_visible = True
    toolbar_motion = 1.0
    toolbar_target = 1.0
    toolbar_last_tick = pygame.time.get_ticks()
    closing_started = None
    closing_duration_ms = 300
    color_palette_open = False
    pen_color = (235,78,136)
    rect_color = (235,78,136)
    palette_colors = [(235,78,136),(255,211,35),(65,155,255),(65,205,145),(175,105,245),(255,255,255),(20,20,20)]
    palette_buttons = []
    # Visual-only selection animation; does not alter tool behavior.
    selected_tool_at = pygame.time.get_ticks()
    selected_color_at = selected_tool_at
    dragging_scroll = False
    items = sorted(blocks, key=lambda b: int(b.get('order') or 0))
    if not items:
        items = [dict(lesson)]
    # A single-block lesson may keep its reading in the lesson row itself.
    # Never silently render an empty block when the lesson has real content.
    if len(items) == 1 and not str(items[0].get('content') or '').strip():
        fallback = lesson.get('content') or lesson.get('instructions') or ''
        if str(fallback).strip():
            items[0] = {**items[0], 'content': fallback}
    image_cache = {}
    text_hits = []
    selection_start = None
    selection_end = None
    selecting = False
    selection_committed = False
    selection_menu = []
    text_highlights = []  # Persisted character selections, in document coordinates.
    def selected_text():
        if selection_start is None or selection_end is None:
            return ''
        a, b = sorted((selection_start, selection_end))
        return '\n'.join(text_hits[i][0][a[1] if i == a[0] else 0:b[1] if i == b[0] else None]
                         for i in range(a[0], min(b[0] + 1, len(text_hits)))).strip()
    def copy_selection():
        value = selected_text()
        if not value:
            return
        try:
            import pygame.scrap
            pygame.scrap.init()
            pygame.scrap.put(pygame.SCRAP_TEXT, (value + '\0').encode('utf-8'))
        except (pygame.error, ImportError, OSError):
            pass
    def highlight_selected_text():
        """Apply a real text highlight, without switching drawing tools."""
        nonlocal selection_start, selection_end, selection_committed
        if selection_start is None or selection_end is None or not selected_text():
            return
        a, b = sorted((selection_start, selection_end))
        for index in range(a[0], min(b[0] + 1, len(text_hits))):
            value, font, x, doc_y, line_h = text_hits[index]
            left = a[1] if index == a[0] else 0
            right = b[1] if index == b[0] else len(value)
            if right <= left:
                continue
            start_x = x + font.size(value[:left])[0]
            end_x = x + font.size(value[:right])[0]
            text_highlights.append((start_x, doc_y, max(1, end_x - start_x), line_h))
        selection_start = selection_end = None
        selection_committed = False
        selection_menu.clear()

    def image(ref, maxsize):
        if not ref:
            return None
        key = (str(ref), tuple(maxsize))
        if key not in image_cache:
            try:
                # The Tkinter lesson passes an already-resolved absolute image
                # path. resolve_media() intentionally rejects absolute paths,
                # so use that trusted path directly when it exists.
                reference = Path(str(ref)).expanduser()
                if reference.is_absolute() and reference.is_file():
                    path = reference
                else:
                    path = resolve_media(data_dir, str(ref))
                    # Lesson editor stores pictures in content_library/media.
                    if path is None and data_dir:
                        root = Path(data_dir).resolve()
                        for candidate in (root / 'content_library' / 'media' / reference,
                                          root / 'content_library' / 'media' / reference.name):
                            candidate = candidate.resolve()
                            if candidate.is_relative_to(root) and candidate.is_file():
                                path = candidate
                                break
                image_cache[key] = load_image(pygame, path, maxsize)
            except (OSError, ValueError, pygame.error):
                image_cache[key] = None
        return image_cache[key]
    def fonts():
        return (vietnamese_font(pygame, max(14, int(settings.get('title_size', 20) * zoom)), bold=True),
                vietnamese_font(pygame, max(13, int(settings.get('content_size', settings.get('text_size', 18)) * zoom))),
                vietnamese_font(pygame, 17))
    def wrap(s, font, width):
        lines = []
        for para in str(s).split('\n'):
            line = ''
            for word in para.split():
                trial = (line + ' ' + word).strip()
                if line and font.size(trial)[0] > width:
                    lines.append(line); line = word
                else:
                    line = trial
            lines.append(line)
        return lines
    def draw_text_center(text, font, color, rect, top):
        lines = wrap(text, font, rect.width - 22)
        line_h = font.get_linesize() + 5
        for j, line in enumerate(lines):
            surf = font.render(line, True, color)
            draw_selectable(line, font, color, rect.centerx - surf.get_width() // 2, top + j * line_h)
        return len(lines) * line_h
    toolbar = [('select','Chon'), ('highlight','Highlight'), ('pen','But'),
               ('eraser','Tay'), ('text','Ghi chu'), ('rect','Khung'),
               ('undo','Undo'), ('redo','Redo'), ('zoomout','-'),
               ('zoomin','+'), ('dark','Sang/Toi'), ('color','Mau'), ('exit','Dong / ESC')]
    buttons = []
    def use_image_wrap(block):
        mode = str(block.get('layout') or 'auto')
        return mode == 'image_wrap_left' or (len(items) == 1 and mode == 'auto')

    def picture_geometry(block, card_width):
        if not block.get('image'):
            return 0, 0, None
        max_w = min(int(settings.get('image_width', 350) * zoom), int(card_width * .40))
        max_h = int(settings.get('image_height', 240) * zoom)
        surf = image(block.get('image'), (max_w, max_h))
        if surf is None:
            return 0, 0, None
        return surf.get_width(), surf.get_height(), surf

    def wrapped_content_lines(block, font, card_width, picture_width, picture_height):
        """Wrap each paragraph using the same pixel geometry as the image draw."""
        pad, gap = 20, 22
        line_h = font.get_linesize() + 5
        narrow_width = max(80, card_width - 2*pad - picture_width - gap)
        wide_width = max(160, card_width - 2*pad)
        # Border is drawn outside the image by 2px; add breathing room.
        reserved_rows = math.ceil((picture_height + 8) / line_h) if picture_height else 0
        rows = []
        for paragraph in str(block.get('content') or '').split('\n'):
            words = paragraph.split()
            if not words:
                rows.append(('', len(rows) >= reserved_rows))
                continue
            line = ''
            for word in words:
                limit = wide_width if len(rows) >= reserved_rows else narrow_width
                candidate = (line + ' ' + word).strip()
                if line and font.size(candidate)[0] > limit:
                    rows.append((line, len(rows) >= reserved_rows))
                    line = word
                else:
                    line = candidate
            if line:
                # Recheck the final row against its actual destination width.
                limit = wide_width if len(rows) >= reserved_rows else narrow_width
                if font.size(line)[0] > limit and ' ' in line:
                    chunks = wrap(line, font, limit)
                    for chunk in chunks:
                        rows.append((chunk, len(rows) >= reserved_rows))
                else:
                    rows.append((line, len(rows) >= reserved_rows))
        return rows

    def draw_justified(text, font, color, x, y, width, is_last=False):
        words = str(text).split(' ')
        # Never stretch sparse lines or short paragraph endings into huge gaps.
        # Preserve natural word spacing for the selection hit map.
        natural_width = font.size(text)[0]
        normal_space = max(1, font.size(' ')[0])
        gap_width = (width - sum(font.size(word)[0] for word in words)) / max(1, len(words)-1)
        if (is_last or len(words) < 4 or natural_width >= width
                or natural_width < width * 0.84 or gap_width > normal_space * 2.0):
            draw_selectable(text, font, color, x, y)
            return
        extra = (width - sum(font.size(word)[0] for word in words)) / (len(words) - 1)
        cursor = float(x)
        # Record each word with its actual coordinates so drag-selection still works.
        for index, word in enumerate(words):
            draw_selectable(word, font, color, round(cursor), y)
            cursor += font.size(word)[0] + extra

    def draw_selectable(text, font, color, x, y):
        """Record per-character positions in document coordinates for selection."""
        text = str(text)
        glyph = font.render(text, True, color)
        doc_y = y + scroll
        text_hits.append((text, font, x, doc_y, font.get_linesize()))
        # Draw saved highlight beneath glyphs, as in the Reading viewer.
        # Document coordinates keep the highlight aligned while scrolling.
        for hx, hy, hw, hh in text_highlights:
            if abs(hy - doc_y) <= 2 and hx < x + glyph.get_width() and hx + hw > x:
                left = max(hx, x)
                right = min(hx + hw, x + glyph.get_width())
                if right > left:
                    pygame.draw.rect(screen, (255, 229, 133),
                                     pygame.Rect(int(left), int(y), int(right-left), int(hh)))
        if selection_start is not None and selection_end is not None:
            a, b = sorted((selection_start, selection_end))
            row_index = len(text_hits) - 1
            if a[0] <= row_index <= b[0]:
                left = a[1] if a[0] == row_index else 0
                right = b[1] if b[0] == row_index else len(text)
                if right > left:
                    sx = x + font.size(text[:left])[0]
                    ex = x + font.size(text[:right])[0]
                    overlay = pygame.Surface((max(1, ex-sx), font.get_linesize()), pygame.SRCALPHA)
                    overlay.fill((60, 145, 245, 95))
                    screen.blit(overlay, (sx, y))
        screen.blit(glyph, (x, y))

    def hit_text(pos):
        x, y = pos[0], pos[1] + scroll
        nearest = None
        distance = float('inf')
        for i, (text, font, tx, ty, line_h) in enumerate(text_hits):
            # Accept dragging slightly above/below the glyph to select across lines.
            vertical_distance = max(0, ty-y, y-(ty+line_h))
            if vertical_distance <= max(12, line_h):
                for k in range(len(text)+1):
                    horizontal_distance = abs(x - (tx + font.size(text[:k])[0]))
                    delta = vertical_distance * 5 + horizontal_distance
                    if delta < distance:
                        nearest, distance = (i, k), delta
        return nearest

    def layout(w, h, heading, body):
        margin = max(24, int(w * .035)); content_w = w - margin * 2
        y = int(80 + 68 * toolbar_motion)
        result = []
        title_lines = wrap(lesson.get('title') or title, heading, content_w - 40)
        instruction_lines = wrap(lesson.get('instructions') or '', body, content_w - 40) if lesson.get('instructions') else []
        header_h = max(118, 23 + len(title_lines)*(heading.get_linesize()+5) + (12 + len(instruction_lines)*(body.get_linesize()+5) if instruction_lines else 0) + 20)
        result.append(('banner', pygame.Rect(margin, y, content_w, header_h), None))
        y += header_h + 22
        for block in items:
            pic_w, pic_h, _ = picture_geometry(block, content_w)
            if use_image_wrap(block):
                has_image = bool(pic_w and pic_h)
                effective_w = pic_w if has_image else 0
                effective_h = pic_h if has_image else 0
                title_lines_block = wrap(block.get('title') or '', heading, max(160, content_w - 80))
                rows = wrapped_content_lines(block, body, content_w, effective_w, effective_h)
                height = max(20 + len(title_lines_block)*(heading.get_linesize()+5) + 13 + effective_h + 32, 20 + len(title_lines_block)*(heading.get_linesize()+5) + 13 + len(rows)*(body.get_linesize()+5) + 24)
            else:
                text_w = content_w - pic_w - 100
                lines = wrap(block.get('content') or '', body, max(160, text_w - 30))
                lines_title = wrap(block.get('title') or '', heading, max(160, text_w - 30))
                height = max(pic_h + 40, (len(lines) * (body.get_linesize()+5) + len(lines_title)*(heading.get_linesize()+5) + 100))
            result.append(('block', pygame.Rect(margin, y, content_w, height), block))
            y += height + 18
        return result, y + 30
    running = True
    while running and not _app_shutdown.is_set():
        tick_now = pygame.time.get_ticks()
        dt = min(0.06, max(0, (tick_now - toolbar_last_tick) / 1000.0))
        toolbar_last_tick = tick_now
        # Smooth, frame-independent slide; keep the existing toolbar controls.
        toolbar_motion += (toolbar_target - toolbar_motion) * min(1.0, dt * 13.0)
        if abs(toolbar_target - toolbar_motion) < 0.003:
            toolbar_motion = toolbar_target
        w,h = screen.get_size()
        heading,body,small = fonts()
        regions, total_height = layout(w,h,heading,body)
        viewport_top = int(64 + 68 * toolbar_motion)
        viewport = pygame.Rect(0, viewport_top, w, h-40-viewport_top)
        max_scroll = max(0, total_height - viewport_top - viewport.height)
        scroll = min(max_scroll, max(0,scroll))
        buttons = [('toggle',pygame.Rect(w-145, 9, 132, 39),'An tools' if toolbar_visible else 'Hien tools')]
        if toolbar_motion > 0.01:
            bx = 15
            for name,label in toolbar:
                bw = max(57, small.size(label)[0]+23)
                if bx+bw>w-8: break
                buttons.append((name, pygame.Rect(bx, int(65 - (1-toolbar_motion)*68), bw, 49),label))
                bx += bw+5
        palette_buttons = []
        if toolbar_visible and color_palette_open and toolbar_motion > 0.98:
            color_button = next((r for name, r, _ in buttons if name == 'color'), None)
            if color_button is not None:
                palette_width = len(palette_colors) * 39 - 8
                palette_x = max(8, min(w - palette_width - 8, color_button.centerx - palette_width // 2))
                for i, color in enumerate(palette_colors):
                    palette_buttons.append((color, pygame.Rect(palette_x + i * 39, 10, 31, 31)))
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: closing_started = closing_started or pygame.time.get_ticks()
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_F11): closing_started = closing_started or pygame.time.get_ticks()
                elif drawing and drawing['tool'] == 'text':
                    if ev.key == pygame.K_BACKSPACE: drawing['text'] = drawing['text'][:-1]
                    elif ev.key == pygame.K_RETURN:
                        annotations.append(drawing); drawing = None
                elif ev.key == pygame.K_c and ev.mod & pygame.KMOD_CTRL:
                    copy_selection()
                elif ev.key == pygame.K_z and ev.mod & pygame.KMOD_CTRL and annotations:
                    redo.append(annotations.pop())
                elif ev.key == pygame.K_y and ev.mod & pygame.KMOD_CTRL and redo:
                    annotations.append(redo.pop())
                elif ev.key in (pygame.K_DOWN,pygame.K_PAGEDOWN): scroll += 80
                elif ev.key in (pygame.K_UP,pygame.K_PAGEUP): scroll -= 80
            elif ev.type == pygame.MOUSEWHEEL:
                if pygame.key.get_mods() & pygame.KMOD_CTRL:
                    zoom = min(2.2,max(.6,round(zoom+ev.y*.1,2)))
                    image_cache.clear(); text_highlights.clear(); selection_start = selection_end = None
                else: scroll -= ev.y*55
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                pos = ev.pos
                if drawing and drawing['tool']=='text' and getattr(ev,'clicks',1)>=2:
                    if drawing.get('text','').strip(): annotations.append(drawing)
                    drawing = None
                    continue
                chosen_color = next((c for c,r in palette_buttons if r.collidepoint(pos)),None)
                if chosen_color is not None:
                    if tool == 'rect': rect_color = chosen_color
                    else: pen_color = chosen_color
                    selected_color_at = pygame.time.get_ticks()
                    color_palette_open = False
                    continue
                menu_hit = next((name for name, rect in selection_menu if rect.collidepoint(pos)), None)
                if menu_hit:
                    if menu_hit == 'vocab':
                        phrase = selected_text().strip()
                        callback = settings.get('_on_add_vocabulary')
                        if phrase and callable(callback):
                            callback(phrase)
                        selection_committed = False
                    elif menu_hit == 'copy': copy_selection()
                    elif menu_hit == 'highlight':
                        highlight_selected_text()
                    elif menu_hit == 'speak':
                        # Speech support uses the system's installed voice when available.
                        try:
                            import subprocess
                            phrase = selected_text()
                            if phrase and len(phrase) < 500:
                                script = 'Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak([Console]::In.ReadToEnd())'
                                __import__('threading').Thread(target=lambda: subprocess.run(['powershell', '-NoProfile', '-Command', script], input=phrase.encode('utf-8'), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30), daemon=True).start()
                        except Exception:
                            pass
                    continue
                hit = next((name for name,rect,_ in buttons if rect.collidepoint(pos)),None)
                if hit:
                    if hit == 'toggle':
                        toolbar_visible = not toolbar_visible
                        toolbar_target = 1.0 if toolbar_visible else 0.0
                        color_palette_open = False
                    elif hit == 'color': color_palette_open = not color_palette_open
                    elif hit == 'exit': closing_started = closing_started or pygame.time.get_ticks()
                    elif hit == 'dark': dark = not dark
                    elif hit == 'zoomin': zoom = min(2.2,zoom+.1); image_cache.clear(); text_highlights.clear()
                    elif hit == 'zoomout': zoom = max(.6,zoom-.1); image_cache.clear(); text_highlights.clear()
                    elif hit == 'undo' and annotations: redo.append(annotations.pop())
                    elif hit == 'redo' and redo: annotations.append(redo.pop())
                    else:
                        if tool != hit: selected_tool_at = pygame.time.get_ticks()
                        tool = hit
                elif viewport.collidepoint(pos):
                    if tool == 'select':
                        selection_committed = False
                        selection_menu.clear()
                        selection_start = hit_text(pos)
                        selection_end = selection_start
                        selecting = selection_start is not None
                        continue
                    p = (pos[0],pos[1]+scroll)
                    if tool == 'eraser':
                        for i in range(len(annotations)-1,-1,-1):
                            a=annotations[i]
                            if any(abs(q[0]-p[0])<19 and abs(q[1]-p[1])<19 for q in a['points']):
                                redo.append(annotations.pop(i));break
                    elif tool in ('pen','highlight','rect'):
                        drawing={'tool':tool,'points':[p],'color':rect_color if tool=='rect' else pen_color};redo.clear()
                    elif tool == 'text':
                        # Non-blocking in-canvas note: editable using keyboard while the popup is open.
                        drawing={'tool':'text','points':[p],'text':''}
            elif ev.type == pygame.TEXTINPUT and drawing and drawing['tool']=='text':
                drawing['text'] += ev.text
            elif ev.type == pygame.MOUSEMOTION and selecting:
                selection_end = hit_text(ev.pos) or selection_end
            elif ev.type == pygame.MOUSEMOTION and drawing and drawing['tool']!='text':
                drawing['points'].append((ev.pos[0],ev.pos[1]+scroll))
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and selecting:
                selection_end = hit_text(ev.pos) or selection_end
                selecting = False
                selection_committed = bool(selection_start is not None and selection_end is not None
                                           and selection_start != selection_end and selected_text())
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and drawing and drawing['tool']!='text':
                if len(drawing['points']) == 1: drawing['points'].append((ev.pos[0],ev.pos[1]+scroll))
                annotations.append(drawing);drawing=None
        scroll = min(max_scroll,max(0,scroll))
        bg = (23,29,43) if dark else (237,241,255)
        paper = (34,41,57) if dark else (255,255,255)
        ink = (235,239,250) if dark else (35,52,94)
        screen.fill(bg)
        pygame.draw.rect(screen,(35,52,94),(0,0,w,viewport_top))
        screen.blit(vietnamese_font(pygame,23,bold=True).render('LESSON STUDIO  |  '+title[:65],True,(255,255,255)),(23,17))
        now = pygame.time.get_ticks()
        pulse = (math.sin(now * 0.006) + 1.0) * 0.5
        for name,rect,label in buttons:
            if name != "toggle" and (rect.bottom <= 64 or rect.top >= viewport_top):
                continue
            active = name == tool
            pygame.draw.rect(screen,(65,106,210) if active else (51,69,108),rect,border_radius=8)
            if active:
                # A subtle breathing glow, with a brighter outline on selection.
                glow = (85 + int(45*pulse), 165 + int(65*pulse), 240 + int(15*pulse))
                pygame.draw.rect(screen,glow,rect.inflate(4,4),2,border_radius=10)
                pygame.draw.rect(screen,(215,239,255),rect,2,border_radius=8)
            lbl=small.render(label,True,(255,255,255))
            screen.blit(lbl,(rect.centerx-lbl.get_width()//2,rect.centery-lbl.get_height()//2))
        selected_color = rect_color if tool == 'rect' else pen_color
        for color,rect in palette_buttons:
            pygame.draw.rect(screen,color,rect,border_radius=5)
            if color == selected_color:
                # The selected swatch has a pulsing outer ring and a dark
                # separator so white/yellow swatches remain distinguishable.
                outer = rect.inflate(8 + int(2*pulse),8 + int(2*pulse))
                pygame.draw.rect(screen,(110+int(80*pulse),185+int(55*pulse),255),outer,2,border_radius=9)
                pygame.draw.rect(screen,(24,35,65),rect.inflate(3,3),2,border_radius=7)
                pygame.draw.rect(screen,(255,255,255),rect,2,border_radius=5)
            else:
                pygame.draw.rect(screen,(175,187,211),rect,1,border_radius=5)
        screen.set_clip(viewport)
        text_hits.clear()
        for kind,rect,block in regions:
            r=rect.move(0,-int(scroll))
            if r.bottom<viewport.top or r.top>viewport.bottom:continue
            pygame.draw.rect(screen,paper,r,border_radius=13)
            if kind=='banner':
                txt=str(lesson.get('title') or title)
                title_h = draw_text_center(txt,heading,ink,r,r.y+23)
                if lesson.get('instructions'):
                    draw_text_center(lesson['instructions'],body,ink,r,r.y+23+title_h+12)
                continue
            if use_image_wrap(block):
                pad = 20
                pic_w, pic_h, surf = picture_geometry(block, r.width)
                has_image = bool(pic_w and pic_h and surf is not None)
                title_text = str(block.get('title') or '')
                title_lines = wrap(title_text, heading, max(160, r.width - 2*pad - 20))
                title_y = r.y + pad
                for line in title_lines:
                    glyph = heading.render(line, True, ink)
                    draw_selectable(line, heading, ink, r.centerx - glyph.get_width()//2, title_y)
                    title_y += heading.get_linesize()+5
                content_y = title_y + 13
                effective_w = pic_w if has_image else 0
                effective_h = pic_h if has_image else 0
                if has_image:
                    picture = pygame.Rect(r.x+pad, content_y, pic_w, pic_h)
                    pygame.draw.rect(screen,(231,235,249) if not dark else (49,57,75),picture.inflate(4,4),2,border_radius=4)
                    if surf:
                        screen.blit(surf, picture.topleft)
                rows = wrapped_content_lines(block, body, r.width, effective_w, effective_h)
                line_h = body.get_linesize()+5
                for j,(line,full_width) in enumerate(rows):
                    x = r.x+pad if full_width or not has_image else r.x+pad+pic_w+22
                    available = r.width-2*pad if full_width or not has_image else r.width-2*pad-pic_w-22
                    last = j == len(rows)-1 or (j+1 < len(rows) and not rows[j+1][0])
                    draw_justified(line, body, ink, x, content_y+j*line_h, available, last)
                continue
            pad=20
            pic_w,pic_h,surf=picture_geometry(block,r.width)
            picture=pygame.Rect(r.x+pad,r.y+pad,pic_w+20 if surf else 0,pic_h+20 if surf else 0)
            if surf:
                pygame.draw.rect(screen,(231,235,249) if not dark else (49,57,75),picture,border_radius=7)
            if surf:
                screen.blit(surf,(picture.centerx-surf.get_width()//2,picture.centery-surf.get_height()//2))
            text_rect=pygame.Rect(picture.right+18,r.y+20,r.right-picture.right-40,r.height-40)
            title_lines=wrap(block.get('title') or '',heading,text_rect.width-20)
            content_lines=wrap(block.get('content') or '',body,text_rect.width-20)
            text_height=len(title_lines)*(heading.get_linesize()+5)+len(content_lines)*(body.get_linesize()+5)+13
            ty=text_rect.centery-text_height//2
            ty+=draw_text_center(block.get('title') or '',heading,ink,text_rect,ty)+13
            draw_text_center(block.get('content') or '',body,ink,text_rect,ty)
        for a in annotations+([drawing] if drawing else []):
            if not a:continue
            pts=[(int(x),int(y-scroll)) for x,y in a['points']]
            if a['tool']=='pen' and len(pts)>1:
                pygame.draw.lines(screen,a.get('color',(235,78,136)),False,pts,3)
            elif a['tool']=='highlight' and len(pts)>1:
                overlay=pygame.Surface((w,h),pygame.SRCALPHA)
                pygame.draw.lines(overlay,(255,211,35,100),False,pts,19)
                screen.blit(overlay,(0,0))
            elif a['tool']=='rect' and len(pts)>1:
                p1,p2=pts[0],pts[-1]
                pygame.draw.rect(screen,a.get('color',(235,78,136)),pygame.Rect(min(p1[0],p2[0]),min(p1[1],p2[1]),abs(p2[0]-p1[0]),abs(p2[1]-p1[1])),3)
            elif a['tool']=='text':
                label=small.render(a.get('text','')+'|' if a is drawing else a.get('text',''),True,(222,70,120))
                screen.blit(label,pts[0])
        screen.set_clip(None)
        selection_menu.clear()
        if tool == 'select' and not selecting and selection_committed and selection_start != selection_end and selected_text():
            # Compact context actions, analogous to Reading's selection toolbar.
            mx, my = pygame.mouse.get_pos()
            if text_hits:
                a, b = sorted((selection_start, selection_end))
                if b[0] < len(text_hits):
                    _, _, sx, sy, _ = text_hits[a[0]]
                    mx, my = min(w-300, max(12, sx)), max(viewport_top+8, int(sy-scroll)-42)
            menu_items = [('vocab','Them tu',86), ('speak','Phat am',84), ('highlight','Highlight',94), ('copy','Sao chep',94)]
            menu_width = sum(item[2] + 3 for item in menu_items)
            menu_x = min(max(8, w-menu_width-8), max(8, mx))
            for name, label, width in menu_items:
                rect = pygame.Rect(menu_x, my, width, 32)
                pygame.draw.rect(screen, (239,247,255), rect, border_radius=3)
                pygame.draw.rect(screen, (105,152,218), rect, 1, border_radius=3)
                screen.blit(small.render(label, True, (29,69,125)), (rect.x+7,rect.y+7))
                selection_menu.append((name,rect))
                menu_x += width+3
        pygame.draw.rect(screen,(35,52,94),(0,h-40,w,40))
        status=f'{int(zoom*100)}%  |  {tool}  |  ESC: Quay lai Tkinter  |  Cuon chuot: Di chuyen  |  Ctrl+Cuon: Zoom'
        screen.blit(small.render(status,True,(255,255,255)),(22,h-31))
        # Closing transition: resize the REAL OS window, revealing Tkinter behind it.
        # A scaled frame inside a fullscreen surface would leave an opaque backdrop.
        if closing_started is not None:
            snapshot = screen.copy()
            origin = settings.get('_opening_origin', (w / 2, h / 2))
            try:
                ox, oy = float(origin[0]), float(origin[1])
            except (TypeError, ValueError, IndexError):
                ox, oy = w / 2, h / 2
            # Leave fullscreen first; only the lesson window shrinks afterward.
            window_surface = pygame.display.set_mode((w, h), pygame.NOFRAME)
            try:
                from pygame._sdl2.video import Window
                os_window = Window.from_display_module()
            except (ImportError, AttributeError, pygame.error):
                os_window = None
            if os_window is not None:
                start = pygame.time.get_ticks()
                while True:
                    for close_event in pygame.event.get():
                        if close_event.type == pygame.QUIT:
                            pass
                    t = min(1.0, (pygame.time.get_ticks() - start) / closing_duration_ms)
                    eased = 1.0 - (1.0 - t) ** 3
                    scale = 1.0 - 0.92 * eased
                    frame_w = max(1, round(w * scale))
                    frame_h = max(1, round(h * scale))
                    cx = w / 2 + (ox - w / 2) * eased
                    cy = h / 2 + (oy - h / 2) * eased
                    os_window.size = (frame_w, frame_h)
                    os_window.position = (round(cx - frame_w / 2), round(cy - frame_h / 2))
                    window_surface = pygame.display.get_surface()
                    if window_surface.get_size() == (frame_w, frame_h):
                        window_surface.blit(pygame.transform.smoothscale(snapshot, (frame_w, frame_h)), (0, 0))
                        pygame.display.flip()
                    if t >= 1.0:
                        break
                    clock.tick(60)
            # If SDL2 native-window access is unavailable, close without a fake
            # fullscreen animation rather than covering Tkinter with a dark layer.
            running = False
            break
        # Visual-only opening animation; the lesson and tools retain their original logic.
        elapsed = pygame.time.get_ticks() - opening_started
        if elapsed < opening_duration_ms:
            if closing_started is None:
                t = max(0.0, min(1.0, elapsed / opening_duration_ms))
                eased = 1.0 - (1.0 - t) ** 3  # ease-out cubic
            else:
                t = max(0.0, min(1.0, (pygame.time.get_ticks() - closing_started) / closing_duration_ms))
                eased = 1.0 - (1.0 - t) ** 3
                eased = 1.0 - eased  # reverse toward the expand icon
            scale = 0.08 + 0.92 * eased
            frame = screen.copy()
            frame_w = max(1, round(w * scale))
            frame_h = max(1, round(h * scale))
            scaled = pygame.transform.smoothscale(frame, (frame_w, frame_h))
            # Animate from the Tkinter expand icon's screen coordinates.
            origin = settings.get('_opening_origin', (w / 2, h / 2))
            try:
                ox, oy = float(origin[0]), float(origin[1])
            except (TypeError, ValueError, IndexError):
                ox, oy = w / 2, h / 2
            cx = ox + (w / 2 - ox) * eased
            cy = oy + (h / 2 - oy) * eased
            screen.fill((12, 18, 33))
            screen.blit(scaled, (round(cx - frame_w / 2), round(cy - frame_h / 2)))
        pygame.display.flip()
        if closing_started is not None and pygame.time.get_ticks() - closing_started >= closing_duration_ms:
            running = False
        clock.tick(60)

    pygame.key.stop_text_input()
