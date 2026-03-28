"""
AI-powered summarization using Claude.
"""

from datetime import datetime
from typing import Optional

import anthropic

from news_fetcher import NewsItem


def build_morning_digest(
    price_lines: list[str],
    news_by_ticker: dict[str, list[NewsItem]],
    api_key: str,
    watchlist: list[str],
) -> str:
    """
    Build an AI-generated morning digest using Claude.
    Falls back to a simple format if API fails.
    """
    today = datetime.now().strftime("%B %d, %Y")
    header = f"\U0001F4CA *Morning Briefing – {today}*"

    # Format price lines
    price_section = "\n".join(price_lines) if price_lines else "No price data available."

    # Format news by ticker
    news_sections = []
    for ticker in watchlist:
        items = news_by_ticker.get(ticker, [])
        if items:
            news_lines = [f"\n*{ticker}*:"]
            for item in items[:3]:
                date_str = item.published.strftime("%m/%d") if item.published else ""
                prefix = f"[{date_str}] " if date_str else ""
                news_lines.append(f"  - {prefix}{item.title} ({item.source})")
            news_sections.append("\n".join(news_lines))

    news_text = "\n".join(news_sections) if news_sections else "No news available."

    # Try to generate AI summary
    if not api_key:
        return _fallback_digest(header, price_section, news_text)

    try:
        client = anthropic.Anthropic(api_key=api_key)

        system_prompt = (
            "You are a financial news summarizer. Output plain text suitable for WhatsApp "
            "(no markdown headers, just *bold* for emphasis). Use emojis sparingly for visual appeal. "
            "Keep the total response under 1500 characters. Be factual and neutral."
        )

        user_prompt = f"""Today is {today}.

Here are the current prices for the watchlist:
{price_section}

Here is the recent news and SEC filings by ticker:
{news_text}

Please write a morning briefing that:
1. Starts with "{header}"
2. Lists each ticker's price change on its own line
3. Writes 2-3 sentences summarizing the key news for each ticker that has news
4. Ends with a "Key theme of the day" observation

Keep it concise and under 1500 characters total."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        return response.content[0].text

    except Exception as e:
        print(f"Error generating AI digest: {e}")
        return _fallback_digest(header, price_section, news_text, error=str(e))


def _fallback_digest(
    header: str,
    price_section: str,
    news_text: str,
    error: Optional[str] = None,
) -> str:
    """Generate a simple fallback digest when AI is unavailable."""
    parts = [header, "", price_section]

    if news_text and news_text != "No news available.":
        parts.extend(["", news_text])

    if error:
        parts.extend(["", f"_Note: AI summary unavailable ({error})_"])

    return "\n".join(parts)


def build_alert_message(
    ticker: str,
    change_pct: float,
    price: float,
    prev_close: float,
) -> str:
    """
    Build a simple price alert message.
    No Claude call needed - instant formatting.
    """
    direction = "UP" if change_pct >= 0 else "DOWN"
    emoji = "\U0001F7E2" if change_pct >= 0 else "\U0001F534"  # Green/Red circle
    arrow = "\u2B06\uFE0F" if change_pct >= 0 else "\u2B07\uFE0F"  # Up/Down arrow
    sign = "+" if change_pct >= 0 else ""

    message = f"""{emoji} *PRICE ALERT* {emoji}

*{ticker}* {arrow} {direction} {sign}{change_pct:.2f}%

Current: *${price:.2f}*
Previous: ${prev_close:.2f}

_Alert triggered at {datetime.now().strftime('%H:%M:%S')}_"""

    return message
