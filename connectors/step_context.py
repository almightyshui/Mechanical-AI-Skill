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


def _read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def is_step(path):
    return str(path).lower().endswith((".step", ".stp"))


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
    """
    # entity id -> product name, via #id=PRODUCT('id','name',...)
    ent_product = {}  # entity#  -> product name
    for m in re.finditer(r"#(\d+)\s*=\s*PRODUCT\s*\(\s*'([^']*)'\s*,\s*'([^']*)'", text):
        ent_product[m.group(1)] = (m.group(3) or m.group(2) or "").strip()

    # PRODUCT_DEFINITION_FORMATION[_WITH_SPECIFIED_SOURCE]( ... , #productEnt )
    pdf_to_product = {}  # formation entity# -> product name
    for m in re.finditer(r"#(\d+)\s*=\s*PRODUCT_DEFINITION_FORMATION(?:_WITH_SPECIFIED_SOURCE)?\s*\([^)]*#(\d+)\s*\)", text):
        prod = ent_product.get(m.group(2))
        if prod:
            pdf_to_product[m.group(1)] = prod

    # PRODUCT_DEFINITION( ... , #formationEnt , ... ) -> product name
    pd_to_product = {}  # product_definition entity# -> product name
    for m in re.finditer(r"#(\d+)\s*=\s*PRODUCT_DEFINITION\s*\([^)]*?#(\d+)", text):
        prod = pdf_to_product.get(m.group(2))
        if prod:
            pd_to_product[m.group(1)] = prod

    # NEXT_ASSEMBLY_USAGE_OCCURRENCE(..., #parentPD, #childPD, ...)
    nauo_edges = []
    for m in re.finditer(r"NEXT_ASSEMBLY_USAGE_OCCURRENCE\s*\(\s*'[^']*'\s*,\s*'[^']*'\s*,\s*'[^']*'\s*,\s*#(\d+)\s*,\s*#(\d+)", text):
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


def extract_edges(path):
    """Adjacency edges. Prefer real geometric contact (if geometry kernel present);
    else use assembly-relationship edges from NAUO (parent-child = connected)."""
    # try geometry first
    try:
        import step_geometry as SG
        if SG.available():
            adj = SG.adjacency(path)
            if not adj.get("too_large") and adj.get("edges"):
                return [{"a": e["pair"][0], "b": e["pair"][1]} for e in adj["edges"]], \
                       [f"solid_{s['index']}" for s in SG.read_structure(path)]
    except Exception:
        pass
    # fallback: NAUO assembly edges (names)
    text = _read(path)
    pd2name, nauo = _build_graph(text)
    edges = []
    for parent, child in nauo:
        a, b = pd2name.get(parent), pd2name.get(child)
        if a and b:
            edges.append({"a": a, "b": b})
    return edges, None
