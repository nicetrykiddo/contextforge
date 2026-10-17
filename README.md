# ContextForge 3.0

**Persistent, selective context and evidence-backed anti-loop workflow for Codex.** Covers CTF practice, authorized bug bounty research, investigations, software engineering and general multi-session projects. Python 3.10+, standard library only, no network calls from the CLI.

Unlike lossy compaction summaries, the source of truth is project-local `.ctx/`: the original mission card, scope, verified pins, records, tested mechanisms, and checkpoints. Nothing promises an automatic CTF solve.

## One command per new project

In a project directory, install and initialize from GitHub:

```bash
curl -fsSL https://raw.githubusercontent.com/nicetrykiddo/contextforge/main/install.sh | bash -s -- --project . --mode ctf
```

For bug bounty, replace `ctf` with `bugbounty`; also accepts `software`, `investigation`, `general`. The installer installs the CLI into `~/.local/bin/contextforge` and the Codex skill into `~/.agents/skills/contextforge/`, and safely upgrades existing `.ctx` projects. It **preserves existing AGENTS.md**. `git` is needed for remote bootstrap. Review the script before piping it into bash, especially if using the public repo on a sensitive workstation.

For optional Codex hooks, append `--hooks`. Hooks merge with/backup `~/.codex/hooks.json` but require user review and may need to be explicitly enabled in Codex. They are not reliable substitutes for immediate evidence logging.

If you already cloned the repository:

```bash
bash install.sh --project /path/to/workspace --mode ctf
```

In a **new Codex chat**, instruct the agent:

> Install https://github.com/nicetrykiddo/contextforge for this project in CTF mode, use the ContextForge skill, preserve my existing files, and ask me for the exact authorized challenge brief. Do not test live systems until scope and rules are confirmed.

**Important:** Mentioning a GitHub URL to Codex is not an automatic skill installation. The agent needs access to the URL and permission to run the installer. Restart Codex if the skill does not appear; `~/.local/bin` must be on the shell PATH (or use its absolute path).

## Start with the objective, not an exploit story

1. Copy the exact challenge objective, success condition and immutable source reference into `.ctx/MISSION.md` (do not paraphrase away exceptions); put authorization and prohibited techniques into `.ctx/SCOPE.md`.
2. Set an active task: `contextforge task add 'Analyze briefing' --goal 'Identify the precise success condition'`.
3. Run `contextforge audit` and `contextforge rethink --budget 1500`. Review verification state and plan **one** cheap discriminating experiment.
4. Record outcomes with source pointers. Re-run the audit when stuck. Compaction is not allowed to silently replace evidence.

## The anti-loop contract

- Every route has a **stable causal identifier**; renaming a failed idea doesn't grant a fresh lane.
- Every gated experiment has a predicted observable output and a distinct fingerprint; exact duplicate trials without new evidence are blocked.
- Default caps: 20 minutes, 4 attempts, 2 stalled attempts; expiry is checked at CLI calls. Neither Codex nor the CLI can terminate an already-hung model/tool call.
- Progress requires a fresh verified record, timestamped *after* the experiment started. This is a workflow integrity check, **not proof that the record is true**.
- Before declaring success, compare the result with the *original external validator* or equivalent trusted test. A stub banner or assistant explanation is not proof.

## Persistent project state

| File | Why it exists |
| --- | --- |
| `.ctx/MISSION.md` | Exact original objective, source pointer, restrictions and success condition |
| `.ctx/SCOPE.md` | Authorized targets and permitted methods; no implicit scope |
| `.ctx/state.json` | Tasks, active scope, file inventory and checkpoint |
| `.ctx/records.jsonl` | Timestamped evidence, hypotheses, corrections, decisions, failures |
| `.ctx/lanes.json` | Routes, experiments, predictions, attempts and stop reasons |
| `.ctx/HANDOFF.md` | Budgeted recovery context with warnings when anything is omitted |
| `.ctx/compactions/` | Snapshots of **recorded state**, not model thoughts/transcripts |

`contextforge context --query 'parser' --budget 1500` hydrates relevant evidence without scanning the whole workspace. The budget uses an approximate 4-chars/token heuristic, not an actual tokenizer. When pins cannot fit, the CLI explicitly warns.

## Useful commands

```bash
contextforge status
contextforge audit
contextforge check
contextforge task add 'Local fixture investigation' --goal 'Reproduce and explain a parser mismatch'
contextforge scan
contextforge pin --title 'Observed output difference' --body 'Exact reproducible condition' --status verified --proof 'tests/results.log:12-18'
contextforge rethink --budget 1500
contextforge lane start 'Test parser difference' --route 'parser-normalization' --hypothesis 'Input is normalized inconsistently' --falsifier 'Both cases have equal normalized output'
contextforge lane gate --signature 'Compare local fixture A and B' --predict 'Case B differs in parsed representation'
# Perform one scoped and permitted local test and log the actual result
contextforge lane result --id ATTEMPT_ID --outcome no-change --observation 'Both local cases parsed identically'
contextforge checkpoint --summary 'What evidence changed' --next 'One distinct permitted experiment'
contextforge handoff --budget 1500
contextforge snapshot
contextforge hooks install
```

These are sample *API commands*, not a request to run target attacks. For field-learned mistakes and how the skill handles them, see `.agents/skills/contextforge/references/field-lessons.md`. For CLI details read `.agents/skills/contextforge/references/workflow.md`.

## What this cannot do

- Guarantee the optimal solution or identify a hidden anti-AI trap from no evidence.
- Recover clues never persisted before compaction, or hidden internal reasoning.
- Independently validate whether your reported evidence is genuine, or safely capture private secrets from a transcript.
- Circumvent contest rules forbidding scripts, automated attacks or AI-authored attempts.
- Concurrently protect the JSONL ledger from multiple writers; run one writer at a time.

**Security:** `.ctx` may contain sensitive research metadata and is gitignored by this repo. Don't commit project logs, credentials or challenge flags to a public repository. Validate challenge authorization before touching live targets.

## Run tests

```bash
python3 -m unittest discover -s tests -v
python3 ctx.py --help
```

The tests use temporary local fixture projects. No external-target requests are made.

## Historical failure-mode analysis

See `.agents/skills/contextforge/references/field-lessons.md`. These are generalized process lessons from earlier authorized research, not a complete or exhaustive import of all past conversations. The system cannot access past chat thoughts or guarantee that every challenge trap is found.

## One-line install from GitHub

Once uploaded to `nicetrykiddo/contextforge`, from an empty temporary directory run `git clone https://github.com/nicetrykiddo/contextforge.git /tmp/contextforge-install && bash /tmp/contextforge-install/install.sh`; then Codex can use `$contextforge`. Review code before installation and keep `.ctx/` private.