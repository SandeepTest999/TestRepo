"""
TELNET handler: connect to OS2200 and execute SSG scripts with retry support.
"""

from __future__ import annotations

import telnetlib
import time
from typing import Optional

import config
from utils import TelnetError, get_logger

logger = get_logger(__name__)


def _backoff(attempt: int) -> float:
    return config.RETRY_BACKOFF_BASE ** attempt


class TelnetHandler:
    """Establish a TELNET session and execute scripts on OS2200.

    Parameters
    ----------
    host:
        Hostname or IP address of the OS2200 system.
    port:
        TELNET port (default: 23).
    retry_count:
        Maximum number of retry attempts on connection failure.
    """

    def __init__(
        self,
        host: str,
        port: int = config.TELNET_PORT,
        retry_count: int = config.RETRY_COUNT,
    ) -> None:
        self._host = host
        self._port = port
        self._retry_count = retry_count
        self._connection: Optional[telnetlib.Telnet] = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Open a TELNET connection with retry/backoff.

        Raises TelnetError after exhausting retries.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(self._retry_count + 1):
            try:
                logger.info(
                    "Connecting to TELNET %s:%d (attempt %d/%d)…",
                    self._host,
                    self._port,
                    attempt + 1,
                    self._retry_count + 1,
                )
                self._connection = telnetlib.Telnet(
                    self._host, self._port, timeout=config.TELNET_TIMEOUT_SECONDS
                )
                logger.info("TELNET connection established.")
                return
            except Exception as exc:
                last_exc = exc
                if attempt < self._retry_count:
                    delay = _backoff(attempt)
                    logger.warning(
                        "TELNET connection failed (attempt %d/%d): %s. Retrying in %.1fs…",
                        attempt + 1,
                        self._retry_count + 1,
                        exc,
                        delay,
                    )
                    time.sleep(delay)

        raise TelnetError(
            f"TELNET connection to {self._host}:{self._port} failed after "
            f"{self._retry_count + 1} attempt(s): {last_exc}"
        ) from last_exc

    def disconnect(self) -> None:
        """Close the TELNET connection if open."""
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
            finally:
                self._connection = None
            logger.info("TELNET connection closed.")

    def is_connected(self) -> bool:
        """Return True if a TELNET connection is currently open."""
        return self._connection is not None

    # ------------------------------------------------------------------
    # Script execution
    # ------------------------------------------------------------------

    def execute_script(self, script_content: str) -> str:
        """Send *script_content* over the TELNET connection and return the response.

        Raises TelnetError if not connected or if the send/receive fails.
        """
        if not self._connection:
            raise TelnetError("Not connected. Call connect() first.")

        try:
            encoded = (script_content + "\n").encode("ascii")
            self._connection.write(encoded)
            logger.info("Script sent via TELNET (%d bytes).", len(encoded))

            response_bytes = self._connection.read_until(
                b"\n", timeout=config.TELNET_READ_TIMEOUT
            )
            response = response_bytes.decode("ascii", errors="replace").strip()
            logger.debug("TELNET response: %s", response)
            return response
        except TelnetError:
            raise
        except Exception as exc:
            raise TelnetError(f"TELNET script execution failed: {exc}") from exc

    def execute_script_with_retry(self, script_content: str) -> str:
        """Execute *script_content* with automatic reconnect on failure.

        Returns the response string.
        Raises TelnetError after exhausting retries.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(self._retry_count + 1):
            try:
                if not self.is_connected():
                    self.connect()
                return self.execute_script(script_content)
            except TelnetError as exc:
                last_exc = exc
                self.disconnect()
                if attempt < self._retry_count:
                    delay = _backoff(attempt)
                    logger.warning(
                        "TELNET execution failed (attempt %d/%d): %s. Retrying in %.1fs…",
                        attempt + 1,
                        self._retry_count + 1,
                        exc,
                        delay,
                    )
                    time.sleep(delay)

        raise TelnetError(
            f"TELNET script execution failed after {self._retry_count + 1} "
            f"attempt(s): {last_exc}"
        ) from last_exc
