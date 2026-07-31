"""Generate a self-contained, restorable SQL backup of the CDSS database.

Read-only. Reconstructs DDL (enum, tables, constraints, indexes) from
pg_catalog for exact fidelity and emits native COPY data blocks. Database
credentials are never written to the output.

Usage (reads DATABASE_URL from the environment, like the app):

    uv run python backups/dump.py                      # -> backups/backup.sql
    uv run python backups/dump.py path/to/backup.sql   # explicit output path
"""

from __future__ import annotations

import datetime as dt
import io
import os
import re
import sys
from pathlib import Path

import psycopg2

# FK-safe order for restoring data.
DATA_ORDER = [
    "decision_trees",
    "decision_nodes",
    "decision_edges",
    "node_source_references",
    "tree_layouts",
    "medicines",
    "patients",
    "patient_conditions",
    "visits",
    "visit_observations",
    "visit_medications",
    "fhir_import_batches",
    "development_runtime_logs",
    "alembic_version",
]


def _database_url() -> str:
    """DATABASE_URL from the environment, falling back to the .env file."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        env = Path(__file__).resolve().parent.parent / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.startswith("DATABASE_URL="):
                    url = line.split("=", 1)[1].strip()
                    break
    if not url:
        sys.exit("DATABASE_URL is not set.")
    # psycopg2 (libpq) does not accept the channel_binding query parameter.
    return re.sub(r"([?&])channel_binding=require", "", url)


def dump(conn) -> str:
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor()

    cur.execute("select current_database(), version()")
    dbname, dbversion = cur.fetchone()

    cur.execute("select tablename from pg_tables where schemaname='public' order by tablename")
    all_tables = [r[0] for r in cur.fetchall()]

    counts = {}
    for t in all_tables:
        cur.execute(f'select count(*) from public."{t}"')
        counts[t] = cur.fetchone()[0]

    out = io.StringIO()
    w = out.write
    now = dt.datetime.now(dt.UTC).isoformat()

    w("--\n-- CDSS database backup\n")
    w(f"-- Source database : {dbname}\n")
    w(f"-- Server version  : {dbversion}\n")
    w(f"-- Generated (UTC) : {now}\n")
    w("-- Row counts:\n")
    for t in DATA_ORDER:
        if t in all_tables:
            w(f"--   {t}: {counts[t]}\n")
    w("--\n-- Restore into an EMPTY database:\n")
    w("--   createdb cdss_restore\n")
    w("--   psql -d cdss_restore -f <this file>\n--\n\n")
    w("SET client_encoding = 'UTF8';\n")
    w("SET standard_conforming_strings = on;\n\nBEGIN;\n\n")

    # Enum types.
    cur.execute("""
        select t.typname, array_agg(e.enumlabel order by e.enumsortorder)
        from pg_type t
        join pg_enum e on e.enumtypid = t.oid
        join pg_namespace n on n.oid = t.typnamespace
        where n.nspname='public'
        group by t.typname order by t.typname
    """)
    w("-- Types\n")
    for typname, labels in cur.fetchall():
        vals = ", ".join("'" + lab.replace("'", "''") + "'" for lab in labels)
        w(f"CREATE TYPE public.{typname} AS ENUM ({vals});\n")
    w("\n-- Tables\n")

    # Tables (columns only; constraints and indexes added afterwards).
    for t in all_tables:
        cur.execute(
            """
            select a.attname, format_type(a.atttypid, a.atttypmod),
                   a.attnotnull, pg_get_expr(d.adbin, d.adrelid)
            from pg_attribute a
            left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum
            where a.attrelid = ('public.' || %s)::regclass
              and a.attnum > 0 and not a.attisdropped
            order by a.attnum
            """,
            (t,),
        )
        lines = []
        for name, typ, notnull, default in cur.fetchall():
            typ = re.sub(r"\bnode_type\b", "public.node_type", typ)
            line = f'    "{name}" {typ}'
            if default is not None:
                line += f" DEFAULT {default}"
            if notnull:
                line += " NOT NULL"
            lines.append(line)
        w(f"CREATE TABLE public.{t} (\n" + ",\n".join(lines) + "\n);\n\n")

    def constraints(kinds: set[str]):
        for t in all_tables:
            cur.execute(
                """
                select conname, pg_get_constraintdef(oid), contype
                from pg_constraint
                where conrelid = ('public.' || %s)::regclass
                order by conname
                """,
                (t,),
            )
            for conname, condef, contype in cur.fetchall():
                if contype in kinds:
                    yield t, conname, condef

    w("-- Primary keys, unique and check constraints\n")
    for t, conname, condef in constraints({"p", "u", "c"}):
        w(f"ALTER TABLE public.{t} ADD CONSTRAINT {conname} {condef};\n")
    w("\n-- Foreign keys\n")
    for t, conname, condef in constraints({"f"}):
        w(f"ALTER TABLE public.{t} ADD CONSTRAINT {conname} {condef};\n")

    # Indexes not already created by a constraint.
    cur.execute("""
        select c.conindid from pg_constraint c
        join pg_namespace n on n.oid = c.connamespace
        where n.nspname='public' and c.conindid <> 0
    """)
    constraint_index_oids = {r[0] for r in cur.fetchall()}
    w("\n-- Indexes\n")
    for t in all_tables:
        cur.execute(
            """
            select i.indexrelid, ix.indexdef
            from pg_index i
            join pg_class ic on ic.oid = i.indexrelid
            join pg_indexes ix on ix.indexname = ic.relname and ix.schemaname='public'
            where i.indrelid = ('public.' || %s)::regclass
            order by ic.relname
            """,
            (t,),
        )
        for indexrelid, indexdef in cur.fetchall():
            if indexrelid not in constraint_index_oids:
                w(f"{indexdef};\n")

    # Data via native COPY.
    w("\n-- Data\n")
    for t in DATA_ORDER:
        if t not in all_tables:
            continue
        cur.execute(
            """
            select a.attname from pg_attribute a
            where a.attrelid = ('public.' || %s)::regclass
              and a.attnum > 0 and not a.attisdropped
            order by a.attnum
            """,
            (t,),
        )
        collist = ", ".join(f'"{r[0]}"' for r in cur.fetchall())
        w(f"COPY public.{t} ({collist}) FROM stdin;\n")
        buf = io.StringIO()
        cur.copy_expert(f'COPY public."{t}" ({collist}) TO STDOUT WITH (FORMAT text)', buf)
        w(buf.getvalue())
        w("\\.\n\n")

    w("COMMIT;\n")
    return out.getvalue()


def main() -> None:
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
    else:
        target = Path(__file__).resolve().parent / "backup.sql"

    conn = psycopg2.connect(_database_url())
    try:
        sql = dump(conn)
    finally:
        conn.close()

    target.write_text(sql, encoding="utf-8")
    print(f"Wrote {target} ({len(sql):,} bytes)")


if __name__ == "__main__":
    main()
