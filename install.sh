#!/usr/bin/env bash
# Install mechanical-ai-skill as an Agent Skill into Claude Code, Codex CLI, and/or
# Cursor. The SKILL.md format is a cross-platform open standard; this script just
# copies the skill folder into each agent's skills directory.
#
# Usage:
#   bash install.sh                 # interactive: detect agents, ask which to install
#   bash install.sh claude          # install only to Claude Code (~/.claude/skills)
#   bash install.sh codex           # install only to Codex CLI   (~/.codex/skills)
#   bash install.sh cursor          # install to project Cursor   (./.cursor/skills)
#   bash install.sh all             # install to claude + codex (+ cursor if in a repo)
#   bash install.sh claude --project   # project scope (./.claude/skills) instead of ~
set -u

SKILL_NAME="mechanical-ai-skill"
SRC="$(cd "$(dirname "$0")" && pwd)"
PROJECT_SCOPE=0
TARGETS=()

for arg in "$@"; do
  case "$arg" in
    --project) PROJECT_SCOPE=1 ;;
    claude|codex|cursor|all) TARGETS+=("$arg") ;;
    *) echo "unknown arg: $arg"; exit 2 ;;
  esac
done

# personal vs project destination for an agent prefix (e.g. .claude / .codex)
dest_dir() {
  local prefix="$1"
  if [ "$PROJECT_SCOPE" -eq 1 ] || [ "$prefix" = ".cursor" ]; then
    echo "$(pwd)/${prefix}/skills"        # project scope (Cursor is project-only)
  else
    echo "$HOME/${prefix}/skills"         # personal scope
  fi
}

install_to() {
  local label="$1" prefix="$2"
  local dir; dir="$(dest_dir "$prefix")"
  mkdir -p "$dir"
  local target="$dir/$SKILL_NAME"
  rm -rf "$target"
  # copy everything except VCS/build cruft
  ( cd "$SRC" && find . -type d -name '__pycache__' -prune -o -type f -print \
      | grep -vE '\.(pyc)$' | while read -r f; do
          mkdir -p "$target/$(dirname "$f")"; cp "$f" "$target/$f"
        done )
  chmod +x "$target"/scripts/*.sh "$target"/scripts/*.py "$target"/*.sh 2>/dev/null
  echo "  ✓ $label -> $target"
}

# auto-detect installed agents if no explicit target
detect_default() {
  local found=()
  [ -d "$HOME/.claude" ] || command -v claude >/dev/null 2>&1 && found+=("claude")
  [ -d "$HOME/.codex" ]  || command -v codex  >/dev/null 2>&1 && found+=("codex")
  [ -d "$(pwd)/.cursor" ] && found+=("cursor")
  printf '%s\n' "${found[@]}"
}

if [ "${#TARGETS[@]}" -eq 0 ]; then
  echo "No target given. Detected agents:"
  mapfile -t det < <(detect_default)
  if [ "${#det[@]}" -eq 0 ]; then
    echo "  (none detected) — pass one of: claude | codex | cursor | all"
    echo "  e.g.  bash install.sh all"
    exit 1
  fi
  printf '  %s\n' "${det[@]}"
  echo "Installing to all detected. (Re-run with an explicit target to narrow.)"
  TARGETS=("${det[@]}")
fi

# expand "all"
case " ${TARGETS[*]} " in
  *" all "*) TARGETS=(claude codex); [ -d "$(pwd)/.cursor" ] && TARGETS+=(cursor) ;;
esac

echo "Installing skill '$SKILL_NAME' (scope: $([ $PROJECT_SCOPE -eq 1 ] && echo project || echo personal)):"
for t in "${TARGETS[@]}"; do
  case "$t" in
    claude) install_to "Claude Code" ".claude" ;;
    codex)  install_to "Codex CLI"   ".codex"  ;;
    cursor) install_to "Cursor"      ".cursor" ;;
  esac
done

echo
echo "Done. Start a new agent session — the skill loads automatically when a request"
echo "matches its description (e.g. \"check this assembly for interference\","
echo "\"can this bracket hold 200 kg\", \"cut 20% weight\")."
echo "Verify the call flow any time with:  bash $SKILL_NAME/examples/demo.sh"
