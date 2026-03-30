"""
Enhanced news and SEC filing fetcher.
Aggregates from Yahoo Finance RSS, NewsAPI, and SEC EDGAR.
Includes macro/industry news based on sector themes and fundamental financial data.
"""

import feedparser
import requests
import yfinance as yf
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum


class NewsCategory(Enum):
    """Categories for news classification."""
    COMPANY_SPECIFIC = "Company Specific"
    MACRO_INDUSTRY = "Macro/Industry"
    SEC_FILING = "SEC Filing"


class FilingPriority(Enum):
    """Priority levels for SEC filings."""
    HIGH = "High"      # 8-K (Current Events)
    MEDIUM = "Medium"  # DEF14A (Proxy)
    STANDARD = "Standard"  # 10-K, 10-Q


@dataclass
class FinancialSnapshot:
    """Quantitative context for a ticker."""
    ticker: str
    current_price: Optional[float] = None
    previous_close: Optional[float] = None
    forward_pe: Optional[float] = None
    trailing_pe: Optional[float] = None
    market_cap: Optional[int] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    avg_volume: Optional[int] = None
    dividend_yield: Optional[float] = None
    beta: Optional[float] = None
    business_summary: str = ""
    sector: str = ""
    industry: str = ""
    fetched_at: Optional[datetime] = None

    def to_summary_string(self) -> str:
        """Return a formatted summary string for reports."""
        parts = [f"*{self.ticker}*"]
        if self.current_price:
            parts.append(f"Price: ${self.current_price:.2f}")
        if self.forward_pe:
            parts.append(f"Fwd P/E: {self.forward_pe:.1f}")
        if self.market_cap:
            cap_str = self._format_market_cap(self.market_cap)
            parts.append(f"MCap: {cap_str}")
        if self.sector:
            parts.append(f"Sector: {self.sector}")
        return " | ".join(parts)

    @staticmethod
    def _format_market_cap(cap: int) -> str:
        """Format market cap in human-readable form."""
        if cap >= 1_000_000_000_000:
            return f"${cap / 1_000_000_000_000:.2f}T"
        elif cap >= 1_000_000_000:
            return f"${cap / 1_000_000_000:.2f}B"
        elif cap >= 1_000_000:
            return f"${cap / 1_000_000:.2f}M"
        return f"${cap:,}"


@dataclass
class NewsItem:
    """Container for a news article or filing."""
    ticker: str
    title: str
    summary: str
    source: str
    url: str
    published: Optional[datetime]
    category: str = "Company Specific"
    priority: str = "Standard"  # For SEC filings: High, Medium, Standard
    thematic_keywords: list[str] = field(default_factory=list)


@dataclass
class TickerReport:
    """Complete report for a single ticker with financials and news."""
    ticker: str
    financial_snapshot: Optional[FinancialSnapshot]
    company_news: list[NewsItem]
    macro_news: list[NewsItem]
    sec_filings: list[NewsItem]

    @property
    def all_news(self) -> list[NewsItem]:
        """Return all news items combined."""
        return self.company_news + self.macro_news + self.sec_filings

    @property
    def high_priority_filings(self) -> list[NewsItem]:
        """Return only high-priority SEC filings (8-K)."""
        return [f for f in self.sec_filings if f.priority == FilingPriority.HIGH.value]


