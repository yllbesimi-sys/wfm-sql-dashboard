-- Question: By hour of the day, how many agents were needed compared with scheduled, and how often were we short?
--
-- Feeds: dashboard bar chart "Staffing gap by hour" and KPI card 6 "Short-staffed intervals".
--
-- Why a WFM analyst cares: shows WHICH hours are structurally thin or generous, which is what
-- shift start times and lunch placement can fix.
--
-- Table used:   intervals
-- Columns used: date, queue, interval_start, offered, aht_seconds, scheduled_agents
-- Result:       one row per day per queue per hour (1,728 rows).
--
-- SIMPLIFIED staffing formula, the same as query 07 (NOT Erlang C):
--   agents needed = offered x AHT seconds / 1,800 seconds in an interval / 0.85 occupancy target
-- Limits: uses actual contacts and AHT, ignores queueing effects and the service-level target,
-- and has no shrinkage (breaks, meetings). Erlang C is the industry-standard next step.
--
-- The formula appears once, in the WITH step below. Each hour holds two 30-minute intervals.
-- The page adds up the selected rows: average gap = (scheduled - needed) / number of intervals.
-- short_intervals counts the 30-minute intervals where scheduled < needed (as 'short' in query 07).

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
