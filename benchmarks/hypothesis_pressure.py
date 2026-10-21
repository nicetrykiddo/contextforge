#!/usr/bin/env python3
"""Measure hypothesis growth costs and what hot context actually contains.

No model calls, no compaction inference, no implied solving improvement.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import tempfile
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
import ctx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="0,10,100,1000,5000")
    ap.add_argument("--iterations", type=int, default=7)
    ap.add_argument("--output", default="")
    args = ap.parse_args()
    sizes = [int(n) for n in args.sizes.split(",")]
    if sizes != sorted(set(sizes)) or any(n < 0 or n > 40000 for n in sizes):
        ap.error("sizes must be sorted unique non-negative integers up to 40000")
    with tempfile.TemporaryDirectory(prefix="cf-hypotheses-") as td:
        project = Path(td) / "study"
        project.mkdir()
        config = Path(td) / "config"
        env = {**os.environ, "XDG_CONFIG_HOME": str(config)}
        A = lambda **kw: argparse.Namespace(**kw)
        with contextlib.redirect_stdout(io.StringIO()):
            ctx.init(A(root=str(project), name="pressure", mode="bugbounty", scope="."))
            ctx.task_add(A(root=str(project), title="Synthetic parser investigation",
                           scope=None, goal="Verify why the raven oracle differs on input A"))
            ctx.checkpoint(A(root=str(project), task=None,
                             summary="Verified the baseline input A response",
                             next="Check the raven oracle's second input",
                             blocker=None, verified_by="synthetic-fixture"))
        (project / ".ctx/MISSION.md").write_text("# Synthetic mission\nFind RAVEN-KEY marker.\n")
        state = ctx.load(project)
        tid = state["active_task"]
        ctx.append(project, {
            "id": "R-proven", "task": tid, "at": ctx.now(),
            "kind": "finding", "status": "verified",
            "title": "RAVEN-KEY verified observation",
            "body": "Parser output differs on a controlled fixture.",
            "proof": "synthetic-log.txt:42", "path": None, "links": [],
            "tags": [], "supersedes": None,
        })
        measurements = []
        earlier = 0
        for n in sizes:
            for k in range(earlier, n):
                ctx.append(project, {
                    "id": f"R-spec-{k:08d}", "task": tid, "at": ctx.now(),
                    "kind": "hypothesis",
                    "status": "rejected" if k % 3 == 0 else "unverified",
                    "title": f"Speculation number {k:05d} about unrelated behavior",
                    "body": "Plausible but not validated; add another alternative mechanism.",
                    "proof": "", "path": None, "links": [],
                    "tags": [], "supersedes": None,
                })
            earlier = n
            timings = []
            output = ""
            for i in range(args.iterations):
                t0 = time.perf_counter()
                p = subprocess.run(
                    [sys.executable, str(REPO / "ctx.py"), "--root", str(project),
                     "context", "--budget", "1200"],
                    capture_output=True, text=True, env=env, timeout=20,
                )
                if p.returncode:
                    raise RuntimeError(p.stderr)
                timings.append((time.perf_counter() - t0) * 1000)
                output = p.stdout
            query = subprocess.run(
                [sys.executable, str(REPO / "ctx.py"), "--root", str(project),
                 "context", "--query", "raven", "--budget", "350"],
                capture_output=True, text=True, env=env, timeout=20,
            )
            if query.returncode:
                raise RuntimeError(query.stderr)
            records = len((project / ".ctx/records.jsonl").read_text().splitlines())
            entries = re.findall(r"(?m)^- R-spec-\d+ hypothesis/(?:unverified|rejected)", output)
            rejected = len(re.findall(r"(?m)^- R-spec-\d+ hypothesis/rejected", output))
            measurements.append({
                "hypotheses_created": n,
                "records": records,
                "ledger_bytes": (project / ".ctx/records.jsonl").stat().st_size,
                "hot_context_characters": len(output),
                "hot_context_hypotheses": len(entries),
                "hot_context_rejected_hypotheses": rejected,
                "hot_context_keeps_next_step": "Check the raven oracle's second input" in output,
                "query_retrieves_verified_finding": "RAVEN-KEY verified observation" in query.stdout,
                "global_reasoning_written": (config / "contextforge/reasoning.json").exists(),
                "retrieval_ms_median": round(statistics.median(timings), 2),
                "retrieval_ms_max": round(max(timings), 2),
            })
    result = {
        "kind": "OFFLINE_HYPOTHESIS_PRESSURE_NOT_MODEL_EVAL",
        "git_sha": os.getenv("GITHUB_SHA", "local"),
        "python": sys.version.split()[0],
        "measurements": measurements,
        "checkpoint_and_verified_finding_recovered": all(
            x["hot_context_keeps_next_step"] and x["query_retrieves_verified_finding"]
            for x in measurements),
        "no_global_memory_promotion": not any(x["global_reasoning_written"] for x in measurements),
        "limitations": [
            "No real model, agent decisions, auto compaction, or Plus quota involved.",
            "All hypotheses are seeded synthetic records, not generated by Codex.",
            "Latency includes interpreter/process startup and varies with CI hardware."
        ],
    }
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if (result["checkpoint_and_verified_finding_recovered"] and
                 result["no_global_memory_promotion"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
