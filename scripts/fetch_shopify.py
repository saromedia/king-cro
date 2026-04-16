"""
fetch_shopify.py
Pulls orders, abandoned checkouts, products, and basic analytics
from the Shopify Admin API. Returns structured dicts.
"""

import os
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

SHOP_URL = os.getenv("SHOPIFY_SHOP_URL")          # e.g. mystore.myshopify.com
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2025-01")

HEADERS = {
    "X-Shopify-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json",
}


def base_url(resource: str) -> str:
    return f"https://{SHOP_URL}/admin/api/{API_VERSION}/{resource}.json"


MAX_PAGES = 500


def paginate(url: str, resource_key: str, params: dict = None) -> list:
    """Follows Shopify cursor-based pagination and returns all records."""
    results = []
    params = params or {}
    params["limit"] = 250
    page = 0

    while url:
        page += 1
        if page > MAX_PAGES:
            print(f"[fetch_shopify] WARNING: Pagination hit {MAX_PAGES}-page safety limit for {resource_key}, stopping")
            break

        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get(resource_key, []))

        # Cursor pagination via Link header
        link = resp.headers.get("Link", "")
        url = None
        params = {}  # params are baked into next URL
        for part in link.split(","):
            if 'rel="next"' in part:
                url = part.strip().split(";")[0].strip("<> ")
                break

    return results


def fetch_orders(days: int = 30) -> list[dict]:
    """Returns orders from the last `days` days."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    orders = paginate(
        base_url("orders"),
        "orders",
        {"status": "any", "created_at_min": since, "fields": "id,created_at,total_price,subtotal_price,financial_status,fulfillment_status,line_items,customer,discount_codes,refunds"},
    )
    return orders


def fetch_abandoned_checkouts(days: int = 30) -> list[dict]:
    """Returns abandoned checkouts from the last `days` days."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    checkouts = paginate(
        base_url("checkouts"),
        "checkouts",
        {"created_at_min": since},
    )
    return checkouts


def fetch_products() -> list[dict]:
    """Returns all products with description length, image count, variant inventory."""
    raw = paginate(
        base_url("products"),
        "products",
        {"fields": "id,title,body_html,images,variants,status"},
    )
    products = []
    for p in raw:
        desc = p.get("body_html") or ""
        # Strip basic HTML tags for word count
        import re
        clean = re.sub(r"<[^>]+>", " ", desc)
        words = len(clean.split())
        products.append({
            "id": p["id"],
            "title": p["title"],
            "status": p.get("status"),
            "description_word_count": words,
            "image_count": len(p.get("images", [])),
            "variants": [
                {
                    "id": v["id"],
                    "title": v["title"],
                    "inventory_quantity": v.get("inventory_quantity", 0),
                    "available": v.get("inventory_quantity", 0) > 0,
                }
                for v in p.get("variants", [])
            ],
            "has_thin_description": words < 80,
            "has_few_images": len(p.get("images", [])) < 3,
            "has_all_variants_oos": all(
                v.get("inventory_quantity", 0) <= 0 for v in p.get("variants", [])
            ),
        })
    return products


def compute_metrics(orders: list[dict], abandoned: list[dict]) -> dict:
    """
    Derives conversion metrics from raw order and checkout data.
    Note: Shopify does not expose session counts via the Admin REST API.
    Session data requires the Analytics API (GraphQL) or manual export.
    This function computes what it can and flags what's missing.
    """
    total_orders = len(orders)
    total_revenue = sum(float(o.get("total_price", 0)) for o in orders)
    aov = total_revenue / total_orders if total_orders else 0

    total_abandoned = len(abandoned)
    cart_abandonment_rate = (
        total_abandoned / (total_abandoned + total_orders)
        if (total_abandoned + total_orders) > 0
        else None
    )

    refunded_orders = [o for o in orders if o.get("financial_status") == "refunded"]
    refund_rate = len(refunded_orders) / total_orders if total_orders else 0

    # Repeat customers: customers with more than 1 order in dataset
    from collections import Counter
    customer_ids = [o["customer"]["id"] for o in orders if o.get("customer")]
    customer_order_counts = Counter(customer_ids)
    repeat_customers = sum(1 for count in customer_order_counts.values() if count > 1)
    repeat_customer_rate = repeat_customers / len(customer_order_counts) if customer_order_counts else 0

    # Discount usage
    orders_with_discount = [o for o in orders if o.get("discount_codes")]
    discount_usage_rate = len(orders_with_discount) / total_orders if total_orders else 0

    return {
        "period_days": 30,
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "aov": round(aov, 2),
        "total_abandoned_checkouts": total_abandoned,
        "cart_abandonment_rate": round(cart_abandonment_rate, 4) if cart_abandonment_rate else None,
        "refund_rate": round(refund_rate, 4),
        "repeat_customer_rate": round(repeat_customer_rate, 4),
        "discount_usage_rate": round(discount_usage_rate, 4),
        "sessions": None,  # Requires GraphQL Analytics API — see README
        "conversion_rate": None,  # Cannot compute without session data
        "note": "Session and conversion rate data requires Shopify GraphQL Analytics API. See README for setup.",
    }


def fetch_all(dry_run: bool = False) -> dict:
    """Main entry point. Returns all fetched data."""
    if dry_run:
        print("[fetch_shopify] DRY RUN — skipping API calls")
        return {
            "orders": [],
            "abandoned_checkouts": [],
            "products": [],
            "metrics": {"dry_run": True},
        }

    print("[fetch_shopify] Fetching orders...")
    orders = fetch_orders()
    print(f"[fetch_shopify] {len(orders)} orders fetched")

    print("[fetch_shopify] Fetching abandoned checkouts...")
    abandoned = fetch_abandoned_checkouts()
    print(f"[fetch_shopify] {len(abandoned)} abandoned checkouts fetched")

    print("[fetch_shopify] Fetching products...")
    products = fetch_products()
    print(f"[fetch_shopify] {len(products)} products fetched")

    metrics = compute_metrics(orders, abandoned)

    return {
        "orders": orders,
        "abandoned_checkouts": abandoned,
        "products": products,
        "metrics": metrics,
    }
