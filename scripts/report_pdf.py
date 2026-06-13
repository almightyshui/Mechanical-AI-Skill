#!/usr/bin/env python3
"""Universal report generator — turn any contract result JSON into a PDF (or HTML).

Takes one or more result JSON files (from sw_diagnostics / sw_understand / sw_dfm /
run_analysis / optimize) and renders an engineering report: title, status, the
results table, BOM/findings tables where present, and the assumptions/caveats an
engineer must see. Uses reportlab if available; otherwise emits a self-contained
HTML file (so it works with zero extra dependencies).

Usage:
  python report_pdf.py --results r1.json r2.json --out report.pdf --title "Bracket review"
  python report_pdf.py --results r.json --out report.html        # force HTML
"""
import os, sys, json, argparse, html, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _contract as C
import core_bridge as CB


def load(paths):
    out = []
    for p in paths:
        try:
            out.append((p, json.load(open(p, encoding="utf-8"))))
        except Exception as e:
            out.append((p, {"status": "failed", "caveats": [f"could not read {p}: {e}"]}))
    return out


STATUS_LABEL = {
    "ok": "OK — valid results",
    "needs_input": "NEEDS INPUT — nothing was run",
    "deck_only": "DECK ONLY — solver/tool not installed; deck generated",
    "failed": "FAILED — not a valid result",
}


def flatten_results(results, prefix=""):
    """Yield (key, value) rows; expand small lists/dicts for tables."""
    rows = []
    for k, v in (results or {}).items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            rows.append((prefix + str(k), v))
        elif isinstance(v, list):
            rows.append((prefix + str(k), f"[{len(v)} items]"))
        elif isinstance(v, dict):
            rows.append((prefix + str(k), "{...}"))
    return rows


def table_lists(results):
    """Return (name, list-of-dicts) for any list-of-dict in results (BOM, findings)."""
    tables = []
    for k, v in (results or {}).items():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            tables.append((k, v))
    return tables


