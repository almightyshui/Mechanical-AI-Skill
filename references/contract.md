# JSON task / result contract

The full, canonical contract lives in `../sdk/CONTRACT.md` — read it first. This note
summarizes the part relevant while using the Community Edition.

Every capability is a command: `--task task.json` → `--out result.json`. Result
`status` is one of `ok | needs_input | deck_only | failed | enterprise_required`.

## Community capabilities (this repo, open)
- **Stage 0.x — CAD understanding** (`scripts/sw_understand.py`): `generate_bom`,
  `part_count`, `identify_standard_parts`, `explain_assembly`.
- **Stage 0.x — mechanism detection** (`scripts/sw_mechanism.py`): `mechanism_detect` — identify mechanism TYPE (gear train / belt / chain / lead screw) + confidence + evidence.
- **Stage 1.0 — diagnostics** (`scripts/sw_diagnostics.py`): `interference_check`,
  `assembly_error_check`, `mate_conflict_check`, `clearance_check`.
- **Geometry** (`scripts/sw_export.py`): `export_step`.
- **Reporting** (`scripts/report_pdf.py`): render result JSON(s) → basic PDF/HTML.

## Professional capabilities (closed; commands return `enterprise_required`)
- DFM/DFA (`scripts/sw_dfm.py`): `dfm_check`, `dfa_check` (basic)
- Automated FEA/CAE (`scripts/run_analysis.py`): `static_strength`, `modal`,
  `thermal`, `fatigue`, `cfd`, `motion`
- Optimization (`scripts/optimize.py`): `topology_optimize`, `parametric_lightweight`
- Design review (`scripts/design_review.py`): `design_review`, `risk_score`,
  `procurement_list`
- Advanced report template (`report_pdf.py --advanced`)

When the Professional core (`mechanical_ai_core`) is installed, these same commands
return real results; otherwise they return `enterprise_required` with an `upgrade`
note and never fabricate output. See `../sdk/CONTRACT.md` for the extension interface.
