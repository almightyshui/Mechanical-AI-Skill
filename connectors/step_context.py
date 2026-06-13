"""STEP Auto Context — one place that turns a STEP path into the structured inputs
the Community capabilities consume (components / nodes / subassemblies / edges).

Pure text parsing of STEP entities (PRODUCT, PRODUCT_DEFINITION,
PRODUCT_DEFINITION_FORMATION*, NEXT_ASSEMBLY_USAGE_OCCURRENCE). No geometry kernel
needed, so it runs in any environment. Geometric adjacency (edges) optionally uses
the geometry engine when available, else falls back to assembly-relationship edges.

This is what makes "upload a STEP -> get a review" true: capabilities call these
extractors automatically instead of returning needs_input.
"""
import re
import os
import zipfile
import tempfile


# Cache: original zip path -> resolved STEP path inside extracted temp dir.
# A single zip is unpacked once and reused across all 7 capability calls.
_ZIP_CACHE = {}


def _looks_like_step_name(name):
    return name.lower().endswith((".step", ".stp"))


def _sniff_is_step_text(path):
    """Content sniff for files without a .step/.stp name."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(8192)
    except Exception:
        return False
    if not head:
        return False
    up = head.upper()
    if "ISO-10303" in up:
        return True
    return ("PRODUCT(" in up or "PRODUCT (" in up
            or "NEXT_ASSEMBLY_USAGE_OCCURRENCE" in up)


def _pick_step_from_dir(root):
    """Choose the best STEP from an extracted tree.

    Preference: real STEP files (by name OR content), largest first — the
    biggest STEP is almost always the top assembly rather than a single part.
    A zip can also carry SLDASM/SLDPRT (no text STEP); those are ignored here
    since this layer is text-STEP only. Returns a path or None.
    """
    candidates = []  # (size, path)
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            fp = os.path.join(dirpath, fn)
            try:
                size = os.path.getsize(fp)
            except Exception:
                continue
            if _looks_like_step_name(fn) or _sniff_is_step_text(fp):
                candidates.append((size, fp))
    if not candidates:
        return None
    candidates.sort(reverse=True)  # largest first = most likely the assembly
    return candidates[0][1]


def _is_zip(path):
    p = str(path).lower()
    if p.endswith(".zip"):
        return True
    try:
        return zipfile.is_zipfile(path)
    except Exception:
        return False


def resolve_step_path(path):
    """Normalize any input to a usable STEP path.

    - A STEP file (any extension, by content) -> returned as-is.
    - A directory (e.g. an unzipped assembly folder) -> the best STEP inside is
      returned. Agents and users often point at the extracted folder rather than
      the exact .STEP inside it; this makes that just work.
    - A .zip assembly package -> extracted once (cached) and the best STEP
      inside is returned.
    - Anything we can't resolve -> original path returned unchanged, so callers
      degrade exactly as before.
    """
    if not path:
        return path
    # A directory: pick the best STEP within it (handles "pointed at the unzipped
    # folder, not the .STEP file" — the most common path mistake).
    try:
        if os.path.isdir(path):
            step = _pick_step_from_dir(path)
            if step:
                return step
            return path
    except Exception:
        pass
    if _is_zip(path):
        key = os.path.abspath(str(path))
        cached = _ZIP_CACHE.get(key)
        if cached and os.path.exists(cached):
            return cached
        try:
            tmp = tempfile.mkdtemp(prefix="step_ctx_")
            with zipfile.ZipFile(path) as zf:
                # Guard against path traversal in zip member names.
                safe = [n for n in zf.namelist()
                        if not (n.startswith("/") or ".." in n.replace("\\", "/").split("/"))]
                zf.extractall(tmp, members=safe)
            step = _pick_step_from_dir(tmp)
            if step:
                _ZIP_CACHE[key] = step
                return step
        except Exception:
            pass
        return path  # couldn't crack the zip; let caller report needs_input
    return path


def _read(path):
    path = resolve_step_path(path)
    # Real-world STEP from Chinese CAD tools may be UTF-8 (with/without BOM) or
    # GB18030. Try in order so CJK part names survive intact instead of being
    # dropped by errors="ignore" (which would weaken vendor/category matching).
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
        except Exception:
            return ""
    # Last resort: read lossy rather than fail outright.
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def is_step(path):
    """True if this is a STEP file (by CONTENT, not just suffix) OR a .zip that
    contains one.

    A real STEP (ISO 10303-21) starts with an `ISO-10303` header and carries
    PRODUCT / assembly-usage entities. Tools may hand us a STEP with a
    non-standard extension (e.g. `foo.snapshot.1`), or wrap the whole assembly
    in a `.zip` (e.g. `part-7549.snapshot.1.zip`). A clean `.step`/`.stp` suffix
    is a fast accept; a zip is resolved and re-checked; everything else is
    decided by sniffing the file for STEP markers.
    """
    p = str(path).lower()
    if p.endswith((".step", ".stp")):
        return True
    # A directory or zip is a STEP source if we can resolve a STEP out of it.
    try:
        if os.path.isdir(path):
            return _pick_step_from_dir(path) is not None
    except Exception:
        pass
    if _is_zip(path):
        resolved = resolve_step_path(path)
        return resolved != path and bool(resolved) and os.path.exists(str(resolved))
    return _sniff_is_step_text(path)


def extract_components(path):
    """[{name}] — de-duplicated PRODUCT names."""
    text = _read(path)
    out, seen = [], set()
    for m in re.finditer(r"PRODUCT\s*\(\s*'([^']*)'\s*,\s*'([^']*)'", text):
        name = (m.group(2) or m.group(1) or "").strip()
        if name and name not in seen:
            seen.add(name)
            out.append({"name": name})
    return out


def _build_graph(text):
    """Parse PRODUCT, PD->product map, and NAUO parent/child PD links.

    Returns (id2name, nauo_edges) where nauo_edges is [(parent_pd, child_pd)] and
    id2name maps a PRODUCT_DEFINITION id to a product name.

    Real-world STEP (e.g. Chinese CAD exports) spaces entities out and does NOT
    put the referenced #id right before the closing paren, e.g.:
        #N = PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE ( '任何','',#P,.NOT_KNOWN.) ;
        #M = PRODUCT_DEFINITION ( '未知','',#F,#CTX ) ;
    So we resolve the chain by taking the FIRST #ref in the parameter list
    (which is the formation for a PD, and the product for a PDF) rather than
    requiring the ref to be the last argument.
    """
    # entity# -> product name, via  #id = PRODUCT ( 'id','name', ... )
    ent_product = {}
    for m in re.finditer(r"#(\d+)\s*=\s*PRODUCT\s*\(\s*'([^']*)'\s*,\s*'([^']*)'", text):
        ent_product[m.group(1)] = (m.group(3) or m.group(2) or "").strip()

    # formation entity# -> product name.
    # PRODUCT_DEFINITION_FORMATION[_WITH_SPECIFIED_SOURCE] ( 'id','desc', #product, ... )
    # Take the first #ref after the two quoted args = the product entity.
    pdf_to_product = {}
    for m in re.finditer(
            r"#(\d+)\s*=\s*PRODUCT_DEFINITION_FORMATION(?:_WITH_SPECIFIED_SOURCE)?\s*"
            r"\(\s*'[^']*'\s*,\s*'[^']*'\s*,\s*#(\d+)", text):
        prod = ent_product.get(m.group(2))
        if prod:
            pdf_to_product[m.group(1)] = prod

    # product_definition entity# -> product name.
    # PRODUCT_DEFINITION ( 'id','desc', #formation, #context ) — first #ref = formation.
    pd_to_product = {}
    for m in re.finditer(
            r"#(\d+)\s*=\s*PRODUCT_DEFINITION\s*\(\s*'[^']*'\s*,\s*'[^']*'\s*,\s*#(\d+)", text):
        prod = pdf_to_product.get(m.group(2))
        if prod:
            pd_to_product[m.group(1)] = prod

    # NEXT_ASSEMBLY_USAGE_OCCURRENCE ( 'id',' ',' ', #parentPD, #childPD, ... )
    nauo_edges = []
    for m in re.finditer(
            r"NEXT_ASSEMBLY_USAGE_OCCURRENCE\s*\(\s*'[^']*'\s*,\s*'[^']*'\s*,\s*'[^']*'\s*,\s*"
            r"#(\d+)\s*,\s*#(\d+)", text):
        nauo_edges.append((m.group(1), m.group(2)))
    return pd_to_product, nauo_edges


def extract_nodes(path, max_depth=8):
    """Nested [{name, children:[...]}] assembly tree built from NAUO parent/child."""
    text = _read(path)
    pd2name, edges = _build_graph(text)
    if not edges:
        # flat fallback: every product as a leaf under a synthetic root
        comps = extract_components(path)
        return [{"name": c["name"]} for c in comps]
    children = {}
    all_children = set()
    for parent, child in edges:
        children.setdefault(parent, []).append(child)
        all_children.add(child)
    roots = [pd for pd in children if pd not in all_children]

    def build(pd, depth):
        node = {"name": pd2name.get(pd, f"pd_{pd}")}
        if depth < max_depth and pd in children:
            kids = [build(c, depth + 1) for c in children[pd]]
            if kids:
                node["children"] = kids
        return node

    return [build(r, 0) for r in roots] if roots else [{"name": pd2name.get(p, f"pd_{p}")} for p in children]


def extract_subassemblies(path):
    """[{name, instances}] — top-level subassemblies with instance counts."""
    nodes = extract_nodes(path)

    def count(n):
        return 1 + sum(count(c) for c in n.get("children", []))
    return [{"name": n["name"], "instances": count(n)} for n in nodes]


def extract_bom(path):
    """Name-level BOM from STEP text — no geometry kernel needed.

    Quantity = how many times a part appears as a child in a
    NEXT_ASSEMBLY_USAGE_OCCURRENCE (i.e. how many times it is placed into some
    parent). A part that never appears as a child (the top assembly) gets qty 1.

    Returns a dict:
      {
        "source": "STEP-text",
        "geometry": False,            # honest: no volume/mass/material
        "confidence": "medium",
        "total_instances": <int>,
        "unique_parts": <int>,
        "unresolved_instances": <int>,  # NAUO children whose PRODUCT name we
                                        # couldn't resolve (counted, not faked)
        "items": [{"name", "qty"}, ...] # sorted by qty desc
      }

    This is a NAME-level BOM only: no volume, mass, or material. Those require a
    geometry kernel (cadquery) or SolidWorks and are surfaced by the geometry /
    macro paths instead. Callers must present this as name-level.
    """
    text = _read(path)
    pd2name, nauo = _build_graph(text)

    qty = {}
    unresolved = 0
    children = set()
    for parent, child in nauo:
        children.add(child)
        name = pd2name.get(child)
        if name:
            qty[name] = qty.get(name, 0) + 1
        else:
            unresolved += 1

    # Root products (never a child) — present once each if we know their name.
    all_pd = set(pd2name.keys())
    roots = all_pd - children
    for pd in roots:
        name = pd2name.get(pd)
        if name and name not in qty:
            qty[name] = 1

    items = sorted(({"name": n, "qty": q} for n, q in qty.items()),
                   key=lambda it: (-it["qty"], it["name"]))
    total = sum(it["qty"] for it in items) + unresolved
    return {
        "source": "STEP-text",
        "geometry": False,
        "confidence": "medium",
        "total_instances": total,
        "unique_parts": len(items),
        "unresolved_instances": unresolved,
        "items": items,
    }


def extract_edges(path):
    """Adjacency edges with an explicit provenance flag.

    Returns (edges, names, graph_type):
      - graph_type == "geometric": real surface contact from the geometry kernel
        ("who touches whom"). Only when cadquery/OCC is present and the assembly
        isn't deferred for size.
      - graph_type == "hierarchy_fallback": assembly parent->child links from
        NAUO ("who belongs to whom"). This is NOT geometric contact; callers must
        label it as such and never present it as a true adjacency graph.

    The hierarchy fallback keeps a `pd_<id>` placeholder name when a NAUO node's
    PRODUCT name can't be resolved, so real assemblies (where the PD->PRODUCT
    chain is sparse) still yield edges instead of silently dropping all of them.
    """
    path = resolve_step_path(path)
    # try real geometry first
    try:
        import step_geometry as SG
        if SG.available():
            adj = SG.adjacency(path)
            if not adj.get("too_large") and adj.get("edges"):
                return ([{"a": e["pair"][0], "b": e["pair"][1]} for e in adj["edges"]],
                        [f"solid_{s['index']}" for s in SG.read_structure(path)],
                        "geometric")
    except Exception:
        pass
    # fallback: NAUO assembly relationships (hierarchy, NOT geometric contact)
    text = _read(path)
    pd2name, nauo = _build_graph(text)
    edges = []
    for parent, child in nauo:
        a = pd2name.get(parent) or f"pd_{parent}"
        b = pd2name.get(child) or f"pd_{child}"
        edges.append({"a": a, "b": b})
    return edges, None, "hierarchy_fallback"
