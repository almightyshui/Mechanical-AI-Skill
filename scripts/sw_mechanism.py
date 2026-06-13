#!/usr/bin/env python3
"""Stage 0.x — Lightweight CAD-understanding helpers (Community).

Structure-and-rules commands that run anywhere (no commercial solver, no COM needed
when the caller supplies the component data):

  mechanism_detect  — identify the mechanism TYPE (Gear Train / Timing Belt Drive /
                      Chain Drive / Lead Screw System) + confidence + evidence parts.
                      Answers "what is it" — NOT purpose/power-flow/intent (Professional).

  assembly_tree     — render a lightweight text tree of the assembly structure
                      (parse confirmation + layout). Shows what's in the assembly,
                      not why it's arranged this way or how to assemble it (Professional).

Usage: python sw_mechanism.py --task task.json --out result.json
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _contract as C
import core_bridge as CB
import tier
import free_fea

CAPS = {"mechanism_detect", "assembly_tree", "vendor_summary",
        "assembly_stats", "exploded_view", "category_summary", "adjacency_graph"}


def main():
    args = C.standard_args(__doc__)
    task = C.load_task(args.task)
    cap = task.get("capability")
    if cap not in CAPS:
        return C.write(args.out, C.result("failed", "0.2", cap,
                       caveats=[f"this command handles {sorted(CAPS)}"]))

    allowed, reason = tier.free_tier_check(cap, task)
    if not allowed:
        core = CB.get_core()
        if core is None:
            return C.write(args.out, CB.enterprise_required(C, "0.2", cap,
                           extra_caveats=[f"Free tier limit: {reason}."]))
        return C.write(args.out, CB.delegate(C, task, "0.2", cap, fn_name=cap))

    # === STEP Auto Context ===
    # If the model is a STEP path and the capability's input is missing, extract it
    # automatically (components / nodes / subassemblies / edges) instead of asking
    # the caller. This is what makes "upload a STEP -> get a result" work.
    inputs = task.setdefault("inputs", {})
    path = (task.get("model") or {}).get("path", "")
    if str(path).lower().endswith((".step", ".stp")):
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "connectors"))
            import step_context as CTX

            if cap in ("mechanism_detect", "vendor_summary", "category_summary") and not inputs.get("components"):
                inputs["components"] = CTX.extract_components(path)
            elif cap in ("assembly_tree", "exploded_view") and not inputs.get("nodes") and not inputs.get("components"):
                inputs["nodes"] = CTX.extract_nodes(path)
            elif cap == "assembly_stats" and not inputs.get("subassemblies") and not inputs.get("nodes"):
                inputs["subassemblies"] = CTX.extract_subassemblies(path)
            elif cap == "adjacency_graph" and not inputs.get("edges"):
                edges, names = CTX.extract_edges(path)
                if edges:
                    inputs["edges"] = edges
                    if names and not inputs.get("names"):
                        inputs["names"] = names
        except Exception:
            pass  # fall through; engine will report needs_input if truly empty

    fn = free_fea.DISPATCH.get(cap)
    r = fn(task.get("inputs", {}) or {})
    if r["status"] == "needs_input":
        return C.write(args.out, C.result("needs_input", "0.2", cap,
                       needs_input=r.get("needs", []), caveats=[r.get("note", "")]))
    if cap == "mechanism_detect":
        caveat = "Mechanism TYPE identification (experimental); design-intent/purpose/power-flow is Professional."
    elif cap == "vendor_summary":
        caveat = "Brand detection from names; sourcing/pricing/alternates is Professional."
    elif cap == "assembly_stats":
        caveat = "Top-level instance statistics; assembly order/function is Professional."
    elif cap == "exploded_view":
        caveat = "Structure visualization (Mermaid); 3D exploded / assembly-sequence is Professional."
    elif cap == "category_summary":
        caveat = "Component counts by category; procurement (sourcing/cost/alternates) is Professional."
    else:
        caveat = "Assembly structure tree; assembly order/sequence/intent is Professional."
    return C.write(args.out, C.result("ok", "0.2", cap, results=r["results"], caveats=[caveat]))


if __name__ == "__main__":
    main()
