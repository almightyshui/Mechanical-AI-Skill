# Changelog

All notable changes to the Community Edition are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [0.5.6] - 2026-06-13

### Fixed
- **Executive Review report rendering**: the Markdown report had four display
  bugs surfaced on a real assembly — mechanisms showed `?` (wrong field; now reads
  `mechanism`), vendors printed raw Python dicts (now `Vendor (N parts)`), the risk
  score showed `None` (wrong field; now reads `overall_score`), and the score
  direction was ambiguous (now labelled "higher = lower risk; 100 = no flags",
  with deductions shown as `−points`).

### Improved
- **Category classification on real part names**: rules now recognize common
  abbreviations and brand/model conventions (e.g. `Prox`→Sensors, `Bimba`→Pneumatic,
  `Nook`/`BSJ`/`THK`→Linear Motion, `M-16iB`/`FANUC`/`axisN`→Robot, `SCHUNK`/`PSH`→
  Grippers, `TIG`/`weld`→Welding), so a real assembly classifies instead of
  returning "no categories." Vendor and category libraries will be externalized to
  JSON next for easy extension.

## [0.5.5] - 2026-06-13

### Fixed
- **`review_summary` had two entry points; now unified**: `design_review.py`
  still routed `review_summary` to the old metrics-aggregator in `free_fea.py`
  (which demands pre-computed `inputs.metrics`), while `sw_mechanism.py` had the
  new self-orchestrating Executive Review. An agent that picked the former got a
  misleading `needs_input: metrics` even though the real capability runs from the
  STEP alone. `design_review.py` now delegates `review_summary` to the same
  Executive Review, so there is one behaviour regardless of which script is
  invoked. SKILL.md command map now names `sw_mechanism.py` as the script for
  `review_summary`.

## [0.5.4] - 2026-06-13

### Added
- **`review_summary` now writes a report you can find**: it generates
  `review_summary.md` (human-readable: executive summary, mechanisms, vendors,
  categories, risk, name-level BOM table, limits) and `review_summary.json`
  (machine-readable, full BOM) into a **`mech_review/` folder next to the STEP
  file** — a predictable location, not a temp dir the agent picks. Both exact
  paths are returned in `artifacts.summary_md` / `artifacts.summary_json`.

### Docs
- SKILL.md tells the agent to report the exact `artifacts` paths for the review
  and never to invent or guess an output location.

## [0.5.3] - 2026-06-13

### Fixed
- **BOM/structure name resolution on real-world STEP (huge unresolved drop)**:
  the PRODUCT_DEFINITION → FORMATION → PRODUCT name chain failed on common CAD
  exports because the referenced `#id` is not the last argument (e.g.
  `PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE('任何','',#product,.NOT_KNOWN.)`
  and `PRODUCT_DEFINITION('未知','',#formation,#context)`). The old regexes
  required the ref to sit right before the closing paren, so every part resolved
  to "unresolved" — a BOM that counted parts but couldn't name them. The chain
  now takes the first `#ref` in the parameter list per the STEP entity layout,
  resolving real (incl. CJK) part names. On the validating fixture, unresolved
  instances drop from all-of-them to zero. Improves BOM, vendor, category, and
  mechanism detection (all depend on resolved PRODUCT names).

## [0.5.2] - 2026-06-13

### Changed
- **`review_summary` is now an Executive Review, not an aggregator**: instead of
  requiring the caller to pre-run every check and hand in `metrics`, it now reads
  the STEP/zip/folder itself once and orchestrates the free checks — assembly
  scale (unique parts, instances, subassemblies, depth), detected mechanisms,
  vendors, categories, a name-level BOM (top rows inline, full list to
  `artifacts.full_bom`), and a transparent risk score — returning one
  engineer-facing verdict. One command in, a review out. Every figure is
  computed; sub-checks that can't run are omitted, never faked. Design intent /
  load paths / functional reasoning remain Professional.

### Docs
- README updated: executive review, no-SolidWorks name-level BOM, forgiving path
  input (file / odd extension / zip / folder), and the unified status/headline
  layer.

## [0.5.1] - 2026-06-13

### Added
- **Forgiving task input (`normalize_task`)**: agents repeatedly wrote near-miss
  task shapes — `task_type`/`command` instead of `capability`,
  `input_file`/`file`/`path` at the top level (or `model.file`) instead of
  `model.path` — which produced `failed` or a misleading `needs_input` and forced
  several retry rounds. `load_task` now maps these aliases onto the canonical
  schema, so all three entry points (understand / diagnostics / mechanism) accept
  the common variants. The canonical schema is unchanged.
