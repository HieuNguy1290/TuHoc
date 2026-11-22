"""Reading transition on Windows without flashing the full-screen Tk studio.

Capture the native Tk window via PrintWindow while it is outside the virtual
screen; reveal the SDL overlay only after its first frame has been drawn.
"""
import ctypes
import os
import time


def _capture_window(top, sw, sh):
    from PIL import Image
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    hwnd = top.winfo_id()
    user32.GetWindowDC.argtypes = [wintypes.HWND]
    user32.GetWindowDC.restype = wintypes.HDC
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
    gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi32.SelectObject.restype = wintypes.HGDIOBJ
    gdi32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT,
                                 wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
    gdi32.GetDIBits.restype = ctypes.c_int
    user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
    user32.PrintWindow.restype = wintypes.BOOL
    hdc = user32.GetWindowDC(hwnd)
    if not hdc:
        return None
    memory = gdi32.CreateCompatibleDC(hdc)
    bitmap = gdi32.CreateCompatibleBitmap(hdc, sw, sh)
    old = gdi32.SelectObject(memory, bitmap)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [('biSize', wintypes.DWORD), ('biWidth', wintypes.LONG),
                    ('biHeight', wintypes.LONG), ('biPlanes', wintypes.WORD),
                    ('biBitCount', wintypes.WORD), ('biCompression', wintypes.DWORD),
                    ('biSizeImage', wintypes.DWORD), ('biXPelsPerMeter', wintypes.LONG),
                    ('biYPelsPerMeter', wintypes.LONG), ('biClrUsed', wintypes.DWORD),
                    ('biClrImportant', wintypes.DWORD)]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [('bmiHeader', BITMAPINFOHEADER), ('bmiColors', wintypes.DWORD * 3)]

    try:
        # PW_RENDERFULLCONTENT requests a full DWM-rendered window on Win10+.
        if not user32.PrintWindow(hwnd, memory, 2):
            if not user32.PrintWindow(hwnd, memory, 0):
                return None
        info = BITMAPINFO()
        info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        info.bmiHeader.biWidth = sw
        info.bmiHeader.biHeight = -sh
        info.bmiHeader.biPlanes = 1
        info.bmiHeader.biBitCount = 32
        info.bmiHeader.biCompression = 0
        pixels = ctypes.create_string_buffer(sw * sh * 4)
        if not gdi32.GetDIBits(memory, bitmap, 0, sh, pixels, ctypes.byref(info), 0):
            return None
        image = Image.frombytes('RGB', (sw, sh), pixels, 'raw', 'BGRX')
        # A blank PrintWindow result must not be displayed as a black flash.
        samples = [image.getpixel((int(sw * f), int(sh * f))) for f in (.25, .5, .75)]
        if all(max(rgb) - min(rgb) < 3 and max(rgb) < 25 for rgb in samples):
            return None
        return image
    finally:
        gdi32.SelectObject(memory, old)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory)
        user32.ReleaseDC(hwnd, hdc)


def animate(top, start, end, duration, on_finish):
    """Return True if handled; never expose an uncaptured full-screen window."""
    if os.name != 'nt':
        return False
    import pygame
    user32 = ctypes.windll.user32
    sw, sh = top.winfo_screenwidth(), top.winfo_screenheight()
    opening = end[2] > start[2]
    try:
        if opening:
            # Position beyond the *entire* virtual desktop, including monitors
            # to the right of the primary. Tk can layout without a visible flash.
            virtual_right = user32.GetSystemMetrics(76) + user32.GetSystemMetrics(78)
            top.geometry(f'{sw}x{sh}+{virtual_right + 80}+0')
            top.deiconify()
            top.update_idletasks()
            top.update()
        else:
            top.update_idletasks()
        shot = _capture_window(top, sw, sh)
        if shot is None:
            if opening:
                top.withdraw()
            return False
        if opening:
            top.withdraw()
        pygame.display.init()
        flags = pygame.NOFRAME | getattr(pygame, 'HIDDEN', 0)
        screen = pygame.display.set_mode((sw, sh), flags)
        hwnd = pygame.display.get_wm_info()['window']
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x80000
        LWA_COLORKEY = 1
        key = (1, 2, 3)
        exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle | WS_EX_LAYERED)
        user32.SetLayeredWindowAttributes(hwnd, 0x030201, 0, LWA_COLORKEY)
        source = pygame.image.fromstring(shot.tobytes(), shot.size, 'RGB').convert()
        # All resize work occurs while the SDL window is still hidden.
        steps = 30
        frames = []
        for i in range(steps + 1):
            t = i / steps
            eased = t * t * (3 - 2 * t)
            x, y, w, h = (round(a + (b - a) * eased) for a, b in zip(start, end))
            frames.append((x, y, pygame.transform.smoothscale(source, (max(1, w), max(1, h)))))
        clock = pygame.time.Clock()
        start_time = time.perf_counter()
        shown = False
        while True:
            pygame.event.pump()
            t = min(1., (time.perf_counter() - start_time) / duration)
            x, y, frame = frames[min(steps, int(t * steps))]
            screen.fill(key)
            screen.blit(frame, (x, y))
            pygame.display.flip()
            if not shown:
                user32.ShowWindow(hwnd, 8)  # SW_SHOWNOACTIVATE
                user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
                shown = True
                if not opening:
                    top.withdraw()
            if t >= 1.:
                break
            clock.tick(60)
        # Show the real studio while the final SDL frame still covers it,
        # then dismiss SDL to avoid a black intermediate frame.
        if opening:
            top.geometry(f'{sw}x{sh}+0+0')
            top.deiconify()
            top.lift()
        else:
            on_finish()
        pygame.display.quit()
        if opening:
            on_finish()
        return True
    except Exception:
        try:
            pygame.display.quit()
        except Exception:
            pass
        try:
            if opening:
                top.withdraw()
            else:
                top.deiconify()
        except Exception:
            pass
        return False
