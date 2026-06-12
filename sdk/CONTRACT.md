# SDK — task/result contract (open)

The stable interface between an AI agent and the skill, identical across Claude Code,
Codex, and Cursor. Every capability is a command taking `--task task.json` and writing
`--out result.json`. This contract is open so anyone can build on it; the *engines*
behind the Professional capabilities are closed.

## Task
```json
{
  "stage": "0.1|1.0|1.1|2.0|3.0|review",
  "capability": "generate_bom | interference_check | dfm_check | static_strength | ...",
  "model": {"path": "C:/.../x.SLDASM", "type": "assembly|part|step"},
  "units": "SI_mm_t | SI_m_kg_s",
  "solver": "auto|ansys|abaqus|solidworks|...",
  "inputs": { },
  "apply": false,
  "workdir": "C:/.../run1"
}
```

## Result
```json
{
  "status": "ok | needs_input | deck_only | failed | enterprise_required",
  "stage": "...", "capability": "...",
  "results": { }, "assumptions": [ ], "caveats": [ ],
  "needs_input": [ ], "artifacts": { }, "run_command": null,
  "upgrade": {"edition":"Professional","feature":"...","info_url":"..."}
}
```

## Status meaning
- `ok` — ran, valid results.
- `needs_input` — required inputs missing; nothing ran.
- `deck_only` — tool not installed; deck/macro generated + `run_command`.
- `failed` — ran but crashed / didn't converge; results not valid.
- `enterprise_required` — capability needs the Professional core (not installed); see `upgrade`.

## Editions
- **Community (this repo, open):** CAD understanding (BOM, counts, standard parts, assembly explainer), assembly diagnostics (interference / errors / mates / clearance), basic PDF/HTML report, SolidWorks/STEP connectors, this contract.
- **Professional (closed):** DFM/DFA rule engines, automated FEA (auto load-face/mesh + solver), fatigue, modal, thermal, CFD, motion, optimization, agent design-review + risk scoring, procurement/costing, advanced report templates. Community commands for these return `enterprise_required` and degrade gracefully; install the licensed `mechanical_ai_core` package to enable them.

## Extending
A Professional core registers as an importable `mechanical_ai_core` module exposing
functions (`run_analysis(task)`, `dfm_check(task)`, `optimize(task)`,
`design_review(task)`, `risk_score(task)`, `procurement_list(task)`,
`advanced_report(results, out, title)`) that return contract-shaped results. The
Community commands auto-detect and delegate to it via `scripts/core_bridge.py`.
