"""Unit tests for comparator.py"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from comparator import Comparator
from utils import ComparisonError


class TestComparator(unittest.TestCase):

    # ------------------------------------------------------------------
    # run — success path
    # ------------------------------------------------------------------

    def test_run_returns_summary_with_files(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            (folder / "result1.txt").write_text("pass")
            (folder / "result2.txt").write_text("pass")

            comp = Comparator()
            summary = comp.run(folder)
            self.assertIn("2", summary)
            self.assertEqual(comp.last_result, summary)

    def test_on_complete_callback_is_invoked(self):
        callback = MagicMock()
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            (folder / "result.txt").write_text("data")

            comp = Comparator(on_complete=callback)
            comp.run(folder)
            callback.assert_called_once()
            args = callback.call_args[0][0]
            self.assertIsInstance(args, list)
            self.assertEqual(len(args), 1)

    # ------------------------------------------------------------------
    # run — failure paths
    # ------------------------------------------------------------------

    def test_run_raises_when_folder_missing(self):
        comp = Comparator()
        with self.assertRaises(ComparisonError):
            comp.run(Path("/nonexistent/path/xyz123"))

    def test_run_raises_when_folder_empty(self):
        with tempfile.TemporaryDirectory() as td:
            comp = Comparator()
            with self.assertRaises(ComparisonError):
                comp.run(Path(td))

    # ------------------------------------------------------------------
    # initial state
    # ------------------------------------------------------------------

    def test_last_result_initially_none(self):
        comp = Comparator()
        self.assertIsNone(comp.last_result)

    # ------------------------------------------------------------------
    # placeholder summary content
    # ------------------------------------------------------------------

    def test_summary_contains_pass(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            (folder / "output.txt").write_text("some data")

            comp = Comparator()
            summary = comp.run(folder)
            self.assertIn("PASS", summary)

    def test_summary_mentions_file_name(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            (folder / "myresult.txt").write_text("data")

            comp = Comparator()
            summary = comp.run(folder)
            self.assertIn("myresult.txt", summary)


if __name__ == "__main__":
    unittest.main()
