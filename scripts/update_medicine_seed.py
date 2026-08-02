"""Rebuild the medicine section of backups/seed.sql from medicines.csv."""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "backups" / "medicines.csv"
SEED_PATH = ROOT / "backups" / "seed.sql"
START = "-- 6. MEDICINES REFERENCE CATALOG"
END = "-- 7. SYMPTOMS REFERENCE CATALOG"
BORDER_PREFIX = "-- ======================================================================"

ROUTES = {
    "Thu?c U?ng": "Thuốc Uống",
    "Thu?c Truy?n T?nh M?ch": "Thuốc Truyền Tĩnh Mạch",
    "Thu?c U?ng/Thu?c Truy?n T?nh M?ch": "Thuốc Uống/Thuốc Truyền Tĩnh Mạch",
}
SOURCES = {
    "B?ng 10": "Bảng 10",
    "B?ng 16": "Bảng 16",
    "M?c 3.6.5": "Mục 3.6.5",
    "M?c 3.7.1": "Mục 3.7.1",
    "M?c 3.7.5": "Mục 3.7.5",
}
SUBGROUPS = {
    "?CMC": "ƯCMC",
    "?c ch? Renin tr?c ti?p": "Ức chế Renin trực tiếp",
    "?c ch? th? th? Alpha giao c?m": "Ức chế thụ thể Alpha giao cảm",
    "Ch? v?n ch?n l?c alpha-2 giao c?m": "Chất vận chọn lọc alpha-2 giao cảm",
    "Gi?m Adrenergic": "Giảm Adrenergic",
    "Gi?n m?ch": "Giãn mạch",
    "LT gi? Kali": "LT giữ Kali",
}
INSERT_RE = re.compile(
    r"VALUES \('(?P<id>DRUG\d+)', '(?P<name>(?:''|[^'])*)', "
    r"(?P<class>NULL|'(?:''|[^'])*'), (?P<subgroup>NULL|'(?:''|[^'])*'), "
    r"(?P<route>NULL|'(?:''|[^'])*'), .*?, "
    r"(?P<source>NULL|'(?:''|[^'])*'),",
)


def sql(value: str | None) -> str:
    if value is None or not value.strip():
        return "NULL"
    return "'" + value.strip().replace("'", "''") + "'"


def normalize_text(value: str) -> str:
    return (
        value.strip()
        .replace("ng…y", "ngày")
        .replace("nga?y", "ngày")
        .replace("gi?", "giữ")
        .replace("ph£t", "phút")
    )


def unquote(value: str) -> str | None:
    if value == "NULL":
        return None
    return value[1:-1].replace("''", "'")


def existing_catalog(section: str) -> dict[str, dict[str, str | None]]:
    catalog: dict[str, dict[str, str | None]] = {}
    for match in INSERT_RE.finditer(section):
        name = match["name"].replace("''", "'")
        catalog[name] = {
            "id": match["id"],
            "class": unquote(match["class"]),
            "subgroup": unquote(match["subgroup"]),
            "route": unquote(match["route"]),
            "source": unquote(match["source"]),
        }
    return catalog


def drug_class(group: str) -> str | None:
    if "CKCa" in group:
        return "C"
    if "Beta (CB)" in group:
        return "B"
    if "CTTA" in group or "?CMC" in group:
        return "A"
    if group.startswith("L?i Ti?u"):
        return "D"
    return None


def csv_rows() -> list[list[str]]:
    # The supplied export is Windows-1258-like and contains trailing empty rows.
    with CSV_PATH.open(encoding="cp1258", newline="") as handle:
        rows = list(csv.reader(handle))
    real_rows = [row for row in rows[1:] if any(cell.strip() for cell in row)]
    if any(len(row) != 11 for row in real_rows):
        raise ValueError("Every non-empty medicine CSV row must have 11 columns")
    names = [row[0].strip() for row in real_rows]
    if len(names) != len(set(names)):
        raise ValueError("Medicine names must be unique")
    return real_rows


def render(rows: list[list[str]], old: dict[str, dict[str, str | None]]) -> str:
    max_id = max((int(str(item["id"])[4:]) for item in old.values()), default=0)
    records: list[str] = []
    for row in rows:
        name, group, subgroup, route, low, usual, maximum, atc, _sct, source, link = (
            normalize_text(cell) for cell in row
        )
        previous = old.get(name)
        if previous is None:
            max_id += 1
            previous = {"id": f"DRUG{max_id:04d}", "class": None, "subgroup": None}
        class_code = drug_class(group)
        normalized_subgroup = SUBGROUPS.get(subgroup, subgroup) or None
        normalized_route = ROUTES.get(route, route) or None
        normalized_source = SOURCES.get(source, source) or None
        columns = (
            "drug_id, name, drug_class, subgroup, route, dose_low, dose_usual, "
            "dose_max, source, link, available, atc_code"
        )
        values = ", ".join(
            (
                sql(str(previous["id"])),
                sql(name),
                sql(class_code),
                sql(normalized_subgroup),
                sql(normalized_route),
                sql(low),
                sql(usual),
                sql(maximum),
                sql(normalized_source),
                sql(link),
                "TRUE",
                sql(atc),
            )
        )
        updates = ", ".join(
            f"{column} = EXCLUDED.{column}"
            for column in (
                "name", "drug_class", "subgroup", "route", "dose_low", "dose_usual",
                "dose_max", "source", "link", "available", "atc_code",
            )
        )
        records.append(
            f"INSERT INTO public.medicines ({columns})\n"
            f"VALUES ({values})\n"
            f"ON CONFLICT (drug_id) DO UPDATE SET {updates};"
        )
    header = (
        "-- ==========================================================================\n"
        f"-- 6. MEDICINES REFERENCE CATALOG ({len(rows)} drugs)\n"
        "-- ==========================================================================\n"
    )
    return header + "\n\n".join(records) + "\n\n\n"


def main() -> None:
    seed = SEED_PATH.read_text(encoding="utf-8")
    start = seed.index(START)
    start = seed.rfind(BORDER_PREFIX, 0, start)
    end = seed.index(END)
    end = seed.rfind(BORDER_PREFIX, 0, end)
    old = existing_catalog(seed[start:end])
    SEED_PATH.write_text(seed[:start] + render(csv_rows(), old) + seed[end:], encoding="utf-8")


if __name__ == "__main__":
    main()
