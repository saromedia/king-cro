"""
log_result.py
Captures experiment results and feeds them back into the knowledge base.

Two modes:
  1. AB Convert import — parses CSV exports, calculates stats, logs to experiments.md
  2. Manual entry — interactive prompts for non-AB-Convert experiments

Usage:
  # Import AB Convert results (one CSV per test group)
  python scripts/log_result.py --import-ab \
    --id PDP-001 \
    --control results_control.csv \
    --variant results_variant.csv \
    --primary-metric cvr

  # Import with multiple variants
  python scripts/log_result.py --import-ab \
    --id PDP-001 \
    --control results_control.csv \
    --variant results_b.csv \
    --variant results_c.csv

  # Manual entry (interactive prompts)
  python scripts/log_result.py --manual --id PDP-001

  # Quick log (no CSV, just outcome)
  python scripts/log_result.py --quick \
    --id PDP-001 \
    --status winner \
    --lift "+12.3% CVR" \
    --confidence 96.2

  # Recalculate all insights from experiments.md
  python scripts/log_result.py --refresh-insights
"""

import argparse
import csv
import math
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))
from utils import fmt_date

REPO_ROOT = Path(__file__).parent.parent
KNOWLEDGE_DIR = REPO_ROOT / "knowledge"
EXPERIMENTS_PATH = KNOWLEDGE_DIR / "experiments.md"
INSIGHTS_PATH = KNOWLEDGE_DIR / "insights.md"
HYPOTHESES_PATH = KNOWLEDGE_DIR / "hypotheses.md"
HISTORY_PATH = KNOWLEDGE_DIR / "history.md"


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

VALID_TYPES = {"content", "pricing", "offer", "ux", "visual", "value_prop",
               "social_proof", "merchandising", "marketing_angle", "email", "technical"}

VALID_ZONES = {"buybox", "trust-block", "hero-media", "value-prop-bar",
               "social-proof-block", "content-tabs", "sticky-bar", "n/a"}

VALID_STATUSES = {"winner", "loser", "inconclusive"}


def sanitize_csv_value(val: str) -> str:
    """Strip leading formula characters to prevent CSV formula injection."""
    if val and val[0] in ("=", "+", "@", "-"):
        return "'" + val
    return val


def validate_experiment_id(exp_id: str) -> bool:
    """Experiment IDs must match SCOPE-NNN pattern."""
    return bool(re.match(r"^[A-Z]{2,5}-\d{3,4}$", exp_id))


def sanitize_for_markdown(val: str) -> str:
    """Remove pipe characters and newlines that could break markdown tables."""
    return val.replace("|", "-").replace("\n", " ").replace("\r", "").strip()


# ---------------------------------------------------------------------------
# AB Convert CSV parsing
# ---------------------------------------------------------------------------

