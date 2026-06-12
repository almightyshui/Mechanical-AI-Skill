"""Free-tier analysis engine (Community Edition).

Computes REAL results for the free-tier cases without a commercial solver, using
closed-form / analytical engineering formulas for common load cases. This is
deliberately the *basic* engine: single load case, simple supported geometry,
first few modes. The Professional core does automatic load-face/mesh identification
and full 3D FE on arbitrary geometry — that is not reproduced here.

Supported (free):
  static_strength: analytical beam/bar cases (cantilever, simply-supported, axial)
  modal:           first up to 3 natural frequencies of a uniform beam
  dfm_check:       a small set of geometric rules
  risk_score:      simple weighted roll-up of free-tier findings

Inputs are taken from task["inputs"]; if the case isn't analytically covered, the
result says so and points to Professional (full FE), rather than guessing.
"""
import math

G = 9.81


# ----------------------- static (analytical) -----------------------
def _section(inp):
    """Return (A, I, c) area, second moment, extreme-fibre distance for a section."""
    s = inp.get("section", {}) or {}
    shape = s.get("shape", "rect")
    if shape == "rect":
        b = float(s["width"]); h = float(s["height"])
        return b*h, b*h**3/12.0, h/2.0
    if shape == "circle":
        d = float(s["diameter"]); r = d/2.0
        return math.pi*r*r, math.pi*r**4/4.0, r
    if shape == "tube":
        do = float(s["outer_dia"]); di = float(s["inner_dia"])
        ro, ri = do/2.0, di/2.0
        A = math.pi*(ro*ro-ri*ri)
        I = math.pi*(ro**4-ri**4)/4.0
        return A, I, ro
    raise ValueError(f"unsupported section shape: {shape}")


def static_strength(inp):
    """Analytical static stress/deflection for a single load case on a simple beam/bar.

    inputs: case in {cantilever_end_load, simply_supported_center, axial},
            length L, load (N or mass_kg), section {...}, material {E, yield}.
    """
    mat = inp.get("material", {}) or {}
    E = float(mat.get("E")) if mat.get("E") else None
    yld = float(mat.get("yield")) if mat.get("yield") else None
    case = inp.get("case")
    L = inp.get("length")
    loads = inp.get("loads", [])
    if not case or not L or not loads:
        return {"status": "needs_input",
                "needs": ["inputs.case", "inputs.length", "inputs.loads", "inputs.section", "inputs.material.E"],
                "note": "Free static needs a known analytical case (cantilever_end_load / "
                        "simply_supported_center / axial), length, section, load and E. "
                        "Arbitrary 3D geometry FE is Professional."}
    L = float(L)
    ld = loads[0]
    F = ld.get("value_N")
    if F is None and ld.get("mass_kg") is not None:
        F = float(ld["mass_kg"]) * G
    if F is None:
        return {"status": "needs_input", "needs": ["inputs.loads[0].value_N or mass_kg"]}
    F = float(F)
    A, I, c = _section(inp)
    conv = {}
    if ld.get("mass_kg") is not None:
        conv["load_conversion"] = f"{ld['mass_kg']} kg -> {round(F,2)} N (x g=9.81)"

    if case == "axial":
        sigma = F / A
        defl = F * L / (A * E) if E else None
        Mmax = None
    elif case == "cantilever_end_load":
        Mmax = F * L
        sigma = Mmax * c / I
        defl = F * L**3 / (3 * E * I) if E else None
    elif case == "simply_supported_center":
        Mmax = F * L / 4.0
        sigma = Mmax * c / I
        defl = F * L**3 / (48 * E * I) if E else None
    else:
        return {"status": "failed", "note": f"unsupported analytical case: {case}"}

    out = {"case": case, "peak_stress": sigma, "max_deflection": defl,
           "max_moment": Mmax, "section_area": A, "section_I": I}
    out.update(conv)
    if yld:
        out["safety_factor"] = round(yld / sigma, 3) if sigma else None
        out["yield_used"] = yld
    return {"status": "ok", "results": out}


