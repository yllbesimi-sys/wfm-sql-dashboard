-- Question: In each 30-minute interval, how many agents were needed compared with how many were scheduled?
--
-- Why a WFM analyst cares: this is the core capacity-planning view. It shows exactly WHEN
-- the schedule was too thin (negative gap) or too generous (positive gap).
--
-- Table used:   intervals
-- Columns used: date, interval_start, queue, offered, aht_seconds, scheduled_agents
-- Result:       one row per interval per queue (3,456 rows)
--
-- SIMPLIFIED staffing formula (deliberately simple, NOT Erlang C):
--   workload (agent-intervals) = offered contacts x AHT seconds / 1,800 seconds in an interval
--   agents needed              = workload / occupancy target (0.85)
--   gap                        = scheduled agents - agents needed   (negative = short-staffed)
-- Occupancy target 0.85 = we plan for agents to be busy 85% of their logged-in time.
-- Limits: uses ACTUAL contacts and AHT (what really happened, in hindsight); no shrinkage
-- (breaks, meetings); ignores queueing effects and the service-level target. Erlang C is the
-- industry-standard next step because it adds those. Needed agents stay fractional on purpose.
-- The status flag compares the unrounded numbers.

WITH needed AS (
    SELECT
        date,
        interval_start,
        queue,
        offered,
        aht_seconds,
        scheduled_agents,
        offered * aht_seconds / 1800.0 / 0.85 AS agents_needed
    FROM intervals
)
SELECT
    date,
    interval_start,
    queue,
    offered,
    aht_seconds,
    scheduled_agents,
    ROUND(agents_needed, 1)                    AS agents_needed,
    ROUND(scheduled_agents - agents_needed, 1) AS staffing_gap,
    CASE WHEN scheduled_agents < agents_needed THEN 'short' ELSE 'ok' END AS status
FROM needed
ORDER BY date, interval_start, queue;
