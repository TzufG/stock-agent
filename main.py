#!/usr/bin/env python3
"""
Stock Agent - AI-powered stock monitoring with WhatsApp alerts.

Usage:
    python main.py              # Run the agent (scheduler mode)
    python main.py --check      # Run a single price check
    python main.py --briefing   # Send a daily briefing now
    python main.py --analyze TICKER  # Send analysis for a specific ticker
    python main.py --reset      # Reset all price baselines
"""

import sys
import time
import signal
import argparse
from datetime import datetime

import schedule

from config import Config
from alerts import check_price_alerts, get_alert_manager
from ai_digest import send_daily_briefing, send_ticker_analysis


# Flag for graceful shutdown
running = True


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global running
    print("\nShutting down gracefully...")
    running = False


def job_price_check():
    """Scheduled job: Check prices and send alerts if thresholds breached."""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Running price check...")

    try:
        alerted = check_price_alerts()
        if alerted:
            print(f"Alerts triggered for: {', '.join(alerted)}")
        else:
            print("No alerts triggered")
    except Exception as e:
        print(f"Error in price check: {e}")


def job_daily_briefing():
    """Scheduled job: Send the daily morning briefing."""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Sending daily briefing...")

    try:
        success = send_daily_briefing()
        if not success:
            print("Failed to send daily briefing")
    except Exception as e:
        print(f"Error in daily briefing: {e}")


def run_scheduler():
    """Run the main scheduler loop."""
    global running

    print("\n" + "=" * 50)
    print("STOCK AGENT STARTED")
    print("=" * 50)

    Config.print_config()

    # Validate configuration
    issues = Config.validate()
    if issues:
        print("\nConfiguration issues:")
        for issue in issues:
            print(f"  - {issue}")
        print()

    # Schedule price checks
    interval = Config.PRICE_CHECK_INTERVAL
    schedule.every(interval).minutes.do(job_price_check)
    print(f"\nScheduled: Price check every {interval} minutes")

    # Schedule daily briefing
    briefing_time = Config.DAILY_BRIEFING_TIME
    schedule.every().day.at(briefing_time).do(job_daily_briefing)
    print(f"Scheduled: Daily briefing at {briefing_time}")

    # Run initial price check to set baselines
    print("\nRunning initial price check to set baselines...")
    job_price_check()

    print("\nAgent is running. Press Ctrl+C to stop.\n")

    # Main loop
    while running:
        schedule.run_pending()
        time.sleep(1)

    print("Agent stopped.")


def cmd_check():
    """Command: Run a single price check."""
    print("Running price check...")
    alerted = check_price_alerts()
    if alerted:
        print(f"Alerts triggered for: {', '.join(alerted)}")
    else:
        print("No alerts triggered")


def cmd_briefing():
    """Command: Send daily briefing now."""
    print("Generating and sending daily briefing...")
    success = send_daily_briefing()
    if success:
        print("Briefing sent successfully!")
    else:
        print("Failed to send briefing")
        sys.exit(1)


def cmd_analyze(ticker: str):
    """Command: Send analysis for a specific ticker."""
    print(f"Generating and sending analysis for {ticker}...")
    success = send_ticker_analysis(ticker.upper())
    if success:
        print("Analysis sent successfully!")
    else:
        print("Failed to send analysis")
        sys.exit(1)


def cmd_reset():
    """Command: Reset all price baselines."""
    manager = get_alert_manager()
    manager.reset_all_baselines()
    print("All baselines have been reset")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Stock Agent - AI-powered stock monitoring with WhatsApp alerts"
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help="Run a single price check"
    )
    parser.add_argument(
        "--briefing",
        action="store_true",
        help="Send daily briefing now"
    )
    parser.add_argument(
        "--analyze",
        type=str,
        metavar="TICKER",
        help="Send analysis for a specific ticker"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset all price baselines"
    )

    args = parser.parse_args()

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Handle commands
    if args.check:
        cmd_check()
    elif args.briefing:
        cmd_briefing()
    elif args.analyze:
        cmd_analyze(args.analyze)
    elif args.reset:
        cmd_reset()
    else:
        # Default: run scheduler
        run_scheduler()


if __name__ == "__main__":
    main()
