# ContextForge 3.4.2

**Long-session project memory and decision continuity for Codex. Not a model guardrail, policy override, or agent controller.**

ContextForge keeps critical working context outside the conversation so CTF, bug bounty, investigation, software, and general projects can continue through compaction and new chats without repeating hours of discovery.

## What stays in context

- **Hot (always first):** exact mission/source pointer, active task, latest checkpoint, blocker, next action.
- **Warm (selected):** pinned observations, source-linked evidence, decisions, prior negative results.
- **Cold (on demand):** experiment histories, old logs, archived hypotheses, indexed file paths.

The CLI loads the hot layer **before** optional history, including when the token budget is tiny. It warns rather than silently presenting an incomplete summary as complete. More tokens are not always better; the goal is the right evidence, not maximum output.

**ContextForge does not alter LLM safety settings, system instructions, permissions, or tool policies.** It does not decide whether the agent may perform a task. Existing requirements and program rules remain in force. Experiment-lane commands and anti-loop diagnostics are optional recordkeeping, not a compulsory solving protocol.

## Evidence and performance benchmarks

- [Evidence policy](benchmarks/EVIDENCE_POLICY.md): what can be claimed publicly,
  what requires real-agent paired trials, and why "flawless" is not a test result.
- [Private trace analyzer](benchmarks/trace_diagnostics.py): aggregate tool-call,
  compaction and token-use measurements from real Codex JSONL without emitting
  command contents or stored output. Observational only, **not A/B evidence**.
- [Benchmark protocol](BENCHMARKS.md): four-arm real Codex experiments,
  including matched cold restarts and native session resumes, hidden acceptance
  tests, JSONL token telemetry, and strict definitions of what counts as compaction.
- [Measured offline results](benchmarks/RESULTS.md): synthetic memory recovery
  and CLI latency on Python 3.10/3.12, **not LLM performance**.
- [Opt-in real-model runner](benchmarks/live_codex.py): intentionally defaults
  to a zero-cost dry run. No real-model results have been produced in this repo.

**Do not claim the skill increases model task-success rates until actual paired
model experiments show that improvement over the unmodified Codex baseline.**

## Install once for a project

Review the public installer before execution:

```bash
curl -fsSL https://raw.githubusercontent.com/nicetrykiddo/contextforge/main/install.sh | bash -s -- --project "$PWD" --mode bugbounty
```

Modes: `bugbounty`, `ctf`, `software`, `investigation`, `general`. Python 3.10+, standard library only. The installer places `contextforge` in `~/.local/bin` and a reusable skill in `~/.agents/skills/contextforge/`. It preserves any existing `AGENTS.md` and upgrades an existing `.ctx/` project instead of recreating its records.

Hooks are **optional**: add `--hooks` only if you want Codex lifecycle integration. Review/trust the resulting `~/.codex/hooks.json`; enabling them may require `[features] hooks = true` in `~/.codex/config.toml` and a Codex restart. Do not mistake installed hooks for guaranteed invocation in every frontend.

In a new Codex chat:

> Use $contextforge for memory management in this project. Load the exact mission, latest checkpoint and relevant evidence. Save important discoveries, and preserve recovery state before compaction. Keep your normal task strategy and existing permissions unchanged.

A GitHub URL alone does not install a skill; Codex must have the repository available and permission to run the installer.

## Install globally, use from any project

The installer makes `$contextforge` discoverable from
`~/.agents/skills/contextforge/` and places the CLI in `~/.local/bin`.
To **update the global skill without creating or modifying project memory**:

```bash
curl -fsSL https://raw.githubusercontent.com/nicetrykiddo/contextforge/main/install.sh | bash
```

Restart Codex to refresh skill discovery. The skill can be invoked from any
supported project; it does **not** silently apply to every conversation or
initialize every directory. Within a particular long-running project,
run `contextforge init --mode general` once if no `.ctx/` exists, then fill
the exact mission and applicable scope. Mode names are organizational labels,
not different model instructions or permission profiles.

## Efficient long-chat workflow

1. Fill `.ctx/MISSION.md` with the real objective, acceptance test and **path/link to the full original source**. Fill `.ctx/SCOPE.md` with any existing engagement context.
2. Use `contextforge task add 'Short goal' --goal 'Specific outcome'` to separate research threads. **Creating a task does not interrupt an already active task.** Use `contextforge task add 'New task' --focus` to create and immediately switch, or `contextforge task focus TASK_ID` to resume later. The first task becomes active automatically. The first task uses the legacy `.ctx/MISSION.md`; adding a second task creates independent mission/scope cards. Fill the new task cards rather than reusing another task's assumptions.
3. At startup or after compaction, run **one** `contextforge context --budget 1200`. The latest checkpoint now comes before long pinned or historical lists.
4. On a consequential branch, preserve the **reason** for the next action and what would invalidate it. This prevents compaction from restoring a now-pointless plan:
   `contextforge checkpoint --summary 'Verified observation' --next 'Test alternate mechanism' --why-next 'Distinguishes two explanations' --pivot-if 'Negative control behaves identically'`
   The last two flags are optional: do not turn routine tasks into paperwork.
