"""Keeps the s&box editor window drawing while a capture run needs it, without taking the user's focus.

A minimized DirectX window stops presenting frames, so a window capture of it (the bridge's screenshot_game is a PrintWindow of the
editor) comes back completely black. That happened at 22:07Z on 2026-11-06 after the editor had been minimized from the desktop
(its rectangle was at -32000,-32000). This restores the window WITHOUT activating it (the app in front keeps the focus), sends it
behind every other window (so nothing pops up over what the user is doing) and, when the run is over, minimizes it again, so the
window is left as it was found. A window that was not minimized is not touched at all.

    python window_state.py            report the editor window's state, change nothing
"""
import ctypes
import ctypes.wintypes as wt
import time

user32 = ctypes.windll.user32
SW_SHOWNOACTIVATE, SW_SHOWMINNOACTIVE = 4, 7
HWND_BOTTOM = ctypes.c_void_p(1)
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x0001, 0x0002, 0x0010
user32.ShowWindow.argtypes = [wt.HWND, ctypes.c_int]
user32.SetWindowPos.argtypes = [wt.HWND, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
user32.IsIconic.argtypes = [wt.HWND]
user32.IsWindowVisible.argtypes = [wt.HWND]


def editor_window():
    """ ( handle, title ) of the s&box editor's main window, or None. Its title is '<scene> - s&box editor'. """
    found = []
    enum_proc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def look(handle, _):
        length = user32.GetWindowTextLengthW(handle)
        if length:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(handle, buf, length + 1)
            if buf.value.endswith("s&box editor") and user32.IsWindowVisible(handle):
                found.append((handle, buf.value))
        return True

    user32.EnumWindows(enum_proc(look), 0)
    return found[0] if found else None


def state():
    win = editor_window()
    if not win:
        return {"found": False}
    return {"found": True, "handle": win[0], "title": win[1], "minimized": bool(user32.IsIconic(win[0]))}


def ensure_drawing(settle=3.0):
    """ If the editor is minimized: restore it without activating it and put it behind the other windows. Returns the handle if
    it was minimized (so the caller can minimize it again), otherwise None. """
    win = editor_window()
    if not win or not user32.IsIconic(win[0]):
        return None
    handle = win[0]
    user32.ShowWindow(handle, SW_SHOWNOACTIVATE)
    user32.SetWindowPos(handle, HWND_BOTTOM, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
    for _ in range(20):
        if not user32.IsIconic(handle):
            break
        time.sleep(0.25)
    time.sleep(settle)
    return handle


def minimize_again(handle):
    """ Back to how it was found: minimized, without activating anything. """
    if handle:
        user32.ShowWindow(handle, SW_SHOWMINNOACTIVE)


if __name__ == "__main__":
    print(state())
