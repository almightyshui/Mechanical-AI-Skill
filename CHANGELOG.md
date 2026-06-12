# Changelog

All notable changes to the Community Edition are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [0.2.0] - 2026-06-12

Major capability and positioning update — the skill is now self-sufficient on a STEP
file alone for structure and approximate geometry, with several new review outputs.

### Added
- **STEP geometry fallback** (`connectors/step_geometry.py`): with no SolidWorks,
  BOM / part count, and **approximate** interference / clearance now run directly from
  the STEP solids (boolean intersection / distance), instead of returning `deck_only`.
  Flagged approximate; large assemblies (> 40 solids) fall back to the macro rather
  than running a slow O(n^2) boolean.
- **Mechanism detection** extended: robot arm, linear slide, pneumatic cylinder,
  rotary table (in addition to gear train / belt / chain / lead screw).
- **Vendor summary** — detect component brands from part names (FANUC, SCHUNK, SMC,
  THK, Banner, Nook, Bimba, …).
- **Assembly statistics** — top-level subassemblies with instance counts.
- **Component category summary** — counts by kind (motors, sensors, cylinders, …);
  statistics only, not a procurement list.
- **Exploded structure graph** — Mermaid diagram of the assembly tree.
- **Review summary** dashboard + **assembly tree** text view.
- **Risk score** is now multi-factor with transparent contributors (interference,
  DFM, part/fastener counts, assembly depth, tool clearance, subassemblies, instances,
  mechanisms).
- **Basic DFA** is now free (complexity + tool-clearance); it proactively flags a
  likely fastener under-count on STEP-derived assemblies.

### Changed
- README repositioned as an *engineering review layer* (Why / What-it-is-not /
  Example-first / Community-first), with logo, architecture diagram, and badges.
- Wording tightened for honesty: "assembly structure summary" (not "explanation"),
  "material metadata when available", mechanism detection marked experimental.

### Notes
- Advanced engineering (fatigue, thermal, CFD, multibody, optimization, advanced
  DFM/DFA, automated design review, procurement) remains the closed Professional Edition.

## [0.1.0] - 2026-06-12

First public release of the Community Edition — an AI mechanical-engineering CAD
**review** skill for Claude Code, Codex, and Cursor.

### Added
- **CAD understanding**: BOM generation, part count, standard-part identification,
  assembly explanation (`sw_understand.py`).
- **Assembly diagnostics**: interference / mate / clearance checks via the SolidWorks
  API (`sw_diagnostics.py`).
- **Basic DFM**: deep holes, thin walls, sharp internal corners (`sw_dfm.py` +
  `free_fea.py`).
- **Free-tier analysis**: single-load-case static (stress, deflection, safety factor)
  and first-3-mode modal (frequencies, resonance) via analytical formulas — no
  commercial solver needed (`run_analysis.py`).
- **Simple risk score**: transparent weighted roll-up of the free checks
  (`design_review.py`).
- **Reporting**: render any result to a PDF/HTML report (`report_pdf.py`).
- **Freemium architecture**: a single tier guard (`tier.py`) and a core bridge
  (`core_bridge.py`) — Professional capabilities return `enterprise_required` and
  degrade gracefully until the licensed core is installed.
- **Stable JSON contract** (`sdk/CONTRACT.md`), open connectors (`connectors/`),
  task examples, and an end-to-end `examples/demo.sh`.
- **Packaging**: Claude Code plugin manifest, `install.sh` for Codex/Cursor, CI
  workflow, issue templates, logo, architecture diagram, and a gear-reducer case study.

### Notes
- Advanced engineering (fatigue, thermal, CFD, multibody dynamics, optimization,
  advanced DFM/DFA, automated design review) is the closed Professional Edition.
- Free-tier results use public textbook formulas and are verifiable by hand.

[0.1.0]: https://github.com/almightyshui/Mechanical-AI-Skill/releases/tag/v0.1.0
[0.2.0]: https://github.com/almightyshui/Mechanical-AI-Skill/releases/tag/v0.2.0
