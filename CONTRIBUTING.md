# Contributing

Thanks for your interest in the Mechanical AI Review Skill. This is the open
**Community Edition** — contributions to it are welcome.

## What lives here (and what doesn't)
This repo is the **Community Edition**: CAD understanding (BOM, standard parts,
assembly explanation), interference/clearance diagnostics, basic DFM, single-load-case
static and first-3-mode modal analysis, a simple risk score, and reporting.

Advanced engineering (full/auto FE, fatigue, thermal, CFD, optimization, advanced
DFM/DFA rule libraries, automated design review) is the closed **Professional Edition**
and is **not** part of this repo. PRs that try to add those engines here will be
redirected — but a clean interface or a useful free-tier improvement is very welcome.

## Good first contributions
- New CAD connectors or better standard-part matching (`connectors/`)
- More free-tier geometric DFM rules (`scripts/free_fea.py`)
- Additional analytical static/modal cases (more sections, support conditions)
- Better reports, examples, or docs
- Bug fixes and clearer error messages

## Ground rules
- **Never fabricate engineering results.** Every command returns `ok` only when it
  truly computed something; otherwise `needs_input` / `deck_only` / `failed` /
  `enterprise_required`. Always surface `assumptions` and `caveats`.
- Keep the free tier honest: free-tier code uses **public textbook formulas only** —
  do not import Professional methods/thresholds.
- Respect the JSON contract in `sdk/CONTRACT.md` — commands take `--task`/`--out` and
  return the standard result shape.
- No new pip dependencies for the orchestration layer (it must run in Codex/Cursor
  sandboxes). Reports may optionally use `reportlab`.

## Developing
```bash
git clone https://github.com/almightyshui/Mechanical-AI-Skill
cd Mechanical-AI-Skill
bash examples/demo.sh          # runs a full pass, no SolidWorks needed
python -m py_compile scripts/*.py connectors/*.py   # quick sanity check
```
Please run `examples/demo.sh` before opening a PR and confirm it still completes.

## Reporting bugs / requesting features
Use the issue templates (Bug report / Feature request). For usage questions, open a
Discussion instead.

By contributing, you agree your contributions are licensed under the repo's MIT License.
