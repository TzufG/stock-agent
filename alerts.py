"""
WhatsApp alert system using Twilio.
Tracks price baselines and sends alerts when thresholds are breached.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict

from twilio.rest import Client

from config import Config
from data_fetchers import PriceData, fetch_price


# File to persist alert baselines between runs
BASELINES_FILE = Path(__file__).parent / "baselines.json"


@dataclass
class AlertBaseline:
    """Tracks the baseline price for alert calculations."""
    ticker: str
    baseline_price: float
    last_alert_time: str
    last_alert_price: float


class AlertManager:
    """Manages price alerts and WhatsApp notifications."""

    def __init__(self):
        self.baselines: dict[str, AlertBaseline] = {}
        self.twilio_client: Optional[Client] = None
        self._load_baselines()
        self._init_twilio()

    def _init_twilio(self) -> None:
        """Initialize Twilio client if credentials are available."""
        if Config.TWILIO_ACCOUNT_SID and Config.TWILIO_AUTH_TOKEN:
            try:
                self.twilio_client = Client(
                    Config.TWILIO_ACCOUNT_SID,
                    Config.TWILIO_AUTH_TOKEN
                )
            except Exception as e:
                print(f"Error initializing Twilio client: {e}")
                self.twilio_client = None

    def _load_baselines(self) -> None:
        """Load alert baselines from disk."""
        if BASELINES_FILE.exists():
            try:
                with open(BASELINES_FILE, "r") as f:
                    data = json.load(f)
                    for ticker, baseline_data in data.items():
                        self.baselines[ticker] = AlertBaseline(**baseline_data)
            except Exception as e:
                print(f"Error loading baselines: {e}")
                self.baselines = {}

    def _save_baselines(self) -> None:
        """Save alert baselines to disk."""
        try:
            data = {ticker: asdict(baseline) for ticker, baseline in self.baselines.items()}
            with open(BASELINES_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving baselines: {e}")

    def get_baseline(self, ticker: str) -> Optional[AlertBaseline]:
        """Get the current baseline for a ticker."""
        return self.baselines.get(ticker.upper())

    def set_baseline(self, ticker: str, price: float) -> None:
        """Set a new baseline for a ticker (after sending an alert)."""
        ticker = ticker.upper()
        now = datetime.now().isoformat()

        self.baselines[ticker] = AlertBaseline(
            ticker=ticker,
            baseline_price=price,
            last_alert_time=now,
            last_alert_price=price,
        )
        self._save_baselines()

    def calculate_change_from_baseline(self, ticker: str, current_price: float) -> Optional[float]:
        """
        Calculate percentage change from the alert baseline.
        Returns None if no baseline exists.
        """
        baseline = self.get_baseline(ticker)
        if not baseline:
            return None

        if baseline.baseline_price == 0:
            return None

        return ((current_price - baseline.baseline_price) / baseline.baseline_price) * 100

    def check_and_alert(self, price_data: PriceData) -> bool:
        """
        Check if the price has moved enough from baseline to trigger an alert.
        If so, send the alert and update the baseline.
        Returns True if an alert was sent.
        """
        ticker = price_data.ticker.upper()
        current_price = price_data.current_price

        # If no baseline exists, set the current price as baseline
        baseline = self.get_baseline(ticker)
        if not baseline:
            self.set_baseline(ticker, current_price)
            print(f"[{ticker}] Initialized baseline at ${current_price:.2f}")
            return False

        # Calculate change from baseline
        change_pct = self.calculate_change_from_baseline(ticker, current_price)
        if change_pct is None:
            return False

        # Check if threshold is breached
        if abs(change_pct) >= Config.PRICE_ALERT_THRESHOLD:
            # Send alert
            direction = "UP" if change_pct > 0 else "DOWN"
            message = self._format_price_alert(price_data, baseline, change_pct, direction)

            success = self.send_whatsapp(message)

            if success:
                # Update baseline to current price
                self.set_baseline(ticker, current_price)
                print(f"[{ticker}] Alert sent! {direction} {abs(change_pct):.2f}% to ${current_price:.2f}")
                return True
            else:
                print(f"[{ticker}] Alert threshold breached but failed to send WhatsApp")
                return False

        return False

    def _format_price_alert(
        self,
        price_data: PriceData,
        baseline: AlertBaseline,
        change_pct: float,
        direction: str
    ) -> str:
        """Format a price alert message."""
        emoji = "\U0001F7E2" if direction == "UP" else "\U0001F534"  # Green/Red circle
        arrow = "\u2B06\uFE0F" if direction == "UP" else "\u2B07\uFE0F"  # Up/Down arrow

        name = price_data.name or price_data.ticker

        message = f"""
{emoji} *PRICE ALERT* {emoji}

*{name}* ({price_data.ticker}) {arrow}

Current: *${price_data.current_price:.2f}*
Baseline: ${baseline.baseline_price:.2f}
Change: {'+' if change_pct > 0 else ''}{change_pct:.2f}%

Day Range: ${price_data.day_low:.2f} - ${price_data.day_high:.2f}
Volume: {price_data.volume:,}

_Alert triggered at {datetime.now().strftime('%H:%M:%S')}_
""".strip()

        return message

    def send_whatsapp(self, message: str) -> bool:
        """
        Send a WhatsApp message via Twilio.
        Returns True if successful.
        """
        if not self.twilio_client:
            print("Twilio client not initialized - cannot send WhatsApp")
            return False

        if not Config.TWILIO_WHATSAPP_FROM or not Config.TWILIO_WHATSAPP_TO:
            print("WhatsApp numbers not configured")
            return False

        try:
            msg = self.twilio_client.messages.create(
                body=message,
                from_=Config.TWILIO_WHATSAPP_FROM,
                to=Config.TWILIO_WHATSAPP_TO
            )
            print(f"WhatsApp sent successfully (SID: {msg.sid})")
            return True
        except Exception as e:
            print(f"Error sending WhatsApp: {e}")
            return False

    def check_all_tickers(self, tickers: list[str]) -> list[str]:
        """
        Check all tickers for price alerts.
        Returns list of tickers that triggered alerts.
        """
        alerted = []

        for ticker in tickers:
            price_data = fetch_price(ticker)
            if price_data:
                if self.check_and_alert(price_data):
                    alerted.append(ticker)
            else:
                print(f"[{ticker}] Could not fetch price data")

        return alerted

    def reset_baseline(self, ticker: str) -> None:
        """Reset the baseline for a ticker (will be reinitialized on next check)."""
        ticker = ticker.upper()
        if ticker in self.baselines:
            del self.baselines[ticker]
            self._save_baselines()
            print(f"[{ticker}] Baseline reset")

    def reset_all_baselines(self) -> None:
        """Reset all baselines."""
        self.baselines = {}
        self._save_baselines()
        print("All baselines reset")


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get or create the global AlertManager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def check_price_alerts(tickers: Optional[list[str]] = None) -> list[str]:
    """
    Convenience function to check price alerts for tickers.
    Uses watchlist from config if tickers not provided.
    """
    if tickers is None:
        tickers = Config.WATCHLIST

    manager = get_alert_manager()
    return manager.check_all_tickers(tickers)


def send_whatsapp_message(message: str) -> bool:
    """Convenience function to send a WhatsApp message."""
    manager = get_alert_manager()
    return manager.send_whatsapp(message)
