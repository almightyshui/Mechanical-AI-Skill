# Security Policy

## Reporting a vulnerability
Please **do not** open a public issue for security problems. Instead, report privately
via GitHub Security Advisories ("Report a vulnerability" on the Security tab) or by
contacting the maintainer (@almightyshui).

Include what the issue is, how to reproduce it, and the potential impact. You'll get an
acknowledgement and, where applicable, a fix and a credit.

## What to consider when running this skill
This skill is run **by an AI agent with your permissions**, and it can drive real tools
on your machine. Be aware:

- **It executes locally.** Commands run Python and, when present, drive the SolidWorks
  COM API. Only install the skill from a source you trust, and read `SKILL.md` first.
- **It can read CAD/STEP files you point it at.** It does not phone home; it processes
  files locally. The optional online lookup (`references/knowledge/literature.md`) only
  runs through your host agent's web tools and only when explicitly invoked.
- **It never modifies your CAD silently.** Geometry-writing actions (e.g. optimization
  `apply:true`) are Professional, off by default, and gated.
- **Honest-by-design.** The skill does not fabricate results; an unavailable capability
  returns `enterprise_required` / `deck_only`, never a fake number. This is a safety
  property — a fabricated safety factor would be dangerous.

## Scope
This policy covers the Community Edition in this repository. The Professional core is
distributed and supported separately.

## Supported versions
The latest release on `main` is supported. Older tags are not maintained.
