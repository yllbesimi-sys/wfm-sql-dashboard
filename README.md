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
- [ ] Milestone 2 — SQL queries 1–4
- [ ] Milestone 3 — SQL queries 5–8
- [ ] Milestone 4 — dashboard
- [ ] Milestone 5 — polish, Vercel deploy, interview notes

## Try it

Needs Python 3 (no extra packages).

```bash
python scripts/generate_data.py   # rebuilds data/wfm.db (same result every time)
python scripts/check_data.py      # prints row counts and sample rows
```

## Project layout

| Path | What |
|---|---|
| `sql/` | One `.sql` file per business question (from Milestone 2) |
| `data/schema.sql` | Table definitions |
| `data/wfm.db` | The SQLite database |
| `scripts/` | Data generator and helper scripts |
| `docs/DATA.md` | What each column means and how the fake data is shaped |
| `docs/LEARNING.md` | Plain-language SQL explanations |
| `CLAUDE.md` | The working rules for the AI assistant |

## Simplifications

- Data is generated from simple formulas (daily/time-of-day curves, noise, a few injected spikes), not from a real
  contact center. See [docs/DATA.md](docs/DATA.md).
- The staffing formula used in the analysis is *workload ÷ occupancy target*. The industry-standard method is
  **Erlang C**, which also accounts for queueing and service-level targets; it is a natural next step.
