# WFM SQL Dashboard

A workforce-management (WFM) dashboard for a **fictional** contact center. Every metric — service level,
abandon rate, forecast accuracy, staffing gap, adherence — is calculated by a plain SQL query in [`/sql`](sql/).

> **Honesty notes**
> - **All data is synthetic.** It is produced by [`scripts/generate_data.py`](scripts/generate_data.py) with a fixed
>   random seed. No real employer, customer, or employee data was used. Agent IDs like `AGT-001` are made up.
> - **This project was built with AI assistance** (Claude Code). The author is a Workforce Management Analyst who
>   specified the domain, reviewed the work, and is learning SQL through it; the AI wrote most of the code.
> - Some things are deliberately simplified — see [Simplifications](#simplifications).

## What it is

- 3 queues: `Support-EN`, `Support-DE`, `Billing-EN`
- ~8 weeks of data, 30-minute intervals, Monday–Saturday, 08:00–20:00
- SQLite database in a single file: [`data/wfm.db`](data/) (committed, so the repo works right after cloning)
- 8 SQL questions (easiest first), a static dashboard, and a "Show the SQL" panel next to every chart

## Status

- [x] Milestone 1 — repo setup, synthetic data generator, database
- [x] Milestone 2 — SQL queries 1–4
- [ ] Milestone 3 — SQL queries 5–8
- [ ] Milestone 4 — dashboard
- [ ] Milestone 5 — polish, Vercel deploy, interview notes

## Try it

Needs Python 3 (no extra packages).

```bash
python scripts/generate_data.py   # rebuilds data/wfm.db (same result every time)
python scripts/check_data.py      # prints row counts and sample rows
```

Run the SQL queries (each one is a plain file in [`sql/`](sql/)):

```bash
python scripts/run_sql.py                                   # list the queries
python scripts/run_sql.py sql/02_aht_per_queue.sql          # run one and see the result table
python scripts/verify_queries.py                            # re-check every result with plain Python
```

| Query | Question it answers |
|---|---|
| [`01_offered_per_day_queue`](sql/01_offered_per_day_queue.sql) | Contacts offered per day, per queue |
| [`02_aht_per_queue`](sql/02_aht_per_queue.sql) | Average handle time per queue (weighted by contacts) |
| [`03_service_level_per_interval`](sql/03_service_level_per_interval.sql) | Service level per interval vs the 80/20 target |
| [`04_abandon_rate_weekly`](sql/04_abandon_rate_weekly.sql) | Abandon rate per queue per week |

Every query is explained line by line, in plain language, in [docs/LEARNING.md](docs/LEARNING.md).

## Project layout

| Path | What |
|---|---|
| `sql/` | One `.sql` file per business question |
| `data/schema.sql` | Table definitions |
| `data/wfm.db` | The SQLite database |
| `scripts/` | Data generator, query runner (`run_sql.py`), query checker (`verify_queries.py`) |
| `docs/DATA.md` | What each column means and how the fake data is shaped |
| `docs/LEARNING.md` | Plain-language SQL explanations |
| `CLAUDE.md` | The working rules for the AI assistant |

## Simplifications

- Data is generated from simple formulas (daily/time-of-day curves, noise, a few injected spikes), not from a real
  contact center. See [docs/DATA.md](docs/DATA.md).
- The staffing formula used in the analysis is *workload ÷ occupancy target*. The industry-standard method is
  **Erlang C**, which also accounts for queueing and service-level targets; it is a natural next step.
