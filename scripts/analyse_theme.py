"""
analyse_theme.py
Scope-aware Liquid theme analyser.
Only checks files and rules relevant to the active scope.

To add a new scope:
1. Add a SCOPE_FILE_PATTERNS entry
2. Add a SCOPE_CHECKS entry pointing to check functions
3. Add check functions below
"""

import os
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

THEME_DIR = os.getenv("THEME_DIR", "")

# ---------------------------------------------------------------------------
# Scope → file patterns
# Add new scopes here. Patterns are matched against relative file paths.
# ---------------------------------------------------------------------------

SCOPE_FILE_PATTERNS = {
    "pdp": [
        r"(?:^|/)(?:main-)?product(?:-template|-form|-price|-media|-info|-variant)?\.liquid$",
        r"(?:^|/)product[_-]",
    ],
    "mini-cart": [
        r"cart-drawer",
        r"mini-cart",
        r"cart-items",
        r"cart-footer",
        r"cart-template",
    ],
    "collection": [
        r"(?:^|/)(?:main-)?collection(?:-template)?\.liquid$",
        r"product-card",
        r"product-grid",
    ],
    "homepage": [
        r"(?:^|/)index\.",
        r"(?:^|/)hero",
        r"(?:^|/)slideshow",
        r"featured-collection",
        r"featured-products",
    ],
    "checkout": [
        r"checkout",
    ],
}


def file_matches_scope(rel_path: str, scope: str) -> bool:
    patterns = SCOPE_FILE_PATTERNS.get(scope, [])
    path_lower = rel_path.lower()
    return any(re.search(p, path_lower) for p in patterns)


# ---------------------------------------------------------------------------
# Check functions — PDP scope
# ---------------------------------------------------------------------------

def pdp_check_missing_lazy_loading(path: str, lines: list[str]) -> list[dict]:
    findings = []
    for i, line in enumerate(lines, 1):
        if re.search(r"<img\b", line, re.IGNORECASE) and "loading=" not in line:
            findings.append({
                "scope": "pdp",
                "file": path, "line": i,
                "issue": "img tag missing loading='lazy'",
                "suggestion": "Add loading=\"lazy\" to improve page speed.",
                "severity": "medium",
                "experiment_type": "technical",
            })
    return findings


def pdp_check_missing_alt_tags(path: str, lines: list[str]) -> list[dict]:
    findings = []
    for i, line in enumerate(lines, 1):
        if re.search(r"<img\b", line, re.IGNORECASE):
            if "alt=" not in line and ".alt" not in line:
                findings.append({
                    "scope": "pdp",
                    "file": path, "line": i,
                    "issue": "img tag missing alt attribute",
                    "suggestion": "Add alt={{ image.alt | escape }} for accessibility and SEO.",
                    "severity": "low",
                    "experiment_type": "technical",
                })
    return findings


def pdp_check_render_blocking_scripts(path: str, lines: list[str]) -> list[dict]:
    findings = []
    in_head = False
    for i, line in enumerate(lines, 1):
        if re.search(r"<head\b", line, re.IGNORECASE):
            in_head = True
        if re.search(r"</head>", line, re.IGNORECASE):
            in_head = False
        if in_head and re.search(r"<script\b", line, re.IGNORECASE):
            if "defer" not in line and "async" not in line and "application/ld+json" not in line:
                findings.append({
                    "scope": "pdp",
                    "file": path, "line": i,
                    "issue": "Render-blocking script in <head> without defer or async",
                    "suggestion": "Add defer or async to prevent blocking page render.",
                    "severity": "high",
                    "experiment_type": "technical",
                })
    return findings


def pdp_check_structured_data(path: str, lines: list[str]) -> list[dict]:
    full_text = "\n".join(lines)
    if "application/ld+json" not in full_text:
        return [{
            "scope": "pdp",
            "file": path, "line": 1,
            "issue": "No JSON-LD structured data found on product template",
            "suggestion": "Add Product schema with name, price, availability, aggregateRating.",
            "severity": "medium",
            "experiment_type": "technical",
        }]
    return []


def pdp_check_atc_button(path: str, lines: list[str]) -> list[dict]:
    full_text = "\n".join(lines)
    has_submit = bool(re.search(r'type=["\']submit["\']', full_text))
    has_atc = bool(re.search(r'add.*cart|cart.*add', full_text, re.IGNORECASE))
    if not has_submit and not has_atc:
        return [{
            "scope": "pdp",
            "file": path, "line": 1,
            "issue": "No identifiable add-to-cart button or form found",
            "suggestion": "Verify ATC button exists and is not conditionally hidden.",
            "severity": "high",
            "experiment_type": "ux",
        }]
    return []


def pdp_check_trust_signals(path: str, lines: list[str]) -> list[dict]:
    full_text = "\n".join(lines)
    findings = []
    checks = {
        "returns policy": r'return|refund|money.back',
        "secure checkout badge": r'secure|ssl|badge|trust',
        "reviews / rating": r'review|rating|star|judge\.me|yotpo|okendo|stamped',
    }
    for label, pattern in checks.items():
        if not re.search(pattern, full_text, re.IGNORECASE):
            findings.append({
                "scope": "pdp",
                "file": path, "line": 1,
                "issue": f"No {label} signals found on product template",
                "suggestion": f"Add visible {label} near the ATC button.",
                "severity": "medium",
                "experiment_type": "social_proof",
            })
    return findings


