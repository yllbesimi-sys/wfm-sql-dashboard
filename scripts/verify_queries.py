"""Check every SQL query's result against an independent calculation in plain Python.

The SQL files are the source of truth for the metrics; this script only proves they do what
they claim (a second pair of eyes). Run:  python scripts/verify_queries.py
"""
import sqlite3
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
con = sqlite3.connect(f"{(ROOT / 'data' / 'wfm.db').as_uri()}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
raw = con.execute("SELECT * FROM intervals").fetchall()
failed = []


def run(name):
    return con.execute((ROOT / "sql" / name).read_text(encoding="utf-8")).fetchall()


def check(label, ok):
    print(("OK    " if ok else "FAIL  ") + label)
    if not ok:
        failed.append(label)


# 1. offered per day per queue
expected = defaultdict(int)
for r in raw:
    expected[(r["date"], r["queue"])] += r["offered"]
got = {(r["date"], r["queue"]): r["offered_contacts"] for r in run("01_offered_per_day_queue.sql")}
check(f"01 offered per day/queue: {len(got)} rows match", got == dict(expected))

# 2. AHT per queue (weighted and simple)
ok = True
for r in run("02_aht_per_queue.sql"):
    q = [x for x in raw if x["queue"] == r["queue"]]
    weighted = sum(x["aht_seconds"] * x["answered"] for x in q) / sum(x["answered"] for x in q)
    simple = sum(x["aht_seconds"] for x in q) / len(q)
    ok &= abs(r["aht_weighted_sec"] - weighted) < 0.06 and abs(r["aht_simple_avg_sec"] - simple) < 0.06
check("02 AHT per queue (weighted + simple)", ok)

# 3. service level per interval
sql3 = {(r["date"], r["interval_start"], r["queue"]): r for r in run("03_service_level_per_interval.sql")}
ok = len(sql3) == len(raw)
for x in raw:
    r = sql3[(x["date"], x["interval_start"], x["queue"])]
    if x["offered"] == 0:
        ok &= r["service_level_pct"] is None and r["meets_80_20"] is None
    else:
        sl = 100 * x["answered_within_20s"] / x["offered"]
        ok &= abs(r["service_level_pct"] - sl) < 0.06 and r["meets_80_20"] == ("yes" if sl >= 80 else "no")
check(f"03 service level: {len(sql3)} intervals match", ok)

# 4. abandon rate per week per queue (week = Monday on or before the date)
off, abn = defaultdict(int), defaultdict(int)
for x in raw:
    d = date.fromisoformat(x["date"])
    key = ((d - timedelta(days=d.weekday())).isoformat(), x["queue"])
    off[key] += x["offered"]
    abn[key] += x["abandoned"]
sql4 = {(r["week_start"], r["queue"]): r for r in run("04_abandon_rate_weekly.sql")}
ok = set(sql4) == set(off) and all(
    sql4[k]["offered"] == off[k] and sql4[k]["abandoned"] == abn[k]
    and abs(sql4[k]["abandon_rate_pct"] - 100 * abn[k] / off[k]) < 0.006
    for k in off
)
check(f"04 abandon rate weekly: {len(sql4)} week/queue rows match", ok)

sys.exit(1 if failed else 0)
