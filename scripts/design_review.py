#!/usr/bin/env python3
"""Design review / risk score / procurement (Community Edition).

Free: risk_score (simple weighted roll-up of free-tier signals).
Professional: design_review (agent), procurement_list, advanced risk scoring.

Usage: --task task.json --out result.json
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _contract as C
import core_bridge as CB
import tier
import free_fea

CAPS = {"design_review", "risk_score", "procurement_list"}


def main():
    args = C.standard_args(__doc__)
    task = C.load_task(args.task)
    cap = task.get("capability")
    if cap not in CAPS:
        return C.write(args.out, C.result("failed", "review", cap,
                       caveats=[f"unknown capability; expected one of {sorted(CAPS)}"]))

    allowed, reason = tier.free_tier_check(cap, task)
    if not allowed:
        core = CB.get_core()
        if core is None:
            return C.write(args.out, CB.enterprise_required(C, "review", cap,
                           extra_caveats=[f"Free tier limit: {reason}."]))
        return C.write(args.out, CB.delegate(C, task, "review", cap, fn_name=cap))

    # FREE simple risk score
    r = free_fea.risk_score(task.get("inputs", {}) or {})
    if r["status"] == "needs_input":
        return C.write(args.out, C.result("needs_input", "review", cap,
                       needs_input=r.get("needs", []), caveats=[r.get("note", "")]))
    return C.write(args.out, C.result("ok", "review", cap, results=r["results"],
                   caveats=["Simple risk score from free-tier checks; advanced scoring "
                            "(criticality weighting, code compliance, full physics) is Professional."]))


if __name__ == "__main__":
    main()
