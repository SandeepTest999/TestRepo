"""Unit tests for streamlit_app.py helpers and constants."""

import unittest

from progress_indicator import StepStatus


class TestStreamlitAppConstants(unittest.TestCase):
    """Verify that the streamlit_app module can be introspected safely."""

    # ------------------------------------------------------------------
    # Module-level constants
    # ------------------------------------------------------------------

    def test_step_names_cover_all_seven_steps(self):
        """STEP_NAMES must contain entries for steps 1-7."""
        # Import at function level to avoid Streamlit runtime side-effects
        # during collection; instead test the module-level dict directly.
        from streamlit_app import STEP_NAMES

        self.assertEqual(len(STEP_NAMES), 7)
        for i in range(1, 8):
            self.assertIn(i, STEP_NAMES)
            self.assertIsInstance(STEP_NAMES[i], str)
            self.assertTrue(len(STEP_NAMES[i]) > 0)

    def test_status_icons_map_all_statuses(self):
        from streamlit_app import STATUS_ICONS

        for status in StepStatus:
            self.assertIn(status, STATUS_ICONS)
            self.assertIsInstance(STATUS_ICONS[status], str)

    def test_defaults_contain_expected_keys(self):
        from streamlit_app import _DEFAULTS

        expected_keys = {
            "phase",
            "credentials_mgr",
            "file_mgr",
            "ftp_handler",
            "ssg_script",
            "saved_script_path",
            "step_statuses",
            "step_messages",
            "workflow_error",
            "comparison_summary",
        }
        self.assertEqual(set(_DEFAULTS.keys()), expected_keys)

    def test_defaults_phase_is_credentials(self):
        from streamlit_app import _DEFAULTS

        self.assertEqual(_DEFAULTS["phase"], "credentials")

    def test_defaults_step_statuses_all_pending(self):
        from streamlit_app import _DEFAULTS

        for step_num, status in _DEFAULTS["step_statuses"].items():
            self.assertEqual(status, StepStatus.PENDING)
            self.assertIn(step_num, range(1, 8))


if __name__ == "__main__":
    unittest.main()
