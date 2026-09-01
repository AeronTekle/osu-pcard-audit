"""Create the assignment views and export compact result summaries."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "pcards.db"
SQL_PATH = ROOT / "analysis_queries.sql"
OUTPUT_PATH = ROOT / "analysis_results.json"


def main() -> None:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.executescript(SQL_PATH.read_text(encoding="utf-8"))
    connection.commit()

    results: dict[str, dict[str, object]] = {}
    for part, question_count in (("T2", 14), ("T3", 8)):
        for question in range(1, question_count + 1):
            view = f"qry_{part}_Question{question}"
            count = connection.execute(f'SELECT COUNT(*) FROM "{view}"').fetchone()[0]
            rows = [dict(row) for row in connection.execute(f'SELECT * FROM "{view}" LIMIT 10')]
            results[view] = {"row_count": count, "first_10_rows": rows}

    OUTPUT_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    connection.close()
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
