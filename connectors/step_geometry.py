"""STEP geometry engine — structure + geometric checks without SolidWorks.

Uses cadquery/OCP (OpenCASCADE) when available. If not installed, callers should
fall back to deck_only. This makes the Community skill self-sufficient on a STEP
file for: assembly structure (BOM/tree), and approximate geometric interference /
clearance. Geometry results are flagged approximate — they are NOT a substitute for
the SolidWorks Interference Detection used in production.
"""
import os

def available():
    try:
        import cadquery  # noqa
        return True
    except Exception:
        return False


def _load(path):
    import cadquery as cq
    return cq.importers.importStep(path)


def read_structure(path):
    """Return solids found in the STEP and basic counts.

    NOTE: a STEP file often merges an assembly into one compound; we report the
    solids we can see. True named-component BOM is best from a SolidWorks assembly.
    """
    import cadquery as cq
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_SOLID
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp

    wp = _load(path)
    compound = wp.val().wrapped
    exp = TopExp_Explorer(compound, TopAbs_SOLID)
    solids = []
    idx = 0
    while exp.More():
        from OCP.TopoDS import TopoDS
        sol = TopoDS.Solid_s(exp.Current())
        props = GProp_GProps()
        BRepGProp.VolumeProperties_s(sol, props)
        vol = props.Mass()  # volume for VolumeProperties
        c = props.CentreOfMass()
        solids.append({"index": idx, "volume_mm3": round(vol, 3),
                       "centroid": [round(c.X(), 2), round(c.Y(), 2), round(c.Z(), 2)],
                       "_shape": sol})
        idx += 1
        exp.Next()
    return solids


def interference(path, min_volume_mm3=1.0, max_solids=40, max_pairs=400):
    """Approximate solid-solid interference via pairwise boolean intersection.

    Returns overlaps with their volume. APPROXIMATE: depends on STEP tessellation
    and assumes solids are positioned as in the file. Flag as rough; confirm in CAD.

    Scale guard: pairwise boolean is O(n^2) and expensive. For large assemblies
    (> max_solids), this is refused with a clear message rather than hanging — use
    SolidWorks Interference Detection on big models.
    """
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp

    solids = read_structure(path)
    n = len(solids)
    if n > max_solids:
        return {"solids": n, "interferences": [], "interference_count": None,
                "total_volume_mm3": None, "too_large": True,
                "message": f"{n} solids exceeds the STEP-geometry limit ({max_solids}). "
                           f"Pairwise boolean interference is O(n^2) and would be slow/unreliable "
                           f"on an assembly this size. Run SolidWorks Interference Detection instead "
                           f"(use the generated macro), or check a smaller sub-assembly."}
    overlaps = []
    checked = 0
    for i in range(n):
        for j in range(i + 1, n):
            if checked >= max_pairs:
                break
            checked += 1
            try:
                common = BRepAlgoAPI_Common(solids[i]["_shape"], solids[j]["_shape"])
                if not common.IsDone():
                    continue
                shp = common.Shape()
                props = GProp_GProps()
                BRepGProp.VolumeProperties_s(shp, props)
                v = props.Mass()
                if v and v > min_volume_mm3:
                    overlaps.append({"pair": [i, j], "volume_mm3": round(v, 3)})
            except Exception:
                continue
    overlaps.sort(key=lambda o: -o["volume_mm3"])
    total = round(sum(o["volume_mm3"] for o in overlaps), 3)
    return {"solids": n, "interferences": overlaps,
            "interference_count": len(overlaps), "total_volume_mm3": total,
            "too_large": False}


def clearance(path, min_gap_mm=1.0, max_pairs=200):
    """Approximate minimum gap between solid pairs (non-touching).

    Reports pairs whose minimum distance is below min_gap_mm. APPROXIMATE.
    """
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    solids = read_structure(path)
    n = len(solids)
    tight = []
    checked = 0
    for i in range(n):
        for j in range(i + 1, n):
            if checked >= max_pairs:
                break
            checked += 1
            try:
                dss = BRepExtrema_DistShapeShape(solids[i]["_shape"], solids[j]["_shape"])
                if not dss.IsDone():
                    continue
                d = dss.Value()
                if 0 < d < min_gap_mm:
                    tight.append({"pair": [i, j], "gap_mm": round(d, 3)})
            except Exception:
                continue
    tight.sort(key=lambda t: t["gap_mm"])
    return {"solids": n, "tight_clearances": tight, "count": len(tight),
            "min_gap_threshold_mm": min_gap_mm}
