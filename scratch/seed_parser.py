"""Offline parser: reconstruct TreeGraph objects straight from backups/cdss_merged.sql,
without a live Postgres connection, so the real domain/FHIR code can be exercised.
"""

from __future__ import annotations

import json
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cdss.domain.decision_tree.contracts import NodeType  # noqa: E402
from cdss.domain.decision_tree.graph import (  # noqa: E402
    EdgeDefinition,
    NodeDefinition,
    SourceReferenceDefinition,
    TreeDefinition,
    TreeGraph,
)

SQL_PATH = Path(__file__).resolve().parent.parent / "backups" / "cdss_merged.sql"


def strip_sql_line_comments(text: str) -> str:
    """Remove '-- ...' line comments, respecting single-quoted strings (with '' escapes)."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "'":
            out.append(ch)
            i += 1
            while i < n:
                if text[i : i + 2] == "''":
                    out.append("''")
                    i += 2
                    continue
                out.append(text[i])
                if text[i] == "'":
                    i += 1
                    break
                i += 1
            continue
        if text[i : i + 2] == "--":
            nl = text.find("\n", i)
            if nl == -1:
                break
            i = nl
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def find_matching_paren(text: str, open_idx: int) -> int:
    """text[open_idx] must be '('. Return index of the matching ')'."""
    assert text[open_idx] == "("
    depth = 0
    i = open_idx
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "'":
            i += 1
            while i < n:
                if text[i] == "'" and (i + 1 >= n or text[i + 1] != "'"):
                    break
                if text[i] == "'" and text[i + 1] == "'":
                    i += 2
                    continue
                i += 1
            i += 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("unbalanced parens")


def split_top_level(text: str) -> list[str]:
    """Split text on top-level commas (outside quotes/parens)."""
    parts: list[str] = []
    depth = 0
    i = 0
    n = len(text)
    start = 0
    while i < n:
        ch = text[i]
        if ch == "'":
            i += 1
            while i < n:
                if text[i] == "'" and text[i : i + 2] != "''":
                    break
                if text[i : i + 2] == "''":
                    i += 2
                    continue
                i += 1
            i += 1
            continue
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(text[start:i])
            start = i + 1
        i += 1
    parts.append(text[start:])
    return [p.strip() for p in parts]


def parse_scalar(token: str):
    token = token.strip()
    if token.upper().startswith("NULL"):
        return None
    if token.startswith("gen_random_uuid()"):
        return str(uuid.uuid4())
    if token.startswith("now()"):
        return None
    if token.startswith("ARRAY["):
        close = token.index("]")
        inner = token[len("ARRAY[") : close]
        return [int(x.strip()) for x in inner.split(",") if x.strip()]
    if token.startswith("'"):
        # find matching closing quote (handle '' escapes), then optional ::cast
        m = re.match(r"'((?:[^']|'')*)'", token, re.S)
        assert m, f"bad quoted token: {token!r}"
        raw = m.group(1).replace("''", "'")
        rest = token[m.end() :].strip()
        if rest.startswith("::jsonb"):
            return json.loads(raw)
        return raw
    # bare number
    try:
        return int(token)
    except ValueError:
        return token


def extract_cte_body(statement: str, cte_name: str) -> str | None:
    marker = f"{cte_name} ("
    idx = statement.find(marker)
    if idx == -1:
        # The accepted form already includes '(' immediately after the CTE name.
        return None
    # careful: this '(' is the column-list paren, not the AS ( body. Find "AS (" after it.
    close_idx = find_matching_paren(statement, statement.find("(", idx))
    as_idx = statement.find("AS", close_idx)
    body_open = statement.find("(", as_idx)
    body_close = find_matching_paren(statement, body_open)
    return statement[body_open + 1 : body_close]


def parse_values_rows(cte_body: str) -> list[list]:
    body = cte_body.strip()
    assert body.upper().startswith("VALUES"), body[:50]
    rest = body[len("VALUES") :]
    rows: list[list] = []
    i = 0
    n = len(rest)
    while i < n:
        if rest[i] == "(":
            close = find_matching_paren(rest, i)
            row_text = rest[i + 1 : close]
            rows.append([parse_scalar(tok) for tok in split_top_level(row_text)])
            i = close + 1
        else:
            i += 1
    return rows


@dataclass
class RawTree:
    tree_key: str
    name_en: str
    name_vi: str
    nodes: list[NodeDefinition]
    edges: list[EdgeDefinition]
    references: list[tuple] = None  # (node_key, source_title, section_path, locator,
    # locator_detail, printed_page_numbers, pdf_page_numbers, reference_note, reference_order)

    def __post_init__(self):
        if self.references is None:
            self.references = []


def parse_all_trees() -> dict[str, RawTree]:
    content = SQL_PATH.read_text(encoding="utf-8")
    trees: dict[str, RawTree] = {}

    # ---- 1. COPY-style decision_trees ----
    id_to_key: dict[str, str] = {}
    for m in re.finditer(
        r"COPY public\.decision_trees \([^)]*\) FROM stdin;\n(.*?)\n\\\.\n", content, re.S
    ):
        for line in m.group(1).split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t")
            tid, tkey, name_en, name_vi = parts[0], parts[1], parts[2], parts[3]
            id_to_key[tid] = tkey
            trees[tkey] = RawTree(tkey, name_en, name_vi, [], [])

    # ---- 2. COPY-style decision_nodes ----
    node_id_to_key: dict[str, tuple[str, str]] = {}  # node_id -> (tree_key, node_key)
    for m in re.finditer(
        r"COPY public\.decision_nodes \([^)]*\) FROM stdin;\n(.*?)\n\\\.\n", content, re.S
    ):
        for line in m.group(1).split("\n"):
            if not line.strip():
                continue
            cols = line.split("\t")
            (
                nid,
                tree_id,
                node_key,
                node_type,
                text_en,
                text_vi,
                cond,
                ctx_patch,
                action,
                global_cfg,
                link_tree,
                link_node,
                disp_order,
                _created,
                _updated,
            ) = cols
            tkey = id_to_key.get(tree_id)
            if tkey is None:
                continue

            def jv(s: str):
                return None if s == r"\N" else json.loads(s)

            def sv(s: str):
                return None if s == r"\N" else s

            node = NodeDefinition(
                id=uuid.UUID(nid),
                tree_id=uuid.UUID(tree_id),
                node_key=node_key,
                node_type=NodeType(node_type),
                text_en=text_en,
                text_vi=text_vi,
                condition_definition=jv(cond),
                context_patch=jv(ctx_patch),
                action_payload=jv(action),
                global_config=jv(global_cfg),
                link_target_tree_key=sv(link_tree),
                link_target_node_key=sv(link_node),
                display_order=int(disp_order),
            )
            trees[tkey].nodes.append(node)
            node_id_to_key[nid] = (tkey, node_key)

    # ---- 3. COPY-style decision_edges ----
    for m in re.finditer(
        r"COPY public\.decision_edges \([^)]*\) FROM stdin;\n(.*?)\n\\\.\n", content, re.S
    ):
        for line in m.group(1).split("\n"):
            if not line.strip():
                continue
            eid, from_id, to_id, order = line.split("\t")
            from_info = node_id_to_key.get(from_id)
            to_info = node_id_to_key.get(to_id)
            if from_info is None or to_info is None:
                continue
            tkey = from_info[0]
            trees[tkey].edges.append((eid, from_info[1], to_info[1], int(order)))

    # ---- 3b. COPY-style node_source_references ----
    def parse_pg_array(s: str) -> list[int] | None:
        if s == r"\N":
            return None
        return [int(x) for x in s.strip("{}").split(",") if x]

    for m in re.finditer(
        r"COPY public\.node_source_references \([^)]*\) FROM stdin;\n(.*?)\n\\\.\n", content, re.S
    ):
        for line in m.group(1).split("\n"):
            if not line.strip():
                continue
            cols = line.split("\t")
            (
                _rid,
                node_id,
                source_title,
                section_path,
                locator,
                locator_detail,
                printed_pages,
                pdf_pages,
                reference_note,
                ref_order,
            ) = cols
            info = node_id_to_key.get(node_id)
            if info is None:
                continue
            tkey, node_key = info
            trees[tkey].references.append(
                (
                    node_key,
                    source_title,
                    json.loads(section_path),
                    None if locator == r"\N" else locator,
                    None if locator_detail == r"\N" else locator_detail,
                    parse_pg_array(printed_pages),
                    parse_pg_array(pdf_pages),
                    None if reference_note == r"\N" else reference_note,
                    int(ref_order),
                )
            )

    # ---- 4. INSERT-style decision_trees (gen_random_uuid based) ----
    for m in re.finditer(
        r"INSERT INTO public\.decision_trees \(\s*(.*?)\)\s*VALUES\s*\((.*?)\);",
        content,
        re.S,
    ):
        vals = [parse_scalar(t) for t in split_top_level(m.group(2))]
        # columns: id, tree_key, name_en, name_vi, created_at, updated_at
        _id, tkey, name_en, name_vi = vals[0], vals[1], vals[2], vals[3]
        if tkey not in trees:
            trees[tkey] = RawTree(tkey, name_en, name_vi, [], [])

    # ---- 5. INSERT-style node_seed / edge_seed CTEs, one per statement ----
    # Each statement block runs from one "WITH tree_ctx AS (" to its terminating ";"
    tree_statement_pattern = (
        r"WITH tree_ctx AS \(\s*SELECT id AS tree_id\s+"
        r"FROM public\.decision_trees\s+"
        r"WHERE tree_key = '([a-z0-9-]+)'\s*\).*?"
        r"(?=\nWITH tree_ctx AS \(|\Z)"
    )
    for stmt_match in re.finditer(
        tree_statement_pattern,
        content,
        re.S,
    ):
        tkey = stmt_match.group(1)
        stmt = strip_sql_line_comments(stmt_match.group(0))
        if tkey not in trees:
            continue

        node_body = extract_cte_body(stmt, "node_seed")
        if node_body is not None and "INSERT INTO public.decision_nodes" in stmt:
            for row in parse_values_rows(node_body):
                (
                    node_key,
                    node_type,
                    text_en,
                    text_vi,
                    cond,
                    ctx_patch,
                    action,
                    global_cfg,
                    link_tree,
                    link_node,
                    disp_order,
                ) = row
                node = NodeDefinition(
                    id=uuid.uuid4(),
                    tree_id=uuid.uuid4(),  # placeholder, reset below
                    node_key=node_key,
                    node_type=NodeType(node_type),
                    text_en=text_en,
                    text_vi=text_vi,
                    condition_definition=cond,
                    context_patch=ctx_patch,
                    action_payload=action,
                    global_config=global_cfg,
                    link_target_tree_key=link_tree,
                    link_target_node_key=link_node,
                    display_order=int(disp_order) if disp_order is not None else 0,
                )
                trees[tkey].nodes.append(node)

        edge_body = extract_cte_body(stmt, "edge_seed")
        if edge_body is not None and "INSERT INTO public.decision_edges" in stmt:
            for row in parse_values_rows(edge_body):
                from_key, to_key, order = row
                trees[tkey].edges.append((str(uuid.uuid4()), from_key, to_key, int(order)))

        ref_body = extract_cte_body(stmt, "reference_seed")
        if ref_body is not None and "INSERT INTO public.node_source_references" in stmt:
            for row in parse_values_rows(ref_body):
                (
                    node_key,
                    source_title,
                    section_path,
                    locator,
                    locator_detail,
                    printed_pages,
                    pdf_pages,
                    reference_note,
                    ref_order,
                ) = row
                trees[tkey].references.append(
                    (
                        node_key,
                        source_title,
                        section_path,
                        locator,
                        locator_detail,
                        printed_pages,
                        pdf_pages,
                        reference_note,
                        int(ref_order),
                    )
                )

    return trees


def build_tree_graph(raw: RawTree) -> TreeGraph:
    tree_id = uuid.uuid4()
    tree_def = TreeDefinition(
        id=tree_id, tree_key=raw.tree_key, name_en=raw.name_en, name_vi=raw.name_vi
    )

    key_to_node: dict[str, NodeDefinition] = {}
    fixed_nodes = []
    for node in raw.nodes:
        fixed = NodeDefinition(
            id=node.id,
            tree_id=tree_id,
            node_key=node.node_key,
            node_type=node.node_type,
            text_en=node.text_en,
            text_vi=node.text_vi,
            condition_definition=node.condition_definition,
            context_patch=node.context_patch,
            action_payload=node.action_payload,
            global_config=node.global_config,
            link_target_tree_key=node.link_target_tree_key,
            link_target_node_key=node.link_target_node_key,
            display_order=node.display_order,
        )
        fixed_nodes.append(fixed)
        key_to_node[fixed.node_key] = fixed

    edges = []
    for eid, from_key, to_key, order in raw.edges:
        from_node = key_to_node.get(from_key)
        to_node = key_to_node.get(to_key)
        if from_node is None or to_node is None:
            raise ValueError(f"{raw.tree_key}: edge references unknown node {from_key} -> {to_key}")
        edges.append(
            EdgeDefinition(
                id=uuid.UUID(eid) if len(eid) == 36 else uuid.uuid4(),
                from_node_id=from_node.id,
                to_node_id=to_node.id,
                traversal_order=order,
                from_tree_id=tree_id,
                to_tree_id=tree_id,
            )
        )

    references = []
    for (
        node_key,
        source_title,
        section_path,
        locator,
        locator_detail,
        printed_pages,
        pdf_pages,
        reference_note,
        ref_order,
    ) in raw.references:
        node = key_to_node.get(node_key)
        if node is None:
            raise ValueError(f"{raw.tree_key}: reference references unknown node {node_key}")
        references.append(
            SourceReferenceDefinition(
                id=uuid.uuid4(),
                node_id=node.id,
                source_title=source_title,
                section_path=section_path,
                reference_order=ref_order,
                locator=locator,
                locator_detail=locator_detail,
                printed_page_numbers=tuple(printed_pages) if printed_pages is not None else None,
                pdf_page_numbers=tuple(pdf_pages) if pdf_pages is not None else None,
                reference_note=reference_note,
            )
        )

    return TreeGraph.build(tree=tree_def, nodes=fixed_nodes, edges=edges, references=references)


if __name__ == "__main__":
    trees = parse_all_trees()
    print(f"Parsed {len(trees)} trees:")
    for key, raw in sorted(trees.items()):
        print(f"  {key}: {len(raw.nodes)} nodes, {len(raw.edges)} edges")
