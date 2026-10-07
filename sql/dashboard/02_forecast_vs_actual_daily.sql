-- Question: How did forecast and actual contact volume compare, day by day?
--
-- Feeds: dashboard line chart "Forecast vs actual volume".
--
-- Why a WFM analyst cares: the gap between the two lines is the forecast error you have to
-- absorb with the schedule. Days where actual runs far above forecast are the ones to investigate.
--
-- Table used:   intervals
-- Columns used: date, queue, forecast_offered, offered
-- Result:       one row per day per queue (144 rows). The page adds the rows of the selected
--               queue(s) for each day.

SELECT
    date,
    queue,
    SUM(forecast_offered) AS forecast_offered,
    SUM(offered)          AS offered
FROM intervals
GROUP BY date, queue
ORDER BY date, queue;
