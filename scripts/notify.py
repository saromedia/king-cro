"""
notify.py
Sends Slack and optional email notifications with the weekly CRO digest.
"""

import os
import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date
from dotenv import load_dotenv

load_dotenv()

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL", "")


def send_slack(top_findings: list[dict], metrics: dict, report_date: str, dry_run: bool = False) -> None:
    if not SLACK_WEBHOOK_URL:
        print("[notify] SLACK_WEBHOOK_URL not set — skipping Slack")
        return

    cart_rate = metrics.get("cart_abandonment_rate")
    aov = metrics.get("aov")
    orders = metrics.get("total_orders")

    summary_lines = [
        f"*Shopify CRO Weekly — {report_date}*",
        f"Orders (30d): {orders} | AOV: ${aov} | Cart abandonment: {f'{cart_rate:.1%}' if cart_rate else 'n/a'}",
        "",
        "*Top findings this week:*",
    ]

    for i, f in enumerate(top_findings[:5], 1):
        location = f.get("file", "")
        if f.get("line"):
            location += f":{f['line']}"
        summary_lines.append(
            f"{i}. [ICE {f['ice_score']}] {f['issue']} — _{location}_"
        )

    summary_lines.append(f"\nFull report: `reports/{report_date}.md`")

    payload = {"text": "\n".join(summary_lines)}

    if dry_run:
        print("[notify] DRY RUN — Slack payload:")
        print(json.dumps(payload, indent=2))
        return

    resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
    if resp.status_code == 200:
        print("[notify] Slack message sent")
    else:
        print(f"[notify] Slack error {resp.status_code}: {resp.text}")


def send_email(top_findings: list[dict], metrics: dict, report_date: str, report_md: str, dry_run: bool = False) -> None:
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASS, NOTIFY_EMAIL]):
        print("[notify] SMTP config incomplete — skipping email")
        return

    cart_rate = metrics.get("cart_abandonment_rate")
    aov = metrics.get("aov")
    orders = metrics.get("total_orders")

    body_lines = [
        f"Shopify CRO Weekly — {report_date}",
        f"Orders (30d): {orders} | AOV: ${aov} | Cart abandonment: {f'{cart_rate:.1%}' if cart_rate else 'n/a'}",
        "",
        "Top findings:",
    ]

    for i, f in enumerate(top_findings[:5], 1):
        location = f.get("file", "")
        if f.get("line"):
            location += f":{f['line']}"
        body_lines.append(f"  {i}. [ICE {f['ice_score']}] {f['issue']} ({location})")

    body_lines += ["", "— Full report attached as text below —", "", report_md]

    msg = MIMEMultipart()
    msg["Subject"] = f"CRO Weekly Digest — {report_date}"
    msg["From"] = SMTP_USER
    msg["To"] = NOTIFY_EMAIL
    msg.attach(MIMEText("\n".join(body_lines), "plain"))

    if dry_run:
        print("[notify] DRY RUN — would send email to:", NOTIFY_EMAIL)
        return

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        print(f"[notify] Email sent to {NOTIFY_EMAIL}")
    except Exception as e:
        print(f"[notify] Email error: {e}")
