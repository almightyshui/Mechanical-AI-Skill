# Benchmarks

How the Community Edition performs on real assemblies. **The structural numbers below
are real** (parsed from actual STEP files); timing columns are filled in per machine —
run `examples/demo.sh` or the individual commands and record your own, since speed
depends on your hardware and whether SolidWorks is in the loop.

> Honesty note: a STEP file carries no mates / FEA / fastener names, so part and
> fastener counts from a STEP are geometry-level (see the welding-cell case study).
> Numbers marked *(measure)* are placeholders for you to fill on your machine — they
> are intentionally left blank rather than estimated.

## Parsed assemblies

| Assembly | Source | Unique parts | Instances | Subassemblies | Depth | Parse time |
|---|---|--:|--:|--:|--:|--:|
| Two-stage gear reducer | gearbox.step | 27 | 67 | — | — | *(measure)* |
| Robotic welding cell (FANUC M-16iB) | 39 MB STEP | 142 | 356 | 13 | 3 | *(measure)* |
| Planetary gearbox | planetary.step | — | — | — | — | *(measure)* |

(The welding-cell and gear-reducer figures are the actual outputs documented in the
[case studies](CASE_STUDY_welding_cell.md).)

## What to record per assembly
When you benchmark on your own hardware, capture:
- **STEP size** (MB)
- **Unique parts / instances / subassemblies / depth** (from `generate_bom` + `assembly_stats`)
- **Analysis time** per command (BOM, assembly_tree, mechanism_detect, risk_score, review_summary)
- Whether SolidWorks COM was used or the STEP-geometry fallback

## Reproduce
```bash
bash examples/demo.sh          # end-to-end free-tier pass, prints a machine-readable summary
# time an individual command:
time python scripts/sw_understand.py --task examples/00_generate_bom.json --out /tmp/out.json
```
