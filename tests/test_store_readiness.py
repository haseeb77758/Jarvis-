"""Store readiness audit must preserve missing publisher/account blockers."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("store_readiness", ROOT / "tools" / "store_readiness.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class StoreReadinessTests(unittest.TestCase):
    def test_repository_preparation_passes_without_partner_center(self):
        problems, owner = module.examine(ROOT)
        self.assertEqual(problems, [])
        self.assertTrue(any("Individual developer" in item for item in owner))
        self.assertTrue(any("privacy" in item.lower() for item in owner))
        self.assertTrue(any("Windows 11 laptop" in item for item in owner))

    def test_empty_repository_is_not_claimed_ready(self):
        with tempfile.TemporaryDirectory() as temp:
            problems, owner = module.examine(Path(temp))
            self.assertGreater(len(problems), 5)
            self.assertTrue(any("app.py" in problem for problem in problems))


if __name__ == "__main__":
    unittest.main()
