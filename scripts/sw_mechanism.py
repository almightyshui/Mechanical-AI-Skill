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
import json
import _contract as C
import core_bridge as CB
import tier
import free_fea

CAPS = {"mechanism_detect", "assembly_tree", "vendor_summary",
        "assembly_stats", "exploded_view", "category_summary", "adjacency_graph",
        "review_summary"}

# Fields large enough to blow up an agent's context on a big assembly. We keep a
# short preview inline and write the full value to a sidecar file. Counts/notes
# always stay inline so the agent still gets the real answer.
_BIG_FIELDS = ("tree_text", "mermaid", "neighbours", "most_connected")
_PREVIEW_LINES = 12   # for newline-delimited text (tree_text / mermaid)
_PREVIEW_ITEMS = 8    # for dict/list fields (neighbours / most_connected)


def _sidecar_path(out_path, cap):
    base = out_path or f"{cap}_result.json"
    root = base[:-5] if base.endswith(".json") else base
    return f"{root}.full.json"


def _slim_results(results, cap, out_path, detail):
    """Return (inline_results, wrote_path_or_None).

    detail == 'full'  -> return everything as-is (no sidecar).
    detail == 'summary' (default) -> truncate big fields, dump full to sidecar.
    """
    if detail == "full":
        return results, None
    has_big = any(k in results for k in _BIG_FIELDS)
    if not has_big:
        return results, None   # small command — nothing to slim

    full_path = _sidecar_path(out_path, cap)
    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(results, indent=2, ensure_ascii=False))
        wrote = full_path
    except Exception:
        wrote = None

    slim = {}
    for k, v in results.items():
        if k == "tree_text" and isinstance(v, str):
            lines = v.split("\n")
            slim["tree_preview"] = "\n".join(lines[:_PREVIEW_LINES])
            if len(lines) > _PREVIEW_LINES:
                slim["tree_preview"] += f"\n... ({len(lines)} lines total)"
        elif k == "mermaid" and isinstance(v, str):
            lines = v.split("\n")
            slim["mermaid_preview"] = "\n".join(lines[:_PREVIEW_LINES])
            if len(lines) > _PREVIEW_LINES:
                slim["mermaid_preview"] += f"\n... ({len(lines)} lines total)"
        elif k == "neighbours" and isinstance(v, dict):
            items = list(v.items())[:_PREVIEW_ITEMS]
            preview = {}
            for a, b in items:
                if isinstance(b, list) and len(b) > _PREVIEW_ITEMS:
                    preview[a] = b[:_PREVIEW_ITEMS] + [f"...(+{len(b) - _PREVIEW_ITEMS} more)"]
                else:
                    preview[a] = b
            slim["neighbours_preview"] = preview
            if len(v) > _PREVIEW_ITEMS:
                slim["neighbours_truncated"] = f"{len(v)} nodes total"
        elif k == "most_connected" and isinstance(v, list):
            slim["most_connected"] = v[:_PREVIEW_ITEMS]
        else:
            slim[k] = v   # counts, notes, graph_type — keep inline
    return slim, wrote


