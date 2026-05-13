# SAMPLE — Weekly CRO Report

> **This is an illustrative sample, not a real run.** Numbers, brand, file paths,
> and findings are fabricated to show the shape of what the agent produces. A
> real report would live at `reports/pdp/DD-MM-YYYY.md` and be committed by
> the GitHub Actions workflow.
>
> The structure below matches the contract defined in [CLAUDE.md](../../CLAUDE.md)
> under "Report structure".

---

**Scope:** `pdp` | **Filter:** none | **Brand:** Sample Brand Co. | **Run date:** 13-05-2026 | **Period:** 06-05-2026 → 12-05-2026

---

## Executive summary

Mobile PDP conversion is the headline problem this week. Mobile sessions are 71%
of traffic but mobile CVR (1.42%) sits 46% below desktop (2.64%) — wider than
last week's 38% gap. The ATC button on mobile drops below the fold on viewports
under 390px wide because the gallery is full-height; this is the single change
most likely to close the gap. Review widget lazy-loading is firing after the
fold paint and causing a ~700ms layout shift that suppresses the rating display
during the first scroll. Two thirds of completed `social_proof` experiments
have won, but only one is currently active — strategically under-utilised.

## Metrics snapshot

| Metric | This week | Last week | WoW Δ | Flag |
|---|---|---|---|---|
| Sessions | 24,180 | 23,705 | +2.0% | |
| Sessions — mobile | 17,160 (71%) | 16,710 (70%) | +2.7% | |
| Sessions — desktop | 7,020 (29%) | 6,995 (30%) | +0.4% | |
| Conversion rate | 1.78% | 1.91% | -6.8% | ⚠️ |
| CVR — mobile | 1.42% | 1.54% | -7.8% | ⚠️ |
| CVR — desktop | 2.64% | 2.71% | -2.6% | |
| Mobile vs desktop CVR gap | -46% | -43% | widening | ⚠️ |
| AOV | $64.20 | $63.85 | +0.5% | |
| Cart abandonment rate | 73.4% | 72.1% | +1.3pp | ⚠️ |
| Refund rate | 2.1% | 2.0% | +0.1pp | |
| Repeat customer rate | 18.3% | 19.0% | -0.7pp | ⚠️ |
| Discount code usage | 41% | 38% | +3pp | ⚠️ |

**Flags:** mobile CVR drop, gap widening, cart abandonment above 70% threshold
(playbook benchmark), repeat customer rate below 20% threshold, discount usage
climbing (price resistance signal).

## Findings

| Type | Finding | Location | ICE | Priority |
|---|---|---|---|---|
| `ux` | ATC button below the fold on viewports <390px (iPhone SE / 12 mini) — gallery takes 100vh | `sections/main-product.liquid:84` | 9.3 | P0 |
| `technical` | Review widget script blocks rendering — `<script src="…yotpo…">` in `<head>` without `defer` | `layout/theme.liquid:42` | 8.7 | P0 |
| `social_proof` | Rating + review count not visible above the fold; widget renders after first scroll | `sections/main-product.liquid:112-118` | 8.3 | P1 |
| `value_prop` | No cost-per-serve or quantity callout next to price — buyers compare on $/serve | `snippets/product-price.liquid:21` | 8.0 | P1 [Confidence +1 based on 75% win rate for value_prop] |
| `content` | 6 of 22 SKUs have descriptions under 80 words (playbook threshold) | API audit — see appendix | 7.0 | P2 |
| `ux` | Variant selector renders out-of-stock options as enabled — buyers tap then bounce | `snippets/product-form.liquid:38-46` | 7.7 | P1 |
| `value_prop` | Free shipping threshold ($75) shown only in footer; AOV is $64 — bar should be on PDP | `snippets/product-form.liquid` (not present) | 7.3 | P1 |
| `visual` | ATC button is a flat outline style — competitors use a high-contrast filled CTA | `sections/main-product.liquid:84` | 6.7 | P2 |
| `technical` | Hero image not using `srcset` — desktop downloads the mobile image and vice versa | `sections/main-product.liquid:62` | 6.7 | P2 |
| `social_proof` | `application/ld+json` product schema missing `aggregateRating` — Google may not render stars in SERP | `snippets/product-schema.liquid:14-30` | 6.3 | P2 |
| `merchandising` | No "frequently bought together" or post-ATC upsell — AOV could lift with bundles | site-wide | 6.0 | P3 |
| `email` | Exit popup fires after 5s on every page — abandoning users on PDP get the same offer as homepage browsers | `sections/popup.liquid:24` | 5.7 | P3 |

## Top 5 actions

1. **[ux]** Move ATC button above the fold on viewports under 390px — cap gallery at 70vh on `(max-width: 390px)` — `sections/main-product.liquid:84`
2. **[technical]** Add `defer` to the review widget script and switch the widget itself to render-after-paint — `layout/theme.liquid:42`
3. **[social_proof]** Render a static "★★★★★ 1,240 reviews" line above the fold, with the full widget loading lazily below — `sections/main-product.liquid:112`
4. **[value_prop]** Add cost-per-serve under the price (e.g. "$2.14 per serve") — `snippets/product-price.liquid:21`
5. **[ux]** Disable + visually dim out-of-stock variant options in the selector — `snippets/product-form.liquid:38-46`

## Experiments this week

New suggestions only — not already in `knowledge/experiments.md`.

