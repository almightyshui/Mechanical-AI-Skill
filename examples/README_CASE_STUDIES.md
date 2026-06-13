# Case Studies

Real assemblies run through the Community Edition, end to end. Each folder is a
self-contained example of "upload a STEP → get an engineering review."

```
examples/<case_name>/
  review.md        # the actual review_summary output (verbatim, not edited)
  input.step       # the source STEP (optional — large files may be omitted)
  screenshots/     # optional: report / viewer screenshots for README & docs
```

## Cases

| Case | Type | What it shows |
|---|---|---|
| `robot_welding_cell/` | Dual-station FANUC M-16iB TIG welding cell | Full review: 142 parts, 78% custom, 6 vendors, complexity High, 4 findings |

More cases welcome (packaging machine, linear transfer, fixture, gantry, …). To
contribute one: run `review_summary` on your STEP, drop the generated
`review_summary.md` in as `review.md`, and add a row above. Keep `review.md`
**verbatim** — the value of a case study is that it's real output, not a polished
mock-up.
