from exercise_gfx import draw_question_progress, present_frame
from extras_render import draw_extras
from question_rich_text import draw as draw_rich, wrap as wrap_rich
"""Optional Pygame exercise renderer. Does not own scoring, data, or navigation."""
import math
import random
import threading
import queue
import time
import wave
import traceback
from pathlib import Path
from functools import lru_cache

from pygame_session_guard import acquire as acquire_sdl_session, release as release_sdl_session, shutdown as _app_shutdown
from new_exercise_runtime import NEW_TYPES
from exercise_buttons import complete_rect, draw_complete
from exercise_gfx import draw_rect as aa_rect

SUPPORTED = set(NEW_TYPES) | {'listening_image_choice', 'choice', 'picture_choice', 'true_false', 'listening_choice', 'order', 'fill', 'listening_fill', 'error', 'matching'}


# A1: bounded caches; SDL display is still closed after every question.
@lru_cache(maxsize=32)
def _cached_font(path, size, bold):
    import pygame
    font = pygame.font.Font(path, size) if path else pygame.font.SysFont('segoeui,arial,dejavusans', size, bold=bold)
    if path:
        font.set_bold(bold)
    return font

@lru_cache(maxsize=32)
def _cached_image(path, mtime_ns, target):
    import pygame
    original = pygame.image.load(path).convert_alpha()
    w, h = original.get_size()
    scale = min(target[0] / max(w, 1), target[1] / max(h, 1), 1.0)
    dims = (max(1, int(w * scale)), max(1, int(h * scale)))
    return pygame.transform.smoothscale(original, dims)

def _image(path, bounds):
    source = Path(path)
    return _cached_image(str(source.resolve()), source.stat().st_mtime_ns, bounds)

# A2.1: diagnostics only. Keep A1 SDL initialization and teardown unchanged.
def _a21_log(message):
    try:
        import os
        location = Path(os.environ.get('LOCALAPPDATA') or Path.home()) / 'TuHoc'
        location.mkdir(parents=True, exist_ok=True)
        with (location / 'pygame_a21.log').open('a', encoding='utf-8') as handle:
            handle.write(time.strftime('%Y-%m-%d %H:%M:%S') + ' ' + str(message) + '\n')
    except (OSError, ValueError):
        pass


_shutdown_requested = threading.Event()

def close(parent=None):
    """Request immediate cancellation without tearing SDL down from Tk's thread."""
    _shutdown_requested.set()
    try:
        import pygame
        if pygame.display.get_init() and pygame.display.get_surface() is not None:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
    except Exception:
        pass


def available():
    try:
        import pygame
        return True
    except ImportError:
        return False


# Keep every SDL window on the same worker thread across consecutive questions.
# Creating a new SDL thread per question can leave Windows with a black window.
_jobs = queue.Queue()
_feedback_jobs = queue.Queue()
_worker_lock = threading.Lock()
_worker_thread = None

# Keep the SDL window open this long after an answer, waiting for the next
# question, so consecutive questions reuse the same window (no close/reopen).
_KEEP_OPEN_SECONDS = None  # Remain open until explicit exit/cancel

def _close_display():
    try:
        import pygame
        if pygame.display.get_init():
            _a21_log('display_quit_begin')
            pygame.display.quit()
            _a21_log('display_quit_ok')
    except Exception:
        pass

def _idle_wait_for_next_job():
    """Keep the window responsive while waiting for the next question.
    Returns the next job, or None if the window should close."""
    import pygame
    while True:
        if _shutdown_requested.is_set() or _app_shutdown.is_set():
            return None
        try:
            feedback = _feedback_jobs.get_nowait()
        except queue.Empty:
            feedback = None
        if feedback is not None:
            try:
                from dragon_feedback import play
                if not play(bool(feedback)):
                    return None
            except Exception:
                traceback.print_exc()
        try:
            return _jobs.get(timeout=0.03)
        except queue.Empty:
            pass
        try:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return None
        except pygame.error:
            return None
    return None

def _show_question_error(question, error):
    """Keep SDL visible on invalid/new questions instead of silently exiting.

    The question is not scored or advanced. Escape/Enter returns to Tk so
    the author can correct the question data.
    """
    try:
        import pygame
        if not pygame.get_init():
            pygame.init()
        if not pygame.display.get_init():
            pygame.display.init()
        screen = pygame.display.get_surface()
        if screen is None:
            screen = pygame.display.set_mode((960, 640))
        pygame.display.set_caption('Tự Học - Lỗi dữ liệu câu hỏi')
        font = pygame.font.SysFont('arial', 24)
        small = pygame.font.SysFont('arial', 19)
        def lines(text, width=86):
            import textwrap
            return textwrap.wrap(str(text), width=width, break_long_words=True)[:6]
        description = '%s: %s' % (type(error).__name__, error)
        clock = pygame.time.Clock()
        while not _shutdown_requested.is_set():
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN)):
                    return
            screen.fill((244, 248, 252))
            screen.blit(font.render('Question could not be opened', True, (168, 44, 44)), (48, 92))
            screen.blit(small.render('Type: ' + str(question.get('type', 'unknown'))[:50], True, (40, 54, 72)), (48, 155))
            for i, line in enumerate(lines(description)):
                screen.blit(small.render(line, True, (70, 78, 92)), (48, 205 + 30 * i))
            screen.blit(small.render('Press Enter or Esc to return to the editor.', True, (45, 88, 135)), (48, 500))
            pygame.display.flip()
            clock.tick(30)
    except Exception:
        traceback.print_exc()


def _exercise_worker():
    pending = None
    while True:
        prepared, results = pending if pending is not None else _jobs.get()
        pending = None
        answer = None
        started = time.monotonic()
        _a21_log('question_start type=' + str(prepared.get('type', 'unknown')))
        try:
            if not (_shutdown_requested.is_set() or _app_shutdown.is_set()):
                answer = _run(prepared)
        except Exception as exc:
            # Keep a newly added, malformed question from silently closing SDL.
            try:
                (Path(__import__('os').environ.get('LOCALAPPDATA',str(Path.home()))) / 'TuHoc').mkdir(parents=True,exist_ok=True)
                with (Path(__import__('os').environ.get('LOCALAPPDATA',str(Path.home()))) / 'TuHoc' / 'pygame_exercises_error.log').open('a', encoding='utf-8') as log:
                    log.write('\n' + time.strftime('%Y-%m-%d %H:%M:%S') + '\n')
                    log.write(traceback.format_exc())
            except OSError:
                traceback.print_exc()
            _show_question_error(prepared, exc)
        finally:
            _a21_log('question_end type=' + str(prepared.get('type', 'unknown')) +
                     ' elapsed_ms=' + str(round((time.monotonic() - started) * 1000)))
            release_sdl_session()
            results.put(answer)
            _jobs.task_done()
        # Answered normally -> keep the window for the next question.
        # Cancelled / error / shutdown -> close it right away.
        if answer is None or _shutdown_requested.is_set() or _app_shutdown.is_set():
            _close_display()
        else:
            pending = _idle_wait_for_next_job()
            if pending is None:
                _close_display()

