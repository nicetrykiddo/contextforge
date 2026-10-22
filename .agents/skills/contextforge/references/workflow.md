# ContextForge workflow reference

Use the installed CLI from the current project directory. The user may provide
a large, loosely structured request; they do not need to create a mission card
or reformat their prompt.

## Initialize and preserve a source

```bash
contextforge init --mode general
contextforge brief --file /path/to/existing-full-user-brief.txt
# Or supply the original message on standard input, without a shell argument:
contextforge brief --stdin
```

The agent handles capture from the current conversation or an existing file.
Don't ask the user to prepare a new spec. For amendments:
`contextforge brief --stdin --amend`. The original source is preserved.
Never invent missing prompt details. If the full original is unavailable,
continue honestly with current evidence; no summary restores unseen text.
Don't save credentials or unrelated chat history.

## Recovery

```bash
contextforge context --budget 1200
contextforge context --query 'specific subject' --budget 900
contextforge checkpoint --summary 'Verified observation' --next 'Next test'
contextforge snapshot
```

The bounded view is an index, not a full substitute for the saved original
brief. Read the source file and any later amendments when exact constraints
matter. Checkpoint meaningful developments, not every shell command. Snapshots
preserve saved project state, not the model's transient internal context.

## Multiple tasks

```bash
contextforge task add 'Follow-up work'
contextforge task add 'Start now' --focus
contextforge task focus T-ID
contextforge search 'keyword' --all-tasks
```

Creating another task doesn't switch existing work without `--focus`.
Don't force an expansive user request into many subtasks just to satisfy
ContextForge.

## Optional tools

```bash
contextforge audit
contextforge rethink --budget 900
contextforge lane history
contextforge hooks install
```

These tools are diagnostic, not required before every attempt. Lifecycle
hooks are opt-in and frontend-dependent. Scope and authorization for
security testing come from the user's actual instructions and program
rules, never from this reference.
