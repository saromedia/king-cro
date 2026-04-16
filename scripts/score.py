"""
score.py
Applies ICE scoring heuristics to raw findings.
Returns findings sorted by ICE score descending.

ICE confidence is calibrated from historical win rates in insights.md:
- Types with >60% win rate (3+ decided): confidence +1
- Types with <30% win rate (3+ decided): confidence -1
"""

import re
from pathlib import Path

INSIGHTS_PATH = Path(__file__).parent.parent / "knowledge" / "insights.md"

# ---------------------------------------------------------------------------
# Impact heuristics by issue type keyword
# ---------------------------------------------------------------------------

IMPACT_MAP = {
    "add-to-cart": 9,
    "atc": 9,
    "checkout": 8,
    "abandoned": 8,
    "trust": 7,
    "returns": 6,
    "secure": 6,
    "review": 7,
    "upsell": 6,
    "cross-sell": 6,
    "free ship": 6,
    "description": 5,
    "image": 5,
    "lazy": 4,
    "render-blocking": 5,
    "pagination": 5,
    "filter": 5,
    "structured data": 4,
    "alt": 3,
    "footer": 3,
    "payment icon": 2,
}

CONFIDENCE_MAP = {
    "high": 8,
    "medium": 6,
    "low": 4,
}

EASE_MAP = {
    "add loading": 9,
    "add alt": 9,
    "add defer": 8,
    "add async": 8,
    "add link": 8,
    "add badge": 7,
    "add message": 7,
    "add section": 5,
    "add schema": 5,
    "verify": 6,
    "ensure": 5,
    "default": 5,
}


def estimate_impact(issue: str) -> int:
    issue_lower = issue.lower()
    for keyword, score in IMPACT_MAP.items():
        if keyword in issue_lower:
            return score
    return 5  # default mid


def estimate_confidence(severity: str) -> int:
    return CONFIDENCE_MAP.get(severity, 6)


def estimate_ease(suggestion: str) -> int:
    suggestion_lower = suggestion.lower()
    for keyword, score in EASE_MAP.items():
        if keyword in suggestion_lower:
            return score
    return EASE_MAP["default"]


def load_win_rate_calibration() -> dict:
    """
    Reads insights.md win rate table and returns a dict of type → adjustment.
    +1 for types with >60% win rate (3+ decided), -1 for <30%.
    """
    calibration = {}
    try:
        content = INSIGHTS_PATH.read_text(encoding="utf-8")
        for line in content.splitlines():
            if not line.strip().startswith("|") or "---" in line or "Type" in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 8:
                continue
            exp_type = parts[1]
            try:
                winners = int(parts[4]) if parts[4].isdigit() else 0
                losers = int(parts[5]) if parts[5].isdigit() else 0
            except (ValueError, IndexError):
                continue
            decided = winners + losers
            if decided >= 3:
                win_rate = winners / decided
                if win_rate > 0.60:
                    calibration[exp_type] = +1
                elif win_rate < 0.30:
                    calibration[exp_type] = -1
    except FileNotFoundError:
        pass
    return calibration


def score_findings(findings: list[dict]) -> list[dict]:
    calibration = load_win_rate_calibration()
    scored = []
    for f in findings:
        impact = estimate_impact(f.get("issue", ""))
        confidence = estimate_confidence(f.get("severity", "medium"))
        ease = estimate_ease(f.get("suggestion", ""))

        # Apply win rate calibration to confidence
        exp_type = f.get("experiment_type", "")
        adjustment = calibration.get(exp_type, 0)
        if adjustment:
            confidence = max(1, min(10, confidence + adjustment))

        ice = round((impact + confidence + ease) / 3, 1)

        entry = {
            **f,
            "ice_impact": impact,
            "ice_confidence": confidence,
            "ice_ease": ease,
            "ice_score": ice,
        }
        if adjustment:
            entry["ice_calibration"] = f"Confidence {'+' if adjustment > 0 else ''}{adjustment} from {exp_type} win rate"

        scored.append(entry)

    scored.sort(key=lambda x: x["ice_score"], reverse=True)
    return scored


def score_product_findings(products: list[dict]) -> list[dict]:
    """Converts product-level data issues into scoreable findings."""
    findings = []

    for p in products:
        if p.get("has_thin_description"):
            findings.append({
                "file": "Shopify Admin API — products",
                "line": None,
                "issue": f"Product '{p['title']}' has thin description ({p['description_word_count']} words)",
                "suggestion": "Expand product description to at least 80 words covering materials, dimensions, use case, and care.",
                "severity": "medium",
            })
        if p.get("has_few_images"):
            findings.append({
                "file": "Shopify Admin API — products",
                "line": None,
                "issue": f"Product '{p['title']}' has only {p['image_count']} image(s)",
                "suggestion": "Add at least 3 images: hero, lifestyle, and detail/scale shot.",
                "severity": "medium",
            })
        if p.get("has_all_variants_oos"):
            findings.append({
                "file": "Shopify Admin API — products",
                "line": None,
                "issue": f"Product '{p['title']}' has all variants out of stock",
                "suggestion": "Hide, redirect, or show a back-in-stock notification for this product.",
                "severity": "high",
            })

    return findings


def score_metric_findings(metrics: dict) -> list[dict]:
    """Converts metric thresholds into findings."""
    findings = []

    cart_rate = metrics.get("cart_abandonment_rate")
    if cart_rate and cart_rate > 0.70:
        findings.append({
            "file": "Shopify Admin API — metrics",
            "line": None,
            "issue": f"Cart abandonment rate is {cart_rate:.1%} — above 70% benchmark",
            "suggestion": "Audit checkout flow for friction. Consider abandoned cart email recovery.",
            "severity": "high",
        })

    repeat_rate = metrics.get("repeat_customer_rate")
    if repeat_rate and repeat_rate < 0.20:
        findings.append({
            "file": "Shopify Admin API — metrics",
            "line": None,
            "issue": f"Repeat customer rate is {repeat_rate:.1%} — below 20% benchmark",
            "suggestion": "Introduce post-purchase email flow and loyalty incentive.",
            "severity": "medium",
        })

    discount_rate = metrics.get("discount_usage_rate")
    if discount_rate and discount_rate > 0.40:
        findings.append({
            "file": "Shopify Admin API — metrics",
            "line": None,
            "issue": f"Discount code usage is {discount_rate:.1%} — signals price resistance",
            "suggestion": "Review pricing strategy or shift discounts to loyalty program rather than public codes.",
            "severity": "medium",
        })

    return findings
