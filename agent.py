"""
Main Stock Agent that orchestrates all components.
"""

import config
from price_monitor import PriceMonitor
from news_fetcher import NewsFetcher
from ai_summarizer import build_morning_digest, build_alert_message
from whatsapp_sender import WhatsAppSender


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

        # Initialize WhatsApp sender
        self.whatsapp = WhatsAppSender(
            account_sid=config.TWILIO_ACCOUNT_SID,
            auth_token=config.TWILIO_AUTH_TOKEN,
            from_number=config.TWILIO_WHATSAPP_FROM,
            to_number=config.WHATSAPP_TO,
        )

        # Store config for later use
        self.api_key = config.ANTHROPIC_API_KEY
        self.watchlist = config.WATCHLIST

    def check_price_alerts(self) -> None:
        """
        Check for price alerts and send WhatsApp message for each trigger.
        """
        alerts = self.price_monitor.check_alerts()

        for snap in alerts:
            message = build_alert_message(
                ticker=snap.ticker,
                change_pct=snap.change_pct,
                price=snap.price,
                prev_close=snap.prev_close,
            )
            self.whatsapp.send(message)
            print(f"Alert sent for {snap.ticker}: {snap.change_pct:+.2f}%")

    def send_morning_report(self) -> None:
        """
        Generate and send the morning briefing report.
        Fetches prices, news, builds AI digest, and sends via WhatsApp.
        """
        print("Fetching prices...")
        price_lines = self.price_monitor.morning_summary_lines()

        print("Fetching news...")
        news_by_ticker = self.news_fetcher.fetch_all(days_back=1)

        print("Generating AI digest...")
        digest = build_morning_digest(
            price_lines=price_lines,
            news_by_ticker=news_by_ticker,
            api_key=self.api_key,
            watchlist=self.watchlist,
        )

        print("Sending morning report...")
        success = self.whatsapp.send_chunks(digest)

        if success:
            print("Morning report sent successfully!")
        else:
            print("Failed to send morning report")
