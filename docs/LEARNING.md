# SQL learning notes

Plain-language explanations of every query in this project, written as I go. Query explanations start in Milestone 2.

## Basics you need first

**SQL** is a language for asking questions of tables. A **table** is like an Excel sheet: columns (fields) and rows
(records). A **database** is a collection of tables.

**SQLite** is a database that lives in one file (`data/wfm.db`). There is no server and no password; any program
(or the `sqlite3` tool) can open the file and run SQL against it.

### Our three tables

- `intervals` — one row per **queue × day × half-hour**. This is the main table: volume, answered, abandoned, AHT,
  scheduled agents. (Think: your interval report.)
- `agents` — one row per agent (who they are, which team and queue).
- `adherence` — one row per **agent × day**: scheduled minutes vs. minutes in adherence.

### How the table definitions read (from `data/schema.sql`)

```sql
CREATE TABLE intervals (                 -- "make a new table called intervals"
    date           TEXT    NOT NULL,     -- a column called date; TEXT = stored as text; NOT NULL = may not be empty
    offered        INTEGER NOT NULL,     -- INTEGER = a whole number
    ...
    PRIMARY KEY (date, interval_start, queue)   -- these three together identify a row; no duplicates allowed
);
```

The five SQL words you will meet again and again: `SELECT` (which columns), `FROM` (which table),
`WHERE` (filter rows), `GROUP BY` (one result row per group), `ORDER BY` (sort).
Each query explanation below will show them in action.

### The order SQL thinks in (not the order it is written in)

You *write* `SELECT` first, but SQL *works* in this order, which is a useful way to read any query:

1. `FROM` — pick the table.
2. `WHERE` — throw away rows you don't want (optional).
3. `GROUP BY` — put the remaining rows into buckets (optional).
4. `SELECT` — decide which columns / calculations to show.
5. `ORDER BY` — sort the result.

## How to run a query

```bash
python scripts/run_sql.py                                   # list the available queries
python scripts/run_sql.py sql/01_offered_per_day_queue.sql  # run one
python scripts/run_sql.py sql/03_service_level_per_interval.sql --limit 0   # show every row
```

- The script opens the database **read-only**, so you cannot damage the data by experimenting.
- Long results are cut to 40 rows. Add `--limit 0` to see all rows.
- To change a query: open the `.sql` file in any editor, change it, save, run it again.
- `NULL` in a result means "no value / unknown". It is not the same as 0.
- `python scripts/verify_queries.py` recalculates every result in plain Python and compares it with the SQL.

---

## Query 1 — Offered contacts per day, per queue

**File:** `sql/01_offered_per_day_queue.sql`
**Business question:** How many contacts did each queue receive each day?
**Why it matters:** Daily volume is the base of forecasting. It shows which weekdays are heavy and which days were unusual.

```sql
SELECT
    date,
    queue,
    SUM(offered) AS offered_contacts
FROM intervals
GROUP BY date, queue
ORDER BY date, queue;
```

**Line by line**

| Line | What it means |
|---|---|
| `SELECT` | "Show me these columns." Everything up to `FROM` is the list of result columns. |
| `date,` `queue,` | Copy these two columns into the result as they are. |
| `SUM(offered) AS offered_contacts` | Add up the `offered` numbers. `SUM` is an *aggregate function*: it squashes many rows into one number. `AS offered_contacts` gives the result column a readable name (an *alias*). |
| `FROM intervals` | Take the data from the `intervals` table (one row per queue per half-hour). |
| `GROUP BY date, queue` | "Make one bucket for every combination of date and queue." Each bucket holds 24 rows (the 24 half-hours of that day) and `SUM` adds up inside each bucket. Without `GROUP BY`, `SUM` would add up the whole table into a single number. Rule of thumb: every column in `SELECT` that is *not* inside an aggregate must be in `GROUP BY`. |
| `ORDER BY date, queue` | Sort by date first, then by queue name within each date. Without `ORDER BY`, SQL promises no particular order. |
| `;` | The end of the query. |

**What you should see:** 144 rows (48 days × 3 queues).

```
date        queue       offered_contacts
2026-08-03  Billing-EN               701
2026-08-03  Support-DE               485
2026-08-03  Support-EN              1177
```

- The whole period holds 102,045 offered contacts.
- The busiest day-queue is Support-EN on 2026-08-24 (1,367 contacts). The quietest is Support-DE on Saturday 2026-09-26 (253).
- Monday 2026-08-03 brought Support-EN 1,177 contacts; Saturday 2026-08-08 only 727. Saturdays are lighter by design.

**WFM note:** compare like with like — Mondays with Mondays. On Saturday 2026-08-22, Support-EN received 867 contacts, about 29% above a typical Saturday for that queue (the forecast said 657). Daily totals show *that* a day was unusual but not *when* in the day. Query 3 looks inside the day.

**Try it yourself:** add `WHERE queue = 'Support-EN'` on its own line between `FROM intervals` and `GROUP BY ...`. You now get 48 rows, one queue only. (That is step 2 of "the order SQL thinks in": filter first, then group.)

---

## Query 2 — Average handle time (AHT) per queue

