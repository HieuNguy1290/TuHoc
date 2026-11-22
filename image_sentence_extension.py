from exercise_buttons import draw_complete
from exercise_gfx import draw_question_progress, present_frame
from extras_render import draw_extras
from exercise_gfx import open_exercise_window
"""Nhìn hình - hoàn thành câu: bấm từ trong ngân hàng để tự điền vào chỗ chấm.

Dữ liệu câu hỏi:
  type='image_sentence_fill', prompt, image,
  blank_text   : câu có các chỗ chấm, ví dụ 'There .... a .... on the ....'
                 (chỗ chấm = 4 dấu chấm trở lên hoặc 3 dấu gạch dưới trở lên)
  blank_answers: đáp án theo thứ tự từng chỗ chấm (có thể là cụm nhiều từ)
  distractors  : đáp án nhiễu
"""
import random
from collections import Counter
import re
from pathlib import Path

BLANK = re.compile(r'\.{4,}|_{3,}')


GROUP_TAG = re.compile(r'\|([A-Za-z][A-Za-z0-9_]*)(/)?(?=\s|$|[.,;:!?])')


def parse_group_template(text):
    """Return (display_text, group_id_per_slot); reject malformed/nested markers."""
    text = str(text or '')
    clean, ids, active, cursor = [], [], None, 0
    for marker in GROUP_TAG.finditer(text):
        chunk = text[cursor:marker.start()]
        clean.append(chunk)
        ids.extend([active] * len(BLANK.findall(chunk)))
        group_id, closing = marker.group(1).casefold(), bool(marker.group(2))
        if closing:
            if active != group_id:
                raise ValueError(f'Đóng nhóm |{group_id}/ không khớp nhóm đang mở.')
            active = None
        else:
            if active is not None:
                raise ValueError('Không được lồng các nhóm đáp án.')
            active = group_id
        cursor = marker.end()
    chunk = text[cursor:]
    clean.append(chunk)
    ids.extend([active] * len(BLANK.findall(chunk)))
    if active is not None:
        raise ValueError(f'Nhóm |{active} chưa đóng bằng |{active}/.')
    display = ''.join(clean)
    if re.search(r'\|[A-Za-z]', display):
        raise ValueError('Thẻ nhóm không hợp lệ. Dùng |a ... |a/ (hoặc |b, |c, ...).')
    return display, ids


def parse_group_answers(text):
    """One group per line: |a answer 1, answer 2. Preserve duplicates."""
    result = {}
    for line in str(text or '').splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.fullmatch(r'\|([A-Za-z][A-Za-z0-9_]*)\s+(.+)', line)
        if not match:
            raise ValueError('Đáp án nhóm phải theo mẫu: |a vẽ tranh, đánh cầu lông')
        key = match.group(1).casefold()
        if key in result:
            raise ValueError(f'Nhóm |{key} bị khai báo đáp án nhiều lần.')
        vals = [x.strip() for x in match.group(2).split(',')]
        if not all(vals):
            raise ValueError(f'Nhóm |{key} có đáp án rỗng.')
        result[key] = vals
    return result


def grouped_expected(text, answer_text):
    display, ids = parse_group_template(text)
    groups = parse_group_answers(answer_text)
    if not ids or any(g is None for g in ids):
        raise ValueError('Mọi ô .... phải nằm trong một nhóm |a ... |a/.')
    if set(ids) != set(groups):
        raise ValueError('Mã nhóm trong nội dung và đáp án không khớp.')
    positions = {key: [i for i, g in enumerate(ids) if g == key] for key in groups}
    if any(len(positions[k]) != len(v) for k, v in groups.items()):
        raise ValueError('Số đáp án của mỗi nhóm phải bằng số ô trống thuộc nhóm đó.')
    indices = {key: 0 for key in groups}
    expected_values = []
    for key in ids:
        expected_values.append(groups[key][indices[key]])
        indices[key] += 1
    return display, ids, expected_values


def blank_count(text):
    return len(BLANK.findall(str(text or '')))


