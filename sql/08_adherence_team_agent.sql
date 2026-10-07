-- Question: How well did each team, and each agent, stick to their schedule (adherence)?
--
-- Why a WFM analyst cares: low adherence means the agents you scheduled were not really
-- there, so the schedule delivers less capacity than planned. Team level shows patterns,
-- agent level shows who needs a conversation.
--
-- Tables used:  adherence (minutes per agent per day) + agents (which team/queue an agent is in)
-- Columns used: adherence.agent_id, scheduled_minutes, adherent_minutes; agents.agent_id, team, queue
-- Result:       4 'team' rows first, then 69 'agent' rows (73 rows). The 'level' column says which.
--               Team rows have no agent_id (NULL).
--
-- Definition: adherence % = SUM(adherent_minutes) / SUM(scheduled_minutes) x 100.
-- Add up first, divide once: a 7-hour day should not weigh the same as an 8-hour day,
-- and long shifts should count for more than short ones.

SELECT
    'team'                    AS level,
    a.team,
    NULL                      AS agent_id,
    a.queue,
    COUNT(*)                  AS shifts_worked,
    SUM(h.scheduled_minutes)  AS scheduled_minutes,
    SUM(h.adherent_minutes)   AS adherent_minutes,
    ROUND(100.0 * SUM(h.adherent_minutes) / SUM(h.scheduled_minutes), 1) AS adherence_pct
FROM adherence AS h
JOIN agents    AS a ON a.agent_id = h.agent_id
GROUP BY a.team, a.queue

UNION ALL

SELECT
    'agent',
    a.team,
    h.agent_id,
    a.queue,
    COUNT(*),
    SUM(h.scheduled_minutes),
    SUM(h.adherent_minutes),
    ROUND(100.0 * SUM(h.adherent_minutes) / SUM(h.scheduled_minutes), 1)
FROM adherence AS h
JOIN agents    AS a ON a.agent_id = h.agent_id
GROUP BY a.team, a.queue, h.agent_id

ORDER BY level DESC, team, agent_id;
