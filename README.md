# Alpaca NBBO Fetcher

Python script that downloads historical SIP National Best Bid and Offer (NBBO) quotes from Alpaca for US equities during regular trading hours and saves them as CSV files.

## Data granularity

The script requests **tick-level quotes** (every NBBO update) via the Alpaca historical quotes endpoint with `feed=sip`.  
This is **not** minute-bar data. For liquid symbols you can easily receive tens of thousands of rows per trading minute.

## Requirements

- Python 3.10+
- Alpaca API keys (paper or live) with access to historical SIP data

## Setup

```bash
pip install -r requirements.txt
```

Set environment variables:

```bash
export APCA_API_KEY_ID="your_key_id"
export APCA_API_SECRET_KEY="your_secret_key"
```

## Usage

Edit the `SYMBOLS`, `START_DATE` and `END_DATE` constants at the top of `fetch_nbbo.py`, then:

```bash
python fetch_nbbo.py
```

CSV files are written to the `nbbo_data/` directory (one file per symbol).

## Notes

- Free Alpaca accounts can access historical SIP data older than 15 minutes.
- The script iterates day-by-day and only requests regular hours (09:30–16:00 America/New_York).
- Weekends are skipped. Holidays are not specially filtered (Alpaca will simply return no data).
- Rate limits apply; the script prints progress per day.

## License

MIT
