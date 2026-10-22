# Command snippets (global install; run from project root)

```bash
contextforge init --mode ctf --scope .
contextforge task add 'Research challenge' --goal 'Evaluate task from original specification, with bounded local tests'
$EDITOR .ctx/SCOPE.md
$EDITOR .ctx/MISSION.md
contextforge scan
contextforge rethink --budget 1500

contextforge lane start 'Check parsing mismatch' --route parser-mismatch \
  --hypothesis 'Parser accepts a local malformed fixture' \
  --falsifier 'Local parser rejects that fixture' --minutes 20
contextforge lane gate --signature 'Execute case A against local parser revision X' \
  --predict 'Fixture A passes parser unexpectedly'
# Observe only permitted behavior; no auto-target interaction.
contextforge add --kind evidence --status verified --title 'Fixture A outcome' \
  --body 'Local parser returned X' --proof 'Fixture/test/output file path'
contextforge lane result --id A-ID --outcome progress --observation 'New behavior X' --evidence R-ID
contextforge checkpoint --summary 'Verified result' --next 'Discriminating test' \
  --why-next 'Tests the key assumption' --pivot-if 'Matched control gives the same result'
contextforge handoff --budget 1500
```

Use `contextforge lane history` to see exhausted approaches. To retry the **same** underlying route, provide a NEW verified evidence record observed after the previous route stopped and pass its ID with `lane start --new-evidence`.

If existing projects contain v1 state: `contextforge upgrade` creates only the missing mission card. Preserve the existing `AGENTS.md`; merge the short contract manually and use the new global CLI rather than an old project-local `ctx.py`.

## Backlog versus active task

When a task is already active, `contextforge task add 'Later work'`
creates a separate work item without moving the active pointer. Use
`contextforge task add 'Switch now' --focus` to create and focus immediately
or `contextforge task focus T-ID` to resume an existing task. Before an
unqualified `add` or `checkpoint`, ensure the active task matches the work.
This intentionally restores the pre-3.4.1 default because automatically
switching during backlog creation caused plausible misfiling of evidence.

## How to keep strategic context portable\n\nAfter a **consequential choice**, optionally add `--why-next` (evidence connecting the next action to the actual win condition) and `--pivot-if` (observable failure/stop criterion). Both fields survive fresh sessions and compaction; they are not compulsory for routine steps. Avoid updating a checkpoint after every command or rewriting a plan merely for appearances. When two genuine attempts fail for the same reason, reconsider the assumption or selection strategy rather than only switching filenames/targets. If a cheap acceptance criterion can invalidate a candidate, check it before expensive execution.\n\nThe fuller cross-domain diagnostic lives in `decision-quality.md`. Do not load it on every turn.\n\n## What belongs in mission versus records?
- `MISSION.md`: exact goal, win test, full original source path, hard scope limits, interfaces, suspicious premises and unknowns. Human reviewed. Pinned each handoff.
- Records: traceable observations, what each test distinguishes, failed assumptions, negative results, decisions, and evidence references. Updated per investigation.
- The model must inspect full original source when subtleties matter; no lossy summary can guarantee optimal reasoning.

## When not to use
- One-shot arithmetic or simple informational question.
- Tasks where no evidence loop, iteration, or context handoff is needed.
- Any activity forbidden by the owner's rules, including prohibited target automation.

## Compaction hardening
```bash
# One-time after installing the global CLI and skill (opt in, inspect hooks before trusting):
contextforge hooks install
# After enabling `hooks = true` under [features] in ~/.codex/config.toml,
# restart Codex and approve the hook trust prompt.

# In an investigation, as soon as a decisive fact appears:
contextforge pin --title 'Subtle constraint' --body 'Precisely what differs, with source reference' --status verified --proof 'evidence/local-log:line'
contextforge checkpoint --summary 'Current verified state' --next 'Single distinguishing test'
contextforge snapshot
```
`PreCompact` snapshots only **already recorded** project metadata to `.ctx/compactions/`, not the full chat or private model reasoning. `PostCompact` shows a recovery reminder. `SessionStart` asks Codex to load the mission and fresh handoff. Hooks require support, activation and trust; some frontends may not deliver them reliably. Use manually recorded pins and checkpoints even if hooks are enabled. Snapshots may contain sensitive research metadata; `.ctx/` stays excluded from Git by default.
