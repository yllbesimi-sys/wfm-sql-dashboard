# SQL learning notes

Plain-language explanations of every query in this project, written as I go. Query explanations start in Milestone 2.

## Basics you need first

**SQL** is a language for asking questions of tables. A **table** is like an Excel sheet: columns (fields) and rows
(records). A **database** is a collection of tables.

**SQLite** is a database that lives in one file (`data/wfm.db`). There is no server and no password; any program
(or the `sqlite3` tool) can open the file and run SQL against it.

### Our three tables

- `intervals` — one row per **queue × day × half-hour**. This is the main table: volume, answered, abandoned, AHT,
  scheduled agents. (Think: your interval report.)
- `agents` — one row per agent (who they are, which team and queue).
- `adherence` — one row per **agent × day**: scheduled minutes vs. minutes in adherence.

### How the table definitions read (from `data/schema.sql`)

```sql
CREATE TABLE intervals (                 -- "make a new table called intervals"
    date           TEXT    NOT NULL,     -- a column called date; TEXT = stored as text; NOT NULL = may not be empty
    offered        INTEGER NOT NULL,     -- INTEGER = a whole number
    ...
    PRIMARY KEY (date, interval_start, queue)   -- these three together identify a row; no duplicates allowed
);
```

The five SQL words you will meet again and again: `SELECT` (which columns), `FROM` (which table),
`WHERE` (filter rows), `GROUP BY` (one result row per group), `ORDER BY` (sort).
Each query explanation below will show them in action.
