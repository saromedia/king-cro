# Brand & Industry Context

Maintained by the store owner. The agent reads this before every run to ground
recommendations in the specific realities of this business — not generic CRO advice.

**If this file still contains placeholder values, the agent must flag it and ask the
owner to populate it before producing industry-specific recommendations.**

---

## Business overview

| Field | Value |
|---|---|
| Brand name | [Your Brand Name] |
| Store URL | [your-store.myshopify.com] |
| Industry / category | [e.g. health supplements, streetwear, pet accessories, home fragrance] |
| Business model | [DTC / wholesale / hybrid / marketplace] |
| Founded | [year] |
| Monthly traffic (approx) | [e.g. 25,000 sessions] |
| Monthly orders (approx) | [e.g. 500] |
| Current CVR (approx) | [e.g. 2.1%] |
| AOV range | [e.g. $45-65] |
| SKU count | [e.g. 35 active products] |
| Primary platform | [Shopify / Shopify Plus] |

## What you sell

[Describe the product range in 2-3 sentences. What category? Physical / digital?
Single product vs many? Is there a hero product that drives most revenue?]

Example: "We sell premium plant-based protein powders and supplements. 80% of revenue
comes from our flagship 1kg protein tub. We have 12 SKUs across 3 product lines."

## Target customer

| Field | Value |
|---|---|
| Primary demographic | [e.g. health-conscious millennials, 25-40] |
| Age range | [e.g. 25-40] |
| Gender skew | [e.g. 60% female, 40% male] |
| Geographic focus | [e.g. Australia + NZ, expanding to US] |
| Income level | [e.g. mid-to-high disposable income] |
| Buying motivation | [impulse / considered / habitual / gift] |
| Purchase frequency | [one-time / occasional / subscription / repeat] |
| Average research time | [minutes / hours / days / weeks] |

### Customer psychographics

[What do they care about? What are they comparing you against?
What's the "job to be done" your product fulfils?]

Example: "Our customers care about clean ingredients and transparent sourcing. They
compare us against [Competitor A] and [Competitor B]. The job-to-be-done is 'feel
confident I'm putting something healthy in my body without sacrificing taste.'"

## Competitive landscape

| Competitor | What they do well | Where you beat them |
|---|---|---|
| [Competitor 1] | [e.g. strong brand recognition, large social following] | [e.g. better ingredient quality, more transparent labelling] |
| [Competitor 2] | [e.g. lower prices, faster shipping] | [e.g. premium positioning, better product reviews] |
| [Competitor 3] | [e.g. wider product range] | [e.g. deeper expertise in our niche, stronger community] |

## Price positioning

| Field | Value |
|---|---|
| Price range | [e.g. $29-89 per product] |
| Position | [budget / mid-range / premium / luxury] |
| Price sensitivity | [low / medium / high] |
| Discount strategy | [never / rare / seasonal / frequent / always-on] |
| BNPL relevance | [low / medium / high — depends on AOV and demographic] |
| Free shipping threshold | [e.g. $75 / n/a] |

## Known friction points

[What do you already know hurts conversion? Customer complaints,
support tickets, heatmap observations, session recordings, past test results.
Be honest — this is the most valuable section.]

1. [e.g. "Mobile users drop off at the product page — ATC button is below the fold"]
2. [e.g. "Customers email asking about ingredients that are already on the page — they can't find them"]
3. [e.g. "High cart abandonment — we think shipping cost surprise is the cause"]

## Brand voice and positioning

| Field | Value |
|---|---|
| Tone | [e.g. friendly and expert, not salesy / luxury and minimal / playful and bold] |
| Messaging pillars | [e.g. transparency, quality, community] |
| Key differentiator (1 sentence) | [e.g. "The only protein powder with 100% traceable ingredients and a 90-day taste guarantee"] |

## Seasonality and key dates

| Period | Impact | Notes |
|---|---|---|
| [e.g. Jan — New Year resolutions] | [high traffic, high CVR] | [Don't run disruptive tests during peak] |
| [e.g. Nov — Black Friday / Cyber Monday] | [highest revenue month] | [Pause experiments 2 weeks before, run offer tests only] |
| [e.g. Jun-Aug — winter in AU] | [lower traffic] | [Good time for longer-running tests] |

## Past experiment learnings

[What have you tested before (on any platform)? What won, what lost?
This is critical — it prevents re-running losing tests and builds on winners.]

| What was tested | Result | Lift / drop | Notes |
|---|---|---|---|
| [e.g. Added trust badges below ATC button] | [winner] | [+8% CVR] | [Social proof near purchase point works for us] |
| [e.g. Changed ATC button from green to orange] | [loser] | [-3% CVR] | [Don't test button colours again — diminishing returns] |
| [e.g. Added free shipping threshold bar in cart] | [winner] | [+12% AOV] | [Customers respond to progress indicators] |

## A/B testing setup

| Field | Value |
|---|---|
| Testing tool | [e.g. AB Convert] |
| How results are captured | [e.g. CSV export from AB Convert dashboard — one file per test group] |
| Minimum test duration policy | [e.g. 2 weeks minimum, regardless of significance] |
| Significance threshold | [e.g. 95%] |
| Who calls winners | [e.g. Head of CRO reviews results and makes the call] |
| Current experiment capacity | [e.g. 2-3 concurrent tests in independent zones] |

## What the agent should know

[Anything else that would change how recommendations are made.]

Examples:
- "We're rebranding in Q3 — don't suggest visual changes until after launch"
- "We've tried popups 3 times and the founder vetoes them every time"
- "We're migrating to Shopify Plus in 2 months — checkout experiments can wait"
- "Our developer is part-time, so prefer low-effort experiments (toggles, copy changes)"

---

## How this file is used

The CRO agent reads this file before every run. It uses the information to:

1. **Filter recommendations** — don't suggest BNPL experiments if BNPL relevance is low
2. **Calibrate ICE scores** — a "premium" brand gets different impact estimates than "budget"
3. **Avoid repeat failures** — past experiment learnings prevent re-testing known losers
4. **Match brand voice** — content suggestions align with tone
5. **Respect seasonality** — don't suggest disruptive changes during peak periods
6. **Set realistic benchmarks** — compare against industry, not generic Shopify averages
7. **Understand customer journey** — "considered purchase" products need different CRO than impulse buys
