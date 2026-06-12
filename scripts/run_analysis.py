#!/usr/bin/env python3
"""Stage 2.0 — analysis (Community Edition: free static + modal, gated rest).

Free tier (computed locally, real results):
  - static_strength : single load case, analytical beam/bar (no auto-faces, no contact)
  - modal           : first up to 3 natural frequencies (uniform-beam analytical)

Professional (delegated to mechanical_ai_core if installed, else enterprise_required):
  - multi-load / contact / nonlinear / auto load-face static, modal > 3 modes
  - thermal, cfd, fatigue, motion

Usage: --task task.json --out result.json
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _contract as C
import core_bridge as CB
import tier
import free_fea

CAPS = ["static_strength", "modal", "thermal", "fatigue", "cfd", "motion"]


def main():
    args = C.standard_args(__doc__)
    task = C.load_task(args.task)
    cap = task.get("capability")
    if cap not in CAPS:
        return C.write(args.out, C.result("failed", "2.0", cap,
                       caveats=[f"unknown capability; expected one of {CAPS}"]))
    ok, missing = C.require(task, "model", "units")
    if not ok:
        return C.write(args.out, C.result("needs_input", "2.0", cap, needs_input=missing))

    allowed, reason = tier.free_tier_check(cap, task)
    if not allowed:
        # over the free line (or pro-only) -> try core, else enterprise_required
        core = CB.get_core()
        if core is None:
            return C.write(args.out, CB.enterprise_required(C, "2.0", cap,
                           extra_caveats=[f"Free tier limit: {reason}."]))
        return C.write(args.out, CB.delegate(C, task, "2.0", cap, fn_name="run_analysis"))

    # FREE tier — compute locally
    inp = task.get("inputs", {}) or {}
    fn = free_fea.DISPATCH.get(cap)
    r = fn(inp)
    assumptions = [f"Units: {task['units']} (confirm consistency).",
                   "Free tier: analytical engineering formulas (single load case / first modes), "
                   "not full 3D FE — Professional does automatic FE on arbitrary geometry."]
    if r["status"] == "needs_input":
        return C.write(args.out, C.result("needs_input", "2.0", cap,
                       needs_input=r.get("needs", []), caveats=[r.get("note", "")]))
    if r["status"] != "ok":
        return C.write(args.out, C.result("failed", "2.0", cap, caveats=[r.get("note", "analysis failed")]))
    caveats = ["Analytical result for an idealized case; confirm geometry matches the assumption.",
               r["results"].get("note", "")]
    return C.write(args.out, C.result("ok", "2.0", cap, results=r["results"],
                   assumptions=assumptions, caveats=[c for c in caveats if c]))


if __name__ == "__main__":
    main()
