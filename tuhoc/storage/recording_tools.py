"""Opt-in voice and app-window recording. Requires Windows and optional recording extras.

Never starts recording on app launch. Audio from system playback uses WASAPI loopback.
"""
from tuhoc.paths import PROJECT_ROOT
import datetime
import subprocess
import threading
import time
import wave
from pathlib import Path

RATE = 44100


def prerequisites():
    try:
        import numpy, soundcard, mss, cv2, imageio_ffmpeg  # noqa: F401
    except ImportError as exc:
        raise RuntimeError('Thiếu thư viện ghi hình/ghi âm. Chạy CAI_GHI_AM_GHI_HINH.bat.\n' + str(exc)) from exc


def recording_folder():
    import os
    directory = PROJECT_ROOT / 'BanGhi'
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def stamp():
    return datetime.datetime.now().strftime('%Y%m%d_%H%M%S')


def app_bounds(root):
    # Win32 coordinates may be negative on a secondary display.
    import ctypes
    from ctypes import wintypes
    rectangle = wintypes.RECT()
    if not ctypes.windll.user32.GetWindowRect(int(root.winfo_id()), ctypes.byref(rectangle)):
        raise RuntimeError('Không xác định được vị trí cửa sổ.')
    return {'left': rectangle.left, 'top': rectangle.top,
            'width': rectangle.right - rectangle.left,
            'height': rectangle.bottom - rectangle.top}


def microphone_choices():
    """Return available actual input devices; ids survive combo-box renumbering."""
    import soundcard as sc
    default = sc.default_microphone()
    devices = sc.all_microphones(include_loopback=False)
    result = []
    for d in devices:
        result.append({'id': str(d.id), 'name': str(d.name),
                       'default': bool(default and str(d.id) == str(default.id))})
    return result


def resolve_microphone(device_id=None):
    import soundcard as sc
    if device_id:
        for device in sc.all_microphones(include_loopback=False):
            if str(device.id) == str(device_id):
                return device
        raise RuntimeError('Micro đã chọn không còn kết nối. Vào + > Thiết bị ghi âm để chọn lại.')
    return sc.default_microphone()


def start_audio_capture(stop_event, destination, mode, errors, microphone_id=None):
    """Write signed 16 bit stereo PCM audio directly to WAV, with low memory use."""
    try:
        import numpy as np
        import soundcard as sc
        if mode == 'system':
            speaker = sc.default_speaker()
            if speaker is None:
                raise RuntimeError('Chưa chọn loa phát âm thanh mặc định trong Windows.')
            device = sc.get_microphone(id=str(speaker.id), include_loopback=True)
        else:
            device = resolve_microphone(microphone_id)
        if device is None:
            raise RuntimeError('Không tìm thấy ' + ('thiết bị âm thanh hệ thống' if mode == 'system' else 'micro.'))
        with wave.open(str(destination), 'wb') as wav:
            wav.setnchannels(2)
            wav.setsampwidth(2)
            wav.setframerate(RATE)
            with device.recorder(samplerate=RATE, channels=(1 if mode == 'microphone' else 2), blocksize=2048) as recorder:
                while not stop_event.is_set():
                    arr = recorder.record(numframes=2048)
                    # soundcard returns float samples in [-1, 1].
                    if arr.ndim == 1: arr = arr[:, None]
                    if arr.shape[1] == 1: arr = np.repeat(arr, 2, axis=1)
                    pcm = (np.clip(arr[:, :2], -1, 1) * 32767).astype('<i2')
                    wav.writeframes(pcm.tobytes())
    except Exception as exc:
        errors.append((mode, str(exc)))


