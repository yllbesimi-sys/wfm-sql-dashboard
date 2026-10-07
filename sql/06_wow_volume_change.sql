-- Question: How did each queue's weekly volume change compared with the week before?
--
-- Why a WFM analyst cares: week-over-week change shows growth, seasonality and one-off
-- events, and tells you whether last week is a fair guide for next week's forecast.
--
-- Table used:   intervals
-- Columns used: date, queue, offered
-- Result:       one row per week per queue (8 weeks x 3 queues = 24 rows).
--               The first week of each queue has no previous week, so its change is NULL.
--
-- How it works, in two named steps (WITH ... AS):
--   weekly        -> total offered contacts per queue per week (same Monday-labelled weeks as query 04)
--   with_previous -> adds LAG(): the previous week's total of the SAME queue, on the same row
-- All 8 weeks are full Monday-Saturday weeks, so the comparison is fair.

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
