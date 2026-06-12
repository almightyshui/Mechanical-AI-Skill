#!/usr/bin/env python3
"""Stage 1.x — DFM / DFA (Community Edition: basic DFM free, advanced/DFA gated).

Free: dfm_check with the basic rule set (caller supplies measured features).
Professional: advanced DFM rule library, and all DFA, via mechanical_ai_core.

Usage: --task task.json --out result.json
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _contract as C
import core_bridge as CB
import tier
import free_fea

CAPS = {"dfm_check", "dfa_check"}


def main():
    args = C.standard_args(__doc__)
    task = C.load_task(args.task)
    cap = task.get("capability")
    if cap not in CAPS:
        return C.write(args.out, C.result("failed", "1.1", cap,
                       caveats=[f"unknown capability; expected one of {sorted(CAPS)}"]))
    if not task.get("model", {}).get("path"):
        return C.write(args.out, C.result("needs_input", "1.1", cap, needs_input=["model.path"]))

    allowed, reason = tier.free_tier_check(cap, task)
    if not allowed:
        core = CB.get_core()
        if core is None:
            return C.write(args.out, CB.enterprise_required(C, "1.1", cap,
                           extra_caveats=[f"Free tier limit: {reason}."]))
        return C.write(args.out, CB.delegate(C, task, "1.1", cap,
                       fn_name=cap))

    # FREE basic DFM / DFA — dispatch by capability
    fn = free_fea.DISPATCH.get(cap)
    r = fn(task.get("inputs", {}) or {})
    if r["status"] == "needs_input":
        return C.write(args.out, C.result("needs_input", "1.1", cap,
                       needs_input=r.get("needs", []), caveats=[r.get("note", "")]))
    caveat = ("Basic DFM rule set; the advanced rule library is Professional."
              if cap == "dfm_check" else
              "Basic DFA (complexity + tool clearance); sequence/path/time/automation are Professional.")
    return C.write(args.out, C.result("ok", "1.1", cap, results=r["results"], caveats=[caveat]))


if __name__ == "__main__":
    main()
