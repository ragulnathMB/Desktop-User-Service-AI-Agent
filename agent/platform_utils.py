"""OS specific helpers: hide from taskbar, exclude from screenshots, glass blur."""
from __future__ import annotations

import ctypes
import platform
import sys

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


def os_label() -> str:
    if IS_WIN:
        return f"Windows {platform.release()}"
    if IS_MAC:
        return f"macOS {platform.mac_ver()[0]}"
    return f"Linux ({platform.release()})"


def modifier_key() -> str:
    return "command" if IS_MAC else "ctrl"


# ---------------------------------------------------------------- Windows
if IS_WIN:
    from ctypes import wintypes

    _user32 = ctypes.windll.user32
    _user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    _user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    _user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
    _user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    _user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
    _user32.SetWindowDisplayAffinity.restype = wintypes.BOOL
    _user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                     ctypes.c_int, ctypes.c_int, wintypes.UINT]
    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.SetForegroundWindow.argtypes = [wintypes.HWND]

    GWL_EXSTYLE = -20
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_APPWINDOW = 0x00040000
    WDA_EXCLUDEFROMCAPTURE = 0x00000011

    class _ACCENT(ctypes.Structure):
        _fields_ = [("AccentState", ctypes.c_int), ("AccentFlags", ctypes.c_int),
                    ("GradientColor", ctypes.c_uint), ("AnimationId", ctypes.c_int)]

    class _WCAD(ctypes.Structure):
        _fields_ = [("Attribute", ctypes.c_int), ("Data", ctypes.c_void_p), ("SizeOfData", ctypes.c_size_t)]


def hide_from_taskbar(hwnd: int) -> None:
    """Remove the taskbar button / Alt-Tab entry (Windows)."""
    if not IS_WIN:
        return
    try:
        style = _user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        style = (style | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
        _user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style)
        _user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0004 | 0x0010 | 0x0020)
    except Exception:
        pass


def exclude_from_capture(hwnd: int) -> bool:
    """Make a window invisible to screenshots / screen sharing. True = natively excluded."""
    if not IS_WIN:
        return False
    try:
        return bool(_user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE))
    except Exception:
        return False


def enable_blur(hwnd: int) -> bool:
    """Blur-behind (frosted glass) for a frameless window on Windows 10/11."""
    if not IS_WIN:
        return False
    try:
        fn = _user32.SetWindowCompositionAttribute
        fn.argtypes = [wintypes.HWND, ctypes.c_void_p]
        fn.restype = wintypes.BOOL
        accent = _ACCENT(3, 0, 0x01000000, 0)  # ACCENT_ENABLE_BLURBEHIND
        data = _WCAD(19, ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p), ctypes.sizeof(accent))
        return bool(fn(hwnd, ctypes.byref(data)))
    except Exception:
        return False


def get_foreground():
    if IS_WIN:
        try:
            return int(_user32.GetForegroundWindow() or 0) or None
        except Exception:
            return None
    return None


def restore_foreground(handle) -> None:
    if IS_WIN and handle:
        try:
            _user32.SetForegroundWindow(handle)
        except Exception:
            pass


# ------------------------------------------------------------------ macOS
def mac_hide_dock_icon() -> None:
    if not IS_MAC:
        return
    try:
        from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
        NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    except Exception:
        pass


def mac_prepare_window(winid: int) -> None:
    if not IS_MAC:
        return
    try:
        import objc
        view = objc.objc_object(c_void_p=ctypes.c_void_p(winid))
        view.window().setSharingType_(0)  # NSWindowSharingNone
    except Exception:
        pass
