# ContextForge benchmark results

## 2026-10-21: Offline recovery mechanics (NOT LLM performance)

Source: [GitHub Actions run 39601201137](https://github.com/nicetrykiddo/contextforge/actions/runs/39601201137).
Commit tested: `262823a3a37192496b86620faaed0fb9d8a44ef6`.

| Measurement | Python 3.10 | Python 3.12 |
| --- | ---: | ---: |
| Recovery/isolation/checkpoint cases passing | 11/11 | 11/11 |
| Noise records | 48 | 48 |
| Process-restart repeats | 12 | 12 |
| Context retrieval median (includes process startup) | 78.88 ms | 59.23 ms |
| Context retrieval p95 (includes process startup) | 88.50 ms | 60.54 ms |
| Ledger size | 25,247 B | 25,247 B |

**Important:** The eleven checks consist of eight task-budget recovery cases
(2 tasks × 4 approximate budgets), relevant evidence, malformed optional global
memory and snapshot content. These are not 11 model trials and not 11 solved tasks.
All checks passed on both GitHub-hosted environments.

## 2026-10-21: Long-session ledger growth and snapshot regression

At commit `7a0bbcfe`, increasing the synthetic ledger to **20,001 records /
9.54 MB** caused a snapshot failure. The 8 MB file limit prevented the
recovery archive from being written, even while ordinary context lookup worked.

- [Failing long-history benchmark](https://github.com/nicetrykiddo/contextforge/actions/runs/39602886518)
- [Passing after the snapshot-size and retention fix](https://github.com/nicetrykiddo/contextforge/actions/runs/39603160874)

On that **passing** GitHub run:

| Number of records | Ledger size | Python 3.10 lookup median | Python 3.12 lookup median | Python 3.10 snapshot | Python 3.12 snapshot |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 101 | 47.5 KB | 54.36 ms | 79.32 ms | 3.44 ms | 6.33 ms |
| 1,001 | 474 KB | 61.93 ms | 96.48 ms | 16.69 ms | 25.63 ms |
| 5,001 | 2.38 MB | 114.10 ms | 169.03 ms | 89.32 ms | 131.81 ms |
| 20,001 | 9.54 MB | 332.68 ms | 469.61 ms | 393.46 ms | 554.71 ms |

All four sizes passed source-recovery and approximate context-budget checks,
and snapshots succeeded after the fix. Numbers include interpreter startup
for lookup; runners were separate hosted environments under changing load.
Do **not** interpret the difference between Python 3.10 and 3.12 as a clean
language-version causal effect.

**Observed performance flaw:** lookup reads and scores the entire JSONL ledger
on each call. Roughly half-second lookups at 20k records may be acceptable
once at session start, but not once per model turn. This is a strong reason to
add an indexed local store (for example SQLite with explicit schema/version
migration) if real investigations routinely exceed this volume.

Compaction snapshot ledger cap increased from 8 MB to 64 MB, while other
state-file limits remain 8 MB. The latest eight archive snapshots are kept.
This is **not infinite-scale memory**: beyond the cap, archiving/rotation
needs an explicit design and tests, not promises.

## 2026-10-21: Hypothesis accumulation and relevance

Two GitHub-hosted offline benchmark runs exposed and then verified a context
retrieval issue. At 10 or more synthetic hypotheses, the old default hot view
included eight speculative records, three of them **already rejected**.
Those stale guesses occupied context despite a verified finding being present.

After making rejected hypotheses cold and limiting default hot context to two
tentative entries, the same scenarios produced:

| Seeded local hypotheses | Old: shown in hot context | Fixed: shown | Fixed: rejected shown |
| ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 |
| 10 | 8 | 2 | 0 |
| 100 | 8 | 2 | 0 |
| 1,000 | 8 | 2 | 0 |
| 5,000 | 8 | 2 | 0 |

Both before and after, the saved next action and targeted verified finding
remained retrievable, and none of the synthetic hypotheses entered the global
reasoning store. Following the fix, old rejected entries remained explicitly
queryable with `context --query hypothesis`.

Python 3.12 median lookup latency rose from ~69 ms for an almost empty ledger
to ~114 ms at 5,000 hypotheses in the **fixed** run. It still reads the full
ledger; lowering emitted context does **not** eliminate growth in storage or CPU.

- [Baseline observation](https://github.com/nicetrykiddo/contextforge/actions/runs/39608057560)
- [Fix validated (Python 3.10 and 3.12)](https://github.com/nicetrykiddo/contextforge/actions/runs/39608648219)

**Interpretation:** This confirms reduced prompt clutter from speculative
records in an offline fixture. It does **not** prove improved agent decisions,
faster CTF solutions, LLM learning, or native automatic compaction survival.

### Real model evaluation

| Model | Resumed baseline success | Resumed ContextForge | Cold baseline success | Cold ContextForge | Compaction confirmed | Agent token overhead |
| --- | --- | --- | --- | --- | --- | --- |
| Not run | N/A | N/A | N/A | N/A | **No evidence** | N/A |

There are **zero** actual GPT/Codex model trials in this report. The execution
environment did not have an authenticated Codex CLI/model endpoint. The separately
provided `benchmarks/live_codex.py` runner is opt-in, uses your own available
Codex quota, and outputs JSONL evidence + an external hidden grader result.
It does **not** force native compaction or claim that a model restarted cold
merely because a server-side prompt-cache entry expired.

### Interpretation

Offline checks support that this specific CLI can retrieve saved facts after
fresh Python processes and can fit under its **approximate character budget**
in these fixtures. They cannot establish that real Codex agents preserve key
state before compaction, choose good retrieval queries, perform fewer tool
calls, solve higher-quality tasks, or outperform native Codex compaction.

**Release gate:** Do not market cross-session memory as improving real model
success until matched, preregistered, multi-seed Codex trials with external
acceptance tests show an improvement at acceptable token/time overhead.
Negative regressions must be published, not hidden.

Full protocol: [BENCHMARKS.md](../BENCHMARKS.md).
