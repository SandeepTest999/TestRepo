"""Unit tests for telnet_handler.py"""

import unittest
from unittest.mock import MagicMock, patch

from telnet_handler import TelnetHandler
from utils import TelnetError


class TestTelnetHandler(unittest.TestCase):

    # ------------------------------------------------------------------
    # connect
    # ------------------------------------------------------------------

    @patch("telnet_handler.telnetlib.Telnet")
    def test_connect_success(self, mock_telnet_cls):
        mock_conn = MagicMock()
        mock_telnet_cls.return_value = mock_conn

        handler = TelnetHandler("host", 23, retry_count=1)
        handler.connect()
        self.assertTrue(handler.is_connected())

    @patch("telnet_handler.time.sleep", return_value=None)
    @patch("telnet_handler.telnetlib.Telnet")
    def test_connect_retries_and_fails(self, mock_telnet_cls, _sleep):
        mock_telnet_cls.side_effect = OSError("refused")

        handler = TelnetHandler("host", 23, retry_count=2)
        with self.assertRaises(TelnetError):
            handler.connect()

    # ------------------------------------------------------------------
    # disconnect
    # ------------------------------------------------------------------

    @patch("telnet_handler.telnetlib.Telnet")
    def test_disconnect(self, mock_telnet_cls):
        mock_conn = MagicMock()
        mock_telnet_cls.return_value = mock_conn

        handler = TelnetHandler("host", 23)
        handler.connect()
        handler.disconnect()
        self.assertFalse(handler.is_connected())

    # ------------------------------------------------------------------
    # execute_script
    # ------------------------------------------------------------------

    @patch("telnet_handler.telnetlib.Telnet")
    def test_execute_script_success(self, mock_telnet_cls):
        mock_conn = MagicMock()
        mock_conn.read_until.return_value = b"OK\n"
        mock_telnet_cls.return_value = mock_conn

        handler = TelnetHandler("host", 23)
        handler.connect()
        response = handler.execute_script("@SSG\nSGS.\n@EOF\n")
        self.assertEqual(response, "OK")

    def test_execute_script_raises_when_not_connected(self):
        handler = TelnetHandler("host", 23)
        with self.assertRaises(TelnetError):
            handler.execute_script("@SSG\n")

    # ------------------------------------------------------------------
    # execute_script_with_retry
    # ------------------------------------------------------------------

    @patch("telnet_handler.time.sleep", return_value=None)
    @patch("telnet_handler.telnetlib.Telnet")
    def test_execute_with_retry_reconnects(self, mock_telnet_cls, _sleep):
        # First connect succeeds; execute_script fails once then succeeds
        mock_conn = MagicMock()
        mock_conn.read_until.side_effect = [OSError("read error"), b"OK\n"]
        mock_telnet_cls.return_value = mock_conn

        handler = TelnetHandler("host", 23, retry_count=2)
        response = handler.execute_script_with_retry("@SSG\n")
        self.assertEqual(response, "OK")


if __name__ == "__main__":
    unittest.main()
