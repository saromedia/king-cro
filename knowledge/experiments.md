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

### Status labels
- `suggested` — proposed, not yet started
- `active` — currently running
- `winner` — ran, improved CVR or AOV
- `loser` — ran, did not improve
- `paused` — started but paused
- `dismissed` — decided not to run

### Log

| ID | Scope | Type | Zone | Test mode | Experiment | ICE | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| — | — | — | — | — | *(add your experiments here)* | — | — | — |
