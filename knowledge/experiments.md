# Experiments

This file does two things:
1. Defines the experiment taxonomy the agent uses to type every suggestion
2. Tracks the status of all experiments ever suggested or run

The agent reads this before every run. It types every finding and suggestion
against the taxonomy below. When an `--only` filter is active, it only surfaces
experiments of the specified types.

---

## Taxonomy

| Type | What it covers |
|---|---|
| `content` | Product copy, headlines, descriptions, FAQs, button text |
| `pricing` | Price points, compare-at prices, anchoring, bundles, quantity breaks |
| `offer` | Discounts, free shipping thresholds, GWP, urgency, scarcity |
| `ux` | Layout, navigation, interaction, form design, checkout flow, tab structure |
| `visual` | Image style, colour choices, button shape/size, typography, aesthetic A/B tests |
| `value_prop` | USPs, benefit callouts, product-specific info near price, badges |
| `social_proof` | Reviews, ratings, UGC, testimonials, trust badges |
| `merchandising` | Product ordering, cross-sells, upsells, collections, search |
| `marketing_angle` | Positioning, value proposition framing, audience targeting |
| `email` | Capture, popup timing/offer, abandoned cart flows, post-purchase |
| `technical` | Page speed, structured data, lazy loading, Core Web Vitals |

### Type disambiguation
- Moving the ATC button = `ux`. Changing its colour or shape = `visual`.
- Benefit callout near price = `value_prop`. Rewriting the description = `content`.
- Free shipping progress bar = `value_prop`. Changing the threshold itself = `offer`.

---

## PDP zones (for test isolation)

| Zone | What it covers |
|---|---|
| `buybox` | ATC button, price, variant selector, BNPL, express checkout |
| `trust-block` | Reviews widget, trust badges, returns policy snippet |
| `hero-media` | Product images, video |
| `value-prop-bar` | USP block, free shipping bar, benefit callouts |
| `social-proof-block` | UGC, featured reviews, rating overlay |
| `content-tabs` | Description, specs, FAQ tabs |
| `sticky-bar` | Sticky ATC or sticky nav |

---

## How to use the `--only` filter

```bash
uv run python scripts/run_agent.py --weekly --only visual,ux
uv run python scripts/run_agent.py --weekly --only value_prop,social_proof
uv run python scripts/run_agent.py --weekly  # all types, no filter
```

---

## Experiment log

### ID scheme

Format: `{SCOPE}-{NNN}` — e.g. `PDP-001`, `CART-012`, `COL-003`

Scope prefixes:
- `PDP` — product detail page
- `CART` — mini-cart / cart drawer
- `COL` — collection pages
- `HOME` — homepage
- `CHK` — checkout
- `SITE` — site-wide (cross-scope)

IDs are assigned sequentially within each scope. Never reuse an ID, even if dismissed.

### Status labels
- `suggested` — proposed, not yet started
- `active` — currently running
- `winner` — ran, statistically significant improvement
- `loser` — ran, no improvement or negative result
- `inconclusive` — ran, did not reach significance
- `paused` — started but paused
- `dismissed` — decided not to run

### Log

| ID | Scope | Type | Zone | Test mode | Experiment | Hypothesis | ICE | Status | Start | End | Lift | Confidence | Tool | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| — | — | — | — | — | *(add experiments here)* | — | — | — | — | — | — | — | — | — |

### Column reference

- **ID**: Unique experiment identifier (see ID scheme above)
- **Scope**: Which page scope this experiment targets
- **Type**: Experiment type from taxonomy above
- **Zone**: Which zone on the page (see zone map above)
- **Test mode**: `solo` / `concurrent` / `sequential` (see playbook.md)
- **Experiment**: Short description of what's being tested
- **Hypothesis**: Link to hypothesis ID in hypotheses.md (e.g. `H-003`) or brief statement
- **ICE**: Score at time of suggestion (may differ from final impact)
- **Status**: Current status (see labels above)
- **Start**: Date test started (DD-MM-YYYY)
- **End**: Date test concluded (DD-MM-YYYY)
- **Lift**: Observed lift on primary metric (e.g. `+12.3% CVR`, `-2.1% AOV`)
- **Confidence**: Statistical confidence level (e.g. `97%`, `< 90%`)
- **Tool**: Testing tool used (e.g. `AB Convert`, `manual`, `theme toggle`)
- **Notes**: Context, learnings, follow-up actions

### Active zone tracker

Use this to check which zones have active experiments before suggesting new ones.

| Zone | Active experiment | Status | Started |
|---|---|---|---|
| buybox | — | — | — |
| trust-block | — | — | — |
| hero-media | — | — | — |
| value-prop-bar | — | — | — |
| social-proof-block | — | — | — |
| content-tabs | — | — | — |
| sticky-bar | — | — | — |
