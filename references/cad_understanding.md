# Stage 0.x — CAD understanding (BOM, counts, standard parts, explainer)

The lowest-friction entry point: read a SolidWorks assembly (or STEP) and *understand* it before any diagnostics or simulation. Driven by `scripts/sw_understand.py` via the SolidWorks COM API. No solver needed.

Capabilities: `generate_bom`, `part_count`, `identify_standard_parts`, `explain_assembly`.

## What each does
- **part_count** — unique parts and total instances.
- **generate_bom** — a bill of materials: item, part name, quantity, and a heuristic standard-part flag, sorted by quantity.
- **identify_standard_parts** — screws/bolts/nuts/washers/bearings/seals/pins/springs matched by name pattern (M6x20, ISO/DIN/GB refs, "hex bolt", "6204 bearing", etc.). Heuristic — the agent confirms against the real part library.
- **explain_assembly** — returns the component tree + mate structure so the **agent writes the prose**: how the assembly works, which parts are core (load-bearing/moving) vs. hardware, and a suggested assembly order.

## Assembly-order guidance (for explain_assembly)
The agent proposes an order from the structure: base/frame part first → parts mated to it → sub-assemblies → moving parts → fasteners last. Call out any part that must go in before another becomes inaccessible.

## STEP-only input
A STEP file has solids but no part names, mates, or quantities the way a SolidWorks assembly does. With STEP the skill can list/count solids via the host's STEP reader but can't produce a true named BOM or mate-based explanation — say so, and ask for the SolidWorks assembly if a real BOM is needed.

## Honesty
- Standard-part identification is a name-pattern heuristic; flag it as "confirm against your library."
- If SolidWorks/pywin32 isn't available, the command returns `deck_only` with a macro that exports the component list — it never fabricates a BOM.

## Hand-off
`explain_assembly` output feeds a natural-language explanation; `generate_bom` output can go straight into the PDF report (`scripts/report_pdf.py`) as a BOM table, or be combined with a diagnostics/DFM result in one report.
