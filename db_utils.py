"""Read-only database helpers used by the Streamlit app and tests."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pandas as pd


FORBIDDEN_SQL = re.compile(
    r"\b(insert|update|delete|drop|alter|attach|detach|pragma|vacuum|reindex|"
    r"create|replace|trigger|load_extension)\b",
    re.IGNORECASE,
)


def connect_read_only(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    connection.execute("PRAGMA query_only = ON")
    return connection


def get_years(db_path: Path) -> list[int]:
    with connect_read_only(db_path) as connection:
        rows = connection.execute(
            "SELECT DISTINCT Year FROM pcards WHERE Year IS NOT NULL ORDER BY Year DESC"
        ).fetchall()
    return [int(row[0]) for row in rows]


def search_transactions(
    db_path: Path,
    *,
    year: int,
    field: str,
    keyword: str,
    limit: int = 5000,
) -> tuple[int, pd.DataFrame]:
    if field not in {"Description", "Vendor"}:
        raise ValueError("Search field must be Description or Vendor.")
    keyword = keyword.strip()
    if not keyword:
        return 0, pd.DataFrame()

    where = f"Year = ? AND lower(COALESCE({field}, '')) LIKE lower(?)"
    params = (year, f"%{keyword}%")
    columns = (
        "ID, Year, Month, Amount, FullName, Description, Vendor, "
        "TransactionDate, PostedDate, MCC"
    )
    with connect_read_only(db_path) as connection:
        total = connection.execute(
            f"SELECT COUNT(*) FROM pcards WHERE {where}", params
        ).fetchone()[0]
        frame = pd.read_sql_query(
            f"SELECT {columns} FROM pcards WHERE {where} "
            "ORDER BY Amount DESC, TransactionDate ASC LIMIT ?",
            connection,
            params=(*params, limit),
        )
    return int(total), frame


def validate_readonly_sql(sql: str) -> str:
    cleaned = sql.strip()
    if not cleaned:
        raise ValueError("The model did not return a query.")
    if ";" in cleaned or "--" in cleaned or "/*" in cleaned:
        raise ValueError("Only one SQL statement without comments is allowed.")
    if not re.match(r"^(select|with)\b", cleaned, re.IGNORECASE):
        raise ValueError("Only SELECT queries are allowed.")
    if FORBIDDEN_SQL.search(cleaned):
        raise ValueError("The generated query contains a blocked SQL operation.")
    return cleaned


def run_readonly_query(
    db_path: Path, sql: str, row_limit: int = 500
) -> tuple[str, pd.DataFrame]:
    safe_sql = validate_readonly_sql(sql)
    executed_sql = safe_sql
    if not re.search(r"\blimit\s+\d+", safe_sql, re.IGNORECASE):
        executed_sql = f"{safe_sql}\nLIMIT {int(row_limit)}"

    with connect_read_only(db_path) as connection:
        # Prevent accidentally expensive model-generated queries from running forever.
        remaining_steps = 25_000_000

        def progress() -> int:
            nonlocal remaining_steps
            remaining_steps -= 10_000
            return 1 if remaining_steps <= 0 else 0

        connection.set_progress_handler(progress, 10_000)
        frame = pd.read_sql_query(executed_sql, connection)
    return executed_sql, frame
