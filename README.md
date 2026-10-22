# ContextForge

Project memory for long-running Codex work. ContextForge stores task goals, checkpoints, evidence and recovery state in local files so they can be retrieved in another session.

- Python 3.10+; standard library only
- Local CLI and reusable Codex skill
- Per-task missions, checkpoints and searchable evidence
- Bounded context output, handoff files and state snapshots
- Optional Codex compaction hooks and global reasoning reminders

## Install

Review [install.sh](install.sh) before running it.

**Global CLI and skill**

```bash
curl -fsSL https://raw.githubusercontent.com/nicetrykiddo/contextforge/main/install.sh | bash
```

**Install and initialize the current project**

```bash
curl -fsSL https://raw.githubusercontent.com/nicetrykiddo/contextforge/main/install.sh | bash -s -- --project "$PWD" --mode general
```

Modes: `general`, `software`, `investigation`, `bugbounty`, `ctf`. Modes select organizational templates; they don't change model permissions or behavior.

The installer places the CLI at `~/.local/bin/contextforge` and the skill at `~/.agents/skills/contextforge/`. Restart Codex after installing or updating the skill. Existing `.ctx/` state and project `AGENTS.md` files are preserved.

Compaction hooks are optional: add `--hooks` during installation, or run `contextforge hooks install` later. Verify hook support and configuration in your Codex frontend.

## Original requests

ContextForge is designed for large, multi-part prompts, not only short task
titles. The original request is the source of truth. `brief` stores its full
text in private local metadata while `context` emits a bounded pointer and
checkpoint for long-session recovery. A saved source is not rewritten or
silently replaced by an agent-generated summary. `brief --amend` records later
user instructions separately.

The CLI does **not** automatically access private Codex conversations. The
agent must provide text already visible in the session through stdin or an
existing source file. Nothing can reconstruct a user message that was lost
before it was captured.

## Quick start

From the project directory:

```bash
contextforge init --mode general
contextforge task add "Fix parser regression" --goal "Reproduce and fix null-input failure"
contextforge add --kind evidence --title "Failure reproduced" --body "Test fails on null input"
contextforge checkpoint --summary "Root cause isolated" --next "Add regression test"
contextforge context --budget 1200
```

Initialization is needed only once per project. **No manually written mission or separate specification is required.** For long tasks, the agent can save the original request verbatim with `contextforge brief --stdin` while that text is available, or `contextforge brief --file /path/to/existing-original.txt`. New instructions can be appended with `--amend`. Do not copy credentials or unrelated conversation history into the local brief.

For an existing active task, `task add` creates a backlog item without switching focus. Use `task add "Title" --focus` to create and switch, or `task focus T-ID` to resume a task.

### Resume after interruption

```bash
contextforge context --budget 1200
contextforge context --query "parser" --budget 900
contextforge search "parser"
contextforge snapshot
contextforge handoff --budget 1200
```

`context` prioritizes the active mission and last checkpoint. Topic searches retrieve saved evidence; `search --all-tasks` explicitly searches across tasks. Snapshots back up recorded state, not unsaved chat history.

In Codex, invoke the `$contextforge` skill when working on a long-lived project. It supplies guidance on when to save verified observations and recover state without turning routine actions into bookkeeping.

## Storage

| Path | Purpose |
| --- | --- |
| `.ctx/MISSION.md`, `.ctx/SCOPE.md` | Project objective and constraints |
| `.ctx/tasks/T-ID/` | Independent task missions and scope cards |
| `.ctx/state.json` | Active task, checkpoints and file inventory |
| `.ctx/records.jsonl` | Evidence, decisions and experiment records |
| `.ctx/briefs/` | Preserved original requests and subsequent amendments |
| `.ctx/lanes.json` | Optional experiment history |
| `.ctx/HANDOFF.md` | Generated resume summary |
| `.ctx/compactions/` | Local state snapshots |

Keep `.ctx/` private and out of public Git repositories. Avoid saving secrets in records or global lessons.

## Other commands

```bash
contextforge status
contextforge check
contextforge audit
contextforge rethink --budget 900
contextforge reasoning list
contextforge --help
```

`rethink` and global reasoning reminders are optional. For full CLI usage, see [the workflow reference](.agents/skills/contextforge/references/workflow.md).

## Testing and limitations

```bash
python3 -m unittest discover -s tests -v
python3 benchmarks/offline_recovery.py --noise 48 --replays 12
```

[Benchmark commands and methodology](BENCHMARKS.md) · [Measured offline results](benchmarks/RESULTS.md)

Offline tests cover storage, retrieval, task isolation and snapshots. **Comparative real-agent task-success results are not available**, so improved bug discovery, reasoning accuracy or token efficiency over native Codex has not been established.

ContextForge restores only information that was recorded. Lifecycle hooks and native compaction support depend on the Codex version and frontend. The snapshot archive has size and retention limits, and global reasoning reminders are not model retraining.

## License

No license file is currently included. Licensing terms must be clarified before reuse or redistribution.
