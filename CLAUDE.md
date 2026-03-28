# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the agent (continuous monitoring with scheduler)
python main.py

# One-off commands
python main.py --check              # Single price check
python main.py --briefing           # Send daily briefing now
python main.py --analyze TICKER     # Deep dive analysis for a ticker
python main.py --reset              # Reset all price baselines

# Install dependencies
pip install -r requirements.txt
```

## Architecture

This is a stock/ETF monitoring agent that sends WhatsApp alerts via Twilio.

**Data Flow:**
1. `main.py` runs the scheduler (`schedule` library) with two jobs:
   - Price check every N minutes (default 15)
   - Daily briefing at configured time (default 08:00)
2. `data_fetchers.py` pulls data from three sources:
   - **yfinance**: Real-time prices via `fetch_price()` / `fetch_prices()`
   - **Yahoo Finance RSS + NewsAPI**: News via `fetch_all_news()`
   - **SEC EDGAR**: Filings (8-K, 10-Q, 10-K, DEF14A) via `fetch_sec_filings()`
3. `alerts.py` manages price thresholds:
   - `AlertManager` tracks baselines in `baselines.json`
   - Triggers WhatsApp alert when price moves ≥threshold% from baseline
   - Resets baseline to current price after each alert
4. `ai_digest.py` generates AI content via Claude:
   - `generate_daily_briefing()`: Morning summary for all watchlist tickers
   - `generate_ticker_deep_dive()`: Single-ticker analysis

**Key Data Classes** (in `data_fetchers.py`):
- `PriceData`: Current price, change%, volume, 52-week range
- `NewsItem`: Title, source, URL, published date
- `SECFiling`: Filing type, title, URL, filed date

**Configuration** (`config.py`):
- All settings loaded from `.env` via `python-dotenv`
- `Config.validate()` returns list of missing required values
- Watchlist is comma-separated tickers in `WATCHLIST` env var

**State Persistence:**
- `baselines.json`: Alert baselines persisted between runs (gitignored)
