"""Regenerate the Python medicine lookup from backups/medicines.sql.

backups/medicines.sql is the hand-maintained source of truth (dose, name,
availability). This script parses its INSERT statement and writes
src/cdss/domain/decision_tree/medicines.py, a generated, do-not-hand-edit
module the app imports at runtime -- no live database read is involved.

Usage:

    uv run python backups/generate_medicines.py
"""

from __future__ import annotations

from pathlib import Path

SQL_PATH = Path(__file__).resolve().parent / "medicines.sql"
OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "cdss"
    / "domain"
    / "decision_tree"
    / "medicines.py"
)
COLUMNS = (
    "drug_id",
    "name",
    "drug_class",
    "subgroup",
    "route",
    "dose_low",
    "dose_usual",
    "dose_max",
    "source",
    "link",
    "available",
)


def extract_row_tuples(sql_text: str) -> list[str]:
    """Split the INSERT ... VALUES block into raw `(...)` row substrings."""

    values_index = sql_text.index("VALUES")
    text = sql_text[values_index + len("VALUES") :]

    rows: list[str] = []
    i, n = 0, len(text)
    while i < n:
        if text[i] != "(":
            i += 1
            continue
        start = i
        depth = 0
        in_string = False
        j = i
        while j < n:
            ch = text[j]
            if in_string:
                if ch == "'" and text[j + 1 : j + 2] == "'":
                    j += 2
                    continue
                if ch == "'":
                    in_string = False
                j += 1
                continue
            if ch == "'":
                in_string = True
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    j += 1
                    break
            j += 1
        rows.append(text[start:j])
        i = j
    return rows


def split_fields(row_tuple: str) -> list[str]:
    """Split a `(...)` row into its raw (still-quoted) field tokens."""

    inner = row_tuple[1:-1]
    fields: list[str] = []
    current: list[str] = []
    in_string = False
    i, n = 0, len(inner)
    while i < n:
        ch = inner[i]
        if in_string:
            if ch == "'" and inner[i + 1 : i + 2] == "'":
                current.append("'")
                i += 2
                continue
            current.append(ch)
            if ch == "'":
                in_string = False
            i += 1
            continue
        if ch == "'":
            in_string = True
            current.append(ch)
        elif ch == ",":
            fields.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
        i += 1
    fields.append("".join(current).strip())
    return fields


def parse_value(token: str) -> str | bool | None:
    if token == "NULL":
        return None
    if token == "true":
        return True
    if token == "false":
        return False
    if token.startswith("'") and token.endswith("'"):
        return token[1:-1].replace("''", "'")
    raise ValueError(f"Unrecognized SQL literal: {token!r}")


def parse_medicines(sql_text: str) -> list[dict[str, str | bool | None]]:
    medicines = []
    for row_tuple in extract_row_tuples(sql_text):
        raw_fields = split_fields(row_tuple)
        if len(raw_fields) != len(COLUMNS):
            raise ValueError(f"Expected {len(COLUMNS)} fields, got {len(raw_fields)}: {row_tuple}")
        values = [parse_value(f) for f in raw_fields]
        medicines.append(dict(zip(COLUMNS, values, strict=True)))
    return medicines


def render_python_literal(value: str | bool | None) -> str:
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "True" if value else "False"
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def render_module(medicines: list[dict[str, str | bool | None]]) -> str:
    lines = [
        '"""Medicine lookup data, generated from backups/medicines.sql.',
        "",
        "GENERATED FILE -- do not hand-edit. To change a dose, name, or",
        "availability: edit backups/medicines.sql, then regenerate:",
        "",
        "    uv run python backups/generate_medicines.py",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from collections.abc import Mapping",
        "",
        "from cdss.domain.decision_tree.contracts import JsonObject",
        "",
        "MEDICINES: tuple[JsonObject, ...] = (",
    ]
    for medicine in medicines:
        fields = ", ".join(
            f'"{column}": {render_python_literal(medicine[column])}' for column in COLUMNS
        )
        lines.append(f"    {{{fields}}},")
    lines.append(")")
    lines.append("")
    lines.append("MEDICINES_BY_ID: Mapping[str, JsonObject] = {")
    lines.append('    str(medicine["drug_id"]): medicine for medicine in MEDICINES')
    lines.append("}")
    lines.append("")
    lines.append("_CLASS_LETTERS = sorted(")
    lines.append('    {str(m["drug_class"]) for m in MEDICINES if m["drug_class"] is not None}')
    lines.append(")")
    lines.append("")
    lines.append("MEDICINES_BY_CLASS: Mapping[str, tuple[JsonObject, ...]] = {")
    lines.append("    class_letter: tuple(")
    lines.append('        m for m in MEDICINES if m["drug_class"] == class_letter')
    lines.append("    )")
    lines.append("    for class_letter in _CLASS_LETTERS")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    sql_text = SQL_PATH.read_text(encoding="utf-8")
    medicines = parse_medicines(sql_text)
    module_source = render_module(medicines)
    OUTPUT_PATH.write_text(module_source, encoding="utf-8")
    print(f"Parsed {len(medicines)} medicines from {SQL_PATH}")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
