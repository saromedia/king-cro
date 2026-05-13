"""
run_agent.py
Master orchestrator for the Shopify CRO agent.

Usage:
  python scripts/run_agent.py --weekly          # full scan + notify
  python scripts/run_agent.py --weekly --dry-run  # simulate without API calls or Slack
  python scripts/run_agent.py                   # ad-hoc: reads knowledge base, awaits prompt
"""

import argparse
import os
import sys
from datetime import date
from pathlib import Path

import anthropic
from dotenv import load_dotenv


def fmt_date(d=None) -> str:
    """Format a date as DD-MM-YYYY. Defaults to today."""
    d = d or date.today()
    return d.strftime("%d-%m-%Y")

load_dotenv()

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).parent))

import fetch_shopify
import fetch_analytics
import analyse_theme
import score as scorer
import notify
import power

REPO_ROOT = Path(__file__).parent.parent
KNOWLEDGE_DIR = REPO_ROOT / "knowledge"
REPORTS_ROOT = REPO_ROOT / "reports"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_knowledge_base() -> str:
    files = {
        "CLAUDE.md": REPO_ROOT / "CLAUDE.md",
        "brand.md": KNOWLEDGE_DIR / "brand.md",
        "hypotheses.md": KNOWLEDGE_DIR / "hypotheses.md",
        "playbook.md": KNOWLEDGE_DIR / "playbook.md",
        "history.md": KNOWLEDGE_DIR / "history.md",
        "insights.md": KNOWLEDGE_DIR / "insights.md",
        "experiments.md": KNOWLEDGE_DIR / "experiments.md",
    }
    sections = []
    for name, path in files.items():
        if path.exists():
            content = path.read_text(encoding="utf-8")
            sections.append(f"## {name}\n\n{content}")
        else:
            sections.append(f"## {name}\n\n(file not found)")
    return "\n\n---\n\n".join(sections)


def build_synthesis_prompt(knowledge: str, all_findings: list[dict], metrics: dict, products: list[dict], **kwargs) -> str:
    top_findings_text = "\n".join(
        f"- [ICE {f['ice_score']}] {f['issue']} | {f.get('file','')}{':%d' % f['line'] if f.get('line') else ''} | {f['suggestion']}"
        for f in all_findings[:20]
    )

    metrics_text = "\n".join(f"- {k}: {v}" for k, v in metrics.items())

    # Merge analytics data if available
    analytics = kwargs.get("analytics")
    only_types = kwargs.get("only_types", [])
    scope = kwargs.get("scope", "pdp")

    if analytics:
        sessions_data = analytics.get("sessions", {})
        device_data = analytics.get("device_breakdown", {})
        if sessions_data.get("total_sessions"):
            metrics_text += f"\n- total_sessions (Analytics API): {sessions_data['total_sessions']}"
            metrics_text += f"\n- conversion_rate (Analytics API): {sessions_data.get('conversion_rate')}"
        if device_data.get("gap_flagged"):
            metrics_text += f"\n- DEVICE GAP ALERT: {device_data['gap_note']}"

    thin_products = [p for p in products if p.get("has_thin_description")]
    few_images = [p for p in products if p.get("has_few_images")]
    all_oos = [p for p in products if p.get("has_all_variants_oos")]

    product_summary = (
        f"- {len(thin_products)} products with thin descriptions (< 80 words)\n"
        f"- {len(few_images)} products with fewer than 3 images\n"
        f"- {len(all_oos)} products fully out of stock\n"
    )

    filter_block = (
        f"ACTIVE FILTER: Only surface findings and experiments of these types: "
        f"{', '.join(only_types)}. Ignore all other types entirely."
        if only_types
        else "No type filter active — include all experiment types."
    )

    # Calculate power analysis if we have session data
    power_note = ""
    sessions_total = metrics.get("total_sessions")
    cvr = metrics.get("conversion_rate")
    if sessions_total and cvr:
        # Use actual daily session data if available, otherwise approximate
        period_days = 30
        if analytics and analytics.get("sessions", {}).get("period_days"):
            period_days = analytics["sessions"]["period_days"]
        weekly_sessions = int(sessions_total / period_days * 7)
        cvr_pct = float(cvr) * 100 if float(cvr) < 1 else float(cvr)
        viability = power.assess_test_viability(
            baseline_cvr=cvr_pct,
            mde_relative=10,
            num_variants=2,
            weekly_sessions=weekly_sessions,
        )
        power_note = (
            f"\n\n# POWER ANALYSIS\n\n"
            f"- Weekly sessions (est): {weekly_sessions:,}\n"
            f"- Baseline CVR: {cvr_pct}%\n"
            f"- For a 10% relative MDE (A/B): {viability['sample_per_variant']:,} sessions/variant, ~{viability['estimated_weeks']} weeks\n"
            f"- A/B viable in <6 weeks: {'YES' if viability['viable'] else 'NO'}\n"
        )
        # Check MVT viability
        mvt_viability = power.assess_test_viability(
            baseline_cvr=cvr_pct,
            mde_relative=10,
            num_variants=3,
            weekly_sessions=weekly_sessions,
        )
        power_note += (
            f"- For a 3-way MVT: {mvt_viability['total_sessions_required']:,} total sessions, ~{mvt_viability['estimated_weeks']} weeks\n"
            f"- 3-way MVT viable in <6 weeks: {'YES' if mvt_viability['viable'] else 'NO'}\n"
            f"\nUse these numbers when suggesting experiments. Flag any proposal that would take >6 weeks.\n"
        )

    return f"""You are a senior Shopify CRO analyst. Below is your knowledge base (including brand context, past experiment results, and win rates by experiment type), the metrics from this week's scan, and the scored findings from the theme audit and product analysis.

Produce a weekly CRO report exactly matching the structure defined in CLAUDE.md. Be specific. Cite file:line references. Use raw numbers for metrics. Do not add generic advice not supported by the findings below.

Ground all recommendations in the brand context from brand.md. Consider the industry, customer profile, price positioning, and known friction points when scoring impact and suggesting experiments. If brand.md is empty, note this prominently and flag that recommendations are generic until it's populated.

When suggesting experiments, check the win rate table in insights.md. Boost confidence for experiment types with >60% win rate (3+ decided). Reduce confidence for types with <30% win rate (3+ decided). Note the calibration.

ACTIVE SCOPE: {scope} — restrict all findings, actions, and experiments to this page scope only.
{filter_block}

---

# KNOWLEDGE BASE

{knowledge}

---

# THIS WEEK'S METRICS

{metrics_text}

---

# PRODUCT DATA SUMMARY

{product_summary}

---

# SCORED FINDINGS (top 20, sorted by ICE score)

{top_findings_text}

---
{power_note}
---

Now produce the full report in Markdown.
"""


