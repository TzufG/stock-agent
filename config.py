"""
Configuration management for Stock Agent.
Loads settings from environment variables.
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env file from the same directory as this script
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)


def get_list(key: str, default: str = "") -> list[str]:
    """Parse a comma-separated env var into a list of strings."""
    value = os.getenv(key, default)
    if not value:
        return []
    return [item.strip().upper() for item in value.split(",") if item.strip()]


# Anthropic
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

# Email (Gmail)
SMTP_EMAIL: str = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
EMAIL_TO: str = os.getenv("EMAIL_TO", "")

# NewsAPI (optional)
NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")

# Watchlist
WATCHLIST: list[str] = get_list("WATCHLIST", "SPY,QQQ")

# Alert settings
PRICE_CHANGE_THRESHOLD: float = float(os.getenv("PRICE_CHANGE_THRESHOLD", "3.0"))

# Scheduling
MORNING_REPORT_TIME: str = os.getenv("MORNING_REPORT_TIME", "07:30")
PRICE_CHECK_INTERVAL_MINUTES: int = int(os.getenv("PRICE_CHECK_INTERVAL_MINUTES", "15"))
