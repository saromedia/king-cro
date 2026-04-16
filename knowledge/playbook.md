# CRO Playbook

Each section covers one scope. The agent reads only the section matching the active
scope. To activate a new scope, populate its section and update CLAUDE.md.

Active scope: **pdp**

---

## Scope: pdp — Product Detail Page

### Metrics to pull

| Metric | Notes |
|---|---|
| Sessions | Total + device split. Flag mobile/desktop CVR gap > 30%. |
| Conversion rate | Orders / sessions. Flag if below 1.5%. |
| AOV | Week-over-week delta. |
| Cart abandonment rate | Flag if above 70%. |
| Refund rate | Flag week-over-week spikes. |
| Repeat customer rate | Flag if below 20%. |
| Discount code usage | High rate signals price resistance. |

Product-level signals:
- Descriptions under 80 words
- Fewer than 3 images
- Out-of-stock variants with no redirect or alternative
- Products with high views and low add-to-cart (if analytics available)

### Theme files to check

Target these files (adapt names to actual theme):
- `sections/main-product.liquid` or `sections/product-template.liquid`
- `snippets/product-form.liquid`
- `snippets/product-price.liquid`
- `snippets/product-media.liquid`
- Any file with `product` in the name under `sections/` or `snippets/`

### Checklist

**Buybox (above fold)**
- [ ] ATC button above fold on mobile? Distinct colour? Has loading/spinner state?
- [ ] Price clearly displayed? Compare-at price crossed out when on sale?
- [ ] Variant selector usable? Out-of-stock variants visually disabled?
- [ ] BNPL / Afterpay messaging visible near price?
- [ ] Express checkout / dynamic checkout button present?
- [ ] Key value indicator near price (e.g. cost-per-unit, quantity info, badge)?

**Trust and social proof**
- [ ] Star rating and review count near product title?
- [ ] Reviews widget rendered and loading?
- [ ] Returns policy visible above the fold (not just footer)?
- [ ] Secure checkout badge present?
- [ ] UGC or credibility content block present?
- [ ] `application/ld+json` product schema with `aggregateRating` in `<head>`?

**Value proposition**
- [ ] USP block visible above fold or immediately below buybox?
- [ ] Free shipping indicator present?
- [ ] Key product benefits called out visually (not just in description text)?
- [ ] FAQ or objection-handling block in or near buybox?

**Product content**
- [ ] Description: minimum 80 words after HTML strip?
- [ ] Images: at least 3? (hero, lifestyle, detail/scale)
- [ ] Lazy loading on all `img` tags (`loading="lazy"`)?
- [ ] Alt tags on all product images?

**Page structure**
- [ ] Quick-nav for long PDPs?
- [ ] Collapsible tabs for secondary content?
- [ ] Sticky ATC or sticky nav bar on scroll?

**Performance**
- [ ] No render-blocking `<script>` in `<head>` without `defer`/`async`?
- [ ] Large images using responsive `srcset`?

---

### Testing methodology — A/B vs multivariate

The agent uses this framework when suggesting how to run each experiment.

#### Decision rule: same zone = sequential, different zone = can be concurrent

Every experiment is assigned a zone — the part of the page it primarily affects.
Two experiments in the same zone have interaction effects: you cannot attribute a
result to one change if two things changed simultaneously in that area.

#### Concurrent test rules

| Scenario | Rule | Reason |
|---|---|---|
| Two changes in the same zone | Sequential (A/B each) | Interaction effects corrupt attribution |
| Changes in different zones | Concurrent (MVT) fine | Independent — no interaction |
| Different psychological mechanisms, different zones | Concurrent fine | e.g. offer copy + image style |
| One test depends on the other winning first | Sequential, gate on result | e.g. test copy only after layout wins |

#### Traffic and significance thresholds

- Target minimum detectable effect: ~10% relative CVR lift (e.g. 2.0% → 2.2%)
- Required sample per variant: ~4,000 sessions for 80% power at p < 0.05
- MVT with N variants: multiply by N — a 3-way MVT needs ~12,000 sessions total
- Sessions < 2,000/week: A/B only, no MVT
- Sessions 2,000–8,000/week: A/B or 2-way MVT when zones are clearly independent
- Sessions > 8,000/week: MVT with up to 4 variants is viable

The agent checks session volume and flags underpowered MVT proposals.

---

### ICE scoring guide

| Score | Impact | Confidence | Ease |
|---|---|---|---|
| 9–10 | Could move CVR > 0.5% | Direct data evidence | Under 1 hour |
| 7–8 | Likely meaningful lift | Strong circumstantial | Half a day |
| 5–6 | Moderate potential | Plausible, unconfirmed | 1–2 days |
| 3–4 | Small or niche | Hypothesis only | Requires dev |
| 1–2 | Marginal | Speculation | Complex or risky |

---

### Benchmarks

| Metric | Target | Notes |
|---|---|---|
| Conversion rate | > 2.0% | Shopify avg ~1.5% |
| Cart abandonment | < 65% | Baymard avg ~70% |
| Repeat customer rate | > 25% | Healthy DTC benchmark |
| Mobile CVR vs desktop | Within 20% gap | |

*Update benchmarks as your store matures and you establish your own baselines.*

---

## Scope: mini-cart — Cart Drawer / Mini-Cart

**Status: STUB — not yet active**

To activate: populate the sections below, then run with `--scope mini-cart`

### Metrics to pull
*(populate when activating)*

### Theme files to check
- `sections/cart-drawer.liquid`
- `snippets/cart-items.liquid`
- `snippets/cart-footer.liquid`
*(confirm actual filenames from theme when activating)*

### Checklist
*(populate when activating)*
- [ ] Upsell or cross-sell product recommendation present?
- [ ] Free shipping threshold bar visible and dynamic?
- [ ] Checkout button above fold in the drawer?
- [ ] Trust signals near checkout button?
- [ ] Cart item count and subtotal clearly visible?

---

## Scope: collection — Collection Pages

**Status: STUB — not yet active**

### Theme files to check
- `sections/main-collection.liquid` or `sections/collection-template.liquid`
- `snippets/product-card.liquid`

### Checklist
*(populate when activating)*
- [ ] Faceted filtering enabled?
- [ ] Sort dropdown visible on mobile?
- [ ] Product cards show price, title, image?
- [ ] Pagination or load-more present?
- [ ] Empty state handled?

---

## Scope: homepage — Homepage

**Status: STUB — not yet active**

### Theme files to check
- `sections/hero.liquid` or `sections/slideshow.liquid`
- `sections/featured-collection.liquid`
*(confirm actual filenames when activating)*

### Checklist
*(populate when activating)*

---

## Scope: checkout — Checkout Flow

**Status: STUB — not yet active**

Note: Shopify checkout customisation requires checkout extensibility or Shopify Plus.

### Checklist
*(populate when activating)*