# ----------------------- modal (analytical) -----------------------
# Uniform Euler-Bernoulli beam natural frequencies: f_n = (beta_n^2 / 2pi) sqrt(EI/(rho*A*L^4))
_BETA = {
    "cantilever": [1.875104, 4.694091, 7.854757],
    "simply_supported": [math.pi, 2*math.pi, 3*math.pi],
    "fixed_fixed": [4.730041, 7.853205, 10.995608],
    "free_free": [4.730041, 7.853205, 10.995608],
}


def modal(inp):
    mat = inp.get("material", {}) or {}
    E = mat.get("E"); rho = mat.get("rho")
    L = inp.get("length")
    mount = inp.get("mounting", "cantilever")
    n = min(int(inp.get("n_modes", 3) or 3), 3)
    if not (E and rho and L and inp.get("section")):
        return {"status": "needs_input",
                "needs": ["inputs.material.E", "inputs.material.rho", "inputs.length", "inputs.section", "inputs.mounting"],
                "note": "Free modal computes a uniform-beam analytical result (first 3 modes). "
                        "Full 3D modal on arbitrary geometry is Professional."}
    E = float(E); rho = float(rho); L = float(L)
    A, I, _ = _section(inp)
    betas = _BETA.get(mount)
    if not betas:
        return {"status": "failed",
                "note": f"unsupported mounting '{mount}'; use one of {list(_BETA)}"}
    freqs = []
    for b in betas[:n]:
        f = (b**2 / (2*math.pi)) * math.sqrt(E*I / (rho*A*L**4))
        freqs.append(round(f, 3))
    out = {"mounting": mount, "frequencies_hz": freqs, "modes_returned": len(freqs)}
    exc = inp.get("excitation_hz")
    if exc and freqs:
        margin = (freqs[0] - exc) / exc
        out["excitation_hz"] = exc
        out["first_mode_margin_pct"] = round(margin*100, 1)
        out["resonance_risk"] = abs(margin) < 0.2
    return {"status": "ok", "results": out}


# ----------------------- basic DFM -----------------------
def dfm_check(inp):
    """Basic geometric DFM from caller-provided feature measurements.

    The free tier checks a few rules against features the caller supplies in
    inputs.features (e.g. from a SolidWorks walk). It does NOT include the
    enterprise rule library / process-specific knowledge.
    """
    feats = inp.get("features")
    if feats is None:
        return {"status": "needs_input", "needs": ["inputs.features"],
                "note": "Provide measured features [{type,value,...}] (holes depth/dia, wall "
                        "thickness, internal radius). Auto feature-extraction + advanced rules "
                        "are Professional."}
    th = {"deep_hole_depth_to_dia": float(inp.get("deep_hole_depth_to_dia", 5.0)),
          "min_wall_mm": float(inp.get("min_wall_mm", 1.0)),
          "min_internal_radius_mm": float(inp.get("min_internal_radius_mm", 0.5))}
    findings = []
    for f in feats:
        t = f.get("type")
        if t == "hole" and f.get("depth") and f.get("diameter"):
            ratio = f["depth"]/f["diameter"]
            if ratio > th["deep_hole_depth_to_dia"]:
                findings.append({"type": "deep_hole", "feature": f.get("name", "hole"),
                                 "value": round(ratio, 2), "threshold": th["deep_hole_depth_to_dia"],
                                 "severity": "risk", "suggestion": "increase dia / reduce depth or call out gun-drilling"})
        if t == "wall" and f.get("thickness") is not None:
            if f["thickness"] < th["min_wall_mm"]:
                findings.append({"type": "thin_wall", "feature": f.get("name", "wall"),
                                 "value": f["thickness"], "threshold": th["min_wall_mm"],
                                 "severity": "risk", "suggestion": "thicken or add ribs"})
        if t == "internal_corner" and f.get("radius") is not None:
            if f["radius"] < th["min_internal_radius_mm"]:
                findings.append({"type": "sharp_internal_corner", "feature": f.get("name", "corner"),
                                 "value": f["radius"], "threshold": th["min_internal_radius_mm"],
                                 "severity": "blocker", "suggestion": "add radius >= tool radius"})
    return {"status": "ok", "results": {"findings": findings, "thresholds_used": th,
            "ruleset": "basic", "note": "Basic DFM rule set; advanced rule library is Professional."}}


