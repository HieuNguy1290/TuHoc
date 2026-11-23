from tuhoc.paths import PROJECT_ROOT
from tuhoc.exercises.exercise_gfx import draw_question_progress
"""Dang bai 'Nghe va chon dap an bang hinh' (type: listening_image_choice).

Cau hoi:
    {'type': 'listening_image_choice',
     'question': 'Nghe va chon hinh dung',      # tuy chon
     'audio': 'audio/abc.mp3',                   # duoc host resolve -> _resolved_audio
     'image_options': [{'image': 'img/a.png', 'label': 'a cat'}, ...],  # 2-6 hinh
     'answer': 'img/a.png'}                      # ref hinh dung (host cham diem)

Tra ve: ref (chuoi 'image') cua hinh duoc chon, hoac None neu huy.
Khong tu cham diem; cung quy uoc voi pygame_exercises.
"""
import math
import os
import time
import random
from pathlib import Path

NAVY = (34, 51, 78); GREEN = (30, 146, 110); GOLD = (255, 204, 89)
BG = (240, 247, 251); CARD = (255, 255, 255); GREY = (223, 231, 241); MUTED = (110, 125, 145)
W, H = 960, 640
MIN_OPTIONS, MAX_OPTIONS = 2, 6


def _options(question):
    """Danh sach (ref, label) hop le; None neu so luong khong hop le."""
    out = []
    for opt in question.get('image_options') or []:
        if isinstance(opt, dict):
            ref = str(opt.get('image', '')).strip()
            label = str(opt.get('label', '') or '').strip()
        else:
            ref, label = str(opt).strip(), ''
        if ref:
            out.append((ref, label))
    return out if MIN_OPTIONS <= len(out) <= MAX_OPTIONS else None


