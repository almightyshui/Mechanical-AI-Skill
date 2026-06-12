# Case Study — Robotic Welding Cell (real STEP, 39 MB)

A real-world test: a 39 MB SolidWorks-exported STEP (AP214) of a **dual-station FANUC
M-16iB robotic TIG welding cell** — no SolidWorks, no Professional core, just the
Community Edition reading the STEP. Every number below is the **actual output** of the
free commands on this file; nothing is hand-edited or invented.

## Input
```
机器人自动焊接机.STEP   (SolidWorks AP214 export, ~39 MB)
```
The agent extracted the `PRODUCT` / `NEXT_ASSEMBLY_USAGE_OCCURRENCE` structure from the
STEP and fed it to the free-tier commands.

## What the Community Edition returned

### Structure
- **1** top-level assembly (机器人自动焊接机 — "robotic welding machine")
- **13** subassemblies
- **356** instances
- **assembly depth 3**
- **142** unique products

### Assembly statistics — top subassemblies (instances)
The cell is a near-symmetric dual-station layout:

| Top subassembly | Instances |
|---|--:|
| Station 1 (301065_P001) | 148 |
| Station 2 (301065_P001) | 148 |
| Retracted mechanism (301066_P001) | 46 |
| Station 1 fixture (307070_p001) | 20 |
| Station 1 sub (301060_p005) | 16 |
| 330001_P001 | 7 |
| TIG375 (welder) | 2 |
| a-242406lp | 1 |

Station 1 and Station 2 are nearly identical (148 instances each) — the classic
load-one-side / weld-the-other dual-station arrangement.

### Mechanism detection *(experimental)*
| Mechanism | Confidence | Evidence |
|---|--:|---|
| **Robot Arm** (primary) | 95% | M-16iB axis1 / 2 / 3 / 4 / 5-6 |
| Pneumatic Cylinder | 76% | Bimba-12-D MainBody / Rod / Position |

The primary mechanism — a robot arm — matches both the assembly name and the FANUC
M-16iB 6-axis arc-welding robot in the part list. (Type identification only; design
intent / power flow is Professional.)

### Vendor summary
Brands detected from part names:

| Vendor | Count | Example part |
|---|--:|---|
| Nook | 4 | Nook-1-BSJ-U ball-screw jack |
| Bimba | 3 | Bimba-12-D pneumatic cylinder |
| SCHUNK | 1 | SCHUNK PSH 22-2 parallel gripper |
| Banner | 1 | Banner 12 mm proximity switch |

*(Name-based detection only — no sourcing, pricing, or alternates. Some components,
e.g. the FANUC M-16iB arm, RJ3iB controller, and TIG375 welder, use generic part
codes that the brand rules don't match yet.)*

### Basic DFA — honesty in action
The DFA pass ran, but it flagged its own blind spot:

> **Only 2 fasteners detected among 356 parts — almost certainly an under-count.**
> STEP exports usually drop fastener / Toolbox part names; use the original SolidWorks
> assembly for a true fastener count. Complexity here reflects non-fastener parts only.

This is the point of the project: instead of reporting a confident-but-wrong fastener
count, the skill tells you *why* the number is unreliable and what to do about it.

## Why this matters
On a 39 MB, 356-instance industrial assembly, with **no SolidWorks and no commercial
solver**, the Community Edition:
- reconstructed the assembly structure and the dual-station layout,
- identified the primary mechanism (robot arm) and a secondary one (pneumatic cylinder),
- named four component vendors,
- and was honest about what it could not see (fastener count, true interference).

That's a real, useful first-pass review of a real machine — and an honest map of where
the production tools (SolidWorks interference, Professional FE / DFM / design review)
take over.

## Honesty notes
- Structure, statistics, vendor and mechanism results are computed from the STEP product
  tree — deterministic, not guessed.
- A STEP file carries no mates, no FEA, no DFM measurements, and (usually) no fastener
  names, so interference, DFM, and a true fastener count need the SolidWorks assembly or
  the Professional core. The skill returns `deck_only` / a caveat for those rather than
  fabricating a result.
- Mechanism detection is name/standard-part based and marked experimental.