def synthesise_report(prompt: str, dry_run: bool = False) -> str:
    if dry_run:
        return f"# DRY RUN REPORT — {date.today()}\n\nThis is a simulated report. No Claude API call was made.\n"

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set in .env")

    client = anthropic.Anthropic(api_key=api_key)

    # Use prompt caching: the knowledge base + instructions are stable across runs,
    # so mark them as cacheable to reduce latency and cost on repeat runs.
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=12000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            }
        ],
    )
    return message.content[0].text


def append_to_history(report_date: str, metrics: dict, top_findings: list[dict]) -> None:
    history_path = KNOWLEDGE_DIR / "history.md"
    cart_rate = metrics.get("cart_abandonment_rate")

    entry_lines = [
        f"\n## {report_date}\n",
        "### Metrics snapshot",
        f"- Orders (30d): {metrics.get('total_orders', 'n/a')}",
        f"- AOV: ${metrics.get('aov', 'n/a')}",
        f"- Cart abandonment: {f'{cart_rate:.1%}' if cart_rate else 'n/a'}",
        f"- Conversion rate: {metrics.get('conversion_rate', 'n/a')} (session data required)",
        "",
        "### Top findings",
    ]

    for i, f in enumerate(top_findings[:5], 1):
        location = f.get("file", "")
        if f.get("line"):
            location += f":{f['line']}"
        entry_lines.append(f"{i}. [ICE {f['ice_score']}] {f['issue']} — {location} — Status: New")

    entry_lines += [
        "",
        "### Hypothesis updates",
        "- (see full report for hypothesis status)",
        "",
        "### Actioned since last run",
        "- (fill in manually)",
        "",
    ]

    with open(history_path, "a", encoding="utf-8") as f:
        f.write("\n".join(entry_lines))

    print(f"[run_agent] Appended to {history_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_weekly(dry_run: bool = False, only_types: list[str] = None, scope: str = "pdp") -> None:
    only_types = only_types or []
    report_date = fmt_date()
    reports_dir = REPORTS_ROOT / scope
    reports_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n[run_agent] Starting weekly CRO scan — {report_date}")
    print(f"[run_agent] Scope: {scope} | Dry run: {dry_run}")
    if only_types:
        print(f"[run_agent] Filter: --only {', '.join(only_types)}\n")
    else:
        print("[run_agent] No type filter — full scan\n")

    # 1. Read knowledge base
    print("[run_agent] Reading knowledge base...")
    knowledge = read_knowledge_base()

    # 2. Fetch Shopify data
    shopify_data = fetch_shopify.fetch_all(dry_run=dry_run)
    metrics = shopify_data["metrics"]
    products = shopify_data["products"]

    # 3. Fetch analytics (sessions + CVR via GraphQL)
    analytics_data = fetch_analytics.fetch_all_analytics(dry_run=dry_run)
    # Merge CVR into metrics if available
    sessions = analytics_data.get("sessions", {})
    if sessions.get("conversion_rate"):
        metrics["conversion_rate"] = sessions["conversion_rate"]
        metrics["total_sessions"] = sessions["total_sessions"]

    # 4. Analyse theme
    theme_findings = analyse_theme.analyse(scope=scope, dry_run=dry_run)

    # 5. Score all findings
    print("[run_agent] Scoring findings...")
    product_findings = scorer.score_product_findings(products)
    metric_findings = scorer.score_metric_findings(metrics)
    # Add device gap as a finding if flagged
    device_data = analytics_data.get("device_breakdown", {})
    if device_data.get("gap_flagged"):
        metric_findings.append({
            "file": "Shopify Analytics API — device breakdown",
            "line": None,
            "issue": device_data["gap_note"],
            "suggestion": "Audit mobile product and cart UX. Run on a real device. Check button sizes, tap targets, and checkout flow.",
            "severity": "high",
        })
    raw_findings = theme_findings + product_findings + metric_findings
    all_findings = scorer.score_findings(raw_findings)
    print(f"[run_agent] {len(all_findings)} total findings, top ICE: {all_findings[0]['ice_score'] if all_findings else 'n/a'}")

    # 6. Synthesise report via Claude API
    print("[run_agent] Synthesising report...")
    prompt = build_synthesis_prompt(knowledge, all_findings, metrics, products, analytics=analytics_data, only_types=only_types, scope=scope)
    report_md = synthesise_report(prompt, dry_run=dry_run)

    # 7. Write report
    report_path = reports_dir / f"{report_date}.md"
    report_path.write_text(report_md, encoding="utf-8")
    print(f"[run_agent] Report written to {report_path}")

    # 8. Append to history
    if not dry_run:
        append_to_history(report_date, metrics, all_findings)

    # 9. Notify
    notify.send_slack(all_findings[:5], metrics, report_date, dry_run=dry_run)
    notify.send_email(all_findings[:5], metrics, report_date, report_md, dry_run=dry_run)

    print(f"\n[run_agent] Done. {'(dry run — no external calls made)' if dry_run else ''}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shopify CRO Agent")
    parser.add_argument("--weekly", action="store_true", help="Run full weekly scan")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without API calls or notifications")
    parser.add_argument(
        "--scope",
        type=str,
        default="pdp",
        help="Page scope to analyse. Default: pdp. Options: pdp, mini-cart, collection, homepage, checkout",
    )
    parser.add_argument(
        "--only",
        type=str,
        default="",
        help="Comma-separated experiment types to focus on. "
             "e.g. --only pricing,offer  or  --only ux,content,social_proof\n"
             "Valid types: content, pricing, offer, ux, visual, value_prop, social_proof, "
             "merchandising, marketing_angle, email, technical",
    )
    args = parser.parse_args()

    only_types = [t.strip().lower() for t in args.only.split(",") if t.strip()] if args.only else []

    if args.weekly or args.dry_run:
        run_weekly(dry_run=args.dry_run, only_types=only_types, scope=args.scope)
    else:
        print("Ad-hoc mode: open this project in Claude Code and run your prompt.")
        print("The agent will read the knowledge base and focus on what you specify.")
        print("\nFor weekly scan:        python scripts/run_agent.py --weekly")
        print("For dry run:            python scripts/run_agent.py --weekly --dry-run")
        print("For focused scan:       python scripts/run_agent.py --weekly --only pricing,offer")
        print("For different scope:    python scripts/run_agent.py --weekly --scope mini-cart")
