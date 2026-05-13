"""
utils.py
Shared helpers used by multiple scripts.
"""

from datetime import date


def fmt_date(d=None) -> str:
    """Format a date as DD-MM-YYYY. Defaults to today."""
    d = d or date.today()
    return d.strftime("%d-%m-%Y")
