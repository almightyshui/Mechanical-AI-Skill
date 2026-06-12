# Knowledge base — engineering formulas & criteria

Quick-reference formulas, failure criteria, and rule-of-thumb thresholds the agent uses when **interpreting** simulation results. Offline; cite the standard/textbook source shown so the report can attribute it. These are general engineering references, not a substitute for the governing code on a specific project.

## Safety factor (static strength)
- Definition: SF = strength / peak stress. Use **yield** strength for ductile metals (onset of permanent deformation), **ultimate** for brittle materials (cast iron, ceramics) — they fail without yielding.
  - `SF = σ_yield / σ_von_Mises` (ductile)   `SF = σ_ult / σ_max_principal` (brittle)
- Typical minimum SF targets (the *user's* design code governs; these are common defaults):
  - 1.25–1.5: well-characterized loads & materials, ductile, non-critical (ASME-style).
  - 2–3: ordinary machine design with uncertainty (Shigley typical range).
  - 4+: brittle materials, shock/impact, or life-safety. Source: Shigley's *Mechanical Engineering Design*.
- Note: a linear-elastic FE peak above yield doesn't mean fracture — it means local yielding; report it as "predicted to yield locally," and consider an elastic-plastic run if the user needs margin past yield.

## Yield / failure criteria (which stress to compare)
- **von Mises (distortion energy)** — default for ductile metals. `σ_vm = sqrt(½[(σ1−σ2)²+(σ2−σ3)²+(σ3−σ1)²])`.
- **Tresca (max shear)** — more conservative than von Mises (~15% at worst); some pressure-vessel codes use it.
- **Max normal/principal stress** — for brittle materials.
- **Mohr–Coulomb / modified Mohr** — brittle with different tension/compression strength.
Source: Shigley ch. 5; Boresi, *Advanced Mechanics of Materials*.

## Fatigue (cycles to failure)
- **Endurance limit** (steels) ≈ 0.5·σ_ult (for σ_ult ≤ ~1400 MPa), capped ~700 MPa. Aluminum has **no** true endurance limit — use fatigue strength at 5×10⁸ cycles. Source: Shigley ch. 6.
- **Marin factors** (correct the lab endurance limit to the real part): `σ_e = k_a k_b k_c k_d k_e · σ_e' ` (surface, size, load, temperature, reliability). Surface finish k_a is usually the biggest hit.
- **Mean-stress corrections** (combine alternating σ_a and mean σ_m):
  - Goodman (common, slightly conservative): `σ_a/σ_e + σ_m/σ_ult = 1/SF`
  - Soderberg (most conservative, uses yield): `σ_a/σ_e + σ_m/σ_yield = 1/SF`
  - Gerber (parabola, less conservative): `σ_a/σ_e + (σ_m/σ_ult)² = 1/SF`
- **Basquin (S-N)**: `σ_a = σ_f'(2N)^b`. **Miner's rule** (variable amplitude): `Σ n_i/N_i = D`; fail when D ≥ 1.
- Sensitivity warning: fatigue life ∝ a high power of stress — a ~10% stress error can shift life 2–3×. The underlying stress mesh must be converged. Source: Stephens, *Metal Fatigue in Engineering*.

## Modal / vibration (resonance)
- Excitation from rotating machinery: `f_exc [Hz] = RPM / 60`; add harmonics (2×, 3×) and blade/pole-pass = (blades or poles)·RPM/60.
- **Frequency separation rule of thumb**: keep the structure's natural frequency at least **±20–30%** from any strong excitation; some specs require a factor of 1.5–2× separation. Source: Blevins, *Formulas for Natural Frequency and Mode Shape*.
- Single-DOF natural frequency: `f_n = (1/2π)·sqrt(k/m)`. Cantilever beam 1st mode: `f_n = (1.875²/2π)·sqrt(EI/(ρA L⁴))`.
- Modal analysis is undamped/linear — gives natural frequencies, not response amplitude. Damping reduces amplitude at resonance (`Q ≈ 1/2ζ`) but not the frequencies.

## Thermal
- Conduction (Fourier): `q = -k·A·dT/dx`. Convection (Newton): `q = h·A·(T_s − T_∞)`.
- Convection coefficient h ranges [W/m²K]: natural air 5–25; forced air 25–250; forced liquid 100–20,000; boiling 2,500–100,000. The assumed h is usually the dominant uncertainty in a non-CFD thermal model — state it. Source: Incropera, *Fundamentals of Heat and Mass Transfer*.
- Thermal stress (fully constrained bar): `σ = E·α·ΔT`. Free expansion: `ΔL = α·L·ΔT`.
- Common temperature limits to compare against: motor insulation Class B 130°C / F 155°C / H 180°C; Li-ion cell typically ≤ 60°C; silicon junction often ≤ 125–150°C (check the datasheet). 

## CFD / fluid
- Reynolds number: `Re = ρ·V·L/μ`. Pipe transition ~2300; external flow depends on geometry.
- Drag: `F_d = ½·ρ·V²·C_d·A`. Pressure drop / dynamic pressure: `q = ½ρV²`.
- Turbulence model picks: k-ω SST (general default, good near walls/separation), k-ε (robust, free-shear), laminar (low Re). Wall functions assume a y+ band — check it. Source: Versteeg & Malalasekera, *An Introduction to CFD*.

## Topology optimization
- Objective usually = minimize compliance (maximize stiffness) at a target volume fraction, OR minimize mass subject to a stress/displacement constraint. Always pair the mass target with a constraint that must hold (min SF or max displacement).
- The result is a concept (density field) — rebuild to CAD and re-validate with a normal strength + fatigue run; the smoothed shape's peak stress differs from the raw field. Source: Bendsøe & Sigmund, *Topology Optimization*.

## How the agent should use this
When reporting a result, pull the relevant formula/threshold here, compute the judgment (SF, resonance margin, life margin, temperature margin), and attribute the criterion ("per Goodman", "Shigley's typical SF range"). If the user is bound by a specific code, defer to `standards.md` and the user's code rather than these generic defaults.
