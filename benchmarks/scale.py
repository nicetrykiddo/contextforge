#!/usr/bin/env python3
"""Growth curve for context lookup. No model calls, no external network."""
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import ctx  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="100,1000,5000")
    ap.add_argument("--trials", type=int, default=7)
    ap.add_argument("--output", default="")
    options = ap.parse_args()
    sizes = [int(s) for s in options.sizes.split(",")]
    if not sizes or sorted(sizes) != sizes or sizes[0] < 10 or sizes[-1] > 50000:
        ap.error("sizes must be increasing and between 10 and 50000")
    if not (1 <= options.trials <= 100):
        ap.error("trials must be between 1 and 100")
    results = []
    with tempfile.TemporaryDirectory(prefix="cf-scale-") as td:
        root = Path(td) / "project"
        root.mkdir()
        class Args:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
        with open(os.devnull, "w") as nowhere:
            import contextlib
            with contextlib.redirect_stdout(nowhere):
                ctx.init(Args(root=str(root), name="scale", mode="general", scope="."))
                ctx.task_add(Args(root=str(root), title="Long investigation",
                                  scope=None, goal="Retrieve the UNIQUE-RAVEN-ORACLE finding"))
        state = ctx.load(root)
        tid = state["active_task"]
        (root / ".ctx" / "MISSION.md").write_text(
            "# Long investigation\nExact objective: preserve the correct next action.\n")
        # A very old finding must not disappear after thousands of later records.
        ctx.append(root, {
            "id": "R-raven-anchor", "at": ctx.now(), "task": tid,
            "kind": "finding", "status": "verified",
            "title": "UNIQUE-RAVEN-ORACLE",
            "body": "The raven branch is the only reliable discriminator.",
            "proof": "synthetic-test:repro", "path": None,
            "tags": [], "links": [], "supersedes": None
        })
        with open(os.devnull, "w") as checkpoint_output, contextlib.redirect_stdout(checkpoint_output):
            ctx.checkpoint(Args(root=str(root), task=None,
                                summary="Resume from UNIQUE-RAVEN-ORACLE",
                                next="Inspect raven observation", blocker=None,
                                verified_by="synthetic-test"))
        current = 0
        for size in sizes:
            for i in range(current, size):
                ctx.append(root, {
                    "id": f"R-noise-{i:07d}", "at": ctx.now(), "task": tid,
                    "kind": "note", "status": "unverified",
                    "title": f"Unrelated historical log number {i}",
                    "body": f"Routine discovery with no match {i}: " + "junk " * 35,
                    "proof": "", "path": None,
                    "tags": [], "links": [], "supersedes": None
                })
            current = size
            measurements = []
            retrieved = True
            bounded = True
            for _ in range(options.trials):
                start = time.perf_counter()
                p = subprocess.run(
                    [sys.executable, str(ROOT / "ctx.py"), "--root", str(root),
                     "context", "--query", "raven", "--budget", "350"],
                    capture_output=True, text=True, timeout=30)
                measurements.append(1000 * (time.perf_counter() - start))
                if p.returncode:
                    raise RuntimeError(p.stderr)
                retrieved &= ("UNIQUE-RAVEN-ORACLE" in p.stdout and
                              "Inspect raven observation" in p.stdout)
                bounded &= len(p.stdout) <= 1401
            measurements.sort()
            results.append({
                "records": size + 1,
                "ledger_bytes": (root / ".ctx/records.jsonl").stat().st_size,
                "context_output_in_budget": bounded,
                "old_query_relevant_finding_recovered": retrieved,
                "median_ms": round(statistics.median(measurements), 2),
                "p95_ms": round(measurements[min(len(measurements)-1, int(len(measurements)*.95))], 2),
                "n": len(measurements)
            })
    output = {
        "kind": "OFFLINE_SCALING_NOT_MODEL_EVAL",
        "python": sys.version.split()[0],
        "git_commit": os.getenv("GITHUB_SHA", "local"),
        "results": results,
        "pass": all(x["context_output_in_budget"] and
                    x["old_query_relevant_finding_recovered"] for x in results),
        "limitations": [
            "Synthetic JSONL evidence only. One writer. No LLM/compaction.",
            "CLI durations include process startup and vary across hosted runners.",
            "No long-prompt semantic recall or accuracy claims."
        ]
    }
    if options.output:
        dest = Path(options.output)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))
    return 0 if output["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
