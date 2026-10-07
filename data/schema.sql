-- Database structure for the fictional contact center.
-- Run by scripts/generate_data.py. Times are stored as text: dates 'YYYY-MM-DD', intervals 'HH:MM'.

CREATE TABLE intervals (
    date                 TEXT    NOT NULL,  -- calendar day
    interval_start       TEXT    NOT NULL,  -- start of the 30-minute interval, e.g. '08:30'
    queue                TEXT    NOT NULL,  -- 'Support-EN', 'Support-DE' or 'Billing-EN'
    forecast_offered     INTEGER NOT NULL,  -- contacts we PLANNED for
    offered              INTEGER NOT NULL,  -- contacts that actually arrived
    answered             INTEGER NOT NULL,  -- contacts an agent picked up
    abandoned            INTEGER NOT NULL,  -- contacts that hung up while waiting (offered = answered + abandoned)
    aht_seconds          INTEGER NOT NULL,  -- average handle time of answered contacts, in seconds
    answered_within_20s  INTEGER NOT NULL,  -- answered contacts picked up within 20 seconds
    scheduled_agents     INTEGER NOT NULL,  -- agents scheduled on this queue in this interval
    PRIMARY KEY (date, interval_start, queue)
);

CREATE TABLE agents (
    agent_id TEXT PRIMARY KEY,              -- fictional ID, e.g. 'AGT-001'
    team     TEXT NOT NULL,                 -- fictional team name
    queue    TEXT NOT NULL                  -- the queue this agent works
);

CREATE TABLE adherence (
    date               TEXT    NOT NULL,
    agent_id           TEXT    NOT NULL REFERENCES agents (agent_id),
    scheduled_minutes  INTEGER NOT NULL,    -- minutes the agent was scheduled to work
    adherent_minutes   INTEGER NOT NULL,    -- minutes the agent was actually in the right state
    PRIMARY KEY (date, agent_id)
);