def launch(parent, question, on_answer, on_cancel=None, *, allow_feedback=True, on_frame=None):
    """Open an independent SDL window and poll results on Tk's main thread.

    Editor previews opt out of feedback grading via allow_feedback.
    """
    if not available() or question.get('type') not in SUPPORTED:
        return False
    # Resolve media on Tk thread before launching the SDL worker.
    prepared = dict(question)
    frames = queue.Queue(maxsize=1) if on_frame is not None else None
    if frames is not None:
        frame_sent = False

        def capture_frame():
            nonlocal frame_sent
            if not frame_sent:
                import pygame
                surface = pygame.display.get_surface()
                frames.put_nowait((surface.get_size(), pygame.image.tobytes(surface, 'RGB')))
                frame_sent = True

        prepared['_studio_frame'] = capture_frame
    # The quiz flow normally supplies _pygame_image; resolve image fields
    # as well for callers that only pass the original question object.
    if not prepared.get('_pygame_image') and prepared.get('image') and hasattr(parent, 'media_file'):
        try:
            image_file = parent.media_file(str(prepared['image']))
            if image_file and Path(image_file).is_file():
                prepared['_pygame_image'] = str(image_file)
        except (OSError, ValueError, TypeError):
            pass
    if prepared.get('audio'):
        relative = str(prepared.get('audio') or '').strip()
        resolved = parent.media_file(relative) if relative and hasattr(parent, 'media_file') else None
        prepared['_resolved_audio'] = str(resolved) if resolved and Path(resolved).is_file() else ''
    if prepared.get('type') in ('image_multi_choice', 'listening_image_choice'):
        resolved = {}
        for opt in prepared.get('image_options', []):
            ref = str(opt.get('image',''))
            try:
                path = parent.media_file(ref) if hasattr(parent,'media_file') else None
                if path and Path(path).is_file(): resolved[ref] = str(path)
            except (OSError, ValueError, TypeError): pass
        prepared['_choice_images'] = resolved
        if prepared.get('type') == 'listening_image_choice':
            question['_choice_images'] = resolved  # de bang tra dap an ve duoc hinh
    if prepared.get('type') == 'matching':
        # Image tokens are stored relative to the current subject's content_library.
        from matching_widget import parse_pairs
        raw_options = prepared.get('options') or []
        if isinstance(raw_options, str): raw_options = [x.strip() for x in raw_options.split('|') if x.strip()]
        raw_pairs = parse_pairs(raw_options)
        resolved = {}
        for token in {part for pair in raw_pairs for part in pair if part.startswith('img:')}:
            relative = token[4:]
            try:
                path = parent.media_file(relative) if hasattr(parent, 'media_file') else None
                if path and Path(path).is_file():
                    resolved[token] = str(path)
            except (OSError, ValueError, TypeError):
                pass
        prepared['_matching_images'] = resolved
    if _app_shutdown.is_set():
        return False
    _shutdown_requested.clear()
    # The SDL window is a separate native window. Make the Tk application
    # modal while it is active so the user cannot edit the underlying screen.
    # Tk's grab affects Tk windows only; pygame still receives mouse/keyboard.
    modal_owner = None
    previous_grab = None
    modal_released = False
    def release_modal():
        nonlocal modal_released
        if modal_released:
            return
        modal_released = True
        try:
            if modal_owner is not None and modal_owner.winfo_exists():
                if modal_owner.grab_current() == modal_owner:
                    modal_owner.grab_release()
                if previous_grab is not None and previous_grab.winfo_exists():
                    previous_grab.grab_set()
        except Exception:
            pass

    # Reserve the shared SDL display before queueing: reject overlaps instead
    # of accumulating pending windows or conflicting with reading screens.
    if not acquire_sdl_session():
        return False
    try:
        modal_owner = parent.winfo_toplevel()
        previous_grab = modal_owner.grab_current()
        # Do not steal a grab from a different modal dialog. The quiz preview
        # may be launched inside a Tk Toplevel that already owns its grab.
        if previous_grab is None or previous_grab == modal_owner:
            modal_owner.grab_set()
            if previous_grab == modal_owner:
                previous_grab = None
        else:
            modal_owner = None
    except Exception:
        modal_owner = None
    # Optional effect, controlled from the existing Settings page.
    settings = getattr(parent, '_display_settings', {}) or {}
    feedback_enabled = allow_feedback and bool(settings.get('dragon_feedback_enabled', False))
    results = queue.Queue(maxsize=1)
    global _worker_thread
    try:
        with _worker_lock:
            if _worker_thread is None or not _worker_thread.is_alive():
                _worker_thread = threading.Thread(target=_exercise_worker, name='TuHocPygame', daemon=True)
                _worker_thread.start()
            _jobs.put_nowait((prepared, results))
    except Exception:
        release_modal()
        release_sdl_session()
        raise
    def poll():
        if frames is not None:
            try:
                size, pixels = frames.get_nowait()
            except queue.Empty:
                pass
            else:
                if parent.winfo_exists():
                    try:
                        on_frame(size, pixels)
                    except Exception:
                        traceback.print_exc()
        try:
            result = results.get_nowait()
        except queue.Empty:
            try:
                if parent.winfo_exists():
                    parent.after(65, poll)
            except Exception:
                pass
            else:
                if not parent.winfo_exists():
                    close(parent)
            return
        # Unlock the editor before displaying results, opening another question,
        # or showing an error dialog. This also handles cancellation.
        release_modal()
        try:
            if parent.winfo_exists():
                if result is None:
                    if on_cancel is not None:
                        on_cancel()
                    # Tk result view has now been built; restore app foreground on Windows.
                    try:
                        parent.deiconify()
                        parent.lift()
                        parent.focus_force()
                        if __import__('sys').platform == 'win32':
                            parent.attributes('-topmost', True)
                            parent.after(120, lambda: parent.attributes('-topmost', False)
                                         if parent.winfo_exists() else None)
                    except Exception:
                        pass
                else:
                    if feedback_enabled and hasattr(parent, '_quiz_correct'):
                        try:
                            is_correct = bool(parent._quiz_correct(question, result))
                            _feedback_jobs.put_nowait(is_correct)
                            # The SDL worker displays the effect while the Tk UI waits.
                            parent.after(1750, lambda: on_answer(result) if parent.winfo_exists() else None)
                        except Exception:
                            traceback.print_exc()
                            on_answer(result)
                    else:
                        on_answer(result)
        except Exception:
            traceback.print_exc()
    def _on_parent_destroy(event):
        if event.widget is modal_owner:
            close(parent)
    if modal_owner is not None:
        try:
            modal_owner.bind("<Destroy>", _on_parent_destroy, add="+")
        except Exception:
            pass
    parent.after(65, poll)
    return True


