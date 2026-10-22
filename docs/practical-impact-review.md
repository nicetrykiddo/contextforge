# ContextForge impact and compatibility review (v3.4.1 -> v3.4.2)

This is a **threat-model and workflow review**, not a vulnerability leaderboard.
The earlier audit tested whether a behavior was reproducible; it did not adequately
test an attacker's access, practical harm, intended functionality, or the side
effects of changing behavior. Its "High" labels were not substantiated as
remote-exploitable security severity. Most observations were local integrity
or workflow issues. Local adversarial fixtures are useful but not equivalent
to real-user impact.

## The trust boundary matters

- The CLI runs as the user's OS account, reads and writes a user-managed
  project `.ctx/` (normally mode 0700), and does not expose a network server.
- The earlier `HANDOFF.md`, `MISSION.md` and `compactions/` symlink
  demonstrations required a crafted entry in *already initialized private
  metadata*. No remote attacker access was shown. Their observable effect was
  limited to files the running user could access. Neither RCE nor privilege
  escalation was shown.
- It is still worth not following unexpected links in managed state: mistakes
  and other local tools can create them. Keep the defensive protections, but
  do not market those synthetic conditions as high-severity remote findings.
- The newly identified `AGENTS.md` issue was more plausible: a cloned
  repository can supply a dangling symlink **before** ContextForge is
  initialized. The v3.4.1 installer checked `.exists()`, which ignores a
  dangling symlink; writing the generated `AGENTS.md` could create a
  previously nonexistent outside file, under the user's own permissions.
  This was reproduced in GitHub Actions and corrected in v3.4.2.
  The observed path did **not** overwrite an existing file.
- Hardlink checks and rejection of named pipes are defensive, but accidental
  legitimate use of hardlinked metadata could now fail. This is a deliberate
  unsupported configuration rather than proof of an attacker.

## Intended behavior versus actual damage

| Previously flagged behavior | Actual harm / plausible usage | Decision |
| --- | --- | --- |
| H1/H2 handoff/snapshot follows metadata symlink | Possible local out-of-tree overwrite if an entry in private `.ctx/` is crafted; no OS privilege bypass | Keep atomic replacements and link rejection; correct severity claim |
| H3 mission symlink points outside root | Exposes an already readable file to agent output. A subsequent external disclosure was **not** shown | Keep internal source-path protection |
| H6 snapshot directory symlink | Archive goes outside private metadata if path crafted. Some people deliberately symlink backup directories | Keep current strict private archive boundary; clearer compatibility documentation |
| H4 unrelated task makes checkpoint "stale" | False warning and avoidable interruptions; not security harm | Keep task-scoped staleness fix |
| H5 explicit query emits unrelated records | Consumes context; however broad recall is sometimes intentional | Keep focused behavior; use queryless or explicitly broad retrieval for exploration |
| H7 approve from another local process | CLI was being conflated with identity verification. A TTY prompt is **not human authentication** | Keep optional manual review convention, but do not claim a security barrier; headless activation is unsupported |
| H8 search spans tasks | May mix target-specific notes, but cross-task recall is also useful and all files belong to the same OS user | Keep task-specific default and documented `--all-tasks` |
| H9 generated instructions refer to stale shared mission | Can restore an incorrect objective after compaction | Keep active-task recovery fix |
| H10 adding task does not auto-focus | **Could be intentional:** creating backlog must not steal focus from ongoing work. v3.4.1 auto-focus fix caused a regression | Revert to preserving existing focus; add explicit `task add --focus` |
| H11 scanning B forgets A paths | Loss of combined file index; but v3.4.1 fix preserved overlapping stale paths even after deletion | Keep combined index; remove paths verified absent by completed scoped scans |
| Scoped index completion warning | A later small task scan could wrongly clear the earlier task's truncation warning | Maintain per-task truncation status; allow completed rescans to clear their own warnings |

## Specific regression demonstrations

Tests in `tests/test_practical_impact.py` run using temporary project
fixtures (not mocks of command output).

1. **Backlog:** Save a checkpoint on A, create B to investigate later.
   Under 3.4.1, `active_task` silently changed to B and the next unqualified
   checkpoint could be misfiled. Fixed: adding B keeps A active unless
   `--focus` is supplied, and CLI output makes this explicit.
2. **Overlapping scopes:** A scans project `.`; B scans `src/`; remove
   `src/old.txt`. Under 3.4.1, B's completed scan retains the now-missing
   file because A also indexes it. Fixed: deletion applies to the physical
   file inventory when a complete scoped scan verifies absence.
3. **Closed task:** Closing A then explicitly focusing A previously made
   `active_task=A` while `tasks[A].status=closed`. Fixed: a focus command
   intentionally reopens A with consistent status.
4. **Partial index:** A's scan truncates; B's smaller scan completes. A global
   "complete" status would be false. Preserve per-task truncation information,
   then clear it if A is rescanned completely.
5. **Project-root symlink:** A dangling `AGENTS.md` symlink before init
   previously caused creation of an outside file. Fixed: a symlink is treated
   as an existing entry and preserved.

The tests demonstrate deterministic command behavior, not that the model
would or would not achieve more tasks with these changes.

## Previously shipped safeguards: possible negative side effects

- **Global reasoning memory:** Approved reminders are matched using broad
  keywords/concepts. No held-out real-model evidence establishes a net
  gain or rules out negative transfer. Approval through an interactive
  terminal has operational cost and can be automated by an agent that
  controls its own PTY. Keep optional, not a machine-enforced safety policy.
- **Hypothesis-pressure cap:** Hiding rejected hypotheses reduces prompt
  clutter, but may obscure a relevant rejected avenue unless the agent
  explicitly queries history. Results show mechanical retrieval only.
- **Snapshot allowlist:** Backing up only task mission/scope cards avoids
  collecting arbitrary Markdown, but may omit unrelated task-local notes.
  Store important evidence in source-referenced records and independent
  project files; don't call snapshots a complete project backup.
- **Metadata symlink/hardlink restrictions:** Legitimate dotfile or backup
  managers using links in `.ctx/` may now fail. There is no general-purpose
  symlink mode; this is a tradeoff, not a universal improvement.
- **Compaction hooks:** Support varies with Codex frontend and configuration;
  a 10-second hook can still fail under sufficiently large or slow backups.
  Real large-ledger and real-compaction test results remain separate from
  successful offline snapshot tests.
- **Query restrictions:** Focused retrieval prevents noise but cross-task
  investigation needs explicit `search --all-tasks`; broad exploration
  should not be mistaken for data leakage between OS principals.
- **Codex agent effectiveness:** Nothing in these CLI tests establishes
  fewer false bug reports or successful bounties. The user-supplied
  Wordfence rollout documented two local reproduction claims and zero
  eligible confirmed reports, but no counterfactual no-skill run.

## Remaining limitations and future verification

Test real Codex workflows with and without ContextForge on independent,
broad held-out tasks. Include true interruptions/compactions, overlapping
tasks, environment changes, negative-transfer cases and recovery from
false hypotheses. Track completion, repeated action sequences and full
token/time costs. Avoid new "reasoning engines" until benefits exceed
native Codex with acceptable regressions.

This review intentionally does **not** designate all unusual behaviors as
vulnerabilities, or claim all remaining defects have been found.
