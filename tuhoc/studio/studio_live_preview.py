"""Run real exercise renderers in a private SDL display for the layout editor."""
import multiprocessing
import os
import random
import time


class _RestartPreview(BaseException):
    pass


def text_rect(block):
    if block is None:
        return None
    return (block.x, block.y, block.width, block.height)


def option_rects(pairs, prefix='option'):
    return {f'{prefix}_{i}': rect for rect, i in pairs if type(i) is int}


def enclosing(rects):
    import pygame

    rects = [pygame.Rect(rect) for rect in rects if rect is not None]
    return rects[0].unionall(rects[1:]) if rects else None


def _post_input(pygame, action):
    kind, data = action
    if kind in ('click', 'release', 'motion'):
        value = {'click': pygame.MOUSEBUTTONDOWN, 'release': pygame.MOUSEBUTTONUP,
                 'motion': pygame.MOUSEMOTION}[kind]
        pos = tuple(data)
        attrs = {'pos': pos, 'button': 1} if kind != 'motion' else {'pos': pos, 'rel': (0, 0), 'buttons': tuple(pygame.mouse.get_pressed())}
    elif kind == 'wheel':
        value, attrs = pygame.MOUSEWHEEL, {'x': 0, 'y': data}
    elif kind == 'text':
        value, attrs = pygame.TEXTINPUT, {'text': data}
    elif kind == 'text_key':
        value, attrs = pygame.KEYDOWN, {'key': pygame.K_UNKNOWN, 'unicode': data, 'mod': 0, 'scancode': 0}
    elif kind == 'key':
        name, shifted = (data, False) if isinstance(data, str) else data
        try:
            key = pygame.key.key_code(name)
        except ValueError:
            return
        value, attrs = pygame.KEYDOWN, {'key': key, 'unicode': '',
                                        'mod': pygame.KMOD_SHIFT if shifted else 0, 'scancode': 0}
    else:
        return
    pygame.event.post(pygame.event.Event(value, attrs))


def _render_worker(pipe, question):
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
    os.environ['TU_HOC_PROFILE'] = '0'
    import pygame
    from tuhoc.exercises.pygame_exercises import _run

    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((960, 640))
    revision = None
    layout = {}
    restore_scroll = 0
    needs_frame = True
    last_frame = 0
    settling = 0
    frame_delay = 0
    playing = False
    pending = []
    original_image = question.get('_pygame_image')
    latest_scroll = 0
    kind = question.get('type')
    wheel_step = 44 if question.get('_layout_context') == 'exam' else 48 if kind in ('image_sentence_fill', 'image_letter_pick') else 38 if kind in (
        'sentence_gaps', 'passage_gaps', 'conversation_gaps') else 65
    pointer = (480, 320)
    pressed = False
    pygame.mouse.get_pos = lambda: pointer
    pygame.mouse.get_pressed = lambda: (pressed, False, False)

    def handle(message):
        nonlocal revision, layout, latest_scroll, restore_scroll, playing, needs_frame
        command, payload = message
        if command == 'close':
            raise EOFError
        if command == 'layout':
            revision, layout, reset, image = payload
            question['_pygame_image'] = image or original_image
            restore_scroll = 0 if reset else latest_scroll
            pending.clear()
            raise _RestartPreview
        if command == 'play':
            playing = payload
        elif command == 'input':
            pending.append(payload)
            needs_frame = True

    def capture(surface, regions, scroll, limit):
        nonlocal needs_frame, last_frame, latest_scroll, restore_scroll, pointer, pressed, settling, frame_delay
        latest_scroll = scroll
        if frame_delay:
            frame_delay -= 1
            if frame_delay:
                return
        if restore_scroll > 0 and limit:
            steps = min(39, round(restore_scroll / wheel_step))
            restore_scroll = 0
            if steps:
                _post_input(pygame, ('wheel', -steps))
                frame_delay = 2
                return
        now = time.monotonic()
        if needs_frame or settling or playing and now-last_frame >= .08:
            serialized = {key: tuple(rect) for key, rect in regions.items() if rect is not None}
            pipe.send(('frame', (revision, surface.get_size(), pygame.image.tobytes(surface, 'RGB'),
                                 serialized, scroll, limit)))
            needs_frame = False
            last_frame = now
        if settling:
            settling -= 1
        else:
            while not playing and not pipe.poll(.08):
                # A stationary editing view needs only its last frame.
                pass
        while pipe.poll():
            handle(pipe.recv())
        if pending:
            # Some loops consume events after drawing their frame. Wait through
            # that frame so the next image reflects the new input or scroll.
            frame_delay = 2
        for action in pending:
            kind, data = action
            if kind in ('click', 'release', 'motion'):
                pointer = tuple(data)
            if kind in ('click', 'release'):
                pressed = kind == 'click'
            _post_input(pygame, action)
        pending.clear()

    try:
        while True:
            try:
                if revision is None:
                    handle(pipe.recv())
                    continue
                random.seed(9731)
                needs_frame = True
                frame_delay = 0
                settling = 3 if question.get('audio') else 0
                pygame.event.clear()
                if question.get('_layout_context') == 'exam':
                    from tuhoc.exams.exam_pygame import ExamLayoutScene
                    exam = ExamLayoutScene(question['_preview_root'], question, layout)
                    clock = pygame.time.Clock()
                    while True:
                        capture(*exam.draw())
                        for event in pygame.event.get():
                            exam.event(event)
                        clock.tick(30)
                result = _run({**question, 'layout': layout, '_studio_scene': capture})
                pipe.send(('finished', (revision, result)))
                revision = None
            except _RestartPreview:
                if pygame.mixer.get_init():
                    pygame.mixer.stop()
                    pygame.mixer.music.stop()
            except Exception as exc:
                pipe.send(('error', (revision, str(exc))))
                revision = None
    except (EOFError, BrokenPipeError, KeyboardInterrupt):
        pass
    finally:
        pygame.quit()
        pipe.close()


class LivePreview:
    def __init__(self, question):
        ctx = multiprocessing.get_context('spawn')
        self.pipe, other = ctx.Pipe()
        self.process = ctx.Process(target=_render_worker, args=(other, question), daemon=True)
        try:
            self.process.start()
        except BaseException:
            self.pipe.close()
            raise
        finally:
            other.close()

    def send(self, kind, payload=None):
        self.pipe.send((kind, payload))

    def read(self):
        while self.pipe.poll():
            yield self.pipe.recv()

    def close(self):
        try:
            self.send('close')
        except (EOFError, OSError):
            pass
        self.pipe.close()
        self.process.join(.12)
        if self.process.is_alive():
            self.process.terminate()
            self.process.join(.12)
        if not self.process.is_alive():
            self.process.close()
