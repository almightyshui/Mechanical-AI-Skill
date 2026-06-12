---
name: mechanical-ai-skill
description: 'Mechanical engineering CAD-review skill for AI agents (Codex, Claude Code, Cursor) — Community Edition, freemium. Drives the SolidWorks API and reads STEP to: generate a BOM, identify standard parts, explain an assembly, check interference / clearances, run basic DFM, compute single-load-case static analysis (stress, deflection, safety factor) and first-3-mode modal (frequencies, resonance), produce a simple risk score, and render a PDF/HTML report — all free and real, no commercial solver needed. Trigger on a SolidWorks/STEP file or requests like "explain this assembly", "generate a BOM", "check for interference", "is this machinable", "what is the safety factor", "will it resonate", "give me a risk score", "make a report". Advanced work — fatigue, thermal, CFD, multibody dynamics, topology optimization, automatic load identification, advanced DFM/DFA, design review, procurement — is Professional Edition: those commands return enterprise_required and degrade gracefully until the licensed core is installed.'
---

# Mechanical AI Skill — Community Edition

A mechanical-engineering **CAD-review** skill for AI coding agents. It sits between the agent and SolidWorks/STEP and answers the everyday questions an engineer asks of a model: *What's in this assembly? Make me a BOM. How does it work? Does anything interfere? Give me a report.*

The agent turns a natural-language request into a JSON task; this skill runs it against the real tools and returns a structured result the agent reports back.

## Editions

This is the **open Community Edition**, freemium. On its own — no license — it does CAD understanding, assembly diagnostics, basic reporting, **and real entry-level analysis**: single-load-case static (stress / deflection / safety factor), first-3-mode modal (frequencies / resonance), basic DFM, and a simple risk score. Upload a STEP and get real results, not a demo.

Advanced engineering is **Professional Edition** (closed source): full/auto FE (multi-load, contact, nonlinear, automatic load-face / constraint / mesh), modal beyond 3 modes, fatigue / thermal / CFD / multibody dynamics, optimization & lightweighting, advanced DFM/DFA rule library, advanced risk scoring, automated design review, procurement, and advanced report templates. The Community commands cover these too: within the free tier they compute locally; beyond it they return `enterprise_required` (with an `upgrade` note) until the licensed `mechanical_ai_core` package is installed — they never crash and never fabricate results.

| Capability | Community (free) | Professional |
|---|---|---|
| BOM, part count, standard-part ID, assembly explainer | ✅ | ✅ |
| Interference / mate / clearance diagnostics | ✅ | ✅ |
| STEP export, basic PDF/HTML report | ✅ | ✅ |
| Static analysis | single load case | multi-load, contact, nonlinear, auto-faces |
| Modal analysis | first 3 modes | unlimited modes, prestressed |
| DFM | basic rules | advanced rule library + DFA |
| Risk score | simple roll-up | criticality-weighted, code-aware |
| Fatigue · thermal · CFD · multibody dynamics | `enterprise_required` | ✅ |
| Optimization / lightweighting | `enterprise_required` | ✅ |
| Auto load / constraint / mesh ID | `enterprise_required` | ✅ |
| Automated design review · procurement · advanced report | `enterprise_required` | ✅ |

## The JSON contract

Every capability is one command: `--task task.json` → `--out result.json`. Result `status` is `ok | needs_input | deck_only | failed | enterprise_required`, plus `results`, `assumptions`, `caveats`. The canonical schema is `sdk/CONTRACT.md`; a Community summary is `references/contract.md`.

## Commands

```bash
# Community (open) — work standalone
python scripts/sw_understand.py  --task task.json --out result.json   # BOM / count / std parts / explain
python scripts/sw_diagnostics.py --task task.json --out result.json   # interference / mates / clearance
python scripts/sw_export.py      --task task.json --out result.json   # export STEP
python scripts/report_pdf.py     --results r1.json --out report.pdf   # basic PDF/HTML report

# Professional (gated) — return enterprise_required unless the core is installed
python scripts/sw_dfm.py         --task task.json --out result.json   # DFM / DFA
python scripts/run_analysis.py   --task task.json --out result.json   # FEA / fatigue / modal / thermal / CFD / motion
python scripts/optimize.py       --task task.json --out result.json   # optimization / lightweighting
python scripts/design_review.py  --task task.json --out result.json   # design_review / risk_score / procurement_list
```

All commands degrade gracefully: if SolidWorks isn't installed the open commands return `deck_only` with a macro; if the Professional core isn't installed the gated commands return `enterprise_required`. Nothing is ever faked.

## What the Community Edition does

### CAD understanding (stage 0.x) — `sw_understand.py`
`generate_bom` (item / part / qty / standard-part flag), `part_count`, `identify_standard_parts`, and `explain_assembly` (returns the component + mate tree; the agent writes the working-principle explanation and a suggested assembly order). See `references/cad_understanding.md`.

### Assembly diagnostics (stage 1.0) — `sw_diagnostics.py`
`interference_check` (overlap volume per clashing pair, distinguishing likely press-fits from errors), `assembly_error_check` (rebuild / dangling refs), `mate_conflict_check` (over/under-defined), `clearance_check` (min-gap violations). See `references/assembly_diagnostics.md`.

### Geometry — `sw_export.py`
`export_step` for downstream use.

### Reporting — `report_pdf.py`
Render any result JSON(s) into a basic PDF (or HTML if reportlab is absent): status, results, BOM/finding tables, assumptions, caveats. `--advanced` uses Professional templates (gated).

## How it stays honest
- `needs_input` when data is missing (nothing runs); `deck_only` when SolidWorks is absent (macro generated); `failed` when a run errors; `enterprise_required` when a Professional capability isn't licensed.
- Every default and auto-choice goes in `assumptions`; every limit in `caveats`.
- Standard-part identification is a name heuristic — flagged for confirmation.

## Knowledge base (open)
`references/knowledge/` ships open engineering references for interpreting open-edition results and answering questions: `formulas.md` (criteria/formulas), `standards.md` (which code governs), `faq.md` (troubleshooting), `literature.md` (optional online lookup via the host's web tools). The DFM/DFA rule library and the simulation/optimization know-how are Professional.

## Install
See `INSTALL.md`. Short version — Claude Code plugin: `/plugin marketplace add almightyshui/Mechanical-AI-Skill` then `/plugin install mechanical-ai-skill`; or `bash install.sh all` for Codex/Cursor.

## File map
- `sdk/CONTRACT.md` — canonical task/result contract + edition/extension interface
- `connectors/` — open SolidWorks / STEP / BOM adapters
- `scripts/` — commands (open: sw_understand, sw_diagnostics, sw_export, report_pdf; gated stubs: sw_dfm, run_analysis, optimize, design_review; `core_bridge.py` does the detect-and-delegate)
- `references/` — open docs (contract, cad_understanding, assembly_diagnostics, solidworks connector, units, materials) + `knowledge/`
- `examples/` — task templates; `demo.sh` shows the open flow + graceful gating
