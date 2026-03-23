"""Unit tests for ssg_generator.py"""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import config
from file_manager import FileManager
from ssg_generator import SSGGenerator


class TestSSGGenerator(unittest.TestCase):

    def _make_generator(self, tmp_path: Path) -> SSGGenerator:
        """Create an SSGGenerator backed by a FileManager rooted at tmp_path."""
        fm = MagicMock(spec=FileManager)
        fm.save_script.side_effect = lambda name, content: tmp_path / name
        fm.temp_folder = tmp_path
        return SSGGenerator(fm)

    # ------------------------------------------------------------------
    # generate
    # ------------------------------------------------------------------

    def test_generate_returns_default_template(self):
        gen = SSGGenerator(MagicMock(spec=FileManager))
        script = gen.generate()
        self.assertIn("@SSG", script)
        self.assertIn("SGS.", script)
        self.assertIn("@EOF", script)
        self.assertIn("SKEL", script)
        self.assertIn("*MESSAGE SCRIPT IS STARTED. TEST PASS", script)

    def test_generate_matches_config_template(self):
        gen = SSGGenerator(MagicMock(spec=FileManager))
        self.assertEqual(gen.generate(), config.SSG_SCRIPT_TEMPLATE)

    # ------------------------------------------------------------------
    # save
    # ------------------------------------------------------------------

    def test_save_stores_script(self, tmp_path=None):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            fm = MagicMock(spec=FileManager)
            saved = td_path / "ssg_test.txt"
            fm.save_script.return_value = saved

            gen = SSGGenerator(fm)
            result_path = gen.save(config.SSG_SCRIPT_TEMPLATE, "ssg_test.txt")

            fm.save_script.assert_called_once_with(
                "ssg_test.txt", config.SSG_SCRIPT_TEMPLATE
            )
            self.assertEqual(gen.final_script, config.SSG_SCRIPT_TEMPLATE)
            self.assertEqual(gen.saved_path, saved)

    # ------------------------------------------------------------------
    # review_and_edit (with mocked input)
    # ------------------------------------------------------------------

    @patch("builtins.input", return_value="A")
    def test_review_accept_as_is(self, _mock_input):
        gen = SSGGenerator(MagicMock(spec=FileManager))
        script = config.SSG_SCRIPT_TEMPLATE
        result = gen.review_and_edit(script)
        self.assertEqual(result, script)

    @patch("builtins.input", side_effect=["T", "NEW CONTENT", "END"])
    def test_review_inline_replacement(self, _mock_input):
        gen = SSGGenerator(MagicMock(spec=FileManager))
        result = gen.review_and_edit(config.SSG_SCRIPT_TEMPLATE)
        self.assertIn("NEW CONTENT", result)

    # ------------------------------------------------------------------
    # initial state
    # ------------------------------------------------------------------

    def test_initial_final_script_is_none(self):
        gen = SSGGenerator(MagicMock(spec=FileManager))
        self.assertIsNone(gen.final_script)
        self.assertIsNone(gen.saved_path)


if __name__ == "__main__":
    unittest.main()
