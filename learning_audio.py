"""Offline MP3/WAV player for learning blocks and listening exercises."""
import os, sys, ctypes
from pathlib import Path

class LearningAudio:
    def __init__(self):
        self._pygame=None
        self._alias='tuhoc_learning_audio'
        self._closed=False
    def stop(self):
        """Stop playback and release the currently opened MCI device."""
        if sys.platform=='win32':
            try:ctypes.windll.winmm.mciSendStringW(f'stop {self._alias}',None,0,None)
            except Exception:pass
            try:ctypes.windll.winmm.mciSendStringW(f'close {self._alias}',None,0,None)
            except Exception:pass
        if self._pygame:
            try:
                self._pygame.mixer.music.stop()
                self._pygame.mixer.music.unload()
            except Exception:pass
    def play(self,path):
        if not path:raise FileNotFoundError('Chưa có file âm thanh')
        path=Path(path).resolve()
        if not path.is_file():raise FileNotFoundError(str(path))
        self.stop()
        self._closed=False
        if sys.platform=='win32':
            def mci(command):
                buf=ctypes.create_unicode_buffer(512)
                result=ctypes.windll.winmm.mciSendStringW(command,buf,512,None)
                if result:
                    error=ctypes.create_unicode_buffer(512)
                    ctypes.windll.winmm.mciGetErrorStringW(result,error,512)
                    raise RuntimeError(error.value or f'MCI error {result}')
            mci(f'open "{path}" alias {self._alias}')
            try:
                mci(f'play {self._alias} from 0')
            except Exception:
                self.stop()
                raise
            return
        try:
            import pygame
            if not pygame.mixer.get_init():pygame.mixer.init()
            pygame.mixer.music.load(str(path));pygame.mixer.music.play()
            self._pygame=pygame
        except ImportError as exc:
            raise RuntimeError('Hệ điều hành này cần cài pygame để phát MP3/WAV (pip install pygame).') from exc

    def close(self):
        """Explicit lifecycle hook for page/window shutdown."""
        if not self._closed:
            self.stop()
            self._closed=True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
