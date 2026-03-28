#!/usr/bin/env python3
"""
Stock Agent - AI-powered stock monitoring with WhatsApp alerts.
"""

import logging
import time
import signal
import sys

import schedule

import config
from agent import StockAgent


# Set up logging to both stdout and file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("agent.log"),
    ],
)
logger = logging.getLogger(__name__)

# Flag for graceful shutdown
running = True


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global running
    logger.info("Shutdown signal received, stopping...")
    running = False


def main():
    """Main entry point."""
    global running

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("=" * 50)
    logger.info("STOCK AGENT STARTING")
    logger.info("=" * 50)
    logger.info(f"Watchlist: {', '.join(config.WATCHLIST)}")
    logger.info(f"Price threshold: {config.PRICE_CHANGE_THRESHOLD}%")
    logger.info(f"Check interval: {config.PRICE_CHECK_INTERVAL_MINUTES} minutes")
    logger.info(f"Morning report time: {config.MORNING_REPORT_TIME}")

    # Initialize agent
    agent = StockAgent()

    # Schedule morning report
    schedule.every().day.at(config.MORNING_REPORT_TIME).do(
        lambda: _run_job("morning_report", agent.send_morning_report)
    )
    logger.info(f"Scheduled: Morning report at {config.MORNING_REPORT_TIME}")

    # Schedule price checks
    schedule.every(config.PRICE_CHECK_INTERVAL_MINUTES).minutes.do(
        lambda: _run_job("price_check", agent.check_price_alerts)
    )
    logger.info(f"Scheduled: Price check every {config.PRICE_CHECK_INTERVAL_MINUTES} minutes")

    # Send morning report immediately on startup
    logger.info("Sending initial morning report...")
    _run_job("morning_report", agent.send_morning_report)

    logger.info("Agent is running. Press Ctrl+C to stop.")

    # Main loop
    while running:
        schedule.run_pending()
        time.sleep(30)

    logger.info("Agent stopped.")


def _run_job(name: str, func) -> None:
    """Run a job with error handling and logging."""
    try:
        logger.info(f"Running job: {name}")
        func()
        logger.info(f"Job completed: {name}")
    except Exception as e:
        logger.error(f"Job failed: {name} - {e}", exc_info=True)


if __name__ == "__main__":
    main()
