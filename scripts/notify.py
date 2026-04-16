"""
notify.py
Sends Slack and optional email notifications with the weekly CRO digest.

Slack supports two modes:
  1. Incoming webhook (posts to a channel — use a private channel for DM-like behaviour)
  2. Bot token + user ID (sends a real DM via the Slack API)
If both are configured, bot token takes priority.
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
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_DM_USER_ID = os.getenv("SLACK_DM_USER_ID", "")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL", "")


def _build_slack_message(top_findings: list[dict], metrics: dict, report_date: str) -> str:
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

    return "\n".join(summary_lines)


def _send_slack_dm(text: str, dry_run: bool = False) -> None:
    """Send a real DM via the Slack API using a bot token."""
    if dry_run:
        print(f"[notify] DRY RUN — would DM Slack user {SLACK_DM_USER_ID}")
        return

    try:
        resp = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            json={"channel": SLACK_DM_USER_ID, "text": text},
            timeout=10,
        )
        data = resp.json()
        if data.get("ok"):
            print("[notify] Slack DM sent")
        else:
            print(f"[notify] Slack DM failed: {data.get('error', 'unknown')}")
    except Exception as e:
        print(f"[notify] Slack DM delivery failed: {e}")


def _send_slack_webhook(text: str, dry_run: bool = False) -> None:
    """Send a message via an incoming webhook (posts to a channel)."""
    payload = {"text": text}

    if dry_run:
        print("[notify] DRY RUN — Slack webhook payload:")
        print(json.dumps(payload, indent=2))
        return

    try:
        resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        if resp.status_code == 200:
            print("[notify] Slack message sent")
        else:
            print(f"[notify] Slack error {resp.status_code}")
    except Exception as e:
        print(f"[notify] Slack delivery failed: {e}")


def send_slack(top_findings: list[dict], metrics: dict, report_date: str, dry_run: bool = False) -> None:
    # Bot token DM takes priority over webhook
    if SLACK_BOT_TOKEN and SLACK_DM_USER_ID:
        text = _build_slack_message(top_findings, metrics, report_date)
        _send_slack_dm(text, dry_run=dry_run)
    elif SLACK_WEBHOOK_URL:
        text = _build_slack_message(top_findings, metrics, report_date)
        _send_slack_webhook(text, dry_run=dry_run)
    else:
        print("[notify] No Slack config set — skipping Slack")


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
    except Exception:
        print("[notify] Email delivery failed — check SMTP configuration")
