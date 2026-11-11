"""Source launcher safety tests; never install packages or launch apps."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("jarvis_source_launcher", ROOT / "RUN-JARVIS.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class SourceLauncherTests(unittest.TestCase):
    def test_check_mode_has_no_install_or_launch_side_effect(self):
        with patch.object(sys, 'argv', ['RUN-JARVIS.py', '--check']), \
             patch.object(launcher, 'python_ok'), \
             patch.object(launcher, 'setup') as setup, \
             patch.object(launcher, 'run') as run:
            launcher.main()
            setup.assert_not_called()
            run.assert_not_called()

    def test_setup_requires_explicit_yes(self):
        with patch.object(sys, 'argv', ['RUN-JARVIS.py', '--setup']), \
             patch.object(launcher, 'python_ok'), \
             patch('builtins.input', return_value='no'), \
             patch.object(launcher, 'setup') as setup, \
             patch.object(launcher, 'run') as run:
            with self.assertRaises(SystemExit):
                launcher.main()
            setup.assert_not_called()
            run.assert_not_called()

    def test_runner_never_uses_shell(self):
        with patch.object(launcher.subprocess, 'run') as runner:
            launcher.run('python', '--version')
        runner.assert_called_once_with(('python', '--version'), cwd=ROOT, check=True, shell=False)


if __name__ == '__main__':
    unittest.main()
