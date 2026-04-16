# Hypotheses

Maintained by the store owner. The agent reads this before every run and treats each
item as an investigation priority. Add hunches freely — the agent will confirm or refute.

## Status labels
- `[ ]` not yet investigated
- `[~]` under investigation — seen but inconclusive
- `[✓]` confirmed — experiment validated this
- `[✗]` refuted — experiment disproved this

## ID scheme
Format: `H-{NNN}` — e.g. `H-001`, `H-002`. Assigned sequentially. Never reuse.

## How to add a hypothesis

Each hypothesis must include:
- **ID** (H-NNN)
- **Scope** tag (pdp, mini-cart, collection, homepage, checkout, site-wide)
- **Statement** — what you think is happening
- **Why** — observation, customer feedback, data signal, gut feel
- **Where to look** — which files, metrics, or data the agent should check
- **Added** — date added (DD-MM-YYYY)
- **Experiments** — IDs of experiments that tested this (auto-updated by agent)

Example:
```
- [ ] **H-001** [pdp] Add-to-cart button not prominent enough on mobile
  Why: Mobile sessions are 65% of traffic but mobile CVR is 40% below desktop.
  Look at: Product template — button size, position, contrast. Mobile CVR split in API.
  Added: 16-04-2026
  Experiments: PDP-003 (active)
```

## Escalation rules
The agent monitors hypothesis age and flags stale items:
- **> 2 weeks uninvestigated** `[ ]`: "This hypothesis has been sitting for N weeks — should the agent investigate it this run?"
- **> 4 weeks under investigation** `[~]`: "This hypothesis has been inconclusive for N weeks — design an experiment to test it directly, or dismiss it."
- **Confirmed but no experiment**: "This was confirmed by data but no experiment has been suggested to act on it."

---

## Active

<!-- Add your hypotheses below. Use the format above. -->

---

## Backlog

<!-- Ideas not yet formalised into full hypotheses — dump them here.
     When you're ready to promote one, move it to Active with a full entry. -->