- **Self-healing `needs_input`**: when a command can't auto-extract because no
  `model.path` was given, the caveat now includes a copy-pasteable correct task
  example, so an agent can fix it in one step instead of guessing or falling back
  to manual component lists.

## [0.5.0] - 2026-06-13

### Added
- **STEP text-level BOM (no geometry engine needed)**: `generate_bom` and
  `part_count` now produce a real name-level BOM from STEP PRODUCT names and
  NAUO instance counts when neither SolidWorks nor a geometry kernel is present
  — instead of falling straight to `deck_only`. Quantities are real (counted
  from how many times each part is placed via NEXT_ASSEMBLY_USAGE_OCCURRENCE).
  New `step_context.extract_bom()` backs this. The degradation chain is now
  SolidWorks → geometry kernel → STEP-text → macro, so a plain STEP upload
  almost always returns an actual BOM. Honest about limits: results carry
  `source: "STEP-text"`, `geometry: false`, and a caveat that there is no
  volume / mass / material / standard-part classification (those need a geometry
  kernel or the SolidWorks assembly). Unresolved-name instances are counted and
  reported separately, never invented. Large BOMs inline a 20-row preview and
  write the full list to `artifacts.full_bom` to keep agent context small.

## [0.4.2] - 2026-06-13

### Added
- **Unified status layer (`headline` + `tier` on every result)**: each result now
  carries a one-line `headline` that states the outcome unambiguously —
  `[SUCCESS]` / `[PARTIAL]` / `[NEEDS INPUT]` / `[NOT IN COMMUNITY]` / `[FAILED]`
  — so an agent can't misread a successful or gracefully-degraded result as a
  failure. This addresses the observed failure mode where an agent saw
  `deck_only` or a summarized `ok` and reported "0 succeeded / needs SolidWorks",
  then fabricated part names, vendors, and counts.
- **SKILL.md "READ THIS FIRST" block**: explicit rules for reporting each status
  (deck_only is NOT a failure; ok is a real result; never fabricate part
  names/vendors/counts from filenames or preview images), plus a note that the
  model path accepts a STEP file, a non-standard extension, a zip, or an
  unzipped folder.

### Changed
- **`_read` tries multiple encodings** (utf-8-sig → utf-8 → gb18030, then lossy)
  so CJK part names from Chinese CAD exports are read intact instead of dropped,
  strengthening vendor/category matching. Never raises.

## [0.4.1] - 2026-06-13

### Fixed
- **Accept a directory as the model path**: agents and users frequently point
  at the unzipped assembly *folder* (e.g. `.../-7549.snapshot.1/`) rather than
  the exact `.STEP` inside it. Previously that read as a non-STEP and every
  command returned `needs_input`/`deck_only`, looking like "can't read the
  file." `resolve_step_path()` and `is_step()` now treat a directory as a STEP
  source — they pick the best STEP within it (largest = most likely the top
  assembly), the same selection used for zips. Verified: all 7 STEP Auto Context
  commands return `ok` when handed the folder path.

## [0.4.0] - 2026-06-13

