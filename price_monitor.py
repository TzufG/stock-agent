"""
Price monitoring with threshold-based alerts.
"""

import yfinance as yf
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class PriceSnapshot:
    """Container for a price snapshot."""
    ticker: str
    price: float
    prev_close: float
    change_pct: float
    direction: str  # "up" or "down"
    timestamp: datetime


class PriceMonitor:
    """Monitors prices and detects threshold breaches."""

    def __init__(self, tickers: list[str], threshold_pct: float):
        self.tickers = [t.upper() for t in tickers]
        self.threshold_pct = threshold_pct
        # Track last alert price per ticker to avoid duplicate alerts
        self.last_alert_price: dict[str, float] = {}

    def fetch_all(self) -> list[PriceSnapshot]:
        """
        Fetch current prices for all tickers.
        Uses yfinance period="2d" interval="1d" to get current and previous close.
        """
        snapshots = []
        now = datetime.now()

        for ticker in self.tickers:
            snapshot = self._fetch_ticker(ticker, now)
            if snapshot:
                snapshots.append(snapshot)

        return snapshots

    def _fetch_ticker(self, ticker: str, timestamp: datetime) -> Optional[PriceSnapshot]:
        """Fetch price data for a single ticker."""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2d", interval="1d")

            if len(hist) < 1:
                return None

            # Current price is the last close
            price = float(hist["Close"].iloc[-1])

            # Previous close
            if len(hist) >= 2:
                prev_close = float(hist["Close"].iloc[-2])
            else:
                prev_close = price

            # Calculate change
            if prev_close > 0:
                change_pct = ((price - prev_close) / prev_close) * 100
            else:
                change_pct = 0.0

            direction = "up" if change_pct >= 0 else "down"

            return PriceSnapshot(
                ticker=ticker,
                price=round(price, 2),
                prev_close=round(prev_close, 2),
                change_pct=round(change_pct, 2),
                direction=direction,
                timestamp=timestamp,
            )
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            return None

    def check_alerts(self) -> list[PriceSnapshot]:
        """
        Check all tickers and return those that moved >= threshold since last alert.
        Updates last_alert_price on trigger.
        """
        snapshots = self.fetch_all()
        alerts = []

        for snap in snapshots:
            # Get the baseline price (last alert price or previous close)
            baseline = self.last_alert_price.get(snap.ticker, snap.prev_close)

            if baseline <= 0:
                # Initialize baseline
                self.last_alert_price[snap.ticker] = snap.price
                continue

            # Calculate change from baseline
            change_from_baseline = ((snap.price - baseline) / baseline) * 100

            if abs(change_from_baseline) >= self.threshold_pct:
                # Update the snapshot's change_pct to reflect change from baseline
                snap.change_pct = round(change_from_baseline, 2)
                snap.direction = "up" if change_from_baseline >= 0 else "down"

                # Update last alert price
                self.last_alert_price[snap.ticker] = snap.price

                alerts.append(snap)

        return alerts

    def morning_summary_lines(self) -> list[str]:
        """
        Generate formatted one-liner per ticker for morning summary.
        """
        snapshots = self.fetch_all()
        lines = []

        for snap in snapshots:
            emoji = "\u2B06\uFE0F" if snap.direction == "up" else "\u2B07\uFE0F"
            sign = "+" if snap.change_pct >= 0 else ""
            line = f"{snap.ticker}: ${snap.price:.2f} ({sign}{snap.change_pct:.2f}%) {emoji}"
            lines.append(line)

        return lines
