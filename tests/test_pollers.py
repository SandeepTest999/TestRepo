"""Unit tests for pollers.py"""

import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile

from pollers import ResultsPoller
from utils import PollingTimeoutError


class TestResultsPoller(unittest.TestCase):

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_poller(self, folder, callback, interval=1, timeout=5, expected=0):
        return ResultsPoller(
            results_folder=folder,
            on_results_ready=callback,
            interval_seconds=interval,
            timeout_seconds=timeout,
            expected_file_count=expected,
        )

    # ------------------------------------------------------------------
    # Files detected
    # ------------------------------------------------------------------

    def test_detects_existing_files(self):
        callback = MagicMock()
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            (folder / "result.txt").write_text("data")
            poller = self._make_poller(folder, callback, interval=1, timeout=5)
            count = poller.poll()
            self.assertGreater(count, 0)
            callback.assert_called_once_with(folder)

    def test_detects_files_added_during_polling(self):
        callback = MagicMock()
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            poller = self._make_poller(folder, callback, interval=1, timeout=10)

            def _add_file():
                time.sleep(1.5)
                (folder / "result.txt").write_text("data")

            t = threading.Thread(target=_add_file)
            t.start()
            count = poller.poll()
            t.join()
            self.assertGreater(count, 0)
            callback.assert_called_once()

    # ------------------------------------------------------------------
    # Timeout
    # ------------------------------------------------------------------

    def test_raises_on_timeout(self):
        callback = MagicMock()
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)  # empty folder
            poller = self._make_poller(folder, callback, interval=1, timeout=2)
            with self.assertRaises(PollingTimeoutError):
                poller.poll()
            callback.assert_not_called()

    # ------------------------------------------------------------------
    # Expected file count
    # ------------------------------------------------------------------

    def test_waits_for_expected_file_count(self):
        callback = MagicMock()
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            (folder / "file1.txt").write_text("a")
            # Only 1 file, but expected is 2 — should time out
            poller = self._make_poller(folder, callback, interval=1, timeout=2, expected=2)
            with self.assertRaises(PollingTimeoutError):
                poller.poll()

    # ------------------------------------------------------------------
    # stop()
    # ------------------------------------------------------------------

    def test_stop_exits_loop(self):
        callback = MagicMock()
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            poller = self._make_poller(folder, callback, interval=2, timeout=30)

            def _stop_after_delay():
                time.sleep(1)
                poller.stop()

            t = threading.Thread(target=_stop_after_delay)
            t.start()
            poller.poll()
            t.join()
            callback.assert_not_called()


if __name__ == "__main__":
    unittest.main()
