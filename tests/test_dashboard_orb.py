"""Tests for HASEEB AI's animated, local-only premium desktop orb.

No real GUI, microphone, network connection or GPU required for these tests.
"""
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dashboard import RotatingOrb, _sphere_points, _project_orb_point


class AnimatedOrbTests(unittest.TestCase):
    def test_fibonacci_sphere_points_are_bounded_and_deterministic(self):
        first = _sphere_points(144)
        self.assertEqual(first, _sphere_points(144))
        self.assertEqual(len(first), 144)
        for point in first:
            self.assertAlmostEqual(sum(component * component for component in point), 1.0, places=6)
        for invalid in (0, 501, 1.5, "144"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                _sphere_points(invalid)

    def test_sphere_rotates_on_y_axis_with_bounded_projection(self):
        point = (1.0, 0.2, 0.0)
        a = _project_orb_point(point, 0)
        b = _project_orb_point(point, math.pi / 2)
        self.assertNotAlmostEqual(a[0], b[0])
        for result in (a, b):
            self.assertLessEqual(abs(result[0]), 61)
            self.assertLessEqual(abs(result[1]), 61)
            self.assertTrue(-1 <= result[2] <= 1)

    def _mock_orb(self):
        orb = RotatingOrb.__new__(RotatingOrb)
        orb.canvas = Mock()
        orb.canvas.winfo_exists.return_value = True
        orb.canvas.winfo_viewable.return_value = True
        orb.points = _sphere_points(7)
        orb.dots = list(range(7))
        orb.orbit = "orbit"
        orb.satellite = "satellite"
        orb.center_text = "center"
        orb.cx = 95
        orb.cy = 75
        orb.phase = 0
        orb.running = True
        orb.alive = True
        return orb

    def test_animation_moves_dots_and_schedules_only_tk_callback(self):
        orb = self._mock_orb()
        orb._tick()
        self.assertAlmostEqual(orb.phase, .042)
        self.assertEqual(orb.canvas.coords.call_count, 8)
        orb.canvas.after.assert_called_once()
        self.assertEqual(orb.canvas.after.call_args.args[0], RotatingOrb.FRAME_MS)
        self.assertTrue(callable(orb.canvas.after.call_args.args[1]))

    def test_pause_reduces_cpu_activity_without_destroying_state(self):
        orb = self._mock_orb()
        self.assertFalse(orb.toggle())
        orb._tick()
        orb.canvas.coords.assert_not_called()
        self.assertEqual(orb.phase, 0)
        self.assertEqual(orb.canvas.after.call_args.args[0], 250)
        self.assertTrue(orb.toggle())
        orb._tick()
        self.assertGreater(orb.phase, 0)

    def test_minimized_window_does_not_redraw_and_destroy_stops_loop(self):
        orb = self._mock_orb()
        orb.canvas.winfo_viewable.return_value = False
        orb._tick()
        orb.canvas.coords.assert_not_called()
        orb.canvas.after.assert_called_once()
        orb.alive = False
        orb.canvas.reset_mock()
        orb._tick()
        orb.canvas.after.assert_not_called()


if __name__ == "__main__":
    unittest.main()