def split_text(text):
    """-> list of ('text', str) / ('slot', index)."""
    parts, last, slot = [], 0, 0
    text = str(text or '')
    for m in BLANK.finditer(text):
        if m.start() > last:
            parts.append(('text', text[last:m.start()]))
        parts.append(('slot', slot)); slot += 1; last = m.end()
    if last < len(text):
        parts.append(('text', text[last:]))
    return parts


def _display_template(question):
    text = question.get('blank_text', '')
    if question.get('type') == 'image_letter_pick' and question.get('group_syntax'):
        try:
            return parse_group_template(text)[0]
        except ValueError:
            return text
    return text


def fill_text(question, values):
    """Ghép đáp án vào câu để hiển thị lại (xem lại bài / kết quả)."""
    values = list(values or [])
    out = []
    for typ, value in split_text(_display_template(question)):
        if typ == 'text':
            out.append(value)
        else:
            got = str(values[value]).strip() if value < len(values) else ''
            out.append(got if got else '....')
    return ''.join(out)


def expected(question):
    return [str(x) for x in (question.get('blank_answers') or [])]


def _group_ranges(text):
    """Each nonempty line containing slots is an independent answer group."""
    groups = []
    offset = 0
    for line in str(text or '').splitlines():
        count = blank_count(line)
        if count:
            groups.append((offset, offset + count))
        offset += count
    return groups


def correct(question, answer):
    exp = expected(question)
    if not isinstance(answer, (list, tuple)) or not exp or len(answer) != len(exp):
        return False
    normalize = lambda value: str(value).strip().casefold()
    if question.get('type') == 'image_letter_pick' and question.get('group_syntax'):
        try:
            _, parsed_ids, parsed_expected = grouped_expected(
                question.get('blank_text', ''), question.get('group_answer_text', ''))
        except ValueError:
            return False
        ids = question.get('blank_group_ids')
        if ids != parsed_ids or list(map(normalize, exp)) != list(map(normalize, parsed_expected)):
            return False
        if not isinstance(ids, list) or len(ids) != len(exp):
            return False
        groups = {}
        for i, key in enumerate(ids):
            groups.setdefault(key, []).append(i)
        return all(Counter(normalize(answer[i]) for i in positions) ==
                   Counter(normalize(exp[i]) for i in positions)
                   for positions in groups.values())
    if question.get('type') == 'image_letter_pick' and question.get('unordered_groups', False):
        ids = question.get('blank_group_ids')
        if ids is not None:
            if not isinstance(ids, list) or len(ids) != len(exp) or any(not str(g).strip() for g in ids):
                return False
            groups = {}
            for index, group_id in enumerate(ids):
                groups.setdefault(str(group_id).strip(), []).append(index)
            return all(Counter(normalize(answer[i]) for i in positions) ==
                       Counter(normalize(exp[i]) for i in positions)
                       for positions in groups.values())
        # Backward compatibility: questions created before explicit group IDs.
        groups = _group_ranges(question.get('blank_text', ''))
        if not groups or groups[-1][1] != len(exp):
            return False
        return all(Counter(map(normalize, answer[start:end])) ==
                   Counter(map(normalize, exp[start:end])) for start, end in groups)
    return all(normalize(a) == normalize(b) for a, b in zip(answer, exp))


