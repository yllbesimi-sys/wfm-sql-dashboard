# Interview notes

Ten likely questions, with short answers to say **in your own words**. The facts come from this project, so you can back each one up. Change the wording until it sounds like you, and delete any sentence that isn't true for you.

## Ten likely questions

**1. Tell me about this project.**
I'm a workforce management analyst and I'm learning SQL, so I built a dashboard for a made-up contact center: three queues and eight weeks of half-hourly data. Eight SQL queries answer the questions I'd normally ask every week, like service level, abandons, forecast accuracy and the staffing gap. A web page shows the results, with the SQL next to every chart. The data is synthetic, and I built it with an AI assistant.

**2. How much did you do yourself, and how much did the AI do?**
The AI wrote most of the code. I chose the problem and the WFM rules, set the working rules (plan first, explain every query, keep the logic in SQL, be honest), approved every plan, and made the calls, like rebuilding the staffing from real shifts. I ran the queries and quizzed myself on them. I can explain what the queries do; I'm still learning to write them from scratch.

**3. The data is fake. Why should I trust anything it shows?**
You shouldn't trust the numbers as facts, and the README says so. What the project shows is the method: the same queries would run on real data with the same columns. I checked that by recalculating every result separately in plain Python (14 checks), and I tested the checks by deliberately breaking a query to see them fail. The fake data is simple: curves plus noise, so it can't prove the method works on real data.

**4. Why is AHT weighted, and why do you "add up, then divide" for rates?**
Averaging averages treats a quiet half-hour like a busy one. Weighting by contacts fixes that. Example: 10 calls at 300 seconds and 90 calls at 500 seconds average 480, not 400. The same logic applies to percentages: 1 abandon out of 5 and 4 out of 100 is 5 out of 105, 4.8%, not the average of 20% and 4%.

**5. How do you define service level, and why?**
Calls answered within 20 seconds divided by calls *offered*, so people who hang up count against us. Dividing by answered calls looks better but hides the abandons. The 80/20 target is just a number in the query, so it's easy to change. I wrote the choice in the SQL comment so nobody has to guess.

**6. What is the difference between `GROUP BY` and a window function?**
`GROUP BY` squashes many rows into one per group. A window function keeps every row and adds a column worked out from other rows. I used `LAG` for week-over-week change: it brings last week's volume onto this week's row. `PARTITION BY queue` makes it restart for each queue. Without it, one queue's week gets compared with another queue's, and the numbers look plausible but are wrong.

**7. What is the difference between `WHERE` and `HAVING`?**
`WHERE` filters rows before they are grouped. `HAVING` filters the groups after the totals are worked out, for example "only queues with more than 1,000 contacts". In this project I only needed `WHERE`, for example to skip intervals with no contacts when measuring forecast error, so `HAVING` is something I understand but haven't used here.

**8. What is the difference between `INNER JOIN` and `LEFT JOIN`, and what did your join do?**
An `INNER JOIN` keeps only rows that have a match in both tables. A `LEFT JOIN` keeps every row from the left table and fills the gaps with `NULL`. In query 8, I joined the adherence table to the agents table to get each agent's team. I used a plain join because every agent exists in both tables. If some agents had no adherence rows and I wanted to see them, I'd use a `LEFT JOIN`.

**9. How did you handle `NULL` and division by zero?**
Three intervals had no contacts, so their service level can't be worked out. I left it `NULL`, meaning "unknown", rather than 0, because 0 would claim they failed. `NULLIF(offered, 0)` makes that explicit. The AI first told me it prevents a crash. When I was quizzed on it, that turned out to be wrong for SQLite, which returns `NULL` anyway, though other databases do raise an error. The docs were corrected.

**10. How does your staffing formula work, and what is wrong with it?**
Workload is contacts times handle time. Divide by the seconds in a half-hour to get agents kept fully busy, then divide by 85% occupancy to get agents needed. Gap is scheduled minus needed. It's simple on purpose. It ignores queueing and the service-level target, which Erlang C handles, and it has no shrinkage. It is also partly circular, because the fake data was built with the same idea. Erlang C would be my next step.

## Three things to be ready to admit you are still learning

1. **Writing SQL from a blank page.** You can read and explain the eight queries, including `LAG`, the `WITH` steps and the join, but writing something new without help is still hard. Say what you do about it: you change the queries, break them on purpose and run them again.
2. **Erlang C and proper staffing maths.** You know the simple formula and why it falls short, but you can't yet do the Erlang C calculation, or explain how it responds to the service-level target.
3. **The programming around the SQL.** The Python, JavaScript and deployment were written by the AI. You understand what each part is for, but you couldn't build or debug them alone yet.

If an interviewer asks about any of these, a good answer is short and calm: "That's still a learning area for me. Here's what I do understand, and here's how I'd close the gap."

## Numbers worth remembering

| Fact | Value |
|---|---|
| Data | 3 queues, 8 weeks, 3,456 half-hour intervals, 69 agents |
| Contacts offered | 102,045 |
| Service level (80/20) | 83.6% overall |
| Abandon rate | 4.5% |
| Short-staffed half-hours | 730 of 3,456 (21%) |
| Forecast error (MAPE) | 15.9% (Support-EN), 21.5% (Billing-EN), 25.3% (Support-DE) |
