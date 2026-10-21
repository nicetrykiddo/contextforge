#!/usr/bin/env python3
"""Deterministic CONTEXT SYSTEM benchmark. No LLM inference occurs here.

Measurements: recoverability, isolation, bounded output, CLI latency, state size.
NEVER report these numbers as task-success uplift or automatic compaction.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "ctx.py"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--noise", type=int, default=48)
    p.add_argument("--replays", type=int, default=12)
    p.add_argument("--output", default="")
    args = p.parse_args()
    if not (2 <= args.noise <= 500 and 1 <= args.replays <= 100):
        p.error("noise=2..500, replays=1..100")
    with tempfile.TemporaryDirectory(prefix="contextforge-eval-") as temporary:
        parent = Path(temporary)
        root = parent / "workspace"
        env = dict(os.environ, XDG_CONFIG_HOME=str(parent / "config"))
        def run(*commands, check=True):
            t0 = time.perf_counter_ns()
            result = subprocess.run([sys.executable, str(CLI), "--root", str(root),
                                     *map(str, commands)],
                                    env=env, capture_output=True, text=True, timeout=30)
            elapsed = (time.perf_counter_ns() - t0) / 1e6
            if check and result.returncode:
                raise RuntimeError(f"{commands}: {result.stderr}\n{result.stdout}")
            return result.stdout, elapsed, result
        run("init", "--mode", "bugbounty")
        task_a = run("task", "add", "Alpha parser", "--goal",
                     "Investigate canonicalization with token ALPHA-SIGNAL-17")[0].split()[0]
        (root / ".ctx" / "MISSION.md").write_text(
            "# Mission Alpha\nCorrectness predicate: ALPHA-MISSION-913\n")
        run("checkpoint", "--summary", "Alpha repro proves ALPHA-CHECKPOINT-719",
            "--next", "Recheck alpha parser with fixture A")
        task_b = run("task", "add", "Beta serializer", "--goal",
                     "Investigate serialization with token BETA-SIGNAL-32")[0].split()[0]
        task_b_card = root / ".ctx" / "tasks" / task_b / "MISSION.md"
        task_b_card.write_text("# Mission Beta\nCorrectness predicate: BETA-MISSION-457\n")
        run("task", "focus", task_b)
        run("checkpoint", "--summary", "Beta repro proves BETA-CHECKPOINT-289",
            "--next", "Recheck beta serializer with fixture B")
        for i in range(args.noise):
            run("pin", "--title", f"Older clue number {i}",
                "--body", f"Unrelated trace event {i} " + "padding " * 20,
                "--proof", f"synthetic-fixture.txt:{i+1}", "--status", "unverified")
        run("add", "--kind", "finding", "--status", "verified",
            "--title", "RAVEN-ORACLE-FINDING",
            "--body", "Only the raven oracle distinguishes the two outputs.",
            "--proof", "synthetic-fixture.txt:999")
        cases = []
        latencies = []
        for task, key, foreign in [
            (task_a, "ALPHA-CHECKPOINT-719", "BETA-CHECKPOINT-289"),
            (task_b, "BETA-CHECKPOINT-289", "ALPHA-CHECKPOINT-719"),
        ]:
            run("task", "focus", task)
            for budget in (100, 350, 800, 1500):
                text, milliseconds, _ = run("context", "--budget", budget)
                cases.append({
                    "scenario": "fresh_process_after_context_loss",
                    "task": task, "budget_estimated_tokens": budget,
                    "has_correct_checkpoint": key in text,
                    "leaked_other_checkpoint": foreign in text,
                    "within_approximate_budget": len(text) <= budget * 4 + 1,
                    "output_characters": len(text)
                })
                latencies.append(milliseconds)
        text, _, _ = run("context", "--query", "raven", "--budget", 350)
        cases.append({"scenario": "relevant_evidence_behind_noise",
                      "passed": "RAVEN-ORACLE-FINDING" in text,
                      "noise_records": args.noise})
        file = parent / "config" / "contextforge" / "reasoning.json"
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("{ broken JSON")
        text, _, _ = run("context", "--budget", 1500)
        cases.append({"scenario": "corrupted_optional_global_store",
                      "passed": "BETA-CHECKPOINT-289" in text and
                                "Optional global reasoning unavailable" in text})
        run("snapshot")
        archive = sorted((root / ".ctx" / "compactions").glob("*.zip"))[-1]
        with zipfile.ZipFile(archive) as z:
            names = set(z.namelist())
        cases.append({"scenario": "durable_snapshot_contains_target_cards",
                      "passed": all(f"tasks/{tid}/MISSION.md" in names
                                    for tid in (task_a, task_b))})
        for _ in range(args.replays):
            _text, ms, _ = run("context", "--budget", 800)
            latencies.append(ms)
        record_file = root / ".ctx" / "records.jsonl"
        results = {
            "kind": "DETERMINISTIC_MEMORY_BENCHMARK_NOT_MODEL_EVAL",
            "git_commit": os.getenv("GITHUB_SHA", "local"),
            "python": sys.version.split()[0],
            "noise_records": args.noise,
            "fresh_process_replays": args.replays,
            "cases": cases,
            "all_checks_pass": all(c.get("passed", (
                c.get("has_correct_checkpoint", False) and
                not c.get("leaked_other_checkpoint", True) and
                c.get("within_approximate_budget", False)))
                for c in cases),
            "cli_context_latency_ms": {
                "median": round(statistics.median(latencies), 2),
                "p95": round(sorted(latencies)[min(len(latencies)-1, int(0.95*len(latencies)))], 2),
                "n": len(latencies),
            },
            "durable_records_bytes": record_file.stat().st_size,
            "limitations": [
                "This did not invoke a language model or Codex.",
                "No native compaction, cache expiry, or Plus quota was exercised.",
                "Tasks and evidence were seeded; no agent discovered or saved them.",
                "4 characters/token is only an approximate budget.",
                "CLI timings include Python process startup; hardware and load vary."
            ]
        }
        if args.output:
            dest = Path(args.output)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(results, indent=2) + "\n")
        print(json.dumps(results, indent=2))
        return 0 if results["all_checks_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
