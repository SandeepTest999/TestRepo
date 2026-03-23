"""
FTP handler: upload and download operations with session-cached credentials
and configurable retry/exponential-backoff.
"""

from __future__ import annotations

import ftplib
import time
from pathlib import Path
from typing import Optional

import config
from credentials_manager import CredentialsManager
from utils import FTPError, get_logger

logger = get_logger(__name__)


def _backoff(attempt: int) -> float:
    """Return the backoff delay (seconds) for the given attempt index (0-based)."""
    return config.RETRY_BACKOFF_BASE ** attempt


class FTPHandler:
    """Perform FTP upload and download operations.

    Parameters
    ----------
    credentials_manager:
        The application-wide :class:`CredentialsManager` instance.
    retry_count:
        Maximum number of retry attempts on failure.
    """

    def __init__(
        self,
        credentials_manager: CredentialsManager,
        retry_count: int = config.RETRY_COUNT,
    ) -> None:
        self._creds_mgr = credentials_manager
        self._retry_count = retry_count

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upload(self, local_path: Path, remote_path: str) -> None:
        """Upload *local_path* to *remote_path* on the FTP server.

        Raises FTPError after exhausting retries.
        """
        self._with_retry("upload", self._do_upload, local_path, remote_path)

    def download(self, remote_path: str, local_path: Path) -> None:
        """Download *remote_path* from the FTP server to *local_path*.

        Raises FTPError after exhausting retries.
        """
        self._with_retry("download", self._do_download, remote_path, local_path)

    def test_connection(self) -> bool:
        """Return True if an FTP connection can be established successfully."""
        try:
            creds = self._creds_mgr.get_credentials()
            with ftplib.FTP() as ftp:
                ftp.connect(creds.host, creds.port, timeout=config.FTP_TIMEOUT_SECONDS)
                ftp.login(creds.username, creds.password)
            return True
        except Exception as exc:
            logger.warning("FTP connection test failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _do_upload(self, local_path: Path, remote_path: str) -> None:
        creds = self._creds_mgr.get_credentials()
        with ftplib.FTP() as ftp:
            ftp.connect(creds.host, creds.port, timeout=config.FTP_TIMEOUT_SECONDS)
            ftp.login(creds.username, creds.password)
            with open(local_path, "rb") as f:
                ftp.storbinary(f"STOR {remote_path}", f)
        logger.info("FTP upload complete: '%s' -> '%s'.", local_path, remote_path)

    def _do_download(self, remote_path: str, local_path: Path) -> None:
        creds = self._creds_mgr.get_credentials()
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with ftplib.FTP() as ftp:
            ftp.connect(creds.host, creds.port, timeout=config.FTP_TIMEOUT_SECONDS)
            ftp.login(creds.username, creds.password)
            with open(local_path, "wb") as f:
                ftp.retrbinary(f"RETR {remote_path}", f.write)
        logger.info("FTP download complete: '%s' -> '%s'.", remote_path, local_path)

    def _with_retry(self, operation: str, fn, *args) -> None:
        last_exc: Optional[Exception] = None
        for attempt in range(self._retry_count + 1):
            try:
                fn(*args)
                return
            except Exception as exc:
                last_exc = exc
                if attempt < self._retry_count:
                    delay = _backoff(attempt)
                    logger.warning(
                        "FTP %s failed (attempt %d/%d): %s. Retrying in %.1fs…",
                        operation,
                        attempt + 1,
                        self._retry_count + 1,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "FTP %s failed after %d attempt(s): %s",
                        operation,
                        self._retry_count + 1,
                        exc,
                    )
        raise FTPError(
            f"FTP {operation} failed after {self._retry_count + 1} attempt(s): {last_exc}"
        ) from last_exc
