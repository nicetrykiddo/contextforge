"""Regression checks for long-chat memory priority (no target network calls)."""
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = ROOT / "ctx.py"


class ResumePriorityTests(unittest.TestCase):
    def test_checkpoint_survives_pin_overflow_and_history_is_optional(self):
        with tempfile.TemporaryDirectory() as project:
            def cli(*args):
                return subprocess.run(
                    [sys.executable, str(CLI), "--root", project, *args],
                    text=True, capture_output=True, check=True
                ).stdout

            cli("init", "--mode", "bugbounty")
            (pathlib.Path(project) / ".ctx" / "MISSION.md").write_text(
                "# Goal\nInvestigate authorized local fixture.\n", encoding="utf-8"
            )
            cli("task", "add", "Investigate fixture", "--goal", "Find parsing difference")
            cli("checkpoint", "--summary", "PRESERVE THIS DECISIVE STATE",
                "--next", "Compare input A against input B")
            for i in range(12):
                cli("pin", "--title", "Observation " + str(i),
                    "--body", "Detailed investigation finding " * 10,
                    "--status", "verified", "--proof", "local-log.txt:" + str(i + 1))

            short = cli("context", "--budget", "350")
            self.assertIn("PRESERVE THIS DECISIVE STATE", short)
            self.assertIn("Compare input A against input B", short)
            self.assertIn("WARNING: Context incomplete", short)
            self.assertNotIn("Experiment guard:", short)

            detailed = cli("context", "--query", "experiment", "--budget", "1700")
            self.assertIn("Experiment guard:", detailed)


if __name__ == "__main__":
    unittest.main()
