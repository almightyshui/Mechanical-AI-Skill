"""Freemium tier guard (Community Edition).

Decides, per task, whether a capability falls inside the FREE tier (runs locally
in this open repo) or requires the PROFESSIONAL core. Keeps the boundary in ONE
place so it's auditable and hard to get wrong.

Free tier (this repo computes real results):
  - static_strength : single load case, single fixture set, no contact/nonlinearity
  - modal           : first 3 modes max
  - dfm_check       : basic rule set (a handful of geometric rules)
  - risk_score      : simple weighted score from free-tier checks

Everything else -> Professional:
  - >1 load case, contact, nonlinear, auto load/constraint identification
  - modal beyond 3 modes
  - thermal, cfd, fatigue, motion, optimization
  - advanced DFM/DFA, advanced risk scoring, design review, procurement, advanced report
"""

FREE_CAPS = {"static_strength", "modal", "dfm_check", "risk_score"}
PRO_ONLY_CAPS = {"thermal", "cfd", "fatigue", "motion",
                 "topology_optimize", "parametric_lightweight",
                 "dfa_check", "design_review", "procurement_list"}

MAX_FREE_MODES = 3


def free_tier_check(capability, task):
    """Return (allowed_in_free, reason_if_not).

    allowed_in_free=True  -> compute locally (free).
    allowed_in_free=False -> caller returns enterprise_required with `reason`.
    """
    inp = (task or {}).get("inputs", {}) or {}

    if capability in PRO_ONLY_CAPS:
        return False, f"'{capability}' is a Professional capability"

    if capability == "static_strength":
        loads = inp.get("loads", [])
        # auto load/fixture identification is Professional
        if any(isinstance(l, dict) and l.get("face") == "auto" for l in loads):
            return False, "automatic load-face identification (Professional)"
        if "auto" in (inp.get("fixtures", []) or []):
            return False, "automatic fixture identification (Professional)"
        if len(loads) > 1:
            return False, "multiple load cases (free tier is single load case)"
        if inp.get("contact") or inp.get("nonlinear") or inp.get("nlgeom"):
            return False, "contact / nonlinear analysis (Professional)"
        return True, None

    if capability == "modal":
        n = int(inp.get("n_modes", 3) or 3)
        if n > MAX_FREE_MODES:
            return False, f"modal beyond first {MAX_FREE_MODES} modes (free tier caps at {MAX_FREE_MODES})"
        if inp.get("prestress"):
            return False, "prestressed modal (Professional)"
        return True, None

    if capability == "dfm_check":
        if inp.get("advanced") or inp.get("ruleset") in ("enterprise", "advanced"):
            return False, "advanced DFM rule library (Professional)"
        return True, None

    if capability == "risk_score":
        if inp.get("advanced"):
            return False, "advanced risk scoring (Professional)"
        return True, None

    # unknown capability is not a free-tier grant
    return False, f"'{capability}' not available in the free tier"
