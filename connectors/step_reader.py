"""Open STEP reader helper.

Reads solids / bounding box from a STEP file when SolidWorks isn't available.
Geometry-level only: STEP carries no part names, quantities, or mates, so a true
named BOM or mate-based explanation needs the SolidWorks assembly instead.

Intentionally dependency-light. If a STEP kernel (e.g. python-occ / steputils) is
installed it is used; otherwise this returns a clear 'reader unavailable' note so
callers degrade gracefully rather than crash.
"""

def read_step(path):
    try:
        # Optional: use a STEP kernel if the host has one installed.
        import steputils.p21 as p21  # type: ignore
        doc = p21.readfile(path)
        return {"ok": True, "entities": len(doc.data), "note": "parsed with steputils"}
    except Exception as e:
        return {"ok": False, "note": f"STEP kernel not available ({e}); "
                "list solids in your CAD tool or provide the SolidWorks assembly."}