def _render_review_md(step_name, summary, bom_items, caveats):
    """Human-readable Executive Review (Markdown). Plain prose + small tables;
    every number comes straight from the computed summary — nothing added."""
    a = summary.get("assembly", {})
    L = []
    L.append(f"# Mechanical Review — {step_name}")
    L.append("")
    L.append("## Executive Summary")
    L.append("")
    L.append(f"- Unique parts: {a.get('unique_parts', '?')}")
    L.append(f"- Total instances: {a.get('total_instances', '?')}")
    L.append(f"- Top-level subassemblies: {a.get('top_level_subassemblies', '?')}")
    L.append(f"- Assembly depth: {a.get('assembly_depth', '?')}")
    L.append("")

    comp = summary.get("complexity")
    if comp:
        L.append("## Complexity")
        L.append("")
        L.append(f"- Level: **{comp.get('level', '?')}**")
        if comp.get("reasons"):
            L.append(f"- Drivers: {', '.join(comp['reasons'])}")
        L.append("")

    mix = summary.get("manufacturing_mix")
    if mix:
        L.append("## Manufacturing mix")
        L.append("")
        L.append(f"- Custom (in-house): {mix['custom_instances']} instances ({mix['custom_pct']}%)")
        L.append(f"- Commercial / classified: {mix['commercial_instances']} instances ({mix['commercial_pct']}%)")
        L.append("")

    vc = summary.get("vendor_concentration")
    if vc and vc.get("identified_vendors"):
        L.append("## Vendor concentration")
        L.append("")
        L.append(f"- Identified vendors: {vc['identified_vendors']} "
                 f"({vc['vendor_matched_parts']} parts matched)")
        if vc.get("top_vendors"):
            L.append(f"- Top: {', '.join(vc['top_vendors'])}")
        L.append("")

    mech = summary.get("mechanisms")
    if mech:
        L.append("## Detected mechanisms")
        L.append("")
        prim = mech.get("primary")
        if prim:
            L.append(f"- Primary: {prim}")
        for m in (mech.get("detected") or mech.get("mechanisms") or []):
            if isinstance(m, dict):
                name = m.get("mechanism") or m.get("type") or m.get("name") or "?"
                conf = m.get("confidence")
                L.append(f"- {name}" + (f" (confidence {conf}%)" if conf is not None else ""))
            else:
                L.append(f"- {m}")
        L.append("")

    ven = summary.get("vendors")
    if ven:
        rows = (ven.get("vendors") if isinstance(ven, dict) else ven) or []
        L.append("## Vendors")
        L.append("")
        if rows:
            for r in rows:
                if isinstance(r, dict):
                    name = r.get("vendor") or r.get("name") or "?"
                    cnt = r.get("count")
                    L.append(f"- {name}" + (f" ({cnt} parts)" if cnt is not None else ""))
                else:
                    L.append(f"- {r}")
        else:
            L.append("- None detected from part names")
        L.append("")

    cat = summary.get("categories")
    if cat:
        rows = (cat.get("categories") if isinstance(cat, dict) else cat) or []
        L.append("## Categories")
        L.append("")
        if rows:
            for r in rows:
                if isinstance(r, dict):
                    L.append(f"- {r.get('category', r.get('name', '?'))}: {r.get('count', '?')}")
                else:
                    L.append(f"- {r}")
        else:
            L.append("- No categories classified")
        L.append("")

    risk = summary.get("risk")
    if risk:
        L.append("## Risk")
        L.append("")
        if isinstance(risk, dict):
            score = risk.get("overall_score", risk.get("score"))
        else:
            score = risk
        L.append(f"- Risk score: {score} / 100 (higher = lower risk; 100 = no flags raised)")
        contribs = (risk.get("contributors") or []) if isinstance(risk, dict) else []
        if contribs:
            L.append("- Points deducted for:")
            for c in contribs:
                if isinstance(c, dict):
                    L.append(f"  - {c.get('factor', '?')}: −{c.get('points', '?')}")
        L.append("")

    fnd = summary.get("findings")
    if fnd and fnd.get("findings"):
        L.append("## Findings")
        L.append("")
        for i, f in enumerate(fnd["findings"], 1):
            sev = (f.get("severity") or "").capitalize()
            L.append(f"### {i}. {f.get('finding', '?')} ({sev})")
            L.append("")
            if f.get("evidence"):
                L.append(f"- Evidence: {f['evidence']}")
            if f.get("impact"):
                L.append(f"- Impact: {f['impact']}")
            L.append(f"- Recommendation: *(Professional)*")
            L.append("")
        L.append("*Findings state fact, evidence, and impact. Specific recommendations — "
                 "what to change — are a Professional capability.*")
        L.append("")

    if bom_items:
        L.append("## BOM (name-level)")
        L.append("")
        L.append("| # | Part | Qty |")
        L.append("|---|------|-----|")
        for it in bom_items:
            L.append(f"| {it['item']} | {it['part']} | {it['qty']} |")
        L.append("")

    if caveats:
        L.append("## Notes & limits")
        L.append("")
        for c in caveats:
            L.append(f"- {c}")
        L.append("")
    L.append("*Generated by Mechanical AI Skill (Community). Name-level / STEP-text; "
             "geometry-level data and engineering reasoning are Professional.*")
    return "\n".join(L)


