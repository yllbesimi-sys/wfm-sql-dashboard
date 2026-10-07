"""Run one of the .sql files in /sql against data/wfm.db and print the result as a table.

  python scripts/run_sql.py                                  list the available queries
  python scripts/run_sql.py sql/02_aht_per_queue.sql         run one
  python scripts/run_sql.py sql/03_service_level_per_interval.sql --limit 0    show every row

This script contains no metric logic: the logic lives in the .sql files.
The database is opened read-only, so a typo in a query can never change the data.
"""
import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "wfm.db"


def question(path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("-- Question:"):
            return line.removeprefix("-- Question:").strip()
    return ""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?", help="a .sql file, e.g. sql/01_offered_per_day_queue.sql")
    ap.add_argument("--limit", type=int, default=40, help="rows to show (default 40, 0 = all)")
    args = ap.parse_args()

    if not args.file:
        for p in sorted((ROOT / "sql").glob("*.sql")):
            print(f"sql/{p.name}\n    {question(p)}")
        return

    path = Path(args.file)
    if not path.exists():
        path = ROOT / args.file
    if not path.exists():
        sys.exit(f"File not found: {args.file}")

    con = sqlite3.connect(f"{DB.as_uri()}?mode=ro", uri=True)
    try:
        cur = con.execute(path.read_text(encoding="utf-8"))
    except sqlite3.Error as e:
        sys.exit(f"SQL error: {e}")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()

    shown = rows if args.limit == 0 else rows[: args.limit]
    cells = [["NULL" if v is None else str(v) for v in r] for r in shown]
    widths = [max([len(c)] + [len(r[i]) for r in cells]) for i, c in enumerate(cols)]
    numeric = [bool(rows) and isinstance(rows[0][i], (int, float)) for i in range(len(cols))]

    def line(values):
        return "  ".join(v.rjust(w) if num else v.ljust(w) for v, w, num in zip(values, widths, numeric))

    print(line(cols))
    print("  ".join("-" * w for w in widths))
    for r in cells:
        print(line(r))
    note = f"{len(rows)} rows"
    if len(shown) < len(rows):
        note = f"showing the first {len(shown)} of {len(rows)} rows (use --limit 0 to see all)"
    print(f"\n{note}")


if __name__ == "__main__":
    main()
