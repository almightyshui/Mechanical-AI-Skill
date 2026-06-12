#!/usr/bin/env bash
# Community Edition (freemium) demo: real free-tier analysis + graceful gating.
# No SolidWorks and no commercial solver needed — the free analyses are analytical.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; SKILL="$(dirname "$HERE")"; SCR="$SKILL/scripts"
WORK="$(mktemp -d)"; PY="${PYTHON:-python3}"
hr(){ printf '\n\033[1m%s\033[0m\n' "------------------------------------------------------------"; }
say(){ printf '\033[36m%s\033[0m\n' "$*"; }
show(){ "$PY" - "$1" <<'PYEOF'
import json,sys
d=json.load(open(sys.argv[1]))
print(f"  status      : {d['status']}")
if d.get('results'):     print(f"  results     : {json.dumps(d['results'])[:240]}")
if d.get('needs_input'): print(f"  needs_input : {d['needs_input']}")
if d.get('upgrade'):     print(f"  upgrade     : {d['upgrade'].get('feature')}")
if d.get('caveats'):     print(f"  caveat      : {d['caveats'][-1][:110]}")
PYEOF
}

echo "demo workdir: $WORK"
bash "$SCR/detect_solvers.sh" 2>/dev/null | sed 's/^/  /'

hr; echo "FREE — \"generate a BOM\" (open)"
echo '{"stage":"0.1","capability":"generate_bom","model":{"path":"C:/work/gripper.SLDASM","type":"assembly"},"units":"SI_mm_t","workdir":"'"$WORK"'"}' > "$WORK/bom.json"
$PY "$SCR/sw_understand.py" --task "$WORK/bom.json" --out "$WORK/r.json" >/dev/null 2>&1; show "$WORK/r.json"

hr; echo "FREE — \"what's the safety factor?\" (single-load static, REAL result)"
say 'User: "500 N on the end of this 100mm steel cantilever, 20x20mm. Safe?"'
cat > "$WORK/s.json" <<JSON
{"stage":"2.0","capability":"static_strength","model":{"path":"C:/work/beam.SLDPRT","type":"part"},"units":"SI_m_kg_s",
 "inputs":{"case":"cantilever_end_load","length":0.1,"loads":[{"value_N":500}],
   "section":{"shape":"rect","width":0.02,"height":0.02},"material":{"E":200e9,"yield":250e6}}}
JSON
$PY "$SCR/run_analysis.py" --task "$WORK/s.json" --out "$WORK/r.json" >/dev/null 2>&1; show "$WORK/r.json"

hr; echo "FREE — \"will it resonate?\" (first 3 modes, REAL frequencies)"
cat > "$WORK/m.json" <<JSON
{"stage":"2.0","capability":"modal","model":{"path":"C:/work/arm.SLDPRT","type":"part"},"units":"SI_m_kg_s",
 "inputs":{"mounting":"cantilever","length":0.1,"n_modes":3,"excitation_hz":1700,
   "section":{"shape":"rect","width":0.02,"height":0.02},"material":{"E":200e9,"rho":7850}}}
JSON
$PY "$SCR/run_analysis.py" --task "$WORK/m.json" --out "$WORK/r.json" >/dev/null 2>&1; show "$WORK/r.json"

hr; echo "FREE — \"is it machinable?\" (basic DFM, REAL findings)"
cat > "$WORK/d.json" <<JSON
{"stage":"1.1","capability":"dfm_check","model":{"path":"C:/work/bracket.SLDPRT","type":"part"},"units":"SI_mm_t",
 "inputs":{"features":[{"type":"hole","name":"h1","depth":60,"diameter":5},{"type":"wall","name":"w1","thickness":0.8}]}}
JSON
$PY "$SCR/sw_dfm.py" --task "$WORK/d.json" --out "$WORK/r.json" >/dev/null 2>&1; show "$WORK/r.json"

hr; echo "FREE — \"give me a risk score\" (simple 0-100 roll-up)"
cat > "$WORK/rs.json" <<JSON
{"stage":"review","capability":"risk_score","model":{"path":"C:/work/arm.step","type":"step"},"units":"SI_mm_t",
 "inputs":{"signals":{"interferences":0,"dfm_blockers":0,"dfm_risks":2,"min_safety_factor":6.67,"resonance_risk":true}}}
JSON
$PY "$SCR/design_review.py" --task "$WORK/rs.json" --out "$WORK/r.json" >/dev/null 2>&1; show "$WORK/r.json"

hr; echo "GATED — beyond the free line degrades gracefully"
say 'User: "Run a fatigue analysis."  → Professional'
echo '{"stage":"2.0","capability":"fatigue","model":{"path":"C:/work/shaft.SLDPRT","type":"part"},"units":"SI_mm_t","inputs":{}}' > "$WORK/f.json"
$PY "$SCR/run_analysis.py" --task "$WORK/f.json" --out "$WORK/r.json" >/dev/null 2>&1; show "$WORK/r.json"
say 'User: "Modal, give me 10 modes."  → free caps at 3'
echo '{"stage":"2.0","capability":"modal","model":{"path":"C:/work/arm.SLDPRT","type":"part"},"units":"SI_m_kg_s","inputs":{"n_modes":10,"length":0.1,"section":{"shape":"rect","width":0.02,"height":0.02},"material":{"E":200e9,"rho":7850}}}' > "$WORK/m10.json"
$PY "$SCR/run_analysis.py" --task "$WORK/m10.json" --out "$WORK/r.json" >/dev/null 2>&1; show "$WORK/r.json"

hr; echo "SUMMARY (machine-readable — what an agent would report)"
"$PY" - <<'PYEOF'
import json
# A compact one-glance summary of a review pass (representative values).
print(json.dumps({
    "status": "ok",
    "bom_unique_parts": 27,
    "bom_total_instances": 67,
    "interference_count": 2,
    "dfm_findings": {"blocker": 0, "risk": 2},
    "static_safety_factor": 5.67,
    "risk_score": 71
}, indent=2))
PYEOF

hr; echo "DONE — free tier returns REAL analysis; beyond it, enterprise_required (graceful)."
echo "Install the licensed mechanical_ai_core to unlock full FE, fatigue, optimization, etc."
