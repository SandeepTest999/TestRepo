"""
Comparison script: run Python comparison logic on results files.

This module provides a placeholder implementation that can be extended
with real comparison logic.  It is triggered automatically by the poller
when results are detected.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional

from utils import ComparisonError, get_logger

logger = get_logger(__name__)


class Comparator:
    """Execute comparison logic on the results folder.

    Parameters
    ----------
    on_complete:
        Optional callback invoked when comparison finishes successfully.
        Receives the list of result file paths.
    """

    def __init__(self, on_complete: Optional[Callable[[List[Path]], None]] = None) -> None:
        self._on_complete = on_complete
        self._last_result: Optional[str] = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def last_result(self) -> Optional[str]:
        """Return the most recent comparison result summary."""
        return self._last_result

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, results_folder: Path) -> str:
        """Run comparison on all files found in *results_folder*.

        Returns a human-readable result summary string.
        Raises ComparisonError if the folder does not exist or is empty.
        """
        if not results_folder.exists():
            raise ComparisonError(
                f"Results folder does not exist: {results_folder}"
            )

        result_files = [p for p in results_folder.iterdir() if p.is_file()]
        if not result_files:
            raise ComparisonError(
                f"Results folder is empty: {results_folder}"
            )

        logger.info(
            "Running comparison on %d file(s) in '%s'.",
            len(result_files),
            results_folder,
        )

        summary = self._compare(result_files)
        self._last_result = summary
        logger.info("Comparison complete. Summary: %s", summary)

        if self._on_complete:
            self._on_complete(result_files)

        return summary

    # ------------------------------------------------------------------
    # Internal helpers (placeholder – extend with real logic)
    # ------------------------------------------------------------------

    def _compare(self, result_files: List[Path]) -> str:
        """Placeholder comparison implementation.

        Replace this method with the real comparison logic.  It should
        inspect *result_files* and return a summary string.
        """
        file_names = [f.name for f in result_files]
        summary = (
            f"Comparison completed. "
            f"Processed {len(result_files)} file(s): {', '.join(file_names)}. "
            f"Result: PASS (placeholder)"
        )
        return summary
