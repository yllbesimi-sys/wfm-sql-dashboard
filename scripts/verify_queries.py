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

# 5. forecast accuracy per queue (intervals with zero actual contacts are left out)
ok = True
for r in run("05_forecast_accuracy.sql"):
    q = [x for x in raw if x["queue"] == r["queue"] and x["offered"] > 0]
    tot = sum(x["offered"] for x in q)
    mape = 100 * sum(abs(x["offered"] - x["forecast_offered"]) / x["offered"] for x in q) / len(q)
    wape = 100 * sum(abs(x["offered"] - x["forecast_offered"]) for x in q) / tot
    bias = 100 * (sum(x["forecast_offered"] for x in q) - tot) / tot
    ok &= r["intervals_compared"] == len(q) and all(
        abs(r[k] - v) < 0.06 for k, v in (("mape_pct", mape), ("wape_pct", wape), ("bias_pct", bias)))
check("05 forecast accuracy (MAPE, WAPE, bias)", ok)

# 6. week-over-week change (previous week of the same queue)
weekly = defaultdict(int)
for x in raw:
    d = date.fromisoformat(x["date"])
    weekly[(x["queue"], (d - timedelta(days=d.weekday())).isoformat())] += x["offered"]
sql6 = {(r["queue"], r["week_start"]): r for r in run("06_wow_volume_change.sql")}
ok = set(sql6) == set(weekly)
for (queue, wk), r in sql6.items():
    prev = weekly.get((queue, (date.fromisoformat(wk) - timedelta(days=7)).isoformat()))
    if prev is None:
        ok &= r["previous_week_offered"] is None and r["wow_change_pct"] is None
    else:
        ok &= r["previous_week_offered"] == prev and abs(r["wow_change_pct"] - 100 * (r["offered"] - prev) / prev) < 0.06
check(f"06 week-over-week change: {len(sql6)} rows match", ok)

# 7. staffing gap (workload / 1800 / 0.85 occupancy)
sql7 = {(r["date"], r["interval_start"], r["queue"]): r for r in run("07_staffing_gap.sql")}
ok = len(sql7) == len(raw)
for x in raw:
    r = sql7[(x["date"], x["interval_start"], x["queue"])]
    need = x["offered"] * x["aht_seconds"] / 1800 / 0.85
    ok &= (abs(r["agents_needed"] - need) < 0.06 and abs(r["staffing_gap"] - (x["scheduled_agents"] - need)) < 0.06
           and r["status"] == ("short" if x["scheduled_agents"] < need else "ok"))
check(f"07 staffing gap: {len(sql7)} intervals match", ok)

# 8. adherence per team and per agent (the JOIN done by hand with a dict)
team_of = {r["agent_id"]: (r["team"], r["queue"]) for r in con.execute("SELECT * FROM agents")}
tot = defaultdict(lambda: [0, 0, 0])
for r in con.execute("SELECT * FROM adherence"):
    team, queue = team_of[r["agent_id"]]
    for key in (("team", team, None, queue), ("agent", team, r["agent_id"], queue)):
        tot[key][0] += 1
        tot[key][1] += r["scheduled_minutes"]
        tot[key][2] += r["adherent_minutes"]
sql8 = {(r["level"], r["team"], r["agent_id"], r["queue"]): r for r in run("08_adherence_team_agent.sql")}
ok = set(sql8) == set(tot) and all(
    (r["shifts_worked"], r["scheduled_minutes"], r["adherent_minutes"]) == tuple(tot[k])
    and abs(r["adherence_pct"] - 100 * tot[k][2] / tot[k][1]) < 0.06
    for k, r in sql8.items()
)
check(f"08 adherence: {len(sql8)} team/agent rows match", ok)

sys.exit(1 if failed else 0)