def _run(question):
    if question.get('type') == 'listening_image_choice':
        from listening_image_choice import run as _run_lic
        return _run_lic(question)
    if question.get('type') in NEW_TYPES:
        from new_exercise_runtime import run
        return run(question)
    import pygame
    if not pygame.get_init():
        pygame.init()
    # Reuse the already-open window when possible (no close/reopen between
    # questions); create it only the first time.
    import os
    if not pygame.display.get_init():
        pygame.display.init()
    _a21_log('legacy_display_open_begin')
    from exercise_gfx import open_exercise_window
    screen = open_exercise_window((960, 640))
    _a21_log('legacy_display_open_ok')
    pygame.event.clear()  # drop clicks left over from the previous question
    pygame.display.set_caption('Tự Học - Bài tập')
    clock = pygame.time.Clock()
    # Prefer a real Unicode font with full Vietnamese glyph coverage.
    # On Windows, Segoe UI supports Vietnamese combining marks reliably.
    font_candidates = [
        Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / 'segoeui.ttf',
        Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / 'arial.ttf',
        Path(__file__).resolve().parent / 'assets' / 'fonts' / 'NotoSans-Regular.ttf',
        Path('/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
    ]
    font_path = next((str(p) for p in font_candidates if p.is_file()), None)
    def make_font(size, bold=False):
        return _cached_font(font_path, size, bold)
    fonts = [make_font(size, bold) for size,bold in ((29,True),(23,False),(22,True),(19,False))]
    navy=(34,51,78); green=(30,146,110); gold=(255,204,89); bg=(240,247,251)
    kind=question.get('type','choice')
    custom_flow = (question.get('layout') or {}).get('version') == 4
    options=question.get('options') or []
    if isinstance(options,str): options=[s.strip() for s in options.split('|') if s.strip()]
    options=list(options)
    if kind in ('choice','picture_choice','listening_choice') and len(options)>8:
        raise ValueError('Maximum 8 options; received %d' % len(options))
    if kind=='true_false' and not options: options=['Đúng','Sai']
    random.shuffle(options)
    # Optional per-question geometry for legacy multiple-choice cards.
    # Keys identify visible slots after the existing option shuffle, not answers.
    legacy_choice_geometry = {}
    legacy_answer_area = None
    if kind in ('choice', 'picture_choice', 'true_false', 'listening_choice'):
        try:
            from question_layout_runtime import element as _layout_element
            legacy_answer_area = _layout_element(question, 'answer_area')
            for _slot in range(min(8, len(options))):
                _geometry = _layout_element(question, 'option_%d' % _slot)
                if _geometry:
                    legacy_choice_geometry[_slot] = _geometry
        except (ImportError, AttributeError, TypeError, ValueError):
            pass  # Old questions retain their original geometry.
    # Text-entry geometry is shared by fill, listening_fill, and error.
    legacy_text_area = None
    if kind in ('fill', 'listening_fill', 'error'):
        try:
            from question_layout_runtime import element as _text_element
            field = 'input_area' if (question.get('layout') or {}).get('version') in (2, 3, 4) else 'answer_area'
            legacy_text_area = _text_element(question, field)
        except (ImportError, AttributeError, TypeError, ValueError):
            pass
    # Order-card geometry is read once; slot indices follow the shuffled display.
    legacy_order_area = None
    legacy_order_geometry = {}
    if kind == 'order':
        try:
            from question_layout_runtime import element as _order_element
            legacy_order_area = _order_element(question, 'answer_area')
            for _slot in range(min(20, len(options))):
                _geom = _order_element(question, 'option_%d' % _slot)
                if _geom:
                    legacy_order_geometry[_slot] = _geom
        except (ImportError, AttributeError, TypeError, ValueError):
            pass
    if kind=='order':
        source=question.get('options') or []
        if isinstance(source,str): source=[x.strip() for x in source.split('|') if x.strip()]
        if not source: source=str(question.get('answer','')).split()  # Legacy word-order questions
        options=list(source)
        if len(options)>20:
            raise ValueError('Maximum 20 order items; received %d' % len(options))
        random.shuffle(options)
    # Matching uses two visible columns: option_0..n-1 on the left,
    # option_n..2n-1 on the shuffled right. Layout keys are display slots.
    legacy_match_area = None
    legacy_match_geometry = {}
    if kind == 'matching':
        try:
            from question_layout_runtime import element as _match_element
            legacy_match_area = _match_element(question, 'answer_area')
            for _slot in range(14):
                _geom = _match_element(question, 'option_%d' % _slot)
                if _geom:
                    legacy_match_geometry[_slot] = _geom
        except (ImportError, AttributeError, TypeError, ValueError):
            pass
    matching_pairs = []
    matching_right = []
    matching_links = {}
    matching_selected = None
    matching_keyboard_side = 0  # 0 = left column, 1 = right column
    matching_images = {}
    if kind == 'matching':
        from matching_widget import parse_pairs
        matching_options = question.get('options') or []
        if isinstance(matching_options, str): matching_options = [x.strip() for x in matching_options.split('|') if x.strip()]
        matching_pairs = parse_pairs(matching_options)
        if not 2 <= len(matching_pairs) <= 7:
            raise ValueError('Matching requires 2-7 valid pairs; received %d' % len(matching_pairs))
        matching_right = list(range(len(matching_pairs)))
        random.shuffle(matching_right)
        for token, image_file in question.get('_matching_images', {}).items():
            try:
                matching_images[token] = _image(image_file, (112, 53))
            except (pygame.error, OSError, ValueError):
                pass
    matching_cells = []
    matching_buttons = {}
    zoom_image_path = None
    typed='';chosen=[];selected_option=None;drag=None;hover=-1;particles=[];answer=None
    # Load once per question, not once per animation frame.
    question_image = None
    from layout_typography import TextBlock, resolve_font
    from question_layout_runtime import element as runtime_element
    image_frame = image_destination = None
    image_path = str(question.get('_pygame_image') or '').strip()
    if image_path and Path(image_path).is_file():
        try:
            question_image = _image(image_path, (420, 220) if kind in ('listening_choice', 'listening_fill') else (600, 230) if kind == 'matching' else (290, 125))
        except (pygame.error, OSError, ValueError):
            question_image = None
    if question_image is not None:
        from layout_images import pygame_image
        image_layout = runtime_element(question, 'question_image')
        if image_layout:
            try:
                question_image, image_destination, image_frame = pygame_image(
                    image_path, image_layout, (66, 165, *question_image.get_size()))
            except (OSError, ValueError, pygame.error):
                pass
    zoom_open = False
    zoom_hit = None
    stop_pressed_until = 0.0
    # Optional question-level audio uses the existing listening player on all
    # legacy exercise types; no audio means no player and no reserved space.
    requires_audio = kind in ('listening_choice', 'listening_fill')
    audio_path = str(question.get('_resolved_audio') or '').strip()
    is_listening = requires_audio or bool(audio_path)
    audio_error = ''
    waveform = None
    waveform_rects = None
    waveform_drag = None
    # Decode waveform only AFTER the first question frame is visible.
    # This avoids a black SDL window while a long audio file is decoded.
    waveform_pending = bool(audio_path)
    # Match the normalized audio_player rectangle saved by Layout Editor.
    def audio_player_rect(default_y):
        fallback = pygame.Rect(53, default_y, 828, 73)
        try:
            from question_layout_runtime import element
            saved = element(question, 'audio_player')
            if saved:
                x = int(saved.get('x', fallback.x))
                y = int(saved.get('y', fallback.y))
                w = int(saved.get('width', fallback.width))
                h = int(saved.get('height', fallback.height))
                return pygame.Rect(max(30, min(920, x)), max(90, y),
                                   max(240, min(w, 900)), max(65, min(h, 220)))
        except (ImportError, TypeError, ValueError, AttributeError):
            pass
        return fallback
    playing = False
    paused = False
    played_seconds = 0.0
    started_at = None
    total_seconds = 0.0
    if audio_path:
        try:
            import mutagen
            total_seconds = float(mutagen.File(audio_path).info.length)
        except (ImportError, AttributeError, OSError, ValueError, TypeError):
            try:
                with wave.open(audio_path, 'rb') as wav:
                    total_seconds = wav.getnframes() / wav.getframerate()
            except (OSError, ValueError, EOFError, wave.Error):
                pass
        # Fallback for MP3/OGG when mutagen is not installed: ask Pygame's
        # decoder for the actual audio duration (not the playback clock).
        if not (math.isfinite(total_seconds) and total_seconds > 0):
            try:
                import pygame
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                total_seconds = float(pygame.mixer.Sound(audio_path).get_length())
            except (pygame.error, OSError, ValueError, TypeError):
                pass
        if not math.isfinite(total_seconds) or total_seconds < 0:
            total_seconds = 0.0
    def stamp(seconds):
        seconds = max(0, int(seconds))
        return f'{seconds//60:02d}:{seconds%60:02d}'
    if requires_audio and not audio_path:
        audio_error = 'Chưa tìm thấy file nghe. Hãy kiểm tra âm thanh trong Quản lý nội dung.'
    def play_audio():
        if waveform is not None:
            waveform.play()
            return
        nonlocal playing, paused, played_seconds, started_at, audio_error
        if not audio_path:
            audio_error = 'Không tìm thấy file âm thanh.'
            return
        try:
            if not pygame.mixer.get_init(): pygame.mixer.init()
            if playing and not paused:
                played_seconds += max(0.0, time.monotonic() - started_at)
                pygame.mixer.music.pause()
                paused = True
            elif paused:
                pygame.mixer.music.unpause()
                started_at = time.monotonic()
                paused = False
            else:
                pygame.mixer.music.stop()
                pygame.mixer.music.load(audio_path)
                pygame.mixer.music.play()
                played_seconds = 0.0
                started_at = time.monotonic()
                playing = True
                paused = False
            audio_error = ''
        except (pygame.error, OSError) as exc:
            playing = paused = False
            audio_error = 'Không phát được âm thanh: ' + str(exc)[:80]
    def stop_audio():
        if waveform is not None:
            waveform.stop()
            return
        nonlocal playing, paused, played_seconds, started_at, stop_pressed_until
        stop_pressed_until = time.monotonic() + 0.15
        if pygame.mixer.get_init(): pygame.mixer.music.stop()
        playing = paused = False
        played_seconds = 0.0
        started_at = None
    def confirm_exit():
        # Modal stays inside SDL: no cross-thread Tk dialog.
        modal = pygame.Rect(245, 225, 470, 185)
        yes = pygame.Rect(360, 335, 105, 43)
        no = pygame.Rect(495, 335, 105, 43)
        while True:
            if _shutdown_requested.is_set() or _app_shutdown.is_set(): return True
            veil = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            veil.fill((17, 31, 48, 170))
            screen.blit(veil, (0, 0))
            rounded(modal, (255, 255, 255), 16)
            draw_text('Thoát bài tập?', fonts[0], navy, 330, 252)
            draw_text('Bạn muốn đóng cửa sổ bài tập?', fonts[3], navy, 300, 295)
            rounded(yes, (42, 150, 115), 9)
            rounded(no, (223, 231, 241), 9)
            draw_text('Thoát', fonts[2], (255,255,255), 378, 343)
            draw_text('Ở lại', fonts[2], navy, 513, 343)
            pygame.display.flip()
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return True
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_n): return False
                    if event.key in (pygame.K_RETURN, pygame.K_y): return True
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if yes.collidepoint(event.pos): return True
                    if no.collidepoint(event.pos): return False
            clock.tick(30)

    # Scroll the entire question AND its answer area vertically. Never scroll horizontally.
    content_scroll = 0
    scrollbar_drag_offset = None  # Pointer offset inside the viewport scrollbar thumb.
    def wrapped_lines(value, font, max_width):
        lines = []
        for paragraph in str(value).split('\n'):
            line = ''
            for word in paragraph.split():
                candidate = (line + ' ' + word).strip()
                if font.size(candidate)[0] <= max_width:
                    line = candidate
                else:
                    if line:
                        lines.append(line)
                        line = ''
                    for char in word:
                        if line and font.size(line + char)[0] > max_width:
                            lines.append(line)
                            line = ''
                        line += char
            lines.append(line)
        return lines or ['']
    def draw_text(text,font,color,x,y,max_width=840):
        cy = y
        for line in (wrap_rich(text,font,max_width) if '**' in str(text) else wrapped_lines(text, font, max_width)):
            draw_rich(screen,font,line,color,x,cy)
            cy += font.get_height()+7
        return cy-7
    def rounded(rect,color,radius=15):aa_rect(screen,color,rect,border_radius=radius)
    def _match_geom(ref):
        """Bo cuc bai noi. Khong anh = nhu cu; co anh = day cac the xuong va keo nut len sat the cuoi."""
        n = max(len(matching_pairs), 1)
        base_top = max(186, min(ref + 30, 245))
        gap = min(71, (515 - base_top) / n)
        top, btn_y = base_top, 545
        if question_image is not None:
            top = max(base_top, (image_frame.bottom if image_frame else max(165, ref + 8) + question_image.get_height()) + 16)
            btn_y = int(top + (n - 1) * gap + min(62, gap - 7) + 18)
        return base_top, top, gap, btn_y
    prompt_geometry = runtime_element(question,'question_text') or {}
    prompt_x = prompt_geometry.get('x', 60)
    prompt_y = prompt_geometry.get('y', 123)
    prompt_width = max(1,prompt_geometry.get('width',825))
    prompt_font = resolve_font(prompt_geometry, fonts[1], 23)
    input_font = resolve_font(legacy_text_area, fonts[0], 29)
    choice_fonts = {i: resolve_font({**(legacy_answer_area or {}), **(legacy_choice_geometry.get(i) or {})},
                                    fonts[2], 22) for i in range(len(options[:8]))}
    order_preview = runtime_element(question, 'answer_preview') if kind == 'order' else None
    prompt = question.get('prompt','Hoàn thành bài tập')
    prompt_block = TextBlock(prompt, prompt_geometry, fonts[1], 23,
                             (prompt_x, prompt_y, prompt_width), prompt_font.get_linesize()+7) if prompt_geometry else None
    mini_fade = 0.0      # 0..1 fade of the floating mini player
    mini_rects = None
    try:
        pygame.key.start_text_input()
        while True:
            display_screen = screen
            prompt_lines = (wrap_rich(prompt,prompt_font,prompt_width)
                            if prompt_geometry and '**' in str(prompt)
                            else wrapped_lines(prompt,prompt_font,prompt_width))
            prompt_end = prompt_y + len(prompt_lines) * (prompt_font.get_height()+7) - 7
            lis_img = (question_image.get_height() + 12) if (question_image is not None and is_listening and not image_frame) else 0
            answer_top = max(210, prompt_end + (105 if (waveform is not None or waveform_pending) else 85 if is_listening else 24)) + lis_img
            if image_frame:
                answer_top = max(answer_top, image_frame.bottom + 12)
            elif question_image is not None and not is_listening:
                answer_top = max(answer_top, max(165, prompt_end+8) + question_image.get_height()+12)
            # Every question type needs a defined scroll extent before any
            # optional per-answer geometry extends it. Previously the choice
            # branch read content_bottom before assignment when a saved layout
            # was present (notably listening_choice).
            content_bottom = max(620, answer_top + 190)
            if kind in ('choice','picture_choice','true_false','listening_choice'):
                # Measure with the same font and width used to draw the answers.
                # Each hit box includes every wrapped line, including long tokens.
                choice_layout = []
                choice_y = answer_top
                for i, opt in enumerate(options[:8]):
                    lines = wrapped_lines(f'{chr(65+i)}. {opt}', fonts[2], 785)
                    text_height = len(lines) * (fonts[2].get_height()+7) - 7
                    card_height = max(47, text_height + 20)
                    choice_layout.append((choice_y, card_height, lines))
                    choice_y += card_height + 7
                # Apply saved answer-area and per-slot positions to both
                # rendering and hitboxes; keep legacy dimensions by default.
                if legacy_answer_area or legacy_choice_geometry:
                    area = legacy_answer_area or {}
                    area_x = int(area.get('x', 66))
                    area_y = int(area.get('y', answer_top))
                    area_w = max(80, int(area.get('width', 828)))
                    updated = []
                    cursor = area_y
                    spacing = 7
                    if custom_flow and len(choice_layout) > 1 and 'height' in area:
                        spacing = max(7, (area['height'] - sum(h for _, h, _ in choice_layout)) // (len(choice_layout)-1))
                    for i, (old_y, old_h, _lines) in enumerate(choice_layout):
                        geom = legacy_choice_geometry.get(i) or {}
                        card_x = int(geom.get('x', area_x))
                        card_y = int(geom.get('y', cursor))
                        card_w = max(1 if custom_flow else 80, int(geom.get('width', area_w)))
                        card_font_width = max(40, card_w - 36)
                        card_font = choice_fonts.get(i, fonts[2])
                        card_lines = wrapped_lines(f'{chr(65+i)}. {options[i]}', card_font, card_font_width)
                        text_h = len(card_lines) * (card_font.get_height()+7) - 7
                        natural_height = max(47, old_h, text_h+20)
                        if custom_flow and 'height' in geom:
                            card_h = max(1, geom['height'])
                        else:
                            card_h = max(47, int(geom.get('height', natural_height)), text_h+20)
                        updated.append((card_x, card_y, card_w, card_h, card_lines))
                        cursor = max(cursor, card_y + card_h + spacing)
                    choice_layout = updated
                    content_bottom = max(content_bottom, cursor + 92)
                else:
                    choice_layout = [(66, y, 828, h, lines) for y, h, lines in choice_layout]
                # Include all cards even without a custom layout. This keeps
                # long or newly added choices reachable by scrolling.
                if choice_layout:
                    content_bottom = max(content_bottom, max(y + h for _, y, _, h, _ in choice_layout) + 92)
            elif kind == 'order':
                # Long phrase/sentence cards use two columns and wrapped text.
                order_cols = 2 if any(len(str(v)) > 16 for v in options) else 4
                order_rows = (len(options) + order_cols - 1) // order_cols
                content_bottom = answer_top + 175 + order_rows * (92 if order_cols == 2 else 62) + 85
                if legacy_order_area or legacy_order_geometry:
                    area = legacy_order_area or {}
                    base_x = int(area.get('x', 66))
                    base_y = int(area.get('y', answer_top + 110))
                    base_w = max(80, int(area.get('width', 828)))
                    columns = order_cols
                    default_w = max(80, (base_w - (columns - 1) * 13) // columns)
                    default_h = 84 if columns == 2 else 54
                    for i in range(min(20, len(options))):
                        geom = legacy_order_geometry.get(i) or {}
                        x = int(geom.get('x', base_x + (i % columns) * (default_w + 13)))
                        yy = int(geom.get('y', base_y + (i // columns) * (default_h + 9)))
                        h = max(30, int(geom.get('height', default_h)))
                        content_bottom = max(content_bottom, yy + h + 130)
            elif kind == 'matching':
                content_bottom = max(620, prompt_end+40)
                content_bottom = max(620, _match_geom(prompt_end)[3] + 75)
                if legacy_match_area or legacy_match_geometry:
                    _base, _top, _gap, _button = _match_geom(prompt_end)
                    _n = len(matching_pairs)
                    _area = legacy_match_area or {}
                    _ax = int(_area.get('x', 75))
                    _ay = int(_area.get('y', _top))
                    _aw = max(200, int(_area.get('width', 807)))
                    for _side in (0, 1):
                        for _row in range(_n):
                            _slot = _row + (_n if _side else 0)
                            _g = legacy_match_geometry.get(_slot) or {}
                            _yy = int(_g.get('y', _ay + _row * _gap))
                            _hh = max(30, int(_g.get('height', min(62, _gap-7))))
                            content_bottom = max(content_bottom, _yy + _hh + 105)
            else:
                content_bottom = answer_top + 190
                if kind in ('fill', 'listening_fill', 'error') and legacy_text_area:
                    _ty = int(legacy_text_area.get('y', answer_top + 60))
                    _th = max(40, int(legacy_text_area.get('height', 66)))
                    content_bottom = max(content_bottom, _ty + _th + 85)
            # Respect lower custom layout elements without altering legacy
            # answer geometry or grading. The helper ignores locked controls.
            try:
                from layout_scroll_extent import content_bottom as _layout_bottom
                content_bottom = _layout_bottom(question, content_bottom)
            except (ImportError, TypeError, ValueError, AttributeError):
                pass  # Original application remains usable without layout support.
            if is_listening:
                _audio_bounds = audio_player_rect(max(177, prompt_end + 10))
                content_bottom = max(content_bottom, _audio_bounds.bottom + 100)
            if order_preview:
                content_bottom = max(content_bottom, order_preview.get('y', 0) + order_preview.get('height', 60) + 80)
            virtual_height = max(640, int(content_bottom + 35))
            max_content_scroll = max(0, virtual_height - 640)
            content_scroll = max(0, min(content_scroll, max_content_scroll))
            mouse_real = pygame.mouse.get_pos()
            mouse = (mouse_real[0], mouse_real[1] + content_scroll)
            screen = pygame.Surface((960, virtual_height))
            screen.fill(bg)
            rounded(pygame.Rect(28,25,904,virtual_height-50),(255,255,255),23)
            # Shared counter badge replaces the former full-width navigation strip.
            draw_question_progress(screen, question)
            # Full prompt is rendered with word wrapping; answer controls follow it.
            # The complete content is scrolled together in the vertical direction.
            if prompt_block is None:
                prompt_bottom = draw_text(prompt,prompt_font,navy,prompt_x,prompt_y,prompt_width)
            else:
                prompt_block.draw(screen, navy)
                prompt_bottom = prompt_block.bottom
            if waveform is not None:
                waveform.update()
            if is_listening and waveform is None and playing and not paused and not pygame.mixer.music.get_busy():
                playing = False
                played_seconds = total_seconds or played_seconds
                started_at = None
            elapsed = played_seconds + (max(0, time.monotonic()-started_at) if playing and not paused and started_at else 0)
            if total_seconds: elapsed = min(elapsed, total_seconds)
            _audio_player_bounds = audio_player_rect(max(177, prompt_bottom+10)) if is_listening else None
            play_rect = pygame.Rect(_audio_player_bounds.x + 13, _audio_player_bounds.y, 122, 36) if is_listening else None
            stop_rect = pygame.Rect(play_rect.right + 11, play_rect.y, 80, 36) if play_rect else None
            if play_rect and waveform is None:
                depth = 2 if playing and not paused else 5
                rounded(play_rect.move(0,depth), (26,95,120), 9)
                rounded(play_rect, (43,155,177) if playing and not paused else (64,188,209), 9)
                label = 'Pause' if playing and not paused else ('Playing' if paused else 'Play')
                screen.blit(fonts[3].render(label,True,(255,255,255)), (play_rect.x+35,play_rect.y+8))
                if playing and not paused:
                    aa_rect(screen,(255,255,255),(play_rect.x+12,play_rect.y+10,5,16))
                    aa_rect(screen,(255,255,255),(play_rect.x+21,play_rect.y+10,5,16))
                else:
                    pygame.draw.polygon(screen,(255,255,255),[(play_rect.x+12,play_rect.y+9),(play_rect.x+12,play_rect.y+27),(play_rect.x+26,play_rect.y+18)])
                stop_down = time.monotonic() < stop_pressed_until or (stop_rect.collidepoint(mouse) and pygame.mouse.get_pressed()[0])
                stop_depth = 1 if stop_down else 5
                rounded(stop_rect.move(0,5), (115,52,61), 9)
                rounded(stop_rect.move(0,stop_depth-1 if stop_down else 0), (183,63,75) if stop_down else (206,78,89), 9)
                screen.blit(fonts[3].render('Stop',True,(255,255,255)),(stop_rect.x+16,stop_rect.y+8+(stop_depth-1 if stop_down else 0)))
                draw_text(stamp(elapsed)+' / '+(stamp(total_seconds) if total_seconds else '--:--'),fonts[3],navy,300,play_rect.y+6,200)
                if audio_error: draw_text(audio_error,fonts[3],(174,58,58),515,play_rect.y+6,370)
            if waveform_pending and play_rect is not None:
                loading_rect = _audio_player_bounds
                aa_rect(screen, (255,255,255), loading_rect, border_radius=10)
                aa_rect(screen, (166,184,218), loading_rect, 2, border_radius=10)
                screen.blit(fonts[3].render('Dang tai am thanh...', True, navy), (loading_rect.x+20, loading_rect.centery-10))
            if waveform is not None and play_rect is not None:
                waveform_rects = waveform.draw(screen, _audio_player_bounds,fonts[3])
                if audio_error: draw_text(audio_error,fonts[3],(174,58,58),65,play_rect.y+114,800)
            y=max(210, prompt_bottom + (105 if (waveform is not None or waveform_pending) else 85 if is_listening else 24)) + lis_img
            if image_frame:
                screen.blit(question_image, image_destination)
                y = max(y, image_frame.bottom + 12)
            elif question_image is not None and not is_listening:
                image_y = max(165, prompt_bottom + 8)
                image_x = (960 - question_image.get_width()) // 2 if kind == 'matching' else 66
                screen.blit(question_image, (image_x, image_y))
                y = max(y, image_y + question_image.get_height() + 12)
            zoom_hit = None
            matching_zoom_hits = []
            if question_image is not None:
                if is_listening and not image_frame:
                    # Listening: image goes BELOW the player; no gap when there is none.
                    image_y = y - lis_img
                    screen.blit(question_image, (66, image_y))
                from exercise_image_zoom import draw_zoom_icon
                zoom_hit = draw_zoom_icon(screen, image_frame or pygame.Rect(
                    (960 - question_image.get_width()) // 2 if kind == 'matching' else 66,
                    image_y, *question_image.get_size()))
            cells=[]
            matching_cells = []
            matching_buttons = {}
            hover_caption = None
            if kind == 'matching':
                n = len(matching_pairs)
                base_top, top, gap, match_btn_y = _match_geom(prompt_bottom)
                match_dy = match_btn_y - 545
                card_h = min(62, gap-7)
                left_x, right_x, card_w = 75, 650, 232
                # Use exactly the same rectangles for drawing, links, hover,
                # and mouse hit testing. No layout means original geometry.
                match_rects = {}
                area = legacy_match_area or {}
                area_x = int(area.get('x', left_x))
                area_y = int(area.get('y', top))
                area_w = max(200, int(area.get('width', right_x + card_w - left_x)))
                if custom_flow and n and 'height' in area:
                    gap = max(15, area['height'] / n)
                    card_h = max(15, min(62, gap-5))
                for side in (0, 1):
                    for row in range(n):
                        slot = row + (n if side else 0)
                        geom = legacy_match_geometry.get(slot) or {}
                        default_x = (area_x if side == 0 else area_x + area_w - card_w) if (legacy_match_area or legacy_match_geometry) else (left_x if side == 0 else right_x)
                        default_y = (area_y if (legacy_match_area or legacy_match_geometry) else top) + row * gap
                        match_rects[(side, row)] = pygame.Rect(
                            int(geom.get('x', default_x)), int(geom.get('y', default_y)),
                            max(80, int(geom.get('width', card_w))),
                            max(1 if custom_flow else 30, int(geom.get('height', card_h))))
                match_bottom = max((rect.bottom for rect in match_rects.values()), default=top)
                centers = [match_rects[(0, i)].centery for i in range(n)]
                # Keep completed links subtle; emphasize only the pair being inspected.
                hovered_pair = None
                hovered_side = None
                for side in (0, 1):
                    for row in range(n):
                        candidate = match_rects[(side, row)]
                        if candidate.collidepoint(mouse):
                            hovered_pair = row if side == 0 else matching_right[row]
                            hovered_side = side
                for a,b in matching_links.items():
                    target_row = matching_right.index(b)
                    start = (match_rects[(0, a)].right + 7, match_rects[(0, a)].centery)
                    end = (match_rects[(1, target_row)].left - 7, match_rects[(1, target_row)].centery)
                    focused = (hovered_pair == a if hovered_side == 0 else hovered_pair == b if hovered_side == 1 else False) or matching_selected == a
                    color = (31, 116, 174) if focused else (192, 210, 205)
                    pygame.draw.line(screen, color, start, end, 4 if focused else 2)
                    if focused:
                        pygame.draw.circle(screen, color, start, 5)
                        pygame.draw.circle(screen, color, end, 5)
                for side in (0,1):
                    for row in range(n):
                        pair_idx = row if side==0 else matching_right[row]
                        token = matching_pairs[pair_idx][side]
                        rect = match_rects[(side, row)]
                        matching_cells.append((rect,side,pair_idx))
                        active = side==0 and matching_selected==pair_idx
                        linked = pair_idx in matching_links if side==0 else pair_idx in matching_links.values()
                        pressed = rect.collidepoint(mouse) and pygame.mouse.get_pressed()[0]
                        rounded(rect.move(0,4),(171,195,185),10)
                        rounded(rect.move(0,2 if pressed else 0),(217,238,255) if active else (207,236,224) if rect.collidepoint(mouse) else (222,243,232) if linked else (245,248,247),10)
                        aa_rect(screen,(58,145,105) if active else (195,216,205),rect,2,border_radius=10)
                        # Numbered pair badges help identify connections without tracing crossing lines.
                        if linked:
                            linked_left = pair_idx if side == 0 else next(
                                (left for left, right in matching_links.items() if right == pair_idx), None)
                            if linked_left is not None:
                                badge = pygame.Rect(rect.right - 12 if side == 0 else rect.left - 12, rect.centery - 11, 24, 22)
                                aa_rect(screen, (42, 133, 99), badge, border_radius=6)
                                number = fonts[3].render(str(linked_left + 1), True, (255, 255, 255))
                                screen.blit(number, number.get_rect(center=badge.center))
                        picture = matching_images.get(token)
                        if picture is not None:
                            pic_rect=picture.get_rect(center=rect.center)
                            screen.blit(picture,pic_rect)
                            match_path=question.get('_matching_images',{}).get(token)
                            if match_path:
                                matching_zoom_hits.append((draw_zoom_icon(screen,pic_rect),match_path))
                        else:
                            caption = '[Không tìm thấy ảnh]' if token.startswith('img:') else token
                            width_limit = max(40, rect.width-28)
                            label_font = fonts[2] if fonts[2].size(caption)[0] <= width_limit else fonts[3]
                            label_font = resolve_font({**(legacy_match_area or {}), **(legacy_match_geometry.get(row + side * n) or {})}, label_font,
                                                      22 if label_font is fonts[2] else 19)
                            # Show up to two wrapped lines; hover shows the complete answer.
                            lines = wrapped_lines(caption, label_font, width_limit)
                            if len(lines) > 2:
                                lines = lines[:2]
                                while lines[-1] and label_font.size(lines[-1] + '…')[0] > width_limit:
                                    lines[-1] = lines[-1][:-1]
                                lines[-1] += '…'
                            line_height = label_font.get_height() + 2
                            for line_no, line in enumerate(lines):
                                surface = label_font.render(line, True, navy)
                                center_y = rect.centery + (line_no - (len(lines)-1)/2)*line_height
                                screen.blit(surface, surface.get_rect(center=(rect.centerx, int(center_y))))
                            if rect.collidepoint(mouse) and (len(wrapped_lines(caption,label_font,width_limit)) > 2):
                                hover_caption = caption
                match_buttons_y = max(545 + match_dy, match_bottom + 18)
                reset_rect=pygame.Rect(75,match_buttons_y,165,48)
                check_rect=complete_rect(match_buttons_y)
                matching_buttons={'reset':reset_rect,'check':check_rect}
                rounded(reset_rect,(207,229,219) if reset_rect.collidepoint(mouse) else (225,235,230),10)
                matching_ready = len(matching_links) == len(matching_pairs)
                # Completion is drawn on the viewport after the scrollable page.
                # Keep the content-space rect for legacy layout compatibility.
                draw_text('Làm lại',fonts[3],navy,121,match_buttons_y+12,125)
                if matching_selected is not None:
                    draw_text('', fonts[3], (31, 116, 174), 335, 517, 300)
                if hover_caption:
                    # Complete text in a dedicated panel, wrapping instead of clipping.
                    tip_font = fonts[3]
                    tip_lines = wrapped_lines(hover_caption, tip_font, 780)
                    tip_h = min(150, 14 + len(tip_lines) * (tip_font.get_height()+3))
                    tip_y = max(105, min(520+match_dy-tip_h, int(mouse[1])-tip_h-12))
                    tip = pygame.Rect(85, tip_y, 790, tip_h)
                    rounded(tip, (255, 252, 229), 9)
                    aa_rect(screen, (170, 146, 84), tip, 1, border_radius=9)
                    for line_no, line in enumerate(tip_lines):
                        line_y = tip_y + 7 + line_no * (tip_font.get_height()+3)
                        if line_y + tip_font.get_height() <= tip.bottom:
                            screen.blit(tip_font.render(line, True, navy), (tip.x+9, line_y))
            elif kind in ('choice' ,'picture_choice','true_false','listening_choice'):
                for i,opt in enumerate(options[:8]):
                    card_x, card_y, card_width, card_height, lines = choice_layout[i]
                    r=pygame.Rect(card_x,card_y,card_width,card_height);cells.append((r,i))
                    selected = selected_option == i
                    rounded(r,(193,235,215) if selected else (222,246,237) if r.collidepoint(mouse) else (235,241,248),10)
                    if selected:
                        aa_rect(screen, green, r, 2, border_radius=10)
                    card_font = choice_fonts.get(i, fonts[2])
                    clip = screen.get_clip()
                    if custom_flow and i in legacy_choice_geometry:
                        screen.set_clip(clip.clip(r))
                    try:
                        for line_no, line in enumerate(lines):
                            screen.blit(card_font.render(line,True,navy),
                                        (r.x+18,r.y+10+line_no*(card_font.get_height()+7)))
                    finally:
                        screen.set_clip(clip)
                # The choice submit control is rendered on the viewport below.
                # Do not add a scrolling hitbox for the same control.
                confirm_ready = selected_option is not None
            elif kind=='order':
                draw_text('',fonts[3],green,67,y)
                # Display the assembled text in a wrapping panel; long sentences
                # must not be clipped or overlap the available choices.
                chosen_text = ' '.join(str(options[j]) for j in chosen)
                preview_geometry = order_preview or {}
                preview_font = resolve_font(preview_geometry, fonts[3], 19)
                preview_width = preview_geometry.get('width', 828)
                preview_lines = wrapped_lines(chosen_text or 'Chưa chọn thẻ nào', preview_font, max(1, preview_width-48))
                preview_height = max(60, 20 + len(preview_lines)*(preview_font.get_height()+5))
                preview_rect = pygame.Rect(preview_geometry.get('x', 66), preview_geometry.get('y', y+35),
                                           preview_width, preview_geometry.get('height', preview_height))
                rounded(preview_rect,(235,245,252),10)
                for line_idx,line_text in enumerate(preview_lines):
                    screen.blit(preview_font.render(line_text,True,navy),(preview_rect.x+12,preview_rect.y+9+line_idx*(preview_font.get_height()+5)))
                cards_y = preview_rect.bottom+16
                cols = 2 if any(len(str(v))>16 for v in options) else 4
                card_w = 404 if cols==2 else 197
                card_h = 84 if cols==2 else 54
                gap_x = 16 if cols==2 else 13
                gap_y = 9
                if custom_flow and legacy_order_area and 'height' in legacy_order_area:
                    rows = max(1, (len(options)+cols-1)//cols)
                    card_h = max(15, (legacy_order_area['height'] - gap_y*(rows-1))//rows)
                order_card_bottom = cards_y
                for i,opt in enumerate(options[:20]):
                    col=i%cols;row=i//cols
                    if legacy_order_area or legacy_order_geometry:
                        area = legacy_order_area or {}
                        area_x = int(area.get('x', 66))
                        area_y = int(area.get('y', cards_y))
                        area_w = max(80, int(area.get('width', 828)))
                        slot_w = max(80, (area_w - (cols-1)*gap_x)//cols)
                        geom = legacy_order_geometry.get(i) or {}
                        r=pygame.Rect(int(geom.get('x', area_x+col*(slot_w+gap_x))),
                                      int(geom.get('y', area_y+row*(card_h+gap_y))),
                                      max(80,int(geom.get('width', slot_w))),
                                      max(1 if custom_flow else 30,int(geom.get('height', card_h))))
                    else:
                        r=pygame.Rect(66+col*(card_w+gap_x),cards_y+row*(card_h+gap_y),card_w,card_h)
                    order_card_bottom = max(order_card_bottom, r.bottom)
                    cells.append((r,i))
                    rounded(r,(224,236,242) if i in chosen else (255,235,177) if r.collidepoint(mouse) else (227,242,253),10)
                    if i in chosen:aa_rect(screen,green,r,2,border_radius=10)
                    label_font = resolve_font({**(legacy_order_area or {}), **(legacy_order_geometry.get(i) or {})}, fonts[3], 19)
                    label_lines=wrapped_lines(str(opt),label_font,max(40,r.width-25))
                    max_lines=3 if cols==2 else 2
                    for line_no,label_line in enumerate(label_lines[:max_lines]):
                        screen.blit(label_font.render(label_line,True,navy),(r.x+12,r.y+7+line_no*(label_font.get_height()+3)))
                buttons_y=max(cards_y+((len(options)+cols-1)//cols)*(card_h+gap_y), order_card_bottom+gap_y)+15
                r=pygame.Rect(66,buttons_y,185,48);cells.append((r,'reset'))
                rounded(r,(209,223,217) if r.collidepoint(mouse) else (230,233,238),10)
                draw_text('Xóa',fonts[2],navy,r.x+53,r.y+9)
                # Submit is a fixed viewport control; do not add a scrollable hitbox.
                ready=len(chosen)==len(options)
            else:
                draw_text('',fonts[3],green,67,y)
                if kind in ('fill', 'listening_fill', 'error') and legacy_text_area:
                    _a = legacy_text_area
                    r = pygame.Rect(int(_a.get('x', 66)), int(_a.get('y', y+60)),
                                    max(100, int(_a.get('width', 828))),
                                    max(40, int(_a.get('height', 66))))
                else:
                    r = pygame.Rect(66,y+60,828,66)
                rounded(r,(235,241,248))
                # Clip long user input to the visible box without changing its value.
                _text_surface = input_font.render(typed+'|', True, navy)
                _available = max(1, r.width-30)
                _visible_text = _text_surface.subsurface(
                    pygame.Rect(max(0, _text_surface.get_width()-_available), 0,
                                min(_available, _text_surface.get_width()), _text_surface.get_height()))
                screen.blit(_visible_text, (r.x+15, r.y+max(0,(r.height-_visible_text.get_height())//2)))
                confirm_ready = bool(typed.strip())
                if kind not in ('fill', 'listening_fill', 'error'):
                    confirm_rect = complete_rect(y+140)
                    draw_complete(screen, confirm_rect, fonts[2], confirm_ready, confirm_rect.collidepoint(mouse), pygame.mouse.get_pressed()[0])
                    cells.append((confirm_rect,'confirm_text'))
            draw_extras(screen, question)
            if (question.get('layout') or {}).get('extras') and not content_scroll:
                draw_question_progress(screen, question)
            # Show a vertical slice of the tall content; horizontal position never moves.
            display_screen.blit(screen, (0, 0), (0, content_scroll, 960, 640))
            scrollbar_track = None
            scrollbar_thumb = None
            if max_content_scroll:
                scrollbar_track = pygame.Rect(938, 110, 7, 455)
                aa_rect(display_screen, (220,229,236), scrollbar_track, border_radius=3)
                thumb_h = min(scrollbar_track.height, max(35, int(scrollbar_track.height * 640 / virtual_height)))
                thumb_y = scrollbar_track.y + int((scrollbar_track.height-thumb_h)*content_scroll/max_content_scroll)
                scrollbar_thumb = pygame.Rect(scrollbar_track.x, thumb_y, 7, thumb_h)
                aa_rect(display_screen, (80,135,170), scrollbar_thumb, border_radius=3)
            else:
                scrollbar_drag_offset = None
            # The question counter belongs to the viewport, not the scrolled
            # question surface. A small opaque header prevents text bleed-through.
            if content_scroll:
                pygame.draw.rect(display_screen, bg, (28, 0, 904, 90))
                draw_question_progress(display_screen, question)
            # Choice-family completion is anchored to the viewport, not the tall
            # question surface. Opaque footer prevents underlying answer cards
            # from showing through and from receiving accidental clicks.
            fixed_choice_submit = kind in ('choice', 'picture_choice', 'true_false', 'listening_choice')
            fixed_sequence_submit = kind in ('matching', 'order')
            fixed_text_submit = kind in ('fill', 'listening_fill', 'error')
            fixed_submit_rect = complete_rect(577) if fixed_choice_submit else None
            if fixed_choice_submit:
                pygame.draw.rect(display_screen, bg, (28, 565, 904, 75))
                draw_complete(display_screen, fixed_submit_rect, fonts[2],
                              selected_option is not None,
                              fixed_submit_rect.collidepoint(mouse_real),
                              pygame.mouse.get_pressed()[0])
            if fixed_sequence_submit:
                fixed_sequence_rect = complete_rect(577)
                pygame.draw.rect(display_screen, bg, (28, 565, 904, 75))
                sequence_ready = (len(matching_links) == len(matching_pairs) if kind == 'matching'
                                  else len(chosen) == len(options))
                draw_complete(display_screen, fixed_sequence_rect, fonts[2], sequence_ready,
                              fixed_sequence_rect.collidepoint(mouse_real), pygame.mouse.get_pressed()[0])
            if fixed_text_submit:
                fixed_text_rect = complete_rect(577)
                pygame.draw.rect(display_screen, bg, (28, 565, 904, 75))
                draw_complete(display_screen, fixed_text_rect, fonts[2],
                              bool(typed.strip()), fixed_text_rect.collidepoint(mouse_real),
                              pygame.mouse.get_pressed()[0])
            screen = display_screen
            # Floating mini player: appears when the real waveform has scrolled off-screen.
            mini_target = 0.0
            if waveform is not None and play_rect is not None and is_listening and not zoom_open:
                if play_rect.y + 73 - content_scroll < 24:
                    mini_target = 1.0
            mini_fade += (mini_target - mini_fade) * 0.35
            if abs(mini_target - mini_fade) < 0.03:
                mini_fade = mini_target
            mini_rects = None
            if waveform is not None and mini_fade > 0:
                mini_rect = pygame.Rect(0, 0, 300, 48)
                # Keep the floating audio player clear of the viewport-fixed
                # Complete button (whose footer begins at y=565). Otherwise
                # the player overlays the submit button and intercepts clicks.
                has_fixed_footer = fixed_choice_submit or fixed_sequence_submit or fixed_text_submit
                mini_rect.midbottom = (480, 555 if has_fixed_footer else 640 - 14)
                mini_hover = mini_rect.collidepoint(mouse_real)
                # Translucent over the content; solid when the pointer is on it.
                mini_opacity = mini_fade * (1.0 if mini_hover else 0.6)
                mini_rects = waveform.draw_mini(display_screen, mini_rect, mini_opacity, fonts[3])
            draw_text('',fonts[3],(112,127,143),65,603)
            if _shutdown_requested.is_set() or _app_shutdown.is_set():
                return None
            if zoom_open:
                from exercise_image_zoom import draw as draw_image_zoom
                zoom_close_rect = draw_image_zoom(display_screen, zoom_image_path or image_path)
            for ev in pygame.event.get():
                if _shutdown_requested.is_set() or _app_shutdown.is_set(): return None
                # Zoom overlay owns its events; ESC closes only the overlay.
                if zoom_open:
                    if ev.type == pygame.QUIT:
                        if confirm_exit(): return None
                    elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                        zoom_open = False
                    elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                        zoom_open = False
                    continue
                if ev.type==pygame.QUIT:
                    if confirm_exit(): return None
                    continue
                if ev.type==pygame.KEYDOWN:
                    if ev.key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN, pygame.K_HOME, pygame.K_END):
                        if ev.key == pygame.K_HOME:
                            content_scroll = 0
                        elif ev.key == pygame.K_END:
                            content_scroll = max_content_scroll
                        else:
                            step = -480 if ev.key == pygame.K_PAGEUP else 480
                            content_scroll = max(0, min(max_content_scroll, content_scroll + step))
                        continue
                    if ev.key==pygame.K_ESCAPE:
                        if confirm_exit(): return None
                        continue
                    # Keyboard access to answer selection and completion. These
                    # shortcuts use the same readiness guards as the fixed footer.
                    if kind in ('choice', 'picture_choice', 'true_false', 'listening_choice'):
                        count = min(len(options), 8)
                        # Keep a keyboard-selected answer visible even when its
                        # card has been moved in the layout editor or is below
                        # the viewport. The answer cards use document coords;
                        # only the viewport is scrolled (never move the cards).
                        def reveal_keyboard_choice():
                            nonlocal content_scroll
                            if selected_option is None or selected_option >= len(choice_layout):
                                return
                            _, card_y, _, card_h, _ = choice_layout[selected_option]
                            visible_top = content_scroll + 98
                            visible_bottom = content_scroll + 553
                            if card_y < visible_top:
                                content_scroll = max(0, card_y - 98)
                            elif card_y + card_h > visible_bottom:
                                content_scroll = min(max_content_scroll, card_y + card_h - 553)
                        if count and ev.key in (pygame.K_DOWN, pygame.K_RIGHT):
                            selected_option = (selected_option + 1) % count if selected_option is not None else 0
                            reveal_keyboard_choice()
                            continue
                        if count and ev.key in (pygame.K_UP, pygame.K_LEFT):
                            selected_option = (selected_option - 1) % count if selected_option is not None else count - 1
                            reveal_keyboard_choice()
                            continue
                        if pygame.K_1 <= ev.key <= pygame.K_8 and ev.key - pygame.K_1 < count:
                            selected_option = ev.key - pygame.K_1
                            reveal_keyboard_choice()
                            continue
                        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and selected_option is not None:
                            return str(options[selected_option])
                    elif kind == 'order':
                        # Number keys add/remove visible cards without submitting.
                        # Do not limit the mouse path: exercises may have >8 cards.
                        if pygame.K_1 <= ev.key <= pygame.K_8:
                            card_index = ev.key - pygame.K_1
                            if card_index < len(options):
                                if card_index in chosen:
                                    chosen.remove(card_index)
                                else:
                                    chosen.append(card_index)
                            continue
                        if ev.key == pygame.K_DELETE:
                            chosen.clear()
                            continue
                        if ev.key == pygame.K_BACKSPACE:
                            if chosen:
                                chosen.pop()
                            continue
                        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and len(chosen) == len(options):
                            return ' '.join(str(options[j]) for j in chosen)
                    elif kind == 'matching':
                        # Keyboard pairing: Left/Right chooses a column, 1-7
                        # chooses the displayed row in that column. Right rows
                        # are shuffled, so map their visible row to pair ID.
                        if ev.key in (pygame.K_LEFT, pygame.K_RIGHT):
                            matching_keyboard_side = 0 if ev.key == pygame.K_LEFT else 1
                            continue
                        if pygame.K_1 <= ev.key <= pygame.K_8:
                            row = ev.key - pygame.K_1
                            if row < len(matching_pairs):
                                if matching_keyboard_side == 0:
                                    matching_selected = (None if matching_selected == row else row)
                                    matching_keyboard_side = 1 if matching_selected is not None else 0
                                elif matching_selected is not None:
                                    right_id = matching_right[row]
                                    for left_id, linked_right in list(matching_links.items()):
                                        if linked_right == right_id:
                                            del matching_links[left_id]
                                    matching_links[matching_selected] = right_id
                                    matching_selected = None
                                    matching_keyboard_side = 0
                            continue
                        if ev.key == pygame.K_DELETE:
                            matching_links.clear()
                            matching_selected = None
                            matching_keyboard_side = 0
                            continue
                        if ev.key == pygame.K_BACKSPACE:
                            if matching_selected is not None:
                                matching_selected = None
                            elif matching_links:
                                matching_links.pop(next(reversed(matching_links)))
                            matching_keyboard_side = 0
                            continue
                        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and len(matching_links) == len(matching_pairs):
                            return dict(matching_links)
                    else:
                        if ev.key == pygame.K_BACKSPACE:
                            typed = typed[:-1]
                        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and typed.strip():
                            return typed.strip()
                if ev.type == pygame.TEXTINPUT and kind not in ('choice','picture_choice','true_false','listening_choice','order','matching'):
                    if ev.text and len(typed) + len(ev.text) <= 180:
                        typed += ev.text
                if ev.type==pygame.MOUSEBUTTONUP and ev.button==1:
                    waveform_drag=None
                    scrollbar_drag_offset=None
                if ev.type==pygame.MOUSEMOTION and scrollbar_drag_offset is not None and scrollbar_track is not None and scrollbar_thumb is not None:
                    # Scrollbar is viewport-fixed: never apply content_scroll to its pointer.
                    available = max(1, scrollbar_track.height-scrollbar_thumb.height)
                    new_top = max(scrollbar_track.top, min(scrollbar_track.top+available, ev.pos[1]-scrollbar_drag_offset))
                    content_scroll = round((new_top-scrollbar_track.top)*max_content_scroll/available)
                    continue
                if ev.type==pygame.MOUSEMOTION and waveform_drag=='mini' and waveform is not None and mini_rects:
                    mw=mini_rects[0]
                    waveform.seek(max(0,min(1,(ev.pos[0]-mw.x)/max(1,mw.width)))*waveform.duration)
                if ev.type==pygame.MOUSEMOTION and waveform_drag in ('wave','volume') and waveform is not None and waveform_rects:
                    # Waveform rectangles are in document coordinates. Pointer
                    # movement is in viewport coordinates, so use the same
                    # scroll transform as mouse-down before seeking/volume.
                    # Stop dragging if the waveform is behind fixed chrome.
                    if ev.pos[1] < 90 or (fixed_choice_submit or fixed_sequence_submit or fixed_text_submit) and ev.pos[1] >= 565:
                        waveform_drag = None
                    else:
                        wr,_,_,vr=waveform_rects
                        content_pointer = (ev.pos[0], ev.pos[1] + content_scroll)
                        if waveform_drag=='volume':
                            waveform.set_volume(max(0.0, min(1.0, (content_pointer[0]-vr.x)/max(1, vr.width))))
                        elif waveform_drag=='wave':
                            waveform.seek(max(0.0, min(1.0, (content_pointer[0]-wr.x)/max(1, wr.width)))*waveform.duration)
                if ev.type==pygame.MOUSEWHEEL:
                    content_scroll = max(0, min(max_content_scroll, content_scroll - ev.y*65))
                if ev.type==pygame.MOUSEBUTTONDOWN and ev.button in (4,5):
                    content_scroll = max(0, min(max_content_scroll, content_scroll + (-65 if ev.button==4 else 65)))
                    continue
                if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1 and scrollbar_track is not None and scrollbar_thumb is not None:
                    # Give the narrow scrollbar a larger pointer target. Clicking
                    # the track jumps to that position; dragging the thumb is smooth.
                    scrollbar_hit = scrollbar_track.inflate(16, 0)
                    if scrollbar_hit.collidepoint(ev.pos):
                        if scrollbar_thumb.inflate(16, 0).collidepoint(ev.pos):
                            scrollbar_drag_offset = ev.pos[1]-scrollbar_thumb.top
                        else:
                            scrollbar_drag_offset = scrollbar_thumb.height//2
                            available = max(1, scrollbar_track.height-scrollbar_thumb.height)
                            new_top = max(scrollbar_track.top, min(scrollbar_track.top+available, ev.pos[1]-scrollbar_drag_offset))
                            content_scroll = round((new_top-scrollbar_track.top)*max_content_scroll/available)
                        continue
                if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1 and waveform is not None and mini_rects and mini_fade>0.05:
                    mw,mp=mini_rects
                    if mp.inflate(8,8).collidepoint(ev.pos):
                        waveform.play(); continue
                    if mw.inflate(0,16).collidepoint(ev.pos):
                        waveform.seek(max(0,min(1,(ev.pos[0]-mw.x)/max(1,mw.width)))*waveform.duration)
                        waveform_drag='mini'; continue
                    if (mw.union(mp)).inflate(60,20).collidepoint(ev.pos):
                        continue  # click on the pill's padding: don't hit content underneath
                if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                    # Resolve viewport-anchored controls before scroll offsets.
                    # The top header and bottom footer mask underlying answers.
                    if fixed_choice_submit:
                        if fixed_submit_rect.collidepoint(ev.pos):
                            if selected_option is not None:
                                return str(options[selected_option])
                            continue
                        if ev.pos[1] < 90 or ev.pos[1] >= 565:
                            continue
                    if fixed_sequence_submit:
                        if fixed_sequence_rect.collidepoint(ev.pos):
                            if kind == 'matching' and len(matching_links) == len(matching_pairs):
                                return dict(matching_links)
                            if kind == 'order' and len(chosen) == len(options):
                                return ' '.join(str(options[j]) for j in chosen)
                            continue
                        if ev.pos[1] < 90 or ev.pos[1] >= 565:
                            continue
                    if fixed_text_submit:
                        if fixed_text_rect.collidepoint(ev.pos):
                            if typed.strip():
                                return typed.strip()
                            continue
                        if ev.pos[1] < 90 or ev.pos[1] >= 565:
                            continue
                    # The viewport header and the fixed footer are not part of
                    # the scrollable question. Block clicks through these areas
                    # for every exercise type, including non-legacy exercises.
                    if ev.pos[1] < 90 or ev.pos[1] >= 565:
                        continue
                    ev.pos = (ev.pos[0], ev.pos[1]+content_scroll)
                    matching_zoom_path = next((path for hit,path in matching_zoom_hits if hit.collidepoint(ev.pos)),None)
                    if matching_zoom_path:
                        zoom_image_path = matching_zoom_path
                        zoom_open = True
                        continue
                    if zoom_hit is not None and zoom_hit.collidepoint(ev.pos):
                        zoom_image_path = image_path
                        zoom_open = True
                        continue
                    if waveform is not None and waveform_rects is not None:
                        wave_r,play_r,speed_r,volume_r=waveform_rects
                        menu_hit = next((value for area,value in getattr(waveform,'speed_menu_rects',[]) if area.collidepoint(ev.pos)),None)
                        if menu_hit is not None:
                            waveform.set_speed(menu_hit)
                            waveform.speed_menu_open=False
                            continue
                        if wave_r.collidepoint(ev.pos):
                            waveform.seek(max(0.0, min(1.0, (ev.pos[0]-wave_r.x)/max(1, wave_r.width)))*waveform.duration)
                            waveform_drag='wave'
                            continue
                        if play_r.collidepoint(ev.pos):
                            waveform.play()
                            continue
                        if speed_r.collidepoint(ev.pos):
                            waveform.speed_menu_open=not getattr(waveform,'speed_menu_open',False)
                            continue
                        if volume_r.inflate(0,18).collidepoint(ev.pos):
                            waveform.set_volume(max(0.0, min(1.0, (ev.pos[0]-volume_r.x)/max(1, volume_r.width))))
                            waveform_drag='volume'
                            continue
                    if play_rect and waveform is None and play_rect.collidepoint(ev.pos):
                        play_audio()
                        continue
                    if stop_rect and waveform is None and stop_rect.collidepoint(ev.pos):
                        stop_audio()
                        continue
                    if kind == 'matching':
                        if matching_buttons['reset'].collidepoint(ev.pos):
                            matching_links.clear()
                            matching_selected = None
                            matching_keyboard_side = 0
                        else:
                            for rect,side,pair_idx in matching_cells:
                                if not rect.collidepoint(ev.pos):
                                    continue
                                if side == 0:
                                    matching_selected = None if matching_selected == pair_idx else pair_idx
                                    # A mouse-selected left item can be completed
                                    # immediately using a number key on the right.
                                    matching_keyboard_side = 1 if matching_selected is not None else 0
                                elif matching_selected is not None:
                                    for left,right in list(matching_links.items()):
                                        if right == pair_idx:
                                            del matching_links[left]
                                    matching_links[matching_selected] = pair_idx
                                    matching_selected = None
                                    matching_keyboard_side = 0
                                else:
                                    # Clicking an unmatched right item must not
                                    # leave the keyboard in right-column mode.
                                    matching_keyboard_side = 0
                                break
                        continue
                    for rect,index in cells:
                        if not rect.collidepoint(ev.pos):continue
                        if kind=='order':
                            if index=='reset':chosen=[]
                            elif isinstance(index,int):
                                if index in chosen:chosen.remove(index)
                                else:chosen.append(index)
                        elif index == 'confirm_choice':
                            if selected_option is not None:
                                return str(options[selected_option])
                        elif index == 'confirm_text':
                            if typed.strip():
                                return typed.strip()
                        elif isinstance(index, int):
                            # Selecting an answer must never submit it immediately.
                            selected_option = index
            present_frame(question)
            # Show the actual question before loading/decoding audio.
            if waveform_pending:
                waveform_pending = False
                try:
                    from pygame_waveform import WaveformAudio
                    waveform = WaveformAudio(audio_path)
                except Exception as exc:
                    audio_error = 'Waveform: ' + str(exc)[:70]
            clock.tick(30)
    finally:
        pygame.key.stop_text_input()
        try:
            if waveform is not None: waveform.stop()
            if is_listening and pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
        except pygame.error: pass
        # Do NOT quit the display here: the worker keeps the window open for
        # the next question and closes it when the quiz ends or is cancelled.