class NewsFetcher:
    """Fetches news from multiple sources with macro/industry context and fundamentals."""

    # Priority mapping for SEC filing types
    FILING_PRIORITY_MAP = {
        "8-K": FilingPriority.HIGH,
        "DEF14A": FilingPriority.MEDIUM,
        "DEF 14A": FilingPriority.MEDIUM,
        "10-K": FilingPriority.STANDARD,
        "10-Q": FilingPriority.STANDARD,
    }

    # Comprehensive thematic mapping for macro news
    THEMATIC_MAP = {
        # Tech Giants
        "AAPL": {
            "keywords": ["Consumer Electronics", "Smartphone Market", "Augmented Reality",
                        "App Store Regulation", "iPhone Sales", "Apple Silicon"],
            "themes": ["tech hardware", "mobile ecosystem", "wearables"]
        },
        "MSFT": {
            "keywords": ["Cloud Computing", "Enterprise Software", "AI Integration",
                        "Azure Growth", "Gaming Industry", "Copilot AI"],
            "themes": ["enterprise tech", "cloud infrastructure", "productivity software"]
        },
        "GOOGL": {
            "keywords": ["Digital Advertising", "Search Engine", "AI Development",
                        "Antitrust Regulation", "YouTube", "Waymo Autonomous"],
            "themes": ["digital ads", "AI research", "cloud services"]
        },
        "GOOG": {
            "keywords": ["Digital Advertising", "Search Engine", "AI Development",
                        "Antitrust Regulation", "YouTube", "Waymo Autonomous"],
            "themes": ["digital ads", "AI research", "cloud services"]
        },
        "AMZN": {
            "keywords": ["E-commerce", "Cloud Services AWS", "Retail Disruption",
                        "Logistics Innovation", "Prime Membership", "Alexa AI"],
            "themes": ["retail", "cloud computing", "logistics"]
        },
        "META": {
            "keywords": ["Social Media", "Digital Advertising", "Metaverse VR",
                        "Instagram Reels", "WhatsApp Business", "AI Chatbots"],
            "themes": ["social platforms", "virtual reality", "digital ads"]
        },
        # Semiconductors & AI
        "NVDA": {
            "keywords": ["AI Chips", "Data Center Demand", "Semiconductor Trade Policy",
                        "GPU Computing", "CUDA Platform", "Autonomous Driving"],
            "themes": ["AI infrastructure", "gaming", "data centers"]
        },
        "AMD": {
            "keywords": ["CPU Market", "Data Center Chips", "Gaming Processors",
                        "Intel Competition", "AI Accelerators"],
            "themes": ["semiconductors", "computing", "gaming"]
        },
        "INTC": {
            "keywords": ["Semiconductor Manufacturing", "Foundry Services", "PC Market",
                        "Chip Fabrication", "Moore's Law"],
            "themes": ["chip manufacturing", "computing", "foundry"]
        },
        # Electric Vehicles & Energy
        "TSLA": {
            "keywords": ["Electric Vehicles", "Lithium Supply", "Auto Charging Infrastructure",
                        "EV Subsidies", "Battery Technology", "Autonomous Driving FSD"],
            "themes": ["EVs", "clean energy", "automotive"]
        },
        # Financial & ETFs
        "SPY": {
            "keywords": ["Federal Reserve", "Inflation Data", "S&P 500 Outlook",
                        "Interest Rates", "Economic Indicators", "Market Volatility"],
            "themes": ["macro economy", "monetary policy", "equities"]
        },
        "QQQ": {
            "keywords": ["Tech Sector", "NASDAQ", "Growth Stocks",
                        "Tech Earnings", "Innovation Economy"],
            "themes": ["tech stocks", "growth investing", "NASDAQ"]
        },
        "VOO": {
            "keywords": ["Federal Reserve", "Inflation Data", "S&P 500 Outlook",
                        "Index Investing", "Passive Management"],
            "themes": ["index funds", "passive investing", "large cap"]
        },
        "VTI": {
            "keywords": ["US Economy", "Stock Market", "Economic Indicators",
                        "Total Market", "GDP Growth"],
            "themes": ["total market", "US equities", "diversification"]
        },
        # Other Popular Stocks
        "NFLX": {
            "keywords": ["Streaming Wars", "Content Spending", "Subscriber Growth",
                        "Ad-Supported Tier", "Password Sharing"],
            "themes": ["streaming", "entertainment", "media"]
        },
        "DIS": {
            "keywords": ["Disney Plus", "Theme Parks", "Box Office",
                        "Streaming Competition", "ESPN"],
            "themes": ["entertainment", "media", "streaming"]
        },
        "JPM": {
            "keywords": ["Banking Sector", "Interest Rates", "Credit Markets",
                        "Investment Banking", "Consumer Lending"],
            "themes": ["banking", "finance", "credit"]
        },
        "V": {
            "keywords": ["Payment Processing", "Digital Payments", "Fintech",
                        "Cross-border Transactions", "Consumer Spending"],
            "themes": ["payments", "fintech", "consumer"]
        },
    }

    def __init__(self, tickers: list[str], news_api_key: str = ""):
        self.tickers = [t.upper() for t in tickers]
        self.news_api_key = news_api_key
        self._snapshot_cache: dict[str, FinancialSnapshot] = {}

    def get_financial_snapshot(self, ticker: str, use_cache: bool = True) -> Optional[FinancialSnapshot]:
        """
        Fetches comprehensive financial metrics for a ticker.
        Uses caching to avoid redundant API calls.
        """
        ticker = ticker.upper()

        # Return cached if available and requested
        if use_cache and ticker in self._snapshot_cache:
            cached = self._snapshot_cache[ticker]
            # Cache valid for 5 minutes
            if cached.fetched_at and (datetime.now() - cached.fetched_at).seconds < 300:
                return cached

        try:
            t = yf.Ticker(ticker)
            info = t.info

            # Extract business summary with length limit
            summary = info.get("longBusinessSummary", "")
            if len(summary) > 300:
                summary = summary[:297] + "..."

            snapshot = FinancialSnapshot(
                ticker=ticker,
                current_price=info.get("currentPrice") or info.get("regularMarketPrice"),
                previous_close=info.get("previousClose") or info.get("regularMarketPreviousClose"),
                forward_pe=info.get("forwardPE"),
                trailing_pe=info.get("trailingPE"),
                market_cap=info.get("marketCap"),
                fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
                fifty_two_week_low=info.get("fiftyTwoWeekLow"),
                avg_volume=info.get("averageVolume"),
                dividend_yield=info.get("dividendYield"),
                beta=info.get("beta"),
                business_summary=summary,
                sector=info.get("sector", ""),
                industry=info.get("industry", ""),
                fetched_at=datetime.now(),
            )

            self._snapshot_cache[ticker] = snapshot
            return snapshot

        except Exception as e:
            print(f"Error fetching financial snapshot for {ticker}: {e}")
            return None

    def get_thematic_keywords(self, ticker: str) -> list[str]:
        """Get thematic keywords for a ticker for macro news search."""
        ticker = ticker.upper()
        if ticker in self.THEMATIC_MAP:
            return self.THEMATIC_MAP[ticker]["keywords"]

        # Fallback: try to get sector from yfinance
        snapshot = self.get_financial_snapshot(ticker)
        if snapshot and snapshot.sector:
            return [snapshot.sector, snapshot.industry] if snapshot.industry else [snapshot.sector]

        return []

    def fetch_for_ticker(self, ticker: str, days_back: int = 1) -> list[NewsItem]:
        """
        Fetch company-specific news for a single ticker from Yahoo RSS + NewsAPI.
        Deduplicates by title and returns top 8.
        """
        items = []

        # Yahoo Finance RSS (company specific)
        yahoo_items = self._fetch_yahoo_rss(ticker)
        items.extend(yahoo_items)

        # NewsAPI company-specific (if key available)
        if self.news_api_key:
            newsapi_items = self._fetch_newsapi(
                ticker, days_back,
                category=NewsCategory.COMPANY_SPECIFIC.value
            )
            items.extend(newsapi_items)

        # Deduplicate by title (case-insensitive)
        unique_items = self._deduplicate_news(items)

        # Sort by published date (newest first)
        unique_items.sort(key=lambda x: x.published or datetime.min, reverse=True)

        return unique_items[:8]

    def fetch_macro_news(self, ticker: str, days_back: int = 2) -> list[NewsItem]:
        """
        Fetches news based on the sector/theme rather than just the ticker.
        Uses thematic keywords to capture industry-wide changes.
        """
        if not self.news_api_key:
            return []

        keywords = self.get_thematic_keywords(ticker)
        if not keywords:
            return []

        # Build a sophisticated query string
        query = " OR ".join([f'"{kw}"' for kw in keywords[:3]])

        items = self._fetch_newsapi(
            query,
            days_back,
            category=NewsCategory.MACRO_INDUSTRY.value,
            thematic_keywords=keywords
        )

        return items[:5]  # Limit macro news

    def fetch_filings(self, ticker: str, days_back: int = 7) -> list[NewsItem]:
        """
        Fetch SEC filings for a ticker from EDGAR.
        Includes priority flagging for 8-K filings.
        """
        items = []
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")

            url = (
                f"https://efts.sec.gov/LATEST/search-index?"
                f'q="{ticker}"&dateRange=custom&startdt={start_str}&enddt={end_str}'
                f"&forms=8-K,DEF14A,10-Q,10-K"
            )

            headers = {
                "User-Agent": "StockAgent/1.0 (Personal Research Tool)",
                "Accept": "application/json",
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            hits = data.get("hits", {}).get("hits", [])

            for hit in hits[:5]:
                source_data = hit.get("_source", {})
                form_type = source_data.get("form", "Filing")
                file_date_str = source_data.get("file_date", "")
                display_names = source_data.get("display_names", ["Unknown"])
                company = display_names[0] if display_names else "Unknown"

                # Parse date
                filed_date = None
                if file_date_str:
                    try:
                        filed_date = datetime.strptime(file_date_str, "%Y-%m-%d")
                    except ValueError:
                        pass

                # Determine priority
                priority = self.FILING_PRIORITY_MAP.get(
                    form_type, FilingPriority.STANDARD
                ).value

                # Build filing URL
                cik = source_data.get("ciks", [""])[0] if source_data.get("ciks") else ""
                filing_url = (
                    f"https://www.sec.gov/cgi-bin/browse-edgar?"
                    f"action=getcompany&CIK={cik}&type={form_type}"
                )

                # Create summary based on filing type
                if form_type == "8-K":
                    summary = "IMPORTANT: Current event or material change disclosure"
                elif form_type in ("DEF14A", "DEF 14A"):
                    summary = "Proxy statement - shareholder voting matters"
                elif form_type == "10-K":
                    summary = "Annual report - comprehensive business overview"
                elif form_type == "10-Q":
                    summary = "Quarterly report - financial update"
                else:
                    summary = f"SEC {form_type} filing"

                items.append(
                    NewsItem(
                        ticker=ticker.upper(),
                        title=f"{form_type}: {company}",
                        summary=summary,
                        source="SEC EDGAR",
                        url=filing_url,
                        published=filed_date,
                        category=NewsCategory.SEC_FILING.value,
                        priority=priority,
                    )
                )

        except Exception as e:
            print(f"Error fetching SEC filings for {ticker}: {e}")

        # Sort by priority (High first) then by date
        items.sort(
            key=lambda x: (
                0 if x.priority == FilingPriority.HIGH.value else
                1 if x.priority == FilingPriority.MEDIUM.value else 2,
                x.published or datetime.min
            ),
            reverse=True
        )

        return items

    def fetch_ticker_report(self, ticker: str, days_back: int = 1) -> TickerReport:
        """
        Fetch complete report for a single ticker including financials and all news.
        """
        ticker = ticker.upper()

        # Financial snapshot
        snapshot = self.get_financial_snapshot(ticker)

        # Company-specific news
        company_news = self.fetch_for_ticker(ticker, days_back)

        # Macro/industry news
        macro_news = self.fetch_macro_news(ticker, days_back=2)

        # SEC filings
        sec_filings = self.fetch_filings(ticker, days_back=7)

        return TickerReport(
            ticker=ticker,
            financial_snapshot=snapshot,
            company_news=company_news,
            macro_news=macro_news,
            sec_filings=sec_filings,
        )

    def fetch_all(self, days_back: int = 1) -> dict[str, TickerReport]:
        """
        Fetch comprehensive reports for all tickers.
        Returns dict mapping ticker -> TickerReport with financials and categorized news.
        """
        result = {}
        for ticker in self.tickers:
            try:
                report = self.fetch_ticker_report(ticker, days_back)
                result[ticker] = report
            except Exception as e:
                print(f"Error fetching report for {ticker}: {e}")
                # Create empty report on error
                result[ticker] = TickerReport(
                    ticker=ticker,
                    financial_snapshot=None,
                    company_news=[],
                    macro_news=[],
                    sec_filings=[],
                )
        return result

    def fetch_all_legacy(self, days_back: int = 1) -> dict[str, list[NewsItem]]:
        """
        Legacy method for backward compatibility.
        Returns dict mapping ticker -> list of NewsItem.
        """
        result = {}
        for ticker in self.tickers:
            report = self.fetch_ticker_report(ticker, days_back)
            all_items = report.all_news
            if all_items:
                result[ticker] = all_items
        return result

    def _fetch_yahoo_rss(self, ticker: str) -> list[NewsItem]:
        """Fetch news from Yahoo Finance RSS feed."""
        items = []
        try:
            url = (
                f"https://feeds.finance.yahoo.com/rss/2.0/headline?"
                f"s={ticker}&region=US&lang=en-US"
            )
            feed = feedparser.parse(url)

            for entry in feed.entries[:5]:
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])

                items.append(
                    NewsItem(
                        ticker=ticker.upper(),
                        title=entry.get("title", ""),
                        summary=entry.get("summary", "")[:200] if entry.get("summary") else "",
                        source="Yahoo Finance",
                        url=entry.get("link", ""),
                        published=published,
                        category=NewsCategory.COMPANY_SPECIFIC.value,
                    )
                )
        except Exception as e:
            print(f"Error fetching Yahoo RSS for {ticker}: {e}")

        return items

    def _fetch_newsapi(
        self,
        query: str,
        days_back: int = 1,
        category: str = "Company Specific",
        thematic_keywords: Optional[list[str]] = None
    ) -> list[NewsItem]:
        """Fetch news from NewsAPI."""
        items = []
        if not self.news_api_key:
            return items

        try:
            from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

            url = "https://newsapi.org/v2/everything"
            params = {
                "q": query,
                "from": from_date,
                "language": "en",
                "sortBy": "relevancy",
                "pageSize": 5,
                "apiKey": self.news_api_key,
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            for article in data.get("articles", []):
                published = None
                if article.get("publishedAt"):
                    try:
                        published = datetime.fromisoformat(
                            article["publishedAt"].replace("Z", "+00:00")
                        ).replace(tzinfo=None)
                    except ValueError:
                        published = datetime.now()

                # Extract ticker from query (first word or the query itself)
                ticker_label = query.split()[0].upper() if " " in query else query.upper()
                # Clean up ticker label
                ticker_label = ticker_label.strip('"').strip("'")

                items.append(
                    NewsItem(
                        ticker=ticker_label,
                        title=article.get("title", ""),
                        summary=(
                            article.get("description", "")[:200]
                            if article.get("description") else ""
                        ),
                        source=article.get("source", {}).get("name", "NewsAPI"),
                        url=article.get("url", ""),
                        published=published,
                        category=category,
                        thematic_keywords=thematic_keywords or [],
                    )
                )
        except Exception as e:
            print(f"Error fetching NewsAPI for {query}: {e}")

        return items

    def _deduplicate_news(self, items: list[NewsItem]) -> list[NewsItem]:
        """Remove duplicate news items based on title similarity."""
        seen_titles = set()
        unique_items = []
        for item in items:
            title_lower = item.title.lower().strip()
            if title_lower and title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_items.append(item)
        return unique_items
