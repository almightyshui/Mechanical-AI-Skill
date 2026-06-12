#!/usr/bin/env python3
"""Stage 3.0 — optimization / lightweighting (Community Edition stub).

The optimization engine (region identification, topology/parametric proposal,
CAD write-back, and the re-validation loop) is Professional Edition. This Community
command validates the task and delegates to the closed-source core if installed;
otherwise returns `enterprise_required`.

Capabilities: topology_optimize, parametric_lightweight.
Usage: --task task.json --out result.json
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _contract as C
import core_bridge as CB

CAPS = ["topology_optimize", "parametric_lightweight"]


def main():
    args = C.standard_args(__doc__)
    task = C.load_task(args.task)
    cap = task.get("capability")
    if cap not in CAPS:
        return C.write(args.out, C.result("failed", "3.0", cap,
                       caveats=[f"unknown capability; expected one of {CAPS}"]))
    ok, missing = C.require(task, "model", "units")
    if not ok:
        return C.write(args.out, C.result("needs_input", "3.0", cap, needs_input=missing))
    return C.write(args.out, CB.delegate(C, task, "3.0", cap, fn_name="optimize"))


if __name__ == "__main__":
    main()