def build_editor(parent, original, import_media, resolve_media=None, kind='image_sentence_fill'):
    letters = kind == 'image_letter_pick'
    import tkinter as tk
    from tkinter import filedialog

    def label(value):
        tk.Label(parent, text=value, bg='white', fg='#285D40', anchor='w').pack(fill='x', pady=(9, 3))

    label('Hình minh họa (không bắt buộc)')
    row = tk.Frame(parent, bg='white'); row.pack(fill='x')
    image = tk.Entry(row, font=('Segoe UI', 11)); image.pack(side='left', fill='x', expand=True)
    image.insert(0, str(original.get('image') or ''))

    def browse():
        f = filedialog.askopenfilename(parent=parent.winfo_toplevel(), filetypes=[('Ảnh', '*.png *.jpg *.jpeg *.gif *.webp')])
        if f:
            image.delete(0, 'end'); image.insert(0, import_media(f))

    tk.Button(row, text='Chọn ảnh', command=browse).pack(side='left', padx=5)

    audio = None
    if letters:
        def resolve_audio(ref):
            try:
                path = resolve_media(ref) if resolve_media and ref else None
                return path if path and Path(path).is_file() else None
            except (OSError, ValueError, TypeError):
                return None

        label('File nghe (không bắt buộc) - học sinh bấm nghe rồi chọn chữ cái')
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
            f = filedialog.askopenfilename(parent=parent.winfo_toplevel(), filetypes=[('Âm thanh', '*.mp3 *.wav *.ogg')])
            if f:
                audio.delete(0, 'end'); audio.insert(0, import_media(f)); check_audio()

        def clear_audio():
            audio.delete(0, 'end'); check_audio()

        tk.Button(arow, text='Chọn tệp', command=browse_audio).pack(side='left', padx=5)
        tk.Button(arow, text='Bỏ file nghe', command=clear_audio).pack(side='left')
        audio.bind('<FocusOut>', check_audio, add='+'); check_audio()

    label('Từ/cụm có chỗ chấm: gõ .... (4 dấu chấm) tại mỗi chữ cái bị thiếu, ví dụ Hap....y b....rthday (nhấn Enter để xuống dòng)' if letters else 'Câu có chỗ chấm: gõ .... (4 dấu chấm) tại mỗi vị trí học sinh cần điền (nhấn Enter để xuống dòng)')
    template = tk.Text(parent, height=3, wrap='word', font=('Segoe UI', 11)); template.pack(fill='x')
    template.insert('1.0', original.get('blank_text') or ('Hap....y b....rthday' if letters else 'There .... a .... on the ....'))

    label('Chữ cái đúng theo thứ tự các chỗ chấm (mỗi dòng một chữ)' if letters else 'Đáp án đúng theo thứ tự các chỗ chấm (mỗi dòng một đáp án, có thể nhiều từ, ví dụ: birthday cake)')
    answers = tk.Text(parent, height=4, font=('Segoe UI', 11)); answers.pack(fill='x')
    answers.insert('1.0', original.get('group_answer_text', '') if original.get('group_syntax') else '\n'.join(map(str, original.get('blank_answers') or (['p', 'i'] if letters else ['is', 'birthday cake', 'table']))))

    group_syntax = tk.BooleanVar(value=bool(original.get('group_syntax', False))) if letters else None
    if letters:
        tk.Checkbutton(parent, text='Dùng nhóm |a .... |a/, |b .... |b/, ...; đáp án |a từ 1, từ 2',
                       variable=group_syntax, bg='white', anchor='w').pack(fill='x')
    unordered_groups = None
    group_ids = None
    if letters:
        unordered_groups = tk.BooleanVar(value=bool(original.get('unordered_groups', False)))
        tk.Checkbutton(parent, text='Chấm không phân biệt thứ tự trong từng nhóm đáp án',
                       variable=unordered_groups, bg='white', fg='#285D40', anchor='w').pack(fill='x', pady=(7, 2))
        label('Mã nhóm cho TỪNG ô trống, theo thứ tự (mỗi dòng một mã; các ô cùng nhóm dùng cùng mã). Ví dụ: A, A, A, B, B')
        group_ids = tk.Text(parent, height=4, font=('Segoe UI', 11)); group_ids.pack(fill='x')
        saved_ids = original.get('blank_group_ids')
        if saved_ids is None:
            saved_ids = [str(i + 1) for i, (start, end) in enumerate(_group_ranges(original.get('blank_text', '')))
                         for _ in range(start, end)]
        group_ids.insert('1.0', '\n'.join(map(str, saved_ids)))

    label('Chữ cái nhiễu (mỗi dòng một chữ, không bắt buộc)' if letters else 'Đáp án nhiễu (mỗi dòng một từ/cụm, không bắt buộc)')
    distract = tk.Text(parent, height=3, font=('Segoe UI', 11)); distract.pack(fill='x')
    distract.insert('1.0', '\n'.join(map(str, original.get('distractors') or (['o', 'b'] if letters else ['are', 'chair']))))

    def collect():
        text = template.get('1.0', 'end-1c').strip()
        values = [s.strip() for s in answers.get('1.0', 'end-1c').splitlines() if s.strip()]
        extras = [s.strip() for s in distract.get('1.0', 'end-1c').splitlines() if s.strip()]
        ref = image.get().strip()
        use_syntax = bool(group_syntax.get()) if group_syntax is not None else False
        if use_syntax:
            display, parsed_ids, values = grouped_expected(text, answers.get('1.0', 'end-1c'))
        n = blank_count(text)
        if n < 1:
            raise ValueError('Câu cần có ít nhất một chỗ chấm (gõ ....).')
        if n != len(values):
            raise ValueError(f'Câu có {n} chỗ chấm nhưng có {len(values)} đáp án đúng. Hai số này phải bằng nhau.')
        pool = [x.casefold() for x in values + extras]
        if len(values) + len(extras) > 12:
            raise ValueError('Tối đa 12 từ trong ngân hàng đáp án.')
        for x in extras:
            if x.casefold() in [v.casefold() for v in values]:
                raise ValueError(f'Đáp án nhiễu "{x}" trùng với một đáp án đúng.')
        if ref and resolve_media:
            path = resolve_media(ref)
            if not path or not Path(path).is_file():
                raise ValueError('Không tìm thấy ảnh minh họa.')
        result = {'type': kind, 'blank_text': text, 'blank_answers': values,
                  'distractors': extras, 'options': values + extras, 'answer': ' | '.join(values), 'image': ref}
        if use_syntax:
            result['group_syntax'] = True
            result['group_answer_text'] = answers.get('1.0', 'end-1c').strip()
            result['blank_group_ids'] = parsed_ids
        if unordered_groups is not None:
            result['unordered_groups'] = bool(unordered_groups.get())
            ids = [line.strip() for line in group_ids.get('1.0', 'end-1c').splitlines() if line.strip()]
            if use_syntax:
                pass
            elif result['unordered_groups']:
                if len(ids) != n:
                    raise ValueError(f'Đã bật chấm theo nhóm: cần {n} mã nhóm (mỗi ô trống một mã), hiện có {len(ids)}.')
                result['blank_group_ids'] = ids
            elif ids and len(ids) == n:
                result['blank_group_ids'] = ids
        if audio is not None:
            ref_audio = audio.get().strip()
            if ref_audio and (not resolve_media or not resolve_audio(ref_audio)):
                raise ValueError(f'Không tìm thấy tệp âm thanh: {ref_audio}')
            result['audio'] = ref_audio       # rỗng = không có file nghe
        return result

    return collect


