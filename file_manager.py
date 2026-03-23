"""
File manager: temp folder creation, SSG script storage, and cleanup of
files older than the configured retention period.

The temp folder is placed inside the user's home directory so that no
administrator rights are required.
"""

from __future__ import annotations

import os
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import config
from utils import get_logger

logger = get_logger(__name__)


class FileManager:
    """Manage temporary files and the local results folder."""

    def __init__(
        self,
        temp_folder_name: str = config.TEMP_FOLDER_NAME,
        results_folder_name: str = config.RESULTS_FOLDER_NAME,
        retention_days: int = config.FILE_RETENTION_DAYS,
    ) -> None:
        self._temp_folder: Path = Path.home() / temp_folder_name
        self._results_folder: Path = Path.home() / results_folder_name
        self._retention_days = retention_days

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def temp_folder(self) -> Path:
        """Return (and create if necessary) the temp folder path."""
        self._temp_folder.mkdir(parents=True, exist_ok=True)
        return self._temp_folder

    @property
    def results_folder(self) -> Path:
        """Return (and create if necessary) the results folder path."""
        self._results_folder.mkdir(parents=True, exist_ok=True)
        return self._results_folder

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def save_script(self, filename: str, content: str) -> Path:
        """Save *content* to *filename* inside the temp folder.

        Returns the full path to the saved file.
        """
        dest = self.temp_folder / filename
        dest.write_text(content, encoding="utf-8")
        logger.info("Script saved to '%s'.", dest)
        return dest

    def read_script(self, filename: str) -> str:
        """Read and return the content of *filename* from the temp folder."""
        path = self.temp_folder / filename
        if not path.exists():
            raise FileNotFoundError(f"Script file not found: {path}")
        return path.read_text(encoding="utf-8")

    def list_results(self) -> list[Path]:
        """Return a list of files currently in the results folder."""
        return [p for p in self.results_folder.iterdir() if p.is_file()]

    def results_file_count(self) -> int:
        """Return the number of files in the results folder."""
        return len(self.list_results())

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup_old_files(self) -> int:
        """Delete files in the temp folder older than *retention_days*.

        Returns the number of files deleted.
        """
        cutoff = datetime.now() - timedelta(days=self._retention_days)
        deleted = 0
        if not self._temp_folder.exists():
            return 0
        for path in self._temp_folder.iterdir():
            if not path.is_file():
                continue
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            if mtime < cutoff:
                path.unlink()
                logger.info("Deleted old temp file '%s' (modified: %s).", path.name, mtime)
                deleted += 1
        if deleted:
            logger.info("Cleanup complete: %d file(s) removed.", deleted)
        else:
            logger.debug("Cleanup complete: no files exceeded the retention period.")
        return deleted

    def cleanup_all_temp(self) -> None:
        """Remove all files from the temp folder (manual full cleanup)."""
        if self._temp_folder.exists():
            shutil.rmtree(self._temp_folder)
            logger.info("Temp folder '%s' removed entirely.", self._temp_folder)
