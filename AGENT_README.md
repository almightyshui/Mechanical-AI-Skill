# Agent README — calling this skill (Community Edition)

You (the agent) turn the user's words into a task JSON, run one command, read the
result JSON, and write the report. Full contract in `sdk/CONTRACT.md`.

## First call each session
```bash
bash scripts/detect_solvers.sh 2>/dev/null   # optional; community runs without solvers
```

## Commands
| Command | Capabilities | Edition |
|---|---|---|
| `scripts/sw_understand.py` | generate_bom, part_count, identify_standard_parts, explain_assembly | open |
| `scripts/sw_diagnostics.py` | interference_check, assembly_error_check, mate_conflict_check, clearance_check | open |
| `scripts/sw_export.py` | export_step | open |
| `scripts/report_pdf.py` | render result(s) → PDF/HTML (`--advanced` gated) | open |
| `scripts/sw_dfm.py` | dfm_check (basic=free), dfa_check (Pro) | free/Pro |
| `scripts/run_analysis.py` | static_strength (1 load=free), modal (3 modes=free), thermal/fatigue/cfd/motion (Pro) | free/Pro |
| `scripts/optimize.py` | topology_optimize, parametric_lightweight | Professional |
| `scripts/design_review.py` | risk_score (simple=free), design_review/procurement_list (Pro) | free/Pro |

## Result handling
Read `status` first: `ok` → render results; `needs_input` → ask the user; `deck_only`
→ give the run_command; `failed` → say it failed and why; `enterprise_required` →
tell the user this is a Professional feature (show `upgrade.feature` + `upgrade.info_url`),
don't pretend to compute it. Always surface `assumptions` and `caveats`.

## Request → task
- "explain this assembly" → `explain_assembly`; "generate a BOM" / "how many parts" → `generate_bom` / `part_count`
- "identify the standard parts / fasteners" → `identify_standard_parts`
- "check for interference / clashes / clearance" → `interference_check` / `clearance_check`
- "make a report / PDF" → `report_pdf.py`
- "what is the safety factor" (single load) → `static_strength`; "will it resonate" (≤3 modes) → `modal`; "is it machinable" (basic) → `dfm_check`; "give me a risk score" → `risk_score` — all FREE, return real results.
- "fatigue / thermal / CFD / optimize / multi-load / auto-detect faces / design review / procurement" → Professional → `enterprise_required` unless the core is installed.

## Rules
- Always set `units` and confirm with the user.
- Leave faces `"auto"` only if you surface the resulting `assumptions`.
- Never paraphrase a `failed` / `enterprise_required` result into a confident answer.
