"""
AI-powered digest generation using Claude.
Creates daily morning briefings with price performance, news summaries, and SEC filings.
"""

from datetime import datetime
from typing import Optional

import anthropic

from config import Config
from data_fetchers import (
    PriceData,
    NewsItem,
    SECFiling,
    fetch_prices,
    fetch_all_news,
    fetch_all_sec_filings,
    fetch_historical_prices,
)
from alerts import send_whatsapp_message


def create_claude_client() -> Optional[anthropic.Anthropic]:
    """Create an Anthropic client if API key is configured."""
    if not Config.ANTHROPIC_API_KEY:
        print("Anthropic API key not configured")
        return None

    try:
        return anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
    except Exception as e:
        print(f"Error creating Anthropic client: {e}")
        return None


def format_price_data_for_prompt(prices: dict[str, PriceData]) -> str:
    """Format price data for inclusion in the AI prompt."""
    if not prices:
        return "No price data available."

    lines = []
    for ticker, data in prices.items():
        change_emoji = "\u2B06\uFE0F" if data.change_percent >= 0 else "\u2B07\uFE0F"
        lines.append(
            f"- {ticker} ({data.name or 'N/A'}): ${data.current_price:.2f} "
            f"({'+' if data.change_percent >= 0 else ''}{data.change_percent:.2f}% {change_emoji})"
        )

    return "\n".join(lines)


def format_news_for_prompt(news_by_ticker: dict[str, list[NewsItem]]) -> str:
    """Format news data for inclusion in the AI prompt."""
    if not news_by_ticker:
        return "No news available."

    lines = []
    for ticker, news_items in news_by_ticker.items():
        lines.append(f"\n{ticker}:")
        for item in news_items[:3]:  # Limit to top 3 per ticker
            date_str = item.published.strftime("%m/%d") if item.published else "N/A"
            lines.append(f"  - [{date_str}] {item.title} (Source: {item.source})")

    return "\n".join(lines)


def format_filings_for_prompt(filings_by_ticker: dict[str, list[SECFiling]]) -> str:
    """Format SEC filings for inclusion in the AI prompt."""
    if not filings_by_ticker:
        return "No recent SEC filings."

    lines = []
    for ticker, filings in filings_by_ticker.items():
        lines.append(f"\n{ticker}:")
        for filing in filings[:3]:  # Limit to top 3 per ticker
            date_str = filing.filed_date.strftime("%m/%d") if filing.filed_date else "N/A"
            lines.append(f"  - [{date_str}] {filing.filing_type}: {filing.title}")

    return "\n".join(lines)


