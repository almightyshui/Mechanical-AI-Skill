# Material property library

Typical room-temperature engineering values. **Always tell the user the source and let them confirm or override** — real designs should use the certified datasheet for the actual alloy/temper. These are textbook nominal values for getting a model running, not certified design data.

Units below: E in Pa, ρ in kg/m³, yield in Pa, k in W/(m·K), α in 1/K, cp in J/(kg·K).

| Material | E | ν | ρ | Yield | Ultimate | k | α | cp |
|---|---|---|---|---|---|---|---|---|
| Structural steel (mild) | 200e9 | 0.30 | 7850 | 250e6 | 400e6 | 60.5 | 1.2e-5 | 460 |
| Stainless 304 | 193e9 | 0.29 | 8000 | 215e6 | 505e6 | 16.2 | 1.7e-5 | 500 |
| Aluminum 6061-T6 | 68.9e9 | 0.33 | 2700 | 276e6 | 310e6 | 167 | 2.36e-5 | 896 |
| Aluminum 7075-T6 | 71.7e9 | 0.33 | 2810 | 503e6 | 572e6 | 130 | 2.36e-5 | 960 |
| Titanium Ti-6Al-4V | 113.8e9 | 0.34 | 4430 | 880e6 | 950e6 | 6.7 | 8.6e-6 | 526 |
| Copper (annealed) | 110e9 | 0.34 | 8960 | 70e6 | 220e6 | 401 | 1.7e-5 | 385 |
| Brass (C26000) | 110e9 | 0.34 | 8530 | 200e6 | 360e6 | 120 | 2.0e-5 | 380 |
| Cast iron (gray) | 100e9 | 0.26 | 7200 | — | 240e6 | 53 | 1.1e-5 | 490 |
| ABS plastic | 2.3e9 | 0.35 | 1050 | 40e6 | 45e6 | 0.17 | 9.0e-5 | 1300 |
| PLA | 3.5e9 | 0.36 | 1240 | 50e6 | 60e6 | 0.13 | 8.0e-5 | 1800 |
| Nylon (PA6) | 2.0e9 | 0.39 | 1140 | 45e6 | 75e6 | 0.25 | 8.0e-5 | 1700 |

Notes:
- Cast iron is brittle — compare against ultimate, not yield; von Mises is a poor failure criterion for it (consider max-principal).
- Polymer properties are strongly temperature- and rate-dependent; these are coarse.
- For temperature-dependent runs, ask the user for property-vs-temperature tables; the single values above are room-temperature only.
- When you use any of these, state in the report: "Material data: nominal textbook values for <material> (not certified) — confirm against your datasheet."

## Fluid properties (for CFD, family 5)
Room-temperature nominal values. Confirm with the user; properties vary with temperature/pressure.

| Fluid | density ρ [kg/m³] | dynamic viscosity μ [Pa·s] | note |
|---|---|---|---|
| Air (20°C, 1 atm) | 1.204 | 1.81e-5 | incompressible if Mach < ~0.3 |
| Water (20°C) | 998 | 1.00e-3 | |
| Engine oil (SAE 30, 20°C) | 880 | ~0.29 | strongly temp-dependent |
| Nitrogen (20°C) | 1.16 | 1.76e-5 | |

Reynolds number Re = ρ·V·L / μ. Use it to choose laminar (low Re) vs turbulent (high Re, pick a turbulence model). For internal pipe flow, transition is around Re ≈ 2300; for external flow it depends on geometry.