| ID | Type | Zone | Test mode | Hypothesis | What to change | What to measure | Tool | Effort |
|---|---|---|---|---|---|---|---|---|
| PDP-018 | `ux` | `buybox` | Solo (shares zone with PDP-014) | ATC above-fold on small mobile lifts mobile CVR | Cap gallery at 70vh on viewports <390px | Mobile CVR, mobile ATC click-through | AB Convert | ~2h dev |
| PDP-019 | `social_proof` | `trust-block` | Concurrent OK | Visible rating above fold lifts CVR | Static rating line above fold | CVR, scroll depth, widget impression | AB Convert | ~3h dev |
| PDP-020 | `value_prop` | `value-prop-bar` | Concurrent OK | Cost-per-serve framing reduces price objection | Add `$X.XX per serve` under price | CVR, AOV (control for variant mix) | AB Convert | ~2h dev |
| PDP-021 | `technical` | site-wide | Run alone (perf measurement) | Defer-load review script lifts LCP, indirectly lifts CVR | Add `defer` attribute, lazy-init widget | LCP, CLS, mobile CVR | AB Convert + WebPageTest | ~1h dev |

**Test isolation check:**
- PDP-018 and PDP-019 are in different zones (`buybox` vs `trust-block`) — concurrent MVT is fine.
- PDP-018 shares `buybox` with PDP-014 (currently running) → must wait. Marked **Sequential, run after PDP-014 concludes**.
- Current session volume (24k/wk) supports up to a 2-way MVT — see playbook traffic table. A 4-way MVT would be underpowered; avoid.

## Hypothesis status

From `knowledge/hypotheses.md` — only items tagged `pdp` or `site-wide`:

- `[~]` **H-001** Mobile ATC not prominent enough — **partially supported** by this week's finding. Recommend running PDP-018 to test directly.
- `[✗]` **H-003** Buyers churn because pricing feels high — refuted by PDP-011 result (price reduction did not lift CVR). Discount usage climbing suggests a **value-perception** problem, not a price-point problem. Reframe hypothesis around value_prop, not pricing.
- `[ ]` **H-007** Out-of-stock variants leak conversions — **now supported** by code finding at `product-form.liquid:38`. Promote to active investigation; suggested experiment PDP-022 to be drafted next week.
- `[~]` **H-009** Free shipping threshold creates friction at AOV ≈ $64 — **supported**. AOV ($64) is just below the threshold ($75) — buyers may be abandoning at the $11 gap. Consider testing $65 threshold or a progress bar.

## Strategy pulse

From `knowledge/insights.md` and the `experiments.md` log:

- **`social_proof` win rate: 3/4 (75%)** — highest decided win rate of any type, but only **1 of 8 backlog items** is `social_proof`. This is the most under-weighted category relative to its track record. Confidence on social_proof experiments has been auto-boosted by +1 per the calibration rule in CLAUDE.md.
- **`value_prop` win rate: 3/4 (75%)** — same story, with 2 of 8 backlog items. Confidence boosted +1.
- **`visual` win rate: 1/3 (33%)** — 4 of 8 backlog items are visual. **Recommend pausing the visual backlog** and re-weighting toward `social_proof` and `value_prop`. Visual experiments are over-represented relative to evidence.
- **`pricing` win rate: 0/2 (0%)** — confidence reduced by -1. Two price-point tests have failed. The data points to **value perception**, not price level, as the lever. Stop testing price points; test value framing.
- **Blind spot:** **zero `email` experiments** have been run. Cart abandonment is 73% and rising — capturing abandoners is leverage we have not touched.

**Challenge for the owner this week:** You have run 3 `visual` tests with a 33% win rate and 0 `email` tests despite a 73% cart abandonment rate. Why? If the answer is "I don't have the email tool wired up", that is the highest-ROI infrastructure decision available right now.

## Watch list

Monitor next week:

- Mobile CVR — did this week's drop continue or revert?
- Discount code usage — is the +3pp climb a trend or noise?
- Repeat customer rate — has it fallen below 18%? If so, escalate to a retention review.
- PDP-014 result — if it concludes this week, unblocks PDP-018.

## Out of scope this run

Noted but not actioned — file under the relevant scope for a future run:

- **`mini-cart`:** Cart drawer has no shipping-threshold progress bar. Likely contributing to the $75 threshold friction noted in H-009. File as a `mini-cart` hypothesis.
- **`checkout`:** Discount code field is collapsed by default — but discount usage is climbing. Worth a checkout-scope review to confirm whether buyers are hunting for codes (which suppresses CVR when they leave to search).
- **`homepage`:** Hero image is 1.8MB unoptimised. Affects LCP site-wide, not just PDP. File as a `homepage` performance hypothesis.

---

## Appendix — raw data references

- Shopify Orders API: 06-05-2026 to 12-05-2026, 430 orders, $27,604 revenue
- Shopify Analytics GraphQL: `onlineStoreSessions`, `onlineStoreConversionRate`
- Abandoned checkouts: 1,158 in period
- Theme files analysed: 28 `.liquid` files under `sections/`, `snippets/`, `layout/`
- Products audited: 22 SKUs (6 flagged for thin description)
- Active experiments at run time: PDP-014, PDP-016, PDP-017 (see `experiments.md`)
- Anthropic synthesis: `claude-opus-4-7`, 2 calls, ~18k input tokens
