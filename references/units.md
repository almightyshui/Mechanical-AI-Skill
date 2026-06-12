# Consistent unit systems

FE solvers (ANSYS APDL, Abaqus) carry **no units** — they compute on raw numbers. You must feed one self-consistent system. Mixing (e.g. mm for length but N/m² for stress) silently produces results off by orders of magnitude. **Confirm the system with the user before solving and record it in the report.**

A system is consistent if, given the chosen length, mass, and time units, all derived units follow. Two standard choices:

## SI (m, kg, s)  — "everything in base SI"
| Quantity | Unit | Note |
|---|---|---|
| Length | m | |
| Mass | kg | |
| Time | s | |
| Force | N | |
| Stress / pressure / E | Pa (N/m²) | 1 MPa = 1e6 |
| Density | kg/m³ | steel 7850 |
| Energy | J | |
| Temperature | K or °C | be consistent across the model |
| Conductivity k | W/(m·K) | |
| Convection h | W/(m²·K) | |

This is the cleanest. Geometry in meters → small numbers (a 10 mm feature = 0.01).

## SI (mm, t, s)  — "the CAD-friendly mm system" (very common in industry)
Because CAD is usually in mm, this avoids re-scaling geometry. The catch: **mass unit must be the tonne (10³ kg)** for consistency.
| Quantity | Unit | Note |
|---|---|---|
| Length | mm | |
| Mass | t (tonne) | |
| Time | s | |
| Force | N | |
| Stress / E | MPa (N/mm²) | steel E = 200000 |
| Density | t/mm³ | steel = 7.85e-9 |
| Energy | mJ | |
| Conductivity k | mW/(mm·K) = W/(m·K)×1 → enter as N/(s·K)... | thermal in mm-system is error-prone; prefer SI(m) for thermal |

Density gotcha: steel is **7.85e-9 t/mm³**, NOT 7850. Modal/gravity results are wrong if you forget this.

## US customary (in, lbf, s) — if the user insists
Use the (in, lbf·s²/in [=slinch], s) system: E_steel ≈ 29e6 psi, density ≈ 7.34e-4 slinch/in³. Easy to get wrong; steer the user to SI if possible.

## How to pick
- Geometry already in mm and structural-only → mm-tonne system (no rescale), remember ρ in t/mm³.
- Any thermal or coupled analysis → prefer SI(m, kg, s); the mm-system thermal units are a frequent error source.
- When importing a mesh, check its coordinate magnitudes: nodes around 100 → likely mm; around 0.1 → likely m. Confirm with the user, don't assume.

## Self-check before solving
State to the user, e.g.: "Using SI mm-tonne: lengths mm, E=200000 MPa, ρ=7.85e-9 t/mm³, forces N, stress out in MPa." Getting explicit agreement here prevents the most common class of garbage results.
