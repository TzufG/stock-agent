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
    forward_pe: Optional[float]
    market_cap: Optional[float]
    market_cap_str: str
    sector: str
    industry: str
    fifty_two_week_high: Optional[float]
    fifty_two_week_low: Optional[float]
    current_price: Optional[float]
    beta: Optional[float]
    dividend_yield: Optional[float]
    revenue_growth: Optional[float]
    profit_margin: Optional[float]
    debt_to_equity: Optional[float]
    business_summary: str


# Industry keywords for macro context analysis
INDUSTRY_KEYWORDS = {
    # Technology & AI
    "Technology": [
        "AI adoption", "cloud infrastructure", "cybersecurity spending",
        "digital transformation", "semiconductor demand", "enterprise software"
    ],
    "Semiconductors": [
        "AI chip demand", "foundry capacity", "chip export restrictions",
        "data center buildout", "automotive chips", "supply chain reshoring"
    ],
    "Software—Infrastructure": [
        "cloud migration", "AI integration", "enterprise spending",
        "SaaS growth", "cybersecurity threats", "developer tools"
    ],
    "Software—Application": [
        "AI copilots", "productivity software", "subscription fatigue",
        "enterprise adoption", "vertical SaaS", "automation trends"
    ],
    "Internet Content & Information": [
        "digital advertising", "AI search disruption", "content moderation",
        "antitrust regulation", "user engagement", "creator economy"
    ],
    # Defense & Aerospace
    "Aerospace & Defense": [
        "defense budget increases", "geopolitical tensions", "hypersonic weapons",
        "space commercialization", "nuclear modernization", "NATO expansion"
    ],
    # Consumer & Retail
    "Consumer Electronics": [
        "smartphone upgrade cycles", "wearables growth", "AR/VR adoption",
        "supply chain costs", "premium pricing power", "ecosystem lock-in"
    ],
    "Discount Stores": [
        "consumer spending", "inflation impact", "private label growth",
        "e-commerce competition", "wage pressures", "inventory management"
    ],
    "Internet Retail": [
        "e-commerce penetration", "logistics automation", "last-mile delivery",
        "advertising revenue", "subscription services", "marketplace dynamics"
    ],
    # Financial
    "Asset Management": [
        "interest rate environment", "AUM flows", "passive vs active",
        "alternative investments", "fee compression", "regulatory changes"
    ],
    "Banks—Diversified": [
        "net interest margins", "credit quality", "capital requirements",
        "digital banking", "loan growth", "deposit competition"
    ],
    # Healthcare
    "Drug Manufacturers": [
        "patent cliffs", "GLP-1 competition", "FDA approvals",
        "pricing pressure", "M&A activity", "pipeline catalysts"
    ],
    "Biotechnology": [
        "clinical trial results", "gene therapy", "AI drug discovery",
        "funding environment", "regulatory pathways", "partnership deals"
    ],
    # Energy
    "Oil & Gas": [
        "OPEC+ production", "energy transition", "refining margins",
        "geopolitical supply risks", "carbon regulations", "LNG demand"
    ],
    "Utilities—Regulated Electric": [
        "rate case outcomes", "renewable integration", "grid modernization",
        "data center power demand", "nuclear renaissance", "regulatory support"
    ],
    # ETFs - Broad Market
    "Exchange Traded Fund": [
        "Federal Reserve policy", "inflation trajectory", "earnings growth",
        "market concentration", "recession indicators", "geopolitical risks"
    ],
}


def _format_market_cap(market_cap: Optional[float]) -> str:
    """Format market cap in human-readable form."""
    if not market_cap:
        return "N/A"
    if market_cap >= 1e12:
        return f"${market_cap / 1e12:.2f}T"
    elif market_cap >= 1e9:
        return f"${market_cap / 1e9:.2f}B"
    elif market_cap >= 1e6:
        return f"${market_cap / 1e6:.2f}M"
    return f"${market_cap:,.0f}"