**File:** `sql/02_aht_per_queue.sql`
**Business question:** What is the average handle time of each queue?
**Why it matters:** Workload = contacts × AHT. A small AHT mistake becomes a staffing mistake.

```sql
SELECT
    queue,
    ROUND(1.0 * SUM(aht_seconds * answered) / SUM(answered), 1) AS aht_weighted_sec,
    ROUND(AVG(aht_seconds), 1)                                  AS aht_simple_avg_sec,
    SUM(answered)                                               AS answered_contacts
FROM intervals
GROUP BY queue
ORDER BY queue;
```

**The idea first.** Each row of `intervals` already contains an *average* (`aht_seconds` for that half-hour). If we simply average those 1,152 averages per queue, a quiet interval with 8 calls counts as much as a busy one with 80. A fair AHT counts each *call* equally. So we weight each interval's average by how many contacts it covers (`answered`).

Tiny example: interval A has 10 contacts at 300 s, interval B has 90 contacts at 500 s.
Simple average of the two = (300 + 500) / 2 = **400 s**. Weighted = (10 × 300 + 90 × 500) / 100 = **480 s** — the true figure, because 90% of the calls were the 500 s kind.

**Line by line**

| Line | What it means |
|---|---|
| `queue,` | Show the queue name. |
| `aht_seconds * answered` | Per row: average seconds × number of contacts = *total handle seconds* in that interval. |
| `SUM(aht_seconds * answered)` | Add those totals up over the whole queue = all handle seconds ever worked. |
| `/ SUM(answered)` | Divide by the total number of answered contacts = seconds per contact. This is the weighted average. |
| `1.0 *` | SQLite divides whole numbers as whole numbers (`7 / 2` gives `3`). Multiplying by `1.0` first switches it to decimal maths (`3.5`). |
| `ROUND(..., 1)` | Round to one decimal place. |
| `AVG(aht_seconds)` | The plain average of the interval averages (every interval counts equally). Shown for comparison. |
| `SUM(answered) AS answered_contacts` | How many contacts stand behind the number. |
| `GROUP BY queue` | One bucket per queue, so 3 result rows. |

**What you should see:**

```
queue       aht_weighted_sec  aht_simple_avg_sec  answered_contacts
Billing-EN             538.0               538.6              29231
Support-DE             480.9               480.5              19544
Support-EN             418.7               419.2              48697
```

That is about 9.0, 8.0 and 7.0 minutes per contact.

**Honest note:** here the two columns are almost the same (under 1 second apart). That is because the fake data gives every interval the same AHT noise regardless of volume. In real data AHT often differs between busy and quiet times, and then the weighted number can differ noticeably. The weighted one is the correct method either way, so it is the headline figure.

**Try it yourself:** add `WHERE interval_start >= '12:00'` between `FROM` and `GROUP BY` to see the AHT of afternoon intervals only.

---

## Query 3 — Service level per interval (80/20 target)

**File:** `sql/03_service_level_per_interval.sql`
**Business question:** What service level did each half-hour achieve, and did it hit the 80/20 target?
**Why it matters:** Service level is the main quality target. Per interval it shows *when* the queue is under-staffed, which a daily average hides.

```sql
SELECT
    date,
    interval_start,
    queue,
    offered,
    answered_within_20s,
    ROUND(100.0 * answered_within_20s / NULLIF(offered, 0), 1) AS service_level_pct,
    CASE
        WHEN offered = 0 THEN NULL
        WHEN 100.0 * answered_within_20s / offered >= 80 THEN 'yes'
        ELSE 'no'
    END AS meets_80_20
FROM intervals
ORDER BY date, interval_start, queue;
```

**Definition:** service level % = contacts answered within 20 seconds ÷ contacts **offered** × 100. We divide by *offered* (everyone who called), so people who gave up count against us. Dividing by *answered* is also used in some centers, but it flatters the number when many people abandon. "80/20" means: at least 80% answered within 20 seconds.

**Line by line**

| Line | What it means |
|---|---|
| `date, interval_start, queue, offered, answered_within_20s,` | Plain columns, copied as they are, so you can see the numbers behind the percentage. |
| `100.0 * answered_within_20s / ...` | Turn the fraction into a percentage. `100.0` (with the `.0`) forces decimal maths, see Query 2. |
| `NULLIF(offered, 0)` | Returns `offered` normally, but returns `NULL` ("unknown") when `offered` is 0. **Why:** dividing by 0 is impossible, and the result for those rows must be "unknown". Dividing by `NULL` gives `NULL`. (SQLite would give `NULL` for `x / 0` on its own, but many databases, e.g. PostgreSQL and SQL Server, stop with an error. `NULLIF` makes the intent explicit and works everywhere.) 3 intervals in our data really have zero contacts (all Support-DE, at 18:00 / 19:00 / 19:30). |
| `ROUND(..., 1) AS service_level_pct` | One decimal, and a readable column name. |
| `CASE ... END` | SQL's version of if / else. It reads top to bottom and the **first match wins**. |
| `WHEN offered = 0 THEN NULL` | No contacts, so no verdict (neither pass nor fail). |
| `WHEN 100.0 * answered_within_20s / offered >= 80 THEN 'yes'` | At or above the target. (We can divide by `offered` here without `NULLIF`, because the line above already caught the zero case.) We compare the *unrounded* value on purpose. |
| `ELSE 'no'` | Everything else misses the target. |
| `END AS meets_80_20` | Close the `CASE` and name the new column. |
| `FROM intervals` | No `GROUP BY` this time: we do **not** want to collapse rows. One result row per interval = 3,456 rows. |
| `ORDER BY date, interval_start, queue` | Chronological, queues side by side. |

