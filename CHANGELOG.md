# Changelog

All notable changes to the Community Edition are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

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
