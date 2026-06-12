# Install & use — Claude Code, Codex CLI, Cursor

This skill uses the cross-platform **Agent Skills** standard (`SKILL.md`). The same files work in Claude Code, Codex CLI, and Cursor — only the install directory differs. Pick whichever method fits.

## Fastest: the install script
From the unpacked skill folder:
```bash
bash install.sh all          # install to Claude Code + Codex (+ Cursor if in a repo)
bash install.sh claude       # just Claude Code   (~/.claude/skills)
bash install.sh codex        # just Codex CLI     (~/.codex/skills)
bash install.sh cursor       # Cursor (project)   ./.cursor/skills
bash install.sh claude --project   # project scope ./.claude/skills (shared via git)
```
With no argument it detects installed agents and installs to those. Then start a new agent session — the skill loads automatically when a request matches its description.

## Claude Code

**As a plugin** (this folder includes `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`):
```bash
# shorthand owner/repo (or a full git URL, or a local path):
/plugin marketplace add almightyshui/Mechanical-AI-Skill
/plugin install mechanical-ai-skill
# or browse: type /plugin , go to Discover, pick it
```
After install, `/reload-plugins` (or restart the session) to load it.

**As a plain skill** (no plugin):
```bash
mkdir -p ~/.claude/skills
cp -r mechanical-ai-skill ~/.claude/skills/      # personal (all projects)
# or project scope, shared via git:
mkdir -p .claude/skills && cp -r mechanical-ai-skill .claude/skills/
```

## Codex CLI
```bash
mkdir -p ~/.codex/skills
cp -r mechanical-ai-skill ~/.codex/skills/       # personal
# or project scope:
mkdir -p .codex/skills && cp -r mechanical-ai-skill .codex/skills/
```
Codex loads skills at session startup and matches them by the `description`. (An optional `openai.yaml` can add Codex-only UI/MCP hints; not required — the `SKILL.md` is sufficient.)

## Cursor
Cursor uses **project-scoped** skills:
```bash
mkdir -p .cursor/skills && cp -r mechanical-ai-skill .cursor/skills/
```

## One folder, every agent (symlink)
If you keep a single canonical copy, symlink the others to it so an update propagates everywhere:
```bash
# canonical copy in ~/.claude/skills, link the rest:
ln -s ~/.claude/skills/mechanical-ai-skill ~/.codex/skills/mechanical-ai-skill
ln -s ~/.claude/skills/mechanical-ai-skill ./.cursor/skills/mechanical-ai-skill
```

## Directory reference
| Agent | Personal | Project (shared via git) |
|-------|----------|--------------------------|
| Claude Code | `~/.claude/skills/` | `.claude/skills/` |
| Codex CLI | `~/.codex/skills/` | `.codex/skills/` |
| Cursor | — (project only) | `.cursor/skills/` |

## Verify it's working
```bash
# from inside the installed skill folder:
bash examples/demo.sh           # runs the full task->command->result flow (no solver needed)
bash scripts/detect_solvers.sh  # shows which simulation tools are live on this machine
```
Then in an agent session, try: *"check this assembly for interference"*, *"can this bracket hold 200 kg?"*, or *"optimize this link, cut 20% weight"* — the agent will route to the skill (see `AGENT_README.md` for the call flow).

## Update / remove
- **Update**: re-run `install.sh`, or replace the folder with the new version (it overwrites).
- **Remove**: delete the `mechanical-ai-skill` folder from the agent's skills directory.
- **Disable temporarily**: rename it with a leading underscore (e.g. `_mechanical-ai-skill`).

## Notes
- The scripts are plain Python 3 + bash with no pip dependencies, so they run in Codex's sandbox and Cursor alike. The SolidWorks path additionally needs `pywin32` on Windows; the FE/CFD paths need the respective solver on `PATH` — without them the skill returns `deck_only` (generates the deck/macro) rather than failing.
- Plugins/skills run with your agent's permissions — only install from sources you trust, and read `SKILL.md` first.