5. If you need only one topic, use `contextforge context --query 'authentication' --budget 900`, `contextforge search 'authentication'`, or inspect the referenced source file.
6. After a meaningful finding, use `contextforge pin --title 'Critical clue' --body 'Observation, conditions and limits' --status verified --proof 'logs/example.txt:42'`.
7. At a meaningful milestone, use `contextforge checkpoint --summary 'Current state' --next 'Precise next action'`. Checkpoints are isolated per active task. Before compaction, `contextforge snapshot`; for chat-switch text, `contextforge handoff --budget 1200`. Handoff **does not scan files automatically**; run `contextforge handoff --refresh` only when you need an updated file inventory.

Avoid recording every thought or rerunning `scan`, `audit`, and `rethink` at every chat turn: that just wastes the context you're trying to save. These commands remain available on demand.

## Why the strategy layer is minimal (real rollout audit)

An opt-in inspection of one real, long Codex investigation found **1,439 tool calls
and 8 compactions** in a JSONL session. ContextForge was invoked repeatedly; the
agent preserved its broad goal and recorded useful negative evidence. Yet it
invested in some findings that failed the downstream acceptance/eligibility
criteria and repeatedly switched candidates without reliably revisiting its
*selection strategy*. These are case observations, not controlled causal proof
that ContextForge or compaction caused the wasted work.

The installed skill now keeps a **short, universally applicable decision anchor**:
success condition, cheapest relevant disqualifier, decisive evidence, why the
next step helps, and a falsifiable reason to change direction. It applies to
coding, research, authorized security tests, operations and other multi-step
projects. No compulsory audit loop, no new engine, no model/tool/safety
modifications, and no automatic cross-project learning.

**Not yet established:** This improves real-agent task completion, tool budget,
or reasoning accuracy over unmodified Codex. The external real-model benchmark
still needs repeated matched trials; see [BENCHMARKS.md](BENCHMARKS.md).

## Persistent files

| Path | Role |
| --- | --- |
| `.ctx/MISSION.md` | Legacy/single-task mission and shared project mission |
| `.ctx/tasks/TASK_ID/MISSION.md` | Independent target mission (multi-task projects) |
| `.ctx/tasks/TASK_ID/SCOPE.md` | Independent target engagement context (multi-task projects) |
| `.ctx/SCOPE.md` | Existing project/program boundaries |
| `.ctx/state.json` | Tasks, per-task checkpoints, legacy checkpoint mirror, and task-safe file inventory |
| `.ctx/records.jsonl` | Timestamped evidence/decisions/failures |
| `.ctx/lanes.json` | Optional experiment notes/history |
| `.ctx/HANDOFF.md` | Generated compact resume view |
| `.ctx/compactions/` | Backups of recorded project state |

`.ctx/` is private project metadata and should not be pushed to public Git. Save references rather than credentials or private customer data.

## Optional tools

```bash
contextforge status
contextforge check
contextforge context --query 'jwt parser' --budget 1000
contextforge checkpoint --summary 'Reproduced X in version Y' --next 'Check the second code path'
contextforge snapshot
contextforge handoff --budget 1200
contextforge audit
contextforge rethink --budget 1500
python3 -m unittest discover -s tests -v
```

See `.agents/skills/contextforge/references/workflow.md` for more command syntax and `references/field-lessons.md` for optional investigation pitfalls.

## Hypotheses: tentative local context, not a scorecard

Recording another hypothesis is **not progress** and does not train the model.
Rejected hypotheses are kept in the project evidence history but are no longer
automatically injected into every hot recovery view. Ordinary `context` loads
at most two tentative hypotheses; the full audit trail remains available with
`contextforge context --query hypothesis` and via the original JSONL ledger.

This is a retrieval optimization, **not a rule restricting how the agent reasons,
tests, or uses its existing safety controls**. The agent can investigate any
legitimate hypothesis, and no project hypothesis is silently promoted into
global reasoning memory. We have no evidence that saving more hypotheses
improves model task-completion rate.

The deterministic [hypothesis-pressure benchmark](benchmarks/hypothesis_pressure.py)
measures this behavior at 0, 10, 100, 1,000 and 5,000 seeded guesses,
including previously rejected entries. It is not a real-model test.

## Practical impact review (3.4.2)

The earlier adversarial audit proved several **local file-manipulation behaviors**,
but it did not establish a plausible remote attacker, an exploitable privilege
boundary, or real-world vulnerability severity. The managed `.ctx/` directory
normally has owner-only permissions and is ignored by Git. A crafted symlink
inside it generally requires the current user or another process already
able to tamper with the user's project metadata. The file-integrity guards
remain sensible defense in depth, not evidence of a remote compromise.

A subsequent real-workflow review found that two prior fixes were harmful:
automatically focusing every newly created task interrupted active work when
adding backlog items; preserving every overlapping task's inventory entry
kept deleted files indexed indefinitely. Both are corrected and backed by
regression tests. Focusing a closed task now explicitly reopens it so its
recorded status matches the active selection.