**What you should see:** 3,456 rows. The first ones:

```
date        interval_start  queue       offered  answered_within_20s  service_level_pct  meets_80_20
2026-08-03  08:00           Billing-EN       14                   14              100.0  yes
2026-08-03  08:00           Support-DE       11                   11              100.0  yes
2026-08-03  08:00           Support-EN       28                   26               92.9  yes
...
2026-08-03  09:00           Billing-EN       42                   26               61.9  no
```

- 2,794 intervals meet 80/20, 659 miss it, and 3 are `NULL` (no contacts). So about 81% of the intervals with contacts hit the target.
- Careful: that is a share of *intervals*. The service level of the whole period (all answered-within-20s ÷ all offered) is 83.6%. Busy intervals weigh more in that second number.

**WFM notes**
- Small intervals are noisy: with 11 contacts, one late call moves service level by 9 points.
- Never average the interval percentages to get a period service level. Add up the numerators and denominators, then divide once (the same trap as Query 4).
- In this fake data the worst intervals are at 0.0%. That is what a badly overloaded queue looks like in the model.

**Try it yourself**
- One queue, one day: add `WHERE queue = 'Support-EN' AND date = '2026-08-11'` before `ORDER BY`. You get 24 rows and can watch the day unfold.
- Worst first: replace the `ORDER BY` line with `WHERE offered > 0` and then `ORDER BY service_level_pct ASC;` (on separate lines). Without the `WHERE`, the three `NULL` rows would come first, because SQLite sorts `NULL` before every number.

---

## Query 4 — Abandon rate per queue per week

**File:** `sql/04_abandon_rate_weekly.sql`
**Business question:** What share of contacts hang up before being answered, per queue per week?
**Why it matters:** Abandons are the customer-visible cost of under-staffing. A weekly view shows whether things get better or worse.

```sql
SELECT
    date(date, '-6 days', 'weekday 1') AS week_start,
    queue,
    SUM(offered)                       AS offered,
    SUM(abandoned)                     AS abandoned,
    ROUND(100.0 * SUM(abandoned) / SUM(offered), 2) AS abandon_rate_pct
FROM intervals
GROUP BY week_start, queue
ORDER BY week_start, queue;
```

**Line by line**

| Line | What it means |
|---|---|
| `date(date, '-6 days', 'weekday 1')` | SQLite's `date()` function takes a date and then applies *modifiers* one after another. `'-6 days'` goes back six days. `'weekday 1'` then moves **forward** to the next Monday (0 = Sunday, 1 = Monday, ...), or stays put if it already is a Monday. Together they give "the Monday of this date's week". Example: Wednesday 2026-08-05 → 2026-07-30 → next Monday is 2026-08-03. Monday 2026-08-03 → 2026-07-28 → next Monday is 2026-08-03 (itself). |
| `AS week_start` | Name that value `week_start`. Every day of one week now carries the same label, so we can group by it. |
| `SUM(offered)`, `SUM(abandoned)` | Total contacts and total abandons in each week/queue bucket. |
| `100.0 * SUM(abandoned) / SUM(offered)` | Abandon rate: **add up first, divide once**. |
| `ROUND(..., 2)` | Two decimals (the rates are small numbers). |
| `GROUP BY week_start, queue` | One bucket per week per queue: 8 × 3 = 24. SQLite lets you reuse the alias `week_start` here; some other databases make you repeat the whole expression. |
| `ORDER BY week_start, queue` | Weeks in order, queues side by side. |

**What you should see:** 24 rows, e.g.

```
week_start  queue       offered  abandoned  abandon_rate_pct
2026-08-03  Billing-EN     3684        222              6.03
2026-08-03  Support-DE     2526        139               5.5
2026-08-03  Support-EN     6284        193              3.07
```

- Highest: Support-DE, week of 2026-09-14, **6.78%** (177 of 2,611).
- Lowest: Billing-EN, week of 2026-08-10, **3.06%** (110 of 3,600).
- Billing-EN swings from 6.03% in week 1 to 3.06% in week 2 and 6.48% in week 8. The generator has no built-in trend in abandons, so these ups and downs come from where spikes, leave days and short shifts happened to fall.

**WFM note — why "add up, then divide":** imagine interval A has 1 abandon out of 5 contacts (20%) and interval B has 4 out of 100 (4%). Averaging the two percentages gives 12%. The truth is 5 abandons out of 105 contacts = **4.76%**. Averaging percentages lets tiny intervals shout as loudly as huge ones.

**Simplification:** the data has no wait times, so we cannot ignore very short abandons (many centers exclude abandons in the first few seconds). Weeks run Monday to Sunday and our data stops on Saturday, so Sunday never appears.

