-- Question: What are the building blocks of the headline KPIs, per day and queue?
--
-- Feeds: the dashboard's service-level hero and its Offered contacts, Abandon rate, Average handle
-- time and Forecast error tiles.
--
-- Why this shape: the dashboard lets you pick any queue and any date range, with no server.
-- So this query exports one row per day per queue holding the numerators and denominators.
-- The page adds up the rows you selected and divides ONCE (add up first, divide once, as in
-- queries 04, 05 and 08). The definitions are:
--   Service level  = answered_within_20s / offered        (as in query 03)
--   Abandon rate   = abandoned / offered                  (as in query 04)
--   AHT (seconds)  = handle_seconds / answered            (weighted, as in query 02)
--   Forecast error = abs_forecast_error / offered         (WAPE, as in query 05)
--
-- Table used:   intervals
-- Result:       one row per day per queue (48 days x 3 queues = 144 rows)
--
-- WHERE offered > 0: intervals with no contacts are left out of the forecast error (same rule
-- as query 05). They add 0 to every other column, so nothing else changes.

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
