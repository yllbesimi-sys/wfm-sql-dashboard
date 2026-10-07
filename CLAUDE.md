# CLAUDE.md — project rules (follow in every session)

Project: a workforce-management (WFM) dashboard for a FICTIONAL contact center, fed by SQL queries.
Owner: a Workforce Management Analyst (strong WFM domain knowledge, beginner at SQL/programming).
Claude does the programming; the owner reviews, runs, and asks questions. The repo is a portfolio
project for job applications, so it must be honest, clean, and explainable.

## Rules

1. **PLAN FIRST.** Before writing code in any milestone, show a short plan and wait for approval.
2. **EXPLAIN EVERYTHING IN PLAIN LANGUAGE.** After writing each SQL query, explain it line by line
   as if the reader is new to SQL, and say what business question it answers. Put these
   explanations in `docs/LEARNING.md` as you go.
3. **SMALL STEPS.** Work in milestones. After each milestone: say how to run it, what the owner
   should see, then commit with a clear message and push to GitHub.
4. **SQL IS THE STAR.** All metrics come from plain `.sql` files in `/sql`, each with comments at
   the top saying what question it answers. No metric logic hidden in application code.
5. **FICTIONAL DATA ONLY.** Synthetic data from a script with a fixed random seed. Never use or ask
   for real employer or customer data. No real names; IDs like `AGT-001`.
6. **NO SECRETS IN GIT.** Never commit passwords, API keys, or `.env` files. Tell the owner if
   anything like that is needed.
7. **BE HONEST.** The README must say the data is synthetic and the project was built with AI
   assistance. If something is simplified (e.g. the staffing formula), say so in the docs.
8. **KEEP IT SIMPLE.** Prefer the simplest approach that works. When picking a tool, say why in
   two sentences.
9. **WHEN ASKED "WHY", EXPLAIN.** Explain the choice and mention what the alternative was.

## Milestones

1. Repo setup, CLAUDE.md, README skeleton, synthetic data generator, database created.
2. SQL queries 1 to 4, with explanations and a way to run each one and see results.
3. SQL queries 5 to 8, with explanations.
4. The dashboard (static site; queries run at build time, results exported; "Show the SQL" panels).
5. Polish: README with screenshots, Vercel deploy, final cleanup, `docs/INTERVIEW.md`.

## Project facts

- 3 queues: Support-EN, Support-DE, Billing-EN. ~8 weeks, 30-minute intervals, Mon–Sat, 08:00–20:00.
- SQLite database in one file: `data/wfm.db` (committed on purpose, so the repo runs after cloning).
- Tables: `intervals`, `agents`, `adherence` (schema in `data/schema.sql`).
- Service level target: 80/20 (80% of contacts answered within 20 seconds).
- Staffing formula is deliberately simple (workload hours / occupancy target); Erlang C is the
  industry-standard next step and must be mentioned in the docs.
- Dashboard: static site in `dashboard/` (plain HTML/CSS/JS + vendored Chart.js 4.4.7). `scripts/export_dashboard.py`
  runs `sql/dashboard/*.sql` and writes `dashboard/data/*.json` (committed). After changing the SQL or the database,
  re-run the export, then `python scripts/verify_queries.py` (it fails if the JSON is stale). The JS only adds up the
  SQL's building blocks and divides; it must never define a metric.
- Deployment: Vercel project `wfm-sql-dashboard` (personal account), root directory `dashboard/`, no build step, auto-deploys
  on every push to `main`. Live at https://wfm-sql-dashboard.vercel.app. Re-export the JSON before pushing SQL/data changes.
- Git remote: https://github.com/yllbesimi-sys/wfm-sql-dashboard.git (branch `main`).
  This folder is its own git repo; the home folder above it is a different repo — never commit there.
