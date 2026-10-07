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
- [x] Milestone 3 — SQL queries 5–8
- [x] Milestone 4 — dashboard
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
| [`05_forecast_accuracy`](sql/05_forecast_accuracy.sql) | Forecast vs actual: MAPE, WAPE and bias per queue |
| [`06_wow_volume_change`](sql/06_wow_volume_change.sql) | Week-over-week volume change (window function `LAG`) |
| [`07_staffing_gap`](sql/07_staffing_gap.sql) | Agents needed vs scheduled per interval (simple formula, not Erlang C) |
| [`08_adherence_team_agent`](sql/08_adherence_team_agent.sql) | Schedule adherence per team and per agent |

Every query is explained line by line, in plain language, in [docs/LEARNING.md](docs/LEARNING.md).

## The dashboard

A static web page in [`dashboard/`](dashboard/): KPI cards, a forecast vs actual chart, a service-level heatmap (weekday × hour), a staffing-gap chart, filters for queue and date range, and a **"Show the SQL"** panel under every chart that displays the exact query behind it.

```bash
python scripts/export_dashboard.py                        # run the SQL, write dashboard/data/*.json
python -m http.server 8000 --directory dashboard          # then open http://localhost:8000
```

(Open it through the small web server above; double-clicking `index.html` cannot load the data files.)

```
data/wfm.db -> sql/dashboard/*.sql -> scripts/export_dashboard.py -> dashboard/data/*.json -> the page
              (all the logic)        (runs the SQL, no logic)        (committed to git)       (draws it)
```

**One deliberate compromise.** To let you pick any queue and date range without a server, the SQL exports *building blocks* (contacts offered, answered within 20 s, abandons, handle seconds ... per day or per hour). The browser adds up the rows you selected and divides once ("add up first, divide once"). Every metric definition lives in the SQL files; the JavaScript never defines a metric. [`scripts/verify_queries.py`](scripts/verify_queries.py) checks the exported numbers against the standalone queries (for example 102,045 contacts and 83.6% service level for the full period).

Known limits: light theme only; Chart.js 4.4.7 is vendored in [`dashboard/vendor/`](dashboard/vendor/) (see its README); the staffing need is the simplified formula, not Erlang C.

## Project layout

| Path | What |
|---|---|
| `sql/` | One `.sql` file per business question (`sql/dashboard/` feeds the dashboard) |
| `dashboard/` | The static dashboard (HTML, CSS, JS, exported JSON) |
| `data/schema.sql` | Table definitions |
| `data/wfm.db` | The SQLite database |
| `scripts/` | Data generator, query runner (`run_sql.py`), query checker (`verify_queries.py`), dashboard export (`export_dashboard.py`) |
| `docs/DATA.md` | What each column means and how the fake data is shaped |
| `docs/LEARNING.md` | Plain-language SQL explanations |
| `CLAUDE.md` | The working rules for the AI assistant |

## Simplifications

- Data is generated from simple formulas (daily/time-of-day curves, noise, a few injected spikes), not from a real
  contact center. See [docs/DATA.md](docs/DATA.md).
- The staffing formula used in the analysis is *workload ÷ occupancy target*. The industry-standard method is
  **Erlang C**, which also accounts for queueing and service-level targets; it is a natural next step.
