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
| `NULLIF(offered, 0)` | Returns `offered` normally, but returns `NULL` ("unknown") when `offered` is 0. **Why:** dividing by 0 is impossible. Dividing by `NULL` just gives `NULL`, so the query keeps going instead of failing. 3 intervals in our data really have zero contacts (all Support-DE, at 18:00 / 19:00 / 19:30). |
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
