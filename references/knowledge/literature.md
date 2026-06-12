# Knowledge base — literature & paper search (optional online)

For questions the offline knowledge base can't settle — a specific material's fatigue data, a novel method, a current standard edition, validation data for a CFD model — the agent can look up academic/authoritative sources online. **This is the only online-dependent part of the skill; everything else works offline.** In a no-network environment (e.g. a locked-down Codex sandbox), skip this and rely on `formulas.md` / `standards.md`, telling the user that an online lookup would refine the answer.

## When to go online
- The user asks for a value/method not in the offline files (e.g. "fatigue strength of Ti-6Al-4V at 400°C", "best turbulence model for a centrifugal pump").
- You need the **current edition / clause** of a standard (editions change; don't guess).
- The user wants validation references or recent literature for a method.
- You're about to state a specific numeric allowable from a code — verify it instead of inventing it.

## Where to look (authoritative first)
- **Standards bodies**: iso.org, asme.org, astm.org, cen.eu, the user's national body (e.g. GB). For the authoritative clause/edition.
- **Scholarly indexes**: Google Scholar, Semantic Scholar, arXiv (preprints), NASA NTRS, ScienceDirect/Springer (abstracts), NIST (material/thermophysical data, e.g. NIST WebBook for fluid properties).
- **Material data**: MMPDS (aerospace metals), MatWeb, manufacturer datasheets, ASM Handbook references.
- Prefer primary sources (peer-reviewed papers, official standard pages, government labs) over forums/blogs.

## How the host agent does it
This skill doesn't bundle a scraper. It relies on the **host agent's own web tools**:
- **Claude Code / Claude**: the built-in web search / fetch.
- **Codex / Cursor**: their web-browsing or MCP search tools, if enabled.
The agent runs the search, reads the source, and brings the value back into the analysis. If the host has no web access, treat this section as unavailable.

## Citation discipline (important)
- **Attribute every online value** to its source (standard + edition + clause, or paper author/year/DOI). A simulation report that cites its allowables is defensible; one that doesn't isn't.
- **Paraphrase; don't paste.** Pull the number or the method, state it in your own words, and link the source. Do not reproduce copyrighted standard text or large paper excerpts — quote minimally and attribute, or just summarize and cite.
- **Distinguish nominal vs certified.** A value from a textbook/aggregator is nominal; tell the user to confirm against the certified datasheet or governing standard for a real design.
- **Flag conflicts.** If sources disagree (common for material fatigue data), report the range and the more authoritative source rather than picking one silently.

## Putting it back into the result
When an online value is used, record it in the contract result:
- add it to `assumptions` with the citation ("σ_e = 240 MPa for X per <source, year>"),
- if it changes a pass/fail, say so in `caveats` with the source,
- never let an unattributed online number drive a safety conclusion.

## Example
> User: "Is 7075-T6 OK for this fitting at 150°C?"
> Agent: offline `materials.md` has room-temp 7075-T6; 150°C reduces strength, and that's temperature-dependent → go online, find the elevated-temperature knockdown from MMPDS or a paper, cite it, apply it, and note in `assumptions` that the value is from <source> and should be confirmed against MMPDS for design.
