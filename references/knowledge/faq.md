# Knowledge base — FAQ & troubleshooting

Symptom → likely cause → fix, for the problems users actually hit. Offline. When the skill returns `failed` or `deck_only`, or a result looks wrong, the agent consults this to give an actionable next step instead of a dead end.

## Solver won't run / setup
**"No solver detected" / status deck_only.**
Cause: ANSYS/Abaqus/etc. not on PATH, or this is a headless/sandbox box. Fix: run `scripts/detect_solvers.sh`; put the solver's bin dir on PATH or pass `--exe`. If truly unavailable, use the generated deck/macro on a machine that has the solver — `deck_only` is expected, not an error.

**"License denied / license server" early exit.**
Cause: no free license seat or wrong license env. Fix: check `ANSYSLMD_LICENSE_FILE` / `ABAQUSLM_LICENSE_FILE` / `LM_LICENSE_FILE`; free a seat; confirm the server is reachable.

**SolidWorks step returns deck_only on Linux.**
Cause: SolidWorks is Windows-only and needs `pywin32`. Fix: run the generated `.swp` macro in SolidWorks, or run the skill on a Windows host with a licensed SolidWorks session.

## Structural (strength) results look wrong
**"Negative pivot" / "numerical singularity" / "rigid body motion" → solve fails.**
Cause: model not fully constrained (a free rigid-body DOF). Fix: ensure all 6 DOF are removed; add the missing fixture; check that bonded contact actually connects the parts. This is the #1 static-FEA failure.

**Peak stress is absurdly high (e.g. >> yield at a sharp corner).**
Cause: **stress singularity** at a sharp re-entrant corner / point load / point constraint — stress there rises without bound as the mesh refines and never converges. Fix: add a fillet (real parts have one), distribute the load/constraint over an area, or read stress a small distance away. Don't report a singular peak as the safety factor.

**Results change a lot when I refine the mesh.**
Cause: mesh not converged. Fix: run a **mesh convergence study** — refine until the quantity of interest changes < ~5%. Refine locally at stress concentrations, not globally. Report the converged value, not the first run.

**Displacement looks right but stress seems low/high.**
Cause: element order. Linear (first-order) elements are too stiff in bending and under-report stress; use quadratic (SOLID186 / C3D20 / C3D10) or a finer mesh for bending-dominated parts. Reduced-integration linear elements (C3D8R) can hourglass — check.

**Everything is 1000× or 1e6× off.**
Cause: **unit inconsistency** — the #1 silent error. Fix: re-confirm the unit system (`../units.md`). In the mm-tonne system steel density is 7.85e-9 t/mm³ (not 7850) and E = 200000 MPa; mixing mm geometry with Pa stresses is the classic mistake.

## Modal
**First six frequencies are ~0 Hz.**
Cause: free-free model — those are rigid-body modes. Either intended (unconstrained part) or you forgot the mounting constraints. Confirm which mounting condition is physical.

**Frequencies seem too high / too low.**
Cause: missing or wrong density (too high), or over-stiff constraints (ENCASTRE is stiffer than a real bolted joint → frequencies too high). Fix: verify ρ; model the mounting compliance more realistically if margins are tight.

## Thermal
**Temperatures unrealistic.**
Cause: wrong/guessed convection coefficient h, or missing heat path, or unit mix (W vs mW in mm-system thermal). Fix: state and sanity-check h (see ranges in `formulas.md`); prefer SI(m,kg,s) for thermal to avoid mm-system unit traps; consider CFD if cooling detail drives the answer.

## CFD
**"Divergence detected" / floating-point exception / residuals climb.**
Cause: too-large initial step/Courant number, poor mesh (bad y+, skew), or wrong BC. Fix: lower under-relaxation / time step, improve boundary-layer mesh, start from a lower-Re or first-order scheme then ramp up, double-check inlet/outlet definitions.

**Residuals dropped but the answer feels off.**
Cause: converged ≠ mesh-independent ≠ validated. Fix: confirm monitored quantities (drag, Δp) are flat AND do a mesh-independence check; pick an appropriate turbulence model; validate against data if it matters (ASME V&V 20 — see `standards.md`).

## Motion / dynamics
**"Redundant constraints" warning, or wrong reaction forces.**
Cause: over-defined assembly (redundant mates) — the solver can't distribute reactions uniquely. Fix: remove redundant mates / use a proper joint set so the mechanism has the intended DOF (Grübler count).

## Optimization
**Optimized part is lighter but fails when I re-check it.**
Cause: a load case was omitted from the optimization, or the raw topology result was trusted without rebuilding/re-validating. Fix: include all governing load cases; always rebuild to clean CAD and re-run strength + fatigue. Never report mass savings without confirming the safety constraint still holds.

## "Should I trust this number?"
Default answer the agent should give: an FE/CFD result is trustworthy only after (1) units confirmed, (2) constraints/BCs physical, (3) mesh convergence checked, (4) the right criterion applied, and (5) for anything safety-critical, comparison to test data or the governing code. Surface which of these have/haven't been done in the `caveats`.
