"""Enterprise-core bridge (Community Edition).

The Community Edition is fully functional on its own for CAD understanding,
assembly diagnostics, and basic reporting. Advanced capabilities — DFM/DFA rule
engines, automatic load-face / constraint / mesh selection, FEA/fatigue/modal
solving, optimization, and the agent reviewer — live in the closed-source
`mechanical_ai_core` package (Professional Edition).

This bridge tries to import that package. If present, the command delegates to it.
If absent, the command returns a clean `enterprise_required` result that tells the
user which feature needs the upgrade — it never crashes and never fakes output.

To enable Professional features, install the core package (license required); it
registers itself as an importable module named `mechanical_ai_core`.
"""
import importlib

INFO_URL = "https://github.com/almightyshui/Mechanical-AI-Skill#editions"

# capability -> the enterprise feature group it belongs to (for the upgrade message)
ENTERPRISE_FEATURES = {
    "dfm_check": "Advanced DFM rule engine",
    "dfa_check": "Advanced DFA rule engine",
    "static_strength": "Automated FEA (auto load-face / mesh + solver)",
    "modal": "Automated modal analysis",
    "thermal": "Automated thermal analysis",
    "fatigue": "Fatigue analysis engine",
    "cfd": "Automated CFD",
    "motion": "Kinematics / dynamics engine",
    "topology_optimize": "Optimization engine",
    "parametric_lightweight": "Optimization engine",
    "design_review": "Automated design review (agent)",
    "risk_score": "Risk scoring engine",
    "procurement_list": "Procurement / costing engine",
    "advanced_report": "Professional report templates",
}


def core_available():
    try:
        importlib.import_module("mechanical_ai_core")
        return True
    except Exception:
        return False


def get_core():
    """Return the core module, or None if not installed."""
    try:
        return importlib.import_module("mechanical_ai_core")
    except Exception:
        return None


def enterprise_required(C, stage, capability, extra_caveats=None):
    """Build a standard enterprise_required contract result."""
    feature = ENTERPRISE_FEATURES.get(capability, "a Professional Edition feature")
    caveats = [
        f"'{capability}' requires the Professional Edition ({feature}), which is not "
        "installed. The Community Edition covers CAD understanding, assembly "
        "diagnostics, and basic reporting.",
    ]
    if extra_caveats:
        caveats += extra_caveats
    return C.result(
        "enterprise_required", stage, capability,
        caveats=caveats,
        upgrade={"edition": "Professional", "feature": feature, "info_url": INFO_URL},
    )


def delegate(C, task, stage, capability, fn_name):
    """Delegate a capability to the core package if present, else enterprise_required.

    The core package is expected to expose a function `fn_name(task) -> dict` that
    returns a contract-shaped result dict.
    """
    core = get_core()
    if core is None:
        return enterprise_required(C, stage, capability)
    fn = getattr(core, fn_name, None)
    if fn is None:
        return enterprise_required(
            C, stage, capability,
            extra_caveats=[f"core package present but missing '{fn_name}'; update it."])
    try:
        return fn(task)
    except Exception as e:
        return C.result("failed", stage, capability,
                        caveats=[f"core '{fn_name}' error: {e}"])