def parse_ab_convert_csv(filepath: str) -> dict:
    """
    Parses an AB Convert CSV export for a single test group.

    Each CSV contains rows for one test group. Each row is a tracked event.
    Rows with an orderId represent conversions. Rows without are sessions.

    Returns:
        {
            "file": filepath,
            "test_group": str,
            "experiment_id": str,
            "total_rows": int,
            "conversions": int,
            "total_revenue": float,
            "unique_sessions": int,
            "device_breakdown": {"mobile": int, "desktop": int, "other": int},
            "visitor_breakdown": {"new": int, "returning": int},
            "country_breakdown": {country: count},
        }
    """
    rows = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter="\t")
        # Also try comma delimiter if tab produces single-column rows
        first_row = next(reader, None)
        if first_row and len(first_row) <= 2:
            f.seek(0)
            reader = csv.DictReader(f, delimiter=",")
            first_row = next(reader, None)

        if first_row:
            rows.append(first_row)
        for row in reader:
            rows.append(row)

    if not rows:
        print(f"[log_result] WARNING: No rows found in {filepath}")
        return {"file": filepath, "total_rows": 0, "conversions": 0}

    # Sanitize all cell values to prevent formula injection
    rows = [{k: sanitize_csv_value(str(v)) for k, v in row.items()} for row in rows]

    # Determine test group and experiment ID from first row
    test_group = rows[0].get("testGroup", "unknown")
    experiment_id = rows[0].get("experimentId", "unknown")

    # Count conversions (rows with non-empty orderId)
    conversions = 0
    total_revenue = 0.0
    unique_sessions = set()
    device_counts = {"mobile": 0, "desktop": 0, "tablet": 0, "other": 0}
    visitor_counts = {"new": 0, "returning": 0}
    country_counts = {}

    for row in rows:
        order_id = (row.get("orderId") or "").strip()
        if order_id:
            conversions += 1
            try:
                rev = float(row.get("revenue") or 0)
                total_revenue += rev
            except (ValueError, TypeError):
                pass

        session_id = (row.get("sessionId") or "").strip()
        if session_id:
            unique_sessions.add(session_id)

        device = (row.get("deviceType") or "other").strip().lower()
        if device in device_counts:
            device_counts[device] += 1
        else:
            device_counts["other"] += 1

        visitor = (row.get("visitorType") or "").strip().lower()
        if "return" in visitor:
            visitor_counts["returning"] += 1
        else:
            visitor_counts["new"] += 1

        country = (row.get("country") or "unknown").strip()
        country_counts[country] = country_counts.get(country, 0) + 1

    # Use unique sessions if available, otherwise total rows
    session_count = len(unique_sessions) if unique_sessions else len(rows)

    return {
        "file": filepath,
        "test_group": test_group,
        "experiment_id": experiment_id,
        "total_rows": len(rows),
        "conversions": conversions,
        "total_revenue": round(total_revenue, 2),
        "unique_sessions": session_count,
        "device_breakdown": device_counts,
        "visitor_breakdown": visitor_counts,
        "country_breakdown": country_counts,
    }


# ---------------------------------------------------------------------------
# Statistical analysis
# ---------------------------------------------------------------------------

def z_test_proportions(conversions_a: int, sessions_a: int,
                       conversions_b: int, sessions_b: int) -> dict:
    """
    Two-proportion z-test comparing variant B against control A.

    Returns:
        {
            "z_score": float,
            "p_value": float,
            "confidence": float (as percentage, e.g. 96.2),
            "significant_at_95": bool,
            "significant_at_90": bool,
            "lift_relative": float (as percentage, e.g. 12.3),
            "lift_absolute": float (as percentage points),
            "cvr_a": float,
            "cvr_b": float,
        }
    """
    if sessions_a == 0 or sessions_b == 0:
        return {"error": "Zero sessions in one or both groups"}

    p_a = conversions_a / sessions_a
    p_b = conversions_b / sessions_b

    # Pooled proportion
    p_pool = (conversions_a + conversions_b) / (sessions_a + sessions_b)

    # Standard error
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / sessions_a + 1 / sessions_b))

    if se == 0:
        return {"error": "Zero standard error — identical proportions or no variance"}

    z = (p_b - p_a) / se

    # Two-tailed p-value using normal approximation
    p_value = 2 * (1 - _normal_cdf(abs(z)))

    lift_absolute = (p_b - p_a) * 100
    lift_relative = ((p_b - p_a) / p_a * 100) if p_a > 0 else 0

    confidence = (1 - p_value) * 100

    return {
        "z_score": round(z, 4),
        "p_value": round(p_value, 6),
        "confidence": round(confidence, 1),
        "significant_at_95": p_value < 0.05,
        "significant_at_90": p_value < 0.10,
        "lift_relative": round(lift_relative, 1),
        "lift_absolute": round(lift_absolute, 2),
        "cvr_a": round(p_a * 100, 2),
        "cvr_b": round(p_b * 100, 2),
    }


def revenue_per_visitor(revenue: float, sessions: int) -> float:
    return round(revenue / sessions, 2) if sessions > 0 else 0


