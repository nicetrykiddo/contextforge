# ContextForge 3.3

**Long-session project memory for Codex. Not a model guardrail, policy override, or agent controller.**

ContextForge keeps critical working context outside the conversation so CTF, bug bounty, investigation, software, and general projects can continue through compaction and new chats without repeating hours of discovery.

## What stays in context

- **Hot (always first):** exact mission/source pointer, active task, latest checkpoint, blocker, next action.
- **Warm (selected):** pinned observations, source-linked evidence, decisions, prior negative results.
- **Cold (on demand):** experiment histories, old logs, archived hypotheses, indexed file paths.

The CLI loads the hot layer **before** optional history, including when the token budget is tiny. It warns rather than silently presenting an incomplete summary as complete. More tokens are not always better; the goal is the right evidence, not maximum output.

**ContextForge does not alter LLM safety settings, system instructions, permissions, or tool policies.** It does not decide whether the agent may perform a task. Existing requirements and program rules remain in force. Experiment-lane commands and anti-loop diagnostics are optional recordkeeping, not a compulsory solving protocol.

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

## Efficient long-chat workflow

1. Fill `.ctx/MISSION.md` with the real objective, acceptance test and **path/link to the full original source**. Fill `.ctx/SCOPE.md` with any existing engagement context.
2. Use `contextforge task add 'Short goal' --goal 'Specific outcome'` to separate research threads. The first task uses the legacy `.ctx/MISSION.md`; adding a second task creates `.ctx/tasks/TASK_ID/MISSION.md` cards so each target has its own objective. **Fill the new task card**; do not reuse the first target's mission.
3. At startup or after compaction, run **one** `contextforge context --budget 1200`. The latest checkpoint now comes before long pinned or historical lists.
4. If you need only one topic, use `contextforge context --query 'authentication' --budget 900`, `contextforge search 'authentication'`, or inspect the referenced source file.
5. After a meaningful finding, use `contextforge pin --title 'Critical clue' --body 'Observation, conditions and limits' --status verified --proof 'logs/example.txt:42'`.
6. At a meaningful milestone, use `contextforge checkpoint --summary 'Current state' --next 'Precise next action'`. Checkpoints are isolated per active task. Before compaction, `contextforge snapshot`; for chat-switch text, `contextforge handoff --budget 1200`. Handoff **does not scan files automatically**; run `contextforge handoff --refresh` only when you need an updated file inventory.

Avoid recording every thought or rerunning `scan`, `audit`, and `rethink` at every chat turn: that just wastes the context you're trying to save. These commands remain available on demand.

## Persistent files

| Path | Role |
| --- | --- |
| `.ctx/MISSION.md` | Legacy/single-task mission and shared project mission |\n| `.ctx/tasks/TASK_ID/MISSION.md` | Independent target mission (multi-task projects) |
| `.ctx/SCOPE.md` | Existing project/program boundaries |
| `.ctx/state.json` | Tasks, per-task checkpoints, legacy checkpoint mirror, and bounded file inventory |
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

## Important limits

- Compaction is lossy; only information recorded **before** compaction can be restored.
- No hook can recover unrecorded internal thoughts, guarantee perfect memory, or interrupt an already-running tool/model call.
- Token budgets approximate 4 characters per token, not the model's exact tokenizer.
- Hook support varies by Codex version/frontend. Check that lifecycle callbacks actually fire.
- CLI project reads/writes are serialized via a project lock; global reasoning mutations have a separate lock. Direct Python API calls that bypass the CLI are not guaranteed transactional.\n- `--proof` remains an **attested pointer**, not independent validation. Use optional `--proof-file` to capture an SHA256 digest of a local artifact; `contextforge check` flags later changes. File integrity does not prove an exploit claim.\n- Project memory files use private permissions on initialization/upgrade; check ownership on shared machines.
- A compact handoff is an index into source evidence, **not a substitute for the original files**.

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
