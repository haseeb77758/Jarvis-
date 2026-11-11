"""Bounded Windows UI Automation: observed windows and exact named controls."""
import os
import time


def desktop():
    if os.name != 'nt':
        raise RuntimeError('UI Automation Windows par available hai.')
    import pythoncom
    pythoncom.CoInitialize()
    from pywinauto import Desktop
    return Desktop(backend='uia')


def windows():
    result = []
    for window in desktop().windows(visible_only=True):
        try:
            title = window.window_text().strip()
            if title:
                result.append(title[:250])
        except Exception:
            continue
        if len(result) >= 50:
            break
    return result


def match_window(title):
    matches = []
    exact = []
    for window in desktop().windows(visible_only=True):
        try:
            current = window.window_text().strip()
            if current.casefold() == title.casefold():
                exact.append(window)
            elif title.casefold() in current.casefold():
                matches.append(window)
        except Exception:
            continue
    candidates = exact or matches
    if not candidates:
        raise RuntimeError('Window nahi mili. windows command se exact title dekhein.')
    if len(candidates) > 1:
        raise RuntimeError('Ek se zyada windows match karti hain. Zyada specific title dein.')
    return candidates[0]


def inspect(title):
    window = match_window(title)
    rows = ['Window: ' + window.window_text()[:250]]
    queue = [(window, 0)]
    deadline = time.monotonic() + 5
    while queue and len(rows) < 65 and time.monotonic() < deadline:
        control, depth = queue.pop(0)
        if depth >= 3:
            continue
        try:
            children = control.children()
        except Exception:
            continue
        for child in children[:65]:
            try:
                kind = child.element_info.control_type
                # Edit/document values and password fields are not read into the snapshot.
                if kind in {'Edit', 'Document'} or getattr(child.element_info, 'is_password', False):
                    continue
                name = child.window_text().strip()
                if name:
                    rows.append(f'{kind}: {name[:160]}')
                queue.append((child, depth + 1))
            except Exception:
                continue
            if len(rows) >= 65:
                break
    return '\n'.join(rows)


def focus(title):
    target = match_window(title)
    target.set_focus()
    import ctypes
    if ctypes.windll.user32.GetForegroundWindow() != target.handle:
        raise RuntimeError('Window ko focus nahi mila. Windows ne foreground switch block kiya ho sakta hai.')
    return 'Window focus verified: ' + target.window_text()[:250]


def wait_window(title, stop):
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        if stop.is_set():
            raise RuntimeError('Stopped.')
        try:
            target = match_window(title)
            return 'Window found: ' + target.window_text()[:250]
        except RuntimeError as exc:
            if 'Ek se zyada' in str(exc):
                raise
            stop.wait(0.3)
    raise RuntimeError('12 seconds mein target window nahi mili.')


def invoke(title, name):
    target = match_window(title)
    # Exact name only. A missing/ambiguous control never falls back to coordinates.
    controls = [c for c in target.descendants(title=name, control_type='Button')
                if c.is_visible() and c.is_enabled()]
    if len(controls) != 1:
        raise RuntimeError('Exactly ek visible enabled button nahi mila. inspect: title se check karein.')
    controls[0].invoke()
    return f'Button invoke request bhej di: {name}. Result target app mein verify karein.'