def _normal_cdf(x: float) -> float:
    """Approximation of the standard normal CDF (no scipy needed)."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def analyse_ab_convert(control_data: dict, variant_data_list: list[dict],
                       primary_metric: str = "cvr") -> dict:
    """
    Runs statistical analysis on AB Convert parsed data.

    Args:
        control_data: parsed control group
        variant_data_list: list of parsed variant groups
        primary_metric: "cvr" or "rpv" (revenue per visitor)

    Returns analysis summary with stats for each variant vs control.
    """
    results = {
        "control": {
            "group": control_data["test_group"],
            "sessions": control_data["unique_sessions"],
            "conversions": control_data["conversions"],
            "revenue": control_data["total_revenue"],
            "cvr": round(control_data["conversions"] / control_data["unique_sessions"] * 100, 2) if control_data["unique_sessions"] else 0,
            "rpv": revenue_per_visitor(control_data["total_revenue"], control_data["unique_sessions"]),
            "aov": round(control_data["total_revenue"] / control_data["conversions"], 2) if control_data["conversions"] else 0,
        },
        "variants": [],
        "primary_metric": primary_metric,
        "winner": None,
    }

    for variant_data in variant_data_list:
        stats = z_test_proportions(
            control_data["conversions"], control_data["unique_sessions"],
            variant_data["conversions"], variant_data["unique_sessions"],
        )

        variant_result = {
            "group": variant_data["test_group"],
            "sessions": variant_data["unique_sessions"],
            "conversions": variant_data["conversions"],
            "revenue": variant_data["total_revenue"],
            "cvr": round(variant_data["conversions"] / variant_data["unique_sessions"] * 100, 2) if variant_data["unique_sessions"] else 0,
            "rpv": revenue_per_visitor(variant_data["total_revenue"], variant_data["unique_sessions"]),
            "aov": round(variant_data["total_revenue"] / variant_data["conversions"], 2) if variant_data["conversions"] else 0,
            "stats": stats,
        }
        results["variants"].append(variant_result)

    # Determine winner
    for v in results["variants"]:
        stats = v.get("stats", {})
        if stats.get("significant_at_95") and stats.get("lift_relative", 0) > 0:
            if results["winner"] is None or stats["lift_relative"] > results["winner"]["stats"]["lift_relative"]:
                results["winner"] = v

    return results


# ---------------------------------------------------------------------------
# Knowledge base updates
# ---------------------------------------------------------------------------

def update_experiments_log(experiment_id: str, status: str, lift: str,
                           confidence: str, end_date: str = None,
                           notes: str = "") -> None:
    """
    Updates an existing experiment row in experiments.md, or appends a note
    if the experiment is not found in the log.
    """
    end_date = end_date or fmt_date()
    content = EXPERIMENTS_PATH.read_text(encoding="utf-8")

    # Try to find and update existing row
    # Look for a row starting with | {experiment_id} |
    pattern = re.compile(
        r"^(\|[^|]*" + re.escape(experiment_id) + r"[^|]*\|)",
        re.MULTILINE,
    )
    match = pattern.search(content)

    if match:
        # Build column index map from header row
        col_map = {}
        lines = content.splitlines()
        for line in lines:
            if line.strip().startswith("|") and "ID" in line and "Status" in line:
                headers = [h.strip() for h in line.split("|")]
                col_map = {name: idx for idx, name in enumerate(headers) if name}
                break

        new_lines = []
        for line in lines:
            cells = [p.strip() for p in line.split("|")] if line.strip().startswith("|") else []
            if cells and len(cells) >= 2 and cells[1] == experiment_id:
                parts = [p for p in line.split("|")]
                if col_map:
                    if "Status" in col_map and col_map["Status"] < len(parts):
                        parts[col_map["Status"]] = f" {status} "
                    if "End" in col_map and col_map["End"] < len(parts):
                        parts[col_map["End"]] = f" {end_date} "
                    if "Lift" in col_map and col_map["Lift"] < len(parts):
                        parts[col_map["Lift"]] = f" {lift} "
                    if "Confidence" in col_map and col_map["Confidence"] < len(parts):
                        parts[col_map["Confidence"]] = f" {confidence} "
                    if notes and "Notes" in col_map and col_map["Notes"] < len(parts):
                        parts[col_map["Notes"]] = f" {notes} "
                    new_lines.append("|".join(parts))
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        content = "\n".join(new_lines)
        EXPERIMENTS_PATH.write_text(content, encoding="utf-8")
        print(f"[log_result] Updated {experiment_id} in experiments.md — status: {status}")
    else:
        print(f"[log_result] Experiment {experiment_id} not found in log — add it manually or via the CRO agent")


def update_zone_tracker(experiment_id: str, zone: str, status: str) -> None:
    """Updates the active zone tracker in experiments.md."""
    content = EXPERIMENTS_PATH.read_text(encoding="utf-8")

    if status in ("winner", "loser", "inconclusive", "dismissed"):
        # Clear the zone
        content = re.sub(
            rf"(\| {re.escape(zone)}\s*\|)[^|]*\|[^|]*\|[^|]*\|",
            rf"\1 — | — | — |",
            content,
        )
    elif status == "active":
        content = re.sub(
            rf"(\| {re.escape(zone)}\s*\|)[^|]*\|[^|]*\|[^|]*\|",
            rf"\1 {experiment_id} | active | {fmt_date()} |",
            content,
        )

    EXPERIMENTS_PATH.write_text(content, encoding="utf-8")


def update_insights(experiment_id: str, exp_type: str, status: str,
                    lift: str, confidence: str) -> None:
    """
    Recalculates win rates in insights.md based on the full experiments.md log.
    Appends a dated observation entry.
    """
    # Read experiments.md and count outcomes per type.
    # Use a header-derived column map so reordering columns in experiments.md
    # cannot silently produce wrong win rates.
    content = EXPERIMENTS_PATH.read_text(encoding="utf-8")
    type_stats = {}
    col_map: dict[str, int] = {}

    for line in content.splitlines():
        if not line.strip().startswith("|") or "---" in line:
            continue
        parts = [p.strip() for p in line.split("|")]

        # The header row defines column positions. Cache it the first time we see it.
        if not col_map:
            if "ID" in parts and "Type" in parts and "Status" in parts:
                col_map = {name: idx for idx, name in enumerate(parts) if name}
                continue
            # Skip any pre-header noise (zone tracker tables etc.)
            continue

        id_idx = col_map.get("ID")
        type_idx = col_map.get("Type")
        status_idx = col_map.get("Status")
        if id_idx is None or type_idx is None or status_idx is None:
            continue
        if len(parts) <= max(id_idx, type_idx, status_idx):
            continue

        row_id = parts[id_idx]
        if not row_id or row_id == "—":
            continue
        row_type = parts[type_idx]
        row_status = parts[status_idx]

        if not row_type:
            continue

        if row_type not in type_stats:
            type_stats[row_type] = {"suggested": 0, "active": 0, "winners": 0, "losers": 0, "inconclusive": 0}

        if row_status == "suggested":
            type_stats[row_type]["suggested"] += 1
        elif row_status == "active":
            type_stats[row_type]["active"] += 1
        elif row_status == "winner":
            type_stats[row_type]["winners"] += 1
        elif row_status == "loser":
            type_stats[row_type]["losers"] += 1
        elif row_status == "inconclusive":
            type_stats[row_type]["inconclusive"] += 1

    # Build updated win rate table
    table_lines = [
        "| Type | Suggested | Active | Winners | Losers | Inconclusive | Win rate | Signal |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for t, s in sorted(type_stats.items()):
        decided = s["winners"] + s["losers"]
        win_rate = f"{s['winners'] / decided:.0%}" if decided > 0 else "n/a"
        signal = _win_rate_signal(s["winners"], s["losers"], decided)
        table_lines.append(
            f"| {t} | {s['suggested']} | {s['active']} | {s['winners']} | {s['losers']} | {s['inconclusive']} | {win_rate} | {signal} |"
        )

    # Build observation entry
    observation = f"""
