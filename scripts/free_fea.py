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
    subs = s.get("subassemblies")
    if subs and subs > 8:
        deduct(min(8, (subs - 8)//2 + 2), f"many subassemblies ({subs})", low)
    inst = s.get("instances")
    if inst and inst > 200:
        deduct(min(8, (inst - 200)//100 + 3), f"high instance count ({inst})", med)
    mech = s.get("mechanism_count")
    if mech and mech > 3:
        deduct(min(6, (mech - 3)*2), f"many distinct mechanisms ({mech})", low)

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
    subs = int(inp.get("subassemblies", 0) or 0)
    instances = int(inp.get("instances", 0) or 0)

    # complexity score (0-100, higher = simpler/better) — transparent linear rule
    score = 100
    if n_parts > 50:  score -= min(25, (n_parts - 50) // 8)
    if n_fast > 20:   score -= min(20, (n_fast - 20) // 4)
    if len(fast_types) > 4: score -= min(15, (len(fast_types) - 4) * 3)
    if depth > 4:     score -= min(15, (depth - 4) * 4)
    if subs > 8:      score -= min(10, (subs - 8) // 2)
    if instances > 200: score -= min(10, (instances - 200) // 100 + 2)
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

    # honest caveat: STEP exports usually strip fastener part names, so a low
    # fastener count on a large assembly is almost certainly an under-count.
    notes = ("Basic DFA: complexity stats + geometric tool/insertion checks. "
             "Assembly sequence, path, time, ergonomics and automation are Professional.")
    fastener_caveat = None
    if n_parts >= 40 and n_fast <= 2:
        fastener_caveat = (f"Only {n_fast} fastener(s) detected among {n_parts} parts — "
                           "almost certainly an under-count. STEP exports usually drop "
                           "fastener/toolbox part names; use the original SolidWorks "
                           "assembly for a true fastener count. Complexity here reflects "
                           "non-fastener parts only.")

    return {"status": "ok", "results": {
        "parts": n_parts,
        "fasteners": n_fast,
        "fastener_types": len(fast_types),
        "assembly_depth": depth,
        "subassemblies": subs,
        "instances": instances,
        "complexity_score": score,
        "dfa_score": dfa_score,
        "tool_clearance_warnings": warnings,
        "issues_summary": f"{len(warnings)} tool-clearance warning(s)",
        "fastener_caveat": fastener_caveat,
        "note": notes}}


# ----------------------- basic mechanism detection (Community) -----------------------
# "What is it?" — name + standard-part + simple-topology rules. NOT purpose/intent.
import re as _re

_MECH_RULES = [
    ("Gear Train",         [r"\bgear\b", r"spur", r"helical", r"pinion", r"\bring_gear\b", r"\bsun\b", r"\bplanet\b"]),
    ("Timing Belt Drive",  [r"timing", r"\bpulley\b", r"\bbelt\b", r"sprocket.*belt"]),
    ("Chain Drive",        [r"\bchain\b", r"\bsprocket\b", r"roller_chain"]),
    ("Lead Screw System",  [r"lead.?screw", r"ball.?screw", r"\bscrew_shaft\b", r"\bnut_block\b", r"acme"]),
    ("Robot Arm",          [r"\brobot\b", r"\baxis[\s_-]?\d", r"\bj[1-6]\b", r"manipulator", r"\blink[\s_-]?\d", r"fanuc", r"kuka", r"abb_irb", r"ur\d+"]),
    ("Linear Slide",       [r"linear[\s_-]?(guide|rail|slide|stage)", r"\blm[\s_-]?guide\b", r"\bcarriage\b", r"\brail_block\b", r"thk"]),
    ("Pneumatic Cylinder", [r"pneumatic", r"\bcylinder\b", r"\bpiston\b", r"air[\s_-]?cylinder", r"smc", r"festo", r"bimba"]),
    ("Rotary Table",       [r"rotary[\s_-]?(table|stage|axis)", r"\bturntable\b", r"index(er|ing)[\s_-]?table", r"\bgoniometer\b"]),
]


def mechanism_detect(inp):
    """Identify the mechanism TYPE from part names + standard parts (Community).

    Two layers, both rule-based:
      1) single-part type rules (gear train, belt, chain, lead screw, robot arm,
         linear slide, pneumatic cylinder, rotary table)
      2) composite pattern matching — recognizes multi-component groupings by which
         roles are present (e.g. motor + coupling + shaft -> "Rotary Drive Train";
         guide + carriage + screw -> "Linear Motion Module")

    It reports WHAT is grouped — not what it's for, how power flows, or why it's
    designed this way. That interpretation is Professional.

    inputs: components: [{name, standard_part?}]
    """
    comps = inp.get("components")
    if comps is None:
        return {"status": "needs_input", "needs": ["inputs.components"],
                "note": "Provide the component list. This identifies the mechanism TYPE only; "
                        "purpose / power-flow / design-intent inference is Professional."}
    names = [(c.get("name") or "").lower() for c in comps]

    # --- layer 1: single-part type rules ---
    detected = []
    for mech, patterns in _MECH_RULES:
        hits = [n for n in names if any(_re.search(p, n) for p in patterns)]
        if hits:
            conf = min(95, 40 + 12 * len(hits))
            detected.append({"mechanism": mech, "confidence": conf,
                             "evidence": sorted(set(hits))[:8]})
    detected.sort(key=lambda d: -d["confidence"])

    # --- layer 2: composite pattern matching (roles present in the assembly) ---
    def has_role(role_patterns):
        for n in names:
            if any(_re.search(p, n) for p in role_patterns):
                return n
        return None

    roles = {
        "motor":     [r"\bmotor\b", r"servo", r"stepper", r"\bbldc\b"],
        "coupling":  [r"coupling", r"\bjaw\b.*coupl"],
        "shaft":     [r"\bshaft\b", r"\baxle\b", r"spindle"],
        "gear":      [r"\bgear\b", r"pinion", r"reducer", r"gearbox"],
        "guide":     [r"linear.*(guide|rail)", r"\blm.?guide\b", r"\brail\b"],
        "carriage":  [r"carriage", r"\bblock\b", r"slider", r"\bslide\b"],
        "screw":     [r"lead.?screw", r"ball.?screw", r"\bbsj\b", r"acme", r"screw.?jack"],
        "bearing":   [r"\bbearing\b", r"\b6[0-9]{3}\b", r"pillow.?block"],
        "cylinder":  [r"cylinder", r"\bpiston\b", r"pneumatic"],
    }
    present = {r: has_role(p) for r, p in roles.items()}

    composites = []
    def add_comp(name, need, note):
        ev = [present[r] for r in need if present.get(r)]
        if all(present.get(r) for r in need):
            composites.append({"composite": name, "roles_present": need,
                               "evidence": ev, "note": note})

    add_comp("Rotary Drive Train", ["motor", "coupling", "shaft"],
             "motor + coupling + shaft grouped (a rotary drive chain is present)")
    add_comp("Geared Drive", ["motor", "gear"],
             "motor + gear/reducer grouped")
    add_comp("Linear Motion Module", ["guide", "carriage", "screw"],
             "linear guide + carriage + screw grouped (a linear motion stage is present)")
    add_comp("Belt/Screw Actuated Slide", ["guide", "carriage"],
             "guide + carriage grouped (a linear slide is present)")
    add_comp("Supported Rotating Shaft", ["shaft", "bearing"],
             "shaft + bearing grouped (a supported rotating member is present)")

    if not detected and not composites:
        return {"status": "ok", "results": {"detected": [], "composites": [],
                "note": "No common mechanism or composite matched by name/standard-part rules. "
                        "Type identification only (experimental), not design-intent analysis."}}
    return {"status": "ok", "results": {
        "detected": detected,
        "primary": detected[0]["mechanism"] if detected else (composites[0]["composite"] if composites else None),
        "composites": composites,
        "note": "Mechanism TYPE + composite-pattern identification (experimental) from names "
                "and standard parts. It reports WHAT is grouped — not what it's for, how power "
                "flows, or why it's designed this way (that is Professional)."}}


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
        ("Instances",           m.get("instances")),
        ("Subassemblies",       m.get("subassemblies")),
        ("Leaf Parts",          m.get("leaf_parts")),
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


# ----------------------- vendor summary (Community) -----------------------
# Identify component vendors/brands from part names. Pure name matching — "what
# brands are in here", not sourcing/pricing/alternates (those are Professional).
_VENDOR_RULES = {
    "FANUC": [r"fanuc"], "KUKA": [r"kuka"], "ABB": [r"\babb\b|irb\d"],
    "Universal Robots": [r"\bur[3-9,10,16,20]\b|universal.?robot"],
    "SCHUNK": [r"schunk"], "SMC": [r"\bsmc\b"], "Festo": [r"festo"],
    "Bimba": [r"bimba"], "Banner": [r"banner"], "Keyence": [r"keyence"],
    "THK": [r"\bthk\b"], "NSK": [r"\bnsk\b"], "SKF": [r"\bskf\b"],
    "Bosch Rexroth": [r"rexroth|bosch"], "Misumi": [r"misumi"],
    "Nook": [r"\bnook\b"], "Parker": [r"parker"], "Omron": [r"omron"],
    "Allen-Bradley": [r"allen.?bradley|\bab_"], "IGUS": [r"\bigus\b"],
}


def vendor_summary(inp):
    """Detect component vendors/brands from part names (Community).

    Answers 'what brands are in this assembly'. It does NOT do sourcing, pricing,
    alternates, or supply-chain analysis — that is Professional (procurement intel).

    inputs.components: [{name}]
    """
    comps = inp.get("components")
    if comps is None:
        return {"status": "needs_input", "needs": ["inputs.components"],
                "note": "Provide the component list. Vendor detection is name-based; "
                        "sourcing / pricing / alternates is Professional."}
    names = [(c.get("name") or "") for c in comps]
    found = {}
    for vendor, pats in _VENDOR_RULES.items():
        hits = [n for n in names if any(_re.search(p, n.lower()) for p in pats)]
        if hits:
            found[vendor] = {"count": len(hits), "examples": sorted(set(hits))[:5]}
    detected = sorted(found.items(), key=lambda kv: -kv[1]["count"])
    return {"status": "ok", "results": {
        "vendors": [{"vendor": v, **d} for v, d in detected],
        "vendor_count": len(detected),
        "note": "Brand detection from part names (Community). Sourcing, pricing, "
                "alternate-part and supply-chain analysis is Professional."}}


DISPATCH.update({"vendor_summary": vendor_summary})


# ----------------------- assembly statistics (Community) -----------------------
def assembly_stats(inp):
    """Top-level assembly statistics — counts per subassembly (instances).

    Pure counting/aggregation of the parsed structure. It reports how many instances
    sit under each top-level node — it does NOT interpret assembly order or function
    (Professional).

    inputs.subassemblies: [{name, instances}]  OR
    inputs.nodes: nested [{name, children?}]   (instances counted from the tree)
    """
    subs = inp.get("subassemblies")
    nodes = inp.get("nodes")
    if subs is None and nodes is None:
        return {"status": "needs_input", "needs": ["inputs.subassemblies or inputs.nodes"],
                "note": "Provide top-level subassemblies with instance counts, or the nested tree."}

    def count_instances(node):
        kids = node.get("children") or []
        return 1 + sum(count_instances(k) for k in kids)

    if subs is None:
        subs = [{"name": n["name"], "instances": count_instances(n) - 1 or 1} for n in nodes]

    subs = sorted(subs, key=lambda x: -(x.get("instances") or 0))
    total = sum(s.get("instances") or 0 for s in subs)
    return {"status": "ok", "results": {
        "top_assemblies": [{"name": s["name"], "instances": s.get("instances")} for s in subs],
        "subassembly_count": len(subs),
        "total_instances": total,
        "note": "Top-level instance counts (statistics only). Assembly order / function "
                "interpretation is Professional."}}


# ----------------------- exploded view (Community, lightweight viz) -----------------------
def exploded_view(inp):
    """Render the assembly structure as a Mermaid graph (and ASCII) for the README.

    A visualization of the parsed structure — not a true 3D exploded view, and not
    an assembly-sequence diagram (that's Professional). Great for screenshots.

    inputs.nodes: nested [{name, children?}]  OR inputs.components: [{name, parent?}]
    inputs.root_name: optional top label
    """
    nodes = inp.get("nodes")
    comps = inp.get("components")
    root = inp.get("root_name", "Assembly")
    if not nodes and not comps:
        return {"status": "needs_input", "needs": ["inputs.nodes or inputs.components"],
                "note": "Provide the assembly hierarchy. This visualizes structure, "
                        "not assembly sequence (Professional)."}

    if comps and not nodes:
        by_parent = {}
        roots = []
        for c in comps:
            p = c.get("parent")
            (by_parent.setdefault(p, []) if p else roots).append({"name": c["name"]}) \
                if p else roots.append({"name": c["name"]})
        for r in roots:
            r["children"] = by_parent.get(r["name"], [])
        nodes = roots

    # Mermaid
    lines = ["graph TD"]
    counter = [0]
    def sid(name):
        counter[0] += 1
        return f"n{counter[0]}"
    def walk(parent_id, parent_name, tree):
        for node in tree:
            nid = sid(node["name"])
            safe = node["name"].replace('"', "'")
            lines.append(f'  {parent_id}["{parent_name}"] --> {nid}["{safe}"]')
            kids = node.get("children") or []
            if kids:
                walk(nid, node["name"], kids)
    rootid = sid(root)
    walk(rootid, root, nodes)
    mermaid = "\n".join(lines)

    return {"status": "ok", "results": {
        "mermaid": mermaid,
        "note": "Structure visualization (Mermaid). Not a 3D exploded view and not an "
                "assembly-sequence diagram (Professional)."}}


# ----------------------- component category summary (Community) -----------------------
# Count components by category from names. Statistics only — NOT a procurement list,
# sourcing, supplier or cost analysis (that is Professional procurement intelligence).
_CATEGORY_RULES = [
    ("Motors",              [r"\bmotor\b", r"servo", r"stepper"]),
    ("Sensors",             [r"sensor", r"\bencoder\b", r"proximity", r"photoeye", r"\blimit_switch\b"]),
    ("Pneumatic Cylinders", [r"pneumatic.*cylinder", r"air.?cylinder", r"\bcylinder\b"]),
    ("Robot Arms",          [r"\brobot\b", r"manipulator"]),
    ("Bearings",            [r"\bbearing\b", r"\b6[0-9]{3}\b"]),
    ("Gears",               [r"\bgear\b", r"pinion"]),
    ("Linear Guides",       [r"linear.*(guide|rail)", r"\blm.?guide\b"]),
    ("Fasteners",           [r"\bbolt\b", r"\bscrew\b", r"\bnut\b", r"\bwasher\b"]),
    ("Couplings",           [r"coupling"]),
    ("Valves",              [r"\bvalve\b"]),
]


def category_summary(inp):
    """Count components by category from part names (Community).

    Answers 'how many of each kind of thing' — statistics only. It is NOT a
    procurement list and does NOT do sourcing, suppliers, alternates, or cost
    (that is Professional procurement intelligence).

    inputs.components: [{name, qty?}]
    """
    comps = inp.get("components")
    if comps is None:
        return {"status": "needs_input", "needs": ["inputs.components"],
                "note": "Provide the component list. This counts by category; procurement "
                        "(sourcing/cost/alternates) is Professional."}
    counts = {}
    for c in comps:
        name = (c.get("name") or "").lower()
        qty = c.get("qty", 1) or 1
        for cat, pats in _CATEGORY_RULES:
            if any(_re.search(p, name) for p in pats):
                counts[cat] = counts.get(cat, 0) + qty
                break  # first matching category only
    out = sorted(counts.items(), key=lambda kv: -kv[1])
    return {"status": "ok", "results": {
        "categories": [{"category": k, "count": v} for k, v in out],
        "note": "Component counts by category (statistics only). Procurement lists, "
                "sourcing, alternates and cost are Professional."}}


DISPATCH.update({"assembly_stats": assembly_stats, "exploded_view": exploded_view,
                 "category_summary": category_summary})


# ----------------------- fastener intelligence v2 (Community) -----------------------
# Rule-based checks on caller-supplied fastener data. Geometry + public engineering
# rules of thumb only. NOT a preload/torque/joint-stiffness analysis (that needs the
# real load path and is Professional). Numbers here are first-pass screens.

# Minimum thread engagement as a multiple of nominal diameter, by mating material.
_ENGAGE_MULT = {"steel": 1.0, "cast_iron": 1.25, "brass": 1.5, "bronze": 1.5,
                "aluminum": 2.0, "aluminium": 2.0, "magnesium": 2.5, "plastic": 2.5}


def fastener_check(inp):
    """Fastener intelligence v2 — engagement + stack (washer/nut) checks.

    inputs.fasteners: list of joints, each:
      {name, diameter_mm, mating_material?, thread_engagement_mm?,
       stack?: ["bolt","washer","plate","washer","nut"]}

    Two rule-based screens:
      1) engagement_check — is threaded engagement >= recommended (mult x diameter)?
      2) stack_analysis   — flags a likely missing washer or missing nut from the
         stack description (no flat bearing surface / no thread termination).

    First-pass screens from public rules of thumb. Real preload / torque / joint-
    stiffness analysis needs the load path and is Professional.
    """
    fasteners = inp.get("fasteners")
    if fasteners is None:
        return {"status": "needs_input", "needs": ["inputs.fasteners"],
                "note": "Provide fasteners [{name, diameter_mm, mating_material?, "
                        "thread_engagement_mm?, stack?}]. These are rule-of-thumb screens; "
                        "preload/torque/joint analysis is Professional."}

    results = []
    for f in fasteners:
        name = f.get("name", "fastener")
        d = f.get("diameter_mm")
        findings = []

        # 1) engagement check
        eng = f.get("thread_engagement_mm")
        mat = (f.get("mating_material") or "steel").lower()
        mult = _ENGAGE_MULT.get(mat, 1.5)
        if d and eng is not None:
            recommended = round(mult * d, 2)
            if eng < recommended:
                findings.append({"type": "engagement", "severity": "risk",
                    "detail": f"thread engagement {eng} mm < recommended {recommended} mm "
                              f"({mult}xD for {mat})",
                    "suggestion": "deepen the tapped hole, use a longer thread, or a thread insert"})
            else:
                findings.append({"type": "engagement", "severity": "ok",
                    "detail": f"engagement {eng} mm >= {recommended} mm ({mult}xD for {mat})"})

        # 2) stack analysis — look at the layer description
        stack = [s.lower() for s in (f.get("stack") or [])]
        if stack:
            has_head = any(t in stack[0] for t in ("bolt", "screw", "cap"))
            has_nut = any("nut" in s for s in stack)
            has_thread_end = has_nut or "tapped" in " ".join(stack) or "blind" in " ".join(stack)
            washer_count = sum(1 for s in stack if "washer" in s)
            # missing nut / thread termination
            if has_head and not has_thread_end:
                findings.append({"type": "stack", "severity": "risk",
                    "detail": "through-bolt stack with no nut or tapped/blind termination",
                    "suggestion": "add a nut, or confirm the far part is tapped"})
            # washer under nut/head into soft material
            soft = (f.get("mating_material") or "").lower() in ("aluminum", "aluminium", "plastic", "magnesium")
            if has_nut and washer_count == 0:
                findings.append({"type": "stack", "severity": "risk",
                    "detail": "nutted joint with no washer in the stack",
                    "suggestion": "add a washer under the nut (and head) to spread bearing load"
                                  + (" — especially into soft material" if soft else "")})
            elif soft and washer_count == 0:
                findings.append({"type": "stack", "severity": "risk",
                    "detail": "bolt bearing directly on soft material, no washer",
                    "suggestion": "add a washer to avoid embedment / loss of preload"})

        results.append({"fastener": name, "diameter_mm": d, "findings": findings})

    n_risk = sum(1 for r in results for x in r["findings"] if x["severity"] == "risk")
    return {"status": "ok", "results": {
        "fasteners_checked": len(results),
        "risk_count": n_risk,
        "details": results,
        "note": "Rule-of-thumb fastener screens (engagement vs n*D; missing washer/nut "
                "from the stack). Not a preload/torque/joint-stiffness analysis (Professional)."}}


DISPATCH.update({"fastener_check": fastener_check})


# ----------------------- adjacency graph (Community, geometric neighbours) -----------------------
def adjacency_graph(inp):
    """Geometric adjacency graph — which parts touch / are neighbours.

    Reports WHO IS ADJACENT TO WHOM (pure geometry: parts within a contact tolerance).
    It does NOT compute how load flows, how parts are constrained/mated, or why they're
    arranged this way — force flow, constraint graph, and design intent are Professional.

    inputs (either):
      - edges: [{a, b}]                  caller-supplied adjacency (e.g. from STEP geometry
                                         or a SolidWorks walk); names or indices
      - names: [..]                      optional labels for indices
    Output: neighbour list per node + a Mermaid graph.
    """
    edges = inp.get("edges")
    if edges is None:
        return {"status": "needs_input", "needs": ["inputs.edges"],
                "note": "Provide adjacency edges [{a,b}] (parts that touch/are near). "
                        "Force flow / constraints / intent are Professional."}
    names = inp.get("names")

    def label(x):
        if names and isinstance(x, int) and 0 <= x < len(names):
            return names[x]
        return str(x)

    neigh = {}
    norm_edges = []
    for e in edges:
        a, b = label(e.get("a")), label(e.get("b"))
        if a == b:
            continue
        norm_edges.append((a, b))
        neigh.setdefault(a, set()).add(b)
        neigh.setdefault(b, set()).add(a)

    # Mermaid undirected graph
    lines = ["graph LR"]
    seen = set()
    for a, b in norm_edges:
        key = tuple(sorted((a, b)))
        if key in seen:
            continue
        seen.add(key)
        sa = a.replace('"', "'"); sb = b.replace('"', "'")
        lines.append(f'  {abs(hash(a))%100000}["{sa}"] --- {abs(hash(b))%100000}["{sb}"]')
    mermaid = "\n".join(lines)

    degree = {k: len(v) for k, v in neigh.items()}
    hubs = sorted(degree.items(), key=lambda kv: -kv[1])[:5]
    return {"status": "ok", "results": {
        "node_count": len(neigh),
        "edge_count": len(seen),
        "neighbours": {k: sorted(v) for k, v in neigh.items()},
        "most_connected": [{"part": k, "neighbours": d} for k, d in hubs],
        "mermaid": mermaid,
        "note": "Geometric adjacency only (who touches whom). Force-flow, constraint "
                "graph, and design intent are Professional."}}


DISPATCH.update({"adjacency_graph": adjacency_graph})
