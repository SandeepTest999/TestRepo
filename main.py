"""
Entry point for the OS2200 test package automation workflow.

Usage:
    python main.py [--telnet-host HOST] [--telnet-port PORT]
                   [--ftp-upload-path PATH] [--ftp-results-path PATH]
                   [--log-level LEVEL]
"""

from __future__ import annotations

import argparse
import signal
import sys

import utils
from workflow_manager import WorkflowManager, WorkflowState


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="testrepo",
        description="OS2200 test package automation workflow",
    )
    parser.add_argument(
        "--telnet-host",
        default="localhost",
        help="Hostname or IP of the OS2200 TELNET target (default: localhost)",
    )
    parser.add_argument(
        "--telnet-port",
        type=int,
        default=23,
        help="TELNET port (default: 23)",
    )
    parser.add_argument(
        "--ftp-upload-path",
        default="/upload/ssg_script.txt",
        help="Remote FTP path for SSG script upload",
    )
    parser.add_argument(
        "--ftp-results-path",
        default="/results/results_archive.tar",
        help="Remote FTP path for results download",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity level (default: INFO)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point.  Returns an exit code (0 = success)."""
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    # Initialise logging
    import logging
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    utils.setup_logging(log_level)
    logger = utils.get_logger(__name__)

    logger.info("OS2200 test package automation starting.")

    # Build workflow manager
    manager = WorkflowManager(
        telnet_host=args.telnet_host,
        telnet_port=args.telnet_port,
        ftp_remote_upload_path=args.ftp_upload_path,
        ftp_remote_results_path=args.ftp_results_path,
    )

    # Graceful Ctrl-C handling
    def _signal_handler(sig, frame):
        print("\n\nInterrupt received. Aborting workflow…")
        manager.abort()
        sys.exit(1)

    signal.signal(signal.SIGINT, _signal_handler)

    # Run the workflow
    try:
        manager.run()
    except Exception as exc:
        logger.exception("Unexpected error: %s", exc)
        return 1

    return 0 if manager.state == WorkflowState.COMPLETED else 1


if __name__ == "__main__":
    sys.exit(main())
