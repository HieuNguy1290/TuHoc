from tuhoc.exercises.question_rich_text import draw as draw_rich, wrap as wrap_rich
from tuhoc.exercises.exercise_buttons import draw_complete
from tuhoc.exercises.exercise_gfx import draw_question_progress
from tuhoc.exercises.exercise_gfx import open_exercise_window
"""Independent inline text fields for a single multi-blank exercise."""
import re
import unicodedata
from pathlib import Path

MARKER = re.compile(r'\[\[(\d+)\]\]')


def build_editor(parent, original, import_media, resolve_media=None):
    import tkinter as tk
    from tkinter import filedialog

    def label(value):
        tk.Label(parent, text=value, bg='white', fg='#285D40', anchor='w').pack(fill='x', pady=(9, 3))

    label('Câu có ô trống: dùng [[1]], [[2]], ... tại vị trí cần nhập')
    template = tk.Text(parent, height=4, wrap='word', font=('Segoe UI', 11))
    template.pack(fill='x')
    template.insert('1.0', original.get('blank_text') or 'Nếu đổi chỗ hai chữ số, ta được số mới gồm [[1]] chục và [[2]] đơn vị.')
    label('Đáp án đúng theo thứ tự ô (mỗi dòng một đáp án, từ 1 đến 8 ô)')
    answers = tk.Text(parent, height=5, font=('Segoe UI', 11))
    answers.pack(fill='x')
    initial = original.get('blank_answers') or []
    answers.insert('1.0', '\n'.join(map(str, initial)))
    label('Hình minh họa (không bắt buộc)')
    row = tk.Frame(parent, bg='white'); row.pack(fill='x')
    image = tk.Entry(row, font=('Segoe UI', 11)); image.pack(side='left', fill='x', expand=True)
    image.insert(0, str(original.get('image') or ''))

    def browse():
        file = filedialog.askopenfilename(parent=parent.winfo_toplevel(), filetypes=[('Ảnh', '*.png *.jpg *.jpeg *.gif *.webp')])
        if file:
            image.delete(0, 'end'); image.insert(0, import_media(file))

    tk.Button(row, text='Chọn ảnh', command=browse).pack(side='left', padx=5)

    def resolve_audio(ref):
        try:
            path = resolve_media(ref) if resolve_media and ref else None
            return path if path and Path(path).is_file() else None
        except (OSError, ValueError, TypeError):
            return None

    label('File nghe (không bắt buộc) - học sinh bấm nghe rồi điền vào ô trống')
    arow = tk.Frame(parent, bg='white'); arow.pack(fill='x')
    audio = tk.Entry(arow, font=('Segoe UI', 11)); audio.pack(side='left', fill='x', expand=True)
    audio.insert(0, str(original.get('audio') or ''))
    audio_note = tk.Label(parent, bg='white', anchor='w', font=('Segoe UI', 9))
    audio_note.pack(fill='x')

    def check_audio(*_):
        ref = audio.get().strip()
        ok = bool(ref) and resolve_audio(ref) is not None
        audio_note.config(text='' if not ref else 'Đã tìm thấy tệp.' if ok else 'Không tìm thấy tệp âm thanh.',
                          fg='#285D40' if ok else '#B54747')

    def browse_audio():
        file = filedialog.askopenfilename(parent=parent.winfo_toplevel(), filetypes=[('Âm thanh', '*.mp3 *.wav *.ogg')])
        if file:
            audio.delete(0, 'end'); audio.insert(0, import_media(file)); check_audio()

    def clear_audio():
        audio.delete(0, 'end'); check_audio()

    tk.Button(arow, text='Chọn tệp', command=browse_audio).pack(side='left', padx=5)
    tk.Button(arow, text='Bỏ file nghe', command=clear_audio).pack(side='left')
    audio.bind('<FocusOut>', check_audio, add='+'); check_audio()

    def collect():
        text = template.get('1.0', 'end-1c').strip()
        values = [s.strip() for s in answers.get('1.0', 'end-1c').strip().splitlines()]
        indices = [int(s) for s in MARKER.findall(text)]
        if not 1 <= len(values) <= 8 or any(not s for s in values):
            raise ValueError('Cần từ 1 đến 8 đáp án, mỗi dòng một đáp án không rỗng.')
        if any(len(v) > 32 for v in values):
            raise ValueError('Mỗi đáp án tối đa 32 ký tự (giới hạn nhập khi làm bài).')
        if sorted(indices) != list(range(1, len(values) + 1)):
            raise ValueError('Các ô phải là [[1]], [[2]], ... mỗi ô xuất hiện đúng một lần và khớp số đáp án.')
        ref = image.get().strip()
        if ref and resolve_media:
            path = resolve_media(ref)
            if not path or not Path(path).is_file():
                raise ValueError('Không tìm thấy ảnh minh họa.')
        ref_audio = audio.get().strip()
        if ref_audio and not resolve_audio(ref_audio):
            raise ValueError(f'Không tìm thấy tệp âm thanh: {ref_audio}')
        return {'type': 'multi_fill_blanks', 'blank_text': text, 'blank_answers': values,
                'answer': ' | '.join(values), 'options': [], 'image': ref, 'audio': ref_audio}

    return collect


