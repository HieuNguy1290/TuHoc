from question_prompt import display_prompt
from exercise_gfx import draw_question_progress, present_frame
from extras_render import draw_extras
from question_layout_store import pixel_extras
from question_rich_text import draw as draw_rich
"""Pygame interaction and scoring for the five additional editor formats."""
import re
import random
from pathlib import Path

NEW_TYPES = frozenset(('image_multi_choice','picture_missing_letters','sentence_gaps','conversation_gaps','passage_gaps','image_multi_select','text_multi_select','audio_multi_select','image_write_answer','image_underline_choice','sentence_underline_words','dropdown_fill_blank','multi_fill_blanks','image_sentence_fill','image_letter_pick','inline_dropdown_fill'))
TOKEN = re.compile(r'\S+')

def gaps(question):
    kind=question.get('type')
    if kind=='conversation_gaps':
        result=[]
        for line in question.get('dialogue',[]):
            text=line.get('text','')
            result.append((text, sorted(set(line.get('hidden_indices',[])))))
        return result
    return [(str(question.get('source_text','')), sorted(set(question.get('hidden_indices',[]))))]

def expected(question):
    kind=question.get('type')
    if kind in ('image_sentence_fill','image_letter_pick','inline_dropdown_fill'):
        return [str(x) for x in (question.get('blank_answers') or [])]
    if kind == 'multi_fill_blanks':
        return list(question.get('blank_answers') or [])
    if kind == 'dropdown_fill_blank':
        if question.get('blank_answers'): return list(question['blank_answers'])
        return str(question.get('answer',''))
    if kind in ('image_underline_choice','sentence_underline_words'):
        from underline_extension import expected as underline_expected
        return underline_expected(question)
    if kind == 'image_write_answer':
        from image_write_extension import expected
        return expected(question)
    if kind in ('image_multi_select','text_multi_select','audio_multi_select'):
        from multi_select_extension import expected_answers
        return expected_answers(question)
    if kind=='image_multi_choice':return str(question.get('answer',''))
    if kind=='picture_missing_letters':return str(question.get('answer',''))
    if kind in ('sentence_gaps','passage_gaps','conversation_gaps'):
        out=[]
        for text,indices in gaps(question):
            tokens=TOKEN.findall(text)
            out.extend(tokens[i] for i in indices if isinstance(i,int) and 0<=i<len(tokens))
        return out
    return None

def correct(question,answer):
    kind=question.get('type')
    if kind in ('image_sentence_fill','image_letter_pick','inline_dropdown_fill'):
        from image_sentence_extension import correct as isf_correct
        return isf_correct(question, answer)
    if kind == 'multi_fill_blanks':
        from multi_fill_blanks_extension import correct as multi_correct
        return multi_correct(question, answer)
    if kind == 'dropdown_fill_blank':
        if question.get('blank_answers'):
            from dropdown_inline_logic import correct as inline_correct
            return inline_correct(question,answer)
        return str(answer).strip() == str(question.get('answer','')).strip()
    if kind in ('image_underline_choice','sentence_underline_words'):
        from underline_extension import correct as underline_correct
        return underline_correct(question,answer)
    if kind == 'image_write_answer':
        from image_write_extension import correct
        return correct(question, answer)
    if kind in ('image_multi_select','text_multi_select','audio_multi_select'):
        from multi_select_extension import is_correct
        return is_correct(question, answer)
    if kind=='image_multi_choice':return str(answer)==str(question.get('answer',''))
    if kind=='picture_missing_letters':return str(answer).casefold()==str(question.get('answer','')).casefold()
    if kind in ('sentence_gaps','passage_gaps','conversation_gaps'):
        exp=expected(question)
        return isinstance(answer,(list,tuple)) and len(answer)==len(exp) and all(str(a).casefold()==str(b).casefold() for a,b in zip(answer,exp))
    return False

def answer_text(question,answer):
    if question.get('type') == 'sentence_underline_words' and isinstance(answer,(list,tuple,set)):
        from underline_extension import TOKEN
        words=TOKEN.findall(question.get('source_text',''))
        return ' | '.join(words[i] for i in sorted(set(answer)) if isinstance(i,int) and 0<=i<len(words))
    if isinstance(answer,(list,tuple)):return ' | '.join(str(x) for x in answer)
    return str(answer)

