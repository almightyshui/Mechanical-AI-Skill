# Stage 1.0 — Assembly diagnostics (SolidWorks API)

"Analyze this assembly for interference / errors." No simulation — purely the SolidWorks COM API via pywin32 (Windows + a licensed SolidWorks session). Driven by `scripts/sw_diagnostics.py` with a task JSON (contract.md).

## API entry (pywin32 COM)
```python
import win32com.client as win32
sw = win32.Dispatch("SldWorks.Application")
sw.Visible = True
model = sw.OpenDoc6(path, 2, 0, "", 0, 0)   # 2 = assembly document
asm = model.Extension
```

## interference_check
SolidWorks exposes Interference Detection through the assembly API:
```python
ife = model.InterferenceDetectionManager
ife.TreatCoincidenceAsInterference = False      # press-fit faces touching: usually not an error
ife.IncludeMultibodyPartInterferences = True
count = ife.GetInterferenceCount()
results = ife.GetInterferences()                # each has volume + the two component bodies
```
For each interference report: the two components, the **overlap volume**, and a location. Return them in `results.interferences`.

Interpretation the agent should apply (state in caveats):
- A nonzero overlap is not always a bug — **press-fits, interference fits, and weld-prep** are intentional. Flag interferences but distinguish "likely intentional (small, between mating shaft/hole)" from "likely error (large, between unrelated parts)" when volume and component pairing suggest it. Don't assert intent the user didn't state — present, and let the agent/user judge.
- Coincident faces (zero-volume touching) are normal contact, not interference — controlled by `TreatCoincidenceAsInterference`.

## assembly_error_check
Walk the feature/component tree for rebuild and reference errors:
```python
# component suppression / rebuild state, dangling mates, missing files
for comp in model.GetComponents(True):
    state = comp.GetSuppression()      # detect suppressed / lightweight / out-of-date
    # check comp.IsRoot, comp referenced file exists, etc.
mgr = model.FeatureManager
# model.GetActiveConfiguration(), rebuild via model.EditRebuild3() and read errors
```
Report: rebuild errors, dangling/dependent references, missing component files, out-of-date components. Each as `{component, type, message}`.

## mate_conflict_check
Enumerate mates and their status:
```python
# iterate mate features; SolidWorks marks over-defined / conflicting mates
# model.GetMateEntityCount, mate.Status, etc.
```
Report `overdefined`, `underdefined`, and `conflicting_mates`. Over-defined mates are the usual cause of "the assembly won't move / won't rebuild"; under-defined components have unconstrained DOF (may be fine, may be an oversight).

## clearance_check
Like interference but for a minimum gap: report component pairs whose closest distance is below `inputs.min_clearance`. Useful for "is there at least 2 mm everywhere for the wiring."

## Result & handoff
`sw_diagnostics.py` returns the contract result JSON with `status: ok` and the findings, or `deck_only`/`failed` if SolidWorks/pywin32 isn't available (then it emits the macro the user can run instead — never a fake clean bill of health). The agent renders a report grouping findings by severity and, for interference, sorts by overlap volume.

## Pitfalls
- SolidWorks is Windows-only; on Linux this stage is macro-only (generate a `.swp`/VBA the user runs). `detect_solvers.sh` reports pywin32/SolidWorks availability.
- Large assemblies in lightweight/large-design-review mode may not expose full interference data — resolve components first.
- Always open read-only-ish (don't save) for a pure diagnostic; never modify the model in stage 1.0.