class RecordingSession:
    def __init__(self, root=None, kind='video', with_microphone=True, microphone_id=None, capture_region=None, noise_settings=None, output_dir=None, fps=30):
        self.root = root
        self.output_dir = Path(output_dir).expanduser() if output_dir else None
        self.capture_region = capture_region
        self.noise_settings = noise_settings or {}
        self.kind = kind
        self.with_microphone = with_microphone
        self.microphone_id = microphone_id
        self.stop_event = threading.Event()
        self.threads = []
        self.errors = []
        self.output = None
        self.temp = []
        self.started = None
        self.location = None
        self.fps = int(fps) if int(fps) in (12,24,30,60) else 30

    def start(self):
        import sys
        if sys.platform != 'win32':
            raise RuntimeError('Tính năng quay ứng dụng và thu tiếng hệ thống dành cho Windows.')
        prerequisites()
        dest = self.output_dir or recording_folder()
        dest.mkdir(parents=True, exist_ok=True)
        basename = 'GhiHinh' if self.kind == 'video' else 'GhiAm'
        self.output = dest / (basename + '_' + stamp() + ('.mp4' if self.kind == 'video' else '.wav'))
        self.started = time.monotonic()
        if self.kind == 'video':
            self.location = self.capture_region or app_bounds(self.root)
            system_path = self.output.with_name(self.output.stem + '_system.wav')
            self.temp.append(system_path)
            self._launch(start_audio_capture, system_path, 'system', self.errors)
            if self.with_microphone:
                mic_path = self.output.with_name(self.output.stem + '_mic.wav')
                self.temp.append(mic_path)
                self._launch(start_audio_capture, mic_path, 'microphone', self.errors, self.microphone_id)
            self._launch(self._capture_video)
        else:
            self._launch(start_audio_capture, self.output, 'microphone', self.errors, self.microphone_id)
        return self.output

    def _launch(self, fn, *args):
        thread = threading.Thread(target=fn, args=(self.stop_event, *args), daemon=True)
        thread.start()
        self.threads.append(thread)

    def _capture_video(self, event):
        try:
            import cv2
            import numpy as np
            import mss
            location = self.location
            # Codec requires even dimensions. This records a fixed window rectangle.
            width = max(2, location['width'] // 2 * 2)
            height = max(2, location['height'] // 2 * 2)
            fps = self.fps
            raw_video = self.output.with_name(self.output.stem + '_silent.mp4')
            self.temp.append(raw_video)
            writer = cv2.VideoWriter(str(raw_video), cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
            if not writer.isOpened():
                raise RuntimeError('Không khởi tạo được bộ mã hóa MP4.')
            with mss.mss() as shot:
                # Capture uses fixed rectangle; moving window during recording is discouraged.
                # VideoWriter uses constant FPS, not capture timestamps. Fill skipped
                # frame slots with the latest image so elapsed video time stays real.
                capture_start = time.monotonic()
                frames_written = 0
                last_frame = None
                while not event.is_set():
                    pixels = np.asarray(shot.grab({'left': location['left'], 'top': location['top'], 'width': width, 'height': height}))
                    frame = cv2.cvtColor(pixels, cv2.COLOR_BGRA2BGR)
                    now = time.monotonic()
                    target_count = max(1, int((now - capture_start) * fps) + 1)
                    if last_frame is not None:
                        while frames_written < target_count - 1:
                            writer.write(last_frame)
                            frames_written += 1
                    writer.write(frame)
                    frames_written += 1
                    last_frame = frame
                    next_frame = capture_start + frames_written / fps
                    event.wait(max(0, next_frame - time.monotonic()))
                # Preserve the last partial interval at the moment recording stops.
                if last_frame is not None:
                    target_count = max(frames_written, round((time.monotonic() - capture_start) * fps))
                    while frames_written < target_count:
                        writer.write(last_frame)
                        frames_written += 1
            writer.release()
        except Exception as exc:
            self.errors.append(('video', str(exc)))
            self.stop_event.set()

    def _mic_filters(self):
        """FFmpeg filters applied only to microphone audio, not desktop playback."""
        settings = self.noise_settings
        strength = max(0.0, min(1.0, float(settings.get('strength', 0.55))))
        gate = max(-75.0, min(-20.0, float(settings.get('gate_db', -48))))
        # afftdn noise floor parameter is in dB; higher strength removes more noise.
        noise_floor = -75 + strength * 45
        chain = ['highpass=f=80', f'afftdn=nf={noise_floor:.1f}:nr={6+strength*18:.1f}',
                 f'agate=threshold={10**(gate/20):.6f}:ratio=2:attack=15:release=220']
        if settings.get('auto_level', True):
            chain.append('dynaudnorm=f=150:g=9:p=0.9:m=8')
        return ','.join(chain)

    def finish(self):
        self.stop_event.set()
        for thread in self.threads:
            thread.join(timeout=4)
        if any(t.is_alive() for t in self.threads):
            raise RuntimeError('Thiết bị ghi chưa dừng kịp. Hãy kiểm tra file ghi.')
        if self.errors and (self.kind != 'video' or any(k == 'video' for k, _ in self.errors)):
            raise RuntimeError('; '.join(f'{mode}: {err}' for mode, err in self.errors))
        if self.kind == 'voice' and self.noise_settings.get("enabled"):
            import imageio_ffmpeg
            original = self.output
            cleaned = original.with_name(original.stem + "_clean.wav")
            cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(original), "-af", self._mic_filters(), str(cleaned)]
            done = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if done.returncode: raise RuntimeError("Lọc âm thanh thất bại: " + done.stderr[-500:])
            cleaned.replace(original)
        if self.kind == 'video':
            import imageio_ffmpeg
            video = self.output.with_name(self.output.stem + '_silent.mp4')
            sounds = [p for p in self.temp if p.suffix == '.wav' and p.exists() and p.stat().st_size > 44]
            if not sounds:
                # Video-only is valid when the computer has no active audio device.
                if video.exists() and video.stat().st_size > 100:
                    video.replace(self.output)
                    for part in self.temp:
                        try: part.unlink(missing_ok=True)
                        except OSError: pass
                    return self.output, list(self.errors)
                raise RuntimeError('Không tạo được video. ' + str(self.errors))
            command = [imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-y', '-i', str(video)]
            for sound in sounds:
                command.extend(['-i', str(sound)])
            mic_index = next((i+1 for i, sound in enumerate(sounds) if sound.name.endswith('_mic.wav')), None)
            filters = []
            if mic_index is not None and self.noise_settings.get('enabled'):
                filters.append(f'[{mic_index}:a]{self._mic_filters()}[micclean]')
            if len(sounds) == 2:
                streams = ['micclean' if i == mic_index else f'{i}:a' for i in (1, 2)]
                filters.append(f'[{streams[0]}][{streams[1]}]amix=inputs=2:duration=longest:normalize=1[a]')
                command.extend(['-filter_complex', ';'.join(filters), '-map', '0:v:0', '-map', '[a]'])
            elif filters:
                command.extend(['-filter_complex', ';'.join(filters), '-map', '0:v:0', '-map', '[micclean]'])
            else:
                command.extend(['-map', '0:v:0', '-map', '1:a:0'])
            command.extend(['-c:v', 'copy', '-c:a', 'aac', '-shortest', str(self.output)])
            done = subprocess.run(command, capture_output=True, text=True, timeout=90)
            if done.returncode:
                raise RuntimeError('Ghép tiếng thất bại: ' + done.stderr[-500:])
            for part in self.temp:
                try: part.unlink(missing_ok=True)
                except OSError: pass
        if self.output is None or not self.output.exists() or self.output.stat().st_size < 100:
            raise RuntimeError('File ghi bị rỗng.')
        return self.output, list(self.errors)
