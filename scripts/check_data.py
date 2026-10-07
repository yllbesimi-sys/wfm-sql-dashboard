"""Quick look at data/wfm.db: row counts, date range, a few sample rows. Run: python scripts/check_data.py"""
import sqlite3
from pathlib import Path

con = sqlite3.connect(Path(__file__).resolve().parent.parent / "data" / "wfm.db")


def show(title, sql):
    cur = con.execute(sql)
    print(f"\n== {title} ==")
    print(" | ".join(c[0] for c in cur.description))
    for row in cur.fetchall():
        print(" | ".join(str(v) for v in row))


show("Row counts", "SELECT 'intervals', COUNT(*) FROM intervals UNION ALL SELECT 'agents', COUNT(*) FROM agents "
                   "UNION ALL SELECT 'adherence', COUNT(*) FROM adherence")
show("Date range", "SELECT MIN(date), MAX(date), COUNT(DISTINCT date) AS days FROM intervals")
show("Totals per queue", "SELECT queue, SUM(offered) AS offered, SUM(answered) AS answered, SUM(abandoned) AS abandoned "
                         "FROM intervals GROUP BY queue")
show("Sample intervals", "SELECT * FROM intervals ORDER BY date, interval_start, queue LIMIT 5")
show("Sample agents", "SELECT * FROM agents LIMIT 3")
show("Sample adherence", "SELECT * FROM adherence LIMIT 3")
