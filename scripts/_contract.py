"""Shared helpers for the contract-based command entry points (Community Edition).

Every command reads a task JSON and writes a result JSON in the shape defined in
references/contract.md. Result is `ok` only when explicitly built that way, so the
"never fake a result" rule is structural. Community Edition adds one extra status:
`enterprise_required` — returned when a capability needs the closed-source core.
"""
import json, sys, os


def load_task(path):
    # Explicit UTF-8: task files routinely carry CJK paths/names, and the
    # platform default (GBK on Windows) raises UnicodeDecodeError on them.
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def result(status, stage, capability, results=None, assumptions=None,
           caveats=None, needs_input=None, artifacts=None, run_command=None,
           upgrade=None):
    r = {
        "status": status,   # ok | needs_input | deck_only | failed | enterprise_required
        "stage": stage,
        "capability": capability,
        "results": results or {},
        "assumptions": assumptions or [],
        "caveats": caveats or [],
        "needs_input": needs_input or [],
        "artifacts": artifacts or {},
        "run_command": run_command,
    }
    if upgrade:
        r["upgrade"] = upgrade   # {edition, feature, info_url} when enterprise_required
    return r


def write(out_path, res):
    # ensure_ascii=False keeps CJK part names readable instead of \uXXXX;
    # explicit UTF-8 so the file is valid regardless of platform default.
    txt = json.dumps(res, indent=2, ensure_ascii=False)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(txt)
    print(txt)
    return res


def require(task, *keys):
    missing = [k for k in keys if not task.get(k)]
    return (len(missing) == 0, missing)


def require_inputs(task, *keys):
    inp = task.get("inputs", {}) or {}
    missing = [k for k in keys if inp.get(k) in (None, "", [])]
    return (len(missing) == 0, missing)


def has_pywin32():
    try:
        import importlib.util
        return importlib.util.find_spec("win32com") is not None
    except Exception:
        return False


def standard_args(description):
    import argparse
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--task", required=True, help="path to task JSON")
    ap.add_argument("--out", help="path to write result JSON")
    return ap.parse_args()