def get_industry_keywords(industry: str, sector: str) -> list[str]:
    """Get relevant macro/industry keywords for context analysis."""
    # Try industry first, then sector, then default
    keywords = INDUSTRY_KEYWORDS.get(industry, [])
    if not keywords:
        keywords = INDUSTRY_KEYWORDS.get(sector, [])
    if not keywords:
        # Default macro keywords
        keywords = [
            "interest rate environment", "inflation trends", "economic growth",
            "regulatory changes", "competitive dynamics", "market sentiment"
        ]
    return keywords


def fetch_fundamentals(ticker: str) -> TickerFundamentals:
    """Fetch comprehensive financial data for a ticker using yfinance."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Extract business summary (truncated)
        summary = info.get("longBusinessSummary", "")
        if len(summary) > 400:
            summary = summary[:397] + "..."

        return TickerFundamentals(
            ticker=ticker.upper(),
            pe_ratio=info.get("trailingPE"),
            forward_pe=info.get("forwardPE"),
            market_cap=info.get("marketCap"),
            market_cap_str=_format_market_cap(info.get("marketCap")),
            sector=info.get("sector", "N/A"),
            industry=info.get("industry", "N/A"),
            fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
            fifty_two_week_low=info.get("fiftyTwoWeekLow"),
            current_price=info.get("currentPrice") or info.get("regularMarketPrice"),
            beta=info.get("beta"),
            dividend_yield=info.get("dividendYield"),
            revenue_growth=info.get("revenueGrowth"),
            profit_margin=info.get("profitMargins"),
            debt_to_equity=info.get("debtToEquity"),
            business_summary=summary,
        )
    except Exception as e:
        print(f"Error fetching fundamentals for {ticker}: {e}")
        return TickerFundamentals(
            ticker=ticker.upper(),
            pe_ratio=None,
            forward_pe=None,
            market_cap=None,
            market_cap_str="N/A",
            sector="N/A",
            industry="N/A",
            fifty_two_week_high=None,
            fifty_two_week_low=None,
            current_price=None,
            beta=None,
            dividend_yield=None,
            revenue_growth=None,
            profit_margin=None,
            debt_to_equity=None,
            business_summary="",
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

        # Format news for the prompt (include summary for context)
        news_text = ""
        if news_articles:
            news_lines = []
            for n in news_articles[:6]:
                date_str = n.published.strftime('%Y-%m-%d') if n.published else 'N/A'
                line = f"- **{n.title}** ({n.source}, {date_str})"
                if n.summary:
                    line += f"\n  {n.summary}"
                news_lines.append(line)
            news_text = "\n".join(news_lines)
        else:
            news_text = "No recent news articles available."

        # Format SEC filings with filing type context
        filings_text = ""
        if sec_filings:
            filing_lines = []
            for f in sec_filings:
                date_str = f.published.strftime('%Y-%m-%d') if f.published else 'N/A'
                # Add context based on filing type
                filing_context = ""
                if "8-K" in f.title:
                    filing_context = " [Material Event]"
                elif "10-K" in f.title:
                    filing_context = " [Annual Report]"
                elif "10-Q" in f.title:
                    filing_context = " [Quarterly Report]"
                elif "DEF14A" in f.title or "DEF 14A" in f.title:
                    filing_context = " [Proxy Statement]"
                filing_lines.append(f"- {f.title}{filing_context} (Filed: {date_str})")
            filings_text = "\n".join(filing_lines)
        else:
            filings_text = "No recent SEC filings in the past 7 days."

        # Build comprehensive fundamentals text
        pe_str = f"{fundamentals.pe_ratio:.2f}" if fundamentals.pe_ratio else "N/A"
        fwd_pe_str = f"{fundamentals.forward_pe:.2f}" if fundamentals.forward_pe else "N/A"
        price_str = f"${fundamentals.current_price:.2f}" if fundamentals.current_price else "N/A"
        high_52w = f"${fundamentals.fifty_two_week_high:.2f}" if fundamentals.fifty_two_week_high else "N/A"
        low_52w = f"${fundamentals.fifty_two_week_low:.2f}" if fundamentals.fifty_two_week_low else "N/A"
        beta_str = f"{fundamentals.beta:.2f}" if fundamentals.beta else "N/A"
        div_yield_str = f"{fundamentals.dividend_yield * 100:.2f}%" if fundamentals.dividend_yield else "N/A"
        rev_growth_str = f"{fundamentals.revenue_growth * 100:.1f}%" if fundamentals.revenue_growth else "N/A"
        margin_str = f"{fundamentals.profit_margin * 100:.1f}%" if fundamentals.profit_margin else "N/A"
        de_str = f"{fundamentals.debt_to_equity:.1f}" if fundamentals.debt_to_equity else "N/A"

        # Calculate 52-week position
        position_52w = ""
        if fundamentals.current_price and fundamentals.fifty_two_week_high and fundamentals.fifty_two_week_low:
            range_size = fundamentals.fifty_two_week_high - fundamentals.fifty_two_week_low
            if range_size > 0:
                position = (fundamentals.current_price - fundamentals.fifty_two_week_low) / range_size * 100
                position_52w = f" (currently at {position:.0f}% of 52-week range)"

        fundamentals_text = f"""
