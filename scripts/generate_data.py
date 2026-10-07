"""Generate the FICTIONAL contact-center dataset into data/wfm.db.

Everything here is synthetic. A fixed random seed makes the output identical on every run.
Run:  python scripts/generate_data.py
"""
import math
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

SEED = 42
ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "wfm.db"
SCHEMA_PATH = ROOT / "data" / "schema.sql"

START = date(2026, 8, 3)          # a Monday
WEEKS = 8
OPEN_HOUR, CLOSE_HOUR = 8, 20     # 08:00-20:00, 30-minute intervals -> 24 per day
SLOTS = (CLOSE_HOUR - OPEN_HOUR) * 2
INTERVAL_SECONDS = 1800

# Per queue: busiest-interval volume (before day/trend factors), planned AHT, agent roster, team names.
QUEUES = {
    "Support-EN": {"peak": 80, "aht": 420, "agents": 30, "teams": ["Alpha", "Bravo"]},
    "Support-DE": {"peak": 32, "aht": 480, "agents": 15, "teams": ["Charlie"]},
    "Billing-EN": {"peak": 48, "aht": 540, "agents": 24, "teams": ["Delta"]},
}
DAY_FACTOR = [1.15, 1.05, 1.00, 0.98, 0.95, 0.60]   # Mon..Sat
OCCUPANCY_TARGET = 0.85           # same simple idea the staffing-gap query uses later
PLAN_BUFFER = 1.10                # planner aims a bit above the forecast need
N_SPIKES = 5

# Shifts: 8.5h span (480 paid minutes) or 7.5h part-time span (420 paid), each with ONE 30-minute lunch interval.
SHIFT_SPANS = [17, 17, 17, 15]    # in 30-minute intervals; 3 in 4 agents are full-time
LUNCH_OFFSETS = [8, 9, 10]        # lunch starts 4h, 4.5h or 5h after shift start
P_OFF = {"weekday": 0.12, "saturday": 0.45, "leave_cluster": 0.35}   # chance an agent is off that day
P_LEAVE_CLUSTER = 0.06            # share of queue-days where many people happen to be on leave


def time_of_day(h):
    """Shape of a contact-center day: morning peak ~10:30, lunch dip, afternoon bump ~15:00. Peak ~= 1."""
    morning = math.exp(-(((h - 10.5) / 1.5) ** 2))
    afternoon = 0.85 * math.exp(-(((h - 15.0) / 1.8) ** 2))
    return (0.25 + morning + afternoon) / 1.25


def service_level(rho):
    """Share of offered contacts answered within 20s, given load rho = workload / agent capacity.
    A smooth S-curve: ~95% at rho 0.75, ~50% at rho 1.0, collapsing above that. A simplification, not Erlang C."""
    return 1 / (1 + math.exp(12 * (rho - 1.0)))


def noisy_count(rng, mean):
    """Poisson-like count (normal approximation), never negative."""
    return max(0, round(rng.gauss(mean, math.sqrt(max(mean, 1)))))


def plan_shifts(rng, need, n_agents):
    """Greedy planner: place each agent's shift (start, length, lunch) where it covers the most still-uncovered need.
    Returns one (start_slot, length, lunch_slot) per agent and the resulting headcount per slot."""
    coverage = [0] * SLOTS
    shifts = []
    for k in range(n_agents):
        best, best_gain = None, -1.0
        for length in ([max(SHIFT_SPANS)] if k < 2 else set(SHIFT_SPANS)):   # k=0 opens, k=1 closes the queue
            for start in range(SLOTS - length + 1):
                if (k == 0 and start != 0) or (k == 1 and start != SLOTS - length):
                    continue
                for lo in LUNCH_OFFSETS:
                    on = [i for i in range(start, start + length) if i != start + lo]
                    gain = sum(min(1.0, max(0.0, need[i] - coverage[i])) for i in on) + rng.random() * 0.01
                    if gain > best_gain:
                        best, best_gain = (start, length, start + lo, on), gain
        start, length, lunch, on = best
        for i in on:
            coverage[i] += 1
        shifts.append((start, length, lunch))
    return shifts, coverage


