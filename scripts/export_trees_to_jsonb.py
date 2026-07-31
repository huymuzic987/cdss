"""Export decision trees from backups/seed.sql into single JSONB files per tree.

Reads backups/seed.sql (the source of truth) and writes backups/DecisionTreeJSONB/{tree_key}.jsonb
containing the tree metadata, decision nodes, decision edges (transitions), and guideline citations (references).
"""

import json
import re
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEED_SQL_PATH = PROJECT_ROOT / "backups" / "seed.sql"
JSONB_DIR = PROJECT_ROOT / "backups" / "DecisionTreeJSONB"


def parse_sql_literal(val_str: str):
    """Parse a single SQL column value from an INSERT statement VALUES tuple."""
    val_str = val_str.strip()
    if val_str.upper() == "NULL":
        return None
    if val_str.startswith("ARRAY["):
        m = re.search(r"ARRAY\[(.*?)\]", val_str)
        if m and m.group(1).strip():
            return [int(x.strip()) for x in m.group(1).split(",") if x.strip()]
        return None
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


def export_trees():
    content = SEED_SQL_PATH.read_text(encoding="utf-8")
    JSONB_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Parse decision_trees
    trees = {}  # tree_key -> dict of tree data
    tree_key_to_id = {}
    tree_id_to_key = {}

    pattern_trees = re.compile(
        r"INSERT INTO public\.decision_trees\s*\([^)]+\)\s*VALUES\s*\((.*?)\)\s*ON CONFLICT",
        re.DOTALL,
    )
    for m in pattern_trees.finditer(content):
        vals = [parse_sql_literal(tok) for tok in split_sql_values(m.group(1))]
        tree_id = vals[0]
        tree_key = vals[1]
        name_en = vals[2]
        name_vi = vals[3]
        created_at = vals[4]
        updated_at = vals[5]

        tree_key_to_id[tree_key] = tree_id
        tree_id_to_key[tree_id] = tree_key

        trees[tree_key] = {
            "id": tree_id,
            "tree_key": tree_key,
            "name_en": name_en,
            "name_vi": name_vi,
            "created_at": created_at,
            "updated_at": updated_at,
            "nodes": {},
        }

    # Helper mapping for nodes
    node_id_to_info = {}  # node_id -> (tree_key, node_key)
    node_pair_to_id = {}  # (tree_key, node_key) -> node_id

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

        node_id = parse_sql_literal(tokens[0])
        node_key = parse_sql_literal(tokens[2])
        node_type_str = parse_sql_literal(tokens[3]).split("::")[0].strip("'")

        created_at = parse_sql_literal(tokens[13]) if len(tokens) > 13 else None
        updated_at = parse_sql_literal(tokens[14]) if len(tokens) > 14 else None

        node_data = {
            "id": node_id,
            "node_key": node_key,
            "node_type": node_type_str,
            "text_en": parse_sql_literal(tokens[4]),
            "text_vi": parse_sql_literal(tokens[5]),
            "condition_definition": parse_sql_literal(tokens[6]),
            "context_patch": parse_sql_literal(tokens[7]),
            "action_payload": parse_sql_literal(tokens[8]),
            "global_config": parse_sql_literal(tokens[9]),
            "link_target_tree_key": parse_sql_literal(tokens[10]),
            "link_target_node_key": parse_sql_literal(tokens[11]),
            "display_order": int(parse_sql_literal(tokens[12])),
            "created_at": created_at,
            "updated_at": updated_at,
            "references": [],
            "transitions": [],
        }

        trees[tkey]["nodes"][node_key] = node_data
        node_id_to_info[node_id] = (tkey, node_key)
        node_pair_to_id[(tkey, node_key)] = node_id

    def resolve_node(tok: str) -> tuple[str | None, str | None, str | None]:
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
                if lit in node_id_to_info:
                    tk, nk = node_id_to_info[lit]
                    return tk, nk, lit
        return None, None, None

    # 3. Parse decision_edges
    pattern_edges = re.compile(
        r"INSERT INTO public\.decision_edges\s*\([^)]+\)\s*VALUES\s*\((.*?)\)\s*ON CONFLICT",
        re.DOTALL,
    )
    for m in pattern_edges.finditer(content):
        tokens = split_sql_values(m.group(1))
        edge_id = parse_sql_literal(tokens[0])

        from_tkey, from_nkey, from_id = resolve_node(tokens[1])
        to_tkey, to_nkey, to_id = resolve_node(tokens[2])
        traversal_order = int(parse_sql_literal(tokens[3]))

        if from_tkey and from_nkey and to_nkey:
            from_node = trees[from_tkey]["nodes"][from_nkey]
            to_node = trees[to_tkey]["nodes"].get(to_nkey) if to_tkey in trees else None
            candidate_condition = to_node["condition_definition"] if to_node else None

            from_node["transitions"].append(
                {
                    "edge_id": edge_id,
                    "traversal_order": traversal_order,
                    "to_node_key": to_nkey,
                    "candidate_condition": candidate_condition,
                }
            )

    # 4. Parse node_source_references
    pattern_refs = re.compile(
        r"INSERT INTO public\.node_source_references\s*\([^)]+\)\s*VALUES\s*\((.*?)\)\s*ON CONFLICT",
        re.DOTALL,
    )
    for m in pattern_refs.finditer(content):
        tokens = split_sql_values(m.group(1))
        ref_id = parse_sql_literal(tokens[0])
        ref_tkey, ref_nkey, node_id = resolve_node(tokens[1])

        if ref_tkey and ref_nkey:
            source_title = parse_sql_literal(tokens[2])
            section_path = parse_sql_literal(tokens[3])
            locator = parse_sql_literal(tokens[4])
            locator_detail = parse_sql_literal(tokens[5])
            printed_pages = parse_sql_literal(tokens[6])
            pdf_pages = parse_sql_literal(tokens[7])
            reference_note = parse_sql_literal(tokens[8])
            ref_order = int(parse_sql_literal(tokens[9]))

            ref_data = {
                "id": ref_id,
                "source_title": source_title,
                "section_path": section_path,
                "locator": locator,
                "locator_detail": locator_detail,
                "printed_page_numbers": printed_pages,
                "pdf_page_numbers": pdf_pages,
                "reference_note": reference_note,
                "reference_order": ref_order,
            }
            trees[ref_tkey]["nodes"][ref_nkey]["references"].append(ref_data)

    # Sort transitions and references & compute entry / root / global node keys
    exported_count = 0
    for tkey, tdata in sorted(trees.items()):
        nodes = tdata["nodes"]

        # Sort transitions by traversal_order
        for nkey, ndata in nodes.items():
            ndata["transitions"].sort(key=lambda t: t["traversal_order"])
            ndata["references"].sort(key=lambda r: r["reference_order"])

        start_nodes = [k for k, n in nodes.items() if n["node_type"] == "START"]
        global_nodes = [k for k, n in nodes.items() if n["node_type"] == "GLOBAL"]
        root_nodes = sorted(list(set(start_nodes + global_nodes)))

        doc = {
            "format": "cdss-traversal-graph",
            "format_version": 1,
            "source": "backups/seed.sql",
            "traversal_semantics": {
                "entry": "entry_node_keys",
                "node_lookup": "trees[].nodes[node_key]",
                "branch_priority": "transitions sorted by traversal_order ascending",
                "branch_condition": "condition_definition on the target node; copied to candidate_condition",
                "cross_tree_jump": "LINK nodes use link_target_tree_key and optional link_target_node_key",
            },
            "document_type": "decision_tree",
            "tree": {
                "id": tdata["id"],
                "tree_key": tdata["tree_key"],
                "name_en": tdata["name_en"],
                "name_vi": tdata["name_vi"],
                "created_at": tdata["created_at"],
                "updated_at": tdata["updated_at"],
                "entry_node_keys": start_nodes,
                "root_node_keys": root_nodes,
                "global_node_keys": global_nodes,
                "nodes": nodes,
            },
        }

        out_path = JSONB_DIR / f"{tkey}.jsonb"
        out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        exported_count += 1
        print(f"Exported {tkey}.jsonb ({len(nodes)} nodes)")

    print(f"\nSuccessfully exported {exported_count} decision tree JSONB files to {JSONB_DIR}")


if __name__ == "__main__":
    export_trees()
