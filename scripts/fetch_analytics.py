"""
fetch_analytics.py
Pulls session and conversion rate data from the Shopify GraphQL Admin API.
The REST API does not expose session data — this requires GraphQL.

Requires the same SHOPIFY_SHOP_URL and SHOPIFY_ACCESS_TOKEN as fetch_shopify.py,
plus the read_analytics scope on your custom app.
"""

import os
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

SHOP_URL = os.getenv("SHOPIFY_SHOP_URL")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2025-01")

GRAPHQL_URL = f"https://{SHOP_URL}/admin/api/{API_VERSION}/graphql.json"

HEADERS = {
    "X-Shopify-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json",
}


def _date_range(days: int = 30) -> tuple[str, str]:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()


def fetch_sessions_and_cvr(days: int = 30) -> dict:
    """
    Queries the ShopifyQL analytics endpoint for sessions and conversion rate.
    Returns a dict with total_sessions, converted_sessions, conversion_rate,
    and a device breakdown if available.
    """
    start, end = _date_range(days)

    # ShopifyQL query for sessions overview
    query = """
    query {
      shopifyqlQuery(
        query: "FROM sessions SINCE %s UNTIL %s SHOW sessions, converted_sessions, conversion_rate ORDER BY day"
      ) {
        ... on TableResponse {
          tableData {
            rowData
            columns {
              name
              dataType
            }
          }
        }
        parseErrors {
          code
          message
        }
      }
    }
    """ % (start, end)

    try:
        resp = requests.post(
            GRAPHQL_URL,
            headers=HEADERS,
            json={"query": query},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {
            "error": str(e),
            "total_sessions": None,
            "converted_sessions": None,
            "conversion_rate": None,
        }

    errors = data.get("errors") or []
    if errors:
        return {
            "error": str(errors),
            "total_sessions": None,
            "converted_sessions": None,
            "conversion_rate": None,
        }

    query_result = (data.get("data") or {}).get("shopifyqlQuery", {})
    parse_errors = query_result.get("parseErrors", [])
    if parse_errors:
        # read_analytics scope may not be enabled
        return {
            "error": f"ShopifyQL parse error: {parse_errors}",
            "total_sessions": None,
            "converted_sessions": None,
            "conversion_rate": None,
            "note": "Ensure read_analytics scope is enabled on your Shopify custom app.",
        }

    table = (query_result.get("tableData") or {})
    columns = [c["name"] for c in table.get("columns", [])]
    rows = table.get("rowData", [])

    if not columns or not rows:
        return {
            "total_sessions": None,
            "converted_sessions": None,
            "conversion_rate": None,
            "note": "No analytics data returned. Check date range and app scopes.",
        }

    # Aggregate totals across all days
    try:
        sessions_idx = columns.index("sessions")
        converted_idx = columns.index("converted_sessions")
        cvr_idx = columns.index("conversion_rate")
    except ValueError:
        return {
            "error": f"Unexpected columns: {columns}",
            "total_sessions": None,
            "converted_sessions": None,
            "conversion_rate": None,
        }

    total_sessions = sum(int(row[sessions_idx] or 0) for row in rows)
    total_converted = sum(int(row[converted_idx] or 0) for row in rows)
    avg_cvr = total_converted / total_sessions if total_sessions else 0

    return {
        "total_sessions": total_sessions,
        "converted_sessions": total_converted,
        "conversion_rate": round(avg_cvr, 4),
        "period_days": days,
        "daily_rows": [
            {col: row[i] for i, col in enumerate(columns)}
            for row in rows
        ],
    }


def fetch_device_breakdown(days: int = 30) -> dict:
    """
    Pulls session and conversion rate split by device type.
    Useful for flagging mobile vs desktop CVR gaps.
    """
    start, end = _date_range(days)

    query = """
    query {
      shopifyqlQuery(
        query: "FROM sessions SINCE %s UNTIL %s SHOW sessions, conversion_rate GROUP BY device_type"
      ) {
        ... on TableResponse {
          tableData {
            rowData
            columns {
              name
              dataType
            }
          }
        }
        parseErrors {
          code
          message
        }
      }
    }
    """ % (start, end)

    try:
        resp = requests.post(
            GRAPHQL_URL,
            headers=HEADERS,
            json={"query": query},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"error": str(e), "breakdown": []}

    query_result = (data.get("data") or {}).get("shopifyqlQuery", {})
    table = (query_result.get("tableData") or {})
    columns = [c["name"] for c in table.get("columns", [])]
    rows = table.get("rowData", [])

    if not columns or not rows:
        return {"breakdown": []}

    breakdown = [
        {col: row[i] for i, col in enumerate(columns)}
        for row in rows
    ]

    # Flag mobile/desktop gap
    result = {"breakdown": breakdown, "gap_flagged": False, "gap_note": None}
    try:
        device_map = {row.get("device_type", "").lower(): row for row in breakdown}
        mobile_cvr = float(device_map.get("mobile", {}).get("conversion_rate", 0) or 0)
        desktop_cvr = float(device_map.get("desktop", {}).get("conversion_rate", 1) or 1)
        if desktop_cvr > 0:
            gap_pct = (desktop_cvr - mobile_cvr) / desktop_cvr
            if gap_pct > 0.30:
                result["gap_flagged"] = True
                result["gap_note"] = (
                    f"Mobile CVR ({mobile_cvr:.1%}) is {gap_pct:.0%} below "
                    f"desktop CVR ({desktop_cvr:.1%}) — exceeds 30% threshold"
                )
    except Exception:
        pass

    return result


def fetch_all_analytics(dry_run: bool = False) -> dict:
    if dry_run:
        print("[fetch_analytics] DRY RUN — skipping analytics API calls")
        return {
            "sessions": {"dry_run": True},
            "device_breakdown": {"dry_run": True},
        }

    print("[fetch_analytics] Fetching sessions and CVR via GraphQL...")
    sessions = fetch_sessions_and_cvr()
    if sessions.get("error"):
        print(f"[fetch_analytics] Sessions error: {sessions['error']}")
    else:
        print(f"[fetch_analytics] Sessions: {sessions.get('total_sessions')} | CVR: {sessions.get('conversion_rate')}")

    print("[fetch_analytics] Fetching device breakdown...")
    devices = fetch_device_breakdown()
    if devices.get("gap_flagged"):
        print(f"[fetch_analytics] WARNING: {devices['gap_note']}")

    return {
        "sessions": sessions,
        "device_breakdown": devices,
    }
