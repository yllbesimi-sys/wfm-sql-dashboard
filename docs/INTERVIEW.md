# Interview notes

Talking points for this project. Everything here comes from what actually happened while building it, so you can back it up. **Only say what is true for you**: edit the wording until it sounds like you, and if a sentence claims something you did not do, change it.

## 1. The pitch

**30 seconds**

> I'm a workforce management analyst, and I wanted to show I can work with data directly in SQL. So I built a dashboard for a fictional contact center: three queues, eight weeks of half-hourly data that I generated with a seeded script. Every metric, like service level, abandon rate, forecast accuracy and the staffing gap, comes from a plain SQL file, and the dashboard shows the query next to each chart. I built it with an AI assistant, and I can tell you exactly what that meant.

**2 minutes**

> The data is synthetic on purpose: no real employer data. I made it realistic: weekday and time-of-day patterns, a few unforecast spikes, and staffing built from real shifts with lunches, so shortages show up at the peak hour and at closing time instead of at random.
>
> There are eight SQL questions, easiest first: volume, handle time, service level against the 80/20 target, abandons, forecast accuracy, week-over-week change with a window function, a staffing gap, and adherence with a join. Each one is explained line by line in plain language.
>
> Then a static dashboard: KPI tiles, a forecast chart, a service-level heatmap by weekday and hour, and a staffing-gap chart, with filters. The SQL runs at build time and the results are exported, so it deploys with no backend.
>
> I checked everything with an independent Python calculation, 14 checks, and I wrote down every simplification, for example that my staffing formula is not Erlang C.

## 2. How to talk about the AI assistance

Be direct about it. It is in the README, and it is more credible than hiding it.

**What the AI did:** wrote the code, the SQL, the explanations and the documentation.

**What you did** (confirm each one is true for you):
- Defined the problem and the WFM rules: the 80/20 target, what counts as service level and abandon rate, the staffing formula, the queues and the shape of the data.
- Set the working rules in [`CLAUDE.md`](../CLAUDE.md): plan first, explain everything, SQL is the star, fictional data only, be honest.
- Approved every plan before any code was written, and made the calls: for example, when the staffing pattern was flagged as unrealistic you chose to rebuild it from real shifts, and you chose to leave the thin closing hour as it was.
- Ran the queries and tested yourself with quizzes on them.

**How errors were handled** (this is a strength, tell it):
- The AI claimed `NULLIF` protects a query from crashing on division by zero. When you were quizzed on it, it turned out to be wrong for SQLite, which returns `NULL` for `x / 0` anyway; other databases like PostgreSQL raise an error. The comment and docs were corrected and the correction was pushed.
- The first version of the fake data had far too many failing intervals and a noisy forecast; it was re-tuned and the changes were documented.
- An edit once garbled special characters in a document; it was caught before pushing.
- The checker script was tested by deliberately breaking queries to prove it can fail.

**A fair summary:** "I specified, reviewed and verified; the AI wrote most of the code. What I can do is read the SQL, explain every line, and spot when a number is wrong."

## 3. Likely questions, with answer outlines

**1. Why is AHT weighted?** Each interval holds an average. If you average those averages, a quiet interval with 8 calls counts as much as a busy one with 80. Weight each by the contacts it covers. Example: 10 contacts at 300 s and 90 at 500 s: simple average 400 s, true 480 s. Honest detail: in this fake data the two numbers differ by under 1 second, because the generated AHT doesn't depend on volume. In real data the gap can be bigger.

**2. How do you define service level?** Contacts answered within 20 seconds divided by contacts *offered*, so people who hang up count against you. Dividing by answered looks better and hides abandons. The choice is written in the SQL header.

**3. Why "add up first, divide once"?** Averaging percentages lets small intervals shout as loudly as big ones. Example: 1 abandon out of 5 (20%) and 4 out of 100 (4%): averaging the percentages gives 12%, the truth is 5 out of 105 = 4.76%. Same reason team adherence isn't the average of its agents' percentages.

**4. MAPE, WAPE and bias: what is the difference?** MAPE averages the percentage miss of each interval, so tiny intervals weigh a lot. WAPE is total miss over total volume, steadier. Bias keeps the sign and shows whether you tend to over- or under-forecast. Here, bias is near zero but MAPE is 16% to 25%: errors cancel in the total, not per interval. The smallest queue (Support-DE) forecasts worst, because with 10 to 20 contacts per interval, normal randomness is large.

**5. What is the trap with filtering in the forecast query?** If you keep only intervals with actual volume of 20 or more, MAPE improves, but Support-DE's bias jumps to -6.6%, because you selected intervals by the thing you are measuring against. Don't filter on the actual when judging a forecast.

