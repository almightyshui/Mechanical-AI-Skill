#!/usr/bin/env bash
# Detect what's available for the Community Edition (SolidWorks + the Professional core).
set -u
echo "=== mechanical-ai-skill (Community) environment ==="
echo
echo "--- SolidWorks (for live CAD operations) ---"
for d in "/mnt/c/Program Files/SOLIDWORKS Corp" "/mnt/c/Program Files/SolidWorks Corp"; do
  [ -d "$d" ] && echo "  install dir: $d"
done
python -c "import win32com.client" 2>/dev/null && echo "  pywin32: available (live SolidWorks API)" \
  || echo "  pywin32: not installed — open commands return deck_only (macro) instead"
[ "$(uname -s 2>/dev/null)" = "Linux" ] && echo "  note: SolidWorks is Windows-only; on Linux this is macro-only."
echo
echo "--- Professional core (mechanical_ai_core) ---"
python -c "import mechanical_ai_core" 2>/dev/null \
  && echo "  Professional core: INSTALLED — DFM/FEA/optimization/review enabled" \
  || echo "  Professional core: not installed — those commands return enterprise_required"
echo
echo ">> Community features (BOM, diagnostics, report) work regardless of the above."
