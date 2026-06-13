"""Shared helpers for the contract-based command entry points (Community Edition).

Every command reads a task JSON and writes a result JSON in the shape defined in
references/contract.md. Result is `ok` only when explicitly built that way, so the
"never fake a result" rule is structural. Community Edition adds one extra status:
`enterprise_required` — returned when a capability needs the closed-source core.
"""
import json, sys, os


def normalize_task(task):
    """Forgive the common shapes agents write instead of the canonical schema.

    Agents repeatedly produce near-misses: `task_type` instead of `capability`,
    `input_file`/`file`/`path` at the top level instead of `model.path`, the
    path under `model.file`, etc. Rather than fail/needs_input and make the agent
    retry, we map these onto the canonical form. The canonical schema still works
    unchanged; this only fills gaps.
    """
    if not isinstance(task, dict):
        return task
    # capability aliases
    if not task.get("capability"):
        for k in ("task_type", "command", "operation", "cap"):
            if task.get(k):
                task["capability"] = task[k]
                break
    # model.path aliases
    model = task.get("model")
    if not isinstance(model, dict):
        model = {}
    if not model.get("path"):
        for k in ("input_file", "file", "path", "model_path", "step", "assembly_path"):
            v = task.get(k) or (model.get(k) if isinstance(model, dict) else None)
            if v:
                model["path"] = v
                break
    if model:
        task["model"] = model
    # detail alias at root -> inputs.detail handled by callers; leave as-is
    return task


def load_task(path):
    # Explicit UTF-8: task files routinely carry CJK paths/names, and the
    # platform default (GBK on Windows) raises UnicodeDecodeError on them.
    with open(path, encoding="utf-8") as f:
        return normalize_task(json.load(f))


def _headline(status, capability, results, needs_input, artifacts, upgrade):
    """One unambiguous line so an agent can't misread the outcome.

    The recurring failure mode: an agent sees `deck_only` or a summarized `ok`
    and reports the command as "failed" or "not supported", then invents a
    result. The headline states plainly what happened and what (if anything) the
    user must do — no interpretation required.
    """
    if status == "ok":
        bits = []
        for k in ("node_count", "edge_count", "part_count", "count",
                  "component_count", "subassembly_count", "unique_parts",
                  "total_instances"):
            if isinstance(results, dict) and k in results:
                bits.append(f"{results[k]} {k.replace('_', ' ')}")
        detail = ("; ".join(bits)) if bits else "completed"
        gt = results.get("graph_type") if isinstance(results, dict) else None
        if gt == "hierarchy_fallback":
            detail += " (hierarchy/belongs-to, not geometric contact)"
        return f"[SUCCESS] {capability}: {detail}. This is a real Community result."
    if status == "deck_only":
        return (f"[PARTIAL] {capability}: no geometry engine (SolidWorks/cadquery) on this "
                f"machine, so a runnable macro was generated instead. This is a graceful "
                f"degradation, NOT a failure and NOT a missing feature — the capability "
                f"exists and works where a geometry engine is present.")
    if status == "needs_input":
        miss = ", ".join(needs_input or []) or "additional data"
        return (f"[NEEDS INPUT] {capability}: provide {miss}. The command ran correctly; it "
                f"just needs this input. Not a failure.")
    if status == "enterprise_required":
        feat = (upgrade or {}).get("feature", capability)
        return (f"[NOT IN COMMUNITY] {feat}: this is a Professional/Enterprise capability. "
                f"Community correctly declined rather than fabricating an answer.")
    if status == "failed":
        return f"[FAILED] {capability}: the command could not run. See caveats for why."
    return f"{capability}: {status}"


def result(status, stage, capability, results=None, assumptions=None,
           caveats=None, needs_input=None, artifacts=None, run_command=None,
           upgrade=None):
    r = {
        "status": status,   # ok | needs_input | deck_only | failed | enterprise_required
        "headline": _headline(status, capability, results or {}, needs_input,
                              artifacts or {}, upgrade),
        "tier": "community",
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
