"""
SSG script generator: creates the test script locally, presents it to the
user for review/editing, and saves the final version to the temp folder.
"""

from __future__ import annotations

import tempfile
import subprocess
import shutil
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import config
from file_manager import FileManager
from utils import SSGGenerationError, get_logger

logger = get_logger(__name__)


class SSGGenerator:
    """Generate, review, and persist SSG scripts.

    Parameters
    ----------
    file_manager:
        The application-wide :class:`FileManager` instance.
    """

    def __init__(self, file_manager: FileManager) -> None:
        self._file_manager = file_manager
        self._final_script: Optional[str] = None
        self._saved_path: Optional[Path] = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def final_script(self) -> Optional[str]:
        """Return the final (possibly user-edited) script content."""
        return self._final_script

    @property
    def saved_path(self) -> Optional[Path]:
        """Return the path where the script was last saved."""
        return self._saved_path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self) -> str:
        """Generate the default SSG script and return its content."""
        script = config.SSG_SCRIPT_TEMPLATE
        logger.info("SSG script generated.")
        return script

    def review_and_edit(self, script: str) -> str:
        """Present *script* to the user and allow editing.

        The user is shown the script content in the terminal and given
        the option to:
          1. Accept as-is
          2. Open in a text editor (uses $EDITOR or notepad/nano/vi as fallback)
          3. Type a replacement inline

        Returns the final (possibly edited) script content.
        """
        print("\n" + "=" * 60)
        print("Generated SSG Script (please review):")
        print("=" * 60)
        print(script)
        print("=" * 60)

        while True:
            print("\nOptions:")
            print("  [A] Accept script as-is")
            print("  [E] Open in editor")
            print("  [T] Type replacement script inline")
            choice = input("Your choice [A/E/T]: ").strip().upper()

            if choice == "A":
                logger.info("User accepted the SSG script as-is.")
                return script

            if choice == "E":
                edited = self._open_in_editor(script)
                logger.info("User edited the SSG script in an external editor.")
                return edited

            if choice == "T":
                print("Enter the new script content. Type END on a line by itself to finish:")
                lines = []
                while True:
                    line = input()
                    if line.strip() == "END":
                        break
                    lines.append(line)
                edited = "\n".join(lines) + "\n"
                logger.info("User provided a replacement SSG script inline.")
                return edited

            print("Invalid choice. Please enter A, E, or T.")

    def save(self, script: str, filename: Optional[str] = None) -> Path:
        """Save *script* to the temp folder.

        Parameters
        ----------
        script:
            The script content to persist.
        filename:
            Optional explicit filename; defaults to a timestamped name.

        Returns the path to the saved file.
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ssg_script_{timestamp}.txt"

        self._final_script = script
        self._saved_path = self._file_manager.save_script(filename, script)
        logger.info("SSG script saved to '%s'.", self._saved_path)
        return self._saved_path

    def generate_review_and_save(self) -> Path:
        """Convenience: generate → user review → save.

        Returns the path to the saved script.
        """
        raw_script = self.generate()
        final_script = self.review_and_edit(raw_script)
        return self.save(final_script)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _open_in_editor(self, initial_content: str) -> str:
        """Write *initial_content* to a temp file, open an editor, and
        return the (possibly modified) content.
        """
        editor = (
            os.environ.get("EDITOR")
            or os.environ.get("VISUAL")
            or self._detect_editor()
        )

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp.write(initial_content)
            tmp_path = tmp.name

        try:
            subprocess.run([editor, tmp_path], check=True)
            with open(tmp_path, encoding="utf-8") as f:
                return f.read()
        except Exception as exc:
            raise SSGGenerationError(f"Failed to open editor '{editor}': {exc}") from exc
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    @staticmethod
    def _detect_editor() -> str:
        """Return a best-guess editor available on the current platform."""

        for candidate in ("nano", "vi", "vim", "notepad"):
            if shutil.which(candidate):
                return candidate
        return "vi"
