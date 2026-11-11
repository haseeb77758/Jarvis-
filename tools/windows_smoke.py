"""Windows-runner smoke test, no desktop input or app launches."""
from pathlib import Path
import sys
import tkinter as tk

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import App
import pyautogui

root = tk.Tk()
try:
    app = App(root)
    root.update_idletasks()
    root.update()
    assert root.winfo_exists()
    assert app.mode.get() == 'Computer commands'
    assert app.permission.get() is False
    width, height = pyautogui.size()
    assert width > 0 and height > 0
    image = pyautogui.screenshot()
    assert image.width > 0 and image.height > 0
    app.halt()
    assert app.stop.is_set()
    print(f'Windows UI and screenshot smoke passed ({width}x{height}); no input performed.')
finally:
    root.destroy()