def _executive_review(task, args):
    """Executive Review — one command, one engineering verdict.

    Unlike the old aggregate-what-you're-given review, this orchestrates the
    free checks itself: it reads the STEP/zip/folder once, derives components /
    nodes / subassemblies, runs mechanism / vendor / category / BOM / risk, and
    returns an engineer-facing summary plus pointers to the per-analysis
    artifacts. Honest throughout: every figure is computed, nothing invented; if
    a sub-check can't run it's omitted, not faked.
    """
    path = (task.get("model") or {}).get("path", "")
    if not path:
        return C.write(args.out, C.result("needs_input", "0.2", "review_summary",
            needs_input=["model.path"],
            caveats=['Point the task at the assembly, e.g. '
                     '{"capability":"review_summary","model":{"path":"C:/path/to/assembly_or_folder"}}']))
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "connectors"))
    try:
        import step_context as CTX
    except Exception:
        CTX = None
    if CTX is None or not CTX.is_step(path):
        # Format Intelligence: tell the user what the file IS and what to do,
        # instead of a generic failure.
        fmt = None
        try:
            fmt = CTX.detect_format(path) if CTX else None
        except Exception:
            fmt = None
        if fmt and not fmt.get("supported"):
            cav = [f"Input format: {fmt['format']} — not directly analyzable. "
                   f"{fmt.get('action', 'Export STEP and try again.')}"]
            if fmt.get("referenced_parts"):
                cav.append(f"The assembly references {fmt['referenced_parts']} parts; "
                           f"once exported to STEP they can be analyzed.")
            return C.write(args.out, C.result("needs_input", "0.2", "review_summary",
                needs_input=[f"a STEP export of this {fmt['format']} file"],
                results={"input_format": fmt["format"], "supported": False,
                         "suggested_action": fmt.get("action")},
                caveats=cav))
        return C.write(args.out, C.result("needs_input", "0.2", "review_summary",
            needs_input=["a readable STEP/zip/folder at model.path"],
            caveats=["Could not resolve a STEP source from the given path."]))

    components = CTX.extract_components(path)
    nodes = CTX.extract_nodes(path)
    subs = CTX.extract_subassemblies(path)
    bom = CTX.extract_bom(path)

    def _depth(ns):
        return 1 + max((_depth(n.get("children", [])) for n in ns), default=0) if ns else 0

    summary = {
        "assembly": {
            "unique_parts": bom["unique_parts"],
            "total_instances": bom["total_instances"],
            "top_level_subassemblies": len(subs),
            "assembly_depth": _depth(nodes),
        },
        "source": "STEP-text",
        "geometry": False,
    }

    # mechanism / vendor / category — reuse the free engines on extracted components
    mech = free_fea.DISPATCH["mechanism_detect"]({"components": components})
    if mech.get("status") == "ok":
        summary["mechanisms"] = mech["results"]
    ven = free_fea.DISPATCH["vendor_summary"]({"components": components})
    if ven.get("status") == "ok":
        summary["vendors"] = ven["results"]
    cat = free_fea.DISPATCH["category_summary"]({"components": components})
    if cat.get("status") == "ok":
        summary["categories"] = cat["results"]

    # risk — feed the signals we actually have (transparent, partial is fine)
    signals = {"parts": bom["unique_parts"], "assembly_depth": summary["assembly"]["assembly_depth"]}
    risk = free_fea.DISPATCH["risk_score"]({"signals": signals})
    if risk.get("status") == "ok":
        summary["risk"] = risk["results"]

    # --- Review Summary V2: derive engineer-facing intelligence from the
    # already-computed figures. Pure aggregation — no new data, nothing invented. ---
    a = summary["assembly"]
    inst = a.get("total_instances", 0)
    uniq = a.get("unique_parts", 0)
    depth = a.get("assembly_depth", 0)

    # Manufacturing mix: custom (drawing-series clusters) vs commercial (the rest).
    custom_inst = 0
    commercial_inst = 0
    for r in (cat.get("results", {}).get("categories", []) if cat.get("status") == "ok" else []):
        if r.get("custom"):
            custom_inst += r.get("count", 0)
        else:
            commercial_inst += r.get("count", 0)
    classified = custom_inst + commercial_inst
    if classified:
        summary["manufacturing_mix"] = {
            "custom_instances": custom_inst,
            "commercial_instances": commercial_inst,
            "custom_pct": round(100 * custom_inst / classified),
            "commercial_pct": round(100 * commercial_inst / classified),
            "basis": "classified instances; custom = in-house drawing-number series, "
                     "commercial = matched a known category/vendor",
        }

    # Subsystems present (from detected mechanisms) — drives the complexity read.
    subsystems = []
    if mech.get("status") == "ok":
        subsystems = [d.get("mechanism") for d in mech["results"].get("detected", []) if d.get("mechanism")]

    # Complexity level: transparent thresholds on instance count, part variety,
    # depth, and subsystem count. Reasons are listed so it's not a black box.
    reasons = []
    score = 0
    if inst >= 300: score += 2; reasons.append(f"{inst} instances")
    elif inst >= 100: score += 1; reasons.append(f"{inst} instances")
    if uniq >= 100: score += 2; reasons.append(f"{uniq} unique parts")
    elif uniq >= 40: score += 1; reasons.append(f"{uniq} unique parts")
    if depth >= 4: score += 1; reasons.append(f"assembly depth {depth}")
    if len(subsystems) >= 2: score += 1; reasons.append(f"{len(subsystems)} mechanism subsystems")
    level = "High" if score >= 4 else ("Medium" if score >= 2 else "Low")
    summary["complexity"] = {"level": level, "reasons": reasons,
                             "basis": "transparent thresholds on instances, part variety, depth, subsystems"}

    # Vendor concentration: how much of the assembly is identifiable commercial brands.
    if ven.get("status") == "ok":
        vrows = ven["results"].get("vendors", [])
        vendor_parts = sum(v.get("count", 0) for v in vrows)
        summary["vendor_concentration"] = {
            "identified_vendors": len(vrows),
            "vendor_matched_parts": vendor_parts,
            "top_vendors": [v.get("vendor") for v in vrows[:5]],
        }

    # --- Findings Engine: rule-driven facts (Community). Recommendations are Pro. ---
    mix = summary.get("manufacturing_mix") or {}
    vc = summary.get("vendor_concentration") or {}
    vrows2 = ven["results"].get("vendors", []) if ven.get("status") == "ok" else []
    top_vendor = vrows2[0].get("vendor") if vrows2 else None
    vendor_parts2 = sum(v.get("count", 0) for v in vrows2)
    max_share = round(100 * vrows2[0].get("count", 0) / vendor_parts2) if vendor_parts2 else 0
    fsignals = {
        "unique_parts": uniq,
        "instances": inst,
        "assembly_depth": depth,
        "custom_pct": mix.get("custom_pct", 0),
        "max_vendor_share": max_share,
        "top_vendor": top_vendor,
    }
    fres = free_fea.DISPATCH["findings"]({"signals": fsignals})
    if fres.get("status") == "ok":
        summary["findings"] = fres["results"]

    # Output goes next to the STEP, in a predictable folder, so the user (and the
    # agent) can always find it — instead of a temp dir the agent picks and then
    # misreports. Falls back to workdir / cwd if the STEP dir isn't writable.
    out_dir = None
    try:
        resolved = CTX.resolve_step_path(path)
        base = os.path.dirname(os.path.abspath(resolved))
        cand = os.path.join(base, "mech_review")
        os.makedirs(cand, exist_ok=True)
        out_dir = cand
    except Exception:
        out_dir = None
    if not out_dir:
        out_dir = task.get("workdir", ".")
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception:
            out_dir = "."

    artifacts = {}
    full_items = [{"item": i + 1, "part": it["name"], "qty": it["qty"]}
                  for i, it in enumerate(bom["items"])]
    if len(full_items) > 15:
        summary["top_parts"] = full_items[:15]
        summary["top_parts_note"] = f"top 15 of {len(full_items)} parts; full BOM in the JSON/MD summary"
    else:
        summary["top_parts"] = full_items

    caveats = [
        "Executive Review aggregates the free Community checks computed from STEP text "
        "(names + NAUO). All figures are computed; none invented. No geometry-level data "
        "(volume/mass/material/contact) — that needs a geometry kernel or SolidWorks. "
        "Design intent, load paths, and functional reasoning are Professional.",
    ]
    if bom["unresolved_instances"]:
        caveats.append(f"{bom['unresolved_instances']} instance(s) had unresolved names "
                       f"(counted, not itemized).")

    # --- write the two summary artifacts (JSON for programs, MD for humans) ---
    full_summary = dict(summary)
    full_summary["bom_full"] = full_items
    try:
        jpath = os.path.join(out_dir, "review_summary.json")
        with open(jpath, "w", encoding="utf-8") as f:
            f.write(json.dumps({"capability": "review_summary", "status": "ok",
                                "results": full_summary, "caveats": caveats},
                               indent=2, ensure_ascii=False))
        artifacts["summary_json"] = jpath
    except Exception:
        pass
    try:
        mpath = os.path.join(out_dir, "review_summary.md")
        with open(mpath, "w", encoding="utf-8") as f:
            f.write(_render_review_md(os.path.basename(path), summary, full_items, caveats))
        artifacts["summary_md"] = mpath
    except Exception:
        pass

    return C.write(args.out, C.result("ok", "0.2", "review_summary",
                   results=summary, artifacts=artifacts, caveats=caveats))


