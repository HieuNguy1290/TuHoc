"""Non-blocking launcher for the Pygame exam question-bank editor.

Safe to call repeatedly from Tk callbacks. No subprocess waits on Tk's UI thread.
"""
from tuhoc.paths import PROJECT_ROOT
import ctypes
import tempfile
import traceback
from datetime import datetime
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

_LOG = logging.getLogger(__name__)
_process = None
_started_at = 0.0
_generation = 0
_pending_job = None
_STARTUP_GRACE_S = 2.0
_POLL_MS = 350
_LOG_DIR = Path(os.environ.get('CHCV_NHCH_LOG_DIR', str(Path.home() / 'CungHocCungVui_Logs')))
_DIAG_LOG = _LOG_DIR / 'nhch_launcher.log'
_CHILD_LOG = _LOG_DIR / 'nhch_child.log'
_child_stream = None


def _diag(event, **details):
    """Append one timestamped diagnostic record, independent of app logging config."""
    stamp = datetime.now().astimezone().isoformat(timespec='milliseconds')
    fields = ' '.join('{}={!r}'.format(k, v) for k, v in details.items())
    line = '{} | {} | {}\n'.format(stamp, event, fields)
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        with _DIAG_LOG.open('a', encoding='utf-8') as f:
            f.write(line)
    except OSError:
        # Logging must never stop the user from opening the question bank.
        try:
            with (Path(tempfile.gettempdir()) / 'chcv_nhch_launcher_fallback.log').open('a', encoding='utf-8') as f:
                f.write(line)
        except OSError:
            pass


def _child_log_stream():
    global _child_stream
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    _child_stream = _CHILD_LOG.open('a', encoding='utf-8', buffering=1)
    _child_stream.write('\n===== NHCH child launch {} =====\n'.format(datetime.now().astimezone().isoformat()))
    return _child_stream


def _process_state(proc):
    try:
        return proc.poll()
    except Exception as exc:
        _diag('process_poll_error', error=repr(exc))
        return 'poll_error'



def _windows_for_pid(pid):
    """Enumerate visible, unowned top-level windows belonging to pid (Windows)."""
    if os.name != 'nt':
        return []
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    found = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def visit(hwnd, unused):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd) and not user32.GetWindow(hwnd, 4):
            found.append(hwnd)
        return True

    callback = callback_type(visit)
    user32.EnumWindows(callback, 0)
    return found


def _activate(pid):
    if os.name != 'nt':
        return False
    try:
        windows = _windows_for_pid(pid)
        if not windows:
            return False
        user32 = ctypes.windll.user32
        hwnd = windows[0]
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        return True
    except (OSError, AttributeError, ValueError) as exc:
        _LOG.warning('NHCH could not activate pid=%s: %s', pid, exc)
        return False


def _cancel_job(master):
    global _pending_job
    if _pending_job is not None:
        try:
            master.after_cancel(_pending_job)
        except (AttributeError, RuntimeError, ValueError):
            pass
        _pending_job = None


def _schedule(master, root, generation):
    global _pending_job
    try:
        _pending_job = master.after(_POLL_MS, lambda: _poll_window(master, root, generation))
    except (AttributeError, RuntimeError):
        _pending_job = None


def _launch(root):
    global _process, _started_at, _generation
    script = Path(__file__).resolve().with_name('exam_bank_pygame.py')
    if not script.is_file():
        raise FileNotFoundError('Missing NHCH module: {}'.format(script))
    flags = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0) if os.name == 'nt' else 0
    command = [sys.executable, '-m', 'tuhoc.exams.exam_bank_pygame', str(Path(root).resolve())]
    _diag('launch_attempt', command=command, cwd=str(PROJECT_ROOT), flags=flags)
    try:
        child_stream = _child_log_stream()
    except OSError as exc:
        _diag('child_log_open_failed', error=repr(exc))
        child_stream = None
    try:
        _process = subprocess.Popen(
            command, cwd=str(PROJECT_ROOT), creationflags=flags,
            stdout=child_stream if child_stream is not None else subprocess.DEVNULL,
            stderr=subprocess.STDOUT if child_stream is not None else subprocess.DEVNULL,
        )
    except Exception as exc:
        _diag('launch_failed', error=repr(exc), traceback=traceback.format_exc())
        raise
    _started_at = time.monotonic()
    _generation += 1
    _LOG.info('NHCH launched pid=%s generation=%s', _process.pid, _generation)
    _diag('launch_success', pid=_process.pid, generation=_generation, child_log=str(_CHILD_LOG))
    return _process


def _poll_window(master, root, generation):
    global _pending_job, _process
    _pending_job = None
    if generation != _generation or _process is None:
        return
    exit_code = _process.poll()
    if exit_code is not None:
        _LOG.info('NHCH closed pid=%s exit=%s', _process.pid, exit_code)
        _diag('process_exit', pid=_process.pid, exit_code=exit_code)
        _process = None
        return
    # Keep observing the process even after the window appears: the next click
    # can then distinguish a closed window from an invisible, still-live process.
    if os.name == 'nt':
        try:
            visible = bool(_windows_for_pid(_process.pid))
        except (OSError, AttributeError, ValueError) as exc:
            _LOG.warning('NHCH window lookup failed pid=%s: %s', _process.pid, exc)
            visible = False
        _LOG.debug('NHCH poll pid=%s visible=%s', _process.pid, visible)
        # Record state transitions, not every 350ms poll.
        current = (_process.pid, visible)
        if getattr(_poll_window, '_last_window_state', None) != current:
            _diag('window_state', pid=_process.pid, visible=visible)
            _poll_window._last_window_state = current
    _schedule(master, root, generation)


def open_editor(master, root):
    """Open, focus, or recover the NHCH editor without blocking Tk.

    If a process survives after its native window disappears, a new launch is
    allowed after a short grace period. The old process is asked to terminate
    asynchronously, without wait() on the Tk event loop.
    """
    global _process
    _diag('click_received', platform=os.name, root=str(root), launcher=str(Path(__file__).resolve()),
          current_pid=getattr(_process, 'pid', None), generation=_generation)
    if _process is not None:
        code = _process.poll()
        _LOG.info('NHCH click pid=%s poll=%s', _process.pid, code)
        _diag('existing_process', pid=_process.pid, poll=code, elapsed_s=round(time.monotonic()-_started_at, 2))
        if code is not None:
            _process = None
        elif os.name != 'nt':
            _diag('reuse_non_windows_process', pid=_process.pid)
            return _process
        elif _activate(_process.pid):
            _diag('activate_existing_window', pid=_process.pid)
            return _process
        elif time.monotonic() - _started_at < _STARTUP_GRACE_S:
            _diag('startup_grace_skip', pid=_process.pid)
            return _process
        else:
            old = _process
            _process = None
            _cancel_job(master)
            try:
                old.terminate()
            except (OSError, ProcessLookupError) as exc:
                _LOG.warning('NHCH old pid=%s termination failed: %s', old.pid, exc)
            _LOG.warning('NHCH invisible old pid=%s; restarting', old.pid)
            _diag('restart_invisible_process', old_pid=old.pid)

    _cancel_job(master)
    try:
        proc = _launch(root)
    except Exception as exc:
        _diag('open_editor_exception', error=repr(exc), traceback=traceback.format_exc())
        raise
    _schedule(master, root, _generation)
    _diag('poll_scheduled', pid=proc.pid, generation=_generation, job=str(_pending_job))
    return proc
