"""Native Tk responsive dashboard regression tests.

The checks catch a real Windows screenshot regression where packed Canvas and
Text children expanded both sidebars and pushed chat Send/Mic below the window.
No Ollama, file operations, microphones, internet or desktop controls run.
"""
from __future__ import annotations

import tkinter as tk
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

from dashboard import make_dashboard


class LayoutRegressionTests(TestCase):
    def _open(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest("No display available for Tk geometry smoke test: " + str(exc))
        self.addCleanup(lambda: root.destroy() if root.winfo_exists() else None)
        app = SimpleNamespace(
            root=root,
            ai=SimpleNamespace(model="Puter account default"),
            ai_status=tk.StringVar(master=root, value="AI CONNECTED"),
            mode=tk.StringVar(master=root, value="AI chat"),
            status=tk.StringVar(master=root, value="Ready"),
            voice_language=tk.StringVar(master=root, value="Auto"),
            livekit_voice_state=tk.StringVar(master=root, value='LIVEKIT OFF'),
            speak_enabled=tk.BooleanVar(master=root, value=False),
            permission=tk.BooleanVar(master=root, value=False),
        )
        for command in ("open_voice_settings", "open_livekit_voice", "open_gemini_settings", "toggle_livekit_voice", "open_diagnostics", "halt", "resume", "connect_github", "update_jarvis",
                        "setup_ai", "open_sandbox", "open_toolkit",
                        "show_memory", "choose", "add_app", "clear",
                        "listen_voice", "setup_voice", "test_voice",
                        "submit"):
            setattr(app, command, Mock())
        make_dashboard(app)
        return root, app

    def test_primary_livekit_button_and_legacy_mic_both_available(self):
        root, app = self._open()
        self.assertIsNotNone(app.livekit_primary_button)
        self.assertIn('Talk Live', app.livekit_primary_button.cget('text'))
        app.livekit_primary_button.invoke()
        app.toggle_livekit_voice.assert_called_once()
        app.livekit_voice_state.set('LIVE')
        root.update_idletasks()
        self.assertTrue(root.winfo_exists())

    def test_fixed_sidebars_and_visible_chat_controls(self):
        root, app = self._open()
        body = next(w for w in root.winfo_children() if w.winfo_manager() == "pack"
                    and w.winfo_children() and w.winfo_children()[0].winfo_manager() == "grid")
        for width, height in ((1280, 760), (1120, 700)):
            with self.subTest(width=width, height=height):
                root.geometry(f"{width}x{height}+0+0")
                root.update()
                left = body.grid_slaves(row=0, column=0)[0]
                center = body.grid_slaves(row=0, column=1)[0]
                right = body.grid_slaves(row=0, column=2)[0]
                self.assertLessEqual(left.winfo_width(), 250)
                self.assertGreaterEqual(left.winfo_width(), 205)
                # These frames hold packed children, so grid_propagate(False)
                # would NOT prevent huge default Canvas/Text requests.
                self.assertFalse(left.pack_propagate())
                self.assertFalse(right.pack_propagate())
                self.assertLessEqual(right.winfo_width(), 295)
                # Windows runners may clamp requested window width to their
                # virtual desktop. Assert against the ACTUAL mapped width.
                actual_width = root.winfo_width()
                self.assertGreaterEqual(actual_width, 1020)
                self.assertGreaterEqual(center.winfo_width(), actual_width - 580)
                self.assertGreater(app.log.winfo_height(), 80)
                self.assertGreater(app.entry.winfo_height(), 38)
                self.assertTrue(app.send.winfo_ismapped())
                self.assertTrue(app.entry.winfo_ismapped())
                self.assertTrue(app.orb.canvas.winfo_ismapped())
                # Composer + Send must remain inside the actual window, not offscreen.
                window_bottom = root.winfo_rooty() + root.winfo_height()
                self.assertLess(app.send.winfo_rooty() + app.send.winfo_height(), window_bottom)
                self.assertLess(app.entry.winfo_rooty() + app.entry.winfo_height(), window_bottom)

    def test_orb_animation_can_be_paused_with_existing_button(self):
        root, app = self._open()
        root.geometry("1280x760+0+0")
        root.update()
        self.assertTrue(app.orb.running)
        app.orb.toggle()
        self.assertFalse(app.orb.running)
        self.assertTrue(app.orb.canvas.winfo_ismapped())


if __name__ == "__main__":
    import unittest
    unittest.main()

