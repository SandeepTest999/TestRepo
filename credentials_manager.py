"""
Session-cached FTP/TELNET credentials manager.

Credentials are held in memory only for the duration of the application
session.  No persistent storage is used to avoid security risks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from utils import CredentialsError, get_logger

logger = get_logger(__name__)


@dataclass
class Credentials:
    host: str
    username: str
    password: str
    port: int = 21


class CredentialsManager:
    """Manage session-scoped FTP/TELNET credentials in memory."""

    def __init__(self) -> None:
        self._credentials: Optional[Credentials] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_credentials(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 21,
    ) -> None:
        """Cache credentials for the current session."""
        if not host or not username or not password:
            raise CredentialsError("Host, username, and password must not be empty.")
        self._credentials = Credentials(
            host=host.strip(),
            username=username.strip(),
            password=password,
            port=port,
        )
        logger.info("Credentials cached for host '%s' (user: %s).", host, username)

    def get_credentials(self) -> Credentials:
        """Return the cached credentials.

        Raises CredentialsError if no credentials have been set yet.
        """
        if self._credentials is None:
            raise CredentialsError(
                "No credentials available. Call set_credentials() first."
            )
        return self._credentials

    def has_credentials(self) -> bool:
        """Return True if credentials have been cached."""
        return self._credentials is not None

    def clear_credentials(self) -> None:
        """Remove cached credentials from memory."""
        self._credentials = None
        logger.info("Credentials cleared from session cache.")

    def prompt_and_set(self, default_port: int = 21) -> Credentials:
        """Interactively prompt the user for credentials and cache them.

        Uses getpass so the password is not echoed to the terminal.
        """
        import getpass

        print("\n--- FTP Credentials ---")
        host = input("  Host: ").strip()
        username = input("  Username: ").strip()
        password = getpass.getpass("  Password: ")
        port_str = input(f"  Port [{default_port}]: ").strip()
        port = int(port_str) if port_str else default_port

        self.set_credentials(host, username, password, port)
        return self.get_credentials()
