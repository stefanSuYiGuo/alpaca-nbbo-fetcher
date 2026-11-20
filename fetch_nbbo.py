#!/usr/bin/env python3
"""
Fetch historical SIP NBBO quotes from Alpaca for US equities
during regular trading hours (09:30-16:00 America/New_York)
and save to CSV.

Data is tick-level (every quote update), not minute bars.

Output structure:
  data/
    AAPL/
      AAPL_2026_06_01.csv
      AAPL_2026_06_02.csv
      ...
    SPY/
      ...
"""

import os
import sys
import time
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo

import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockQuotesRequest
from alpaca.data.enums import DataFeed

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SYMBOLS = [
    # Large-cap stocks
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
    # Broad ETFs
    "SPY", "QQQ", "IWM", "DIA", "VTI", "VOO",
    # Leveraged / inverse ETFs
    "TQQQ", "SQQQ", "SOXL", "SOXS", "UPRO", "SPXU",
    "TNA", "TZA", "FAS", "FAZ", "LABU", "LABD",
]
START_DATE = "2026-06-01"
END_DATE = "2026-11-19"
OUTPUT_DIR = "data"
FEED = DataFeed.SIP

# Regular trading hours (ET)
MARKET_OPEN = dtime(9, 30)
MARKET_CLOSE = dtime(16, 0)
ET = ZoneInfo("America/New_York")

# Rate-limit / retry settings (free tier is 200 req/min)
MAX_RETRIES = 5
BASE_SLEEP = 0.4  # seconds between requests to stay under 200/min

# ---------------------------------------------------------------------------
def get_client() -> StockHistoricalDataClient:
    key = os.environ.get("APCA_API_KEY_ID")
    secret = os.environ.get("APCA_API_SECRET_KEY")
    if not key or not secret:
        print("Error: set APCA_API_KEY_ID and APCA_API_SECRET_KEY environment variables.", file=sys.stderr)
        sys.exit(1)
    return StockHistoricalDataClient(api_key=key, secret_key=secret)


def fetch_with_retry(client, request, max_retries=MAX_RETRIES):
    """Fetch quotes with exponential backoff on rate-limit or transient errors."""
    for attempt in range(max_retries):
        try:
            return client.get_stock_quotes(request)
        except Exception as e:
            msg = str(e).lower()
            if "429" in msg or "too many" in msg or "rate" in msg or "timeout" in msg:
                sleep_time = BASE_SLEEP * (2 ** attempt) + 1
                print(f"    Rate limited / transient error, sleeping {sleep_time:.1f}s (attempt {attempt+1})")
                time.sleep(sleep_time)
                continue
            raise
    raise RuntimeError(f"Failed after {max_retries} retries")


def main():
    client = get_client()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    start_date = datetime.fromisoformat(START_DATE).date()
    end_date = datetime.fromisoformat(END_DATE).date()

    for symbol in SYMBOLS:
        symbol_dir = os.path.join(OUTPUT_DIR, symbol)
        os.makedirs(symbol_dir, exist_ok=True)
        print(f"\n=== {symbol} ===")

        current = start_date
        while current <= end_date:
            if current.weekday() >= 5:  # weekend
                current += timedelta(days=1)
                continue

            day_str = current.isoformat()
            filename = f"{symbol}_{day_str.replace('-', '_')}.csv"
            outfile = os.path.join(symbol_dir, filename)

            if os.path.exists(outfile):
                print(f"  {day_str}: already exists, skipping")
                current += timedelta(days=1)
                continue

            day_start = datetime.combine(current, MARKET_OPEN, tzinfo=ET)
            day_end = datetime.combine(current, MARKET_CLOSE, tzinfo=ET)

            all_pages = []
            page_token = None
            page_num = 0

            while True:
                request = StockQuotesRequest(
                    symbol_or_symbols=symbol,
                    start=day_start,
                    end=day_end,
                    feed=FEED,
                    limit=10000,
                    page_token=page_token,
                )

                try:
                    quotes = fetch_with_retry(client, request)
                except Exception as e:
                    print(f"  {day_str}: error - {e}")
                    break

                if not quotes or not hasattr(quotes, "df") or quotes.df.empty:
                    if page_num == 0:
                        print(f"  {day_str}: no data")
                    break

                df = quotes.df.reset_index()
                keep = [c for c in [
                    "timestamp", "symbol", "bid_price", "bid_size",
                    "ask_price", "ask_size", "bid_exchange", "ask_exchange"
                ] if c in df.columns]
                all_pages.append(df[keep])
                page_num += 1

                # Pagination
                next_token = getattr(quotes, "next_page_token", None)
                if not next_token:
                    break
                page_token = next_token
                time.sleep(BASE_SLEEP)

            if all_pages:
                result = pd.concat(all_pages, ignore_index=True)
                result.to_csv(outfile, index=False)
                print(f"  {day_str}: {len(result)} quotes -> {outfile}")

            time.sleep(BASE_SLEEP)
            current += timedelta(days=1)

    print("\nDone.")


if __name__ == "__main__":
    main()
