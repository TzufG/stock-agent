"""
Configuration management for Stock Agent.
Loads settings from environment variables with sensible defaults.
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
    return [item.strip() for item in value.split(",") if item.strip()]


class Config:
    """Central configuration for the stock agent."""

    # Watchlist
    WATCHLIST: list[str] = get_list("WATCHLIST", "SPY,QQQ")

    # Alert settings
    PRICE_ALERT_THRESHOLD: float = float(os.getenv("PRICE_ALERT_THRESHOLD", "3"))
    PRICE_CHECK_INTERVAL: int = int(os.getenv("PRICE_CHECK_INTERVAL", "15"))

    # Daily briefing
    DAILY_BRIEFING_TIME: str = os.getenv("DAILY_BRIEFING_TIME", "08:00")

    # Twilio (WhatsApp)
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_WHATSAPP_FROM: str = os.getenv("TWILIO_WHATSAPP_FROM", "")
    TWILIO_WHATSAPP_TO: str = os.getenv("TWILIO_WHATSAPP_TO", "")

    # NewsAPI
    NEWSAPI_KEY: str = os.getenv("NEWSAPI_KEY", "")

    # Anthropic
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

    @classmethod
    def validate(cls) -> list[str]:
        """
        Validate that required configuration is present.
        Returns a list of missing/invalid config items.
        """
        issues = []

        if not cls.WATCHLIST:
            issues.append("WATCHLIST is empty - add at least one ticker")

        if not cls.TWILIO_ACCOUNT_SID:
            issues.append("TWILIO_ACCOUNT_SID is required for WhatsApp alerts")
        if not cls.TWILIO_AUTH_TOKEN:
            issues.append("TWILIO_AUTH_TOKEN is required for WhatsApp alerts")
        if not cls.TWILIO_WHATSAPP_FROM:
            issues.append("TWILIO_WHATSAPP_FROM is required for WhatsApp alerts")
        if not cls.TWILIO_WHATSAPP_TO:
            issues.append("TWILIO_WHATSAPP_TO is required for WhatsApp alerts")

        if not cls.ANTHROPIC_API_KEY:
            issues.append("ANTHROPIC_API_KEY is required for AI digest generation")

        # NewsAPI is optional but we'll warn if missing
        if not cls.NEWSAPI_KEY:
            issues.append("NEWSAPI_KEY is missing - news from NewsAPI will be unavailable")

        return issues

    @classmethod
    def print_config(cls) -> None:
        """Print current configuration (masking sensitive values)."""
        print("=" * 50)
        print("Stock Agent Configuration")
        print("=" * 50)
        print(f"Watchlist: {', '.join(cls.WATCHLIST)}")
        print(f"Price alert threshold: {cls.PRICE_ALERT_THRESHOLD}%")
        print(f"Price check interval: {cls.PRICE_CHECK_INTERVAL} minutes")
        print(f"Daily briefing time: {cls.DAILY_BRIEFING_TIME}")
        print(f"Claude model: {cls.CLAUDE_MODEL}")
        print(f"Twilio configured: {bool(cls.TWILIO_ACCOUNT_SID and cls.TWILIO_AUTH_TOKEN)}")
        print(f"NewsAPI configured: {bool(cls.NEWSAPI_KEY)}")
        print(f"Anthropic configured: {bool(cls.ANTHROPIC_API_KEY)}")
        print("=" * 50)