def generate_daily_briefing(tickers: Optional[list[str]] = None) -> Optional[str]:
    """
    Generate an AI-written daily briefing for the watchlist.
    Returns the briefing text or None if generation fails.
    """
    if tickers is None:
        tickers = Config.WATCHLIST

    if not tickers:
        print("No tickers in watchlist")
        return None

    client = create_claude_client()
    if not client:
        return None

    print(f"Fetching data for {len(tickers)} tickers...")

    # Fetch all data
    prices = fetch_prices(tickers)
    news_by_ticker = {ticker: fetch_all_news(ticker, limit=5) for ticker in tickers}
    filings_by_ticker = fetch_all_sec_filings(tickers, limit_per_ticker=3)

    # Format data for the prompt
    price_summary = format_price_data_for_prompt(prices)
    news_summary = format_news_for_prompt(news_by_ticker)
    filings_summary = format_filings_for_prompt(filings_by_ticker)

    # Build the prompt
    today = datetime.now().strftime("%A, %B %d, %Y")

    prompt = f"""You are a professional financial analyst writing a concise morning briefing for an investor.

Today is {today}.

Here is the current market data for the watchlist:

## Price Performance (vs previous close)
{price_summary}

## Recent News Headlines
{news_summary}

## Recent SEC Filings
{filings_summary}

---

Write a concise, WhatsApp-friendly morning briefing that:
1. Opens with a brief market mood summary (1-2 sentences)
2. Highlights the biggest movers (up and down) with brief context
3. Summarizes the most important news (2-3 key stories)
4. Notes any significant SEC filings worth attention
5. Ends with 1-2 things to watch today

Keep it under 1500 characters to fit WhatsApp nicely. Use simple formatting (no markdown headers).
Use relevant emojis sparingly for visual appeal.
Be direct and actionable - this is for a busy investor checking their phone."""

    try:
        print("Generating AI briefing...")

        response = client.messages.create(
            model=Config.CLAUDE_MODEL,
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        briefing = response.content[0].text

        # Add header
        header = f"\U0001F4C8 *MORNING BRIEFING* \U0001F4C8\n{today}\n\n"
        full_briefing = header + briefing

        return full_briefing

    except Exception as e:
        print(f"Error generating briefing: {e}")
        return None


def send_daily_briefing(tickers: Optional[list[str]] = None) -> bool:
    """
    Generate and send the daily briefing via WhatsApp.
    Returns True if successful.
    """
    briefing = generate_daily_briefing(tickers)

    if not briefing:
        print("Failed to generate daily briefing")
        return False

    print("Sending daily briefing via WhatsApp...")
    success = send_whatsapp_message(briefing)

    if success:
        print("Daily briefing sent successfully!")
    else:
        print("Failed to send daily briefing")

    return success


def generate_ticker_deep_dive(ticker: str) -> Optional[str]:
    """
    Generate a deeper analysis for a single ticker.
    Useful for on-demand analysis requests.
    """
    client = create_claude_client()
    if not client:
        return None

    print(f"Fetching detailed data for {ticker}...")

    # Fetch all data
    from data_fetchers import fetch_price, fetch_all_news, fetch_sec_filings, fetch_historical_prices

    price = fetch_price(ticker)
    news = fetch_all_news(ticker, limit=10)
    filings = fetch_sec_filings(ticker, limit=5)
    historical = fetch_historical_prices(ticker, days=30)

    if not price:
        print(f"Could not fetch data for {ticker}")
        return None

    # Format historical performance
    hist_summary = "No historical data available."
    if historical and len(historical) >= 2:
        first_price = historical[0]["close"]
        last_price = historical[-1]["close"]
        period_change = ((last_price - first_price) / first_price) * 100
        hist_summary = f"30-day change: {'+' if period_change >= 0 else ''}{period_change:.2f}%"

    # Format news
    news_lines = []
    for item in news[:5]:
        date_str = item.published.strftime("%m/%d") if item.published else "N/A"
        news_lines.append(f"- [{date_str}] {item.title}")
    news_text = "\n".join(news_lines) if news_lines else "No recent news."

    # Format filings
    filing_lines = []
    for filing in filings[:3]:
        date_str = filing.filed_date.strftime("%m/%d") if filing.filed_date else "N/A"
        filing_lines.append(f"- [{date_str}] {filing.filing_type}: {filing.title}")
    filings_text = "\n".join(filing_lines) if filing_lines else "No recent filings."

    prompt = f"""You are a professional financial analyst providing a quick but insightful analysis.

Ticker: {ticker}
Company: {price.name or 'N/A'}

## Current Price Data
- Current Price: ${price.current_price:.2f}
- Previous Close: ${price.previous_close:.2f}
- Day Change: {'+' if price.change_percent >= 0 else ''}{price.change_percent:.2f}%
- Day Range: ${price.day_low:.2f} - ${price.day_high:.2f}
- 52-Week Range: ${price.fifty_two_week_low:.2f} - ${price.fifty_two_week_high:.2f}
- Volume: {price.volume:,}
- Market Cap: ${price.market_cap:,.0f}
- {hist_summary}

## Recent News
{news_text}

## Recent SEC Filings
{filings_text}

---

Write a concise analysis (under 1200 characters) covering:
1. Current price action and what it suggests
2. Key news driving the stock
3. Any notable SEC filings and their implications
4. A brief outlook

Be direct and insightful. Use emojis sparingly for emphasis.
This is for a WhatsApp message, so keep formatting simple."""

    try:
        print("Generating AI analysis...")

        response = client.messages.create(
            model=Config.CLAUDE_MODEL,
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        analysis = response.content[0].text

        header = f"\U0001F50D *{ticker} ANALYSIS*\n{datetime.now().strftime('%B %d, %Y')}\n\n"
        full_analysis = header + analysis

        return full_analysis

    except Exception as e:
        print(f"Error generating analysis: {e}")
        return None


def send_ticker_analysis(ticker: str) -> bool:
    """Generate and send a deep dive analysis for a ticker."""
    analysis = generate_ticker_deep_dive(ticker)

    if not analysis:
        print(f"Failed to generate analysis for {ticker}")
        return False

    print(f"Sending {ticker} analysis via WhatsApp...")
    success = send_whatsapp_message(analysis)

    if success:
        print(f"{ticker} analysis sent successfully!")
    else:
        print(f"Failed to send {ticker} analysis")

    return success
