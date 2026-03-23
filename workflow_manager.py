"""
Workflow manager: orchestrates all steps of the OS2200 test package
automation workflow with step tracking, pause/resume, and retry support.
"""

from __future__ import annotations

import threading
from enum import Enum
from typing import Callable, Dict, List, Optional

from comparator import Comparator
from credentials_manager import CredentialsManager
from file_manager import FileManager
from ftp_handler import FTPHandler
from pollers import ResultsPoller
from progress_indicator import ProgressIndicator, StepStatus
from ssg_generator import SSGGenerator
from telnet_handler import TelnetHandler
from utils import WorkflowError, get_logger

logger = get_logger(__name__)


class WorkflowState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


# Step numbers (1-based) match ProgressIndicator.WORKFLOW_STEPS
STEP_CREDENTIALS = 1
STEP_SSG_GENERATE = 2
STEP_FTP_UPLOAD = 3
STEP_TELNET_EXECUTE = 4
STEP_POLL_RESULTS = 5
STEP_FTP_DOWNLOAD = 6
STEP_COMPARE = 7


class WorkflowManager:
    """Coordinate the full OS2200 test package workflow.

    Parameters
    ----------
    telnet_host:
        Hostname/IP of the OS2200 TELNET target.
    telnet_port:
        TELNET port (default 23).
    ftp_remote_upload_path:
        Remote FTP path for the SSG script upload.
    ftp_remote_results_path:
        Remote FTP path from which results are downloaded.
    """

    def __init__(
        self,
        telnet_host: str = "localhost",
        telnet_port: int = 23,
        ftp_remote_upload_path: str = "/upload/ssg_script.txt",
        ftp_remote_results_path: str = "/results/",
    ) -> None:
        self._telnet_host = telnet_host
        self._telnet_port = telnet_port
        self._ftp_remote_upload = ftp_remote_upload_path
        self._ftp_remote_results = ftp_remote_results_path

        # Shared components
        self.credentials_mgr = CredentialsManager()
        self.file_mgr = FileManager()
        self.progress = ProgressIndicator()

        # Lazy-initialised handlers
        self._ftp: Optional[FTPHandler] = None
        self._telnet: Optional[TelnetHandler] = None
        self._ssg: Optional[SSGGenerator] = None
        self._comparator: Optional[Comparator] = None
        self._poller: Optional[ResultsPoller] = None

        self._state = WorkflowState.IDLE
        self._current_step = 0
        self._pause_event = threading.Event()
        self._pause_event.set()  # not paused initially

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> WorkflowState:
        return self._state

    def run(self) -> None:
        """Execute the full workflow from step 1 to completion."""
        self._state = WorkflowState.RUNNING
        logger.info("Workflow started.")

        # Run cleanup of old temp files at start
        self.file_mgr.cleanup_old_files()

        steps: List[Callable[[], None]] = [
            self._step1_credentials,
            self._step2_ssg_generate,
            self._step3_ftp_upload,
            self._step4_telnet_execute,
            self._step5_poll_results,
            self._step6_ftp_download,
            self._step7_compare,
        ]

        for step_fn in steps:
            if self._state == WorkflowState.PAUSED:
                logger.info("Workflow paused before step %d.", self._current_step + 1)
                self._pause_event.wait()  # block until resume() is called

            try:
                step_fn()
            except WorkflowError as exc:
                self._handle_step_failure(exc)
                return  # Workflow stays paused; caller can call resume() or abort()

        self._state = WorkflowState.COMPLETED
        self.progress.mark_workflow_complete()
        self.progress.render()
        logger.info("Workflow completed successfully.")

    def pause(self) -> None:
        """Pause the workflow before the next step."""
        self._pause_event.clear()
        self._state = WorkflowState.PAUSED
        logger.info("Workflow paused.")

    def resume(self, retry: bool = False) -> None:
        """Resume a paused (or failed) workflow.

        Parameters
        ----------
        retry:
            If True, the failed step will be retried.  Otherwise the
            workflow continues from the next step.
        """
        if retry and self._state == WorkflowState.FAILED:
            self._state = WorkflowState.RUNNING
            logger.info("Retrying failed step %d.", self._current_step)
            self._pause_event.set()
            # Re-run from the failed step
            self._run_from_step(self._current_step)
        else:
            self._state = WorkflowState.RUNNING
            self._pause_event.set()
            logger.info("Workflow resumed.")

    def abort(self) -> None:
        """Abort the workflow."""
        self._state = WorkflowState.FAILED
        if self._poller:
            self._poller.stop()
        logger.warning("Workflow aborted.")

    # ------------------------------------------------------------------
    # Workflow steps
    # ------------------------------------------------------------------

    def _step1_credentials(self) -> None:
        self._current_step = STEP_CREDENTIALS
        self.progress.mark_running(STEP_CREDENTIALS)
        self.progress.render()
        logger.info("Step 1: Collecting FTP credentials.")

        if not self.credentials_mgr.has_credentials():
            self.credentials_mgr.prompt_and_set()

        self._ftp = FTPHandler(self.credentials_mgr)
        self.progress.mark_completed(STEP_CREDENTIALS, "Credentials cached")
        self.progress.render()

    def _step2_ssg_generate(self) -> None:
        self._current_step = STEP_SSG_GENERATE
        self.progress.mark_running(STEP_SSG_GENERATE)
        self.progress.render()
        logger.info("Step 2: Generating SSG script.")

        self._ssg = SSGGenerator(self.file_mgr)
        self._ssg.generate_review_and_save()
        self.progress.mark_completed(
            STEP_SSG_GENERATE, f"Saved to {self._ssg.saved_path.name}"
        )
        self.progress.render()

    def _step3_ftp_upload(self) -> None:
        self._current_step = STEP_FTP_UPLOAD
        self.progress.mark_running(STEP_FTP_UPLOAD)
        self.progress.render()
        logger.info("Step 3: FTP upload.")

        if self._ssg is None or self._ssg.saved_path is None:
            raise WorkflowError(
                "SSG script has not been generated yet. "
                "Ensure Step 2 completes before Step 3."
            )

        self._ftp.upload(self._ssg.saved_path, self._ftp_remote_upload)
        self.progress.mark_completed(STEP_FTP_UPLOAD, "Upload complete")
        self.progress.render()

    def _step4_telnet_execute(self) -> None:
        self._current_step = STEP_TELNET_EXECUTE
        self.progress.mark_running(STEP_TELNET_EXECUTE)
        self.progress.render()
        logger.info("Step 4: TELNET execution.")

        self._telnet = TelnetHandler(self._telnet_host, self._telnet_port)
        script_content = self._ssg.final_script if self._ssg else ""
        response = self._telnet.execute_script_with_retry(script_content or "")
        logger.info("TELNET response: %s", response)
        self.progress.mark_completed(STEP_TELNET_EXECUTE, "Script executed")
        self.progress.render()

    def _step5_poll_results(self) -> None:
        self._current_step = STEP_POLL_RESULTS
        self.progress.mark_running(STEP_POLL_RESULTS)
        self.progress.render()
        logger.info("Step 5: Polling for results.")

        self._poller = ResultsPoller(
            results_folder=self.file_mgr.results_folder,
            on_results_ready=self._on_results_ready,
        )
        self._poller.poll()
        self.progress.mark_completed(STEP_POLL_RESULTS, "Results detected")
        self.progress.render()

    def _step6_ftp_download(self) -> None:
        self._current_step = STEP_FTP_DOWNLOAD
        self.progress.mark_running(STEP_FTP_DOWNLOAD)
        self.progress.render()
        logger.info("Step 6: FTP results retrieval.")

        local_path = self.file_mgr.results_folder / "results_archive.tar"
        self._ftp.download(self._ftp_remote_results, local_path)
        self.progress.mark_completed(STEP_FTP_DOWNLOAD, "Results downloaded")
        self.progress.render()

    def _step7_compare(self) -> None:
        self._current_step = STEP_COMPARE
        self.progress.mark_running(STEP_COMPARE)
        self.progress.render()
        logger.info("Step 7: Running comparison.")

        self._comparator = Comparator(on_complete=self._on_comparison_complete)
        summary = self._comparator.run(self.file_mgr.results_folder)
        logger.info("Comparison summary: %s", summary)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_results_ready(self, results_folder) -> None:
        logger.info("Results ready callback fired for '%s'.", results_folder)

    def _on_comparison_complete(self, result_files) -> None:
        self.progress.mark_completed(STEP_COMPARE, "Comparison done")
        self.progress.mark_workflow_complete()
        self.progress.render()
        logger.info("Comparison complete. Test Package Completed.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _handle_step_failure(self, exc: WorkflowError) -> None:
        self._state = WorkflowState.FAILED
        step_num = self._current_step
        self.progress.mark_failed(step_num, str(exc))
        self.progress.render()
        logger.error("Step %d failed: %s", step_num, exc)
        print(
            f"\n❌  Step {step_num} failed: {exc}\n"
            "    The workflow has been paused. You can retry or abort.\n"
        )

    def _run_from_step(self, start_step: int) -> None:
        """Re-run the workflow starting from *start_step*."""
        all_steps = [
            None,  # placeholder so index matches step number
            self._step1_credentials,
            self._step2_ssg_generate,
            self._step3_ftp_upload,
            self._step4_telnet_execute,
            self._step5_poll_results,
            self._step6_ftp_download,
            self._step7_compare,
        ]
        for step_fn in all_steps[start_step:]:
            if step_fn is None:
                continue
            try:
                step_fn()
            except WorkflowError as exc:
                self._handle_step_failure(exc)
                return

        self._state = WorkflowState.COMPLETED
        self.progress.mark_workflow_complete()
        self.progress.render()
        logger.info("Workflow completed after retry.")