def main():
    rng = random.Random(SEED)
    days = [START + timedelta(days=7 * w + d) for w in range(WEEKS) for d in range(6)]
    slots = [f"{h:02d}:{m:02d}" for h in range(OPEN_HOUR, CLOSE_HOUR) for m in (0, 30)]

    agent_rows, agent_skill, agents_by_queue = [], {}, {}
    n = 0
    for queue, q in QUEUES.items():
        agents_by_queue[queue] = []
        for i in range(q["agents"]):
            n += 1
            agent_id = f"AGT-{n:03d}"
            agent_rows.append((agent_id, q["teams"][i % len(q["teams"])], queue))
            agents_by_queue[queue].append(agent_id)
            agent_skill[agent_id] = rng.uniform(0.84, 0.97)   # each agent's typical adherence

    # Unexpected spikes: nobody forecast them, so those intervals end up short-staffed.
    spikes = {}
    for _ in range(N_SPIKES):
        day, queue, first = rng.choice(days), rng.choice(list(QUEUES)), rng.randrange(2, 18)
        mult = rng.uniform(1.8, 2.3)
        for i in range(first, first + rng.randint(3, 5)):
            spikes[(day, slots[i], queue)] = mult

    interval_rows, adherence_rows = [], []
    for day in days:
        week = (day - START).days // 7
        for queue, q in QUEUES.items():
            day_noise = rng.gauss(1.0, 0.05)   # a busier or quieter day than expected

            # 1) Volume and forecast for each interval of the day.
            day_data = []
            for slot in slots:
                h = int(slot[:2]) + int(slot[3:]) / 60 + 0.25   # interval midpoint
                expected = q["peak"] * DAY_FACTOR[day.weekday()] * (1 + 0.01 * week) * time_of_day(h)
                forecast = round(expected * rng.gauss(1.0, 0.05))
                offered = noisy_count(rng, expected * day_noise * spikes.get((day, slot, queue), 1.0))
                aht = round(q["aht"] * rng.gauss(1.0, 0.05))
                day_data.append((forecast, offered, aht))

            # 2) Who works today, and where the planner puts their shifts (based on the FORECAST only).
            if day.weekday() == 5:
                p_off = P_OFF["saturday"]
            elif rng.random() < P_LEAVE_CLUSTER:
                p_off = P_OFF["leave_cluster"]
            else:
                p_off = P_OFF["weekday"]
            working = [a for a in agents_by_queue[queue] if rng.random() > p_off]
            need = [max(1.0, PLAN_BUFFER * f * q["aht"] / INTERVAL_SECONDS / OCCUPANCY_TARGET) for f, _, _ in day_data]   # queue is never left empty
            shifts, coverage = plan_shifts(rng, need, len(working))

            # 3) Adherence rows for exactly the agents who were scheduled (same shifts).
            for agent_id, (_, length, _) in zip(working, shifts):
                scheduled_min = (length - 1) * 30   # paid minutes: span minus the lunch interval
                pct = min(1.0, max(0.5, rng.gauss(agent_skill[agent_id], 0.03)))
                adherence_rows.append((day.isoformat(), agent_id, scheduled_min, round(scheduled_min * pct)))

            # 4) Outcome of each interval, driven by how loaded the scheduled agents are.
            for slot, (forecast, offered, aht), scheduled in zip(slots, day_data, coverage):
                rho = offered * aht / (max(scheduled, 1) * INTERVAL_SECONDS)
                sl = 0.0 if scheduled == 0 else min(1.0, max(0.0, service_level(rho) + rng.gauss(0, 0.03)))
                abandoned = min(offered, noisy_count(rng, offered * (0.01 + 0.18 * (1 - sl))))
                answered = offered - abandoned
                within_20s = min(answered, round(offered * sl))
                interval_rows.append((day.isoformat(), slot, queue, forecast, offered, answered,
                                      abandoned, aht, within_20s, scheduled))

    DB_PATH.unlink(missing_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    con.executemany("INSERT INTO intervals VALUES (?,?,?,?,?,?,?,?,?,?)", interval_rows)
    con.executemany("INSERT INTO agents VALUES (?,?,?)", agent_rows)
    con.executemany("INSERT INTO adherence VALUES (?,?,?,?)", adherence_rows)
    con.commit()
    con.close()

    print(f"Created {DB_PATH}")
    print(f"  intervals: {len(interval_rows)}  agents: {len(agent_rows)}  adherence: {len(adherence_rows)}")
    print(f"  spike intervals injected: {len(spikes)}")


if __name__ == "__main__":
    main()