**Valuation Metrics:**
- Market Cap: {fundamentals.market_cap_str}
- Trailing P/E: {pe_str} | Forward P/E: {fwd_pe_str}
- Current Price: {price_str}
- 52-Week Range: {low_52w} - {high_52w}{position_52w}

**Financial Health:**
- Beta: {beta_str}
- Dividend Yield: {div_yield_str}
- Revenue Growth (YoY): {rev_growth_str}
- Profit Margin: {margin_str}
- Debt-to-Equity: {de_str}

**Classification:**
- Sector: {fundamentals.sector}
- Industry: {fundamentals.industry}
"""

        # Add business summary if available
        if fundamentals.business_summary:
            fundamentals_text += f"\n**Business:** {fundamentals.business_summary}\n"

        # Get industry-specific keywords for macro context
        industry_keywords = get_industry_keywords(fundamentals.industry, fundamentals.sector)
        keywords_str = ", ".join(industry_keywords[:6])

        # Generate AI summary for this ticker
        try:
            client = anthropic.Anthropic(api_key=api_key)

            system_prompt = """You are a Senior Equity Research Analyst at a top-tier investment bank.

Your analysis must be:
- Rigorously data-driven with specific numbers and metrics
- Professional, objective, and analytical in tone
- Focused on actionable investment insights
- Free of generic filler or boilerplate language
- Concise yet comprehensive

Structure each paragraph with a clear topic sentence followed by supporting analysis."""

            user_prompt = f"""Generate a professional equity research summary for **{ticker}** as of {today}.

═══════════════════════════════════════════════════════════
FINANCIAL DATA & FUNDAMENTALS
═══════════════════════════════════════════════════════════
{fundamentals_text}

═══════════════════════════════════════════════════════════
RECENT SEC FILINGS (Past 7 Days)
═══════════════════════════════════════════════════════════
{filings_text}

═══════════════════════════════════════════════════════════
RECENT NEWS & HEADLINES (Yahoo Finance, NewsAPI)
═══════════════════════════════════════════════════════════
{news_text}

═══════════════════════════════════════════════════════════
INDUSTRY CONTEXT KEYWORDS
═══════════════════════════════════════════════════════════
{keywords_str}

═══════════════════════════════════════════════════════════
OUTPUT FORMAT: Write exactly 3 paragraphs with these headers
═══════════════════════════════════════════════════════════

### Fundamental & Operational Health
Analyze the company's current financial position. Use the P/E ratio (trailing vs forward), market cap classification, profit margins, debt levels, and any recent 10-K/10-Q filings. Assess core business strength, balance sheet health, and identify any immediate operational risks or recent successes from SEC disclosures.

