"""
Streamlit web UI for the OS2200 Test Package Automation workflow.

Launch with::

    streamlit run streamlit_app.py

The existing console-based workflow (``python main.py``) is **not** modified.
"""

from __future__ import annotations

import logging
from pathlib import Path

import streamlit as st

import config
import utils
from comparator import Comparator
from credentials_manager import CredentialsManager
from file_manager import FileManager
from ftp_handler import FTPHandler
from pollers import ResultsPoller
from progress_indicator import StepStatus
from ssg_generator import SSGGenerator
from telnet_handler import TelnetHandler
from utils import WorkflowError

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="OS2200 Test Package Automation",
    page_icon="🔧",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STEP_NAMES = {
    1: "Collect FTP credentials",
    2: "Generate SSG script (user review)",
    3: "FTP upload",
    4: "TELNET execution",
    5: "Poll for results",
    6: "FTP results retrieval",
    7: "Run comparison",
}

STATUS_ICONS = {
    StepStatus.PENDING: "⏳",
    StepStatus.RUNNING: "🔄",
    StepStatus.COMPLETED: "✅",
    StepStatus.FAILED: "❌",
    StepStatus.PAUSED: "⏸️",
}

# ---------------------------------------------------------------------------
# Session-state defaults
# ---------------------------------------------------------------------------

_DEFAULTS: dict = {
    "phase": "credentials",  # credentials | script_review | execute | done
    "credentials_mgr": None,
    "file_mgr": None,
    "ftp_handler": None,
    "ssg_script": None,
    "saved_script_path": None,
    "step_statuses": {i: StepStatus.PENDING for i in range(1, 8)},
    "step_messages": {i: "" for i in range(1, 8)},
    "workflow_error": None,
    "comparison_summary": None,
}

for _key, _default in _DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _default


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _set_step(step: int, status: StepStatus, message: str = "") -> None:
    """Update the status of a single workflow step in session state."""
    st.session_state.step_statuses[step] = status
    st.session_state.step_messages[step] = message


def _render_progress() -> None:
    """Render the workflow progress table from session state."""
    for i in range(1, 8):
        status = st.session_state.step_statuses[i]
        icon = STATUS_ICONS[status]
        msg = st.session_state.step_messages[i]
        suffix = f"  —  {msg}" if msg else ""
        st.markdown(f"**Step {i}:** {icon} {STEP_NAMES[i]}{suffix}")

    if all(
        s == StepStatus.COMPLETED
        for s in st.session_state.step_statuses.values()
    ):
        st.success("🎉  Test Package Completed!")


def _reset_workflow() -> None:
    """Reset all session state to defaults."""
    for key, default in _DEFAULTS.items():
        st.session_state[key] = default


# ---------------------------------------------------------------------------
# Sidebar — configuration
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("⚙️  Configuration")

    telnet_host = st.text_input("TELNET Host", value="localhost")
    telnet_port = st.number_input(
        "TELNET Port", value=23, min_value=1, max_value=65535
    )
    ftp_upload_path = st.text_input(
        "FTP Upload Path", value="/upload/ssg_script.txt"
    )
    ftp_results_path = st.text_input(
        "FTP Results Path", value="/results/results_archive.tar"
    )
    log_level = st.selectbox("Log Level", ["INFO", "DEBUG", "WARNING", "ERROR"])

    st.divider()

    if st.button("🔄 Reset Workflow"):
        _reset_workflow()
        st.rerun()

# ---------------------------------------------------------------------------
# Initialise logging (once per session)
# ---------------------------------------------------------------------------

if "logging_initialised" not in st.session_state:
    _log_level = getattr(logging, str(log_level).upper(), logging.INFO)
    utils.setup_logging(_log_level)
    st.session_state["logging_initialised"] = True

# ---------------------------------------------------------------------------
# Title and progress
# ---------------------------------------------------------------------------

st.title("🔧 OS2200 Test Package Automation")
st.caption("Web-based UI for the test package workflow")

with st.expander("📊 Workflow Progress", expanded=True):
    _render_progress()

st.divider()

# ---------------------------------------------------------------------------
# Phase: Credentials
# ---------------------------------------------------------------------------

if st.session_state.phase == "credentials":
    st.header("Step 1: FTP Credentials")

    with st.form("credentials_form"):
        col1, col2 = st.columns(2)
        with col1:
            ftp_host = st.text_input("FTP Host")
            ftp_username = st.text_input("FTP Username")
        with col2:
            ftp_password = st.text_input("FTP Password", type="password")
            ftp_port = st.number_input(
                "FTP Port", value=21, min_value=1, max_value=65535
            )

        submitted = st.form_submit_button("Submit Credentials")

        if submitted:
            if not ftp_host or not ftp_username or not ftp_password:
                st.error("Host, username, and password are required.")
            else:
                creds_mgr = CredentialsManager()
                creds_mgr.set_credentials(
                    ftp_host, ftp_username, ftp_password, int(ftp_port)
                )
                st.session_state.credentials_mgr = creds_mgr
                st.session_state.file_mgr = FileManager()
                st.session_state.ftp_handler = FTPHandler(creds_mgr)
                _set_step(1, StepStatus.COMPLETED, "Credentials cached")
                st.session_state.phase = "script_review"
                st.rerun()

# ---------------------------------------------------------------------------
# Phase: Script Review
# ---------------------------------------------------------------------------

