#!/usr/bin/env python3
"""
Fetch historical SIP NBBO quotes from Alpaca for US equities
during regular trading hours (09:30-16:00 America/New_York)
and save to CSV.

Data is tick-level (every quote update), not minute bars.
"""

import os
import sys
from datetime import datetime, time
from zoneinfo import ZoneInfo

import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockQuotesRequest
from alpaca.data.enums import DataFeed

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SYMBOLS = ["AAPL", "MSFT", "SPY"]  # edit this list
START_DATE = "2026-06-01"
END_DATE = "2026-11-19"
OUTPUT_DIR = "nbbo_data"
FEED = DataFeed.SIP

# Regular trading hours (ET)
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)
ET = ZoneInfo("America/New_York")

# ---------------------------------------------------------------------------
def get_client() -> StockHistoricalDataClient:
    key = os.environ.get("APCA_API_KEY_ID")
    secret = os.environ.get("APCA_API_SECRET_KEY")
    if not key or not secret:
        print("Error: set APCA_API_KEY_ID and APCA_API_SECRET_KEY environment variables.", file=sys.stderr)
        sys.exit(1)
    return StockHistoricalDataClient(api_key=key, secret_key=secret)


def trading_days(start: str, end: str):
    """Yield each calendar date in range (inclusive). Caller filters weekends/holidays."""
    current = datetime.fromisoformat(start).date()
    last = datetime.fromisoformat(end).date()
    while current <= last:
        yield current
        current = current.replace(day=current.day + 1) if current.day < 28 else current.replace(month=current.month + 1, day=1) if current.month < 12 else current.replace(year=current.year + 1, month=1, day=1)
        # simpler:
    # better way below in actual loop


def main():
    client = get_client()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    start_dt = datetime.fromisoformat(START_DATE)
    end_dt = datetime.fromisoformat(END_DATE)

    for symbol in SYMBOLS:
        print(f"Fetching {symbol} ...")
        all_rows = []

        # Iterate day by day to keep requests manageable and stay within free-tier constraints
        current = start_dt.date()
        end_date = end_dt.date()

        while current <= end_date:
            # Skip weekends
            if current.weekday() >= 5:
                current = current.fromordinal(current.toordinal() + 1)
                continue

            day_start = datetime.combine(current, MARKET_OPEN, tzinfo=ET)
            day_end = datetime.combine(current, MARKET_CLOSE, tzinfo=ET)

            request = StockQuotesRequest(
                symbol_or_symbols=symbol,
                start=day_start,
                end=day_end,
                feed=FEED,
                limit=10000,
            )

            try:
                quotes = client.get_stock_quotes(request)
                if quotes and hasattr(quotes, "df") and not quotes.df.empty:
                    df = quotes.df.reset_index()
                    # Keep only relevant columns
                    keep = [c for c in ["timestamp", "symbol", "bid_price", "bid_size", "ask_price", "ask_size", "bid_exchange", "ask_exchange"] if c in df.columns]
                    all_rows.append(df[keep])
                    print(f"  {current}: {len(df)} quotes")
                else:
                    print(f"  {current}: no data")
            except Exception as e:
                print(f"  {current}: error - {e}")

            current = current.fromordinal(current.toordinal() + 1)

        if all_rows:
            result = pd.concat(all_rows, ignore_index=True)
            outfile = os.path.join(OUTPUT_DIR, f"{symbol}_nbbo_{START_DATE}_to_{END_DATE}.csv")
            result.to_csv(outfile, index=False)
            print(f"Saved {len(result)} rows to {outfile}")
        else:
            print(f"No data for {symbol}")

    print("Done.")


if __name__ == "__main__":
    main()
