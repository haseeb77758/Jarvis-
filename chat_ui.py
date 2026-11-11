"""Chat composer for HASEEB AI Jarvis's visible, local Ollama conversation.

Compatible with the older Entry methods used by the controller, but supports
multiline prompts: Enter sends, Shift+Enter adds a new line.
"""
from __future__ import annotations

import tkinter as tk


class ChatComposer(tk.Text):
    def get(self, *args):
        if not args:
            return super().get("1.0", "end-1c")
        return super().get(*args)

    def delete(self, first, last=None):
        if first == 0:
            first = "1.0"
        return super().delete(first, last) if last is not None else super().delete(first)

    def insert(self, index, chars, *args):
        if index == 0:
            index = "1.0"
        return super().insert(index, chars, *args)


def on_return(event, send):
    """Send on Enter; preserve Shift+Enter newline in the Tk text widget."""
    if event.state & 0x0001:
        return None
    send()
    return "break"


def preset_prompt(entry, prompt):
    """Populate the composer without silently sending a request."""
    entry.delete(0, "end")
    entry.insert(0, prompt)
    entry.focus_set()