def render_html(reports, title):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    css = """body{font-family:-apple-system,Segoe UI,Inter,Arial,sans-serif;color:#1a1a1a;
    max-width:820px;margin:32px auto;padding:0 20px;line-height:1.5}
    h1{font-size:22px;border-bottom:2px solid #333;padding-bottom:6px}
    h2{font-size:17px;margin-top:28px} .meta{color:#666;font-size:13px}
    .status{display:inline-block;padding:2px 8px;border-radius:4px;font-size:13px;font-weight:600}
    .ok{background:#e6f4ea;color:#137333}.deck_only{background:#fef7e0;color:#b06000}
    .needs_input{background:#e8f0fe;color:#1967d2}.failed{background:#fce8e6;color:#c5221f}
    table{border-collapse:collapse;width:100%;margin:10px 0;font-size:13px}
    th,td{border:1px solid #ddd;padding:6px 8px;text-align:left}th{background:#f5f5f5}
    .note{color:#555;font-size:13px}ul{margin:6px 0}li{margin:3px 0}
    .caveat{color:#b06000}.assume{color:#444}"""
    parts = [f"<!doctype html><meta charset=utf-8><style>{css}</style>",
             f"<h1>{html.escape(title)}</h1>",
             f"<div class=meta>Generated {now} · mech-sim-assistant</div>"]
    for path, r in reports:
        st = r.get("status", "?")
        cap = r.get("capability", "?"); stage = r.get("stage", "?")
        parts.append(f"<h2>{html.escape(str(cap))} <span class='meta'>(stage {html.escape(str(stage))})</span></h2>")
        parts.append(f"<p><span class='status {st}'>{html.escape(STATUS_LABEL.get(st, st))}</span></p>")
        # scalar results
        rows = flatten_results(r.get("results"))
        if rows:
            parts.append("<table><tr><th>Quantity</th><th>Value</th></tr>")
            for k, v in rows:
                parts.append(f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>")
            parts.append("</table>")
        # list tables (BOM, findings, ...)
        for name, items in table_lists(r.get("results", {})):
            cols = list({k for it in items for k in it.keys()})
            parts.append(f"<p class=note><b>{html.escape(name)}</b> ({len(items)})</p>")
            parts.append("<table><tr>" + "".join(f"<th>{html.escape(c)}</th>" for c in cols) + "</tr>")
            for it in items:
                parts.append("<tr>" + "".join(f"<td>{html.escape(str(it.get(c,'')))}</td>" for c in cols) + "</tr>")
            parts.append("</table>")
        if r.get("needs_input"):
            parts.append("<p class=note><b>Needs input:</b></p><ul>" +
                         "".join(f"<li>{html.escape(str(x))}</li>" for x in r['needs_input']) + "</ul>")
        if r.get("assumptions"):
            parts.append("<p class=note><b>Assumptions:</b></p><ul class=assume>" +
                         "".join(f"<li>{html.escape(str(x))}</li>" for x in r['assumptions']) + "</ul>")
        if r.get("caveats"):
            parts.append("<p class=note><b>Caveats:</b></p><ul class=caveat>" +
                         "".join(f"<li>{html.escape(str(x))}</li>" for x in r['caveats']) + "</ul>")
        if r.get("run_command"):
            parts.append(f"<p class=note><b>Run command:</b> <code>{html.escape(str(r['run_command']))}</code></p>")
    return "\n".join(parts)


def render_pdf(reports, title, out):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                    TableStyle, ListFlowable, ListItem)
    styles = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=9, leading=12)
    doc = SimpleDocTemplate(out, pagesize=A4, title=title)
    story = [Paragraph(html.escape(title), styles["Title"]),
             Paragraph(datetime.datetime.now().strftime("Generated %Y-%m-%d %H:%M · mech-sim-assistant"), small),
             Spacer(1, 12)]
    for path, r in reports:
        st = r.get("status", "?")
        story.append(Paragraph(f"{html.escape(str(r.get('capability','?')))} "
                               f"(stage {html.escape(str(r.get('stage','?')))})", styles["Heading2"]))
        story.append(Paragraph(f"<b>Status:</b> {html.escape(STATUS_LABEL.get(st, st))}", small))
        story.append(Spacer(1, 6))
        rows = flatten_results(r.get("results"))
        if rows:
            data = [["Quantity", "Value"]] + [[str(k), str(v)] for k, v in rows]
            t = Table(data, colWidths=[200, 280])
            t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f0f0f0")),
                                   ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                                   ("FONTSIZE", (0,0), (-1,-1), 8)]))
            story.append(t); story.append(Spacer(1, 6))
        for name, items in table_lists(r.get("results", {})):
            cols = list({k for it in items for k in it.keys()})
            story.append(Paragraph(f"<b>{html.escape(name)}</b> ({len(items)})", small))
            data = [cols] + [[str(it.get(c, "")) for c in cols] for it in items]
            t = Table(data)
            t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f0f0f0")),
                                   ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                                   ("FONTSIZE", (0,0), (-1,-1), 7)]))
            story.append(t); story.append(Spacer(1, 6))
        for label, key, color in [("Needs input", "needs_input", "#1967d2"),
                                    ("Assumptions", "assumptions", "#444444"),
                                    ("Caveats", "caveats", "#b06000")]:
            if r.get(key):
                story.append(Paragraph(f"<b>{label}:</b>", small))
                story.append(ListFlowable([ListItem(Paragraph(html.escape(str(x)), small)) for x in r[key]],
                                          bulletType="bullet"))
        if r.get("run_command"):
            story.append(Paragraph(f"<b>Run command:</b> {html.escape(str(r['run_command']))}", small))
        story.append(Spacer(1, 14))
    doc.build(story)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="Engineering analysis report")
    ap.add_argument("--advanced", action="store_true",
                    help="Professional report template (requires Professional Edition)")
    a = ap.parse_args()
    if a.advanced:
        core = CB.get_core()
        if core is None or not hasattr(core, 'advanced_report'):
            print(json.dumps(CB.enterprise_required(C, 'report', 'advanced_report')))
            return
        print(json.dumps(core.advanced_report(a.results, a.out, a.title)))
        return
    reports = load(a.results)

    want_pdf = a.out.lower().endswith(".pdf")
    if want_pdf:
        try:
            render_pdf(reports, a.title, a.out)
            print(json.dumps({"status": "ok", "report": a.out, "format": "pdf"}))
            return
        except Exception as e:
            html_out = os.path.splitext(a.out)[0] + ".html"
            open(html_out, "w", encoding="utf-8").write(render_html(reports, a.title))
            print(json.dumps({"status": "ok", "report": html_out, "format": "html",
                              "note": f"reportlab unavailable ({e}); wrote HTML instead. "
                                      "pip install reportlab for PDF."}))
            return
    open(a.out, "w", encoding="utf-8").write(render_html(reports, a.title))
    print(json.dumps({"status": "ok", "report": a.out, "format": "html"}))


if __name__ == "__main__":
    main()
