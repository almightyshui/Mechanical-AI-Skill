# Example task JSONs

**Quick start:** `bash demo.sh` runs the full request → result flow (no SolidWorks
needed) and shows both the open features and the graceful `enterprise_required` gating.

| File | Command | Tier |
|------|---------|------|
| 00_generate_bom / 01_explain_assembly | `python ../scripts/sw_understand.py --task <file> --out result.json` | free |
| 10..13 interference / errors / mates / clearance | `python ../scripts/sw_diagnostics.py --task <file> --out result.json` | free |
| 17_dfm_basic | `python ../scripts/sw_dfm.py --task 17_dfm_basic.json --out result.json` | free (basic) |
| 14_export_step | `python ../scripts/sw_export.py --task 14_export_step.json --out result.json` | free |
| 20_static_free | `python ../scripts/run_analysis.py --task 20_static_free.json --out result.json` | free (single load) |
| 21_modal_free | `python ../scripts/run_analysis.py --task 21_modal_free.json --out result.json` | free (3 modes) |
| 42_risk_score_free | `python ../scripts/design_review.py --task 42_risk_score_free.json --out result.json` | free (simple) |
| 22_thermal_PRO | `python ../scripts/run_analysis.py --task 22_thermal_PRO.json --out result.json` | Professional* |
| 40_design_review_PRO | `python ../scripts/design_review.py --task 40_design_review_PRO.json --out result.json` | Professional* |

\* Professional examples return `enterprise_required` until the licensed core is installed.

Render any result into a report:
`python ../scripts/report_pdf.py --results result.json --out report.pdf`

Notes: `C:/work/...` paths assume a Windows SolidWorks host — change to yours.
`face:"auto"` lets the (Professional) engine pick faces and reports the choice in `assumptions`.