def run(question):
    if question.get('type') == 'inline_dropdown_fill':
        from inline_dropdown_extension import run as idf_run
        return idf_run(question)
    if question.get('type') == 'image_letter_pick':
        from image_letter_pick_extension import run as ilp_run
        return ilp_run(question)
    if question.get('type') == 'image_sentence_fill':
        from image_sentence_extension import run as isf_run
        return isf_run(question)
    if question.get('type') == 'multi_fill_blanks':
        from multi_fill_blanks_extension import run as multi_run
        return multi_run(question)
    if question.get('type') == 'dropdown_fill_blank':
        from dropdown_extension import run as dropdown_run
        return dropdown_run(question)
    if question.get('type') in ('image_underline_choice','sentence_underline_words'):
        from underline_extension import run as underline_run
        return underline_run(question)
    if question.get('type') == 'image_write_answer':
        from image_write_extension import run
        return run(question)
    if question.get('type') in ('image_multi_select','text_multi_select','audio_multi_select'):
        from multi_select_extension import run
        return run(question)
    import pygame
    from layout_typography import TextBlock, resolve_font
    from exercise_buttons import complete_rect, draw_complete
    from exercise_gfx import draw_rect as aa_rect
    from pygame_exercises import _image, _cached_font, _a21_log
    from exercise_gfx import open_exercise_window
    _a21_log('extended_display_set_mode_begin')
    screen=open_exercise_window((960,640))
    _a21_log('extended_display_set_mode_ok')
    pygame.display.set_caption('Tự Học - Bài tập')
    clock=pygame.time.Clock()
    font=_cached_font(None,21,False)
    small=_cached_font(None,17,False)
    title=_cached_font(None,26,True)
    navy=(32,52,77);blue=(47,120,200);bg=(241,247,252)
    kind=question['type']
    # Optional question narration: does not replace type-specific listening audio.
    # The button is drawn inside the existing header, so absent media uses no space.
    narration_path = str(question.get('_resolved_audio') or '').strip()
    narration_path = narration_path if narration_path and Path(narration_path).is_file() else ''
    narration_playing = False
    narration_button = pygame.Rect(566, 51, 166, 32) if narration_path else None
    narration_error = False
    narration_waveform = None
    narration_waveform_pending = bool(narration_path)
    narration_waveform_rects = None
    from question_layout_runtime import element as _audio_layout_element, rectangle
    _audio_geometry = _audio_layout_element(question, 'audio_player') or {}
    narration_waveform_area = pygame.Rect(
        int(_audio_geometry.get('x', 510)), int(_audio_geometry.get('y', 39)),
        max(250, int(_audio_geometry.get('width', 382))),
        max(75, int(_audio_geometry.get('height', 92)))) if narration_path else None
    # Layout Editor stores viewport coordinates. Never convert the player's
    # position into document/scroll coordinates or force it to a header band.
    # Clamp only to the physical display so the player remains accessible.
    # Saved audio_player = a document element: it scrolls with the answers.
    # No saved layout = legacy header overlay (fixed, unchanged).
    audio_doc = bool(narration_waveform_area is not None and _audio_geometry)
    narration_mini_box = None
    narration_mini_rects = None
    if narration_waveform_area is not None:
        narration_waveform_area.width = min(narration_waveform_area.width, 936)
        narration_waveform_area.height = min(narration_waveform_area.height, 220)
        narration_waveform_area.x = max(0, min(narration_waveform_area.x,
                                              960 - narration_waveform_area.width))
        narration_waveform_area.y = max(0, min(narration_waveform_area.y,
                                              (2560 if audio_doc else 640) - narration_waveform_area.height))
    exp=expected(question)
    # Optional question illustration, separate from the images used as answers.
    question_picture = None
    question_picture_rect = question_picture_frame = None
    question_picture_path = str(question.get('_pygame_image') or '').strip()
    if kind == 'image_multi_choice' and question_picture_path and Path(question_picture_path).is_file():
        try:
            geometry = _audio_layout_element(question,'question_image')
            if geometry:
                from layout_images import pygame_image
                question_picture, question_picture_rect, question_picture_frame = pygame_image(
                    question_picture_path,geometry,(737,119,155,105))
            else:
                question_picture = _image(question_picture_path, (155, 105))
        except (pygame.error, OSError, ValueError):
            pass
    images={}
    if kind=='image_multi_choice':
        options=question.get('image_options') or [{'image':x} for x in question.get('options',[])]
        items=[str(o.get('image','')) for o in options]
        for name,path in question.get('_choice_images',{}).items():
            try:
                # Keep the full-resolution image. The previous 205x104
                # thumbnail was scaled *again* when drawing a resized card.
                images[name] = pygame.image.load(str(path)).convert_alpha()
            except (pygame.error,OSError,ValueError):pass
        chosen=None
    elif kind=='picture_missing_letters':
        letters=list(str(exp));hidden=set(question.get('hidden_indices',[]));values={i:'' for i in hidden};active=next(iter(sorted(hidden)),None)
        picture=None
        try:
            p=question.get('_pygame_image')
            if p:
                picture=_image(p,(300,170))
        except (pygame.error,OSError,ValueError):pass
    else:
        parts=gaps(question);flat=[];slot=0
        for text,indices in parts:
            tokens=list(TOKEN.finditer(text)); hidden=set(indices);segments=[];last=0
            for i,m in enumerate(tokens):
                if i in hidden:
                    if m.start()>last:segments.append(('text',text[last:m.start()]))
                    segments.append(('slot',slot));slot+=1;last=m.end()
            if last<len(text):segments.append(('text',text[last:]))
            if kind=='conversation_gaps':
                speaker=str(question.get('dialogue',[])[len(flat)].get('speaker',''))
                segments.insert(0,('text',speaker+': '))
            flat.append(segments)
        # Optional illustration for all gap-based formats.  Do not reserve
        # any vertical space when the question has no usable image.
        sentence_picture = None
        optional_picture_path = str(question.get('_pygame_image') or '').strip()
        if optional_picture_path and Path(optional_picture_path).is_file():
            try:
                sentence_picture = _image(optional_picture_path, (370, 190))
            except (pygame.error, OSError, ValueError):
                pass
        choices=list(exp)+list(question.get('distractors',[]));random.shuffle(choices)
        from pygame_scroll import ScrollThumb
        gap_scrollbar = ScrollThumb()
        assigned={};selected_slot=0;scroll=0;max_scroll=0;choice_page=0
        # Layout overrides apply only to the three gap-based question types.
        # Keep the choice bank, answer correctness and legacy geometry unchanged.
        from question_layout_runtime import element as layout_element
        gap_area = layout_element(question, 'answer_area') or {}
        gap_image_area = layout_element(question, 'question_image') or {}
        bank = layout_element(question, 'word_bank') or {}
        gap_slot_layouts = [layout_element(question, f'slot_{i}') for i in range(len(exp))]
        word_layouts = [layout_element(question, f'word_{i}') for i in range(len(choices))]
        gap_font = resolve_font(gap_area, font, 21)
        bank_font = resolve_font(bank, small, 16)
        gap_left = int(gap_area.get('x', 65))
        gap_top = int(gap_area.get('y', 221))
        gap_right = min(900, gap_left + max(115, int(gap_area.get('width', 810))))
        if gap_right <= gap_left + 115:
            gap_right = gap_left + 116
        gap_picture_rect = gap_picture_frame = None
        if sentence_picture is not None and gap_image_area:
            from layout_images import pygame_image
            try:
                sentence_picture, gap_picture_rect, gap_picture_frame = pygame_image(
                    optional_picture_path,gap_image_area,(gap_left,gap_top,*sentence_picture.get_size()))
            except (OSError,ValueError,pygame.error):
                pass
    def draw_label(value,x,y,f=font,color=navy):draw_rich(screen,f,str(value),color,x,y)
    def wrap_prompt(value, face, max_width):
        # Keep the complete question; split at word boundaries and preserve newlines.
        lines=[]
        for paragraph in str(value).split('\n'):
            if not paragraph.strip():
                lines.append('')
                continue
            line=''
            for word in paragraph.split():
                candidate=(line+' '+word).strip()
                if face.size(candidate)[0] <= max_width:
                    line=candidate
                else:
                    if line:
                        lines.append(line)
                    line=''
                    # Also handle a single unbroken word wider than the question area.
                    for char in word:
                        if line and face.size(line+char)[0] > max_width:
                            lines.append(line)
                            line=''
                        line+=char
            lines.append(line)
        return lines or ['']
    prompt_scroll=0
    prompt_block = TextBlock(display_prompt(question, 'Hoàn thành bài tập'),
                             _audio_layout_element(question, 'question_text'), font, 21, (52, 109, 845), 27)
    prompt_lines = prompt_block.lines
    prompt_visible=3
    def button(rect,label,fill=(231,239,248),enabled=True,label_font=None):
        # Consistent hover/pressed feedback for gap and letter controls.
        pointer = pygame.mouse.get_pos()
        if letter_page:pointer = (pointer[0],pointer[1]+letter_page.scroll)
        hovered = enabled and rect.collidepoint(pointer)
        pressed = hovered and pygame.mouse.get_pressed()[0]
        if not enabled:
            face, edge, ink = (235,238,241), (207,214,221), (134,143,153)
        elif hovered:
            face = (162,222,199) if pressed else (195,239,218)
            edge, ink = (44,143,108), navy
        else:
            face, edge, ink = fill, (185,201,221), navy
        aa_rect(screen,(172,189,199),rect.move(0,2),border_radius=8)
        aa_rect(screen,face,rect,border_radius=8)
        aa_rect(screen,edge,rect,2 if hovered else 1,border_radius=8)
        t=(label_font or small).render(str(label),True,ink);screen.blit(t,t.get_rect(center=rect.center))
    zoom_path = None
    zoom_regions = []
    from exercise_image_zoom import draw_zoom_icon
    letter_page=None
    # Opt-in scrolling for the image-choice layout; legacy questions unchanged.
    choice_page_surface = None
    choice_positions = {}
    if kind == 'image_multi_choice':
        from question_layout_runtime import element as layout_element
        from exercise_layout import Page
        for i in range(len(items)):
            geometry = layout_element(question, 'option_%d' % i)
            if geometry:
                choice_positions[i] = geometry
        if choice_positions:
            # A wide, short saved option box turns an image into a tiny icon.
            # Build image-sized cards, keeping their authored order and x anchor.
            # Reflow subsequent cards so enlarged pictures never overlap.
            previous_bottom = 285
            for i in range(len(items)):
                old = choice_positions.get(i, {})
                path = question.get('_choice_images', {}).get(items[i])
                source = images.get(items[i])
                if source is None:
                    continue
                iw, ih = source.get_size()
                target_w = max(1, old.get('width', max(180, min(360, iw + 24))))
                target_h = max(1, old.get('height', max(125, min(245, round(target_w * ih / max(1, iw)) + 24))))
                x = old.get('x', max(48, min(900-target_w, 95)))
                y = old.get('y', max(previous_bottom + 14, 300))
                choice_positions[i] = dict(old, x=x, y=y, width=target_w, height=target_h)
                previous_bottom = y + target_h
            choice_page_surface = Page(screen)
        if choice_page_surface is None and audio_doc and narration_waveform_area.bottom > 560:
            choice_page_surface = Page(screen)
    if kind=='picture_missing_letters':
        from layout_scroll_extent import content_bottom as scroll_extent
        letter_slots = {i: _audio_layout_element(question, f'slot_{i}') for i in hidden}
        from exercise_layout import Page, wrap as flow_wrap, block_top, image_message, letter_items
        letter_page=Page(screen)
        letter_prompt_bottom = prompt_block.bottom
        letter_note=image_message(question,picture)
        media_height=picture.get_height()+22 if picture else 32 if letter_note else 0
        from question_layout_runtime import element as layout_element
        letter_area_geometry = layout_element(question, 'answer_area') or {}
        letter_cell_geometry = layout_element(question, 'option_0') or {}
        letter_text_font = resolve_font(letter_area_geometry, font, 21)
        letter_font = resolve_font({**letter_area_geometry, **letter_cell_geometry}, small, 17)
        letter_left = min(870, letter_area_geometry.get('x', 70))
        letter_width = min(945-letter_left, max(32, letter_area_geometry.get('width', 820)))
        letter_cell = (min(letter_width, max(20, letter_cell_geometry.get('width', 42))),
                       min(140, max(20, letter_cell_geometry.get('height', 44))))
        letter_positions,letter_height=letter_items(
            letters, hidden, letter_text_font, left=letter_left, width=letter_width, cell=letter_cell)
        letter_group_top=block_top(letter_prompt_bottom,media_height+letter_height)
        letter_top=letter_group_top+media_height
        letter_hint_y=letter_top+letter_height+20
        letter_submit_y=max(553,letter_top+letter_height+20)
        # Optional per-question layout: position the editable letter group.
        # Preserve all legacy geometry when no answer_area override is saved.
        from question_layout_runtime import element as layout_element
        letter_area_geometry = layout_element(question, 'answer_area') or {}
        if 'y' in letter_area_geometry:
            letter_top = letter_area_geometry['y']
            letter_hint_y = letter_top + letter_height + 20
            letter_submit_y = max(553, letter_hint_y)
        letter_image_geometry = layout_element(question, 'question_image') or {}
        letter_picture_rect = letter_picture_frame = None
        if picture and letter_image_geometry:
            from layout_images import pygame_image
            try:
                picture, letter_picture_rect, letter_picture_frame = pygame_image(
                    question['_pygame_image'],letter_image_geometry,
                    (480-picture.get_width()//2,letter_group_top,*picture.get_size()))
            except (OSError,ValueError,pygame.error):
                pass
        letter_content_bottom = max(letter_submit_y + 48,
                                    letter_top + letter_height + 40,
                                    (letter_picture_frame.bottom if letter_picture_frame else letter_group_top + (picture.get_height() if picture else 0)) + 30)
        if audio_doc: letter_content_bottom = max(letter_content_bottom, narration_waveform_area.bottom + 40)
    extras_bottom = max((extra['rect']['y'] + extra['rect']['height']
                         for extra in pixel_extras(question.get('layout'))), default=0)
    try:
        pygame.key.start_text_input()
        while True:
            if letter_page:screen=letter_page.begin(scroll_extent(question, max(letter_content_bottom, extras_bottom)))
            elif choice_page_surface:
                lowest = max((g.get('y', 244+(i//3)*140) + g.get('height', 118)
                              for i,g in choice_positions.items()), default=640)
                if audio_doc:
                    lowest = max(lowest, narration_waveform_area.bottom)
                if question_picture_frame:
                    lowest = max(lowest,question_picture_frame.bottom)
                screen = choice_page_surface.begin(max(640, lowest+40, extras_bottom))
            screen.fill(bg);aa_rect(screen,'white',(25,25,910,screen.get_height()-50),border_radius=18)
            # Shared counter badge replaces the former full-width navigation strip.
            if not choice_page_surface:
                draw_question_progress(screen, question)
            # Draw the waveform only on the fixed viewport after scrolling content
            # has been presented. Drawing here would create a second scrolled copy.
            current_page = letter_page or choice_page_surface
            gap_mode = kind in ('sentence_gaps', 'passage_gaps', 'conversation_gaps')
            displayed_scroll = current_page.scroll if current_page else scroll if gap_mode else 0
            displayed_limit = current_page.limit if current_page else max_scroll if gap_mode else 0
            if narration_path and narration_waveform is not None:
                narration_waveform.update()
            elif narration_button is not None:
                if narration_playing and pygame.mixer.get_init() and not pygame.mixer.music.get_busy():
                    narration_playing = False
                aa_rect(screen, (47, 120, 200), narration_button, border_radius=8)
                draw_label('Dừng nghe' if narration_playing else 'Nghe câu hỏi',
                           narration_button.x + 12, narration_button.y + 5, small, 'white')
            prompt_scroll=min(prompt_scroll,max(0,len(prompt_lines)-prompt_visible))
            prompt_block.draw(screen, navy, 0 if letter_page else prompt_scroll, None if letter_page else prompt_visible)
            hits=[];zoom_regions=[];submit=complete_rect(letter_submit_y if letter_page else 553)
            can_submit = (chosen is not None if kind=='image_multi_choice'
                          else all(values.values()) if kind=='picture_missing_letters'
                          else len(assigned)==len(exp) if kind in ('sentence_gaps','passage_gaps','conversation_gaps')
                          else False)
            _ptr=pygame.mouse.get_pos()
            if letter_page:_ptr=(_ptr[0],_ptr[1]+letter_page.scroll)
            if not choice_page_surface and not letter_page:
                draw_complete(screen,submit,font,can_submit,submit.collidepoint(_ptr),pygame.mouse.get_pressed()[0])
            if kind=='image_multi_choice':
                if question_picture is not None:
                    target = question_picture_rect or question_picture.get_rect(topright=(892,119))
                    screen.blit(question_picture, target)
                    zoom_regions.append((draw_zoom_icon(screen,question_picture_frame or target),question_picture_path))
                for i,path in enumerate(items):
                    x=95+(i%3)*280;y=244+(i//3)*140
                    geometry = choice_positions.get(i, {})
                    x = geometry.get('x', x)
                    y = geometry.get('y', y)
                    rect=pygame.Rect(x,y,geometry.get('width',235),geometry.get('height',118))
                    aa_rect(screen,(209,235,255) if chosen==i else (242,246,251),rect,border_radius=10)
                    aa_rect(screen,blue if chosen==i else (195,210,225),rect,2,border_radius=10)
                    im=images.get(path)
                    if im:
                        # Use almost the entire answer card, preserving the
                        # source aspect ratio without pre-shrinking the image.
                        inner = rect.inflate(-10, -10)
                        iw, ih = im.get_size()
                        factor = min(inner.width / max(1, iw), inner.height / max(1, ih))
                        fitted_size = (max(1, round(iw * factor)), max(1, round(ih * factor)))
                        shown = pygame.transform.smoothscale(im, fitted_size) if fitted_size != (iw, ih) else im
                        image_rect = shown.get_rect(center=inner.center)
                        previous_clip = screen.get_clip()
                        screen.set_clip(rect.clip(previous_clip))
                        screen.blit(shown, image_rect)
                        screen.set_clip(previous_clip)
                        if question.get('_choice_images', {}).get(path):
                            # Anchor to the actual image, not an artificial
                            # rectangle: place the icon outside upper-right.
                            zoom_rect = draw_zoom_icon(screen, image_rect)
                            zoom_regions.append((zoom_rect, question['_choice_images'][path]))
                    else:draw_label('Không tìm thấy ảnh',x+20,y+40,small)
                    draw_label(chr(65+i),x+12,y+8,resolve_font(geometry, small, 16))
                    hits.append((rect,('choose',i)))
            elif kind=='picture_missing_letters':
                if picture:
                    picture_rect=letter_picture_rect or picture.get_rect(midtop=(480,letter_group_top))
                    screen.blit(picture,picture_rect)
                    if question.get('_pygame_image'):
                        zoom_regions.append((draw_zoom_icon(screen, letter_picture_frame or picture_rect),question['_pygame_image']))
                elif letter_note:
                    draw_label(letter_note,70,letter_group_top,small)
                for i,x,dy in letter_positions:
                    y=letter_top+dy
                    if i in hidden:
                        geometry = letter_slots[i]
                        rect = pygame.Rect(rectangle(geometry, (x, y, *letter_cell)))
                        button(rect,values.get(i,'_'),(215,238,255) if i==active else (234,240,246),
                               label_font=resolve_font(geometry, letter_font, 17))
                        hits.append((rect,('letter',i)))
                    else:
                        t=letter_text_font.render(letters[i],True,navy)
                        screen.blit(t,t.get_rect(midleft=(x,y+letter_cell[1]//2)))
            else:
                # The gap passage is a dedicated scroll viewport.  Clip both
                # text and media so they cannot paint over fixed controls.
                gap_viewport = pygame.Rect(55, 210, 850, max(1, min(355, gap_area.get('height', 285))))
                old_clip = screen.get_clip()
                screen.set_clip(gap_viewport)
                y=gap_top-scroll;slot_hits=[]
                pending_gap_zoom = None
                if sentence_picture is not None:
                    image_rect=(gap_picture_rect.move(0,-scroll) if gap_picture_rect
                                else sentence_picture.get_rect(topleft=(gap_left,y)))
                    if image_rect.bottom>210 and image_rect.top<495:
                        screen.blit(sentence_picture,image_rect)
                        # Draw icon after restoring clip, outside the picture.
                        pending_gap_zoom = (gap_picture_frame.move(0,-scroll) if gap_picture_frame else image_rect, optional_picture_path)
                    if not gap_image_area:
                        y+=sentence_picture.get_height()+18
                content_bottom=y
                for segments in flat:
                    x=gap_left
                    for typ,value in segments:
                        if typ=='text':
                            # Preserve explicit Enter/newlines in the authored source.
                            # Keep existing word wrapping and slot indices unchanged.
                            for line_no, line_text in enumerate(re.split(r'\r\n|\r|\n', value)):
                                if line_no:
                                    x=gap_left
                                    y+=40
                                for token in re.findall(r'\S+\s*|[ \t]+', line_text):
                                    w=gap_font.size(token)[0]
                                    if x+w>gap_right and x>gap_left:
                                        x=gap_left
                                        y+=40
                                    if -10<y<490:
                                        draw_label(token,x,y,gap_font)
                                    x+=w
                        else:
                            w=115
                            if x+w>gap_right:x=gap_left;y+=40
                            geometry = gap_slot_layouts[value]
                            rect = pygame.Rect(rectangle(geometry, (x, y+scroll-4, w, 34))).move(0, -scroll)
                            if gap_viewport.colliderect(rect):
                                button(rect,choices[assigned[value]] if value in assigned else '........', (211,237,255) if selected_slot==value else (234,240,246),
                                       label_font=resolve_font(geometry, small, 16))
                                hits.append((rect.clip(gap_viewport),('slot',value)))
                            x+=w+5
                    y+=55
                content_bottom=max(y+scroll,
                    (gap_picture_frame.bottom if gap_picture_frame else gap_top + (sentence_picture.get_height() if sentence_picture else 0)) + 18)
                authored = [geometry for geometry in (*gap_slot_layouts, *word_layouts, bank) if geometry]
                saved_bottom = max((g.get('y', 0) + g.get('height', 35) for g in authored), default=0)
                max_scroll=max(0,content_bottom-465, extras_bottom-490, saved_bottom-545)
                scroll=min(scroll,max_scroll)
                screen.set_clip(old_clip)
                if pending_gap_zoom is not None:
                    image_rect, picture_path = pending_gap_zoom
                    icon_rect = draw_zoom_icon(screen, image_rect)
                    if gap_viewport.colliderect(icon_rect) and picture_path:
                        zoom_regions.append((icon_rect, picture_path))
                gap_scrollbar.configure(pygame.Rect(908, 213, 5, 279), gap_viewport.height, scroll, max_scroll, minimum=22)
                if gap_scrollbar.track:
                    aa_rect(screen, (220, 229, 237), gap_scrollbar.track, border_radius=2)
                    aa_rect(screen, (104, 145, 183), gap_scrollbar.thumb, border_radius=2)
                bank_left = min(810, max(0, bank.get('x', 65)))
                bank_right = min(918, bank_left + max(65, bank.get('width', 825)))
                cy = bank.get('y', 505) - scroll if 'y' in bank else 505
                bank_height = max(1, bank.get('height', 35))
                available_choices=[(i,c) for i,c in enumerate(choices) if i not in assigned.values()]
                pages=[];page=[];used=bank_left
                for i,choice in available_choices:
                    w=min(bank_right-bank_left,180,max(65,small.size(str(choice))[0]+24))
                    if used+w>bank_right and page:
                        pages.append(page);page=[];used=bank_left
                    page.append((i,choice,used,w));used+=w+8
                if page:pages.append(page)
                choice_page=min(choice_page,max(0,len(pages)-1))
                if pages:
                    for i,choice,cx,w in pages[choice_page]:
                        geometry = word_layouts[i] or {}
                        rect = pygame.Rect(rectangle(geometry, (cx, cy, w, bank_height)))
                        if 'y' in geometry:
                            rect.y -= scroll
                        button(rect, str(choice), label_font=resolve_font(geometry, bank_font, 16))
                        hits.append((rect, ('choice', i)))
                if len(pages)>1:
                    prev=pygame.Rect(65,547,100,34);nxt=pygame.Rect(178,547,100,34)
                    button(prev,'◀ Trước',enabled=choice_page>0)
                    button(nxt,'Tiếp ▶',enabled=choice_page<len(pages)-1)
                    hits.append((prev,('page',-1)));hits.append((nxt,('page',1)))
                    draw_label(f'Trang đáp án {choice_page+1}/{len(pages)}',295,554,small)
            if not letter_page and not choice_page_surface and extras_bottom:
                draw_extras(screen, question, offset=(0, -scroll))
                draw_question_progress(screen, question)
                draw_complete(screen, submit, font, can_submit, submit.collidepoint(_ptr),
                              pygame.mouse.get_pressed()[0])
            if audio_doc and narration_waveform is not None:
                # Document element: drawn on the scrolling surface, so it moves
                # with the answers. Hover uses content coordinates.
                _m = pygame.mouse.get_pos()
                _sc = letter_page.scroll if letter_page else choice_page_surface.scroll if choice_page_surface else 0
                pygame.draw.rect(screen, (255, 255, 255), narration_waveform_area, border_radius=8)
                narration_waveform_rects = narration_waveform.draw(
                    screen, narration_waveform_area, small, (_m[0], _m[1] + _sc))
            if letter_page:
                letter_page.present(question)
                # The completion control and progress counter belong to the
                # viewport, not to the scrolling question content.
                fixed_submit = complete_rect(553)
                aa_rect(letter_page.display, 'white',
                        (fixed_submit.x-8, fixed_submit.y-7,
                         fixed_submit.width+16, fixed_submit.height+14), border_radius=9)
                draw_complete(letter_page.display, fixed_submit, font, can_submit,
                              fixed_submit.collidepoint(pygame.mouse.get_pos()),
                              pygame.mouse.get_pressed()[0])
                aa_rect(letter_page.display, 'white', (30, 29, 915, 62), border_radius=10)
                draw_question_progress(letter_page.display, question)
                if narration_button is not None and narration_waveform is None:
                    aa_rect(letter_page.display, (47, 120, 200), narration_button, border_radius=8)
                    draw_rich(letter_page.display, small,
                              'Dừng nghe' if narration_playing else 'Nghe câu hỏi',
                              'white', narration_button.x+12, narration_button.y+5)
            elif choice_page_surface:
                choice_page_surface.present(question)
                # Keep progress and completion controls fixed on the viewport.
                aa_rect(choice_page_surface.display, 'white', (30, 29, 915, 62), border_radius=10)
                draw_question_progress(choice_page_surface.display, question)
                if narration_button is not None and narration_waveform is None:
                    aa_rect(choice_page_surface.display, (47, 120, 200), narration_button, border_radius=8)
                    draw_rich(choice_page_surface.display, small,
                              'Dừng nghe' if narration_playing else 'Nghe câu hỏi',
                              'white', narration_button.x + 12, narration_button.y + 5)
                fixed_submit = complete_rect(553)
                aa_rect(choice_page_surface.display, 'white', (fixed_submit.x-8, fixed_submit.y-7, fixed_submit.width+16, fixed_submit.height+14), border_radius=9)
                draw_complete(choice_page_surface.display, fixed_submit, font, can_submit,
                              fixed_submit.collidepoint(pygame.mouse.get_pos()),
                              pygame.mouse.get_pressed()[0])
            if narration_waveform is not None and not audio_doc:
                # The audio player is a viewport overlay, never part of the
                # scrollable question surface. Paint its own opaque backing so
                # scrolled answer cards cannot show through the waveform.
                display = (letter_page.display if letter_page else
                           choice_page_surface.display if choice_page_surface else screen)
                if narration_waveform_area is not None:
                    # Use the saved editor coordinates in viewport space. Do
                    # not add/subtract Page.scroll when drawing the player.
                    audio_box = narration_waveform_area.clip(display.get_rect())
                    if audio_box.width > 0 and audio_box.height > 0:
                        # Paint only the saved player rectangle on the final
                        # viewport, after Page.present() has applied scrolling.
                        # Clearing a hard-coded header strip would overwrite
                        # the user's saved layout and conceal question content.
                        pygame.draw.rect(display, (255, 255, 255), audio_box,
                                         border_radius=8)
                        previous_clip = display.get_clip()
                        display.set_clip(audio_box)
                        try:
                            narration_waveform_rects = narration_waveform.draw(
                                display, narration_waveform_area, small)
                        finally:
                            display.set_clip(previous_clip)
            narration_mini_box = None
            narration_mini_rects = None
            if audio_doc and narration_waveform is not None and not zoom_path:
                _sc = letter_page.scroll if letter_page else choice_page_surface.scroll if choice_page_surface else 0
                if _sc > 0 and (narration_waveform_area.bottom - _sc < 92 or narration_waveform_area.top - _sc > 546):
                    _disp = (letter_page.display if letter_page else
                             choice_page_surface.display if choice_page_surface else screen)
                    narration_mini_box = pygame.Rect(0, 0, 300, 48)
                    narration_mini_box.midbottom = (480, 540)
                    narration_mini_rects = narration_waveform.draw_mini(_disp, narration_mini_box, 0.95, small)
            if zoom_path:
                from exercise_image_zoom import draw as draw_image_zoom
                draw_image_zoom(letter_page.display if letter_page else choice_page_surface.display if choice_page_surface else screen, zoom_path)
            event_scroll = (letter_page.scroll if letter_page else choice_page_surface.scroll if choice_page_surface else 0)
            for event in (letter_page.events(scroll_enabled=not bool(zoom_path)) if letter_page else choice_page_surface.events(scroll_enabled=not bool(zoom_path)) if choice_page_surface else pygame.event.get()):
                if zoom_path:
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        zoom_path = None
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        zoom_path = None
                    elif event.type == pygame.QUIT:
                        zoom_path = None
                    continue
                if gap_mode:
                    consumed, offset = gap_scrollbar.event(event)
                    if consumed:
                        if offset is not None:
                            scroll = offset
                        continue
                if event.type==pygame.QUIT:
                    from pygame_exit_dialog import confirm
                    if confirm(letter_page.display if letter_page else screen, clock, 'Thoát bài tập?', 'Bạn muốn rời bài tập này?'):return None
                    continue
                if event.type==pygame.KEYDOWN:
                    if event.key==pygame.K_ESCAPE:
                        from pygame_exit_dialog import confirm
                        if confirm(letter_page.display if letter_page else screen, clock, 'Thoát bài tập?', 'Bạn muốn rời bài tập này?'):return None
                        continue
                    if kind=='picture_missing_letters':
                        if event.key==pygame.K_BACKSPACE and active is not None:values[active]=''
                        if event.key==pygame.K_RETURN and all(values.values()):return ''.join(values.get(i,c) for i,c in enumerate(letters))
                if event.type==pygame.TEXTINPUT and kind=='picture_missing_letters' and active is not None:
                    if event.text:values[active]=event.text[0];pending=[i for i in sorted(hidden) if i>active];active=pending[0] if pending else active
                if event.type==pygame.MOUSEWHEEL and pygame.mouse.get_pos()[1]<215:
                    prompt_scroll=max(0,min(max(0,len(prompt_lines)-prompt_visible),prompt_scroll-event.y))
                if event.type==pygame.MOUSEWHEEL and kind in ('sentence_gaps','passage_gaps','conversation_gaps'):
                    # Wheel over the passage scrolls its content; the answer
                    # bank and question header keep their own interactions.
                    if 210 <= pygame.mouse.get_pos()[1] < 495:
                        scroll=max(0,min(max_scroll,scroll-event.y*38))
                if event.type==pygame.KEYDOWN and kind in ('sentence_gaps','passage_gaps','conversation_gaps'):
                    if event.key==pygame.K_PAGEUP:
                        scroll=max(0,scroll-240)
                    elif event.key==pygame.K_PAGEDOWN:
                        scroll=min(max_scroll,scroll+240)
                if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                    # Page.events() maps pointer coordinates to the scrolled
                    # content surface. The completion control is intentionally
                    # fixed to the viewport, so check it first in viewport
                    # coordinates; otherwise an underlying option/zoom icon
                    # may intercept the click after scrolling.
                    if choice_page_surface:
                        viewport_pos = (event.pos[0], event.pos[1] - event_scroll)
                        if can_submit and fixed_submit.collidepoint(viewport_pos):
                            return items[chosen]
                        # The progress/header strip is fixed on top of content.
                        # Never select an option hidden behind that strip.
                        if viewport_pos[1] < 92 or fixed_submit.inflate(16,14).collidepoint(viewport_pos):
                            audio_hit = (not audio_doc and narration_waveform is not None and narration_waveform_area is not None
                                         and narration_waveform_area.collidepoint(viewport_pos))
                            if not audio_hit and (narration_button is None or not narration_button.collidepoint(viewport_pos)):
                                continue
                    elif letter_page:
                        viewport_pos = (event.pos[0], event.pos[1] - event_scroll)
                        if can_submit and fixed_submit.collidepoint(viewport_pos):
                            return ''.join(values.get(i,c) for i,c in enumerate(letters))
                        if viewport_pos[1] < 92 or fixed_submit.inflate(16,14).collidepoint(viewport_pos):
                            audio_hit = (not audio_doc and narration_waveform is not None and narration_waveform_area is not None
                                         and narration_waveform_area.collidepoint(viewport_pos))
                            if not audio_hit and (narration_button is None or not narration_button.collidepoint(viewport_pos)):
                                continue
                    else:
                        viewport_pos = event.pos
                    if narration_mini_box is not None and narration_waveform is not None and narration_mini_box.collidepoint(viewport_pos):
                        if narration_mini_rects:
                            _mw, _mp = narration_mini_rects
                            if _mp.inflate(8, 8).collidepoint(viewport_pos):
                                narration_waveform.play()
                            elif _mw.inflate(0, 16).collidepoint(viewport_pos):
                                narration_waveform.seek(max(0.0, min(1.0, (viewport_pos[0]-_mw.x)/max(1, _mw.width)))*narration_waveform.duration)
                        continue
                    audio_click_pos = event.pos if audio_doc else viewport_pos
                    if (narration_waveform is not None and
                            narration_waveform_area is not None and
                            narration_waveform_area.collidepoint(audio_click_pos)):
                        # This fixed overlay owns its entire rectangle, not
                        # only the small control hitboxes. Prevent clicks from
                        # selecting answers that scroll underneath the player.
                        if not narration_waveform_rects:
                            continue
                        wave, play, speed, volume = narration_waveform_rects
                        if any(r.collidepoint(audio_click_pos) for r in (wave, play, speed, volume)) or any(
                                r.collidepoint(audio_click_pos) for r, _ in getattr(narration_waveform, 'speed_menu_rects', [])):
                            menu_hit = next((value for r, value in getattr(narration_waveform, 'speed_menu_rects', [])
                                             if r.collidepoint(audio_click_pos)), None)
                            if menu_hit is not None:
                                narration_waveform.set_speed(menu_hit)
                                narration_waveform.speed_menu_open = False
                            elif play.collidepoint(audio_click_pos):
                                narration_waveform.play()
                            elif wave.collidepoint(audio_click_pos):
                                narration_waveform.seek((audio_click_pos[0]-wave.x)/max(1,wave.width)*narration_waveform.duration)
                            elif volume.collidepoint(audio_click_pos):
                                narration_waveform.set_volume((audio_click_pos[0]-volume.x)/max(1,volume.width))
                            elif speed.collidepoint(audio_click_pos):
                                narration_waveform.speed_menu_open = not getattr(narration_waveform,'speed_menu_open',False)
                        # Consume clicks on the player background too.
                        continue
                    if narration_waveform is None and narration_button is not None and narration_button.collidepoint(viewport_pos):
                        try:
                            if not pygame.mixer.get_init():
                                pygame.mixer.init()
                            if narration_playing:
                                pygame.mixer.music.stop()
                                narration_playing = False
                            else:
                                pygame.mixer.music.load(narration_path)
                                pygame.mixer.music.play()
                                narration_playing = True
                        except (pygame.error, OSError, ValueError):
                            narration_error = True
                            narration_playing = False
                        continue
                    zoom_clicked = next((path for rect,path in zoom_regions if rect.collidepoint(event.pos)), None)
                    if zoom_clicked:
                        zoom_path = zoom_clicked
                        continue
                    if can_submit and not choice_page_surface and not letter_page and submit.collidepoint(event.pos):
                        if kind=='image_multi_choice' and chosen is not None:return items[chosen]
                        if kind=='picture_missing_letters' and all(values.values()):return ''.join(values.get(i,c) for i,c in enumerate(letters))
                        if kind in ('sentence_gaps','passage_gaps','conversation_gaps') and len(assigned)==len(exp):return [choices[assigned[i]] for i in range(len(exp))]
                    for rect,(action,index) in hits:
                        if not rect.collidepoint(event.pos):continue
                        if action=='page':
                            choice_page=max(0,min(len(pages)-1,choice_page+index))
                        elif action=='choose':chosen=None if chosen==index else index
                        elif action=='letter':active=index
                        elif action=='slot':
                            if index in assigned:del assigned[index]
                            selected_slot=index
                        elif action=='choice':
                            if selected_slot in assigned:del assigned[selected_slot]
                            assigned[selected_slot]=index
                            selected_slot=next((i for i in range(len(exp)) if i not in assigned),selected_slot)
                        break
            regions = None
            if question.get('_studio_scene'):
                from studio_live_preview import enclosing, option_rects, text_rect
                current_page = letter_page or choice_page_surface
                gap_mode = kind in ('sentence_gaps', 'passage_gaps', 'conversation_gaps')
                media = narration_waveform_area if narration_waveform is not None or narration_waveform_pending else narration_button
                regions = {'question_text': text_rect(prompt_block), 'audio_player': media}
                fixed = {'_scrollbar'}
                if not audio_doc:
                    fixed.add('audio_player')
                regions['_scrollbar'] = current_page.scrollbar.track if current_page else (
                    gap_scrollbar.track if gap_mode else None)
                if kind == 'image_multi_choice':
                    regions['question_image'] = (question_picture_frame or target) if question_picture is not None else None
                elif kind == 'picture_missing_letters':
                    regions['question_image'] = (letter_picture_frame or picture_rect) if picture else None
                    regions['answer_area'] = (letter_left, letter_top, letter_width, letter_height)
                else:
                    regions['question_image'] = (gap_picture_frame or image_rect.move(0, displayed_scroll)) if sentence_picture is not None else None
                    regions['answer_area'] = (gap_left, gap_top, gap_right-gap_left, gap_viewport.height)
                    region_words = [(rect, index) for rect, (action, index) in hits if action == 'choice']
                    if region_words:
                        regions['word_bank'] = enclosing(rect for rect, _ in region_words).move(0, displayed_scroll if 'y' in bank else 0)
                        if 'y' not in bank:
                            fixed.add('word_bank')
                    fixed.update(('answer_area', 'question_text'))
                for rect, (action, index) in hits:
                    prefix = {'choose':'option', 'letter':'slot', 'slot':'slot', 'choice':'word'}.get(action)
                    if prefix:
                        key = f'{prefix}_{index}'
                        shifts = gap_mode and (action == 'slot' or 'y' in (word_layouts[index] or {}) or 'y' in bank)
                        regions[key] = rect.move(0, displayed_scroll) if shifts else rect
                        if gap_mode and not shifts:
                            fixed.add(key)
            present_frame(question, regions, scroll=displayed_scroll, limit=max_scroll if regions and gap_mode else displayed_limit, fixed=fixed if regions else ())
            if narration_waveform_pending:
                narration_waveform_pending = False
                try:
                    from pygame_waveform import WaveformAudio
                    narration_waveform = WaveformAudio(narration_path)
                except Exception as exc:
                    narration_error = str(exc)
            clock.tick(30)
    finally:
        if narration_waveform is not None:
            narration_waveform.stop()
        if narration_path and pygame.mixer.get_init():
            try:
                pygame.mixer.music.stop()
            except pygame.error:
                pass
        pygame.key.stop_text_input()  # SDL display remains owned by the session worker
