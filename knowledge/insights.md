# Strategic Insights

Maintained by the agent. Updated after every run with type-level pattern analysis.
The agent reads this before each run to inform the Strategy pulse section of the report.

Purpose: surface which experiment types are generating the most wins, which are
underrepresented relative to their win rate, and challenge the owner with strategic
questions about where to focus next.

---

## How the agent updates this file

After each run, the agent:
1. Re-reads the full experiments.md log
2. Calculates win rate per type (winners / (winners + losers), ignoring suggested/active)
3. Compares representation in backlog vs win rate
4. Identifies types that are high-win but low-volume in the backlog ("underutilised")
5. Identifies types that are high-volume in the backlog but low-win ("over-indexed")
6. Appends a dated entry below

---

## Win rate table (agent updates this)

| Type | Suggested | Active | Winners | Losers | Win rate | Signal |
|---|---|---|---|---|---|---|
| *(agent populates after first experiments complete)* | | | | | | |

---

## Strategic observations (agent appends entries)

### Format

```
## DD-MM-YYYY

### Win rate snapshot
[table of current win rates]

### Pattern observations
- [observation with supporting data]

### Underutilised strategies
- [type]: win rate X% but only Y experiments in backlog vs Z winners

### Strategic nudges for owner
- [challenge question based on data]
```

---

## Log

<!-- Agent appends entries below after each run. Nothing here yet — fresh install. -->