def _layout(n):
    cols = n if n <= 3 else (2 if n == 4 else 3)
    rows = math.ceil(n / cols)
    gap = 20
    area = (40, 215, 880, 345)
    cw = (area[2] - gap * (cols - 1)) // cols
    ch = min(190, (area[3] - gap * (rows - 1)) // rows)
    rects = []
    for i in range(n):
        r, c = divmod(i, cols)
        in_row = cols if r < rows - 1 else n - cols * (rows - 1)
        x0 = area[0] + (area[2] - (in_row * cw + gap * (in_row - 1))) // 2
        rects.append((x0 + c * (cw + gap), area[1] + r * (ch + gap), cw, ch))
    return rects


def run(question):
    """Luon tat am thanh khi roi bai, ke ca khi co loi bat ngo."""
    try:
        return _run(question)
    finally:
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.stop()   # dung ca kenh Sound cua waveform
        except Exception:
            pass


def _run(question):
    import pygame
    import tuhoc.exercises.pygame_exercises as host

    options = _options(question)
    if options is None:
        return None
    # Preserve legacy random order unless individual answer positions are saved.
    from tuhoc.studio.layout_typography import TextBlock, resolve_font
    from tuhoc.studio.question_layout_runtime import element as layout_element
    custom_options = [layout_element(question, f'option_{i}') for i in range(len(options))]
    if not any(custom_options):
        random.shuffle(options)
    images = question.get('_choice_images') or {}
    audio_path = question.get('_resolved_audio') or ''
    prompt = str(question.get('question') or question.get('prompt') or 'Nghe và chọn hình đúng.')

    from tuhoc.exercises.exercise_gfx import open_exercise_window, draw_rect as aa_rect
    from tuhoc.exercises.exercise_layout import Page
    from tuhoc.studio.layout_scroll_extent import content_bottom
    screen = open_exercise_window((W, H))
    page = Page(screen)
    pygame.event.clear()
    pygame.display.set_caption('Tự Học - Bài tập')
    clock = pygame.time.Clock()

    win = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
    candidates = [win / 'segoeui.ttf', win / 'arial.ttf',
                  PROJECT_ROOT / 'assets' / 'fonts' / 'NotoSans-Regular.ttf',
                  Path('/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf'),
                  Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
    font_path = next((str(p) for p in candidates if p.is_file()), None)
    f_title = host._cached_font(font_path, 26, True)
    f_body = host._cached_font(font_path, 20, False)
    f_bold = host._cached_font(font_path, 20, True)
    f_small = host._cached_font(font_path, 16, False)

    question_picture = None
    image_rect = image_frame = None
    question_picture_path = str(question.get('_pygame_image') or '').strip()
    if question_picture_path and Path(question_picture_path).is_file():
        try:
            geometry = layout_element(question, 'question_image')
            if geometry:
                from tuhoc.studio.layout_images import pygame_image
                question_picture, image_rect, image_frame = pygame_image(
                    question_picture_path, geometry, (802, 137, 110, 70))
            else:
                question_picture = host._image(question_picture_path, (110, 70))
        except (pygame.error, OSError, ValueError):
            pass
    from tuhoc.exercises.exercise_image_zoom import draw_zoom_icon, draw as draw_zoom
    zoom_open = None
    zoom_hits = []
    # ---- hinh anh: tai mot lan ----
    cards = _layout(len(options))
    # A custom answer rectangle is used for both drawing and hit-testing.
    for i, custom in enumerate(custom_options):
        if custom:
            x, y, w, h = cards[i]
            cards[i] = (custom.get('x', x), custom.get('y', y),
                        max(48, custom.get('width', w)),
                        max(48, custom.get('height', h)))
    extent = content_bottom(question, max(620, max(pygame.Rect(r).bottom + 78 for r in cards)))
    pics = []
    # Keep the original pixels for custom-sized cards (never enlarge a thumbnail).
    def original_picture(path, max_width, max_height):
        source = pygame.image.load(str(path)).convert_alpha()
        sw, sh = source.get_size()
        ratio = min(max_width / max(1, sw), max_height / max(1, sh))
        size = (max(1, round(sw * ratio)), max(1, round(sh * ratio)))
        return pygame.transform.smoothscale(source, size) if size != (sw, sh) else source
    for (ref, _), rect in zip(options, cards):
        surf = None
        path = images.get(ref)
        if path and Path(path).is_file():
            try:
                if custom_options[len(pics)]:
                    surf = original_picture(path, max(1, rect[2] - 24),
                                            max(1, rect[3] - 24 - (26 if _ else 0)))
                else:
                    surf = host._image(path, (rect[2] - 24, rect[3] - 24 - (26 if _ else 0)))
            except (pygame.error, OSError, ValueError):
                surf = None
        pics.append(surf)

    # ---- audio ----
    total = 0.0
    if audio_path:
        try:
            import mutagen
            total = float(mutagen.File(audio_path).info.length)
        except Exception:
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                total = float(pygame.mixer.Sound(audio_path).get_length())
            except Exception:
                total = 0.0
    st = {'playing': False, 'paused': False, 'played': 0.0, 'since': None,
          'plays': 0, 'error': '' if audio_path else 'Chưa tìm thấy file nghe. Kiểm tra trong Quản lý nội dung.'}

    wf = None               # WaveformAudio (giong cac bai nghe khac); None = dung bo phat don gian
    wf_pending = bool(audio_path)
    wf_rects = None
    wf_drag = None

    def elapsed():
        if st['since'] is None:
            return st['played']
        return min(total or 1e9, st['played'] + time.monotonic() - st['since'])

    def toggle_audio():
        if not audio_path:
            return
        if wf is not None:
            wf.play()
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            if st['playing'] and not st['paused']:
                st['played'] = elapsed(); st['since'] = None; st['paused'] = True
                pygame.mixer.music.pause()
            elif st['paused']:
                pygame.mixer.music.unpause(); st['since'] = time.monotonic(); st['paused'] = False
            else:
                pygame.mixer.music.stop(); pygame.mixer.music.load(audio_path); pygame.mixer.music.play()
                st.update(played=0.0, since=time.monotonic(), playing=True, paused=False)
                st['plays'] += 1
            st['error'] = ''
        except (pygame.error, OSError) as exc:
            st.update(playing=False, paused=False, since=None)
            st['error'] = 'Không phát được âm thanh: ' + str(exc)[:70]

    def replay():
        if not audio_path:
            return
        if wf is not None:
            wf.seek(0)
            if not (wf.active and not wf.paused):
                wf.play()
            return
        st.update(playing=False, paused=False, since=None, played=0.0)
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass
        toggle_audio()

    def stop_audio():
        if wf is not None:
            wf.stop()
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except pygame.error:
            pass

    # ---- ve ----
    def text(s, font, color, x, y, center=False):
        img = font.render(s, True, color)
        screen.blit(img, img.get_rect(center=(x, y)) if center else (x, y))

    def rrect(rect, color, r=14, width=0):
        aa_rect(screen, color, rect, width, border_radius=r)

    def wrap(s, font, maxw):
        lines, cur = [], ''
        for word in s.split():
            t = (cur + ' ' + word).strip()
            if font.size(t)[0] <= maxw or not cur:
                cur = t
            else:
                lines.append(cur); cur = word
        return lines + ([cur] if cur else [])

    from tuhoc.studio.question_layout_runtime import rectangle
    prompt_block = TextBlock(prompt, layout_element(question, 'question_text'),
                             f_title, 26, (40, 44, 880), 32, 2)
    audio_rect = pygame.Rect(rectangle(layout_element(question, 'audio_player'), (40, 104, 880, 92)))
    extent = max(extent, prompt_block.bottom, audio_rect.bottom + 10)
    play_side = min(64, max(12, audio_rect.height-16), max(12, audio_rect.width//5))
    replay_side = min(48, play_side)
    play_btn = pygame.Rect(audio_rect.x+20, audio_rect.centery-play_side//2, play_side, play_side)
    replay_btn = pygame.Rect(play_btn.right+16, audio_rect.centery-replay_side//2, replay_side, replay_side)
    bar = pygame.Rect(replay_btn.right+22, audio_rect.centery-8, max(1, audio_rect.right-replay_btn.right-112), 12)
    from tuhoc.exercises.exercise_buttons import complete_rect
    submit = complete_rect(572)
    # Text size follows the matching saved answer slot, if specified.
    option_label_fonts = [resolve_font(c, f_bold, 20) for c in custom_options]
    selected = None
    hover = None
    ripples = []          # (x, y, t0)
    press_until = {}

    def confirm_exit():
        modal = pygame.Rect(245, 225, 470, 185)
        yes, no = pygame.Rect(360, 335, 105, 43), pygame.Rect(495, 335, 105, 43)
        while True:
            if host._shutdown_requested.is_set():
                return True
            veil = pygame.Surface((W, H), pygame.SRCALPHA); veil.fill((17, 31, 48, 170))
            screen.blit(veil, (0, 0))
            rrect(modal, CARD, 16)
            text('Thoát bài tập?', f_title, NAVY, 330, 252)
            text('Bạn muốn đóng cửa sổ bài tập?', f_body, NAVY, 300, 295)
            rrect(yes, GREEN, 9); rrect(no, GREY, 9)
            text('Thoát', f_bold, (255, 255, 255), yes.centerx, yes.centery, True)
            text('Ở lại', f_bold, NAVY, no.centerx, no.centery, True)
            draw_question_progress(screen, question)
            pygame.display.flip()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return True
                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_ESCAPE, pygame.K_n): return False
                    if ev.key in (pygame.K_RETURN, pygame.K_y): return True
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if yes.collidepoint(ev.pos): return True
                    if no.collidepoint(ev.pos): return False
            clock.tick(30)

    while True:
        now = time.monotonic()
        if host._shutdown_requested.is_set():
            stop_audio(); return None
        # het bai nghe
        if st['playing'] and not st['paused'] and pygame.mixer.get_init() and not pygame.mixer.music.get_busy():
            st.update(playing=False, since=None, played=total)

        for ev in page.events(scroll_enabled=not bool(zoom_open)):
            if zoom_open:
                if ev.type in (pygame.MOUSEBUTTONDOWN,pygame.QUIT) or (ev.type==pygame.KEYDOWN and ev.key==pygame.K_ESCAPE):zoom_open=None
                continue
            if ev.type == pygame.QUIT:
                stop_audio(); return None
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if confirm_exit():
                        stop_audio(); return None
                elif ev.key == pygame.K_SPACE:
                    toggle_audio()
                elif ev.key == pygame.K_r:
                    replay()
                elif pygame.K_1 <= ev.key <= pygame.K_6 and ev.key - pygame.K_1 < len(options):
                    selected = ev.key - pygame.K_1
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and selected is not None:
                    stop_audio(); return options[selected][0]
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                wf_drag = None
            elif ev.type == pygame.MOUSEMOTION and wf_drag and wf is not None and wf_rects:
                wr, _, _, vr = wf_rects
                if wf_drag == 'volume':
                    wf.set_volume((ev.pos[0] - vr.x) / max(1, vr.width))
                else:
                    wf.seek(max(0, min(1, (ev.pos[0] - wr.x) / max(1, wr.width))) * wf.duration)
            elif ev.type == pygame.MOUSEMOTION:
                hover = next((i for i, r in enumerate(cards) if pygame.Rect(r).collidepoint(ev.pos)), None)
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if submit.collidepoint(ev.viewport_pos):
                    if selected is not None:
                        stop_audio()
                        return options[selected][0]
                    continue
                zoom_target=next((path for rect,path in zoom_hits if rect.collidepoint(ev.pos)),None)
                if zoom_target:
                    zoom_open=zoom_target;continue
                ripples.append((ev.pos[0], ev.pos[1], now))
                if wf is not None and wf_rects:
                    wr, pr_, sr, vr = wf_rects
                    menu_hit = next((v for a, v in getattr(wf, 'speed_menu_rects', []) if a.collidepoint(ev.pos)), None)
                    if menu_hit is not None:
                        wf.set_speed(menu_hit); wf.speed_menu_open = False
                        continue
                    if wr.collidepoint(ev.pos):
                        wf.seek((ev.pos[0] - wr.x) / max(1, wr.width) * wf.duration); wf_drag = 'wave'
                        continue
                    if pr_.collidepoint(ev.pos):
                        wf.play(); continue
                    if sr.collidepoint(ev.pos):
                        wf.speed_menu_open = not getattr(wf, 'speed_menu_open', False); continue
                    if vr.inflate(0, 18).collidepoint(ev.pos):
                        wf.set_volume((ev.pos[0] - vr.x) / max(1, vr.width)); wf_drag = 'volume'
                        continue
                if wf is None and play_btn.collidepoint(ev.pos):
                    toggle_audio()
                elif wf is None and replay_btn.collidepoint(ev.pos):
                    replay()
                else:
                    for i, r in enumerate(cards):
                        if pygame.Rect(r).collidepoint(ev.pos):
                            selected = i; press_until[i] = now + 0.12

        screen = page.begin(extent, padding=0)
        screen.fill(BG)
        # tieu de
        #text('NGHE VÀ CHỌN HÌNH', f_small, GREEN, 40, 22)
        prompt_block.draw(screen, NAVY)
        # khung audio: waveform giong cac bai nghe khac
        rrect(audio_rect, CARD, 18)
        if wf is not None:
            wf.update()
            wf_rects = wf.draw(screen, pygame.Rect(audio_rect.x+13, audio_rect.y+8, max(16, audio_rect.width-52), max(16, audio_rect.height-19)), f_small)
            if st['error']:
                text(st['error'], f_small, (200, 60, 60), 60, 108)
        elif wf_pending:
            text('Đang tải âm thanh...', f_body, NAVY, 74, 138)
        else:
            pulse = 1 + 0.05 * math.sin(now * 6) if st['playing'] and not st['paused'] else 1
            pr = int(32 * pulse)
            pygame.draw.circle(screen, GREEN, play_btn.center, pr)
            cx, cy = play_btn.center
            if st['playing'] and not st['paused']:
                aa_rect(screen, (255, 255, 255), (cx - 11, cy - 12, 8, 24), border_radius=2)
                aa_rect(screen, (255, 255, 255), (cx + 3, cy - 12, 8, 24), border_radius=2)
            else:
                pygame.draw.polygon(screen, (255, 255, 255), [(cx - 8, cy - 14), (cx - 8, cy + 14), (cx + 14, cy)])
            pygame.draw.circle(screen, GREY, replay_btn.center, 24)
            pygame.draw.arc(screen, NAVY, replay_btn.inflate(-22, -22), 0.6, 5.6, 3)
            rx, ry = replay_btn.centerx + 7, replay_btn.centery - 9
            pygame.draw.polygon(screen, NAVY, [(rx, ry - 5), (rx + 8, ry + 2), (rx - 2, ry + 4)])
            rrect(bar, GREY, 6)
            e = elapsed()
            frac = min(1.0, e / total) if total > 0 else 0
            if frac > 0:
                rrect(pygame.Rect(bar.x, bar.y, max(12, int(bar.w * frac)), bar.h), GREEN, 6)
            mm = lambda s: f'{int(s) // 60:02d}:{int(s) % 60:02d}'
            text(mm(e), f_small, MUTED, bar.x, bar.bottom + 8)
            text(mm(total), f_small, MUTED, bar.right - f_small.size(mm(total))[0], bar.bottom + 8)
            if st['error']:
                text(st['error'], f_small, (200, 60, 60), 210, 106)
        # Zoom controls for both question and answer illustrations.
        zoom_hits=[]
        if question_picture is not None:
            qr=image_rect or question_picture.get_rect(bottomright=(912,207))
            screen.blit(question_picture,qr)
            zoom_hits.append((draw_zoom_icon(screen,image_frame or qr),question_picture_path))
        # the hinh
        for i, (r, (ref, label)) in enumerate(zip(cards, options)):
            rect = pygame.Rect(r)
            lift = 4 if (hover == i or selected == i) else 0
            if press_until.get(i, 0) > now:
                lift = -2
            rect.y -= lift
            shadow = rect.move(0, 5 + lift)
            rrect(shadow, (214, 224, 236), 16)
            rrect(rect, CARD, 16)
            if selected == i:
                rrect(rect, GOLD, 16, 4)
            elif hover == i:
                rrect(rect, GREEN, 16, 2)
            else:
                rrect(rect, GREY, 16, 2)
            avail_h = rect.h - 16 - (28 if label else 0)
            pic = pics[i]
            # Image and caption must be clipped to their OWN answer card.
            # Saved layouts can make cards much shorter than their old images.
            inner = rect.inflate(-16, -16)
            if label:
                inner.height = max(1, inner.height - 28)
            if pic is not None and inner.width > 0 and inner.height > 0:
                pw, ph = pic.get_size()
                scale = min(1.0, inner.width / max(1, pw), inner.height / max(1, ph))
                fitted = (max(1, int(pw * scale)), max(1, int(ph * scale)))
                shown = pygame.transform.smoothscale(pic, fitted) if fitted != (pw, ph) else pic
                old_clip = screen.get_clip()
                screen.set_clip(rect.clip(old_clip))
                shown_rect=shown.get_rect(center=inner.center)
                screen.blit(shown,shown_rect)
                screen.set_clip(old_clip)
                image_path=images.get(ref)
                if image_path:zoom_hits.append((draw_zoom_icon(screen,shown_rect),image_path))
            elif pic is None:
                text('Thiếu hình', f_body, MUTED, rect.centerx, rect.y + 8 + max(1, avail_h) // 2, True)
            if label:
                old_clip = screen.get_clip()
                screen.set_clip(rect.clip(old_clip))
                label_surface = option_label_fonts[i].render(label, True, NAVY)
                # Long captions cannot bleed into neighboring answer cards.
                if label_surface.get_width() > max(1, rect.width - 16):
                    factor = (rect.width - 16) / max(1, label_surface.get_width())
                    label_surface = pygame.transform.smoothscale(label_surface, (max(1, int(label_surface.get_width() * factor)), max(1, int(label_surface.get_height() * factor))))
                screen.blit(label_surface, label_surface.get_rect(center=(rect.centerx, rect.bottom - 18)))
                screen.set_clip(old_clip)
            badge = pygame.Rect(rect.x + 8, rect.y + 8, 28, 28)
            pygame.draw.circle(screen, GOLD if selected == i else GREY, badge.center, 14)
            text(str(i + 1), f_small, NAVY, badge.centerx, badge.centery, True)
        # nut xac nhan
        ready = selected is not None
        # hieu ung click
        alive = []
        for x, y, t0 in ripples:
            age = now - t0
            if age < 0.45:
                s = pygame.Surface((W, H), pygame.SRCALPHA)
                pygame.draw.circle(s, (30, 146, 110, int(120 * (1 - age / 0.45))), (x, y), int(8 + age * 90), 3)
                screen.blit(s, (0, 0)); alive.append((x, y, t0))
        ripples = alive
        page.present(question)
        page.complete(question, submit, f_bold, ready)
        screen = page.display
        if zoom_open:draw_zoom(screen,zoom_open)
        regions = None
        if question.get('_studio_scene'):
            from tuhoc.studio.studio_live_preview import option_rects, text_rect
            regions = {'question_text': text_rect(prompt_block), 'audio_player': audio_rect,
                       'question_image': (image_frame or qr) if question_picture is not None else None}
            regions.update(option_rects((r, i) for i, r in enumerate(cards)))
        page.frame(question, regions)
        if wf_pending:      # giai ma am thanh SAU khung hinh dau tien, tranh man hinh den
            wf_pending = False
            try:
                from tuhoc.exercises.pygame_waveform import WaveformAudio
                wf = WaveformAudio(audio_path)
            except Exception as exc:
                st['error'] = 'Waveform: ' + str(exc)[:60]
        clock.tick(60)
