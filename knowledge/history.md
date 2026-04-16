# History

Maintained by the agent. Appended after every run. Read before each scan to avoid
repeating actioned findings and to detect regressions. Do not delete entries.

## Entry format

```
## YYYY-MM-DD

### Metrics snapshot
- Conversion rate: X.X% (±X.X% WoW)
- AOV: $XXX (±$XX WoW)
- Cart abandonment: XX% (±X% WoW)
- Sessions: XXXXX (±XX% WoW)

### Top findings
1. [ICE X.X] Finding description — file:line or metric — Status: New / Ongoing / Regression

### Hypothesis updates
- Hypothesis name: Confirmed / Refuted / Insufficient data

### Actioned since last run
- (owner fills this in between runs, or leave blank)
```

## Status labels
- `New` — first time flagged
- `Ongoing` — flagged before, not yet fixed
- `Regression` — was fixed, has returned
- `Actioned` — fix implemented, monitor for impact

---

## Log

<!-- Agent appends entries below. Nothing here yet — fresh install. -->
