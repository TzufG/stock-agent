"""
AI-powered summarization using Claude.
"""

from datetime import datetime
from typing import Optional
from dataclasses import dataclass

import anthropic
import yfinance as yf

from news_fetcher import NewsItem


@dataclass
class TickerFundamentals:
    """Container for ticker financial fundamentals."""
    ticker: str
    pe_ratio: Optional[float]
    market_cap: Optional[float]
    market_cap_str: str
    sector: str
    industry: str
    fifty_two_week_high: Optional[float]
    fifty_two_week_low: Optional[float]
    current_price: Optional[float]


def fetch_fundamentals(ticker: str) -> TickerFundamentals:
    """Fetch fundamental financial data for a ticker using yfinance."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Format market cap
        market_cap = info.get("marketCap")
        if market_cap:
            if market_cap >= 1e12:
                market_cap_str = f"${market_cap / 1e12:.2f}T"
            elif market_cap >= 1e9:
                market_cap_str = f"${market_cap / 1e9:.2f}B"
            elif market_cap >= 1e6:
                market_cap_str = f"${market_cap / 1e6:.2f}M"
            else:
                market_cap_str = f"${market_cap:,.0f}"
        else:
            market_cap_str = "N/A"

        return TickerFundamentals(
            ticker=ticker.upper(),
            pe_ratio=info.get("trailingPE") or info.get("forwardPE"),
            market_cap=market_cap,
            market_cap_str=market_cap_str,
            sector=info.get("sector", "N/A"),
            industry=info.get("industry", "N/A"),
            fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
            fifty_two_week_low=info.get("fiftyTwoWeekLow"),
            current_price=info.get("currentPrice") or info.get("regularMarketPrice"),
        )
    except Exception as e:
        print(f"Error fetching fundamentals for {ticker}: {e}")
        return TickerFundamentals(
            ticker=ticker.upper(),
            pe_ratio=None,
            market_cap=None,
            market_cap_str="N/A",
            sector="N/A",
            industry="N/A",
            fifty_two_week_high=None,
            fifty_two_week_low=None,
            current_price=None,
        )


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


def build_equity_research_summary(
    news_by_ticker: dict[str, list[NewsItem]],
    api_key: str,
) -> str:
    """
    Generate professional 3-paragraph equity research summaries for each ticker.

    For each ticker, produces:
    - Paragraph 1: Fundamental & Operational Health
    - Paragraph 2: Current News & Sentiment Analysis
    - Paragraph 3: Macro Context & Industry Vector
    """
    if not api_key:
        return _fallback_research_summary(news_by_ticker)

    today = datetime.now().strftime("%B %d, %Y")
    summaries = []

    for ticker, news_items in news_by_ticker.items():
        # Fetch fundamentals for this ticker
        fundamentals = fetch_fundamentals(ticker)

        # Categorize news items
        sec_filings = [n for n in news_items if n.source == "SEC EDGAR"]
        news_articles = [n for n in news_items if n.source != "SEC EDGAR"]

        # Format news for the prompt
        news_text = ""
        if news_articles:
            news_text = "\n".join([
                f"- {n.title} ({n.source}, {n.published.strftime('%Y-%m-%d') if n.published else 'N/A'})"
                for n in news_articles[:6]
            ])
        else:
            news_text = "No recent news articles available."

        # Format SEC filings for the prompt
        filings_text = ""
        if sec_filings:
            filings_text = "\n".join([
                f"- {f.title} (Filed: {f.published.strftime('%Y-%m-%d') if f.published else 'N/A'})"
                for f in sec_filings
            ])
        else:
            filings_text = "No recent SEC filings."

        # Format fundamentals
        pe_str = f"{fundamentals.pe_ratio:.2f}" if fundamentals.pe_ratio else "N/A"
        price_str = f"${fundamentals.current_price:.2f}" if fundamentals.current_price else "N/A"
        high_52w = f"${fundamentals.fifty_two_week_high:.2f}" if fundamentals.fifty_two_week_high else "N/A"
        low_52w = f"${fundamentals.fifty_two_week_low:.2f}" if fundamentals.fifty_two_week_low else "N/A"

        fundamentals_text = f"""