**Try it yourself:** put `WHERE queue = 'Support-DE'` between `FROM` and `GROUP BY` to see one queue's 8 weeks.

---

## Query 5 — Forecast accuracy (MAPE, WAPE, bias)

**File:** `sql/05_forecast_accuracy.sql`
**Business question:** How far off was the volume forecast, per queue?
**Why it matters:** Every schedule starts from the forecast. Accuracy says how much to trust it; bias says whether you tend to over- or under-staff.

```sql
SELECT
    queue,
    COUNT(*)                                                                   AS intervals_compared,
    ROUND(100.0 * AVG(ABS(offered - forecast_offered) * 1.0 / offered), 1)     AS mape_pct,
    ROUND(100.0 * SUM(ABS(offered - forecast_offered)) / SUM(offered), 1)      AS wape_pct,
    ROUND(100.0 * (SUM(forecast_offered) - SUM(offered)) / SUM(offered), 1)    AS bias_pct
FROM intervals
WHERE offered > 0
GROUP BY queue
ORDER BY queue;
```

**The three measures** (all per 30-minute interval, forecast vs actual `offered`):

| Measure | In words | Good for |
|---|---|---|
| **MAPE** (mean absolute percentage error) | For each interval: how far off was the forecast, as a % of what really came in? Then average those %. | The classic number. Every interval counts equally. |
| **WAPE** (weighted absolute percentage error) | Total miss in contacts ÷ total actual contacts. | Busy intervals count more. Not blown up by tiny intervals. |
| **Bias** | Total forecast vs total actual, *keeping the sign*. Positive = over-forecast, negative = under-forecast. | Seeing whether you are systematically high or low. |

**Line by line**

| Line | What it means |
|---|---|
| `COUNT(*)` | How many rows are in each bucket (here: intervals that were compared). |
| `ABS(offered - forecast_offered)` | The size of the miss, ignoring direction (`ABS` = absolute value: -5 and 5 both become 5). Without it, over- and under-forecasts would cancel each other out. |
| `* 1.0 / offered` | Miss as a fraction of the actual volume (`1.0` forces decimal maths, see Query 2). |
| `AVG(...)` | Average of those fractions over the queue's intervals. `100.0 *` turns it into a percent. That is **MAPE**. |
| `SUM(ABS(...)) / SUM(offered)` | Add up all the misses, divide by all the actual contacts: **WAPE**. |
| `SUM(forecast_offered) - SUM(offered)` | No `ABS` here: over and under cancel, so what remains is the **bias**. |
| `WHERE offered > 0` | Leave out intervals with no actual contacts: a % of zero can't be calculated. `WHERE` runs *before* `GROUP BY` (step 2 in "the order SQL thinks in"), so those 3 rows never reach the buckets. |

**What you should see:**

```
queue       intervals_compared  mape_pct  wape_pct  bias_pct
Billing-EN                1152      21.5      15.8      -0.5
Support-DE                1149      25.3      19.0      -1.6
Support-EN                1152      15.9      13.4      -0.1
```

- The smaller the queue, the worse the accuracy: Support-EN (biggest) has 15.9% MAPE, Support-DE (smallest) 25.3%. With 10 to 20 contacts per interval, a miss of 3 or 4 contacts is just normal randomness.
- Bias is close to zero everywhere: the forecast is not systematically high or low. Yet MAPE is large. Errors cancel out in the total but not interval by interval. That is why one number is never enough.
- MAPE is higher than WAPE because small intervals have big percentage errors (actual 2, forecast 4 = 100% error) and MAPE gives them full weight.

**Honest note:** in this fake data the forecast is "the true expected volume ± 5% noise", while actual volume adds random arrival noise and unforecast spikes. So most of the error is random and cannot be forecast away. A real forecast has structural errors too (missed trends, campaigns, holidays).

**Try it yourself:** change `WHERE offered > 0` to `WHERE offered >= 20`. MAPE drops (to 14.4 / 16.0 / 14.1) because the tiny intervals are gone. But look at `bias_pct`: Support-DE jumps to -6.6%. That is a trap: choosing intervals by their *actual* volume keeps the ones that happened to come in high, so the forecast looks too low. Never filter on the thing you are measuring against.

---

## Query 6 — Week-over-week volume change (LAG)

**File:** `sql/06_wow_volume_change.sql`
**Business question:** How did each queue's weekly volume change compared with the week before?
**Why it matters:** It shows growth, seasonality and one-off events, and whether last week is a fair guide for next week.

```sql
WITH weekly AS (
    SELECT
        date(date, '-6 days', 'weekday 1') AS week_start,
        queue,
        SUM(offered)                       AS offered
    FROM intervals
    GROUP BY week_start, queue
),
with_previous AS (
    SELECT
        week_start,
        queue,
        offered,
        LAG(offered) OVER (PARTITION BY queue ORDER BY week_start) AS previous_week_offered
    FROM weekly
)
SELECT
    week_start,
    queue,
    offered,
    previous_week_offered,
    offered - previous_week_offered                                           AS change,
    ROUND(100.0 * (offered - previous_week_offered) / previous_week_offered, 1) AS wow_change_pct
FROM with_previous
ORDER BY queue, week_start;
```

