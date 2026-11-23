"""Opt-in, low-impact navigation timing. Set TU_HOC_PROFILE=0 to disable.

Logs are written beside the executable to navigation_performance.log. Timings
are diagnostic, not proof of actual pixels reaching the display.
"""
from tuhoc.paths import PROJECT_ROOT
import functools
import os
from queue import Full, Queue
from threading import Lock, Thread
import time
from datetime import datetime
from pathlib import Path

ENABLED = os.environ.get('TU_HOC_PROFILE', '1').strip().lower() not in ('0', 'false', 'off')
LOG = Path(os.environ.get('TU_HOC_NAV_LOG') or (PROJECT_ROOT / 'navigation_performance.log'))
_lines=Queue(maxsize=512)
_start=Lock()
_worker=None


def _writer():
    while True:
        line=_lines.get()
        try:
            with LOG.open('a',encoding='utf-8') as stream:
                stream.write(line)
        except OSError:
            pass
        finally:
            _lines.task_done()


def flush():
    """Drain diagnostic lines before normal application shutdown."""
    _lines.join()



def record(page, stage, milliseconds, note=''):
    if not ENABLED:
        return
    global _worker
    with _start:
        if _worker is None:
            _worker=Thread(target=_writer,name='TuHocNavigationLog',daemon=True)
            _worker.start()
    line=f'{datetime.now().isoformat(timespec="milliseconds")} | page={str(page)!r} | stage={stage} | ms={milliseconds:.2f} | {note}\n'
    try:
        _lines.put_nowait(line)
    except Full:
        pass



def install(app_class):
    """Instrument existing functions without changing their behavior or signatures."""
    if not ENABLED:
        return
    for name in ('clear', '_snapshot_before_navigation', '_remove_page_fade',
                 '_fade_in_new_page', 'layout'):
        original = getattr(app_class, name, None)
        if original is None:
            continue

        def make_wrapper(fn, stage):
            @functools.wraps(fn)
            def wrapped(self, *args, **kwargs):
                page = args[0] if stage == 'layout' and args else getattr(self, '_admin_page', '?')
                start = time.perf_counter()
                try:
                    return fn(self, *args, **kwargs)
                finally:
                    record(page, stage, (time.perf_counter() - start) * 1000)
            return wrapped
        setattr(app_class, name, make_wrapper(original, name))
