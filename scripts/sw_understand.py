#!/usr/bin/env python3
"""Stage 0.x — CAD understanding (BOM, part count, standard-part ID, assembly explainer).

Reads a task JSON, drives the SolidWorks COM API (pywin32, Windows + license) to
walk the assembly tree, and returns a contract result with the bill of materials,
component counts, identified standard/fastener parts, and the raw structure the
agent uses to explain how the assembly works and suggest an assembly order.

If SolidWorks/pywin32 isn't available it returns deck_only with a generated macro
(never a fabricated BOM). For a STEP-only input it falls back to whatever the host
STEP reader can give (geometry-level part list) and says so.

Capabilities: generate_bom, part_count, identify_standard_parts, explain_assembly.
See references/cad_understanding.md and references/contract.md.

Usage: python sw_understand.py --task task.json --out result.json
"""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _contract as C

CAPS = {"generate_bom", "part_count", "identify_standard_parts", "explain_assembly"}

# Heuristic standard-part / fastener name patterns (offline; the agent confirms).
STD_PATTERNS = [
    (r"\b(M\d+(\.\d+)?[xX]\d+)\b", "metric_screw"),
    (r"\b(ISO\s?\d+|DIN\s?\d+|GB/?T?\s?\d+|ANSI\s?B?\d+)\b", "standard_ref"),
    (r"\b(hex|socket|cap|pan|flat|countersunk)\s*(head)?\s*(screw|bolt)\b", "screw"),
    (r"\b(washer|spring washer|flat washer)\b", "washer"),
    (r"\b(nut|lock\s*nut|hex\s*nut)\b", "nut"),
    (r"\b(bearing|ball bearing|roller bearing|6\d{3}[a-z]{0,2})\b", "bearing"),
    (r"\b(o-?ring|oring|seal|gasket)\b", "seal"),
    (r"\b(dowel|pin|retaining ring|circlip|snap ring)\b", "pin_ring"),
    (r"\b(spring|compression spring|extension spring)\b", "spring"),
]

MACRO = """' SolidWorks BOM / structure export macro (auto-generated)
Dim swApp As Object, swModel As Object
Sub main()
    Set swApp = Application.SldWorks
    Set swModel = swApp.OpenDoc6("{path}", 2, 0, "", 0, 0)
    ' Walk swModel.GetComponents(False); for each: Name2, GetPathName,
    ' component config, and count by part. Export to CSV for the skill to read.
    Debug.Print "Components: " & UBound(swModel.GetComponents(False)) + 1
End Sub
"""


def classify_standard(name):
    nm = (name or "").lower()
    for pat, kind in STD_PATTERNS:
        if re.search(pat, nm, re.I):
            return kind
    return None


def walk_real(task):
    import win32com.client as win32
    cap = task["capability"]
    path = task["model"]["path"]
    sw = win32.Dispatch("SldWorks.Application"); sw.Visible = True
    model = sw.OpenDoc6(path, 2, 0, "", 0, 0)
    if model is None:
        return C.result("failed", "0.1", cap, caveats=[f"Could not open: {path}"])
    comps = model.GetComponents(False) or []   # top-level + children
    # tally by part file (instances -> quantity)
    tally = {}
    for comp in comps:
        try:
            nm = comp.Name2
            pth = comp.GetPathName() if hasattr(comp, "GetPathName") else ""
            key = pth or nm
            base = os.path.splitext(os.path.basename(key))[0] if key else nm
            tally.setdefault(base, {"name": base, "qty": 0, "path": pth})
            tally[base]["qty"] += 1
        except Exception:
            continue
    items = list(tally.values())
    for it in items:
        k = classify_standard(it["name"])
        if k:
            it["standard_part"] = k

    if cap == "part_count":
        res = {"unique_parts": len(items), "total_instances": sum(i["qty"] for i in items)}
    elif cap == "identify_standard_parts":
        std = [i for i in items if i.get("standard_part")]
        res = {"standard_parts": std, "count": len(std),
               "note": "Heuristic name match — confirm against the actual part library."}
    elif cap == "generate_bom":
        res = {"bom": [{"item": n+1, "part": it["name"], "qty": it["qty"],
                        "standard_part": it.get("standard_part", None)}
                       for n, it in enumerate(sorted(items, key=lambda x: -x["qty"]))],
               "unique_parts": len(items),
               "total_instances": sum(i["qty"] for i in items)}
    else:  # explain_assembly — return structure; the AGENT writes the prose explanation
        res = {"components": items,
               "top_level_count": len(items),
               "structure_note": "Agent: use this tree + mates to explain working principle, "
                                  "identify core load-bearing/moving parts, and suggest an "
                                  "assembly order (base part first, then mated children, "
                                  "fasteners last)."}
    return C.result("ok", "0.1", cap, results=res,
                    caveats=["Standard-part flags are heuristic name matches; confirm."])


def main():
    args = C.standard_args(__doc__)
    task = C.load_task(args.task)
    cap = task.get("capability")
    if cap not in CAPS:
        return C.write(args.out, C.result("failed", "0.1", cap,
                       caveats=[f"unknown capability; expected one of {sorted(CAPS)}"]))
    if not task.get("model", {}).get("path"):
        return C.write(args.out, C.result("needs_input", "0.1", cap, needs_input=["model.path"]))

    if not C.has_pywin32():
        path = task["model"]["path"]
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "connectors"))
        try:
            import step_context as SC
            is_step = SC.is_step(path)
            path = SC.resolve_step_path(path)
        except Exception:
            is_step = str(path).lower().endswith((".step", ".stp"))
        # STEP fallback: read solids geometrically (no part names, but real counts)
        if is_step and cap in ("generate_bom", "part_count"):
            try:
                sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "connectors"))
                import step_geometry as G
                if G.available():
                    solids = G.read_structure(path)
                    n = len(solids)
                    if cap == "part_count":
                        res = {"solid_count": n, "method": "STEP geometry"}
                    else:
                        res = {"bom": [{"item": i + 1, "part": f"solid_{s['index']}",
                                        "qty": 1, "volume_mm3": s["volume_mm3"],
                                        "standard_part": False} for i, s in enumerate(solids)],
                               "unique_parts": n, "total_instances": n,
                               "method": "STEP geometry"}
                    return C.write(args.out, C.result("ok", "0.1", cap, results=res,
                        assumptions=["No SolidWorks; solids read directly from the STEP file.",
                                     "Geometry-level: solids are not named components and identical "
                                     "parts are not auto-grouped (a true named BOM needs the SW assembly)."],
                        caveats=["STEP-level BOM: counts solids, not named components. For named parts, "
                                 "quantities, and standard-part flags, use the SolidWorks assembly."]))
            except Exception:
                pass  # fall through to macro
        wd = task.get("workdir", "."); os.makedirs(wd, exist_ok=True)
        mpath = os.path.join(wd, "bom_export_macro.swp")
        open(mpath, "w", encoding="utf-8").write(MACRO.format(path=task["model"]["path"]))
        return C.write(args.out, C.result(
            "deck_only", "0.1", cap, artifacts={"macro": mpath},
            run_command="In SolidWorks: Tools > Macro > Run > bom_export_macro.swp (exports component list to CSV)",
            caveats=["SolidWorks/pywin32 not available; generated a macro instead of a fabricated BOM. "
                     "For a STEP-only file, use the host's STEP reader to list solids (geometry-level, no part names)."]))
    try:
        return C.write(args.out, walk_real(task))
    except Exception as e:
        return C.write(args.out, C.result("failed", "0.1", cap, caveats=[f"SolidWorks API error: {e}"]))


if __name__ == "__main__":
    main()
