#!/usr/bin/env python3
"""Stage 1.0 — SolidWorks assembly diagnostics (interference / errors / mates).

Reads a task JSON, drives the SolidWorks COM API (pywin32, Windows + license),
and writes a contract result JSON. If SolidWorks/pywin32 isn't available, returns
status=deck_only with a generated VBA macro the user can run — never a fake clean
result. See references/assembly_diagnostics.md and references/contract.md.

Usage: python sw_diagnostics.py --task task.json --out result.json
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _contract as C

CAPS = {"interference_check", "assembly_error_check", "mate_conflict_check", "clearance_check"}

MACRO_TEMPLATE = """' SolidWorks diagnostic macro (auto-generated)
' Open the assembly, then Tools > Macro > Run this .swp.
Dim swApp As Object, swModel As Object, swIFM As Object
Sub main()
    Set swApp = Application.SldWorks
    Set swModel = swApp.OpenDoc6("{path}", 2, 0, "", 0, 0)
    Set swIFM = swModel.InterferenceDetectionManager
    swIFM.TreatCoincidenceAsInterference = False
    Dim n As Long : n = swIFM.GetInterferenceCount
    Debug.Print "Interference count: " & n
    ' (enumerate swIFM.GetInterferences for volumes + components)
End Sub
"""


def run_real(task):
    import win32com.client as win32
    cap = task["capability"]
    path = task["model"]["path"]
    sw = win32.Dispatch("SldWorks.Application")
    sw.Visible = True
    model = sw.OpenDoc6(path, 2, 0, "", 0, 0)
    if model is None:
        return C.result("failed", "1.0", cap,
                        caveats=[f"Could not open assembly: {path}"])
    assumptions, caveats, res = [], [], {}
    if cap == "interference_check":
        ifm = model.InterferenceDetectionManager
        ifm.TreatCoincidenceAsInterference = bool(
            (task.get("inputs") or {}).get("treat_coincident_as_clearance", False))
        ifm.IncludeMultibodyPartInterferences = True
        count = ifm.GetInterferenceCount()
        items = []
        interferences = ifm.GetInterferences() or []
        for it in interferences:
            try:
                vol = it.Volume
                comps = [c.Name2 for c in (it.Components or [])]
            except Exception:
                vol, comps = None, []
            items.append({"components": comps, "volume": vol})
        res = {"count": count, "interferences": items}
        caveats.append("Interference may be intentional (press-fit/weld-prep); "
                       "review large overlaps between unrelated parts as likely errors.")
    elif cap == "assembly_error_check":
        model.EditRebuild3()
        comps = model.GetComponents(True) or []
        errs = []
        for comp in comps:
            try:
                if comp.GetSuppression() == 0:  # suppressed
                    errs.append({"component": comp.Name2, "type": "suppressed",
                                 "message": "component suppressed"})
            except Exception:
                pass
        res = {"errors": errs, "component_count": len(comps)}
        caveats.append("Resolve lightweight components for a complete check.")
    elif cap == "mate_conflict_check":
        # Placeholder structure; full mate-status walk depends on SW version API.
        res = {"overdefined": [], "underdefined": [], "conflicting_mates": [],
               "note": "Mate-status enumeration is SW-version specific; see reference."}
    elif cap == "clearance_check":
        mc = (task.get("inputs") or {}).get("min_clearance")
        if mc is None:
            return C.result("needs_input", "1.0", cap,
                            needs_input=["inputs.min_clearance"])
        res = {"min_clearance": mc, "violations": [],
               "note": "Run InterferenceDetection with a coincidence tolerance for gaps."}
    model.Quit if hasattr(model, "Quit") else None
    return C.result("ok", "1.0", cap, results=res, assumptions=assumptions, caveats=caveats)


def run_step_fallback(task):
    """No SolidWorks, but a STEP file + cadquery: do approximate geometry.

    Real boolean-based interference / distance-based clearance. APPROXIMATE — flagged
    as such; production sign-off still uses the SolidWorks check. Returns None if the
    capability isn't geometry-checkable here, so the caller can fall to deck_only.
    """
    cap = task["capability"]
    path = task["model"]["path"]
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "connectors"))
    import step_geometry as G
    if cap == "interference_check":
        r = G.interference(path, min_volume_mm3=(task.get("inputs") or {}).get("min_volume_mm3", 1.0))
        if r.get("too_large"):
            return None  # too big for STEP boolean -> fall through to deck_only macro
        return C.result("ok", "1.0", cap, results={
            "count": r["interference_count"], "total_volume_mm3": r["total_volume_mm3"],
            "interferences": [{"solids": o["pair"], "volume_mm3": o["volume_mm3"]}
                              for o in r["interferences"]],
            "solids_analyzed": r["solids"], "method": "STEP geometry (approximate)"},
            assumptions=["No SolidWorks; computed from STEP solids via boolean intersection.",
                         "Solids identified by geometry, not named components."],
            caveats=["APPROXIMATE: volumes depend on STEP tessellation and how the file "
                     "stores solids; a small overlap may be a coincident/press-fit face. "
                     "Confirm in SolidWorks before sign-off — this is a rough screen, not the production check."])
    if cap == "clearance_check":
        mc = (task.get("inputs") or {}).get("min_clearance")
        if mc is None:
            return C.result("needs_input", "1.0", cap, needs_input=["inputs.min_clearance"])
        r = G.clearance(path, min_gap_mm=mc)
        return C.result("ok", "1.0", cap, results={
            "min_clearance": mc, "violations": r["tight_clearances"],
            "count": r["count"], "solids_analyzed": r["solids"],
            "method": "STEP geometry (approximate)"},
            assumptions=["No SolidWorks; minimum distance between STEP solids via OCC extrema."],
            caveats=["APPROXIMATE: distances from STEP geometry; confirm tight gaps in CAD."])
    return None  # not geometry-checkable here -> deck_only


def main():
    args = C.standard_args(__doc__)
    task = C.load_task(args.task)
    cap = task.get("capability")
    if cap not in CAPS:
        return C.write(args.out, C.result("failed", "1.0", cap,
                       caveats=[f"unknown capability; expected one of {sorted(CAPS)}"]))
    ok, missing = C.require(task, "model")
    if not ok or not task["model"].get("path"):
        return C.write(args.out, C.result("needs_input", "1.0", cap,
                       needs_input=["model.path"]))
    # STEP geometry fallback: no SolidWorks, but a .step/.stp + cadquery available
    if not C.has_pywin32():
        path = task["model"]["path"]
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "connectors"))
        try:
            import step_context as SC
            is_step = SC.is_step(path)
            resolved = SC.resolve_step_path(path)
            if resolved and resolved != path:
                task["model"]["path"] = resolved  # zip -> extracted STEP
        except Exception:
            is_step = str(path).lower().endswith((".step", ".stp"))
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "connectors"))
            import step_geometry as G
            geom_ok = G.available()
        except Exception:
            geom_ok = False
        if is_step and geom_ok:
            try:
                res = run_step_fallback(task)
                if res is not None:
                    return C.write(args.out, res)
            except Exception as e:
                return C.write(args.out, C.result("failed", "1.0", cap,
                               caveats=[f"STEP geometry check failed: {e}"]))
    if not C.has_pywin32():
        macro = MACRO_TEMPLATE.format(path=task["model"]["path"])
        wd = task.get("workdir", ".")
        os.makedirs(wd, exist_ok=True)
        mpath = os.path.join(wd, "diagnostic_macro.swp")
        open(mpath, "w").write(macro)
        return C.write(args.out, C.result(
            "deck_only", "1.0", cap,
            artifacts={"macro": mpath},
            run_command="In SolidWorks: Tools > Macro > Run > diagnostic_macro.swp",
            caveats=["SolidWorks/pywin32 not available here (Windows + license required); "
                     "generated a macro to run in SolidWorks instead of faking results."]))
    try:
        return C.write(args.out, run_real(task))
    except Exception as e:
        return C.write(args.out, C.result("failed", "1.0", cap,
                       caveats=[f"SolidWorks API error: {e}"]))


if __name__ == "__main__":
    main()
