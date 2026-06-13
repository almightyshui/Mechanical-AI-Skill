# Case Study — Robotic Welding Cell

A real 39 MB SolidWorks-exported STEP of a **dual-station FANUC M-16iB robotic TIG
welding cell**. No SolidWorks, no geometry kernel, no Professional core — just the
Community Edition reading the STEP text. **Every figure below is the actual output
of `review_summary` on this file; nothing is hand-edited or invented.**

This is what "upload a STEP, get an engineering review" looks like.

---

## Input

```
机器人自动焊接机.STEP   (SolidWorks AP214 export, ~39 MB)
```

One command:

```
review_summary  →  model.path = the STEP / its folder / a zip
```

The report below is written to `mech_review/review_summary.md` next to the STEP.

---

## Output (verbatim)

### Executive Summary
- Unique parts: 142
- Total instances: 357
- Top-level subassemblies: 1
- Assembly depth: 4

### Complexity
- Level: **High**
- Drivers: 357 instances, 142 unique parts, assembly depth 4, 2 mechanism subsystems

### Manufacturing mix
- Custom (in-house): 79 instances (78%)
- Commercial / classified: 22 instances (22%)

### Vendor concentration
- Identified vendors: 6 (19 parts matched)
- Top: FANUC, Nook, SCHUNK, Bimba, Banner

### Detected mechanisms
- Primary: Robot Arm
- Robot Arm (confidence 95%)
- Pneumatic Cylinder (confidence 76%)

### Vendors
- FANUC (7), Nook (4), SCHUNK (3), Bimba (3), Banner (1), Lincoln Electric (1)

### Categories
- Robot / Arm: 7 · Grippers: 5 · Linear Motion: 4 · Pneumatic: 3 · Motors: 1 · Sensors: 1 · Welding: 1
- Custom Machined (301065): 44 · (301066): 19 · (307070): 6 · (301060): 5 · (330001): 5

### Risk
- 88 / 100 (higher = lower risk; 100 = no flags). Deducted: high part count (142) −12

### Findings
1. **High part variety** (Medium) — 142 unique parts across 357 instances — *Recommendation: Professional*
2. **High custom-part ratio** (Medium) — 78% of classified instances are custom — *Recommendation: Professional*
3. **High instance count** (Medium) — 357 total instances — *Recommendation: Professional*
4. **Deep assembly structure** (Low) — assembly depth 4 — *Recommendation: Professional*

(Full 142-row name-level BOM is in the generated report and `review_summary.json`.)

---

## Why this matters

A plain STEP viewer (FreeCAD, CAD Assistant, online 3D viewers) shows you the
geometry. None of them tell you, from the file alone, that this is a **dual-station
FANUC M-16iB welding cell, 78% in-house parts, six vendors, high complexity, with
four findings worth a closer look** — in a report a manager, buyer, or reviewer can
read in five minutes.

That is the difference between *viewing* a model and *understanding* an assembly.

## The honesty line

Everything here is computed from STEP part names and assembly structure. There is
**no** volume, mass, material, or contact analysis (those need a geometry kernel or
SolidWorks), and the findings state **fact, evidence, and impact** — not what to
change. Specific recommendations are a Professional capability. The skill never
invents a number it cannot compute.