**New idea 1 — `WITH ... AS` (a named step).** It lets you build a result in stages. `weekly` is a small temporary table that exists only while this query runs; `with_previous` builds on it; the last `SELECT` builds on that. Read it top to bottom like a recipe. The inside of `weekly` is exactly the weekly grouping from Query 4.

**New idea 2 — window functions.** `GROUP BY` collapses many rows into one. A *window function* does not collapse anything: every row stays, and it just adds a column calculated by looking at *other* rows. Here `LAG` looks one row back.

**Line by line**

| Line | What it means |
|---|---|
| `LAG(offered)` | "The `offered` value from the previous row." |
| `OVER (...)` | Says *which* previous row: this defines the window. |
| `PARTITION BY queue` | Handle each queue separately. Without it, Support-DE's first week would borrow Billing-EN's last week. |
| `ORDER BY week_start` | Inside each queue, "previous" means "the earlier week". |
| (first week of each queue) | There is no earlier row, so `LAG` gives `NULL`. |
| `offered - previous_week_offered` | Change in contacts. With `NULL` in it, the answer is `NULL` too. |
| `100.0 * change / previous_week_offered` | Change as a percent of last week. |
| `ORDER BY queue, week_start` | Each queue's story reads top to bottom. |

**Why two steps and not one?** Repeating `LAG(...)` three times in the final `SELECT` would be messy; the named step calculates it once and gives it a name.

**What you should see:** 24 rows, 3 of them with `NULL` (week 1 of each queue). Support-EN:

```
week_start  offered  previous  change  wow_change_pct
2026-08-03     6284  NULL      NULL    NULL
2026-08-10     6344  6284        60      1.0
2026-08-17     6325  6344       -19     -0.3
2026-08-24     6446  6325       121      1.9
2026-08-31     6309  6446      -137     -2.1
```

- Biggest rise: Billing-EN, week of 2026-08-17: **+7.0%** (3,600 to 3,851). Biggest fall: Support-DE, week of 2026-08-10: **-3.1%**.
- The generator adds about 1% growth per week, but the week-to-week noise (±2%) is larger, so you see wobble around a slow upward drift.

**WFM note:** comparing weeks is only fair when they have the same length and no special days. All 8 weeks here are full Monday to Saturday weeks. With a bank-holiday week you would adjust first.

**Try it yourself:** change `LAG(offered)` to `LAG(offered, 2)` (two weeks back). The first *two* weeks of each queue become `NULL`, and the comparison is with two weeks ago. (The column name `previous_week_offered` would then be misleading, so rename it as well.)

---

## Query 7 — Staffing gap (agents needed vs scheduled)

**File:** `sql/07_staffing_gap.sql`
**Business question:** In each half-hour, how many agents were needed compared with how many were scheduled?
**Why it matters:** This is the heart of capacity planning: it shows exactly *when* the schedule is too thin or too generous.

```sql
WITH needed AS (
    SELECT
        date, interval_start, queue, offered, aht_seconds, scheduled_agents,
        offered * aht_seconds / 1800.0 / 0.85 AS agents_needed
    FROM intervals
)
SELECT
    date, interval_start, queue, offered, aht_seconds, scheduled_agents,
    ROUND(agents_needed, 1)                    AS agents_needed,
    ROUND(scheduled_agents - agents_needed, 1) AS staffing_gap,
    CASE WHEN scheduled_agents < agents_needed THEN 'short' ELSE 'ok' END AS status
FROM needed
ORDER BY date, interval_start, queue;
```

**The formula — deliberately simple.** In plain steps:

1. **Workload in seconds** = contacts × average handle time.
2. **Agents it would keep fully busy** = workload ÷ 1,800 (the seconds in one 30-minute interval).
3. **Agents needed** = that ÷ 0.85 (the *occupancy target*). Agents can't be busy 100% of the time; there must be gaps to breathe and wait for the next contact. At 85% busy, you need about 18% more people than "fully busy".
4. **Gap** = scheduled − needed. Negative = short-staffed.

Worked example from the output: Billing-EN, 2026-08-03, 09:00. 42 contacts × 529 s = 22,218 s. ÷ 1,800 = 12.3 agents fully busy. ÷ 0.85 = **14.5 needed**. Only 13 were scheduled, so the gap is **-1.5** and the status is `short`.

**Line by line**

| Line | What it means |
|---|---|
| `WITH needed AS (...)` | A named step that calculates `agents_needed` once. Otherwise the formula would be pasted three times into the final `SELECT`. |
| `1800.0` | The `.0` keeps the maths in decimals (see Query 2). |
| `ROUND(agents_needed, 1)` | Show one decimal. The number stays fractional on purpose (14.5 agents means "between 14 and 15"). |
| `scheduled_agents - agents_needed` | The gap. |
| `CASE WHEN scheduled_agents < agents_needed ...` | `short` if scheduled is below needed, else `ok`. It compares the *unrounded* numbers. |
| `FROM needed` | The final `SELECT` reads from the named step above, not from the raw table. |

**What you should see:** 3,456 rows.

