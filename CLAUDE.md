# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the agent (continuous monitoring with scheduler)
python main.py

# Install dependencies
pip install -r requirements.txt

# Verify syntax
python -c "import ast; [ast.parse(open(f).read()) for f in ['main.py','agent.py','price_monitor.py','news_fetcher.py','ai_summarizer.py','whatsapp_sender.py','config.py']]"
```

## Architecture

**Data Flow:**
1. `main.py` sets up logging (stdout + agent.log) and runs the scheduler:
   - Morning report at `MORNING_REPORT_TIME` (default 07:30)
   - Price check every `PRICE_CHECK_INTERVAL_MINUTES` (default 15)
   - Sends morning report immediately on startup
2. `agent.py` (`StockAgent`) orchestrates all components
3. `price_monitor.py` (`PriceMonitor`) fetches prices via yfinance:
   - `fetch_all()` returns `list[PriceSnapshot]`
   - `check_alerts()` returns tickers that moved >= threshold from `last_alert_price`
   - `morning_summary_lines()` returns formatted price lines
4. `news_fetcher.py` (`NewsFetcher`) aggregates from three sources:
   - Yahoo Finance RSS
   - NewsAPI (optional, requires `NEWS_API_KEY`)
   - SEC EDGAR (8-K, DEF14A, 10-Q, 10-K)
5. `ai_summarizer.py` generates content:
   - `build_morning_digest()` calls Claude claude-sonnet-4-20250514 with fallback
   - `build_alert_message()` instant formatting, no API call
6. `whatsapp_sender.py` (`WhatsAppSender`) sends via Twilio:
   - `send()` for single messages (truncates at 1500 chars)
   - `send_chunks()` for long messages

**Key Data Classes:**
- `PriceSnapshot`: ticker, price, prev_close, change_pct, direction, timestamp
- `NewsItem`: ticker, title, summary, source, url, published

**Configuration** (`config.py`):
- All settings loaded from `.env` as module-level variables
- No Config class - direct imports like `config.WATCHLIST`