# ----------------------- simple risk score -----------------------
def risk_score(inp):
    """Simple weighted roll-up from free-tier signals the caller passes in.

    inputs.signals: {interferences, dfm_blockers, dfm_risks, min_safety_factor,
                     resonance_risk, parts, fasteners, assembly_depth,
                     tool_clearance_warnings}
    Produces a 0-100 score, a transparent list of contributors (each with the points
    it cost), and High/Med/Low buckets. Advanced scoring (criticality-weighted,
    code-aware, FEA/reliability/maintenance dimensions) is Professional.
    """
    s = inp.get("signals")
    if s is None:
        return {"status": "needs_input", "needs": ["inputs.signals"],
                "note": "Provide signals from the free checks {interferences, dfm_blockers, "
                        "dfm_risks, min_safety_factor, resonance_risk, parts, fasteners, "
                        "assembly_depth, tool_clearance_warnings}. Advanced scoring is Professional."}
    score = 100
    high, med, low = [], [], []
    contributors = []   # transparent breakdown: each factor and the points it cost

    def deduct(points, label, bucket=None):
        nonlocal score
        if points <= 0:
            return
        score -= points
        contributors.append({"factor": label, "points": points})
        if bucket is not None:
            bucket.append(label)

    # --- design-integrity signals ---
    if s.get("interferences"):
        deduct(25, f"{s['interferences']} interference(s)", high)
    if s.get("dfm_blockers"):
        deduct(15, f"{s['dfm_blockers']} DFM blocker(s)", high)
    sf = s.get("min_safety_factor")
    if sf is not None:
        if sf < 1.0:
            deduct(30, f"safety factor {sf} < 1 (predicted to yield)", high)
        elif sf < 1.5:
            deduct(12, f"safety factor {sf} below typical 1.5 target", med)
    if s.get("resonance_risk"):
        deduct(12, "1st mode within 20% of excitation (resonance risk)", med)
    if s.get("dfm_risks"):
        deduct(min(10, 2*s["dfm_risks"]), f"{s['dfm_risks']} DFM cost/risk item(s)", low)

    # --- assembly-complexity signals (from basic DFA) ---
    parts = s.get("parts")
    if parts and parts > 50:
        deduct(min(12, (parts - 50)//8 + 4), f"high part count ({parts})", med)
    fasteners = s.get("fasteners")
    if fasteners and fasteners > 20:
        deduct(min(10, (fasteners - 20)//4 + 3), f"high fastener count ({fasteners})", med)
    depth = s.get("assembly_depth")
    if depth and depth > 4:
        deduct(min(8, (depth - 4)*2), f"deep assembly tree (depth {depth})", low)
    tcw = s.get("tool_clearance_warnings")
    if tcw:
        deduct(min(10, 4*tcw), f"{tcw} tool-clearance issue(s)", med)

    score = max(0, min(100, score))
    contributors.sort(key=lambda c: -c["points"])
    return {"status": "ok", "results": {"overall_score": score,
            "contributors": contributors,
            "high": high, "med": med, "low": low, "scoring": "simple",
            "note": "Simple multi-factor risk score (design integrity + assembly complexity). "
                    "Advanced scoring — criticality-weighted, code-aware, with FEA / reliability / "
                    "maintenance dimensions — is Professional."}}


DISPATCH = {"static_strength": static_strength, "modal": modal,
            "dfm_check": dfm_check, "risk_score": risk_score}


# ----------------------- basic DFA (Community) -----------------------
def dfa_check(inp):
    """Basic Design-for-Assembly: complexity stats + geometric assemblability.

    Geometry + rules only (no sequence/path/time prediction — those are Professional).
    inputs:
      components: [{name, fastener?:bool, fastener_type?}]   (from assembly walk)
      assembly_depth: int                                    (tree depth)
      access_checks: [{name, tool, required_mm, available_mm}]  (optional tool-space checks)
    """
    comps = inp.get("components")
    if comps is None:
        return {"status": "needs_input", "needs": ["inputs.components"],
                "note": "Provide the component list [{name, fastener?}] from the assembly walk. "
                        "Assembly sequence/path/time prediction is Professional."}
    n_parts = len(comps)
    fasteners = [c for c in comps if c.get("fastener")]
    n_fast = len(fasteners)
    fast_types = sorted({c.get("fastener_type") or c.get("name") for c in fasteners})
    depth = int(inp.get("assembly_depth", 0) or 0)

    # complexity score (0-100, higher = simpler/better) — transparent linear rule
    score = 100
    if n_parts > 50:  score -= min(25, (n_parts - 50) // 8)
    if n_fast > 20:   score -= min(20, (n_fast - 20) // 4)
    if len(fast_types) > 4: score -= min(15, (len(fast_types) - 4) * 3)
    if depth > 4:     score -= min(15, (depth - 4) * 4)
    score = max(0, min(100, score))

    # basic assemblability (geometric tool-space / insertion checks supplied by caller)
    warnings = []
    for a in inp.get("access_checks", []) or []:
        req = a.get("required_mm"); avail = a.get("available_mm")
        if req is not None and avail is not None and avail < req:
            warnings.append({"feature": a.get("name", "fastener"),
                             "tool": a.get("tool", "tool"),
                             "required_mm": req, "available_mm": avail,
                             "severity": "warning",
                             "issue": "insufficient tool clearance",
                             "suggestion": "reposition, recess, or use a lower-profile drive"})
    # DFA score folds in access warnings
    dfa_score = max(0, score - 4 * len(warnings))

    return {"status": "ok", "results": {
        "parts": n_parts,
        "fasteners": n_fast,
        "fastener_types": len(fast_types),
        "assembly_depth": depth,
        "complexity_score": score,
        "dfa_score": dfa_score,
        "tool_clearance_warnings": warnings,
        "issues_summary": f"{len(warnings)} tool-clearance warning(s)",
        "note": "Basic DFA: complexity stats + geometric tool/insertion checks. "
                "Assembly sequence, path, time, ergonomics and automation are Professional."}}


# ----------------------- basic mechanism detection (Community) -----------------------
# "What is it?" — name + standard-part + simple-topology rules. NOT purpose/intent.
import re as _re

_MECH_RULES = [
    ("Gear Train",        [r"\bgear\b", r"spur", r"helical", r"pinion", r"\bring_gear\b", r"\bsun\b", r"\bplanet\b"]),
    ("Timing Belt Drive", [r"timing", r"\bpulley\b", r"\bbelt\b", r"sprocket.*belt"]),
    ("Chain Drive",       [r"\bchain\b", r"\bsprocket\b", r"roller_chain"]),
    ("Lead Screw System", [r"lead.?screw", r"ball.?screw", r"\bscrew_shaft\b", r"\bnut_block\b", r"acme"]),
]


def mechanism_detect(inp):
    """Identify the mechanism TYPE from part names + standard parts (Community).

    Answers 'what is it' (Gear Train / Timing Belt Drive / Chain Drive / Lead Screw
    System) with a confidence and the evidence parts. It does NOT infer purpose,
    power flow, design intent, or failure modes — those are Professional.

    inputs: components: [{name, standard_part?}]
    """
    comps = inp.get("components")
    if comps is None:
        return {"status": "needs_input", "needs": ["inputs.components"],
                "note": "Provide the component list. This identifies the mechanism TYPE only; "
                        "purpose / power-flow / design-intent inference is Professional."}
    names = [(c.get("name") or "").lower() for c in comps]
    detected = []
    for mech, patterns in _MECH_RULES:
        hits = [n for n in names if any(_re.search(p, n) for p in patterns)]
        if hits:
            # crude confidence: more matching parts -> higher, capped
            conf = min(95, 40 + 12 * len(hits))
            detected.append({"mechanism": mech, "confidence": conf,
                             "evidence": sorted(set(hits))[:8]})
    detected.sort(key=lambda d: -d["confidence"])
    if not detected:
        return {"status": "ok", "results": {"detected": [],
                "note": "No common mechanism matched by name/standard-part rules. "
                        "This is type identification only (experimental), not design-intent analysis."}}
    return {"status": "ok", "results": {
        "detected": detected,
        "primary": detected[0]["mechanism"],
        "note": "Mechanism TYPE identification (experimental) from names + standard parts. "
                "It answers 'what is it', not 'what is it for' — purpose/intent is Professional."}}


DISPATCH.update({"dfa_check": dfa_check, "mechanism_detect": mechanism_detect})


# ----------------------- assembly tree (Community, lightweight viz) -----------------------
def assembly_tree(inp):
    """Render a lightweight text tree of the assembly structure (no 3D).

    Confirms 'parsing succeeded' at a glance. Pure structure display — it does NOT
    explain why parts are arranged this way or how they assemble (Professional).

    inputs.nodes: nested [{name, children?:[...]}], OR
    inputs.components: flat [{name, parent?}]  (parent = name of parent node)
    inputs.root_name: optional label for the top node
    """
    nodes = inp.get("nodes")
    comps = inp.get("components")
    root_name = inp.get("root_name", "Assembly")

    def render(tree, prefix="", lines=None):
        if lines is None:
            lines = []
        for i, node in enumerate(tree):
            last = i == len(tree) - 1
            branch = "└── " if last else "├── "
            lines.append(prefix + branch + node["name"])
            kids = node.get("children") or []
            if kids:
                ext = "    " if last else "│   "
                render(kids, prefix + ext, lines)
        return lines

    if nodes:
        tree = nodes
    elif comps:
        # build a 2-level tree from flat list with optional parent
        by_parent = {}
        roots = []
        for c in comps:
            p = c.get("parent")
            if p:
                by_parent.setdefault(p, []).append({"name": c["name"]})
            else:
                roots.append({"name": c["name"]})
        for r in roots:
            r["children"] = by_parent.get(r["name"], [])
        tree = roots
    else:
        return {"status": "needs_input", "needs": ["inputs.nodes or inputs.components"],
                "note": "Provide the assembly hierarchy (nested nodes or flat components with parent). "
                        "This renders the structure; assembly order / intent is Professional."}

    lines = [root_name] + render(tree)
    text = "\n".join(lines)
    # count nodes
    def count(t):
        return sum(1 + count(n.get("children") or []) for n in t)
    return {"status": "ok", "results": {
        "tree_text": text,
        "node_count": count(tree),
        "note": "Assembly structure tree (parse confirmation + layout). It shows what is "
                "in the assembly, not why it's arranged this way or how to assemble it (Professional)."}}


DISPATCH.update({"assembly_tree": assembly_tree})


# ----------------------- review summary (Community, one-glance overview) -----------------------
def review_summary(inp):
    """One-glance Mechanical Review Summary — aggregates the free-tier metrics.

    Pure aggregation of already-computed numbers the caller passes in. It does NOT
    re-run analyses or add interpretation — it's a dashboard of what the free checks
    found. Great for a screenshot/GIF.

    inputs.metrics: {parts, fasteners, assembly_depth, detected_mechanisms,
                     interferences, dfm_warnings, dfa_warnings, risk_score}
    """
    m = inp.get("metrics")
    if m is None:
        return {"status": "needs_input", "needs": ["inputs.metrics"],
                "note": "Provide the metrics gathered from the free checks to summarize."}
    rows = [
        ("Parts",               m.get("parts")),
        ("Fasteners",           m.get("fasteners")),
        ("Assembly Depth",      m.get("assembly_depth")),
        ("Detected Mechanisms", m.get("detected_mechanisms")),
        ("Interferences",       m.get("interferences")),
        ("DFM Warnings",        m.get("dfm_warnings")),
        ("DFA Warnings",        m.get("dfa_warnings")),
        ("Risk Score",          m.get("risk_score")),
    ]
    rows = [(k, v) for k, v in rows if v is not None]
    width = max((len(k) for k, _ in rows), default=10)
    lines = ["Mechanical Review Summary", "=" * 30]
    for k, v in rows:
        suffix = " / 100" if k == "Risk Score" else ""
        lines.append(f"{k.ljust(width)} : {v}{suffix}")
    return {"status": "ok", "results": {
        "summary_text": "\n".join(lines),
        "metrics": {k: v for k, v in rows},
        "note": "One-glance aggregation of the free checks (no new analysis, no interpretation)."}}


DISPATCH.update({"review_summary": review_summary})
