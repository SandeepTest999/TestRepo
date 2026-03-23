"""
Results folder poller: periodically checks file count and triggers the
comparator automatically when results arrive.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

import config
from utils import PollingTimeoutError, get_logger

logger = get_logger(__name__)


class ResultsPoller:
    """Poll a local results folder and fire a callback when files appear.

    Parameters
    ----------
    results_folder:
        Path to the folder that will receive result files.
    on_results_ready:
        Callback invoked with the results folder path once files are
        detected.  This is where :class:`comparator.Comparator` is
        triggered.
    interval_seconds:
        How often to check the folder (default: ``POLLING_INTERVAL_SECONDS``).
    timeout_seconds:
        Maximum time to poll before raising :class:`PollingTimeoutError`
        (default: ``POLLING_TIMEOUT_SECONDS``).
    expected_file_count:
        If > 0, polling waits until at least this many files are present.
        If 0, any non-empty folder is treated as ready.
    """

    def __init__(
        self,
        results_folder: Path,
        on_results_ready: Callable[[Path], None],
        interval_seconds: int = config.POLLING_INTERVAL_SECONDS,
        timeout_seconds: int = config.POLLING_TIMEOUT_SECONDS,
        expected_file_count: int = 0,
    ) -> None:
        self._results_folder = results_folder
        self._on_results_ready = on_results_ready
        self._interval = interval_seconds
        self._timeout = timeout_seconds
        self._expected = expected_file_count
        self._stop_flag = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def poll(self) -> int:
        """Block and poll until results arrive (or timeout).

        Returns the file count detected when polling stops.
        Raises :class:`PollingTimeoutError` on timeout.
        """
        self._stop_flag = False
        self._results_folder.mkdir(parents=True, exist_ok=True)
        elapsed = 0.0

        logger.info(
            "Polling '%s' every %ds (timeout: %ds)…",
            self._results_folder,
            self._interval,
            self._timeout,
        )

        while not self._stop_flag:
            count = self._count_files()
            logger.debug("Poll check: %d file(s) in results folder.", count)

            if self._is_ready(count):
                logger.info(
                    "Results ready: %d file(s) detected. Triggering comparison.",
                    count,
                )
                self._on_results_ready(self._results_folder)
                return count

            if elapsed >= self._timeout:
                raise PollingTimeoutError(
                    f"Polling timed out after {self._timeout}s. "
                    f"No results found in '{self._results_folder}'."
                )

            time.sleep(self._interval)
            elapsed += self._interval

        logger.info("Polling stopped by stop() call.")
        return self._count_files()

    def stop(self) -> None:
        """Request the polling loop to exit on the next iteration."""
        self._stop_flag = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _count_files(self) -> int:
        if not self._results_folder.exists():
            return 0
        return sum(1 for p in self._results_folder.iterdir() if p.is_file())

    def _is_ready(self, count: int) -> bool:
        if self._expected > 0:
            return count >= self._expected
        return count > 0