**6. Explain the window function.** `GROUP BY` collapses rows; a window function keeps every row and adds a column calculated from other rows. `LAG(offered)` brings in the previous week's total. `PARTITION BY queue` restarts for each queue; without it, Billing-EN's week 2 gets compared with Support-EN's week 1 and shows a fake -42.7% drop, with no error message. The first week of each queue is `NULL`, because nothing comes before it.

**7. How does the staffing gap work, and what are its limits?** Workload = contacts × AHT; divide by 1,800 seconds per interval to get agents kept fully busy; divide by the 85% occupancy target to get agents needed; gap = scheduled minus needed. Limits, stated up front: no Erlang C (so no queueing effect or service-level target), no shrinkage, uses actual (hindsight) workload, and it is partly circular because the data generator's planner used the same formula. Erlang C is the industry-standard next step.

**8. What does the gap tell you that an average would not?** Summed over all intervals every queue has a surplus, yet 730 of 3,456 intervals (21%) are short-staffed: mainly the 10:00 peak and the last hour. You can't move the lunchtime surplus to cover the 10:00 shortage, so the interval view matters.

**9. How did you handle `NULL` and division by zero?** Three intervals have no contacts, so their service level is undefined and is left `NULL` instead of `0` (zero would be a false claim of failure). `NULLIF(offered, 0)` makes the intent explicit and is portable. (Mention the correction from section 2.)

**10. Why does the dashboard export "building blocks" instead of percentages?** The page has no server, so it can't re-run SQL when you change a filter. So SQL exports counts and sums per day or hour, and the browser adds up the selected rows and divides once. The definitions live in SQL; the JavaScript only adds and divides. The alternative was running SQLite in the browser, which is heavier and was not what was asked for.

**11. How do you know the numbers are right?** Fourteen automatic checks recompute every query from the raw tables in plain Python and compare, reconcile the dashboard totals against the standalone queries (for example 102,045 contacts, 83.6% service level), and check that the exported JSON isn't stale. I also deliberately broke queries to prove the checks can fail, and compared the live page against independent calculations for three different filter combinations.

**12. What are the limits of the data?** It is synthetic: arrivals are noise around a curve, service level comes from a smooth S-curve of agent load rather than a queue simulation, adherence is generated independently of service level, and the results were tuned by hand to look plausible (about 83% service level, 4 to 5% abandons). Nothing here proves the method would work on real data.

**13. What would you do next with real data?** Erlang C staffing instead of the simple formula; model shrinkage (breaks, meetings, absence); intraday re-forecasting; multi-skill agents; real wait times, so very short abandons can be excluded; compare the planner's schedule with an optimiser.

## 4. Numbers worth remembering

| Fact | Value |
|---|---|
| Data | 3 queues, 8 weeks, 3,456 intervals, 69 agents |
| Offered contacts | 102,045 |
| Service level (80/20) | 83.6% overall; 81% of intervals meet it (2,794 of 3,453 with contacts) |
| Abandon rate | 4.5% |
| AHT | 7:47 overall (about 7, 8 and 9 minutes for Support-EN, Support-DE and Billing-EN) |
| Forecast error | WAPE 15.2%; MAPE 15.9% (EN), 21.5% (Billing), 25.3% (DE) |
| Short-staffed intervals | 730 of 3,456 (21%) |
| Weakest heatmap slot (all queues) | Monday 19:00, 22.8% |
| Monday vs Friday service level | about 75% vs 91% |
| Adherence | teams 88.2% to 91.0%; agents 83.8% to 96.4% |

## 5. A two-minute demo path

1. Start on the hero: "83.6%, 3.6 points above target, but averages hide things."
2. Heatmap: "Monday 10:00 is 41% and the last hour is the weakest all week." Hover a cell to show the contacts behind it.
3. Staffing chart: "Same story from the capacity side: short at 10:00 and at closing, surplus at lunch." Open **View as table**.
4. Click **Show the SQL** under the heatmap: "This is the exact query; each line is explained in the docs."
5. Filter to one queue and a two-week range: "Everything re-calculates from the same building blocks."

## 6. Limits to own up to, in one list

- Synthetic data; plausible, not proven on real data.
- Simplified staffing formula, partly circular; not Erlang C; no shrinkage.
- Service level in the data is modelled by a curve, not simulated.
- Short abandons can't be excluded (no wait times).
- Light theme only; touch interaction on phones was not tested.
- Built with AI assistance; you reviewed and verified, the AI wrote most of the code.
