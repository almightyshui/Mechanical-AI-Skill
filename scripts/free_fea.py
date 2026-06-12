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

    inputs.signals: {interferences:int, dfm_blockers:int, dfm_risks:int,
                     min_safety_factor:float|None, resonance_risk:bool|None}
    Produces a 0-100 score + High/Med/Low issue buckets. Advanced scoring
    (weighted by criticality, code compliance, full physics) is Professional.
    """
    s = inp.get("signals")
    if s is None:
        return {"status": "needs_input", "needs": ["inputs.signals"],
                "note": "Provide signals from the free checks {interferences, dfm_blockers, "
                        "dfm_risks, min_safety_factor, resonance_risk}. Advanced scoring is Professional."}
    score = 100
    high, med, low = [], [], []
    if s.get("interferences"):
        score -= 25; high.append(f"{s['interferences']} interference(s) detected")
    if s.get("dfm_blockers"):
        score -= 15; high.append(f"{s['dfm_blockers']} DFM blocker(s)")
    sf = s.get("min_safety_factor")
    if sf is not None:
        if sf < 1.0:
            score -= 30; high.append(f"safety factor {sf} < 1 (predicted to yield)")
        elif sf < 1.5:
            score -= 12; med.append(f"safety factor {sf} below typical 1.5 target")
    if s.get("resonance_risk"):
        score -= 12; med.append("1st mode within 20% of excitation (resonance risk)")
    if s.get("dfm_risks"):
        score -= min(10, 2*s["dfm_risks"]); low.append(f"{s['dfm_risks']} DFM cost/risk item(s)")
    score = max(0, min(100, score))
    return {"status": "ok", "results": {"overall_score": score,
            "high": high, "med": med, "low": low, "scoring": "simple",
            "note": "Simple risk score from free-tier checks; advanced scoring is Professional."}}


DISPATCH = {"static_strength": static_strength, "modal": modal,
            "dfm_check": dfm_check, "risk_score": risk_score}
