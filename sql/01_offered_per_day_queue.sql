-- Question: How many contacts did each queue receive each day?
--
-- Why a WFM analyst cares: daily volume per queue is the starting point for
-- forecasting, for spotting unusual days (spikes), and for comparing weekdays.
--
-- Table used:   intervals
-- Columns used: date, queue, offered
-- Result:       one row per day per queue (48 days x 3 queues = 144 rows)

SELECT
    date,
    queue,
    SUM(offered) AS offered_contacts
FROM intervals
GROUP BY date, queue
ORDER BY date, queue;
