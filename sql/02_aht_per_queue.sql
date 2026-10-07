-- Question: What is the average handle time (AHT) of each queue?
--
-- Why a WFM analyst cares: AHT drives workload (contacts x AHT = work to staff for),
-- so a small error in AHT becomes a staffing error.
--
-- Table used:   intervals
-- Columns used: queue, aht_seconds, answered
-- Result:       one row per queue (3 rows)
--
-- Definition choice: the headline number is the WEIGHTED average. Every interval
-- already holds an average (aht_seconds), so we weight each one by the number of
-- contacts it covers (answered). A busy interval with 80 calls then counts more
-- than a quiet one with 8. The plain average of the interval averages is shown
-- next to it for comparison.

SELECT
    queue,
    ROUND(1.0 * SUM(aht_seconds * answered) / SUM(answered), 1) AS aht_weighted_sec,
    ROUND(AVG(aht_seconds), 1)                                  AS aht_simple_avg_sec,
    SUM(answered)                                               AS answered_contacts
FROM intervals
GROUP BY queue
ORDER BY queue;
