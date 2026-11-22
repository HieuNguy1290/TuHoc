"""Prevent overlapping standalone SDL windows and capture lifecycle failures."""
import logging
import threading
from pathlib import Path

_lock = threading.Lock()
shutdown = threading.Event()

def request_shutdown():
    """Signal all SDL loops; SDL cleanup remains on the owning thread."""
    shutdown.set()
    try:
        import pygame
        if pygame.display.get_init() and pygame.display.get_surface() is not None:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
    except Exception:
        pass

def active():
    return _lock.locked()

_logger = logging.getLogger('tuhoc.pygame.lifecycle')


def acquire():
    """Reserve the shared SDL display for one active session."""
    return not shutdown.is_set() and _lock.acquire(blocking=False)


def release():
    """Release the reservation held by the current session."""
    _lock.release()


def launch(target, args, name):
    """Return False if another standalone SDL session is active."""
    if not acquire():
        return False

    def runner():
        try:
            target(*args)
        except Exception:
            try:
                root = Path.home() / 'TuHoc'
                root.mkdir(parents=True, exist_ok=True)
                handler = logging.FileHandler(root / 'pygame_lifecycle_errors.log', encoding='utf-8')
                _logger.addHandler(handler)
                try:
                    _logger.exception('SDL session failed: %s', name)
                finally:
                    _logger.removeHandler(handler)
                    handler.close()
            except Exception:
                _logger.exception('SDL session failed: %s', name)
        finally:
            try:
                import pygame
                if pygame.display.get_init():
                    pygame.display.quit()
            except ImportError:
                pass
            finally:
                _lock.release()

    try:
        threading.Thread(target=runner, name=name, daemon=True).start()
    except Exception:
        _lock.release()
        raise
    return True
