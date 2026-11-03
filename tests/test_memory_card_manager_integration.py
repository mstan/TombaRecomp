"""Source contract only; no discs, generated code, cards or game processes."""
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
class MemoryCardManagerIntegration(unittest.TestCase):
    def test_all_regional_entry_points_opt_in_before_engine(self):
        for name in ("CMakeLists.txt", "eu/CMakeLists.txt", "eu2/CMakeLists.txt", "jp/CMakeLists.txt"):
            with self.subTest(entry=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                self.assertEqual(text.count("/cmake/MemoryCardManager.cmake"), 1)
                self.assertLess(text.index("/cmake/MemoryCardManager.cmake"), text.index("/runtime/runtime.cmake"))
    def test_shared_option_is_overridable(self):
        text = (ROOT / "cmake/MemoryCardManager.cmake").read_text(encoding="utf-8")
        self.assertIn('option(PSX_MEMORY_CARD_MANAGER', text)
        self.assertIn(' ON)', text)
        self.assertNotIn('FORCE', text)
if __name__ == "__main__":
    unittest.main()
