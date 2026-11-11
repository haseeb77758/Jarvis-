"""Exercise the local installation test path on a real Windows CI runner.

This intentionally runs from an isolated source copy that excludes Store-only
release assets. It never creates shortcuts or writes to the current user's
Jarvis installation.
"""
from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from install_windows import copy_source, run_local_tests


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="jarvis-personal-setup-smoke-") as temporary:
        target = Path(temporary) / "JarvisApp"
        copied = copy_source(target)
        assert copied > 15
        assert not (target / "STORE-LISTING-DRAFT.md").exists()
        assert not (target / ".github" / "workflows" / "store-msix.yml").exists()
        run_local_tests(Path(sys.executable), target)
        print("PASS: clean-source personal installer runs all runtime tests without Store files")


if __name__ == "__main__":
    main()
