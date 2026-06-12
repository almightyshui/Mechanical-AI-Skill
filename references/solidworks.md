# SolidWorks connector (open)

How the Community commands drive SolidWorks through its COM API (pywin32). This
covers only the **open** operations: opening a document, walking the assembly,
running interference detection, and exporting STEP. The Simulation/Motion automation
(and the auto load-face / mesh logic) is Professional.

SolidWorks is driven via COM — there's no text "deck". On Windows with a licensed
session and `pywin32`, the commands call the API directly; on other platforms they
generate a `.swp` macro for the user to run (status `deck_only`), never a fake result.

```python
import win32com.client as win32
sw = win32.Dispatch("SldWorks.Application"); sw.Visible = True
model = sw.OpenDoc6(path, 2, 0, "", 0, 0)   # 2 = assembly (1 = part)
```

Open operations used by the Community commands:
- **Walk components** → `model.GetComponents(False)` → BOM / counts (`bom.py`, `sw_understand.py`).
- **Interference detection** → `model.InterferenceDetectionManager` → `sw_diagnostics.py`.
- **Mate / rebuild status** → component suppression, dangling refs, over/under-defined mates.
- **Export STEP** → `model.SaveAs3("out.step", 0, 0)` → `sw_export.py`.

Pitfalls: confirm document units; resolve lightweight components before a full
interference check; never save/modify the model in a read-only diagnostic.

Extending this connector (more CAD systems, richer standard-part matching) is exactly
the kind of contribution the open edition welcomes — see `../connectors/`.
