"""
Main Stock Agent that orchestrates all components.
"""

import config
from price_monitor import PriceMonitor
from news_fetcher import NewsFetcher, TickerReport
from ai_summarizer import build_morning_digest, build_alert_message
from email_sender import EmailSender


class StockAgent:
    """Orchestrates price monitoring, news fetching, and notifications."""

    def __init__(self):
        # Initialize price monitor
        self.price_monitor = PriceMonitor(
            tickers=config.WATCHLIST,
            threshold_pct=config.PRICE_CHANGE_THRESHOLD,
        )

        # Initialize news fetcher
        self.news_fetcher = NewsFetcher(
            tickers=config.WATCHLIST,
            news_api_key=config.NEWS_API_KEY,
        )

        # Initialize email sender
        self.email = EmailSender(
            smtp_email=config.SMTP_EMAIL,
            smtp_password=config.SMTP_PASSWORD,
            to_email=config.EMAIL_TO,
        )

        # Store config for later use
        self.api_key = config.ANTHROPIC_API_KEY
        self.watchlist = config.WATCHLIST

    def check_price_alerts(self) -> None:
        """
        Check for price alerts and send email for each trigger.
        """
        alerts = self.price_monitor.check_alerts()

        for snap in alerts:
            message = build_alert_message(
                ticker=snap.ticker,
                change_pct=snap.change_pct,
                price=snap.price,
                prev_close=snap.prev_close,
            )
            self.email.send_alert(snap.ticker, message)
            print(f"Alert sent for {snap.ticker}: {snap.change_pct:+.2f}%")

    def send_morning_report(self) -> None:
        """
        Generate and send the morning briefing report.
        Fetches prices, news, builds AI digest, and sends via email.
        """
        print("Fetching prices...")
        price_lines = self.price_monitor.morning_summary_lines()

        print("Fetching news and financial data...")
        reports_by_ticker = self.news_fetcher.fetch_all(days_back=1)

        # Convert TickerReport to legacy format for ai_summarizer compatibility
        news_by_ticker = self._extract_news_from_reports(reports_by_ticker)

        print("Generating AI digest...")
        digest = build_morning_digest(
            price_lines=price_lines,
            news_by_ticker=news_by_ticker,
            api_key=self.api_key,
            watchlist=self.watchlist,
        )

        print("Sending morning report...")
        success = self.email.send_morning_report(digest)

        if success:
            print("Morning report sent successfully!")
        else:
            print("Failed to send morning report")

    def _extract_news_from_reports(
        self, reports: dict[str, TickerReport]
    ) -> dict[str, list]:
        """
        Extract news items from TickerReports for backward compatibility.
        """
        result = {}
        for ticker, report in reports.items():
            all_news = report.all_news
            if all_news:
                result[ticker] = all_news
        return result
