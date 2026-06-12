"""Open BOM helper: component list -> bill of materials, with standard-part flags.

Pure, dependency-free logic so the community can read and extend it. The SolidWorks
COM walk that produces `components` lives in the command scripts; this turns it into
a tidy BOM. Heuristic standard-part matching is deliberately simple here — the
*advanced* engineering rule library is Professional.
"""
import re

STD_PATTERNS = [
    (r"\bM\d+(\.\d+)?[xX]\d+\b", "metric_screw"),
    (r"\b(ISO|DIN|GB/?T?|ANSI)\s?\d+\b", "standard_ref"),
    (r"\b(hex|socket|cap|pan|flat|countersunk)\s*(head)?\s*(screw|bolt)\b", "screw"),
    (r"\b(washer|nut|lock\s*nut)\b", "fastener"),
    (r"\b(bearing|6\d{3}[a-z]{0,2})\b", "bearing"),
    (r"\b(o-?ring|seal|gasket|dowel|pin|circlip|spring)\b", "standard_component"),
]

def classify(name):
    nm = (name or "").lower()
    for pat, kind in STD_PATTERNS:
        if re.search(pat, nm, re.I):
            return kind
    return None

def build_bom(components):
    """components: list of {name, path?} -> tally into a BOM list."""
    tally = {}
    for c in components:
        base = c.get("name", "?")
        tally.setdefault(base, {"part": base, "qty": 0})
        tally[base]["qty"] += 1
    bom = []
    for i, it in enumerate(sorted(tally.values(), key=lambda x: -x["qty"]), 1):
        bom.append({"item": i, "part": it["part"], "qty": it["qty"],
                    "standard_part": classify(it["part"])})
    return bom
