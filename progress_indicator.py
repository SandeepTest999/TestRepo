"""
Visual progress indicator for the OS2200 workflow steps.

Displays each step with its current status using Unicode emoji and
supports terminal-based real-time updates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


_STATUS_ICONS = {
    StepStatus.PENDING: "⏳",
    StepStatus.RUNNING: "🔄",
    StepStatus.COMPLETED: "✅",
    StepStatus.FAILED: "❌",
    StepStatus.PAUSED: "⏸️ ",
}


@dataclass
class Step:
    number: int
    name: str
    status: StepStatus = StepStatus.PENDING
    message: str = ""


class ProgressIndicator:
    """Terminal-based progress display for the workflow.

    Maintains a list of :class:`Step` objects and prints a formatted
    status table each time ``render()`` is called.
    """

    WORKFLOW_STEPS = [
        "Collect FTP credentials",
        "Generate SSG script (user review)",
        "FTP upload",
        "TELNET execution",
        "Poll for results",
        "FTP results retrieval",
        "Run comparison",
    ]

    def __init__(self) -> None:
        self._steps: List[Step] = [
            Step(number=i + 1, name=name)
            for i, name in enumerate(self.WORKFLOW_STEPS)
        ]
        self._workflow_complete = False

    # ------------------------------------------------------------------
    # Status updates
    # ------------------------------------------------------------------

    def set_status(
        self,
        step_number: int,
        status: StepStatus,
        message: str = "",
    ) -> None:
        """Update the status of *step_number* (1-based)."""
        step = self._get_step(step_number)
        step.status = status
        step.message = message

    def mark_running(self, step_number: int, message: str = "") -> None:
        self.set_status(step_number, StepStatus.RUNNING, message)

    def mark_completed(self, step_number: int, message: str = "") -> None:
        self.set_status(step_number, StepStatus.COMPLETED, message)

    def mark_failed(self, step_number: int, message: str = "") -> None:
        self.set_status(step_number, StepStatus.FAILED, message)

    def mark_paused(self, step_number: int, message: str = "") -> None:
        self.set_status(step_number, StepStatus.PAUSED, message)

    def mark_workflow_complete(self) -> None:
        """Mark the entire workflow as complete (Test Package Completed)."""
        self._workflow_complete = True

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self) -> None:
        """Print the current progress table to stdout."""
        print("\n" + "=" * 55)
        print(" OS2200 Test Package Automation — Workflow Progress")
        print("=" * 55)
        for step in self._steps:
            icon = _STATUS_ICONS[step.status]
            suffix = f"  [{step.message}]" if step.message else ""
            print(f"  Step {step.number}: {icon} {step.name}{suffix}")
        print("=" * 55)
        if self._workflow_complete:
            print("  🎉  Test Package Completed")
            print("=" * 55)
        print()

    def get_status_summary(self) -> dict:
        """Return a dict mapping step names to their current status strings."""
        return {
            step.name: step.status.value
            for step in self._steps
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_step(self, step_number: int) -> Step:
        if step_number < 1 or step_number > len(self._steps):
            raise ValueError(
                f"Step number {step_number} is out of range "
                f"(1–{len(self._steps)})."
            )
        return self._steps[step_number - 1]
