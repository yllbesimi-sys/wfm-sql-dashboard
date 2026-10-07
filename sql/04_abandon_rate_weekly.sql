-- Question: What share of contacts hang up before being answered, per queue per week?
--
-- Why a WFM analyst cares: abandons are the customer-visible cost of under-staffing.
-- A weekly view shows whether things are getting better or worse over time.
--
-- Table used:   intervals
-- Columns used: date, queue, offered, abandoned
-- Result:       one row per week per queue (8 weeks x 3 queues = 24 rows)
--
-- Definition choice: abandon rate % = SUM(abandoned) / SUM(offered) x 100.
-- We add up first and divide once. Averaging the 48 interval percentages per week would
-- be wrong: a quiet interval with 1 abandon out of 5 would weigh as much as a busy one.
-- Weeks run Monday to Sunday (our data stops on Saturday) and are labelled by their Monday.
-- Simplification: the data has no wait times, so very short abandons cannot be excluded
-- (some centers ignore abandons in the first few seconds).

SELECT
    date(date, '-6 days', 'weekday 1') AS week_start,
    queue,
    SUM(offered)                       AS offered,
    SUM(abandoned)                     AS abandoned,
    ROUND(100.0 * SUM(abandoned) / SUM(offered), 2) AS abandon_rate_pct
FROM intervals
GROUP BY week_start, queue
ORDER BY week_start, queue;