def main():
    args = C.standard_args(__doc__)
    task = C.load_task(args.task)
    cap = task.get("capability")
    if cap not in CAPS:
        return C.write(args.out, C.result("failed", "0.2", cap,
                       caveats=[f"this command handles {sorted(CAPS)}"]))

    if cap == "review_summary":
        return _executive_review(task, args)

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
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "connectors"))
    try:
        import step_context as CTX
        _is_step = CTX.is_step(path) if path else False
    except Exception:
        CTX = None
        _is_step = str(path).lower().endswith((".step", ".stp"))
    if _is_step and CTX is not None:
        try:
            if cap in ("mechanism_detect", "vendor_summary", "category_summary") and not inputs.get("components"):
                inputs["components"] = CTX.extract_components(path)
            elif cap in ("assembly_tree", "exploded_view") and not inputs.get("nodes") and not inputs.get("components"):
                inputs["nodes"] = CTX.extract_nodes(path)
            elif cap == "assembly_stats" and not inputs.get("subassemblies") and not inputs.get("nodes"):
                inputs["subassemblies"] = CTX.extract_subassemblies(path)
            elif cap == "adjacency_graph" and not inputs.get("edges"):
                edges, names, _gtype = CTX.extract_edges(path)
                if edges:
                    inputs["edges"] = edges
                    inputs["_graph_type"] = _gtype  # geometric | hierarchy_fallback
                    if names and not inputs.get("names"):
                        inputs["names"] = names
        except Exception:
            pass  # fall through; engine will report needs_input if truly empty

    fn = free_fea.DISPATCH.get(cap)
    r = fn(task.get("inputs", {}) or {})
    if r["status"] == "needs_input":
        extra = []
        if not path:
            extra.append(
                "No model.path was provided, so nothing could be auto-extracted. "
                "Point the task at the STEP file / zip / folder, e.g.: "
                '{"capability":"' + str(cap) + '","model":{"path":"C:/path/to/assembly_or_folder"}} '
                "— then this command auto-extracts what it needs (no manual component list required).")
        return C.write(args.out, C.result("needs_input", "0.2", cap,
                       needs_input=r.get("needs", []),
                       caveats=[r.get("note", "")] + extra))
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
    elif cap == "adjacency_graph":
        gtype = (task.get("inputs") or {}).get("_graph_type", "geometric")
        if gtype == "hierarchy_fallback":
            caveat = ("HIERARCHY graph (parent->child from the assembly tree), NOT a geometric "
                      "adjacency graph. No geometry kernel was available, so this shows which parts "
                      "BELONG together, not which parts TOUCH. True contact adjacency needs SolidWorks "
                      "or a geometry kernel (cadquery).")
        else:
            caveat = ("Geometric adjacency only (who touches whom). Force-flow, constraint graph, "
                      "and design intent are Professional.")
    else:
        caveat = "Assembly structure tree; assembly order/sequence/intent is Professional."
    detail = (task.get("inputs") or {}).get("detail") or task.get("detail") or "summary"
    slim, full_path = _slim_results(r["results"], cap, args.out, detail)
    caveats = [caveat]
    artifacts = {}
    if full_path:
        artifacts["full_results"] = full_path
        caveats.append(f"Inline output is a summary; full result written to {full_path}. "
                       f"Pass \"detail\":\"full\" to get everything inline.")
    return C.write(args.out, C.result("ok", "0.2", cap, results=slim,
                   caveats=caveats, artifacts=artifacts))


if __name__ == "__main__":
    main()
