-- Question: Which weekdays and hours of the day miss the 80/20 service level?
--
-- Feeds: dashboard heatmap "Service level by weekday and hour".
--
-- Why a WFM analyst cares: a heatmap shows the recurring weak spots (for example Monday
-- 10:00) at a glance, which is exactly where shift patterns and breaks should be adjusted.
--
-- Table used:   intervals
-- Columns used: date, queue, interval_start, offered, answered_within_20s
-- Result:       one row per day per queue per hour (48 x 3 x 12 = 1,728 rows).
--
-- The page adds up the rows that match the chosen queue and date range, grouped by weekday and
-- hour, then divides: service level = answered_within_20s / offered (as in query 03).
-- weekday: 1 = Monday ... 6 = Saturday (strftime '%w' gives 0 for Sunday, which never occurs).
-- hour:    the hour the 30-minute interval starts in (8 = 08:00-08:59, ... 19 = 19:00-19:59).

SELECT
    date,
    CAST(strftime('%w', date) AS INTEGER)       AS weekday,
    queue,
    CAST(substr(interval_start, 1, 2) AS INTEGER) AS hour,
    SUM(offered)                                AS offered,
    SUM(answered_within_20s)                    AS answered_within_20s
FROM intervals
GROUP BY date, queue, hour
ORDER BY date, queue, hour;