elif st.session_state.phase == "script_review":
    st.header("Step 2: Generate & Review SSG Script")
    st.info(
        "Review the generated SSG script below. "
        "Edit the content if needed, then click **Accept & Continue**."
    )

    _set_step(2, StepStatus.RUNNING)

    edited_script = st.text_area(
        "SSG Script Content",
        value=config.SSG_SCRIPT_TEMPLATE,
        height=200,
    )

    if st.button("✅ Accept & Continue"):
        file_mgr: FileManager = st.session_state.file_mgr
        ssg = SSGGenerator(file_mgr)
        saved_path = ssg.save(edited_script)

        st.session_state.ssg_script = edited_script
        st.session_state.saved_script_path = saved_path
        _set_step(2, StepStatus.COMPLETED, f"Saved to {saved_path.name}")
        st.session_state.phase = "execute"
        st.rerun()

# ---------------------------------------------------------------------------
# Phase: Execute remaining steps (3-7)
# ---------------------------------------------------------------------------

elif st.session_state.phase == "execute":
    st.header("Steps 3–7: Automated Execution")
    st.info("Click the button below to execute the remaining workflow steps.")

    if st.button("▶️ Execute Workflow"):
        ftp_handler: FTPHandler = st.session_state.ftp_handler
        script_path: Path = st.session_state.saved_script_path
        script_content: str = st.session_state.ssg_script
        file_mgr: FileManager = st.session_state.file_mgr

        # -- Step 3: FTP Upload ------------------------------------------------
        with st.status("Step 3: FTP Upload…", expanded=True) as s3:
            _set_step(3, StepStatus.RUNNING)
            try:
                ftp_handler.upload(script_path, ftp_upload_path)
                _set_step(3, StepStatus.COMPLETED, "Upload complete")
                s3.update(label="Step 3: FTP Upload ✅", state="complete")
            except WorkflowError as exc:
                _set_step(3, StepStatus.FAILED, str(exc))
                s3.update(label=f"Step 3: FTP Upload ❌", state="error")
                st.error(f"Step 3 failed: {exc}")
                st.session_state.workflow_error = str(exc)
                st.stop()

        # -- Step 4: TELNET Execution ------------------------------------------
        with st.status("Step 4: TELNET Execution…", expanded=True) as s4:
            _set_step(4, StepStatus.RUNNING)
            try:
                telnet = TelnetHandler(telnet_host, int(telnet_port))
                response = telnet.execute_script_with_retry(script_content)
                _set_step(4, StepStatus.COMPLETED, "Script executed")
                s4.update(label="Step 4: TELNET Execution ✅", state="complete")
                st.code(response, language="text")
            except WorkflowError as exc:
                _set_step(4, StepStatus.FAILED, str(exc))
                s4.update(label=f"Step 4: TELNET Execution ❌", state="error")
                st.error(f"Step 4 failed: {exc}")
                st.session_state.workflow_error = str(exc)
                st.stop()

        # -- Step 5: Poll for Results ------------------------------------------
        with st.status("Step 5: Polling for results…", expanded=True) as s5:
            _set_step(5, StepStatus.RUNNING)
            try:
                poller = ResultsPoller(
                    results_folder=file_mgr.results_folder,
                    on_results_ready=lambda folder: None,
                )
                count = poller.poll()
                _set_step(5, StepStatus.COMPLETED, f"Results detected ({count} file(s))")
                s5.update(label="Step 5: Poll for Results ✅", state="complete")
            except WorkflowError as exc:
                _set_step(5, StepStatus.FAILED, str(exc))
                s5.update(label=f"Step 5: Poll for Results ❌", state="error")
                st.error(f"Step 5 failed: {exc}")
                st.session_state.workflow_error = str(exc)
                st.stop()

        # -- Step 6: FTP Results Retrieval -------------------------------------
        with st.status("Step 6: FTP Results Retrieval…", expanded=True) as s6:
            _set_step(6, StepStatus.RUNNING)
            try:
                local_path = file_mgr.results_folder / "results_archive.tar"
                ftp_handler.download(ftp_results_path, local_path)
                _set_step(6, StepStatus.COMPLETED, "Results downloaded")
                s6.update(
                    label="Step 6: FTP Results Retrieval ✅", state="complete"
                )
            except WorkflowError as exc:
                _set_step(6, StepStatus.FAILED, str(exc))
                s6.update(
                    label=f"Step 6: FTP Results Retrieval ❌", state="error"
                )
                st.error(f"Step 6 failed: {exc}")
                st.session_state.workflow_error = str(exc)
                st.stop()

        # -- Step 7: Comparison ------------------------------------------------
        with st.status("Step 7: Running Comparison…", expanded=True) as s7:
            _set_step(7, StepStatus.RUNNING)
            try:
                comparator = Comparator()
                summary = comparator.run(file_mgr.results_folder)
                _set_step(7, StepStatus.COMPLETED, "Comparison done")
                s7.update(label="Step 7: Comparison ✅", state="complete")
                st.write(f"**Summary:** {summary}")
                st.session_state.comparison_summary = summary
            except WorkflowError as exc:
                _set_step(7, StepStatus.FAILED, str(exc))
                s7.update(label=f"Step 7: Comparison ❌", state="error")
                st.error(f"Step 7 failed: {exc}")
                st.session_state.workflow_error = str(exc)
                st.stop()

        # All steps succeeded
        st.session_state.phase = "done"
        st.rerun()

    if st.session_state.workflow_error:
        st.error(f"Workflow error: {st.session_state.workflow_error}")
        if st.button("🔄 Retry from failed step"):
            st.session_state.workflow_error = None
            st.rerun()

# ---------------------------------------------------------------------------
# Phase: Done
# ---------------------------------------------------------------------------

elif st.session_state.phase == "done":
    st.balloons()
    st.header("✅ Workflow Complete")
    st.success("🎉  All 7 steps completed successfully!")

    if st.session_state.comparison_summary:
        st.subheader("Comparison Summary")
        st.write(st.session_state.comparison_summary)

    st.info(
        "Use the **🔄 Reset Workflow** button in the sidebar to start a new run."
    )
