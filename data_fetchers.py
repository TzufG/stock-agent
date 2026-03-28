"""
Data fetching modules for stock prices, news, and SEC filings.
"""

import feedparser
import requests
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass

from config import Config


@dataclass
class PriceData:
    """Container for stock price information."""
    ticker: str
    current_price: float
    previous_close: float
    change_percent: float
    market_cap: Optional[float] = None
    volume: Optional[int] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    name: Optional[str] = None


@dataclass
class NewsItem:
    """Container for a news article."""
    title: str
    source: str
    url: str
    published: Optional[datetime] = None
    summary: Optional[str] = None


@dataclass
class SECFiling:
    """Container for an SEC filing."""
    ticker: str
    filing_type: str
    title: str
    url: str
    filed_date: Optional[datetime] = None


# =============================================================================
# PRICE DATA (yfinance)
# =============================================================================

def fetch_price(ticker: str) -> Optional[PriceData]:
    """
    Fetch current price data for a single ticker using yfinance.
    Returns None if the ticker is invalid or data unavailable.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        current_price = info.get("regularMarketPrice") or info.get("currentPrice")
        previous_close = info.get("regularMarketPreviousClose") or info.get("previousClose")

        if current_price is None or previous_close is None:
            # Try getting from history as fallback
            hist = stock.history(period="2d")
            if len(hist) >= 1:
                current_price = float(hist["Close"].iloc[-1])
                if len(hist) >= 2:
                    previous_close = float(hist["Close"].iloc[-2])
                else:
                    previous_close = current_price

        if current_price is None:
            return None

        change_percent = ((current_price - previous_close) / previous_close) * 100 if previous_close else 0

        return PriceData(
            ticker=ticker.upper(),
            current_price=current_price,
            previous_close=previous_close,
            change_percent=round(change_percent, 2),
            market_cap=info.get("marketCap"),
            volume=info.get("regularMarketVolume") or info.get("volume"),
            day_high=info.get("dayHigh"),
            day_low=info.get("dayLow"),
            fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
            fifty_two_week_low=info.get("fiftyTwoWeekLow"),
            name=info.get("shortName") or info.get("longName"),
        )
    except Exception as e:
        print(f"Error fetching price for {ticker}: {e}")
        return None


def fetch_prices(tickers: list[str]) -> dict[str, PriceData]:
    """
    Fetch price data for multiple tickers.
    Returns a dict mapping ticker -> PriceData (only for successful fetches).
    """
    results = {}
    for ticker in tickers:
        data = fetch_price(ticker)
        if data:
            results[ticker.upper()] = data
    return results


def fetch_historical_prices(ticker: str, days: int = 30) -> Optional[list[dict]]:
    """
    Fetch historical price data for charting/analysis.
    Returns a list of dicts with date, open, high, low, close, volume.
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=f"{days}d")

        if hist.empty:
            return None

        return [
            {
                "date": idx.strftime("%Y-%m-%d"),
                "open": round(row["Open"], 2),
                "high": round(row["High"], 2),
                "low": round(row["Low"], 2),
                "close": round(row["Close"], 2),
                "volume": int(row["Volume"]),
            }
            for idx, row in hist.iterrows()
        ]
    except Exception as e:
        print(f"Error fetching historical prices for {ticker}: {e}")
        return None


# =============================================================================
# NEWS (Yahoo Finance RSS + NewsAPI)
# =============================================================================

def fetch_yahoo_finance_news(ticker: str, limit: int = 5) -> list[NewsItem]:
    """
    Fetch news from Yahoo Finance RSS feed for a ticker.
    """
    news_items = []
    try:
        # Yahoo Finance RSS feed URL
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
        feed = feedparser.parse(url)

        for entry in feed.entries[:limit]:
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])

            news_items.append(
                NewsItem(
                    title=entry.get("title", ""),
                    source="Yahoo Finance",
                    url=entry.get("link", ""),
                    published=published,
                    summary=entry.get("summary", ""),
                )
            )
    except Exception as e:
        print(f"Error fetching Yahoo Finance news for {ticker}: {e}")

    return news_items


def fetch_newsapi_news(query: str, limit: int = 5) -> list[NewsItem]:
    """
    Fetch news from NewsAPI for a query (ticker or company name).
    Requires NEWSAPI_KEY to be configured.
    """
    if not Config.NEWSAPI_KEY:
        return []

    news_items = []
    try:
        from newsapi import NewsApiClient

        newsapi = NewsApiClient(api_key=Config.NEWSAPI_KEY)

        # Search for articles from the past 7 days
        from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        response = newsapi.get_everything(
            q=query,
            from_param=from_date,
            language="en",
            sort_by="relevancy",
            page_size=limit,
        )

        for article in response.get("articles", []):
            published = None
            if article.get("publishedAt"):
                try:
                    published = datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00"))
                except ValueError:
                    pass

            news_items.append(
                NewsItem(
                    title=article.get("title", ""),
                    source=article.get("source", {}).get("name", "Unknown"),
                    url=article.get("url", ""),
                    published=published,
                    summary=article.get("description", ""),
                )
            )
    except Exception as e:
        print(f"Error fetching NewsAPI news for {query}: {e}")

    return news_items


