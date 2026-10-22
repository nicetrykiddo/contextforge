# Benchmarks

ContextForge includes offline tests of memory mechanics and an optional Codex runner. The two test different things.

## Offline recovery

```bash
python3 benchmarks/offline_recovery.py --noise 48 --replays 12 --output .bench-results/offline.json
python3 benchmarks/scale.py --sizes 100,1000,5000,20000 --trials 7 --output .bench-results/scale.json
python3 benchmarks/hypothesis_pressure.py --sizes 0,10,100,1000,5000 --iterations 7 --output .bench-results/hypothesis.json
```

These tests measure recovery across fresh CLI processes, task-scoped retrieval, snapshot integrity, output limits, record growth and latency. They do not invoke a language model.

[Recorded results](benchmarks/RESULTS.md)

## Codex trial runner

Requires an authenticated, compatible Codex CLI. By default it prints a dry-run plan and makes no model calls.

```bash
python3 benchmarks/live_codex.py --seeds 1 --arms cold-plain,cold-forge
```

Add `--execute` to run the trial with the configured Codex model, or set `--model MODEL_ID` explicitly. Each arm runs three phases; choose seeds and arms according to available usage.

| Arm | Between phases | Memory |
| --- | --- | --- |
| `cold-plain` | New thread | Native only |
| `cold-forge` | New thread | ContextForge |
| `resume-plain` | Same captured thread | Native only |
| `resume-forge` | Same captured thread | ContextForge |

Each trial generates an independent synthetic Python workspace. The agent reads an ephemeral diagnostic, encounters distractor content, then implements the function after the diagnostic is removed. An external check evaluates the resulting implementation.

Results include graded pass/fail, wall time, model-reported usage, CLI invocation counts, and observable compaction events. Private JSONL traces are written under `.bench-results/` and should not be committed.

**Scope:** This runner evaluates a narrow persistence task. It is not an SWE or vulnerability-discovery benchmark. No comparative real-model results are published here.

## Evaluating agent outcomes

For broader comparisons, use independently graded held-out tasks and isolate baseline and intervention environments. Keep the model, reasoning effort, tool access and time limits equal. Randomize trial order, include failures and report full task-level results, confidence intervals, time and token overhead. Separate cold-thread recovery from native session resume and actual compaction.

Global skills and `AGENTS.md` instructions can contaminate a native baseline if they remain discoverable. Confirm isolation before interpreting results.

The `live_codex.py` CLI records compaction only when the execution trace exposes an explicit event; missing events are not evidence that no compaction occurred. The reported token counts are not equivalent to subscription quota consumption.
