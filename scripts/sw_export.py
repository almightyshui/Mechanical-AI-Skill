#!/usr/bin/env python3
"""SolidWorks -> STEP export (geometry hand-off for downstream simulation).

Reads a task JSON, drives the SolidWorks COM API to export the part/assembly to
STEP, and returns a contract result with the STEP path + mass properties. Falls
back to a macro (deck_only) if SolidWorks/pywin32 isn't present.

Usage: python sw_export.py --task task.json --out result.json
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _contract as C

MACRO = """' SolidWorks STEP export macro (auto-generated)
Dim swApp As Object, swModel As Object
Sub main()
    Set swApp = Application.SldWorks
    Set swModel = swApp.OpenDoc6("{path}", {doctype}, 0, "", 0, 0)
    swModel.SaveAs3 "{step}", 0, 0
End Sub
"""


def main():
    args = C.standard_args(__doc__)
    task = C.load_task(args.task)
    cap = "export_step"
    if not task.get("model", {}).get("path"):
        return C.write(args.out, C.result("needs_input", "2.0", cap, needs_input=["model.path"]))
    src = task["model"]["path"]
    wd = task.get("workdir", ".")
    os.makedirs(wd, exist_ok=True)
    step = os.path.join(wd, os.path.splitext(os.path.basename(src))[0] + ".step")
    doctype = 2 if task["model"].get("type") == "assembly" else 1

    if not C.has_pywin32():
        mpath = os.path.join(wd, "export_step_macro.swp")
        open(mpath, "w", encoding="utf-8").write(MACRO.format(path=src, doctype=doctype, step=step))
        return C.write(args.out, C.result(
            "deck_only", "2.0", cap, artifacts={"macro": mpath, "step": step},
            run_command="In SolidWorks: Tools > Macro > Run > export_step_macro.swp",
            caveats=["SolidWorks/pywin32 not available; generated an export macro."]))
    try:
        import win32com.client as win32
        sw = win32.Dispatch("SldWorks.Application"); sw.Visible = True
        model = sw.OpenDoc6(src, doctype, 0, "", 0, 0)
        ok = model.SaveAs3(step, 0, 0)
        mp = None
        try:
            ext = model.Extension
            mprops = ext.GetMassProperties(1)  # [..., mass, ...] version-specific
            mp = list(mprops) if mprops else None
        except Exception:
            pass
        if not os.path.exists(step):
            return C.write(args.out, C.result("failed", "2.0", cap,
                           caveats=["STEP file was not produced."]))
        return C.write(args.out, C.result("ok", "2.0", cap,
                       results={"step_path": step, "mass_properties": mp},
                       artifacts={"step": step}))
    except Exception as e:
        return C.write(args.out, C.result("failed", "2.0", cap,
                       caveats=[f"SolidWorks API error: {e}"]))


if __name__ == "__main__":
    main()
