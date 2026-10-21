# ContextForge benchmarks: what is measured, what is not

**As of 2026-10-21, passing unit tests is not evidence of better agent outcomes.**
We specifically reject fabricated LLM win rates, hidden-model claims, and
the assumption that lost prompt cache = lost conversation state.

## Two experiment families

### 1. Offline memory-mechanics benchmark (CI; no model)

Run:

```bash
python3 benchmarks/offline_recovery.py --noise 48 --replays 12 --output .bench-results/offline.json
```

It seeds two independent targets, 48 distractor observations, separate missions
and checkpoints; starts **new Python CLI processes** with 100/350/800/1500
approximate-token budgets; switches tasks; tests query-relevant evidence, corrupt
optional global lesson storage, and source-state snapshots. Measures wall time,
record sizes, and whether exact recovery facts are present.

It **does not** measure solving, Codex compaction, LLM context retention,
model caching, API usage limits, or the value of the skill to an actual model.

### 2. Real Codex agent trials (opt-in; consume Plus/Codex usage)

Prerequisites: compatible **authenticated** Codex CLI on your machine and Python
3.10+. The runner uses Codex's existing identity and preserves normal sandbox
permissions. It never installs a new model or sets guardrail overrides.

See cost before running:

```bash
python3 benchmarks/live_codex.py --model gpt-6-sol \
  --seeds 1 --arms cold-plain,cold-forge
```

The default is a **dry run** and sends no model requests. To run the small
6-turn comparison deliberately:

```bash
python3 benchmarks/live_codex.py --model gpt-6-sol \
  --seeds 1 --arms cold-plain,cold-forge --execute
```

To produce a more meaningful paired estimate, after verifying the runner and
estimating your remaining usage, repeat with e.g.:

```bash
python3 benchmarks/live_codex.py --model gpt-6-sol \
  --seeds 1,2,3,4,5 \
  --arms cold-plain,cold-forge,resume-plain,resume-forge \
  --timeout 300 --execute
```

That last command schedules **60 Codex invocations**, which may hit Plus limits.
Run only when you explicitly want to spend those turns. `--model` can be
omitted to use your configured default; don't infer plan entitlement from the
model name. Failed quota/auth requests must be recorded as failures, not
silently excluded.

**Arms:**

| Arm | Session between phases | Memory intervention |
| --- | --- | --- |
| `cold-plain` | New Codex thread every phase | No ContextForge |
| `cold-forge` | New Codex thread every phase | Project AGENTS.md, skill, ContextForge CLI |
| `resume-plain` | Native `codex exec resume --last` | No ContextForge |
| `resume-forge` | Native `codex exec resume --last` | ContextForge |

Each trial uses an independent workspace and a synthetic offline Python task.
At phase 1, the agent must run a **transient diagnostic** defining an algorithm.
The harness deletes that diagnostic before phase 2. Phase 2 introduces unrelated
distractions. Phase 3 asks the agent to implement the behavior. An external
hidden grader verifies nine representative inputs using parameters never given
to the agent by the phase-3 prompt. All arms can write normal notes; baseline
is **not** forbidden from recording discoveries. ContextForge may also record
evidence. This is a test of **durable state**, not exploit generation.

Raw per-turn Codex JSON events are saved locally in `.bench-results/`; report
contains exit status, wall time, input/cached/output/reasoning token counters when
exposed by the installed Codex, and strict grader pass/fail. **Do not publish
private traces**. The benchmark source and generated fixture should be audited
for leakage; the "hidden" oracle is hidden from the workspace, not proof
against an actively gaming adversarial model.

## Native automatic compaction is a separate experiment

A new thread after a Plus-limit pause is NOT a native compaction event.
Native Codex resume is also NOT a cold new thread. KV/prompt caching is yet
another subsystem. The runner **never labels a reset as compaction**.

If Codex JSONL events explicitly contain a compaction event, the runner reports
it. If none appear, it records `native_compaction_observed=false`. This
**does not prove no compaction occurred**, because some Codex frontends may
not expose a dedicated event. To claim native compaction improvement, independently
validate runtime compaction telemetry/hook callbacks and compare matched runs
that really crossed a context threshold. Prefer a supported instrumentation
interface; don't force 100k+ junk tokens into Plus simply to create a graph.

The user-level situation `quota hit -> hours later -> continue` should be
tested with BOTH native session resume and fresh new-thread restart, because
only the latter necessarily loses the session's in-thread state. Prompt-cache
TTL/cold start is not itself a memory failure.

## Preregistered metrics and interpretation

**Primary:** grader success per arm, paired by seed. A model answer claiming
success is irrelevant; only the external test counts.

**Secondary:** number of Codex requests/turns, sum of reported input/output/
reasoning tokens, cached-input tokens, time-to-success, errors, success after
each cold restart, and evidence that compaction actually occurred. Record
hardware, Codex version, model, reasoning effort, date, tool versions, and
retry/quota errors. Do not compare runs with different tool/permission settings.

**Operational checks:** checkpoint accuracy, exact mission identity, provenance
recovery, stale/contradictory evidence, irrelevant-context ratio, truncated
hot context, log-growth and retrieval latency. A failure on any of these
is a valid negative result for the context layer.

**Baseline contamination risk:** If your regular Codex account already has
ContextForge installed as a global skill, the "plain" arm might still load it.
Review each trace and the `contextforge_cli_events_total` field before
interpreting performance. A properly controlled run must isolate skill
discovery/config without changing model safety settings, account authentication,
or tool permissions. A contaminated baseline is **not** a valid no-skill test.

**Task-coverage risk:** The included coding fixture is deliberately narrow
(transient diagnostic plus small code patch), not a validated substitute for a
multi-hour authorized bug bounty or real enterprise codebase. Add licensed,
sanitized, externally graded tasks of different lengths before generalizing.

**Comparison:** randomize arm order, pair trial seeds, aim for 10+ seeds per
model when quota permits, include multiple model families, report both gains
and regressions, and show confidence intervals rather than cherry-picked examples.
Single 1-seed runs are smoke tests, not efficacy evidence. Codex may improve its
native persistence between versions; rerun the no-skill baseline after updates.

**Ablations** to add after the first real-model baseline: core context only,
global reasoning off/on, checkpoint interval variants, cold-reset frequency,
small vs large evidence corpus, corruption injection, multiple targets and
contradictory clues. Any optional learned lesson is data, not a model policy.

**Abort criteria / anti-slop gate:** do NOT claim ContextForge improves task
completion unless multiple paired real-model runs beat baseline on a
predeclared external grader, after accounting for tokens and overhead. If
`cold-forge` performs worse than `cold-plain`, diagnose or remove features.
If native resume matches it, prefer the free built-in Codex mechanism.

## Limitations of this first benchmark

- The real-model runner has been checked for dry-run behavior by CI, but
  CI has no model credentials and will **not** execute Codex inference.
- The offline harness cannot induce true server-side compaction or expire KV
  caches. Do not use offline results as evidence of model intelligence.
- Results depend on the Codex CLI and model version; usage telemetry schemas
  can change. No dollar cost is inferred from ChatGPT Plus usage.
- Long-run LLM efficacy remains **unverified until actual trials are recorded**.
