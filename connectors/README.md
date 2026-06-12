# Connectors (open)

Thin, open adapters between the skill and the CAD/geometry world. No commercial
secrets here — these just read what the tools expose. The value-adding engines that
consume this data (DFM/DFA, FEA automation, optimization) are Professional.

- `solidworks.py` — open a SolidWorks document via the COM API (pywin32), walk the
  component tree, read mates, run Interference Detection, export STEP.
- `step_reader.py` — read a STEP file's solids/bounding box when SolidWorks isn't
  available (geometry-level only — no part names or mates).
- `bom.py` — turn a component walk into a bill of materials (item / part / qty) and
  flag standard parts by name pattern.

These are imported by the open commands (`sw_understand.py`, `sw_diagnostics.py`,
`sw_export.py`). They are intentionally simple and well-documented so the community
can extend them (new CAD systems, better standard-part matching, etc.).