Global-lesson approval requiring a TTY is **an interaction convention**, not
human identity verification: a local agent controlling a terminal can satisfy
it. Noninteractive approval is intentionally unavailable today and can
inconvenience scripted administration; it should not be marketed as a security
barrier. Cross-task search and zero-match query fallbacks may be intentional
for some research; use explicit `--all-tasks` when broad search is wanted.
The optional global reasoning layer still lacks held-out model evidence of
positive transfer.

See [the practical-impact review](docs/practical-impact-review.md) for
preconditions, plausibility, possible regressions and deliberately unproven
claims. No claim is made that v3.4.2 improves LLM completion rates.

## Security and data-integrity hardening (3.4.1)

- Managed metadata rejects symlinks, hardlinks and non-regular file types; this
  prevents straightforward reads/writes beyond the metadata tree and FIFO hangs.
  Snapshot task-card collection includes only `MISSION.md` and `SCOPE.md`.
- Task `search` is scoped to the **active task** by default. Use
  `contextforge search 'term' --all-tasks` for intentional cross-task queries
  or `--task T-ID` for one other task. Query-specific context does not add
  records that fail its relevance filter. For an explicit hypothesis history
  query, tentative/rejected local hypotheses remain retrievable.
- Active-task `scan` preserves other tasks' inventory entries and prunes only
  deleted paths exclusive to the scanned scope, when the scan is complete.
  Shared paths may require rescanning another task to establish deletion.
- Task checkpoints are stale only when **relevant** records have changed.
  Unrelated notes from another task no longer invalidate the checkpoint.
- Global reasoning `approve` now requires an interactive terminal where the
  operator reviews the exact lesson text and types its ID. This blocks normal
  unattended subprocess approval but **does not prove a human** is operating
  the terminal. An agent controlling a PTY or local files can still impersonate
  an operator; do not treat a status flag as independently authenticated review.
  The global store stays optional, not a safety authorization mechanism.
- These are offline implementation protections. They do not demonstrate that
  real language models complete tasks more accurately. Native Codex
  compaction, hidden tool behavior and Plus usage limits still require real
  agent evaluation.

## Important limits

- Compaction is lossy; only information recorded **before** compaction can be restored.
- No hook can recover unrecorded internal thoughts, guarantee perfect memory, or interrupt an already-running tool/model call.
- Token budgets approximate 4 characters per token, not the model's exact tokenizer.
- Hook support varies by Codex version/frontend. Check that lifecycle callbacks actually fire.
- CLI project reads/writes are serialized via a project lock; global reasoning mutations have a separate lock. Direct Python API calls that bypass the CLI are not guaranteed transactional.
- `--proof` remains an **attested pointer**, not independent validation. Use optional `--proof-file` to capture an SHA256 digest of a local artifact; `contextforge check` flags later changes. File integrity does not prove an exploit claim.
- Project memory files use private permissions on initialization/upgrade; check ownership on shared machines.
- A compact handoff is an index into source evidence, **not a substitute for the original files**.
- Compaction archives now support up to **64 MB of evidence records** per snapshot (8 MB for other individual state files) and retain the latest eight snapshots. Larger ledgers must be archived explicitly; the unbounded JSONL lookup cost remains a known scaling issue. A successful snapshot contains the full current ledger within that limit.

ContextForge makes context recovery reliable **to the extent that important discoveries have been persisted**. It cannot guarantee a CTF solve or detect every misleading lead.

## Global reasoning memory: reviewed, abstract, optional

One repository, two independent stores:

- **Local:** `.ctx/` keeps target-specific findings and compaction recovery.
- **Global:** `~/.config/contextforge/reasoning.json` (or `$XDG_CONFIG_HOME/contextforge/reasoning.json`) keeps only approved, project-agnostic lessons about reasoning.

Each global lesson contains a *principle*, a general situation (*when*) and a mental check (*response*). No project data is copied automatically. Nothing changes LLM safety instructions, permissions, tools, or model settings. Global lessons are context, not model retraining.

```bash
ctx="contextforge reasoning"
$ctx propose --principle 'A successful tool response does not prove the goal was reached' \
  --when 'a tool reports acceptance before its effects are confirmed' \
  --response 'separate receipt, processing, and final observable outcome' \
  --tags 'tools verification progress'
$ctx list --status proposed
$ctx approve L-REPLACE_WITH_PRINTED_ID
$ctx select --query 'tool accepted but outcome is unconfirmed' --budget 160
```

Use `reasoning reject ID` for a pending proposal and `reasoning retire ID` to deactivate an approved lesson. Approval is always explicit; the system does **not** mine logs and promote mistakes automatically. Near-duplicates are blocked by a deterministic similarity heuristic, not semantic AI matching. Retrieval additionally uses a small fixed taxonomy of reasoning concepts; it does not use embeddings or retrain the model. Maximum 24 approved lessons.

Ordinary project context can include at most **two** relevant approved reminders, and only when enough tokens remain (budget at least 800). They appear after mission, checkpoint and pinned evidence. Irrelevant lessons are omitted. Explicit `reasoning select` can return up to three. Store is local to this computer, not synced.

Don't put targets, commands, IPs, URLs, emails, credentials, flags, or user data in global lessons. This is judgment memory, not a cross-target technical notes dump.
