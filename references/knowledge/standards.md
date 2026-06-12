# Knowledge base — engineering standards & codes

A map of the standards an engineer reaches for, what each covers, and how it bears on a simulation. **The skill does not reproduce copyrighted standard text.** It points to the right standard and clause area so the agent can tell the user which code governs and what to look up; the user must consult the actual standard for binding values. When a project names a governing code, that code overrides the generic defaults in `formulas.md`.

## How to use
- Identify the user's domain (pressure vessel, structural steel, machinery, lifting, aerospace, automotive, additive) → name the likely governing standard(s) below.
- Tell the user the standard + the relevant part/clause to check; do not quote clause text verbatim or invent specific allowable numbers from a standard — direct them to the source.
- If the user states allowable values or a code edition, use those over any default.

## Structural / mechanical FEA & strength
- **ASME BPVC** (Boiler & Pressure Vessel Code): Section VIII Div 2 Part 5 covers *Design by Analysis* — elastic stress linearization, membrane/bending categorization, and protection against plastic collapse, local failure, buckling, and fatigue. The reference for FE-based pressure-equipment qualification (US).
- **EN 13445 / PED** — European pressure vessels; Annex on Design by Analysis (DBA), direct-route and stress-categorization route.
- **Eurocode 3 (EN 1993)** — steel structures; buckling, member/connection checks, partial safety factors γ_M.
- **AISC 360** — US structural steel (LRFD/ASD).
- **GB 150 / GB/T 700 / GB 50017** — Chinese pressure-vessel and structural-steel codes (if the user is in CN).
- **Shigley / Roark's Formulas for Stress and Strain** — not standards but the standard *references* for closed-form checks and stress concentration factors.

## Fatigue & durability
- **ASME BPVC VIII-2 Part 5** fatigue (smooth-bar and welded-joint curves; the welded curves use structural-stress / mesh-insensitive methods).
- **Eurocode 3 part 1-9 (EN 1993-1-9)** — fatigue of steel structures; detail categories (FAT classes) and S-N curves for welds.
- **IIW recommendations** (Hobbacher) — weld fatigue: nominal, hot-spot (structural) stress, and effective notch stress approaches. Tell the user which method their FE post-processing implies.
- **FKM Guideline** (Germany) — comprehensive analytical strength/fatigue assessment from FE stresses; widely used in machine design.
- **ASTM E1049** — cycle counting (rainflow) for variable-amplitude histories feeding Miner's rule.

## Welds, GD&T, materials
- **AWS D1.1** — structural welding (US); weld quality affecting fatigue class.
- **ISO 5817** — weld quality levels (B/C/D) which map to fatigue detail categories.
- **ASME Y14.5 / ISO 1101** — GD&T; relevant when interference/clearance checks (stage 1.0) must respect tolerances rather than nominal geometry.
- **ASTM/EN material specs** (e.g. ASTM A36, A572; EN 10025) — the source of certified yield/ultimate values that should replace the nominal data in `../materials.md`.

## Vibration / modal
- **ISO 10816 / ISO 20816** — mechanical vibration evaluation by measurement on machines (acceptance zones A–D); useful to frame whether a predicted response is acceptable.
- **API 617/684** — rotordynamics for turbomachinery (critical speeds, separation margins) if the user is in that domain.

## Thermal / electronics
- **JEDEC JESD51** — standardized thermal measurement/junction-to-ambient definitions for semiconductor packages (frames what a chip "θ_JA" means in a thermal model).
- **IEC 60034** — rotating electrical machines; insulation thermal classes (B/F/H limits referenced in `formulas.md`).

## CFD / aero
- No single binding "CFD code"; verification & validation guidance: **ASME V&V 20** (V&V in CFD and heat transfer) and the AIAA CFD V&V guides. Cite these when telling the user a CFD result needs mesh-independence + validation before it's trusted.

## Additive / lightweighted parts
- **ISO/ASTM 52900 series** — additive manufacturing terminology and process categories; relevant after topology optimization when the organic result is meant for printing (affects min feature size, anisotropy to feed back into a re-validation run).

## Reporting etiquette
When a standard governs, the agent should say e.g.: "For pressure-vessel qualification this would fall under ASME VIII-2 Part 5 Design-by-Analysis (stress linearization) — confirm the edition and consult it for allowable values," rather than asserting a pass under a code the skill hasn't actually applied. Never fabricate clause numbers or allowable values; if unsure of the exact clause, name the standard and section area only, or use the online lookup in `literature.md` to find the current reference.
