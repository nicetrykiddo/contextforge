#!/usr/bin/env python3
"""Opt-in *real Codex* paired benchmark for session memory.

Never silently spends Plus/Codex usage. No API keys stored. Read BENCHMARKS.md.
Four arms: fresh session vs resume, each with/without ContextForge.
Reports native compaction only if a runtime event explicitly identifies it.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
ARMS = ("cold-plain", "cold-forge", "resume-plain", "resume-forge")


def fixture(directory, seed, forge=False, stress_kb=0):
    directory.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    factor, bias = rng.randint(6, 79), rng.randint(13, 190)
    (directory / "worker.py").write_text(
        '"""Transform telemetry IDs. Original algorithm is missing.\n'
        'Inspect the one-time diagnostic during stage 1.\n"""\n\n'
        'def transform(value: int) -> int:\n'
        '    return value  # BUG: not the diagnostic-defined transform\n')
    (directory / "ephemeral_probe.py").write_text(
        '"""One-time synthetic diagnostic; removed before implementation.\n'
        'The diagnostic is not available when you return to this task.\n"""\n'
        f'print("DIAGNOSTIC: transform(x) = (x * {factor} + {bias}) % 251")\n')
    rng2 = random.Random(seed * 17 + 19)
    lines = [f"Decoy item {i}: transient class={rng2.randrange(1000)}; "
             "NOT related to telemetry transformation.\n" for i in range(190)]
    (directory / "decoy.md").write_text("# Independent decoy catalogue\n" + ''.join(lines))
    if stress_kb:
        (directory / "stress.txt").write_text(
            "Generated distraction, not part of the hidden test.\n" *
            (stress_kb * 1024 // 55))
    if forge:
        # Isolate installation to the fixture. No global configuration changes.
        skill = ROOT / ".agents" / "skills" / "contextforge"
        destination = directory / ".agents" / "skills" / "contextforge"
        shutil.copytree(skill, destination)
        # CLI's local AGENTS.md instructs the agent to use the memory system.
        result = subprocess.run(
            [sys.executable, str(ROOT / "ctx.py"), "--root", str(directory),
             "init", "--mode", "software"],
            capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(f"Failed to initialize ContextForge: {result.stderr}")
        (directory / ".ctx" / "MISSION.md").write_text(
            "# Memory resilience benchmark\n"
            "Recover the ephemeral diagnostic algorithm and implement worker.transform.\n"
            "The diagnostic will be deleted after the first phase.\n")
        (directory / ".ctx" / "SCOPE.md").write_text(
            "# Offline scope\nOnly generated files in this temporary benchmark directory.\n")
    return {"factor": factor, "bias": bias}


PHASES = [
    "Stage 1 / 3. Inspect worker.py and RUN python3 ephemeral_probe.py. "
    "Learn the diagnostic transform, but DO NOT modify worker.py yet. "
    "The diagnostic disappears before stage 3. Save notes however you ordinarily would. "
    "Do not assume the phase 3 model will receive the earlier conversation.",
    "Stage 2 / 3. Inspect decoy.md and identify why it is irrelevant to worker.transform. "
    "Do not modify worker.py. Continue maintaining research state using your usual workflow.",
    "Stage 3 / 3. Implement worker.transform(value) using the diagnostic formula you "
    "found during stage 1. The diagnostic has now been removed; use any notes, project "
    "context or your resumed session. Only edit worker.py. Run a local quick check if helpful."
]


def codex_invocation(arm, model, phase):
    cmd = ["codex", "exec", "--json", "--sandbox", "workspace-write",
           "--skip-git-repo-check"]
    if model:
        cmd += ["--model", model]
    if "resume" in arm and phase:
        cmd += ["resume", "--last", PHASES[phase]]
    else:
        cmd += [PHASES[phase]]
    return cmd


def read_events(jsonl):
    events = []
    for line in jsonl.splitlines():
        try:
            value = json.loads(line)
            if isinstance(value, dict):
                events.append(value)
        except json.JSONDecodeError:
            pass
    return events


def summarize_events(events):
    usage = {"input_tokens": 0, "cached_input_tokens": 0,
             "output_tokens": 0, "reasoning_output_tokens": 0}
    for event in events:
        if event.get("type") in ("turn.completed", "turn.failed"):
            u = event.get("usage") or {}
            for key in usage:
                if isinstance(u.get(key), (int, float)):
                    usage[key] += u[key]
    # Do not infer compaction from token count or a model saying "compacted".
    explicit_compactions = [e.get("type") for e in events
                            if "compact" in str(e.get("type", "")).lower()]
    return usage, explicit_compactions


def verify(directory, formula):
    values = (-503, -1, 0, 1, 2, 17, 47, 251, 999)
    test = ('from worker import transform\n'
            f'factor = {formula["factor"]}\n'
            f'bias = {formula["bias"]}\n'
            f'for x in {values!r}:\n'
            ' assert transform(x) == (x * factor + bias) % 251, x\n'
            'print("PASS")\n')
    try:
        p = subprocess.run([sys.executable, "-c", test], cwd=directory,
                           text=True, capture_output=True, timeout=12)
        return p.returncode == 0, p.stderr[-300:]
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)


def run_trial(outdir, arm, model, seed, timeout, stress_kb, keep_workspace=False):
    # Independent workspace outside results and other trial fixtures. In particular,
    # do not let an agent browse previous arms' data through the parent directory.
    workspace = Path(tempfile.mkdtemp(prefix=f"cf-model-{arm}-seed{seed}-"))
    truth = fixture(workspace, seed, forge=("forge" in arm), stress_kb=stress_kb)
    env = os.environ.copy()
    bin_dir = outdir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    executable = bin_dir / "contextforge"
    if not executable.exists():
        executable.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' ' + shlex.quote(str(ROOT / 'ctx.py')) + ' "$@"\n')
        executable.chmod(0o700)
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
    phases = []
    for index in range(3):
        if index == 1:
            (workspace / "ephemeral_probe.py").unlink(missing_ok=True)
            shutil.rmtree(workspace / "__pycache__", ignore_errors=True)
        command = codex_invocation(arm, model, index)
        start = time.monotonic()
        try:
            p = subprocess.run(command, cwd=workspace, env=env, text=True,
                               capture_output=True, timeout=timeout)
            duration = round(time.monotonic() - start, 2)
            events = read_events(p.stdout)
            usage, compactions = summarize_events(events)
            # Keep trace outside agent-visible workspace: otherwise a cold
            # control can recover the deleted diagnostic from its own JSONL!
            trace_dir = outdir / "traces" / f"{arm}-seed{seed}"
            trace_dir.mkdir(parents=True, exist_ok=True)
            trace = trace_dir / f"phase{index+1}.events.jsonl"
            trace.write_text(p.stdout)
            try:
                trace.chmod(0o600)
            except OSError:
                pass
            phases.append({"phase": index+1, "exit_code": p.returncode,
                           "wall_seconds": duration,
                           "usage": usage,
                           "native_compaction_events": compactions,
                           "event_count": len(events),
                           "stderr_tail": p.stderr[-300:] if p.returncode else ""})
            if p.returncode:
                break
        except subprocess.TimeoutExpired:
            phases.append({"phase": index+1, "error": "TIMEOUT", "timeout_seconds": timeout})
            break
    ok, grader_error = verify(workspace, truth)
    report = {
        "arm": arm, "model": model or "Codex configured default", "seed": seed,
        "phases_completed": len(phases),
        "all_phases_succeeded": len(phases) == 3 and all(
            x.get("exit_code") == 0 for x in phases),
        "hidden_grader_pass": ok,
        "grader_error": grader_error if not ok else "",
        "native_compaction_observed": any(x.get("native_compaction_events") for x in phases),
        "token_totals": {key: sum(x.get("usage", {}).get(key, 0) for x in phases)
                         for key in ("input_tokens", "cached_input_tokens",
                                     "output_tokens", "reasoning_output_tokens")},
        "total_wall_seconds": round(sum(x.get("wall_seconds", 0) for x in phases), 2),
        "phases": phases,
        "workspace": str(workspace) if keep_workspace else "(removed after trial)"
    }
    if not keep_workspace:
        shutil.rmtree(workspace)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="", help="Codex model ID; empty uses existing account default")
    ap.add_argument("--seeds", default="1", help="Comma-separated integers, e.g. 1,2,3,4,5")
    ap.add_argument("--arms", default="cold-plain,cold-forge")
    ap.add_argument("--timeout", type=int, default=300, help="Seconds per Codex invocation")
    ap.add_argument("--stress-kb", type=int, default=0, help="Extra irrelevant data: expensive, NOT proof of native compaction")
    ap.add_argument("--output-dir", default=".bench-results", help="PRIVATE local folder for traces and results")
    ap.add_argument("--execute", action="store_true", help="Required: uses your Codex/Plus quota")
    ap.add_argument("--keep-workspaces", action="store_true",
                    help="Retain synthetic agent workspaces under /tmp for debugging")
    args = ap.parse_args()
    arms = args.arms.split(",")
    seeds = [int(v) for v in args.seeds.split(",")]
    if not arms or any(a not in ARMS for a in arms) or len(set(arms)) != len(arms):
        ap.error("Invalid or duplicate arms")
    if len(seeds) > 50 or len(seeds) != len(set(seeds)) or args.timeout < 30 or args.stress_kb > 2048:
        ap.error("Invalid seed count, timeout or stress size")
    turn_count = len(arms) * len(seeds) * 3
    if not args.execute:
        print(json.dumps({"status": "DRY_RUN_ONLY_NO_MODEL_CALLED",
                          "codex_calls_if_executed": turn_count,
                          "arms": arms, "seeds": seeds, "model": args.model or "configured default",
                          "note": "Add --execute to intentionally spend Codex usage. "
                                  "Native compaction is not forced and must be observed."}, indent=2))
        return 0
    if not shutil.which("codex"):
        ap.error("codex CLI unavailable; no model requests were made")
    outdir = Path(args.output_dir).expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    version = subprocess.run(["codex", "--version"], capture_output=True, text=True)
    results = []
    order = [(arm, seed) for seed in seeds for arm in arms]
    random.Random(73291).shuffle(order)
    for arm, seed in order:
        result = run_trial(outdir, arm, args.model, seed, args.timeout,
                           args.stress_kb, keep_workspace=args.keep_workspaces)
        results.append(result)
        print(f'{arm} seed={seed} passed={result["hidden_grader_pass"]} '
              f'usage={result["token_totals"]["input_tokens"]} input tokens', flush=True)
        (outdir / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    report = {
        "kind": "REAL_CODEX_CLI_MODEL_TRIALS",
        "model": args.model or "configured default",
        "codex_version": version.stdout.strip(),
        "attempted_calls": turn_count,
        "actual_compaction_evidence": "Only events with type containing compact; absence does not prove none occurred",
        "warning": "Fresh session and native compaction are distinct interventions. "
                   "Plus caps depend on account and cannot be measured by token totals alone.",
        "results": results
    }
    (outdir / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"report": str(outdir / "report.json"),
                      "trials": len(results),
                      "native_compaction_events_observed": sum(r["native_compaction_observed"] for r in results),
                      "PASS": sum(r["hidden_grader_pass"] for r in results)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