def pdp_check_value_prop(path: str, lines: list[str]) -> list[dict]:
    full_text = "\n".join(lines)
    findings = []
    if not re.search(r'usp|benefit|free.ship|shipping.free|serving|per.serve|cost.per', full_text, re.IGNORECASE):
        findings.append({
            "scope": "pdp",
            "file": path, "line": 1,
            "issue": "No USP block, value indicator, or free shipping message found on product template",
            "suggestion": "Add a value proposition block (USPs, key benefit callout, or free shipping indicator) near the buybox.",
            "severity": "medium",
            "experiment_type": "value_prop",
        })
    return findings


def pdp_check_bnpl(path: str, lines: list[str]) -> list[dict]:
    full_text = "\n".join(lines)
    if not re.search(r'afterpay|klarna|zip|laybuy|sezzle|buy.now.pay', full_text, re.IGNORECASE):
        return [{
            "scope": "pdp",
            "file": path, "line": 1,
            "issue": "No BNPL / Afterpay messaging found on product template",
            "suggestion": "Add Afterpay or Zip widget near price. Position above fold for higher AOV products.",
            "severity": "low",
            "experiment_type": "value_prop",
        }]
    return []


# ---------------------------------------------------------------------------
# Check functions — mini-cart scope (stub — add checks when activating)
# ---------------------------------------------------------------------------

def minicart_check_upsell(path: str, lines: list[str]) -> list[dict]:
    full_text = "\n".join(lines)
    if not re.search(r'upsell|cross.sell|recommend|also.like', full_text, re.IGNORECASE):
        return [{
            "scope": "mini-cart",
            "file": path, "line": 1,
            "issue": "No upsell or cross-sell section found in cart template",
            "suggestion": "Add product recommendations above the checkout button.",
            "severity": "medium",
            "experiment_type": "merchandising",
        }]
    return []


def minicart_check_free_shipping(path: str, lines: list[str]) -> list[dict]:
    full_text = "\n".join(lines)
    if not re.search(r'free.ship|shipping.free|free.deliver', full_text, re.IGNORECASE):
        return [{
            "scope": "mini-cart",
            "file": path, "line": 1,
            "issue": "No free shipping threshold messaging in cart",
            "suggestion": "Show dynamic 'Add $X more for free shipping' progress bar.",
            "severity": "medium",
            "experiment_type": "value_prop",
        }]
    return []


# ---------------------------------------------------------------------------
# Scope → checks registry
# Add new scope check lists here when activating a scope.
# ---------------------------------------------------------------------------

SCOPE_CHECKS = {
    "pdp": [
        pdp_check_missing_lazy_loading,
        pdp_check_missing_alt_tags,
        pdp_check_render_blocking_scripts,
        pdp_check_structured_data,
        pdp_check_atc_button,
        pdp_check_trust_signals,
        pdp_check_value_prop,
        pdp_check_bnpl,
    ],
    "mini-cart": [
        minicart_check_upsell,
        minicart_check_free_shipping,
        # Add more mini-cart checks here
    ],
    "collection": [
        # Stub — add checks when activating
    ],
    "homepage": [
        # Stub — add checks when activating
    ],
    "checkout": [
        # Stub — add checks when activating
    ],
}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def analyse(scope: str = "pdp", dry_run: bool = False) -> list[dict]:
    if dry_run:
        print(f"[analyse_theme] DRY RUN — skipping theme analysis (scope: {scope})")
        return []

    if scope not in SCOPE_CHECKS:
        print(f"[analyse_theme] Unknown scope '{scope}' — no checks registered")
        return []

    if not SCOPE_CHECKS[scope]:
        print(f"[analyse_theme] Scope '{scope}' is a stub — no checks defined yet")
        return []

    if not THEME_DIR or not Path(THEME_DIR).exists():
        print(f"[analyse_theme] WARNING: THEME_DIR not set or missing: '{THEME_DIR}'")
        return []

    theme_path = Path(THEME_DIR)
    all_liquid = list(theme_path.rglob("*.liquid"))
    scoped_files = [
        f for f in all_liquid
        if file_matches_scope(str(f.relative_to(theme_path)), scope)
    ]

    print(f"[analyse_theme] Scope: {scope} — {len(scoped_files)} matching files (of {len(all_liquid)} total)")

    findings = []
    checks = SCOPE_CHECKS[scope]

    for file in scoped_files:
        rel_path = str(file.relative_to(theme_path))
        try:
            lines = file.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception as e:
            print(f"[analyse_theme] Could not read {rel_path}: {e}")
            continue

        for check in checks:
            findings.extend(check(rel_path, lines))

    print(f"[analyse_theme] {len(findings)} findings in {scope} scope")
    return findings