### Changed
- **Summary-by-default output (big token savings for agents)**: the
  structure/graph commands (`assembly_tree`, `exploded_view`, `adjacency_graph`)
  used to dump the entire tree / Mermaid / neighbour map inline — on a 400-part
  assembly that was ~18k tokens across the set, most of it the same node list
  drawn three ways. They now return a compact summary by default (counts +
  graph_type + a short preview) and write the full result to a `.full.json`
  sidecar referenced under `artifacts.full_results`. Same 8-command run drops
  from ~18k to ~2.5k tokens (-86%). Pass `"detail":"full"` (in `inputs` or at
  the task root) to get everything inline as before. Summary counts are
  identical to the full result and truncation is labelled (e.g. "401 nodes
  total") — the summary never alters or invents data. Small commands
  (`assembly_stats`, `vendor_summary`, `category_summary`, `mechanism_detect`)
  were already tiny and are unchanged.

## [0.3.4] - 2026-06-13

### Fixed
- **UTF-8 everywhere (Windows CJK paths)**: task files, result files, and all
  generated macros/reports are now read and written as explicit UTF-8. Before,
  bare `open()` used the platform default (GBK on Chinese-locale Windows) and
  raised on any task carrying a CJK path or part name (e.g.
  `机器人自动焊接机.STEP`), which made callers misreport capabilities as
  "missing" or "Pro-only" when in fact the command simply never ran. Result JSON
  now uses `ensure_ascii=False` so CJK names stay readable instead of `\uXXXX`.
- **`adjacency_graph` on real assemblies**: previously returned `needs_input`
  (0 edges) on a large STEP even though the file carried hundreds of assembly
  links, because unresolved PRODUCT_DEFINITION ids were silently dropped. The
  NAUO fallback now keeps a `pd_<id>` placeholder so no edge is lost, and —
  critically — the output is explicitly tagged `graph_type: "hierarchy_fallback"`
  (parent→child "belongs-to", NOT geometric "touches") whenever no geometry
  kernel is present. A true contact graph (`graph_type: "geometric"`) still
  requires SolidWorks or cadquery. The hierarchy graph is never presented as a
  geometric adjacency graph — consistent with the never-fabricate rule.

## [0.3.3] - 2026-06-13

### Fixed
- **Zip assembly packages work directly**: capabilities now accept a `.zip`
  (a common way CAD assemblies are shared, e.g. `part-7549.snapshot.1.zip`)
  without the caller unzipping by hand. A new `resolve_step_path()` layer in
  `step_context` detects a zip (by name or signature), extracts it once
  (cached + path-traversal guarded), and picks the best STEP inside — largest
  STEP wins, since that is almost always the top assembly rather than a single
  part. `is_step()` recognizes such a zip, and the 7 STEP Auto Context commands
  plus BOM (`generate_bom`/`part_count`) and interference/clearance diagnostics
  resolve the zip transparently. Previously every command returned `needs_input`
  on a zip, which read as "can't analyze this assembly." Verified end to end on
  a multi-STEP zip: 7 commands return `ok` with real extracted structure.

## [0.3.2] - 2026-06-13

### Fixed
- **STEP detection by content, not extension**: `is_step()` now sniffs the file
  for ISO-10303 / PRODUCT / NAUO markers instead of trusting only a `.step`/`.stp`
  suffix. CAD tools sometimes export a STEP under a non-standard name (e.g.
  `foo.snapshot.1`); previously every capability returned `needs_input` on such a
  file, which read as "can't open STEP." Now content wins: the 7 STEP Auto Context
  commands (`assembly_tree`, `assembly_stats`, `mechanism_detect`, `vendor_summary`,
  `category_summary`, `adjacency_graph`, `exploded_view`) plus BOM (`generate_bom` /
  `part_count`) and interference/clearance diagnostics all recognize a STEP
  regardless of its file extension. Verified end to end on a `.snapshot.1` file.

## [0.3.1] - 2026-06-12

### Fixed
- **STEP Auto Context**: `assembly_tree`, `assembly_stats`, `mechanism_detect`,
  `vendor_summary`, `category_summary`, `adjacency_graph`, and `exploded_view` now
  extract their inputs (components / nodes / subassemblies / edges) **directly from a
  STEP file** via a new `connectors/step_context.py` layer. Previously they returned
  `needs_input` unless the caller pre-extracted the data by hand. Now a STEP path is
  enough — "upload a STEP -> get a result" actually works end to end.

## [0.3.0] - 2026-06-12

Capability expansion driven by real-assembly testing (a 39 MB robotic welding cell).

### Added
- **STEP geometry fallback** for diagnostics: approximate interference / clearance and
  BOM run directly from a STEP when SolidWorks isn't present (instead of `deck_only`),
  with a scale guard that defers very large assemblies to the SolidWorks macro.
- **Fastener intelligence v2** (`fastener_check`): thread-engagement (n x D by mating
  material) and missing-washer / missing-nut stack screens.
- **Composite mechanism patterns**: motor+coupling+shaft -> rotary drive train;
  guide+carriage+screw -> linear motion module (on top of single-type detection).
- **Adjacency graph** (`adjacency_graph`): geometric "who touches whom", auto-computed
  from a STEP; force-flow / constraint graph remain Professional.
- **Assembly statistics**, **component category summary**, **exploded structure graph**
  (Mermaid), **vendor summary** — structure/statistics outputs for large cells.
- Flagship **case study**: robotic welding cell (real 39 MB STEP).
- **Benchmarks** doc and a **how-it-compares** table.

### Changed
- DFA proactively flags a likely fastener under-count on STEP-derived assemblies.
- Repositioned as the **first AI-native engineering review layer**; Professional framed
  as the **Engineering Intelligence Layer** (why / force-flow / where-it-fails / how-to-make).

### Notes
- Community now exposes 14 free capabilities. The closed `mechanical_ai_core` engine
  skeleton (API contracts only) exists separately; advanced engineering stays Professional.

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
[0.3.0]: https://github.com/almightyshui/Mechanical-AI-Skill/releases/tag/v0.3.0
[0.3.1]: https://github.com/almightyshui/Mechanical-AI-Skill/releases/tag/v0.3.1
