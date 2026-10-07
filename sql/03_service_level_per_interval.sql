-- Question: What service level did each 30-minute interval achieve, and did it hit the 80/20 target?
--
-- Why a WFM analyst cares: service level is the main quality target. Looking at it
-- per interval shows WHEN the queue is under-staffed, not just that it was on average.
--
-- Table used:   intervals
-- Columns used: date, interval_start, queue, offered, answered_within_20s
-- Result:       one row per interval per queue (48 days x 24 intervals x 3 queues = 3,456 rows)
--
-- Definition choice: service level % = answered_within_20s / offered x 100.
-- We divide by OFFERED (everyone who called), so contacts who gave up count against us.
-- Dividing by answered instead would look better but hides the abandons.
-- Target "80/20": 80% of contacts answered within 20 seconds.
-- 3 intervals have zero contacts: their service level is undefined, so it is left empty (NULL)
-- instead of crashing with a division by zero.

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