def correct(question, answer):
    values = question.get('blank_answers') or []
    norm = lambda x: unicodedata.normalize('NFC', str(x)).strip().casefold()
    return (isinstance(answer, (list, tuple)) and len(answer) == len(values) and bool(values)
            and all(norm(a) == norm(b) for a, b in zip(answer, values)))


def run(question):
    import pygame
    from tuhoc.exercises.pygame_exercises import _image, _cached_font
    pygame.init(); pygame.display.init()
    screen = open_exercise_window((960, 640))
    pygame.display.set_caption('Tự Học - Bài tập')
    clock = pygame.time.Clock()
    from tuhoc.exercises.exercise_layout import Page
    from tuhoc.studio.layout_scroll_extent import content_bottom as layout_content_bottom
    page = Page(screen)
    font = _cached_font(None, 22, False)
    small = _cached_font(None, 19, False)
    title = _cached_font(None, 28, True)
    navy = (32, 52, 77)
    from tuhoc.studio.question_layout_runtime import element as layout_element, rectangle
    text_layout = layout_element(question, "question_text")
    image_layout = layout_element(question, "question_image")
    audio_layout = layout_element(question, "audio_player")
    answer_layout = layout_element(question, "answer_area")
    from tuhoc.studio.layout_typography import TextBlock, resolve_font
    prompt_font = resolve_font(text_layout, font, 22)
    small = resolve_font(answer_layout, small, 17)
    template = str(question.get('blank_text') or '')
    expected = question.get('blank_answers') or []
    if not 1 <= len(expected) <= 8:
        return None
    values = [''] * len(expected)
    slot_geometry = [layout_element(question, f'slot_{i}') for i in range(len(values))]
    active = 0
    audio_path = str(question.get('_resolved_audio') or '').strip()
    has_audio = bool(str(question.get('audio') or '').strip())
    audio_err = '' if (audio_path or not has_audio) else 'Chưa tìm thấy file nghe. Kiểm tra trong Quản lý nội dung.'
    wf = None; wf_pending = bool(audio_path); wf_rects = None; wf_drag = None
    picture = None
    authored_rect = authored_frame = None
    if question.get('_pygame_image'):
        try:
            bounds = (340, 140 if has_audio else 175)
            if image_layout:
                from tuhoc.studio.layout_images import pygame_image
                picture, authored_rect, authored_frame = pygame_image(question['_pygame_image'],image_layout,(55,180,*bounds))
            else:
                picture = _image(question['_pygame_image'],bounds)
        except (OSError, ValueError, pygame.error):
            pass

    def lines(text, width):
        result = []; current = ''
        for word in str(text).split():
            candidate = (current + ' ' + word).strip()
            if current and font.size(candidate)[0] > width:
                result.append(current); current = word
            else:
                current = candidate
        if current: result.append(current)
        return result

    # Allow elements positioned below the initial viewport to remain reachable.
    scroll_bottom = layout_content_bottom(question, 640)
    fixed_submit = pygame.Rect(690, 557, 200, 45)
    try:
        while True:
            screen = page.begin(scroll_bottom)
            screen.fill((241, 247, 252))
            pygame.draw.rect(screen, 'white', (25, 25, 910, max(590, screen.get_height() - 50)), border_radius=18)
            y = 100
            if text_layout:
                tx = text_layout.get('x', 55)
                ty = text_layout.get('y', y)
                tw = max(80, text_layout.get('width', 845))
                prompt_block = TextBlock(question.get('prompt') or 'Điền đáp án vào các ô trống.',
                                         text_layout, font, 22, (tx, ty, tw),
                                         prompt_font.get_linesize()+5, 4)
                prompt_block.draw(screen, navy)
                y = max(y + 33 * len(prompt_block.lines), prompt_block.bottom)
            else:
                for line in wrap_rich(question.get('prompt') or 'Điền đáp án vào các ô trống.', font, 845)[:4]:
                    draw_rich(screen, font, line, navy, 55, y); y += 33
            prompt_bottom = y
            if has_audio:       # khung nghe ngay dưới đề, giống dạng nghe
                y += 8
                audio_rect = pygame.Rect(52, y, 856, 88)
                if audio_layout:
                    audio_rect = pygame.Rect(audio_layout.get('x', audio_rect.x),
                                             audio_layout.get('y', audio_rect.y),
                                             max(180, audio_layout.get('width', audio_rect.w)),
                                             max(65, audio_layout.get('height', audio_rect.h)))
                pygame.draw.rect(screen, (246, 250, 254), audio_rect, border_radius=14)
                pygame.draw.rect(screen, (214, 224, 238), audio_rect, 1, border_radius=14)
                if wf is not None:
                    wf.update()
                    wf_rects = wf.draw(screen, pygame.Rect(audio_rect.x + 10, audio_rect.y + 6, audio_rect.w - 20, audio_rect.h - 12), small)
                elif wf_pending:
                    screen.blit(small.render('Đang tải âm thanh...', True, navy), (audio_rect.x + 22, audio_rect.centery - 8))
                if audio_err:
                    screen.blit(small.render(audio_err, True, (200, 60, 60)), (audio_rect.x + 22, audio_rect.centery - 8))
                y = max(y + (0 if audio_layout else audio_rect.h) + 6, audio_rect.bottom + 6)
            image_rect = None
            if picture:
                y += 10
                if authored_frame:
                    screen.blit(picture,authored_rect)
                    y = max(y,authored_frame.bottom+22)
                else:
                    image_rect = picture.get_rect(midtop=(480, y))
                    screen.blit(picture, image_rect)
                    y += picture.get_height() + 22
            else:
                y += 24
            # Flow the words and input boxes together, including wrapping to new lines.
            # Answer-flow origin and wrapping follow the optional saved area.
            # The same `boxes` rectangles drive drawing and mouse hit-testing.
            answer_left = answer_layout.get('x', 55) if answer_layout else 55
            answer_right = min(920, answer_left + max(120, answer_layout.get('width', 845))) if answer_layout else 900
            if answer_layout:
                y = answer_layout.get('y', y)
            answer_top = y
            x = answer_left; line_height = 55; boxes = []
            pieces = re.split(r'(\[\[\d+\]\]|\s+)', template)
            for part in pieces:
                if not part: continue
                match = MARKER.fullmatch(part)
                if match:
                    i = int(match.group(1)) - 1
                    if not 0 <= i < len(values): continue
                    width = 88
                    if x + width > answer_right: x = answer_left; y += line_height
                    geometry = slot_geometry[i]
                    rect = pygame.Rect(rectangle(geometry, (x, y - 8, width, 42)))
                    field_font = resolve_font(geometry, small, 19)
                    pygame.draw.rect(screen, (248, 253, 255), rect, border_radius=8)
                    pygame.draw.rect(screen, (51, 143, 98) if i == active else (155, 176, 192), rect, 2, border_radius=8)
                    display = values[i]
                    while display and field_font.size(display)[0] > rect.width - 18: display = display[1:]
                    screen.blit(field_font.render(display, True, navy), (rect.x + 10, rect.y + 9))
                    if i == active and pygame.time.get_ticks() % 1000 < 500:
                        cursor_x = rect.x + 10 + field_font.size(display)[0]
                        pygame.draw.line(screen, navy, (cursor_x, rect.y + 8), (cursor_x, rect.bottom - 8), 2)
                    boxes.append((rect, i)); x += width + 7
                elif part.isspace():
                    if '\n' in part: x = answer_left; y += line_height
                    else: x += font.size(' ')[0]
                else:
                    for word in re.findall(r'\S+', part):
                        width = font.size(word)[0]
                        if x + width > answer_right: x = answer_left; y += line_height
                        screen.blit(font.render(word, True, navy), (x, y))
                        x += width
            # Include dynamically wrapped input fields in the scroll extent.
            content_end = max(scroll_bottom, y + line_height + 40)
            if content_end > scroll_bottom:
                scroll_bottom = content_end
            ready = all(v.strip() for v in values)
            screen.blit(small.render('Tab: đổi ô', True, (100, 115, 132)), (55, min(scroll_bottom - 36, y + 52)))
            page.present(question)
            # These controls are locked to the viewport, not to the content.
            mouse = pygame.mouse.get_pos()
            draw_complete(page.display, fixed_submit, small, ready,
                          fixed_submit.collidepoint(mouse), pygame.mouse.get_pressed()[0])
            draw_question_progress(page.display, question)
            regions = None
            if question.get('_studio_scene'):
                from tuhoc.studio.studio_live_preview import option_rects, text_rect
                regions = {'question_text': text_rect(prompt_block) if text_layout else (55, 100, 845, prompt_bottom-100),
                           'question_image': authored_frame or image_rect,
                           'audio_player': audio_rect if has_audio else None,
                           'answer_area': (answer_left, answer_top, answer_right-answer_left, y-answer_top+line_height)}
                regions.update(option_rects(boxes, 'slot'))
            page.frame(question, regions)
            if wf_pending:      # giải mã âm thanh SAU khung hình đầu tiên, tránh màn hình đen
                wf_pending = False
                try:
                    from tuhoc.exercises.pygame_waveform import WaveformAudio
                    wf = WaveformAudio(audio_path)
                except Exception as exc:
                    audio_err = 'Không phát được âm thanh: ' + str(exc)[:60]
            for event in page.events():
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1: wf_drag = None
                if event.type == pygame.MOUSEMOTION and wf_drag and wf is not None and wf_rects:
                    wr, _, _, vr = wf_rects
                    if wf_drag == 'volume': wf.set_volume((event.pos[0] - vr.x) / max(1, vr.width))
                    else: wf.seek(max(0, min(1, (event.pos[0] - wr.x) / max(1, wr.width))) * wf.duration)
                if event.type == pygame.QUIT: return None
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE: return None
                    if event.key == pygame.K_PAGEUP:
                        page.scroll = max(0, page.scroll - 320); continue
                    if event.key == pygame.K_PAGEDOWN:
                        page.scroll = min(page.limit, page.scroll + 320); continue
                    if event.key == pygame.K_TAB:
                        active = (active + (-1 if event.mod & pygame.KMOD_SHIFT else 1)) % len(values)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if ready: return list(values)
                        active = (active + 1) % len(values)
                    elif event.key == pygame.K_BACKSPACE:
                        values[active] = values[active][:-1]
                    elif event.unicode and event.unicode.isprintable() and not (event.mod & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
                        if len(values[active]) < 32:
                            values[active] += event.unicode
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if wf is not None and wf_rects:      # Space dành cho gõ chữ nên chỉ điều khiển bằng chuột
                        wr, pr_, sr, vr = wf_rects
                        menu_hit = next((v for a, v in getattr(wf, 'speed_menu_rects', []) if a.collidepoint(event.pos)), None)
                        if menu_hit is not None:
                            wf.set_speed(menu_hit); wf.speed_menu_open = False; continue
                        if wr.collidepoint(event.pos):
                            wf.seek((event.pos[0] - wr.x) / max(1, wr.width) * wf.duration); wf_drag = 'wave'; continue
                        if pr_.collidepoint(event.pos):
                            wf.play(); continue
                        if sr.collidepoint(event.pos):
                            wf.speed_menu_open = not getattr(wf, 'speed_menu_open', False); continue
                        if vr.inflate(0, 18).collidepoint(event.pos):
                            wf.set_volume((event.pos[0] - vr.x) / max(1, vr.width)); wf_drag = 'volume'; continue
                    viewport_pos = event.viewport_pos
                    if fixed_submit.collidepoint(viewport_pos):
                        if ready: return list(values)
                        continue
                    for rect, i in boxes:
                        if rect.collidepoint(event.pos): active = i; break
            clock.tick(45)
    finally:
        if wf is not None:      # luôn tắt tiếng khi rời bài
            try: wf.stop()
            except Exception: pass
        # Session worker owns the shared SDL display
