# Cost & Data Transparency

This document explains exactly what data the CRO agent sends to Anthropic's API,
what it does **not** send, and what each weekly run actually costs.

Written for the store owner / decision-maker who reasonably wants to know
"am I paying for Claude to read every order line by line?" — short answer: no.

> Numbers and pricing in this document reflect Anthropic's published rates as
> of 2026-05-13. Verify current pricing at https://www.anthropic.com/pricing
> before quoting figures to a client.

---

## What does NOT reach Claude

The following is fetched, parsed, and aggregated **locally** by Python scripts
in `scripts/`. Only the aggregated numbers ever appear in the prompt.

| Source | What is read | What is sent to Claude |
|---|---|---|
| Shopify Orders API | Individual orders for the period | Aggregated metrics only: total orders, AOV, refund rate, repeat-customer rate, discount usage rate |
| Shopify Customers API | Customer records | Counts only: total customers, repeat customer count |
| Shopify Abandoned Checkouts | Individual abandoned checkout records | One number: abandoned checkout count → cart abandonment rate |
| Shopify Analytics (ShopifyQL) | Sessions + CVR by day, by device | Aggregated totals + a device-gap flag |
| Theme `.liquid` files | Up to ~30 files via grep heuristics in `analyse_theme.py` | A bounded list of findings (file + line + 1-line issue summary). The agent never sees full file contents |
| Product API | Up to N products (configurable) | Counts of products flagged for thin descriptions, missing images, OOS |

**Specifically NOT sent to Claude:**

- Individual order records, line items, prices, or quantities
- Customer email addresses, names, shipping addresses, or any PII
- Payment information
- Raw checkout payloads
- Full theme source files
- Full product descriptions or images

The reason this is true is architectural, not promise-based: the only place
data enters the prompt is [scripts/run_agent.py — build_synthesis_prompt](scripts/run_agent.py).
That function only formats values produced by `score_metric_findings`,
`score_product_findings`, `analyse_theme.analyse`, and `fetch_analytics` — all
of which return aggregates or bounded lists, never raw rows.

---

## What DOES reach Claude

Per weekly run, the prompt contains roughly:

| Section | Typical size | Source |
|---|---|---|
| Instructions (your role, output contract) | ~1.5k tokens | Static text in `build_synthesis_prompt` |
| Knowledge base (`brand.md`, `playbook.md`, `hypotheses.md`, `history.md`, `insights.md`, `experiments.md`, `CLAUDE.md`) | ~6–10k tokens | `knowledge/` files |
| This week's metrics (10–20 numeric lines) | ~0.2k tokens | Aggregated by `fetch_shopify` + `fetch_analytics` |
| Product summary (3 counts) | ~0.1k tokens | Aggregated by `fetch_shopify` |
| Top N findings (default N = 20) | ~1–3k tokens | One line per finding, file:line citation only |
| Power analysis | ~0.3k tokens | Computed locally from session totals |

**Typical total input:** 9–15k tokens per run.
**Typical output:** 4–8k tokens (the synthesised report).

---

## Estimated cost per run

Using Claude Sonnet 4.6 pricing (verify current rates before quoting):

| Scenario | Input tokens | Output tokens | Approx. cost |
|---|---|---|---|
| First run of the week (cold cache) | ~12,000 | ~6,000 | ~$0.13 |
| Subsequent runs same scope (warm cache, after PR #5 lands) | ~12,000 (10k cached) | ~6,000 | ~$0.05 |
| 52 weekly runs over a year, mixed cache hits | — | — | **~$5–8/year** |

These are estimates, not contractual. The actual numbers depend on:
- How long `brand.md`, `playbook.md`, and `history.md` grow over time
- How many findings the theme analyser produces
- How verbose Claude is in the report

**Order volume does not change cost.** Whether you have 50 orders or 50,000 in
the period, the prompt only contains the aggregated metrics — same token count.

---

## Verifying actual cost on your own runs

Anthropic's API response includes `usage` fields on every call. To see the real
numbers for your store, add this snippet after the API call in
[scripts/run_agent.py — synthesise_report](scripts/run_agent.py):

```python
print(f"[cost] input_tokens: {message.usage.input_tokens}")
print(f"[cost] cache_read_input_tokens: {getattr(message.usage, 'cache_read_input_tokens', 0)}")
print(f"[cost] cache_creation_input_tokens: {getattr(message.usage, 'cache_creation_input_tokens', 0)}")
print(f"[cost] output_tokens: {message.usage.output_tokens}")
```

Anthropic also exposes per-key usage at https://console.anthropic.com → Usage.
Filter by API key to see exactly what the CRO agent consumed in a given week.

---

## Setting a hard ceiling (recommended)

For peace of mind, add a budget guardrail. Anthropic provides per-key monthly
limits in the console:

1. https://console.anthropic.com → Settings → API Keys
2. Click the key used by the CRO agent
3. Set "Monthly spend limit" to e.g. $20 — generous headroom over expected ~$0.50/month

If the agent ever malfunctions and tries to spend more, Anthropic rejects the
calls. The agent fails loudly; no surprise bills.

---

## When cost would actually become a concern

These are the failure modes worth knowing about:

1. **A regression that loops the agent on errors.** Defended by the per-key
   monthly limit above.
2. **`knowledge/` files growing into the hundreds of thousands of tokens.**
   Theoretically possible if `history.md` is never pruned. At current pace this
   takes many years; if it ever happens, the fix is to archive old history
   entries to a separate file.
3. **An ad-hoc Claude Code session reading the entire theme directory.**
   When *you* run `claude` in this repo for ad-hoc analysis, the model can
   load full theme files into context if you ask it to. That's a separate cost
   centre from the weekly scan. The weekly scan via `run_agent.py` does not
   load full theme files.

---

## Quick answers for client questions

> "Is Claude reading every one of my orders?"

No. Orders are fetched by Python, aggregated locally into a few summary
numbers (AOV, refund rate, etc.), and only those numbers are sent to Claude.
The agent could not name a single order, customer, or product line item if
asked — it never sees them.

> "What does each weekly run cost?"

About 5–15 cents at current Anthropic pricing. The cost is roughly fixed
regardless of order volume, because the prompt is mostly the knowledge base
plus aggregated metrics — not the raw data.

> "Can you guarantee customer PII never goes to Anthropic?"

The architecture is designed so that nothing reaching the prompt-builder
function contains PII — only aggregates and theme-file paths. The only way
to send PII would be to put it in `knowledge/brand.md` manually, which is
your decision.

> "What if Claude pricing changes?"

Set a per-key monthly budget in the Anthropic console. If pricing changes
unfavourably, the agent stops calling once you hit your limit. Re-evaluate
and adjust the limit, or pause the weekly cron, before re-enabling.