- 730 intervals are `short` (21%) and 2,726 `ok`.
- When it happens: 64% of the 19:00 to 19:59 intervals are short, 56% of the 10:00 to 10:59 intervals, and only 2% of the 12:00 to 12:59 ones. Thin evening cover and an under-covered morning peak, with a comfortable lunch.
- Worst gap: Support-EN, Monday 2026-09-21, 10:00: 103 contacts at 406 s needed **27.3** agents; only **15** were scheduled (gap -12.3).
- Most over-staffed: Support-EN, 2026-09-10, 12:00: 23 contacts needed 5.5 agents; 23 were scheduled (gap +17.5).

**WFM note — averages hide the problem.** Add up all gaps and each queue has a *surplus* (e.g. Support-EN +4,291 agent-intervals). Yet 730 intervals are short. You can't use the extra people at 12:00 to cover the shortage at 10:00, so the interval view matters.

**Honest limits (also in the SQL comments):**
- This is a **simplification, not Erlang C.** Erlang C is the industry-standard method: it also considers how contacts queue up and the service-level target (80/20), and usually needs more agents than this formula. It is the natural next step for this project.
- It uses **actual** contacts and AHT (hindsight), not the forecast.
- There is **no shrinkage** (breaks, meetings, training); lunch is already out of `scheduled_agents`.
- The data generator's planner used the same idea (workload ÷ 85% occupancy), so this query agrees with the data *by construction*. It is a good illustration, not independent proof that the method is right.

**Try it yourself:** change `0.85` to `0.75` (a relaxed target, more people needed): short intervals rise from 730 to 1,066. Change it to `0.90`: they fall to 587. One number in the query changes the whole staffing picture.

---

## Query 8 — Adherence per team and per agent

**File:** `sql/08_adherence_team_agent.sql`
**Business question:** How well did each team, and each agent, stick to their schedule?
**Why it matters:** Low adherence means the agents you scheduled weren't really available, so you get less capacity than planned. Team level shows patterns; agent level shows who needs a conversation.

```sql
SELECT
    'team'                    AS level,
    a.team,
    NULL                      AS agent_id,
    a.queue,
    COUNT(*)                  AS shifts_worked,
    SUM(h.scheduled_minutes)  AS scheduled_minutes,
    SUM(h.adherent_minutes)   AS adherent_minutes,
    ROUND(100.0 * SUM(h.adherent_minutes) / SUM(h.scheduled_minutes), 1) AS adherence_pct
FROM adherence AS h
JOIN agents    AS a ON a.agent_id = h.agent_id
GROUP BY a.team, a.queue

UNION ALL

SELECT
    'agent',
    a.team,
    h.agent_id,
    a.queue,
    COUNT(*),
    SUM(h.scheduled_minutes),
    SUM(h.adherent_minutes),
    ROUND(100.0 * SUM(h.adherent_minutes) / SUM(h.scheduled_minutes), 1)
FROM adherence AS h
JOIN agents    AS a ON a.agent_id = h.agent_id
GROUP BY a.team, a.queue, h.agent_id

ORDER BY level DESC, team, agent_id;
```

**New idea 1 — `JOIN` (combining two tables).** The `adherence` table knows *which agent* worked *how many minutes*, but not the agent's team. The `agents` table knows the team. `JOIN agents ON a.agent_id = h.agent_id` says: "for each adherence row, find the agents row with the same `agent_id` and attach its columns." Now every adherence row also carries `team` and `queue`.
`AS h` and `AS a` are short nicknames for the two tables, so `h.scheduled_minutes` means "the `scheduled_minutes` column from `adherence`". (A plain `JOIN` keeps only rows that find a match. All 69 agents exist in both tables, so nothing is lost.)

