"""Verify JSONB trees match the trees in backups/seed.sql."""

import json
import re
import uuid
from pathlib import Path
from typing import Any

import pytest

from cdss.domain.decision_tree.contracts import NodeType
from cdss.domain.decision_tree.graph import (
    EdgeDefinition,
    NodeDefinition,
    SourceReferenceDefinition,
    TreeDefinition,
    TreeGraph,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SEED_SQL_PATH = PROJECT_ROOT / "backups" / "seed.sql"
JSONB_DIR = PROJECT_ROOT / "backups" / "DecisionTreeJSONB"


def parse_sql_literal(val_str: str) -> Any:
    """Parse a single SQL column value from an INSERT statement VALUES tuple."""
    val_str = val_str.strip()
    if val_str.upper() == "NULL":
        return None
    if val_str.startswith("ARRAY["):
        m = re.search(r"ARRAY\[(.*?)\]", val_str)
        if m and m.group(1).strip():
            return tuple(int(x.strip()) for x in m.group(1).split(",") if x.strip())
        return ()
    if val_str.startswith("'"):
        m = re.match(r"^'((?:[^']|'')*)'", val_str, re.DOTALL)
        if not m:
            raise ValueError(f"Could not parse string literal: {val_str[:50]}")
        raw = m.group(1).replace("''", "'")
        rest = val_str[m.end() :].strip()
        if rest.startswith("::jsonb"):
            return json.loads(raw)
        return raw
    if re.match(r"^-?\d+$", val_str):
        return int(val_str)
    return val_str


def split_sql_values(values_text: str) -> list[str]:
    """Split comma-separated SQL values inside a VALUES (...) clause."""
    tokens = []
    current = []
    in_quote = False
    in_paren = 0
    in_bracket = 0
    i = 0
    n = len(values_text)

    while i < n:
        ch = values_text[i]
        if ch == "'":
            if in_quote and i + 1 < n and values_text[i + 1] == "'":
                current.append("''")
                i += 2
                continue
            in_quote = not in_quote
            current.append(ch)
            i += 1
            continue

        if not in_quote:
            if ch == "(":
                in_paren += 1
            elif ch == ")":
                in_paren -= 1
            elif ch == "[":
                in_bracket += 1
            elif ch == "]":
                in_bracket -= 1
            elif ch == "," and in_paren == 0 and in_bracket == 0:
                tokens.append("".join(current).strip())
                current = []
                i += 1
                continue

        current.append(ch)
        i += 1

    if current:
        tokens.append("".join(current).strip())

    return tokens


def parse_seed_sql_trees(sql_path: Path = SEED_SQL_PATH) -> dict[str, TreeGraph]:
    content = sql_path.read_text(encoding="utf-8")

    tree_defs: dict[str, TreeDefinition] = {}
    tree_id_to_key: dict[uuid.UUID, str] = {}
    tree_key_to_id: dict[str, uuid.UUID] = {}

    nodes_by_tree: dict[str, list[NodeDefinition]] = {}
    node_id_to_info: dict[uuid.UUID, tuple[str, str]] = {}  # node_id -> (tree_key, node_key)
    node_pair_to_id: dict[tuple[str, str], uuid.UUID] = {}  # (tree_key, node_key) -> node_id

    edges_by_tree: dict[str, list[tuple[uuid.UUID, uuid.UUID, uuid.UUID, int]]] = {}
    references_by_tree: dict[str, list[SourceReferenceDefinition]] = {}

    # 1. Parse decision_trees
    pattern_trees = re.compile(
        r"INSERT INTO public\.decision_trees\s*\([^)]+\)\s*VALUES\s*\((.*?)\)\s*ON CONFLICT",
        re.DOTALL,
    )
    for m in pattern_trees.finditer(content):
        vals = [parse_sql_literal(tok) for tok in split_sql_values(m.group(1))]
        tree_id = uuid.UUID(vals[0])
        tree_key = vals[1]
        name_en = vals[2]
        name_vi = vals[3]

        tree_def = TreeDefinition(id=tree_id, tree_key=tree_key, name_en=name_en, name_vi=name_vi)
        tree_defs[tree_key] = tree_def
        tree_id_to_key[tree_id] = tree_key
        tree_key_to_id[tree_key] = tree_id
        nodes_by_tree[tree_key] = []
        edges_by_tree[tree_key] = []
        references_by_tree[tree_key] = []

    # 2. Parse decision_nodes
    pattern_nodes = re.compile(
        r"INSERT INTO public\.decision_nodes\s*\([^)]+\)\s*VALUES\s*\((.*?)\)\s*ON CONFLICT",
        re.DOTALL,
    )
    for m in pattern_nodes.finditer(content):
        tokens = split_sql_values(m.group(1))

        tree_key_match = re.search(r"tree_key\s*=\s*'([^']+)'", tokens[1])
        if not tree_key_match:
            continue
        tkey = tree_key_match.group(1)
        tree_id = tree_key_to_id[tkey]

        node_id = uuid.UUID(parse_sql_literal(tokens[0]))
        node_key = parse_sql_literal(tokens[2])
        node_type_str = parse_sql_literal(tokens[3]).split("::")[0].strip("'")

        node_def = NodeDefinition(
            id=node_id,
            tree_id=tree_id,
            node_key=node_key,
            node_type=NodeType(node_type_str),
            text_en=parse_sql_literal(tokens[4]),
            text_vi=parse_sql_literal(tokens[5]),
            condition_definition=parse_sql_literal(tokens[6]),
            context_patch=parse_sql_literal(tokens[7]),
            action_payload=parse_sql_literal(tokens[8]),
            global_config=parse_sql_literal(tokens[9]),
            link_target_tree_key=parse_sql_literal(tokens[10]),
            link_target_node_key=parse_sql_literal(tokens[11]),
            display_order=int(parse_sql_literal(tokens[12])),
        )
        nodes_by_tree[tkey].append(node_def)
        node_id_to_info[node_id] = (tkey, node_key)
        node_pair_to_id[(tkey, node_key)] = node_id

    def resolve_node(tok: str) -> tuple[str | None, str | None, uuid.UUID | None]:
        tok = tok.strip()
        if tok.startswith("("):
            m_t = re.search(r"tree_key\s*=\s*'([^']+)'", tok)
            m_n = re.search(r"node_key\s*=\s*'([^']+)'", tok)
            if m_t and m_n:
                tk, nk = m_t.group(1), m_n.group(1)
                return tk, nk, node_pair_to_id.get((tk, nk))
        else:
            lit = parse_sql_literal(tok)
            if isinstance(lit, str) and len(lit) == 36:
                uid = uuid.UUID(lit)
                if uid in node_id_to_info:
                    tk, nk = node_id_to_info[uid]
                    return tk, nk, uid
        return None, None, None

    # 3. Parse decision_edges
    pattern_edges = re.compile(
        r"INSERT INTO public\.decision_edges\s*\([^)]+\)\s*VALUES\s*\((.*?)\)\s*ON CONFLICT",
        re.DOTALL,
    )
    for m in pattern_edges.finditer(content):
        tokens = split_sql_values(m.group(1))
        edge_id = uuid.UUID(parse_sql_literal(tokens[0]))

        from_tkey, from_nkey, from_id = resolve_node(tokens[1])
        to_tkey, to_nkey, to_id = resolve_node(tokens[2])
        traversal_order = int(parse_sql_literal(tokens[3]))

        if from_tkey and from_id and to_id:
            edges_by_tree[from_tkey].append((edge_id, from_id, to_id, traversal_order))

    # 4. Parse node_source_references
    pattern_refs = re.compile(
        r"INSERT INTO public\.node_source_references\s*\([^)]+\)\s*VALUES\s*"
        r"\((.*?)\)\s*ON CONFLICT",
        re.DOTALL,
    )
    for m in pattern_refs.finditer(content):
        tokens = split_sql_values(m.group(1))
        ref_id = uuid.UUID(parse_sql_literal(tokens[0]))
        ref_tkey, ref_nkey, node_id = resolve_node(tokens[1])

        if ref_tkey and node_id:
            source_title = parse_sql_literal(tokens[2])
            section_path = parse_sql_literal(tokens[3])
            locator = parse_sql_literal(tokens[4])
            locator_detail = parse_sql_literal(tokens[5])
            printed_pages = parse_sql_literal(tokens[6])
            pdf_pages = parse_sql_literal(tokens[7])
            reference_note = parse_sql_literal(tokens[8])
            ref_order = int(parse_sql_literal(tokens[9]))

            ref_def = SourceReferenceDefinition(
                id=ref_id,
                node_id=node_id,
                source_title=source_title,
                section_path=section_path,
                reference_order=ref_order,
                locator=locator,
                locator_detail=locator_detail,
                printed_page_numbers=tuple(printed_pages) if printed_pages else None,
                pdf_page_numbers=tuple(pdf_pages) if pdf_pages else None,
                reference_note=reference_note,
            )
            references_by_tree[ref_tkey].append(ref_def)

    # Build TreeGraph objects
    graphs: dict[str, TreeGraph] = {}
    for tkey, tree_def in tree_defs.items():
        tree_edges = [
            EdgeDefinition(
                id=eid,
                from_node_id=fid,
                to_node_id=tid,
                traversal_order=order,
                from_tree_id=tree_def.id,
                to_tree_id=tree_def.id,
            )
            for eid, fid, tid, order in edges_by_tree[tkey]
        ]
        graphs[tkey] = TreeGraph.build(
            tree=tree_def,
            nodes=nodes_by_tree[tkey],
            edges=tree_edges,
            references=references_by_tree[tkey],
        )

    return graphs


def load_tree_graph_from_jsonb(file_path: Path) -> TreeGraph:
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    tree_data = data["tree"]
    tree_id = uuid.UUID(tree_data["id"]) if "id" in tree_data else uuid.uuid4()

    tree_def = TreeDefinition(
        id=tree_id,
        tree_key=tree_data["tree_key"],
        name_en=tree_data["name_en"],
        name_vi=tree_data["name_vi"],
    )

    nodes_dict = tree_data["nodes"]
    node_key_to_id: dict[str, uuid.UUID] = {}
    nodes: list[NodeDefinition] = []
    edges: list[EdgeDefinition] = []
    references: list[SourceReferenceDefinition] = []

    for node_key, n in nodes_dict.items():
        nid = uuid.UUID(n["id"]) if n.get("id") else uuid.uuid4()
        node_key_to_id[node_key] = nid

        node_def = NodeDefinition(
            id=nid,
            tree_id=tree_id,
            node_key=node_key,
            node_type=NodeType(n["node_type"]),
            text_en=n["text_en"],
            text_vi=n["text_vi"],
            condition_definition=n.get("condition_definition"),
            context_patch=n.get("context_patch"),
            action_payload=n.get("action_payload"),
            global_config=n.get("global_config"),
            link_target_tree_key=n.get("link_target_tree_key"),
            link_target_node_key=n.get("link_target_node_key"),
            display_order=n.get("display_order", 0),
        )
        nodes.append(node_def)

        for ref in n.get("references", []):
            references.append(
                SourceReferenceDefinition(
                    id=uuid.uuid4(),
                    node_id=nid,
                    source_title=ref["source_title"],
                    section_path=ref.get("section_path"),
                    reference_order=ref.get("reference_order", 0),
                    locator=ref.get("locator"),
                    locator_detail=ref.get("locator_detail"),
                    printed_page_numbers=tuple(ref["printed_page_numbers"])
                    if ref.get("printed_page_numbers")
                    else None,
                    pdf_page_numbers=tuple(ref["pdf_page_numbers"])
                    if ref.get("pdf_page_numbers")
                    else None,
                    reference_note=ref.get("reference_note"),
                )
            )

    for node_key, n in nodes_dict.items():
        from_id = node_key_to_id[node_key]
        for t in n.get("transitions", []):
            to_id = node_key_to_id.get(t["to_node_key"])
            if to_id:
                edges.append(
                    EdgeDefinition(
                        id=uuid.UUID(t["edge_id"]) if t.get("edge_id") else uuid.uuid4(),
                        from_node_id=from_id,
                        to_node_id=to_id,
                        traversal_order=t["traversal_order"],
                        from_tree_id=tree_id,
                        to_tree_id=tree_id,
                    )
                )

    return TreeGraph.build(tree=tree_def, nodes=nodes, edges=edges, references=references)


@pytest.fixture(scope="module")
def sql_tree_graphs():
    return parse_seed_sql_trees()


def test_jsonb_trees_match_seed_sql(sql_tree_graphs):
    jsonb_files = list(JSONB_DIR.glob("*.jsonb"))
    tree_files = [f for f in jsonb_files if f.stem not in ("medicines", "symptoms")]

    discrepancies: list[str] = []

    if len(tree_files) != len(sql_tree_graphs):
        discrepancies.append(
            f"Tree count mismatch: {len(tree_files)} JSONB files vs "
            f"{len(sql_tree_graphs)} trees in seed.sql"
        )

    for jsonb_file in sorted(tree_files):
        json_graph = load_tree_graph_from_jsonb(jsonb_file)
        tree_key = json_graph.tree.tree_key

        if tree_key not in sql_tree_graphs:
            discrepancies.append(
                f"Tree key '{tree_key}' from {jsonb_file.name} not found in seed.sql"
            )
            continue
        sql_graph = sql_tree_graphs[tree_key]

        # 1. Compare Tree Metadata
        if json_graph.tree.name_en != sql_graph.tree.name_en:
            discrepancies.append(
                f"[{tree_key}] name_en mismatch: '{json_graph.tree.name_en}' (JSONB) "
                f"vs '{sql_graph.tree.name_en}' (SQL)"
            )
        if json_graph.tree.name_vi != sql_graph.tree.name_vi:
            discrepancies.append(
                f"[{tree_key}] name_vi mismatch: '{json_graph.tree.name_vi}' (JSONB) "
                f"vs '{sql_graph.tree.name_vi}' (SQL)"
            )

        # 2. Compare Nodes Count & Set of Keys
        json_node_keys = set(json_graph.nodes_by_key.keys())
        sql_node_keys = set(sql_graph.nodes_by_key.keys())

        missing_in_jsonb = sql_node_keys - json_node_keys
        extra_in_jsonb = json_node_keys - sql_node_keys

        if missing_in_jsonb:
            discrepancies.append(f"[{tree_key}] Nodes missing in JSONB: {missing_in_jsonb}")
        if extra_in_jsonb:
            discrepancies.append(f"[{tree_key}] Extra nodes in JSONB: {extra_in_jsonb}")

        common_keys = json_node_keys & sql_node_keys

        # 3. Compare Node Details
        for key in common_keys:
            jn = json_graph.nodes_by_key[key]
            sn = sql_graph.nodes_by_key[key]

            if jn.node_type != sn.node_type:
                discrepancies.append(
                    f"[{tree_key}:{key}] node_type mismatch: {jn.node_type} vs {sn.node_type}"
                )
            if jn.text_en != sn.text_en:
                discrepancies.append(f"[{tree_key}:{key}] text_en mismatch")
            if jn.text_vi != sn.text_vi:
                discrepancies.append(f"[{tree_key}:{key}] text_vi mismatch")
            if jn.condition_definition != sn.condition_definition:
                discrepancies.append(f"[{tree_key}:{key}] condition_definition mismatch")
            if jn.context_patch != sn.context_patch:
                discrepancies.append(f"[{tree_key}:{key}] context_patch mismatch")
            if jn.action_payload != sn.action_payload:
                discrepancies.append(f"[{tree_key}:{key}] action_payload mismatch")
            if jn.global_config != sn.global_config:
                discrepancies.append(f"[{tree_key}:{key}] global_config mismatch")
            if jn.link_target_tree_key != sn.link_target_tree_key:
                discrepancies.append(f"[{tree_key}:{key}] link_target_tree_key mismatch")
            if jn.link_target_node_key != sn.link_target_node_key:
                discrepancies.append(f"[{tree_key}:{key}] link_target_node_key mismatch")
            if jn.display_order != sn.display_order:
                discrepancies.append(
                    f"[{tree_key}:{key}] display_order mismatch: "
                    f"{jn.display_order} vs {sn.display_order}"
                )

        # 4. Compare Outgoing Edges
        for key in common_keys:
            j_node = json_graph.nodes_by_key[key]
            s_node = sql_graph.nodes_by_key[key]

            j_outgoing = json_graph.outgoing_edges_by_node_id.get(j_node.id, ())
            s_outgoing = sql_graph.outgoing_edges_by_node_id.get(s_node.id, ())

            j_edges = sorted(
                [
                    (json_graph.nodes_by_id[e.to_node_id].node_key, e.traversal_order)
                    for e in j_outgoing
                ],
                key=lambda x: (x[0], x[1]),
            )
            s_edges = sorted(
                [
                    (sql_graph.nodes_by_id[e.to_node_id].node_key, e.traversal_order)
                    for e in s_outgoing
                ],
                key=lambda x: (x[0], x[1]),
            )
            if j_edges != s_edges:
                discrepancies.append(
                    f"[{tree_key}:{key}] Outgoing edges mismatch:\n"
                    f"  JSONB: {j_edges}\n  SQL:   {s_edges}"
                )

    if discrepancies:
        msg = (
            f"Found {len(discrepancies)} discrepancies between JSONB trees and seed.sql:\n"
            + "\n".join(discrepancies)
        )
        pytest.fail(msg)


def test_inference_key_prefix_matches_persisted_node_type(sql_tree_graphs) -> None:
    mismatches = [
        f"{tree_key}:{node.node_key}:{node.node_type.value}"
        for tree_key, graph in sql_tree_graphs.items()
        for node in graph.nodes_by_id.values()
        if ("_INFERENCE_" in node.node_key) != (node.node_type is NodeType.INFERENCE)
    ]

    assert mismatches == []


def test_combine_inference_never_encodes_or_alternatives(sql_tree_graphs) -> None:
    invalid = [
        f"{tree_key}:{node.node_key}"
        for tree_key, graph in sql_tree_graphs.items()
        for node in graph.nodes_by_id.values()
        if node.node_type is NodeType.INFERENCE
        and re.match(r"^T\d+_INFERENCE_COMBINE_", node.node_key)
        and ("_OR_" in node.node_key or " or " in node.text_en.casefold())
    ]

    assert invalid == []


def test_every_inference_uses_the_canonical_key_grammar(sql_tree_graphs) -> None:
    keywords = {
        "DETERMINE",
        "CLASSIFY",
        "SET",
        "RESTORE",
        "EVALUATE",
        "COMPARE",
        "TEST",
        "START",
        "ADD",
        "COMBINE",
        "SELECT",
        "ADJUST",
        "CHANGE",
        "ESCALATE",
        "REDUCE",
        "STOP",
        "KEEP",
        "MAINTAIN",
        "MONITOR",
        "AVOID",
    }
    invalid = []
    for tree_key, graph in sql_tree_graphs.items():
        for node in graph.nodes_by_id.values():
            if node.node_type is not NodeType.INFERENCE:
                continue
            match = re.match(r"^T\d+_INFERENCE_([A-Z]+)_[A-Z0-9_]+$", node.node_key)
            if match is None or match.group(1) not in keywords:
                invalid.append(f"{tree_key}:{node.node_key}")

    assert invalid == []
