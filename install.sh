#!/usr/bin/env bash
set -euo pipefail

# One command from GitHub or a local checkout; never modify a target unless --project is given.
repo='https://github.com/nicetrykiddo/contextforge.git'
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
tempdir=''
project=''
mode='general'
with_hooks=0
while (($#)); do
  case "$1" in
    --project) (($# >= 2)) || { echo 'Missing --project value' >&2; exit 2; }; project="$2"; shift 2 ;;
    --mode) (($# >= 2)) || { echo 'Missing --mode value' >&2; exit 2; }; mode="$2"; shift 2 ;;
    --hooks) with_hooks=1; shift ;;
    -h|--help) echo 'Usage: bash install.sh [--project DIR] [--mode ctf|bugbounty|investigation|software|general] [--hooks]'; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done
case "$mode" in ctf|bugbounty|investigation|software|general) ;; *) echo "Invalid mode: $mode" >&2; exit 2 ;; esac
if ! test -f "$here/ctx.py"; then
  command -v git >/dev/null || { echo 'git required for remote bootstrap' >&2; exit 1; }
  tempdir="$(mktemp -d)"
  trap 'rm -rf "$tempdir"' EXIT
  git clone --depth=1 --quiet "$repo" "$tempdir/contextforge"
  here="$tempdir/contextforge"
fi
python3 -c 'import sys; assert sys.version_info >= (3,10), "Python 3.10+ required"'
mkdir -p "$HOME/.local/bin" "$HOME/.agents/skills/contextforge/references"
install -m 0755 "$here/ctx.py" "$HOME/.local/bin/contextforge"
install -m 0644 "$here/.agents/skills/contextforge/SKILL.md" "$HOME/.agents/skills/contextforge/SKILL.md"
install -m 0644 "$here/.agents/skills/contextforge/references/workflow.md" "$HOME/.agents/skills/contextforge/references/workflow.md"
install -m 0644 "$here/.agents/skills/contextforge/references/field-lessons.md" "$HOME/.agents/skills/contextforge/references/field-lessons.md"
cli="$HOME/.local/bin/contextforge"
if [[ -n "$project" ]]; then
  mkdir -p "$project"
  if [[ -f "$project/.ctx/state.json" ]]; then
    (cd "$project" && "$cli" upgrade)
  else
    (cd "$project" && "$cli" init --mode "$mode" --scope .)
  fi
fi
if ((with_hooks)); then "$cli" hooks install; fi
printf 'ContextForge installed: %s\nCodex skill: %s\n' "$cli" "$HOME/.agents/skills/contextforge/SKILL.md"
if [[ -n "$project" ]]; then
  printf 'Project: %s\nNext: fill .ctx/MISSION.md and .ctx/SCOPE.md using original sources before testing.\n' "$project"
fi
printf 'Restart Codex to discover the skill. Review hooks.json changes before enabling hooks.\n'