def fetch_all_news(ticker: str, limit: int = 10) -> list[NewsItem]:
    """
    Fetch news from all available sources for a ticker.
    Combines Yahoo Finance RSS and NewsAPI results.
    """
    yahoo_news = fetch_yahoo_finance_news(ticker, limit=limit // 2)
    newsapi_news = fetch_newsapi_news(ticker, limit=limit // 2)

    all_news = yahoo_news + newsapi_news

    # Sort by published date (newest first), handling None dates
    all_news.sort(key=lambda x: x.published or datetime.min, reverse=True)

    return all_news[:limit]


# =============================================================================
# SEC FILINGS (EDGAR)
# =============================================================================

# SEC EDGAR RSS feed base URL
SEC_EDGAR_RSS_BASE = "https://www.sec.gov/cgi-bin/browse-edgar"

# Filing types we care about
SEC_FILING_TYPES = ["8-K", "10-Q", "10-K", "DEF 14A"]


def fetch_sec_filings(ticker: str, filing_types: Optional[list[str]] = None, limit: int = 10) -> list[SECFiling]:
    """
    Fetch SEC filings for a ticker from EDGAR.
    Filters by filing_types if provided, otherwise gets all types we care about.
    """
    if filing_types is None:
        filing_types = SEC_FILING_TYPES

    filings = []

    try:
        # First, we need to get the CIK for the ticker
        cik = get_cik_for_ticker(ticker)
        if not cik:
            return []

        # Fetch RSS feed for company filings
        url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=&dateb=&owner=include&count={limit * 2}&output=atom"

        headers = {
            "User-Agent": "StockAgent/1.0 (Personal Use)",
            "Accept": "application/atom+xml",
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        feed = feedparser.parse(response.content)

        for entry in feed.entries:
            title = entry.get("title", "")

            # Check if this is a filing type we care about
            filing_type = None
            for ft in filing_types:
                if ft in title:
                    filing_type = ft
                    break

            if not filing_type:
                continue

            filed_date = None
            if hasattr(entry, "updated_parsed") and entry.updated_parsed:
                filed_date = datetime(*entry.updated_parsed[:6])

            filings.append(
                SECFiling(
                    ticker=ticker.upper(),
                    filing_type=filing_type,
                    title=title,
                    url=entry.get("link", ""),
                    filed_date=filed_date,
                )
            )

            if len(filings) >= limit:
                break

    except Exception as e:
        print(f"Error fetching SEC filings for {ticker}: {e}")

    return filings


def get_cik_for_ticker(ticker: str) -> Optional[str]:
    """
    Look up the SEC CIK number for a ticker symbol.
    """
    try:
        # SEC provides a JSON mapping of tickers to CIKs
        url = "https://www.sec.gov/files/company_tickers.json"
        headers = {"User-Agent": "StockAgent/1.0 (Personal Use)"}

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()

        ticker_upper = ticker.upper()
        for entry in data.values():
            if entry.get("ticker", "").upper() == ticker_upper:
                # CIK needs to be zero-padded to 10 digits
                return str(entry.get("cik_str", "")).zfill(10)

        return None
    except Exception as e:
        print(f"Error looking up CIK for {ticker}: {e}")
        return None


def fetch_all_sec_filings(tickers: list[str], limit_per_ticker: int = 5) -> dict[str, list[SECFiling]]:
    """
    Fetch SEC filings for multiple tickers.
    Returns a dict mapping ticker -> list of SECFiling.
    """
    results = {}
    for ticker in tickers:
        filings = fetch_sec_filings(ticker, limit=limit_per_ticker)
        if filings:
            results[ticker.upper()] = filings
    return results


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def fetch_all_data_for_ticker(ticker: str) -> dict:
    """
    Fetch all available data (price, news, SEC filings) for a single ticker.
    Returns a dict with all the data.
    """
    return {
        "price": fetch_price(ticker),
        "news": fetch_all_news(ticker),
        "sec_filings": fetch_sec_filings(ticker),
    }


def fetch_all_data_for_watchlist(tickers: list[str]) -> dict[str, dict]:
    """
    Fetch all available data for all tickers in the watchlist.
    Returns a dict mapping ticker -> data dict.
    """
    results = {}
    for ticker in tickers:
        results[ticker.upper()] = fetch_all_data_for_ticker(ticker)
    return results