## {fmt_date()}

### Result logged
- Experiment: {experiment_id}
- Type: {exp_type}
- Status: {status}
- Lift: {lift}
- Confidence: {confidence}

### Win rate snapshot
{chr(10).join(table_lines)}

### Pattern observations
"""
    # Add auto-observations
    for t, s in sorted(type_stats.items()):
        decided = s["winners"] + s["losers"]
        if decided >= 3 and s["winners"] / decided >= 0.67:
            observation += f"- **{t}** is a strong performer: {s['winners']}/{decided} winners ({s['winners']/decided:.0%}). Consider increasing experiment volume.\n"
        elif decided >= 3 and s["winners"] / decided <= 0.33:
            observation += f"- **{t}** is underperforming: {s['winners']}/{decided} winners ({s['winners']/decided:.0%}). Re-evaluate approach before running more.\n"

    # Check for underutilised types
    high_win_low_volume = []
    for t, s in type_stats.items():
        decided = s["winners"] + s["losers"]
        if decided >= 2 and s["winners"] / decided >= 0.6 and s["suggested"] + s["active"] <= 1:
            high_win_low_volume.append(t)

    if high_win_low_volume:
        observation += f"\n### Underutilised strategies\n"
        for t in high_win_low_volume:
            s = type_stats[t]
            decided = s["winners"] + s["losers"]
            observation += f"- **{t}**: {s['winners']}/{decided} win rate but only {s['suggested'] + s['active']} in pipeline. Generate more experiments of this type.\n"

    # Write updated insights.md
    insights_content = INSIGHTS_PATH.read_text(encoding="utf-8")

    # Replace win rate table
    old_table_pattern = r"\| Type \| Suggested \| Active \|.*?(?=\n---|\n## |\Z)"
    new_table = "\n".join(table_lines)
    if re.search(old_table_pattern, insights_content, re.DOTALL):
        insights_content = re.sub(old_table_pattern, new_table, insights_content, flags=re.DOTALL)
    else:
        # Insert table after the header
        insights_content = insights_content.replace(
            "| *(agent populates after first experiments complete)* | | | | | | |",
            "\n".join(table_lines[1:]),  # skip header row since it already exists
        )

    # Append observation to log
    if "<!-- Agent appends entries below" in insights_content:
        insights_content = insights_content.replace(
            "<!-- Agent appends entries below after each run. Nothing here yet — fresh install. -->",
            observation,
        )
    else:
        insights_content += "\n" + observation

    INSIGHTS_PATH.write_text(insights_content, encoding="utf-8")
    print(f"[log_result] Updated insights.md with win rates and observation")


def _win_rate_signal(winners: int, losers: int, decided: int) -> str:
    if decided == 0:
        return "No data"
    if decided < 3:
        return "Too early"
    rate = winners / decided
    if rate >= 0.67:
        return "Strong — increase volume"
    elif rate >= 0.50:
        return "Moderate — continue"
    elif rate >= 0.33:
        return "Weak — review approach"
    else:
        return "Poor — deprioritise or rethink"


def update_hypothesis(hypothesis_id: str, status: str, experiment_id: str) -> None:
    """
    Updates a hypothesis status in hypotheses.md based on experiment outcome.
    """
    if not hypothesis_id or hypothesis_id == "—":
        return

    content = HYPOTHESES_PATH.read_text(encoding="utf-8")

    if status == "winner":
        # Mark hypothesis as confirmed
        content = content.replace(
            f"- [ ] **{hypothesis_id}",
            f"- [✓] **{hypothesis_id}",
        )
        content = content.replace(
            f"- [~] **{hypothesis_id}",
            f"- [✓] **{hypothesis_id}",
        )
    elif status == "loser":
        # Mark as refuted (but only if it was the only experiment testing it)
        content = content.replace(
            f"- [~] **{hypothesis_id}",
            f"- [✗] **{hypothesis_id}",
        )

    # Add experiment reference
    # Look for the hypothesis line and add a note after it
    lines = content.splitlines()
    new_lines = []
    for i, line in enumerate(lines):
        new_lines.append(line)
        if hypothesis_id in line and line.strip().startswith("- ["):
            # Append experiment reference after any existing "Tested by:" lines
            ref_line = f"  Tested by: {experiment_id} ({status}, {fmt_date()})"
            # Skip past existing "Tested by:" lines to find insertion point
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith("Tested by:"):
                j += 1
            # Only add if this experiment isn't already recorded
            existing_refs = [lines[k] for k in range(i + 1, j)]
            if not any(experiment_id in ref for ref in existing_refs):
                new_lines.append(ref_line)

    HYPOTHESES_PATH.write_text("\n".join(new_lines), encoding="utf-8")
    print(f"[log_result] Updated hypothesis '{hypothesis_id}' — {status}")


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def print_analysis_report(analysis: dict, experiment_id: str) -> str:
    """Prints a formatted analysis report and returns a summary string."""
    ctrl = analysis["control"]
    print(f"\n{'='*60}")
    print(f"  EXPERIMENT RESULTS: {experiment_id}")
    print(f"{'='*60}\n")

    print(f"  Control ({ctrl['group']}):")
    print(f"    Sessions:    {ctrl['sessions']:,}")
    print(f"    Conversions: {ctrl['conversions']:,}")
    print(f"    CVR:         {ctrl['cvr']}%")
    print(f"    Revenue:     ${ctrl['revenue']:,.2f}")
    print(f"    RPV:         ${ctrl['rpv']}")
    print(f"    AOV:         ${ctrl['aov']}")

    overall_status = "inconclusive"
    best_lift = ""
    best_confidence = ""

    for v in analysis["variants"]:
        stats = v.get("stats", {})
        print(f"\n  Variant ({v['group']}):")
        print(f"    Sessions:    {v['sessions']:,}")
        print(f"    Conversions: {v['conversions']:,}")
        print(f"    CVR:         {v['cvr']}%")
        print(f"    Revenue:     ${v['revenue']:,.2f}")
        print(f"    RPV:         ${v['rpv']}")
        print(f"    AOV:         ${v['aov']}")

        if "error" not in stats:
            direction = "up" if stats["lift_relative"] > 0 else "down"
            sig_marker = "***" if stats["significant_at_95"] else ("**" if stats["significant_at_90"] else "")
            print(f"\n    Lift:        {stats['lift_relative']:+.1f}% CVR ({stats['lift_absolute']:+.2f}pp) {sig_marker}")
            print(f"    Confidence:  {stats['confidence']}%")
            print(f"    p-value:     {stats['p_value']}")
            print(f"    z-score:     {stats['z_score']}")

            if stats["significant_at_95"]:
                if stats["lift_relative"] > 0:
                    print(f"    Result:      WINNER at 95% confidence")
                    overall_status = "winner"
                else:
                    print(f"    Result:      LOSER at 95% confidence")
                    overall_status = "loser"
            elif stats["significant_at_90"]:
                print(f"    Result:      TRENDING at 90% (not yet significant at 95%)")
                overall_status = "inconclusive"
            else:
                print(f"    Result:      INCONCLUSIVE (confidence below 90%)")
                overall_status = "inconclusive"

            best_lift = f"{stats['lift_relative']:+.1f}% CVR"
            best_confidence = f"{stats['confidence']}%"
        else:
            print(f"    Stats error: {stats['error']}")

    if analysis["winner"]:
        print(f"\n  {'='*60}")
        print(f"  WINNER: Variant {analysis['winner']['group']}")
        print(f"  {'='*60}")
    else:
        print(f"\n  {'='*60}")
        print(f"  NO CLEAR WINNER")
        print(f"  {'='*60}")

    print()
    return overall_status, best_lift, best_confidence


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------

def prompt_experiment_metadata(experiment_id: str) -> dict:
    """Prompts user for experiment metadata needed to log the result."""
    print(f"\n--- Logging result for {experiment_id} ---\n")

    exp_type = input("Experiment type (content/pricing/offer/ux/visual/value_prop/social_proof/merchandising/marketing_angle/email/technical): ").strip().lower()
    while exp_type not in VALID_TYPES:
        print(f"  Invalid type '{exp_type}'. Must be one of: {', '.join(sorted(VALID_TYPES))}")
        exp_type = input("Experiment type: ").strip().lower()

    zone = input("Zone (buybox/trust-block/hero-media/value-prop-bar/social-proof-block/content-tabs/sticky-bar/n/a): ").strip().lower()
    while zone not in VALID_ZONES:
        print(f"  Invalid zone '{zone}'. Must be one of: {', '.join(sorted(VALID_ZONES))}")
        zone = input("Zone: ").strip().lower()

    hypothesis_id = input("Linked hypothesis ID (e.g. H-003, or press Enter for none): ").strip() or "—"
    if hypothesis_id != "—" and not re.match(r"^H-\d{3,4}$", hypothesis_id):
        print(f"  Warning: '{hypothesis_id}' doesn't match expected format H-NNN. Proceeding anyway.")

    learnings = sanitize_for_markdown(input("Key learning (1 sentence — what did this teach you?): ").strip())
    follow_up = sanitize_for_markdown(input("Follow-up action (implement winner / iterate / abandon / new experiment): ").strip())

    return {
        "type": exp_type,
        "zone": zone,
        "hypothesis_id": hypothesis_id,
        "learnings": learnings,
        "follow_up": follow_up,
    }


def manual_entry(experiment_id: str) -> None:
    """Full interactive manual entry for experiments without AB Convert data."""
    metadata = prompt_experiment_metadata(experiment_id)

    print("\n--- Enter results ---\n")
    status = input("Outcome (winner/loser/inconclusive): ").strip().lower()
    lift = input("Observed lift (e.g. +12.3% CVR, -2.1% AOV): ").strip()
    confidence = input("Statistical confidence (e.g. 96.2%): ").strip()
    start_date = input("Test start date (DD-MM-YYYY): ").strip()
    end_date = input("Test end date (DD-MM-YYYY, or Enter for today): ").strip() or fmt_date()
    tool = input("Testing tool used (e.g. AB Convert, manual toggle): ").strip() or "AB Convert"

    notes = f"{metadata['learnings']}. Follow-up: {metadata['follow_up']}"

    update_experiments_log(experiment_id, status, lift, confidence, end_date, notes)
    update_zone_tracker(experiment_id, metadata["zone"], status)
    update_insights(experiment_id, metadata["type"], status, lift, confidence)
    update_hypothesis(metadata["hypothesis_id"], status, experiment_id)

    print(f"\n[log_result] Done. Experiment {experiment_id} logged as {status}.")
    print(f"[log_result] Updated: experiments.md, insights.md" +
          (f", hypotheses.md ({metadata['hypothesis_id']})" if metadata["hypothesis_id"] != "—" else ""))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_ab_import(args) -> None:
    """Parse AB Convert CSVs, analyse, and log results."""
    experiment_id = args.id

    if not validate_experiment_id(experiment_id):
        print(f"[log_result] ERROR: Invalid experiment ID '{experiment_id}'. Expected format: PDP-001, CART-012, etc.")
        return

    # Validate CSV file paths exist and are actual files (not directories or traversal)
    for csv_path in [args.control] + args.variant:
        p = Path(csv_path).resolve()
        if not p.exists():
            print(f"[log_result] ERROR: File not found: {csv_path}")
            return
        if not p.is_file():
            print(f"[log_result] ERROR: Not a file: {csv_path}")
            return
        if not p.suffix.lower() == ".csv":
            print(f"[log_result] WARNING: {csv_path} does not have .csv extension")

    # Parse CSVs
    print(f"\n[log_result] Parsing control: {args.control}")
    control_data = parse_ab_convert_csv(args.control)
    print(f"  Rows: {control_data['total_rows']} | Sessions: {control_data['unique_sessions']} | Conversions: {control_data['conversions']}")

    variant_data_list = []
    for vf in args.variant:
        print(f"[log_result] Parsing variant: {vf}")
        vd = parse_ab_convert_csv(vf)
        print(f"  Rows: {vd['total_rows']} | Sessions: {vd['unique_sessions']} | Conversions: {vd['conversions']}")
        variant_data_list.append(vd)

    # Analyse
    analysis = analyse_ab_convert(control_data, variant_data_list, args.primary_metric)

    # Print report
    overall_status, best_lift, best_confidence = print_analysis_report(analysis, experiment_id)

    # Prompt for metadata
    metadata = prompt_experiment_metadata(experiment_id)

    # Confirm before writing
    print(f"\nAbout to log {experiment_id} as '{overall_status}' with lift {best_lift}")
    confirm = input("Proceed? (y/n): ").strip().lower()
    if confirm != "y":
        override = input("Override status (winner/loser/inconclusive) or 'cancel': ").strip().lower()
        if override == "cancel":
            print("[log_result] Cancelled.")
            return
        if override not in VALID_STATUSES:
            print(f"[log_result] ERROR: Invalid status '{override}'. Must be one of: {', '.join(sorted(VALID_STATUSES))}")
            return
        overall_status = override

    notes = f"{metadata['learnings']}. Follow-up: {metadata['follow_up']}"

    # Write to knowledge base
    update_experiments_log(experiment_id, overall_status, best_lift, best_confidence,
                          fmt_date(), notes)
    update_zone_tracker(experiment_id, metadata["zone"], overall_status)
    update_insights(experiment_id, metadata["type"], overall_status, best_lift, best_confidence)
    update_hypothesis(metadata["hypothesis_id"], overall_status, experiment_id)

    print(f"\n[log_result] Done. Experiment {experiment_id} logged as {overall_status}.")
    print(f"[log_result] Updated: experiments.md, insights.md" +
          (f", hypotheses.md ({metadata['hypothesis_id']})" if metadata["hypothesis_id"] != "—" else ""))


def refresh_insights() -> None:
    """Recalculates all insights from experiments.md without logging a new result."""
    update_insights("(refresh)", "—", "—", "—", "—")
    print("[log_result] Insights recalculated from experiments.md")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Log experiment results to the CRO knowledge base")

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--import-ab", action="store_true",
                      help="Import AB Convert CSV exports")
    mode.add_argument("--manual", action="store_true",
                      help="Interactive manual entry")
    mode.add_argument("--quick", action="store_true",
                      help="Quick log without CSV import")
    mode.add_argument("--refresh-insights", action="store_true",
                      help="Recalculate insights from experiments.md")

    parser.add_argument("--id", type=str, help="Experiment ID (e.g. PDP-001)")
    parser.add_argument("--control", type=str, help="Path to control group CSV")
    parser.add_argument("--variant", type=str, action="append", default=[],
                        help="Path to variant CSV (can specify multiple)")
    parser.add_argument("--primary-metric", type=str, default="cvr",
                        choices=["cvr", "rpv"], help="Primary metric to evaluate")

    # Quick mode args
    parser.add_argument("--status", type=str, choices=["winner", "loser", "inconclusive"])
    parser.add_argument("--lift", type=str, help="e.g. '+12.3%% CVR'")
    parser.add_argument("--confidence", type=float, help="e.g. 96.2")

    args = parser.parse_args()

    if args.import_ab:
        if not args.id or not args.control or not args.variant:
            parser.error("--import-ab requires --id, --control, and at least one --variant")
        run_ab_import(args)

    elif args.manual:
        if not args.id:
            parser.error("--manual requires --id")
        manual_entry(args.id)

    elif args.quick:
        if not all([args.id, args.status, args.lift, args.confidence]):
            parser.error("--quick requires --id, --status, --lift, and --confidence")
        metadata = prompt_experiment_metadata(args.id)
        notes = f"{metadata['learnings']}. Follow-up: {metadata['follow_up']}"
        update_experiments_log(args.id, args.status, args.lift,
                              f"{args.confidence}%", notes=notes)
        update_zone_tracker(args.id, metadata["zone"], args.status)
        update_insights(args.id, metadata["type"], args.status, args.lift, f"{args.confidence}%")
        update_hypothesis(metadata["hypothesis_id"], args.status, args.id)
        print(f"\n[log_result] Done. {args.id} logged as {args.status}.")

    elif args.refresh_insights:
        refresh_insights()
