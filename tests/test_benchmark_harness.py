"""Benchmark harness tests: no Codex, network, or paid inference."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("live_bench", HERE / "benchmarks/live_codex.py")
live = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(live)


class BenchmarkHarnessTests(unittest.TestCase):
    def test_dry_run_never_invokes_model(self):
        x = subprocess.run(
            [sys.executable, str(HERE / "benchmarks/live_codex.py"),
             "--model", "gpt-6-sol", "--seeds", "1,2", "--arms",
             "cold-plain,cold-forge"],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(x.returncode, 0, x.stderr)
        self.assertIn("DRY_RUN_ONLY_NO_MODEL_CALLED", x.stdout)
        self.assertIn('"codex_calls_if_executed": 12', x.stdout)

    def test_hidden_grader_rejects_wrong_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            truth = live.fixture(directory, seed=112, forge=False)
            self.assertFalse(live.verify(directory, truth)[0])
            (directory / "worker.py").write_text(
                f"def transform(value):\n"
                f"    return (value * {truth['factor']} + {truth['bias']}) % 251\n")
            (directory / "ephemeral_probe.py").unlink()
            self.assertTrue(live.verify(directory, truth)[0])

    def test_resume_uses_exact_thread_and_never_ambient_last(self):
        baseline = live.codex_invocation('cold-plain', '', 2)
        self.assertNotIn('resume', baseline)
        with self.assertRaises(ValueError):
            live.codex_invocation('resume-forge', '', 2)
        exact = live.codex_invocation('resume-forge', '', 2,
                                      thread_id='0199a213-81c0-7800-8aa1-bbab2a035a53')
        self.assertIn('resume', exact)
        self.assertNotIn('--last', exact)
        self.assertIn('0199a213-81c0-7800-8aa1-bbab2a035a53', exact)

    def test_native_compaction_is_not_inferred_from_token_use(self):
        events = [
            {"type": "thread.started", "thread_id": "test"},
            {"type": "turn.completed", "usage": {
                "input_tokens": 100000, "cached_input_tokens": 100,
                "output_tokens": 1000, "reasoning_output_tokens": 50
            }}
        ]
        usage, compacted = live.summarize_events(events)
        self.assertEqual(usage["input_tokens"], 100000)
        self.assertEqual(compacted, [])
        events.append({"type": "thread.compacted"})
        _, compacted = live.summarize_events(events)
        self.assertEqual(compacted, ["thread.compacted"])


if __name__ == "__main__":
    unittest.main()
