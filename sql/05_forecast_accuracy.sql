-- Question: How accurate was the volume forecast, per queue?
--
-- Why a WFM analyst cares: every staffing decision starts from the forecast. If it is
-- off, the schedule is off. Accuracy numbers tell you how much to trust it, and the
-- bias tells you whether you tend to over- or under-forecast.
--
-- Table used:   intervals
-- Columns used: queue, forecast_offered, offered
-- Result:       one row per queue (3 rows)
--
-- Definitions (all measured per 30-minute interval, forecast vs actual "offered"):
--   MAPE  = average of |actual - forecast| / actual, as a percent.
--           Every interval counts equally, so small noisy intervals weigh as much as big ones.
--   WAPE  = total |actual - forecast| / total actual. Busy intervals weigh more; steadier than MAPE.
--   Bias  = (total forecast - total actual) / total actual.
--           Positive = we over-forecast (too many agents planned). Negative = under-forecast.
-- Intervals with zero actual contacts are left out (3 of them): you cannot divide by zero actual.
-- Note: at 30-minute level these errors look large. The same forecast looks much better
-- when measured per day or per week, because the interval errors partly cancel out.

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
