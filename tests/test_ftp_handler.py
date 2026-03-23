"""Unit tests for ftp_handler.py"""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

from credentials_manager import CredentialsManager, Credentials
from ftp_handler import FTPHandler
from utils import FTPError


class TestFTPHandler(unittest.TestCase):

    def _make_handler(self, retry_count=1):
        mgr = CredentialsManager()
        mgr.set_credentials("ftp.example.com", "user", "pass", port=21)
        return FTPHandler(mgr, retry_count=retry_count)

    # ------------------------------------------------------------------
    # test_connection
    # ------------------------------------------------------------------

    @patch("ftp_handler.ftplib.FTP")
    def test_test_connection_success(self, mock_ftp_cls):
        mock_ftp = MagicMock()
        mock_ftp_cls.return_value.__enter__ = lambda s: mock_ftp
        mock_ftp_cls.return_value.__exit__ = MagicMock(return_value=False)

        handler = self._make_handler()
        result = handler.test_connection()
        self.assertTrue(result)

    @patch("ftp_handler.ftplib.FTP")
    def test_test_connection_failure(self, mock_ftp_cls):
        mock_ftp_cls.return_value.__enter__.side_effect = OSError("refused")
        mock_ftp_cls.return_value.__exit__ = MagicMock(return_value=False)

        handler = self._make_handler()
        result = handler.test_connection()
        self.assertFalse(result)

    # ------------------------------------------------------------------
    # upload
    # ------------------------------------------------------------------

    @patch("builtins.open", mock_open(read_data=b"data"))
    @patch("ftp_handler.ftplib.FTP")
    def test_upload_success(self, mock_ftp_cls):
        mock_ftp = MagicMock()
        mock_ftp_cls.return_value.__enter__ = lambda s: mock_ftp
        mock_ftp_cls.return_value.__exit__ = MagicMock(return_value=False)

        handler = self._make_handler()
        handler.upload(Path("/tmp/script.txt"), "/remote/script.txt")
        mock_ftp.storbinary.assert_called_once()

    @patch("ftp_handler.time.sleep", return_value=None)
    @patch("ftp_handler.ftplib.FTP")
    def test_upload_retries_and_fails(self, mock_ftp_cls, _sleep):
        mock_ftp_cls.return_value.__enter__.side_effect = OSError("connection refused")
        mock_ftp_cls.return_value.__exit__ = MagicMock(return_value=False)

        handler = self._make_handler(retry_count=2)
        with self.assertRaises(FTPError):
            handler.upload(Path("/tmp/script.txt"), "/remote/script.txt")

    # ------------------------------------------------------------------
    # download
    # ------------------------------------------------------------------

    @patch("ftp_handler.ftplib.FTP")
    def test_download_success(self, mock_ftp_cls):
        mock_ftp = MagicMock()
        mock_ftp_cls.return_value.__enter__ = lambda s: mock_ftp
        mock_ftp_cls.return_value.__exit__ = MagicMock(return_value=False)

        handler = self._make_handler()
        with patch("builtins.open", mock_open()):
            handler.download("/remote/result.txt", Path("/tmp/result.txt"))
        mock_ftp.retrbinary.assert_called_once()

    # ------------------------------------------------------------------
    # No credentials
    # ------------------------------------------------------------------

    def test_upload_raises_when_no_credentials(self):
        mgr = CredentialsManager()  # no credentials set
        handler = FTPHandler(mgr, retry_count=0)
        with self.assertRaises(Exception):
            handler.upload(Path("/tmp/x.txt"), "/remote/x.txt")


if __name__ == "__main__":
    unittest.main()
