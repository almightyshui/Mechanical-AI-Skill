# Test Matrix

Regression coverage for the Community Edition. Every release should re-run these
before publishing, so a rule change that fixes one assembly doesn't silently break
another.

## Status legend
- **PASS** — runs clean, output is sane and honest (no invented data, correct status/headline)
- **PARTIAL** — runs, but a known limitation applies (noted)
- **FAIL** — broken; do not release

## Assembly types

| Type | Sample | review_summary | BOM | Mechanisms | Vendors | Categories | Findings | Notes |
|---|---|---|---|---|---|---|---|---|
| Robot welding cell | 机器人自动焊接机.STEP (39 MB) | PASS | PASS | PASS | PASS | PASS | PASS | Reference case; see `examples/robot_welding_cell/` |
| Fixture | — | — | — | — | — | — | — | TODO: add a fixture STEP |
| Conveyor / transfer | — | — | — | — | — | — | — | TODO |
| Packaging machine | — | — | — | — | — | — | — | TODO |
| Gantry system | — | — | — | — | — | — | — | TODO |

## Input-format coverage

| Input | Status | Notes |
|---|---|---|
| `.STEP` / `.step` | PASS | standard |
| Non-standard extension (e.g. `.snapshot.1`) | PASS | detected by content, not suffix |
| `.zip` of an assembly | PASS | auto-extracts, picks top-level STEP |
| Unzipped folder | PASS | resolves the STEP inside |
| Missing `model.path` | PASS | returns needs_input with a copy-paste example |

## Degradation coverage (no SolidWorks / no geometry kernel)

| Capability | Behaviour | Status |
|---|---|---|
| generate_bom / part_count | name-level BOM from STEP text | PASS |
| review_summary / mechanism / vendor / category | run from STEP text | PASS |
| interference / clearance / assembly_error / mate_conflict | emit a runnable macro (`deck_only`) | PASS |
| design_review / procurement_list | `enterprise_required` (Professional) | PASS |

## Per-release regression log

| Version | Date | Result | Notes |
|---|---|---|---|
| 0.7.0 | 2026-06-13 | PASS | Findings Engine; welding-cell reference case clean |

> Append a row each release. If any reference case drops from PASS, fix before publishing.
