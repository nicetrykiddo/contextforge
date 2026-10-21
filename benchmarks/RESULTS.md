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
