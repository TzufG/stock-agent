"""
News and SEC filing fetcher.
Aggregates from Yahoo Finance RSS, NewsAPI, and SEC EDGAR.
"""

import feedparser
import requests
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class NewsItem:
    """Container for a news article or filing."""
    ticker: str
    title: str
    summary: str
    source: str
    url: str
    published: Optional[datetime]


class NewsFetcher:
    """Fetches news from multiple sources."""

    def __init__(self, tickers: list[str], news_api_key: str = ""):
        self.tickers = [t.upper() for t in tickers]
        self.news_api_key = news_api_key

    def fetch_for_ticker(self, ticker: str, days_back: int = 1) -> list[NewsItem]:
        """
        Fetch news for a single ticker from Yahoo RSS + NewsAPI.
        Deduplicates by title and returns top 8.
        """
        items = []

        # Yahoo Finance RSS
        yahoo_items = self._fetch_yahoo_rss(ticker)
        items.extend(yahoo_items)

        # NewsAPI (if key available)
        if self.news_api_key:
            newsapi_items = self._fetch_newsapi(ticker, days_back)
            items.extend(newsapi_items)

        # Deduplicate by title (case-insensitive)
        seen_titles = set()
        unique_items = []
        for item in items:
            title_lower = item.title.lower().strip()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_items.append(item)

        # Sort by published date (newest first)
        unique_items.sort(key=lambda x: x.published or datetime.min, reverse=True)

        return unique_items[:8]

    def fetch_filings(self, ticker: str, days_back: int = 7) -> list[NewsItem]:
        """
        Fetch SEC filings for a ticker from EDGAR.
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
                source = hit.get("_source", {})
                form_type = source.get("form", "Filing")
                file_date_str = source.get("file_date", "")
                display_names = source.get("display_names", ["Unknown"])
                company = display_names[0] if display_names else "Unknown"

                # Parse date
                filed_date = None
                if file_date_str:
                    try:
                        filed_date = datetime.strptime(file_date_str, "%Y-%m-%d")
                    except ValueError:
                        pass

                # Build filing URL
                accession = source.get("adsh", "").replace("-", "")
                cik = source.get("ciks", [""])[0] if source.get("ciks") else ""
                filing_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={form_type}"

                items.append(
                    NewsItem(
                        ticker=ticker.upper(),
                        title=f"{form_type}: {company}",
                        summary=f"SEC {form_type} filing",
                        source="SEC EDGAR",
                        url=filing_url,
                        published=filed_date,
                    )
                )

        except Exception as e:
            print(f"Error fetching SEC filings for {ticker}: {e}")

        return items

    def fetch_all(self, days_back: int = 1) -> dict[str, list[NewsItem]]:
        """
        Fetch news for all tickers.
        Returns dict mapping ticker -> list of NewsItem.
        """
        result = {}
        for ticker in self.tickers:
            news = self.fetch_for_ticker(ticker, days_back)
            filings = self.fetch_filings(ticker, days_back=7)
            # Combine news and filings
            all_items = news + filings
            if all_items:
                result[ticker] = all_items
        return result

    def _fetch_yahoo_rss(self, ticker: str) -> list[NewsItem]:
        """Fetch news from Yahoo Finance RSS feed."""
        items = []
        try:
            url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
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
                    )
                )
        except Exception as e:
            print(f"Error fetching Yahoo RSS for {ticker}: {e}")

        return items

    def _fetch_newsapi(self, ticker: str, days_back: int = 1) -> list[NewsItem]:
        """Fetch news from NewsAPI."""
        items = []
        if not self.news_api_key:
            return items

        try:
            from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

            url = "https://newsapi.org/v2/everything"
            params = {
                "q": ticker,
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
                        pass

                items.append(
                    NewsItem(
                        ticker=ticker.upper(),
                        title=article.get("title", ""),
                        summary=article.get("description", "")[:200] if article.get("description") else "",
                        source=article.get("source", {}).get("name", "NewsAPI"),
                        url=article.get("url", ""),
                        published=published,
                    )
                )
        except Exception as e:
            print(f"Error fetching NewsAPI for {ticker}: {e}")

        return items