def run(question, letter_mode=False):
    import pygame
    from pygame_exercises import _image, _cached_font
    from exercise_image_zoom import draw_zoom_icon, draw as draw_zoom
    pygame.init(); pygame.display.init()
    screen = open_exercise_window((960, 640))
    pygame.display.set_caption('Tự Học - Bài tập')
    clock = pygame.time.Clock()
    font = _cached_font(None, 22, False)
    sent_font = _cached_font(None, 28, False)
    small = _cached_font(None, 19, False)
    title = _cached_font(None, 26, True)
    navy = (32, 52, 77); bg = (241, 247, 252); green = (44, 143, 108)

    exp = expected(question)
    choices = list(exp) + [str(x) for x in (question.get('distractors') or [])]
    # Custom option slots refer to the editor's original option order.
    # Preserve the legacy shuffle unless an individual chip was positioned.
    from layout_typography import TextBlock, resolve_font
    from question_layout_runtime import element as layout_element, rectangle
    chip_layouts = [layout_element(question, 'option_%d' % i) for i in range(len(choices))]
    if not any(chip_layouts):
        random.shuffle(choices)
    assigned = {}            # slot -> choice index
    target = None            # slot do học sinh chủ động chọn

    picture = None; picture_path = question.get('_pygame_image')
    image_geometry = layout_element(question, 'question_image')
    image_rect = image_frame = None
    if picture_path:
        try:
            if image_geometry:
                from layout_images import pygame_image
                picture, image_rect, image_frame = pygame_image(picture_path,image_geometry,(65,180,520,260))
            else:
                picture = _image(picture_path, (520, 260))
        except (OSError, ValueError, pygame.error): picture = None

    # ---- bố cục câu (độ rộng ô cố định nên không bị nhảy khi điền) ----
    widest = max([sent_font.size(c)[0] for c in choices] + [0])
    slot_w = max(34, widest + 14) if letter_mode else max(96, widest + 26)
    slot_gap = 2 if letter_mode else 8
    answer_area = layout_element(question, 'answer_area') or {}
    sent_font = resolve_font(answer_area, sent_font, 28)
    slot_geometry = [layout_element(question, f'slot_{i}') for i in range(len(question.get('blank_answers') or []))]
    left = min(840, answer_area.get('x', 65))
    right = min(930, left + max(90, answer_area.get('width', 810)))
    items = []; x = left; y = 0; line_h = 46
    # Gom các mảnh chữ + ô trống dính liền nhau thành "từ" để xuống dòng theo cả từ
    # (ví dụ Hap....y không bị cắt giữa chữ và ô trống).
    words, cur = [], []
    def flush():
        nonlocal cur
        if cur:
            words.append(cur); cur = []
    for typ, value in split_text(_display_template(question)):
        if typ == 'text':
            for line_no, part in enumerate(re.split(r'\r\n|\r|\n', value)):
                if line_no:          # Enter trong nội dung = xuống dòng thật
                    flush(); words.append('NL')
                for token in re.findall(r'\S+\s*|\s+', part):
                    cur.append(('text', token, sent_font.size(token)[0]))
                    if token[-1:].isspace():
                        flush()
        else:
            cur.append(('slot', value, slot_w + slot_gap))
    flush()
    for word in words:
        if word == 'NL':
            x = left; y += line_h
            continue
        total = sum(w for _, _, w in word)
        if x + total > right and x > left:
            x = left; y += line_h
        for typ, value, w in word:
            if typ == 'text':
                items.append(('text', value, x, y, w))
            else:
                items.append(('slot', value, x, y, slot_w))
            x += w
    sentence_h = y + line_h

    def wrap(text, face, width):
        lines = []
        for para in str(text).split('\n'):
            line = ''
            for word in para.split():
                trial = (line + ' ' + word).strip()
                if line and face.size(trial)[0] > width:
                    lines.append(line); line = word
                else:
                    line = trial
            lines.append(line)
        return lines
    prompt = TextBlock(question.get('prompt') or 'Look and complete the sentence:',
                       layout_element(question, 'question_text'), font, 22, (52, 109, 845), 27, 3)

    # ---- hàng đáp án (chip) ----
    chip_pos = []; cx = left; cy = 0; chip_h = 42
    for i, c in enumerate(choices):
        w = max(48, small.size(c)[0] + 28) if letter_mode else max(70, small.size(c)[0] + 36)
        if cx + w > right and cx > left:
            cx = left; cy += chip_h + 8
        chip_pos.append((i, cx, cy, w)); cx += w + 10
    chip_rows = (cy // (chip_h + 8)) + 1 if choices else 0
    chips_bottom = 562
    chips_top = chips_bottom - (chip_rows * (chip_h + 8) - 8)
    # Store actual hitboxes in the same coordinate system used for drawing.
    # A missing per-option override retains the original flowing chip row.
    custom_chip_rects = {}
    custom_chip_fonts = {}
    for i, geometry in enumerate(chip_layouts):
        if geometry:
            default = chip_pos[i]
            custom_chip_rects[i] = pygame.Rect(
                geometry.get('x', default[1]),
                geometry.get('y', chips_top + default[2]),
                max(28, geometry.get('width', default[3])),
                max(28, geometry.get('height', chip_h)),
            )
            custom_chip_fonts[i] = resolve_font(geometry, font, 22)
    hint_y = chips_top - 30
    sentence_top = hint_y - 14 - sentence_h
    prompt_bottom = prompt.bottom

    # ---- file nghe (không bắt buộc, chỉ dạng chọn chữ cái) ----
    has_audio = bool(letter_mode and str(question.get('audio') or '').strip())
    audio_path = str(question.get('_resolved_audio') or '').strip() if has_audio else ''
    audio_h = 92 if has_audio else 0
    audio_rect = pygame.Rect(rectangle(layout_element(question, 'audio_player'), (52, prompt_bottom + 8, 856, 88)))
    audio_err = '' if (audio_path or not has_audio) else 'Chưa tìm thấy file nghe. Kiểm tra trong Quản lý nội dung.'
    wf = None; wf_pending = bool(audio_path); wf_rects = None; wf_drag = None
    content_top = prompt_bottom + audio_h      # vùng dưới khung nghe: hình + câu + đáp án
    if not picture:   # không có hình: đưa câu lên sát nội dung câu hỏi, đáp án ngay bên dưới
        sentence_top = content_top + 40
        hint_y = sentence_top + sentence_h + 30
        chips_top = hint_y + 34
    if 'y' in answer_area:
        sentence_top = answer_area['y']
        hint_y = sentence_top + sentence_h + 10
        chips_top = hint_y + 30
    img_box_h = max(60, sentence_top - 12 - content_top)
    if picture and image_frame is None:
        iw, ih = picture.get_size()
        k = min(1.0, img_box_h / max(1, ih))
        if k < 1.0:
            picture = pygame.transform.smoothscale(picture, (max(1, int(iw * k)), max(1, int(ih * k))))

    def button(rect, label, enabled=True, face_font=None):
        mouse = pygame.mouse.get_pos()
        if scroll_max:
            mouse = (mouse[0], mouse[1] + scroll_y)
        hover = enabled and rect.collidepoint(mouse)
        face = (195, 239, 218) if hover else (240, 244, 248)
        edge = green if hover else (200, 210, 222)
        if not enabled:
            face, edge = (236, 239, 242), (210, 216, 223)
        pygame.draw.rect(screen, (176, 190, 200), rect.move(0, 2), border_radius=8)
        pygame.draw.rect(screen, face, rect, border_radius=8)
        pygame.draw.rect(screen, edge, rect, 2 if hover else 1, border_radius=8)
        t = (face_font or small).render(str(label), True, navy if enabled else (150, 158, 168))
        screen.blit(t, t.get_rect(center=rect.center))

    def first_empty():
        return next((i for i in range(len(exp)) if i not in assigned), None)

    # Layout extents are measured in document coordinates.  Only the lesson
    # surface scrolls; the completion button and question counter stay fixed.
    from layout_scroll_extent import content_bottom as layout_content_bottom
    H = 640
    natural_bottom = max(
        640, chips_top + chip_rows * (chip_h + 8) + 45,
        sentence_top + sentence_h + 30,
        max((r.bottom + 28 for r in custom_chip_rects.values()), default=0),
    )
    content_height = max(H, int(layout_content_bottom(question, natural_bottom)))
    scroll_max = max(0, content_height - H)
    scroll_y = 0
    viewport = pygame.Rect(25, 26, 910, 538)
    display_screen = screen
    lesson_surface = pygame.Surface((960, content_height)).convert() if scroll_max else None

    zoom = None
    try:
        while True:
            screen = lesson_surface if lesson_surface is not None else display_screen
            screen.fill(bg)
            pygame.draw.rect(screen, 'white', (25, 25, 910, max(590, content_height - 50)), border_radius=18)
            idx = max(1, int(question.get('_index') or 1)); tot = max(1, int(question.get('_total') or 1))
            prompt.draw(screen, navy)
            zoom_rects = []; hits = []
            if has_audio:
                pygame.draw.rect(screen, (246, 250, 254), audio_rect, border_radius=14)
                pygame.draw.rect(screen, (214, 224, 238), audio_rect, 1, border_radius=14)
                if wf is not None:
                    wf.update()
                    wf_rects = wf.draw(screen, pygame.Rect(audio_rect.x + 10, audio_rect.y + 6, audio_rect.w - 20, audio_rect.h - 12), small)
                elif wf_pending:
                    screen.blit(small.render('Đang tải âm thanh...', True, navy), (audio_rect.x + 22, audio_rect.centery - 8))
                if audio_err:
                    screen.blit(small.render(audio_err, True, (200, 60, 60)), (audio_rect.x + 22, audio_rect.centery - 8))
            if picture:
                pr = image_rect or picture.get_rect(topleft=(left, content_top + 8))
                pygame.draw.rect(screen, (30, 30, 30), pr.inflate(2, 2), 1)
                screen.blit(picture, pr)
                zoom_rects.append((draw_zoom_icon(screen, image_frame or pr), picture_path))
            # câu
            for typ, value, ix, iy, w in items:
                ry = sentence_top + iy
                if typ == 'text':
                    screen.blit(sent_font.render(value, True, navy), (ix, ry))
                else:
                    geometry = slot_geometry[value] if value < len(slot_geometry) else None
                    rect = pygame.Rect(rectangle(geometry, (ix, ry - 2, w, 38)))
                    field_font = resolve_font(geometry, sent_font, 28)
                    if value in assigned:
                        pygame.draw.rect(screen, (214, 236, 255), rect, border_radius=8)
                        pygame.draw.rect(screen, (70, 119, 169), rect, 2, border_radius=8)
                        txt = field_font.render(choices[assigned[value]], True, navy)
                        screen.blit(txt, txt.get_rect(center=rect.center))
                    else:
                        active = (target == value) or (target is None and first_empty() == value)
                        if active:
                            pygame.draw.rect(screen, (233, 245, 255), rect, border_radius=8)
                            pygame.draw.rect(screen, (70, 119, 169), rect, 2, border_radius=8)
                        dots = field_font.render('....', True, navy)
                        screen.blit(dots, dots.get_rect(center=(rect.centerx, rect.centery + 4)))
                    hits.append((rect, ('slot', value)))
            hint = small.render('Click vào đáp án phía dưới để tự động điền vào chỗ chấm', True, navy)
            screen.blit(hint, (left, hint_y))
            used = set(assigned.values())
            for i, cx0, cy0, w in chip_pos:
                rect = custom_chip_rects.get(i) or pygame.Rect(cx0, chips_top + cy0, w, chip_h)
                button(rect, choices[i], enabled=i not in used, face_font=custom_chip_fonts.get(i))
                if i not in used:
                    hits.append((rect, ('choice', i)))
            can_submit = len(assigned) == len(exp) and bool(exp)
            submit = pygame.Rect(738, 570, 170, 38)
            draw_extras(screen, question)
            if lesson_surface is not None:
                screen = display_screen
                screen.fill(bg)
                screen.blit(lesson_surface, (0, 0), area=pygame.Rect(0, scroll_y, 960, 640))
                if scroll_max:
                    track = pygame.Rect(940, 36, 7, 518)
                    pygame.draw.rect(screen, (216, 226, 235), track, border_radius=4)
                    thumb_h = max(32, round(track.height * H / content_height))
                    thumb_y = track.y + round((track.height - thumb_h) * scroll_y / scroll_max)
                    pygame.draw.rect(screen, (112, 141, 166), (track.x, thumb_y, track.w, thumb_h), border_radius=4)
            draw_complete(screen,submit,small,can_submit,submit.collidepoint(pygame.mouse.get_pos()),pygame.mouse.get_pressed()[0])
            if zoom:
                draw_zoom(screen, zoom)

            def leave():
                from pygame_exit_dialog import confirm
                return confirm(screen, clock, 'Thoát bài tập?', 'Bạn muốn rời bài tập này?')

            for event in pygame.event.get():
                if zoom:
                    if event.type in (pygame.MOUSEBUTTONDOWN, pygame.QUIT) or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                        zoom = None
                    continue
                if event.type == pygame.MOUSEWHEEL and scroll_max:
                    scroll_y = max(0, min(scroll_max, scroll_y - event.y * 48))
                    continue
                if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5) and scroll_max:
                    scroll_y = max(0, min(scroll_max, scroll_y + (-48 if event.button == 4 else 48)))
                    continue
                if event.type == pygame.QUIT:
                    if leave(): return None
                    continue
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    wf_drag = None
                if event.type == pygame.MOUSEMOTION and wf_drag and wf is not None and wf_rects:
                    wr, _, _, vr = wf_rects
                    if wf_drag == 'volume':
                        wf.set_volume((event.pos[0] - vr.x) / max(1, vr.width))
                    else:
                        wf.seek(max(0, min(1, (event.pos[0] - wr.x) / max(1, wr.width))) * wf.duration)
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN) and scroll_max:
                        scroll_y = max(0, min(scroll_max, scroll_y + (-H // 2 if event.key == pygame.K_PAGEUP else H // 2)))
                        continue
                    if event.key == pygame.K_ESCAPE:
                        if leave(): return None
                        continue
                    if event.key == pygame.K_SPACE and wf is not None:
                        wf.play(); continue
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and can_submit:
                        return [choices[assigned[i]] for i in range(len(exp))]
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if wf is not None and wf_rects:
                        wr, pr_, sr, vr = wf_rects
                        audio_pos = (event.pos[0], event.pos[1] + scroll_y)
                        menu_hit = next((v for a, v in getattr(wf, 'speed_menu_rects', []) if a.collidepoint(audio_pos)), None)
                        if menu_hit is not None:
                            wf.set_speed(menu_hit); wf.speed_menu_open = False; continue
                        if wr.collidepoint(audio_pos):
                            wf.seek((event.pos[0] - wr.x) / max(1, wr.width) * wf.duration); wf_drag = 'wave'; continue
                        if pr_.collidepoint(audio_pos):
                            wf.play(); continue
                        if sr.collidepoint(audio_pos):
                            wf.speed_menu_open = not getattr(wf, 'speed_menu_open', False); continue
                        if vr.inflate(0, 18).collidepoint(audio_pos):
                            wf.set_volume((event.pos[0] - vr.x) / max(1, vr.width)); wf_drag = 'volume'; continue
                    content_pos = (event.pos[0], event.pos[1] + scroll_y)
                    z = next((p for r, p in zoom_rects if r.collidepoint(content_pos)), None)
                    if z:
                        zoom = z; continue
                    if can_submit and submit.collidepoint(event.pos):
                        return [choices[assigned[i]] for i in range(len(exp))]
                    for rect, (action, index) in hits:
                        if not rect.collidepoint(content_pos):
                            continue
                        if action == 'slot':
                            if index in assigned:
                                del assigned[index]; target = index
                            else:
                                target = index
                        else:
                            slot = target if (target is not None and target not in assigned) else first_empty()
                            if slot is not None:
                                assigned[slot] = index
                            target = None
                        break
            draw_question_progress(display_screen, question)
            present_frame(question)
            if wf_pending:      # giải mã âm thanh SAU khung hình đầu tiên, tránh màn hình đen
                wf_pending = False
                try:
                    from pygame_waveform import WaveformAudio
                    wf = WaveformAudio(audio_path)
                except Exception as exc:
                    audio_err = 'Không phát được âm thanh: ' + str(exc)[:60]
            clock.tick(30)
    finally:
        if wf is not None:      # luôn tắt tiếng khi rời bài
            try: wf.stop()
            except Exception: pass
        # Session worker owns the shared SDL display