### Current News & Sentiment Analysis
Synthesize the recent headlines from Yahoo Finance and NewsAPI. What is the prevailing "market narrative" right now? Determine if sentiment is bullish, bearish, or neutral with supporting evidence. Identify the single most important **catalyst** driving current sentiment (e.g., earnings beat/miss, product launch, executive change, legal/regulatory action, M&A activity).

### Macro Context & Industry Vector
Using the industry keywords provided ({keywords_str}), explain how macroeconomic and sector-specific trends are affecting this ticker. Address relevant factors like: interest rate environment, AI/technology shifts, regulatory changes, supply chain dynamics, or geopolitical risks. Provide a forward-looking statement on the company's trajectory over the next 6-12 months given these global shifts.

CRITICAL INSTRUCTIONS:
- Be specific: cite actual numbers, percentages, and metrics from the data provided
- Avoid vague statements like "the company is well-positioned" without supporting data
- If data is limited or unavailable, acknowledge this explicitly
- Keep each paragraph focused and substantive (4-6 sentences each)"""

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            ticker_summary = f"## {ticker}\n\n{response.content[0].text}"
            summaries.append(ticker_summary)

        except Exception as e:
            print(f"Error generating research summary for {ticker}: {e}")
            summaries.append(_fallback_ticker_summary(ticker, fundamentals, news_items))

    # Combine all summaries
    header = f"# Equity Research Summary\n**Date:** {today}\n\n"
    return header + "\n\n---\n\n".join(summaries)


def _fallback_research_summary(news_by_ticker: dict[str, list[NewsItem]]) -> str:
    """Generate a fallback summary when AI is unavailable."""
    today = datetime.now().strftime("%B %d, %Y")
    header = f"# Equity Research Summary\n**Date:** {today}\n\n"
    header += "> *Note: AI analysis unavailable. Displaying structured raw data.*\n\n"

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
    lines.append("\n### Fundamental & Operational Health")
    pe_str = f"{fundamentals.pe_ratio:.2f}" if fundamentals.pe_ratio else "N/A"
    fwd_pe_str = f"{fundamentals.forward_pe:.2f}" if fundamentals.forward_pe else "N/A"
    margin_str = f"{fundamentals.profit_margin * 100:.1f}%" if fundamentals.profit_margin else "N/A"
    de_str = f"{fundamentals.debt_to_equity:.1f}" if fundamentals.debt_to_equity else "N/A"

    lines.append(f"- **Market Cap:** {fundamentals.market_cap_str}")
    lines.append(f"- **Trailing P/E:** {pe_str} | **Forward P/E:** {fwd_pe_str}")
    lines.append(f"- **Profit Margin:** {margin_str} | **Debt/Equity:** {de_str}")
    lines.append(f"- **Sector:** {fundamentals.sector} | **Industry:** {fundamentals.industry}")

    # SEC Filings
    sec_filings = [n for n in news_items if n.source == "SEC EDGAR"]
    if sec_filings:
        lines.append("\n**Recent SEC Filings:**")
        for f in sec_filings[:3]:
            date_str = f.published.strftime('%Y-%m-%d') if f.published else "N/A"
            lines.append(f"- {f.title} ({date_str})")

    # News section
    lines.append("\n### Current News & Sentiment Analysis")
    news_articles = [n for n in news_items if n.source != "SEC EDGAR"]
    if news_articles:
        for n in news_articles[:4]:
            date_str = n.published.strftime('%Y-%m-%d') if n.published else "N/A"
            lines.append(f"- **{n.title}** ({n.source}, {date_str})")
    else:
        lines.append("- No recent news available.")

    # Macro context section
    lines.append("\n### Macro Context & Industry Vector")
    industry_keywords = get_industry_keywords(fundamentals.industry, fundamentals.sector)
    lines.append(f"**Relevant Themes:** {', '.join(industry_keywords[:4])}")
    lines.append("\n*AI-generated analysis unavailable. Review news and filings above for context.*")

    return "\n".join(lines)