**New idea 2 — `UNION ALL` (stacking results).** The first `SELECT` produces the 4 team rows, the second the 69 agent rows, and `UNION ALL` stacks them into one result. Both halves must have the same columns in the same order; the column names come from the first one. (`UNION` without `ALL` also removes duplicates, which we don't need.)

**Line by line**

| Line | What it means |
|---|---|
| `'team' AS level` | A constant text in every row of this half, so you can tell team rows from agent rows. |
| `NULL AS agent_id` | A team has no single agent; `NULL` fills the slot so both halves have the same columns. |
| `COUNT(*) AS shifts_worked` | Rows in the bucket = shifts worked (one adherence row per agent per day worked). |
| `SUM(...)` for minutes | Total scheduled and total adherent minutes in the bucket. |
| `100.0 * SUM(adherent) / SUM(scheduled)` | Adherence %: **add up, then divide once.** A 7-hour day weighs less than an 8-hour day, as it should. |
| `GROUP BY a.team, a.queue` | One bucket per team (4). `queue` is included only because we show it; each team belongs to one queue. |
| `GROUP BY a.team, a.queue, h.agent_id` | One bucket per agent (69). |
| `ORDER BY level DESC, team, agent_id` | Sorts the whole stacked result. `'team'` comes after `'agent'` in the alphabet, so `DESC` puts the team rows first. After a `UNION`, `ORDER BY` can only use the result's column names (no `a.` / `h.`). |

**What you should see:** 73 rows (4 team + 69 agent).

```
level  team     agent_id  queue       shifts_worked  scheduled_minutes  adherent_minutes  adherence_pct
team   Alpha    NULL      Support-EN            572             271380            246512           90.8
team   Bravo    NULL      Support-EN            579             274680            242343           88.2
team   Charlie  NULL      Support-DE            580             275340            250508           91.0
team   Delta    NULL      Billing-EN            932             442440            397684           89.9
agent  Alpha    AGT-001   Support-EN             37              17760             16476           92.8
```

- Bravo is the lowest team at 88.2%; Charlie is the highest at 91.0%.
- Agents range from **96.4%** (AGT-061) down to **83.8%** (AGT-068), both on team Delta. 10 of the 69 agents are below 85%.

**WFM notes**
- A team's adherence is *not* the average of its agents' percentages: it is weighted by minutes (add up, then divide), the same reasoning as Query 4.
- Adherence is not occupancy or conformance: it only says whether the agent was in the right state at the scheduled time.

**Honest note:** the generator gives each agent a stable personal adherence level (84 to 97%) plus daily noise, so the same agents show up as low every time. That is realistic, but it is by construction. Also, adherence has no effect on service level in this fake data, so don't read causality into it.

**Try it yourself:** replace the last line with `ORDER BY level DESC, adherence_pct ASC;` and the lowest adherence comes first within each level (Bravo at the top of the teams, AGT-068 at the top of the agents).

---

## Dashboard queries (`sql/dashboard/`)

The dashboard is a static web page: there is no server and no database behind it. The queries below run once, when you run `python scripts/export_dashboard.py`, and their results are saved as JSON files that the page reads.

**Why these queries look different from 1–8.** The dashboard lets you pick *any* queue and *any* date range. The page can't re-run SQL, so each query exports **building blocks** (counts and sums per day, or per day and hour). When you change a filter, the page adds up the blocks of the rows you selected and then divides **once**: *add up first, divide once*, exactly like Queries 4, 5 and 8. The definitions of every metric live in the SQL headers; the page only adds and divides. (Averaging ready-made percentages would be wrong, see Query 4.)

Worked example, Support-EN for the first week (2026-08-03 to 2026-08-08), six day-rows of query D1 added up:

| Block | Sum | KPI | How |
|---|---|---|---|
| offered | 6,284 | | |
| answered_within_20s | 5,685 | Service level **90.5%** | 5,685 ÷ 6,284 |
| abandoned | 193 | Abandon rate **3.1%** | 193 ÷ 6,284 (the same 3.07% as Query 4) |
| handle_seconds | 2,536,821 | AHT **416.5 s** | 2,536,821 ÷ 6,091 answered |
| abs_forecast_error | 815 | Forecast error (WAPE) **13.0%** | 815 ÷ 6,284 |

---

### D1 — KPI building blocks per day and queue

**File:** `sql/dashboard/01_kpi_daily.sql` · **Feeds:** KPI cards 1–5
**Business question:** What are the building blocks of the headline KPIs, per day and queue?

```sql
SELECT
    date,
    queue,
    SUM(offered)                                AS offered,
    SUM(answered)                               AS answered,
    SUM(abandoned)                              AS abandoned,
    SUM(answered_within_20s)                    AS answered_within_20s,
    SUM(aht_seconds * answered)                 AS handle_seconds,
    SUM(ABS(offered - forecast_offered))        AS abs_forecast_error
FROM intervals
WHERE offered > 0
GROUP BY date, queue
ORDER BY date, queue;
```

**Line by line**

| Line | What it means |
|---|---|
| `SUM(offered)`, `SUM(answered)`, `SUM(abandoned)`, `SUM(answered_within_20s)` | Add up each count over the 24 half-hours of the day, per queue (the `GROUP BY` buckets, as in Query 1). |
| `SUM(aht_seconds * answered)` | **Total handle seconds**: each interval's average × its contacts, added up (the numerator of the weighted AHT in Query 2). |
| `SUM(ABS(offered - forecast_offered))` | Total size of the forecast misses in contacts (Query 5's WAPE numerator). |
| `WHERE offered > 0` | Skip intervals with no contacts, as in Query 5. They add 0 to every other column, so only the forecast error is affected. |
| `GROUP BY date, queue` | One row per day per queue: 48 × 3 = 144 rows. |

**Result:** 144 rows. For the whole period the blocks give 102,045 contacts, service level 83.6%, abandon rate 4.5%, AHT about 7:47, forecast error (WAPE) 15.2%. The first row is `2026-08-03, Billing-EN, 701, 681, 20, 606, 363401, 132`.

**Try it yourself:** change `GROUP BY date, queue` to `GROUP BY queue`, then delete the `date,` line in `SELECT` and change the `ORDER BY` to `queue`. You get 3 rows with the *period totals* per queue. Dividing them (for example Support-EN: 2,119 ÷ 50,816 = 4.17% abandon rate) gives the same answer the dashboard shows when you leave the full date range.

---

### D2 — Forecast and actual volume per day

**File:** `sql/dashboard/02_forecast_vs_actual_daily.sql` · **Feeds:** the line chart
**Business question:** How did forecast and actual contact volume compare, day by day?

```sql
SELECT
    date,
    queue,
    SUM(forecast_offered) AS forecast_offered,
    SUM(offered)          AS offered
FROM intervals
GROUP BY date, queue
ORDER BY date, queue;
```

The same pattern as Query 1, with the forecast added beside the actual volume: `SUM(...)` per `GROUP BY date, queue` bucket. 144 rows. The chart draws one line for each column. When "All queues" is selected, the page adds the three queues of each day.

---

### D3 — Service level building blocks per weekday and hour

**File:** `sql/dashboard/03_service_level_heatmap.sql` · **Feeds:** the heatmap
**Business question:** Which weekdays and hours of the day miss the 80/20 service level?

```sql
SELECT
    date,
    CAST(strftime('%w', date) AS INTEGER)       AS weekday,
    queue,
    CAST(substr(interval_start, 1, 2) AS INTEGER) AS hour,
    SUM(offered)                                AS offered,
    SUM(answered_within_20s)                    AS answered_within_20s
FROM intervals
GROUP BY date, queue, hour
ORDER BY date, queue, hour;
```

**Line by line**

| Line | What it means |
|---|---|
| `strftime('%w', date)` | `strftime` formats a date. `'%w'` returns the weekday as a number, **0 = Sunday**, 1 = Monday ... 6 = Saturday. Our data has no Sundays, so we see 1 to 6. It comes back as text, so `CAST(... AS INTEGER)` turns it into a number. |
| `substr(interval_start, 1, 2)` | `substr(text, start, length)` cuts out a piece of text: the first 2 characters of `'08:30'` are `'08'`. |
| `CAST(... AS INTEGER) AS hour` | Turns `'08'` into the number 8, so the page can sort and label it. |
| `GROUP BY date, queue, hour` | One bucket per day, queue and hour, which holds that hour's two half-hour intervals. SQLite lets you group by the alias `hour`. `weekday` is not in the `GROUP BY`, but it is calculated from `date`, which is, so every row in a bucket has the same weekday. |
| `SUM(...)` | The two numbers needed for service level: contacts offered, and contacts answered within 20 seconds. |

**Result:** 1,728 rows (48 days × 3 queues × 12 hours). The first: `2026-08-03, weekday 1, Billing-EN, hour 8, offered 25, answered_within_20s 24`.

**How the page uses it:** for a chosen queue and date range, it adds the rows into 6 × 12 cells (weekday × hour) and divides inside each cell: `answered_within_20s ÷ offered`. Cells under 80% are the weak spots.

**Try it yourself:** add `WHERE queue = 'Support-DE'` on its own line after `FROM intervals`. You get 576 rows (48 × 12), one queue only.

---

### D4 — Staffing building blocks per hour

**File:** `sql/dashboard/04_staffing_gap_hourly.sql` · **Feeds:** the staffing chart and KPI card 6
**Business question:** By hour of the day, how many agents were needed compared with scheduled, and how often were we short?

```sql
WITH needed AS (
    SELECT
        date,
        queue,
        CAST(substr(interval_start, 1, 2) AS INTEGER) AS hour,
        scheduled_agents,
        offered * aht_seconds / 1800.0 / 0.85         AS agents_needed
    FROM intervals
)
SELECT
    date,
    queue,
    hour,
    COUNT(*)                                                       AS intervals,
    SUM(scheduled_agents)                                          AS scheduled_agent_intervals,
    ROUND(SUM(agents_needed), 3)                                   AS needed_agent_intervals,
    SUM(CASE WHEN scheduled_agents < agents_needed THEN 1 ELSE 0 END) AS short_intervals
FROM needed
GROUP BY date, queue, hour
ORDER BY date, queue, hour;
```

**Line by line**

| Line | What it means |
|---|---|
| `WITH needed AS (...)` | The named step from Query 7: it calculates `agents_needed` per interval once (workload ÷ 1,800 ÷ 0.85 occupancy; the simplified formula, not Erlang C). |
| `COUNT(*) AS intervals` | How many 30-minute intervals are in the bucket (2 per hour). |
| `SUM(scheduled_agents)` | Scheduled agents added over those intervals. Dividing by `intervals` later gives the *average* agents per interval. |
| `ROUND(SUM(agents_needed), 3)` | Needed agents added the same way, rounded to 3 decimals to keep the exported file small. |
| `SUM(CASE WHEN scheduled_agents < agents_needed THEN 1 ELSE 0 END)` | **A counting trick:** the `CASE` gives 1 for every short interval and 0 for the others, so adding it up *counts* the short intervals. This is `status = 'short'` from Query 7. |

**Result:** 1,728 rows. Across all rows: 730 short intervals out of 3,456, which is 21.1%, the same count as Query 7 (`scripts/verify_queries.py` checks that they agree).

**How the page uses it:** average gap for an hour = (Σ scheduled − Σ needed) ÷ (number of half-hour slots). With several queues selected, the gaps of the queues are added within each half-hour, so "All queues" shows the whole center's gap per half-hour. Red bars (below zero) are hours where the schedule is short.

**Honest limits:** the formula is the same simplification as Query 7 (actual workload, 85% occupancy, no shrinkage, no queueing effects). Erlang C would be the next step.
