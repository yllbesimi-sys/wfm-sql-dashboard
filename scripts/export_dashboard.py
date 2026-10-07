"""Run every query in sql/dashboard/ and save the results as JSON for the static dashboard.

  python scripts/export_dashboard.py

This is the "build step": it only runs the SQL files and writes their results (plus the SQL text,
shown in the "Show the SQL" panels) to dashboard/data/. No metric logic lives here.
"""
import json
import sqlite3
from pathlib import Path

from run_sql import question  # reads the "-- Question:" line of a .sql file

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dashboard" / "data"


def main():
    con = sqlite3.connect(f"{(ROOT / 'data' / 'wfm.db').as_uri()}?mode=ro", uri=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for path in sorted((ROOT / "sql" / "dashboard").glob("*.sql")):
        sql = path.read_text(encoding="utf-8")
        cur = con.execute(sql)
        data = {
            "file": f"sql/dashboard/{path.name}",
            "question": question(path),
            "sql": sql,
            "columns": [d[0] for d in cur.description],
            "rows": [list(r) for r in cur.fetchall()],
        }
        target = OUT / f"{path.stem}.json"
        target.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8", newline="\n")
        print(f"{target.relative_to(ROOT).as_posix():45} {len(data['rows']):5} rows  {target.stat().st_size // 1024:4} KB")


if __name__ == "__main__":
    main()