- Market Cap: {fundamentals.market_cap_str}
- P/E Ratio: {pe_str}
- Current Price: {price_str}
- 52-Week Range: {low_52w} - {high_52w}
- Sector: {fundamentals.sector}
- Industry: {fundamentals.industry}
"""

        # Generate AI summary for this ticker
        try:
            client = anthropic.Anthropic(api_key=api_key)

            system_prompt = """You are a Senior Equity Research Analyst writing professional investment summaries.
Your analysis should be:
- Data-driven and objective
- Professional and analytical in tone
- Focused on actionable insights
- Free of generic filler content

Use markdown formatting with clear headers."""

            user_prompt = f"""Generate a professional 3-paragraph equity research summary for {ticker} as of {today}.

FINANCIAL DATA:
{fundamentals_text}

RECENT SEC FILINGS:
{filings_text}

RECENT NEWS:
{news_text}

Write exactly 3 paragraphs with the following structure:

**Paragraph 1 - Fundamental & Operational Health:**
Analyze the company's current financial position using the P/E ratio, Market Cap, and recent SEC filings. Summarize their core business strength and any immediate operational risks or successes.

**Paragraph 2 - Current News & Sentiment Analysis:**
Synthesize the recent headlines. What is the market narrative right now? Identify if sentiment is bullish or bearish and highlight the single most important catalyst (earnings, product launch, legal issue, etc.).

**Paragraph 3 - Macro Context & Industry Vector:**
Explain how broader trends (AI, interest rates, supply chain, regulatory shifts) affect this specific ticker. Provide a forward-looking statement on how global shifts will impact the company over the next 6-12 months.

Be specific and data-driven. Avoid generic statements. If data is limited, acknowledge it and focus on what IS available."""

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1200,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            ticker_summary = f"## {ticker}\n\n{response.content[0].text}"
            summaries.append(ticker_summary)

        except Exception as e:
            print(f"Error generating research summary for {ticker}: {e}")
            summaries.append(_fallback_ticker_summary(ticker, fundamentals, news_items))

    # Combine all summaries
    header = f"# Equity Research Summary - {today}\n\n"
    return header + "\n\n---\n\n".join(summaries)


def _fallback_research_summary(news_by_ticker: dict[str, list[NewsItem]]) -> str:
    """Generate a fallback summary when AI is unavailable."""
    today = datetime.now().strftime("%B %d, %Y")
    header = f"# Equity Research Summary - {today}\n\n"
    header += "_Note: AI analysis unavailable. Displaying raw data._\n\n"

    sections = []
    for ticker, items in news_by_ticker.items():
        fundamentals = fetch_fundamentals(ticker)
        sections.append(_fallback_ticker_summary(ticker, fundamentals, items))

    return header + "\n\n---\n\n".join(sections)


def _fallback_ticker_summary(
    ticker: str,
    fundamentals: TickerFundamentals,
    news_items: list[NewsItem],
) -> str:
    """Generate a fallback summary for a single ticker."""
    lines = [f"## {ticker}"]

    # Fundamentals section
    pe_str = f"{fundamentals.pe_ratio:.2f}" if fundamentals.pe_ratio else "N/A"
    lines.append(f"\n**Fundamentals:** Market Cap: {fundamentals.market_cap_str} | P/E: {pe_str} | Sector: {fundamentals.sector}")

    # SEC Filings
    sec_filings = [n for n in news_items if n.source == "SEC EDGAR"]
    if sec_filings:
        lines.append("\n**Recent SEC Filings:**")
        for f in sec_filings[:3]:
            date_str = f.published.strftime('%Y-%m-%d') if f.published else "N/A"
            lines.append(f"- {f.title} ({date_str})")

    # News
    news_articles = [n for n in news_items if n.source != "SEC EDGAR"]
    if news_articles:
        lines.append("\n**Recent News:**")
        for n in news_articles[:4]:
            date_str = n.published.strftime('%Y-%m-%d') if n.published else "N/A"
            lines.append(f"- {n.title} ({n.source}, {date_str})")

    return "\n".join(lines)
